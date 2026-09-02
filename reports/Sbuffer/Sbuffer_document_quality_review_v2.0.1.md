# Sbuffer 文档质量评审 v2.0.1

## 版本与范围

| 项目 | 内容 |
| --- | --- |
| 报告版本 | v2.0.1 |
| 评审文档 | [Sbuffer_design_document_zh_v2.0.1.md](../../outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.1.md) |
| 前一版本 | [v2.0.0](../../outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.0.md) |
| 使用模板 | `chip_design_document_template_zh.md` 结构版本 v2.1.0 |
| 版本选择 | Patch：RTL、I/O、FG/FC/CK 和 case 不变；重新生成并落实 Mermaid 真实渲染门禁 |
| XiangShan commit | `aee742c92250058644c3166fae54c489161347cc`，clean |
| 配置 | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen |
| 日期 | 2026-09-01 |

## 证据基线

| 类型 | 资产 | 结果 |
| --- | --- | --- |
| Preflight | `tools/preflight.sh --module Sbuffer --config DefaultConfig --strict --document-tools` | 0 error、0 warning。 |
| 主源码 | `third_party/XiangShan/src/main/scala/xiangshan/mem/sbuffer/Sbuffer.scala` | commit 与 v2.0.0 相同，submodule clean。 |
| 可选规格 | `inputs/Sbuffer/Sbuffer_spec.md`、`SbufferData_spec.md` | 未变化，只作为意图输入。 |
| RTL evidence | [manifest.json](../../evidence/Sbuffer/v2.0.1/manifest.json)、[ports.csv](../../evidence/Sbuffer/v2.0.1/ports.csv) | 166 ports：37 input、129 output。 |
| RTL hash | `1e1fe1c1fcea11b0e016dfce391dd771c62eff310cdb4702e712d5a9407e027e` | 与 v2.0.0 完全一致。 |
| Mermaid evidence | [diagram manifest](../../evidence/Sbuffer/v2.0.1/diagrams/manifest.json) | Mermaid CLI 11.16.0 实际渲染 3 张非空 SVG。 |

工具环境：Darwin/arm64、OpenJDK 17.0.20.1、Mill 0.12.17、firtool 1.149.0、Node.js 22.23.2、Espresso commit `85265139e9598852f9388d293658a1977a829a01`。RTL 生成状态为 `success`。

## 版本差异

### Added

- 使用模板结构版本 v2.1.0 的图形渲染签核要求。
- v2.0.1 独立的 RTL manifest、166-port CSV、3 张 SVG 和 diagram source/SVG hash manifest。
- Preflight 对固定 Node.js、Mermaid CLI 和 browser 的检查结果。

### Changed

- 文档版本从 v2.0.0 递增为 v2.0.1，前一版本链接改为 v2.0.0。
- 所有 RTL、端口和图形 evidence 链接切换到 `evidence/Sbuffer/v2.0.1/`。
- 文档控制记录使用模板 v2.1.0，并将变更类型标为 Patch。

### Fixed

- 新版工作流不再用 fence 配对替代 Mermaid 验证；每张图必须经过真实 parser/browser 渲染。
- 微架构图避免 `[i]`、`*` 和 subgraph-ID 连线等高风险语法；时序图使用兼容文本。
- 微架构图保持纵向布局，viewBox 约 `1298 x 1790`，避免横向 4096 px 图在 Markdown 栏内缩放过小。

### Removed

- 无设计行为、接口、参数、状态、FG、FC、CK 或 case 删除。

### Remaining OPEN

- `OPEN-BEHAV-001`：merge `cohCount := 0` 与后置 active 自增的连接优先级待设计确认。
- `OPEN-BEHAV-002`：drain/coherence 首选 entry 非 candidate 时不退选待设计确认。
- `OPEN-VERIFY-001`：UCAgent checker、SVA 编译、formal bind/prove/cover 尚未运行。

## 行为对比

| 维度 | v2.0.0 -> v2.0.1 |
| --- | --- |
| XiangShan commit / 配置 | 不变 |
| RTL SHA-256 | 不变 |
| Verilog 端口 | 不变，166 leaves |
| 参数 / 顶层 FSM | 不变 |
| FG / FC / CK | 不变，10 / 22 / 75 |
| User-story case | 不变，4 个 |
| Mermaid 语义 | 不变；重新按模板 v2.1.0 生成和签核 evidence |

## I/O 与图形完整性

| 维度 | 结果 |
| --- | --- |
| Chisel I/O | 匿名 top Bundle、子 Bundle、对象、方向和类型保持完整。 |
| Verilog I/O | Generated/Elided 状态与 v2.0.1 `ports.csv` 对应；OPEN Verilog ports 为 0。 |
| 状态图 | 实际渲染成功，非空 SVG。 |
| 微架构图 | 实际渲染成功，DUT subgraph 和跨边界节点有效。 |
| 事务时序图 | 实际渲染成功，completion/replay 分支完整。 |
| 图源新鲜度 | strict checker 比较每个 Mermaid fence 的 source SHA-256 与 manifest。 |

## 质量评分

| 维度 | 评分 | 说明 |
| --- | --- | --- |
| 设计信息 | 5/5 | 行为契约与已核验 v2.0.0 一致。 |
| Chisel / Verilog I/O | 5/5 | 166-port evidence 与配置裁剪状态完整。 |
| 参数与 FSM | 5/5 | 独立章节及源码位置完整。 |
| 形式化可生成性 | 4/5 | 75 CK 完整；UCAgent/SVA 未运行。 |
| 图形与场景 | 5/5 | 3 张图真实渲染、hash 签核；4 个 case 完整。 |
| 版本与证据 | 5/5 | 文档、报告、history、RTL 与 diagram evidence 同版本。 |

## 验证结果

- `make render MODULE=Sbuffer VERSION=v2.0.1`：通过；3 张 SVG 实际渲染成功。
- `tools/validate_document.py --module Sbuffer --version v2.0.1 --strict-evidence`：通过；10 FG、22 FC、75 CK、4 case，RTL/diagram evidence source hash 一致。
- `make lint MODULE=Sbuffer VERSION=v2.0.1`：通过；实际重渲染 3 张图，并验证 16 个项目 Markdown、3 份 RTL manifest 和 2 份 diagram manifest。
- UCAgent checker：仓库未提供，未运行。
- SVA compile / prove / cover：无 harness，未运行。

## 签核建议

文档结构、I/O 和 Mermaid evidence 可进入评审。后续优先关闭两个 `OPEN-BEHAV-*` 并接入 UCAgent/formal 工具；完成前文档状态保持 Review。
