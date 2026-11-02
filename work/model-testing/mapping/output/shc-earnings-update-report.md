# Mapping report: shc-earnings-update

Preparer: mx-feature (Task 6 preparer). Base 9c018f76. Output: `cases/goldens/shc-earnings-update/mapping.json`.

## Per module

| Module | Entries | Unmapped | Facts | Unmapped % |
|---|---|---|---|---|
| CP-0 | 2 | 14 | 16 | 88 |
| CP-1B | 7 | 44 | 51 | 86 |
| CP-1D | 0 | 30 | 30 | 100 |

Total 9 entries, 88 unmapped, 97 facts.

### CP-0
- Files: `src/deploy_vii/readiness.py` (`build_readiness` sets every fact's table/row/field), `src/deploy_vii/cp0_workflow.py`. Commit eeab0b8fecda6ee1a74b16c66711503e12928583.
- Entries: `legal_name` -> T1/run/issuer (the run's issuer name, fixed by the context file as "Sotera Health Company"; golden prints the cover capitalisation, a value comparison matter); 10-Q `period_end` -> T1/run/reporting_period (field fixed, content written by the model).

### CP-1B
- Files: `src/deploy_workflow/earnings_workflow.py` (`compose_delta` sets ids and periods), `src/deploy_vii/bindings/cp1b.py` (`_LAYOUT_TEMPLATES`: T1B.1 rows and fields), `src/deploy_workflow/owners/cp1b.py`. Commit 438317d342f7e0f93808d3d8c769887182162be2.
- Periods: prior fact `q2-2024`, current fact `q2-2025` (context.json `prior_period`/`current_period`), delta and assessment facts `q2-2024->q2-2025`.
- Entries: Consolidated net revenues (T1B.1/revenue prior, current, delta) and Adjusted EBITDA (T1B.1/adjusted_ebitda prior, current, delta); deltas depend on their two operands. Guidance -> T1B.3/guidance/assessment (the owner path always writes it as missing, GUIDANCE_NOT_SUPPLIED, matching the golden's missing fact).

### CP-1D
- Files: `src/deploy_workflow/owners/cp1d.py` (`_register`, `_bridge_rows`, `_Facts`). Commit 5d5b6861247f4165d23e46a05b935b1f16325d97.
- No entries (see reasons).

## Unmapped reasons, grouped
- CP-0 (14): the readiness module records only T1 run fields, per-source P3/P5/T2/T3/T6, per-consumer T4/T8, T5 gaps, T7; ticker, state, file number, filer category, shares, address, sponsors, borrower, parent, guarantors, segments, signature date, fiscal year end and reporting unit have no field.
- CP-1B segment revenue and income (18): T1B.1 rows are consolidated only.
- CP-1B consolidated net income (3): no net income row in T1B.1.
- CP-1B debt context (23): T1B.2 holds only cash_closing, total_debt, net_debt (consolidated); no per-instrument, terms, rate, revolver or margin-tier field. `Total long-term debt` gross principal is not T1B.2 total_debt (CP-1 balance measure).
- CP-1D reconciliation lines (28): bridge rows come from a management bridge attachment (row ids a01.. by source order); this case has none (management_bridge false), and the lines are 10-Q rows. No net income or adjusted net income cell exists. CP-1D writes one period only.
- CP-1D Adjusted EBITDA (2): T1D.3/start/value is CP-1 `adjusted_ebitda_ltm`, a trailing-twelve-month figure, not the 3-month golden value.

## Modules over 20% unmapped
- CP-0 (88%): the golden facts are registrant identity details that the readiness module does not hold.
- CP-1B (86%): the golden is built from segment, net income and debt-term facts outside the CP-1B T1B tables; only consolidated revenue, Adjusted EBITDA and guidance are held.
- CP-1D (100%): the module restates a management bridge on an LTM basis; the golden holds 10-Q quarterly reconciliation lines and the case has no bridge.

Not verified: `load_mapping` was not run (no venv by rule); the period strings q2-2025, q2-2024 and `q2-2024->q2-2025` were read from code and context.json, not from a live run; whether the case's run feeds CP-1B through `compose_delta` for a year-over-year quarter pair was not exercised; the T1/run/reporting_period value format was not checked against a result.
