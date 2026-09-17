
## Summary

Describe the plugin behavior changed and affected workflow or artifact contract.

## Validation

- [ ] `make repo-lint`
- [ ] `make plugin-check`
- [ ] `make test`
- [ ] `make template-check` when template content or location changes
- [ ] `python -m build` when package code or resources change
- [ ] Install the wheel and run `python -I -m pytest -q --import-mode=append -o pythonpath=''` when package code or resources change
- [ ] Workflow, Guide_Doc, template and Checker contracts agree
- [ ] Local module assets, cache and runtime state are excluded
- [ ] `git diff --check`

Record any local module regression and its document version; summarize relevant OPEN items without committing generated assets.
