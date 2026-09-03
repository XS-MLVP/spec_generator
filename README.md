# XiangShan Spec Generator

基于 XiangShan Chisel/Scala 源码、指定配置的 elaborated SystemVerilog、统一模板和可选 spec，生成可追溯、可版本化、可供设计评审与形式化验证使用的模块文档。

项目不把输入 spec 当作最终事实。生成流程会核对源码和实际 RTL，将结论分为 `FACT-*`、`OPEN-*`，并为 I/O、参数、顶层状态机、FG/FC/CK、Mermaid 图和场景案例保存可机器检查的证据。

## 当前状态

| 项目 | 当前基线 |
| --- | --- |
| XiangShan submodule | `aee742c92250058644c3166fae54c489161347cc` |
| 默认配置 | `DefaultConfig` |
| 模板结构版本 | `v3.0.0` |
| 最新 Sbuffer 文档 | [v2.0.1](outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.1.md) |
| 最新质量报告 | [v2.0.1](reports/Sbuffer/Sbuffer_document_quality_review_v2.0.1.md) |
| 文档版本历史 | [VERSION_HISTORY.md](outputs/Sbuffer/VERSION_HISTORY.md) |
| 自动检查 | Linux/macOS：RTL evidence、文档结构、链接和 Mermaid 实际渲染 |

当前输出适合作为设计评审、验证计划和属性生成的输入。在 UCAgent checker、SVA 编译以及 formal prove/cover 回归完成前，文档不应标记为 `Frozen`。

## 为一个模块生成 Spec 文档

这里的 “Spec 文档” 指 `outputs/<Module>/` 下按照当前模板生成的模块规格与验证计划。任意支持项目 Skill 的 LLM/Agent 都可以完成源码分析、版本选择、RTL evidence、正文、质量报告和检查；确定性生成与校验仍由仓库工具完成。

### 第 1 步：克隆并初始化项目

```bash
git clone --recurse-submodules git@github.com:XS-MLVP/spec_generator.git
cd spec_generator
```

已有 clone 补齐 submodule：

```bash
make init
```

所有 Agent 和 `make` 命令都应从仓库根目录 `spec_generator/` 执行。

### 第 2 步：确定模块和配置

至少准备以下信息：

| 信息 | 是否必需 | 示例 |
| --- | --- | --- |
| 文档模块名 | 必需 | `Sbuffer`、`ICache` |
| Chisel 顶层 class | 建议提供 | `Sbuffer` |
| XiangShan 配置 | 必需 | `DefaultConfig` |
| 已有 spec | 可选 | `inputs/Sbuffer/Sbuffer_spec.md` |

模块名区分大小写，并用于创建 `inputs/<Module>`、`outputs/<Module>`、`reports/<Module>` 和 `evidence/<Module>`。若功能名可能对应多个 Chisel class，应在请求中明确 DUT 顶层 class。

配置决定参数、功能开关和最终 Verilog 端口。没有项目特定要求时使用 `DefaultConfig`；不能把其他配置生成的 RTL evidence 复用到当前文档。

### 第 3 步：准备 RTL 并生成 FM-Agent 输入规约

RTL 文件统一放在：

```text
rtls/<Module>/*.v|*.sv|*.svh
```

仓库固定了 FM-Agent 的 `chip` 分支 commit。准备好 RTL 后运行：

```bash
make fm-spec MODULE=vfScheduler
```

该命令实际在 `third_party/FM-Agent` 中执行：

```bash
uv run python <absolute-path>/rtls/vfScheduler --hardware --verilog
```

FM-Agent 的原始工作区和相对证据保留在 `rtls/<Module>/fm_agent/`，`*_spec.md`/`*_info.md` 同步到 `inputs/<Module>/fm_agent/`。该阶段是长时间运行的 LLM 任务：中等规模 RTL 通常需要 20–30 分钟，复杂设计可能更久；启动前应确认 API 凭据、网络和费用预算，运行时不要因为几分钟没有终端输出而重复启动。进度可查看 `rtls/<Module>/fm_agent/fm_agent.log`，以进程退出码判断结果。

