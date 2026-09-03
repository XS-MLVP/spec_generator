#!/usr/bin/env python3
"""Validate repository-owned links, template, and Skill metadata."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".cache", "node_modules", "third_party"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def is_repository_owned(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    if not parts or EXCLUDED_PARTS.intersection(parts):
        return False
    if parts[0] in {"inputs", "outputs", "evidence"}:
        return False
    if parts[0] == "reports" and (len(parts) < 2 or parts[1] != "template"):
        return False
    return True


def main() -> int:
    errors: list[str] = []
    markdown_files = [path for path in ROOT.rglob("*.md") if is_repository_owned(path)]
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

    template = ROOT / "templates/chip-design-document/chip_design_document_template_zh.md"
    if not re.search(r"^> 模板结构版本：v\d+\.\d+\.\d+$", template.read_text(encoding="utf-8"), re.M):
        errors.append("template structure version missing or invalid")

    skill = ROOT / ".opencode/skills/xiangshan-design-document/SKILL.md"
    skill_text = skill.read_text(encoding="utf-8")
    if not skill_text.startswith("---\n") or "name: xiangshan-design-document" not in skill_text[:500] or "description:" not in skill_text[:500]:
        errors.append("invalid xiangshan-design-document Skill frontmatter")

    print(
        f"Repository Markdown files={len(markdown_files)}; "
        "module artifacts are validated by validate_document.py"
    )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
