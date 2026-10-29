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
  - **Implementers.** Stage 1: one fresh `general-purpose` agent with `model: opus` per module, in an isolated worktree; its fix rounds are Opus too. Stages 2-4 (AGENTS.md 423a06e, user, 2026-10-28): one `mx-feature` (Sonnet) implementer per module, and `mx-feature` for its fix rounds; no Opus implementers. At most six Opus agents at once (AGENTS.md e069df7).
  - **Per-module review.** `mx-adversary` reviews every module diff that carries arithmetic, ordering or security code. In Stage 1 it reviews arithmetic correctness against the lease only, not forgery.
  - **Stage review** (AGENTS.md 423a06e, which replaces the earlier "this lane may use Fable" exception). Stages 1 and 2: an Opus reviewer (`mx-precise` or `mx-autonomous`), read-only; its findings go to a fix round. Stage 3: `mx-architect` (Fable) may do the one end-of-stage check that every pathway renders its assigned blocks. Stage 4: Fable writes one class-level plan (verify by replaying the producer's rules, within the threat model's limits) and does the end-of-stage review; it writes no code, and `mx-autonomous` stands in if Fable has no credits. Those are the only Fable uses left for this lane. Diffs that only apply LEAD's ruling text are checked by `mx-feature`.
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
- [x] Dispatch the Opus implementer with the brief.
- [x] It writes the test from the oracle's `cases` first and confirms it fails.
- [x] It writes the pure calculation, then runs the test file (seconds) and the static gates.
- [x] It runs confidence-review and commits.
- [x] `mx-adversary` reviews arithmetic against the lease. Any fix round goes to an Opus agent.
- [x] Merge into the lane branch.

**Rulings rounds** (LEAD `docs/rulings/2026-10-28-stage1.md`, 2d27e50; a ruling beats the lease). Each module gets one rulings round after its current review returns. The original implementer merges the lane tip, applies its section test-first and runs the reviewer's probes. The round is not counted as a fix round. Review is scoped to the ruling diff: `mx-adversary` for financial arithmetic (CP-2D, CP-2A, CP-1D, CP-1C), `mx-precise` for wording-only rounds (CP-2E, CP-DR, CP-3D). The merged modules (CP-2E, CP-DR, CP-3D) are reworked on their own branches and merged again.

| Module | Rulings | Notes |
|---|---|---|
| CP-2E | E1–E5 | merged; rework on branch |
| CP-2A | A1–A8 | A5 replaces the v02 strict xfail; A7 removes the positive-interest refusal |
| CP-3D | D1–D3, X1 (i)–(v) | merged; rework on branch; the five shapes get claim wording, none raises |
| CP-DR | R1–R3 | merged; rework on branch |
| CP-2D | 2D1–2D9, 2D-a–d | 2D-a: substring match only over analyst fields; 2D-b/c/d: missing operands, facility terms and cross-check mismatches settle; 2D9 financing total |
| CP-1C | 1C1–1C6, C1–C3, 1C-x | folded into the running fix 1; C2 overrides the builder |
| CP-1D | 1D1–1D10, 1D2 follow-up, 1D-x | 1D3 settles (no raise); 1D1 oracle amendment lands after methodology |
| CP-4 | 4-1 | b658bc1 approved and merged (056b355); re-pin to 7328203 (expected 154fc2d0…, builder 71cf0758…) dispatched |
| CP-L10 | L10-a, L10-c | folded into the running amendment-1 fix; L10-b `methods/cpl10.md` note goes to Stage 2 |

LEAD round 2 is committed at 842c911 (merged d9cada2), and round 3 at f5ee633 (merged 2b4b393). Stage 2 `methods/<cp>.md` notes: cp1d (1D4), cpl10 (L10-b), cp2d (2D-a stem list). CP-4 T4C.7 `stated_value` display is open in QUEUE for the CP-4 build (engine-side; owner decides). `methodology.json`: merge `lead/methodology-serialised` when LEAD sends the commit, before the Stage 2 builds of CP-L10, CP-1C, CP-1D and CP-2A. No module build edits it.

