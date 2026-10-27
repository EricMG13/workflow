# Task4-A3 — CP1B bindings and FP02 report specifications

Status: frozen pre-implementation component contract; implementation requires
LEAD's committed exact-base admission in docs/QUEUE.md. This is not actual owner,
consumer, selected-run render, native or CP1B checkpoint acceptance.

## Authority and exclusive boundary

Reuse the independently reviewed A1 contract docs/CP1B-CORE-LEASE.md, SHA256
b32b91f8fdf562d101e3c37cd14336a640f1baeac6d4ced93111fc6bc21d767d,
and cases/earnings/expected.json, SHA256
041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599.
The source-first numerical conclusions of C3 preparation and independent reviews
are reused, not re-audited. C2 preparation commit
0259861308f19a788ee097283fd107a878286294 / file SHA256
c70bea51d4d6258b5be25cfd3cd54b0a8849c1099f3c191cf6e3dd53887098c5
is a proposal resolved by this contract; its zero-prior not_applicable proposal
is superseded by A1's missing/ZERO_DENOMINATOR rule. Independent render oracle:
cases/earnings/render-expected.json. The financial manifest and source hashes in
that oracle remain unchanged. Review: work/cp1b-preparation/render-contract-review.md.

C2's eventual exclusive files, and no others:

- NEW src/deploy_vii/bindings/cp1b.py
- src/deploy_vii/bindings/shipped.py
- src/deploy_vii/report_view.py
- NEW tests/test_earnings_render.py

No assets, general slot rewrite, replacement renderer, runtime wrapper, live,
registry, source/access, core arithmetic, earnings workflow or prior publication
changes. C3 owns the future producer; C1 owns separately leased access/complete
CP5 scope. PM integrates. LEAD owns cases/shared contracts/plan/queue/team.
This reviewer writes only this lease, render-expected.json and its review report.

Reference source inspected: main2463dcb6776404e0bafe6c9b30a25c699db288d4;
C2 proposal inspected d04c19cb237c4125dcb3765cb0745479913a4430 lineage.
The implementation base must be the exact subsequent PM-integrated contract and
prerequisite revision recorded by LEAD; neither reference is an automatic code
admission. Uncapped implementation does not remove exclusive leases, frozen
source, one-heavy-job admission, Sol/high sensitive semantics/review or the
paid/provider/live pause. Route evidence is the explicit Sol/high assignment;
no hidden runtime telemetry is claimed.

## Consumer input and component status

Consume the existing canonical ModuleView(module_id='CP-1B'), Facts and ordinary
ReportTables; no alternative financial values, label joins or new series API.
C2 introduces shipped map CP1B once, immediately after CP1 in SHIPPED_MAPS.
The small CP1B layout guard in report_view checks any output-bearing/shown CP1B
before layout consumption, including a candidate component preview. It is
structural, not run/issuer/grant/settlement authentication. Candidate, accepted
and restricted use the existing SHOWN_STATUSES; do not promote any status.

Fixtures are explicitly synthetic, seeded component previews. Their run has
case_kind='synthetic', pathway='earnings_update', an explicit requested module
set and candidate CP1B; all fixture hashes/IDs are labelled fixture identities,
never actual settled receipts. A restricted shown-state fixture may test existing
presentation only. Other owners remain honestly unrun/not_in_pathway unless a
separate fixture supplies their actual declared data. No fake CP5 outcome,
publication, owner tool invocation or qualification flag is allowed. Existing
unrun/blocked/stale behavior must not inherit an earlier fixture's rows. A3 does
not establish a new settlement/status/QA rule. Actual module policy belongs to
the later C3 owner contract.

## Canonical layout — fixed in both earnings cases

Exactly three ReportTables, ordered T1B.1, T1B.2, T1B.3, interface_id=None.
Each has row_header='Measure' except T1B.3 row_header='Assessment'. All rows have
row_kind='row'. Every canonical fact belongs to one of these cells exactly once;
there are no undeclared extra facts or duplicate coordinates. Canonical fact ID:
`cp1b:{table_id}:{row_id}:{field}`. No CP1 T4 identity is borrowed. Titles, ordered
fields, row IDs/labels, bindings and visible headings are frozen in the oracle.