已有工作区默认走 `--resume`；进程中断或网络/模型错误修复后再次运行普通 `make fm-spec MODULE=<Module>`，RTL 或规约需要完整重跑时才使用 `make fm-spec-fresh MODULE=<Module>`。只有 `make fm-spec-check MODULE=<Module>` 通过后，才将规约交给文档 Skill；部分输出不得手工当作完成结果。

### 第 4 步：放置可选输入 Spec

已有需求说明、旧设计文档或 AI 生成的草稿可以放入：

```text
inputs/<Module>/
```

例如：

```text
inputs/ICache/ICache_spec.md
inputs/ICache/ICache_ecc_spec.md
```

没有 spec 也可以生成。Skill 会把 spec 作为设计意图参考，并以 Chisel/Scala 和 elaborated RTL 核验实现事实；冲突内容会进入质量报告或登记为 `OPEN-*`。

### 第 5 步：运行环境预检

```bash
make preflight MODULE=<Module> CONFIG=<Config>
```

Sbuffer 示例：

```bash
make preflight MODULE=Sbuffer CONFIG=DefaultConfig
```

看到 `Summary: 0 error(s)` 后再开始生成。工具支持 Linux x86-64/ARM64 和 macOS Intel/Apple Silicon。缺少的 JDK、Mill、Node.js、Mermaid CLI 和 headless browser 会下载到 `.cache/`；非 Linux x86-64 主机会构建固定 commit 的 native Espresso。详细依赖见 [environment/README.md](environment/README.md)。

### 第 6 步：使用通用 Skill 生成

通用 Skill 的唯一主源为 `skills/chip-dv-spec/`。仓库同时提供 `.opencode/skills/`、`.claude/skills/` 和 `.codex/skills/` 发现入口；选择所用平台并从仓库根目录启动。使用下面的请求模板：

```text
请使用 chip-dv-spec Skill 为 <Module> 生成模块规格与验证计划。
DUT Chisel 顶层 class：<ClassName>
XiangShan 配置：<Config>
可选 spec：inputs/<Module>/（如不存在则只使用源码）
请根据 VERSION_HISTORY.md 选择下一个合法版本，生成设计文档、质量报告、
RTL/端口 evidence 和 Mermaid 渲染 evidence，并运行严格 checker 与 make lint。
```

Sbuffer 示例：

```text
请使用 chip-dv-spec Skill 为 Sbuffer 生成下一版模块规格与验证计划。
DUT Chisel 顶层 class：Sbuffer
XiangShan 配置：DefaultConfig
可选 spec：inputs/Sbuffer/
请生成全部版本化产物并运行严格 checker 与 make lint。
```

如果平台只在会话启动时加载 Skill，修改 Skill 后需要重启对应会话。

### 第 7 步：检查生成产物

一次完整生成应新增同一版本的以下内容：

```text
outputs/<Module>/<Module>_design_document_zh_vX.Y.Z.md
outputs/<Module>/VERSION_HISTORY.md
reports/<Module>/<Module>_document_quality_review_vX.Y.Z.md
evidence/<Module>/vX.Y.Z/manifest.json
evidence/<Module>/vX.Y.Z/ports.csv
evidence/<Module>/vX.Y.Z/diagrams/manifest.json
evidence/<Module>/vX.Y.Z/diagrams/*.svg
```

设计文档、质量报告、history 和 evidence 的版本必须完全一致。`manifest.json` 应记录 XiangShan commit、配置、生成状态、工具版本、RTL SHA-256 和端口数量。

### 第 8 步：独立运行验收

即使 AI 已报告检查通过，也建议使用者重新运行：

```bash
make lint MODULE=<Module> VERSION=vX.Y.Z
```

该命令会真实重渲染 Mermaid，而不只是检查代码块语法。验收完成后重点阅读质量报告中的：

- spec 被确认、修正或拒绝的内容。
- `OPEN-IO-*`、`OPEN-PARAM-*`、`OPEN-BEHAV-*` 和 `OPEN-VERIFY-*`。
- 未运行的 UCAgent、SVA 或 formal 检查。
- RTL 生成是否为 `success`；若为 `partial`，是否明确说明失败发生在目标模块 RTL 输出之后。

