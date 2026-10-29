# CP-3D quote fix + 6h review (mx-precise; controller-saved)

## CP-3D review of 22e9166 and 0b0835f (diff c8dbd05..0b0835f, cp3d.py and test_method_cp3d.py)

**Spec verdict: APPROVE.** **Quality verdict: APPROVE, with one Low.** There are no High or Medium findings.

### Spec
1. **Every quote read after a match uses the normalised text.** Confirmed by reading the file. The reads after `quoted` at cp3d.py:414 are:
   - `_token_once` (:177), which serves the level (:444), margin and amortisation (:515) and the reference-rate level (:579);
   - `_labelled` (:424), called at :451 and :454;
   - `as_of_text` (:473);
   - maturity `date_text` (:539);
   - `rr.name` (:571-573);
   - `inst.name` (:638-640).

   All of them run on `normalise(...)`. Nothing else reads quote text: `cited_pages`, `_trace` and `terms_period` use only source_id and locator. `_PUBLISHED` reads the page side, which is out of scope.
2. **Normalising can't validate a value the page doesn't state.** This holds for figures, labels and dates, and fails narrowly for names (Low 1). Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-quote-review/`:
   - `probe_reads.py` (exit 0). Each of the following is refused: a soft hyphen at a token or label edge, a soft hyphen plus newline, NBSP between label and figure, a whitespace split not on the page, and a margin through a wrap with no hyphen on the page.
   - For tokens, the wrap join only drops whitespace after an ASCII `-`. A `-` is not a digit, `.` or whitespace, so tokens and `\bkind\s+` labels read the same in the plain and joined forms. Dates hold no hyphen.
3. **Check order and wording.**
   - The level order is still numeral (:440), occurrence (:444), leading zero (:447), label (:450-456), decimals (:457), bound (:460). Rulings 6g and 6h say the leading zero comes before the label; that holds.
   - Recovery (:597-600) uses the existing `_NO_LEADING_ZERO` wording with the `recovery: percent_text <x>` frame, before the shape and bound. Recovery has no quote, so there is no occurrence step.
4. **Each new test fails without its change.**
   - `revert_mutants.py` exit 0: the control passes, and all 6 mutants are killed by their own cases.
   - `mutants_6h.py` exit 0: all 3 mutants are killed.
   - Caveat: both runners need the worktree path as argv[1]. Run without it, they raise IndexError, and a piped `tail` hides that exit.
   - The two 6h label-order tests passed before the change. They are guards, but the `level_check_after_label` mutant kills them.
5. **No pinned refusal or frozen output changes.** The test diff only adds, at :1125 onward. The positive-oracle accept tests compare tables and claims, and 234 tests pass.
6. **No stub, fake value or catch-all** in either commit.

### Findings
**Low 1. Names can validate a whitespace variant the page doesn't print, through `quoted`'s quote-side wrap join.**
- Where: cp3d.py:638-641 (`inst.name`) and :571-574 (`rr.name`).
- Scenario: the page prints `Northbridge Term-Loan` and the quote is `Northbridge Term-\nLoan senior`. `quoted` matches this through the joined needle (task 7.11), but `normalise` reads it as `Term- Loan`.
- Result: the name `Northbridge Term- Loan`, which the page never prints, is accepted and rendered at r05/T3E. The name the page does print, `Northbridge Term-Loan`, is refused with `instrument: name does not occur in the quote`.
- When it appeared: at c8dbd05 the raw read refused both names, so the acceptance comes in with 22e9166. The false refusal was there before.
- Impact: this is a one-space difference in a name, not a figure. A page-side wrap would legitimately normalise to `Term- Loan` too.
- Possible fix: read names against both quote readings, plain and wrap-joined (`quotes._needles` is private).
- Probe: `probe_wrap.py` in the same folder, exit 1. It exits 1 when `Term- Loan` is accepted. Its case C1 shows that an ASCII name accepted against an en-dash page is expected behaviour.

**Info 2 (older than this change, for the owner, not counted). A quote that starts or ends mid-token validates part of a page figure.**
- Where: `_token_once` (:173-177) checks token boundaries inside the quote only.
- Scenario 1: quote `25 basis points.` on a page with `margin is 425 basis points.` gives bps_text 25 with no issues.
- Scenario 2: quote `0 percent.` on a page stating `10 percent` gives zero amortisation with no issues, which selects the simple margin convention.
- When it appeared: raw and normalised reads are identical here, so it predates both commits.
- Probe: `probe_reads.py`, cases D1 and D2, which print `[]`; the script exits 0.

**Info 3.** A recovery `percent_text` such as `05abc` now gets the leading-zero issue instead of the bound issue. The implementer noted this; it matches the other fields, and no test covers it.

Noted only, as briefed, not counted: the sign is not read (`−0.25` validates as +0.25), and the `Published` date is read from the raw page.

### Gates (from the cp3d-stage1 root)
- pytest `tests/test_method_cp3d.py`: 234 passed, exit 0.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.
- Runners: `revert_mutants.py <worktree>` exit 0; `mutants_6h.py <worktree>` exit 0.

Not verified: I didn't run the two commits' mutants at c8dbd05 myself; I relied on the runners' control and mutant runs. The wrap-join gap is probed only for `instrument.name`; `rr.name` is reasoned from the same code. There's no probe on real pages with hyphen wraps. I didn't run `prose.issues` or `bare_figures`. The full suite and Stage 2 weren't run, as briefed.
