"""Workspace-bound commands for the XiangShan documentation workflow."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ucagent.plugins import PluginContext
from ucagent.tools.fileops import is_file_writeable
from ucagent.tools.uctool import UCTool


class SpecGeneratorCommandArgs(BaseModel):
    """Select a repository action and its exact module/version inputs."""

    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "preflight", "evidence", "metadata", "render", "validate", "lint"
    ] = Field(
        description="preflight checks tools; evidence generates RTL/ports; render creates SVGs; "
        "metadata updates generated fields; validate checks artifacts; lint performs final checks."
    )
    module: str = Field(
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
        description="Exact XiangShan module class, e.g. Sbuffer.",
    )
    config: str = Field(
        default="DefaultConfig",
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
        description="XiangShan configuration class.",
    )
    version: str = Field(
        default="",
        pattern=r"^(v[0-9]+\.[0-9]+\.[0-9]+)?$",
        description="Target document version, e.g. v1.0.0; required except for preflight.",
    )
    change_type: Literal["Major", "Minor", "Patch"] | None = Field(
        default=None,
        description="For metadata: semantic change category when adding a history row.",
    )
    summary: str = Field(
        default="",
        max_length=1000,
        description="For metadata: one-line change summary, required with change_type.",
    )


class SpecGeneratorCommand(UCTool):
    """Run the repository's fixed commands with bounded output and progress."""

    name: str = "SpecGeneratorCommand"
    description: str = (
        "Run Spec Generator preflight, evidence, render, metadata, validate, or lint "
        "in a spec_generator repository workspace. Read stderr/stdout on failure. "
        "Generate evidence before drafting, then render before metadata and final lint."
    )
    args_schema: type[BaseModel] = SpecGeneratorCommandArgs
    workspace: str
    write_dirs: list[str] = Field(default_factory=list)
    un_write_dirs: list[str] = Field(default_factory=list)
    command_timeout: int = Field(default=3600, gt=0)

    def _run(
        self,
        action: str,
        module: str,
        config: str = "DefaultConfig",
        version: str = "",
        change_type: str | None = None,
        summary: str = "",
    ) -> dict:
        """Validate paths/policy, execute one fixed action, and return bounded diagnostics."""
        try:
            args = SpecGeneratorCommandArgs(
                action=action,
                module=module,
                config=config,
                version=version,
                change_type=change_type,
                summary=summary,
            )
        except ValidationError:
            return {
                "ok": False,
                "error_code": "INVALID_ARGUMENTS",
                "error": "Invalid action, module, config, version, or metadata arguments.",
                "next_action": "Use an action from the schema, identifier-only module/config, and a vMAJOR.MINOR.PATCH version.",
            }
        if (
            (action != "preflight" and not args.version)
            or (change_type is not None and not summary.strip())
            or any(char in summary for char in "\r\n|")
            or (action != "metadata" and (change_type or summary))
        ):
            return {
                "ok": False,
                "error_code": "INVALID_ARGUMENTS",
                "error": "A version is required except for preflight; history metadata requires a category and one-line summary without table separators.",
                "next_action": "Set version; use change_type and summary only for metadata.",
            }
        workspace = Path(self.workspace).resolve()
        required = [
            "Makefile",
            "tools/preflight.sh",
            "tools/generate_rtl.sh",
            "tools/validate_document.py",
            "tools/validate_mermaid.py",
            "tools/update_document_metadata.py",
            "templates/chip-design-document/chip_design_document_template_zh.md",
        ]
        missing = [name for name in required if not (workspace / name).is_file()]
        if missing:
            return {
                "ok": False,
                "error_code": "SPEC_GENERATOR_WORKSPACE_INVALID",
                "error": "Required repository files are missing.",
                "workspace": str(workspace),
                "observed": missing,
                "next_action": "Use the spec_generator repository root as workspace; initialize its XiangShan submodules before preflight.",
            }

        # Each action has a fixed write footprint; resolved paths must stay in the workspace.
        targets = [".cache"]
        if action == "evidence":
            targets += [
                f"evidence/{module}/{version}",
                "third_party/XiangShan/out",
                "third_party/XiangShan/build",
                "third_party/XiangShan/src/main/resources/espresso",
            ]
        elif action == "render":
            targets += [f"evidence/{module}/{version}/diagrams"]
        elif action == "metadata":
            targets += [
                f"outputs/{module}/{module}_design_document_zh_{version}.md",
                f"outputs/{module}/VERSION_HISTORY.md",
                f"reports/{module}/{module}_document_quality_review_{version}.md",
            ]
        for name in [
            *required,
            *targets,
            f"outputs/{module}",
            f"reports/{module}",
            f"evidence/{module}",
            "third_party/XiangShan",
        ]:
            if not (workspace / name).resolve().is_relative_to(workspace):
                return {
                    "ok": False,
                    "error_code": "PATH_OUTSIDE_WORKSPACE",
                    "error": "A repository path resolves outside the workspace.",
                    "artifact": name,
                    "next_action": "Use repository-local files and directories; remove the external symlink.",
                }
        # Existing children may themselves redirect subprocess writes, even when
        # their parent directory is local. Internal tool-install symlinks are valid.
        for name in targets:
            for directory, dirs, files in os.walk(workspace / name, followlinks=False):
                for entry in (*dirs, *files):
                    path = Path(directory) / entry
                    if path.is_symlink() and not path.resolve().is_relative_to(
                        workspace
                    ):
                        return {
                            "ok": False,
                            "error_code": "PATH_OUTSIDE_WORKSPACE",
                            "error": "A writable tree contains an external symlink.",
                            "artifact": str(path.relative_to(workspace)),
                            "next_action": "Replace the external symlink with a workspace-local path before retrying.",
                        }
        for name in targets:
            permitted, reason = is_file_writeable(
                name, self.un_write_dirs, self.write_dirs
            )
            protected_children = [
                path
                for path in self.un_write_dirs
                if (workspace / path)
                .resolve()
                .is_relative_to((workspace / name).resolve())
            ]
            if not permitted or protected_children:
                return {
                    "ok": False,
                    "error_code": "WRITE_POLICY_DENIED",
                    "error": reason
                    if not permitted
                    else "The action would write beneath a protected path.",
                    "artifact": name,
                    "next_action": "Select the design-document workflow or configure its required write directories without conflicting protected paths.",
                }

        command = [
            "make",
            action,
            f"MODULE={module}",
            f"CONFIG={config}",
            "ALLOW_HISTORICAL_TEMPLATE=",
        ]
        if version:
            command.append(f"VERSION={version}")
        if action == "metadata":
            # Pass free-text summaries directly to Python, never through make's shell expansion.
            command = [
                sys.executable,
                "tools/update_document_metadata.py",
                "--module",
                module,
                "--version",
                version,
                "--update-history",
            ]
            if change_type:
                command += ["--change-type", change_type, "--summary", summary]
        env = os.environ.copy()
        for key in ("MAKEFLAGS", "MFLAGS", "GNUMAKEFLAGS", "MAKEFILES"):
            env.pop(key, None)
        env.update(
            XIANGSHAN_ROOT=str(workspace / "third_party/XiangShan"),
            TEMPLATE_GENERATE_CACHE=str(workspace / ".cache"),
            PYTHONPYCACHEPREFIX=str(workspace / ".cache/python"),
        )
        started = time.monotonic()
        timed_out = False
        self.put_alive_data(f"Starting {action} for {module} {version}")
        try:
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                process = subprocess.Popen(
                    command,
                    cwd=workspace,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
                try:
                    while process.poll() is None:
                        remaining = self.command_timeout - (time.monotonic() - started)
                        if remaining <= 0 or self.is_force_exit():
                            timed_out = True
                            break
                        try:
                            process.wait(timeout=min(5, remaining))
                        except subprocess.TimeoutExpired:
                            self.put_alive_data(
                                f"{action}: running for {int(time.monotonic() - started)} seconds"
                            )
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                output = {}
                for key, stream in (("stdout", stdout), ("stderr", stderr)):
                    size = stream.seek(0, os.SEEK_END)
                    stream.seek(max(0, size - 12000))
                    output[key] = stream.read().decode("utf-8", errors="replace")
                    output[f"{key}_truncated"] = size > 12000
        except OSError as exc:
            return {
                "ok": False,
                "error_code": "COMMAND_UNAVAILABLE",
                "error": str(exc),
                "next_action": "Check make/Python availability and repository file permissions, then retry.",
            }
        result = {
            "ok": not timed_out and process.returncode == 0,
            "action": action,
            "module": module,
            "version": version,
            "returncode": process.returncode,
            **output,
        }
        if not result["ok"]:
            result.update(
                error_code="COMMAND_TIMEOUT"
                if timed_out
                else "SPEC_GENERATOR_COMMAND_FAILED",
                error=f"{action} did not complete successfully.",
                next_action="Inspect stdout/stderr, repair the named environment or artifact problem, then rerun this action.",
            )
        return result


def create_tools(context: PluginContext) -> list[UCTool]:
    """Bind the tool to the active workspace and its resolved write policy."""
    return [
        SpecGeneratorCommand(
            workspace=str(context.workspace),
            write_dirs=list(context.write_dirs),
            un_write_dirs=list(context.un_write_dirs),
            call_time_out=3660,
        )
    ]
