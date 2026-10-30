# Perf-sweep register

Profile: `work/perf-sweep/profiles/prof3.out` = cProfile of
`tests/test_earnings_workflow.py::test_fresh_actual_owner_cases_settle_exact_values_lineage_claim_and_immutable_receipt[E-NO-YOY]`
on 2bbf633 (PR manager worktree): 1727 s profiled, 1277 s plain (scale ≈ 0.74).
`prof2.out` was already deleted from `/private/tmp` when this sweep started (06:53Z); not recovered.
Seconds below are profiled cumulative seconds in that one test unless marked otherwise.

## Product rows (plan only — `work/perf-sweep/product-plan.md`)

| Row | Location | Cost (profiled) | Change | Risk | Conf. | Status |
|---|---|---|---|---|---|---|
| P1 | `src/deploy_workflow/earnings_workflow.py:1685` `_reference`, called from `_operands` :1696 | 1,440 `content_hash()` calls on the same CP-1 producer Module, 237.3 s | hash the producer once per `_operands` call | 1 | 2 | applied 17e07ba |
| P2 | `src/deploy_vii/contracts.py:290` in `validate_tables` :254 | 144.2 s self over 5,281 calls (O(tables × facts) rescan) | group fact ids by table once, before the table loop | 2 | 2 | applied 2ded26c |
| P3 | `src/deploy_vii/execution.py:607` `Execution.result` | 372 calls: 122.1 s `model_validate_json` + 29.6 s `content_hash` re-parsing the same content-addressed blobs | keep `_load` (read + sha256 check) on every call; memoise only parse+canonical check by verified sha256 | 3 | 2 | applied 4af08ce |
| P4 | `src/deploy_vii/contracts.py:78` `Contract.content_hash` instance cache | 2.03 M calls, 415.4 s | **not recommended**: see product-plan §P4 | 4 | 2 | not-recommended |
| P5 | `src/deploy_vii/financial_validation.py:42` `records` | 47.7 M recursive calls, 126.0 s | precompute per-class model-bearing field names; same order | 2 | 1 | deferred (needs trial) |
| P6 | `src/deploy_vii/live/submission.py:488/499`, `cp1_workflow.py:256/296` | `quality_inputs` 458.9 s, `_stage_registers` 609.1 s (overlapping) | memoise trusted recomputation | 5 | 1 | deferred: verification invariant ("every stage recomputed", `cp1_workflow.py:257`, `submission.py:489`) needs an owner ruling |

## Test-only rows

| Row | Location | Finding | Status |
|---|---|---|---|
| T1 | `heavy`/`fast` tier markers | Not added: the project already keeps a per-change fast set, `work/build/keep/fast-set.txt` (10,360 passed in 5m10s, `work/build/ledger.md` 06:41), which excludes the heavy owner suites. Markers would be a second list of the same thing. | not-needed (ruling; Modules owns the fast set) |
| T2 | `tests/test_earnings_workflow.py:1261,1315,1576` | owner history is already shared at module scope with per-test `copytree` (`reopen_component` :1269). The two tests that rebuild (`:1586` fresh cases, `:1684` negative fresh case) assert a fresh execution; sharing would weaken them. | not-a-defect for this file; other files pending durations |
| T3 | `pytest-xdist` | new dependency | decision (decision record + user's word) |

## Heavy set (from the PR manager's 410afa2 full run; `pm-410afa2-durations.txt`)

15 test items ≥ 470 s = 15,748 s (4.37 h) of the 10h09m (36,540 s) run. Targets for the
before/after harness: `heavy-targets.txt` (whole test functions, so all parametrizations:
`well_shaped_wrong_owner_review` ×5, `authentic_financial_delivery` ×2 included).
`test_actual_composed_new_money_figures…` 1,545 s is fixture **setup** (`settled_owner_component`,
module scope), not the test body. Every earnings heavy test settles or re-settles a CP-1B
owner (`submit_review` → `_complete_intent` / `_verify_outcome`), the product path P1–P3 target.
The 410afa2 run also had 3 `test_owner_s1a` file failures (PR manager); not this sweep's rows.

## Follow-up rows found while applying

| Row | Location | Finding | Status |
|---|---|---|---|
| F1 | `src/deploy_workflow/host.py:492-527` `_ParsedExecution.result` | already caches parsed results (4 entries, `_load` every call; commit 7d0b671). After P3 the base `Execution.result` does the same, so this override is a second cache layer: measured (mx-adversary, `probes/adv_p3_memory.py`, loaded machine) +1,290 MiB RSS per 4 CP-1-size entries in each cache, +2,579 MiB for both, peak RSS 3.41 GB. Deleting the override (and later `pack`) is a `deploy_workflow` host change outside the approved P1–P3. | deferred (owner) |
| F2 | `cases/cpos-owner` builder and manifest | pin `src/deploy_vii/contracts.py` = `3b33bfc…` (b0ac40c); after P2 it is `618229c…`. The same builder's `report_view.py`/`render.py` pins were already stale at b0ac40c; no test reads them; `cases/pins.py --check` does not cover them (exit 0). `cases/` is outside this sweep's scope. | deferred (owner) |
