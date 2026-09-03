# DV 与 Testplan 写法

验证策略说明 driver、monitor、checker、scoreboard、reference model、assertion、coverage model、formal harness 和 regression 的职责，以及 transaction 从输入到输出的采样点。

FG 按验证目标分组，FC 描述一个可审查的功能契约，CK 描述一个独立可实现的检查。每个 FC 应有自然语言说明和表格，包含目标、触发/前置条件、DUT 处理、可观察结果、边界和检查机制。每个 CK 包含唯一 ID、Style、单一性质、观察点和来源证据。数量由 DUT 行为决定，不按示例凑数。

Style 使用当前模板允许的枚举。Assume 仅用于环境合法性；Assert/Seq 检查 DUT 行为；Cover 检查正常、边界和恢复路径可达性。跨周期属性给出采样时刻、延迟来源和 frame condition；优先级链拆成相邻优先级性质；多 entry/多 lane 更新同时检查目标正确性和非目标稳定性。

Case 用于说明多个 FC/CK 如何协作，不替代 CK。仅在 DUT 存在相应事务或风险时生成正常、资源边界、错误/恢复场景；每个已有 Case 采用统一字段：参与者、前置条件、输入、预期输出、步骤、关联 FC/CK、异常分支和可判定验收标准。
