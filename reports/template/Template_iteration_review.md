# 模板必选性与双 DUT 迭代评审

## 本轮问题与修订

| 发现 | 对 Sbuffer 的影响 | 对 ICache 的影响 | 模板修订 |
| --- | --- | --- | --- |
| 使用者无法判断何时可删除缓存、存储、flush 或特性章节。 | 容易错误保留 `CACHE-PATH`，或遗漏 DCache/flush 事务契约。 | 容易遗漏 MSHR/refill、异常和 ECC 控制平面。 | 新增“文档范围裁定”，将项目分为必选、条件必选和可选。 |
| 端口总览不足以支持协议 SVA。 | 需关联 DCache request/response ID 和 replay。 | 需关联 MSHR ID、2-beat grant、IFU 及 CtrlUnit。 | 新增“接口字段与响应关联”条件必选章节。 |
| 注释要求不明确，模板容易被剪裁为只剩标签。 | 可能失去 harness 延迟与 OPEN 边界。 | 可能失去 grant/flush 同周期的细节。 | 在每个章节前加入 HTML 注释，标明 REQUIRED / CONDITIONAL REQUIRED / OPTIONAL。 |
| 静态图片占位符无法随文档自动演进。 | 文本箭头图难以审阅数据、前递和写回的交叉关系。 | 流水、MSHR 与 flush 关系需要可维护图表达。 | 用必选自动生成总图替换 SVG 占位符，并对 FSM/跨模块事务增加条件必选状态图/时序图。 |

## 生成结果评估

| 质量维度 | Sbuffer | ICache | 结论 |
| --- | --- | --- | --- |
| 范围裁定 | 6 个条件项均明确应用或不适用。 | 6 个条件项均明确应用或不适用。 | 通过。 |
| 设计信息 | 覆盖 enqueue、data、写回、replay、forward、drain、可选 trace。 | 覆盖预取、WayLookup、hit/miss/refill、异常、flush、ECC。 | 与原文关键行为一致；未知实现登记 OPEN。 |
| UCAgent 结构 | API/Coverage、Style、Symbolic 数据检查齐全。 | API/Coverage、Style、Symbolic array 检查齐全。 | 通过静态格式检查。 |
| 可生成性 | 协议 ID、延迟参数和观察点明确。 | MSHR/grant 关联、2 beat、array 镜像和公平性明确。 | 需真实 RTL/harness 才可编译属性。 |
| 图形表达 | 总图、状态图、DCache hit/replay/flush 时序图齐全。 | 模板可据模块流水与 MSHR 事务生成相应自动生成图。 | 图源静态检查通过；待目标 Markdown 渲染器实际渲染。 |

## 结论

此版本可作为后续 DUT 文档的交付模板：必选项保证 UCAgent 最小可用性和自动生成总图，条件必选项防止状态机、缓存、队列和恢复逻辑被无意遗漏。下一步应在目标 Markdown 平台渲染图源，并以真实 RTL 运行 UCAgent checker 和属性编译来反馈模板。

## 2026-09-01 结构化交付修订

| 评审意见 | 模板修订 | Sbuffer 落地 |
| --- | --- | --- |
| I/O 需同时给出 Chisel 与准确 Verilog 定义。 | 新增顶层 Bundle 与逐字段映射表，强制 Bundle class、Chisel object、Scala 位置和 elaborated Verilog 端口。禁止猜测端口名。 | 已列规格可确认的子 Bundle；因缺源码/Verilog，以 `OPEN-IO-001/002` 阻塞签核。 |
| 参数需独立并标明 Scala 位置。 | 新增独立“参数定义”和“形式化 Harness 参数”。 | 参数与资源/状态分离；Scala 位置待 `OPEN-PARAM-001` 关闭。 |
| 状态只列顶层状态机，表和图同节。 | 新增独立“顶层状态机”，明确排除 entry/子模块状态。 | 四态 `sbuffer_state` 表与 Mermaid 图已合并。 |
| 微架构图需明确 DUT 边界。 | 强制 Mermaid `subgraph DUT[...]`，跨界箭头须对应 I/O 表。 | Store Queue、DCache、Load、flush、CSR/prefetch 交互均跨明确边界。 |
| FC 要有自然语言，FC/CK 用表格且标签可见。 | 规定自然语言 + FC 表 + CK 表；标签用反引号包裹。 | 18 个 FC 和 62 个 CK 已按新结构重排。 |
| 增加场景视角案例。 | 新增必选附录及 user-story 模板。 | 增加正常写回、合并前递、replay 重试和 flush 排空案例。 |

本轮剩余阻塞不是文档排版问题，而是输入资产缺失：必须取得 Scala 源码和指定配置的 elaborated Verilog，才能满足“Verilog I/O 必须准确”和参数源码定位要求；在此之前不得用命名惯例补全。

## 2026-09-01 跨平台工具链修订

