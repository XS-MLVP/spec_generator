
# 插件维护指南

本项目维护一个 UCAgent 插件。安装、环境、工具接口和 Python 模块职责统一见 [README](README.md)。

## 维护位置

| 内容 | 唯一维护位置 |
| --- | --- |
| 插件身份与能力 | `ucagent-plugin.toml`、`pyproject.toml`、`spec_generator_plugin/plugin.py` |
| 工作流与阶段要求 | `spec_generator_plugin/resources/workflows/design-document.yaml` |
| 完整生成方法 | `spec_generator_plugin/resources/Guide_Doc/generation-guide.md` |
| 文档模板 | `spec_generator_plugin/resources/Guide_Doc/chip_design_document_template_zh.md` |
| 工具与验收入口 | `spec_generator_plugin/tools.py`、`checkers.py` |
| 证据及校验实现 | 插件包内 `runtime.py`、`evidence.py`、`validation.py`、`documents.py`、`rendering.py`、`scripts/` |
| 仓库维护检查 | `spec_generator_plugin/repository.py`，通过 `make repo-lint` 调用 |
| 回归测试 | `tests/` |

直接编辑插件资源。模板源文件作为 Guide_Doc 写作参考，运行时复制到工作区；无需维护副本或执行资源同步脚本。
工作区中的 `Guide_Doc/` 和 `.ucagent/` 是运行产物，不是维护源文件。

## Git 管理范围

根目录的 `inputs/`、`outputs/`、`reports/`、`evidence/`、`Guide_Doc/`、`.ucagent/`、`.cache/`、构建产物和本地配置由 `.gitignore` 忽略。目录规则限定在仓库根目录，包内资源和 `tests/fixtures/` 中的同名样例仍可提交；Python 字节码和安装元数据在各级目录均忽略。Mermaid/Node 工具缓存位于 `.cache/`，无需另设 Node 项目规则。

XiangShan 是独立 Git 子模块，其文件和忽略规则由子模块管理。自定义输出路径或独立工作区应配置各自的忽略规则；个人路径也可写入 `.git/info/exclude`。`.gitignore` 不会移除已跟踪文件，提交前用 `git status --short` 查看实际变更，用 `git check-ignore -v --no-index <路径>` 排查规则。

## 修改规则

工作流描述目标与步骤，Guide_Doc 描述完整方法，模板定义固定标题、层级、顺序和各节表格数量，Checker 校验关键约束。修改字段或硬性行为时，同步更新受影响的协议层与测试。

- 模板版本使用 SemVer：不兼容结构改动升 Major，兼容字段升 Minor，注释或措辞升 Patch；插件发行版本与模板版本分别维护。
- 实现事实保持 `matching RTL > Chisel/Scala > 配置 > 可选 spec > 显式推断` 的证据顺序。
- 不修改 XiangShan submodule 来迁就文档工具。
- 运行说明使用 `SpecGeneratorCommand`、`Check` 和 `Complete` 等实际接口。
- `inputs/`、`outputs/`、模块级 `reports/`、`evidence/`、缓存和运行状态不提交。
- Python 运行与开发依赖统一声明在 `pyproject.toml`；源码归档范围由 `MANIFEST.in` 定义。
- 本次改动的原因与验证结果记录在提交或 PR 中；产物目录只保存本地任务结果。

## 产物设计与验收约定

完整生成要求以 [Guide_Doc](spec_generator_plugin/resources/Guide_Doc/generation-guide.md) 和
[文档模板](spec_generator_plugin/resources/Guide_Doc/chip_design_document_template_zh.md) 为准。维护时须保持以下关系：

- 正文建立生产者、消费者和数据流模型；验证计划把 FC、CK、Coverage 与关闭条件连接起来；附录保存精确端口、参数、证据和签核状态。每项行为只定义一个权威 `P-*`，其余内容引用该 ID。
- 精确 Verilog 端口必须来自同 commit、同配置的 elaborated RTL。Chisel 字段可能因配置或优化而被裁剪；检查器从实际 RTL 重新提取端口，与 `ports.csv` 核对；文档中的明确端口声明不得与之矛盾，未映射端口给出提醒。
- Mermaid 必须实际渲染，diagram manifest 中的源 hash 和 SVG hash 必须与当前文档及图片一致。
- `FG-API` 只声明环境 Assume，`FG-COVERAGE` 只声明 Cover。每个 CK 对应一个性质；Coverage 采样应基于观察结果或已确认的事务。
- 属性状态区分 `Illustrative`、`Planned`、`Generated`、`Compiled`、`Proved`、`Covered`。格式检查通过不能代替 SVA 编译或 formal 证明；未执行项保留未签核状态。

