## Stage 5.3 rewrite tournament, assess mode (code 9f71bfa)

I ran the roles inline, in the order the contract sets. Candidates were applied only to the scratch copy `<S>/s53/rt/tree`, which is now deleted. The lane worktree is unchanged (`git status` is clean). Impact sets came from grep, because GitNexus does not index this repo:
- `_verify`: two callers, `owner_workflow.py:1475` (`write_receipt`, `sealed=False`) and `:2409` (`verify_owner_run_receipt`, `sealed=True`). `financial_workflow._verify` is a different function.
- `_verify_submissions`: called at `owner_workflow.py:2310` and directly by `tests/test_owner_s1a.py:47,1303,1327,1331,1364,1387`.
- `cp4c.content_issues`: called at `cp4c.py:1053` (`payload_issues`), `:1445` (`_resolve`) and `:2719`, and by `tests/test_connect_cp4c.py:247-294`.

Tests monkeypatch `owner._snapshot`, `_attempt_of`, `_fill` and `_verify_audit` by module global. That still works, because the helpers look those names up at call time.

Baseline at 9f71bfa: focused owner tests 115 passed, 1 skipped; cp4c tests 1424 passed.

| Target | Winner | Verified | Test result | Applied |
|---|---|---|---|---|
| 1 `_verify` (owner_workflow.py:2198, C901 21→7) | 2c Readability | yes | 115 passed, 1 skipped (+4 probe); ruff, format and mypy 0 | no, assess mode |
| 2 `_verify_submissions` (:2025, C901 18→14) | 2c Readability | yes | 115 passed, 1 skipped (+3 probe); 3 direct `_verify_submissions` callers in test_owner_s1a passed (291 s); mypy 0 | no, assess mode |
| 3 `cp4c.content_issues` (cp4c.py:938, C901 20→5) | 2c Readability | yes | 1424 passed; 428-input differential identical; ruff, format and mypy 0 | no, assess mode |

With T1 and T2 applied together: 122 passed, 1 skipped; ruff, format and mypy 0.

How the bracket went, all three targets:
- **2a Speed vs 2b Memory: 2a wins.** 2a used `set(valid)` for the final membership test and lazy coordinates. 2b used generator chains instead of building lists.
- **2a vs 2c: 2c wins.** 2a only saves work on collections of a few dozen items. The real cost is snapshot I/O, which no candidate changes.
- **2c vs Incumbent: 2c wins.** The Incumbent's case was that check order picks which refusal fires and which lookups are guarded (R4-4). 2c keeps every check in its original order, so that argument does not tell against it.

### T1 `_verify`: 2c wins
- It splits `_verify` into four named stages run in the original order: final heads (LOW 1 and MEDIUM 1), the retained-step Counter, R6-2 ancestry, and receipt coordinates. `_verify` becomes a linear script, like the existing `_verify_*` family.
- `stale_binding` stays first and last. Every middle refusal is still `identity_mismatch` at the same point in the sequence. The `NotAuthorized`/`ValueError` mapping is kept exactly. `ancestors` gains its missing `set[str]` annotation.
- Spot-check (plan §0, R6-2): a resealed receipt whose begin `snapshot_before` lies outside the ancestry is refused before `_verify_audit` runs (tripwire). With the coordinate check removed, the probe fails. A dropped head is refused before any ancestry read. A snapshot mismatch gives `stale_binding`. All 4 probes pass on both the incumbent and the candidate.

```diff
@@ -2195,28 +2195,16 @@
-def _verify(
+def _verify_final_heads(
     store: Execution,
+    snapshot: ExecutionSnapshot,
     receipt: OwnerRunReceipt,
-    *,
-    publication_directory: Path | None,
-    sealed: bool,
+    deterministic: str | None,
 ) -> None:
-    snapshot = store.read()
-    ...stale_binding check, store.pack, plan check, analytical/deterministic (moved below)...
+    """Every final head is its module's settled head and is named in the receipt; no begun attempt
+    is left unfinished (S1a adv-4 LOW 1); the deterministic head binds the final snapshot's
+    inputs, as an analytical one does in `_verify_settlements` (S1a adv-4 MEDIUM 1), with the
+    same explicit exception mapping."""
@@ -2242,6 +2227,12 @@
+def _verify_retained(
+    snapshot: ExecutionSnapshot, receipt: OwnerRunReceipt, analytical: tuple[str, ...]
+) -> None:
@@ -2255,10 +2246,18 @@
-    allowed = frozenset(analytical) | ...
-    ancestors = set()
+def _ancestry(store, receipt, snapshot, allowed: frozenset[str]
+) -> tuple[set[str], list[ExecutionSnapshot]]:
+    ancestors: set[str] = set()
@@ -2277,6 +2276,12 @@
     chain.reverse()
+    return ancestors, chain
+
+def _receipt_coordinates(receipt: OwnerRunReceipt) -> list[str]:
@@ -2291,8 +2296,38 @@
-    if any(digest not in ancestors for digest in coordinates):
+    return coordinates
+
+def _verify(...same signature...) -> None:
+    ...stale_binding, store.pack, plan check, analytical, deterministic (verbatim)...
+    _verify_final_heads(store, snapshot, receipt, deterministic)
+    _verify_retained(snapshot, receipt, analytical)
+    allowed = frozenset(analytical) | frozenset(() if deterministic is None else (deterministic,))
+    ancestors, chain = _ancestry(store, receipt, snapshot, allowed)
+    if any(digest not in ancestors for digest in _receipt_coordinates(receipt)):
+        raise WorkflowError("identity_mismatch")
```

