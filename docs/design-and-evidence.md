# 设计与证据模型

本文说明 XiangShan Spec Generator 的内部工作原理和文档协议。日常使用请从项目 [README](../README.md) 开始。

## 生成原则

项目将设计意图、实现事实和待确认问题分开处理：

1. 同 commit、同配置生成的 elaborated SystemVerilog 用于确认最终模块、扁平端口和位宽。
2. Chisel/Scala 用于确认 Bundle、参数、状态机、更新规则、优先级和特性门控。
3. 配置与生成命令用于确认最终参数和启用特性。
4. `inputs/<Module>/` 中的 spec 用于理解设计意图、术语和候选场景。
5. 无法由以上证据闭合的推断登记为 `OPEN-*`。

输入 spec 与 RTL 冲突时，文档分别记录意图和实际行为，不用较低优先级材料覆盖实现。

## 文档结构

模板把内容分为三层：

- **正文**：先建立生产者、消费者、关键概念和数据流，再按 `P-*` 规则解释行为。正文使用逻辑接口名和 `[E-*]` 证据编号。
- **验证计划**：用 Test Plan、Coverage Design Contract、场景和属性契约连接 FC、CK 与关闭条件。
- **附录**：保存精确端口、参数、配置裁剪、证据位置、FACT/OPEN、FC/CK 注册和签核状态。

每项行为只有一个权威 `P-*` 定义。FC、CK、Coverage 和 Case 引用规则 ID，不在同一抽象层重复机制。

## I/O 与证据

Chisel 字段存在不代表它一定出现在最终 Verilog。配置关闭、常量传播和 dead-port elimination 都可能产生 `Elided` 字段。

精确 Verilog 名称必须来自 matching elaboration，不能按 Chisel 命名猜测。严格检查器会展开附录中的端口模式，并与 `ports.csv` 双向比较名称、方向和位宽。

Mermaid 图必须经过真实 parser 和浏览器渲染。diagram manifest 保存源 hash、SVG hash 和渲染器版本，以识别过期图片。

## 验证模型

`FG-API` 只包含环境 Assume，不能假设 DUT 输出正确；`FG-COVERAGE` 只包含 Cover。每个 CK 只验证一个性质，并在附录维护独立的属性实现状态：

- `Illustrative`：代表性公式。
- `Planned`：已定义 CK，尚无完整公式。
- `Generated`：已有逐 CK 公式。
- `Compiled`：属性和 bind 已编译。
- `Proved`：Assert/Assume 已完成目标证明。
- `Covered`：Cover 已命中。

Coverage 基于 DUT 输出、完成事件、状态转换或 scoreboard 确认的事务采样，不能仅根据“已经发送激励”计数。每个 Coverage 项明确重要值、有限分箱、必要交叉、非法/忽略条件、有效性保护和关闭对象。

## 版本与本地资产

模块文档版本与模板版本相互独立：

- Major：DUT 范围、身份或文档 schema 不兼容变化。
- Minor：接口、参数、状态、行为或验证覆盖发生语义变化。
- Patch：证据、OPEN、措辞、图形或格式变化，行为契约不变。

每次生成创建新版本，不覆盖历史文档或 evidence。RTL 缓存按 commit、配置、生成参数、工具和平台形成 fingerprint，可供相同配置的多个模块复用。

`inputs/`、`outputs/`、模块级 `reports/` 和 `evidence/` 被 `.gitignore` 排除。它们仍构成本地文档版本，应由使用者在项目外归档。工具仓库只维护模板、Skill、脚本、通用文档和经许可的参考资料。

## 检查边界

`make repo-lint` 只检查仓库自有文件，不读取用户模块资产。`make lint MODULE=<Module> VERSION=<version>` 对指定本地模块执行 Mermaid 重渲染、版本一致性、标签追溯、端口/evidence 和链接检查。

静态检查是最低门禁，不等于 UCAgent 解析、SVA 编译或 formal prove/cover 已完成。未运行的工具必须在质量报告和签核状态中明确保留。
