
# XiangShan Spec Generator — UCAgent 插件

`xiangshan-spec-generator` 是为 XiangShan 模块生成中文设计与功能检测点文档的 UCAgent 插件。
插件以指定配置的 elaborated RTL、Chisel/Scala 源码和可选输入 spec 为依据，生成版本化文档、质量报告和可追溯证据，并通过证据与完整性检查验收。

工作流为 `xiangshan-spec-generator:design-document`：

1. 核验模块、配置和版本，检查工具环境并生成 RTL/端口 evidence。
2. 按插件模板编写设计文档、质量报告和版本历史。
3. 渲染 Mermaid、同步元数据，由 Checker 执行阶段验收。

## 获取与准备

需要 Python 3.11+ 和支持插件工作流的 UCAgent；在 UCAgent 使用的同一个 Python 环境中安装本插件及其依赖。模型或外部后端按 UCAgent 的常规方式配置。

CI 使用下面的固定 UCAgent 源码提交验证。新环境先安装该版本；已有兼容 UCAgent 的环境可跳过：

```bash
python -m pip install 'UCAgent @ git+https://github.com/XS-MLVP/UCAgent.git@856ee9f9fd68cac09bda2f6495c55d96c6857038'
```

获取插件源码并安装：

```bash
git clone --recurse-submodules https://github.com/XS-MLVP/spec_generator.git
cd spec_generator
python -m pip install -e .
```

