# CP-DR Stage 2 report (mx-feature)

CP-DR Stage 2 is done and committed: SHA ca5cf5a2d34bda0ae18566fadc3276d4b00614d0 on claude/s2-cpdr (base 6e51653, tree clean at start). The fast gates and mutants pass. The store runs through `OwnerWorkflow` are deferred and unrun, so the task is built, not done.

**Files and lease mapping** (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cpdr`)
- `src/deploy_workflow/owners/cpdr.py`
  - Plug-in parts: `STEP_IDS`, `SCHEMAS`, `QUALIFICATION` (implemented), `RULES`, `ENTRY_VALIDATOR`, `view`, `probe`, `submit`.
  - Internals: `cpdr_upstream`, `context_block`, `research_module`, `_candidate`.
  - Store adapter: `_inputs`, used by `submit` and `probe`. `view` goes through `cpdr_upstream`, which `_inputs` also calls.
  - Reader: `cpdr_reader` returns `CpdrHead` / `CpdrGapHead` / `CpdrTotals` (per Q6 it stays in `owners/cpdr.py`).
- `src/deploy_workflow/owner_workflow.py`: rows appended at the end of `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["research"]`, `_ENTRY_VALIDATORS` and `OWNER_SPECS`. No `_PRECHECKS` row, as the lease says (ruling Q5). The spec is `research`, `sources=True`, `inputs=module_context`, `rules=journaled`, `entry=owner_core`.
- `src/deploy_vii/bindings/cpdr.py` (new): slots `cpdr-tdr-1` and `cpdr-tdr-2` go to evidence, `cpdr-tdr-3` to limitations.
- `src/deploy_vii/bindings/shipped.py`: `CPDR` is appended last in `SHIPPED_MAPS`.
- `src/deploy_vii/methods/cpdr.md`: moved from `docs/methods-drafts/cpdr.md` by `git mv`, with the DRAFT line dropped and a "Guard limits" section added.
- `tests/test_connect_cpdr.py` (145 tests), `tests/cpdr_runs.py` (`cpdr_closed`) and `tests/test_owner_cpdr.py`.
- `host.py` is untouched. The H1 rows for CP-DR already exist and a test pins them.
- No `report_view.py` row is needed. The bindings are rails only, so no `_Spec` row is needed. A test pins that `_spec_of("evidence")` and `_spec_of("limitations")` have no producers.

**Backlog**
- **Guard-limit notes:** done. Rule W, B8 and the item 8 comma costs do not apply to CP-DR. The note records the digit rule, the prohibited words, blank quotes, the cited-page rule, `RULES` being pure over the text, and bounded lines.
- **Blank citation quote inventory:**
  - Result: CP-DR already refused a blank quote, but through the occurrence check, with the wording `Quote/locator mismatch ... ""`. It never accepted one.
  - Fix: it now gives `gaps[i].questions[j].citations[k].quote: empty text` before the occurrence check, for the whole `defect_classes` blank set.
  - Not touched: the LEAD product item on `readiness.citation_issues` (it is in the library).
- **Caller-quoting lines:**
  - Sites cpdr:126, :137, :155, :161 and :231 and the validator's other id-quoting lines now go through `clipped`. That covers the parse `ValueError`s, the `gap_id` lines, the question-id lines and the searched-source line.
  - The `RULES` absence lines use `listed_issues`, with the count line `... N further absence claims not listed`.
  - The unread-page rule reuses `unread_citation_issues`.
  - Strictly, those validator and parse lines are not `RULES`/precheck lines. CP-DR has no precheck.
- **"Every module" items:** the owner items (product `assert`s, jscpd) are not CP-DR-specific, so nothing was done on them. Nothing in the backlog's per-module table is for CP-DR, and none of CP-DR's backlog work waits on a LEAD re-pin.

**Test-first evidence**
- Red runs before code: the blank-quote, clipped-line and `RULES` tests failed for the right causes (frame missing, 5025-character message, no `RULES`).
- The adapter, view, reader, registration and bindings tests were red at collection (missing bindings module) before the code existed. I did not watch each of those fail individually.
- Gates, all exit 0:
  - The pytest set passes: `test_connect_cpdr`, `test_method_cpdr`, `test_owner_g1x`, `test_host_h1` and `test_defect_classes_selfcheck`, 501 passed in about 10 s.
  - `ruff check` and `ruff format --check` pass on the 7 changed files.
  - `mypy --strict` passes on the same 7 files.
- Mutants: 51 run from full temporary copies with `PYTHONDONTWRITEBYTECODE=1`. They cover each adapter field, each registration row, `SHIPPED_MAPS`, the bindings, `RULES`, the view, the reader, `probe` and `submit`. All were killed except `submit-candidate-check`, which is equivalent. `finish` is handed the candidate's own JSON, so the guard cannot fire. The script is `<S>/cpdr-s2/mutants.py` with output in `<S>/cpdr-s2/out2.txt`.
- A fast test runs against a real `Execution`, with CP-0 settled through `submit_cp0_review`. It covers `submit` for the three positive cases, all 18 refusal classes as journaled invalid steps, the two blocked attempts, `probe`, a forged-fact `probe` refusal and the reader. Settled limitations, inherited limitations, facts and inputs equal the oracle.

**Deviations from the lease**
- `research_module(*, report, inputs, attempt, run)` takes an extra `run` argument, because `CpdrInputs` cannot carry the run.
- The step output retained by the journal is the canonical submission JSON.
- `bookkeeping` keeps its Stage 1 signature.

**D3 is OPEN.** The reader and a test pinning what it exposes (head hash and status, per-gap status/questions/answered, the eight totals, unresolved question ids, status only when blocked) are in. No completion is claimed.

**Text for LEAD**
- `methodology.json`: no change.
- `docs/TOOL-CONTRACT.md`: add the matrix row exactly as the lease's "Tool use" section gives it.
- D2 view row: `owners.cpdr.view` registered in `_VIEWS["research"]`, with the draft keys `gaps`, `sources`, `question_limits` and `upstream`. A gap whose text splits two ways shows the full text as `description` and null consumers and remediation.
- `docs/reuse/manifest.json`: not edited, because the `shipped.py` entry is shared across modules. The entry's `sha256` after this change is `4765995accbef6630f01016f9b4ec2973739f3f3ccae3bafa30130fa3392efb2`, and `project_commit` should be ca5cf5a. The new files (`bindings/cpdr.py`, `methods/cpdr.md`) are not imports, so they have no record.
- `MODULE_FAMILY`: not added, per Q8 and the coordinator's note.
- `DELIVERY_SCOPES`: none in lease, per Q1, and no row was created.

**Deferred commands** (for `work/build/deferred-runs.md`; not run)
- `PYTHONPATH=src "<venv>/python" -m pytest -q -p no:cacheprovider tests/test_owner_cpdr.py`
- `tests/cpdr_runs.py` runs via `cpdr_closed(case, root)` for partial, unresolved and empty_agenda.
- `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py`, and the render suites `test_legal_render.py`, `test_earnings_render.py` and `test_cp1_chart_render.py`. The render suites use `SHIPPED_MAPS` and `test_owner_s1a.py` reads `OWNER_SPECS`, which both changed.
- `python3 -I cases/cpdr-owner/builder/build.py`, then compare `shasum` against `cases/PINS.json`.

Not verified:
- Nothing ran through `OwnerWorkflow` (tool sessions, receipts, the receipt verifier's replay of the CP-DR step, the lease's tamper recipe, run-level refusals, the rendering pin). `tests/cpdr_runs.py` and `tests/test_owner_cpdr.py` are written but not run. Only `make_pack` and the mypy/ruff checks touched them.
- `test_owner_cpdr.py` has only the closed runs and the refusal matrix. The tamper, stale-binding and read-before-submit tests are not written.
- The `render`, `test_owner_workflow` and `test_owner_s1a` suites were not run after the registration and `SHIPPED_MAPS` changes.
- The `RULES` search-header and span expectations (`expect_matching_spans`, `expect_spans`) are not asserted anywhere.
- The `docs/reuse/manifest.json` record is not written.
- Mutation testing covered the tests I wrote; the old Stage 1 suite was not mutation-tested.
- `jscpd` and the suppression count were not run.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a
