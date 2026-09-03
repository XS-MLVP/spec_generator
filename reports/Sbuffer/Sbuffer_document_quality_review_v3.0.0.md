# Sbuffer 文档质量评审 v3.0.0

## 版本与范围

| 项目 | 内容 |
| --- | --- |
| 报告版本 | v3.0.0 |
| 评审文档 | [Sbuffer_design_document_zh_v3.0.0.md](../../outputs/Sbuffer/Sbuffer_design_document_zh_v3.0.0.md) |
| 前一版本 | [v2.0.1](../../outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.1.md) |
| 使用模板 | `chip_design_document_template_zh.md` 结构版本 v3.1.1 |
| 版本选择 | Major：v3.1.1 将正文、验证计划、审计附录及 P/FC/CK 注册协议改为与 v2 不兼容的人类可读 schema；RTL、配置和行为契约不变 |
| XiangShan commit | `aee742c92250058644c3166fae54c489161347cc`，submodule clean |
| 配置 | `DefaultConfig`，1 core，SystemVerilog split，FPGA/reset-gen |
| 日期 | 2026-09-03 |

## 版本差异

### Added

- 11 个唯一 `P-*` 行为小节，均含输入、输出、延迟、text 伪代码、适用实例、边界与限制和证据。
- 一页摘要、稳定逻辑名、实例能力矩阵、Coverage Summary、集中形式化契约以及附录 A-G。
- v3.0.0 独立 RTL evidence 与 3 张 Mermaid SVG/source-hash evidence。

### Changed

- 从 v2.1.0 模板布局迁移为 v3.1.1 三层结构；FC/CK 详细注册集中到附录 F，Test Plan 成为统一执行入口。
- I/O 由 Chisel/Verilog 表迁移为“逻辑名 -> Chisel -> exact RTL”映射，仍覆盖相同 166 leaves。
- 源码 path:line 从正文移入唯一 E-ID 证据索引；正文仅引用 `[E-*]`。

### Fixed

- 摘要明确 Store Queue 的生产者角色、DCache/Load pipeline 的消费者角色和 flush/CSR 控制方角色。
- 明确 active/inflight、ptag/vtag、insert/merge、completion/replay 四组差异，以及 forward 两边沿、empty 一边沿等实现延迟。
- 将 spec 中“组合 forward”“coherence counter MSB timeout”“reset 后 empty 立即有效”等表述按当前源码纠正。
- 明确 DUT 不锁存 CMO 类型，增加 drain_all 期间 `isCmo` 稳定的环境契约；移除仅由 Difftest 条件断言支持的 wline-zero Assume，避免过度约束。

### Removed

- 无 FG、FC、CK、场景、接口、参数、状态或行为语义删除；仅删除 v2 schema 的重复 FC/CK 正文注册形式。

### Remaining OPEN

- `OPEN-BEHAV-001`：merge counter 清零与后置 active 自增的 last-connect 意图待确认。
- `OPEN-BEHAV-002`：drain/coherence 首选 entry 非 candidate 时无退选的进展意图待确认。
- `OPEN-VERIFY-001`：UCAgent、SVA compile、formal bind/prove/cover 和 regression 未运行。

## 基线与工具

| 类型 | 资产 / 版本 | 结果 |
| --- | --- | --- |
| 主源码 | `third_party/XiangShan/src/main/scala/xiangshan/mem/sbuffer/Sbuffer.scala` | commit 与 v2.0.1 相同；复核 reset、enqueue、data、eviction、response、timeout、forward、FSM 和 feature gating。 |
| 可选规格 | `inputs/Sbuffer/Sbuffer_spec.md`、`SbufferData_spec.md` | 仅作意图与场景参考；冲突项未覆盖 RTL 事实。 |
| Preflight | `./tools/preflight.sh --module Sbuffer --config DefaultConfig --strict --document-tools` | 0 error、0 warning；源码、配置、工具、浏览器和子模块状态通过。 |
| RTL manifest | [manifest.json](../../evidence/Sbuffer/v3.0.0/manifest.json) | generation_status `success`；command 已记录；cache key `91e19f7fa5fb610379e3`。 |
| RTL ports | [ports.csv](../../evidence/Sbuffer/v3.0.0/ports.csv) | 166 leaves：37 input、129 output；0 open I/O。 |
| RTL hash | `1e1fe1c1fcea11b0e016dfce391dd771c62eff310cdb4702e712d5a9407e027e` | 与 v2.0.1 一致。 |
| 工具环境 | Darwin arm64；OpenJDK 17.0.20.1；Mill 0.12.17；firtool 1.149.0 | 来自 v3 manifest。 |
| Espresso | native build `85265139e9598852f9388d293658a1977a829a01` for Darwin/arm64 | 来自 v3 manifest。 |
| Mermaid | CLI 11.16.0；Node.js 22.23.2；pinned browser workflow | 3 张 SVG 实际渲染。 |
| Cache fingerprint | `91e19f7fa5fb610379e3` | v3 evidence cache key。 |
| RTL 生成状态 | Success | wrapper exit status 0；本轮复用已有 matching evidence，未重新运行 elaboration。 |

## Spec 裁定

