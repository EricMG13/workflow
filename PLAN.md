# Deploy Workflow Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for each bounded role
> assignment; use subagent-driven-development when the authorized role delegates.
> Task steps use checkboxes. The user has authorized this new project/team and scope.

**Goal:** All intended analytical modules demonstrate permitted tool-assisted execution,
validated output, actual downstream consumption and assigned rendered deliverables.
**Architecture:** Reuse the selected Claude core through small explicit host/tool
interfaces. Preserve its financial meaning; add missing owners and bindings in
connected slices. A single module matrix and queue govern work.
**Tech Stack:** Python 3.13.15, uv 0.12.5, Pydantic, pypdf, openpyxl and existing HTML.
**Spec:** [docs/SPEC.md](docs/SPEC.md).

## Global constraints

24 analytical owners plus deterministic CP-MODEL/CP-OS; six pathways; Python arithmetic;
scoped source/upstream access; independent oracles; no review-file-only completion.
Sol/high for financial/stateful code; Luna/medium mechanics. Paid testing paused.
One heavy job and two disjoint implementation lanes. AGENTS.md contains full rules.

## Review focus

- Failed reads must not credit evidence that was never returned; preserve earlier reads.
- Wrong/stale/unselected source or producer identities must refuse without disclosure.
- Zero, missing and blocked financial values must retain distinct values/status.
- Retried submissions must not double-settle or silently lose citations/lineage.
- Rendered cells must match independently expected units/periods/citations and producer IDs.

## Task 0 — LEAD: freeze the first interface and cases

Files: docs/TOOL-CONTRACT.md, cases/source/manifest.json, cases/upstream/manifest.json,
docs/MODULES.csv, docs/QUEUE.md. C1/C2 own the eventual fixture source/test files.
Consumes: docs/SPEC.md and pinned reuse manifest. Produces: exact source and upstream
tool contracts plus independent positive/refusal expectations and exclusive assignments.

- [ ] Inspect selected source functions and known risks; do not rediscover every old plan.
- [ ] Freeze the first source session and upstream invocation/result/lineage envelope.
- [ ] Define explicit identity/scope/limit/error behavior and expected positive/failure records.
- [ ] Independent Sol/high checks sensitive expectations. Publish the concise first leases.

## Task 1 — C1: safe source tools through a supported host interface

Files: src/deploy_workflow/tools/source.py, src/deploy_workflow/tools/__init__.py,
src/deploy_workflow/host.py, tests/test_source_tools.py; named narrow correction to
src/deploy_vii/live/tools.py only if the known failed-render mutation is confirmed.
Consumes: pinned PackTools/ToolRules and Task0 schema. Produces: a fixed host callable
that exposes only the admitted step's source search/read/extraction, with actual
invocation/result and submission binding. No general shell/Python execution interface.

- [ ] Pin independent source/locator/quote facts from synthetic raw bytes before candidate output.
- [ ] Add causal refusal/failed-render/prior-success preservation cases; reproduce before fixing.
- [ ] Sol/high implements the smallest adapter and any confirmed evidence mutation fix.
- [ ] Run the focused cases and import/scope checks under owned resource admission.
- [ ] Complete confidence review, required rewrite workflow and independent sensitive review.
- [ ] Return exact commit/files/commands/results and a demonstrable real host invocation.

## Task 2 — C2: bounded frozen lookup and verification

Files: src/deploy_workflow/tools/upstream.py, tests/test_upstream_tools.py.
Consumes: Task0 envelope and existing live.context projections, CP5 python_checks,
readiness citation checks and quote matching. Produces: exact permitted producer/
table/field lookup and read-only verification with actual invocation/result records.

- [ ] Independently pin a frozen producer value and identity; define stale/foreign/hidden-field refusals.
- [ ] Add scoped success/refusal tests before the adapter; no raw pack permission to upstream-only roles.
- [ ] Sol/high wraps existing typed projections/checks without another arithmetic engine.
- [ ] Verify returned values/status/citations and fail-closed disclosure behavior.
- [ ] Complete code review workflows and hand off its exact interface/commit to C1/LEAD.

## Task 3 — first connected source-to-rendered slice

C1 owns src/deploy_workflow/workflow.py and actual owner dispatch/submission;
C2 owns src/deploy_workflow/rendering.py and tests/test_connected_render.py.
Shared API changes require LEAD's exclusive handoff. Use actual CP0→CP1→CP4→CP5
producers as applicable, then deterministic Model publication. Initial tool delivery
can be demonstrated before all downstream owners finish, but is not full completion.

- [ ] Freeze coherent financial/legal raw sources and independently calculated expected output.
- [ ] Use actual supported analyst tool invocations; retain the resulting review/submission lineage.
- [ ] Execute real validators/composers/settlement and real downstream reads, not injected final modules.
- [ ] Render actual selected-run values, citations/status and source/provenance links; verify visible DOM.
- [ ] Close applicable matrix rows only after all required links are evidenced.

## Task 4 — complete earnings and specialist owners in small slices

C1 queue: CP1B, CP1C, CP1D, CP2/3 typed consumption, CP3D, CP2E.
C2 queue: CP2D→CP3C; CP2A→CP2G→CP2H; CP4 versioned duties→CP4C.
Each owner receives a separate exact file/interface/case lease before code.

- [ ] Add each missing owner using its source-method requirements and independent oracle.
- [ ] Connect its tools, real output, selected consumer and assigned section before claiming it complete.
- [ ] Demonstrate earnings, relative-value, covenant/refinancing and distress pathways incrementally.

## Task 5 — portfolio, research, terminal owners and assembled proof

C1 queue: distinct CP3B/CP6A, CP8 and CPL10. C2 queue: minimal anchored LOCAL CPDR,
CPOS navigation and remaining real section bindings. PR MANAGER owns integration.

- [ ] Implement only minimal necessary version/attachment safety for named owners.
- [ ] Demonstrate all 26 rows across six independent representative pathways.
- [ ] Compare actual tool→artifact→consumer→visible-output evidence with the frozen expectations.
- [ ] Run applicable assembled checks once per supported candidate; retain failures/skips honestly.
- [ ] Produce the working run guide and a separate enterprise/production handoff backlog.

## Progress and completion

Report named modules with tool use / real output / consumer connection / rendered
section / representative-case verification. No invented percentage. Historical
passes and imported files start as reuse evidence only. Current status lives in
MODULES.csv and QUEUE.md. The user requested a LEAD/team execution arrangement;
keep that method and do not restart a planning/approval chain for this bootstrap.
