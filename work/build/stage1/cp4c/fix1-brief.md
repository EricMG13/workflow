# CP-4C fix round 1 (after the first adversary review; carries round 10's cell grammar)

**Review:** `work/build/stage1/cp4c/review-adversary.md`. Controller decisions: `work/build/stage1/cp4c/questions.md`, Q1–Q4. **Reviewer probes:** `<S>/cp4c-adversary/` (P below), where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. **Re-review:** mx-adversary, by finding id. The change touches money arithmetic only through the row reader; A-1 is unchanged.

## Step 0
Work from `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2c15c441717ec41c`. Run `git merge claude/module-dev-status-review-0981b6`. This is a plain merge, because your bdde577 is not on the lane. On a `docs/CP4C-OWNER-LEASE.md` header conflict, take the lane's version. Report any other conflict. Confirm the merge parent equals the lane tip.

## Fix (test-first; red seen for the reported cause)
1. **M1, Q1.** `_row_amount` (cp4c.py:515-516) reads the page line that starts with the quote, not the first line that starts with the quote's label. If no line starts with the quote, it gets the existing #11 text. Cases are in `P/probe_quote_row.py`:
   - duplicate `Other` rows, where the second line is quoted;
   - `Provisions` against `Other Provisions`.

   Both must read the cited line, or be refused.
2. **L1, Q2.** A row whose cell count differs from the header's gets the #11 text (`Deferred items  1  1    1  5.00  7.00`).
3. **Round 10, Q4.** The quoted cell must fully match `-?[0-9]+(\.[0-9]+)?` before `Decimal(cell)`. Otherwise it gets the #11 text. That covers exponents, underscores, non-ASCII digits and commas.
4. **L2, Q3.** A known CP-1 EBITDA with no amount raises a `ValueError` invariant, as for CP-1 total debt. Kill `cp1_ebitda_known_text_raises` in reverse: the mutant that keeps today's "missing" reason must now fail. Case: `P/probe_cp1_known_text.py`.
5. **L3.** Add a test that calls `waterfall()` with an EV over 38 digits that partly pays rank 1, and expects state 14. It must kill `state_14_claims_only` (`P/probe_state14_paid_mutant.py`).
6. **L4.** Add tests that kill the 8 survivors in `P/probe_survivors.py`: `through_reason_group_first`, `rank_first_missing_is_last`, `rank_total_allows_zero`, `negative_claim_unchecked`, `fits_zero_is_partial`, `row_amount_infinite_ok`, `no_cp2g_id_period_check`, `no_cp2a_lineage_check`. The probe gives each distinguishing input.

Not in this round (with LEAD, questions.md B1–B6): the builder sync, total debt `not_applicable`, the #9 repair issue, raw against product quote matching, the zero share, and the implied-multiple choice.

## Rules
- **Files:** `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py`. Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all. No new user wording.
- **Gates (exit 0):**
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp4c.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.

  Run nothing else.
- **Mutants:** only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Rerun `P/mutants_adversary.py` and your `<S>/cp4c-r6h-8/mutants.py`. Each fix's revert must be killed.
- **Hypothesis:** the existing properties still pass.

## Report (as text)
- the commit;
- each finding mapped to its test;
- exit codes of `P/probe_quote_row.py`, `P/probe_cp1_known_text.py`, `P/probe_state14_paid_mutant.py`, `P/probe_survivors.py`, `P/mutants_adversary.py` and your runner (survivors left, with reasons);
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
