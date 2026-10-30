## CP-4 owner `test_tables_claims_and_limitations_equal_the_oracle`: root cause

There are two causes, and both are in the test. The oracle and the product are correct, so no oracle preparer or reviewer and no RED product test are needed. The shard's tracebacks had not printed when I stopped (at 05:43 `s2.log` still showed only `......FFF..................`). I reproduced the failure directly instead, on copies of the shard's own closed stores (pytest basetemp `pytest-67`: `positive0`, `gap0`, `gap_false_same_definition0`). All three cases fail at the same assertions.

**Cause 1: `_ctx` takes `upstream.facts[0]` as the metric** (the test is wrong; this is the first assertion that fails)
- **Evidence:** `tests/test_method_cp4.py:394` sets `metric = inputs.upstream.facts[0]`, which assumes the Stage 1 stand-in upstream with one fact (`make_upstream`, `:152`).
  - The owner test passes the real `cp4_legal.upstream_of(store, attempt)` (`tests/test_owner_cp4.py:100`).
  - In the real upstream, `Upstream.facts` is every CP-1 fact that can be referenced (`src/deploy_vii/cp4_legal.py:207`): 231 in all three runs.
  - `facts[0]` is `interface-fact:3588e1…`, but the bound metric (from `s1a.figure_fact`, the same choice `cp4_runs.metric_ref` makes) is `interface-fact:723fc2…`, at index 140.
- **What fails:** every cell bound at run time.
  - T4.9 fails first, at `test_method_cp4.py:251` (`actual.amount == metric.amount`), reached through `:270` and `:378` from `test_owner_cp4.py:137`.
  - T4C.8 (`:290`), T4F.2 (`:339`) and T4F.3 also fail, and the bound count is 4 against 11, 9 and 9 (`test_owner_cp4.py:140`).
- **Fix (test, fresh mx-feature), in `tests/test_owner_cp4.py` only:**
  - In the test at :128, keep `store = Execution(closed[case][0])`.
  - Take `metric = s1a.figure_fact(store.head_module(_head(store, "CP-1")).facts, runs.METRIC)`.
  - After `ctx = stage1._ctx(inputs)`, set `ctx["metric"] = next(f for f in inputs.upstream.facts if f.fact_id == metric.fact_id)` and `ctx["metric_row"] = inputs.upstream.rows[(metric.table_id, metric.row_id)]`.
  - Leave `test_method_cp4.py` alone: the Stage 1 tests are correct with a one-fact upstream.

**Cause 2: `inherited_limitations` compares a list with the oracle's rule object** (the test is wrong; the oracle is deliberate)
- **Evidence:** `test_owner_cp4.py:152` asserts `list(module.inherited_limitations) == want["inherited_limitations"]`. That value is a dict, `{rule, literal_head_from_CP-0, then: "CP-1 head: … (bound at run time)"}`, so the assertion can never hold.
  - The rule itself is right. Applied as `test_owner_rendering._cp4_expected_limitations` (`:2358-2366`) and `test_owner_cp3.py:287-293` apply theirs, it gives exactly the genuine lists: 21, 23 and 23 entries. The product side is `execution.py:345-366` and `:476-481`.
- **Fix (test, the same mx-feature dispatch):** compare against the expected list built from the rule:

  ```python
  rule = want["inherited_limitations"]
  cp1 = store.head_module(_head(store, "CP-1"))
  wanted = [x for x in dict.fromkeys([*rule["literal_head_from_CP-0"], *cp1.limitations, *cp1.inherited_limitations]) if x not in want["settled_limitations"]]
  ```

  Then assert `list(module.inherited_limitations) == wanted`.

**Everything else in the test already holds:** table order, the other 29 tables (T4F.5 included), claims, `settled_limitations`, module inputs and attempt inputs. With both fixes the bound count is 11, 9 and 9, and the whole body passes for all three cases.

**Low (one more fix in the same file, not a failure):** `test_owner_cp4.py:166` (`test_d3_cp4_reads_its_upstream_heads`) also uses `inputs.upstream.facts[0]`. It passes, but it only proves that some CP-1 fact belongs to CP-1. It should use the bound metric from `figure_fact`, as in cause 1.

**Origin:** Stage 2, commit 3efd33d (the test body), with d92ce29 the last touch. The suite had never run on genuine stores before.

**Reach into other owner suites (step 3):** neither cause reaches them.
- `.facts[0]` as a metric appears only in `test_method_cp4.py:394` and `:478` (Stage 1, correct there) and `test_owner_cp4.py:166`. `test_connect_cp4.py:475` is not an owner suite.
- cp3 already builds inherited limitations from the rule (`:287-293`), and cpl10 calls the product's `inherited_limitations` (`:258`).
- cp4c, cp2a, cp2d, cp3c and cp2g have no `inherited_limitations` comparison and no `_ctx` import. Their shared helpers are `stage1._record` and `_norm`, which are separate code.

## Probes
Both are under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4-rca/`. Each was run from `tree/` (`git archive 5cf7f0c`) with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests` and the argument `…/cp4-rca/stores`, and each has a `.log` next to it. They are plain Python, not pytest, and run on the copied genuine stores.

| Probe | Exit | What it shows |
|---|---|---|
| `probe_tables.py` | 1 (expected) | Replays lines 133-154 step by step. Shows causes 1 and 2 in every case; nothing else fails. |
| `probe_metric_fix.py` | 0 | With the bound metric and the inherited list built from the rule, the bound count is 11, 9 and 9 and inherited matches in all three cases. The fixer should run it after the edit, adapted to call the edited test function. |

`stores/` (about 490 MB, three copied stores) is kept so the fixer can reuse it; delete it after the fix. I started no background process.

Not verified: the shard's own pytest tracebacks (not printed when I stopped; my reproduction used the stores that shard produced); the exact edited test running under pytest on a genuine promotion (only the equivalent probe logic ran); the rest of the s2 shard (`test_probe_cp4`, `test_owner_cp2a`) and the other running shards; whether the stores were complete at copy time beyond the CP-4 head and receipt the probes read.
