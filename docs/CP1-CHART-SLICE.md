# CP1 chart series in report and canonical Model — Task3-C

Authority: the user explicitly requested continued C1/C2/PR MANAGER coordination
through replacement of the KPI-table fallback with actual CP1 chart series in
rendered report and Model output. This is continuation of the approved project and
team method, not a new approval chain. Code base: clean integrated
`5a4d3c36e7e8e259df5fc016ecef84d776415456`. Paid/provider/live tests remain paused.

## Outcome and limits

Produce real S.1 Leverage, S.2 Interest cover, S.3 Liquidity and S.4 Maturity wall
SVG figures, their exact table twins and functioning provenance interactions in
both the delivered report and canonical published Model HTML. Use the existing
ChartSpec/SVG/assets/display/index path; no new plotting dependency, chart runtime,
financial arithmetic engine or analytical owner. The existing calculation JSON
continues to contain the authentic underlying Model values, bases, metrics and
operands; no ModelReport schema change or second calculation JSON is required.
Actual serialized ReportView figures carry chart marks in both HTML outputs.

Keep source limitations, restricted states, QA semantics and all previous evidence.
Missing financial source still refuses actual CP1 admission and Model publication.
Missing trailing ratios remain gaps, and missing maturity data remains a disclosed
gap. An unavailable individual chart must name its actual reason; it must not
manufacture zero or conceal a missing implementation as a source limitation.
Only this frozen synthetic historical credit-snapshot case is qualified. Other
owners/pathways/issuers, comparative years, projections and providers remain open.

## Source-first independent expectations

Reuse `cases/financial/manifest.json` unchanged, SHA256
`6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`.
Financial source: `82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429`;
identity source: `74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4`.
Literal independent chart oracle and its source/route review are in
`cases/charts/expected.json` and `docs/reviews/cp1-chart-expectations.md`.
They were calculated before candidate code, from the source and adopted formulas.

- S.1: four QUARTER categories in chronological order. Total and net reported
  leverage are unavailable in Q1–Q3. Q4 trailing total leverage is 50/30 = 5/3;
  net leverage is (50-20)/30 = 1, in MULTIPLE. No later FY inputs fill early quarters.
- S.2: same four categories; reported interest coverage unavailable Q1–Q3;
  Q4 trailing EBITDA30 / positive cash-interest denominator5 = 6 MULTIPLE.
  Retain normalized interest -5 and coefficient -1 in the actual computation basis.
- S.3: cash 16.25/17.50/18.75/20.00 USD millions; actual undrawn RCF0 each;
  liquidity equals cash plus undrawn RCF, thus the same four amounts. Use three
  line series; never stack liquidity total with its components or treat term-loan
  commitment minus drawing as revolving headroom.
- S.4: one current facility exposure, principal50 USD millions at2025-12-31,
  contractual maturity2029-12-31, term-loan, annual amortisation0. This is current
  principal classified by maturity, not a forecast of2029 debt. Display a grouped
  chart with this single dated category, no invented future zero bins. The complete
  source population has exactly one facility. FY and Q4 share the same closing
  balance and must never double-count it as100. Name the snapshot and convention.

Q4 own period remains2025-10-01..2025-12-31; trailing ratio operands cover all four
quarters2025-01-01..2025-12-31. FY remains a distinct reported period. Values stay
exact Decimal; 38-digit half-even financial arithmetic is unchanged. Display text
uses the existing display formatter separately from exact SVG numeric values.
Each numeric/gap mark and its table twin retain current CP1 source/computation and
period/unit identities through existing passports and companion fact references.

## Public C1 to C2 interface

New leaf module `deploy_workflow.financial_series`; no shared __init__ change.

`cp1_chart_series(module: ModuleView) -> tuple[FinancialFigureSeries, ...]`

Immutable typed records, with exactly these consumer-facing names:

- FinancialFigureSeries: `fig_id`, `title`, `kind`, `unit_class`, `unit`,
  `series` (ordered tuple[str,...]), `points` (ordered tuple[FinancialSeriesPoint,...]),
  `reason` (str | None).
- FinancialSeriesPoint: `series`, `category`, `fact_id`, `companion_fact_ids`
  (ordered tuple[str,...]).

Producer returns S.1–S.4 in order. It owns strict canonical joins from T4.10 metric
and basis identities to T4.14 period coordinates and T4.18 facility snapshots.
Use QUARTER identity, not guessed label substrings, equal dates or equal values.
Unsupported/ambiguous basis, currency, scale or perimeter is an explicit reason or
ValueError, never silently guessed. Points are unique by (series,category).
All primary and companion IDs belong to the same current selected CP1 ModuleView.
No duplicated amounts, arithmetic, status or report-wide C/K/S/G IDs in this API;
no ReportView/ChartSpec imports or private source/state access in the producer.
Missing/inapplicable CP1 yields no invented numeric series. Record the exact empty
or refusal policy in tests/handoff; malformed accepted data fails closed.

C2 resolves actual current Fact.amount/status/unit/currency/scale and existing
report-index references. Monetary points retain source-native USD MILLIONS
(scale1000000), ratios MULTIPLE (scale1); do not rescale or recalculate them.
Known zero remains plotted. Nonknown existing facts use their actual G# reference;
do not invent a gap fact or passport. Empty unsupported figures carry a reason.
Use existing format_value/fact_spelling and ChartSpec coherence checks. A table
twin may use one point per row so its flattened cell texts equal mark texts in
point order. Preserve companion date/basis/facility references visibly or through
the existing fact passport path; compact calculation cards need not repeat the
full fact passport. No synthetic chart values or manually authored HTML/SVG.

## Exact disjoint leases and route

After LEAD freezes/reviews this contract and PR MANAGER integrates its exact commit:

