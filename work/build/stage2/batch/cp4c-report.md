# Parallel connector: CP-4C (general-purpose, opus)

The CP-4C connection is built and committed on `claude/s2b-cp4c`. Every gate exits 0 apart from ruff's one pre-existing finding, and all 57 mutants are killed. The genuine runs (`tests/test_owner_cp4c.py`) are written but not run, so CP-4C is built, not done, until Stage 5 runs them.

**Commits** (on top of 8d5d404)
- c58996b: backlog rows
- d373439: the connection
- 54c6a0b: the method note, `tests/cp4c_runs.py` and `tests/test_owner_cp4c.py`
- 5ae21cc: a test that the reader reports an accepted head's own status

**Lease lines and their symbols**
- Public API (`owners/cp4c.py`):
  - `MODULE_ID`, `STEP_ID`, `STEP_IDS`, `QUALIFICATION`, `SCHEMAS`, plus `SUBMISSION_INPUT`.
  - `Upstream` has one extra field the lease does not list, `inherited` (default `()`, the CP-2G precedent).
  - `cp4c_upstream`; `cp2a_reader`, which takes the row both T2H.3 source texts name; `cp4_reader`, which reads T4C.11, T4.10.r02 and T4.13.
  - The lease's `cp2g_reader` is `owners.cp2g.cp2g_reader`, selected into `cp4c.Cp2gHead` by `cp2g_of` (ruling Q6).
  - `waterfall`, `validate_restructuring`, `restructuring`, `context_block`, `cp4c_module`, `cp4c_reader`, `submit`, `view`, `probe`, `RULES`. The single adapter all of them go through is `_inputs`.
- Files:
  - `owner_workflow.py`: the `OWNER_SPECS["CP-4C"]` row (sources=True, inputs="module_context", rules="journaled", entry "owner_core"), plus `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["restructuring_fulcrum"]` and `_ENTRY_VALIDATORS`. No `_PRECHECKS` row.
  - `bindings/cp4c.py` and the `SHIPPED_MAPS` row.
  - Two `_DISTRESSED` `_Spec` rows.
  - `methods/cp4c.md`, `tests/test_owner_cp4c.py`, `tests/cp4c_runs.py`.

**Backlog rows: all done**
- `base_period` now reads the period from the shocks that state one, so a shock with no period is not a conflict (round 5 item 16, pinned by a test). Two different periods raise; no period at all raises.
- The source patterns use `[0-9]` with escaped dots.
- The base-period basis comes from the applied row, not a hard-coded `s03`.
- Every caller-quoting issue line is cut at 600 characters, and a raised composition lists at most 20 lines.
- A rationale is also checked as `RunText`.
- The payload is read through `json_object`.
- `source_row` and its frozen oracle are unchanged (Q-SQ1).

**Test-first evidence**
- Backlog: 10 tests red for their own causes: the period conflict, unclipped lines of 5032 characters, the missing "further issues" tail, the missing `RunText` issue, and no `json_object` call.
- Connection: 93 red on the first run:
  - missing attributes: `submit` x57, `cp4c_upstream` x15, `_inputs` x5, `view` x3, `SCHEMAS` x3, `RULES` x2;
  - registry KeyErrors;
  - `_check_specs` refused with `not_permitted`;
  - CP-4C absent from `SHIPPED_MAPS`.
- Method note: FileNotFoundError.
- Mutant survivors: two survived the first pass and are now killed:
  - the reader's constant status, killed by the new test;
  - the `\d` mutant, now applied to both patterns. Changing only the first pattern makes no difference, because the second pattern and the same-row check still refuse the text.

**Gates**
- Fast set (5 files): exit 0, 1721 passed.
- All `test_connect_*.py` together: exit 0, 2033 passed, 2 skipped.
- `ruff check` on changed files: exit 1, from the SIM102 at `report_view.py:293` alone, which predates this work.
- `ruff format --check`: 0. `mypy --strict`: 0. `pins.py --check`: 0.
- Mutants (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-batch/mutants.py`): exit 0, 57/57 killed.
- Suppression counts are still 13 `noqa` and 8 `type: ignore`.

**DeliveryScope row** (lease, word for word; not added, it belongs to G2 in Stage 3): `DeliveryScope(scope_id="cp4c-fp05-recovery", pathway="distressed_restructuring", requested_modules=("CP-4C",), sections=("recovery-by-class","value-allocation-claims"), rails=("evidence","limitations"))`

**Close-release text:** "CP-4C connected (Stage 2): owner core with one store adapter for submit, probe and view, the read_inputs view, the cited-page rule, readers (CP-2G through `cp2g_reader`), append-only registrations, bindings and the two FP05 `_Spec` rows. D3 for CP-2G, CP-2A and CP-4 is proven on seeded heads, one of them settled by the real CP-2G core. The genuine runs are deferred to Stage 5."

**Reused files touched (for the D12 manifest records)**
- `src/deploy_vii/report_view.py`: a073edd7... before, 77b1a0304a8445b4c6700840416121dba7b2f8eca9410d36091505c663144def after.
- `src/deploy_vii/bindings/shipped.py`: 0899560e... before, c40b4b5ba8eaa41cb331fe1a6f79d78b982a006685d5e83fe991f69ef826c8b6 after.

**For the integrator and LEAD**
1. v08 oracle gap. v08 cites identity page:1, which is outside the step's scope, so at run level the journal holds a second line: "Cited page not read through read_pages: identity page:1". The oracle's `refusal_rules` say the limitations equal the issues. Both test files pin the two-line form; the oracle is not edited.
2. Merge conflict ahead in `tests/test_connect_cp3.py`. It hard-coded "CP-4C" and "CP-3C" as modules with no spec, which breaks once either gains one. I changed it to use `_specless_modules()` alone, which gives the same coverage. The CP-3C connector will likely edit the same line, so the two edits will conflict; the resolved line is the same either way.
3. Not mine to edit. The lease asks for a `docs/TOOL-CONTRACT.md` row and for `cases/cp4c-owner/cp4c-view-tree.json` to be committed; both are on the forbidden list.
4. Lease naming. The lease names `Claims.from_sources`; the Stage 1 core implements it as `claim_classes`, which I left untouched.
5. `cp4_reader` is narrower than the Stage 1 test head. It returns only the lease's selection, so the adapter-equality test compares against the Stage 1 head narrowed the same way, and also checks that `compute` gives exactly the Stage 1 result.
6. Shape issues keep a raw Pydantic parse. For text `json_object` refuses, the parse still runs to produce Pydantic's own shape issue (CP-2G precedent, needed for r12).
7. Statement rows. The view offers every readable row under the page's "Period end" header; Python does not classify which rows are liabilities.
8. Required heads. CP-1, CP-2A, CP-4 and CP-2G are required edges, so their readers refuse a blocked head.

**Deferred commands**
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cp4c.py` (Stage 5; 11-26 minutes per case)
- `python3 -I cases/cp4c-owner/builder/build.py && shasum -a 256 cases/cp4c-owner/*.json`

**Not verified:**
- The genuine runs: CP-1 promotion on the legal pack, the CP-2A, CP-4 and CP-2G literals replayed in this pack, the CP-4C run, tamper and blocked at run level, and the first-run T4.18 confirmation. Only the CP-0 stage of the driver was smoke-run: valid for positive, and `cp1_not_authorized` for refused.
- The G2 render.
- `tests/test_stage2_classes.py` (the final builder's).
- Integration with the CP-1C, CP-3C and CP-2H branches.

`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n` (`n` because the first mutant pass left two survivors)
