# CP-3 Stage 2 report (mx-feature)

CP-3 Stage 2 connection is built and committed as fc380d6 on claude/s2-cp3, cut from 2cb5a7e. It cannot yet run end to end: R3 `create` refuses `not_permitted` because of a G1 guard, which is outside Q2 scope (details in the LEAD text).

**Gates (all exit 0)**
- `pytest` on test_connect_cp3, test_method_cp3, test_owner_g1x, test_host_h1 and test_defect_classes_selfcheck: 393 passed, about 10 s.
- `ruff check` and `ruff format --check` on the 6 changed files.
- `MYPYPATH=src:tests mypy --strict` on the same 6 files.
- Mutants: 23 of 23 killed. Scripts and probes are in `<S>/cp3-s2/` (`mutants.py`, `p_blank.py`, `p_store.py`, `p_create.py`, `p_create2.py`). They cover each registration row, each field of the OwnerSpec row, the cp3.py parts and the driver's composition rules.
- Test-first: with `git checkout src`, test_connect_cp3 failed for the right cause (the registrations and `probe` did not exist). The src patch was then reapplied.

**Files**
- `src/deploy_workflow/owners/cp3.py`: adds `QUALIFICATION`, `ENTRY_VALIDATOR` and `probe`. `probe` reuses `cp1a.probe_one_step` with `_validate_step` and `cp3_module`.
- `src/deploy_workflow/owner_workflow.py`: appends CP-3 to `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_ENTRY_VALIDATORS` and `OwnerSpec` (after CP-MODEL).
- `tests/test_connect_cp3.py`: fast tests.
- `tests/cp3_cp6_runs.py`: `cp3_closed` plus `reach_cp3`, `close`, `drive_cp3` and `literal` composition. There is no `cp6_closed`.
- `tests/test_owner_cp3.py`: the run assertions, written but not run (18 tests collect).
- `tests/s1a_runs.py`: `drive_cp1` gains an optional `context=` argument, backward compatible, so the driver can pass its own source-context literal.

**Lease D12 lines**
The lease's D12 text is its Files and Public API sections. The `host.py` and `methodology.json` lines are not CP-3's.

| Lease line | Status | Symbol |
|---|---|---|
| `OWNER_SPECS["CP-3"]` row | built | `OwnerSpec(module_id="CP-3", relative_value, sources=True, extract=False, upstream_grant=None, inputs="none", rules="journaled", entry="model_payload", kind="analytical", publish=None)` |
| `SUPPORTED_ANALYTICAL` +CP-3 | built | `owner_workflow.py` |
| `_QUALIFICATION` (PROMOTED) | built | `cp3.QUALIFICATION`, which is `cp3_relative_value.PROMOTED` |
| `_PROBES` +CP-3 | built | `cp3.probe` |
| `owners.cp3.probe` | built | positional seam, per the protocol |
| `_ENTRY_VALIDATORS` +CP-3 | built | `cp3._validate_step`; not listed in the lease but required by protocol §2 and `_check_steps` |
| `OWNER_SPECS["CP-6"]`, `owners/cp6.py` (`probe`, `view`), CP-6 registrations | blocked on CP-6 freeze | not touched |
| `methodology.json` `T6-FINAL` | blocked on CP-6 freeze (Q7) | not touched |
| `cp6_closed` | blocked on CP-6 freeze | not exported |
| `host.py` / `_SOURCE_STEPS` | none | the lease assigns it to H1, and it is already in the lane |

No `_CORES` row, `_VIEWS` row, `_PRECHECKS` row, `view`, `RULES`, `SCHEMAS`, `submit` or reader: CP-3 is live-contract with `inputs="none"`, and the lease names none of them. The store adapter is the engine's own `cp3_upstream`, which `_validate_step` and `probe` already use.

`bindings/cp3.py`, `shipped.py` and the `relative-value` `_Spec` row already exist. A test checks that `validate_bindings(view, SHIPPED_MAPS) == ()` over the composed module and that `_spec_of("relative-value").owner == "CP-3"`.