已有 clone 执行 `make init` 补齐 XiangShan 子模块。下面的源码启动命令从仓库根目录运行；仅开发插件和运行单元测试时可省略子模块下载。
插件自带执行代码；工作区只需提供 `third_party/XiangShan/` 源码和输入/输出目录。
JDK、Mill、Node.js、Mermaid 等证据工具的准备方法见 [环境准备](#环境准备)。

确定目标模块的 Chisel class、配置及文档版本。可选需求说明放到 `inputs/<Module>/`；实现结论仍需源码和 matching RTL 验证，无法确认的内容保留为 `OPEN-*`。

## 启动工作流

直接从源码目录加载，无需将插件复制到 UCAgent 仓库：

```bash
ucagent --validate-plugin .

SPEC_DOCUMENT_VERSION=v1.0.0 XIANGSHAN_CONFIG=DefaultConfig \
ucagent . Sbuffer \
  --plugin . \
  --plugin-workflow xiangshan-spec-generator:design-document \
  --output outputs/Sbuffer \
  --no-history
```

将 `Sbuffer` 替换为实际模块名。首次版本默认 `v1.0.0`，配置默认 `DefaultConfig`；已有归档时选择更高的新版本。
新任务使用 `--no-history`；恢复当前未完成任务时保留同一版本并省略该选项。

安装后 UCAgent 通过 `ucagent.plugins` entry point 发现插件；发行包名为 `ucagent-xiangshan-spec-generator`，CLI 使用插件 ID `xiangshan-spec-generator`：

```bash
ucagent --list-plugins
ucagent --validate-plugin xiangshan-spec-generator
```

启动命令中的 `--plugin .` 相应替换为 `--plugin xiangshan-spec-generator`，第一个位置参数可改为独立工作区路径，并将 XiangShan clone（含子模块）放到该工作区的 `third_party/XiangShan/`。安装 wheel 后也使用这一入口。安装只提供插件发现信息，生成任务仍需显式选择 `--plugin` 和 `--plugin-workflow`。

## 生成产物

```text
outputs/<Module>/<Module>_design_document_zh_vX.Y.Z.md
outputs/<Module>/VERSION_HISTORY.md
reports/<Module>/<Module>_document_quality_review_vX.Y.Z.md
evidence/<Module>/vX.Y.Z/manifest.json
evidence/<Module>/vX.Y.Z/ports.csv
evidence/<Module>/vX.Y.Z/<Module>.sv
evidence/<Module>/vX.Y.Z/diagrams/manifest.json
evidence/<Module>/vX.Y.Z/diagrams/*.svg
```

仓库根目录中的这些本地工作资产由 `.gitignore` 忽略；独立工作区需自行配置忽略规则。长期保存请使用项目外的制品库或评审系统。
质量报告必须如实记录 `OPEN-*`、RTL 状态及尚未执行的 SVA/formal 检查。

## 环境准备

插件面向 Linux 和 macOS，激活时检查 Bash、Git、Curl 和 Make；生成环境还需要 C compiler。JDK 17 和浏览器优先复用可用安装，否则下载到 `.cache/`；Node.js 22 和 Mermaid CLI 使用缓存中的固定版本，Mill 版本由 XiangShan 源码指定。首次准备工具需要网络访问。

完成环境准备后，在仓库根目录执行 `make init` 初始化子模块，启动后调用 `SpecGeneratorCommand(action="preflight", module="<Module>", config="<Config>")` 检查环境。
环境就绪后，按[启动工作流](#启动工作流)中的命令运行。

### Linux

Debian/Ubuntu：

```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk git curl make build-essential python3 time
```

Fedora/RHEL：

```bash
sudo dnf install -y java-17-openjdk-devel git curl make gcc python3 time
```

Linux x86-64 默认使用 XiangShan 自带 Espresso。Linux ARM64 会由插件内的 `scripts/prepare_espresso.sh` 在 `.cache/` 中构建 native 版本。

### macOS

使用 Homebrew：

```bash
brew install openjdk@17 git curl make python
export PATH="$(brew --prefix openjdk@17)/bin:$PATH"
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
```

不要求安装 GNU `time`。本项目的 RTL wrapper 直接调用 XiangShan 的 Mill entry，并保留 XiangShan 的生成参数。Apple Silicon 和 Intel macOS 都会按主机架构构建 native Espresso。

## 配置与工作区

| 配置 | 默认值 | 用途 |
| --- | --- | --- |
| `SPEC_DOCUMENT_VERSION` | `v1.0.0` | 本次文档版本 |
| `XIANGSHAN_CONFIG` | `DefaultConfig` | XiangShan 配置 class |
| `--output` | 启动时设为 `outputs/<Module>` | UCAgent 输出与历史管理目录；插件文档路径仍固定为生成产物表中的路径 |

可用 `--override template_overwrite.VERSION=v1.1.0` 和
`--override template_overwrite.XS_CONFIG=DefaultConfig` 覆盖前两个值。
同一任务恢复时保持模块、版本、配置一致；新任务使用新版本及 `--no-history`。

工作区可以独立于插件仓库，只需提供已初始化的 `third_party/XiangShan/`（含其子模块）与可选的 `inputs/<Module>/`。
wheel 包含执行代码、脚本和写作资源，不包含 XiangShan 或大型工具链。插件始终使用自身安装目录中的实现，不执行工作区提供的同名脚本。
命令固定使用工作区的 XiangShan 和 `.cache`。工作流允许写入对应模块的 outputs、reports、evidence，以及缓存和 RTL 构建目录；Scala 源码受保护。
生成器可能临时替换 Espresso 二进制，并在退出时恢复。

## 工具

`SpecGeneratorCommand` 接受 `action`、`module`、`config`、`version`。
除 `preflight` 外都需要版本；模块与配置必须是单个标识符，版本格式为 `vMAJOR.MINOR.PATCH`。

| action | 作用 |
| --- | --- |
| `preflight` | 检查模块、配置、子模块及工具环境 |
| `evidence` | 生成 matching RTL 副本、带工具凭据的 manifest 和 ports.csv |
| `render` | 渲染文档中的 Mermaid，生成 SVG 与 manifest |
| `metadata` | 从已核验 evidence 同步事实元数据，可补充版本历史 |
| `validate` | 检查草稿的证据、内容和关键引用 |
| `lint` | 在草稿检查基础上核验当前图形来源与 SVG |

新增历史行的 `metadata` 调用还需要 `change_type`（Major/Minor/Patch）与单行 `summary`。
先生成 evidence 再编写正文；草稿完成后 metadata；最终 render，再 Check。
单次命令上限一小时，执行中有进度反馈，stdout/stderr 有长度上限与截断标识。

三个阶段均有内容门禁：证据阶段重新核对当前 Git commit/子模块状态、配置、真实 RTL hash 和重新解析的端口；草稿阶段检查模板结构、非空产物、当前模板元数据、机器 ID 引用、明确端口声明及本地文件链接；最终阶段再核验 Mermaid 源码与 SVG 的工具凭据和 hash。Check/Complete 只读核验，不重复生成、渲染或修改产物。

设计文档的固定标题、标题层级、章节顺序和每节表格数量必须与模板一致，检查规则直接从唯一模板提取。当前模板共有 14 张表：附录 A、C、F 各 2 张，其余表格所在小节各 1 张；不能只凑齐总数或把表移到其他小节。P-* 行为小节至少 1 项并可重复；正常、边界、恢复场景小节保留，不适用时说明理由，其他 CASE-* 场景在模板指定位置按需添加。表格行数、正文篇幅和图形数量不固定。接口映射覆盖不足、缺少追溯类别、残留 TODO 等给出提醒；作者需完善或在质量报告中解释适用范围。自动检查通过不等于语义完整、SVA 编译或 formal 已通过。

`metadata` 在设计文档和质量报告中写入一个 `<!-- spec-generator: {...} -->` 事实记录，并同步存在的常用可见元数据单元格；事实记录不代替模板要求的文档控制表，质量报告和版本历史的排版仍可自行组织。可见模板版本若与当前模板矛盾仍会失败。版本历史可使用表格或列表，已有记录不改写。

`evidence` 恢复时验证已有凭据和文件，不覆盖它们；缓存仅在来源和内容校验通过时复用。实际 RTL 副本保存在 evidence 中，清除 `.cache` 不影响已生成的证据。没有 Mermaid 时，`render` 生成空清单，不启动浏览器。

工具凭据与密钥保存在 evidence 和工作区 `.ucagent/`；保留该运行状态以便恢复。凭据用于识别受信任工具执行及检测产物被修改，不代替操作系统隔离：不要向生成 Agent 开放任意 Shell、修改插件/工具链或读取密钥的能力。源码、插件代码和工具链本身仍是受信任输入。

Makefile 只保留源码维护检查；文档任务由 UCAgent 工作流和插件工具驱动。

## 运行资源

选中 `design-document` 工作流后，包内 `resources/Guide_Doc/generation-guide.md` 复制到工作区的 `Guide_Doc/generation-guide.md`，提供完整生成方法。
唯一模板保存在包内 `resources/Guide_Doc/chip_design_document_template_zh.md`，复制为工作区的同名 Guide_Doc 文件。工作流显式关闭通用输出模板，不再额外复制一份空白骨架。指南说明分析方法，模板定义设计文档结构；两者共同指导写作。

插件未声明 Skill，Skill 开关不影响工作流的任务和验收要求。

## 故障排查

| 现象 | 下一步 |
| --- | --- |
| 模块或配置不存在 | 检查 class 大小写、当前 commit 与 Scala 配置定义 |
| preflight 失败 | 处理首个诊断中的工具、网络、源码状态或子模块问题 |
| evidence 已存在 | 当前任务恢复时读取并核验已有证据；新任务选择新版本 |
| RTL 为 partial | 仅目标模块完整且失败发生在 RTL 生成之后时继续，如实记录下游失败 |
| Mermaid 或端口检查失败 | 根据具体图号、端口名与位宽修复文档，再重新渲染及检查 |
| 标题、顺序或表格数量不符 | 对照诊断给出的章节和模板，恢复固定结构；不要改检查器或复制无关表格凑数 |
| 插件模板缺失 | 恢复包内资源或重新安装插件 |
| 找不到插件或出现同名来源冲突 | 确认 pip 与 ucagent 使用同一 Python 环境；调试源码时用 `--plugin /绝对路径/spec_generator`，避免同时通过搜索路径和安装入口选择同一 ID |
| 仍有 OPEN 项 | 补充所需证据或设计确认，不猜测关闭 |

## 项目结构

插件代码直接放在根目录的 `spec_generator_plugin/` 包中。该目录对应插件入口 `spec_generator_plugin.plugin:get_plugin`，集中保存 Python 模块、执行脚本、资源和仓库检查工具；回归测试放在 `tests/`。源码加载使用项目根目录作为 Python 导入路径，安装包测试采用隔离导入，避免误用仓库中的源码。

```text
README.md                             # 使用说明与模块职责
CONTRIBUTING.md                       # 维护、测试、发布约定
ucagent-plugin.toml                   # 源码入口，python_path = "."
pyproject.toml                       # Python 安装入口、依赖与资源打包
Makefile                             # 维护检查
spec_generator_plugin/
  __init__.py                        # 包与版本
  plugin.py                          # UCAgent 插件声明
  tools.py                           # 模型调用入口
  checkers.py                        # 阶段验收入口
  runtime.py                         # 命令执行与证据生成调度
  evidence.py                        # 源码、RTL、端口与凭据
  documents.py                       # Markdown、模板结构与事实元数据
  validation.py                      # 产物一致性验收
  rendering.py                       # Mermaid 实际渲染
  repository.py                      # 开发维护：仓库文档与打包声明检查
  resources/
    workflows/design-document.yaml
    Guide_Doc/generation-guide.md
    Guide_Doc/chip_design_document_template_zh.md
    metadata-fields.json
  scripts/                           # Bash：环境准备、工具安装和 RTL 编译
tests/                               # 回归测试与完整文档样例
  fixtures/design_document.md        # 合成 RTL 的完整文档测试样例
third_party/XiangShan/                # 输入源码子模块
```

运行时按需创建 `Guide_Doc/`、`.ucagent/`、`.cache/` 和模块产物目录；这些不是维护源文件。

`tests/fixtures/design_document.md` 是与测试用合成 RTL 对应的完整文档，用于检查标题、章节、表格、引用以及阶段验收。Guide_Doc 中的模板定义结构，指南说明写作方法；测试样例独立填写，结构相符但内容服务于测试。样例随测试进入源码包，不进入 wheel，也不会复制到用户工作区。模板结构变更时需同步审阅样例，不能从模板自动生成样例来代替独立验证。

### Python 文件职责

以下路径均相对于 `spec_generator_plugin/`。这些文件共同组成一个插件；通常通过 UCAgent 的工具和阶段运行，无需逐个执行。

| 文件 | 职责与调用关系 |
| --- | --- |
| `__init__.py` | 定义插件包和发行版本。 |
| `plugin.py` | 注册工作流、Guide_Doc、工具工厂、Checker 和依赖；源码与 wheel 使用同一入口。 |
| `tools.py` | 实现 `SpecGeneratorCommand`：校验参数、工作区路径与写权限，启动固定子进程，处理超时和进度，限制返回输出长度。 |
| `checkers.py` | 将三个阶段接到验收函数；阶段启动时补充新生成的参考文件。Check/Complete 本身不生成或改写产物。 |
| `runtime.py` | 接收工具指定的动作，调度预检、RTL 生成、元数据、渲染与验收；验证可复用缓存并保存 RTL、端口和生成凭据。 |
| `evidence.py` | 检查 Git/子模块来源，解析 elaborated RTL 端口，核对 CSV/hash，签发及验证工具凭据；共享工作区路径和 JSON 读取。 |
| `documents.py` | 解析 Markdown 标题、表格和代码块，从模板提取结构要求，管理版本化文件路径，读取模板版本并同步事实元数据/历史记录。 |
| `validation.py` | 组合证据、模板结构、元数据、引用、端口声明和图形检查，向工具及 Checker 返回有限长度的可操作诊断。 |
| `rendering.py` | 调用 Node/Mermaid CLI/浏览器生成 SVG 和图形清单；维护命令 `make template-check` 也使用此实现。 |
| `repository.py` | 开发维护入口，检查当前源码仓库的文档链接、模板资源和打包声明。在项目根目录执行 `make repo-lint` 或 `python -m spec_generator_plugin.repository`。 |

主要调用关系：`SpecGeneratorCommand → runtime → evidence / documents / rendering / validation`；`Check / Complete → checkers → validation`。Bash 脚本只负责外部工具与编译环境，Python 负责产物和工作区约束。

## 更多资料

- [贡献与维护指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)

项目采用 [MIT License](LICENSE)。
