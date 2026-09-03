# XiangShan Profile

仓库根目录下：源码为 `third_party/XiangShan/`，可选 spec 为 `inputs/<Module>/`，输出为 `outputs/<Module>/`，报告为 `reports/<Module>/`，evidence 为 `evidence/<Module>/<version>/`。使用 `tools/preflight.sh`、`tools/generate_rtl.sh`、`tools/validate_mermaid.py` 和 `tools/validate_document.py`，不要手工猜测 TopMain 或 firtool 命令。

RTL 准备完成后，可用 `make fm-spec MODULE=<Module>` 自动运行仓库固定版本的 FM-Agent Verilog flow。命令等价于在 `third_party/FM-Agent` 中执行 `uv run python main.py <absolute-rtls-module-dir> --hardware --verilog`；若该模块已有 FM-Agent workspace，默认使用 `--resume`。对于中等规模 RTL，完整运行通常需要 20–30 分钟，复杂设计可能更久；这是正常的长时 LLM 任务，不应因数分钟没有终端输出而重复启动。运行期间观察 `rtls/<Module>/fm_agent/fm_agent.log`，以进程退出码判断成功或失败。

结果保留在 `rtls/<Module>/fm_agent/`，并同步到 `inputs/<Module>/fm_agent/` 供文档 Skill 读取。首次重跑或 RTL 已变化时使用 `make fm-spec-fresh MODULE=<Module>`；进程中断、网络错误或模型错误修复后再次使用普通 `make fm-spec` 继续。只有 `make fm-spec-check MODULE=<Module>` 通过后，才将规约作为文档输入；不完整输出必须保留为失败状态，不能手工补齐或伪造。

FM-Agent 是外部 LLM 工作流，会消耗模型 API、时间和费用。Skill 可以自动触发该阶段，但只有在环境变量/API 凭据和 `uv`、OpenCode、Verible 均可用时才执行；缺失时应保留 OPEN 并停止生成，不得伪造规约。

生成前执行：

```bash
./tools/preflight.sh --module <Module> --config <Config> --strict --document-tools
```

需要精确 RTL I/O 时执行：

```bash
./tools/generate_rtl.sh --module <Module> --config <Config> --version <version>
```

完成后执行 `make lint MODULE=<Module> VERSION=<version>`。记录 XiangShan 完整 commit、Config、生成状态和 evidence manifest；不同 commit/config 的 RTL 不得复用。
