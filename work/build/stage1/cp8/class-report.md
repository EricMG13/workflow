## CP-8 class round (round 11): report

Defect classes B1 (edge cut) and B3 (wrap refusal) are fixed in CP-8. The blank-text class already passed and now has its adapter test. Both round 10 review Lows have tests. All gates exit 0. This was a rulings round: no new issue string, and every frozen case still passes unchanged.

**Commit:** `d648582` on `worktree-agent-a3cc9818386e8861a`, worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a`.
- **Step 0:** the merge was a fast-forward to 864ffe3. That is one ledger-only commit past the 9141621 named in the dispatch, which you accepted.
- **Files changed:** only `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py`. Nothing in `tests/defect_classes.py`, `cases/` or `src/deploy_vii` was touched.

### Adapter test (in `tests/test_method_cp8.py`)
Each adapter adds the case page at a fresh `page:9` on the cited source, with the hash recomputed. It then runs `validate_ledger` on the frozen submission with the case's quote and value in one field.
- **Quote fields**, in `test_r11_shared_quote_cases`, parametrised over the library lists:
  - **Size level** (`thesis.downside_sizes[0].level_text`): `FIGURE_CASES`.
  - **Realized bid** (`observations[6]`): `label_cases("bid", "1.25")`, plus a check that accepted cases also lack the "is not labelled" refusal.
  - **Decision text** (`decision.instrument`, `decision.decision_maker_role`): `TEXT_CASES`.
  - **Flag span** (`attributions[0].flag_quote`): `TEXT_CASES`.
  - **Size-quote span** (`thesis.downside_sizes[0].quote`): `TEXT_CASES`.
  - **Not run:** figure cases whose value is not N.NN. Those values are refused by `_FIGURE` with the same "does not occur" issue, as in the inventory. `test_r11_the_size_level_holds_the_edge_cases_it_can` checks that every edge shape still runs in the 1.25 and 0.25 cases.
- **Blank text**, in `test_r11_blank_text_gets_the_pinned_frame`: `BLANK_CASES` × 26 fields, checked through `blank_failure` against the pinned `<path>: text is empty`. The fields are the 7 decision fields, 10 absence reason/follow_up fields, the 2 `outcome_absence` fields (on no_outcome), `attributions[0].basis`, `lessons[0].lesson`, the 5 `extra_gaps[0].*` fields and `synthesis.text`.
- **Red before the fix:** 13 tests failed. Six were edge cuts (as in the inventory's 6/21), four were wrap-splits (the inventory's 3, plus the size-span field it did not run), and three were new B1 unit tests. Blank text was all green.

### Class by class
- **Genuine, soft hyphen, dashes, NBSP, signs (round 10):** pass, unchanged.
- **Edge cut (B1): fixed.**
  - `edge-prefix`, `edge-minus`, `edge-close-paren`, `edge-open-paren` and `edge-end-digit` (1.25), and `edge-minus-0.25`, now get the pinned `thesis.downside_sizes[0]: level_text <v> does not occur in the quote`.
  - `edge-start`, `edge-end`, `edge-stop` and `edge-mid` stay accepted.
  - How it works: the new `_on_page(value, quote, page)` checks the figure against the page. The figure must be the same unsigned whole figure at every occurrence of the quote (as normalised and as joined), in every page reading (normalised and joined). It reuses the round 10 pattern, now factored into `_whole`, which `_token_once` also uses.
  - It is called at the existing occurrence check in `_size` and `_observation`, with the existing issue. For observations only the end edge can apply, because the label always comes first.
  - The edge gate is implicit. Away from an edge, every character the pattern reads is inside the quote, so the result is the same as checking edges only. The docstring says so.
- **Wrap (B3): fixed.** `_wrap_split(value, quote)` is true when `hyphen_wrapped(quote)` and `"- "` occurs in `normalise(value)`. Each caller keeps its existing issue:
  - decision text: `decision.<f>: text <t> does not occur in the quote`;
  - size-quote span and flag span: `... not a span of the recorded downside paths`.
  - **Not wired:** the size statement and the default subject. Their "values" are owner-built: the statement is a fixed label, a comparator from a closed list and an N.NN level, and the subject is a regex. Neither can hold `"- "`, so the rule can never fire there.
- **Blank text: passes** with the pinned `<path>: text is empty`. No code change.

### Riding items (round 10 review Lows)
- **Low-1:** `"reported as s-1.80x."` was added to `test_r10_a_dash_that_is_not_a_sign_still_validates`, and `("350", "s-350")` to `test_r10_the_rules_non_signs_are_read_unsigned`.
- **Low-2:** `_token_once("1.80", "(see 1.80)")` is now asserted True in `test_r10_a_parenthesis_around_a_unit_is_not_a_sign`.

### Other tests added
- `test_r11_b1_a_bid_cut_at_the_quote_end_is_read_on_the_page`: `bid 98.00` cut from `98.005` is refused; the same cut on the frozen page is accepted.
- `..._every_occurrence_of_the_quote_on_the_page_is_read`: includes the case where the quote is not on the page, which returns False.
- `..._a_wrapped_page_is_read_both_ways`.
- `..._a_wrapped_quote_is_read_joined`.
- `test_r11_b3_a_hyphen_space_in_an_unwrapped_quote_still_occurs`.

### Mutants
Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-class/mutate.py`. It runs in a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. Output is `mutate.out` in the same folder.
- The script exits 0, and the unmutated copy passes.
- All 12 mutants are killed (pytest exit 1): b1-size-revert, b1-observation-revert, b1-unseen-accepts, b1-first-occurrence-only, b1-no-joined-page, b1-no-joined-quote, b3-decision-revert, b3-size-span-revert, b3-flag-revert, b3-unwrapped-refuses, low1-guard-case, low2-paren-close-only.

### Gates (all exit 0, from the worktree root)
- **pytest** on `tests/test_method_cp8.py`: 370 passed.
- **ruff check** and **ruff format --check** on both files. The first run flagged import order and one format line; both were fixed with ruff before the commit.
- **`MYPYPATH=src mypy --strict`** on both files, with the cache in scratch.
- **Also run:** `tests/test_defect_classes_selfcheck.py`, 152 passed.

### Stage 2 notes for `methods/cp8.md` (not written; outside the files I may edit)
- **Round 10 sign rule:** a figure read from a quote is the signed numeral it prints, and an accounting `(N)` reads as negative.
- **Unsigned grammar limit:** a negative leverage or bid fails closed with "does not occur".
- **B1:** a figure at a quote edge is read on the page at every occurrence of the quote, in both readings.
- **B3:** a value holding `"- "` against a wrapped quote does not occur. This covers decision texts, the size-quote span and the flag span. The statement and subject checks take no analyst text.
- **Blank text:** uses the pinned `<path>: text is empty` frame.

### Not verified
- **Not pinned by the rulings:**
  - A wrapped quote whose joined form reads a figure as signed (`(-\n1.25` becomes `(-1.25`). The joined needle then has no unsigned figure to check, so only the plain reading is checked.
  - A page minus followed by a line break before the digits.
- **Not re-run:** LEAD's `p_edge_pages.py`, `p_sign_rule.py` and `p_signed_frozen.py`, the earlier `<S>/cp8-r5/mutate_r5.py` mutants, and the inventory probe.
- **Not run:** the full repo suite.
- **Not mutation-tested:** the overlapping-occurrence step (`at + 1`).
- **Not on the analyst path:** the B1 unit tests call `_on_page` directly with hand-written pages.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
