#!/usr/bin/env python3
"""Validate a document against the repository's current chip DV schema."""

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
TEMPLATE_VERSION_RE = re.compile(r"^> 模板结构版本：(v\d+\.\d+\.\d+)$", re.M)
DOCUMENT_TEMPLATE_VERSION_RE = re.compile(r"\| 使用模板版本 \| (v\d+\.\d+\.\d+) \|")
ALLOWED_STYLES = {"Comb", "Seq", "Seq, Symbolic", "Assume", "Assert", "Cover"}
REQUIRED_H2 = (
    "1. 文档摘要",
    "2. 设计概览",
    "3. 功能行为",
    "4. 验证策略与 Testplan",
    "5. 形式化属性契约",
    "6. Sign-off 与开放项",
    "附录 A：I/O 定义与接口约束",
    "附录 B：参数、编码、状态与复位",
    "附录 C：范围、文档控制、证据与版本变更",
    "附录 D：CK 追溯矩阵",
    "附录 E：场景视角 Test Case",
)
PLACEHOLDER_RE = re.compile(r"\[(?:DUT 名称|vMAJOR|功能行为名称|核心功能名称|API 功能名称|覆盖场景名称|按需增加)")
META_PROSE_RE = re.compile(r"(?:本文档是|推荐阅读(?:顺序)?|完整重排版|本版本(?:进行了|重新排版))")


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


