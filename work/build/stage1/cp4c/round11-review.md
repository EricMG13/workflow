## CP-4C round 11 review (target ed1a721, round diff 04ab3d5..ed1a721)

**Verdict: APPROVE.** Every item I was asked to check holds: B2, B3, B6, Q6, Q7, N1, N2, the M1 riding test, and A-1 unchanged. All four gates exit 0. The diff adds two Low findings (both about test strength, and both fail closed) and a few Info notes. None reopens review.

I exported both commits with `git archive` and ran all probes and mutants against those copies with `PYTHONDONTWRITEBYTECODE=1`:
- /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/old
- /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/new (byte-identical to the target's two files)

The target was not touched. HEAD is ed1a721, the tree is clean, and no file in it is newer than my gate script. The diff changes nothing under `cases/` or `src/deploy_vii`.

### Per ruling or decision

**B2 holds.** Probe: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_b2.py. Exit 0 on new; exit 1 on old, which raises "words the missing and conflicting states only".
- The probe reads the ruled strings from the rulings file itself. Both match byte for byte:
  - the T4E.2 claim reason `Not calculable: total debt is not applicable in CP-1 for LTM Q4 25: 2025-01-01 to 2025-12-31`, on a `missing` cell;
  - the own line `The claim of Senior secured term loan is not available: … ; every recovery at or below its rank is Not calculable.`, which appears exactly once.
- The cp1_references copy equals CP-1's fact unchanged: status `not_applicable`, limitation verbatim.
- The fixture payload gets no validator issue. The positive payload is refused with judgment issues, not a raise.
- Another period raises ValueError "is not for LTM…". So does an absent fact, in both `compute` and `payload_issues`. A known debt with no amount still raises (cp4c.py:541).

**B3 holds.** cp4c.py:934-938 uses `prose.bare_figures` with the same `names` that compute builds at :2333. It sits in the #9 per-field step, after the empty and one-line checks. The issue form matches the pinned v15 frame (`<path>: Bare figure: <token>`).
- Can a name that passes the validator still make `compute` raise on a figure? I found none.
  - /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_b3_fuzz.py: exit 0 on every run. It covered 300, 3,000, 2,000 and 2,000 names, with the frozen issuer and with the issuers `3M 2 Holdings` and `Group 1 of 2`, each name tried as `claims[1].name` and as `valuation[0].label`. There were 0 cases where the validator passed and compute raised.
  - On old, the same probe exits 1 with 312 such cases, so it discriminates.
  - /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_b3_pairs.py fuzzes two classes together, both in the v01 break, so the T4E.7 "A and B" join is exercised: 2,500 pairs, exit 0.
- Why it holds: in every claim, a name sits between non-alphanumeric boundaries, and no `prose.LABELS` pattern can start in CP-4C's fixed text. Labels are lower-cased in every claim (:2194, :2205, :2220), and the validator lower-cases them too.
- I did not re-raise reserved characters (B7).

**B6 holds.** Probe: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_b6.py. Exit 0 on new, with 61 checks over 5 cases and 3 states; exit 1 on old, which lumps the states as "missing".
- The cell stays `missing`, with the ruled frame for each state word, and gets no own line.
- EV's reason comes first wherever EV is unknown (gap v03, and the fixture_ebitda_missing valuations).
- The Q3 raise stays: a known EBITDA with text and no amount raises ValueError.

**Q6 holds.** Probe: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_q6_q7.py. Exit 0 on new; exit 1 on old, where exactly the Q6/Q7 cases read.

The four cases you asked for:
- **Whole line:** reads 10.
- **Cell boundary:** label only, one figure, and ending at the Q4 cell all read 10.
- **Single space inside a cell:**
  - `Other current` and `Other current ` are refused with the #11 text;
  - a single trailing space after a figure cell is refused with #11;
  - a single space between cells is not on the page, so it gets v04;
  - a single space inside a figure cell of the line is refused with #11.
- **Trailing two spaces:** after the label, or after the Q4 cell, the quote is refused with #11 (the empty last quote cell). The whole line plus two spaces is not on the page, so it gets v04.

The three side-effect refusals all fail closed: each gives the #11 issue, with no raise.
- `Other  9  ` with an empty last cell.
- A line whose last cell has one trailing space. On that same line, a quote that stops at the Q4 cell still reads 5.
- A quote carrying the CR of a CRLF line. On the same page, the quote without the CR reads 5.

No frozen read changes:
- /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/probe_prefix_compare.py: exit 0. It takes every character prefix of every frozen page:4 line, under every column, in all 5 cases: 45,060 reads.
  - All 6,600 whole-cell prefix reads are identical between old and new.
  - The 29,730 reads that differ are all cut-cell prefixes, which new refuses.
  - No cut-cell prefix still reads.
- The implementer's copy, cp4c-r11/probe_m1_cited_row.py `--expect`, exits 0. The fix-1 original exits 1 with 7 mismatches, and those are exactly the 7 intended changes: `Pr`, the cut figure, bare CR, U+2028 and the three side effects.

**Q7 holds.** Same probe. Each of the 9 `str.splitlines` boundaries (`\r \x0b \x0c \x1c \x1d \x1e \x85    `) inside a `\n`-line is refused with #11. That holds for a whole-row quote, a quote ending at the Q4 cell, and a hidden later row. A trailing `\r` is stripped and the line reads 5. A CRLF duplicate of an LF line counts as one line (Q5).

**N1, N2 and the M1 riding test hold.** /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/mutants_review.py: exit 0. Each named test, run alone, kills its mutant:
- N1 `<` by `test_n1_…`;
- Q5 list by `test_n2_identical…`;
- `+5.00` and `.5` by `test_n2_…[+5.00]` and `[.5]`;
- `quote in x` by `test_m1_a_line_holding…`.

The same script also kills these:
- a `not_applicable` state word with an underscore;
- `not_applicable` worded as "missing";
- a Q7 check that looks for bare CR only (killed by `[U+2028]`).

**A-1 unchanged: holds.**
- probe_frozen_reads.py, old against new: exit 0. 5 cases, 1,325 cells and 1,020 full-line reads; 0 keys differ.
- probe_alloc_reference.py at 500 per seed: exit 0, 0 mismatches on all 6 seeds.
- probe_hypothesis_big.py at 300 examples, seeds 1 and 2: exit 0, 10 of 10 pass.
- The outputs are a1_alloc_reference.out, a1_hypothesis_big.out and frozen_reads.out in the review folder.

**Implementer's mutants.** I reran cp4c-r11/mutants.py against the new export: exit 0. Of 39 mutants, 37 are killed and 2 are the justified equivalents (`exact_sum_without_80_floor`, `no_balance_invariant`). Output: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/mutants_implementer_rerun.out

### New findings (introduced by this diff)
- **L1 (Low, test strength): B3's "same `names` compute uses" is not pinned.** cp4c.py:937 and tests/test_method_cp4c.py:1519-1534.
  - The mutant `bare_figures(spelt)`, with `names` dropped, survives.
  - The frozen issuer name has no digit, so no test can tell the two apart.
  - The mutant would over-refuse, so it fails closed.
  - Fix: one test with an issuer name holding a digit, used in a class name.
  - Probe: mutants_review.py, `b3_names_dropped`.
- **L2 (Low, test strength): B3's per-path spelling is not pinned for class names.** cp4c.py:935 and tests/test_method_cp4c.py:1529.
  - The mutant `spelt = text.lower()` survives. Under it, the validator would refuse class names such as `Term Loan B-2` or `Q1 Notes`, which `compute` accepts, because class names are not lower-cased in claims.
  - The mutant fails closed.
  - Probe: mutants_review.py, `b3_lower_class_names_too`.

### Info (no action)
- **Two pinning gaps that predate this diff.** The behaviour is correct in both (probe_b2 and probe_b6 exit 0), but neither mutant is killed:
  - `b2_debt_known_without_amount_settles` (cp4c.py:541): the diff rewrote this raise, but it had no test before either.
  - `b6_cp1_reason_before_ev` (cp4c.py:1619): EV-first has no test with both reasons unknown.
- **Q6 side effect 1 lives only in the probe copy.** The mutant `q6_drop_empty_last_cell` survives. The side effect is not ruled, and either behaviour reads the right row.
- **`rstrip` against `removesuffix`.** The mutant `q7_strip_every_trailing_cr` survives. It differs only on `\r\r` endings.
- **Lower-case token in the label issue.** The B3 label issue echoes the token in lower case (`fy2026`), not as the analyst typed it. That is the token `compute` would see. Record it in methods/cp4c.md, as the report says.
- **Standing rules.** No stub, fake value or catch-all was added; the diff adds no `try`/`except`.

### Gates (target root; exit codes)
| Gate | Result | Exit |
|---|---|---|
| pytest `tests/test_method_cp4c.py` | 183 passed | 0 |
| `ruff check`, both files | clean | 0 |
| `ruff format --check`, both files | already formatted | 0 |
| `MYPYPATH=src mypy --strict`, both files | clean | 0 |

To keep the target clean I added `--no-cache` to ruff, put the mypy cache in scratch, and set `PYTHONDONTWRITEBYTECODE=1` and `HYPOTHESIS_STORAGE_DIRECTORY`. Output: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11-review/gates.out

Not verified: real Stage 2 packs (whether CRLF, form feed, U+2028 or issuer names with digits occur in real spans); B7 reserved characters (excluded); the B3 fuzz is bounded (a fixed fragment vocabulary, 11,800 samples, positive context only), not a proof; whether B3 over-refuses names that `compute` would accept (not measurable, because `compute` reruns the validator); A-1 probes ran only at reduced counts (500 × 6 seeds; 300 × 2 seeds); mutmut (hand mutants only); the fix-1 reviewer's mutants_fix1_review.py was not rerun (its sites are stale, per the report); the full repo suite and other modules.