| 问题 | 修订 | 验证 |
| --- | --- | --- |
| XiangShan Makefile 假设 GNU `time`，macOS 无法直接运行。 | `tools/generate_rtl.sh` 直接调用同参数 TopMain，不依赖 GNU time。 | Darwin/arm64 完整生成 Sbuffer RTL，exit code 0。 |
| Java、Mill 和 Espresso 依赖因 OS/架构不同而失败。 | 自动 bootstrap Temurin JDK 17 和 XiangShan pin 的 Mill；Linux x86-64 用 bundled Espresso，其他平台构建固定 commit 的 native Espresso。 | `preflight --strict` 零错误；submodule 与资源 hash 保持 clean。 |
| build 目录清理后 Verilog 证据丢失。 | 新增 `evidence/<Module>/<version>/manifest.json` 与 `ports.csv`，缓存键包含 commit/config/flags/tool/platform/wrapper。 | Sbuffer v1.0.0 保存 166 个端口和 RTL SHA-256。 |
| 静态检查依赖一次性命令。 | 新增模块无关 `validate_document.py`，检查版本、标签、Style、树、case、链接、源码行号和 RTL 端口模式。 | `make validate MODULE=Sbuffer VERSION=v1.0.0` 通过。 |
| 环境说明和 CI 缺失。 | 新增 Linux/macOS 安装说明、多架构 JDK 17 container、根 Makefile 和 Linux/macOS CI matrix。 | 本机工具验证通过；当前主机无 Docker，容器 build 待 CI 验证。 |

## 2026-09-01 Mermaid 渲染门禁修订

| 问题 | 根因 | 修订 | 验证 |
| --- | --- | --- | --- |
| 微架构图无法显示。 | edge label 中的 `[i]` 被 Mermaid parser 当作语法；同时存在从 subgraph ID 直接连线的脆弱写法。 | 图内改用人类可读接口标签，精确数组端口保留在 I/O 表；从内部 PERF 节点跨边界连线。 | Mermaid CLI 11.16.0 实际渲染成功，SVG 42 KB。 |
| 时序图在不同渲染器上兼容性不足。 | message 含冒号、分号、括号等 parser-sensitive 文本。 | 简化 message 文本，仅保留事务语义。 | 实际渲染成功，SVG 29 KB。 |
| 原 checker 只检查 fence 配对。 | 没有真实 Mermaid parser/browser 阶段。 | 新增固定 Node 22.23.2、Mermaid CLI 11.16.0 和 browser bootstrap；`validate_mermaid.py` 生成 SVG/source hash manifest。 | `make render` 与 `make lint` 均通过。 |
| 图源修改后可能沿用旧截图。 | SVG 与 Markdown 无关联校验。 | strict checker 比较每个 fence 的 source SHA-256、SVG SHA-256、数量和非空 `viewBox`。 | Sbuffer v2.0.0 的 3 张图 evidence 校验通过。 |

模板结构版本由 v2.0.0 升为 v2.1.0。这是兼容增强：保留 v2 I/O schema，新增真实 Mermaid 渲染及 evidence 签核要求。

## 2026-09-02 模板维护注释

模板结构版本由 v2.1.0 升为 v2.1.1。该 Patch 不改变生成文档 schema，使用 HTML 注释补充版本、证据优先级、I/O Generated/Elided、Harness 参数、顶层 FSM、Mermaid、FG/FC/CK 和签核状态的维护规则。注释供模板开发者和生成器阅读，不进入 Markdown 渲染正文。

## 2026-09-03 通用 Skill 与可读性重构

| 问题 | 修订 | 验证标准 |
| --- | --- | --- |
| 模板在 DUT 行为前展示范围、审计和完整端口表，连续阅读成本高。 | 模板 v3.0.0 改为摘要、设计概览、功能行为、Testplan、形式化契约、Sign-off，完整 I/O、参数、证据和追溯后移至附录。 | 新文档章节存在且按当前模板排序，正文无生成过程或阅读指导。 |
| Skill 主源位于 `.opencode`，其他平台依赖 OpenCode 路径。 | 建立 `skills/chip-dv-spec/` 唯一主源，OpenCode、Claude、Codex 使用符号链接适配；保留旧名称作为兼容别名。 | 仓库校验器检查三个平台入口均解析到 canonical Skill。 |
| 单一 Skill 文件同时承载格式、DV、证据和工程细节。 | 入口只保留流程与硬约束，详细规则拆入按需加载的 references，XiangShan 作为项目 profile。 | Skill frontmatter、引用链接和平台入口可独立检查。 |
| 旧校验器把全文四级标题当 FC，并强制至少三个 Case。 | 解析范围限制在 Testplan，按显式 FC ID 建立标题/表格关联；Case、FC、CK、图表和行数只报告，不设固定数量。 | 校验当前格式、ID、Style、追溯和 evidence，不根据 DUT 示例数量判定质量。 |

生成流程始终读取当前模板，不维护 v2/v3 运行时分支。历史文档保持原状；只有新生成或显式指定的文档按当前 schema 校验。
