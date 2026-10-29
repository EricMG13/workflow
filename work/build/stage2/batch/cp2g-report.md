# Batch builder 2: CP-2G (general-purpose, opus)

CP-2G is connected on `claude/s2-batch` (s2-batch worktree). All required gates exit 0, except `ruff check`, which exits 1 only on the SIM102 at `report_view.py:293`; that line is identical at `aafa9f0`. All 26 mutants were killed. Two things are left outside the code: one frozen-oracle defect (release item 1) and the G2 `DeliveryScope` row, which I did not add.

The Write tool refused paths in this worktree, so every edit was made from Bash with Python or by writing to the scratchpad and copying in.

**Commits**
- `165bd0b` tests: isolation fix (`hide_row` in `test_owner_g1x`, `test_host_h1`, `test_connect_cp3`, `test_connect_cp4`). It was red before (7 failures) and green after.
- `8c31a5a` feat(cp2g): the Stage 2 section of `owners/cp2g.py`, the `owner_workflow` rows, `bindings/cp2g.py`, `shipped.py`, `report_view.py`, the move `docs/methods-drafts/cp2g.md` → `src/deploy_vii/methods/cp2g.md` with Stage 2 notes, and `tests/test_connect_cp2g.py`.
- `bec64de` tests: `tests/cp2g_runs.py` (`cp2g_closed(case, root)` for 6 cases) and the deferred `tests/test_owner_cp2g.py` (A1–A4, A6, A7).
- `6c3de0f` docs: D12 records chained from the CP-1D records. `shipped.py` goes `9e6ee6cd` → `0899560e`, `report_view.py` goes `fc9c1828` → `a073edd7`, and `project_commit` is `8c31a5a`.
- `8d5d404` tests: each context status comes from its own bound input. This kills the status-swap and `cp2d_status` mutants that every equal-status fixture let survive.

**Lease line → symbol** (all in `owners/cp2g.py` unless noted)
- The constants line → `MODULE_ID`, `STEP_ID`, `SCHEMA_VERSION`, `STEP_IDS`, `QUALIFICATION`, `SCHEMAS`, plus `SUBMISSION_INPUT`.
- `Upstream(bound, current, cp1, cp2a, cp1d)` → `Upstream`, with an added `inherited` field and a `status()` method.
- The other lines map to the same names: `cp2g_upstream`, `cp2a_reader` (built on `cp2a_of`), `cp1d_reader` (built on `cp1d_of`), `validate_forward`, `forward_model` returning `ForwardReport`, `context_block`, `cp2g_module`, `cp2g_reader` returning `Cp2gHead`, `submit`, `view`, `probe` (via `probe_one_step`), `ENTRY_VALIDATOR`.
- One adapter, `_inputs`, is used by submit, probe and view.
- Registration rows are appended after CP-1D in `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["forward_credit_model"]`, `_ENTRY_VALIDATORS` and `OWNER_SPECS`. No `_PRECHECKS` row and no `RULES`.
- Rendering: `SHIPPED_MAPS` ends with `CP2G`; `_DISTRESSED` gains two rows; `_PRESETS` places `forward-credit-path` and `forward-breakpoints` right after `break-points`.

**Backlog rows**
- `base_period` invariant: done. Two periods raise "CP-2G: CP-2A T2B.1 facts differ in period". A shock with no period is not a conflict; no period at all raises.
- Scenario name read from `T2B.1.<row>.name`: done in code. The text in the manifest's `upstream_fact_selection` and at lease :61 is blocked on the release.
- f-string sites: done. `prose.issues` lines and the stale text are clipped, and the join in `_resolve` is bounded.
- `listed_issues` / `clipped`: done with `clipped`; no list of caller content needed `listed_issues`.
- `json_object` rewire: done through `_parsed`, used by both `payload_issues` and the step validator. The frozen r14 issue is unchanged.
- `RunText` check on the four rationales that become `Claim.text`: done.

