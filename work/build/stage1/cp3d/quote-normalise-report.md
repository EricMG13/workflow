# CP-3D raw-quote check report (controller-saved from the implementer's hand-back)

## CP-3D raw-quote reads: confirmed and fixed (worktree `cp3d-stage1`)

The defect class reproduces in CP-3D. Before the fix, a soft hyphen inside a figure let the validator accept values the page does not state:
- bid 98 from a page stating 98.50;
- margin 25 bp from 425;
- zero amortisation from 10 percent;
- reference rate 4% from 4.30%;
- talk at the page's bid level.

Soft hyphens inside labels, dates and names also refused quotes that the page does state. All nine reads now run on `quotes.normalise(quote)`. No wording was added and no pinned refusal changed.

**Commit:** `22e9166` on `claude/cp3d-stage1`, fast-forwarded first to `c8dbd05`. It touches only `src/deploy_workflow/owners/cp3d.py` (+13/−8) and `tests/test_method_cp3d.py` (+145).

**`out.on_page`** (cp3d.py:408-418) calls `quotes.quoted(quote, page)` directly on `context.pages[source_id][locator]`. It has no check of its own and does not use `citation_issues`. It stays as it is. The composer reads only a quote's `source_id` and `locator` (`_trace`, `terms_period`), never its text.

All 14 cases below were red before the fix, each with the issue shown in the table. A soft hyphen is written `­`.

| # | Read (line before the fix) | Test case | Before the fix | Verdict |
|---|---|---|---|---|
| 1 | Level occurrence, `_token_once(lt, o.quote)` :443 | refuse[level-split], refuse[level-cp8-shape] | `bid 98­.50` with level_text 98 validated (bid 98; page 98.50). The exact CP-8 shape `9­8.50` with 8.50 was refused, but by the label issue instead of "does not occur". | fixed |
| 2 | bid/offer label, `_labelled(o.kind, …)` :453 (whitespace-only cleanup :423) | refuse[bid-label], accept[offer-label] | `bid 98.50­3 … offer 98.­50` validated bid 98.50, though the page's bid is 98.503. `off­er 99.25` was refused as "not labelled offer". | fixed |
| 3 | Talk-is-not-bid/offer, `_labelled("(?:bid\|offer)", …)` :450 | refuse[talk-label] | Talk with `b­id 98.50` validated at the bid level. | fixed |
| 4 | `as_of_text not in o.quote` :472 | accept[as-of-date] | `January 9, 20­26` refused. False refusal only. | fixed |
| 5 | margin, `_check_quoted_numeral` → `_token_once` :514 | refuse[margin] | `4­25` with bps_text 25 validated. | fixed |
| 6 | amortisation, same path | refuse[amortisation] | `1­0 percent` with value_text 0 validated; zero amortisation selected the simple margin. | fixed |
| 7 | `date_text not in term.quote.quote` :538 | accept[maturity-date] | `20­29` refused. False refusal only. | fixed |
| 8 | `rr.name not in rr.quote.quote` :570 | refuse[reference-rate-name], accept[reference-rate-name] | Name `SO­FR` validated and was stored with the soft hyphen. Name `SOFR` against `SO­FR reference rate` was refused. | fixed |
| 9 | Reference rate level, `_token_once(pt, …)` :576 | refuse[reference-rate-level] | `4­.30` with percent_text 4 validated. | fixed |
| 10 | `inst.name not in inst.quote.quote` :633 | refuse[instrument-name], accept[instrument-name] | Same two directions as row 8. | fixed |

How the tests check each direction:
- **Refuse cases** use a synthetic page added at `page:9` in both the financial and market sources. They assert the exact one-item issue list, using the existing wording.
- **Accept cases** use the frozen pages. They assert `()` and that the tables and claim texts equal the positive oracle.

Dates can only have been falsely refused, never given a wrong value. A `date_text` holding U+00AD or a dash never parses. A plain-text substring of the raw quote also stays a substring after normalising.

The fix is in `_token_once` and `_labelled` (each now calls `normalise`) and in the four `in` checks: cp3d.py:173-177, :424, :473, :539, :571-573 and :636-638. Rulings 6b, 6e and 6g keep their check order: numeral, occurrence, leading zero, label, decimals, bound.

**Mutants:** I reverted each of the six fixes on its own in a full temporary copy of the worktree. The control exits 0. All six mutants exit 1, each killed by its own cases (`token_once` by 5 cases, `labelled` by 3, `as_of_text` by 1, `maturity_date` by 1, each name by 2). The script exits 0.
- Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-quote-mutants/revert_mutants.py`
- The first run misreported the maturity mutant. It reused the `.pyc` compiled for the `as_of_text` mutant: both reverts drop 11 characters within the same second. The script now sets `PYTHONDONTWRITEBYTECODE` and clears `__pycache__`, and the numbers above come from that rerun.

**Gates, final run, all exit 0:**
- pytest `tests/test_method_cp3d.py`: 229 passed.
- `ruff check`: 0.
- `ruff format --check`: 0. The first run exited 1 on the layout of three new test lines; I fixed them by hand.
- `MYPYPATH=src mypy --strict` on both files: 0.

**Earlier problems, for the owner or LEAD (not fixed here):**
- **Signs are never read.** The lookbehind `(?<![0-9.])` in `_token_once` lets `-` or `−` come before a token, in either reading. A page stating `−0.25 percent` with percent_text `0.25` would validate as +0.25. This is reasoned from the regex, not probed.
- **The `Published` line is read from raw page text** (`publication_dates`). This is the page side, not a quote read. A soft hyphen there falls back to "publication date not stated", which is safe.

**Not verified:**
- No dash or minus case is tested. For numerals and labels I reasoned they are neutral: the mapped `-` is neither a digit, `.` nor whitespace, so tokens split the same way in both readings. Names go through the same `normalise` call, but no dash case was written for them.
- `normalise(quote)` does not join the quote's own hyphen line wraps, but `quoted` may have matched on that joined form. A name with a hyphen at a wrap could still be falsely refused. No frozen case has one.
- The fix also now refuses an `as_of_text` or `date_text` with a trailing `\n`, because `_DATE`'s `$` accepts one. That case is untested.
- `prose.issues` and `bare_figures` were not run; no new strings were added.
- The full suite, Stage 2 and real pages were not run, per the brief.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
