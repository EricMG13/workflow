# CP-2D Stage 2 report (mx-feature)

CP-2D Stage 2 connection: built and committed in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp2d` on `claude/s2-cp2d` (cut at 6e51653). One gate item was not run (see "Gates"), and two backlog rows are blocked on LEAD.

**Commits**
- 545a8a7: code and tests.
- d60d70b: D12 record in `docs/reuse/manifest.json` (two `post_import_patches`, for `shipped.py` and `report_view.py`).
- 1ec1b40: one extra adapter test, added after a mutant survived.

**Files**
- `src/deploy_workflow/owners/cp2d.py`
- `src/deploy_workflow/owner_workflow.py`
- `src/deploy_vii/bindings/cp2d.py` (new)
- `src/deploy_vii/bindings/shipped.py`
- `src/deploy_vii/report_view.py`
- `src/deploy_vii/methods/cp2d.md` (new)
- `tests/test_connect_cp2d.py` (new)
- `tests/cp2d_runs.py` (new)
- `tests/test_method_cp2d.py` (pins updated for the backlog changes)

**Lease line to symbol**
- Seams (`cp2d.py`): `STEP_ID`, `STEP_IDS`, `SCHEMAS`, `QUALIFICATION` (implementation="implemented"), `SUBMISSION_INPUT`, `probe`, `view`, `ENTRY_VALIDATOR`, `submit`.
- Store adapter: `_inputs(store, attempt, submission)` calls `cp2d_upstream`, then `select_cp1`. `submit`, `probe` and `view` all go through `select_cp1`.
- Binding source: `FACT_BINDINGS` plus the T4.18 fields, tested equal to `manifest.fact_bindings`.
- Composition: `validate_liquidity_bridge`, `liquidity_bridge`, `LiquidityBridgeReport`, `cp2d_module`, `context_block`, `FORMULAS`, `RECOMPUTED_TAGS`.
- Reader (Q6: stays in `owners/cp2d.py`): `cp2d_reader(store, head) -> Cp2dHead`, with `WallRead` rows.
  - It exposes horizon, minimum cash or its absence reason, wall rows, funding gap (a known 0 is `Decimal(0)`, distinct from missing), head hash and status.
  - A blocked or stale head exposes status and hash only.
  - D3 is not claimed; it closes in CP-3C's task.
- Registrations in `owner_workflow.py`, all appended: import, `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["liquidity_bridge"]`, `_ENTRY_VALIDATORS`, and `OwnerSpec` with `entry="owner_core"`, `inputs="module_context"`, `rules="none"`. No `_PRECHECKS` row. `_check_steps` passes.
- `SHIPPED_MAPS`: `CP2D` placed right after `CP2` (the lease's position, so not a pure append).
- `report_view.py`: three `_Spec` rows (`liquidity-runway`, `maturity-wall`, `funding-gap`) added to `_COVENANT_REFINANCING`. `_spec_of` serves `liquidity-runway` to the distressed composition too.

**Backlog rows** (red first, then green)
- Sum-copy status (addendum 4 (b)): done. T2E.1.r05 with a non-known operand is a dependant gap, `Not calculable: Equity issuance is conflicting`. A single copy keeps CP-1's status and limitation.
- Recomputed-cell period (addendum 4 (c), (d)): done. `undrawn_rcf`, `liquidity`, `liquidity_to_debt` and commitment-less-drawn take the balance date, with no period invariant. The `cp1_operand` tag stays as a twin pointer. I removed the old periods-differ invariant test for T2E.2.r06 and updated the `PERIOD_DELTA` pins.
- "RCF drawings is" agreement: done. `verb()` and `PLURAL_LABELS` give "are" in `state_reason`, the limitation, LIQ-01, GAP-01 and `GAP_OPERAND`. "Equity repurchases is" has the same issue but the row names only RCF drawings, so I left it.
- Drawings-missing precedence Low (cp2d.py:617): NOT done. The row is a ruling gap for LEAD and names no change. Reported only.
- Oracle re-pin and removal of `PERIOD_DELTA` / `GAP_VALUE_CLASS_DELTA`: BLOCKED on the LEAD re-pin. The test deltas stay.
- Methods guard-limit notes: no module-specific rows apply. `methods/cp2d.md` records the module's own guard limits.
- Blank-quote row: n/a, CP-2D takes no citations. `listed_issues` row: n/a, CP-2D has no `RULES` or `_PRECHECKS`.

**Test-first evidence**
- Backlog tests were red before the code: 8 failures, each for the intended cause (wrong status, wrong period, "is" vs "are").
- The connection tests were red on missing attributes before each part was written.
- The adapter returns exactly `tm._inputs(case)` for all three pack cases over a synthetic real-`Execution` store.
- The adapter also reproduces the Stage 1 operands and facilities exactly from the real promoted CP-1 head.
  - Probe: `<S>/cp2d-s2/real_head_probe.py`, run on a copy of the observed `r2pos-orig` store, exit 0.
  - The composed module also passed `citation_issues` and `prose_issues` there.
- The synthetic-store run also exercises `submit`, `probe`, `view`, the blocked path after two invalid attempts, and the reader.

**Gates**
- `pytest` on `test_connect_cp2d`, `test_method_cp2d`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck`: 655 passed (last full run before the final commit was 653 passed, exit 0; log `<S>/cp2d-s2/gate.log`).
- `ruff check` and `ruff format --check` on the changed files: exit 0. Not clean: `report_view.py:293` SIM102 and some other `src` files; I did not check whether `report_view.py:293` predates my change.
- `mypy --strict` on the six changed `src` and test files and `tests/cp2d_runs.py`: exit 0.
- Mutants: 77 of 77 killed (one per adapter field and operand binding, per registration row, per binding row, per `_Spec` row, and the three backlog behaviours). Script `<S>/cp2d-s2/mutants.py`, log `<S>/cp2d-s2/mutants.log`. One mutant (facility `currency`) survived the first pass, so I added a test and it is now killed.
- Render suites (`test_connected_render` and others): started in the background, never saw a result; they are Stage 5.

