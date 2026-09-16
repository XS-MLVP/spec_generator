---
name: xiangshan-design-document
description: Review the evidence and traceability of a XiangShan design document against the current repository template and strict validators.
---

# XiangShan document review

This is an optional review aid. Read `Guide_Doc/generation-guide.md` and
`Guide_Doc/chip_design_document_template_zh.md` for the complete artifact contract.

Before final validation, verify:

1. Matching RTL, Scala, commit and configuration support every FACT; unresolved claims remain OPEN.
2. Logical interfaces map to the generated port names, directions and widths.
3. P/E references, FG/FC/CK registries, coverage and test-plan cases agree.
4. Design document, quality report and version history use one shared version.
5. Every Mermaid fence has current SVG evidence. Run `SpecGeneratorCommand` with
   `action="render"`, then `action="metadata"` after diagrams change.
6. Run `Check`, repair its diagnostics, then record the current results in the
   quality report and call `Complete`. Do not claim unrun compilation or proof.

Use ordinary file tools and `SpecGeneratorCommand`; no Skill script is required.
