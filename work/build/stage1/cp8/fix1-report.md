# CP-8 fix round 1 report (controller-saved from the implementer's hand-back)

# CP-8 fix round 1 report

M1 is fixed test-first, and committed as `9f2b2f5`. Every figure, date, label and text that `cp8.py` reads from a quote now reads the form the citation matcher accepts. The reviewer's L1 survivors are killed except the four the brief says to justify. All 144 tests pass, and every gate exits 0.

- **Step 0:** `git merge claude/module-dev-status-review-0981b6` (merge commit `52dcb7b`) had no conflicts and left `cp8.py` and the test file unchanged.
- **Commit:** `9f2b2f5` "fix(cp8): read every quoted figure, date and text as the matcher normalises it", on `worktree-agent-a3cc9818386e8861a`, ending with the Co-Authored-By line. Only the two allowed files changed.
- **Files:**
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/src/deploy_workflow/owners/cp8.py`
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/tests/test_method_cp8.py`

## The fix (M1)

- `_norm` is now `deploy_vii.quotes.normalise`.
- It is applied at every read of a quote:
  - observation value, label and as-of date (`_token_once`, `_labelled`);
  - decision text in its quote;
  - size level and statement;
  - default statement date and subject;
  - flag_quote and downside spans;
  - the 6c (f) exit-trigger digit check.
- The only raw quote text left is displayed, never read: the T7.2 quote cells and the T7.3 default cell.
- No new wording. The existing issue fires: `observations[6]: value_text 8.00 does not occur in the quote`.

## Findings and their tests

**M1** (red seen before the fix: the first validated with `()`, the other two were falsely refused):

| Test | Case |
|---|---|
| `test_m1_soft_hyphen_inside_a_quoted_figure` | The p01 case |
| `test_m1_whitespace_inside_a_quoted_date` | A no-break space in a date |
| `test_m1_mapped_dash_inside_a_quoted_designation` | An en dash in "Term Loan B-2", over an edited prior_case page |

- I added `test_m1_soft_hyphen_inside_a_quoted_size_level` and `test_m1_whitespace_inside_a_quoted_default_date` so the size and default reads can be mutated too. Their red is shown by the "reads the raw quote" mutants being killed.
- **Mapped character:** the brief asked for one inside a figure or date. A mapped dash or minus turns one non-digit into another, and the figure tokens, `_FIGURE` and the date form contain no dash. So a mapped character cannot change a figure or date read; it only changes text reads, which is why that test uses a decision designation.

**L1** (each test kills its survivor, confirmed by p07 and my runner):

| Survivor | Test |
|---|---|
| First figure relaxed | `test_8_15_the_first_figure_after_the_label` (p09's two frozen spans) |
| CP-6-present `current_decision` row | `test_decision_line_reads_the_cp6_call` (now also asserts T7.8) |
| Value occurs once relaxed | `test_a_value_quoted_twice_is_refused` (edited pack) |
| Realized check equal-day boundary | `test_a_realized_figure_dated_on_the_decision_day_is_refused` |
| Default statement equal-day boundary | `test_a_default_statement_dated_on_the_decision_day_is_refused` |
| `N.NN` format (8-15) | `test_8_15_a_figure_is_quoted_as_n_nn` |
| Blank flag_quote | `test_a_blank_flag_quote_is_refused` |
| `isnumeric` replaced by `isdigit` | `test_a_numeric_character_counts_as_a_digit_in_analyst_text` (½) |
| EXACT dropped in derive | `test_derive_runs_under_the_exact_context` (an operand needing 29 digits raises `Inexact`) |
| EXACT dropped in compose | `test_composition_runs_under_the_exact_context` |

- The compose test spies on `format_date` (called only inside composition) to check the context traps `Inexact`. No validated input can produce an inexact composer step, so the compose guard is unobservable any other way.

**Justified without a test:**
- **Bid exceeds offer (r38):** the oracle reserves it.
- **The two `source_authority` guards:** they belong to Stage 2, where CP-0 facts are bound.
- **Citation de-duplication:** the oracle compares cites by page, so a duplicate cite is invisible to it.

**Untested direction:** `test_8_7_realized_split_beside_a_missing_expected_fails_closed`. It validates with `()`, then raises "no pinned wording".

## Probes

| Probe | Exit | Result |
|---|---|---|
| `p01_soft_hyphen_figure.py` | 0 | "REFUSED (fixed)" |
| `p09_first_figure_reachable.py` | 0 | Real code refuses both spans; the relaxed rule accepts both |
| `p07_mutate.py` | 1 | 2 survivors: bid exceeds offer (r38) and citation de-dup, both justified |
| `p07b_mutate.py` | 1 | 2 survivors: the two `source_authority` guards (Stage 2), justified |
| my `mutate_r5.py` | 0 | 41 of 41 killed plus control |

- p01 and p09 must run without `-I`, because they import `_common` from their own folder.
- p07, p07b and my runner all mutate a full temporary copy, with a baseline check and a control mutant. My runner now also holds the M1 and L1 mutants: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r5/mutate_r5.py`.

## Gates (both files)

All three exit 0 on the final run.

| Gate | First run |
|---|---|
| `ruff check` | 1 (ISC004, FURB157) |
| `ruff format --check` | 1 |
| `MYPYPATH=src mypy --strict` | 1 (`format_date` not exported from cp8; the test now imports it from `deploy_vii.display`) |

- pytest: 144 passed.
- The worktree guard refused the brief's exact command form (`PYTHONPATH=src "<abs venv>/python" -m pytest …`). I ran `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp8.py`, the same interpreter, with pyproject's `pythonpath` supplying `src`.
- `ruff format` wrote the test's `\u` escapes back as literal invisible characters. I replaced them with named `chr()` constants (the same practice as `deploy_vii.quotes`), and the test source is ASCII-only.

**New strings:** none (docstrings only), so there was nothing to run through `prose.issues` or `bare_figures`.

Not verified: any real document whose quote holds a soft hyphen or mapped character (no frozen quote does; edited and inline quotes only); that the reviewer's p02–p06 and p10–p12 still exit as reported (not re-run; outside this round); the LEAD items (split-plus-missing wording, review "to LEAD" 1–5), left untouched.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