Then:
- [x] **Stage 1 review.** An Opus reviewer (`mx-precise` or `mx-autonomous`) checks every module's calculation against its lease, the input-field lists against `manifest.fact_bindings`, and that nothing reaches into a store, the host or a renderer. Its findings go to the module's implementer as a fix round.

Other modules join Stage 1 once LEAD freezes their leases: CP-1C, CP-L10, CP-8, CP-2G, CP-3C, the CP-6 half of CP-3, then CP-2H, CP-4C, CP-3B and CP-6A. CP-OS is navigation, not a calculation, so it starts in Stage 3.

## Stage 2 — Connections (needs S1a integrated)

Closed 2026-10-29: the Stage 2 close release `claude/s2-release` ab9777f merged into the lane at 7249a64 (fast set, S1a, render suites and `test_source_tools.py` exit 0; reviews in `work/build/stage2/release/`).

S1a deferral (the user, to LEAD, 2026-10-28: "After fix-4"):
- LEAD integrates S1a after fix round 4, if its genuine-path probes pass, and then sends the integration SHA and the deferred-findings list.
- The adversary review that follows does not block G1-X. Anything it finds goes to Stage 4.

- [x] **G1-X.** One Opus agent, brief `work/build/g1x/brief.md`, rebased on the S1a integration commit, then `mx-adversary`.
- [x] **H1.** `_SOURCE_STEPS["CP-3"]`, the `*-submission` producer rule and the fixed source mappings for CP-DR, CP-1D and CP-3D (`work/lead/cp3-cp6-owner-preparation/review-precise-r3-1.md` Q6).
  - H1 also stops `host._execution_state` (host.py:645) from calling `step_chain` for owner-only modules; a `_SOURCE_STEPS` row alone is not enough (protocol §5, LEAD 4d709bf; G1-X adversary L3, `work/build/g1x/review-adversary.md`).
- [x] **Per module.** One `mx-feature` (Sonnet) agent per module adds three things:
  - the plug-in parts and a store adapter (settled head → Stage 1 input object);
  - the `owner_workflow.py` registrations, `bindings/<cp>.py`, `shipped.py` and `_Spec` rows;
  - the run driver (`tests/<cp>_runs.py`) with consumption proof (D3), as the lease lists it.

  It reports any `methodology.json` edit to LEAD's serialised change. `mx-adversary` reviews the store adapter and the consumption proof; `mx-precise` reviews the rest. Fix rounds go to `mx-feature`. Modules merge serially.
- [x] **CP-2D notes** (LEAD):
  - CP-1 T4.13 has no consumers on the S1 store, so `earnings_quality_metrics` reads `not_ready` unless the run's CP-1 readiness literal assesses CP-2D.
  - A stale, not blocked, required head re-raises at begin (`owner_workflow.py:452-456`), so lease :99 holds only for the blocked half.
- [x] **Stage 2 review.** An Opus reviewer (`mx-precise` or `mx-autonomous`) checks the full connection chain on the merged branch:
  1. core seams = protocol §2
  2. registration rows
  3. CP-0 consumer delta and upstream edges = `methodology.json`
  4. binding slot → block id → `_Spec` (unique per block id) → `DELIVERY_SCOPES`
  5. consumption proof (D3)

  Its findings go to `mx-feature` fix rounds.

## Stage 3 — Pathways

