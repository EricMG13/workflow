# CZR CP-1 precheck fix: review (stage contract; mx-precise, read-only)

Change: `claude/s5-czr-cp1` `cf4c0ec..3d93a4c` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3822801a9a54e78a`. The RED commit is aa6ab1d and the fix is 3d93a4c. Write probes only under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/czr-cp1-review/`, and name each probe in the finding it supports. Do not run the full financial, earnings, connected or render suites, or any genuine owner run: a timing measurement is running on this machine.

## Inputs
| Item | File |
|---|---|
| Brief and ruling | lane `work/build/stage5/czr-cp1-brief.md`; `docs/rulings/2026-10-29-stage3.md` item 70 |
| Builder's notes | an unrecognised column cell still consumes `periods` (to keep the `iter(periods)` assertion); a first cell that is itself a column or span cell is now kept, not dropped; `_iso` uses a narrow `except ValueError` for impossible dates; `ruff check` shows 3 errors, which the builder says predate the change |

## Process
1. **Synthetic behaviour unchanged (the key check).** Write a differential probe:
   - Take every statement page of every synthetic pack in the repo: each `cases/**` pack the tests build, plus the `tests/*_runs.py` `make_pack` builders. Select pages with `STATEMENT_HEADING`, and extract them with `extract_statement_lines`.
   - Compare the pre-fix `_column_periods` (from cf4c0ec, loaded from a scratch copy) with the new one over the period sets those cases' CP-1 submissions use. Old `("a", "b")` must equal new `(frozenset({"a"}), frozenset({"b"}))`, and old None must equal new None.
   - Also compare the old caption chain with the new `_statement` for every extracted line.
   - Report the page count, the line count and every difference.
   - A difference is High unless it only turns an old None into a mapping that the synthetic submissions do not reach. Check the "first cell kept" change in particular.
2. **Spec.** Check each brief item:
   - the cell split;
   - the span and year pairing, including n a multiple of k;
   - QUARTER, YTD and FY each need exactly one match;
   - a balance date gives every non-LTM period ending that date;
   - the column sets are pairwise disjoint;
   - `line.period_id in period_ids`;
   - `_statement` puts the caption first, then the single heading kind, else None.

   Probe the edge cases: month abbreviations, a missing comma, a trailing `(1)` footnote, a header with both a span row and a single dated row, k=2 with n=3, Feb 30.
3. **RED is genuine.** The new tests fail on cf4c0ec for the reported cause.
4. **Policy and quality.**
   - No stub, no catch-all; `_iso`'s except is narrow.
   - Run `ruff check` on the changed files at cf4c0ec and at 3d93a4c: no new error.
   - Complexity is reasonable. `complexipy` is not installed, so judge by reading, and flag any function that is clearly over 15.

## Output (return as text, under 800 tokens)
- verdict (APPROVE / REVISE);
- findings ranked High, Medium, Low, each with the location, the evidence and the probe path, plus the probe's exit code;
- a `Not verified:` line.