| Table/title | Ordered fields | Ordered row IDs |
| --- | --- | --- |
| T1B.1 / Paired earnings results | prior,current,delta,growth | revenue,ebitda,adjusted_ebitda,ebitda_margin,cfo_reported,capex,fcf |
| T1B.2 / Balance changes | prior,current,delta | cash_closing,total_debt,net_debt |
| T1B.3 / Evidence and analytical gaps | assessment | variance.summary,drivers,guidance,comparative.prior-year,comparative.trailing-leverage,evidence.inputs,scope.limitations |

T1B.1 and T1B.2 bind as whole tables, preserving columns. T1B.3 has exactly one
assessment Fact per row and exact-row bindings; the existing row fallback's
single Value column loses no assessment column. No whole-table wildcard T1B.3
binding, and no whole-table plus row double binding. Every slot is unique and
starts cp1b-. Binding defaults are presentation defaults only; each cell uses
its own canonical Fact unit/status. T1B.1 default unit_class='text' (mixed native
amount/percent/pp); T1B.2='amount'; T1B.3='text'.

| Coordinate | Destination | Exact cell slot / label |
| --- | --- | --- |
| T1B.1 / all rows | headline-results | cp1b-paired-earnings / Paired earnings results |
| T1B.2 / all rows | kpi-changes | cp1b-balance-changes / Balance changes |
| T1B.3 / variance.summary | variance-drivers | cp1b-variance-summary / Numerical comparison |
| T1B.3 / drivers | variance-drivers | cp1b-drivers / Driver evidence |
| T1B.3 / guidance | guidance-signals | cp1b-guidance / Guidance evidence |
| T1B.3 / comparative.prior-year | limitations | cp1b-prior-year-gap / Prior-year comparison |
| T1B.3 / comparative.trailing-leverage | limitations | cp1b-trailing-leverage-gap / Leverage comparison |
| T1B.3 / evidence.inputs | evidence | cp1b-input-evidence / Selected input evidence |
| T1B.3 / scope.limitations | limitations | cp1b-scope-limitations / Scope limitations |

## Four FP02 specifications

Add exactly these CP1B specs to _EARNINGS_UPDATE. Each owner='CP-1B',
producers=('CP-1B',), collapsed=False, width='full', numbered=False,
pinned=False, dated=False, route_label='Full analysis'. The existing producer
route yields full_analysis_route='CP-1B' for populated blocks. Empty states use
existing honest status behavior; no fabricated populated route/content.

| ID | Title | Kind |
| --- | --- | --- |
| headline-results | Headline results | dense |
| variance-drivers | Variance drivers | prose |
| kpi-changes | KPI changes | dense |
| guidance-signals | Guidance signals | prose |

Do not change pathway block order, CP1-owned metric-strip or EBITDA-adjustments,
chart figure count/source, CP1 maps, Model links or other pathways. Full analysis
#CP-1B retains all three declared tables and canonical fact passports. CP1B
bindings do not qualify CP1D, CP-MODEL or the rest of FP02.

## Values, period scope, units and display

E-QOQ-FLAT uses own q3-2025 and q4-2025, distinct sequential92-day quarters.
Headings are exactly the oracle's ID/date headings. Prior/current facts keep
actual own-period IDs/basis; delta/growth period is the explicit derived pair
`q3-2025->q4-2025`. This pair descriptor is not an invented source period.
Never use FY/LTM just because values coincide. Core's twelve points project to
seven earnings plus three balance rows; the two leverage points are summarized
honestly in comparative.trailing-leverage with both current operand references,
prior missing status/reason and no invented leverage change. They are not extra
hidden rows/columns in either paired table.

