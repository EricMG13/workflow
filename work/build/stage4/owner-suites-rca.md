## Owner suites on s4-int ff9070e: root cause

All 18 failures come from six causes. None is a product defect, and none was introduced by Stage 3 or Stage 4. Five causes need only test or driver fixes. Cause C needs an oracle change (pinned file). Every one predates the Stage 2 release ab9777f, and the evidence is static: `git diff ab9777f ff9070e` is empty for every failing test file, for `cases/cp2g-owner`, `cases/cp3-cp6-owner`, `cases/snapshot`, `cases/cpl10-owner` and `cases/cp4c-owner/cp4c-view-tree.json`, and for `owners/cp2g.py`, `cp4c.py`, `cp3.py` and `cpl10.py`. `report_view.fact_spelling` is byte-identical. The `cp2g_runs.py` and `cp4c_runs.py` diffs since ab9777f are only the item 34 readiness change; `bound_literal` blames to bec64de. Since the code paths are identical, no genuine run at 3429790 or ab9777f was needed.

**A. Unsettled-fact spelling compared with `shown=None`** (test is wrong)
- **Tests:** cp2g `a1_positive`, `a2_gap`, `a2c_cp1d_blocked`; cp4c `a1_positive`, `a2_gap`.
- **Cause:** `tests/test_owner_cp2g.py:154-155` and `tests/test_owner_cp4c.py:149-150` assert `fact_spelling(...)` equals `e["shown"]` for every fact. The oracle's fact-level `shown` is None while a fact is unsettled (`cp2g.Cell.shown`, `owners/cp2g.py:951`; `cp4c.py:1096`). The unsettled spelling is defined in the manifest's `cell_notation` instead.
- **Origin:** Stage 2 (bec64de, 54c6a0b).
- **Fix:** when `e["shown"] is None`, compare `text.replace("G1","G#")` with `"∅ G#"` for missing and `"∅ G# n.m."` for not_applicable; otherwise compare as now. Same edit in both files.
- **Evidence:** on genuine positive runs, the rest of each helper (records, tables, reference tables, claims, limitations; cp4c T4E count 256) matches the oracle.

**B. Driver skips binding a figure whose unit token mismatches** (driver is wrong)
- **Tests:** cp2g `a3[v10]`, cp4c `a3[v17]`.
- **Cause:** `tests/cp2g_runs.py:331-333` and `tests/cp4c_runs.py:293-295` return `match[0]` when `hit[1] != match[2]`. The figure placeholder is left unreplaced, so the submission journals "Malformed run text". The manifest rule `{{FIG:name|token}} -> {<fact_id>|<token>}` keeps the payload's token, and `tests/test_method_cp2g.py:252` binds that way. v10 and v17 are the only mismatched-token refusals.
- **Origin:** Stage 2 (bec64de).
- **Fix:** `match[0] if hit is None else "{" + hit[0] + "|" + match[2] + "}"`, in both drivers.
- **Evidence:** with that binding, the genuine issues equal the oracle exactly, for both v10 and v17.

**C. CP-2G view tree recorded on hand-seeded heads** (oracle is wrong)
- **Test:** cp2g `a1_one_ok_read`, failing at `view_tree.check` (`:201`). The other assertions hold (0 leaked quotes).
- **Cause:** genuine CP-1 sets `limitation="sign normalised"` on known `cash_interest` and `cash_taxes` (`deploy_vii/statement_history.py:75`, `model/history.py:222`). The view passes `fact.limitation` through (`owners/cp2g.py:2996-3001`), which the lease allows (`limitation|null`). `cases/cp2g-owner/cp2g-view-tree.json`, pinned at `cases/PINS.json:36`, records `NoneType` for those two leaves. The tree's own note says it was observed on seeded heads, and the seed `_cp1_fact` (`tests/test_method_cp2g.py:116-127`) sets no limitation.
- **Origin:** Stage 2 (291fa8e).
- **Fix:**
  - **Oracle change (needs a separate preparer and an independent review):** set the leaves `base.operands.cash_interest.limitation` and `base.operands.cash_taxes.limitation` to `"str"` in all three tree entries, then re-pin.
  - **Test change:** make `_cp1_fact` give known `cash_interest` and `cash_taxes` the limitation `"sign normalised"`, so `test_connect_cp2g.py:183` still holds. The fixer must then run `test_method_cp2g`, `test_connect_cp2g` and `test_owner_rendering -k cp2g` fast.