### 可选：手工预生成 Evidence

通常让 Skill 自动执行即可。需要提前预热耗时的 RTL 缓存时，可先运行：

```bash
make evidence MODULE=<Module> CONFIG=<Config> VERSION=vX.Y.Z
```

该版本必须尚未存在。evidence 创建后，再让 Agent 使用完全相同的模块、配置和版本生成正文。历史 evidence 默认禁止覆盖。

### 常见问题

| 现象 | 处理 |
| --- | --- |
| `Chisel class not found` | 核对 class 大小写和当前 XiangShan commit，必要时在请求中给出 Scala 路径。 |
| 配置不存在 | 在 `third_party/XiangShan/src/main/scala/top/Configs.scala` 中确认配置 class。 |
| 首次 RTL 生成较慢 | 属正常情况；同 commit/config/tool fingerprint 的后续模块会复用 split-RTL 缓存。 |
| evidence 已存在 | 选择新的文档版本；不要用 `--replace-evidence` 覆盖历史。 |
| Mermaid 无法显示 | 运行 `make render`/`make lint`；检查版本目录中的 SVG 和 diagram manifest。 |
| 文档仍有 `OPEN-*` | 根据质量报告补充缺失源码、配置、RTL 或设计确认，不要猜测关闭。 |

## 快速命令示例

以下命令展示 Sbuffer 下一 Patch 版本的完整手工检查顺序。正文仍应由 Skill 生成：

```bash
make evidence MODULE=Sbuffer CONFIG=DefaultConfig VERSION=v2.0.2
# 使用 chip-dv-spec Skill 生成 outputs/、reports/ 和 VERSION_HISTORY.md
make render MODULE=Sbuffer VERSION=v2.0.2
make lint MODULE=Sbuffer VERSION=v2.0.2
```

## 生成流程

```text
preflight
  -> 确定文档版本、XiangShan commit 和配置
  -> 读取模板、Chisel/Scala、配置和可选 spec
  -> 生成或复用 split SystemVerilog 缓存
  -> 提取 RTL manifest 和精确端口清单
  -> 生成设计文档、质量报告和版本历史
  -> 实际渲染全部 Mermaid 图并保存 SVG evidence
  -> 严格文档检查和仓库 lint
```

实现事实的证据优先级：

1. 同 commit、同配置生成的 elaborated SystemVerilog：最终模块和扁平端口。
2. Chisel/Scala 源码：Bundle、对象、参数、状态机、更新规则和特性门控。
3. XiangShan 配置与实际生成命令：最终参数值和启用特性。
4. `inputs/<Module>/` 下的可选 spec：设计意图、术语和验证建议。
5. 无法证实的推断：只能登记为 `OPEN-*`。

## 文档模型

模板位于 [chip_design_document_template_zh.md](templates/chip-design-document/chip_design_document_template_zh.md)，当前结构版本为 `v3.0.0`。生成流程始终读取这个最新模板，不按历史模板版本选择分支。主要内容包括：

- 文档版本、RTL 基线、配置、工具链和 evidence。
- Chisel Bundle/object 与精确 Verilog 端口映射。
- `Generated`、`Elided` 和 `OPEN-IO-*` 配置状态。
- 参数的 Scala 定义位置与顶层状态机。
- 带 DUT `subgraph` 边界的微架构图和事务时序图。
- 可转为 Assert、Assume 或 Cover 的 `FG -> FC -> CK` 检测点。
- 正常、资源边界和恢复路径的 user-story case。

平台无关的 Skill 主源位于 [skills/chip-dv-spec/SKILL.md](skills/chip-dv-spec/SKILL.md)。详细的文档格式、DV/Testplan、证据和 XiangShan 工程规则按需放在 `references/`；平台目录只提供发现入口。

FC、CK、Case、端口、图表和文档行数由 DUT 行为与验证风险决定，不使用固定数量作为质量门禁。校验器检查当前格式、ID 关联、Style、evidence 和内部一致性。已有历史文档保留原结构；只有新生成或显式指定的文档按当前模板校验。

