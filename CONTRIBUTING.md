# Contributing

本指南主要面向共同维护和优化文档模板、通用 Skill 及其自动检查工具的开发者。使用现有工具生成某个模块文档，请直接阅读 [README.md](README.md) 的“为一个模块生成 Spec 文档”。

## 维护对象

| 对象 | 路径 | 职责 |
| --- | --- | --- |
| 文档模板 | `templates/chip-design-document/chip_design_document_template_zh.md` | 定义交付文档的章节、字段、表格和标签 schema。 |
| 通用 Skill | `skills/chip-dv-spec/SKILL.md` | 平台无关的任务入口、生成流程和硬约束。 |
| Skill references | `skills/chip-dv-spec/references/` | 文档格式、DV/Testplan、证据及项目 profile。 |
| 平台适配 | `.{opencode,claude,codex}/skills/chip-dv-spec` | 指向通用 Skill 的发现入口，不维护规则副本。 |
| 文档检查器 | `tools/validate_document.py` | 检查单个模块版本的结构和 evidence。 |
| 仓库检查器 | `tools/validate_repository.py` | 检查跨模块链接、manifest 和模板约束。 |
| RTL/图形工具 | `tools/generate_rtl.sh`、`extract_rtl_evidence.py`、`validate_mermaid.py` | 产生可复现 evidence。 |
| FM-Agent 包装器 | `tools/generate_fm_specs.py`、`make fm-spec` | 从 `rtls/<Module>/` 生成并同步硬件子模块规约。 |
| 模板迭代记录 | `reports/template/Template_iteration_review.md` | 记录问题、决策、模板版本和回归结果。 |

模板规定“输出长什么样”，Skill 规定“AI 如何得到正确输出”，checker 负责“把关键规则变成强制门禁”。修改其中一个时，必须评估另外两个是否需要同步。

## 不可破坏的契约

- 实现事实的证据优先级保持为：matching elaborated RTL > Chisel/Scala > 配置 > 可选 spec > 显式推断。
- 无法证实、来源冲突或疑似 RTL 缺陷必须登记为 `OPEN-*`，不能写成 FACT。
- I/O 必须区分 Chisel 声明与当前配置的 `Generated`/`Elided` Verilog 结果。
- 顶层状态机章节不能混入 entry 生命周期或子模块 FSM。
- `FG-API` 只能包含 Assume，`FG-COVERAGE` 只能包含 Cover。
- 已生成的每个 FC 必须有自然语言、FC 表和独立 CK；条目数量由 DUT 行为决定。
- Mermaid 必须真实渲染，并以 source/SVG hash 防止使用过期证据。
- 历史文档和 evidence 不得在普通迭代中被覆盖。
- 不修改 XiangShan submodule 源码来迁就文档生成工具。
- FM-Agent 使用 `third_party/FM-Agent` 固定 submodule；不要从仓库外路径或未记录 commit 生成输入规约。
- FM-Agent 可能运行 20–30 分钟或更久；文档和 Skill 必须说明长时任务、日志位置、真实退出码和 `--resume` 恢复方式，不得用固定短超时杀掉进程。

## 模板版本

模板顶部的 `模板结构版本` 与模块文档版本独立，使用 SemVer：

| 增量 | 模板变化示例 |
| --- | --- |
| Major | 删除/重命名必选章节，改变 FG/FC/CK 解析结构，修改表格到旧生成器无法兼容。 |
| Minor | 增加兼容字段、条件章节或新的可选/必选检查要求。 |
| Patch | 增加 HTML 维护注释、修正文案或示例，不改变输出 schema。 |

升级模板版本时必须：

1. 更新模板顶部 `模板结构版本`。
2. 更新模板“文档控制与依据”中的 `使用模板版本` 示例。
3. 在 `Template_iteration_review.md` 说明问题、改动、兼容性和回归结果。
4. 判断已有模块是否需要生成新文档版本；不要追溯修改历史版本记录的模板号。

