---
name: xiangshan-design-document
description: Use when generating, regenerating, or reviewing XiangShan module design documents from chip_design_document_template_zh.md, XiangShan Chisel/Verilog source, and optional module spec files, including Sbuffer, ICache, DCache, MMU, frontend, backend, and memory modules.
---

# XiangShan Module Design Document

Generate an evidence-based Chinese design and functional-checkpoint document for one XiangShan DUT. Produce both the design document and a quality review. Do not treat an optional spec as authoritative over source code.

## Repository Contract

Resolve all paths from the documentation repository root:

| Asset | Path |
| --- | --- |
| Template | `templates/chip-design-document/chip_design_document_template_zh.md` |
| XiangShan source | `third_party/XiangShan/` |
| Optional module specs | `inputs/<Module>/` |
| Versioned design document | `outputs/<Module>/<Module>_design_document_zh_v<MAJOR.MINOR.PATCH>.md` |
| Versioned quality report | `reports/<Module>/<Module>_document_quality_review_v<MAJOR.MINOR.PATCH>.md` |
| Version history | `outputs/<Module>/VERSION_HISTORY.md` |
| Versioned RTL evidence | `evidence/<Module>/<version>/manifest.json` and `ports.csv` |
| Cross-platform tooling | `tools/preflight.sh`, `tools/generate_rtl.sh`, `tools/validate_document.py` |

Create the module-specific input, output, and report directories when needed. Do not put generated files at repository root. Do not modify XiangShan source merely to make documentation generation easier.

## Document Versioning

Every generated design document and its quality report must have one shared semantic document version. A generated artifact without a version in both its filename and document-control table is invalid.

The template has its own visible `模板结构版本`. Record that value in the generated document as `使用模板版本`. A backward-incompatible template structure change is evidence for a document MAJOR increment; do not infer this from the template modification date alone.

Use `vMAJOR.MINOR.PATCH`, for example `v1.2.3`. This is the documentation version, not the XiangShan RTL version. Record the XiangShan commit and configuration separately.

### Version Selection

Before drafting, inspect:

- `outputs/<Module>/VERSION_HISTORY.md` when present.
- All versioned design documents under `outputs/<Module>/`.
- All versioned quality reports under `reports/<Module>/`.
- Any unversioned legacy output for comparison only.

Choose exactly one next version:

| Increment | Use when |
| --- | --- |
| `MAJOR` | The DUT scope or identity changes incompatibly, or a template/schema change makes the document structure incompatible with prior versions. |
| `MINOR` | Behavior coverage changes: interfaces, parameters, states, FG/FC/CK, scenarios, or supported configurations are added, removed, or semantically changed; a new RTL baseline changes documented behavior. |
| `PATCH` | Facts, evidence, line references, wording, diagrams, OPEN closure, formatting, or quality findings change without changing the documented behavioral contract. Also use PATCH for an intentional regeneration with no semantic change. |

Rules:

- The first versioned document for a module is `v1.0.0`, even when unversioned legacy files exist.
- If the user explicitly requests a valid version greater than all existing versions, use it and record the reason. Reject reuse or downgrade of an existing version unless the user explicitly asks to replace history.
- Every generation creates a new version. Never overwrite an older versioned document or report.
- The design document and quality report must use the same version.
- Compare against the immediately preceding version and summarize actual differences. Do not infer a change category only from timestamps.
- A newer XiangShan commit does not automatically require MAJOR. Classify by the resulting document contract, normally MINOR for behavioral change and PATCH for evidence-only change.

### Required Version Metadata

Add these rows to the design document's `文档控制与依据` table:

| Field | Required value |
| --- | --- |
| 文档版本 | `vMAJOR.MINOR.PATCH` |
| 使用模板版本 | Exact `模板结构版本` read from the template |
| 前一版本 | Previous version and relative link, or `None（首次版本）` |
| 版本变更类型 | `Major / Minor / Patch` plus a short reason |
| XiangShan RTL 基线 | Full submodule commit, not an abbreviated hash |
| 适用配置 | Exact selected configuration and feature switches |
| 生成日期 | ISO `YYYY-MM-DD` |

Put the version directly below the H1 as visible text: `> 文档版本：vMAJOR.MINOR.PATCH`.

The quality report must state its own version, the reviewed design-document version/path, the previous version/path, and a version-to-version change summary grouped as added, changed, fixed, removed, and remaining OPEN items.

Maintain `outputs/<Module>/VERSION_HISTORY.md` with newest version first:

