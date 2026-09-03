# Contributing

本指南面向模板、OpenCode Skill 和工具维护者。生成模块文档请阅读 [README](README.md)。设计原则和证据模型见 [docs/design-and-evidence.md](docs/design-and-evidence.md)。

## 修改范围

| 内容 | 路径 |
| --- | --- |
| 文档模板 | `templates/chip-design-document/chip_design_document_template_zh.md` |
| OpenCode Skill | `.opencode/skills/xiangshan-design-document/SKILL.md` |
| 生成与检查工具 | `tools/`、`Makefile` |
| 通用维护记录 | `reports/template/` |
| 参考案例 | `references/` |

模块级 `inputs/`、`outputs/`、`reports/<Module>/` 和 `evidence/` 是本地回归资产，不提交到仓库。

## 修改规则

模板、Skill 和 checker 是同一协议的三个部分：模板定义输出，Skill 定义生成方法，checker 强制关键约束。修改任一部分时，检查另外两部分是否需要同步。

- 新增模板字段或硬规则时，同步更新 Skill、checker 和模板版本。
- 模板版本使用 SemVer：不兼容结构改动升 Major，兼容字段升 Minor，注释或措辞升 Patch。
- 实现事实必须保持 `matching RTL > Chisel/Scala > 配置 > 可选 spec > 显式推断` 的证据顺序。
- 不修改 XiangShan submodule 来迁就文档工具。
- 不提交模块资产、缓存、凭据、私有路径或 IDE 状态。
- 外部参考资料必须确认许可，并在 `references/README.md` 记录来源和用途。

详细模板协议写在模板注释和 Skill 中，不在本指南重复。

## 开发流程

1. 修改前运行仓库检查，记录已有问题。
2. 做最小一致改动，并更新 `reports/template/Template_iteration_review.md`。
3. 运行仓库和模板门禁。
4. 若改动影响生成结果，使用本地模块生成一个新版本回归，不覆盖历史版本。

```bash
make repo-lint
make template-check
git diff --check
```

可选的本地模块回归：

```bash
make preflight MODULE=<Module> CONFIG=<Config>
make lint MODULE=<Module> VERSION=<version>
```

修改 Skill 后，重启 OpenCode 再做生成回归。

## 提交检查

提交前确认：

- `make repo-lint` 和 `make template-check` 通过。
- 模板版本及附录中的版本示例一致。
- 模板、Skill、checker 和维护记录已同步。
- 本地模块回归产物未进入暂存区。
- `git diff --cached --check` 通过。

提交信息使用简洁的祈使句，例如 `Clarify coverage sampling guidance`。
