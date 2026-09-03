#!/usr/bin/env python3
"""Synchronize generated-document metadata from the matching evidence manifest."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


def replace_row(text: str, label: str, value: str) -> str:
    pattern = rf"^(\| {re.escape(label)} \| ).*?( \|)$"
    updated, count = re.subn(pattern, rf"\g<1>{value}\g<2>", text, count=1, flags=re.M)
    if count != 1:
        raise ValueError(f"metadata row not found exactly once: {label}")
    return updated


def replace_first_value(text: str, label: str, value: str) -> str:
    pattern = rf"^(\| {re.escape(label)} \| `)[^`]*(`.*\|)$"
    updated, count = re.subn(pattern, rf"\g<1>{value}\g<2>", text, count=1, flags=re.M)
    if count != 1:
        raise ValueError(f"metadata value not found exactly once: {label}")
    return updated


def replace_status_prefix(text: str, label: str, status: str) -> str:
    pattern = rf"^(\| {re.escape(label)} \| )(Success|success|Partial|partial|Failed|failed)(.*\|)$"
    updated, count = re.subn(pattern, rf"\g<1>{status}\g<3>", text, count=1, flags=re.M)
    if count != 1:
        raise ValueError(f"status row not found exactly once: {label}")
    return updated


def update_report_template_row(match: re.Match[str], template_version: str) -> str:
    current = match.group(2)
    value = re.sub(r"结构版本 v\d+\.\d+\.\d+", f"结构版本 {template_version}", current) if "结构版本 v" in current else template_version
    return f"{match.group(1)}{value}{match.group(3)}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--update-history", action="store_true")
    parser.add_argument("--change-type", choices=("Major", "Minor", "Patch"))
    parser.add_argument("--summary")
    args = parser.parse_args()

    design = args.root / "outputs" / args.module / f"{args.module}_design_document_zh_{args.version}.md"
    report = args.root / "reports" / args.module / f"{args.module}_document_quality_review_{args.version}.md"
    history = args.root / "outputs" / args.module / "VERSION_HISTORY.md"
    manifest_path = args.root / "evidence" / args.module / args.version / "manifest.json"
    diagram_manifest_path = args.root / "evidence" / args.module / args.version / "diagrams" / "manifest.json"
    template = args.root / "templates" / "chip-design-document" / "chip_design_document_template_zh.md"

    for path in (design, report, manifest_path, template):
        if not path.exists():
            raise SystemExit(f"missing metadata input: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    template_text = template.read_text(encoding="utf-8")
    template_match = re.search(r"> 模板结构版本：([^\s]+)", template_text)
    if not template_match:
        raise SystemExit("template version not found")
    template_version = template_match.group(1)

    port_counts = manifest.get("port_counts", {})
    port_summary = f"{manifest.get('port_count', 0)} 个叶端口：{port_counts.get('input', 0)} input、{port_counts.get('output', 0)} output"
    design_text = design.read_text(encoding="utf-8")
    design_text = replace_row(design_text, "使用模板版本", template_version)
    design_text = replace_first_value(design_text, "XiangShan RTL 基线", manifest["xiangshan_commit"])
    design_text = replace_first_value(design_text, "适用配置", manifest["config"])
    status = str(manifest.get("generation_status", "unknown"))
    design_text = replace_status_prefix(design_text, "RTL 生成状态", status.capitalize())
    design_text = re.sub(r"SHA-256 `[^`]+`", f"SHA-256 `{manifest.get('rtl_sha256', 'OPEN-RTL-HASH')}`", design_text, count=1)
    design_text = re.sub(r"\d+ 个叶端口：\d+ input、\d+ output", port_summary, design_text, count=1)
    if diagram_manifest_path.exists():
        diagrams = json.loads(diagram_manifest_path.read_text(encoding="utf-8"))
        renderer = str(diagrams.get("renderer", "unknown"))
        renderer_label = f"Mermaid CLI {renderer.rsplit('/', 1)[-1]}"
        design_text = re.sub(r"；(?:@mermaid-js/mermaid-cli/|Mermaid CLI )[^；]+；\d+ 张图", f"；{renderer_label}；{diagrams.get('diagram_count', 0)} 张图", design_text, count=1)
    design_text = replace_row(design_text, "生成日期", args.date)
    design.write_text(design_text, encoding="utf-8")

    if report.exists():
        report_text = report.read_text(encoding="utf-8")
        report_text = re.sub(r"^(\| 使用模板(?:版本)? \| )(.*?)( \|)$", lambda match: update_report_template_row(match, template_version), report_text, count=1, flags=re.M)
        report_text = re.sub(r"^(\| XiangShan commit \| `)[^`]*(`.*\|)$", rf"\g<1>{manifest['xiangshan_commit']}\g<2>", report_text, count=1, flags=re.M)
        report_text = re.sub(r"^\| 日期 \| .*? \|$", f"| 日期 | {args.date} |", report_text, count=1, flags=re.M)
        report.write_text(report_text, encoding="utf-8")

    if args.update_history and history.exists():
        history_text = history.read_text(encoding="utf-8")
        if f"| {args.version} |" not in history_text:
            if not args.change_type or not args.summary:
                raise SystemExit("--change-type and --summary are required when adding a history row")
            row = f"| {args.version} | {args.date} | `{manifest['xiangshan_commit']}` | `{manifest['config']}` | {args.change_type} | {args.summary} | [设计文档](./{design.name}) | [质量报告](../../reports/{args.module}/{report.name}) |"
            marker = "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            if marker not in history_text:
                raise SystemExit("history table header not found")
            history_text = history_text.replace(marker, marker + row + "\n", 1)
        history.write_text(history_text, encoding="utf-8")

    print(f"updated metadata: {design.relative_to(args.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
