# CP-DR Stage 2 review (mx-adversary)

## CP-DR Stage 2 review: commit 1e3942a (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cpdr`)

**Verdict: REQUEST CHANGES.** There is one Medium finding: required deferred tests were never written. The code itself held up under every probe I ran.

**Gates, rerun here:**
- The fast set passed: 522 tests, exit 0.
- `ruff check` and `ruff format --check` passed on the 7 changed files (exit 0).
- `mypy --strict` passed on the same files (exit 0).
- `git range-diff` shows 1e3942a is patch-identical to the reported ca5cf5a.

### Medium
**M1. `tests/test_owner_cpdr.py` is missing tests the lease requires, and brief §7 says to write them now (deferred tests are written now and run in Stage 5).** It has only the closed runs and the refusal matrix. Missing:
- Acceptance 8: the tamper recipe at verifier level. It must assert that `_verify_audit` and every check before `_PROBES` pass, then that `cpdr.probe` raises `identity_mismatch`. The fast `test_probe_refuses_a_result_that_is_not_the_rebuilt_candidate` calls the probe directly, which the lease says is not enough.
- Acceptance 5: the run-level refusals (stale_binding, submit before read_inputs, tools other than the pack tools).
- Acceptance 6: the blocked case through `OwnerWorkflow`, with a receipt and the reader showing status only.
- Acceptance 1: "store bytes unchanged".
- The D3 reader call on the closed-run head.
- Tool use: `tests/cpdr_runs.py` `replay` checks `expect_header` but not `expect_spans` or `expect_matching_spans`.

The behaviour itself holds where I could probe it:
- Submit before read_inputs gives `not_permitted`.
- `extract_statements` is refused `not_permitted`.
- The blocked case settles `blocked` and its receipt verifies.
- The RULES-only refusals (`cited_page_not_read`, `searched_source_not_searched`) give the pinned issues and keep the output; after a valid attempt 1, the receipt verifies.

Probes:
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/probe_run_refusals.py` (exit 0)
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/probe_rules_only_receipt.py` (exit 0)
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/probe_closed_run.py` (exit 0: `cpdr_closed` works for partial, unresolved and empty_agenda; the receipts verify; fact ids equal the oracle)

### Low
**L1. Test strength.** I ran 25 mutants of my own on fresh full copies with `PYTHONDONTWRITEBYTECODE=1`. 16 were killed and 9 survived:
- **Survived, not equivalent:**
  - A1/A13: CP-0 status hard-coded to `"restricted"` in `Upstream` and in the view.
  - A2: `as_of` hard-coded to the oracle date.
  - A3: source status hard-coded to `"ready"`.
  - R11: the reader's status hard-coded to `"restricted"`.
  - R12: the reader uses `store.result` in place of `store.head_module`, which drops the head/blob consistency and staleness checks.

  The fixtures never vary CP-0 status, the run's as_of, source status or head staleness, and the test `Store` double returns the same thing from `result` and `head_module`. So a fake constant equal to the oracle value passes.
- **Survived, equivalent:** A7 (probe candidate built on the current store), A16 (re-check after the retained output) and R1 (a non-known `Fact` cannot carry an amount).
- **Killed:** the missing-CP-0, bad-agenda and module-id fail-opens, dropping `rules`, the tail hash, retaining the raw payload, both blank-quote mutants and every other reader mutant.

Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/review_mutants.py`, output `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/review_mutants.out`.

**L2. `cpdr_reader` silently coerces some bad results instead of refusing them.**
- A `known` share carried as text returns `answered_share=None`, which is the "no question was submitted" value.
- A count of 3.9 returns 3 (`int(found.amount)`).
- A result without the per-gap `unresolved`/`answered_share` facts, which the lease's D3 lists, is read without error. That contradicts its docstring, which says it fails closed on a result lacking those facts.

Only a forged blob can reach this: a real head is the Python candidate, and the verifier's probe rebuilds it. No consumer exists yet (D3 OPEN). Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/probe_reader_edges.py` (exit 0).

**L3. `docs/reuse/manifest.json` is now stale for `shipped.py`.** The lease Files list it as changed, and AGENTS.md:171 says to keep it current. Its latest record is 4ef3f9ff…, which matches 83c0d12; the file is now 4765995a… (the report's hash is correct). The report's LEAD text names `project_commit` ca5cf5a, which the rebase replaced with 1e3942a, and the merge will change it again.

### Info
- **The claimed deviations are all admissible.** Each should go to LEAD as lease text:
  - the `run` keyword on `research_module`: `CpdrInputs` has no run_id or issuer_id, and the function is internal;
  - the retained step output being the canonical submission JSON: the lease does not fix the step output, and the verifier's replay of invalid steps accepts it (my RULES-only probe);
  - `bookkeeping` keeping its Stage 1 signature: this predates the task, and changing it would reopen a closed Stage 1 module.
- **One deviation the report did not list:** the lease comment says `Upstream` holds "inherited limitations"; the code holds `agenda`, `sources` and `cp0_status` instead. Nothing breaks, because `settle` derives the inherited limitations.

### Checks that passed
- **Adapter:** `cpdr_upstream` and `_inputs` are the one read point for `submit`, `probe`, `view` and `ENTRY_VALIDATOR`. A missing CP-0, a non-CP-0 blob or a malformed T5 fact raises `identity_mismatch`. The only `except` blocks are the documented `ValueError` → `identity_mismatch` and `ValidationError` → shape issues. No defaults stand in for missing values.
- **Reader and D3:** the reader exposes exactly `expected.consumption.reader`, and a test pins the field names. Nothing claims D3 is complete.
- **Registrations:** every row is appended in the right dict. The spec equals the lease and `_check_steps` passes. `sources` matches `_OWNER_SCOPES`. There is no `_PRECHECKS` row (lease :26), no `report_view.py` change and no `_Spec` row (lease D-C). `CPDR` is last in `SHIPPED_MAPS`. The bindings send TDR.1 and TDR.2 to Evidence and TDR.3 to Limitations.
- **Backlog:** the blank quote now gives `<path>: empty text` before the occurrence check (mutants A14 and A15 killed). The RULES absence lines go through `listed_issues`/`clipped`. The guard-limit notes are written and match `is_blank`. The method note moved by rename (R067) into `src/deploy_vii/methods/`.
- **Library boundary:** `src/deploy_vii` changes only in `bindings/cpdr.py`, `shipped.py` and `methods/cpdr.md`. `cases/`, `methodology.json`, TOOL-CONTRACT and the engines are untouched.

Not verified: the lease's tamper recipe at verifier level and the stale_binding refusal (neither probed); the deferred pytest suites (`test_owner_cpdr.py`, `test_owner_workflow.py`, `test_owner_s1a.py` and the render suites); the `expect_spans` matching; crash-resume between a valid step and `finish`; the oracle builder rebuild. My run probes are scripts, not gates.