**D. CP-0 run-time pack-hash marker not bound** (test is wrong)
- **Tests:** cp3 `test_cp0_r3_equals_the_oracle[positive|gap]`.
- **Cause:** `tests/test_owner_cp3.py:163-170` compares `T7.run.preparation` with the oracle literal `<<PreparedPack.content_hash(), bound at run time>>`. The status, limitations, commands and plan all match.
- **Origin:** Stage 2 (e2669a2).
- **Fix:** replace the marker with `closed.pack.content_hash()` in the expected facts before comparing, as `tests/test_owner_s1a.py:376-381` does.

**E. Signal count compared with a list** (test is wrong)
- **Tests:** cp3 `test_cp2_read_body_register_counts_follow_the_oracle[positive|gap]`.
- **Cause:** `tests/test_owner_cp3.py:246` asserts `body["cp1a_signals"] == frozen["cp1a_signals"]`. The frozen value in `cases/snapshot/cp2-view-tree.json` is a count (positive 0).
- **Origin:** Stage 2 (e2669a2; the tree, 12002e4, is older).
- **Fix:** `assert len(body["cp1a_signals"]) == frozen["cp1a_signals"]`, as `test_owner_s1a.py:484` does. The probe shows the next assertion (`upstream`, `:247`) and every count hold.

**F. CP-L10 citations under the old de-duplication rule** (test is wrong)
- **Tests:** cpl10 `test_closed_run_equals_the_oracle_cell_for_cell[positive|limited]`.
- **Cause:** a50efb2 moved the product (`owners/cpl10.py` `_unique`) and the oracle rule to one citation per (source, page) via `blank.one_per_page`, and updated `test_method_cpl10.py`. It did not update `tests/test_owner_cpl10.py`: `_cites` (`:169-170`) still uses `dict.fromkeys`, and the fact and claim checks call it (`:210`, `:249-250`). For example, `TL10.2.fcf.change` gets one page:3 citation from the product but two from the test.
- **Origin:** Stage 2. a50efb2 is an ancestor of ab9777f; the suite last passed genuinely at fix1 (1ec5ba8), before it.
- **Fix:** at `:210`, a copied cell expects `cp1[copied].citations`; a derived cell expects `_cites(cp1, derives_from)`. In `_cites`, return `one_per_page(tuple(...))`. Copied cells must keep CP-1's own citations: applying `one_per_page` to them as well breaks `TL10.2.fcf.from_value`.
- **Evidence:** with exactly this edit, the whole test passes for both cases on a genuine promotion.

## Probes
All under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/owner-rca/`. Each was run with `run_probe.sh <probe> <case>` (one at a time), and each has a log next to it. Stores were deleted afterwards.

| Probe | Exit | Why |
|---|---|---|
| `probe_cp3.py` (positive) | 1 | Expected: shows D and E, and that the rest holds |
| `probe_cp2g.py` (positive) | 1 | Expected: original tests fail; patched helper and fixed v10 binding match |
| `probe_cp2g_viewtree.py` (on the saved receipt) | 1 | Prints the two-leaf diff behind C |
| `probe_cp4c.py` (positive) | 0 | Patched helper and fixed v17 binding match |
| `probe_cpl10.py` | 1 | Diagnostic: 12 fact and 2 claim mismatches under the old rule, 0 under round 3 |
| `probe_cpl10_fix.py` | 0 | The exact F test edit passes both cases |

The `run_probe.sh` wrapper reported 0 for all six because it appends the exit code to the log.

Not verified: cause A's fixed helper and the assertions after it on genuine cp2g `gap`/`cp1d_blocked` and cp4c `gap` (only the shard tracebacks at `:155`/`:150`; no probe); the cp3 `gap` case beyond the shard traceback; whether the genuine `gap`/`cp1d_blocked` CP-1 heads also carry "sign normalised" (cause C assumes the same financial pack); the effect of the `_cp1_fact` seed change on other cp2g fast tests; no genuine run at 3429790 or ab9777f (attribution is static, from identical code paths); the remaining cp-1, cp-3 and cp-4 shard tests, still running when I stopped.
