# CP-4 Stage 2 report (mx-feature)

CP-4 Stage 2 report (agent=mx-feature)

Commit 67b46ed on claude/s2-cp4, cut at 2cb5a7e. Q3 and Q4 are done as ruled. The driver, `test_owner_cp4.py` and the D3 test were not built (see "Not built").

The Write tool was blocked by the hook for the s2-cp4 path, because the session's own worktree is a different one. I wrote files through Bash heredocs and python, as the dispatch directed, with every command run from the s2-cp4 root. Please check you are fine with that.

**Files**
- `src/deploy_workflow/owner_workflow.py`
  - `StepSpec.inputs` and the `step()` helper now accept `"step_context"`.
  - `_inputs`: `module_context` and `step_context` share one branch, `_VIEWS[step](historical, attempt)`. A missing `_VIEWS` row now raises `WorkflowError("not_permitted")`, where it used to raise `KeyError`. This is a small hardening beyond the ruling, and it covers the verifier's read recompute.
  - `_check_steps`: the clause now covers `step_context` with no `_VIEWS` row.
  - Registrations, each appended last in its dict:
    - `_VIEWS["legal_covenants"] = cp4.view`
    - `_ENTRY_VALIDATORS["CP-4"] = cp4.ENTRY_VALIDATOR`
    - `_PRECHECKS["CP-4"] = cp4.precheck`
    - `_PROBES["CP-4"] = cp4.probe`
    - `_QUALIFICATION["CP-4"] = cp4_legal.PROMOTED`
    - `"CP-4"` added to `SUPPORTED_ANALYTICAL`
  - `OWNER_SPECS["CP-4"]` is the lease literal. It comes after `CP-MODEL` because append-only was the rule.
- `src/deploy_workflow/owners/cp4.py` gained these. The Stage 1 code is untouched.
  - `ENTRY_VALIDATOR = cp4_legal._validate_step`. No adapter.
  - `view(historical, attempt)`: compact JSON of `cp4_legal.context_block(historical.pack(), upstream_of(historical, attempt))`, plus its sha256.
  - `probe(store, snapshot, attempt)`: `probe_one_step` with `_validate_step` and `cp4_module`.
  - `precheck(store, binding, stored)`: reads the text only through `json_object`, then the schema. Text that is not an object, or is ill-shaped, returns `()` and is refused at the journal by the step validator. That fail-through is documented in the docstring. Otherwise it returns `semantic_issues`.
- `tests/test_connect_cp4.py`: 38 tests.

**Lease and ruling map**
- Q3: validator and precheck rows, as above.
- Q4(a): the Literal in `StepSpec` and `step()`.
- Q4(b): the `_inputs` branch plus `_VIEWS["legal_covenants"]`.
- Q4(c): the `_check_steps` clause.
- The seams use the protocol positional forms.

**Backlog rows for CP-4**
- Guard-limit notes: N/A. They apply to CP-1D, CP-3D, CP-8, CP-2E and CP-2H, not CP-4.
- Blank citation quotes: inventoried and not present.
  - Probe: `<S>/cp4-s2/p_blank_quote.py`. I tried `" "`, `""`, U+200B and `"\n\t"`, in both a document row and a covenant row.
  - The engine refuses every one: `Quote/locator mismatch` for the blank ones, and `malformed citation (empty locator or quote)` for `""`.
  - The wording is not `<path>: empty text`, and the refusal is journaled-invalid, not a precheck. I made no change, because the engine is outside my scope and the defect is not present.
- Caller-quoting issue lines: N/A. The gate line carries only the row index and closed-list markers.
- Owner items (product `assert`s, jscpd, CP-2E `fx.` paths, cp2h hash check): not CP-4-specific, left alone.
- `SCHEMAS`: CP-4 has none. It is live-contract, so it uses `STEPS`. The shared hostile-text set does not apply to CP-4 in `tests/defect_classes.py`. I ran my own hostile-text inputs against `precheck`, and they all pass through with no raise.

