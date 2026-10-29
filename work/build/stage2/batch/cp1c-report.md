# Batch builder 3: CP-1C (general-purpose, opus)

## CP-1C batch build (builder 3): report

Everything is committed on `claude/s2-batch`, starting from 8d5d404. All gates exit 0. Mutants: 34 of 34 killed after one fix, described below.

**Commits**
- b2f2308 feat: core connection, registrations, bindings, method note, fast tests.
- 9b0d61b tests: `tests/cp1c_runs.py`, the deferred `tests/test_owner_cp1c.py`, driver and D8 fast tests.
- afc4241 docs: D12 records (project_commit b2f2308).
- 57befe8 tests: binding unit-class test. It kills the surviving mutant.
- 3d0392e tests: fix to the owner test, found on a genuine run.

**Lease line → symbol** (`src/deploy_workflow/owners/cp1c.py`)
- Constants: `MODULE_ID` :66; `STEP_ID`, `STEP_IDS`, `QUALIFICATION`, `SCHEMAS` around :1509; `RULES` :1903 (`unread_citation_issues`).
- Stage 1 functions: `parse_peer_source` :347, `peer_metrics` :409, `median` :413, `position` :429, `outlier` :437.
- Upstream: `cp1c_upstream` :1559, returning `Upstream` and selecting T4.10 facts with `_cp1_metrics` :1580. The one adapter is `_inputs` :1599, used by submit, probe and view.
- Validation and output: `validate_peer_benchmark` :1774, `peer_benchmark` :1783 (`PeerBenchmarkReport`), `cp1c_module` :1793, `context_block` :1844.
- Workflow surface: `view` :1893, `ENTRY_VALIDATOR` :1936, `submit` :1963, `probe` :2000.
- Reader: `cp1c_reader` :2039, with `READER_FACTS` and `Cp1cHead`.
- `owner_workflow.py`: CP-1C added after CP-2G to `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["peer_benchmark"]`, `_ENTRY_VALIDATORS` and `OWNER_SPECS` (`module_context`, `sources=True`, `journaled`, `owner_core`).
- D12: new `bindings/cp1c.py`; `CP1C` appended last in `SHIPPED_MAPS`; one `peer-positioning` `_Spec` row in `_RELATIVE_VALUE`. The `_spec_of` loop already read `_RELATIVE_VALUE`.
- Method note moved to `src/deploy_vii/methods/cp1c.md` with "Stage 2 notes".

**Backlog rows: all done**
- Clipped issue lines at every f-string site, including prose lines.
- Bounded issue list (`listed_issues`) and bounded raised join.
- Blank citation quote gets the `<path>.quote: empty text` frame before the page check.
- Payload parsed only through `json_object`; shape refusal is `BAD_PAYLOAD`.
- RunText check uses one TypeAdapter; the verbatim path set has sinks.
- Synthetic limitation added by `settle`.
- A blocked head's reader returns status and hash only.
- Peer-table guard limits recorded in the method note.

**Test-first evidence** (`.../scratchpad/cp1c-batch/`)
- Red runs: `red_A.out` 22 failed / 9 passed; `red_B.out` 91 failed / 31 passed.
- Part by part: `mid_core.out` 33 failed, `mid_reg.out` 17 failed, `mid_bind.out` 9 failed.
- Green: `green_reader.out` 123 passed. Final count is 138 fast tests.

**Gates (exit codes)**
- Five-file set: 0 (658 passed).
- All 13 `tests/test_connect_*.py` in one run: 0 (2054 passed, 2 skipped).
- `test_connected_render`: 0 (14 passed).
- `ruff check` on changed files: 0. The only hit is SIM102 at `report_view.py:293`, which I confirmed is already there at 8d5d404.
- `ruff format --check`: 0. `MYPYPATH=src mypy --strict` on the 9 changed files: 0. `pins.py --check`: 0.
- Suppressions unchanged: noqa 13, type: ignore 8. No edits to `cases/`, `methodology.json` or TOOL-CONTRACT.
- Extra: 9 other registry-touching test files, 340 passed.

**Mutants** (`mutants.py`, full copy, `PYTHONDONTWRITEBYTECODE=1`, gate is `test_connect_cp1c.py`)
- 34 mutants: 4 adapter fields, 3 CP-1 selection terms, 5 Upstream fields, 6 registration rows, 4 OWNER_SPECS fields, SHIPPED_MAPS, 3 `_Spec` fields, 8 binding rows.
- Round 1: T1C.2 bound as `text` instead of `amount` survived. I added a test that the binding's unit class is the one class its table displays.
- Round 2: baseline 0, 34 of 34 killed, exit 0 (`mutants.out`).

**Genuine run.** Not a gate, but done to lower Stage 5 risk.
- `test_owner_cp1c.py` positive-path subset, about 37 minutes: 22 passed, 1 failed.
- The passes include A1 positive head equals the oracle, inherited limitations, tool use, ruling S6 readiness, refusals r01/r04/r06/r07/r12/r14, blocked, t01–t03, stale_binding for CP-0 and CP-1, A4 tamper reaching the probe, A7 and the D3 reader.
- The failure was a bug in the test: the attempt's inputs include `prepared-pack`, which has no head. Fixed in 3d0392e. I checked the fixed assertions against that store's data before pytest deleted its temp directory, but did not re-run the test in pytest.
- A2 refused passes (1.4 s). CP-0 plus source_context smoke is valid for all three cases.

**DeliveryScope row (lease, word for word)**
`G2 DeliveryScope(scope_id="cp1c-fp03-peers", pathway="relative_value", requested_modules=("CP-1C",), sections=("peer-positioning",), rails=("evidence","limitations"))`. The G2 test is a skip that names it (Stage 3).

**Close-release text**
1. TOOL-CONTRACT.md has no CP-1C `peer_benchmark` row. I was not allowed to edit it.
2. Commit `cases/cp1c-owner/cp1c-view-tree.json` from product-settled heads.
3. Derived-fact citations: I kept the frozen oracle lineage (`expected.lineage_rule`, lease A1). The round 3 rule is one Citation per (source, page). Needs a ruling.
4. `docs/MODULES.csv` CP-1C `downstream_consumption` says `unverified`; the lease says `open`. D3 stays open until CP-3 reads `cp1c_reader` under its own lease.
5. View `rules.direction`: the lease key tree has it, `expected.execution.tool_use.view` omits it. I followed the lease.
6. `tests/test_connect_cp3d.py`: one assertion changed from the full `_RELATIVE_VALUE` list to "the creator's row first", so later appends don't break it.

**Found, not fixed** (outside my scope; for the owner)
- D12 chain forks that were already there: the CP-2D, CP-2E and CP-L10 `shipped.py` records chain from 4ef3f9ff, and CP-2D `report_view.py` from 51a6853e. My records chain correctly from 0899560e and a073edd7.
- CP-1D `_validate_step` parses the raw payload with `model_validate_json` rather than `json_object` (possible §6 deviation, Info).
- Stage 1 `parse_peer_source` takes a keyword `issuer_name` that the lease signature omits (Info).

**Deferred commands**
- `PYTHONPATH=src:tests pytest -q -p no:cacheprovider tests/test_owner_cp1c.py` (three promotions, about 12–15 minutes each, heavy-job lock).
- `python3 -I cases/cp1c-owner/builder/build.py`, then compare sha256 of the three files.

Not verified: the gap and no_peers closed runs, r10/r13, the model-text sweep at run level and the A4 step-output test outcome were not run on genuine stores; the fixed bound-input owner test was not re-run in pytest; G2 rendering (Stage 3); D3 consumption (no consumer exists).

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
