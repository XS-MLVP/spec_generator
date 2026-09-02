# Sbuffer 文档质量评审 v1.0.0

## 版本与范围

| 项目 | 内容 |
| --- | --- |
| 报告版本 | v1.0.0 |
| 评审文档 | [Sbuffer_design_document_zh_v1.0.0.md](../../outputs/Sbuffer/Sbuffer_design_document_zh_v1.0.0.md) |
| 前一版本 | None（首次正式版本）；[legacy](../../outputs/Sbuffer/Sbuffer_design_document_zh.md)仅作对照 |
| 版本选择 | v1.0.0 / Major：首次使用真实 XiangShan 源码和 elaborated RTL，修正后的 I/O 与行为契约不兼容 legacy |
| 模板结构 | pre-v2 schema 历史基线；后续生成使用模板结构 v2.0.0，并按兼容性决定文档版本增量 |
| XiangShan commit | `aee742c92250058644c3166fae54c489161347cc`，clean |
| 配置 | `DefaultConfig`，1 core，SystemVerilog split，`--fpga-platform --reset-gen` |
| 日期 | 2026-09-01 |

## 证据基线

| 类型 | 资产 | 结果 |
| --- | --- | --- |
| 模板 | `templates/chip-design-document/chip_design_document_template_zh.md` | 已应用版本、I/O、参数、FSM、subgraph、表格标签和 case 要求。 |
| 主源码 | `third_party/XiangShan/src/main/scala/xiangshan/mem/sbuffer/Sbuffer.scala` | 已读完整实现。 |
| Bundle / config | LSQBundle、DCacheWrapper、mem/Bundles、Bundle、Parameters、Configs、utility | 已定位 I/O class、默认值和 helper 语义。 |
| 可选规格 | `inputs/Sbuffer/Sbuffer_spec.md`、`SbufferData_spec.md` | 仅用作意图和差异输入。 |
| Elaborated RTL | `third_party/XiangShan/build/rtl/Sbuffer.sv` | 已生成；166 叶端口，37 input / 129 output。 |
| 子模块 RTL | `third_party/XiangShan/build/rtl/SbufferData.sv` | 已生成；用于核对 storage 展开。 |
| 持久证据 | [`manifest.json`](../../evidence/Sbuffer/v1.0.0/manifest.json)、[`ports.csv`](../../evidence/Sbuffer/v1.0.0/ports.csv) | 已从目标 RTL 提取并纳入版本化资产。 |

`Sbuffer.sv` SHA-256 为 `1e1fe1c1fcea11b0e016dfce391dd771c62eff310cdb4702e712d5a9407e027e`；`SbufferData.sv` 为 `a13eb4a50223633f94d29c60fc2aa30a11ed77f68f0210bfa992b1ed1f9c8b9a`。

## 版本差异

### Added

- 首次正式版本号、完整 commit、配置、生成命令、RTL hash 和版本历史。
- 真实匿名 top Bundle、`io.in.req[i]`、S0/S1/S2 forward、`physicalStoreQueueFull`、`sbFull`、`mshr_store_empty`、`flush.isCmo` 与 `io_perf` 结构。
- 166 个 DefaultConfig Verilog 叶端口的精确名称/模式、方向和位宽。
- exact FSM priority、CMO exit、data hazard、same-block wait、accepted miss/replay、feature elision。
- 双写同 byte 优先级、wline replication、非目标 frame condition 和 4 个场景 case。

### Changed

- `SbufferIO` 改为匿名 Bundle；`io.in[i]` 改为 `io.in.req[i]`。
- DCache 类型由旧文档的 `DCacheWriteReq/DCacheResp` 改为 `DCacheLineReq/DCacheLineResp`。
- forward 从“同周期组合”改为 S0 到 S2 两个寄存边界。
- coherence timeout 从 counter MSB 改为 `cohCount >= io.csrCtrl.sbuffer_timeout` 的寄存结果。
- `sbempty` 改为 Sbuffer entries + store MSHR + input valid 的 qualification；`flush.empty` 再加入 SQ empty。
- 仲裁和 FSM 从规格概述改为源码精确优先级。

### Fixed

- 删除 data/ptag/vtag reset 为零的错误结论；只有 state/counters/FSM/mask 等显式初始化。
- 修正“flush.valid 必须保持到 empty”：当前 FSM 由 pulse 进入 drain_all 后自行保持。
- 修正“同块 inflight 阻止新 store”：当前新 store 可分配另一个 entry 并记录 wait mask。
- 修正“completion 只代表 hit”：MainPipe accepted miss 也释放 Sbuffer entry。
- 修正 Difftest 在本模块实例化 `flow/WlineMaxNumber` 个事件的错误；源码每 enqueue channel 一个 event，附 split metadata。
- 修正 prefetch 训练存在 backpressure 的错误；SPB training 是 Valid 路径。

### Removed

- 删除不存在的 `dataInvalid`、`forwardMaskFast` 顶层端口。
- 删除不存在的 refill hit response port；`hit_resps` 只是 MainPipe response 的 Scala alias。
- 删除 DefaultConfig 中被 elaboration 裁剪的 Verilog 端口假名。

