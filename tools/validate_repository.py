#!/usr/bin/env python3
"""Validate repository-level links, evidence, template, and Skill metadata."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".cache", "node_modules", "third_party"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MERMAID_RE = re.compile(r"^```mermaid\s*\n(.*?)^```\s*$", re.M | re.S)


def main() -> int:
    errors: list[str] = []
    markdown_files = [path for path in ROOT.rglob("*.md") if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)]
    for source in markdown_files:
        for raw in LINK_RE.findall(source.read_text(encoding="utf-8")):
            if raw.startswith(("http://", "https://", "#")):
                continue
            target_text, _, fragment = raw.partition("#")
            target = (source.parent / target_text).resolve()
            if not target.exists():
                errors.append(f"broken link: {source.relative_to(ROOT)} -> {raw}")
                continue
            if fragment.startswith("L") and fragment[1:].isdigit() and target.is_file():
                line_count = sum(1 for _ in target.open(encoding="utf-8", errors="replace"))
                if int(fragment[1:]) > line_count:
                    errors.append(f"line out of range: {source.relative_to(ROOT)} -> {raw}")

    for manifest_path in ROOT.glob("evidence/*/v*/manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ports_path = manifest_path.parent / manifest.get("ports_file", "")
        if not ports_path.exists():
            errors.append(f"missing ports file: {ports_path.relative_to(ROOT)}")
            continue
        with ports_path.open(encoding="utf-8", newline="") as handle:
            ports = list(csv.DictReader(handle))
        if manifest.get("port_count") != len(ports):
            errors.append(f"port count mismatch: {manifest_path.relative_to(ROOT)}")
        if manifest.get("schema_version") != 1:
            errors.append(f"unsupported evidence schema: {manifest_path.relative_to(ROOT)}")
        if not str(manifest.get("rtl_source", "")).startswith("cache://"):
            errors.append(f"non-portable rtl_source: {manifest_path.relative_to(ROOT)}")
        serialized = json.dumps(manifest)
        if str(ROOT) in serialized or re.search(r'"/(?:Users|home)/', serialized):
            errors.append(f"host absolute path in manifest: {manifest_path.relative_to(ROOT)}")

    for manifest_path in ROOT.glob("evidence/*/v*/diagrams/manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("diagrams", [])
        if manifest.get("diagram_count") != len(entries):
            errors.append(f"diagram count mismatch: {manifest_path.relative_to(ROOT)}")
        for entry in entries:
            output = manifest_path.parent / str(entry.get("output", ""))
            if not output.exists():
                errors.append(f"missing diagram SVG: {output.relative_to(ROOT)}")
                continue
            data = output.read_bytes()
            svg = data.decode("utf-8", errors="replace")
            if hashlib.sha256(data).hexdigest() != entry.get("svg_sha256"):
                errors.append(f"diagram SVG hash mismatch: {output.relative_to(ROOT)}")
            if len(data) < 200 or "<svg" not in svg or "viewBox=" not in svg:
                errors.append(f"invalid diagram SVG: {output.relative_to(ROOT)}")

    for document in ROOT.glob("outputs/*/*_design_document_zh_v*.md"):
        text = document.read_text(encoding="utf-8")
        template_match = re.search(r"\| 使用模板版本 \| v(\d+)\.", text)
        if not template_match or int(template_match.group(1)) < 2:
            continue
        version_match = re.search(r"_(v\d+\.\d+\.\d+)\.md$", document.name)
        if not version_match:
            errors.append(f"cannot derive document version: {document.relative_to(ROOT)}")
            continue
        module = document.parent.name
        diagram_manifest_path = ROOT / "evidence" / module / version_match.group(1) / "diagrams" / "manifest.json"
        if not diagram_manifest_path.exists():
            errors.append(f"missing required diagram manifest: {diagram_manifest_path.relative_to(ROOT)}")
            continue
        manifest = json.loads(diagram_manifest_path.read_text(encoding="utf-8"))
        sources = [match.group(1).rstrip() + "\n" for match in MERMAID_RE.finditer(text)]
        entries = manifest.get("diagrams", [])
        if len(sources) != len(entries):
            errors.append(f"stale diagram count: {document.relative_to(ROOT)}")
            continue
        for index, source in enumerate(sources):
            if hashlib.sha256(source.encode()).hexdigest() != entries[index].get("source_sha256"):
                errors.append(f"stale diagram source evidence: {document.relative_to(ROOT)} diagram {index + 1}")

    template = ROOT / "templates/chip-design-document/chip_design_document_template_zh.md"
    if not re.search(r"^> 模板结构版本：v\d+\.\d+\.\d+$", template.read_text(encoding="utf-8"), re.M):
        errors.append("template structure version missing or invalid")

    skill = ROOT / ".opencode/skills/xiangshan-design-document/SKILL.md"
    skill_text = skill.read_text(encoding="utf-8")
    if not skill_text.startswith("---\n") or "name: xiangshan-design-document" not in skill_text[:500] or "description:" not in skill_text[:500]:
        errors.append("invalid xiangshan-design-document Skill frontmatter")

    print(
        f"Markdown files={len(markdown_files)} "
        f"RTL manifests={len(list(ROOT.glob('evidence/*/v*/manifest.json')))} "
        f"diagram manifests={len(list(ROOT.glob('evidence/*/v*/diagrams/manifest.json')))}"
    )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
