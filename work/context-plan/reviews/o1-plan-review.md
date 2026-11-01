# O1 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (4 High, 3 Medium)

Target: `docs/superpowers/plans/2026-10-31-part-b-o1.md` draft at 3451eec5. Held: task order (a
simulated Task 1 admits relative_value and covenant_refinancing; credit_snapshot/portfolio_decision
then stop at ow:996 until Task 2, earnings_update until Task 3); baseline plan tuples unchanged;
p1 matches; only `registry.py` changes in `src/deploy_vii` (sha adf30a0b…, manifest.json:1147).

- **F1 High** (plan :138-143). Task 1's RED test expects `publish()` to return `ok` in the `WALK` world,
  whose store has no CP-1, so the real publisher refuses (test_owner_order.py:206-209, 263-266);
  the refusal is non-terminal, the phase stays `walked`, and the verifier rejects that refusal
  (ow:1771-1775). Fix: test the resume in `_blocked_cp1_then_module`'s world (terminal refusal,
  test_owner_order.py:313-337); the `ok`-then-resume case goes in the rewritten `RUN_PROMOTION` test
  (:400-437).
- **F2 High** (:121-123). Today publication must be last: `last.snapshot_after == final` (ow:2399), a
  refusal's `before == final` (ow:2366). Relaxing both to "an ancestor" with no plan-position rule
  lets a reordered audit verify. Fix: in `_verify_chain`, publication transitions start at the
  `after` of the last transition of modules planned before CP-MODEL (or at the refusal), and every
  begin of a later-planned module comes after the last publication; RED test: a receipt from a
  workflow whose `_advance` is patched to the old no-stop walk is rejected.
- **F3 High** (:112-116). "Refused after the stop ⇒ last publication's `snapshot_after`" is wrong when
  another module settles in between. Fix: refused before the stop ⇒ `publications[0].snapshot_before`,
  otherwise ⇒ the final snapshot; RED test with two modules after the stop, the second refused.
- **F4 High** (:354, :359-372). `cases/cp5-owner` is frozen over fan-in {CP-0, CP-1, CP-1A, CP-2, CP-3};
  CP-5 refuses a review leaving a claim unreviewed (cp5_integrity.py:658-663). Only portfolio_decision
  has that fan-in; the other presets add claims, so CP-5 settles blocked and CP-6 is refused. Module
  oracles were frozen in single-module runs; in a preset CP-1D binds the optional CP-1B and CP-3
  binds CP-4. Fix: Task 5 step 1 compares each module's bound input set (`dependencies(preset)`) with
  its oracle run and CP-5's claim coverage; then either per-preset CP-5 oracles or O1 done for the
  covered presets.
