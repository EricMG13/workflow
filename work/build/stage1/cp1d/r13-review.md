## CP-1D round 13 adversarial review: 80cccb1 against d2cb626

**Verdict: FINDINGS.** I found two High findings and one Medium. All three are fail-open paths in which exactly-one passes on the wrong basis figure, and all are reproduced through the real accept path (`validation_issues` then `compute`). The rest of the change holds: W is unchanged, the `\Z` anchors are pinned, no frozen row moved, and there is no stub, fake value or catch-all.

### High

**H1: a joined comma run is hidden, so exactly-one passes on another figure in the quote.** Mark for LEAD: the ruling's own text gives this result.
- **Where:** cp1d.py:356-360 (`_SIGNED_AMOUNT`) feeding step 5 at cp1d.py:679-681.
- **Inputs (a01 accept path, proposed 3.00):** each of these reads `['2.5']`, gets no issue, and composes `T1D.2.a01.basis = accepted = 2.5`:
  - `Rates of 1, 2 and 2.5 cover the saving.`
  - `Fees of 1,25 and 2.5` (decimal comma)
  - `A saving of 1, 250 or 2.5`
  - `In 2025, 250 basis points gave a saving of 2.5.`
  - `-1,250 or 2.5`, `(1,250) or 2.5`, `( 1, 250 ) or 2.5`
  - `2.5 against 1,\n250 last year`
- **Regression:** at d2cb626 every one of these read three figures and was refused.
- **Your `1, 2 and 3 percent` case:** it reads `['3']` and is refused only by the bounds rule, because 3 equals a01's proposed 3.00. Below the proposed amount, it composes.
- **Correctly refused:** `1, 2, 3` reads `[]` and `between 10, and 2.5` reads two figures.
- **Ruling text broken:** LEAD's item 8 cost note says the list, the year-comma, the grouped figure and the decimal comma "are all refused", and the note is headed "failing closed".
- **Root cause:** LEAD's `p13_comma_space_join.py` (d) checks that cost only with the occurrence-style reader (`occurs("2", …)`), never with CP-1D's count.
- **Report misstatement:** the implementer's report calls `1, 2 and 3` reading `['3']` "refused". It is not refused.
- **Fail-closed alternative (A):** step 5 gives the pinned exactly-one text whenever the normalised basis quote holds `[0-9], ?[0-9]`. On a patched temporary copy the gate stays green (613 passed, 1 skipped) and every comma case is refused (p4). Its cost: a quote holding a "Month D, YYYY" date is refused too. d2cb626 also refused that.

**H2: a quote that starts or ends at the page's comma reads part of a comma run.**
- **Where:** cp1d.py:538, `at_start, at_end = needle[:start] in ("", "-"), needle[end:] in ("", ".")`. A leading `,`/`, ` or a trailing `,` is not treated as an edge, so `_COMMA_BEFORE` and `_CONTINUES` never run.
- **a01 accept path (citation clean, all compose):**
  - page `…annualised saving of 2,750 a year.`, quote `an annualised saving of 2,`: reads `['2']`, and accepted = 2;
  - the same with `2, 750` and `2,\n750` on the page;
  - quotes `,2.5 a year.` and `, 2.5 a year.` from `1,2.5`, `1, 2.5` and `1,\n2.5`.
- **Defect pack:**
  - `,250 per year.` on `1,250` reads `['250']`;
  - `, 250 per year.` on `1,\n250` reads `['250']`;
  - `The level is 25,` on `25,250` and on `25, 250` reads `['25']`.
- **Ruling text broken:** item 8 says "no figure is read from part of it", and LEAD says the join "closes `1,\n250` at the quote edge".
- **Status:** this is an incomplete in-round fix, not a predating defect. The CP-1D per-reader text names only `_cut` and `_CONTINUES`, and the implementer listed the end side under Not verified, so LEAD should confirm the fix.
- **Fix (B):** the edge sets become `("", "-", ",", ", ")` and `("", ".", ",")`. On the patched copy the gate is green and p2 exits 0.

### Medium (unruled, for LEAD)

**M1: a hidden point run lets exactly-one pass.**
- `A saving of .25 million, or 2.5 in total.` and `A saving of 1.2.5 or 2.5` both read `['2.5']` and compose 2.5. Both were refused at d2cb626.
- Item 7 explicitly accepts `section 4.2.1 a saving of 25`, so the multi-point form follows the ruling as written.
- The leading-point form is unruled. A fail-closed option is to refuse quotes holding `(?<![0-9])\.[0-9]`. That keeps the section-number acceptance; a multi-point run cannot be told apart from a section number.

### Checks that hold
- **Attack 2:** `.25`, `-.25`, `- .25`, `−.25`, `(.25)`, `( .25 )`, `1.2.5`, `1,2.5` and `1.2,5` all read `[]`. `section 4.2.1 a saving of 25` reads `['25']`.
- **Attack 3:** I fuzzed 3,000 pages, which gave 246,395 counted unsigned figures.
  - Plain and joined page readings never disagree where the needle occurs in both (0 cases).
  - No counted figure that is neither signed nor comma-edge is part of a longer page run.
  - All 7,468 violations are the H2 class.
- **Attack 4:** `_W_MINUS`, `_OPEN_PAREN`, `_CLOSE_PAREN` and the W sign group are byte-equal to d2cb626. Both `\Z` mutants are killed.
- **Attack 5:** the test diff removes 0 lines and adds rows only. No file under `cases/`, `methods/` or `docs/` changed. No stub or catch-all is in the diff.
- ruff check and format both exit 0.

### Probe exit codes
All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r13-review/` and were run with PYTHONDONTWRITEBYTECODE=1.
- `p1_e2e_hidden_run_failopen.py` (H1, M1): exit 1 on HEAD (12 quotes compose); exit 0 on d2cb626.
- `p2_comma_edge_bypass.py` (H2): exit 1.
- `p3_readings_fuzz.py` (attack 3): exit 0. Output is in `p3_readings_fuzz.out`.
- `p4_failclosed_alternative.py` (fixes A and B on a patched copy): exit 0. The gate passes there, and only the M1 point-run quotes still compose.
- `p5_point_runs_and_w.py` (attacks 2 and 4): exit 0.
- `impl/p_r13_mutants.py`: exit 0. The unmutated copy passes and all 13 mutants are killed.
- `impl/p_anchor_survivors.py`: exit 0.
- `impl/p13_quote_classes.py` (the implementer's lane-is-rule variant): exit 1. Its three failures are CP-1D control list, CP-1D control year comma (both H1) and a CP-3D case (another module).
- `lead/p13_quote_classes.py`: exit 1. These are the expected fidelity failures, since the lane is no longer the flags-off reference. Frozen readings moved: none.
- `lead/p13_comma_space_join.py`: exit 1. The only failure is the CP-8 `_labelled` literal `, ?` count (279), which LEAD narrowed away. Frozen triples moved: none. (c) shows 0 disagreements and (d) holds.
- Both LEAD probes point LANE at `wtcopy/`. `basecopy/` is d2cb626.

### Gate
Run once in `wtcopy/`, exit 0: 613 passed, 1 skipped.

Not verified: full suite and other modules; mypy (not run by me); the `cases/` recipe text, PINS.json and `methods/cp1d.md` notes; fixes A and B beyond this gate and probes p1 and p2; A's date cost on real, non-frozen quotes; separators not covered by any ruling (for example `1,​250`), which I did not grade; the fuzz is random, not a proof; a01's proposed 3.00 is inferred from the test docstring and the bounds result; GitNexus was not run.