# Independent CP1 S.1–S.4 expectations — pre-implementation

This review pins source-derived expected results before candidate chart implementation. The accompanying `independent-chart-expected-results.json` is the literal data oracle. No candidate output was used.

## Frozen authority and locators

- Manifest SHA256: `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`.
- Financial source SHA256: `82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429`.
- Identity source SHA256: `74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4`.

Hashes were independently recomputed from the manifest bytes and literal UTF-8 pages joined by U+000C. Source quantities are USD millions: one source-unit million is USD1,000,000. IFRS, consolidated group, unaudited without auditor. Publication date2026-01-10 is distinct from financial snapshot2025-12-31.

Financial page2 lines4/15 supplies quarter/FY EBITDA; page3 lines4/30 cash interest; page4 lines4/5 cash,4/13 debt,4/33–34 RCF commitment/drawings. Page1 line18 explicitly states no RCF. Page5 lines4–5 establishes exactly one complete term-loan population, line11 supplies current50, line13 supplies zero annual amortisation and2029-12-31 maturity, and line14 explicitly identifies the shared FY/Q4 closing balance. Identity page1 lines4/5/7 pins issuer/fiscal scope and absent legal perimeters. Line numbers are one-based within each literal page.

## Expected charts

| Chart | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| S.1 total leverage, x | unavailable | unavailable | unavailable |50/30=5/3|
| S.1 net leverage, x | unavailable | unavailable | unavailable |(50−20)/30=1|
| S.2 interest cover, x | unavailable | unavailable | unavailable |30/5=6|
| S.3 cash, USD millions |16.25|17.50|18.75|20.00|
| S.3 undrawn RCF, USD millions |0|0|0|0|
| S.3 total liquidity, USD millions |16.25|17.50|18.75|20.00|

Arithmetic uses precision38 and ROUND_HALF_EVEN without display quantization before calculation. Exact5/3 is represented as `1.6666666666666666666666666666666666667`. Cash-interest source payments normalize to−5 over twelve months; coefficient−1 produces the positive denominator5. Earlier quarterly ratios lack a complete preceding twelve-month series: no zero-fill, forward FY substitution or quarterly annualization. RCF0 is genuine source-backed zero; term-loan commitment minus drawn must never become revolving headroom. Liquidity total is cash plus undrawn RCF and must not be stacked in addition to those same components.

S.4 contains one current outstanding50 USD million term-loan exposure at2025-12-31, classified under contractual final maturity2029-12-31; annual amortisation is explicitly0. This is not a forecast of2029 balances. The minimal wall has one2029 bucket. No future zero-filled schedule is required; additional empty snapshot buckets need explicit completeness-based interpretation and nonforecast labeling. FY and Q4 must not duplicate the same balance into100.

Q4 own period is2025-10-01..2025-12-31,92days. Its leverage/coverage operands use trailing_four_quarters2025-01-01..2025-12-31,365days and the four actual selected QUARTER construction IDs. Reported FY2025, historical Q4 and rolling basis remain distinct even with equal values/end dates. Do not silently treat source-period IDs as construction IDs.

## Adopted contract evidence and integration boundary

Paths below are relative to `/Users/ericguei/Documents/Deploy Workflow`; only the adopted contracts needed for this review were inspected.

- `src/deploy_vii/model/metrics.py:89–100,185–226`: reported leverage/coverage definitions and trailing quarter basis; missing inputs and denominator<=0 refuse a numeric ratio (`:160–179`).
- `src/deploy_vii/model/debt.py:293–301`: undrawn RCF is commitment minus RCF drawn; `model/statements.py:352`: liquidity is cash plus undrawn RCF.
- `src/deploy_vii/financial_model.py:36–95`: ModelBasis, ModelValue, MetricOperand, ModelMetric and ModelReport identities. Existing ModelReport has no chart-series field, so canonical chart integration is an implementation obligation, not a data gap.
- `src/deploy_vii/report_view.py:235–293`: ChartMark/ChartSpec, formatted numeric marks, missing G# references and table twin equality. `charts.py:674` renders an adopted ChartSpec to SVG.
- `report_view.py:1125–1130` identifies S.1–S.4; `bindings/cp1.py:51–52` currently supplies the KPI-register fallback.

Each numeric mark must retain source/computation/metric references and unit/basis identity; ratio lineage must identify actual operand values and coefficients. Table-twin cell texts and order must match marks exactly under display.format_value. Chart/report/canonical Model must agree on the same current selected run. Geometry choices are not financial facts.

## Independent adverse expectations

The JSON enumerates twelve cases: missing trailing quarters; nonpositive/missing denominator; absent RCF inputs versus explicit0; inappropriate term-loan headroom; duplicated FY/Q4 facility; absent maturity/incomplete facility population; currency/scale error; source/computation/basis reference tampering; stale selection/serialized-series tampering; genuine missing financial source; invented maturity forecast/zero bins; and status inflation.

Existing genuine missing-financial case remains CONDITIONAL/DO NOT RUN: actual CP1 admission and actual publisher refuse without CP1/Model heads or Model files. Restricted CP0/CP1/Model states, existing limitations and QA58/Restricted/Low are not upgraded by chart availability. This chart slice qualifies neither other owners nor legal perimeters, prior-year growth, forecasts, production or live providers.

## Route and evidence limits

LEAD explicitly assigned the existing independent reviewer to Sol/high under AGENTS.md financial/state routing. This records the assignment and static review activity, not hidden runtime model telemetry. Literal source/hash inspections and independent Decimal arithmetic preceded candidate code. No product/source/case/shared-file edits, tests, core validators, heavy jobs or providers were used. Only these two work artifacts were written. No new approval chain is introduced.
