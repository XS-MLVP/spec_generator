"""Exercise command execution, write policy, and actual UCAgent stage startup."""

import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from spec_generator_plugin.checkers import SpecGeneratorArtifactsChecker
from spec_generator_plugin.plugin import get_plugin
from spec_generator_plugin.tools import SpecGeneratorCommand
from ucagent.plugins import (
    collect_plugin_resources,
    load_plugin,
    resolve_plugin_workflow,
)
from ucagent.util.config import load_yaml_with_env_vars


@pytest.fixture
def repository(tmp_path):
    """Build a disposable command repository without real RTL or tool downloads."""
    (tmp_path / "tools").mkdir()
    (tmp_path / ".cache").mkdir()
    for name in (
        "preflight.sh",
        "generate_rtl.sh",
        "validate_document.py",
        "validate_mermaid.py",
    ):
        (tmp_path / "tools" / name).write_text("# Test-only script stub.\n")
    (tmp_path / "tools/update_document_metadata.py").write_text(
        '"""Echo metadata arguments to prove they are passed literally."""\n'
        "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"
    )
    template = (
        tmp_path / "templates/chip-design-document/chip_design_document_template_zh.md"
    )
    template.parent.mkdir(parents=True)
    template.write_text("\n# Test document skeleton\n")
    (tmp_path / "Makefile").write_text(
        ".PHONY: preflight evidence render validate lint\n"
        "preflight evidence render validate lint:\n"
        '\t@printf "%s\\n" "$@ $(MODULE) $(CONFIG) $(VERSION)"\n'
        '\t@test -z "$(ALLOW_HISTORICAL_TEMPLATE)"\n'
        '\t@printf "%s\\n" "$$XIANGSHAN_ROOT" "$$TEMPLATE_GENERATE_CACHE"\n'
        '\t@if test -f .cache/reject; then printf "artifact rejected\\n" >&2; exit 2; fi\n'
    )
    return tmp_path


@pytest.fixture
def command(repository):
    """Bind execution to all intentional writes in the test workspace."""
    return SpecGeneratorCommand(
        workspace=str(repository),
        write_dirs=[
            "outputs",
            "reports",
            "evidence",
            ".cache",
            "third_party/XiangShan",
        ],
        un_write_dirs=["tools", "templates"],
    )


@pytest.mark.parametrize(
    "action", ["preflight", "evidence", "render", "validate", "lint"]
)
def test_actions_execute_locally(command, repository, monkeypatch, action):
    """Every fixed action uses validated inputs and local source/cache overrides."""
    monkeypatch.setenv("XIANGSHAN_ROOT", "/outside/source")
    monkeypatch.setenv("TEMPLATE_GENERATE_CACHE", "/outside/cache")
    monkeypatch.setenv("ALLOW_HISTORICAL_TEMPLATE", "--allow-historical-template")
    result = command.invoke(
        dict(action=action, module="Sbuffer", config="TestConfig", version="v1.2.3")
    )
    assert result["ok"], result
    assert f"{action} Sbuffer TestConfig v1.2.3" in result["stdout"]
    assert str(repository / "third_party/XiangShan") in result["stdout"]
    assert "/outside" not in result["stdout"]


def test_metadata_passes_summary_literally(command, repository):
    """Free-text metadata cannot become shell or Make instructions."""
    summary = 'review $(touch injected) `touch injected` "quoted"'
    result = command.invoke(
        dict(
            action="metadata",
            module="Sbuffer",
            version="v1.2.3",
            change_type="Patch",
            summary=summary,
        )
    )
    assert result["ok"], result
    args = json.loads(result["stdout"])
    assert args[args.index("--summary") + 1] == summary
    assert not (repository / "injected").exists()


@pytest.mark.parametrize(
    "args",
    [
        dict(action="clean", module="Sbuffer"),
        dict(action="preflight", module="../Sbuffer"),
        dict(action="preflight", module="Sbuffer", config="$(touch injected)"),
        dict(action="evidence", module="Sbuffer"),
        dict(
            action="metadata", module="Sbuffer", version="v1.0.0", change_type="Patch"
        ),
        dict(action="metadata", module="Sbuffer", version="v1.0.0", summary="bad|row"),
    ],
)
def test_invalid_arguments_never_launch(command, monkeypatch, args):
    """Invalid inputs are rejected before a subprocess can start."""

    def forbidden(*args, **kwargs):
        """Fail if invalid input reaches the operating system."""
        pytest.fail("Subprocess launched for invalid arguments")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert command._run(**args)["error_code"] == "INVALID_ARGUMENTS"


