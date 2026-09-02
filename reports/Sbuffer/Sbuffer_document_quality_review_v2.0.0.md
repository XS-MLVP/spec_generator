# Sbuffer 文档质量评审 v2.0.0

## 版本与范围

| 项目 | 内容 |
| --- | --- |
| 报告版本 | v2.0.0 |
| 评审文档 | [Sbuffer_design_document_zh_v2.0.0.md](../../outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.0.md) |
| 前一版本 | [v1.0.0](../../outputs/Sbuffer/Sbuffer_design_document_zh_v1.0.0.md) |
| 使用模板 | `chip_design_document_template_zh.md` 结构版本 v2.0.0 |
| 版本选择 | Major：模板 I/O schema 不兼容升级；RTL 行为契约、commit 和配置不变 |
| XiangShan commit | `aee742c92250058644c3166fae54c489161347cc`，clean |
| 配置 | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen |
| 日期 | 2026-09-01 |

## 证据基线

| 类型 | 资产 | 结果 |
| --- | --- | --- |
| Preflight | `tools/preflight.sh --module Sbuffer --config DefaultConfig --strict` | 0 error、0 warning。 |
| 主源码 | `third_party/XiangShan/src/main/scala/xiangshan/mem/sbuffer/Sbuffer.scala` | 与 v1 相同，submodule clean。 |
| Bundle / 参数 | LSQBundle、DCacheWrapper、mem/Bundles、Bundle、Parameters、Configs、utility | 源码位置与 v1 复核一致。 |
| 可选规格 | `inputs/Sbuffer/Sbuffer_spec.md`、`SbufferData_spec.md` | 未变化；仍只作为意图输入。 |
| RTL evidence | [manifest.json](../../evidence/Sbuffer/v2.0.0/manifest.json)、[ports.csv](../../evidence/Sbuffer/v2.0.0/ports.csv) | 共享 cache 命中；166 ports，37 input / 129 output。 |
| RTL hash | `1e1fe1c1fcea11b0e016dfce391dd771c62eff310cdb4702e712d5a9407e027e` | 与 v1 完全一致。 |
| Mermaid evidence | [diagram manifest](../../evidence/Sbuffer/v2.0.0/diagrams/manifest.json) | CLI 11.16.0 实际渲染 3 张非空 SVG。 |

工具环境由 manifest 锁定：Darwin/arm64、OpenJDK 17.0.20.1、Mill 0.12.17、firtool 1.149.0、Espresso commit `85265139e9598852f9388d293658a1977a829a01`。缓存 key 为 `c05dcf1334929192ba69`，生成状态为 `success`。

## 版本差异

### Added

- 文档明确记录模板结构版本 v2.0.0。
- I/O 映射新增“Chisel 存在”“当前配置生成状态”“裁剪/生成依据”三类信息。
- 每个 Generated 端口或数组模式关联 v2 `ports.csv`；每个 Elided 字段说明 feature disable、常量传播、未使用或 dead-port elimination 原因。
- 质量报告记录 preflight、共享 cache、工具版本、cache key 和 evidence 状态。
- 增加状态图、微架构图和时序图的版本化 SVG 及 source/SVG SHA-256 manifest。

### Changed

- I/O 表由 v1 的 7 列 schema 升级为模板 v2 的 10 列 schema。
- Elaborated Verilog 的文档依据统一指向可提交的 v2 evidence，不依赖可清理的 XiangShan `build/rtl`。
- 版本控制由 v1 的 pre-v2 schema 标记改为模板 v2.0.0，并链接前一正式版本。

### Fixed

- 明确区分“Chisel aggregate 中存在”与“DefaultConfig Verilog 中未生成”，避免把 `cmd`、Difftest、prefetch、部分 enqueue/response 字段误写成缺失定义。
- 精确 Generated 端口不再使用缩写后缀作为唯一依据，均给出完整 Verilog 名或可由 manifest 检查的数组模式。
- 修复 evidence invocation 元数据，使 v2 manifest 记录 `--version v2.0.0`。
- 修复微架构图解析错误：边标签中的 `[i]` 被 Mermaid 当作语法，且 subgraph ID 被当作连线节点。现改为纯文本边标签并增加内部 PERF 节点。
- 微架构图由横向改为纵向布局，SVG viewBox 宽度由 4096 降至约 1298，避免在 Markdown 内容栏中缩放过小。
- 简化时序消息中的标点和保留符号，提高不同 Mermaid renderer 的兼容性。
- 本次是对尚未签核、未提交的 v2.0.0 客观错误修复；设计行为、FC/CK、RTL evidence 未变化。

