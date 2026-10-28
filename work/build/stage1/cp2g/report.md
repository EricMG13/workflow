# CP-2G Stage 1 report (controller-saved from the implementer's hand-back)

- **Branch and commit:** `worktree-agent-a4377a7580e8e70db`, commit **53816b7**, based on 556232a.
- **Files:** `src/deploy_workflow/owners/cp2g.py` (new, about 2,360 lines) and `tests/test_method_cp2g.py` (new).
- **Tests:** `PYTHONPATH=src …/python -m pytest -q -p no:cacheprovider tests/test_method_cp2g.py` gives 147 passed in 1.46 s.
- **Gates:** ruff check, ruff format --check, and `MYPYPATH=src mypy --strict` on both files all exit 0. The first run was not green: B023, ISC004 and 3 test typing issues.

## Public surface (pure)
- **Selection and inputs:** `select_cp1` requires exactly one T4.10 fact per label. `Operands.from_cp1` and `Drivers.from_submission` build the inputs.
- **Arithmetic:** `forecast(*, operands, drivers, shock)` runs in a 38-digit context that traps inexact results. Each ratio is one `model/_cells.CONTEXT` division.
- **Breaks:** `test_breaks`, `first_result`, and `break_decline`, which returns an exact Fraction.
- **Validation:** `content_issues`, `payload_issues` (shape issues alone, else content issues), and `stale_issues(*, bound, current)`.
- **Composition:** `compute(inputs) -> ForwardResult` returns:
  - Facts with `derives_from` and `shown`;
  - tables T2H.1–T2H.9 and the three reference tables;
  - claims, limitations, break tests and trajectory.

  It raises on any issue.
- **Schema and seams:** the schema is `ForwardSubmission`. `Upstream`, `validate_forward`, `forward_model`, the readers, view, probe and submit are left for Stage 2.

## Input fields
| Field | Type | Stage 2 source |
|---|---|---|
| `ForwardContext.cp1_facts` | tuple[Fact] | CP-1 head; the 16 T4.10 `LTM Q4 25 (…) · <metric>` facts (manifest `fact_selection_rule`) |
| `cp2a.base_period` | str | CP-2A head `base_period` |
| `cp2a.scenarios[]` | row, name, decline, increase | `T2B.1.<row>.name`, `.ebitda_decline`, `.interest_increase` |
| `cp2a.breaks[]` | row, origin, test, level, required_decline, outcome | `T2B.6.<row>.*` |
| `cp1d.status` | InputStatus or None | Bound CP-1D Input status |
| `cp1d.supported`, `total_leverage`, `net_leverage` | Fact | `T1D.3.supported.value`, `T1D.6.supported.total_leverage`, `T1D.6.supported.net_leverage` |
| `cp1_status`, `cp2a_status` | InputStatus | Bound Input statuses (T2H.1) |
| `names` | tuple[str] | `pack.run.issuer_name` |
| `cp2d_status` | InputStatus or None | Bound CP-2D Input; fails closed if set |
| `ForwardInputs.submission` | ForwardSubmission | Judgment |

## Oracle coverage
- **Covered, cell for cell:**
  - cases positive, gap and cp1d_blocked;
  - fixtures total_loss, cash_missing, debt_repaid and cp2a_gap_head.

  For each: operands, forecast path, all facts in order, tables, the reference tables, claims, limitations, break tests and trajectory. The T2H.4–T2H.8 cells are checked against the FP05 blocks.
- **Refusals:** r01–r16 and v01–v17 exact. v18–v20 go through `stale_issues`, using a made-up Input tuple.
- **Property tests (hypothesis):**
  - roll-forward;
  - downside dominance;
  - monotonic leverage;
  - base control;
  - `first_result`;
  - the `break_decline` round trip.
- **Extra test:** a crossing-boundary test. The oracle alone didn't kill the mutant that flips the comparisons.
- **Stage 1 stand-ins:**
  - CP-1 fact ids `interface-fact:<sha256(label)>`;
  - `calc:` ids;
  - a page-4 citation;
  - `{{FIG}}` replaced by `{fact_id|token}`.
- **Left to Stage 2/4:**
  - `Upstream` and the readers, and the run-level stale_binding;
  - module status, and settled and inherited limitations;
  - the refused and blocked cases and cp2a_blocked;
  - tool use and the view;
  - tamper, D7 rendering, cp0 and cp1_readiness, and D8.

**Engine/oracle disagreements:** none; no engine is reused.

## Rulings needed from LEAD before first review (they currently raise ValueError)
1. Any missing base operand other than cash; only "cash and cash equivalents" is pinned.
2. The T2H.7 claim when exactly one test is first reached. Only the plural is pinned. The positive submission with minimum liquidity 25 reaches this case.
3. The T2H.8 claim when only one of the peak and FY2028 leverage is calculable.
4. EBITDA margin on zero or negative revenue; growth "-1" is valid.
5. A downside scenario whose CP-2A shock is not known.
6. A bound CP-2D head; the lease's line is written with "…".
7. A CP-2A Definition row with other test wording: a validator error with no issue text.
8. An unverified break from a non-positive denominator, which is not one of the lease's three causes.
9. A bound CP-1D fact that is not known or not on the LTM period.

## Decisions to confirm
- **Prose checks:** they cover rationales and gap fields, not limitations, matching the v11 paths.
- **Issue order:**
  - within a driver, the value issue comes before the rationale issue;
  - within the assessment, rationale issues come before the High issue.
- **Probability guard:** it quotes the listed phrase, not the matched casing.
- **`stale_issues`:** its position in the issue order is for Stage 2 to decide.
- **Unknown CP-2A cells:** copies keep the upstream status, while the builder writes missing. No case constructs this.
- **Calculated T2H.3 copy:** it would carry `cp2a:` lineage. No case constructs this.
- **Prose bound set:** the 16 CP-1 facts, plus CP-1D facts when bound. Stage 2 could widen it.
- **Validation input:** strict `Contract` rejects lists for tuple fields, so Stage 2 must validate from JSON text.

## Confidence review
- **Fixed:**
  - stored amounts are made canonical;
  - the unverified-operand cause is the first missing operand in formula order;
  - one `pragma: no cover` and five `type: ignore`s are removed.
- **Rewrite tournament:** `_year` was rewritten, so the base case is the zero-shock formula. `_metric_check` and `_break_issues` hold.

Not verified:
- Stage 2 binding against real CP-1, CP-2A and CP-1D heads;
- Module and Claim assembly and settlement, and inherited limitations;
- run-level stale binding;
- tool use and the view, and tamper/probe;
- FP05 rendering and the readiness re-assertion;
- wording for fail-closed points 1–9;
- the full suite.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