**Backlog rows (Every module)**
- Guard-limit notes in `methods/cp3.md`: not applicable. They are named only for CP-1D, CP-3D, CP-8, CP-2E and CP-2H.
- Blank support/citation quotes: inventoried with `p_blank.py`. 54 variants (3 quote paths, the 9 blank values `BLANK_VALUES`, plus the `as_of` and `limitation` text fields) were all refused. The quote refusals use the engine's own wording (`malformed citation` for `""`, `quote not found` otherwise), not the `<path>: empty text` frame. That wording is in `src/deploy_vii`, which Stage 2 does not edit. This is Info, not the Medium acceptance defect. Regression test: `test_a_blank_quote_is_never_accepted`.
- Caller-quoting issue lines: not applicable, because CP-3 gained no `RULES` or `precheck`.
- Hostile-text set over `SCHEMAS`: the shared set is not in `defect_classes.py` yet. A local copy runs over `RelativeValueSubmission` (9 inputs, only `ValueError` allowed). It is marked as a stand-in for the shared set.
- CP-3 per-module rows: none exist.
- Owner items: not touched.

**DeliveryScope row:** none in lease.

**Text for LEAD**
1. **Blocker for `cp3_closed`.** After CP-3 registers, R3 `OwnerWorkflow.create` still refuses `not_permitted` for both cases (`p_create.py`). The R3 plan is `CP-0, CP-1, CP-1A, CP-2, CP-MODEL, CP-3`, and `_check_specs` refuses an analytical module after the deterministic one (the `seen_deterministic` guard). Without CP-MODEL in `requested_modules`, `create` succeeds (`p_create2.py`). Protocol §5 says "add when a lease does", but the CP-3 lease does not list this G1 change, and it touches the publication and terminal order, so I did not make it. A G1 change is needed before Stage 5 can run `cp3_closed`. The driver follows S1a's order: CP-3 after CP-2, then `finish` publishes CP-MODEL and seals. Whether the walk accepts that order is untested.
2. **D2 view row:** none. CP-3 has no `view` and no TOOL-CONTRACT row. The lease says CP-6 gets the narrowed view.
3. **`methodology.json` and TOOL-CONTRACT:** no edit needed for CP-3. `T6-FINAL` waits for the CP-6 freeze (Q7).
4. **Backlog row "`readiness.citation_issues` accepts a whitespace-only quote":** CP-3's own refusal already catches it, via the page-occurrence check.
5. The `Not verified` item on the driver's CP-3 `{{FIG:}}` binding (below) also belongs to LEAD's attention.

**Deferred commands for `work/build/deferred-runs.md`** (from the lease; the pytest lines use the venv python and `PYTHONPATH=src:tests`)
```
"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -I cases/cp3-cp6-owner/builder/build.py
mkdir /tmp/deploy-workflow-heavy-job.lock && { PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider -o faulthandler_timeout=1800 tests/test_owner_cp3.py; rc=$?; rmdir /tmp/deploy-workflow-heavy-job.lock; exit $rc; }
```
The first line is the lease's light builder reproduction. The second runs the `cp3_closed` driver (R3, both cases; two real CP-1 promotions, 11-26 min each) through `tests/test_owner_cp3.py`. It is blocked until the G1 change in point 1 lands. Also deferred: `test_owner_workflow.py`, `test_owner_s1a.py`, the source suites and the render runs.

**Not written:** the A4 tamper refusals (3), the blocked-CP-1A variant run, the stale-snapshot refusal, the create-time refusals (alias, CP-4C in a CP-3 run, spec override), the CONTEXT-block run checks, and the D3 test. D3 stays open and no completion claim is made. The suite asserts only that no CP-5 or CP-6 head exists in R3 and that `cp3_reader` is absent.

Not verified: the driver (`cp3_closed`, `reach_cp3`, `close`) and every assertion in `tests/test_owner_cp3.py` have never run; only pack assembly and literal composition are tested. The driver's call order, the CP-3 `{{FIG:}}` binding from the CP-1 head without the read-body cross-check, and the `settled_limitations` equality are unproven. CP-MODEL placement relative to CP-3 is not exercised (G1 guard). The probe was run only over fixture heads in a real `Execution` store, not over a promoted run. The receipt verifier on a CP-3 run, host session scope and `_SOURCE_STEPS` for CP-3 at run time, rendering, mutation of `probe_one_step`, GitNexus `impact`/`detect_changes`, jscpd, `complexipy`, `bandit` and `pip-audit` were not run. The hostile-text set is a local stand-in, not the shared one.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a
