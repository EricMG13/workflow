# C: CZR declared cash scope — build (stage contract; mx-feature; sensitive: financial reconciliation)

Rules: `W/work/build/stage8-vii/common.md` (read first). Branch: `claude/s8-vii-c`. The plan is `W/work/build/stage8-vii/C-cash-plan.md`: implement it exactly as written, with the rulings below. Edit only:
`src/deploy_vii/financial_contracts.py`, `src/deploy_vii/financial_reconciliation.py`, `src/deploy_vii/period_reconciliation.py`, `src/deploy_vii/statement_validation.py`, `src/deploy_vii/cash_bridge.py`, and new `tests/test_cash_scope.py`, `tests/test_czr_cash_scope.py`.
The user approved these five src files directly in the s8-vii session (the first three with the group, `financial_contracts.py` and `cash_bridge.py` afterwards: "Yes, both").

## Inputs
| What | Where | Why |
|---|---|---|
| Plan | `W/work/build/stage8-vii/C-cash-plan.md` §1-§9 | exact design, numbers, tests |
| Root cause | `W/work/build/stage7/cash-diff.md` (its locators are corrected by the plan, fault (b)) | background |
| Filing lines | `W/work/build/keep/s7-cash/probe_scope_arith.py`; `cases/czr-2026q2-earnings-update/documents/*.txt` | exact quotes and values |
| CZR helpers | `tests/czr_runs.py` (`czr_closed`, `make_pack`) | the CZR proof test |
| Serializer precedent | `src/deploy_vii/execution.py:117-122`, :170-175 | drop-None wrap serializer idiom |

## Rulings (controller)
- R1: the declaration lists its items (plan fault (a)); no fixed three-balance scope.
- R2: G2 and G3 go in `cash_bridge.cash_bridge_issues` (it runs beside `statement_issues` at `financial_validation.py:135-137`). Issue texts, exactly:
  - G2: `f"Cash scope citation must cite the period's CFS cash line: {bridge_id}"` — when no `cash_scope.citations` entry equals a citation of the same period's CFS line with `item_id` in `{"net_cash_change", "opening_cash", "closing_cash"}`.
  - G3: `f"Declared cash scope balance missing: {bridge_id} {item_id} {date.isoformat()}"` — for each date the check uses (the flow period's end date and the day before its start date) at which a BS `cash_and_equivalents` line is stated, each declared item lacking a BS line there (any status).
- R3: `live/prompts.py` is not edited; the `CashMovementBridge` docstring (and `CashScope`'s) explains the field in one or two sentences each.
- R4: no double-counting validator (the arithmetic shows any nonzero movement as a difference).
- R5: no schema-version bump (plan §1).

## Tests (RED first, exact values)
Exactly plan §8, plus G2 and G3 cases in `tests/test_cash_scope.py` (a scope citing a non-cash CFS line → the G2 issue; the fy-2025 book without the 2024-12-31 noncurrent row → the G3 issue with that date) and one test that a book with no `cash_scope` anywhere gives byte-identical `model_dump_json()` for every bridge and the same `content_hash` for a `Reconciliation`/`PeriodCheck` as a bridge built without the field would (compare against a literal JSON string you write from the contract).
The CZR proof test (`tests/test_czr_cash_scope.py`) must not edit anything under `cases/**`.

## Also report
- Every test file or fixture you find (grep) that pins prompt text, the sent JSON schema, a schema hash or a BS item list, which the new optional item or the new field could change; the controller runs them.
- Node ids: which fail at RED (and why), which must pass at fix.
