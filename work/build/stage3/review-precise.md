## Stage 3 batch review (mx-precise, read-only): reviewed at s3-i4 = claude/s3-i5 18dc1fa

Summary: all four builds need revision. Each has one Medium finding, and every Medium was reproduced by a probe that exited 0. No gate has finished yet, so no build can be called done.

### Spec verdicts
- **G2 owner_rendering (c43b681..ce17c2f): REVISE.** Fails the rulings item 20 Q3 constraint (M1). Q1 is also still open (L1).
- **CP-OS (5af00fe): REVISE.** Fails contract point 1: the verifier cache is keyed on paths, not content (M2).
- **CZR (e59361c..57d3caf, the build commits a3508c7..57d3caf): REVISE.** The D12 record sits in the wrong list, against item 10 and round 5 item 19 (M3).
- **Legal test (724a0ad..2e06b2a): REVISE.** Not every assertion in item 18's `cr1_builder_target` was added (M4).

### Quality verdicts
- **owner_rendering.py and cpos.py: APPROVE.**
  - In owner_rendering.py, each `except` either re-raises as a named refusal, or is documented and logged: the `samefile` `continue` at :901, and the stage-cleanup warning at :975, which re-raises.
  - cpos.py has no catch-all and no stub.
- **CZR driver: APPROVE, with notes L2 and I1.**

### Findings (ranked)
**M1. G2 DR.6 suffix not constrained.** `tests/test_owner_rendering.py:1305-1310`
- The check strips every `∅ G#` and every one of `[\s,;·.()]` from the text after the oracle reason, then requires the remainder to be empty. So any of these passes:
  - a suffix not in the `(∅ G<n>, …)` form;
  - a `G<n>` that the page never cites (the check does no lookup);
  - a `∅ G7` appended to the **positive** reason, which `dr6-expected.json:34` says "contains no G# reference".
- Failure scenario: the renderer appends a stray or dangling gap reference to the DR.6 frame, and the test stays green.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_g2_title_and_reason.py` (exit 0 means all three forged inputs were accepted).

**M2. CP-OS verifier cache keyed on paths.** `tests/test_owner_cpos.py:128-146`, key at :141
- The key is `(str(store.directory), receipt.content_hash(), str(publication_directory))`.
- Failure scenario: a store or publication edited in place after one accepted verification is never verified again, so a refusal is hidden.
- No current test edits a run in place. Copies get fresh paths, and the A8 `tree()` check is independent of the cache. So this is a latent gap against the contract rule, not a live false pass.
- Fix: key on a content digest of the store and publication trees.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_cpos_cache_path_key.py` (pytest, 1 passed: the in-place edit was hidden).

**M3. D12: the statement_extract record is misplaced.** `docs/reuse/manifest.json:1746` sits under `local_patch_lineage`.
- The record's values are correct: prior f4b2c224 is the file at c81932f^1, and d7e15269 is the file at c81932f and at the tip.
- But `post_import_patches` has no record for `src/deploy_vii/statement_extract.py`, so its chain ends at the import sha f4b2c224, while the file at the tip is d7e15269.
- The CZR report says a `post_import_patches` record was added. The commit does not do that.
- Failure scenario: any provenance check that reads `post_import_patches` sees an unrecorded change to a reused file.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_d12_strict.py <s3-i4 path> 697fe8a 18dc1fa` (exit 1). It checks every reused file changed since 697fe8a for four things: the record list, the chain, the last record's sha against the file at rev, and item 19 (both parent sha and commit sha).
- The other Stage 3 records pass: charts.py, bindings/cp1.py, and report_view.py at 80ab9f5, 65cc982, e79d9d8, 70ea110 and f5477b4. The report_view.py failures the probe also prints predate this stage (item 19 at 3e5b537 and 24f879a, a chain fork at 8aef58d) and go to the owner.

**M4. The legal CR.1 test skips the twin-label targets.** `tests/test_legal_render.py:393-395`
- `cr1_builder_target` requires that each twin row label "starts with label_parts[0] and contains each later label_parts entry in order". The test checks only the row count and the cell texts.
- Failure scenario: a wrong companion text, for example "Within threshold" where the gap case needs "Not calculable", or labels missing altogether, still passes.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_legal_cr1_twin_labels.py` (exit 0: every label was set to "WRONG" and both cases still passed).
- The real labels do satisfy the oracle, so adding the assertion will not turn the suite red.

**L1. G2 S.4 title still uses a prefix match.** `tests/test_owner_rendering.py:1260-1261` (`startswith`)
- Rulings item 20 Q1 (exact title on the FP-04 fixture, the given regex elsewhere) has not been applied. It was ruled Low for this fix round.
- Same probe as M1: the title "…(not a forecast) junk" is accepted.

**L2. CZR test-first evidence is partial.**
- Running the a3508c7 RED tests against the pre-fix code: 23 failed and 2 passed. The gap-1 failures are an `AttributeError` for `STATEMENT_HEADING`, a missing name rather than missing behaviour.
- The RED test was edited after the fixes, at `tests/test_czr_fixes.py:85-87`: the slice went from `Q10[103:112]` to `[103:116]` and duplicate labels now resolve to the first. Without that edit, the original RED test fails at 57d3caf with `KeyError: 'Net revenues'`.
- This is a correction to the test data, not a weakened assertion, but it means the RED commit was never confirmed.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_czr_red.sh`

**L3. Two legal CR.1 targets are only partly asserted.** `tests/test_legal_render.py:393`
- "mark texts equal mark_texts" is checked by length only. The per-mark `shown` and pattern checks cover most of it.
- "fact via the T4.9 fact id" is not asserted at all.

**I1. CZR goes beyond "Stop at pack" (item 19).** `czr_closed` and its invented `submissions.json` format (`tests/czr_runs.py:126-149`) predate the ruling and have never been run. The owner decides whether they stay.

**I2. The widened heading regex now matches a connected-case page.** `STATEMENT_HEADING` locates `cases/connected/manifest.json` sources[1] page:2 ("CONSOLIDATED BALANCE SHEETS"), which the old regex did not. I found no CP-1 financial or earnings test that reads `cases/connected`, so no oracle should move; the pending long gate decides it.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage3-review/precise/probe_heading_drift.py`

**I3. ruff findings are on lines no build touched.**
- `ruff check` exits 1 with 9 findings: `statement_extract.py` 234-263 (TRY004), `financial_workflow.py` 439, 446 and 768, and `test_legal_render.py:220`. None of these lines is in the four diffs.
- `ruff format --check` exits 0.

### Gates (`i5/*.status`)
- **Pending:** the A, B and C status files are empty, `cpos.log` is empty, and `czrlong.log` has nothing in it yet. No step has reported an exit code.
- `fast.log` was about 90% done with all dots and one skip when I last read it. It has no exit code yet.
- **Failed / passed:** none so far.

Not verified: none of the i5 gate steps has finished, including the long financial, earnings and connected suites and the CP-OS genuine run. M2 was shown with a stand-in verifier, not a real closed S1a run. I did not run mypy, jscpd or complexipy. I checked the CZR page rule's page counts only by reading the code. I ran no mutation or property tests.