def section(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find(next_heading, start + len(heading)) if next_heading else len(text)
    return text[start : end if end >= 0 else len(text)]


def current_template_version(root: Path) -> str:
    template = root / "templates" / "chip-design-document" / "chip_design_document_template_zh.md"
    match = TEMPLATE_VERSION_RE.search(template.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"template structure version missing: {template}")
    return match.group(1)


def validate_current_structure(text: str, template_version: str, result: Validation) -> tuple[list[str], list[str], list[str]]:
    title = re.search(r"^# (.+) 模块规格与验证计划$", text, re.M)
    result.require(title is not None, "document title must be '<DUT> 模块规格与验证计划'")

    positions: list[int] = []
    for name in REQUIRED_H2:
        match = re.search(rf"^## {re.escape(name)}$", text, re.M)
        result.require(match is not None, f"missing current-schema section: {name}")
        if match:
            positions.append(match.start())
    result.require(positions == sorted(positions) and len(positions) == len(REQUIRED_H2), "current-schema sections are out of order")

    version_match = DOCUMENT_TEMPLATE_VERSION_RE.search(text)
    result.require(version_match is not None, "document-control template version missing")
    if version_match:
        result.require(version_match.group(1) == template_version, f"document uses {version_match.group(1)}, current template is {template_version}")

    main_end = text.find("\n## 附录 A：")
    main_body = text[: main_end if main_end >= 0 else len(text)]
    result.require(META_PROSE_RE.search(main_body) is None, "main body contains generation/reading meta prose")
    result.require(PLACEHOLDER_RE.search(text) is None, "unresolved template placeholder")
    result.require(text.count("```") % 2 == 0, "unbalanced Markdown fences")

    testplan = section(text, "## 4. 验证策略与 Testplan", "## 5. 形式化属性契约")
    fgs = FG_RE.findall(testplan)
    fcs = FC_ROW_RE.findall(testplan)
    ck_pairs = [(name, style.strip()) for name, style in CK_ROW_RE.findall(testplan)]
    cks = [name for name, _ in ck_pairs]
    result.require(bool(fgs), "Testplan contains no FG labels")
    result.require(bool(fcs), "Testplan contains no FC rows")
    result.require(bool(cks), "Testplan contains no CK rows")
    result.require(len(fgs) == len(set(fgs)), "duplicate FG labels")
    result.require(len(fcs) == len(set(fcs)), "duplicate FC labels")
    result.require(len(cks) == len(set(cks)), "duplicate CK labels")
    result.require(not re.search(r"^<(?:FG|FC|CK)-", text, re.M), "bare angle-bracket label may be hidden by Markdown")
    result.require(all(style in ALLOWED_STYLES for _, style in ck_pairs), "illegal CK Style")

    tree_match = re.search(r"### 4\.2 Testplan 标签树\s+```text\n(.*?)```", testplan, re.S)
    result.require(tree_match is not None, "missing Testplan label tree")
    if tree_match:
        tree_fcs = set(re.findall(r"FC-[A-Z0-9-]+", tree_match.group(1)))
        result.require(tree_fcs == set(fcs), f"FC tree/table mismatch: tree-only={sorted(tree_fcs-set(fcs))}, table-only={sorted(set(fcs)-tree_fcs)}")

    fc_headings = set(re.findall(r"^#### .*?(FC-[A-Z0-9-]+).*$", testplan, re.M))
    result.require(fc_headings == set(fcs), f"FC heading/table mismatch: heading-only={sorted(fc_headings-set(fcs))}, table-only={sorted(set(fcs)-fc_headings)}")
    for heading in re.finditer(r"^#### .*?(FC-[A-Z0-9-]+).*$", testplan, re.M):
        next_heading = re.search(r"^#### ", testplan[heading.end() :], re.M)
        end = heading.end() + next_heading.start() if next_heading else len(testplan)
        block = testplan[heading.end() : end]
        prose = block[: block.find("\n|") if "\n|" in block else len(block)]
        result.require(bool(re.search(r"[^\s|`#*\-]", prose)), f"missing prose after FC heading: {heading.group(1)}")

    for fg, next_fg in zip(fgs, fgs[1:] + [None]):
        scope = section(testplan, f"`<{fg}>`", f"`<{next_fg}>`" if next_fg else None)
        styles = [style.strip() for _, style in CK_ROW_RE.findall(scope)]
        if fg == "FG-API":
            result.require(all(style == "Assume" for style in styles), "FG-API contains non-Assume CK")
        if fg == "FG-COVERAGE":
            result.require(all(style == "Cover" for style in styles), "FG-COVERAGE contains non-Cover CK")

    traceability = section(text, "## 附录 D：CK 追溯矩阵", "## 附录 E：场景视角 Test Case")
    traced_cks = set(re.findall(r"^\| (?:`<)?(CK-[A-Z0-9-]+)(?:>`)? \|", traceability, re.M))
    result.require(traced_cks == set(cks), f"CK traceability mismatch: trace-only={sorted(traced_cks-set(cks))}, Testplan-only={sorted(set(cks)-traced_cks)}")
    return fgs, fcs, cks


def validate_links(files: list[Path], result: Validation) -> None:
    for source in files:
        text = source.read_text(encoding="utf-8")
        prose = re.sub(r"^```.*?^```\s*$", "", text, flags=re.M | re.S)
        for raw in LINK_RE.findall(prose):
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
        if match:
            matches.append(name)
            for marker in marker_names:
                indices[marker].add(int(match.group(marker)))
    return matches, indices


def validate_evidence(design: Path, text: str, evidence: Path, strict: bool, result: Validation) -> None:
    manifest_path = evidence / "manifest.json"
    ports_path = evidence / "ports.csv"
    diagram_manifest_path = evidence / "diagrams" / "manifest.json"
    mermaid_sources = [match.group(1).rstrip() + "\n" for match in MERMAID_RE.finditer(text)]

    if manifest_path.exists() and ports_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with ports_path.open(encoding="utf-8", newline="") as handle:
            ports = list(csv.DictReader(handle))
        port_names = {row["name"] for row in ports}
        result.require(manifest.get("port_count") == len(ports), "evidence port count mismatch")
        checked: set[str] = set()
        for line in text.splitlines():
            if any(marker in line for marker in ("未生成", "Elided", "不含", "裁剪")):
                continue
            for token in re.findall(r"`(io_[A-Za-z0-9_\[\]*]+)`", line):
                if token in checked:
                    continue
                checked.add(token)
                matches, indices = match_port_pattern(token, port_names)
                result.require(bool(matches), f"documented RTL port/pattern missing: {token}")
                for marker, values in indices.items():
                    if values:
                        result.require(values == set(range(max(values) + 1)), f"non-contiguous indices for {token} marker [{marker}]: {sorted(values)}")
    elif strict:
        result.errors.append(f"missing evidence manifest/ports: {evidence}")
    else:
        result.warnings.append(f"evidence not available: {evidence}")

    if diagram_manifest_path.exists():
        manifest = json.loads(diagram_manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("diagrams", [])
        result.require(manifest.get("document") == design.name, "Mermaid manifest document mismatch")
        result.require(len(entries) == len(mermaid_sources), "Mermaid manifest entry count mismatch")
        for index, source in enumerate(mermaid_sources):
            if index >= len(entries):
                break
            entry = entries[index]
            result.require(entry.get("source_sha256") == hashlib.sha256(source.encode()).hexdigest(), f"stale Mermaid render evidence for diagram {index + 1}")
            output = diagram_manifest_path.parent / str(entry.get("output", ""))
            result.require(output.exists(), f"missing rendered Mermaid SVG: {output}")
            if output.exists():
                data = output.read_bytes()
                svg = data.decode("utf-8", errors="replace")
                result.require(hashlib.sha256(data).hexdigest() == entry.get("svg_sha256"), f"Mermaid SVG hash mismatch: {output}")
                result.require(len(data) >= 200 and "<svg" in svg and "viewBox=" in svg, f"invalid/blank Mermaid SVG: {output}")
    elif strict and mermaid_sources:
        result.errors.append(f"missing Mermaid render evidence: {diagram_manifest_path.parent}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module")
    parser.add_argument("--version")
    parser.add_argument("--document", type=Path, help="validate a draft directly; skips versioned companion artifacts")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict-evidence", action="store_true")
    args = parser.parse_args()
    result = Validation()

    if args.document:
        design = args.document.resolve()
        report = history = evidence = None
    else:
        if not args.module or not args.version:
            parser.error("--module and --version are required unless --document is used")
        result.require(bool(VERSION_RE.fullmatch(args.version)), f"invalid version: {args.version}")
        design = args.root / "outputs" / args.module / f"{args.module}_design_document_zh_{args.version}.md"
        report = args.root / "reports" / args.module / f"{args.module}_document_quality_review_{args.version}.md"
        history = args.root / "outputs" / args.module / "VERSION_HISTORY.md"
        evidence = args.root / "evidence" / args.module / args.version
        for path in (design, report, history):
            result.require(path.exists(), f"missing artifact: {path}")

    if not design.exists() or result.errors:
        if not design.exists():
            result.errors.append(f"missing document: {design}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    text = design.read_text(encoding="utf-8")
    try:
        template_version = current_template_version(args.root)
    except ValueError as exc:
        result.errors.append(str(exc))
        template_version = ""
    fgs, fcs, cks = validate_current_structure(text, template_version, result)

    if report and history and evidence:
        report_text = report.read_text(encoding="utf-8")
        history_text = history.read_text(encoding="utf-8")
        result.require(f"> 文档版本：{args.version}" in text, "visible design version missing")
        result.require(re.search(rf"\| 文档版本 \| {re.escape(args.version)} \|", text) is not None, "document-control version missing")
        result.require(args.version in report_text, "report version missing")
        result.require(design.name in history_text and report.name in history_text, "history links do not name both artifacts")
        validate_links([design, report, history], result)
        validate_evidence(design, text, evidence, args.strict_evidence, result)
    elif args.strict_evidence:
        result.warnings.append("--strict-evidence is ignored with --document because no module/version evidence path is defined")

    cases = len(re.findall(r"^### CASE-", text, re.M))
    print(f"FG={len(fgs)} FC={len(fcs)} CK={len(cks)} cases={cases}")
    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
