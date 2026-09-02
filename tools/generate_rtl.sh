#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
XS_ROOT=${XIANGSHAN_ROOT:-"$ROOT/third_party/XiangShan"}
CACHE_ROOT=${TEMPLATE_GENERATE_CACHE:-"$ROOT/.cache"}
MODULE=
CONFIG=DefaultConfig
VERSION=
FORCE_GENERATION=0
REPLACE_EVIDENCE=0
ESPRESSO_COMMIT=${ESPRESSO_COMMIT:-85265139e9598852f9388d293658a1977a829a01}

usage() {
  cat <<'EOF'
Usage: tools/generate_rtl.sh --module NAME [--config CONFIG] [--version vX.Y.Z]
                             [--force-generation] [--replace-evidence]

Generates XiangShan split SystemVerilog through TopMain, caches the selected
module by commit/config/tool fingerprint, and optionally writes persistent
evidence/<Module>/<version>/{manifest.json,ports.csv}.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --module) MODULE=${2:?missing module}; shift 2 ;;
    --config) CONFIG=${2:?missing config}; shift 2 ;;
    --version) VERSION=${2:?missing version}; shift 2 ;;
    --force-generation) FORCE_GENERATION=1; shift ;;
    --replace-evidence) REPLACE_EVIDENCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'error: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$MODULE" ]] || { usage >&2; exit 2; }
invocation="tools/generate_rtl.sh --module $MODULE --config $CONFIG${VERSION:+ --version $VERSION}"
if [[ -n "$VERSION" && ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'error: invalid version: %s\n' "$VERSION" >&2
  exit 2
fi
if [[ -n "$VERSION" ]]; then
  evidence_dir="$ROOT/evidence/$MODULE/$VERSION"
  if [[ -e "$evidence_dir/manifest.json" && $REPLACE_EVIDENCE -eq 0 ]]; then
    printf 'error: evidence already exists: %s (use --replace-evidence only for an explicitly documented repair)\n' "$evidence_dir" >&2
    exit 1
  fi
fi

"$ROOT/tools/preflight.sh" --module "$MODULE" --config "$CONFIG" --strict

commit=$(git -C "$XS_ROOT" rev-parse HEAD)
mill_version=$(tr -d '[:space:]' < "$XS_ROOT/.mill-version")
java_home=$("$ROOT/tools/bootstrap_jdk.sh")
java_version=$("$java_home/bin/java" -version 2>&1 | head -n 1)
flags='--issue E.b --num-cores 1 --target systemverilog --split-verilog --dump-fir --fpga-platform --reset-gen --ignore-read-enable-mem --default-layer-specialization=disable'
wrapper_hash=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$ROOT/tools/generate_rtl.sh")
fingerprint=$(printf '%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n' "$commit" "$CONFIG" "$mill_version" "$java_version" "$flags" "$(uname -s)" "$(uname -m)" "$ESPRESSO_COMMIT" "$wrapper_hash" | python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:20])')
cache_dir="$CACHE_ROOT/rtl/$fingerprint"
target_dir="$cache_dir/split"
cache_rtl="$target_dir/$MODULE.sv"
tool_versions="$cache_dir/tool_versions.json"

if [[ $FORCE_GENERATION -eq 0 && -s "$cache_rtl" ]]; then
  printf 'Using cached RTL: %s\n' "$cache_rtl"
else
  rm -rf "$target_dir"
  mkdir -p "$cache_dir" "$target_dir"
  mill=$("$ROOT/tools/bootstrap_mill.sh")
  espresso=$("$ROOT/tools/prepare_espresso.sh")
  bundled="$XS_ROOT/src/main/resources/espresso"
  if [[ "$espresso" == "$bundled" ]]; then
    espresso_desc="XiangShan bundled binary"
  else
    espresso_desc="native build $ESPRESSO_COMMIT for $(uname -s)/$(uname -m)"
  fi
  backup="$cache_dir/espresso.original"
  original_hash=$(git -C "$XS_ROOT" hash-object "src/main/resources/espresso")
  cp "$bundled" "$backup"
  restore() {
    cp "$backup" "$bundled"
    restored_hash=$(git -C "$XS_ROOT" hash-object "src/main/resources/espresso")
    if [[ "$restored_hash" != "$original_hash" ]]; then
      printf 'fatal: failed to restore XiangShan Espresso resource\n' >&2
      exit 1
    fi
  }
  trap restore EXIT INT TERM
  if [[ "$espresso" != "$bundled" ]]; then cp "$espresso" "$bundled"; fi

  command_text="$invocation"
  set +e
  (
    cd "$XS_ROOT"
    JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH" NOOP_HOME="$XS_ROOT" "$mill" -i -Djvm-xmx=40G -Djvm-xss=256m xiangshan.runMain top.TopMain \
      --target-dir "$target_dir" --config "$CONFIG" --issue E.b --num-cores 1 \
      --target systemverilog \
      --firtool-opt "-O=release --disable-annotation-unknown --lowering-options=explicitBitcast,disallowLocalVariables,disallowPortDeclSharing,locationInfoStyle=none" \
      --split-verilog --dump-fir --fpga-platform --reset-gen \
      --firtool-opt --ignore-read-enable-mem \
      --firtool-opt "--default-layer-specialization=disable"
  ) 2>&1 | tee "$cache_dir/generation.log"
  generation_rc=${PIPESTATUS[0]}
  set -e

  restore
  trap - EXIT INT TERM
  if [[ ! -s "$cache_rtl" ]]; then
    printf 'error: generation returned %d and did not produce %s.sv\n' "$generation_rc" "$MODULE" >&2
    exit "$generation_rc"
  fi
  python3 - "$tool_versions" "$mill_version" "$java_version" "$cache_rtl" "$espresso_desc" "$(uname -s)" "$(uname -m)" <<'PY'
import json, subprocess, sys
path, mill_version, java_version, rtl_path, espresso, host_os, host_arch = sys.argv[1:]
firtool = "unknown"
try:
    first = open(rtl_path, encoding="utf-8").readline().strip()
    if "firtool-" in first:
        firtool = first.split("firtool-", 1)[1]
except OSError:
    pass
json.dump({"java": java_version, "mill": mill_version, "firtool": firtool, "espresso": espresso, "host_os": host_os, "host_arch": host_arch}, open(path, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(path, "a", encoding="utf-8").write("\n")
PY
  printf '%s\n' "$command_text" > "$cache_dir/command.txt"
  printf '%s\n' "$generation_rc" > "$cache_dir/generation.exit-code"
fi

status=success
if [[ -f "$cache_dir/generation.exit-code" && "$(cat "$cache_dir/generation.exit-code")" != "0" ]]; then status=partial; fi
command_text=$(cat "$cache_dir/command.txt" 2>/dev/null || true)

if [[ -n "$VERSION" ]]; then
  python3 "$ROOT/tools/extract_rtl_evidence.py" \
    --rtl "$cache_rtl" --module "$MODULE" --output-dir "$evidence_dir" \
    --commit "$commit" --config "$CONFIG" --command "$invocation" \
    --tool-versions "$tool_versions" --generation-status "$status" \
    --rtl-source-label "cache://rtl/$fingerprint/$MODULE.sv" --cache-key "$fingerprint" \
    --generator-flags "$flags"
fi

printf 'RTL: %s\n' "$cache_rtl"
