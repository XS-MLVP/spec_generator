"""Focused tests for the Spec Generator UCAgent plugin descriptor."""

from pathlib import Path

from spec_generator_plugin.plugin import get_plugin
from spec_generator_plugin.tools import SpecGeneratorCommand
from ucagent.plugins import validate_plugin
from ucagent.tools.uctool import to_fastmcp


def test_plugin_descriptor_validates() -> None:
    """The plugin exposes an in-repository workflow and all declared resources."""
    plugin = validate_plugin(get_plugin(), check_dependencies=False)
    assert plugin.name == "xiangshan-spec-generator"
    assert plugin.workflows[0].name == "design-document"
    assert plugin.workflows[0].config_file.is_file()
    assert all(path.exists() for path in plugin.workflows[0].guide_doc_paths)
    assert plugin.workflows[0].template_dir is not None
    assert Path(plugin.workflows[0].template_dir).is_dir()


def test_command_rejects_shell_like_arguments(tmp_path: Path) -> None:
    """The command tool rejects invalid identifiers before starting make."""
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
