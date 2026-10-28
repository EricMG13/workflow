# CP-1D raw-quote check report (controller-saved from the implementer's hand-back)

## CP-1D raw-quote read check: done

I found a defect of the M1 class in CP-1D and fixed it test-first. It caused false refusals only: no wrong value could be stored.

**Commit:** `7c88a98` on `claude/cp1d-stage1`, after fast-forwarding to `c8dbd05`. It touches two files: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp1d-stage1/src/deploy_workflow/owners/cp1d.py` (+3/−2) and `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp1d-stage1/tests/test_method_cp1d.py`.

**What was wrong.** `_basis_amounts` (cp1d.py:503) ran `_AMOUNT.findall` on the raw quote, but `citation_issues` matches the quote with U+00AD deleted. A soft hyphen inside a basis figure (`1­.80`) therefore split it into two amounts. The validator then refused with "Accepted basis quote must contain exactly one amount", although the matched text holds one amount. In the r17 case that same text replaced the bounds text.

**The fix:** `_AMOUNT.findall(normalise(citation.quote))`. No new wording. The stored citation is kept as given. Every oracle file is pure ASCII, so no frozen outcome changes.

**Why no wrong value could be stored.** The pattern `[0-9]+(?:\.[0-9]+)?` reads ASCII digits and `.` only.
- Deleting U+00AD can only join runs, never change one run. So a raw reading with exactly one amount always equals the normalised reading.
- Mapped dashes, minus, quote marks, whitespace and hyphen-wrap joins never touch digits or `.`.

## Reads

The only quote-text read in cp1d.py is `_basis_amounts`, used at four sites. Elsewhere, evidence shows only source and locator (:880), and the `_register` / `item.line` citations are Python-made from the span itself, not analyst quotes read after a match.

| Read (line after the fix) | Test | Verdict |
|---|---|---|
| Shape count `len(amounts) != 1` (:570) | All three soft-hyphen tests below | Fixed |
| Bounds amount `Decimal(amounts[0])` (:573) | `test_soft_hyphen_in_the_basis_figure_meets_the_bounds_rule`: r17 quote with `3­.00` and `3.0­0`, plus `2­026`, whose raw first run (2) would pass the bounds; expects r17's bounds text | Fixed |
| Source path `_outcome` (:541) | `test_soft_hyphen_in_the_basis_figure_composes_the_page_amount`: `1­.80`, `1.­80`, `1.8­0`; every fact equals the oracle except the basis citation's quote | Fixed |
| Recurring kept basis `_outcome` (:533) | `test_partly_supported_recurring_composes_as_zero[basis, U+00AD in the figure]` (`0.­20`); full oracle equality | Fixed |
| A mapped dash or minus in the figure (all four sites) | `test_dash_in_the_basis_figure_reads_like_the_match`, one case for each of the seven `quotes._DASHES` points: page:1 states `1.20-1.80` and the quote uses the mapped dash; the locator accepts it, and the validator refuses with r18's text | Not reproduced, kept as a guard: both readings hold the same two amounts |

Each test also checks that `citation_issues` accepts the quote. Before the fix, 6 of the 15 selected tests failed for exactly this cause; the third bounds case was added later and the revert mutant shows it fails too.

## Mutants and gates

**Mutants: exit 0, all killed.** I ran them on a full copy of the worktree; the copy's `src` was the one imported. The script is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-quote-mutants/mutate.py`.

| Mutant | Failed tests | pytest exit |
|---|---|---|
| Control (no mutant) | 16 passed | 0 |
| Fix reverted | 7 | 1 |
| Source path raw | 2 | 1 |
| Kept basis raw | 1 | 1 |
| Shape count raw | 7 | 1 |
| Bounds amount raw | 2 | 1 |

**Gates, all exit 0, first run after the fix:**
- pytest on `tests/test_method_cp1d.py`: 111 passed, 1 skipped (the Stage 2/4 placeholder).
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

## Older defect, for LEAD

The amount pattern ignores a sign, in raw and normalised readings alike. A page line `a saving of -1.80`, cited as the basis, validates, and `T1D.2.a01.basis` composes 1.8, a value the page does not state. The bounds rule "above 0" never sees the minus.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-quote-mutants/p_signed_basis.py`, exit 1 (reproduces).
- Fixing it needs a ruling (refuse a signed amount, or read the sign), so I did not fix it.

Not verified: the full suite and the other owners' tests (only the CP-1D file ran, per the brief); whitespace inside a figure, which the brief did not ask for; GitNexus `detect_changes`, which is the controller's step; Stage 2 citation checks and rendering of a basis citation that holds U+00AD.

`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
