# CP-2D Stage 2 review (mx-adversary)

## CP-2D Stage 2 review (claude/s2-cp2d, b47c667 vs 8b46132): REQUEST CHANGES

Probe directory: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2d-s2-review/` (named as `<P>/…` below). Every script there was run. The repo was not touched: base and tip were exported with `git archive` into `<P>/tree-*`.

### High
**H1. A frozen render test now fails.** `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]` fail at b47c667 and pass at 8b46132.
- Cause: the three new `_COVENANT_REFINANCING` `_Spec` rows make `liquidity-runway`, `maturity-wall` and `funding-gap` read `CP-2D`/`dense`.
- The frozen CP-4 FP04 oracle pins those blocks the other way: `cases/legal/render-expected.json#other_front_sections` sets `"preserve_existing_fallback": true`, owner `Unbound`, kind `prose`, and the CP-4 FP04 lease :84-86 says the same.
- So the CP-2D lease D7 conflicts with the CP-4 FP04 oracle, and the module cannot edit `cases/`. LEAD must rule or re-pin before merge.
- The test takes 0.4 s, so brief §7 says to run it, not defer it.
- Probes: `<P>/p3_legal_render_unbound.sh` (exit 1), `<P>/p3b_legal_render_base.sh` (base exit 0), `<P>/p4_fast_regressions.sh` (2 failed, 3559 passed).

### Medium
**M1. The adapter makes the lease's facility-FX path unreachable.**
- `_facility_of` → `_usd_millions("T4.18 principal")` requires `currency == "USD"`.
- CP-1 writes T4.18 money facts with `currency=row.currency` (`model_interface.py` `_facilities`/`_observed`).
- So a non-USD facility raises, and the step stays pending. The lease (:95, Facility FX) and ruling A5 (cp2d.py `Facility` docstring) instead require the row and every total to be missing, with the limitation. `methods/cp2d.md` also says "a facility not in USD is not summed".
- The b47c667 test passes only because its fixture (`_row_facts`) hard-codes `currency: USD` on the money facts of a EUR facility.
- Probe: `<P>/p5_fx_facility_unreachable.py`, exit 1 ("T4.18 principal is not in US dollars millions").

**M2. The alias check runs one way only, so it fails open on money.**
- A facility that has a fy-2025 row (same end date) but no q4-2025 row is silently dropped. Its maturities, its share of total debt and the funding gap all go missing.
- The pinned rule refuses this case: the manifest T4.18 rule "the alias must agree", and `_maturity_figure`, which requires population == actual.
- Probe: `<P>/p6_alias_only_facility.py`, exit 1 (adapter returns `['term-loan']` only).
- Ride-along Lows:
  - a term missing from one row is never compared (`term in row and term in other`);
  - `basis` is not compared.

**M3. The deferred acceptance tests were not written.** `tests/test_owner_cp2d.py` is absent. The lease Files list names it, and the brief §7 in force at dispatch already said "write these, do not run them". These are missing:
- the positive, long_horizon and gap_minimum_cash store runs, with:
  - inputs hash-equal to the final heads plus the tail;
  - the receipt verifying;
  - store and model bytes unchanged afterwards;
- a refused `invoke` receipt, with zero ok calls;
- submit before `read_inputs` refused `not_permitted`;
- `stale_binding` when the snapshot changes between read and submit;
- `blocked_cp2d` with its receipt and the status-only reader;
- `begin_refused_cp2_blocked`, with no attempt consumed;
- verifier tamper of the read body, the step output and the head: the audit and the pre-`_PROBES` checks pass, then `verify_owner_run_receipt` refuses with `identity_mismatch`.

Probe: `<P>/p13_missing_acceptance.sh`, exit 1.

**M4. The tests are weak on money paths.** My mutants (`<P>/p7_mutants.py`, log `p7_mutants.log`): 14 of 25 survive.
- **Reader:**
  - a stale head exposing figures survives;
  - constants equal to the oracle survive: horizon 24, months 48, principal 50, share 1, `inside_horizon=False`.
  - The reader is only checked on wall data that is the same in positive and gap_minimum_cash. long_horizon (60, Yes, gap 40) is never read through it.
