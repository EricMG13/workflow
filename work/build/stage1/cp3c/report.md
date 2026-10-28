# CP-3C Stage 1 report (controller-saved from the implementer's hand-back)

- **Branch and commit:** `worktree-agent-aa5a4817fa00cd287`, commit **09d9ee7**, base ae65b75.
- **Files:** `src/deploy_workflow/owners/cp3c.py` (new, 1507 lines) and `tests/test_method_cp3c.py` (new, 635 lines).
- **Pins:** the 4 oracle pins and every `manifest.frozen_inputs` sha match, and the test asserts them.
- **Tests:** RED was seen as an ImportError at collection. Final result: 96 passed in 0.38 s.
- **Gates:** ruff check, ruff format --check, and mypy --strict on both files all exit 0. The first pass failed all three (11 ruff findings, formatting, 8 mypy errors).
- **Size:** the lease estimate was about 450 lines. The extra is mostly cells, tables, verbatim limitation strings and the trace. Look at it in the whole-branch review.

## Public surface
- **Schema:** `StepUp`, `RepricingAbsence`, `PathAssessment` and `RefinancingRiskSubmission`.
- **Inputs:** `Cp1Fact`, `Cp2dFact`, `FacilityTerms`, `Cp1Operands`, `WallRow`, `Cp2dOperands` and `Cp3cInputs`.
- **Composer:**
  - `compose_refinancing(*, operands, step_up_bps) -> Refinancing`;
  - `wall_position(...)`, using CP-2D's whole-month rule;
  - `compose_operands(*, cp1, cp2d, balance_date, currency)`.
- **Validator:** `submission_issues(*, submission, offered)`. `prohibited_conclusions` is the product `business_context.prohibited_issues` plus a core-local check.
- **Result:** `compute(inputs) -> Cp3cResult`, holding:
  - T3D.1–T3D.6 tables and T3D.7–T3D.9 text tables;
  - claims and limitations;
  - status `restricted`.
- **No G1 seam names are defined.**

## Input fields
| Field | Type | Stage 2 source |
|---|---|---|
| `balance_date` | date | CP-2D D0 |
| `as_of` | date | run `as_of` |
| `currency` | str | pack reporting currency |
| `cp1.cash_closing`, `.undrawn_rcf`, `.adjusted_ebitda`, `.cash_interest` | Cp1Fact | CP-1 T4.10 (cash interest negated exactly) |
| `facilities[].facility_id` | str | T4.18 facility id |
| `facilities[].currency` | str | T4.18 facility currency. **Not in fact_bindings; Stage 2 must bind it** |
| `facilities[].facility_name`, `secured_status`, `seniority`, `annual_amortisation` | Cp1Fact | T4.18 `term-loan.*`; the `currency` unit is normalised in Stage 2 |
| `cp2d.horizon`, `run_rate`, `minimum_cash`, `funding_gap` | Cp2dFact | CP-2D `T2E.3.r03`, `T2E.3.r01` (needs the reader pin extension, lease Q3), `T2E.5.r04`, `T2E.5.r07` |
| `cp2d.wall[]` | Cp2dFact ×4 | CP-2D `T2E.4.rNN.c1`–`c4` |
| `submission.*` | judgment | The repricing step-up (D11 uncited assumption), the absence, and the paths with view-ref `basis_refs` |
| `offered` | Mapping ref→name | the `read_inputs` view facts |

## Oracle coverage
- **All 10 cases:**
  - the 3 pack cases cell for cell, including tables, text tables, limitations, status, claims, `derived` and `missing_not_zero`;
  - the 7 fixtures through `derived`, `missing_not_zero` and `wall_position`.
- **Rules:** `source_facts` and `method_rules`, plus lease-boundary and property tests.
- **Refusals:** all 17 refusals, the 3 valid literals, the bps bounds 0 and 1000, the 28 `prohibited_probe` sentences, and the attempt issues of `negative_cases.blocked_cp3c`.
- **Consumption, calculation level:** table ids and titles. CP-2D copies keep their value and class, and gaps stay gaps.
- **Left to Stage 2/4:**
  - cp0_with_cp3c, upstream_asserted_only, cp1_downstream_readiness;
  - the blocked head and receipt, begin_refused_cp2d_blocked;
  - tool_use, the view tree, tamper and probe;
  - consumption by `cp3c_reader`, and fp04 rendering;
  - citations and calculation ids, inherited limitations, stale binding, G1 seams and registration.

**Engine/oracle disagreements:** none exercised. One unexercised difference: the lease's `base_resources` excludes F, while the builder sets the base to None when F is missing. The code follows the lease.

## Rulings needed from LEAD before first review (they currently raise ValueError)
1. **COST-01 at 0 bp.** The validator accepts 0 bp, but the template says the step-up "lowers interest cover", so a valid submission fails composition. Pin a zero form, or rule.
2. **Unpinned gap and n.m. reasons:**
   - ranking not stated;
   - amortisation missing;
   - EBITDA ≤ 0, zero balloon cover, zero cash interest;
   - any missing cash, revolver, F, EBITDA or interest in a computed cell.

   The builder has candidate strings, and its `why_resources` would mislabel some of these.
3. **Claim gap forms** for amortisation missing, ranking not stated and zero EBITDA.
4. **Multi-facility order** of the T3D.9 trace and the claim `cites_from`; the code uses maturity-order groups. The T3D.7–T3D.9 column headers are unpinned.
5. **The trace locator** `"<table_id> <period before ':'>"` is a derivation, not a pinned rule.
6. **Other fail-closed cases:**
   - a non-USD facility (no limitation wording);
   - an empty facility list or zero total principal;
   - an unknown ranking flag;
   - a CP-2D wall row inconsistent with CP-2D's rule;
   - a CP-1 register that names different facilities from the CP-2D wall.
7. **Stage 2 bindings:**
   - facility currency;
   - normalising the T4.18 `currency` unit;
   - the value_class and period of CP-2D gap copies.
8. **No issue de-duplication** (oracle parity).

## Confidence review and mutation
- **Fixed:**
  - `assert` used for narrowing in `src`;
  - a dead branch;
  - unary minus replaced by `copy_negate()`;
  - an equivalent-mutant reset.
- **Hand mutation:** 24 mutants. All are killed after two property tests were added; one dead and one equivalent piece of code were removed.
- **Rewrite tournament:** `_maturity_rows` holds. `_creditor_rows` takes an early return for the unranked case.

Not verified:
- Stage 2 binding against promoted CP-1 and settled CP-2D heads;
- the gap-copy class and period;
- multi-facility order beyond the fixtures;
- `prose.issues` with citations;
- non-terminating /12 amortisation;
- the repo-wide suite;
- mutmut (mutation was done by hand);
- size.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
