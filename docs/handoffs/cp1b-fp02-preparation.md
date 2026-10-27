# C2 CP1B / FP02 preparation — proposal for freeze and independent review

Preparation-only lease: this NEW file. No product writes, tests, browser, server,
engine, analytical execution or provider calls. Base inspected and branched:
`d04c19cb237c4125dcb3765cb0745479913a4430`, branch `codex/cp1b-fp02-preparation`.
C3 source authority is `07cf6dee33006d629cee3aab2702cbc590eb5030`,
`docs/handoffs/earnings-preparation.md`, SHA256
`246edc7d2dfb65a8d3eaa9737be7727147295fb5241caab8b7d4bea1ad444955`.
Table IDs T1B.1/T1B.2/T1B.3 are LEAD's direction; remaining names/shape below are
proposed until LEAD freezes the contract/case and independent Sol/high checks it.
No numerical implementation-lane cap is introduced. Exact disjoint leases,
one-heavy-job/process/load admission, frozen inputs/source and paid/provider/live
pause remain. Task3 case/publication/delivery/native leaves remain frozen.

## Actual seams and minimum later lease

Intended later C2 files: new `src/deploy_vii/bindings/cp1b.py`,
`src/deploy_vii/bindings/shipped.py`, `src/deploy_vii/report_view.py`, and new
`tests/test_earnings_render.py`. C3 owns earnings.py/core and later workflow;
C1 owns separately leased registry/upstream/CP5 access. PM owns integration and
reuse-manifest post-import patch records. None is a present product-writing lease.

Static findings:

- FP02 already lists headline-results, variance-drivers, kpi-changes and
  guidance-signals, but `_EARNINGS_UPDATE` defines only the CP1-owned metric-strip
  and EBITDA-adjustments. New four-block specs must name owner/producer CP-1B and
  Full analysis route CP-1B: dense/prose/dense/prose respectively. A small CP1B
  shape guard should require the expected table IDs/ordered fields/allowed rows
  before consuming their layouts; no general slot or financial-math rewrite.
- `Binding.matches` selects module/table/exact row/fact, with no field selector.
  Every shown fact needs a binding; repeated hits within one block or across two
  composed destinations fail. Evidence/Limitations count as composed everywhere.
  Outside-pathway bindings may be listed as unplaced, which is not placement proof.
  Do not bind an entire table to a front block AND a rail.
  All cell slots need a unique `cp1b-` prefix; shipped maps currently omit CP1B.
- `_slot` preserves ReportTable columns only for whole-table bindings. A row
  binding flattens facts to one Value column. The one-column T1B.3 proposal below
  avoids a general slot rewrite; T1B.1/T1B.2 use whole-table bindings.
- `validate_tables` requires every fact in a declared table exactly once, matching
  table/row/field coordinates and column order. Metadata cannot be silently left
  outside a declared layout. Friendly date headings/row labels require ordinary
  ReportTables (`interface_id=None`), not borrowed CP1 T4 interface identities.
- `renderSources` is source inventory plus source passports; a rail binding does
  NOT add the bound CP1B register there. `renderLimitations` shows module limitation
  strings, not arbitrary bound gap rows. Proposed bounded Evidence proof uses
  existing inventory/source passports and CP1B Full analysis for operand records.
  C3 must carry adopted gap/scope reasons into Module.limitations. Dedicated new
  CP1B rows ON the Evidence rail would require a separately frozen asset lease;
  do not claim that behavior from bindings alone.

Inspected SHA256: report_view.py
`571ee44cbac0a39c3dd77871e13f7f9cc414c4e6700e9e887a70a64b74b7c4cc`;
bindings/__init__.py `6b2c8cc47d32212b3b236ece8df0abbfd6774d22db767cb6f7ea483841b9a7fc`;
financial_rendering.py
`d511935ca9724de3ed734da87498f786742f2e63ca4a62a68408f9d136b089a8`;
assets/app.js `0a8da6637b8da73a048ac828a1485d0a3227507b89252d9aabe5e8446813779b`.
No additional historical import or browser-asset change is proposed.

## Proposed minimum canonical tables and read API

C2 consumes validated current `ModuleView(module_id='CP-1B')`, its canonical facts
and declared ReportTables. No parallel financial values, renderer arithmetic,
label-based joins or new chart-series API is needed. C3's proposed public
EarningsDeltaReview/EarningsDeltaReport/input/validate/compose/submit APIs remain
C3-owned. Freeze the following output contract before either implementation lane:

| Table | Exact ordered fields | Front placement / rows |
| --- | --- | --- |
| T1B.1 | prior, current, delta, growth | headline-results; revenue, ebitda, adjusted_ebitda, ebitda_margin, cfo_reported, capex, fcf |
| T1B.2 | prior, current, delta | kpi-changes; cash_closing, total_debt, net_debt |
| T1B.3 | assessment | exact row partition below; no whole-table wildcard binding |