### Remaining OPEN

- `OPEN-BEHAV-001`：merge 的 `cohCount := 0` 被文件后部 active 自增覆盖，需设计确认意图。
- `OPEN-BEHAV-002`：drain/coherence 首选项非 candidate 时不退选，需确认排空进展意图。
- `OPEN-VERIFY-001`：UCAgent parser、SVA 编译、formal bind/prove/cover 与 Mermaid 实际渲染未执行。

## 规格核验

| 结论 | 规格主张 | 源码结果 |
| --- | --- | --- |
| Confirmed | insert/merge、整行 writeback、active-over-inflight forward、replay retry、四态 FSM。 | 主要职责成立，但时序和边界已按源码细化。 |
| Corrected | SbufferData write/flush 延迟。 | 两者均跨一个寄存边界后更新；源码注释称“2 cycle”是流水阶段命名。 |
| Corrected | threshold 默认 7/base 4。 | DefaultConfig/Constantin 为 9/1。 |
| Corrected | replay counter/timeout。 | counter 从 0 向上计数到 5-bit MSB，而非倒数。 |
| Rejected | SbufferData data reset 为 0。 | data 是无初始化 `Reg`；mask 才是 `RegInit(false)`。 |
| Rejected | 并发 write 同 entry 被上游禁止。 | 双路同 tag 会故意写同 entry；重叠 byte 由后置 channel 1 覆盖。 |
| Rejected | vector/wline 产生多个本地 DiffStoreEvent。 | 每 channel 一个 event，使用 split metadata。 |

## 完整性评分

| 维度 | 评分 | 说明 |
| --- | --- | --- |
| 设计信息 | 5/5 | 核心路径、边界、资源、FSM、恢复和可选特性均有源码证据。 |
| Chisel I/O | 5/5 | top 匿名 Bundle、子 Bundle、对象和有效方向已核对。 |
| Verilog I/O | 5/5 | 对所选 DefaultConfig 产物完成 166 个叶端口核对；裁剪字段明确标记未生成。 |
| 参数定位 | 5/5 | 默认参数、derived constants、runtime/Constantin controls 均有 Scala 位置。 |
| 形式化可生成性 | 4/5 | FC/CK、Style、frame 和 symbolic 约定齐全；尚未运行 UCAgent/SVA。 |
| 图形与场景 | 4/5 | 图源和 4 个 case 完整；未做 Mermaid 实际渲染。 |
| 证据边界 | 5/5 | spec 错误未写成事实，两个行为疑点显式 OPEN。 |

## 静态结果

- 版本一致性：设计文件名、报告文件名、正文版本和历史行均为 v1.0.0，链接有效。
- 标签与树：10 个 FG、22 个 FC、75 个 CK；标签无重复，FC 树与 FC 表完全一致。
- Style scope：`FG-API` 仅含 Assume，`FG-COVERAGE` 仅含 Cover；CK Style 均属于模板允许集合。
- Markdown/Mermaid：4 组 fence 配对，包含 DUT `subgraph`、顶层状态图、事务图和 4 个 case。
- I/O artifact：脚本解析 `Sbuffer.sv` 得到 166 个端口（37 input、129 output），代表性首末端口和所有表中数组边界存在。
- 本项目 Markdown 相对链接与源码文件路径检查通过。
- 统一 checker：`tools/validate_document.py --module Sbuffer --version v1.0.0 --strict-evidence` 通过。
- 仓库 lint：`make lint MODULE=Sbuffer VERSION=v1.0.0` 通过，包含 Bash/Python 语法、项目链接、manifest 可移植性及文档检查。
- UCAgent checker：当前仓库未提供，未运行。
- SVA 编译/prove/cover：无 harness，未运行。
- Mermaid renderer：未安装，未运行。

## Elaborate 记录

1. 原始 `make verilog CONFIG=DefaultConfig` 在 macOS 因 GNU `time -avp` 不可用而未启动 Mill；直接命令又暴露系统 Java stub、Linux x86-64 Espresso 和 `NOOP_HOME` 等跨平台前提。
2. 项目新增跨平台 wrapper：自动 bootstrap Temurin JDK 17 与 Mill 0.12.17，按 OS/architecture 构建 native Espresso，以 trap 恢复资源，并设置 `NOOP_HOME`。
3. `tools/generate_rtl.sh --module Sbuffer --config DefaultConfig` 完整执行成功，TopMain exit code 0；firtool 1.149.0 写出 split RTL。再次调用命中 commit/config/flags/tool fingerprint 缓存。
4. 版本证据由 `tools/extract_rtl_evidence.py` 生成；checker 以 `ports.csv` 严格核对文档中的 RTL 端口与数组模式。

## 签核建议

设计评审应先关闭两个 `OPEN-BEHAV-*`。DV 随后为内部 arrays/state/candidate 暴露 bind mirror，运行 UCAgent checker 与 SVA 编译；只有这些步骤通过后，文档状态才能从 Review 升为 Frozen。
