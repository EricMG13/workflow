# CP-8 round 9 report (controller-saved from the implementer's hand-back)

# CP-8 round 9 report (items 1-5)

All five round 9 CP-8 items are applied test-first and committed as `fa55df5`, on top of `cba7f82`, which I left as it was. All 155 tests pass, and every gate exits 0. No frozen value or pinned refusal changed: the frozen cases and all 68 refusal literals plus r00 pass unchanged.

- **Step 0:** `git merge claude/module-dev-status-review-0981b6` gave merge commit `a36faa2`, with no conflicts.
- **Commit:** `fa55df5` "feat(cp8): apply LEAD round 9 CP-8 items 1-5", ending with the Co-Authored-By line. Only `cp8.py` and the test changed.
- **Files:**
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/src/deploy_workflow/owners/cp8.py`
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/tests/test_method_cp8.py`
- **Test first:** before the module changed, 11 new tests failed, each for its reported cause:
  - blank text was accepted, or got the vocabulary or date wording;
  - the April 30 span validated;
  - a prior_case default statement got the issuer wording or validated;
  - p11's locator issue came first;
  - there was no `exit_trigger` row.

## Items and their tests

| Item | Test | What it checks |
|---|---|---|
| 1 | `test_r9_1_blank_decision_text_is_empty` | action_bias, confidence, instrument, decision_date, decision_maker_role and posture, each blank, give `decision.<field>: text is empty`. The check sits after the citation check and before the vocabulary check. |
| 2 | `test_r9_2_an_as_of_is_the_only_date_its_quote_states` | p03's realized April 30 span; the expected offer's two-date span; the default statement over a two-date span; a span repeating the same date is accepted. The check sits after "does not occur" and before the after-decision check, using the ruled date match on the normalised quote. |
| 3 | `test_r9_3_a_default_statement_cannot_cite_prior_case` | Run with prior_case authority `unknown` and `issuer`. Before the issuer check. |
| 4 | `test_r9_4_the_source_rule_comes_before_locator_and_quote` | p11's three cases: the realized observation's r36 and authority rules, and the default statement's item 3 and issuer rule, now run inside `_cite` after pack and scope and before `citation_issues`. |
| 5 | `test_r9_5_an_exit_trigger_absence_has_its_gap_row` | T7.8 `exit_trigger` sits right after `expected_hold` with the five ruled fields; LIM_NO_EXIT is unchanged. |

**8-7 setup change (item 2):** the 8-7 and 6h split tests chose a two-date span, which item 2 now refuses. The frozen pages have no single-date span that splits a quotation. So `split()` and `split_pack()` now edit the side's quotation line into a bid line and an offer line, each with one date (the hash is recomputed), and cite them separately.
- All the ruled outputs are unchanged:
  - the 8-7 reasons (the 2026-01-09/2026-01-10 and 2026-04-29/2026-04-30 date pairs);
  - the 6c (b) and 6h rows;
  - window end 2026-04-30.
- The old two-date span is kept only as the item 2 refusal input.

## Probes (`<S>/cp8-adversary/`, run without `-I` so `_common` imports)

All five now exit 0.

| Probe | Exit | Result |
|---|---|---|
| `p02_empty_decision_text.py` | 0 | All three blank texts refused |
| `p03_as_of_not_bound_to_figure.py` | 0 | Refused: `as_of_text April 30, 2026 is not the only date in the quote` |
| `p10_prior_case_default_statement.py` | 0 | Refused with the item 3 issue |
| `p11_source_rule_order.py` | 0 | The source rule is reported in all three cases |
| `p08_exit_absence_follow_up.py` | 0 | The follow_up is composed in T7.8 `exit_trigger` |

## Mutants

`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r5/mutate_r5.py` exits **0**: 51 of 51 mutants killed, plus the control.
- It runs from a full temporary copy, with a baseline check and a control mutant.
- Seven new round 9 mutants:
  - blank text allowed;
  - only-date check off, for observations and for the default;
  - a date-count variant of the only-date check;
  - default may cite prior_case;
  - source rule moved after locator and quote;
  - no exit row.
- One anchor was updated (the M1 default read). A first run, before that fix, exited 1 on that stale anchor alone.

## Gates (both files)

All three exit 0 on the final run.

| Gate | First run |
|---|---|
| `ruff check` | 1 (8 × ISC004, implicit concatenations in lists and tuples; fixed by parenthesising, values unchanged) |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` | 0 |

pytest: 155 passed. The worktree guard refuses the `PYTHONPATH=src "<abs venv>/python"` form, so I ran `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp8.py`: the same interpreter, with pyproject's `pythonpath` supplying `src`.

## Prose and bare-figure hits

`probe_prose.py` exits 1. It now covers the 6h and round 9 strings: 79 new strings, 2 hits, neither reworded.
- **The 8-3 rails line:** `Bare figure: 1.67x`. Round 6c rules rails text outside the claim check.
- **The new validator issue:** `observations[4]: as_of_text April 30, 2026 is not the only date in the quote` hits on `observations[4]`. LEAD's round 9 probe already predicted this hit, and validator issues sit outside the claim check.
- **Clean:** the other new strings, including the `exit_trigger` row texts, the item 3 issue and the default-statement date issue.

## Stage 2 notes (methods/cp8.md, not written)

- **Item 2 guard limit:** only `Month D, YYYY` dates are counted. ISO or day-first dates in a quote are not seen, and the rule binds the as-of to the one date the span states, not to the figure.
- **Builder syncs:** optional for items 1 and 4; not done.

Not verified: no frozen case composes any round 9 state, so the split, prior_case-default and exit-row inputs come from edited pages and literals I built; I did not run LEAD's `p_cp8_dates_per_quote.py` (the pinned refusals pass under the new order, which covers its seven literals); the reviewer's other probes (p01, p04–p07b, p09, p12) were not re-run this round.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
