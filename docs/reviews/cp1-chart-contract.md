# Independent Task3-C pre-code contract review

Result: **PASS** for the bounded implementation contract. No material contradiction with the frozen independent source oracle was identified. This receipt freezes expectations; it does not claim candidate implementation, test or actual-run qualification.

## Reviewed identities

- Contract `docs/CP1-CHART-SLICE.md`: SHA256 `e6e3f4a1853dbdcd142ab9afcfdadeabae5452d48a354c8db00a873359457936`.
- Literal oracle `cases/charts/expected.json`: SHA256 `2ca2606c46c09ab285d0602b5f95d06a36d61a6aa4e467fbb45e71afbf665276`.
- Independent review `docs/reviews/cp1-chart-expectations.md`: SHA256 `91da569ccec9606d328d218c800b0565449449d1e3414739bd0c5089ef367248`.

The copied oracle and review were checked byte-for-byte against the previously authored work artifacts. The unchanged financial manifest/source/identity hashes named in the contract match the independent oracle.

## Material checks closed

- S.1/S.2 use four explicit QUARTER categories, Q1–Q3 missing trailing ratios and exact Q4 total50/30, net(50−20)/30 and cover30/5. FY, Q4 own period and trailing-four-quarter operands remain distinct; Decimal precision38/half-even arithmetic remains authoritative.
- S.3 preserves source-native USD MILLIONS (scale1000000), actual cash16.25/17.50/18.75/20, numeric RCF0 and adopted cash+undrawn total. Three line series avoid stacking the total with its components. No term-loan headroom becomes RCF liquidity.
- S.4 uses the sole current principal50 at2025-12-31 classified by contractual2029-12-31 maturity, annual amortisation0. Principal/carrying/drawn amounts are equal in this frozen source. The explicit snapshot/convention, one category and no invented future bins preserve the independent nonforecast interpretation and prevent FY/Q4 double counting.
- The agreed immutable FinancialFigureSeries/FinancialSeriesPoint API carries fact IDs and companion identities rather than duplicate financial values or arithmetic. Current selected CP1 joins, currency/scale/perimeter checks, honest missing facts and fail-closed malformed accepted data remain required. Existing passports and G# references preserve numerical and gap lineage.
- Canonical Model HTML and report both carry authentic serialized ReportView figures/table twins through the existing chart path. Unchanged financial-model/3 calculation JSON remains the underlying value/basis/operand authority. The explicit no-new-ModelReport-schema ruling is a defensible bounded integration choice, not a source gap.
- Ownership is disjoint: C1's new pure producer/test/handoff; C2's report_view/test/handoff. LEAD owns shared contract/queue/oracle decisions and PR MANAGER owns integration/import-patch provenance. No unleased financial engine, workflow, source, renderer asset or receipt edit is authorized.
- A fresh public CP0→five-stage CP1→QA/promotion→Model publication→seal chain avoids modifying or reopening prior sealed evidence. Fresh raw QA receives a binding-specific independent expectation; identical source alone cannot predict the prior58. C2 remains read-only against the final producer receipt; report/Model byte and serialized-series agreement are explicit acceptance requirements.
- Missing-source admission/publication refusal, malformed/foreign references, stale/tampered evidence and pathway/status isolation remain causal adverse cases. Prior packages remain preserved. Model technical readiness READY remains distinct from restricted module heads and QA Restricted/Low; chart availability cannot upgrade these statuses or expand owner/provider/pathway qualification.

## Route and limits

LEAD explicitly requested reuse of the existing independent Sol/high financial/state review role under AGENTS.md; this is assignment evidence, without a hidden telemetry claim. Review used the contract, frozen independent source expectations and their hashes only. No candidate code/output, tests, core validators, heavy jobs, providers, product/source/case/shared-file changes or additional approval chain were used. Only this requested work receipt was written. Implementation and actual native/publication evidence remain for the already-authorized lanes.
