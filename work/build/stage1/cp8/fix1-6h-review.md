# CP-8 fix 1 + 6h re-review (mx-precise; controller-saved)

**CP-8 re-review (fix round 1 and round 6h) at `cba7f82`**

**Verdict: APPROVE.** M1 is fixed, every L1 survivor is killed or justified, and the 6h row matches the ruling byte for byte. Nothing High or Medium is open. One Low and one Info can ride with the next fix.

**The target worktree changed while I was reviewing.** Another session (LEAD round 9) moved `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a` to HEAD `a36faa2` and left uncommitted edits in both `cp8.py` and `tests/test_method_cp8.py`. One of my probe runs hit a `NameError: Callable` from that partly edited `cp8.py`. So I exported `cba7f82` with `git archive` to `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-fix1-review/tree-cba7f82` and re-ran every gate and probe there. The results below come from that copy. I edited nothing in any worktree.

## Findings

**L-1 (Low): a hyphen wrap inside a quote lets a designation the page doesn't state validate.**
- **Where:** `src/deploy_workflow/owners/cp8.py:374-379` (`_norm` is `quotes.normalise`) and `:555` (the decision text check).
- **Cause:** The matcher (`quotes.quoted`, task 7.11) also tries the quote with its own line wraps joined, so `B-\n2` is read as `B-2`. `normalise` does not join wraps, so cp8 reads `B- 2`.
- **Scenario:** The prior_case page prints "Term Loan B-2". The analyst's quote breaks the line after the hyphen.
  - The text "Northbridge Term Loan B- 2" validates, and T7.1 would show that spacing, which the page doesn't have.
  - The page's own text "Term Loan B-2" is refused (`text ... does not occur in the quote`).
- **Scope:** Figures and dates are not affected. A wrap only adds a space after a hyphen, and the figure regexes, the digit check and the date form contain no hyphen. Only text reads are affected: decision text, the size statement, and the downside and flag spans, where the effect is a false refusal.
- **Origin:** This follows the brief, which specified `normalise`. The fixer applied it faithfully.
- **Fix:** Read the same joined reading the matcher accepted. `quotes._joined` is private, so this probably needs a small public helper in `deploy_vii.quotes`, and that file is outside the lane.
- **Probe:** `cp8-fix1-review/q03_quote_side_hyphen_wrap.py`, exit 1 (reproduces).

**I-1 (Info): the format_date spy is sound, and somewhat white-box.**
- **Where:** `tests/test_method_cp8.py:1213-1222`.
- **Sound:**
  - All three `format_date` calls (`cp8.py:1401, 1442, 1500`) sit inside `compose()`'s `with localcontext(EXACT)` at `:1350`.
  - The assertion `traps and all(traps)` fails loudly if a refactor stops calling `format_date`, so it cannot pass vacuously.
  - It kills "L1 exact context dropped (compose)".
- **Brittle:**
  - It depends on cp8 importing `format_date` by name (it monkeypatches `cp8_module.format_date`).
  - It checks only the `Inexact` trap, not the precision or rounding.
- The fixer says no validated input can reach an inexact composer step, so I accept the spy as the only guard available.

## Checks 1 to 5

**1. M1 holds (read in the file, not taken from the report).** `_norm` is `deploy_vii.quotes.normalise`, applied at every read of a quote:
- observations (`:647`, which covers `_token_once`, `_labelled` at `:390` and the `as_of_text in quote` check at `:648`);
- decision text (`:555`);
- size level, span and statement (`:594`, `:598`, `:602`);
- default date and subject (`:712`, `:715`, `:722`);
- flag_quote and the downside span (`:794`);
- the exit-trigger digit check (`:2062`).

Raw quote text remains only where it is displayed (`:1423` T7.2 cells, `:1478` T7.3 default cell) and as the citation key (`:1207`).
- `normalise` is idempotent, so reading `_norm(_norm(x))` at `:598` and `:602` is harmless.
- Probe `q02_normalised_reads.py` passed 8 of 8 cases, exit 0:
  - refused, as they should be: a soft hyphen moving a figure boundary (`98­.00` read as 8.00, `98.0­0` read as 98.0); a soft hyphen inside a date (`March 3­1` read as March 3; default `April 3­0` read as April 3); a soft hyphen carried in the decision text itself;
  - accepted, as they should be: a newline or no-break space inside a date, and a soft hyphen inside a leverage figure.