- [ ] **G2.** (`mx-feature` builds, `mx-precise` reviews.) `owner_rendering.py` per `docs/OWNER-RENDERING-LEASE.md`, with one `DELIVERY_SCOPES` row per module run.
- [ ] **CP-OS.** (`mx-feature` builds, `mx-precise` reviews.) Per `docs/CPOS-OWNER-LEASE.md`, re-pinned at `e8ee084`. `#workbench` resolves via routeOf.
- [ ] **Charts.** The series blocks are listed in `work/build/stage3/charts-inventory.md` (for example CP-2D T2E.4 maturity wall and T2E.3 runway); the oracles to freeze and the rulings still open are in `work/build/stage3/questions.md`. LEAD freezes chart oracles following `docs/CP1-CHART-SLICE.md`, and one `mx-feature` agent wires each frozen chart; `mx-precise` reviews.
- [ ] **Real-data case.** Workflow Test's `cases/czr-2026q2-earnings-update/` (CP-1, CP-1B, CP-2, CP-5 on `earnings_update`) needs LEAD's ruling on a public multi-document `case_kind` and its scope. One `mx-feature` agent then builds its run driver, and Workflow Test runs it.
- [ ] **Stage 3 review.** `mx-architect` (Fable) checks that each of the six pathways renders its assigned blocks from settled facts. Findings go to `mx-feature` fix rounds.

## Stage 4 — Orchestration

Fable writes one class-level plan first (verify by replaying the producer's rules, within the threat model's limits) and writes no code; `mx-feature` implements, `mx-adversary` attacks. `mx-autonomous` stands in if Fable has no credits.

- [ ] **Receipt hardening.** The receipt verifier's tamper and forgery cases (S1a's adversary findings, B1-class hardening) and each module's `tamper`/`refusals`/`tool_use` oracle sections. This stage owns them, if LEAD accepts the deferral proposed on 2026-10-28.
  - S1a review-adversary-4 (the user ruled these known gaps owned here; LEAD 1879180, `docs/reviews/s1a-owner-run.md`, full report and RED tests in `/Users/ericguei/Documents/Deploy Workflow Sessions/s1a-build/work/s1a/review-adversary-4.md`):
    - **HIGH 1.** The verifier never replays `Execution.begin`'s rule (`owner_workflow.py` `_verify_begins` :1007-1024, `_verify_attempts` :1427-1429, the :1632 exemption). Replay begin on `before`:
      - refuse a pending attempt;
      - take `current_inputs` with an explicit identity_mismatch mapping;
      - take `previous` as the attempts with the same module and inputs;
      - refuse if `previous and (len(previous) >= 2 or not previous[-1].issues)`;
      - require an exact `after.attempts`;
      - refuse an unfinished attempt in the final snapshot.
    - **MEDIUM 1.** The CP-MODEL attempt and head `inputs` are unbound. Apply the same replay, plus `current_inputs(final, deterministic) == attempt.inputs`.
    - **LOW 1.** A sealed receipt can carry a pending attempt; HIGH 1 closes it.
  - G1-X adversary review (`work/build/g1x/review-adversary.md`). These predate G1-X and are with the owner (LEAD, 2026-10-28):
    - **Known gap (owner, via LEAD 3f59be2).** Refused records can be dropped, duplicated or reordered across tickets without detection; §4 records them "exactly as for today's".
    - **0d product defect (owner approved; LEAD branch `lead/0d-normalise`, `live/schema.py` only).** A `normalise` TypeError or RecursionError escapes `submit_review` after the binding audit write, and RecursionError escapes the verifier. When the fix lands, remove G1-X's recorded-payload `_fill` TypeError mapping in a later G1-X change (plus any caller diff LEAD sends).
  - CP-8 `cp8.what_changed.outcome.value`: the rails line binds the number of `T7.3.window.realized_value`, never the pinned literal `∅ G#` (rulings round 5, LEAD notes).
- [ ] **Stage 4 review.** Fable reviews (`mx-autonomous` if Fable has no credits). Findings go to `mx-feature` fix rounds.

## Stage 5 — Final verification

- [ ] **5.1** Run every command in `work/build/deferred-runs.md` (no heavy-job lock since the user removed it on 2026-10-28). Log each run in `work/build/ledger.md`.
- [ ] **5.2** Native DOM proof for each delivery scope and the CP-OS nav rows.
- [ ] **5.3** Whole-branch Opus review (`mx-precise` or `mx-autonomous`, unless the user says otherwise); failures go to `mx-feature` fix rounds, test-first. Then `confidence-review` and `rewrite-tournament` on the branch diff.
- [ ] **5.4** PM integrates the branch. LEAD updates `docs/MODULES.csv`.
