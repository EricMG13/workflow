# CP-4C round 11 (rulings round, after fix 1 was approved and merged)

**Review:** mx-adversary, by ruling id. This is money code.
**Inputs:** the fix 1 re-review is `work/build/stage1/cp4c/fix1-review.md`. The controller decisions are in `work/build/stage1/cp4c/questions.md` (Q1–Q7).

## Step 0
1. From `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2c15c441717ec41c`, run `git merge --ff-only claude/module-dev-status-review-0981b6`. The lane now carries your fix 1 and round 11 (d60035b).
2. Confirm that HEAD equals the lane tip.

## Apply
From `docs/rulings/2026-10-28-stage1.md`, `# Round 11`, `## CP-4C`:
1. **B2.** A not_applicable CP-1 total debt settles as A-2 #6 does.
   - It goes in `_debt_claim`.
   - Use the ruled claim reason and own line exactly as written.
   - Copies keep `not_applicable` with CP-1's limitation.
   - Another period, or an absent fact, stays an invariant.
2. **B3.** A claim `name` or valuation `label` holding a figure gets `<path>: Bare figure: <token>`.
   - Build it from `prose.bare_figures` with the same `names` that `compute` uses.
   - Put it at the #9 per-field step, after the empty and one-line checks.
   - Check that anything that passes the validator then also passes `compute`.
3. **B6.** A CP-1 EBITDA that is not known names its state: `Not calculable: EBITDA is <missing|conflicting|not applicable> in CP-1 for LTM Q4 25: 2025-01-01 to 2025-12-31`.
   - The cell stays `missing`.
   - EV's reason still comes first.
   - The known-without-amount raise (Q3) stays.

Controller decisions, module-only (questions.md):
4. **Q6** (re-review N3, plus the pre-existing truncated-figure case). The quote must cover whole cells: its two-space cells must be a prefix of the cited line's cells, each one equal.
   - `Pr` against `PP&E …` is refused.
   - `Other current liabilities  10  10  10  10  1`, which cuts the last cell, is refused.
   - Use the existing #11 text.
5. **Q7** (pre-existing: bare CR or U+2028). The cited line must be one physical line: `len(line.splitlines()) == 1` after the trailing `\r` is stripped. Otherwise it gets the #11 text.
6. **Riding tests.**
   - N1: the longer-row half of Q2. Use `Deferred  items  1  2  3  4  5.00  6`; it must kill the `<` mutant.
   - N2: three tests.
     - Q5: identical duplicates count as one line.
     - Q4: `+5.00` is refused.
     - Q4: `.5` is refused.

## Rules
- **Files:** `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py`. Never edit `cases/` or `src/deploy_vii`.
- **Method:** test-first, with each test seen red for its cause. No stub, fake value or catch-all. No wording beyond the rulings.
- **Gates** (each must exit 0; run nothing else):
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp4c.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- **Mutants:** only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`.
  - Show that each ruling's revert, and each decision's revert, is killed.
  - Rerun `<S>/cp4c-fix1-review/mutants_fix1_review.py` and `<S>/cp4c-fix1-review/probe_m1_cited_row.py <root> --expect`. Update the probe's "partial label" expectation to Q6, in a copy under `<S>/cp4c-r11/`.
- **A-1 is unchanged:** rerun `<S>/cp4c-adversary/probe_alloc_reference.py` and `probe_hypothesis_big.py` at reduced counts.
- **New strings:** run every new string through `prose.issues` and `bare_figures`, and report the hits.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Report (as text)
- the commit;
- each ruling or decision with its test;
- probe and mutant exit codes;
- the gates;
- Stage 2 notes (`methods/cp4c.md`: B4 and B5 guard limits);
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
