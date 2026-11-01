# C-plan: CZR declared cash scope — trace and plan (stage contract; mx-autonomous, read-only)

You plan; you write no code. Read `W/work/build/stage8-vii/common.md` for paths and authority. Read code at `W` (lane tip 5a1d2e2f). Return the plan as text (the controller writes it to `W/work/build/stage8-vii/C-cash-plan.md`), at most ~2.5k tokens.

## Inputs
| What | Where | Why |
|---|---|---|
| Root cause + "honest fix" | `W/work/build/stage7/cash-diff.md` | the design you make exact |
| Arithmetic proof | `W/work/build/keep/s7-cash/probe_scope_arith.py` | the filing numbers both checks must hit |
| Check code | `src/deploy_vii/financial_reconciliation.py` `_cash_movement` :512-550, `_balance` :208, `_check` :138, `_term` :107 | the formula to extend |
| Constructed periods | `src/deploy_vii/period_reconciliation.py` `_period_cash` :262-310 (`source.components[2:]` assumes two balance terms) | must change in step |
| Items | `src/deploy_vii/statement_validation.py` `CORE_ITEMS`/`OPTIONAL_ITEMS` :40-90, `ACCOUNT_LINKS` :93-143 | the new noncurrent restricted-cash item |
| Contracts | `src/deploy_vii/financial_contracts.py` `CashMovementBridge` :367, `FinancialBook` :433 | where the declaration lives |
| In-flight item 82 | branches `claude/s7-absent-input`, `claude/s7-absent-input-2` (`canonical_audit.py`, `canonical_gaps.py`); `W/work/build/stage7/recon-plan.md` | how absent inputs of NCF_CASH_MOVEMENT are classed; must not collide |
| CZR case | `cases/czr-2026q2-earnings-update/` (partial submissions, `partial-builder/st2.py`, documents) | what rows the proof adds |
| Rulings | `W/docs/rulings/2026-10-29-stage3.md` items 75, 82-85 | scope and constraints |

## The design to make exact (user-approved)
The submission may declare that the cash-flow statement's cash scope includes restricted cash. `_cash_movement` then sums the change in each scope balance: BS cash, BS restricted cash, and a sourced noncurrent restricted/escrow balance from the CFS reconciliation table. A missing scope balance stays an absent input, never zero. With no declaration, nothing changes (same check output, byte for byte).

## Answer each, with file:line evidence
1. **Declaration.** Where it lives (a `CashMovementBridge` field, a `FinancialBook` field, or other), its exact name, type and default, and whether it must carry citations (the CFS heading "cash, cash equivalents and restricted cash"). Show whether adding the field changes: the JSON schema the model is shown; serialised bytes or hashes of stored artifacts, frozen fixtures and `cases/pins.py` pinned paths (does `Contract` dump defaults?); stored journals that rebuild. Prefer the option that leaves every stored artifact and pin unchanged.
2. **Noncurrent item.** Exact item id, statement, core vs optional; whether `restricted_cash` today reaches `_balance` at all (via `effective_accounts`/`ACCOUNT_LINKS`) and what both items need so `_balance` finds them. Any other place that enumerates BS items (validators, prompts, schema extras, renderers, `cash_bridge.py`) and must learn the new id.
3. **Formula.** Exact component list and order for `_cash_movement` with and without the declaration; the formula text; what each missing balance yields (term `reason`, status). Confirm the no-declaration output is unchanged.
4. **Constructed periods.** The exact change to `_period_cash` (and `:281`/`:297` as the task names them) so the opening/closing scope balances and the source adjustments combine correctly; every other consumer that indexes NCF_CASH_MOVEMENT `components` by position or assumes two balance terms (search the whole repo, including `src/deploy_workflow` and renderers).
5. **Item 82 interplay.** With item 82's downgrade, how a declared-scope check with a missing scope balance is classed (absent input → downgraded) and that a present-but-disagreeing scope sum stays BLOCK. Any file overlap with item 82.
6. **Files.** Every file to change. The user approved `financial_reconciliation.py`, `period_reconciliation.py`, `statement_validation.py` and the declaration's contract. Name any other `src/deploy_vii` file the plan needs, and why, so the controller can ask the user.
7. **Precheck (Modules' part).** Exactly what `src/deploy_workflow/financial_workflow.py` must accept so the noncurrent row can be taken from a CFS page (function, line, rule), written so the Modules session can build it.
8. **Tests (RED first).** Exact cases with numbers: fy-2025 (-32 = 21 + (85-95) + (12-55)) and h1-2026 (93 = 78 + (96-85) + (16-12)) PASS with the declaration and the rows; the same without the declaration unchanged (difference 53 and -15); a missing noncurrent balance → absent input (BLOCK), never treated as zero; a constructed period combining declared sources. Where each test goes (new test file names; no file listed as off-limits in common.md). How the CZR proof runs without editing `cases/**` (for example a test that loads the CZR partial submission and adds the rows with their exact filing citations in memory).
9. **Risks.** What could let a real disagreement pass (for example a declaration without citations, double counting restricted cash already inside `cash_and_equivalents`, a noncurrent row from a different date), and the guard for each.

End with a `Not verified:` line.
