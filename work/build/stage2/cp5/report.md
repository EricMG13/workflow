# CP-5 Stage 2 report (mx-feature)

CP-5 Stage 2 is built and committed as 258b9ab on claude/s2-cp5 (cut at 8b46132). All gates exit 0 and one mutant survives; the CP-6-blocked rows are listed below.

**Files**
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp5/src/deploy_workflow/owners/cp5.py` (extended; the Stage 1 core was already there):
  - `QUALIFICATION = cp5_integrity.PROMOTED`.
  - `view(historical, attempt)` is `view_body(review_scope(...))`.
  - `ENTRY_VALIDATOR(execution, pack, attempt)` drops `pack` and calls `cp5_integrity._validate_step(execution, attempt)`.
  - `probe(store, snapshot, attempt)` is `probe_one_step(validate=ENTRY_VALIDATOR, build=_candidate)`.
  - The store adapter is `cp5_integrity.review_scope`, shared by all three seams. CP-5 has no `STEP_IDS`, `SCHEMAS`, `RULES` or `submit`.
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp5/src/deploy_workflow/owner_workflow.py`: rows appended last to `OWNER_SPECS`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["integrity_review"]` and `_ENTRY_VALIDATORS`. The `OWNER_SPECS` row is:
  - step `integrity_review`;
  - schema `IntegritySubmission`;
  - `inputs="module_context"`, `rules="none"`;
  - `entry="model_payload"`, kind analytical.

  No `_CORES` row and no `_PRECHECKS` row.
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cp5/tests/test_connect_cp5.py`: 41 fast tests. They run over a real `Execution` journal whose heads come from the `tests/test_method_cp5.py` fixture. I rebuilt CP-0 with a `Run CP-5` T8 command so `current_inputs` authorises CP-5.

**Lease D12 lines**
- Built: `owners.cp5.QUALIFICATION`, `probe`, `view`, `ENTRY_VALIDATOR`.
- Built: the `OWNER_SPECS` row, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS`, `_ENTRY_VALIDATORS`. `_CORES` is correctly not registered.
- Built: fast tests only. The `tests/test_connect_cp5.py` tests cover the view key tree, counts and no quote key, plus the probe and validator refusals.
- Blocked on CP-6 freeze:
  - the shared `tests/cp3_cp6_runs.py` `cp6_closed` driver;
  - the `tests/test_owner_cp5.py` run assertions;
  - RT-1 to RT-3;
  - D3, which needs CP-6 reading the CP-5 head.
- Also blocked on CP-6 freeze: the store-run items that need a full workflow run. These are submit before `read_inputs`, non-pack and upstream tool refusals, the verifier-level forged read body (`cp5-tamper-read-body`), the blocked case that settles `blocked` with `RefusedBegin` for CP-6, and workflow-level store bytes unchanged.
- No D12 item for `src/deploy_vii`, `report_view`, `bindings` or `methods` is needed: the lease says none, and `bindings/cp5.py` and `SHIPPED_MAPS` exist.
- `DeliveryScope`: none in lease. No `MODULE_FAMILY` row (Q8).

**Store-level acceptance items I did write**
- Stale binding: a re-settled CP-2 head or a stale CP-1A head makes `view` raise `identity_mismatch` and `ENTRY_VALIDATOR` return issues.
- Tamper: a forged head, a forged step output and a wrong step shape make `probe` raise `identity_mismatch`. The view digest differs for both oracle cases and with CP-3 blocked, so a constant cannot pass.
- Blocked head: with CP-3 blocked, `blocked_upstream == ["CP-3"]`, CP-3 is listed as `blocked`, and none of its claims are in `claims_to_review`. The oracle review is then refused.
- Store bytes: `view`, `ENTRY_VALIDATOR` and `probe` leave every store file hash unchanged.
- Validator: it equals the core validator on a pending journal and on a `_FrozenExecution`, and it refuses a payload with an unreviewed claim.

**Backlog rows**
- Guard-limit notes: not applicable. CP-5 is not among the listed modules (CP-1D, CP-3D, CP-8, CP-2E, CP-2H).
- Blank citation quote: CP-5 takes no caller-supplied citations. Its submission is labels and refs only, and quotes come from upstream heads. Inventory is nil, no fix is needed.
- `listed_issues`/`clipped`: CP-5 has no `RULES` or `precheck`, so no new issue lines. `validate_integrity` is Stage 1 and untouched.
- Shared hostile-text set: `tests/defect_classes.py` does not have it yet, so it is not run. Blocked until it lands.
- Per-module rows: there are none for CP-5.

**Test-first and gates**
- The `KeyError: 'CP-5'` failure on the spec-row test came before any `src` change. I did not capture each test failing individually. The mutants below cover that gap.
- Fast set (`test_connect_cp5`, `test_method_cp5`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck`): 380 passed in 14 s, exit 0.
- `ruff check` and `ruff format --check` on the three changed files: exit 0.
- `mypy --strict` on those files (`MYPYPATH=src:tests`): exit 0.
- Mutants, run in the copy under `<S>/cp5-s2/`: 13 of 14 killed. The survivor is an equivalent mutant, `attempt.number` inside `review_scope`, which `review_scope` and `view_body` never read. The scripts are `<S>/cp5-s2/mutants.py` and `<S>/cp5-s2/copy`.

**The two tests at `tests/test_owner_workflow.py:208` and `tests/test_owner_s1a.py:308`**
- I did not edit them, per the scope change. Neither has a comment at those lines to change; the lines are the parametrize decorator and the `OwnerWorkflow.create` call.
- With CP-5 registered, both still pass: `-k "unsupported_and_unknown_selection or cp5_selection"` gives 3 passed in 0.8 s.
- Both still refuse with `not_permitted`. The reason has changed: `plan` now puts CP-MODEL before CP-5 (`('CP-0','CP-1','CP-MODEL','CP-5')` for the first, and `('CP-0','CP-1','CP-1A','CP-2','CP-MODEL','CP-5')` for the second). `_check_specs` therefore refuses on the deterministic-before-analytical rule, not on a missing spec.
- Once the round 2 ruling lets CP-5 follow CP-MODEL, the CP-5 selection will no longer be refused. The first case in each test will then need a new expectation, which goes in the ride-along branch.

**Text for LEAD**
- Nothing to change in `methodology.json`.
- No TOOL-CONTRACT edit beyond the CP-5 `integrity_review` row, which the lease already says LEAD edits when it freezes.
- No D2 view row beyond that one.

**Deferred commands**
- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_owner_cp5.py`, under the heavy-job lock. The file is not written and is blocked on CP-6.
- `python -I cases/cp5-owner/builder/build.py`.
- `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` in Stage 5.

Not verified: no R6 or CP-6 run, `cp6_closed`, RT-1 to RT-3 or D3. Submit-before-read, tool refusals, the forged read body and the `RefusedBegin` blocked case were not exercised through `OwnerWorkflow`. The shared hostile-text set was not run because it has not landed. No GitNexus `detect_changes` was run. The probe happy path ran on a hand-settled journal, not a workflow-settled one.

agent=mx-feature fix-rounds=0 gates-first-pass=y
