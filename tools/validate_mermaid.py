#!/usr/bin/env python3
"""Render every Mermaid fence in a Markdown document with pinned mmdc."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


FENCE_RE = re.compile(r"^```mermaid\s*\n(.*?)^```\s*$", re.M | re.S)


def browser_path() -> str | None:
    configured = os.environ.get("MERMAID_BROWSER_PATH") or os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if configured and Path(configured).is_file():
        return configured
    for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        resolved = shutil.which(command)
        if resolved:
            return resolved
    if platform.system() == "Darwin":
        candidates = (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        )
        for candidate in candidates:
            if Path(candidate).is_file():
                return candidate
    return None


def diagram_type(source: str) -> str:
    first = next((line.strip() for line in source.splitlines() if line.strip()), "unknown")
    return first.split()[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mmdc", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    text = args.document.read_text(encoding="utf-8")
    diagrams = [match.group(1).rstrip() + "\n" for match in FENCE_RE.finditer(text)]
    if not diagrams:
        print("error: no Mermaid diagrams found", file=sys.stderr)
        return 1

    mmdc = args.mmdc
    node_result = subprocess.run([str(args.root / "tools/bootstrap_node.sh")], text=True, capture_output=True)
    if node_result.returncode:
        print(node_result.stderr, file=sys.stderr)
        return node_result.returncode
    node_home = Path(node_result.stdout.strip().splitlines()[-1])
    command_env = os.environ.copy()
    command_env["PATH"] = f"{node_home / 'bin'}{os.pathsep}{command_env.get('PATH', '')}"
    if not mmdc:
        result = subprocess.run([str(args.root / "tools/bootstrap_mermaid.sh")], text=True, capture_output=True)
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            return result.returncode
        mmdc = Path(result.stdout.strip().splitlines()[-1])
    browser = browser_path()
    if not browser:
        result = subprocess.run([str(args.root / "tools/bootstrap_mermaid_browser.sh")], text=True, capture_output=True)
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            return result.returncode
        browser = result.stdout.strip().splitlines()[-1]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.output_dir.glob("diagram-*.svg"):
        stale.unlink()
    manifest_entries: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mermaid-") as temp_name:
        temp = Path(temp_name)
        config = temp / "puppeteer.json"
        config.write_text(json.dumps({"executablePath": browser, "headless": True, "args": ["--no-sandbox"]}), encoding="utf-8")
        for index, source in enumerate(diagrams, start=1):
            kind = diagram_type(source)
            input_path = temp / f"diagram-{index:02d}.mmd"
            output_name = f"diagram-{index:02d}-{kind}.svg"
            output_path = args.output_dir / output_name
            input_path.write_text(source, encoding="utf-8")
            command = [str(mmdc), "--input", str(input_path), "--output", str(output_path), "--puppeteerConfigFile", str(config), "--backgroundColor", "transparent", "--quiet"]
            result = subprocess.run(command, text=True, capture_output=True, env=command_env)
            if result.returncode:
                print(f"error: Mermaid diagram {index} ({kind}) failed", file=sys.stderr)
                print(result.stderr or result.stdout, file=sys.stderr)
                return result.returncode
            data = output_path.read_bytes()
            svg = data.decode("utf-8", errors="replace")
            if len(data) < 200 or "<svg" not in svg or "viewBox=" not in svg or not re.search(r"<(?:path|rect|g|text)\b", svg):
                print(f"error: Mermaid diagram {index} rendered an invalid/blank SVG", file=sys.stderr)
                return 1
            manifest_entries.append(
                {
                    "index": index,
                    "type": kind,
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "output": output_name,
                    "svg_sha256": hashlib.sha256(data).hexdigest(),
                    "svg_bytes": len(data),
                }
            )

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document": args.document.name,
        "renderer": f"@mermaid-js/mermaid-cli/{os.environ.get('MERMAID_CLI_VERSION', '11.16.0')}",
        "browser": Path(browser).name,
        "diagram_count": len(manifest_entries),
        "diagrams": manifest_entries,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rendered {len(manifest_entries)} Mermaid diagram(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
