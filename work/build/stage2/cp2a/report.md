# CP-2A Stage 2 report (mx-feature)

CP-2A Stage 2 is built and committed as caa2f5d on claude/s2-cp2a (cut at 6e51653). I have not rebased onto the lane tip.

**Gates (all exit 0, run after the Q6 change)**
- pytest on tests/test_connect_cp2a.py, test_method_cp2a.py, test_owner_g1x.py, test_host_h1.py and test_defect_classes_selfcheck.py: 547 passed, 1 skipped. The skip is the Stage 1 `test_v17_stale_input_is_stage_2` placeholder; v17 is now covered in test_connect_cp2a.py.
- `ruff check` and `ruff format --check` on the changed files exit 0. `ruff check` on `report_view.py` reports one SIM102 at :293; it is present on HEAD and I did not touch it.
- `MYPYPATH=src mypy --strict` exits 0 on the 5 changed src files and 3 tests.
- Mutants (script `<S>/cp2a-s2/mutants.py`, plus `mutant11.py` for the SHIPPED_MAPS reorder, whose text no longer matched `mutants.py` after ruff reformatted the file): 20 of 20 killed. They cover the adapter fields (cp1_facts, offered_periods, names, submission), each registration row (SUPPORTED_ANALYTICAL, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS`, `_ENTRY_VALIDATORS`, the spec), the SHIPPED_MAPS position, the `_PRESETS` order, the `_spec_of` loop, the `_Spec` kind, three binding rows, the tail input id, and the qualification passed to finish.

**Test-first evidence:** the first run of tests/test_connect_cp2a.py was 57 failed and 3 passed. The causes were the missing attributes and registrations. The two clipped-line tests were red on the over-600-character lines. The registration and binding tests passed only after the code landed.

**Files and lease lines**
- `src/deploy_workflow/owners/cp2a.py`:
  - Plug-in parts: `PROMOTED` and `QUALIFICATION`, `STEP_IDS`, `SCHEMAS`, `SUBMISSION_INPUT`, `submit`, `view`, `probe`, `ENTRY_VALIDATOR`.
  - Lease Public API pieces: `DownsideReport`, `Upstream`, `cp2a_upstream`, `validate_downside` (stale input first, then `validate`), `downside_report`, `cp2a_module`, `context_block`.
  - Adapter: `offered_bases` and `_inputs`. Submit, probe and view all reach the core through them.
- `src/deploy_workflow/owner_workflow.py`: rows appended at the end of `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS`, `_ENTRY_VALIDATORS`, the `OWNER_SPECS` spec (`downside_pathway`, `inputs="module_context"`, `rules="none"`, `entry="owner_core"`) and the import. No `_PRECHECKS` row, since the lease has no precheck.
- `src/deploy_vii/bindings/cp2a.py` is new. `shipped.py` puts CP2A last in `SHIPPED_MAPS`.
- `src/deploy_vii/report_view.py`: `_DISTRESSED` with `downside-stress` and `break-points`, appended to the `_spec_of` loop, and both ids inserted in the `_PRESETS` distressed list after `distress-gate`. No `MODULE_FAMILY` row.
- `src/deploy_vii/methods/cp2a.md` was moved from `docs/methods-drafts/cp2a.md` and gained connection notes.
- Tests: `tests/test_connect_cp2a.py` (run), and `tests/cp2a_runs.py` and `tests/test_owner_cp2a.py` (written, not run; `cp2a_runs` only import-checked).
- Q6: I added no `cp2a_reader` and no Head type; a test asserts the attribute is absent. The `cp2g`/`cp4c` readers are untouched.

**Backlog**
- Caller-quoting f-strings: done at `cp2a:593` (prose issue lines) and `:620` (duplicate scenario name), both through `clipped` and both test-first. `:634` quotes `t.metric`, which is a `Literal`, so I left it. CP-2A has no `RULES` or precheck, so `listed_issues` does not apply. The journal bounds validator issues anyway.
- The `ValueError` join in `compute` now goes through `bounded_issues`.
- L6: done at the adapter. The view `kind` and the core's `offered_periods` come from one derivation. A period whose label does not parse, or that lacks exactly one T4.10 fact per metric, is not offered. This is fail-closed, and it covers the Stage 1 note that `validate` raises for an incomplete period. I did not change the `BaseOperands.from_cp1` signature.
- Rule W, B8, item 8 comma costs and blank support quotes: not applicable. CP-2A takes no citations and has no rules; this is noted in `methods/cp2a.md`.
- No row is blocked on a LEAD re-pin.

**For LEAD**
- `methodology.json` already holds T2B.1 to T2B.9; no edit is needed.
- TOOL-CONTRACT: add the CP-2A `downside_pathway` row with the exact view `cp2a.view` registered in `_VIEWS["downside_pathway"]`. The key tree is `upstream`, `base_periods`, `cp1_facts`, `cp1_facts_note`, `scenario_bounds`, `threshold_metrics` and `inherited_limitations`, with no quote, citation or record at any depth. `cp2a-view-tree.json` was not committed (see Not verified).
- D2 view row text: as above.
- `docs/reuse/manifest.json` D12 records for `report_view.py`, `shipped.py`, `bindings/cp2a.py` and `methods/cp2a.md` are not added. Each record needs the final sha256 and the merge commit, and I did not edit that shared file.
- `DeliveryScope` row, copied from lease line 149: `DeliveryScope(scope_id="cp2a-fp05-downside", pathway="distressed_restructuring", requested_modules=("CP-2A",), case_kind="synthetic", sections=("downside-stress","break-points"), rails=("evidence","limitations"))`.

**Deferred commands for `work/build/deferred-runs.md` (each 11-26 min, heavy-job lock)**
- `PYTHONPATH=src "<venv>/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp2a.py`
- `cp2a_closed` cases positive, gap, refused and blocked, driven via `tests/cp2a_runs.py`.
- The oracle rebuild check from the lease: `python3 -I cases/cp2a-owner/builder/build.py`, then `cmp` the three files.
- `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py`, the source suites and the render runs.
- The CP-2G task closes D3.

**Not verified:**
- Anything against a genuine promoted CP-1 head. The store tests use hand-seeded CP-0 and CP-1 modules from the oracle facts, re-cited to the real financial pack. Real T4.10 field, label and period shapes, and the real `Fact` `row_id` and `field` values, are unconfirmed.
- `tests/cp2a_runs.py` and `tests/test_owner_cp2a.py` have not been run. The `cp1_downstream_review` marker binding, `workflow._binding` and the `refused` and `blocked` driving are written from reading only.
- `test_owner_workflow.py`, `test_owner_s1a.py` and the render suites. I started the render tests and killed the run myself, so there is no result. Whether the new `_PRESETS` ids and `SHIPPED_MAPS` row break any existing render snapshot is unknown.
- FP05 rendering, including the `∅ G# n.m.` spelling, and the `DeliveryScope` row, which is G2's.
- The receipt verifier's mapping of the `ValueError` that the shared `probe_one_step` raises for a forged attempt number. `cp2a-view-tree.json` was not committed; the view is tested against the lease tree in test_connect_cp2a.py.
- The `docs/reuse/manifest.json` records.
- No test applies to the `methods/cp2a.md` text, which is documentation.
- The Q8 `MODULE_FAMILY` ruling affects nothing here.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a
