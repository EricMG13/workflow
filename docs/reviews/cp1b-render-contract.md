# Independent CP1B A3 binding/report contract review

Result: **PASS** for exactly these written pre-implementation artifacts:

- docs/CP1B-RENDER-LEASE.md SHA256 b0de1be5a0ae64dff442b5c6652e7a5d8f6d57328d49cc808f37ca5990a6143d
- cases/earnings/render-expected.json SHA256 7b45f939d2d771611e9b11633f348e7c1174cb7ea0b3eb36eeb20661dc4192c4

This is the independent contract/oracle freeze, not a review of future C2 code,
owner settlement, permission grants, complete CP5 consumption or native output.
The reviewer is independent of the future C2 implementer. LEAD assigned this
sensitive architecture review on Sol/high; this is selected-route evidence only,
not a claim of hidden execution telemetry. No additional review chain is created.

## Inputs and reused authority

Read lead/AGENTS.md, README.md, docs/SPEC.md, PLAN.md and the applicable role
boundaries. C2 preparation was read at commit
0259861308f19a788ee097283fd107a878286294; its file hash matches
c70bea51d4d6258b5be25cfd3cd54b0a8849c1099f3c191cf6e3dd53887098c5.
C3 preparation07cf6dee33006d629cee3aab2702cbc590eb5030 and its completed
independent source/numeric review were reused. Its main handoff was inspected.

Exact A1 authority remains unchanged:

- Core lease b32b91f8fdf562d101e3c37cd14336a640f1baeac6d4ced93111fc6bc21d767d.
- Core expected041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599.
- Financial manifest6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432.
- Financial source82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429.
- Identity source74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4.

Reused lead/docs/reviews/cp1b-core-contract.md and work/cp1b-preparation/
core-contract-review.md/core-confidence.md instead of re-auditing finances.
FY current literals already in the frozen financial manifest are reused for the
no-YoY projection; the freeze adds presentation scope, not a financial policy.
No candidate earnings code/output was used to derive expectations.

Static implementation seams inspected in main, initially
2463dcb6776404e0bafe6c9b30a25c699db288d4. Main advanced concurrently to
091a36d6a51b6d8e53c21351795c2a2f2942e790; these inspected product bytes
remain pinned independently of that coordination/integration movement:

| File | SHA256 |
| --- | --- |
| src/deploy_vii/report_view.py | 571ee44cbac0a39c3dd77871e13f7f9cc414c4e6700e9e887a70a64b74b7c4cc |
| src/deploy_vii/contracts.py | ee1b27f912804ab81887401a99177f99068247e8c4ba53c000b0d3fde0205e74 |
| src/deploy_vii/display.py | efdcd5d60400e47c1210442ed165e0642bcb3770aaaebf526dfcb7b750588398 |
| src/deploy_vii/bindings/__init__.py | 6b2c8cc47d32212b3b236ece8df0abbfd6774d22db767cb6f7ea483841b9a7fc |
| src/deploy_vii/bindings/shipped.py | 304230a5eab8f58cea77e8c00cdd69830d5bd57bd7e549e58e026d8f5655f951 |
| src/deploy_vii/assets/app.js | 0a8da6637b8da73a048ac828a1485d0a3227507b89252d9aabe5e8446813779b |

## Contract rulings and root-cause review

1. **Column loss and duplicate composition.** Binding.matches has no field
   selector; _slot uses ReportTable columns only for a whole-table binding.
   validate_bindings treats rails as composed in every pathway. The freeze uses
   whole T1B.1/T1B.2 tables, exactly one assessment column in T1B.3 and exact-row
   partition of that table. Nine distinct cp1b-prefixed slots cover44 canonical
   cells (28 earnings,9 balance,7 assessment) once. No row is bound twice. This
   resolves the real seam without a generic slot rewrite or assets lease.

2. **Permissive layout omissions.** validate_tables permits undeclared tables;
   ModuleView alone does not require the three expected CP1B layouts. A missing
   layout could otherwise flatten a table and extra facts could bypass the
   proposed projection. A3 requires a CP1B-specific structural guard for exact
   ordered table/field/row/fact identities, labels, headers, null interface IDs,
   native units/status/value shape and coverage. The oracle has13 causal mutation
   classes. No catch-all binding, exception-to-empty or guessed layout is allowed.
   The guard preserves canonical values; it is not another financial calculator.

