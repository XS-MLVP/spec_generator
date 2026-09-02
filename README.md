# XiangShan Spec Generator

基于 XiangShan Chisel/Scala 源码、指定配置的 elaborated SystemVerilog、统一模板和可选 spec，生成可追溯、可版本化、可供设计评审与形式化验证使用的模块文档。

项目不把输入 spec 当作最终事实。生成流程会核对源码和实际 RTL，将结论分为 `FACT-*`、`OPEN-*`，并为 I/O、参数、顶层状态机、FG/FC/CK、Mermaid 图和场景案例保存可机器检查的证据。

## 当前状态

| 项目 | 当前基线 |
| --- | --- |
| XiangShan submodule | `aee742c92250058644c3166fae54c489161347cc` |
| 默认配置 | `DefaultConfig` |
| 模板结构版本 | `v2.1.1` |
| 最新 Sbuffer 文档 | [v2.0.1](outputs/Sbuffer/Sbuffer_design_document_zh_v2.0.1.md) |
| 最新质量报告 | [v2.0.1](reports/Sbuffer/Sbuffer_document_quality_review_v2.0.1.md) |
| 文档版本历史 | [VERSION_HISTORY.md](outputs/Sbuffer/VERSION_HISTORY.md) |
| 自动检查 | Linux/macOS：RTL evidence、文档结构、链接和 Mermaid 实际渲染 |

当前输出适合作为设计评审、验证计划和属性生成的输入。在 UCAgent checker、SVA 编译以及 formal prove/cover 回归完成前，文档不应标记为 `Frozen`。

## 快速开始

### 1. 克隆并初始化

```bash
git clone --recurse-submodules git@github.com:XS-MLVP/spec_generator.git
cd spec_generator
```

已有 clone 补齐 submodule：

```bash
make init
```

### 2. 检查环境

```bash
make preflight MODULE=Sbuffer CONFIG=DefaultConfig
```

工具支持 Linux x86-64/ARM64 和 macOS Intel/Apple Silicon。缺少的 JDK、Mill、Node.js、Mermaid CLI 和 headless browser 会下载到 `.cache/`；非 Linux x86-64 主机会构建固定 commit 的 native Espresso。详细依赖见 [environment/README.md](environment/README.md)。

### 3. 生成新版本

先按 SemVer 选择未占用版本。以下以 `v2.0.2` 为例：

```bash
make evidence MODULE=Sbuffer CONFIG=DefaultConfig VERSION=v2.0.2
# 使用 Skill 生成 outputs/、reports/ 和 VERSION_HISTORY.md
make render MODULE=Sbuffer VERSION=v2.0.2
make lint MODULE=Sbuffer VERSION=v2.0.2
```

在 OpenCode 中可直接要求：“使用 `xiangshan-design-document` Skill 为 Sbuffer 生成新版本文档”。修改 `.opencode/skills/` 后需要重启 OpenCode 才会加载新定义。

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

模板位于 [chip_design_document_template_zh.md](templates/chip-design-document/chip_design_document_template_zh.md)，当前结构版本为 `v2.1.1`。主要内容包括：

- 文档版本、RTL 基线、配置、工具链和 evidence。
- Chisel Bundle/object 与精确 Verilog 端口映射。
- `Generated`、`Elided` 和 `OPEN-IO-*` 配置状态。
- 参数的 Scala 定义位置与顶层状态机。
- 带 DUT `subgraph` 边界的微架构图和事务时序图。
- 可转为 Assert、Assume 或 Cover 的 `FG -> FC -> CK` 检测点。
- 正常、资源边界和恢复路径的 user-story case。

项目级 Skill 位于 [.opencode/skills/xiangshan-design-document/SKILL.md](.opencode/skills/xiangshan-design-document/SKILL.md)，定义证据优先级、版本策略、源码分析方法、I/O 映射规则、图形门禁和交付标准。

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
`- .opencode/skills/                 OpenCode 项目 Skill
```

`.cache/` 保存可删除的本机工具和 split-RTL 缓存；`evidence/` 是文档版本的一部分，应提交到 Git。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `make init` | 初始化 XiangShan 及其递归 submodule。 |
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
- FG/FC/CK 唯一性、树表一致性和 Style scope。
- Scala 路径/行号及 Verilog 端口模式。
- Mermaid 真实解析、浏览器渲染、非空 SVG、source/SVG hash。
- XiangShan 生成过程不会遗留 submodule 修改。

CI 在 Linux 和 macOS 上运行同一验证入口。提交前请执行：

```bash
make lint MODULE=Sbuffer VERSION=v2.0.1
```

## 参与贡献

开发流程、版本选择、evidence 要求和提交检查见 [CONTRIBUTING.md](CONTRIBUTING.md)。项目采用 [MIT License](LICENSE)。

## 已知边界

- 尚未集成 UCAgent checker 和正式 SVA/formal harness。
- 默认 RTL evidence 来自完整 `TopMain` elaboration，首次生成开销较大。
- 不同配置的端口和功能可能不同，禁止复用其他配置的 evidence。
- 版本化 SVG 是渲染证明；Markdown 平台仍需支持 Mermaid 才能原位显示源码图。
