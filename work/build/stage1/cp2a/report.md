# CP-2A Stage 1 report (Downside pathway)

- Branch: `worktree-agent-a34fec3e9469279cd`, cut at lane tip `f2cd61f` (it contains 4822066 and e8ee084). The original agent worktree was auto-removed. I recreated it at the authorised fast-forward target.
- Files: `src/deploy_workflow/owners/__init__.py` (empty), `src/deploy_workflow/owners/cp2a.py`, `tests/test_method_cp2a.py`, this report.
- Commits: 5626b90 `feat(cp2a): Stage 1 calculation against the frozen oracle`; fix round 1 is `fix(cp2a): fix round 1 after the mx-adversary review` (its SHA is in the hand-back).

## Public API (Stage 1)
`MODULE_ID`, `STEP_ID`, `SCHEMA_VERSION`; schema `DownsideSubmission` (`Scenario`, `Threshold`, `Assessment`, `DownsideGap`); `BaseOperands.from_cp1(cp1_facts, *, period)`; `stress(*, base, decline, increase) -> StressedRow`; `break_points(*, base, thresholds) -> tuple[BreakPoint, ...]` (with `ThresholdSpec`); `rank`, `crossing`, `lineage`; `Inputs`; `validate(inputs) -> tuple[str, ...]` (content issues); `compute(inputs) -> Result` (raises ValueError on any issue). None of these names clash with protocol §2 (`QUALIFICATION`, `probe`, `view`, `precheck`, `STEP_IDS`, `SCHEMAS`, `RULES`, `submit`). Stage 2 wraps `validate`/`compute` as the lease's `validate_downside`/`downside_report` (pack, Upstream).

## Input fields
| Field | Type | Stage 2 source |
|---|---|---|
| `submission.base_period` | str | judgment (must be a view `base_periods[*].period`) |
| `submission.scenarios[*]` (name, ebitda_decline, interest_increase, category, rationale, limitation) | `Scenario` | judgment |
| `submission.thresholds[*]` (metric, level, label, category, rationale) | `Threshold` | judgment |
| `submission.assessment` (rationale, category, confidence, limitation) | `Assessment` | judgment |
| `submission.gaps[*]` | `DownsideGap` | judgment |
| `cp1_facts` | `tuple[Fact, ...]` | bound CP-1 head, T4.10 facts selected by `manifest.fact_selection_rule` (label `<column> · <metric>`, period = view period), the view's `cp1_facts` |
| `offered_periods` | `tuple[str, ...]` | `context_block` `base_periods[*].period` |
| `names` | `tuple[str, ...]` | `pack.run.issuer_name` |
| derived `BaseOperands`: ebitda, interest (= -cash_interest), fcf, total_debt, cash | `Decimal \| None` | T4.10 `ebitda`, `cash_interest`, `fcf`, `total_debt`, `cash_closing` |
| derived `BaseOperands.gates` | `Mapping[str, str]` | T4.10 `total_leverage_reported`, `net_leverage_reported`, `interest_coverage_reported`, `fcf_to_debt` (status and limitation) |

## Test result
`PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2a.py`: 74 passed, 1 skipped (v17), 1 xfailed (v02, strict) in 1.19 s. That is after fix round 1; it was 70 passed, 1 skipped at 5626b90.

## Gates (exit codes)
ruff check 0; ruff format --check 0; `MYPYPATH=src mypy --strict src/deploy_workflow/owners/cp2a.py tests/test_method_cp2a.py` 0 (fix round 1 adds the test file to mypy). Not first pass: one ruff reformat, and one mypy `no-untyped-call` fixed by rewriting `crossing`. The file has zero `type: ignore`.