**For LEAD**
- `methodology.json`: no change needed. T2E table ids are already registered.
- `docs/TOOL-CONTRACT.md` D2 row, per the lease: CP-2D `liquidity_bridge` is exactly the view `owners.cp2d.view(historical, attempt)` registered in `_VIEWS["liquidity_bridge"]`. Key order is `upstream`, `cp1_facts` (`ref`, `name`, `label`, `period`, `unit`, `shown`, `status`, `limitation`; missing facts included; sorted by name), `cp1_facts_note`, `bounds`, `inherited_limitations`. No quote, citation or record_json at any depth. The tree is still a draft until frozen after a probe.
- `DELIVERY_SCOPES` row (Q1, copied word for word from lease :127): "G2 `owner_rendering.py` with a new `DELIVERY_SCOPES` entry for `(covenant_refinancing, [CP-1, CP-1A, CP-2, CP-2D], synthetic)`, sections `liquidity-runway`, `maturity-wall`, `funding-gap` and the two rails."
- T2E.9 traces all 30 bound names, including `fcf_unlevered` as missing, and the unused names `cfo_reported`, `debt_issuance`, `debt_repayment`. The oracle wording "names the composer read" is ambiguous.
- Plan notes: the CP-1 T4.13 `earnings_quality_metrics` reads `not_ready` unless the run's CP-1 readiness literal assesses CP-2D. A stale required head that is not blocked re-raises at `begin` (`owner_workflow.py` ~:770-774); lease :99 holds only for the blocked half.
- The Stage 1 period-invariant `ValueError` ("operands of T2E.1.r05 differ in period") still propagates out of the step validator. The step stays pending, which fails closed.
- The adapter raises `ValueError`, also leaving the step pending, when a binding selects zero or several facts, a money fact is not USD millions, or a facility's FY alias disagrees.

**Deferred commands** (for `work/build/deferred-runs.md`, not run)
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cp2d.py` (not written: needs the 11-26 minute CP-1 promotion).
- `tests/cp2d_runs.py` (written, imports and assembles; its runs are not done): `cp2d_closed("positive", root)`, and for `long_horizon` and `gap_minimum_cash` `cp2d_closed(case, root, template=reach(root0)[0])`.
- The D3 run assertions are CP-3C's.
- Receipts, promotion, `test_owner_workflow.py`, `test_owner_s1a.py`, the source suites, and the render suites.

Not verified: real-store runs of the full `OwnerWorkflow` (the pack-level literals, receipt verification, `_verify_settlements` replay of the settled head); the oracle CP-0 literal plus consumer delta and the CP-2 literal without CP-MODEL (assembled in `cp2d_runs.py` but never run); a CP-1 head with a missing or foreign-currency facility, or a real facility alias difference (the adapter was only exercised on synthetic variants); the T4.18 "absent" versus "no facility" distinction on a real gap head; host H1 `_submission_producer_inputs` over a CP-2D head; `DELIVERY_SCOPES` rendering (G2); the drawings-precedence Low (not worked, per the row); the render suites.

agent=mx-feature fix-rounds=0 gates-first-pass=n