- A mapped dash or minus inside a figure needs an edited page, because the frozen pages don't hold one. As noted under L-1, mapping one non-digit to another cannot change a figure or date read.

**2. L1 holds.** All the listed survivors are killed: `mutate_r5.py` kills 44 of 44 fix-round and 6h mutants plus the control. Only the four justified survivors remain:
- **r38 (bid exceeds offer):** justified. `docs/CP8-OWNER-LEASE.md:83` and `expected.json#refusal_coverage` mark r38 as a reserved id that is untested by construction.
- **The two `source_authority` guards (`cp8.py:339-350`):** they guard the CP-0 fact-binding adapter, which is Stage 2. Accepted as the controller ruled.
- **Citation de-duplication:** justified. The test's oracle form de-duplicates cites by `(source_id, locator)` (`tests/test_method_cp8.py:165`), so a duplicate cite cannot be seen.

**3. 6h holds.** `cp8.py:1832-1842` against the ruling (`docs/rulings/2026-10-28-stage1.md:914-922`):
- gap (from `METRIC_NAME`), missing_item, why_it_matters, impact (`COMPARED_ONLY`) and both follow_up clauses (`_SAME_DAY_THEN`, `:1136-1139`) match byte for byte, with the fill correct in both directions.
- `test_6h_one_side_split_and_the_other_missing` (`tests/test_method_cp8.py:752-789`) asserts:
  - all five fields in both directions;
  - the T7.4 split and absent reasons and the direction (8-7, 8-1);
  - the unchanged limitation;
  - the 6c (a) T7.3 bid row.
- The `(cut,), (absent,)` unpacking is safe. A side with only a bid or only an offer is refused with "loan_bid and loan_offer must be given together" (probe `q01_split_beside_partial.py`, exit 0), so the 6h row is reached only when a whole side is missing.
- No `_unpinned` or "no pinned wording" remains in either file.

**4. No frozen output changed.** `9f2b2f5` and `cba7f82` touch only the two files. The changes to `cases/` and the lease in the range come from the merges and LEAD's cherry-pick `5fc0d81`. The test only reads oracle values (`EXPECTED[...]`).

**5. Standing rules hold.** There is no stub, fake value or catch-all in the diff. The only new raise is the implicit unpacking `ValueError`, and no validated state reaches it.

## Probe exit codes
| Probe | Exit | Result |
|---|---|---|
| `p01_soft_hyphen_figure` | 0 | "REFUSED (fixed)" |
| `p09_first_figure_reachable` | 0 | real code refuses both spans; the relaxed rule accepts both |
| `p07_mutate` | 1 | survivors: bid exceeds offer, citation de-dup (both justified) |
| `p07b_mutate` | 1 | survivors: the two `source_authority` guards (justified) |
| `mutate_r5` | 1 | 44 of 44 fix-round and 6h mutants killed, plus the control; exits 1 only on 7 "ANCHOR x0" R9 mutants |
| `q01_split_beside_partial` (mine) | 0 | partial sides are refused |
| `q02_normalised_reads` (mine) | 0 | 8 of 8 cases as expected |
| `q03_quote_side_hyphen_wrap` (mine) | 1 | reproduces L-1 |

- `p01` and `p09` ran from copies in `cp8-fix1-review/adv-copy/`. Their `_common.py` hardcodes the live worktree, so the copies point at the exported tree; the probe logic is unchanged.
- The `mutate_r5` R9 mutants were added to the shared runner by the round 9 session after `cba7f82`. Their anchors do not exist at `cba7f82`, so they are out of scope.
- My first runs against the live worktree are superseded. Those three mutation runs exited 1, 1 and 0, and some may have copied the mid-edit tree. `q03`'s first run crashed with the `NameError` above.
- All my probes and outputs are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-fix1-review/`.

## Gates (run in the exported `cba7f82` copy)
All exit 0:
- pytest `tests/test_method_cp8.py`: 144 passed.
- `ruff check`, `ruff format --check`, and `MYPYPATH=src mypy --strict` on both files.

Not verified: I checked only that each L1 mutant is killed by some test, not that the test named for it is the one that kills it. Mapped dash or minus characters inside a figure on an edited page were argued from the regexes, not probed. The live worktree's round 9 working state was not reviewed and differs from `cba7f82`. I did not run `prose.issues` or `bare_figures` on the 6h strings myself; the implementer reports them clean.