def test_missing_workspace_returns_prerequisites(tmp_path):
    """An empty workspace cannot silently pass a repository command."""
    result = SpecGeneratorCommand(workspace=str(tmp_path))._run("preflight", "Sbuffer")
    assert result["error_code"] == "SPEC_GENERATOR_WORKSPACE_INVALID"
    assert "tools/validate_document.py" in result["observed"]


def test_write_policy_and_child_protection(command):
    """Explicit read-only descendants cannot be bypassed by directory writes."""
    command.un_write_dirs.append("evidence/Sbuffer/v1.0.0/manifest.json")
    result = command._run("evidence", "Sbuffer", version="v1.0.0")
    assert result["error_code"] == "WRITE_POLICY_DENIED"
    command.un_write_dirs.pop()
    command.write_dirs = ["outputs"]
    assert command._run("preflight", "Sbuffer")["error_code"] == "WRITE_POLICY_DENIED"


@pytest.mark.parametrize("nested", [False, True])
def test_external_symlink_rejected(command, repository, tmp_path_factory, nested):
    """Neither writable directories nor their children may escape the workspace."""
    outside = tmp_path_factory.mktemp("outside")
    target = repository / "evidence/Sbuffer/v1.0.0"
    target.parent.mkdir(parents=True)
    if nested:
        target.mkdir()
        (target / "manifest.json").symlink_to(outside / "manifest.json")
    else:
        target.symlink_to(outside, target_is_directory=True)
    result = command._run("evidence", "Sbuffer", version="v1.0.0")
    assert result["error_code"] == "PATH_OUTSIDE_WORKSPACE"
    assert list(outside.iterdir()) == []


def test_timeout_terminates_command_tree(command, repository):
    """An overlong command is terminated and reported as a failed action."""
    (repository / "Makefile").write_text("preflight:\n\t@sleep 10\n")
    command.command_timeout = 1
    result = command._run("preflight", "Sbuffer")
    assert not result["ok"]
    assert result["error_code"] == "COMMAND_TIMEOUT"


def test_checker_revalidates_and_preserves_failure(command, repository):
    """Both Check and Complete use current validator results, never cached success."""
    cfg = SimpleNamespace(
        write_dirs=command.write_dirs, un_write_dirs=command.un_write_dirs
    )
    checker = SpecGeneratorArtifactsChecker("Sbuffer", "v1.0.0", cfg=cfg).set_workspace(
        str(repository)
    )
    assert checker.do_check()[0]
    (repository / ".cache/reject").touch()
    passed, result = checker.do_check(is_complete=True)
    assert not passed
    assert result["error_code"] == "SPEC_GENERATOR_COMMAND_FAILED"
    assert "artifact rejected" in result["stderr"]
    assert result["next_action"]


@pytest.mark.parametrize("enabled", [False, True])
def test_agent_startup_and_completion_without_required_skills(
    repository, monkeypatch, enabled
):
    """Real Agent startup copies resources and completes the same gate with skills on/off."""
    from ucagent.verify_agent import VerifyAgent

    project = Path(__file__).resolve().parents[1]
    loaded = load_plugin(str(project), check_dependencies=False)
    selected = resolve_plugin_workflow(
        [loaded], "xiangshan-spec-generator:design-document"
    )
    docs, skills = collect_plugin_resources([loaded], selected)
    monkeypatch.setenv("SPEC_DOCUMENT_VERSION", "v2.3.4")
    monkeypatch.setenv("XIANGSHAN_CONFIG", "TestConfig")
    # All declared stage artifacts exist before startup so reference tracking can attach.
    for name in (
        "evidence/Sbuffer/v2.3.4/manifest.json",
        "evidence/Sbuffer/v2.3.4/ports.csv",
        "evidence/Sbuffer/v2.3.4/diagrams/manifest.json",
        "outputs/Sbuffer/Sbuffer_design_document_zh_v2.3.4.md",
        "outputs/Sbuffer/VERSION_HISTORY.md",
        "reports/Sbuffer/Sbuffer_document_quality_review_v2.3.4.md",
    ):
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test-only fixture\n")
    agent = VerifyAgent(
        workspace=str(repository),
        dut_name="Sbuffer",
        output="outputs/Sbuffer",
        cfg_override=[
            {"backend.key_name": "blank"},
            {"langfuse.enable": False},
            {"skill.use_skill": enabled},
        ],
        no_embed_tools=True,
        no_history=True,
        plugins=[loaded],
        plugin_guide_doc_paths=[str(path) for path in docs],
        plugin_skill_paths=[(name, str(path)) for name, path in skills],
        workflow_config_file=str(selected[1].config_file),
        plugin_workflow="xiangshan-spec-generator:design-document",
        template_dir=str(selected[1].template_dir.parent),
        template_target=selected[1].template_target,
    )
    try:
        assert "v2.3.4" in agent.get_default_system_prompt()
        assert "TestConfig" in agent.get_default_system_prompt()
        assert (repository / "Guide_Doc/generation-guide.md").is_file()
        assert (repository / "Guide_Doc/chip_design_document_template_zh.md").is_file()
        assert (repository / ".ucagent/skills").exists() is enabled
        assert any(
            tool.name == "SpecGeneratorCommand" for tool in agent.tool_list_plugin
        )
        for index, stage in enumerate(agent.stage_manager.stages):
            agent.stage_manager.force_go_to_stage(index)
            stage.set_reached(True)
            assert not stage.skill_list
            for name in stage.reference_files:
                agent.tool_read_text.invoke({"path": name})
            passed, result = stage.do_check(is_complete=True)
            assert passed, result
        (repository / ".cache/reject").touch()
        assert not agent.stage_manager.stages[-1].do_check(is_complete=True)[0]
    finally:
        agent.exit()


