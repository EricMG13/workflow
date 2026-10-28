# CP-8 round 9 scoped review (mx-precise; controller-saved)

CP-8 round 9 scoped review (worktree agent-a3cc9818386e8861a, `git diff a36faa2 fa55df5`)

## Verdict: APPROVE

**Spec verdict: PASS.** Each of items 1 to 5 matches its ruled string and position byte for byte.

**Quality verdict: PASS.** I found no High, Medium or Low findings. There are two Info notes.

## Spec check, item by item (src/deploy_workflow/owners/cp8.py)

1. **Item 1** (cp8.py:573-574). `elif not text.strip()` emits `{path}: text is empty`, where the path is `decision.<field>`. It sits after the `if found` citation branch and before the vocabulary branch, as ruled. Test at tests/test_method_cp8.py:1244.
2. **Item 2.**
   - The `_DATE_IN_QUOTE` regex (cp8.py:114-118) is the ruled pattern exactly.
   - `_only_date` (cp8.py:387) requires every match to equal `at`, so a repeated date is accepted.
   - In `_observation` (cp8.py:681-682) the check runs on `_norm(...)`, right after "does not occur" and before the after-decision check, for both sides.
   - In `_default` (cp8.py:765-768) it has the same position.
   - Both strings match the ruling.
3. **Item 3** (cp8.py:736-743). The ruled string, inside the default's own-source rule and before the issuer check. The test runs with prior_case authority `unknown` and `issuer`.
4. **Item 4** (cp8.py:504-521).
   - `_cite` now runs pack, scope, `only`/`rule`, then `citation_issues`.
   - The realized rule (cp8.py:695-708) runs r36 then authority.
   - The default rule runs item 3 then issuer.
   - The expected and decision quotes are unchanged (`only=`).
5. **Item 5** (cp8.py:1928-1937). The five ruled cells, after the `_EXPECTATIONS` loop and before the `not_compared_*` loop.

## Checks 2 to 7

- **2. Split tests rebuilt.** The 8-7 and 6h tests (test_method_cp8.py:764-857) still assert everything they did before:
  - the 8-7 reasons with both date pairs;
  - `split_row` (6c (b)) and the 6h row with `FOLLOW_UP_6H`;
  - `window_end == date(2026, 4, 30)`;
  - `window_days`, compared, the claims and the limitations.
  Only the setup changed. The fixture is sound:
  - `edited_pack` (test:448-466) asserts that the spans changed and recomputes the sha256.
  - `split()` asserts that each cited quote equals the frozen line before swapping it.
  - Nothing in `src` is faked.
- **3. Date probe.** A second date with a soft hyphen in the month or year, a newline before the day or year, or doubled spaces is refused. A repeated identical date, one copy split by a newline, is accepted. These cases are also refused or accepted correctly:
  - `April 3` against a quote with `April 30` is refused, which is stricter than the old substring check;
  - ISO dates, a date with a letter before the month, and a year followed by a digit are not counted, as ruled.
- **4. Pinned refusals.** `-k "refusal_validator_issues or refusal_ids"` gives 69 passed: 68 entries, plus the coverage test that includes r00. No pinned issue moved.
- **5. Every new test fails without its change.** `mutate_r5.py` kills all mutants, including R9-1 to R9-5: blank text, the only-date check off for observations and for the default, the count variant, prior_case allowed, the rule moved after the locator, and no exit row.
- **6. No frozen value changed.** The diff touches only the two files. No fixture or oracle file is in a36faa2..fa55df5. The removed `Q_REALIZED_OFFER_TWO_DATES` was a test helper, not an oracle value.
- **7. No stubs, fake values or catch-alls.**

## Findings

- **Info** (tests/test_method_cp8.py:1316). The item 5 test pins the row as right after `expected_hold`. It does not pin that the row comes before a `not_compared_*` row, because the positive case has none. The order is correct when read in cp8.py:1928-1938. No probe was run for this.
- **Info.** The ruling says item 2's guard limit is to be recorded in `methods/cp8.md`. Only `docs/methods-drafts/cp8.md` exists, and it was not touched. The implementer's report defers this to Stage 2. It is outside this diff's two-file scope, so I raise it for the controller and do not count it as a defect here.

## Probe exit codes

- `cp8-r5/mutate_r5.py`: 0. Every mutant was killed and none survived. Output: `.../scratchpad/cp8-r5/mutate_r9_review.out`.
- `p02_empty_decision_text.py`: 0
- `p03_as_of_not_bound_to_figure.py`: 0
- `p10_prior_case_default_statement.py`: 0
- `p11_source_rule_order.py`: 0
- `p08_exit_absence_follow_up.py`: 0
- New: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r9-review/p_r9_dates.py`: 0. It covers the item 2 soft-hyphen, newline, repeat and edge cases. It needs `_common.py`, copied into the same folder, and is run without `-I`.

The outputs of the five probes are saved beside them as `*.r9review.out`.

## Gates (target root, that venv)

- pytest `tests/test_method_cp8.py`: exit 0, 155 passed.
- `ruff check` on both files: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict`: 0.

Not verified: I did not run LEAD's `p_cp8_dates_per_quote.py` (I relied on the pinned refusal tests passing). Item 2's order against the after-decision check was confirmed by reading the code only, with no test that combines both defects. The decision field `size` was not run blank, although it shares the code path. The earlier adversary probes (p01, p04 to p07b, p09, p12) were not re-run. The builder syncs are optional and were not checked. The `methods/cp8.md` guard-limit record is not written.