- **F5 Medium** (:281-288). No settled CP-1 head in the CZR fixture (manifest: "Oracle only. No
  recorded module submissions"; RESULT-partial.md: CP-1 blocked at quality). E-* cases run on
  identity + financial via `drive_fresh_foundation` (test_earnings_workflow.py:1048). Fix: build on
  `test_financial_workflow.make_pack()`, gated behind `RUN_PROMOTION`.
- **F6 Medium** (:259-262). `_compose` needs `EarningsDeltaReview` and `EarningsParticipation`
  (earnings_workflow.py:1755-1763) and stamps Northbridge `_COMMON_LIMITS` and the "Owner checkpoint
  only…" `_CHECKPOINT_LIMIT` (:1643-1654, :1672-1680), false on the owner path. Fix: split a composer
  needing no participation that takes its limits as an argument; pin E-* outputs byte-identical;
  report R7 changes.
- **F7 Medium** (:87-89, :159-165). Drivers that publish after the walk break: `tests/cp3_cp6_runs.py`
  `reach_cp3`/`close` (:219-240) and test_owner_order.py:400-437. Fix: add them; publish at the stop
  between `through_cp2` and `drive_cp3`.
- **F8 Low** (:108-110). A clean publish failure leaves `walked` and allows a retry (ow:1408-1436); only
  cleanup errors or an existing head set `failed`. Fix: the walk resumes only after a retry publishes
  or is refused as terminal.
- **F9 Low** (:351). CP-MODEL is exempt from CP-0 `Run <id>` (execution.py:260).
- **F10 Low** (:314-315, :374-376). distressed already passes (no `not_permitted` first); Task 4 is
  consolidation, no RED of its own.
- **F11 Low** (:205-211, :281). Task 2/3 RED tests need a CP-1 promotion (11-26 min,
  cp3_cp6_runs.py:10): gate behind `RUN_PROMOTION`.
- **F12 Info.** `_upstream`'s only caller is ow:1015 (safe to delete); owner tail input id is
  `earnings-delta-submission` (host.py:655), `_submission_schema` host.py:586-614 refuses CP-1B
  `earnings_delta` today; `_verify_model_settlement` (financial_workflow.py:1554-1595) does not depend on
  the final snapshot; cp6 `context_block` :1434, `OwnerCaseId` :98.
- Open questions: Q1 keep "resume after a terminal refusal" but the premise is wrong (in all six
  presets a CP-1 consumer planned before CP-MODEL is refused with `BLOCKED_EDGE` first; once a
  refusal happens CP-5 never settles, ow:1689-1694), do not cite O3; Q2 agree
  (`MODULE_CONTEXTS[committee_challenge]` live/context.py:104-107); Q3 agree plus F6; Q4 CZR unusable;
  smallest honest CP-1B source: the earnings_update pack (identity + financial, the bytes
  `cases/earnings/expected.json` is frozen on, financial sha 82d684…, also cp1d-owner's pack),
  E-QOQ-FLAT's period pair (q3-2025 → q4-2025, `cases/earnings/manifest.json`) and the frozen
  assessments `owner-expected.json:378-382`; expected points `expected.json` `positive`; Q5 agree,
  record the departure from "replaces"; Q6 use the existing `RUN_PROMOTION` skip
  (test_owner_order.py:396-398; pyproject has `--strict-markers` with only `live` and `browser`);
  Q7 disagree: assemble CP-0 consumer rows from frozen `cp0_consumer_row_<m>` literals as
  `cp2a_runs.cp0_review` does; a module with no frozen row is an oracle gap, reported, never made up.

## Controller rulings (2026-10-31)

- Fixes F1-F3 and F5-F12 accepted as proposed; open questions as the reviewer answered.
- **F4 / Done-when (departure from the Part B O1 wording, recorded):** O1 proves the walk machinery,
  not analytical coverage of every preset. Task 5's step 1 compares each module's preset-bound input
  set with its frozen oracle run and CP-5's claim coverage, and writes into the test, before the walk
  runs, each preset's expected end state: settled through CP-5 (and CP-6 where planned) when the
  frozen submissions cover it, otherwise the first module whose frozen submission does not fit its
  preset-bound inputs, or CP-5 settling blocked with the named unreviewed claims. Every preset walks
  on frozen per-module submissions with CP-MODEL publishing inside the walk, and
  `verify_owner_run_receipt` passes on the receipt it produces. Full settlement through CP-5 is
  required where `cases/cp5-owner` covers the fan-in (portfolio_decision). No per-preset CP-5/CP-6
  oracles are commissioned in O1. Cost if wrong: four presets are proven to walk and verify but not
  to settle CP-5 ready; the golden model runs (testing plan) cover end-to-end analytical results.
- **Q5:** `EarningsWorkflow` and its three-run-id gate stay until O2; O1 adds CP-1B to `_CORES` beside
  it (departure from "replaces").
- **Context periods for CP-1B** stay in Phase 2 (research item 4), not O1.
- `RUN_PROMOTION`-gated tests are affected tests: the controller runs them with `RUN_PROMOTION=1`
  before O1 is marked done.
