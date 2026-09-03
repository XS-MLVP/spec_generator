# Sbuffer 文档版本历史

| 版本 | 日期 | XiangShan commit | 配置 | 变更类型 | 摘要 | 设计文档 | 质量报告 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3.0.0 | 2026-09-03 | `aee742c92250058644c3166fae54c489161347cc` | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen | Major | 从 v2 schema 迁移到不兼容的模板 v3.1.1 三层人类可读结构；RTL、166-port I/O、FG/FC/CK 和行为契约不变；3 张 Mermaid 图实际渲染。 | [设计文档](./Sbuffer_design_document_zh_v3.0.0.md) | [质量报告](../../reports/Sbuffer/Sbuffer_document_quality_review_v3.0.0.md) |
| v2.0.1 | 2026-09-01 | `aee742c92250058644c3166fae54c489161347cc` | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen | Patch | 使用模板 v2.1.0 重新生成；RTL/I/O/行为不变；3 张 Mermaid 图由固定 CLI 实际渲染并以 source/SVG hash 签核。 | [设计文档](./Sbuffer_design_document_zh_v2.0.1.md) | [质量报告](../../reports/Sbuffer/Sbuffer_document_quality_review_v2.0.1.md) |
| v2.0.0 | 2026-09-01 | `aee742c92250058644c3166fae54c489161347cc` | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen | Major | 升级模板 v2 I/O schema；RTL 行为/hash 不变；3 张 Mermaid 图已由固定 CLI 实际渲染并保存 SVG evidence。 | [设计文档](./Sbuffer_design_document_zh_v2.0.0.md) | [质量报告](../../reports/Sbuffer/Sbuffer_document_quality_review_v2.0.0.md) |
| v1.0.0 | 2026-09-01 | `aee742c92250058644c3166fae54c489161347cc` | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen | Major | 首次基于真实 Scala 与 166 个 elaborated Verilog 叶端口生成；修正 legacy 的 I/O、forward、timeout、empty、reset 和 Difftest 结论。 | [设计文档](./Sbuffer_design_document_zh_v1.0.0.md) | [质量报告](../../reports/Sbuffer/Sbuffer_document_quality_review_v1.0.0.md) |

> `Sbuffer_design_document_zh.md` 和 `Sbuffer_document_quality_review.md` 是版本规范建立前的 legacy 文件，不占用 SemVer 版本号。
