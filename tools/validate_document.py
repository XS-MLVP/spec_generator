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
P_DEF_ROW_RE = re.compile(r"^\| `(P-[A-Z0-9-]+)` \|", re.M)
P_DEF_HEADING_RE = re.compile(r"^#### `(P-[A-Z0-9-]+)`[：:]", re.M)
P_REF_RE = re.compile(r"`(P-[A-Z0-9-]+)`")
E_DEF_ROW_RE = re.compile(r"^\| (E-[A-Z0-9-]+) \|", re.M)
E_REF_RE = re.compile(r"\[(E-[A-Z0-9-]+)\]")
FC_DETAIL_RE = re.compile(r"^\| `<(FC-[A-Z0-9-]+)>` \| `(FG-[A-Z0-9-]+)` \|", re.M)
CK_DETAIL_RE = re.compile(r"^\| `<(CK-[A-Z0-9-]+)>` \| ([^|]+) \| `(FC-[A-Z0-9-]+)` \|", re.M)
TEST_PLAN_ROW_RE = re.compile(r"^\| P[0-2] \| `(FC-[A-Z0-9-]+)` \| `(CK-[A-Z0-9-]+)` \| ([^|]+) \|", re.M)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MERMAID_RE = re.compile(r"^```mermaid\s*\n(.*?)^```\s*$", re.M | re.S)
CASE_RE = re.compile(r"^#{3,4} CASE-", re.M)
COV_DEF_ROW_RE = re.compile(r"^\| `(COV-[A-Z0-9-]+)` \|", re.M)
COV_REF_RE = re.compile(r"`(COV-[A-Z0-9-]+)`")
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
    start_match = re.search(rf"^`<{re.escape(fg)}>`$", text, re.M)
    if not start_match:
        return ""
    start = start_match.start()
    if next_fg:
        end_match = re.search(rf"^`<{re.escape(next_fg)}>`$", text[start + 1 :], re.M)
        end = start + 1 + end_match.start() if end_match else -1
        return text[start : end if end >= 0 else None]
    end_match = re.search(r"^### Coverage 汇总\s*$|^## 第三部分：附录\s*$|^#{2,3} .*检测点追溯", text[start:], re.M)
    return text[start : start + end_match.start() if end_match else None]


