# XiangShan Design Document Generation

本仓库用于基于香山处理器源码、设计文档模板和可选 spec，生成模块级设计与功能检测点文档。

## 目录结构

```text
.
|- inputs/                         可选输入规格，按模块分类
|  `- Sbuffer/
|- templates/                      文档模板，按模板族分类
|  `- chip-design-document/
|- outputs/                        生成的设计文档，按模块分类
|  `- Sbuffer/
|- reports/                        质量与迭代报告
|  |- Sbuffer/
|  `- template/
|- evidence/                       版本化 RTL manifest/端口证据
|- tools/                          跨 Linux/macOS 的生成与检查工具
|- environment/                    Docker 与系统依赖说明
|- third_party/
|  `- XiangShan/                   香山源码 submodule
`- .opencode/skills/
   `- xiangshan-design-document/   模块文档生成 Skill
```

## 初始化

克隆父仓库后初始化香山源码：

```bash
git submodule update --init --recursive
```

当前 submodule 固定到父仓库记录的 XiangShan 提交。更新源码时应单独评审 submodule 指针变化，并重新生成受影响模块的文档。

环境要求和 Linux/macOS/容器安装方法见 [environment/README.md](environment/README.md)。建议先运行：

```bash
make preflight MODULE=Sbuffer CONFIG=DefaultConfig
```

预检会检查 Java、Mill pin、native Espresso、Node.js、Mermaid CLI/browser、submodule、配置、源码 class、工作区和磁盘空间。缺少工具时按固定版本放入 `.cache/`；非 Linux x86-64 平台自动构建 native Espresso，无需留下 XiangShan 源码修改。

## 文档生成

在 OpenCode 中要求根据 XiangShan 源码为指定模块生成设计文档时，项目 Skill `xiangshan-design-document` 会指导以下流程：

1. 读取 `templates/chip-design-document/chip_design_document_template_zh.md`。
2. 读取 `third_party/XiangShan` 中的模块、Bundle、参数和配置源码。
3. 可选读取 `inputs/<Module>/` 下的规格。
4. 从同一提交、同一配置的 elaborated Verilog 提取精确端口；无法取得时登记 `OPEN-IO-*`，禁止猜测。
5. 选择新的 SemVer 文档版本，首次为 `v1.0.0`，且不得覆盖历史版本。
6. 输出 `outputs/<Module>/<Module>_design_document_zh_v<version>.md`。
7. 输出 `reports/<Module>/<Module>_document_quality_review_v<version>.md`。
8. 更新 `outputs/<Module>/VERSION_HISTORY.md`，记录基线、配置、变更类型及两个版本化文件的链接。
9. 保存 `evidence/<Module>/<version>/manifest.json` 和 `ports.csv`，并运行统一检查器。

常用命令：

```bash
make evidence MODULE=Sbuffer CONFIG=DefaultConfig VERSION=v2.0.2  # 使用下一个未占用版本
make render MODULE=Sbuffer VERSION=v2.0.2
make validate MODULE=Sbuffer VERSION=v2.0.1
make lint MODULE=Sbuffer VERSION=v2.0.1
```

RTL 缓存键包括 XiangShan commit、配置、生成 flags、Java/Mill/Espresso、OS/架构和 wrapper 版本。同一配置的一次 split-RTL 由所有模块共享，避免为 Sbuffer、ICache、DCache 重复 elaboration。`.cache/` 可随时删除；版本化 `evidence/` 应提交到 Git，避免清理构建缓存后丢失端口依据。

文档版本与 XiangShan commit 分开管理：文档版本用于比较文档演进，完整 commit 用于锁定 RTL 证据。接口、参数、状态或 FG/FC/CK 的语义变化通常递增 MINOR；证据、措辞或 OPEN 关闭通常递增 PATCH；不兼容的 DUT 范围或文档结构变化递增 MAJOR。每次生成都必须产生新版本，即使没有语义变化也递增 PATCH 并记录为“仅重新生成”。

模板还维护独立的“模板结构版本”。生成文档必须记录所用模板版本；不兼容的模板结构升级通常要求模块文档递增 MAJOR。

现有无版本 Sbuffer 输出形成于引入 XiangShan submodule 和版本规范之前，视为 legacy。正式版本已从 `v1.0.0` 开始，并保存对应 manifest/ports；后续生成按 SemVer 递增。

修改 `.opencode/skills/` 后需重启 OpenCode，新的 Skill 定义才会加载。