E-NO-YOY explicitly requests absent fy-2024 versus actual fy-2025. The same
seven+three rows remain. All current FY facts, including cash20/debt50/net debt30,
remain known with actual current coordinates. Prior/delta cells mean only the
requested absent FY2024 basis and are missing/COMPARATIVE_NOT_SUPPLIED; the three
applicable growth cells are missing too. This does not assert absence of all
2024 balances: opening-2024 is an existing balance snapshot and is neither
silently substituted for the requested FY income basis nor called missing.
The prior heading is Requested fy-2024 (not supplied), with no invented FY2024
dates/basis/operand IDs; current heading carries actual FY2025 dates. The table
limitation states this scope. Opening-to-closing balance comparisons
would require a separately selected/frozen basis, not renderer inference.

Amounts: unit MILLIONS/currency USD/scale1000000. Margins and growth: PERCENT
fraction/currency None/scale1. Margin delta core PERCENTAGE_POINTS maps to Fact
unit 'pp'/currency None/scale1 as presentation only: no multiplication/division,
recomputation, quantization or value change in C2. Other deltas retain amount
units. Every Fact.decimals=None here. Whole-million display follows the existing
ROUND_HALF_UP formatter (7.5->8,4.75->5,-2.5->(3),1.25->1). Full canonical
values/passports retain exact1.25; table display is never claimed exact1.25.
Margins25.0%, zero growth0.0%; pp uses the existing exact-text path ('0 pp' and
artificial '5 pp'), not a percentage-class conversion. Literal spellings pin the
seeded fixture Decimal representations; equivalent actual pp values may preserve
trailing zeros (0.00 pp/5.00 pp) on that exact-text path. Do not quantize just to
remove them. No source number changes.

Known0 remains known; null missing/conflicting/not_applicable cells use allocated
G# gap references and existing spellings. Never hard-code G/K/S numbers. Relative
growth exists only for revenue,ebitda,adjusted_ebitda. Other growth cells have
amount/text None, status not_applicable and a reason. All three growth measures
with known-zero prior have amount None, status missing and ZERO_DENOMINATOR;
never not_applicable,0,infinity or a renderer calculation. A1 same/reverse/
incompatible-period refusals occur upstream with no CP1B output; A3 cannot
manufacture an apparent decrease or substitute another selected period pair.

## Assessment semantics and evidence surfaces

T1B.3 assessment facts have unit/currency None, scale1, decimals=None, amount=None.
Known records contain nonempty text; missing records contain no text and a
nonempty limitation/citation context. Exact row status/required content is in
the oracle. Required semantics:

- variance.summary: known bounded numerical finding for the positive; missing
  COMPARATIVE_NOT_SUPPLIED for the no-YoY request. Flat earnings does not prove a
  price/volume/FX explanation. No unreviewed driver or guidance assertion.
- drivers and guidance: missing with distinct evidence-gap reasons. A financial
  statement is not management guidance or operational KPI disclosure.
- comparative.prior-year: missing prior-year income series in both cases.
- comparative.trailing-leverage: missing Q3 trailing comparator for positive,
  missing requested FY2024 comparator for no-YoY. Preserve actual current total/
  net leverage and reasons in evidence/Full analysis; no missing-current claim.
- evidence.inputs: known evidence record, not invented numeric answers. Identify
  selected CP1 artifact hash, requested pair, all twelve selected core points,
  role-to-primary/companion fact IDs/basis coordinates and actual citation handles;
  absent prior operand reference remains null/absent, never fabricated. Full
  current CP1B artifact identity comes from ModuleView/full-fact passport, not a
  self-hash inserted into its own hashed payload. A3 fixture records are labelled
  component fixture records; actual verification is the later owner's job.
- scope.limitations: known bounded scope text; actual Module.limitations must
  also carry every adopted source/analytical limitation below.

Known numeric prior/current cells preserve upstream source/value-class semantics
and citations. Known delta/growth cells have calculated value_class, unique
calculation_id, formula and both available operand references/citations; no
new quote/source handle. The later C3 composer/receipt contract owns exact
machine-readable operand encoding and actual lineage verification. A3 requires
that canonical existing fields/Full analysis evidence preserve the references;
it may not claim authenticated lineage from a textual ID. Rendering must expose
canonical status, period, basis, currency, scale, citations, exact source/stated
values where applicable, formula and artifact hash through the existing fact
passports. The current selected CP1 inputs remain separately inspectable.