## 目录结构

```text
.
|- inputs/<Module>/                 可选原始 spec
|- templates/chip-design-document/  设计文档模板
|- outputs/<Module>/                版本化设计文档和 VERSION_HISTORY
|- reports/<Module>/                同版本质量报告
|- evidence/<Module>/<version>/     RTL manifest、ports.csv、Mermaid SVG
|- tools/                            跨平台生成和检查工具
|- environment/                      Linux/macOS/Docker 环境说明
|- third_party/XiangShan/            XiangShan Git submodule
|- skills/chip-dv-spec/              平台无关 Skill 主源
`- .{opencode,claude,codex}/skills/  平台发现适配入口
```

`.cache/` 保存可删除的本机工具和 split-RTL 缓存；`evidence/` 是文档版本的一部分，应提交到 Git。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `make init` | 初始化 XiangShan 及其递归 submodule。 |
| `make fm-spec MODULE=<M>` | 在 `rtls/<M>/` 上运行 FM-Agent；已有 workspace 默认恢复。 |
| `make fm-spec-fresh MODULE=<M>` | 不使用 `--resume` 完整重建该模块的 FM-Agent workspace。 |
| `make fm-spec-check MODULE=<M>` | 校验 FM-Agent manifest、RTL hash 和输出是否完整且未过期。 |
| `make preflight MODULE=<M> CONFIG=<C>` | 检查源码、配置、工具和图形环境。 |
| `make rtl MODULE=<M> CONFIG=<C>` | 生成或复用配置级 split-RTL 缓存。 |
| `make evidence MODULE=<M> CONFIG=<C> VERSION=<V>` | 创建该版本的 RTL manifest 和端口清单。 |
| `make render MODULE=<M> VERSION=<V>` | 实际渲染文档内全部 Mermaid 图并保存 SVG/hash。 |
| `make validate MODULE=<M> VERSION=<V>` | 严格检查单个版本。 |
| `make lint MODULE=<M> VERSION=<V>` | 重渲染图，并运行工具、仓库和文档检查。 |
| `make clean-cache` | 删除可重建的 `.cache/`。 |

## 版本与缓存

文档版本与 XiangShan commit 分开管理：

- `MAJOR`：DUT 范围或文档 schema 不兼容变化。
- `MINOR`：接口、参数、状态、功能或检测点发生语义变化。
- `PATCH`：证据、OPEN 项、措辞、图形或格式变化，行为契约不变。

模板维护独立的结构版本，生成文档必须记录所用模板版本。每次生成都创建新版本，不覆盖历史文档或 evidence。

RTL 缓存键包含 XiangShan commit、配置、生成 flags、Java/Mill/Espresso、OS/架构和 wrapper 版本。同一配置的 split RTL 可供多个模块复用。

## 质量门禁

`make lint` 至少检查：

- Bash/Python 语法和仓库 Markdown 链接。
- 文档、报告、history 和 evidence 的版本一致性。
- 当前模板章节顺序、FG/FC/CK 唯一性、树表/追溯一致性和 Style scope。
- Scala 路径/行号及 Verilog 端口模式。
- Mermaid 真实解析、浏览器渲染、非空 SVG、source/SVG hash。
- XiangShan 生成过程不会遗留 submodule 修改。

CI 在 Linux 和 macOS 上运行同一验证入口。对按照当前模板新生成的版本执行：

```bash
make lint MODULE=<Module> VERSION=<current-schema-version>
```

## 参与贡献

开发流程、版本选择、evidence 要求和提交检查见 [CONTRIBUTING.md](CONTRIBUTING.md)。项目采用 [MIT License](LICENSE)。

## 已知边界

- 尚未集成 UCAgent checker 和正式 SVA/formal harness。
- 默认 RTL evidence 来自完整 `TopMain` elaboration，首次生成开销较大。
- 不同配置的端口和功能可能不同，禁止复用其他配置的 evidence。
- 版本化 SVG 是渲染证明；Markdown 平台仍需支持 Mermaid 才能原位显示源码图。