The listed financial rows are the proposed flat positive set. LEAD must freeze
case-specific row coverage for E-NO-YOY; do not manufacture gaps for unrequested
balance-sheet comparisons or treat known opening balances as missing income.
Each row has explicit native-unit measure label. Prior/current headings contain
actual selected IDs/dates (Q3 Jul1–Sep30 and Q4 Oct1–Dec31), not generic fiscal
labels. Fact.period retains each actual coordinate; derived facts name the pair.
No implicit comparison to a neighboring column or to FY/LTM is permitted.

Proposed exact T1B.3 rows and exclusive binding targets:

| Row ID | Destination | Meaning |
| --- | --- | --- |
| variance.summary | variance-drivers | evidence-bound flat numerical finding, with no causal-driver claim |
| drivers | variance-drivers | missing price/volume/FX or other driver evidence |
| guidance | guidance-signals | no guidance evidence in selected authorized inputs |
| comparative.prior-year | limitations | explicit absent prior-year income comparison |
| comparative.trailing-leverage | limitations | Q3 trailing leverage/change unavailable; Q4 standalone ratio remains valid |
| evidence.inputs | evidence | selected CP1 hash/pair and role-to-operand fact IDs/citation handles; no copied numeric answers |
| scope.limitations | limitations | unaudited/consolidated/flat-case limits |

One assessment Fact per row permits existing prose rendering. Unavailable
assessment facts carry no amount/text and require actual limitation/citation
context; a factual narrative is not evidence of a quantified causal driver.
C3/public receipt verification must reject extra or missing case-required rows,
unknown fields and forged lineage. C2's shape guard rejects unexpected table/column/
row schemas; binding rejects unbound T1B.3 rows and conflicting destinations.
No permissive catch-all or renderer replacement for semantic/grant validation.
CP1's metric-strip, T4.10/T4.17 and EBITDA-adjustments remain separate foundation
output.

Each paired cell must retain its exact selected CP1 result hash, canonical fact
ID, own-period/basis coordinates and source citations through C3's typed report
and evidence record. Prior/current preserve upstream value semantics; new delta/
growth facts are calculated, with unique calculation IDs/formula and both available
operand identities. A missing comparative has no invented upstream operand ID or
canonical period: retain its requested descriptor, null upstream reference and
named absence alongside the actual current operand. Prior/current cell and Full
analysis clicks expose operand passports; source clicks expose exact source
hash/page/quote. Receipt lineage must resolve those records rather than trusting
text IDs alone. The current CP1B artifact hash
comes from settled ModuleView.artifact_sha256/full-fact passport; do not insert an
artifact's own eventual hash into its hashed payload or hard-code K/G/S numbers.

Native units: money USD/MILLIONS/scale1000000; growth and margin are PERCENT
fractions/scale1/currency=None. C3 computes margin change in percentage points in Python and
may emit unit `pp`/scale1/currency=None. Existing fact_spelling renders that unit
on its exact-text path with an explicit pp suffix; no new display class or UI
multiplication is needed. Relative growth is proposed only for revenue and the
reported/adjusted EBITDA rows; other growth cells are explicitly not_applicable
with reason, unless LEAD adopts another reviewed definition.

## Basis, value, error and display expectations

Source expectations come from C3's reviewed literal proposal, not candidate HTML.
E-QOQ-FLAT uses two distinct discrete 92-day quarters. Revenue30→30, EBITDA7.5→7.5,
CFO4.75→4.75, signed capex-2.5→-2.5 and FCF2.25→2.25 yield known zero changes;
revenue/EBITDA growth is known zero. Cash18.75→20 and debt48.75→50 change by exact
1.25; net debt30→30 changes by known zero. Margin.25→.25 changes by zero pp.
C3 supplies/validates every result in Python; C2 only selects and formats facts.

Existing display rounds money to whole millions: a change of1.25 displays1 by
default, while full facts/passports retain1.25 and scale1000000. Percent formatting
uses one decimal (zero appears0.0%, margin25.0%). Do not describe the visible table
as showing exact1.25 or silently change Fact.decimals. Any precision change needs
an explicit display contract; native exact-fact proof is separate.

E-NO-YOY retains supported current FY2025 income values (revenue120/EBITDA30),
while missing prior income/delta/growth stays null with comparative reasons.
Opening2024 is a balance snapshot, not a prior-year income statement. FY365-day
versus Q4 92-day and same-period pair comparisons refuse; reverse-order refusal
and resulting module status remain LEAD decisions, not inferred policy. Missing
Q3 trailing leverage cannot produce a zero change to Q4's known5/3 or1. A zero
prior revenue is still known zero; propose growth not_applicable with a zero-
denominator reason, subject to LEAD's frozen status definition.