@pytest.mark.parametrize("version,config", [(None, None), ("v2.1.0", "MinimalConfig")])
def test_workflow_yaml_environment(monkeypatch, version, config):
    """Both default and supplied environment values produce a valid workflow."""
    for key, value in (
        ("SPEC_DOCUMENT_VERSION", version),
        ("XIANGSHAN_CONFIG", config),
    ):
        monkeypatch.delenv(key, raising=False)
        if value:
            monkeypatch.setenv(key, value)
    cfg = load_yaml_with_env_vars(get_plugin().workflows[0].config_file)
    assert cfg["template_overwrite"]["VERSION"] == (version or "v1.0.0")
    assert cfg["template_overwrite"]["XS_CONFIG"] == (config or "DefaultConfig")
    assert len(cfg["stage"]) == 3


def test_real_validator_rejects_missing_document(tmp_path):
    """The actual repository validator rejects missing evidence without downloads."""
    project = Path(__file__).resolve().parents[1]
    for name in ("tools", "templates"):
        shutil.copytree(project / name, tmp_path / name)
    shutil.copy2(project / "Makefile", tmp_path / "Makefile")
    result = SpecGeneratorCommand(workspace=str(tmp_path), write_dirs=[".cache"])._run(
        "validate", "Sbuffer", version="v1.0.0"
    )
    assert not result["ok"]
    assert "Sbuffer_design_document_zh_v1.0.0.md" in result["stdout"] + result["stderr"]


def test_large_output_is_bounded(command, repository):
    """Long external output cannot overwhelm the agent's context window."""
    (repository / "tools/update_document_metadata.py").write_text(
        '"""Generate large test output."""\nprint("x" * 20000)\n'
    )
    result = command._run("metadata", "Sbuffer", version="v1.0.0")
    assert result["ok"]
    assert result["stdout_truncated"]
    assert len(result["stdout"]) == 12000


def test_generated_state_is_excluded_from_repository_lint():
    """Runtime Markdown is excluded while canonical plugin Guide_Doc remains checked."""
    project = Path(__file__).resolve().parents[1]
    namespace = runpy.run_path(str(project / "tools/validate_repository.py"))
    owns = namespace["is_repository_owned"]
    assert not owns(project / ".ucagent/skills/example/SKILL.md")
    assert not owns(project / "Guide_Doc/generation-guide.md")
    assert owns(project / "src/spec_generator_plugin/resources/Guide_Doc/generation-guide.md")


def test_packaged_assets_match_canonical_sources(tmp_path):
    """The synchronization command reproduces exactly the resources being shipped."""
    project = Path(__file__).resolve().parents[1]
    for name in ("tools/sync_ucagent_resources.py", "templates/chip-design-document/chip_design_document_template_zh.md", ".opencode/skills/xiangshan-design-document/SKILL.md"):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project / name, dest)
    subprocess.run([sys.executable, str(tmp_path / "tools/sync_ucagent_resources.py")], check=True, capture_output=True)
    for path in (tmp_path / "src").rglob("*.md"):
        assert path.read_bytes() == (project / path.relative_to(tmp_path)).read_bytes()