**Test-first evidence**
- First run: 30 of 37 tests failed and 7 passed. I checked each failure was for the right cause:
  - the Literal test failed on the missing `step_context`;
  - the `_check_steps` test (any module) failed with DID NOT RAISE;
  - the `_inputs` serve test failed with `not_permitted`;
  - the `cp4.probe`, `view` and `precheck` tests failed with AttributeError.
- The `_inputs`, `_check_steps` and verifier tests build their own `step_context` spec, so they do not depend on the CP-4 registration.
- Refusals pinned:
  - `_check_steps`: a `step_context` step with no `_VIEWS` row (CP-4 and CP-1A both covered), a `module_context` step with no `_VIEWS` row, no entry validator, and five spec variants (projection, financial precheck, extract, no sources, upstream grant).
  - `_inputs`: no `_VIEWS` row and `inputs="none"`, both `not_permitted`.
  - The verifier path through `_verify_calls_reads`, with a body edit, a digest edit and a bad sequence each giving `identity_mismatch`.
- Serve paths pinned: `step_context` and `module_context`, with positional arguments only.

**Gates (all exit 0)**
- pytest over `test_connect_cp4`, `test_method_cp4`, `test_owner_g1x`, `test_host_h1` and `test_defect_classes_selfcheck`: 345 passed.
- `ruff check` and `ruff format --check` on the three changed files: clean.
- `mypy --strict` on the three changed files: clean.
- Mutants: `<S>/cp4-s2/mutants.py`, with its log in `mutants.log`. 21 mutants, all killed. They cover:
  - every registration row;
  - `OWNER_SPECS` inputs, rules and sources;
  - the `_inputs` branch, argument order and missing-row refusal;
  - the `_check_steps` clause and the Literal;
  - `ENTRY_VALIDATOR`;
  - the view's separators, digest and pack;
  - the precheck guards and result.
- One mutant survived at first: dropping the `json_object` guard. I added a test that patches `json_object` to return `None`, and it is now killed.

**For LEAD**
- `DeliveryScope`: none in lease.
- `MODULE_FAMILY`: no row added (Q8).
- Q1 reader: the CP-4 lease's Public API names no `cp4_reader`, so I built none. CP-4C's own task selects from the head.
- `methodology.json` and `TOOL-CONTRACT.md`: no edits needed from me. The lease's raw-legal and matrix row amendment is already LEAD's at freeze. D2 view row: unchanged from the lease.
- Lease text: the file-list fix is in the Q3 ruling.
- `tests/test_owner_s1a.py:1899` parametrizes `test_unplanned_module_head_refuses` over `"CP-4"`. It relied on CP-4 having no `_QUALIFICATION` row, and now has one. I expect `identity_mismatch` to hold, because the module is unplanned. That is unverified, so please run it.

**Not built**
- `tests/cp4_runs.py`, `tests/test_owner_cp4.py` and the D3 assertions. The dispatch listed no driver, and I could not run one: the store runs are deferred.
- The adapter-over-Module-objects test and the `validate_bindings` and `_spec_of` tests. `cp4_legal.upstream_of` is the adapter and already exists, and the bindings and `_Spec` rows already exist.
- I did not edit `methods/cp4.md`.

**Deferred commands** (for `work/build/deferred-runs.md`; `PY` is the repo venv python)
```
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py tests/test_owner_s1a.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -o faulthandler_timeout=1800 -m pytest -q -p no:cacheprovider tests/test_owner_cp4.py   # file not yet written
```

Not verified: no store run exercised `read_inputs` end to end, nor `create` with CP-4 requested. `test_owner_workflow.py` and `test_owner_s1a.py` were not run, including the parametrized CP-4 case noted above. The `precheck` gate was not exercised through `submit_review` with a refusal audit, or through the verifier's gate replay. No real CP-0/CP-1 heads backed `view` or `probe`: `view` was tested against Stage 1 stand-in upstreams, and `probe` was tested only for its signature. The `step()` helper's Literal is covered by mypy and the `OWNER_SPECS` equality test, not by a separate runtime test. The jscpd and complexipy gates were not run.

agent=mx-feature fix-rounds=0 gates-first-pass=y
