# 源码与 RTL 分析

先确定 DUT 顶层和配置，再递归检查 Bundle、IO、Flipped 方向、Decoupled/Valid 协议、子模块、参数、寄存器、队列/阵列、仲裁、计数器、flush/replay/error 和 feature gate。区分顶层 FSM 与 entry 生命周期、子模块 FSM、协议临时状态。

建立事务模型：发起条件、接受条件、payload、ID/配对、处理路径、完成/取消、响应时延、顺序、背压和非目标稳定性。将实现事实与 spec 意图分开记录；冲突不静默裁决。

端口映射同时记录 Chisel 层级和指定配置下的精确 RTL 叶端口、方向、位宽、Generated/Elided 状态及来源。规则数组只有在 RTL 展示连续命名和索引范围时才能使用模式表示。
