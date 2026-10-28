CP-2E class round is done. Commit 38f0ddc on `worktree-agent-a219254fe68cc1c2d` (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a219254fe68cc1c2d`), parent 864ffe3, which you accepted. All gates exit 0 and all 16 mutants are killed.

Only two files changed: `src/deploy_workflow/owners/cp2e.py` and `tests/test_method_cp2e.py`. No new wording.

**Class by class (adapter test first; the red run matched the inventory):**
- **Genuine, soft hyphen, dashes, NBSP, signs:** pass, before and after.
  - Run through `fx.foreign_ebitda_share.percent_text` (figure cases) and `rate_exposure.spread.bps_text` (figure cases, plus the `spread` label cases for 25 and 1.25).
  - Left out, and pinned by `test_class_cases_cover_the_bounds`: share `sign-2024-2025` and `sign-s-350`, which are above its bound of 100; spread `sign-2024-2025`, which is off its 999.9999 shape.
  - Every case also asserts the exact issue tuple, so a case cannot pass because its quote is off the page.
- **Edge cut (B1):** fixed. 13 share cases and 13 spread cases were red, now pass.
  - `_once(token, quote, page)` counts the unsigned token once in `normalise(quote)`, as before.
  - New: at every occurrence of the quote in every page reading, each counted span must also be an unsigned whole figure on the page.
    - Quote forms: `normalise`, plus the joined reading if the quote is wrapped.
    - Page readings: `normalise`, plus the joined reading if the page is wrapped.
    - Overlapping occurrences count.
  - Checking every span rather than only edge spans gives the same result: away from an edge the surrounding characters are the quote's own.
  - The refusal is the existing `<path>: <key> <v> does not occur in the quote`. It covers the share and every labelled operand (balance, spread, floor).
- **Wrap (B3):** fixed. `wrap-split` was red, now passes. When `hyphen_wrapped(quote)` holds and `"- "` is in `normalise(reference_rate)`, the issue is `rate_exposure.rate_basis: reference_rate does not occur in the quote`. `wrap-joined` stays accepted.
- **Blank text:** fixed. 84 of 85 were red; the one green was the `""` limitation, which already gets the "limitation is required" refusal, so that refusal stands.
  - The frame is `<path>: empty text`, since CP-2E pins none. It fires for whitespace-only text and for `""`, because CP-2E has no schema refusal of `""`.
  - Fields:
    - `shock_rationale`
    - `assessments[0..2].text` and `assessments[2].limitation`
    - `summary.text`
    - `hedge_ratio.rationale`
    - reason and follow_up of `hedge_absence`, `fx.operating_fx_absence`, `rate_absence` and `fx.debt_currency_absence`
    - `rate_exposure.rate_basis.reference_rate`, under both FLOATING and FIXED
  - `reference_rate` is my addition beyond the inventory. It is analyst text, it is rendered as a table cell, and `" "` passed before.

**Own tests beyond the library** (`test_b1_every_occurrence_in_every_reading` and three others), each with an accepted twin:
- a page minus followed by a line break before the digits, refused through the joined page reading;
- a wrapped quote whose joined spelling is cut from `255`;
- a second occurrence that is cut;
- an overlapping occurrence that is cut;
- `floor 2` quoted from a page that prints `floor 25`;
- an unwrapped quote that prints `first- priority`, accepted;
- `Term-SOFR` in a wrapped quote, accepted.

**Riding items:** none for CP-2E.

**Mutants:** `<S>/cp2e-class/mutants.py`, output in `mutants.out`. It runs in a full temporary copy with `PYTHONDONTWRITEBYTECODE=1` and exits 0. The baseline exits 0 and all 16 mutants exit 1 (killed):
- B1: no page check; plain page reading only; plain quote only; first occurrence only; non-overlapping occurrences; labelled reader handed the quote as its page; share reader handed the quote as its page.
- B3: revert; any `-`; wrapped or not.
- Blank: frame never added; `""` only; missing from `prose`; limitation unchecked; absence path without `fx.`; reference_rate unchecked.
- "B3 any `-`" survived the first run. It is killed by the added `test_b3_refuses_only_the_wrap_spelling`.

**Gates (exit codes):**

| Gate | Exit | First run |
|---|---|---|
| pytest `tests/test_method_cp2e.py` (350 passed; every frozen case passes unchanged) | 0 | n (red by design, then 2 adapter set-up fixes) |
| `ruff check` | 0 | y |
| `ruff format --check` | 0 | y |
| `MYPYPATH=src mypy --strict` | 0 | y |

I also ran `tests/test_host_h1.py -k cp2e`: 1 passed.

**Stage 2 notes (`methods/cp2e.md`):**
- Quote figures are read on the page (round 11 B1). A figure counts only if it occurs once unsigned in the normalised quote and, at every occurrence of the quote in every page reading, the page prints it there as the same unsigned whole figure. This covers the share and the balance, spread and floor operands.
- B3: a wrapped rate-basis quote refuses a `reference_rate` spelled with `- `.
- Blank text: every analyst text field, `reference_rate` included, refuses whitespace-only and `""` with `<path>: empty text`.

**Not verified:**
- The full suite was not run.
- `reference_rate` is in the blank class on my reading of "every analyst text field"; the inventory did not list it.
- The joined-page-minus case (a page `-` followed by a line break) is refused by the literal B1 rule. Round 11 lists this case as not examined.
- A non-Insufficient-Information assessment with a `""` limitation now gets `assessments[i].limitation: empty text`, where before it passed. No case pins this either way.
- GitNexus `detect_changes` was not run.

**Pre-existing, for the owner:** the digits issue for the fx absences names `operating_fx_absence.reason` and `debt_currency_absence.*` without the `fx.` prefix. The new empty-text frame uses the true path `fx.…`, so one field now has two path spellings. I left the digits path unchanged.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`
