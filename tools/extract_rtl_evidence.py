#!/usr/bin/env python3
"""Extract an ANSI SystemVerilog module port manifest using only stdlib."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PORT_RE = re.compile(
    r"^\s*(input|output|inout)\s+(?:wire\s+|logic\s+|reg\s+)?"
    r"(?:\[\s*([^\]]+)\s*\]\s+)?([A-Za-z_][A-Za-z0-9_$]*)\s*,?\s*$"
)


def width_from_range(bit_range: str | None) -> int | None:
    if bit_range is None:
        return 1
    match = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", bit_range)
    if not match:
        return None
    return abs(int(match.group(1)) - int(match.group(2))) + 1


def parse_ports(text: str, module: str) -> list[dict[str, object]]:
    match = re.search(rf"\bmodule\s+{re.escape(module)}\s*\((.*?)\n\s*\);", text, re.S)
    if not match:
        raise ValueError(f"module header not found: {module}")
    ports: list[dict[str, object]] = []
    for line_number, line in enumerate(match.group(1).splitlines(), start=1):
        port_match = PORT_RE.match(line)
        if not port_match:
            if line.strip():
                raise ValueError(f"unsupported port declaration in {module}: {line.strip()}")
            continue
        direction, bit_range, name = port_match.groups()
        ports.append(
            {
                "index": len(ports),
                "direction": direction,
                "name": name,
                "range": bit_range or "",
                "width": width_from_range(bit_range),
            }
        )
    return ports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl", required=True, type=Path)
    parser.add_argument("--module", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--command", default="")
    parser.add_argument("--tool-versions", type=Path)
    parser.add_argument("--generation-status", default="success")
    parser.add_argument("--rtl-source-label", default="")
    parser.add_argument("--cache-key", default="")
    parser.add_argument("--generator-flags", default="")
    args = parser.parse_args()

    data = args.rtl.read_bytes()
    text = data.decode("utf-8")
    ports = parse_ports(text, args.module)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with (args.output_dir / "ports.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["index", "direction", "name", "range", "width"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(ports)

    tools: dict[str, str] = {}
    if args.tool_versions and args.tool_versions.exists():
        tools = json.loads(args.tool_versions.read_text(encoding="utf-8"))

    counts = {direction: sum(p["direction"] == direction for p in ports) for direction in ("input", "output", "inout")}
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": args.module,
        "xiangshan_commit": args.commit,
        "config": args.config,
        "generation_status": args.generation_status,
        "command": args.command,
        "generator_flags": args.generator_flags,
        "rtl_source": args.rtl_source_label or args.rtl.name,
        "cache_key": args.cache_key,
        "rtl_sha256": hashlib.sha256(data).hexdigest(),
        "port_count": len(ports),
        "port_counts": counts,
        "tool_versions": tools,
        "ports_file": "ports.csv",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"module": args.module, "ports": len(ports), "sha256": manifest["rtl_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
