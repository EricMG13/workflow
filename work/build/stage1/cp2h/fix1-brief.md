# CP-2H fix round 1 (after the first adversary review)

**Inputs**
- Review: `work/build/stage1/cp2h/review-adversary.md`.
- Controller decisions: `work/build/stage1/cp2h/questions.md`, Q1 and Q2.
- Reviewer probes: `<S>/cp2h-adversary/` (P below), where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

**Re-review:** mx-adversary, by finding id.

## Step 0
From `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb`, run `git merge claude/module-dev-status-review-0981b6`. It is a plain merge, because cc1d0fb is not on the lane. If `docs/CP4C-OWNER-LEASE.md` conflicts in its header, take the lane's version. Report any other conflict. Confirm that the merge parent equals the lane tip.

## Fix (test-first: see each test fail for the reported cause)
1. **F1 (Q1).** `_THRESHOLD` (cp2h.py:140) accepts exactly `[0-9]+\.[0-9]{2}x` or `[0-9]+\.[0-9]%`. Any other form gets the existing `Trigger terms not found`.
   - Test the six forms in `P/p01_threshold_form.py`: `4x`, `2.7x`, `10%`, `2.755x`, `10.05%` and the like.
   - The test must kill C50.
2. **F2.** Add one multi-issue test that pins the round 7 (a) issue order. `P/p06_issue_order.py` is a 19-issue template. The test must kill C28–C35 (`P/spec_other.py`).
3. **F3 (Q2).** Store the percent threshold as a fraction with an exact exponent shift, no rounding context (cp2h.py:318). Case: `P/p02_threshold_scaleb_context.py`.
4. **F4.** Add tests that kill:
   - C25 (tightest takes the first missing year's reason);
   - C26 (T2R.6 takes the first unknown year's reason);
   - C27 (the threshold comes first in the root reason);
   - G1 (the date is read from the Published line);
   - C45 and C46 (sign refusals).

   Probes: `P/p09_reason_order.py`, `P/p12_published_date_read.py`, `P/p03_signs.py`, `P/spec_more.py`.
5. **Info, optional.** Tests for C47 (CP-2G unit/period check) and C48 (the CP-1 `T4.10` filter) where they are cheap. Write one line each for any you leave out.

Not in this round (with LEAD; questions.md B1–B6): the block rule, a blank limitation, first-year lineage, and the Stage 2 items.

## Rules
- Files: `src/deploy_workflow/owners/cp2h.py` and `tests/test_method_cp2h.py`. Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all. No new user wording.
- Gates (each must exit 0), and run nothing else:
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp2h.py`;
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- Mutants: only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Rerun `P/runner.py` with `spec_refusals.py` (29 of 29 must stay killed), `spec_other.py` and `spec_more.py`.

## Report (as text)
- the commit;
- each finding and the test that covers it;
- runner and probe exit codes, with each surviving mutant and the reason it survives;
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