| 版本 | 日期 | XiangShan commit | 配置 | 变更类型 | 摘要 | 设计文档 | 质量报告 |
| --- | --- | --- | --- | --- | --- | --- | --- |

Use relative links from `VERSION_HISTORY.md`. Add exactly one row per generated version. Never rewrite an older row except to repair a broken path or an objectively incorrect metadata value, and record such a repair in the new quality report.

## Required Inputs

The user must identify a DUT by Chisel class, desired Verilog module name, or functional module name. If several classes plausibly match, inspect them and ask one focused question only when source evidence cannot disambiguate the intended top.

Always use:

1. The current document template.
2. The checked-out XiangShan submodule source and its exact Git commit.
3. Elaborated Verilog/SystemVerilog from that same commit and the selected configuration when exact Verilog I/O is claimed.

Specs under `inputs/<Module>/` are optional. Use them to discover intent, terminology, expected scenarios, and possible missing behavior. Validate every implementation claim against source.

## Evidence Order

Use this order for implementation facts:

1. Elaborated Verilog/SystemVerilog from the documented commit and configuration: exact module and flattened port names, directions, widths, generated structures.
2. Chisel/Scala source: Bundle classes, object paths, parameter definitions, state machines, register updates, priorities, assertions, feature guards.
3. XiangShan configuration source and build invocation: parameter values and enabled features for the selected target.
4. Existing module spec: design intent and verification suggestions.
5. Inference: only as an explicit `OPEN-*`, never as a FACT.

When sources conflict, report the conflict. Do not silently choose the spec over RTL. A comment is weaker evidence than executable code. A generated port from a different commit or configuration is not valid evidence.

## Workflow

### 0. Preflight the Environment

Before source analysis or elaboration, run:

```bash
./tools/preflight.sh --module <Module> --config <Config> --strict --document-tools
```

This workflow supports Linux and macOS. Do not assume Homebrew, GNU `time`, x86-64, a system-wide Java, or a system-wide Mill installation. The project scripts bootstrap Temurin JDK 17 when needed, bootstrap the XiangShan-pinned Mill, and select/build a native Espresso for the host OS and architecture.

If preflight fails, resolve missing Java 17, Git, Curl, Make, C compiler, Python 3, nested submodules, configuration, disk space, or dirty-source issues before elaboration. Do not discover these failures halfway through a full-chip generation.

### 1. Establish the Baseline

- Determine the next document version before writing and identify the immediately preceding version used for comparison.
- Record the XiangShan submodule commit with `git -C third_party/XiangShan rev-parse HEAD`.
- Record dirty status. A dirty submodule requires listing relevant modified files in the document baseline.
- Identify the selected XiangShan configuration and all feature switches affecting the DUT.
- Read the full template before drafting.
- Read every Markdown file under `inputs/<Module>/` if the directory exists.

Do not reuse FACT or OPEN conclusions from an older output without rechecking them against the current baseline. Build a concrete change list against the previous version while reviewing evidence.

### 2. Discover the Complete Source Boundary

Locate the DUT class and recursively inspect:

- Base classes and mixed-in traits.
- Top-level `IO(...)`, named or anonymous Bundle definitions, nested Bundle classes, Vec dimensions, Flipped direction changes, and Decoupled/Valid protocols.
- Instantiated child modules and the source files defining them.
- Parameter/config keys and derived constants.
- Top-level state register and transition logic.
- Arrays, queues, SRAMs, CAMs, counters, arbitration, flush/replay/error handling, assertions, and optional instrumentation.

Search by class name, `Module(new ...)`, Bundle type, parameter name, and interface type across `third_party/XiangShan/src`. Do not assume all relevant definitions are in the DUT file.

For anonymous top-level Bundles, write `anonymous Bundle in <Class>.io` rather than inventing a class such as `<Class>IO`. Record the exact enclosing source location.

### 3. Build the I/O Mapping

The I/O chapter must include both levels:

- Chisel: enclosing Bundle class, object path, field path, direction after `Flipped`, Chisel type, dimensions, and Scala `path:line`.
- Verilog: exact elaborated port name, direction, and width.
- Configuration status: whether the Chisel field exists, whether the selected configuration emitted a Verilog leaf, and why it was generated, constant-folded, feature-disabled, or dead-port-eliminated.

Map every externally visible leaf, including each generated Vec element. A summary row may group a regular array only when the exact naming pattern and index range are demonstrated by the generated RTL.

