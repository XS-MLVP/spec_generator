"""Final acceptance gates backed by the Spec Generator's strict validators."""

from ucagent.checkers.base import Checker

from .tools import SpecGeneratorCommand, SpecGeneratorCommandArgs


class SpecGeneratorArtifactsChecker(Checker):
    """Re-run strict validation instead of trusting an agent-authored success claim."""

    def __init__(self, module: str, version: str, run_lint: bool = True, **kwargs):
        """Validate static parameters; defer workspace access until Check/Complete."""
        super().__init__()
        SpecGeneratorCommandArgs(action="validate", module=module, version=version)
        if not version or not isinstance(run_lint, bool):
            raise ValueError("version is required and run_lint must be boolean")
        self.module = module
        self.version = version
        self.run_lint = run_lint
        self.cfg = kwargs.get("cfg")

    def do_check(self, is_complete: bool = False, **kwargs) -> tuple[bool, dict]:
        """Run fresh strict document validation, including Mermaid rendering for final lint."""
        cfg = self.cfg
        runner = SpecGeneratorCommand(
            workspace=self.workspace,
            write_dirs=list(cfg.write_dirs) if cfg is not None else [],
            un_write_dirs=list(cfg.un_write_dirs) if cfg is not None else [],
        )
        result = runner._run(
            action="lint" if self.run_lint else "validate",
            module=self.module,
            version=self.version,
        )
        return result["ok"], result
