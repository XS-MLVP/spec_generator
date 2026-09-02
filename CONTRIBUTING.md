# Contributing

## 开发原则

- 实现事实以同 commit、同配置的 elaborated RTL 和 Chisel/Scala 为准。
- 可选 spec 用于补充意图，不能覆盖源码证据。
- 无法证实、来源冲突或疑似 RTL 缺陷必须登记为 `OPEN-*`。
- 不修改 `third_party/XiangShan` 来迁就文档生成；需要兼容处理时修改本仓库工具。
- `.cache/` 可删除，`evidence/` 必须随对应文档版本提交。

## 新模块

为 `<Module>` 增加文档时使用以下目录：

```text
inputs/<Module>/
outputs/<Module>/
reports/<Module>/
evidence/<Module>/<version>/
```

输入 spec 可省略，设计文档、质量报告、版本历史和 evidence 不可省略。

## 推荐流程

1. 初始化并检查环境：

   ```bash
   make init
   make preflight MODULE=<Module> CONFIG=<Config>
   ```

2. 检查 `outputs/<Module>/VERSION_HISTORY.md`，按 SemVer 选择未占用版本。

3. 创建 RTL evidence：

   ```bash
   make evidence MODULE=<Module> CONFIG=<Config> VERSION=<version>
   ```

4. 使用 `xiangshan-design-document` Skill 生成同版本设计文档、质量报告和版本历史。

5. 实际渲染 Mermaid 并运行完整检查：

   ```bash
   make render MODULE=<Module> VERSION=<version>
   make lint MODULE=<Module> VERSION=<version>
   ```

## 版本规则

| 增量 | 使用条件 |
| --- | --- |
| Major | DUT 范围或文档 schema 出现不兼容变化。 |
| Minor | 接口、参数、状态、功能、FC/CK 或支持配置发生语义变化。 |
| Patch | 证据、OPEN 项、措辞、链接、图形或格式变化，行为契约不变。 |

模板结构版本与模块文档版本独立。生成文档必须记录所使用的模板版本。

历史版本不可覆盖。`--replace-evidence` 只能用于修复客观错误，并必须在新质量报告中记录原因。

## Pull Request 检查

- 说明受影响模块、文档版本、XiangShan commit 和配置。
- 说明 spec 与源码的冲突及新增/关闭的 `OPEN-*`。
- 提交设计文档、同版本质量报告、版本历史、RTL manifest/ports 和 Mermaid evidence。
- 确认 XiangShan submodule clean；若更新 gitlink，解释升级原因和影响。
- 执行 `git diff --check` 和对应版本的 `make lint`。
- 不提交 `.cache/`、submodule build、凭据、私有路径或本地 IDE 配置。

## 提交信息

使用简洁的祈使句，说明实际变化，例如：

```text
Add ICache design document v1.0.0
Fix Mermaid rendering validation
Update XiangShan submodule baseline
```
