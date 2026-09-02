# Sbuffer 文档质量评审

## 评审范围

对比原始 [Sbuffer_spec.md](../../inputs/Sbuffer/Sbuffer_spec.md)、[SbufferData_spec.md](../../inputs/Sbuffer/SbufferData_spec.md) 与历轮标签化文档，并据此修订当前 [Sbuffer_design_document_zh.md](../../outputs/Sbuffer/Sbuffer_design_document_zh.md) 和[模板](../../templates/chip-design-document/chip_design_document_template_zh.md)。

| 维度 | 原始 AI 文档 | 第二轮结果 | 本轮结果 |
| --- | --- | --- | --- |
| 设计信息完整性 | 4/5：接口、功能与子模块较全。 | 4/5：覆盖数据路径、老化/replay、Difftest、prefetch。 | 4/5：新增独立 I/O、参数、顶层 FSM 和场景案例；准确 Verilog 名仍待产物。 |
| 形式化可生成性 | 1/5：CK 缺 Style、API/Coverage 和观测契约。 | 5/5：58 个 CK 有 Style、说明和观测语义。 | 4/5：62 个 CK 以可见表格呈现；需确认 UCAgent 表格解析规则并绑定真实端口。 |
| 检测点独立性 | 2/5：部分检查点混合多个性质。 | 4/5：补充 frame condition。 | 5/5：四级仲裁拆为三个相邻优先级 CK，response 与存储增加非目标稳定性。 |
| 证据边界 | 2/5：AI 推断与 RTL 事实混写。 | 4/5：登记通用 `OPEN-*`。 | 5/5：I/O、参数、状态、时序和特性分别使用专用 OPEN，禁止猜测 Verilog 名。 |
| 验证覆盖闭环 | 3/5：有测试建议，缺形式化边界。 | 5/5：正常、边界和恢复路径齐全。 | 5/5：保留 cover，并新增四个跨 FC 的 user-story case。 |
| 图形表达 | 1/5：没有结构图。 | 4/5：有总图、状态图和时序图。 | 5/5：总图用 Mermaid `subgraph` 明确 DUT 边界，跨界箭头与 I/O 对象对应。 |

## 当前轮修订

- I/O 改为“顶层/子 Bundle class + Chisel object/field + 精确 elaborated Verilog port”逐层映射。当前缺少 Scala 和 Verilog，统一登记 `OPEN-IO-001/002`，未猜测扁平端口名。
- 参数移至独立章节，强制列出 Scala 声明位置、使用位置和生效时机；缺失源码位置由 `OPEN-PARAM-001` 管理。
- 顶层状态机移至独立章节，状态表和 Mermaid 状态图同节；entry 生命周期不再混入顶层状态表。
- 微架构图使用 `subgraph DUT["DUT: Sbuffer"]`，所有跨界箭头标注 I/O 章节中的 Chisel object，并等待 Verilog 端口回填。
- 每个 FC 均先给自然语言描述，再用 FC 表和 CK 表表达标签、触发、结果、边界、Style、观测点与依据。
- FG/FC/CK 标签使用反引号包裹的尖括号文本，例如 `` `<FC-INSERT>` ``，Markdown 页面可见，不再被当作 HTML 隐藏。
- 仲裁优先级拆成三个独立 CK；增加 reset/input API、存储/response frame condition 和 feature-disable 检查。
- 附录新增首次写回、同址合并前递、replay 重试和 flush 排空四个 user-story case。
- 静态复核结果：9 个 FG、18 个 FC、62 个 CK；每个 FC 有自然语言、FC 表和 CK 表。Mermaid 源码包含 DUT subgraph、顶层状态图和事务时序图。

## 结论

当前版本适合作为设计/DV 评审草案，但在关闭 `OPEN-IO-002` 前不能宣称 Verilog I/O 准确，也不能直接完成属性 bind。另需确认 UCAgent 已支持表格中的可见反引号标签；通过标签 checker 后，才可作为属性生成输入。