### Removed

- 删除 I/O 表中将协议/对端、生成状态和裁剪原因混放在单一“条件/对端”列的表达方式。
- 删除对 transient `build/rtl/Sbuffer.sv` 的文档控制链接依赖。

### Remaining OPEN

- `OPEN-BEHAV-001`：merge `cohCount := 0` 与后置 active 自增的连接优先级仍待设计确认。
- `OPEN-BEHAV-002`：drain/coherence 首选 entry 非 candidate 时不退选仍待设计确认。
- `OPEN-VERIFY-001`：UCAgent checker、SVA 编译、formal bind/prove/cover 和 Mermaid 实际渲染尚未执行。

## 行为对比

| 维度 | v1.0.0 -> v2.0.0 |
| --- | --- |
| XiangShan commit | 不变 |
| DefaultConfig 参数 | 不变 |
| RTL SHA-256 | 不变 |
| Verilog 端口集合 | 不变，166 leaves |
| 顶层 FSM | 不变，四态及优先级一致 |
| FG / FC / CK | 不变，10 / 22 / 75 |
| Case | 不变，4 个正常/边界/恢复案例 |
| 设计 OPEN | 不变，2 个行为项 + 1 个验证项 |

因此 Major 版本仅由不兼容模板结构驱动，不表示 Sbuffer RTL 行为发生变化。

## I/O 完整性

| 类别 | 结果 |
| --- | --- |
| Chisel top Bundle | 匿名 `Bundle in Sbuffer.io`，已明确，不虚构 `SbufferIO`。 |
| 子 Bundle | SbufferWriteIO、DCacheToSbufferIO、SbufferForward、SbufferFlushBundle、CustomCSRCtrlIO、StorePrefetchReq、DiffStoreIO 已定位。 |
| Generated leaves | 166 个均由 evidence parser 提取；文档中的精确端口/模式由 checker 对照。 |
| Elided fields | 每组保留 Chisel 声明、状态 `Elided`、Verilog“未生成”和裁剪依据。 |
| OPEN Verilog ports | 0；本配置 I/O 已签核。 |

## 质量评分

| 维度 | 评分 | 说明 |
| --- | --- | --- |
| 设计信息 | 5/5 | 行为内容继承 v1 并复核基线未变。 |
| Chisel I/O | 5/5 | class/object/type/direction/source 完整。 |
| Verilog I/O | 5/5 | Generated/Elided 状态与 166-port evidence 对应。 |
| 参数与 FSM | 5/5 | 独立章节和源码位置保持完整。 |
| 形式化可生成性 | 4/5 | 75 CK、Style/frame/symbolic 完整；未运行 UCAgent/SVA。 |
| 图形与场景 | 5/5 | 3 张 Mermaid 图由固定 CLI 实际渲染，SVG 和 hash 已版本化；4 case 完整。 |
| 版本与证据 | 5/5 | v2 文档、报告、history、manifest 和 ports 同版本。 |

## 验证结果

- `tools/validate_document.py --module Sbuffer --version v2.0.0 --strict-evidence`：通过；10 FG、22 FC、75 CK、4 case。
- `make render MODULE=Sbuffer VERSION=v2.0.0`：通过；stateDiagram、flowchart、sequenceDiagram 共 3 张 SVG 非空。
- `make lint MODULE=Sbuffer VERSION=v2.0.0`：通过；包含固定 Mermaid CLI 的重新渲染、Bash/Python 语法、项目 Markdown、RTL/diagram manifest、版本链接及端口模式检查。
- UCAgent checker：仓库未提供，未运行。
- SVA compile / prove / cover：无 harness，未运行。
- Mermaid renderer：`@mermaid-js/mermaid-cli` 11.16.0；本机使用 Microsoft Edge，Linux/macOS 无浏览器时自动 bootstrap headless shell。

## 签核建议

模板 v2 的结构化 I/O 已具备机器核对条件。后续优先关闭两个 `OPEN-BEHAV-*`，然后接入 UCAgent checker 和 formal harness；在这些验证通过前，文档状态保持 Review。
