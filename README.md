# XiangShan Spec Generator

基于 XiangShan Chisel/Scala、指定配置的 elaborated SystemVerilog、统一模板和可选输入 spec，生成面向设计评审与验证规划的模块文档。

生成流程不会把输入 spec 当作实现事实。它会以 matching RTL 和源码核验接口、参数、状态、行为与检测点，并把无法确认的内容标记为 `OPEN-*`。文档由正文、验证计划和审计附录组成，兼顾阅读与追溯。

当前模板版本：`v3.3.0`。详细原理见 [设计与证据模型](docs/design-and-evidence.md)。

## 快速开始

### 1. 获取项目

```bash
git clone --recurse-submodules git@github.com:XS-MLVP/spec_generator.git
cd spec_generator
```

已有 clone 可补齐 submodule：

```bash
make init
```

所有命令均从仓库根目录执行。

### 2. 准备输入

确定以下信息：

- 模块名，例如 `Sbuffer`、`ICache`。
- DUT Chisel 顶层 class。
- XiangShan 配置，例如 `DefaultConfig`。
- 可选输入 spec，放在 `inputs/<Module>/`。

没有输入 spec 也可以生成。已有需求说明、旧文档或 AI 草稿只作为设计意图参考；其中的实现结论仍需源码和 RTL 证实。

初版 spec 也可由 [FM-Agent](https://github.com/fmagent-project/FM-Agent/tree/chip) 生成，再放入 `inputs/<Module>/` 供本项目核验和完善。

### 3. 检查环境

```bash
make preflight MODULE=<Module> CONFIG=<Config>
```

看到 `Summary: 0 error(s)` 后再生成。项目支持 Linux x86-64/ARM64 和 macOS Intel/Apple Silicon；JDK、Mill、Node.js、Mermaid CLI 等工具会按需下载到 `.cache/`。安装细节见 [环境说明](environment/README.md)。

### 4. 使用 OpenCode 生成

安装 [OpenCode](https://opencode.ai/docs/) 后，在仓库根目录启动：

```bash
opencode
```

请求示例：

```text
请使用 xiangshan-design-document Skill 为 <Module> 生成设计与功能检测点文档。
DUT Chisel 顶层 class：<ClassName>
XiangShan 配置：<Config>
可选 spec：inputs/<Module>/（如不存在则只使用源码）
请选择下一个合法版本，生成设计文档、质量报告、RTL/端口 evidence
和 Mermaid evidence，并运行严格 checker 与 make lint。
```

修改 `.opencode/skills/` 后需重启 OpenCode，Skill 不会在当前会话中热更新。

### 5. 检查产物

一次完整生成会在本地创建：

```text
outputs/<Module>/<Module>_design_document_zh_vX.Y.Z.md
outputs/<Module>/VERSION_HISTORY.md
reports/<Module>/<Module>_document_quality_review_vX.Y.Z.md
evidence/<Module>/vX.Y.Z/manifest.json
evidence/<Module>/vX.Y.Z/ports.csv
evidence/<Module>/vX.Y.Z/diagrams/manifest.json
evidence/<Module>/vX.Y.Z/diagrams/*.svg
```

这些目录是用户工作资产，已被 `.gitignore` 排除。需要长期保存时，请归档到项目外的制品库或评审系统。

独立验收：

```bash
make lint MODULE=<Module> VERSION=vX.Y.Z
```

重点检查质量报告中的 spec 差异、`OPEN-*`、RTL 生成状态，以及未运行的 UCAgent、SVA 或 formal 项。未完成属性编译和 prove/cover 时，文档不应标记为 `Frozen`。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `make preflight MODULE=<M> CONFIG=<C>` | 检查源码、配置和工具环境。 |
| `make evidence MODULE=<M> CONFIG=<C> VERSION=<V>` | 生成 RTL manifest 和端口清单。 |
| `make metadata MODULE=<M> VERSION=<V>` | 从 evidence 同步机器元数据。 |
| `make render MODULE=<M> VERSION=<V>` | 渲染文档中的 Mermaid 图。 |
| `make validate MODULE=<M> VERSION=<V>` | 严格检查单个文档版本。 |
| `make lint MODULE=<M> VERSION=<V>` | 执行模块完整验收。 |
| `make repo-lint` | 检查仓库自有文档和工具。 |
| `make template-check` | 实际渲染模板示例图。 |
| `make clean-cache` | 删除可重建的 `.cache/`。 |

历史 v3 文档可使用：

```bash
make validate MODULE=<M> VERSION=<V> \
  ALLOW_HISTORICAL_TEMPLATE=--allow-historical-template
```

该参数仅用于归档文档，新文档必须使用当前模板。

## 故障排查

| 现象 | 排查方式 |
| --- | --- |
| `Chisel class not found` | 核对 class 大小写、当前 XiangShan commit 和 Scala 路径。 |
| 配置不存在 | 在 `third_party/XiangShan/src/main/scala/top/Configs.scala` 中确认配置 class。 |
| preflight 报工具缺失 | 查看首个 `[ERROR]`；确认网络、磁盘空间、JDK 17、Git、Curl、Make 和 C compiler。 |
| 首次 RTL 生成很慢 | 属正常情况；后续相同 commit/config/tool fingerprint 会复用 `.cache/rtl/`。 |
| evidence 已存在 | 使用新的文档版本；不要覆盖历史 evidence。 |
| RTL 状态为 `partial` | 查看 manifest 和质量报告；只有目标模块 RTL 已完整产生且失败发生在后处理时才可继续。 |
| Mermaid 无法显示 | 运行 `make render` 或 `make lint`，检查 diagram manifest 和 SVG；代码 fence 正确不代表渲染成功。 |
| 端口校验失败 | 确认文档配置与 `ports.csv` 来自同一 commit/config，检查数组索引、方向和位宽。 |
| 模板版本不匹配 | 新文档重新按当前模板生成；只有归档文档使用 historical-template 参数。 |
| 文档残留 `OPEN-*` | 按质量报告补充证据或设计确认，不要猜测关闭。 |

## 更多资料

- [设计与证据模型](docs/design-and-evidence.md)
- [环境说明](environment/README.md)
- [贡献指南](CONTRIBUTING.md)
- [参考案例说明](references/README.md)
- [安全策略](SECURITY.md)

项目采用 [MIT License](LICENSE)。
