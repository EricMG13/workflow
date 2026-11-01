# C-plan: CZR declared cash scope (mx-autonomous, 2026-10-31; controller wrote this file from its text report)

Code at 5a1d2e2f. Checked by running: `probe_scope_arith.py` exit 0; a scratch `czr_runs.czr_closed` on the unmodified partial gave fy-2025 21 (diff 53), h1-2026 78 (diff -15), every other NCF_CASH_MOVEMENT BLOCK with calculated None. CZR period reconciliation never runs there (`historical_report` raises at `financial_adapter.py:198`, partial add-back bridge). A pydantic 2.14.1 probe confirmed a wrap serializer that drops a None field keeps parent dump bytes identical, round-trips, and changes only the validation schema.

## Design faults found
- (a) A fixed three-balance scope can never PASS for an issuer with only current restricted cash (the noncurrent balance stays absent). The declaration lists its items.
- (b) cash-diff.md locators are wrong: the reconciliation tables are at 10-K `page:61` and 10-Q `page:10` (PAGE RULE), not page:60/page:9. The 10-Q's second column is 2025-06-30 (982 / 85 / 19), not 2025-12-31.
- (c) With item 82, a declaration with an omitted row would turn today's computed BLOCK (difference 53) into an absent input downgraded on public cases. Guard G3 closes it.

## 1. Declaration (on `CashMovementBridge`, `financial_contracts.py:367-378`)
- Not on `FinancialBook`: a book field also needs `live/submission.py:1152-1177` `BOOK_PARTS`. Bridges already travel in the CFS part (:1164) and are per period, which constructed periods need.
- New `class CashScope(Contract)`: `items: Annotated[tuple[Literal["restricted_cash", "restricted_cash_noncurrent"], ...], Field(min_length=1, max_length=2)]`; `citations: Located`; a `model_validator`: no duplicate items, and at least one citation whose whitespace-normalised, lower-cased quote contains `"restricted cash"`.
- Field `cash_scope: CashScope | None = None` on `CashMovementBridge`, with `@model_serializer(mode="wrap")` that pops `cash_scope` when None (precedent `execution.py:117-122`, :170-175). Mandatory: `Contract.content_hash` dumps defaults (`contracts.py:78-79`); without it every review, `ReconciliationReport` (`financial_reconciliation.py:86`) and `PeriodCheck` (`period_reconciliation.py:70`) hash changes. With it, stored payloads, journals, `validate_reconciliation_report`'s hash recompute and `cases/PINS.json` paths (raw files, `cases/pins.py:20-30`) stay byte-identical; no schema-version bump.
- The sent schema changes (one nullable property, required under strict_copy, `live/schema.py:5-8`). Update the `CashMovementBridge` docstring so the model learns the field (the docstring is the schema description).

## 2. Noncurrent item
- Add `restricted_cash_noncurrent` to `OPTIONAL_ITEMS["BS"]` (`statement_validation.py:96`). Optional: REQUIRED would add a missing-cell row to every book (`statement_output.py:125`).
- `restricted_cash` never reaches `_balance` today (`effective_accounts` has only `ACCOUNT_LINKS` BS keys, :132-144; a link needs `BALANCE_METRICS` `model/history.py:154-166` and the `AccountObservation` enum, `financial_contracts.py:72,159-167` — large blast radius). Read both items with `_statement_balance` (`financial_reconciliation.py:561-576`, BS lines by exact end date), adding keyword `sign: Literal[-1, 1] = 1` passed to `_term`; `_balance_movements` callers unchanged.
- Enumerations that pick up the new id with no edit: `financial_contracts.py:50-60` (enums at :314, :408), `live/prompts.py:243,428` (prompt text changes), `narrative.py:320`, `balance_movement.py:40`.

## 3. Formula (`_cash_movement`)
- `CASH_SCOPE = ("cash_and_equivalents", "restricted_cash", "restricted_cash_noncurrent")`; `def cash_scope(bridge) -> tuple[str, ...]`: cash first, then the declared items in `CASH_SCOPE` order.
- Components in order: `_balance(end, "cash_and_equivalents")`; `_balance(opening, …, sign=-1)`; for each item in `scope[1:]`: `_statement_balance(end, item)`, `_statement_balance(opening, item, sign=-1)`; then `*adjustments`.
- Formula when declared: `f"closing cash scope - opening cash scope ({' + '.join(scope)}) - signed source adjustments"`; context adds `*bridge.cash_scope.citations`.
- No declaration: same components, formula and context as :535-548 — identical bytes.
- A missing balance: term `amount=None`, `reason` = the observation's reason or "Not supplied" (`_term` :133) → calculated None, difference None, BLOCK, "Missing reported value or complete independent components" (`_check` :153-167). Never zero.

## 4. Constructed periods (`_period_cash` :263-314)
- `bridges = {b.period_id: b for b in book.cash_movement_bridges}` replaces :283.
- `scope` = the `CASH_SCOPE` items declared by any assessed source.
- After the two cash terms at :281, add `_source(_statement_balance(book, node.end_date, item))` and `_source(_statement_balance(book, opening, item, sign=-1))` for each item in `scope[1:]`.
- Replace the :297 slice with `source.components[2 * len(cash_scope(bridges[pid])):]`. A source whose own scope differs from `scope` appends blocker `f"Cash scope differs across source periods: {pid}"`.
- Formula when declared: `f"closing cash scope - opening cash scope ({' + '.join(scope)}) - signed period combination of source adjustments"`.
- Scope exists only with a bridge, so the unadjusted path is untouched. Whole-repo search: only :297 matches `components[2`; `deploy_workflow` and renderers do not index NCF_CASH_MOVEMENT components.