This block is abridged to save space. The full verified `diff -u` (139 lines) is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/rt/work/t1.diff`.

### T2 `_verify_submissions`: 2c wins, narrowly
- It extracts `_replayed_binding` (the R4-3 input read, the fill replay, the call prefix and evidence) and `_submitted_step` (the attempt and step match). The call order is unchanged: `_journaled_issues` still runs before `_attempt_of`, and both `_raw` reads are kept, so I/O is identical.
- The refused, valid and invalid tail is untouched: B2's exact-issues rule, `_verify_invalid_step`, and one settlement per ticket. The item 38 begin-field rule lives in `_verify_walk` (:1599) and is not touched. `test_valid_step_rewriting_repair_issues_is_refused` passes.
- Spot-check (B2): a refused record with one issue dropped, with its issues reordered, or relabelled `invalid` is refused with `identity_mismatch`. The genuine run is accepted. The probe passes on both versions.
- The win is narrow: complexity only falls from 18 to 14, and the Incumbent's "reads as one replay" point partly holds.

Full diff (122 lines): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/rt/work/t2.diff`. The body of each helper is the removed block moved verbatim, except that `binding.binding.ticket_id` becomes the local `ticket_id`. The call sites are now:
```diff
-        # R4-3, G1-X §3: ...  (28 lines: input-read check, _hist, _fill compare, call prefix)
+        historical, filled, evidence = _replayed_binding(store, receipt, submission, spec)
...
-        attempt = _attempt_of(after, binding.binding.ticket_id)  (14 lines: candidates, matches)
-        step = matches[0]
+        attempt, step = _submitted_step(after, historical, submission)
```

### T3 `cp4c.content_issues`: 2c wins
- It splits the function into `_claims_issues`, `_case_id_issues(key, rows)` and `_field_issues`. One `_case_id_issues` now serves valuation, fulcrum and plan, replacing the `judged` tuple and its type annotation. `structural` becomes `structural and not valuation`.
- The pinned order is unchanged: claims, valuation ids, fulcrum ids, plan ids, waterfall (only when structural), High, then text fields. Message strings are byte-identical.
- Spot-check: an exact differential on the `positive` and `gap` cases. Each case ran 214 payloads: the base, 17 single mutations, all 136 pairs and 60 seeded sets of 3-8 mutations, covering every branch. Incumbent and candidate output matched byte for byte (`cmp` 0). A mutant that drops `and not valuation` gives 15 differences, so the probe can tell the versions apart.

Full diff (141 lines): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/rt/work/t3.diff`. The core of `content_issues` becomes:
```diff
+    issues, ids, structural = _claims_issues(sub, _pages(ctx.pack), ctx)
+    valuation = _case_id_issues("valuation", sub.valuation)
+    issues += valuation
+    issues += _case_id_issues("fulcrum", sub.fulcrum)
+    issues += _case_id_issues("plan", sub.plan)
+    if structural and not valuation:
...
-        if text is None:
-            continue
-        ...(22 lines: blank / name / run / guard branches)
+        if text is not None:
+            issues += _field_issues(path, text, kind, bound, names)
```

### Probes
All under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/rt/work/`. They were run from the copy's `tests/` with `PYTHONPATH=src:tests`.
- `test_probe_rt_t1.py`: exit 0 on both versions; 1 failure on the coordinate-removed mutant.
- `test_probe_rt_t2.py`: exit 0 on both versions.
- `probe_t3.py`: identical dumps; 15 differences on the mutant.

The edit scripts (`t1.py`, `t2.py`, `t3.py`) and the incumbent originals (`orig/`) are kept next to them.

### Deviations from the contract
- The three diffs in the report body are abridged to keep it short. The complete `diff -u` output is in the three files above, and those are the patches that were verified.
- The direct `_verify_submissions` callers in test_owner_s1a are not fast tests (291 s). I ran them anyway, because they are the target's own impact set.

Not verified: full `tests/test_owner_s1a.py`, `tests/test_owner_workflow.py`, `tests/test_owner_cp*.py` and genuine/`STORE_RUNS` runs on the candidates; the skipped `test_owner_order.py:356` CP-1 promotion; jscpd and complexipy on the candidates (only ruff C901, ruff check/format and mypy ran); T2's helpers on the financial-module (`_FINANCIAL_MODULES`) path beyond the 3 s1a tests; the T3 differential covers only the `positive` and `gap` cases, not the six fixture/refused/blocked cases; 2a and 2b were judged but never applied or tested.
