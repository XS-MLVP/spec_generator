#!/usr/bin/env python3
"""Validate versioned XiangShan design-document artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path


VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")
FG_RE = re.compile(r"^`<(FG-[A-Z0-9-]+)>`$", re.M)
FC_ROW_RE = re.compile(r"^\| `<(FC-[A-Z0-9-]+)>` \|", re.M)
CK_ROW_RE = re.compile(r"^\| `<(CK-[A-Z0-9-]+)>` \| ([^|]+) \|", re.M)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MERMAID_RE = re.compile(r"^```mermaid\s*\n(.*?)^```\s*$", re.M | re.S)
ALLOWED_STYLES = {"Comb", "Seq", "Seq, Symbolic", "Assume", "Cover"}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


def table_scope(text: str, fg: str, next_fg: str | None) -> str:
    start = text.find(f"`<{fg}>`")
    if start < 0:
        return ""
    if next_fg:
        end = text.find(f"`<{next_fg}>`", start + 1)
        return text[start : end if end >= 0 else None]
    end = text.find("\n## 检测点追溯", start)
    return text[start : end if end >= 0 else None]


def validate_links(files: list[Path], result: Validation) -> None:
    for source in files:
        text = source.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            if raw.startswith(("http://", "https://", "#")):
                continue
            target_text, _, fragment = raw.partition("#")
            target = (source.parent / target_text).resolve()
            result.require(target.exists(), f"broken link: {source} -> {raw}")
            if target.exists() and fragment.startswith("L") and fragment[1:].isdigit() and target.is_file():
                line_count = sum(1 for _ in target.open(encoding="utf-8", errors="replace"))
                result.require(int(fragment[1:]) <= line_count, f"line reference out of range: {source} -> {raw}")


def match_port_pattern(pattern: str, port_names: set[str]) -> tuple[list[str], dict[str, set[int]]]:
    marker_names = re.findall(r"\[([A-Za-z][A-Za-z0-9_]*)\]", pattern)
    regex = re.escape(pattern)
    for marker in marker_names:
        regex = regex.replace(re.escape(f"[{marker}]"), rf"(?P<{marker}>\d+)")
    regex = regex.replace(r"\*", ".*")
    compiled = re.compile(rf"^{regex}$")
    matches: list[str] = []
    indices: dict[str, set[int]] = {marker: set() for marker in marker_names}
    for name in port_names:
        match = compiled.fullmatch(name)
        if not match:
            continue
        matches.append(name)
        for marker in marker_names:
            indices[marker].add(int(match.group(marker)))
    return matches, indices


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict-evidence", action="store_true")
    args = parser.parse_args()

    result = Validation()
    result.require(bool(VERSION_RE.fullmatch(args.version)), f"invalid version: {args.version}")

    design = args.root / "outputs" / args.module / f"{args.module}_design_document_zh_{args.version}.md"
    report = args.root / "reports" / args.module / f"{args.module}_document_quality_review_{args.version}.md"
    history = args.root / "outputs" / args.module / "VERSION_HISTORY.md"
    evidence = args.root / "evidence" / args.module / args.version
    manifest_path = evidence / "manifest.json"
    ports_path = evidence / "ports.csv"
    diagram_manifest_path = evidence / "diagrams" / "manifest.json"

    for path in (design, report, history):
        result.require(path.exists(), f"missing artifact: {path}")
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    text = design.read_text(encoding="utf-8")
    report_text = report.read_text(encoding="utf-8")
    history_text = history.read_text(encoding="utf-8")

    result.require(f"> 文档版本：{args.version}" in text, "visible design version missing")
    result.require(re.search(rf"\| 文档版本 \| {re.escape(args.version)} \|", text) is not None, "document-control version missing")
    result.require(args.version in report_text, "report version missing")
    result.require(design.name in history_text and report.name in history_text, "history links do not name both artifacts")

    existing_versions = []
    for path in design.parent.glob(f"{args.module}_design_document_zh_v*.md"):
        match = re.search(r"_(v\d+\.\d+\.\d+)\.md$", path.name)
        if match:
            existing_versions.append(match.group(1))
    result.require(len(existing_versions) == len(set(existing_versions)), "duplicate versioned design files")

    fgs = FG_RE.findall(text)
    fcs = FC_ROW_RE.findall(text)
    ck_pairs = [(name, style.strip()) for name, style in CK_ROW_RE.findall(text)]
    cks = [name for name, _ in ck_pairs]
    result.require(len(fgs) == len(set(fgs)), "duplicate FG labels")
    result.require(len(fcs) == len(set(fcs)), "duplicate FC labels")
    result.require(len(cks) == len(set(cks)), "duplicate CK labels")
    result.require(not re.search(r"^<(?:FG|FC|CK)-", text, re.M), "bare angle-bracket label may be hidden by Markdown")
    result.require(all(style in ALLOWED_STYLES for _, style in ck_pairs), "illegal CK Style")

    tree_match = re.search(r"### 本 DUT 标签树\s+```text\n(.*?)```", text, re.S)
    result.require(tree_match is not None, "missing label tree")
    if tree_match:
        tree_fcs = set(re.findall(r"FC-[A-Z0-9-]+", tree_match.group(1)))
        result.require(tree_fcs == set(fcs), f"FC tree/table mismatch: tree-only={sorted(tree_fcs-set(fcs))}, table-only={sorted(set(fcs)-tree_fcs)}")

    for index, fg in enumerate(fgs):
        scope = table_scope(text, fg, fgs[index + 1] if index + 1 < len(fgs) else None)
        styles = [style.strip() for _, style in CK_ROW_RE.findall(scope)]
        if fg == "FG-API":
            result.require(all(style == "Assume" for style in styles), "FG-API contains non-Assume CK")
        if fg == "FG-COVERAGE":
            result.require(all(style == "Cover" for style in styles), "FG-COVERAGE contains non-Cover CK")

    headings = list(re.finditer(r"^#### .+$", text, re.M))
    result.require(len(headings) == len(fcs), f"FC natural-language heading count {len(headings)} != FC count {len(fcs)}")
    for idx, heading in enumerate(headings):
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        block = text[heading.end() : end]
        first_table = block.find("\n|")
        prose = block[:first_table] if first_table >= 0 else block
        result.require(bool(re.search(r"[^\s|`#*-]", prose)), f"missing prose after heading: {heading.group(0)}")

    result.require(text.count("```") % 2 == 0, "unbalanced Markdown fences")
    result.require('subgraph DUT["DUT: ' in text, "architecture DUT subgraph missing")
    result.require(len(re.findall(r"^### CASE-", text, re.M)) >= 3, "fewer than three scenario cases")
    mermaid_sources = [match.group(1).rstrip() + "\n" for match in MERMAID_RE.finditer(text)]

    validate_links([design, report, history], result)

    if manifest_path.exists() and ports_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with ports_path.open(encoding="utf-8", newline="") as handle:
            ports = list(csv.DictReader(handle))
        port_names = {row["name"] for row in ports}
        result.require(manifest.get("module") == args.module, "evidence module mismatch")
        result.require(manifest.get("port_count") == len(ports), "evidence port count mismatch")
        commit = manifest.get("xiangshan_commit", "")
        result.require(commit in text and commit in report_text and commit in history_text, "evidence commit not consistent across artifacts")
        claimed = re.search(r"(\d+) 个叶端口：?(\d+)?", text)
        if claimed:
            result.require(int(claimed.group(1)) == len(ports), "document port count does not match manifest")
        checked_tokens: set[str] = set()
        for line in text.splitlines():
            if any(marker in line for marker in ("未生成", "Elided", "不含", "裁剪")):
                continue
            for token in re.findall(r"`(io_[A-Za-z0-9_\[\]*]+)`", line):
                if token in checked_tokens:
                    continue
                checked_tokens.add(token)
                matches, indices = match_port_pattern(token, port_names)
                result.require(bool(matches), f"documented RTL port/pattern missing: {token}")
                for marker, values in indices.items():
                    if values:
                        result.require(values == set(range(max(values) + 1)), f"non-contiguous indices for {token} marker [{marker}]: {sorted(values)}")
    elif args.strict_evidence:
        result.errors.append(f"missing evidence manifest/ports: {evidence}")
    else:
        result.warnings.append(f"evidence not available: {evidence}")

    template_match = re.search(r"\| 使用模板版本 \| v(\d+)\.", text)
    requires_render_evidence = bool(template_match and int(template_match.group(1)) >= 2)
    if diagram_manifest_path.exists():
        diagram_manifest = json.loads(diagram_manifest_path.read_text(encoding="utf-8"))
        entries = diagram_manifest.get("diagrams", [])
        result.require(diagram_manifest.get("document") == design.name, "Mermaid manifest document mismatch")
        result.require(diagram_manifest.get("diagram_count") == len(mermaid_sources), "Mermaid diagram count mismatch")
        result.require(len(entries) == len(mermaid_sources), "Mermaid manifest entry count mismatch")
        for index, source in enumerate(mermaid_sources):
            if index >= len(entries):
                break
            entry = entries[index]
            expected_source_hash = hashlib.sha256(source.encode()).hexdigest()
            result.require(entry.get("source_sha256") == expected_source_hash, f"stale Mermaid render evidence for diagram {index + 1}")
            output = diagram_manifest_path.parent / str(entry.get("output", ""))
            result.require(output.exists(), f"missing rendered Mermaid SVG: {output}")
            if output.exists():
                data = output.read_bytes()
                svg = data.decode("utf-8", errors="replace")
                result.require(hashlib.sha256(data).hexdigest() == entry.get("svg_sha256"), f"Mermaid SVG hash mismatch: {output}")
                result.require(len(data) >= 200 and "<svg" in svg and "viewBox=" in svg, f"invalid/blank Mermaid SVG: {output}")
    elif args.strict_evidence and requires_render_evidence:
        result.errors.append(f"missing Mermaid render evidence: {diagram_manifest_path.parent}")

    print(f"FG={len(fgs)} FC={len(fcs)} CK={len(cks)} cases={len(re.findall(r'^### CASE-', text, re.M))}")
    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