3. **Source and limitation visibility.** Static app.js inspection shows that the
   Evidence rail renders source inventory/source passports, while Limitations
   renders Module.limitations. Rail bindings alone do not render CP1B assessment
   tables there. The freeze makes this explicit: input records are visible in
   Full analysis, source inventory/passports remain existing Evidence behavior,
   and every adopted scope/gap reason must also be in Module.limitations. No
   claim of CP1B rail-table visibility or actual native acceptance is made.

4. **Zero, missing and percentage points.** C2's zero-prior not_applicable
   proposal is superseded by frozen A1: each of revenue/reported EBITDA/adjusted
   EBITDA retains a known delta but missing growth/ZERO_DENOMINATOR. Four other
   earnings growth cells are reasoned not_applicable. Core PERCENTAGE_POINTS may
   map to Fact pp with identical numeric value/scale1, never UI arithmetic.
   Existing exact-text pp display may preserve Decimal trailing zeros; forcing
   0 pp by quantizing an actual0.00 would be an unleased value rewrite. The
   oracle's literal0 pp/5 pp spellings pin only its seeded Decimal fixtures;
   equivalent actual pp representation remains allowed. Whole-million monetary
   strings are separately frozen from exact canonical values/passports.

5. **Missing income does not erase balance data.** E-NO-YOY retains all actual
   current FY2025 values, explicitly cash20/debt50/net debt30 known. Prior/delta
   cells refer only to the requested absent fy-2024 comparison basis, consistent
   with A1. Opening-2024 balance data is explicitly existing, not called missing
   and not silently aliased into FY2024 income. The prior heading is a requested
   descriptor without invented dates/basis/operand IDs. LEAD confirmed this scope
   during review. This is a presentation clarification, not new arithmetic.

6. **No false summary or missing-ID inference.** A static draft review caught
   the gap oracle inheriting positive flat-quarter summary semantics; corrected
   to a missing comparison/current-facts-retained/no-deterioration finding. The
   positive evidence requirements now preserve actual existing nonknown Q3
   leverage fact IDs; only genuinely absent requested operands have null
   references. Q4/FY current standalone ratios remain known; no leverage delta
   is fabricated. These were corrected before binding the PASS hashes above.

7. **Authentication versus preview.** ModuleView carries no authenticated
   current-run/grant/settlement context. A3 fixtures are synthetic candidate
   previews with explicit fixture identities, never fake actual receipts/CP5
   outcomes. Known delta/growth passports retain supplied formula/operand/source
   references; the later C3 owner receipt contract must freeze exact encoding and
   verify their authenticity. Same/reverse/incompatible and stale/foreign/
   nongranted/forged lineage refusals belong upstream, with no renderer fallback.
   A3 does not pretend structural coverage proves those semantic refusals.

8. **Owner and pathway boundaries.** Exactly four future C2 files are leased;
   no assets, wrapper, live/registry, source/access or core changes are included.
   Four new FP02 specs use CP-1B owner/producer/Full analysis route, while CP1
   metric-strip, EBITDA-adjustments and Model publication stay separate. Full
   CP1B/FP02 acceptance still needs actual C3 owner receipt, C1 complete selected
   CP5 scope and settled evidence-referencing review, then separately leased C2
   earnings_rendering and admitted native proof. Uncapped implementation,
   one-heavy-job admission and paid/provider pause remain intact.

## Activity and readiness

Only the three requested lead artifacts were written. No product/test file,
core oracle, financial source, plan/queue/team or other reviewer's file was
modified by this reviewer. Concurrent docs/QUEUE.md changes were observed and
left untouched. JSON was parsed with stdlib only and its inventory printed for
static inspection: three tables with7/3/7 rows and4/3/1 columns;37 numeric cells
plus7 assessments per case; nine bindings;13 rejection guard classes; both cases'
current balances remain known. No product imports or runtime renderer ran.
Whitespace inspection reported no diff error. Core hashes were rechecked unchanged.

The executing-plans skill named by PLAN.md was read for scope/record discipline;
implementation/TDD/job steps do not apply to this docs-only independent freeze.
Confidence-review and rewrite-tournament are mandatory for the later C2 product
changes; no code was written here. The ranked doubts above are this specification
review, not a falsely claimed implementation workflow pass.

No contract blocker remains for A3 component implementation after LEAD's exact
committed integration/base/resource admission. The pinned later focused argv is:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_earnings_render.py`

That command was not run. Actual selected-run owner/receipt/complete CP5/native
requirements remain prerequisites to later acceptance, not blockers to this
bounded seeded component lane. No actual implementation or acceptance is inferred
from this PASS.

Not verified: future C2 implementation or tests, actual owner/receipt/grants/settlement, complete selected CP5 consumption, selected-run export, native visibility, broader nonzero earnings or provider/production behavior.
