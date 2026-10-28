# CP-2D rounds 5, 6 and 6f scoped review (mx-precise; controller-saved)

**Scoped review: CP-2D rounds 5, 6 and 6f, commit 3e099de (diff f0e4a6d..3e099de, cp2d.py and test_method_cp2d.py)**

## Verdicts
- **Spec verdict: APPROVE.** I checked every ruling in scope against `src/deploy_workflow/owners/cp2d.py` and found none applied wrongly. One reading goes to LEAD: 6f (e), item B below.
- **Quality verdict: APPROVE, with Low test-gap notes.** There is no High or Medium finding. The code gives the ruled output on every path I probed. Ten non-equivalent mutants and one ordering mutant survive the test file. Under the standing rules these ride with the next fix or the end batch.

## Gates (run from the target root)
| Gate | Exit |
|---|---|
| pytest `tests/test_method_cp2d.py` (136 passed, exit taken under pipefail) | 0 |
| `ruff check` on both files | 0 |
| `ruff format --check` on both files | 0 |
| `MYPYPATH=src mypy --strict` on both files | 0 |

## A. Rulings checked, wording byte for byte
- **D-1:** the facility-term rows have kind Gap (cp2d.py:733-737). "Facility schedule" is a Gap. The Financing, Facility currency (FX) and CP-1 cross-check rows are Limitation.
- **D-2:** the order is minimum cash, then known gap, then form 3, form 4 and form 5 (:1265-1294). GAP_FACILITY and GAP_OPERAND match the L5 and D-2 text. GAP_MISSING is gone.
  - I traced every way the funding gap can be missing. Form 5 is reached only when the revolver is the cause, so the fall-through at :1293 cannot give a false revolver claim.
- **D-3:** the 2D-c frame is used (:289-293). SCHEDULE_EMPTY and its own line match. An empty schedule with a known zero total debt gives known zero totals (:322-328). SCHEDULE_MISSING stays for an absent schedule.
- **D-4:** NEGATIVE_DEBT matches. ZERO_DEBT is kept for zero.
- **D-5:** the issue text matches. It is added after BASIS_ISSUE and the list is deduplicated.
- **L1:** all six strings match (:194-196, :700-703, :1127-1138).
- **L3:** exact spelling, negatives in brackets, no normalize.
- **L5:** MAT_FX matches.
- **A1:** `months_between` (:257-261) gives the largest n with `add_months(D0, n) <= maturity`, since n = m-1 is always ≤ the maturity and m+1 always lands after it. Inside-horizon stays `maturity <= add_months(D0, H)` (:405). Because `add_months` is monotone in n, months < H means inside and months > H means outside. The property test checks this.
- **A5:** there is no Stage 1 code path, only a docstring. cp2d.py has no default name or currency. The only "USD" is the comparison constant `CURRENCY` (:25). "Northbridge" appears only in the tests.
- **6f (d):** at :1251, MAT_CURRENCY applies when the first currency-problem facility in wall order (:1201-1202) has an unstated currency, and MAT_FX when it has a stated non-USD currency. The MAT_CURRENCY text matches the ruling.
- **6f items 1, 2(a), (b), (c), (f) and 3:** implemented as accepted.

## B. 6f (e): which string the drawings-undisclosed ratio (T2E.2.r09) gets
- **By its letter, 6f (e) gives the implementer's string.** It reads "REV_RATIO and RUNWAY_NO_DRAWINGS are … `Undrawn revolver not calculable: drawings undisclosed` and `Not calculable: revolver drawings undisclosed`". That pairs REV_RATIO, the name the implementer had reported for the ratio, with the undrawn string. It ends "Any other text is a defect."
- **2D-b does not give `Available liquidity not calculable: revolver drawings undisclosed`, so the implementer's alternative is wrong.** 2D-b names the first missing operand, which gives `Not calculable: RCF drawings is missing` (the drawn cell's own reason, :986). L1 already overrides 2D-b for the undrawn, available and runway cells, and it does not name the ratio.
- **The premise behind 6f (e) was false when it was written.** REV_RATIO was `Not calculable: available liquidity missing`. The pinned undisclosed-revolver case names the ratio's immediate operand (available liquidity), and that pattern points to the available-liquidity string.
- **Conclusion:** the rulings decide it by letter in favour of the shipped code (:536-537). The intent is open, so it is a one-line confirmation for LEAD, and the controller holds it. Whichever string LEAD picks, it is a one-constant change pinned at tests/test_method_cp2d.py:1251.

