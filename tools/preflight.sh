#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
XS_ROOT=${XIANGSHAN_ROOT:-"$ROOT/third_party/XiangShan"}
CONFIG=DefaultConfig
MODULE=
STRICT=0
DOCUMENT_TOOLS=0

usage() {
  cat <<'EOF'
Usage: tools/preflight.sh [--module NAME] [--config CONFIG] [--strict] [--document-tools]

Checks the cross-platform environment before XiangShan evidence generation.
--strict also requires a clean XiangShan worktree and initialized nested submodules.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --module) MODULE=${2:?missing module}; shift 2 ;;
    --config) CONFIG=${2:?missing config}; shift 2 ;;
    --strict) STRICT=1; shift ;;
    --document-tools) DOCUMENT_TOOLS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'error: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

errors=0
warnings=0
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; warnings=$((warnings + 1)); }
fail() { printf '[FAIL] %s\n' "$*" >&2; errors=$((errors + 1)); }

printf 'Platform: %s/%s\n' "$(uname -s)" "$(uname -m)"

for tool in git curl python3 make; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool: $(command -v "$tool")"; else fail "$tool is not installed"; fi
done

if [[ -d "$XS_ROOT/.git" || -f "$XS_ROOT/.git" ]]; then
  commit=$(git -C "$XS_ROOT" rev-parse HEAD 2>/dev/null || true)
  [[ -n "$commit" ]] && ok "XiangShan commit: $commit" || fail "cannot resolve XiangShan commit"
else
  fail "XiangShan submodule is not initialized; run git submodule update --init --recursive"
fi

if [[ -f "$XS_ROOT/src/main/scala/top/Configs.scala" ]] && grep -q "class $CONFIG" "$XS_ROOT/src/main/scala/top/Configs.scala"; then
  ok "configuration exists: $CONFIG"
else
  fail "configuration class not found: $CONFIG"
fi

if [[ -n "$MODULE" ]]; then
  if grep -R -q --include='*.scala' "class $MODULE" "$XS_ROOT/src/main/scala"; then
    ok "Chisel class found: $MODULE"
  else
    fail "Chisel class not found under src/main/scala: $MODULE"
  fi
fi

if java_home=$("$ROOT/tools/bootstrap_jdk.sh" 2>/dev/null); then
  java_version=$("$java_home/bin/java" -version 2>&1 | head -n 1)
  ok "Java: $java_version ($java_home)"
else
  fail "Java 17 is unavailable and automatic bootstrap failed"
fi

if [[ -f "$XS_ROOT/.mill-version" ]]; then
  ok "Mill version pin: $(tr -d '[:space:]' < "$XS_ROOT/.mill-version")"
else
  fail "missing XiangShan .mill-version"
fi

if espresso=$("$ROOT/tools/prepare_espresso.sh" 2>/dev/null); then
  ok "Espresso runtime: $espresso"
else
  fail "no executable Espresso for this platform; install a C compiler and make"
fi

if [[ $DOCUMENT_TOOLS -eq 1 ]]; then
  if node_home=$("$ROOT/tools/bootstrap_node.sh" 2>/dev/null); then
    ok "Node.js: $("$node_home/bin/node" --version) ($node_home)"
  else
    fail "pinned Node.js bootstrap failed"
  fi
  if mmdc=$("$ROOT/tools/bootstrap_mermaid.sh" 2>/dev/null); then
    ok "Mermaid CLI: $mmdc"
  else
    fail "Mermaid CLI bootstrap failed"
  fi
  if browser=$("$ROOT/tools/bootstrap_mermaid_browser.sh" 2>/dev/null); then
    ok "Mermaid browser: $browser"
  else
    fail "no Mermaid browser available and browser bootstrap failed"
  fi
fi

if [[ -n "$(git -C "$XS_ROOT" status --short 2>/dev/null || true)" ]]; then
  if [[ $STRICT -eq 1 ]]; then fail "XiangShan worktree is dirty"; else warn "XiangShan worktree is dirty"; fi
else
  ok "XiangShan worktree is clean"
fi

uninitialized=$(git -C "$XS_ROOT" submodule status --recursive 2>/dev/null | awk '/^-/ {count++} END {print count+0}')
if [[ "$uninitialized" -eq 0 ]]; then
  ok "nested submodules initialized"
elif [[ $STRICT -eq 1 ]]; then
  fail "$uninitialized nested submodules are uninitialized"
else
  warn "$uninitialized nested submodules are uninitialized"
fi

free_kb=
case "$(uname -s)" in
  Linux) free_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}') ;;
  Darwin) free_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}') ;;
esac
if [[ -n "$free_kb" && "$free_kb" -lt 10485760 ]]; then
  warn "less than 10 GiB free disk space"
else
  ok "disk space check passed"
fi

printf 'Summary: %d error(s), %d warning(s)\n' "$errors" "$warnings"
[[ $errors -eq 0 ]]
