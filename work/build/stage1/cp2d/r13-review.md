**CP-2D round 13 review (7f2a9a2 against d2cb626): FINDINGS.** Spec: one Medium finding that breaks the ruling, plus one Medium that is unruled and goes to LEAD. Quality: two Low findings.

**Spec**

- **Item 1 holds.** My probe checked every cell of the 3 built cases against the ruled rule on its own terms:
  - 110 known numeric cells, each with the right period;
  - the 5 gap value_class keys, exactly the ruling's;
  - every cell has a class;
  - a copied gap keeps `cp1_operand`, `cp1_unit` and class (cash_bs probe).
  - A sum with differing periods raises `CP-2D: operands of T2E.1.r05 differ in period`.
- **Item 3 holds:**
  - the `Operand` shape;
  - a copy keeps CP-1's status with its limitation verbatim;
  - conflicting spells `∅ G7`, not_applicable `∅ G7 n.m.`;
  - the state reasons and the GAP_OPERAND text match the ruling word for word;
  - the first gap is in formula order.
- **Money trace.** Every arithmetic site reads through `_op` or `_amount`. A non-known operand has no amount (`__post_init__`), so it never reaches arithmetic and is never read as 0.

**Findings**

1. **Medium (ruled): a conflicting revolver gives the runway a false reason.** cp2d.py:636, used at :555.
   - Input: `fixture_burn` with `rcf_commitment=Operand("conflicting", None, None, L)`, or `rcf_drawn` conflicting.
   - Output: T2E.3.r09 has the reason `Not calculable: revolver undisclosed`. T2E.2.r05/r07 and T2E.5.r02/r03/r07 in the same result correctly say `Not calculable: RCF commitment is conflicting`. With drawings conflicting, the runway still blames the commitment.
   - This breaks ruling :1988-1991 ("Dependants stay gap … `Not calculable: <label> is conflicting` / `is not applicable`").
   - Fix: when `undrawn` is an `OperandGap`, use its reason.
   - Probe: `<S>/cp2d-r13-review/probes/r2_conflicting_revolver_prose.py` (exit 1, reproduces).
2. **Medium (unruled, LEAD): you asked whether the undisclosed-revolver wording must change on a conflicting revolver.**
   - The ruling words only GAP_OPERAND, so these strings are unruled: LIQ-01 (`LIQ_UNDISCLOSED` :1361, chosen at :1489-1490), GAP-01 (`GAP_UNDISCLOSED` :1369) and the own limitation `FUNDING_GAP_ON_CASH_ALONE` (:908-914).
   - For a conflicting commitment or drawings, all three state "the revolver is undisclosed", which is false. 4 hits in each of the two variants (same probe).
   - Fail-closed option: LEAD words a state-word form ("…needs the undrawn committed revolver, which is conflicting"), in the GAP_OPERAND frame.
3. **Low: three money clauses are unpinned. The code is correct today.** Reviewer mutants in `<S>/cp2d-r13-review/probes/r3_review_mutants.py` (exit 1) survive:
   - **R1:** `_absent` (:275-278) reads conflicting as undisclosed. No test covers a conflicting or not_applicable revolver copy (T2E.2.r03/r04).
   - **R3:** `_schedule_gap` (:423) reads a non-known `total_debt_bs` as 0. With `facilities=()`, the schedule becomes a known zero and the funding gap gets computed.
   - **R4:** `_amount` in `check_cp1_totals` (:737-745) reads a non-known T4.10 metric as 0.
   - (R5 is an equivalent mutant.)
4. **Low (unruled, LEAD): a sum copy takes one operand's status.** `equity_issuance` conflicting makes T2E.1.r05 (`cp1_operand` "equity_issuance+equity_repurchases") state `conflicting`, with only that fact's limitation (via `_gap_cell` :1031). The ruling separates "a copy" from "a sum of copies" only for period. Fail-closed option: treat the sum as a dependant gap with `Not calculable: Equity issuance is conflicting`.

**The implementer's four calls**

- **Tagged recomputed cells keep the CP-1 metric's period.** This matches ruling :1929 ("a cell with `cp1_operand`") and LEAD's own `rule_period`. Info for LEAD: it puts T4.10's `LTM Q4 25: 2025-01-01 to 2025-12-31` on balances (undrawn revolver, liquidity), the reverse of the :1943 concern.
- **Balance-date fallback when that CP-1 fact is absent** (`_t410` :1143; also T2E.2.r06 with an empty schedule). Unruled, goes to LEAD. :1929 "never defaults it" leans against it. Fail-closed option: raise an invariant. The alternative is to drop the tag so the cell falls under "every other".
- **`Facility.period` as a required field** matches :1937 (each copy's CP-1 period). Only tests construct `Facility`.
- **`Cell.differing_periods`** is unruled internal plumbing. It is never on a returned cell (it raises at :1128-1129). Info.
- **Also for LEAD (Info):** a missing-status revolver keeps the oracle-pinned `REV_*` texts, not CP-1's limitation as :1987 literally says.

**Frozen oracle and quality**

- `_assert_cell` (tests:326-348) applies only `PERIOD_DELTA` and `GAP_VALUE_CLASS_DELTA` and compares everything else exactly.
- The guard test (:311-323) fails once `period` or the gap classes appear in `expected.json`.
- Removed test lines:
  - The one removed assertion (value_class) is replaced by one that knows the delta.
  - The rest move Decimal operands to `_ro`/`_k` known operands.
- No frozen assertion is weakened. The diff has no stub, fake value or catch-all.
- CP-3C reads CP-2D's frozen oracle; LEAD's part C still shows exactly the 6 `q4-2025` moves.

**Exit codes** (run in the temporary copy `<S>/cp2d-r13-review/copy`):

| Gate or probe | Exit | Note |
|---|---|---|
| pytest (cp2d, cp3c, selfcheck) | 0 | 805 passed |
| `ruff check` | 0 | |
| `ruff format --check` | 0 | |
| `mypy --strict` | 0 | |
| implementer `mutants.py` | 0 | 20 of 20 killed |
| `p13_cp2d_period_class.py` | 1 | only part A, which expects the old code; C = 6 moves, D = 110 |
| `r1_rule_and_status.py` | 0 | |
| `r2_conflicting_revolver_prose.py` | 1 | reproduces findings 1 and 2 |
| `r3_review_mutants.py` | 1 | 3 mutants survive (finding 3) |
| `r4_spelling.py` | 0 | |

`<S>` = /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad. My probes are in `<S>/cp2d-r13-review/probes/`.

Not verified: the T2E.6/T2E.7 ledgers for a conflicting or not_applicable operand; the three `fixture_*` cases against the rule (the test helper cannot build them, only partly through `_operands`); a real promoted CP-1 head or Stage 2 adapter building `Operand` and `Facility.period`; the full suite, jscpd and complexipy; GitNexus was not used.