def prose_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    in_comment = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if "<!--" in line:
            in_comment = True
        if in_fence or in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if not line or line.startswith(("|", "#")):
            continue
        lines.append(line)
    return lines


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

    template_match = re.search(r"\| 使用模板版本 \| v(\d+)\.(\d+)\.(\d+) \|", text)
    template_version = tuple(map(int, template_match.groups())) if template_match else (0, 0)
    template_major = template_version[0]
    current_template = args.root / "templates" / "chip-design-document" / "chip_design_document_template_zh.md"
    current_template_match = re.search(r"> 模板结构版本：v(\d+)\.(\d+)\.(\d+)", current_template.read_text(encoding="utf-8")) if current_template.exists() else None
    current_template_version = tuple(map(int, current_template_match.groups())) if current_template_match else None

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

    tree_match = re.search(r"#{3,4} 本 DUT 标签树\s+```text\n(.*?)```", text, re.S)
    result.require(tree_match is not None, "missing label tree")
    if tree_match:
        tree_fcs = set(re.findall(r"FC-[A-Z0-9-]+", tree_match.group(1)))
        result.require(tree_fcs == set(fcs), f"FC tree/table mismatch: tree-only={sorted(tree_fcs-set(fcs))}, table-only={sorted(set(fcs)-tree_fcs)}")

    if template_version < (3, 1):
        for index, fg in enumerate(fgs):
            scope = table_scope(text, fg, fgs[index + 1] if index + 1 < len(fgs) else None)
            styles = [style.strip() for _, style in CK_ROW_RE.findall(scope)]
            if fg == "FG-API":
                result.require(all(style == "Assume" for style in styles), "FG-API contains non-Assume CK")
            if fg == "FG-COVERAGE":
                result.require(all(style == "Cover" for style in styles), "FG-COVERAGE contains non-Cover CK")

        fc_heading_count = 0
        for index, fg in enumerate(fgs):
            scope = table_scope(text, fg, fgs[index + 1] if index + 1 < len(fgs) else None)
            headings = list(re.finditer(r"^#### .+$", scope, re.M))
            scope_fcs = FC_ROW_RE.findall(scope)
            fc_heading_count += len(headings)
            result.require(len(headings) == len(scope_fcs), f"{fg} FC heading count {len(headings)} != FC count {len(scope_fcs)}")
            for heading_index, heading in enumerate(headings):
                end = headings[heading_index + 1].start() if heading_index + 1 < len(headings) else len(scope)
                block = scope[heading.end() : end]
                first_table = block.find("\n|")
                prose = block[:first_table] if first_table >= 0 else block
                result.require(bool(re.search(r"[^\s|`#*-]", prose)), f"missing prose after heading: {heading.group(0)}")
                if template_major >= 3:
                    result.require(bool(P_REF_RE.search(block)), f"missing P-* reference in FC block: {heading.group(0)}")
        result.require(fc_heading_count == len(fcs), f"FC natural-language heading count {fc_heading_count} != FC count {len(fcs)}")
    else:
        fc_details = FC_DETAIL_RE.findall(text)
        ck_details = [(name, style.strip(), fc) for name, style, fc in CK_DETAIL_RE.findall(text)]
        result.require(len(fc_details) == len(fcs), "template v3.1 FC registry rows must include owning FG")
        result.require(len(ck_details) == len(cks), "template v3.1 CK registry rows must include owning FC")
        fc_to_fg = dict(fc_details)
        for ck, style, fc in ck_details:
            result.require(fc in fc_to_fg, f"CK owner FC missing from registry: {ck} -> {fc}")
            owner_fg = fc_to_fg.get(fc)
            if owner_fg == "FG-API":
                result.require(style == "Assume", f"FG-API CK is not Assume: {ck}")
            if owner_fg == "FG-COVERAGE":
                result.require(style == "Cover", f"FG-COVERAGE CK is not Cover: {ck}")
        ck_owner_fcs = {fc for _, _, fc in ck_details}
        result.require(set(fcs) <= ck_owner_fcs, f"FC has no CK in registry: {sorted(set(fcs)-ck_owner_fcs)}")

    if template_major >= 3:
        layer_headings = ["## 第一部分：正文", "## 第二部分：验证计划", "## 第三部分：附录"]
        layer_positions = [text.find(heading) for heading in layer_headings]
        result.require(all(position >= 0 for position in layer_positions), "template v3 document missing main/verification/appendix layer")
        result.require(layer_positions == sorted(layer_positions) and len(set(layer_positions)) == 3, "template v3 document layers are out of order")
        required_headings = (
            "### 文档摘要",
            "### 设计概览",
            "#### 实例能力矩阵",
            "### 功能行为",
            "### Test Plan",
            "### Coverage Summary",
            "### 形式化属性契约",
            "### 测试场景",
            "### 签核与开放项",
            "### 附录 D：证据索引",
            "### 附录 F：FC / CK 完整追溯",
        ) if template_version >= (3, 1) else (
            "### 阅读导引",
            "#### 数据生产者与消费者",
            "#### 关键概念速览",
            "#### 逻辑接口约定",
            "### Coverage 汇总",
            "### Test Plan 与场景",
        )
        for heading in required_headings:
            result.require(heading in text, f"template v3 required section missing: {heading}")

        if template_version >= (3, 1):
            summary_match = re.search(r"^### 文档摘要\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            summary_scope = summary_match.group(1) if summary_match else ""
            for field in ("**模块职责**", "**输入与生产者**", "**输出与消费者**", "**关键概念**", "**关键延迟与容量**", "**验证范围**", "**开放项**"):
                result.require(field in summary_scope, f"template v3.1 summary field missing: {field}")

            behavior_match = re.search(r"^### 功能行为\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            result.require(behavior_match is not None, "template v3.1 functional behavior section missing")
            behavior_scope = behavior_match.group(1) if behavior_match else ""
            p_definitions = P_DEF_HEADING_RE.findall(behavior_scope)
            for p_match in P_DEF_HEADING_RE.finditer(behavior_scope):
                next_match = P_DEF_HEADING_RE.search(behavior_scope, p_match.end())
                block = behavior_scope[p_match.end() : next_match.start() if next_match else None]
                for field in ("**输入**", "**输出**", "**延迟**", "**适用实例**", "**边界与限制**", "**证据**"):
                    result.require(field in block, f"{p_match.group(1)} missing behavior field: {field}")
                result.require("```text" in block, f"{p_match.group(1)} missing formula/pseudocode block")
        else:
            p_section_match = re.search(r"^### 权威行为定义\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            result.require(p_section_match is not None, "template v3 authoritative behavior section missing")
            p_definition_scope = p_section_match.group(1) if p_section_match else ""
            p_definitions = P_DEF_ROW_RE.findall(p_definition_scope)
        p_references = P_REF_RE.findall(text)
        result.require(bool(p_definitions), "template v3 document has no authoritative P-* definitions")
        result.require(len(p_definitions) == len(set(p_definitions)), "duplicate authoritative P-* definitions")
        unresolved_p = set(p_references) - set(p_definitions)
        result.require(not unresolved_p, f"unresolved P-* references: {sorted(unresolved_p)}")

        if all(position >= 0 for position in layer_positions):
            main_body = text[layer_positions[0] : layer_positions[1]]
            dense_lines = [
                line
                for line in prose_lines(main_body)
                if len(re.findall(r"`io_[A-Za-z0-9_\[\]*]+`", line)) >= 3
            ]
            result.require(not dense_lines, "main-body prose contains three or more exact RTL port names in one line")
            if template_version >= (3, 1):
                raw_locations = re.findall(r"`[^`\n]+:\d+`", main_body)
                result.require(not raw_locations, "template v3.1 main body contains raw path:line instead of E-* reference")

        if template_version >= (3, 1):
            evidence_match = re.search(r"^### 附录 D：证据索引\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            evidence_scope = evidence_match.group(1) if evidence_match else ""
            evidence_definitions = set(E_DEF_ROW_RE.findall(evidence_scope))
            evidence_references = set(E_REF_RE.findall(text))
            result.require(bool(evidence_definitions), "template v3.1 evidence appendix has no E-* definitions")
            result.require(len(E_DEF_ROW_RE.findall(evidence_scope)) == len(evidence_definitions), "duplicate E-* definitions")
            result.require(not (evidence_references - evidence_definitions), f"unresolved E-* references: {sorted(evidence_references-evidence_definitions)}")

            test_plan_match = re.search(r"^### Test Plan\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            test_plan_scope = test_plan_match.group(1) if test_plan_match else ""
            test_plan_fcs = set(re.findall(r"`(FC-[A-Z0-9-]+)`", test_plan_scope))
            test_plan_cks = set(re.findall(r"`(CK-[A-Z0-9-]+)`", test_plan_scope))
            result.require(set(fcs) <= test_plan_fcs, f"FC missing from Test Plan: {sorted(set(fcs)-test_plan_fcs)}")
            result.require(set(cks) <= test_plan_cks, f"CK missing from Test Plan: {sorted(set(cks)-test_plan_cks)}")
            ck_registry = {ck: (style, fc) for ck, style, fc in ck_details}
            for fc, ck, raw_style in TEST_PLAN_ROW_RE.findall(test_plan_scope):
                style = raw_style.strip()
                result.require(ck in ck_registry, f"Test Plan CK missing from registry: {ck}")
                if ck in ck_registry:
                    registry_style, registry_fc = ck_registry[ck]
                    result.require((style, fc) == (registry_style, registry_fc), f"Test Plan/registry mismatch for {ck}")
            for line in test_plan_scope.splitlines():
                if re.match(r"^\| P[0-2] \|", line):
                    result.require(bool(P_REF_RE.search(line)), f"Test Plan row missing P-* reference: {line}")

            verification_end = layer_positions[2] if layer_positions[2] >= 0 else len(text)
            reader_facing = text[:verification_end]
            result.require(not FC_ROW_RE.search(reader_facing), "template v3.1 FC registry table appears in main reading path")
            result.require(not CK_ROW_RE.search(reader_facing), "template v3.1 CK registry table appears in main reading path")

            coverage_match = re.search(r"^### Coverage Summary\s*$\n(.*?)(?=^### |\Z)", text, re.M | re.S)
            coverage_scope = coverage_match.group(1) if coverage_match else ""
            coverage_definitions = set(COV_DEF_ROW_RE.findall(coverage_scope))
            coverage_references = set(COV_REF_RE.findall(text))
            result.require(bool(coverage_definitions), "template v3.1 Coverage Summary has no COV-* definitions")
            result.require(not (coverage_references - coverage_definitions), f"unresolved COV-* references: {sorted(coverage_references-coverage_definitions)}")
            case_matches = list(CASE_RE.finditer(text))
            for index, case_match in enumerate(case_matches):
                case_end = case_matches[index + 1].start() if index + 1 < len(case_matches) else text.find("\n### 签核与开放项", case_match.start())
                case_scope = text[case_match.start() : case_end if case_end >= 0 else None]
                result.require(bool(COV_REF_RE.search(case_scope)), f"scenario case missing Coverage reference: {case_match.group(0)}")

    if existing_versions and current_template_version:
        latest_version = max(existing_versions, key=lambda version: tuple(map(int, version[1:].split("."))))
        if args.version == latest_version:
            result.require(template_version == current_template_version, f"latest document template {template_version} != current template {current_template_version}")

    result.require(text.count("```") % 2 == 0, "unbalanced Markdown fences")
    result.require('subgraph DUT["DUT: ' in text, "architecture DUT subgraph missing")
    result.require(len(CASE_RE.findall(text)) >= 3, "fewer than three scenario cases")
    mermaid_sources = [match.group(1).rstrip() + "\n" for match in MERMAID_RE.finditer(text)]

    validate_links([design, report, history], result)

    if manifest_path.exists() and ports_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with ports_path.open(encoding="utf-8", newline="") as handle:
            ports = list(csv.DictReader(handle))
        port_names = {row["name"] for row in ports}
        result.require(manifest.get("module") == args.module, "evidence module mismatch")
        result.require(manifest.get("port_count") == len(ports), "evidence port count mismatch")
        result.require(manifest.get("schema_version") == 1, "unsupported evidence schema version")
        result.require(manifest.get("generation_status") in {"success", "partial"}, "RTL evidence generation did not produce an accepted result")
        result.require(manifest.get("config") in text and manifest.get("config") in report_text, "evidence config not consistent across artifacts")
        port_counts = manifest.get("port_counts", {})
        result.require(sum(port_counts.values()) == len(ports), "manifest port direction counts do not match ports.csv")
        rtl_hash = manifest.get("rtl_sha256", "")
        result.require(bool(re.fullmatch(r"[0-9a-f]{64}", rtl_hash)), "invalid RTL SHA-256 in manifest")
        result.require(rtl_hash in text and rtl_hash in report_text, "RTL SHA-256 not consistent across design/report")
        commit = manifest.get("xiangshan_commit", "")
        result.require(commit in text and commit in report_text and commit in history_text, "evidence commit not consistent across artifacts")
        claimed = re.search(r"(\d+) 个叶端口：?(\d+)?", text)
        if claimed:
            result.require(int(claimed.group(1)) == len(ports), "document port count does not match manifest")
        checked_tokens: set[str] = set()
        covered_ports: set[str] = set()
        for line in text.splitlines():
            if any(marker in line for marker in ("未生成", "Elided", "不含", "裁剪")):
                continue
            for token in re.findall(r"`((?:io_[A-Za-z0-9_\[\]*]+|clock|reset))`", line):
                if token in checked_tokens:
                    continue
                checked_tokens.add(token)
                matches, indices = match_port_pattern(token, port_names)
                result.require(bool(matches), f"documented RTL port/pattern missing: {token}")
                covered_ports.update(matches)
                for marker, values in indices.items():
                    if values:
                        result.require(values == set(range(max(values) + 1)), f"non-contiguous indices for {token} marker [{marker}]: {sorted(values)}")
        if args.strict_evidence and template_version >= (3, 1, 0):
            result.require(port_names <= covered_ports, f"ports.csv leaves missing from document mapping: {sorted(port_names-covered_ports)}")
    elif args.strict_evidence:
        result.errors.append(f"missing evidence manifest/ports: {evidence}")
    else:
        result.warnings.append(f"evidence not available: {evidence}")

    requires_render_evidence = template_major >= 2
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

    print(f"FG={len(fgs)} FC={len(fcs)} CK={len(cks)} cases={len(CASE_RE.findall(text))}")
    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
