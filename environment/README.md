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
make preflight MODULE=Sbuffer CONFIG=DefaultConfig
make evidence MODULE=Sbuffer CONFIG=DefaultConfig VERSION=v2.0.2  # 使用下一个未占用版本
make render MODULE=Sbuffer VERSION=v2.0.2
make validate MODULE=Sbuffer VERSION=v2.0.1
```

`.cache/` 是可删除的本机缓存；`evidence/` 是需要纳入 Git 的版本化证据。