Refuse stale/foreign/unselected CP1/CP1B identity, wrong coordinate/basis,
entity/currency/scale/definition mismatch, nongranted fact/field, forged operand or
citation, duplicate binding and table/column mismatch. Candidate component output
may be labelled as preview by existing contracts; selected-run acceptance needs
verified settlement. Blocked/stale/unrun states never inherit a previous case's
rows or draw invented earnings. Missing comparatives are valid named report gaps;
missing required CP1 authorization is a real workflow refusal with no CP1B output.
No full FP02, CP1D or all-CP5 qualification follows from these bounded cases.

## Authentic selected-run renderer prerequisites — later separate lease

The existing financial wrapper requires requested_modules exactly CP1/CP-MODEL
and an authentic financial-slice receipt. It cannot authenticate an earnings run.
Do not weaken it, edit old receipts, relabel a Task3 run or call a direct composer
as the actual selected-run renderer. A later C2 lease may own new
`src/deploy_workflow/earnings_rendering.py` and focused renderer tests, only after
C3's public workflow receipt/verifier and exact selected-run contract are reviewed.

Proposed public seams: C3 `EarningsSliceReceipt` and
`verify_earnings_slice_receipt(store, receipt)`; C2
`render_earnings_slice(execution_directory: Path, receipt_path: Path, destination: Path) -> Path`.
These names/signatures are proposals. Before implementation C2 needs an actual
strict sealed receipt and portable store, not a replacement local schema/ready flag:

1. Exact run/case/issuer/as-of/method/pathway=earnings_update, case/oracle/source
   pins, pack/final snapshot, requested module set and selected settled head set.
   LEAD must freeze these sets explicitly; the default FP02 preset also includes
   CP-MODEL/CP1D and is not proof either ran. No unsupported run-import API assumed.
2. Current CP1/CP1B result/attempt/status/input hashes, frozen grants and selected
   field/coordinate set; actual bounded upstream arguments/returned bodies,
   evidence-bound analyst submission, validated output and settlement lineage.
3. Actual selected CP5 read/verified/settled review including current CP1B, under
   C1's reviewed multi-producer/claim scope and complete selected review set.
   A lookup or render alone does not close downstream consumption. If this is not
   in the authentic final receipt, actual consumer acceptance remains open.
4. Producer public verification rederives/checks against the authentic audit and
   current snapshot. C2 then confirms same run/pack/snapshot/heads/view, renders via
   unchanged core render/build, re-verifies before staged export/atomic rename,
   and refuses changed/foreign/incomplete inputs or existing destination.
5. New report.html, byte-exact earnings-slice.json and render-receipt.json bind
   inputs/current results/output hashes. If CP-MODEL publication is selected, a
   reviewed extension must verify/export its NEW actual files or refuse scope;
   never leave a calculated-download link without its authenticated file. No old
   Model/publication copies or extra actor raw-pack permissions are implied.

Fresh portable positive/comparative-gap/authorization-refusal runs, clean writer
EOF, exact frozen hashes and separate render/native admission remain required.
Future native proof must cover actual FP02 sections/Full analysis/Evidence source
passports/Limitations, exact operands/current artifacts/known zero versus gaps,
whole-million limits and unchanged files. This preparation grants no runtime lease.

## Confidence review and handoff boundary

Investigated ranked doubts: (1) authentic selected-run authority traced to existing
wrapper's explicit module-set rejection; new public receipt seam is prerequisite.
(2) Double binding/layout loss traced through Binding.matches/validate_bindings/
_slot/validate_tables; fixed proposal uses whole paired tables and single-column
row-partitioned gaps. (3) Evidence/Limitations surface checked in actual app.js;
bindings alone do not display rail registers, so source-passport/Full analysis and
module-limitations obligations are explicit. (4) Exact1.25/percent/pp/zero checked
against display/fact contracts; no UI arithmetic or rounding-before-calc proposed.
(5) Prior-year/own-quarter/trailing confusion checked against C3 literals; no
opening-balance income substitute or missing-to-zero. (6) Current artifact and
operand identity checked against actual full-fact passport and receipt seams;
self-hash/presentation-number authority is excluded. (7) Lease overlap/false
acceptance checked against C3 proposal and current PLAN: C1/C3 prerequisites,
shared asset boundary and downstream CP5 remain explicit.

Verified by static source inspection only; no component test or owner acceptance
claim. LEAD still must freeze exact rows/columns/field semantics, lineage schema,
selected module/consumer/status/direction policy, receipt API/base/files and check
commands after independent Sol/high review. Suggested later focused command from
this C2 clone (NOT RUN; exact dependency/base/admission still required):

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_earnings_render.py
```

Its proposed scope is binding coverage, zero/gap/basis/dimensions/provenance/status,
actual rail visibility and CP1-strip isolation. Doc-only change: rewrite tournament
is exempt. C2 returns this proposal/commit for review; PM alone integrates.
Prior Task3 evidence stays frozen.