The Evidence rail is the existing source inventory and source passports (exact
source hashes, readiness, locators, quotes/content and supplied limitations).
Binding evidence.inputs to evidence establishes binding coverage, not a visible
CP1B rail table: the record remains visible in Full analysis. Limitations rail
shows Module.limitations, not arbitrary bound T1B.3 rows. Therefore Module.limitations
must explicitly retain unaudited/consolidated IFRS USDm scope, missing prior-year
income, missing Q3 trailing comparison where applicable, missing drivers and
guidance/operational KPIs, bounded flat comparison/no broader nonzero earnings
qualification, and component-preview/no owner or CP5 acceptance in fixtures.
No assets lease is needed or implied. Native rail acceptance cannot be asserted
until a later actual selected run proves these existing surfaces.

## Fail-closed layout and oracle checks

Add a CP1B-specific guard, not a generic permissive fallback. With shown CP1B
outputs require exactly the three tables/ordered fields/ordered rows/labels,
interface_id=None, exact fact-ID/coordinate mapping and full coverage (44 cells:
28+9+7). Reject duplicate/missing/extra tables, columns, rows, facts or identities;
wrong ordering, swapped field pointers, borrowed interface identities, unknown
fields, extra undeclared fact tables and invalid row kind/header. Missing a whole
declared layout must fail, never use _slot fallback to flatten a paired table.
Reuse validate_tables and validate_bindings, supplementing their allowance for
undeclared tables. Reject wrong units/currency/scale/decimals for each role,
nonfinite/malformed known/nonknown value shape, numeric assessment facts and
numeric/text shape mismatches. Keep enum status and missing reasons, and enforce
not_applicable growth on the four nongrowth rows; do not rewrite input statuses.
Do not hard-code source-case values or calculate financial truth in this guard.

Independent tests compare the seeded canonical facts and projected ReportView
against the oracle: exact ordered visible headings/rows/columns, values/units/
periods/statuses, known-zero versus missing, flat summary/gaps, evidence records,
Full analysis route, synthetic preview labels and limitations. Explicit mutation
cases verify every rejection class above, binding coverage/double binding and
cross-module/CP1 metric-strip isolation. Test zero-prior for each of three growth
rows and5pp as artificial presentation guards; these are not source/owner cases.
Wrong period/dimensions/forged lineage require the real owner/receipt refusal
later; A3 tests may prove no rewrite/passport loss, not actual authentication.
There is no exception-to-empty, catch-all binding, fake settled hash, ready flag
or fallback invented answer.

## Execution and handoff

No tests, engines, providers or native rendering run during this freeze. Later
source-only focused check, after exact integrated-base/resource admission, from
the C2 checkout (no sync/broad suite):

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_earnings_render.py`

This is a component source/test check, not actual analytical execution. Record
exact argv, base/source/case/oracle/runtime hashes, PID/UTC/exit and complete logs.
Retain causal failures and checks; confidence-review and no-argument changed-
function rewrite-tournament plus independent sensitive review precede completion
and commit. PM-only integration, one-heavy-job rule and paid/provider pause remain.

A later exact C3 owner receipt/verifier contract, C1 complete selected CP5 scope
and settled evidence-referencing CP5 consumption, and a separate C2
src/deploy_workflow/earnings_rendering.py lease are prerequisites to actual
selected-run acceptance. Freeze actual requested/head sets there; no preset proves
CP1D/Model ran. A3 cannot weaken financial_rendering.py, relabel Task3 runs, fake
portable receipts or authenticate stale/foreign runs from ModuleView alone.
Future native acceptance must prove current owner/consumer and source/operand/
artifact identities, actual FP02/Full analysis/Evidence/Limitations surfaces and
unchanged files. Broader CP1B/FP02/nonzero earnings/production remains unaccepted.

Not verified: product implementation, component test results, actual owner/receipt/grants, complete CP5 consumption, selected-run export, native visibility or providers.
