**Verdict: APPROVE (spec PASS, quality PASS).** I found no High or Medium findings. There are two Low findings (one of them a question for LEAD) and three Info notes. I edited nothing and committed nothing.

Target: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp3d-stage1` @ eb4b3cb, diff 864ffe3..eb4b3cb.
- The diff touches only the two allowed files: cp3d.py +104/−22 and test_method_cp3d.py +273/−0.
- That is 399 changed lines, under the 800 ceiling.
- No existing test line was removed or edited, and the worktree is clean.

## Spec verdict, by ruling id

**1. B1: PASS.**
- Code: `cp3d.py:235-254` (`_whole_on_page`), `:223` (`_cut`), `:213` (`_occurrences`), `:508` (`occurs`).
- It covers every occurrence, including overlapping ones, of both needles (the normalised quote, and its joined reading when the quote is wrapped) in both page readings.
- The start edge refuses a digit, `.`, a round-10 minus and a closed `(`. The end edge refuses a digit, `.` plus a digit and a closing `)`. Both fire at the pinned occurrence check, from all three callers (`:536`, `:607`, `:672`).
- **The "or only a sign" simplification:** I tried to refute it and could not.
  - Probe `<S>/cp3d-class-review/p_b1_sign_edge_fuzz.py` (exit 0) compares the tip against a literal reading of the ruling. The literal reading counts `-` and `+` as a sign, and a broader variant also counts `(`.
  - It ran 333,366 quote/page/value triples that `quoted` accepts. Quotes were raw substrings plus whitespace-collapsed, wrap-joined and wrap-inserted forms. There were 0 differences.
  - The reasoning holds: whatever sign precedes the figure is inside the quote, so it is also the page character before the figure. A leading minus is already not a token (`_tokens`), and `+` or an unclosed `(` is never a cut.
- **`is -\n25` (a minus, then a line break, then the digits):** this is a question for LEAD, not a defect under round 10/11 (finding L1).

**2. B3: PASS.**
- `_name_occurs` (`cp3d.py:257-260`) is used for `inst.name` (`:731`) and `rr.name` (`:663`), matching the ruling's caller list.
- The only other text read from a quote is `as_of_text` (`:565`) and `maturity.date_text` (`:631`). Both are dates, and `parse_date` requires the exact `Month D, YYYY` form, so a `- ` spelling is refused already. `kind`, `aspect` and `category` are fixed-list fields, not quote reads. No other value needs B3.

**3. Blank text: PASS.**
- All 21 analyst text fields get `<path>: empty text`: 2 names, 12 absence fields, `recovery.rationale`, 4 `technicals[i].text`, the limitation and `summary.text`.
- The check is the first step of `_Issues.analyst_text` (`cp3d.py:488-490`). The early return drops nothing, because blank text cannot hold digits or a prohibited conclusion; the mutant without the return survives, so the two are equivalent.
- **Frozen order is unchanged.** No frozen CP-3D string is blank (I grepped `cases/cp3d-owner/*.json` for `""` and `" "`: no hits). The tests diff removes no line, and all 650 tests pass.
- The double issue for a blank name is confirmed: `"\t "` gives `instrument.name: empty text` followed by `instrument: name does not occur in the quote`, and `" "` gives only the first (probe `p_wrap_minus_and_edges.py` check B). This order is new and no frozen case pins it.

**4. B2 riding item: PASS.**
- `accounting` (`cp3d.py:195`) applies the parenthesis exclusion only when `value_text` starts with a digit.
- `<S>/cp3d-r10-review/p_tip_sign_rule.py` exits 0. Check C now gives `margin: bps_text -425 <_SHAPE>`. Output is in `<S>/cp3d-class-review/p_tip_sign_rule.out`.

**5. Frozen cases, stubs, catch-alls: PASS.** No frozen case changed, and I found no stub, fake value, catch-all or `try/except` in the diff.

## Findings

- **L1 (Low, question for LEAD; not a defect against the rulings): sign loss on a page minus followed by a line break.** `cp3d.py:179-198`, `:235-254`. Probe `<S>/cp3d-class-review/p_wrap_minus_and_edges.py`, checks W.
  - The page is `The reference rate is -\n0.25 percent today.`, and percent_text is `0.25`.
  - These quotes are accepted with no issue:
    - the full line, as printed;
    - the same line with `- ` in place of the line break;
    - `rate is -\n0.25 percent`.
  - The shorter quote `0.25 percent today.` is refused, because B1 reads the joined page `-0.25`.
  - Round 10 reads the sign on `normalise(quote)`, where `- 0.25` is not a sign, so the code follows the ruling text. LEAD's round 11 "Not verified" says this case "was not examined".
  - It is money-adjacent and inconsistent: quoting more of the page gets past the sign check. Raise it with LEAD.
- **L2 (Low): the "accept" side of B3 is not pinned by any test.** `cp3d.py:260`, tests at `tests/test_method_cp3d.py:1561`. Probe `<S>/cp3d-class-review/p_survivors.py`, exit 0; the tip behaves correctly.
  - Two reviewer mutants survive:
    - dropping the `hyphen_wrapped(quote)` gate;
    - widening `"- "` to `"-"`.
  - The inputs the tests should pin:
    - an unwrapped quote that prints `Acme first- priority Term Loan` must keep that name;
    - a wrapped quote must keep `Acme Term Loan B-2`.
  - Add both as accepted cases; they can ride with the next change.
- **I1 (Info): overlapping occurrences are unpinned.** `cp3d.py:213-220`. The "non-overlapping occurrences" mutant survives. `_whole_on_page("5", "5 .5", "x 5 .5 .5")` is False at the tip, which is correct (`p_survivors.py`). The input is contrived.
- **I2 (Info): which refusal a parenthesised signed figure gets depends on where the quote is cut.** Probe `p_wrap_minus_and_edges.py` check E.
  - Quoting `(-425)` from inside the line gets the shape refusal, as ruled.
  - An edge-cut quote, `-425) basis points.` or `Facility margin is (-425`, gets `does not occur` instead.
  - The figure is refused either way and no sign is lost.
- **I3 (Info): two of my mutants are equivalent.** "B3 name not normalised" makes no difference, because the name must already be a substring of the normalised quote. "Blank: no early return" makes no difference, as explained under item 3.

## Probe and mutant exit codes
All under `<S>/cp3d-class-review/`; each `.py` has a matching `.out`.
- `p_tip_sign_rule.out` (the r10 probe re-run): exit 0.
- `p_b1_sign_edge_fuzz.py`: exit 0, 0 differences.
- `p_wrap_minus_and_edges.py`: exit 0. Its W and E checks only print their results.
- `p_survivors.py`: exit 0.
- `mutants.py` (the implementer's script plus 12 reviewer mutants, all marked `R`): exit 1, which is expected. Run from a full temporary copy with PYTHONDONTWRITEBYTECODE=1.
  - The unmutated copy exits 0, and all 22 of the implementer's mutants are killed.
  - Of my 12: 7 are killed. The 5 that survive are the two B3 accept cases (L2), name not normalised (equivalent), non-overlapping occurrences (I1) and no early return (equivalent).
  - My first "no edge gate" mutant was invalid (an indentation error, pytest exit 2). I corrected it and it is killed.

## Gates (all exit 0)
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp3d.py`: 650 passed, exit 0.
- `ruff check` on both files: 0.
- `ruff format --check` on both files: 0.
- `MYPYPATH=src mypy --strict` on both files: 0.

<S> = /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad

Not verified: the full suite and `tests/test_defect_classes_selfcheck.py` were not run. The fuzz used a small alphabet and short pages, not real pack pages. B1 was not checked on date texts (`as_of_text`, `date_text`), because the ruling scopes it to figures. No pages outside CP-3D's own frozen set were checked, and GitNexus `detect_changes` was not run (I have no MCP tools).