## 5. Item 82
- No file overlap. A declared check with a missing scope balance (difference None) becomes WARN on public cases via `absent_input_limitation` (branch `claude/s7-absent-input-2`), text "absent: restricted_cash_noncurrent (Not supplied)". A present but disagreeing sum stays BLOCK; a constructed source difference stays BLOCK (`CHILD_DIFFERENCE_BLOCKER`); the mixed-scope blocker would downgrade as a structural blocker.
- Once case files declare scope, item 82's CZR test counts change (2 cash BLOCKs, `CZR_PREFIXED_GAPS=135`) — owning session.

## 6. Files
`financial_contracts.py`, `financial_reconciliation.py`, `period_reconciliation.py`, `statement_validation.py`, and `cash_bridge.py` (G2, G3). `live/prompts.py` optional (docstring suffices).

## 7. Precheck (Modules)
For CZR `financial_workflow.py` needs no change: the rows sit on non-statement pages (`STATEMENT_HEADING` :85 matches only K 54/56/60, Q 2/4/9), so `_evidence_issues` coverage (:362-371, :379-381) skips them. Only UNREAD applies (`live/tools.py:1154-1166`): the financials stage must `read_pages` K 61 and Q 10. If Modules wants tables printed on a CFS heading page accepted: in the :398-411 `any(...)`, also accept a line with page statement `"CFS"`, `line.statement == "BS"`, `line.item_id` in `{"cash_and_equivalents", "restricted_cash", "restricted_cash_noncurrent"}`, whose period is a PERIOD_END ending on the `end_date` of the single flow period in `period_ids`; label, value and citation conditions unchanged.

## 8. Tests (RED first)
`tests/test_cash_scope.py` (unit; real `FinancialBook`s with the filing numbers and quotes; any 64-hex `source_sha256`):
- fy-2025 declared with both items: components [887, -866, 85, -95, 12, -55]; calculated -32, difference 0, PASS; formula as §3.
- h1-2026: [965, -887, 96, -85, 16, -12]; 93, PASS.
- Same books without the declaration: 21 / diff 53 BLOCK and 78 / diff -15 BLOCK; old formula; labels `["cash_and_equivalents"] * 2`; `"cash_scope" not in bridge.model_dump_json()`.
- fy-2025 without the 2024-12-31 noncurrent row: that term amount None, reason "Not supplied"; calculated None, difference None, BLOCK. With a `not_applicable` row the term carries its reason. (G3 then also reports the missing row at validation.)
- Constructed: `_period_cash` with a real `HistoricalReport` (one LTM node 2025-07-01..2026-06-30, terms fy-2025 +1, h1-2026 +1, h1-2025 -1). BS (cash, restricted, noncurrent): 2024-12-31 = 866/95/55; 2025-06-30 = 982/85/19; 2025-12-31 = 887/85/12; 2026-06-30 = 965/96/16. NCF -32, 70, 93; reported -9, closing 965. Expected parts [965, -982, 96, -85, 16, -19], calculated -9, PASS (the old slice plus boundary terms gives -1). Variant: h1-2025 bridge without scope → mixed-scope blocker.
- Contract: a quote without "restricted cash" raises; duplicate items raise.

`tests/test_czr_cash_scope.py` (~100 s): load `submissions-partial.json`, add in memory a BS line `bs-restricted-and-escrow-cash-included-in-other-long-term-assets-net` (display_priority max+1, `detail`, full-line quotes): 12 at bs-2025-12-31 and 55 at bs-2024-12-31 (K page:61), 16 at bs-2026-06-30 (Q page:10); empty-component bridges for fy-2025 and h1-2026 with scope citations of the NCF lines (K page:60 "Decrease in cash, cash equivalents and restricted cash | (32) | (127) | (160)", Q page:9 "Increase in cash, cash equivalents and restricted cash | 93 | 70"); `read_pages` for K 61 and Q 10. Write to `tmp_path`, run `czr_closed(tmp_path, path)`, expect RuntimeError (`calculation_gate`); spy on `canonical_audit.reconcile_financials`; assert fy-2025 -32 PASS and h1-2026 93 PASS. Nothing under `cases/**` is edited.

At RED the declared cases fail (extra field forbidden / unknown item); the no-declaration cases pass as guards.

## 9. Risks and guards
- G1: citations that do not name restricted cash are refused by the contract validator; `citation_issues` checks quotes are real.
- G2 (`cash_bridge.py`): a scope citation must equal a citation of the same period's CFS `net_cash_change` / `opening_cash` / `closing_cash` line.
- G3 (`cash_bridge.py`): if `cash_and_equivalents` is stated at a date the check uses, every declared item must have a BS line (any status) there.
- Wrong date: `_statement_balance` matches exact dates; arithmetic catches a mismatch (86 ≠ 93).
- Double counting: any nonzero movement shows as a difference.
- Adding bridges switches constructed checks to adjusted mode, so a case must bridge every CFS period.

Not verified: the code changes; sent-schema/prompt changes against stored live attempt manifests and prefill of nested `cash_scope` citations; whether any test pins prompt text; the CZR test's runtime; h1-2025/fy-2024 becoming computable; G2/G3 behaviour.
