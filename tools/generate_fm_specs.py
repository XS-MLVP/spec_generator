#!/usr/bin/env python3
"""Run the pinned FM-Agent Verilog flow for one rtls/<Module> directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HDL_SUFFIXES = {".v", ".sv", ".svh"}
MANIFEST_NAME = "spec_generator_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_hashes(paths: list[Path], base: Path) -> dict[str, str]:
    return {path.relative_to(base).as_posix(): sha256(path) for path in sorted(paths)}


def source_files(rtl_dir: Path) -> list[Path]:
    return [
        path
        for path in rtl_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in HDL_SUFFIXES
        and "fm_agent" not in path.relative_to(rtl_dir).parts
    ]


def output_files(rtl_dir: Path) -> list[Path]:
    extracted = rtl_dir / "fm_agent" / "extracted_functions"
    if not extracted.is_dir():
        return []
    return sorted(
        path
        for path in extracted.rglob("*.md")
        if path.name.endswith(("_spec.md", "_info.md")) and path.stat().st_size > 0
    )


def sync_inputs(module: str, rtl_dir: Path) -> Path:
    """Copy FM-Agent's spec/info artifacts into the normal Skill input tree."""
    destination = ROOT / "inputs" / module / "fm_agent"
    destination.mkdir(parents=True, exist_ok=True)
    for source in output_files(rtl_dir):
        relative = source.relative_to(rtl_dir / "fm_agent" / "extracted_functions")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def fm_commit(fm_root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(fm_root), "rev-parse", "HEAD"], text=True
    ).strip()


def build_manifest(module: str, rtl_dir: Path, fm_root: Path, command: list[str]) -> dict[str, object]:
    sources = source_files(rtl_dir)
    outputs = output_files(rtl_dir)
    return {
        "schema_version": 1,
        "module": module,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fm_agent_commit": fm_commit(fm_root),
        "rtl_root": f"rtls/{module}",
        "command": shlex.join(command),
        "source_count": len(sources),
        "source_sha256": relative_hashes(sources, rtl_dir),
        "spec_count": sum(path.name.endswith("_spec.md") for path in outputs),
        "info_count": sum(path.name.endswith("_info.md") for path in outputs),
        "output_sha256": relative_hashes(outputs, rtl_dir),
    }


def check_manifest(module: str, rtl_dir: Path, fm_root: Path) -> list[str]:
    manifest_path = rtl_dir / "fm_agent" / MANIFEST_NAME
    if not manifest_path.is_file():
        return [f"missing FM-Agent manifest: {manifest_path}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid FM-Agent manifest: {exc}"]

    errors: list[str] = []
    if manifest.get("module") != module:
        errors.append("FM-Agent manifest module mismatch")
    if manifest.get("fm_agent_commit") != fm_commit(fm_root):
        errors.append("FM-Agent commit changed; regenerate module specs")
    current_sources = relative_hashes(source_files(rtl_dir), rtl_dir)
    if manifest.get("source_sha256") != current_sources:
        errors.append("RTL source set or content changed; regenerate module specs")
    current_outputs = relative_hashes(output_files(rtl_dir), rtl_dir)
    if not current_outputs:
        errors.append("FM-Agent produced no nonempty *_spec.md/_info.md outputs")
    elif manifest.get("output_sha256") != current_outputs:
        errors.append("FM-Agent output set or content differs from manifest")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True, help="directory name under rtls/")
    parser.add_argument("--fm-root", type=Path, default=ROOT / "third_party" / "FM-Agent")
    parser.add_argument("--fresh", action="store_true", help="discard only this module's FM-Agent workspace and regenerate")
    parser.add_argument("--check", action="store_true", help="validate existing outputs without invoking FM-Agent")
    parser.add_argument("--dry-run", action="store_true", help="print the resolved FM-Agent command without running it")
    args = parser.parse_args()

    if not args.module or args.module in {".", ".."} or "/" in args.module or "\\" in args.module:
        parser.error("--module must be one directory name under rtls/")

    rtl_dir = (ROOT / "rtls" / args.module).resolve()
    fm_root = args.fm_root.resolve()
    main_py = fm_root / "main.py"
    if not rtl_dir.is_dir():
        print(f"error: RTL directory does not exist: {rtl_dir}", file=sys.stderr)
        return 1
    sources = source_files(rtl_dir)
    if not sources:
        print(f"error: no Verilog/SystemVerilog files under {rtl_dir}", file=sys.stderr)
        return 1
    if not main_py.is_file() or not (fm_root / "pyproject.toml").is_file():
        print("error: FM-Agent submodule is not initialized; run make init", file=sys.stderr)
        return 1
    if "--verilog" not in main_py.read_text(encoding="utf-8", errors="replace"):
        print("error: pinned FM-Agent does not provide the --hardware --verilog flow", file=sys.stderr)
        return 1

    if args.check:
        errors = check_manifest(args.module, rtl_dir, fm_root)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            manifest = rtl_dir / "fm_agent" / MANIFEST_NAME
            print(f"FM-Agent inputs are current: {manifest}")
        return 1 if errors else 0

    required_tools = ("uv", "opencode", "verible-verilog-syntax")
    missing = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing:
        print(f"error: missing FM-Agent tool(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    command = ["uv", "run", "python", "main.py", str(rtl_dir), "--hardware", "--verilog"]
    workspace = rtl_dir / "fm_agent"
    if workspace.is_dir() and not args.fresh:
        command.append("--resume")
    if args.dry_run:
        print(f"cwd: {fm_root}")
        print(shlex.join(command))
        return 0

    env = os.environ.copy()
    subprocess.run(command, cwd=fm_root, env=env, check=True)
    outputs = output_files(rtl_dir)
    if not outputs:
        print(f"error: FM-Agent completed without usable specs under {workspace}", file=sys.stderr)
        return 1

    manifest = build_manifest(args.module, rtl_dir, fm_root, command)
    manifest_path = workspace / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    input_dir = sync_inputs(args.module, rtl_dir)
    print(
        f"FM-Agent specs: {manifest['spec_count']} spec, {manifest['info_count']} info; "
        f"inputs: {input_dir}; manifest: {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
