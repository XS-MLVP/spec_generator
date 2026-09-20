
# XiangShan Spec Generator

为 XiangShan 模块生成中文设计与功能检测点文档的 **UCAgent 插件**。

- **基于实现生成**：结合 Chisel/Scala 源码与同 commit、同配置的 RTL，记录精确端口和证据来源。
- **交付版本化文档**：生成设计说明、验证计划、质量报告和版本历史，实际渲染 Mermaid 图。
- **分阶段验收**：检查模板结构、证据、引用和图形一致性；无法确认的内容保留为 `OPEN-*`。

工作流：**生成 RTL 证据 → 编写文档 → 渲染与验收**。文档检查通过不代表 SVA 编译或 formal 证明通过。

## 安装

支持 Linux/macOS，需要 Python 3.11+、Bash、Git、Curl、Make 和 C 编译器。JDK 17、Mill、Node.js、Mermaid 和浏览器由插件按需准备或复用，首次运行需要网络。

在 UCAgent 使用的同一 Python 环境中安装。已有兼容 UCAgent 时可跳过第一条命令；下面是 CI 验证的版本：

macOS 安装前先执行 `export ARCHFLAGS="-arch $(uname -m)"`，使 wavekit 扩展仅按当前机器架构编译，避免 universal2 与 `-march=native` 冲突。

```bash
python -m pip install 'UCAgent @ git+https://github.com/XS-MLVP/UCAgent.git@856ee9f9fd68cac09bda2f6495c55d96c6857038'
git clone --recurse-submodules https://github.com/XS-MLVP/spec_generator.git
cd spec_generator
python -m pip install -e .
ucagent --validate-plugin .
```

已有 clone 可运行 `make init` 补齐 XiangShan 子模块。模型连接按 UCAgent 的常规方式配置。

## 使用

在仓库根目录运行，以 `Sbuffer` 为例：

```bash
SPEC_DOCUMENT_VERSION=v1.0.0 XIANGSHAN_CONFIG=DefaultConfig \
ucagent . Sbuffer \
  --backend langchain \
  --plugin . \
  --plugin-workflow xiangshan-spec-generator:design-document \
  --output outputs/Sbuffer \
  --no-history
```

| 参数 | 设置方式 |
| --- | --- |
| 模块 | 将 `Sbuffer` 替换为实际 Chisel class 名，同时修改 `--output` |
| 配置 | `XIANGSHAN_CONFIG`，默认 `DefaultConfig` |
| 文档版本 | `SPEC_DOCUMENT_VERSION`，默认 `v1.0.0` |
| 可选需求说明 | 放入 `inputs/<Module>/`；实现结论仍以源码和 RTL 为准 |

新任务保留 `--no-history`，已有归档时选择更高的新版本；恢复未完成任务时使用相同模块、配置和版本，去掉该选项。保留工作区的 `.ucagent/` 和 `evidence/`，以便恢复及核验证据。

**独立工作区**：安装后，把命令中的 `.` 工作区参数改为目标路径，`--plugin .` 改为 `--plugin xiangshan-spec-generator`。该工作区需提供 `third_party/XiangShan/`，包含初始化后的子模块。wheel 安装也使用这一入口；安装包不包含 XiangShan 或大型工具链。

**后端**：示例使用 LangChain。使用 OpenCode 时改为 `--backend opencode`；上述 UCAgent 版本的配置禁用原生 Shell 和工作区外访问。其他命令行后端需先配置并实测同等限制，见[安全策略](SECURITY.md)。工作流无需 Skill。

## 生成产物

| 路径 | 内容 |
| --- | --- |
| `outputs/<Module>/<Module>_design_document_zh_vX.Y.Z.md` | 设计与功能检测点文档 |
| `outputs/<Module>/VERSION_HISTORY.md` | 版本历史 |
| `reports/<Module>/<Module>_document_quality_review_vX.Y.Z.md` | 质量报告与未签核项 |
| `evidence/<Module>/vX.Y.Z/` | RTL、`ports.csv`、证据清单及 `diagrams/` 中的 SVG |

产物路径固定，`--output` 只指定 UCAgent 的输出与历史管理目录。仓库忽略本地输入、产物和运行状态；需要长期保存时请另行归档。

设计文档需符合模板的标题、层级、章节顺序和各节表格数量；正文篇幅、表格行数和图形数量不固定。完整要求见[生成指南](src/spec_generator_plugin/Guide_Doc/generation-guide.md)和[文档模板](src/spec_generator_plugin/Guide_Doc/chip_design_document_template_zh.md)。

## 插件工具

UCAgent 在工作流中调用 `SpecGeneratorCommand`，并通过 `Check`、`Complete` 验收阶段：

| action | 用途 |
| --- | --- |
| `preflight` | 检查模块、配置、源码和工具环境 |
| `evidence` | 生成 RTL、端口清单和证据；恢复时核验已有文件 |
| `metadata` | 同步事实元数据和版本历史 |
| `render` | 将 Mermaid 渲染成 SVG |
| `validate` | 检查草稿结构、证据与引用 |
| `lint` | 最终检查，包含图形一致性 |

调用时传入 `module`、`config`、`version`；仅 `preflight` 可省略版本。例如：

```python
SpecGeneratorCommand(action="evidence", module="Sbuffer", config="DefaultConfig", version="v1.0.0")
```

新增版本历史行时，`metadata` 还需 `change_type`（Major/Minor/Patch）和单行 `summary`。单次命令上限一小时。
只加载 `--plugin` 可复用工具和 Checker；选择 `--plugin-workflow` 才会启用文档工作流并复制 Guide_Doc。

## 常见问题

- **找不到插件或同名冲突**：确认 pip 与 ucagent 使用同一 Python 环境；源码调试使用 `--plugin /绝对路径/spec_generator`。
- **环境检查失败**：按诊断补齐工具或子模块，确认模块及配置 class 名正确；激活时要求 Bash、Git、Curl、Make 的 `--version` 能正常执行。
- **工具不可见**：检查 `tools.selected_tools` 与 `tools.ignore_tools`，勿屏蔽工作流所需工具。
- **验收失败**：按 `Check` 指出的文件和位置修复；改图后重新 `render`，事实字段变化后重新 `metadata`。已有归档使用新版本，不覆盖历史证据。
- **修改插件资源后仍使用旧内容**：重新启动工作流并重新生成工作区的运行资源。

开发、项目结构与发布方法见 [CONTRIBUTING.md](CONTRIBUTING.md)。项目采用 [MIT License](LICENSE)。
