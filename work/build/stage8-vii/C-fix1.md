# C fix round 1 (mx-feature, resumed builder)

Same rules and files as `C-build.md`. Work on `claude/s8-vii-c` from dd91959f. Commits: `test: RED cash scope fix 1` (tests only, failing for the findings) then `fix: cash scope fix 1` (code only), then, if needed, `style: cash scope lint` (Lows only).

Reviews: mx-adversary REVISE (findings below), mx-precise APPROVE with Lows. Adversary probes are in `W/work/build/stage8-vii/probes/c-adversary/` (each exits 1 while its exploit reproduces; `_common.py` builds the books; `ca82.py` is item 82's `absent_input_limitation`). Read the probe for each finding to see the exact book.

## Findings to fix (rulings by the controller)
- **A1 High (`cash_bridge.py` G3).** A declared item with a `not_applicable`/`missing` row passes G3, so a computed BLOCK (fy-2025 difference 53) becomes an absent input that item 82 downgrades (probes `p1_g3_status_bypass.py`, `p6_constructed_boundary.py`).
  Ruling: G3 becomes: for each date the check uses (end date; the day before the start date when that exists), every declared item must have a BS line there whose value status is `known` or `conflicting`. A declaration therefore never makes a check absent that would otherwise be computed; to leave a balance out, do not declare that item. The check's own absent-input path (term amount None, never zero) stays as is. Issue text for a line that is absent or has another status: `f"Declared cash scope balance missing: {bridge_id} {item_id} {date.isoformat()}"` (unchanged text).
- **A2 Medium (`cash_bridge.py` G3 precondition).** G3 only ran when a BS `cash_and_equivalents` line is stated, but `_balance` also reads explicit accounts (probe `p2_g3_account_cash_skip.py`).
  Ruling: drop the precondition. G3 applies at each date the check uses whether or not cash is stated there.
- **A3 Medium (G1/G2 split, `financial_contracts.py` / `cash_bridge.py`).** G1 and G2 can be met by different citations (probe `p3_g1_g2_split.py`).
  Ruling: G2 requires one citation that both equals a citation of the same period's CFS `net_cash_change`/`opening_cash`/`closing_cash` line and whose whitespace-normalised, lower-cased quote contains `"restricted cash"`. New G2 text: `f"Cash scope citation must cite the period's CFS cash line naming restricted cash: {bridge_id}"`. Keep the contract validator (G1) as is.
- **A4 Low (label).** Nothing ties a declared item's BS row to restricted cash (probe `p7_mislabel_and_double_count.py` part a).
  Ruling: add to G3: the declared item's BS line at that date must have a label whose whitespace-normalised, lower-cased text contains `"restricted"`; else issue `f"Declared cash scope balance must be labelled restricted: {bridge_id} {item_id} {date.isoformat()}"`. (CZR labels: "Restricted cash", "Restricted and escrow cash included in other long-term assets, net".)

## Lows (mx-precise) to fold in
- L1: `period_reconciliation.py` import order (ruff I001).
- L2: `tests/test_cash_scope.py` must pass `ruff format --check` (format the file as ruff would; you cannot run ruff, so match its style: 100 columns, magic trailing commas).
- L3: strict mypy on both new test files: annotate every helper and test (`-> None`), `tests/test_czr_cash_scope.py:99` (`canonical_audit.reconcile_financials` is not explicitly exported: import it from its defining module instead), :115 (compare like types: Decimal with Decimal).
- L4: `test_a_book_without_any_declaration_serializes_as_before` also covers the `Reconciliation` from `_cash_movement` and a `PeriodCheck` from `_period_cash`: for each, `"cash_scope" not in obj.model_dump_json()` and `obj.content_hash() == hashlib.sha256(obj.model_dump_json().encode()).hexdigest()` if that is how `Contract.content_hash` is defined (read `contracts.py:78-79` and match its exact definition). The byte-identity with base is proven separately by the reviewer's probe `W/work/build/stage8-vii/probes/c-review/p1_undeclared_bytes.py`.
- Info: `tests/test_czr_cash_scope.py:111` `pytest.raises(RuntimeError, match="calculation_gate")` (check the real message text in `tests/czr_runs.py`/the CZR run code and match it exactly).

## Tests
RED tests (in `tests/test_cash_scope.py`) reproducing A1 (both a `not_applicable` and a `missing` declared row → the G3 issue), A2 (cash given only as an explicit account, declared row omitted → the G3 issue), A3 (citations split across a CFS cash line not naming restricted cash and a BS quote naming it → the new G2 issue), A4 (a declared `restricted_cash_noncurrent` row labelled "Other long-term assets, net" → the label issue). Update existing tests whose expected G2 text changed. Every existing passing test must stay green.

Report as before (SHAs, node ids failing at RED, `Not verified:`).