Never derive a Verilog name solely from a Chisel path. Firtool naming, flattening, deduplication, prefixes, and configuration can change it. If matching elaborated RTL is unavailable:

- Put `OPEN-IO-<N>` in every unverified Verilog field.
- State the missing generation command/configuration/artifact.
- Mark I/O signoff blocked.
- Do not use examples such as `io_enq_0_valid` as if they were facts.

Prefer versioned evidence or a matching cache. Generate missing RTL only through:

```bash
./tools/generate_rtl.sh --module <Module> --config <Config> --version <version>
```

The wrapper uses the XiangShan TopMain flow without assuming GNU `time`, caches the full split RTL by commit/config/generator/tool/platform fingerprint for reuse across modules, restores any temporary native Espresso substitution, sets integration paths required by generation, and writes persistent `manifest.json` plus `ports.csv`. Do not hand-roll an equivalent command unless the wrapper itself is broken; if that happens, fix the wrapper and record the failure.

Do not replace existing version evidence during normal generation. `--replace-evidence` is reserved for an explicitly documented repair of objectively incorrect metadata or a broken artifact; it does not permit changing historical RTL evidence silently.

A nonzero full-top exit may still leave a complete split module RTL. Accept it only when the selected module file parses successfully, the manifest marks `generation_status: partial`, the failure occurred after RTL emission, and the quality report explains the downstream failure. Never call the full top generation successful in that case.

### 4. Extract Parameters

Keep parameters in their own chapter. For each parameter include:

- Name and Scala type.
- Literal/default/configured value or legal range.
- Declaration/config-key `path:line`.
- Important use `path:line` when different.
- Elaboration-time or runtime effect.
- Observable functional consequence.

Separate derived constants and formal harness parameters. Do not list queues, registers, state values, or resources as parameters. If a configured value cannot be resolved, preserve the expression and create `OPEN-PARAM-*`.

### 5. Extract Only the Top-Level FSM

The dedicated state chapter contains only the DUT's top-level FSM:

- State table with exact Scala state definition and transition evidence.
- Mermaid state diagram in the same chapter.
- Reset entry, transition conditions, simultaneous-event priority, and externally visible restrictions.

Do not promote per-entry Boolean combinations, queue occupancy, child-module FSMs, replay flags, or protocol phases into top-level states. Describe those under resources or the relevant FC.

### 6. Draw the Architecture Boundary

The Mermaid architecture diagram must contain:

```mermaid
flowchart LR
    subgraph DUT["DUT: <Module>"]
        INTERNAL[Internal resource]
    end
```

Every edge crossing the `DUT` subgraph boundary must name a Chisel interface object from the I/O chapter. Add the verified Verilog port prefix only when elaborated RTL proves it. Include all external peers, key internal resources, selection/arbitration points, data paths, and control/recovery paths. Use solid edges for transaction/data flow and dashed edges for control/cancel/error flow.

Keep the state diagram with the state table. Add a sequence diagram when a transaction crosses modules or has response/replay/flush races.

Mermaid source must avoid parser-sensitive text in identifiers and edge labels. In particular, do not put `[i]`, `[x]`, wildcard `*`, semicolons, or subgraph IDs used as edge endpoints inside diagrams. Use human-readable labels such as `enqueue requests 0 and 1`; keep exact Chisel/Verilog patterns in the I/O table.

After writing or changing any Mermaid fence, render every diagram through the pinned workflow:

```bash
make render MODULE=<Module> VERSION=<version>
```

This must create `evidence/<Module>/<version>/diagrams/manifest.json` and nonblank SVG files. A balanced fence or Mermaid-looking source is not sufficient. Never report diagrams as passed when a real renderer was unavailable.

### 7. Define FG, FC, and CK

Follow the current template exactly.

- Render labels visibly with backticks: `` `<FG-NAME>` ``, `` `<FC-NAME>` ``, `` `<CK-NAME>` ``. Bare angle-bracket labels can disappear as HTML.
- Give every FC a natural-language paragraph before its tables. Explain purpose, trigger, processing, observable result, and boundary behavior.
- Present the FC contract in an FC table.
- Present CKs in a separate CK table with label, Style, independent property, observation point, and source evidence.
- Use only `Comb`, `Seq`, `Seq, Symbolic`, `Assume`, or `Cover` styles accepted by the template.
- Keep API checks as environment Assume only. Never assume DUT outputs are correct.
- Keep Coverage checks as Cover only.
- Split a priority chain into independently checkable adjacent-priority properties.
- Add frame conditions for every cross-cycle update, including non-target symbolic stability for multi-entry storage.
- Parameter/feature gating requires both enabled behavior and disabled no-side-effect checks.
- Use reviewed harness parameters for unknown latency. Never write vague timing such as “later” or “after taking effect.”

