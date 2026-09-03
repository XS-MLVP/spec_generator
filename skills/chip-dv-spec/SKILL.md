---
name: chip-dv-spec
description: Generate or reorganize formal chip design specifications and verification Testplans from templates, RTL/source evidence, and optional requirements. Use for DUT behavior, interface contracts, formal properties, coverage, traceability, and sign-off documents; do not use for generic prose editing.
---

# Chip DV Specification

Generate a formal, evidence-based DUT specification and verification Testplan. The current repository template is the only output schema: always read the latest template at `templates/chip-design-document/chip_design_document_template_zh.md` before drafting. Do not select a historical template version at runtime and do not infer required item counts from example documents.

## Workflow

1. Resolve the repository profile and identify the DUT, configuration, source baseline, optional specs, output version, report, history, and evidence paths. When `rtls/<Module>/` exists, treat it as the default RTL input and do not require the user to restate the workflow.
2. Run the profile preflight and collect matching source/RTL evidence before making implementation claims. For standalone RTL with no matching project profile or configuration, run the available RTL/document checks and record unavailable project evidence as `OPEN-*`; do not invent a Chisel class or configuration. If `rtls/<Module>/` contains Verilog/SystemVerilog, run `make fm-spec MODULE=<Module>` through the repository wrapper before reading generated submodule specs. Use `--resume` automatically when a workspace exists; do not ask the user to assemble the FM-Agent command manually.
3. Build an internal fact inventory for interfaces, transactions, data/control paths, state, parameters, boundary behavior, candidate FG/FC/CK, OPEN items, and evidence locations.
4. Write the document in the current template order. Explain DUT behavior first; put flattened RTL ports, exhaustive parameters, evidence, traceability, and audit details in appendices.
5. Derive the Testplan from observed behavior. Use DV terminology: stimulus, driver, monitor, checker, scoreboard, reference model, assertion, Assume/Assert/Cover, coverage, regression, and sign-off.
6. Preserve useful source or baseline facts. When reorganizing an existing document, retain stable IDs or record explicit merge/split/removal rationale. Never delete information merely to make the document shorter.
7. Run the current document validator, evidence checks, and Mermaid rendering. Generate a quality report that states unverified evidence and OPEN items.

For a request such as “为 MptChecker 生成完整规格文档”，the user-facing request may remain short. Infer the following execution contract from the repository: `rtls/MptChecker/` is the DUT input, FM-Agent outputs are synchronized to `inputs/MptChecker/fm_agent/`, the latest template governs the document, and the final gates are `make fm-spec-check`, Mermaid rendering, `validate_document.py`, and `make lint`. Ask only for information that cannot be discovered from the repository, such as an ambiguous top module or required configuration.

## Non-negotiable rules

- Evidence priority is matching elaborated RTL, source code, configuration, optional spec, then explicit inference. Conflicts and unverified claims become `OPEN-*`.
- Use the latest template directly. Do not branch behavior on `v2`/`v3` or any previous schema.
- Validate format and internal references, not fixed counts of FC, CK, Case, ports, diagrams, or lines. Counts are descriptive report data only.
- `FG-API` contains environment `Assume` checks only; `FG-COVERAGE` contains `Cover` checks only. Functional DUT behavior is never an environment assumption.
- Every generated FC/CK must have the fields required by the current template, unique visible IDs, an observation point, and evidence or an OPEN reference.
- Use logical interface and transaction names in the main body. Exact flattened Verilog names belong in the I/O appendix and must come from matching generated RTL.
- Do not emit process narration or reader instructions such as “本文档是……”, “推荐阅读……”, or “本版本进行了……”. The result is a formal verification document.
- Do not overwrite versioned documents, reports, history rows, or evidence.

## Long-running FM-Agent stage

FM-Agent hardware-spec generation is an external LLM workflow and commonly takes 20–30 minutes for a non-trivial RTL tree. Before starting it, tell the user that the task is long-running and may consume model API quota/cost. Keep the process attached or monitor its process and `rtls/<Module>/fm_agent/fm_agent.log`; do not restart it merely because there is no output for several minutes. Wait for a real exit status.

When the execution tool has a timeout parameter, choose a window longer than the expected run or run the command in a monitored background session and poll it. Treat log activity, child-process presence, and resource use as progress signals; silence alone is not failure. Do not report success until the command exits with code 0 and the manifest check passes.

Use the wrapper's resumable behavior: `make fm-spec MODULE=<Module>` resumes an existing workspace, while `make fm-spec-fresh MODULE=<Module>` is an explicit full regeneration. If the process is interrupted or the environment fails, preserve the workspace, report the failure and rerun with resume after fixing the cause. Do not treat partial `*_spec.md`/`*_info.md` files as complete inputs; the wrapper manifest and `make fm-spec-check` must pass before consuming them.

## References

Read only the references needed for the current task:

- [document-format-zh.md](references/document-format-zh.md): current Chinese document information architecture and writing rules.
- [dv-testplan.md](references/dv-testplan.md): FG/FC/CK, verification architecture, coverage, cases, and formal contract style.
- [evidence-traceability.md](references/evidence-traceability.md): evidence hierarchy, OPEN handling, versioning, and traceability.
- [source-analysis.md](references/source-analysis.md): extracting transactions, interfaces, parameters, state, timing, and boundaries.
- [profiles/xiangshan.md](references/profiles/xiangshan.md): XiangShan paths, elaboration, cache, and project-specific commands.

Use deterministic repository tools for preflight, RTL generation, rendering, and validation; do not replace them with guessed commands.
