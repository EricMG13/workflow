## Verdict: CHANGES REQUIRED

All seven finding ids hold. Every behaviour I probed matches round 11, so no code defect is open. One Medium is open, and it is test strength only: two boundary mutants survive on the new B1 code, so the tests do not pin the D0 boundary the brief asks about. The fix is tests only.

Target: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287` at b9972fd. Over the lane tip b6c3392 it adds only `cp3c.py` and its test. Its tracked files and HEAD are unchanged after the review.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-fix1b-review/`, called `<R>` below. They import from `<R>/probe_root/`, a full copy of b9972fd, through `<R>/plib.py`. Mutants ran on the full copies `mutcopy`, `mutcopy2` and `mutcopy3`, and each was restored by sha.

## Per finding id

**M1 → round 11 B1: holds.** `probe_b1_dependants.py` exits 0 and `probe_b1_slot.py` exits 0. The implementer's `probe_past_maturity.py` and `probe_negative_amort_months.py` also exit 0.
- **Months and inside flag:** both are `Gap("Not calculable: facility term-loan maturity date is before the balance date")`. The date stays known and sorts first in wall order (its C-4 place).
- **Dependants (two-facility case, both amortising):** all take the exact reason:
  - the facility's amortisation, balloon, resources, applied, need and cover (T3D.1 r01 c5-c10);
  - the other facility's resources, applied, need and cover (r02 c7-c10). Its own amortisation and balloon stay known;
  - T3D.2 r01, r02, r03, r04, r06, r08 and r09, and the repriced T3D.3 cells.
- **Stays known:** total principal, shares, T3D.4 claims, T3D.5 Base and the nearest date (2025-06-30).
- **Copies:** shown verbatim (-6, `Yes`), with no wall cross-check line.
- **Own line and cause:** the own line occurs once with the exact text. Its ledger row at the same index is `("Facility maturity date (term-loan)", "Limitation")`. The NEED-01 cause is exact.
- **Same slot as an unstated date:** across 384 one-facility combinations (currency, principal, amortisation, ranking, horizon, cash, flow, minimum cash), the cells equal the unstated-date cells with the reason swapped. The only exception is the nearest date, which stays known.
- **On D0:** months are 0, inside is True, every row cell is computed, and no B1 line or reason appears anywhere.
- **Negative months:** none can form a figure.
  - A daily sweep from D0-400 to D0+400 found no negative months.
  - `months_from` is called only in `_facility`'s branch for a maturity on or after D0 (`cp3c.py:832`).
  - `wall_position` and `compose_refinancing` have no caller outside cp3c and its tests. The unguarded `compose_refinancing` with hand-built operands predates this diff.

**M2 → round 11 Q3: holds.** `probe_q3_frames.py` exits 0. It composed 153 cases with ids `tl2`, `tla1` and `2029`, including 121 mixed-kind pairs, and checked all 9 frames in 316 claim checks. The implementer's `probe_digit_id.py` exits 0. Their `prose_probe.py` also exits 0, but only when run as its docstring says (from a copy root with `PYTHONPATH=src:.`); from its own directory it exits 1 on `ModuleNotFoundError`.
- **No ids:** no NEED-01 or LME-01 text or resolved text carries a facility id.
- **Frame by kind:** the cause is set where each gap is made (`:400`, `:694`, `:810`, `:814`, `:829`), and `_because` (`:1698-1703`) reads `Gap.cause`. The only reason comparisons left are `:1728` (minimum cash, the pinned form) and `:1762` (NM_EBITDA, B4 as built). Neither chooses a facility frame.
- **`names=`:** gone from `prose.check` (`:1682`).
- **Mismatched frames:** none found. My frame-swap mutants R01-R07 are all killed.

**M3: holds.** A13, A18 and A25 are killed in both runners. A39's site is gone (PATTERN x0). Its replacements are all killed: the implementer's Q3a, and my R01-R07.

**L1: holds.** `probe_l1_l2.py` exits 0.
- With claims of 30, 50 and -10, Base is 50, which is the middle rank. A rank gap gives that gap.
- A16', L1a and L1b are killed.
- The implementer's `probe_negative_principal.py` exits 1 only on its B6 parts, which stay as built.

**L2: holds.** `probe_l1_l2.py` exits 0.
- `_CONTEXT` is `Context(prec=60)`.
- Computing under a caller context at prec 3 changes no cell.
- The three pack cases are identical at prec 28 and 60.
- 5 × 7 / 12 is stored with 60 digits.
- R16 (back to prec 28) is killed.
- `probe_precision.py` exits 1 only on the 3E-59 conservation residue, which no finite precision removes.

