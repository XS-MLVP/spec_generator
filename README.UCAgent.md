
# UCAgent 插件

本项目提供 `xiangshan-spec-generator` 插件和
`xiangshan-spec-generator:design-document` 工作流。插件复用仓库已有脚本与严格检查，
生成设计文档、质量报告、版本历史、RTL/端口证据和 Mermaid SVG。

## 源码方式运行

使用支持插件工作流的 UCAgent，在 spec_generator 仓库根目录执行：

```bash
ucagent --validate-plugin .
SPEC_DOCUMENT_VERSION=v1.0.0 XIANGSHAN_CONFIG=DefaultConfig \
ucagent . Sbuffer \
  --plugin . \
  --plugin-workflow xiangshan-spec-generator:design-document \
  --output outputs/Sbuffer
```

将 `Sbuffer` 替换为目标 Chisel 模块名。`SPEC_DOCUMENT_VERSION` 是文档版本，默认
`v1.0.0`；已有归档时选择更高的新版本。`XIANGSHAN_CONFIG` 默认 `DefaultConfig`。
也可用 `--override template_overwrite.VERSION=v1.1.0` 和
`--override template_overwrite.XS_CONFIG=DefaultConfig` 覆盖。
新文档任务应使用 `--no-history`，避免恢复上一文档版本的阶段进度；恢复当前未完成任务时省略该选项。

工作区必须是完整的 spec_generator 仓库，包含 `tools/`、`templates/` 和初始化后的
`third_party/XiangShan/`，不是任意空目录。初始化及工具环境准备见 [README](README.md)。
插件通过现有脚本按需准备 JDK、Mill、Node/Mermaid 等工具，可能联网下载并运行较长时间；
插件安装本身不包含 XiangShan 或这些工具。

## 安装方式

在 UCAgent 所用 Python 环境中安装：

```bash
python -m pip install -e .
ucagent --validate-plugin xiangshan-spec-generator
ucagent . Sbuffer --plugin xiangshan-spec-generator \
  --plugin-workflow xiangshan-spec-generator:design-document \
  --output outputs/Sbuffer
```

安装后可以用插件 ID 加载；执行工作区仍须是 spec_generator 仓库。

## 工作流与接口

1. 核验模块、配置和版本，运行 preflight，生成并阅读 matching RTL 与端口 evidence。
2. 按完整模板编写版本化文档、质量报告和历史记录。
3. 渲染 Mermaid，同步元数据，由 `SpecGeneratorArtifactsChecker` 实际运行严格 lint。

`SpecGeneratorCommand` 提供 `preflight`、`evidence`、`render`、`metadata`、`validate`、
`lint` 六种 action，参数为 `module`、`config`、`version`。
新增历史行的 `metadata` 调用还需 `change_type`（Major/Minor/Patch）和单行 `summary`。
命令输出有长度上限，执行中提供进度；单次命令上限为一小时。
子命令使用当前工作区的 XiangShan 和 `.cache`，不会采用外部 `XIANGSHAN_ROOT` 或
`TEMPLATE_GENERATE_CACHE` 路径。工作流允许现有生成器写缓存、构建产物及临时替换后恢复
Espresso 资源，Scala 源码保持受保护。

Guide_Doc 包含完整生成方法与模板；Skill 只是可选检查清单。
`--no-use-skill` 时同样可以生成和验收，验收标准不变。
若只需 Tool/Checker，可仅使用 `--plugin` 而不选择工作流；自定义配置需明确允许相关
outputs、reports、evidence、.cache 及 RTL 构建目录写入。

## 维护与验证

插件入口在 `src/spec_generator_plugin/plugin.py`，工作流位于
`src/spec_generator_plugin/resources/workflows/design-document.yaml`。
原有模板和 OpenCode Skill 仍是生成格式/方法的维护来源。修改后同步发布资源：

```bash
python3 tools/sync_ucagent_resources.py
PYTHONPATH=src python -m pytest -q
ucagent --validate-plugin .
python -m pip wheel . --no-deps --wheel-dir dist
```

wheel 包含工作流、Guide_Doc、模板和可选 Skill。测试不触发真实 RTL elaboration 或工具下载；
实际模块交付仍须通过工作流最后的严格 lint。
