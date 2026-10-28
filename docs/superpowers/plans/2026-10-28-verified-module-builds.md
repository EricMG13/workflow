# Verified Module Builds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working modules first, then connections, then pathways, then orchestration (user, 2026-10-28). A module counts as verified only when all four stages hold for it.

**Architecture:** Each module is one file, `src/deploy_workflow/owners/<cp>.py`.
- **Stage 1** builds its calculation as pure functions, tested against `cases/<slug>-owner/expected.json#cases`.
- **Stage 2** adds the plug-in parts (`probe`, `view`, `submit`, `QUALIFICATION`, `STEP_IDS`, `SCHEMAS`, `RULES`/`precheck` per `docs/G1X-OWNER-CORE-PROTOCOL.md`), the registrations, the block bindings and the consumption proof.
- **Stage 3** renders the module through G2 inside its pathways, with charts.
- **Stage 4** adds receipts, verification on replay and the tamper/forgery cases.

The controller (this session) plans, dispatches and merges, and writes no product code.

**Tech Stack:** Python 3.13.15, pydantic, `Decimal`, pytest, uv. All source is offline. There are no provider calls.

**Spec:** `docs/SPEC.md` plus the frozen leases on `claude/review-wip-worktrees-0145fe`. A lease defines what its module computes. This plan reorders the work across the four stages but does not change what any lease specifies.

## Global Constraints

- **Routing** (user, 2026-10-28; for this lane it overrides AGENTS.md and the global CLAUDE.md):
  - **Implementers.** One fresh `general-purpose` agent with `model: opus` per module per stage, in an isolated worktree. Fix rounds are Opus too; a third round goes to a fresh Opus agent, handed off through files.
  - **Per-module review.** `mx-adversary` reviews every module diff that carries arithmetic, ordering or security code. In Stage 1 it reviews arithmetic correctness against the lease only, not forgery.
  - **Stage review.** `mx-architect` (Fable 5.1) reviews once a whole stage is complete, then fixes and commits its own findings, test-first. Its financial or ordering fixes get an `mx-adversary` check. The user's "stop fable usage" applies to LEAD only; this lane may use Fable.
- **Tests.**
  - Stage 1 calculation tests are pure and take seconds, so they run per module (user, 2026-10-28). A test file whose run exceeds 60 s is not a Stage 1 test.
  - Every heavier run (store, promotion, owner workflow, render) is deferred to Stage 5 under build-first.
  - Static gates `ruff check`, `ruff format --check` and `mypy` always run.
- **Oracles and inputs.**
  - Expected values come only from the frozen `expected.json`, never from code under test.
  - Stage 1 inputs are an explicit typed input object filled from the oracle's own source facts or manifest bindings.
  - There are no stubs in `src`, and no catch-all that hides a failure.
- **Library boundary.** `src/deploy_vii` changes only through a lease's one-line D12 registrations, and only in Stage 2. Its existing engines (for example `cp4_legal.py`, `cp3_relative_value.py`) are called, never edited.
- **Shared files.**
  - `methodology.json` edits go through LEAD's single serialised change; module agents report their edit and do not make it.
  - Workflow Test owns `cases/czr-*/**`, `tests/test_*_case.py` and `tests/test_pathway_*.py`.
- **Concurrency.** At most 10 concurrent subagents.
- **Every report** ends with `Not verified:` and `agent=<name> fix-rounds=<n> gates-first-pass=<y|n>`.

## Review Focus

