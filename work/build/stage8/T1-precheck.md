# T1: H01 + H02 + H08 in the item 70 precheck (stage contract; mx-feature)

Rules: `L/work/build/stage8/common.md`. Before any edit, run `git checkout -b claude/s8-precheck 61a86c10` and confirm the tip. Edit only `src/deploy_workflow/financial_workflow.py` and `tests/test_czr_fixes.py`.

## Inputs
- Rulings `L/docs/rulings/2026-10-29-stage3.md`, items 70, 84 and 85.
- `K/CONSOLIDATED.md` rows H01, H02 and H08.
- Probes `K/probes/v-cp1/probe_h01_h02_h08.py` and `probe_h01_coverage.py`. They show each defect; read them for the exact inputs.

## Findings
- **H08** (`_statement`, :432-447). Implement ruling item 84:
  - the page heading wins when the page names exactly one statement kind;
  - otherwise the caption decides, and only if it names a statement outright (CASH FLOW, BALANCE SHEET, or a full statement phrase such as STATEMENT(S) OF OPERATIONS, STATEMENT(S) OF INCOME, INCOME STATEMENT);
  - a bare word such as INCOME in a caption names nothing;
  - change `tests/test_czr_fixes.py:194-195` to the new outcomes, (`"CASH FLOW ITEMS"`, `"INCOME STATEMENT"`) → IS and (`"Income"`, `"BALANCE SHEET"`) → BS, and add the H08 case: the caption "ADJUSTMENTS TO RECONCILE NET INCOME TO NET CASH PROVIDED BY OPERATING ACTIVITIES:" on a page headed CONSOLIDATED STATEMENTS OF CASH FLOWS → CFS.
- **H01:** a 6-month source satisfies a 9-month YTD period, because the duration is dropped at :470, :493, :536 and :565. Keep the month count in the flow spec, match the span exactly, and fail closed.
- **H02:** an annual header with full-date cells falls through to the balance specs, so Q4 satisfies FY (:588-611, `_hit` :538). After a flow span row, do not fall back to balance specs. Header extraction in `src/deploy_vii/statement_extract.py` (D2b) is out of scope.

Keep every existing `tests/test_czr_fixes.py` case green except the two H08 assertions this ruling reverses. The real-filing cases in that file (the CZR 10-Q and 10-K pages) must still map as before.
