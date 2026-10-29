# CP-2E fix round 1 (after the round 10 review)

Review: `work/build/stage1/cp2e/round10-review.md`. Reviewer probes: `<S>/cp2e-r10-review/`, where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Re-review: mx-precise, by finding id.

## Step 0
- Work from `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a219254fe68cc1c2d`.
- Run `git merge --ff-only claude/module-dev-status-review-0981b6`.
- Confirm HEAD equals the lane tip named in your dispatch before you edit.

## Fix (test-first; see the test fail for the reported cause)
1. **M1.** Round 10's `on_page` change (now `quotes.quoted`) makes three raw-quote reads reachable after a normalised match:
   - `code` (cp2e.py:546);
   - the `labelled` adjacency on `_squash(ref["quote"])` (:558);
   - the E5/E8 `_RATE_PHRASE.findall(rb["quote"])` (:613), and the `reference_rate in rb["quote"]` check (:619).

   Run each on `normalise(ref["quote"])`, so each reads the same text the match used. The method is in `work/build/stage1/quote-normalise-brief.md`. Add no new wording.

   Tests: the probe's three cases (`p_raw_after_normalised.py`, exit 1 today):
   - A: `EUR­IBOR` with `code_text EUR`;
   - B: a hidden `fi­xed rate` stem;
   - C: `spread 25­0` with `bps_text 25`.

   Each must get its existing pinned refusal.
2. **L1, riding.** Add a lowercase letter before `-` (e.g. `mid-25`) to `test_round10_non_sign_forms_still_validate`, so the mutant `guard_upper_only` in `mutants_review.sh` is killed.

Not in this round:
- I1: a quote cut at the digit drops the page's sign. This is a rule gap for all four owners, and it goes to LEAD.
- I2: `_once`'s `== 1` is unpinned. It predates this change and goes to the owner.

## Rules
- Files: `src/deploy_workflow/owners/cp2e.py` and `tests/test_method_cp2e.py`. Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Gates (each must exit 0):
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py`;
  - `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files.

  Run nothing else.
- Run mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`.

## Report (as text)
- the commit;
- each finding and its test;
- exit codes of `p_raw_after_normalised.py`, `mutants_review.sh` (`count_ge_one` may survive; it is I2) and `<S>/cp2e-r10/mutants_r10.sh`;
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