1. **Zero vs missing.** A missing operand gives "Not calculable …" with a limitation, never 0. Each Stage 1 test asserts the oracle's missing cases.
2. **Decimal exactness.** Quantisation and rounding follow each lease exactly (for example CP-2D's runway is 1 dp half-up, stored quantised). No float appears anywhere in the calculation.
3. **Stage 1 inputs vs Stage 2 store.** The Stage 1 input object must be exactly what Stage 2's adapter can fill from a settled head. Each Stage 1 report lists every input field with its lease source (table id, predicate), and the Stage 1 review checks that list against `manifest.fact_bindings`.
4. **Registration collisions (Stage 2).** Every module edits the same registration lines. Worktrees merge serially, and the Stage 2 review checks the merged tables.
5. **Rendered vs settled (Stage 3).** A rendered block equals `store.head_module(head)` facts; the G2 capture check covers this for each delivery scope.

---

## Stage 1 — Working modules (starts now; no S1a dependency)

Base: `e8ee084` (the lane branch, fast-forwarded to the LEAD tip). Brief template: `work/build/stage1/brief.md`.

| Module | Lease | Oracle | Calculation file | Test file |
|---|---|---|---|---|
| CP-2D Liquidity | `docs/CP2D-OWNER-LEASE.md` | `cases/cp2d-owner/` | `owners/cp2d.py` | `tests/test_method_cp2d.py` |
| CP-2A Downside | `docs/CP2A-OWNER-LEASE.md` | `cases/cp2a-owner/` | `owners/cp2a.py` | `tests/test_method_cp2a.py` |
| CP-2E Macro and FX | `docs/CP2E-OWNER-LEASE.md` | `cases/cp2e-owner/` | `owners/cp2e.py` | `tests/test_method_cp2e.py` |
| CP-1D Earnings quality | `docs/CP1D-OWNER-LEASE.md` | `cases/cp1d-owner/` | `owners/cp1d.py` | `tests/test_method_cp1d.py` |
| CP-3D Market implied | `docs/CP3D-OWNER-LEASE.md` | `cases/cp3d-owner/` | `owners/cp3d.py` | `tests/test_method_cp3d.py` |
| CP-DR Anchored research | `docs/CPDR-OWNER-LEASE.md` | `cases/cpdr-owner/` | `owners/cpdr.py` | `tests/test_method_cpdr.py` |
| CP-4 Legal (existing engine `deploy_vii/cp4_legal.py`) | `docs/CP4-OWNER-LEASE.md` | `cases/cp4-owner/` | `owners/cp4.py` (semantic gate) | `tests/test_method_cp4.py` |
| CP-3 Relative value (existing engine `deploy_vii/cp3_relative_value.py`) | `docs/CP3-OWNER-LEASE.md`, CP-3 half | `cases/cp3-cp6-owner/` | `owners/cp3.py` | `tests/test_method_cp3.py` |

| CP-L10 Screening | `docs/CPL10-OWNER-LEASE.md` (70ec120) | `cases/cpl10-owner/` | `owners/cpl10.py` | `tests/test_method_cpl10.py` |
| CP-1C Peer comparison | `docs/CP1C-OWNER-LEASE.md` (70ec120) | `cases/cp1c-owner/` | `owners/cp1c.py` | `tests/test_method_cp1c.py` |

Queued Stage 1 (frozen at 9bfe85e/859b871; dispatch as slots free):

| Module | Lease | Oracle |
|---|---|---|
| CP-2G Forward cases | `docs/CP2G-OWNER-LEASE.md` | `cases/cp2g-owner/` |
| CP-8 Decision ledger | `docs/CP8-OWNER-LEASE.md` (rev 4) | `cases/cp8-owner/` |
| CP-3C Refinancing and LME | `docs/CP3C-OWNER-LEASE.md` (rev 3) | `cases/cp3c-owner/` |

Plus a CP-1C follow-up: rebase d1103da onto the 9bfe85e oracle (manifest 121a0ab9…, expected e786acb3…, builder e32c8b83…), then assert T1C.1, T1C.8, the universe claim and r13/r14. CP-L10 Stage 2 is held until LEAD freezes its amendment 1.

LEAD amendment 1 (2026-10-28) is running for CP-L10 (F1–F5) and CP-1C (T1C.1 `total` → T1C.8). Until it is re-frozen, Stage 1 tests only the untouched parts: the CP-L10 topic rows and arithmetic, refusals r01–r12, and the CP-1C peer tables T1C.2–T1C.7. A follow-up Stage 1 task adds the amended parts.

For each module:
- [ ] Dispatch the Opus implementer with the brief.
- [ ] It writes the test from the oracle's `cases` first and confirms it fails.
- [ ] It writes the pure calculation, then runs the test file (seconds) and the static gates.
- [ ] It runs confidence-review and commits.
- [ ] `mx-adversary` reviews arithmetic against the lease. Any fix round goes to an Opus agent.
- [ ] Merge into the lane branch.

**Rulings rounds** (LEAD `docs/rulings/2026-10-28-stage1.md`, 2d27e50; a ruling beats the lease). Each module gets one rulings round after its current review returns. The original implementer merges the lane tip, applies its section test-first and runs the reviewer's probes. The round is not counted as a fix round. Review is scoped to the ruling diff: `mx-adversary` for financial arithmetic (CP-2D, CP-2A, CP-1D, CP-1C), `mx-precise` for wording-only rounds (CP-2E, CP-DR, CP-3D). The merged modules (CP-2E, CP-DR, CP-3D) are reworked on their own branches and merged again.

| Module | Rulings | Notes |
|---|---|---|
| CP-2E | E1–E5 | merged; rework on branch |
| CP-2A | A1–A8 | A5 replaces the v02 strict xfail; A7 removes the positive-interest refusal |
| CP-3D | D1–D3 | merged; X1 (five raising shapes) waits for round 2 |
| CP-DR | R1–R3 | merged; rework on branch |
| CP-2D | 2D1–2D9 | 2D1 substring match (not word boundary); 2D9 financing total; zero debt not_applicable |
| CP-1C | 1C1–1C6 | folded into the running fix 1 |
| CP-1D | 1D1–1D10 | 1D3 settles (no raise); 1D1 oracle amendment lands after methodology |
| CP-4 | 4-1 | wait for LEAD's oracle commit |

LEAD round 2 is pending: X1 (CP-3D), L10-a/b/c, C1–C3, and the 1D2 basis-limitation follow-up. Those cases fail closed until it arrives. `methodology.json`: merge `lead/methodology-serialised` when LEAD sends the commit, before the Stage 2 builds of CP-L10, CP-1C, CP-1D and CP-2A. No module build edits it.

Then:
- [ ] **Stage 1 review.** Fable checks every module's calculation against its lease, the input-field lists against `manifest.fact_bindings`, and that nothing reaches into a store, the host or a renderer. It fixes and commits, test-first.

Other modules join Stage 1 once LEAD freezes their leases: CP-1C, CP-L10, CP-8, CP-2G, CP-3C, the CP-6 half of CP-3, then CP-2H, CP-4C, CP-3B and CP-6A. CP-OS is navigation, not a calculation, so it starts in Stage 3.

## Stage 2 — Connections (needs S1a integrated)

S1a deferral (the user, to LEAD, 2026-10-28: "After fix-4"):
- LEAD integrates S1a after fix round 4, if its genuine-path probes pass, and then sends the integration SHA and the deferred-findings list.
- The adversary review that follows does not block G1-X. Anything it finds goes to Stage 4.

- [ ] **G1-X.** One Opus agent, brief `work/build/g1x/brief.md`, rebased on the S1a integration commit, then `mx-adversary`.
- [ ] **H1.** `_SOURCE_STEPS["CP-3"]`, the `*-submission` producer rule and the fixed source mappings for CP-DR, CP-1D and CP-3D (`work/lead/cp3-cp6-owner-preparation/review-precise-r3-1.md` Q6).
- [ ] **Per module.** One Opus agent per module adds three things:
  - the plug-in parts and a store adapter (settled head → Stage 1 input object);
  - the `owner_workflow.py` registrations, `bindings/<cp>.py`, `shipped.py` and `_Spec` rows;
  - the run driver (`tests/<cp>_runs.py`) with consumption proof (D3), as the lease lists it.

  It reports any `methodology.json` edit to LEAD's serialised change. `mx-adversary` reviews, and modules merge serially.
- [ ] **CP-2D notes** (LEAD):
  - CP-1 T4.13 has no consumers on the S1 store, so `earnings_quality_metrics` reads `not_ready` unless the run's CP-1 readiness literal assesses CP-2D.
  - A stale, not blocked, required head re-raises at begin (`owner_workflow.py:452-456`), so lease :99 holds only for the blocked half.
- [ ] **Stage 2 review.** Fable checks the full connection chain on the merged branch:
  1. core seams = protocol §2
  2. registration rows
  3. CP-0 consumer delta and upstream edges = `methodology.json`
  4. binding slot → block id → `_Spec` (unique per block id) → `DELIVERY_SCOPES`
  5. consumption proof (D3)

  It fixes and commits its own findings.

## Stage 3 — Pathways

- [ ] **G2.** `owner_rendering.py` per `docs/OWNER-RENDERING-LEASE.md`, with one `DELIVERY_SCOPES` row per module run.
- [ ] **CP-OS.** Per `docs/CPOS-OWNER-LEASE.md`, re-pinned at `e8ee084`. `#workbench` resolves via routeOf.
- [ ] **Charts.** Fable lists the series blocks from Stage 1 (for example CP-2D T2E.4 maturity wall and T2E.3 runway). LEAD freezes chart oracles following `docs/CP1-CHART-SLICE.md`, and one Opus agent wires each frozen chart.
- [ ] **Real-data case.** Workflow Test's `cases/czr-2026q2-earnings-update/` (CP-1, CP-1B, CP-2, CP-5 on `earnings_update`) needs LEAD's ruling on a public multi-document `case_kind` and its scope. One Opus agent then builds its run driver, and Workflow Test runs it.
- [ ] **Stage 3 review.** Fable checks each of the six pathways renders its assigned blocks from settled facts, then fixes and commits.

## Stage 4 — Orchestration

- [ ] **Receipt hardening.** The receipt verifier's tamper and forgery cases (S1a's adversary findings, B1-class hardening) and each module's `tamper`/`refusals`/`tool_use` oracle sections. This stage owns them, if LEAD accepts the deferral proposed on 2026-10-28.
- [ ] **Stage 4 review.** Fable reviews, then fixes and commits.

## Stage 5 — Final verification

- [ ] **5.1** Run every command in `work/build/deferred-runs.md` (no heavy-job lock since the user removed it on 2026-10-28). Log each run in `work/build/ledger.md`.
- [ ] **5.2** Native DOM proof for each delivery scope and the CP-OS nav rows.
- [ ] **5.3** Whole-branch Fable review that fixes failures test-first, then `confidence-review` and `rewrite-tournament` on the branch diff.
- [ ] **5.4** PM integrates the branch. LEAD updates `docs/MODULES.csv`.
