# CP-L10 Stage 2 report (mx-feature)

CP-L10 Stage 2 is connected on `claude/s2-cpl10`. Commits are 3b3ad2b (code) and e0bb540 (reuse-manifest record); Step 0 held (tree clean, HEAD 3f3eba4). The five-file gate set exits 0 with 498 passed, ruff check and ruff format --check exit 0, and mypy --strict on the changed files is clean. 26 of 26 mutants were killed. The branch diff is 1308 lines against the 800-line PR gate. The D3 reader ships with a pin test and claims no completion, as the lease says.

**Rulings applied.**
- **Q1.** The lease row is quoted below, not written by me.
- **Q8.** No `MODULE_FAMILY` row is added or proposed.
- **Q6.** `cpl10_reader` stays in `owners/cpl10.py`.
- **Protocol cite.** The rewire cite is §6 in code, tests and this report.

**Files and the lease line each implements** (all under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cpl10`):
- `src/deploy_workflow/owners/cpl10.py`, Stage 2 section at the end:
  - **Lease line 1:** `STEP_IDS` is checked as a tuple of str; `SCHEMAS` and `QUALIFICATION` are in place.
  - **Lease line 2:** `cpl10_upstream(store, attempt)` is the adapter, used by `submit`, `probe` and `view`.
  - **Lease line 3:** `context_block(*, upstream)` and `view`.
  - **Lease line 4:** `screen_report`, the `ScreenReport` Contract and `cpl10_module(report, *, inputs, attempt)`.
  - **Lease line 5:** `_validate_step`, also exported as `ENTRY_VALIDATOR`.
  - **Lease line 6:** `submit` and `probe`; `probe` reuses `cp1a.probe_one_step`.
  - **Lease line 7:** `cpl10_reader`, `Cpl10Head` and `TopicRead`.
  - `Upstream` gains a defaulted field `inherited_limitations`.
- `src/deploy_workflow/owner_workflow.py`, rows appended last: `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["change_screen"]`, `_ENTRY_VALIDATORS` and the `OwnerSpec` (`entry="owner_core"`, `inputs="module_context"`, `sources=False`, `rules="none"`). There is no `_PRECHECKS` row and no `_OWNER_SCOPES` row, as the lease says.
- `src/deploy_vii/bindings/cpl10.py` (new): TL10.1, TL10.2, TL10.5 and TL10.3 go to `evidence`, TL10.4 to `limitations`, slots `cpl10-tl10-N`.
- `src/deploy_vii/bindings/shipped.py`: `CPL10` appended last. The lease states no position, so I appended it.
- `src/deploy_vii/methods/cpl10.md` (new, from `docs/methods-drafts/cpl10.md`): TL10.5 added, the draft banner removed, and the L10-b substring limit noted.
- `docs/reuse/manifest.json`: one `post_import_patches` entry for `shipped.py`.
- Tests: `tests/test_connect_cpl10.py` (54 tests), plus `tests/cpl10_runs.py` and `tests/test_owner_cpl10.py`.

**Backlog rows**
- **Exact change `-0` or exponent form: done.** I found the cause by probe: the render path was fine (`format_value` prints `0.00`), but the stored change was `-0` for 0 against -0 and `0E+2` for `1E+2` minus itself, which changes the hash, the view and the reader text. `_plain` normalises it, test-first. A magnitude below one millionth still prints in scientific notation, and the rating uses the exact value. Both limits are recorded in `methods/cpl10.md`.
- **L10-b note: done.**
- **Missing-change lineage: blocked.** It waits on LEAD's release.
- **"Every module" rows: nothing to apply, except as noted.**
  - Guard-limit notes are not listed for CP-L10.
  - CP-L10 takes no citations, so the blank quote row does not apply.
  - There is no `RULES`/`precheck`, so `listed_issues` does not apply. Step issues are bounded by the journal.
  - The `is_blank` Cc change and the owner items are LEAD's.
- **Protocol §6 rewire: done.** `_parse` now reads model text only through `json_object`/`exact_json`, for text, bytes and mapping alike. A payload outside the bounded parse is the shape issue `(root): not a JSON object within the payload bounds`. Pydantic-shaped errors are unchanged.

**Test-first evidence.** I wrote `tests/test_connect_cpl10.py` before any code. The first run was red: collection error `ModuleNotFoundError: deploy_vii.bindings.cpl10`, so each test's own cause was not isolated per test. After implementing, 2 tests failed on my own test-data mistakes (key names, tuple vs list), which I corrected, and `test_each_head_status_word_is_its_own` was first wrong on the status word. The first mutant run showed 3 survivors (the two status-word fields and the TL10.5 unit); I added tests for them and all 26 were then killed. The mutant script and results are in `<S>/cpl10-s2/` (`mutants.py`, `result.txt`).

**For LEAD**
- **`methodology.json`:** no edit is needed; D4 and TL10.5 are already in it.
- **TOOL-CONTRACT matrix row:** `CP-L10 change_screen`, `module_context`, no pack tools, one ok `read_inputs`, `invoke` refused `not_permitted`.
- **D2 view row:** the keys are `upstream`, `periods`, `topics`, `pair_screens`, `rules` and `inherited_limitations`. `upstream[].status` is the status word, e.g. "With limitations". `cases/cpl10-owner/cpl10-view-tree.json` is not committed, because I may not edit `cases/`.
- **`MODULE_FAMILY`:** nothing is proposed, per Q8.
- **`DELIVERY_SCOPES`:** the lease (`docs/CPL10-OWNER-LEASE.md`, "Files" and "The run") says: "G2 `owner_rendering.py`: one `DeliveryScope` for `slice-cpl10-screen` (rails only)." The run is `cpl10-owner-positive`, pathway `credit_snapshot`, `requested_modules = ("CP-L10",)`.
- **No `_Spec` row and no composition:** the module owns no Front Page block.

**Deferred commands for `work/build/deferred-runs.md`**
- `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cpl10.py` (a genuine CP-1 promotion).
- `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` (`OWNER_SPECS` now has a 6th row), and the `cpl10_closed` driver run for `positive` and `limited`.
- The render runs (`tests/test_cp1_chart_render.py` and the `SHIPPED_MAPS` consumers).
- The lease's other deferred commands.

**Not verified:**
- **`tests/cpl10_runs.py` and `tests/test_owner_cpl10.py`** were only ruff- and mypy-checked, never run. The CP-1 readiness marker binding is a best reading of the read body: it matches kpi rows on key and period column, not on `observation_ids`, and falls back to the step's pre-fill if the read has no `inputs_sha256`.
- **No `OwnerWorkflow` run, receipt verification or host `_submission_producer_inputs` run.** The fast tests use a real `Execution` with hand-made CP-0 and CP-1 heads, not a genuine CP-1 promotion.
- **The lease's tamper case** (forged blobs, audit and receipt) was approximated by a forged `head_module` in `probe` only.
- **Blocked-CP-1 `RefusedBegin`, the refused-run case and the render states** were not exercised.
- **`test_owner_g1x.py` and `test_host_h1.py`** pass, but they never touch the new rows.
- **An unbindable CP-1** (a missing T4.10 label) settles the step as an issue `CP-L10: <reason>`, but `view` raises `identity_mismatch`. Only the missing-input path is tested, not a missing operand.
- **Citation order of claims** was checked against the oracle claim texts, not their `citations` against CP-1's.
- **Column labels** (`field` in words) are my choice, since the lease leaves them open.
- **No test applies to** the docs and registry-record edits.

agent=mx-feature fix-rounds=0 gates-first-pass=n