C1 starts a new clean branch at exact5a4d3c plus the admitted contract commit, with
existing untracked work preserved. Own only NEW
`src/deploy_workflow/financial_series.py`, NEW `tests/test_financial_series.py`,
and `docs/handoffs/cp1-series.md`. It is a pure deterministic projection. Do not
edit workflow/receipt/source tools, ModelReport, imported core or C2 files.

C2 starts from the same integrated base and owns only
`src/deploy_vii/report_view.py`, NEW `tests/test_cp1_chart_render.py`, and
`docs/handoffs/cp1-chart-rendering.md`. Integrate the producer at the existing
build/_block chart seam after indexing. Existing SVG renderer/assets/render.py/
cp1_render.py/financial_rendering.py/bindings remain outside the lease.
No direct candidate engine/publication constructor or second arithmetic path.

Both financial/provenance implementations and sensitive reviews use explicitly
requested GPT-6.1 Sol/high per AGENTS.md, with actual dispatch evidence and no hidden
telemetry claims. Each coordinator owns its causal RED->GREEN focused checks,
confidence-review, independent sensitive review and no-argument post-edit
rewrite-tournament before completion/commit. Existing source dependencies and
public interfaces stay unchanged; ask LEAD for an exact named lease if required.
They are not alone and must not revert others' work.

LEAD owns this contract/oracle, PLAN.md, MODULES.csv, TEAM.json and QUEUE.md.
PR MANAGER alone integrates exact LEAD-admitted commits and records the targeted
report_view post-import patch in docs/reuse/manifest.json (original baseline entry
unchanged, separate current patch SHA/project commit/reason/review), with its
integration receipt. No additional historical files are imported or modified.

## Checks and actual end-to-end acceptance

1. Freeze source-first independent chart oracle and reviewed interface before code.
   Confirm type field agreement; integrate exact contract, then release two lanes.
2. C1 focused tests pin selection/identity/units and independent known/gap values.
   Cover missing quarters, denominator/nonknown facts, missing RCF versus0, term
   headroom exclusion, FY/Q4 deduplication, missing maturity/incomplete population,
   mixed currency/scale, malformed references and ambiguous period joins.
   Pure small ModuleView fixtures are component evidence, not analyst acceptance.
3. C2 focused tests must first reproduce fallback, then assert real four-chart
   figures, numeric/gap mark identities, exact table twins and existing passports.
   Cover malformed/foreign point or companion refs and status/pathway isolation.
   Refuse forged serialized series through the authentic delivery/publication
   checks; do not label altered publication as a genuine missing-source case.
4. Review exact final diffs and run only relevant checks on frozen final bytes.
   At most one heavy local job and two disjoint implementation lanes. LEAD checks
   processes/load, hashes and admits exact command/PID/UTC/logs/exit into QUEUE.md.
   Quiet jobs are not restarted; no writers change admitted source during a job.
5. Integrate exact reviewed producer and renderer. C1 is the sole Execution writer
   for a fresh actual internal offline positive CP0→five CP1 stages→QA/promotion→
   public publish_cp_model→sealed financial receipt. Use the same frozen source,
   author actual reviews from returned analytical tool/projection bodies and retain
   raw lineage; do not replay helpers as analyst tool-use evidence. A fresh run is
   required because public Execution.begin refuses a second settlement of the
   same input set. No journal pointer/attempt edits, fork API, raw HTML rewrite or
   reuse of a sealed workflow instance. Independently freeze/check new raw QA
   inventory before promotion; do not assume prior58 merely from identical source.
6. Run a fresh genuine missing-financial-source case with actual CP1/publisher
   refusals and no Model files. Preserve both prior packages unchanged. Close all
   owned CLI processes with EOF and retain final snapshot/receipt/file hashes.
7. C2 consumes the actual final receipts read-only through unchanged
   render_financial_slice; canonical model.html/calculation.json/receipt.json stay
   byte-exact copies of the NEW actual publication, with verifier rederivation.
   Report and canonical HTML serialized chart figures must agree on values,
   series/category order, basis/unit/reference semantics; calculation JSON must
   independently agree on the underlying financial and facility evidence.
8. Native browser proof on immutable real outputs: both report chart strip and
   canonical Model route show all four actual SVGs; click Chart/Table toggles and
   mark/keyboard passport interactions. Check exact serialized Q4 5/3,1,6, three
   early-quarter gaps, quarter cash values/zero RCF, one2029 principal50 with
   source maturity/snapshot. Verify current CP1/Model/pack refs, source hash/page/
   quote, units and distinct trailing basis; restricted QA/readiness/limits;
   click calculation link and prove exact canonical bytes. Gap shows no invented
   charts/Model. Use supported bounded native DOM/screenshots for large HTML;
   no full-page AX success claim if bridge frame limit persists, no denied app
   control bypass, no injection. Close only owned tabs/servers and rehash outputs.
9. PR MANAGER runs one justified relevant assembled offline check after a fresh
   resource admission. Package portable real stores/receipts/publication/report/
   native proof and SHA index in a NEW cp1-chart-slice output folder. LEAD closes
   only these proven CP1/Model chart links; all other qualification stays open.

## Rulings

- Existing explicit user team/slice instructions and PLAN.md execution method
  authorize completing this implementation without a new planning approval round.
- Plotted Model output means canonical published HTML charts and their authentic
  serialized ReportView marks, with unchanged financial-model/3 underlying JSON.
  Adding a separate series financial schema would widen the requested slice.
- Fresh actual full run is chosen over a new revision/fork state API; this costs
  local offline execution time while preserving public state/provenance invariants.
- Maturity uses current principal classified by final contractual date, with
  explicit snapshot/convention; it does not predict future outstanding balances.