## Oracle sections covered
- `cases.positive`, `cases.gap`, `cases.interest_undisclosed`: base_operands; every fact (id, order, label, status, text, unit, period, amount_exact, shown through `report_view.fact_spelling`, decimals, value_class, formula, calculation_id, limitation, currency/scale); lineage (citations = ordered, de-duplicated CP-1 citations of `derives_from`); tables T2B.1-T2B.9 (title, rows, fact ids) plus `validate_tables`; `cp1_references` (verbatim copies, labels, spelled, cell text); claims (exact text after FIG binding, limitations, `prose.issues` clean); own limitations; stress rows and not-calculable reasons; break points (outcome, s*, exact fraction, shown, EBITDA at break, crossings, Fraction round trip); ranking and first break; FP05 block cells (state and text through `fact_spelling`); the lease's A1 spelled checks.
- `refusals`: shape r01-r14 (real `DownsideSubmission` and `readiness.shape_issues`, pydantic 2.14.1: every message matches the oracle); content v01, v03-v16; v02 on the composer, as a strict xfail against the frozen oracle (see the disagreement below).
- `property_tests` (hypothesis): base_control, round_trip (exact Fraction at s*, and the Decimal s* is the 38-digit rounding of it), monotonic.
- Left to Stage 2/4: v17 stale input (skipped test, needs the attempt's bound `Input` records); `blocked` and `refused` cases, `execution`, `cp1_readiness`, `cp0`, module status, inherited limitations, receipt, tool use, tamper (A3/A4), view key tree, FP05 rendering through G2.

## Engine/oracle disagreements
- **v02 (oracle defect, pending LEAD amendment).** The frozen oracle expects one issue, `base_period: base EBITDA is missing or not positive for LTM Q4 25: ...`. On the positive CP-1 facts with base EBITDA set to missing, the validator returns three issues for the literal v02 payload, unrewritten: that issue, then `scenarios[0].rationale: Unresolved reference: <ebitda fact id>` and `scenarios[1].rationale: Unresolved reference: <ebitda fact id>`. The payload's prose still names the now unsettled EBITDA fact. `test_v02_base_ebitda_missing_on_the_composer` asserts the oracle's exact tuple under `xfail(strict=True)`, so LEAD's amendment will turn it into a failure and force the update. `test_v02_is_refused_by_the_composer` checks that `compute` refuses.
- No engine is reused (CP-2A has none). `prose`, `business_context.prohibited_issues`/`referencable`, `readiness.shape_issues`, `report_view.fact_spelling` and `model/_cells.CONTEXT` were called, not edited.

## Findings for the controller (no policy invented)
1. **Zero debt or zero cash interest (lease formulas, not in the oracle).** With total debt 0, the total-leverage break gives s* = (L·E - 0)/(L·E) = 1, outcome "Reached at the stated decline". But leverage stays 0, and at s* = 1 the stressed ratio is undefined. Cash interest 0 does the same for the coverage breaks. This breaks the oracle's round-trip property, so the property test is restricted to debt > 0 and interest > 0. The code follows the lease formula. Needs a LEAD ruling (for example "Not reached", as for net debt <= 0).
2. **Monotonic property and negative net debt.** "Leverage does not fall as the decline rises" is false for net leverage when net debt < 0. The test keeps net debt >= 0.
3. **The CP-1 gate is applied per ratio**, from CP-1's own fact for that ratio. The builder uses one case-level flag. Results are identical on all three cases. The gate limitation line is emitted once per gate reason that some cell actually shows. That keeps it out of `interest_undisclosed`, where CP-1's coverage fact is missing but the operand reason shows first.
4. **Missing base FCF (not exercised).** The code says "Not calculable: base free cash flow is missing". The builder would attach the interest-increase sentence to a stressed FCF in that case.
5. **Prose checks (fix round 1).** They now also cover the scenario and assessment `limitation` fields, with the same wording (`<path>: empty text`, `prose.issues`, `prohibited_issues`); a None limitation is skipped, as `cp2_synthesis._texts` does. Every oracle literal still validates, and the content refusals are unchanged. Left for LEAD: names and labels are unchecked. A resolved `{ref|unit}` in a limitation passes validation, but `Claim.limitation` is plain text and is not carried into `cp1_references` or the T2B.1 basis.
6. If the view offers a period for which CP-1 lacks exactly one T4.10 fact per metric, `validate` raises ValueError rather than returning an issue (fail closed).
8. **Fix round 1 (mx-adversary).**
   - T2B.7 now has fixed columns, so a run with no ranked break composes an empty ranking instead of raising IndexError. Two tests cover it: the gap base with FCF missing, and FCF above EBITDA with interest missing and no thresholds.
   - A positive CP-1 cash interest now raises ValueError until LEAD rules between the lease (`I = -cash_interest`) and the manifest ("magnitude").
   - The test typing is fixed.
   - Left unchanged for LEAD: zero debt or zero interest breaks (M3), the gate wording on an LTM base (L2), and net debt <= 0 being checked before the gate (L4).
7. The AGENTS.md ledger line (`work/<lane>/ledger.md`) was not written, because the brief limits the files I may write. Run line: 2026-10-28, cp2a-stage1, pytest tests/test_method_cp2a.py, exit 0, 70 pass / 1 skip.

## Confidence review
I did it manually. I listed doubts on missing-operand paths, the gate interplay, raise-without-reason guards, the inexact-arithmetic trap and lineage fail-closed, and traced each one. Issues 1-6 above are what remains. Rewrite-tournament was not run as a formal multi-candidate tournament; I did one manual simplification of `crossing`.

Not verified: an empty T2B.7 through G2 rendering or the FP05 tab; real CP-1 head facts (units, citations, calculation ids and fact ids are fixture values built from the oracle records); v17; any store, journal, view, probe, G1-X or rendering behaviour; behaviour at zero debt or zero interest (finding 1); shape messages under any pydantic other than 2.14.1.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
