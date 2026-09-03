# Cross-Platform Environment

工具脚本支持 Linux 和 macOS。需要 Python 3.10+、Git、Curl、Make 和 C compiler。JDK 17、Node.js 22、Mermaid CLI 和 headless browser 若未安装，会按固定版本下载到 `.cache/`；生产或 CI 环境仍建议按组织规范预装并缓存这些工具。

## Linux

Debian/Ubuntu：

```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk git curl make build-essential python3 time
```

Fedora/RHEL：

```bash
sudo dnf install -y java-17-openjdk-devel git curl make gcc python3 time
```

Linux x86-64 默认使用 XiangShan 自带 Espresso。Linux ARM64 会由 `tools/prepare_espresso.sh` 在 `.cache/` 中构建 native 版本。

## macOS

使用 Homebrew：

```bash
brew install openjdk@17 git curl make python
export PATH="$(brew --prefix openjdk@17)/bin:$PATH"
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
```

不要求安装 GNU `time`。本项目的 RTL wrapper 直接调用 XiangShan 的 Mill entry，并保留与 Makefile 相同的生成参数。Apple Silicon 和 Intel macOS 都会按主机架构构建 native Espresso。

## Container

Docker/Podman 可使用：

```bash
docker compose -f environment/compose.yaml build
docker compose -f environment/compose.yaml run --rm docs make preflight MODULE=Sbuffer
```

镜像基于固定 OCI digest 的多架构 Temurin JDK 17；Mill 和 Espresso 由项目脚本按 XiangShan pin 与容器架构准备。

## Required Workflow

```bash
make init
make preflight MODULE=<Module> CONFIG=<Config>
make evidence MODULE=<Module> CONFIG=<Config> VERSION=<version>
# 使用 Skill 生成同版本正文和质量报告
make render MODULE=<Module> VERSION=<version>
make lint MODULE=<Module> VERSION=<version>
```

维护模板和工具而不生成模块文档时运行 `make repo-lint` 与 `make template-check`。CI 只使用这两个仓库自有入口，不依赖被 `.gitignore` 排除的本地模块资产。

`.cache/` 是可删除的本机缓存；`evidence/` 是模块文档的本地版本化证据，但与 `inputs/`、`outputs/` 和模块级 `reports/` 一样不纳入本工具仓库。需要长期保留时，应复制到项目外的受控制品存储。
