# Parallel connector: CP-3C (general-purpose, opus)

CP-3C is connected on `claude/s2b-cp3c` (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2b-cp3c`), and the tree is clean. One lease row is blocked: the two D7 `_Spec` rows conflict with the round 4 ruling. All gates exited 0. All 69 mutants were killed.

**SHAs** (base 8d5d404)
- 4fae75d `fix(cp3c)`: the Stage 2 backlog.
- b164286 `feat(cp3c)`: the Stage 2 connection.
- 741880a `tests(cp3c)`: owner acceptance, run driver and methods record.

**Lease line → symbol**
- :100, core → `owners/cp3c.py` Stage 2 section:
  - adapter: `select_cp1`, `select_cp2d`, `_reader_agrees`, `cp3c_upstream`, `select`;
  - validator: `validate_refinancing`;
  - composer: `refinancing_risk`, `cp3c_module`;
  - G1-X seams: `QUALIFICATION`, `STEP_IDS`, `SCHEMAS`, `view`, `probe`, `ENTRY_VALIDATOR=_validate_step`, `submit`;
  - reader: `cp3c_reader`, `Cp3cHead`, `NeedRow`.
- :100, tests → `tests/test_owner_cp3c.py` and `tests/cp3c_runs.py`. The lease says `cp3c_closed(case, root)`; mine is `cp3c_closed(case, root, template)`, which forks a reached CP-2D state.
- :102 → `owner_workflow.py` rows, all appended: `OWNER_SPECS["CP-3C"]` (at the end), `_CORES`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["refinancing_risk"]=cp3c.view`, and `_ENTRY_VALIDATORS` (from the protocol).
- :105 → `bindings/shipped.py` puts `CP3C` directly after `CP2D`. The new `bindings/cp3c.py` binds `refinancing-paths` (T3D.6, .1, .2, .3), `lme-creditor-exposure` (T3D.5, .4), evidence (T3D.7, .9) and limitations (T3D.8), all with `cp3c-` slots.
- :106 → `report_view` `_Spec` rows: **blocked** (see conflicts).
- :108 → `src/deploy_vii/methods/cp3c.md`, including the guard limits (the eight sentences the phrase guard passes) and the derived-cell citation rule.

**Backlog**
- Done in 4fae75d:
  - Info 1: `reporting_currency`, with `UNSOURCED_CURRENCY` raised when no currency is sourced.
  - Info 2: an unsettled term or minimum cash names its status in the same frame.
  - Info 3: `_check_value` messages use the CP-3C frame.
  - f-string sites that quote data: wrapped in `clipped`/`bounded_issues`.
- Blocked (close release): the 6-period re-pin to q4-2025, held by `PRINCIPAL_PERIOD_DELTA`, and `fact_copy_rule`/`frozen_inputs[8]`.

**Test-first evidence**
- Backlog tests against the 8d5d404 core: 23 failed, 7 passed. The failures were the "is not stated" frames, unbounded lengths, DID NOT RAISE, and the missing `reporting_currency`. The 7 that passed are the guards that keep the existing reasons.
- Connect part 2: 69 failed, 31 passed, 19 errors. Causes were AttributeErrors for select / cp3c_upstream / view / SCHEMAS, a KeyError for `refinancing_risk`, "'CP-3C' is not in list" and a StopIteration.
- The next run had 10 failures, all registrations and bindings, before those were added.
- The owner tests run against owner_workflow at 8d5d404: 13 failed, all `KeyError: 'CP-3C'`.

**Gates (exit codes)**
- First gate set plus `test_owner_cp3c` (fast group): 0 (772 passed, 11 skipped).
- Every `test_connect_*`: 0 (2037 passed, 2 skipped).
- `test_legal_render`: 0 (76 passed).
- `ruff check`, `ruff format --check` and `mypy --strict` on the 8 changed files: 0.
- `pins --check`: 0.
- noqa is still 13 and type: ignore still 8.
- **Mutants:** 69 (one per Cp1Fact and Cp2dFact field, operand, facility term, reader-agreement pair, Selection/Inputs/Upstream field and balance date, and one per owner_workflow row, OWNER_SPECS field, shipped placement and binding row). All killed; baseline 0, script exit 0. Script and log: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-batch/mutants.py` and `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-batch/mutants_log.txt`.

**DeliveryScope row (lease :193), word for word:** "Rendered through G2 `owner_rendering.py` with a `DELIVERY_SCOPES` entry for `(covenant_refinancing, [CP-1, CP-1A, CP-2, CP-2D, CP-3C], synthetic)`; sections `refinancing-paths`, `lme-creditor-exposure` and the two rails (the CP-2D blocks are asserted by the CP-2D lease; CP-4 blocks are unasserted, CP-4 not requested)."

**D2 TOOL-CONTRACT row for LEAD (lease :179):** "CP-3C `refinancing_risk`: exactly the view `owners.cp3c.view(historical, attempt)` registered in G1's `_VIEWS["refinancing_risk"]` (`module_context()` has no such entry and deploy_vii cannot register a deploy_workflow core): the bound CP-1 and CP-2D facts named by `manifest.fact_bindings` (`ref`, `name`, `source`, `label`, `period`, `unit`, `shown`, `status`, `limitation`) including missing ones, the facility list (text fields only), the unread optional edges, the step-up and path bounds and the inherited limitations; no quote, citation or record_json at any depth; key tree frozen in `cases/cp3c-owner/manifest.json#view_tree_draft` after a probe on the first product-settled core"

**Conflicts and defects (reported, not built around)**
1. **D7 vs round 4.** The lease rows make `refinancing-paths` and `lme-creditor-exposure` render owner CP-3C instead of the Unbound fallback, so `test_legal_render` fails twice. Round 4 keeps them Unbound. A patch is ready but not applied: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-batch/d7_patch.py` (the two `_Spec` rows, a `CP3C_D7_DELTA` and `test_spec_rows_serve_the_two_blocks`). In scratch, the rows alone give 2 failures in legal render; with the delta, all connect tests plus legal render pass (2114 passed). It needs a LEAD ruling.
2. **Funding-gap ownership (lease Q2) is still open.** CP-3C registers neither `funding-gap` nor `maturity-wall`, so nothing conflicts on the branch.
3. **Oracle defect: CP-1A is bound.** `current_inputs` binds an optional producer the run selects, so CP-1A is in CP-3C's attempt inputs and its limitations are inherited. `expected.cp3c_module.attempt_inputs`, `manifest edges.bound_in_attempt_inputs` and lease acceptance 1 omit it. Tests carry this as `CP1A_BOUND`.
4. **`cp2d_reader` lacks run_rate (T2E.3.r01).** It is read from the head cell and cross-checked; it needs a pin extension.
5. **Lease :185 "CP-4C has no core" is stale.**
6. **`s1a_runs.drive_cp1` hardcodes the readiness literal,** so `cp3c_runs` has its own `drive_cp1`.
7. **CP-2D `_validate_step` uses raw `model_validate_json`,** not the §6 `json_object` path.
8. **`tests/test_connect_cp3.py`** listed "CP-3C" as having no spec; I removed it. That line may conflict with the CP-4C branch.
9. **The oracle gap cells carry no currency;** CP-2D gap copies do, held as `GAP_CURRENCY`.

**Close-release text:**
- Re-pin the CP-3C principal periods to q4-2025 and the gap-cell currency to USD.
- Add CP-1A to `attempt_inputs`, `edges.bound_in_attempt_inputs` and lease acceptance 1.
- Apply `fact_copy_rule` and `frozen_inputs[8]`.
- Re-pin the FP04 render oracle (`cases/legal/render-expected.json`) if the D7 rows are admitted.
- Correct lease :185.
- Add the `cp2d_reader` run_rate pin.

**Reused files touched:** `owner_workflow.py` (rows only), `bindings/shipped.py`, `tests/test_connect_cp3.py`. `report_view.py` and `test_legal_render.py` are touched only in the unapplied patch.

**Deferred (Stage 5) commands:**
- `CP3C_STORE_RUNS=1 PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cp3c.py` (11 written, not run: the three closed runs vs the oracle, receipt and unchanged bytes, CP-1 readiness re-assertion, D3 and reader on the closed heads, submit-before-read/stale, the blocked_cp3c receipt, begin_refused_cp2d_blocked, the tamper with a probe spy, the step-output blob edit).
- `python3 -I cases/cp3c-owner/builder/build.py`.

Not verified: the store runs, the `cp3c_runs` driver end to end, D3 and the reader on genuine heads, receipts and the tamper (all Stage 5). Also not verified: A7 rendering (G2 Stage 3 plus the D7 ruling), the CP-1 readiness `refused_variants` (no test written), and the full test suite.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
