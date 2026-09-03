# 证据与追溯

实现事实依次以 matching elaborated Verilog/SystemVerilog、Chisel/Scala、配置和生成命令、可选 spec 为依据。Verilog 端口名不得从 Chisel 名称推测；Chisel 存在但被配置裁剪的字段标为 `Elided` 并说明原因。无法核验的端口、参数、时延、行为或设计意图建立 `OPEN-IO-*`、`OPEN-PARAM-*`、`OPEN-BEHAV-*` 或其他具体 OPEN。

设计文档、质量报告、VERSION_HISTORY 和 evidence 使用同一文档版本；模板结构版本单独记录。每次生成创建新版本，禁止覆盖已有版本。质量报告记录基线 commit、配置、工具、生成状态、RTL/diagram hash、校验命令、未运行检查和 OPEN 关闭所需证据。

CK 追溯矩阵、Sign-off 表和 Case 引用必须指向文档中存在的 ID。重排旧文档时可生成 baseline 差异报告，报告新增、改变、合并、拆分和移除的 ID，但不以计数变化直接判失败。