Before finalizing, ensure the label tree, FC rows, CK rows, property contract table, and traceability table agree.

### 8. Add Scenario Cases

The appendix must contain user-story cases covering at least:

1. A normal end-to-end transaction.
2. A resource boundary or backpressure condition.
3. An error, replay, flush, cancellation, or recovery path when the DUT supports one.

Each case includes actors, preconditions, Chisel/Verilog inputs, expected outputs, ordered steps, related FC/CK, an exceptional branch, and measurable acceptance criteria. Cases explain collaboration across FCs but do not replace formal CKs.

### 9. Produce the Quality Report

Create `reports/<Module>/<Module>_document_quality_review_v<MAJOR.MINOR.PATCH>.md` in the same run. Report:

- Document version, previous version, selected increment, and why that increment is correct.
- Added, changed, fixed, removed, and still-open differences from the immediately preceding version.
- Baseline commit, configuration, source files, generated RTL artifact, and optional specs used.
- Host OS/architecture, preflight result, Java/Mill/firtool/Espresso versions, cache fingerprint, generation exit status, RTL hash, evidence manifest, and port counts.
- Mermaid CLI/browser versions, actual render result, diagram count, rendered SVG evidence, and any parser/render failure fixed during the run.
- What spec claims were confirmed, corrected, rejected, or left OPEN.
- I/O mapping completeness, including counts of mapped and open leaf ports.
- Parameter source completeness.
- Top-level FSM and diagram consistency.
- FG/FC/CK counts, duplicate-label result, and Style validity.
- Normal, boundary, and recovery case coverage.
- Commands/checkers run and failures or unrun validations.
- Blocking OPEN items and the exact evidence needed to close each one.

When executable RTL contradicts a spec/comment or appears suspicious:

- Record `规格/注释期望` separately from `RTL 实际行为`.
- Create `OPEN-BEHAV-*` or `OPEN-BUG-*`; do not normalize the behavior into an intended requirement.
- Functional CKs describe the observed RTL contract unless the user explicitly requests a proposed/fixed design contract.
- Add a review-only checkpoint or signoff item for design intent; do not encode the suspected bug as an environment Assume.

Do not award a perfect score when exact Verilog I/O, source locations, Markdown rendering, UCAgent parsing, or SVA compilation has not been verified.

## Static Validation

Before completion, run:

```bash
./tools/validate_document.py --module <Module> --version <version> --strict-evidence
make lint MODULE=<Module> VERSION=<version>
```

The checker is the minimum gate. Also check:

- Design filename, report filename, visible header version, document-control version, report version, and history row all match exactly.
- The selected version is greater than every existing module version and no older versioned file was overwritten.
- `VERSION_HISTORY.md` contains one new row with valid relative links to both artifacts.
- Required chapters from the template exist.
- Every FG/FC/CK label is visible and unique.
- Every FC in the tree has one FC table row, a preceding natural-language paragraph, and at least one CK.
- Every CK has a legal Style, observation point, and evidence.
- API contains only Assume; Coverage contains only Cover.
- Mermaid fences are balanced and architecture contains the DUT subgraph.
- Every Mermaid fence has current source-hash-matched render evidence, and `make lint` successfully re-renders all diagrams with the pinned CLI.
- State table and state diagram use the same top-level states.
- Every cross-boundary architecture edge appears in the I/O chapter.
- Every exact Verilog port cited exists in the matching generated RTL.
- Chisel-present but Verilog-elided fields explicitly state selected-config status and evidence; absence is not silently treated as an I/O omission.
- Every Scala path and line reference exists at the recorded submodule commit.
- Output and report links resolve after writing.

Use parsers or repository search for these checks instead of visual counting. If UCAgent checker or Mermaid renderer is unavailable, state that explicitly in the quality report.

## Completion Standard

The task is complete only when the versioned design document, same-version quality report, updated `VERSION_HISTORY.md`, versioned RTL evidence, current Mermaid SVG/manifest evidence, and checker/lint results are written. Exact Verilog I/O and actual diagram rendering are hard evidence requirements. When elaboration or rendering is unavailable, the document status must remain Draft and the corresponding signoff must remain blocked.
