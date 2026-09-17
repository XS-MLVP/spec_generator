"""Focused tests for the Spec Generator UCAgent plugin descriptor."""

from pathlib import Path
import shutil
import tomllib

import pytest

from spec_generator_plugin.plugin import get_plugin
from spec_generator_plugin.tools import SpecGeneratorCommand, create_tools
from ucagent.plugins import PluginContext, PluginError, validate_plugin
from ucagent.tools.uctool import to_fastmcp


def test_plugin_descriptor_validates() -> None:
    """The plugin exposes an in-repository workflow and all declared resources."""
    plugin = validate_plugin(get_plugin(), check_dependencies=False)
    assert plugin.name == "xiangshan-spec-generator"
    assert plugin.workflows[0].name == "design-document"
    assert plugin.workflows[0].config_file.is_file()
    assert all(path.exists() for path in plugin.workflows[0].guide_doc_paths)
    assert plugin.workflows[0].template_dir is None
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    manifest = tomllib.loads((root / "ucagent-plugin.toml").read_text())
    assert plugin.version == project["version"]
    assert plugin.name == manifest["name"]
    assert project["entry-points"]["ucagent.plugins"][plugin.name] == manifest["entry"]
    assert f"UCAgent{plugin.requires_ucagent}" in project["dependencies"]
    assert set(plugin.python_requirements) <= set(project["dependencies"])


def test_command_rejects_shell_like_arguments(tmp_path: Path) -> None:
    """The command tool rejects invalid identifiers before starting any command."""
    tool = SpecGeneratorCommand(workspace=str(tmp_path))
    result = tool._run("preflight", "Sbuffer;touch-pwned")
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_ARGUMENTS"
    assert not (tmp_path / "pwned").exists()


def test_command_has_mcp_convertible_pydantic_schema(tmp_path: Path) -> None:
    """The plugin tool exposes the BaseModel schema required by MCP conversion."""
    mcp_tool = to_fastmcp(SpecGeneratorCommand(workspace=str(tmp_path)))
    schema = mcp_tool.parameters
    assert "action" in schema["properties"]
    assert schema["additionalProperties"] is False


def test_parser_dependency_is_declared_and_diagnosed(monkeypatch):
    """Missing parser metadata yields the same actionable dependency gate as installed plugins."""
    import importlib.metadata

    real_version = importlib.metadata.version

    def installed_version(name):
        """Simulate only the parser distribution being unavailable."""
        if name == "markdown-it-py":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    monkeypatch.setattr(importlib.metadata, "version", installed_version)
    with pytest.raises(PluginError, match="requires Python package markdown-it-py"):
        validate_plugin(get_plugin(), check_dependencies=True)


@pytest.mark.parametrize(
    "command,label",
    [("bash", "Bash"), ("git", "Git"), ("curl", "Curl"), ("make", "GNU Make")],
)
def test_missing_host_command_fails_at_activation(monkeypatch, command, label):
    """Diagnose each missing host prerequisite before the workflow starts."""
    real_which = shutil.which

    def available(name):
        """Hide only the command under test without changing the actual environment."""
        return None if name == command else real_which(name)

    monkeypatch.setattr("ucagent.plugins.shutil.which", available)
    with pytest.raises(PluginError, match=f"requires command {label}: {command}"):
        validate_plugin(get_plugin(), check_dependencies=True)


def test_factory_preserves_resolved_workspace_policy(tmp_path):
    """The registered tool factory must enforce the policy supplied by UCAgent."""
    context = PluginContext(
        workspace=tmp_path,
        output_dir="outputs/Sbuffer",
        write_dirs=("outputs/Sbuffer",),
        un_write_dirs=(".cache",),
        cfg=None,
        plugin_root=get_plugin().root,
    )
    (tool,) = create_tools(context)
    assert tool.workspace == str(tmp_path)
    assert tool.write_dirs == list(context.write_dirs)
    assert tool.un_write_dirs == list(context.un_write_dirs)
    assert tool._run("preflight", "Sbuffer")["error_code"] == "WRITE_POLICY_DENIED"