- **Adapter:**
  - a constant balance date survives, because the fixture end date never varies;
  - these refusals have no test: a missing alias row, a duplicate coordinate, two rows in one period, a known fact without a period, the ratio unit, the view's run-id check.

The code itself behaves correctly: `<P>/p8_reader_stale_and_long_horizon.py` exits 0. The tests just don't pin it, which breaks the brief §7 / CP-DR M1/L1 rule on varied fixtures.

### Low
- **L1.** Both D12 `post_import_patches` records name `project_commit` 545a8a7, which is the pre-rebase commit and is not on the branch. The landing commit is 8aef58d; `docs/reviews/0d-product-defects.md` sets that precedent. All six hashes check out.
- **L2.** The `DeliveryScope` row is not copied word for word. Compared with lease :127 it drops "Who renders:" and the sentence "The other FP04 blocks are unasserted (CP-4 not requested; CP-3C has no core), as the CP-4 FP04 lease does."
- **L3.** "Equity repurchases is …" has the same verb-agreement fault. It is outside the row's scope, so it goes to LEAD or the backlog.
- **L4.** The lease's internal `operands(*, cp1) -> Operands` is built as positional `select_cp1(cp1) -> Selection`.
- **L5.** The report says `ruff check` exited 0 on the changed files. It exits 1 on `report_view.py:293` SIM102, which predates the branch (same at 8b46132).

### Answers to the checks
1. **Adapter.**
   - The real promoted CP-1 head gives exactly the Stage 1 operands and facilities (`<P>/p10_real_head_equals_stage1.py`, exit 0).
   - A non-known fact keeps its status and is never 0 (mutant A2 killed).
   - A refusal fails closed (`<P>/p11_refusal_leaves_pending.py`, exit 0). `view` raises before any audit write or budget use. `submit` journals the step pending and raises the same error on every retry: no head, no loop. Only `interrupt` ends the attempt, and it leaves no head.
   - At workflow level the run cannot reach a receipt. That matches the "no durable resume" design and the manifest's "zero or several fail", so the refusal is the intended behaviour.
   - `FACT_BINDINGS` equals the manifest for all 25 names. For T4.18 only the table and period are checked, not the pinned `facility_id`.
2. **Backlog.** All four behaviour mutants (B1-B4) were killed.
   - The T2E.2.r06 invariant is superseded by LEAD's backlog row ("commitment less drawn … No invariant") and addendum 4(c). Nothing is left unguarded: the adapter sets every facility's period to q4-2025, and the T2E.1.r05 sum invariant test is kept.
   - `PERIOD_DELTA` removes exactly the four recomputed tags and keeps "T4.18 principal".
   - No frozen text holds "RCF drawings is".
3. **Reader.** It exposes what the lease pins, and a known 0 stays `Decimal(0)` (R7 killed). A blocked head gives status and hash only (tested); a stale head does too, but only my probe shows it. D3 is not claimed anywhere.
4. **Registrations.** All rows are appended. `SHIPPED_MAPS` has CP2D directly after CP2, which is the lease's "after CP2". The spec equals the lease. There is no `_OWNER_SCOPES` row and `_check_steps` passes (`<P>/p14_registrations.py`, exit 0). `_spec_of` serving distressed is explicitly in lease D7 :125.
5. **D12 records.** See L1.
6. **Missing tests.** See M3.
7. **Library boundary.** Clean: no change to `cases/`, `methodology.json`, TOOL-CONTRACT or any engine.
8. **Mutants.** See M4.

**Gates I re-ran** (`<P>/p9_gates.sh`): pytest 676 passed (exit 0), `ruff format --check` 0, `mypy --strict` 0, `ruff check` 1 (predating SIM102).

Not verified: `test_connected_render` and `test_financial_render` (`<P>/p12_other_render.sh` was still running at hand-back); any real `OwnerWorkflow` store run, receipt or verifier replay; whether CP-1 promotion actually admits a non-USD facility (M1 rests on model_interface's code path); `test_owner_workflow.py` and `test_owner_s1a.py`.
