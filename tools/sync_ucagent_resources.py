#!/usr/bin/env python3
"""Synchronize canonical document assets into the distributable UCAgent plugin."""

from pathlib import Path
import re


def main() -> None:
    """Copy the existing template and complete generation guidance for packaging."""
    root = Path(__file__).resolve().parents[1]
    resources = root / "src/spec_generator_plugin/resources"
    template = "templates/chip-design-document/chip_design_document_template_zh.md"
    for source, destinations in (
        (template, (template, "Guide_Doc/chip_design_document_template_zh.md")),
        (
            ".opencode/skills/xiangshan-design-document/SKILL.md",
            ("Guide_Doc/generation-guide.md",),
        ),
    ):
        text = (root / source).read_text(encoding="utf-8")
        if text.startswith("---\n"):
            text = text.split("---\n", 2)[2]
        # Runtime Markdown requires a blank line before every ATX heading,
        # including the first heading in a copied resource.
        lines = [""]
        for line in text.splitlines():
            if re.match(r"^#{1,6}\s", line) and (not lines or lines[-1].strip()):
                lines.append("")
            lines.append(line)
        text = "\n".join(lines) + "\n"
        for destination in destinations:
            path = resources / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(path.relative_to(root))


if __name__ == "__main__":
    main()