## Skill 修改原则

Skill 必须说明可执行工作流，而不是重复模板全部正文。重点维护：

- 触发场景、仓库路径和完整交付物。
- 证据优先级与冲突处理。
- preflight、RTL elaboration、缓存和 evidence 规则。
- 文档 SemVer 选择及禁止覆盖历史。
- Bundle/I/O、参数、FSM、FG/FC/CK 和 case 的提取方法。
- Mermaid 安全写法与真实渲染要求。
- 质量报告内容、checker 命令和完成标准。

新增模板硬规则时，应同步回答：

1. Skill 是否告诉 AI 如何满足它？
2. checker 是否能自动发现违反规则的情况？
3. quality report 是否记录了对应结果或未运行项？

修改 Skill 后需要重启会缓存 Skill 的 Agent 会话，再进行真实生成回归。

## 开发流程

### 1. 建立分支和基线

```bash
git switch -c <topic-branch>
make init
make fm-spec MODULE=<Module>
make preflight MODULE=Sbuffer CONFIG=DefaultConfig
python3 tools/validate_repository.py
```

记录修改前的检查结果。不要把已有失败归因于本次改动。

### 2. 做最小一致修改

- 先修改当前模板，明确是 schema 变化还是说明变化；生成器不维护历史模板分支。
- 再同步 Skill 的生成步骤和完成标准。
- 能自动检查的新规则应加入 checker，避免只依赖提示词。
- 跨平台逻辑必须同时考虑 Linux/macOS 和 x86-64/ARM64。
- 不提交 `.cache/`、XiangShan build、凭据、私有路径或 IDE 状态。

### 3. 使用回归模块验证

Sbuffer 是当前模板和 Skill 的基准回归模块。至少执行：

```bash
# 模板自身 Mermaid 示例
rm -rf .cache/mermaid-check/template
./tools/validate_mermaid.py \
  --document templates/chip-design-document/chip_design_document_template_zh.md \
  --output-dir .cache/mermaid-check/template

# 对本次新生成、使用当前模板的模块文档执行
make lint MODULE=<Module> VERSION=<vX.Y.Z>
git diff --check
```

若改动会影响生成结果，应使用新文档版本完整重生成回归模块，而不是改写旧版本或要求历史 schema 通过当前 validator。确认：

- 设计文档、质量报告、VERSION_HISTORY 和 evidence 版本一致。
- RTL commit/config/hash 未变化时，质量报告明确说明。
- FG/FC/CK 的新增、删除或语义变化有行为与证据依据，不按固定数量验收。
- 所有 Mermaid SVG 可渲染且 source hash 最新。
- XiangShan submodule 保持 clean。

### 4. 更新迭代记录

在 `reports/template/Template_iteration_review.md` 记录：

- 原问题和可复现方式。
- 模板、Skill、工具分别如何处理。
- 模板版本及兼容性判断。
- 使用了哪些回归模块和命令。
- 尚未覆盖的风险。

## Pull Request 要求

PR 应聚焦一个模板或 Skill 问题，并说明：

- 修改动机及失败示例。
- 模板版本变化及 SemVer 理由。
- 模板、Skill、checker 是否同步；未同步时说明原因。
- 对已有文档和 UCAgent 解析的兼容性影响。
- Linux/macOS 相关影响。
- 回归命令和实际结果。
- 是否生成了新的模块回归文档/evidence。

使用仓库 PR 模板，并确保：

- `git diff --check` 通过。
- 模板 Mermaid 示例实际渲染成功。
- `make lint MODULE=<Module> VERSION=<current-schema-version>` 通过。
- 敏感信息、缓存和 submodule build 未进入提交。

## 提交信息

使用简洁的祈使句描述维护动作，例如：

```text
Clarify formal harness guidance
Add Mermaid rendering validation
Update template I/O mapping schema
```
