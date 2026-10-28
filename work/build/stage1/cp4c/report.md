# CP-4C Stage 1 report (controller-saved from the implementer's hand-back)

- **Branch and commit:** `worktree-agent-a2c15c441717ec41c`, commit `8c57467`. It sits on 3dbbdaa, the 2ae589b cherry-pick, which is on 60e2348.
- **Pending re-pin:** the 3674158 oracle batch re-pin was sent after the build finished.
- **Files (new):** `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py`.
- **Pins:** manifest 9d81d280…, builder 2ca1c56a…, expected 61ddb316…, submissions 03b1b2aa…, plus the upstream expected/manifest pins.
- **Tests:** 130 passed in 1.51 s. One hand mutation (value-break `<` changed to `<=`) made 71 tests fail.
- **Gates:** ruff check, ruff format --check, and `mypy --strict` on src and test all exit 0. They passed on the second run, after one fix to a test helper.

## Input fields (`Cp4cInputs` = `Cp4cContext` + `RestructuringSubmission`)
| Field | Stage 2 source |
|---|---|
| `context.pack` | Prepared pack; only ready sources' spans are read |
| `context.cp1.status`, `.t410` | Bound CP-1 status; the T4.10 `LTM Q4 25 (…) · total_debt` and `· ebitda` facts |
| `context.cp1.facility_id`, `.secured_status`, `.seniority` | CP-1 T4.18 `term-loan.*` at the quarter period |
| `context.cp2g.status`, `.ebitda`, `.base_first`, `.down_first` | CP-2G `T2H.4.{b,d}{26..28}.ebitda` with its lineage; `T2H.7.b01.*_first` |
| `context.cp2a.status`, `.base_period`, `.facts` | CP-2A T2B.1 facts of the applied row |
| `context.cp4.status`, `.facts` | CP-4 `T4C.11.r01.*`, `T4.10.r02.permits` and `.conditions`, `T4.13.rating.rating` |
| `context.cp3c_status` | The optional edge; `None` in this version |
| `submission` | Judgment (`restructuring_fulcrum`) |

## Oracle coverage
- **Cell for cell:** five cases (positive, gap, fixture_ev_zero, fixture_ebitda_missing, fixture_debt_missing).
- **Refusals:** 36, exact and in order (r01–r13, v01–v27).
- **Guard:** probes, kinds and phrases.
- **Property tests:** conservation, priority, pari passu, monotone break, missing never zero.
- **Other:** stale inputs (CP-2G form).
- **Left to Stage 2/4:** refused, blocked and cp2g_blocked runs; tamper; tool use and the view; execution and consumption; D7 rendering; cp0 and cp1 readiness; module status; inherited limitations; run-level stale binding.
- **Engine/oracle disagreements:** none. The module reads CP-4 head facts only and does not touch the T4C.7 display item.

## Fail-closed raises for LEAD (`ValueError`)
1. A bound CP-3C head.
2. CP-1 T4.18 not SECURED and SENIOR. The lease calls this a validator issue but pins no wording.
3. A `source_row` `period_column` other than `Q4 2025-12-31`.
4. A CP-4 T4.13 rating other than Insufficient Information, or T4.10.r02 conditions other than the frozen text.
5. CP-1 EBITDA not known, or ≤ 0, leaving the implied LTM multiple without a reason.
6. CP-1 total debt with a status other than known or missing, or a non-LTM period, or any upstream copy that is `conflicting`.
7. A negative EV, a negative claim, or a rank whose known claims total ≤ 0.
8. A non-zero T4E.9 balance (see the first finding).
9. A blank or multi-line class name or valuation label, or a Python-worded claim that fails `prose.issues`.
10. A CP-2G EBITDA id or period mismatch, or CP-2A lineage on the downside EBITDA that is missing or inconsistent.
11. A quoted statement row with no numeric cell under the column.
12. A missing upstream fact id, or an unsettled upstream fact with no limitation.
13. More than 38 digits raises `decimal.Inexact`, as the oracle's exact context does.

## Findings
- **Exact conservation does not hold in general.** Per-class rounding at 38 digits can leave a residue in the 38th digit: three equal classes sharing a partial payment do it. The T4E.9 balance is then non-zero, and the code raises. `test_unconserved_waterfall_fails_closed` covers this.
- **Citations differ from CP-2G Stage 1.** CP-4C's calculated cells carry their inputs' de-duplicated citations (oracle `lineage_rule`); CP-2G Stage 1 does not propagate citations.
- **Unpinned choices:**
  - `class_id` is a plain string.
  - Unknown upstream copies keep their upstream status.
  - The T4E.1 status cells show the bound Input status. The builder hard-codes "restricted", which is equal in every case.

## Confidence review and rewrite tournament
- **Fixed:** two `amount or 0` fallbacks now filter explicitly.
- **Verified:** the validator order matches `build.py:1038-1135`, and hand-checked waterfalls agree.
- **Rewrite tournament:** the `waterfall` readability rewrite won and was applied; the `content_issues` incumbent holds.

Not verified:
- Stage 2/4;
- fail-closed states with no oracle case, beyond the 8 tests;
- the full suite;
- the reviews were run inline by the implementer.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