**Round 11 B2: holds.** `probe_b2_order.py` exits 0 over 1944 combinations.
- **Covered:** currency (USD, none, EUR), maturity date (dated, undated, pre-D0), principal, amortisation, secured status and seniority (stated, NOT_STATED, missing), wall row (consistent, months differ, months missing) and horizon (stated, missing).
- **Text, label and kind:** every line matches the ruling.
- **Order:** currency, maturity date, principal, amortisation, secured status, seniority, then wall rows. The unmatched lines and then the path lines come after. No "states no flag" line appears without a horizon.

**Round 11 B5: holds.** `probe_b5_blank.py` exits 0 over 70 checks.
- The blanks tested are `""`, `" "`, `"\t\n"`, NBSP and an em space, on every II path of all three pack submissions, with and without other issues present.
- Each gives exactly the issue list that `None` gives, with the pinned text at the same position, and `compute` refuses it.
- A non-II blank keeps its "only an II" issue.
- B5a and R15 are killed.

## New findings (introduced by this diff)

**N1 (Medium, test strength). Two B1 boundary mutants survive. Probe: `review_mutants.py`, exit 1.**
- **R08, `cp3c.py:1533`, `<` → `<=`:** a maturity exactly on D0 would get the "before the balance date" Limitation line. `test_b1_a_maturity_on_the_balance_date_is_zero_months` (`tests/test_method_cp3c.py:1367-1370`) asserts only `months == 0`. That comparison is a second, separate date check, which B1b does not reach.
- **R09, `cp3c.py:827`, boundary moved to the 1st of D0's month:** maturities from 2025-12-01 to 2025-12-30 would then form -1 months and sign-flipped figures, which is M1's defect class. The only pre-D0 test date is six months before D0.
- **Code today:** right in both states (`probe_b1_dependants.py`, checks 2 and 3 and the sweep, exit 0).
- **Fix:** in the on-D0 test, assert there is no `Facility maturity date (<id>)` row and no B1 reason. Add a D0 - 1 day case that must be the B1 gap.

**N2 (Low, rides with N1). R12 survives.** No test covers a pre-D0 maturity with the CP-2D horizon missing: a mutant that skips the B1 branch when the horizon is a gap goes unnoticed. The code is right (`probe_b1_dependants.py` check 4, `probe_b1_slot.py`). Probe: `review_mutants.py`.

**N3 (Info).** At `tests/test_method_cp3c.py:1620`, `blank or None` sends `None`, not `""`, so the `""` parameter repeats the `None` case. The behaviour for `""` is right (`probe_b5_blank.py`).

## Mutants
- **Implementer's `cp3c-fix1b/run_mutants.py`** (on `mutcopy`; output `impl_run_mutants.out`): exit 1. Everything is killed except:
  - A19 and A44, Info as in round 1;
  - A39, PATTERN x0 (its site is gone).
- **My `cp3c-adversary/mutants.py`** (on `mutcopy2`; output `my_mutants.out`): exit 1. Everything is killed except:
  - A19 and A44, Info;
  - A16 and A39, PATTERN x0 (both sites moved; A16', Q3a and R01-R07 replace them).
- **New `review_mutants.py`** (on `mutcopy3`; output `review_mutants.out`): 17 mutants, 14 killed. R08, R09 and R12 survive, exit 1.

## Gates (target root; no bytecode written; mypy cache in `<R>/mypycache`)
- pytest `tests/test_method_cp3c.py`: 166 passed, exit 0.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.

There is no `except`, stub or suppression in either file. `_because`'s `TypeError` is an invariant raise and is unreachable. B3, B4, B6 and Q2(f) were not re-raised; `probe_empty_register.py` and `probe_burden_collision.py` exit 0.

Not verified: Stage 2 MC-2 passing only the issuer name; the round 11 blank-text rule for CP-3C's other `Text` fields (it belongs to the shared class test, outside fix 1); the CP-2D side of B1; the fixture cases beyond the three pack cases at prec 28 against 60 (the gate's frozen tests cover them, my probe does not); the builder (not run); mutmut (all mutants are hand-written); the full suite; GitNexus `detect_changes`; that `_because`'s `TypeError` is unreachable (judged from the code, not tested).