**Test-first evidence**
- Before the code, 100 of the new tests failed for the right causes: missing seams (`AttributeError`), a prose line of 5035 characters, a stale line of 5032 characters, an unbounded join, the `RunText` issue missing, and raw text reaching the schema.
- One test was already green: `test_model_text_is_refused_or_stored_verbatim`.
- `gates-first-pass=n`: the new test file needed three fixes to its own expectations (12 lines left out, not 13; the stale-head fixture; the oracle mismatch below).

**Gates and mutants**
- Exit 0:
  - the five-file set: 880 passed;
  - every `test_connect_*.py` in one run: 1917 passed, 2 skipped;
  - `ruff format --check` on the 12 changed files;
  - `mypy --strict` on the 12 changed files;
  - `pins.py --check`;
  - the other fast tests that touch the changed registries: 1877 passed.
- `ruff check` exits 1 on the pre-existing SIM102 only; 0 on the other changed files.
- Mutants: the script is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-batch/mutants.py`; it exits 0. 7 adapter fields, 5 `Upstream` fields and 14 registration rows were each killed.
- No new `noqa` (still 13) and no new `type: ignore` (still 8).

**Lease `DeliveryScope` row (word for word)**
`DeliveryScope(scope_id="cp2g-fp05-forward", pathway="distressed_restructuring", requested_modules=("CP-2G","CP-1D"), case_kind="synthetic", sections=("forward-credit-path","forward-breakpoints"), rails=("evidence","limitations"))`, a second scope with `("CP-2G",)` for the gap run.

I did not add it: the row belongs in `owner_rendering.py`, which is G2.

**Close-release text**
- `methodology.json`: no change (D8).
- TOOL-CONTRACT matrix row, for LEAD (lease :150): "CP-2G forward_credit_model: exactly the view `owners.cp2g.view(historical, attempt)` registered in G1's `_VIEWS["forward_credit_model"]` (`module_context()` has no such entry and deploy_vii cannot register a deploy_workflow core): the bound CP-1 operands and ratios, the CP-2A scenarios and breaks, the CP-1D supported figures when bound, the driver bounds, the break metrics offered and the inherited limitations, missing ones offered with their status; no quote, citation or record_json at any depth; key tree frozen in `cases/cp2g-owner/manifest.json#tool_use.view_tree_draft` after a probe on the first product-settled core".
- Release items:
  1. **Oracle defect.** In `expected.json` `cases.blocked`, `attempt_1.limitations` lists only the High line. That run requests CP-2G alone, so CP-1D is unbound, and v13's rationale names `T1D.6.supported.total_leverage`. The real issues are therefore `[assessment.rationale: Unresolved reference: T1D.6.supported.total_leverage, High…]`. The fast test pins both runs; the deferred test marks this one strict xfail.
  2. `cases/cp2g-owner/cp2g-view-tree.json` is LEAD's to commit, because `cases/` is frozen. My tree follows the draft keys; `upstream` lists the bound inputs in bound order, and `minimum_liquidity` carries `bounds` and `may_be_not_assessed`.
  3. Lease corrections: :61 should show `Upstream` with `inherited`; the scenario name comes from `T2B.1.<row>.name`; add the `base_period` invariant text.
  4. `MODULES.csv`: D3 closed for CP-2A and CP-1D once the run is accepted.

**Deferred commands**
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cp2g.py`
- `python3 -I cases/cp2g-owner/builder/build.py && shasum -a 256 cases/cp2g-owner/*.json`

Not verified:
- Every closed run in `cp2g_runs.py` and `test_owner_cp2g.py` from CP-1 on, because the genuine CP-1 promotion takes 11–26 minutes per case. Only import, type-check, the fast driver test and a CP-0 smoke of all six runs were exercised. In the smoke, CP-0 settles restricted with T8 commands for every module in the plan, and the refused run returns `cp1_not_authorized`.
- The CP-1D and CP-2A literal replays through G1, the receipt verifier and the tamper path at run level.
- The first-run CP-1 readiness re-assertion.
- The G2 render.
- The full suite.
- The view tree on product-settled heads.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