| 分类 | 结论 |
| --- | --- |
| Confirmed | 16 entries、双路 enqueue、单路 line write、insert/merge、replay retry、四态 FSM、prefetch/Difftest 配置意图。 |
| Corrected | forward 是 S0/S1/S2 两边沿接口而非组合响应；coherence timeout 比较 CSR 而非 counter MSB；completion 包含 accepted miss；data 不 reset；empty 为寄存资格结果。 |
| Rejected | “flush.valid 必须保持到 empty”不是 DUT 捕获 flush 的必要条件；“SbufferData write 两周期后可见”和“同址 write/flush 禁止”不符合当前 last-connect 与 `GatedValidRegNext` 实现；“Difftest 在 Sbuffer 内拆成 flow 个事件”不符合源码。 |
| OPEN | merge counter last-connect 与仲裁不退选的设计意图，分别登记 `OPEN-BEHAV-001/002`。 |

## 完整性审查

| 维度 | 结果 |
| --- | --- |
| 摘要可读性 | 七个模板字段齐全；角色、关键概念、容量/延迟、范围和三个 OPEN 可独立阅读。 |
| 逻辑名 | 正文稳定使用 `store.accept[i]`、`dcache.write`、`dcache.response`、`load.query[k]`、`load.forward[k]`、`control.flush`、`status.empty` 等；正文无 exact RTL 枚举。 |
| P 单一定义 | 11 个 P 标题各出现一次；所有引用均解析；每节七项协议齐全。 |
| 实例分层 | enqueue 2、forward 3、DCache 1、prefetch/Difftest Elided 分开列；模块规则未混入端口枚举。 |
| I/O | 附录 B 以规则数组完整覆盖 166 leaves；Generated 166、OPEN 0；Elided Chisel 字段及原因单列。strict validator 已将端口模式反向展开并与 ports.csv 全集比较。 |
| 参数 / 配置 | v2.0.1 参数、derived constants、runtime/harness 参数和实例裁剪均保留。 |
| FSM | 仅四态顶层 FSM；状态语义、图和 `P-FLUSH-STATUS` 一致。 |
| FG / FC / CK | 10 / 22 / 75；以 `CK-API-CMO-MODE-STABLE` 替换证据不足的 wline-zero Assume；无重复标签；标签树、Test Plan、附录 F 集合一致；API 全 Assume，Coverage 全 Cover。 |
| Style | 仅 Comb、Seq、Seq, Symbolic、Assume、Cover。 |
| Test Plan | 每个 CK 独占一行，列格式符合模板，每行引用一个有效 `P-*`。 |
| E 引用 | 20 个唯一 E-ID；正文只用 `[E-*]`，链接从输出文档解析有效。 |
| 场景 | 5 个：normal、dual、full boundary、replay recovery、flush drain；只引用 P/CK，不复制算法。 |
| Mermaid | 3 张：微架构 flowchart、跨模块 sequenceDiagram、顶层 stateDiagram；架构图含 `subgraph DUT["DUT: Sbuffer"]`。 |

## 质量评分

| 维度 | 评分 | 说明 |
| --- | --- | --- |
| 设计信息 | 5/5 | 行为与当前源码及 v2.0.1 契约一致。 |
| Chisel / Verilog I/O | 5/5 | 166-port matching evidence 完整。 |
| 参数、实例与 FSM | 5/5 | 参数和裁剪完整，状态图只含顶层 FSM。 |
| 可读结构与追溯 | 5/5 | v3.1.1 三层结构、稳定逻辑名、P/E 单一定义。 |
| 形式化可生成性 | 2/5 | 75 CK 清单完整，属性节只有代表性逻辑公式；逐 CK SVA、harness、编译和 prove/cover 均未完成。 |
| 图形与场景 | 5/5 | 3 张图真实渲染，5 个场景覆盖正常/边界/恢复。 |

## 验证结果

- `make render MODULE=Sbuffer VERSION=v3.0.0`：通过；3 张 SVG 实际渲染并写入 diagram manifest。
- `./tools/validate_document.py --module Sbuffer --version v3.0.0 --strict-evidence`：通过；10 FG、22 FC、75 CK、5 cases，模板版本、manifest 元数据、166-port 反向覆盖、RTL/diagram evidence 与 source hash 一致。
- `./tools/preflight.sh --module Sbuffer --config DefaultConfig --strict --document-tools`：通过；0 error、0 warning。
- `./tools/generate_rtl.sh --module Sbuffer --config DefaultConfig --version v3.0.0`：通过；命中同 commit/config/tool fingerprint 的 RTL 缓存，并创建独立 v3 evidence。
- `make lint MODULE=Sbuffer VERSION=v3.0.0`：通过；重渲染图形，并执行工具语法、仓库和严格文档检查。
- UCAgent checker：仓库未提供独立 checker，未运行。
- SVA compile / formal bind / prove / cover / simulation regression：缺少 harness，未运行；由 `OPEN-VERIFY-001` 阻塞。

## 签核结论

文档结构、I/O、参数、FSM、逻辑名、P/FC/CK 追溯和 Mermaid evidence 满足 Review 交付门槛。形式化与设计意图签核尚未完成，因此状态保持 Review，不能宣称属性通过或冻结发布。