## C. Findings (all Low; the code is correct, the tests do not pin it)
Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2d-r6-review/`:
- `mutate_review.py` runs 19 mutants on a full copy of the worktree. Exit 1: 8 killed, 11 survived.
- `probe_untested_paths.py` checks the ruled behaviour on current code. Exit 0.
- `mutate_review_probe.py` applies each survivor and re-runs the probe. Every probe run fails under its mutant, so none is equivalent. Exit 0.

| # | Where | Surviving mutant(s) | Failure the tests would miss |
|---|---|---|---|
| L1 | cp2d.py:1201-1202, :1251 | K1, K2 | 6f (d)/(c) "first facility in wall order decides" has no two-facility test. Picking the last facility, or "any unstated currency", passes all 136 tests. With an unstated facility first and a EUR one second, the ruled text is MAT_CURRENCY; with EUR first, it is MAT_FX. |
| L2 | cp2d.py:1216 | K5 | 6f (a) limits the amortisation cause to facilities after the horizon. Dropping `f.maturity_date > horizon_end` survives. A facility inside the horizon with no amortisation, plus an undisclosed revolver, would then name a false facility cause instead of the revolver form. |
| L3 | cp2d.py:528, :530, :536 | K8, K9, K18 | With cash missing and drawings missing, 2D-b gives the cash reason on T2E.2.r07, T2E.5.r03 and T2E.2.r09. Removing the guards (so the L1 strings win) survives. |
| L4 | cp2d.py:1162, :1227-1232 | K12, K16, K17 | The form-4 operand order (cash first, formula order, operands before the schedule) is not pinned. Dropping `cash_bs` from the list survives. With cash missing, the claim would then fall through to the revolver form ("because the revolver is undisclosed") while the revolver is disclosed, which is a false claim. |
| L5 | cp2d.py:326 | K14 | D-3: only a known zero total debt makes an empty schedule a known zero. Widening the check to `<= 0` survives. |
| L6 | cp2d.py:1440-1442 | K11b (run in `mutate_review_probe.py`) | D-5 puts the issue after BASIS_ISSUE. Moving it ahead of BASIS_ISSUE survives, because no test raises both issues. |

None of these is a stub, a fake value or a catch-all. A missing value never becomes 0: `_total`, `_diff`, `_op` and `_schedule_gap` all carry the gap. The only try/except-like fall-through is the form-5 default, and I traced it as unreachable for a disclosed revolver.

## D. Implementer probes and mutants: exit codes vs their stated expectations
| Probe or mutant runner | Exit | Matches the report? |
|---|---|---|
| `mutate_r6.py` (full copy) | 0, 42 of 42 killed | yes |
| `mutate_r5.py` | 0, 39 of 39 killed | yes |
| `probes/r5_probe1.py`, `r5_probe2.py`, `r5_probe3.py` | 0 each | yes |
| `probes/r5_probe_sweep.py` | 0 | yes |
| `r5_confidence.py` | 0 | yes |
| `r5_prose.py` | 1 (6 non-claim hits, accepted under 6f item 3) | yes |
| `stage1-review-A/probe_cp2d_month_asymmetry.py` | 1 (asymmetry gone: 18 months, outside H=17, inside H=18) | yes; exit 1 is the expected result after the fix |

My outputs are saved as `*.out` files in the same `cp2d-r6-review` folder.

## Points for LEAD
1. 6f (e): confirm the T2E.2.r09 string (item B).
2. D-1: an unstated currency yields the label `Facility currency (<id>)` with kind Gap, because it goes through the term loop at :723-737. The FX row has the same label with kind Limitation. D-1 lists `Facility currency (<id>)` as Limitation and `Facility <term> (<id>)` as Gap, so the unstated case matches both patterns. The shipped split is consistent with D-1, but you may want to confirm it.
3. A1 for CP-3C: nothing in this worktree imports `cp2d.months_between`, so the CP-3C lane must adopt it itself, as the implementer also noted.

Not verified: real CP-1 heads, T4.18 row facts and the Stage 2 A5 reader (there is no Stage 1 code for A5); L4 "shows both" through T2E.9 (Stage 2); A1's effect on CP-3C; rendering of the T2E.7 Gap rows; any test suite other than tests/test_method_cp2d.py; LEAD's oracle commits 4e82ef1 and 4e3af50 (excluded by the brief).