模块文档版本与模板版本分别维护：范围或 schema 不兼容变化升 Major；接口、行为或覆盖的语义变化升 Minor；证据、措辞和格式变化升 Patch。新任务创建新版本，不覆盖历史文档或 evidence；RTL 缓存只在 commit、配置、参数、工具及平台指纹匹配时复用。

仓库检查只处理维护源文件。模块的最终验收由工作流核验模板结构、证据、引用和图形，并将真实结果写入对应质量报告；不确定的实现结论保留为 `OPEN-*`。

## 开发与验证

在 UCAgent 的 Python 环境中安装开发依赖；新环境先按 [README 的获取与准备](README.md#获取与准备)安装已验证的 UCAgent 版本：

```bash
python -m pip install -e '.[dev]'
make repo-lint
make plugin-check
make test
make template-check
git diff --check
```

`make test` 使用临时工作区验证命令、权限、实际 Agent 初始化、Check/Complete 和模板来源，不触发真实 RTL elaboration。
`make template-check` 使用真实 Mermaid CLI 与浏览器渲染唯一模板中的示例图，可能首次下载工具。
CI 在 Linux/macOS 上先安装固定源码版本的 UCAgent，再验证源码插件和 wheel。测试使用临时源码夹具，因此 CI 不拉取 XiangShan 子模块；实际 RTL 生成任务仍需执行 `make init`。更新 UCAgent 验证版本时，同时更新工作流和 README 中的提交号。
如果修改影响文档产物，按 README 的插件启动命令选一个本地模块和新版本回归；最后检查质量报告和完整 lint 结果。

资源修改后重新启动 UCAgent，使工作区重新获得当前插件的指南。不要编辑旧工作区副本来代替源代码修复。

插件清单、entry point 和 provider 必须使用同一 ID，包版本与 provider 版本一致。Python 依赖同时维护在 `pyproject.toml` 和 provider 中；Bash、Git、Curl、Make 在激活时检查，RTL 工具链由 `preflight` 检查。回归覆盖路径加载、搜索路径发现、工具参数和权限、MCP schema、Checker 阶段生命周期，以及 Skill 启用/禁用两条路径。

## 打包

```bash
python -m build
python -m pip install --force-reinstall --no-deps dist/*.whl
ucagent --validate-plugin xiangshan-spec-generator
python -I -m pytest -q --import-mode=append -o pythonpath=''
```

wheel 必须包含插件代码、执行脚本、工作流、完整 Guide_Doc 和唯一模板；sdist 还包含维护文档、测试和独立文档样例。
上述安装验证在已安装 UCAgent 和开发依赖的临时 Python 环境中执行，`dist/` 中只保留本次版本的 wheel。默认构建从 sdist 生成 wheel；隔离测试确保加载安装包。测试还会在没有插件源码或仓库维护文件的临时工作区验证运行命令；XiangShan 与大型工具链不随包发布。完成后需继续源码开发时，重新执行 `python -m pip install -e '.[dev]'`。

提交前确认版本、资源声明、说明和回归测试一致，提交信息使用简洁的祈使句。

## 方法来源

Coverage 方法参考 Verification Academy《Coverage Cookbook》（2013-08-21 快照）中观察点、有效采样、分箱、交叉、命名和覆盖闭合的表达方法；适用原则统一维护在[生成指南的 Coverage Practice Principles](spec_generator_plugin/resources/Guide_Doc/generation-guide.md#coverage-practice-principles)。

引入外部方法时记录来源和用途，遵守许可与再分发条件；不得大段复制原文、图表或示例代码到模板和生成文档。安全与保密规则见 [SECURITY.md](SECURITY.md)。
