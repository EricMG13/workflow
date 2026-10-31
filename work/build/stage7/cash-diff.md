# CZR NCF_CASH_MOVEMENT differences: root cause (mx-autonomous a2ff1472, 2026-10-31)

The controller wrote this file from the agent's text report. The probes are in `work/build/keep/s7-cash/`. The controller reran `probe_scope_arith.py` (exit 0), which checks every quoted filing line verbatim.

## Cause
Both checks: the filings genuinely differ, and the check's formula does not fit what they print. **The CZR submission is correct**: every term matches the filing.
- The cash-flow statement reconciles the change in **cash, cash equivalents and restricted cash**, including "Restricted and escrow cash included in other long-term assets". The check compares it with the balance sheet's cash-only line.
- fy-2025: 21 + (85 - 95) + (12 - 55) = -32. That is difference 0 under the filing's scope, against 53 under the current formula (10-K page:60 reconciliation table).
- h1-2026: 78 + (96 - 85) + (16 - 12) = 93. That is difference 0 under the filing's scope, against -15 under the current formula (10-Q reconciliation table).

## Why the case files alone cannot fix it
- `CashMovementBridge` components must be same-period cash-flow detail lines (`fx_cash_effect`/`other:*`; `src/deploy_vii/cash_bridge.py:30-41`). The filings print no restricted-cash movement line, so entering one would be a plug.
- The long-term restricted/escrow row is not captured in the submission.

## Honest fix (src/deploy_vii; needs the user's word)
- In `_cash_movement` (`financial_reconciliation.py:512-550`), the submission may declare that the cash-flow scope includes restricted cash. The check then sums the change in each scope balance: balance-sheet cash, balance-sheet restricted cash, and a sourced balance for restricted cash outside the current line, taken from the cash-flow reconciliation table. A missing scope balance stays an absent input, never zero. With no declaration, the check is unchanged.
- It also needs:
  - a balance-sheet item for noncurrent restricted cash (`statement_validation.py:53-60`, `ACCOUNT_LINKS` :131-143);
  - the precheck accepting that row from a cash-flow page.
- The constructed-period checks in `period_reconciliation.py:281`/`:297` must change in step, because they assume two balance terms.
- Effect: fy-2025 and h1-2026 PASS; h1-2025 and fy-2024 become computable; fy-2023 stays absent.
- The case files then add the long-term restricted/escrow rows and the scope declaration, with citations.

## calculation_gate (item 83 Q4: stays BLOCK)
- It is raised because the submission sets `addback_disclosure` to `partial` (`partial-builder/st2.py:200`).
- It clears through the case files, not `src`: enter the release's Adjusted EBITDA reconciliation rows and set the disclosure to `complete`.
- Risk: the EBITDA bridges then become computable and could disagree.
- CZR reaches CP-1 Restricted only with both the cash rule and the add-back schedule.

Not verified:
- The `cash_scope` design, the noncurrent item and the precheck acceptance are untested sketches.
- The period-reconciliation behaviour after the change.
- Whether entering the add-backs leaves the EBITDA bridges agreeing.

## Correction (2026-10-31, from the vii-fixes session's cash-scope plan)
- The cash reconciliation tables are on 10-K **page:61** and 10-Q **page:10**, not page:60 and page:9. The 10-Q table's second column is 2025-06-30 (982 / 85 / 19), not 2025-12-31.
- No `financial_workflow.py` change is needed: `STATEMENT_HEADING` does not match those pages, so coverage skips them. The financials step must read those pages.
- The deploy_vii side adds a BS item `restricted_cash_noncurrent` and a `CashMovementBridge.cash_scope` declaration (on branch claude/s8-vii).
- After that merges, Modules updates the CZR case files and item 82's test 3, which pins the 2 cash BLOCK gaps.
