# D12: lint fix + post_import_patches records (stage contract; mx-scaffold)

Rules: `W/work/build/stage8-vii/common.md` (read first), except: step 0 is `git checkout -b claude/s8-vii-d12 <TIP>` where `<TIP>` is the controller's tip given in the dispatch; you may edit `docs/reuse/manifest.json` and `tests/test_cash_scope.py` only. Use only git and system `python3 -I` with stdlib (allowed).

## Commit 1: `style: ISC004 in tests/test_cash_scope.py`
At `tests/test_cash_scope.py` ~:407-410 (`test_declared_item_row_must_be_labelled_restricted`) the expected tuple holds an implicit string concatenation (ruff ISC004). Wrap the two adjacent string literals in parentheses inside the tuple; same text, same value. Nothing else.

## Commit 2 (must be the LAST commit): `docs: D12 records for stage 8-vii`
Append to `docs/reuse/manifest.json` `post_import_patches`, in this order, one record per (file, commit) below. Do not touch any other key or existing record; keep the file's JSON formatting (indent and key order as the existing records: `destination, imported_sha256, prior_project_sha256, project_commit, sha256, reason, review`).
For each record:
- `destination`: the path;
- `imported_sha256`: that file's `sha256` in the manifest's `files[]` entry with the same `destination`;
- `prior_project_sha256`: sha256 of the file's bytes at `<commit>^1` (`git show <commit>^1:<path> | python3 -I -c "import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"`);
- `project_commit`: the full commit sha below;
- `sha256`: sha256 of the file at `<commit>`;
- `review`: `"docs/rulings/2026-10-31-s8-vii.md"`;
- `reason`: the text given below.

| commit | files | reason |
|---|---|---|
| a147d8163c39a4d1752627af8e1a3e7a3222989e | src/deploy_vii/report_view.py | `H03 (s8-vii A): _RUN_TEXT_FIELDS adds ("CP-L10", "TL10.4", "decision_impact"), the validated TL10.3 credit_transmission text; user-approved in session s8-vii.` |
| a147d8163c39a4d1752627af8e1a3e7a3222989e | src/deploy_vii/source_context.py | `H09 (s8-vii A): _lacks treats a prose.is_blank scope dimension as missing; _disagreements skips blank values; user-approved in session s8-vii.` |
| 0a4917edc602a52328ff62d91e2268d4fcb3bcca | src/deploy_vii/statement_extract.py | `D1-D3 (s8-vii B): year-valued labelled rows are data unless the label is a period/unit caption (D2); a (n<=2 digits) footnote marker before N+1 values is dropped and flagged (D3); ExtractedTable.omitted records unparsed candidate lines (D1); user-approved in session s8-vii.` |
| 4ed0f63cc3928290df06d620c050395edd78b474 | src/deploy_vii/statement_extract.py | `D1-D3 fix 1 (s8-vii B): mypy-strict rename; separator rows of only nil dashes and pipes are not omitted candidates; literal word sets.` |
| d6ca9b631717913fed168d809de9343aeaa35fac | src/deploy_vii/cash_bridge.py, src/deploy_vii/financial_contracts.py, src/deploy_vii/financial_reconciliation.py, src/deploy_vii/period_reconciliation.py, src/deploy_vii/statement_validation.py (one record each, in this order) | `CZR cash scope (s8-vii C): CashMovementBridge.cash_scope declares restricted-cash balances in the CFS cash scope (dropped from JSON when None); optional BS item restricted_cash_noncurrent; NCF_CASH_MOVEMENT single and constructed checks sum each declared balance's change; guards in cash_bridge; user-approved in session s8-vii.` |
| 1309b27b0aef3208fc6790f769e5049b6418cf61 | src/deploy_vii/cash_bridge.py, src/deploy_vii/period_reconciliation.py (one record each) | `CZR cash scope fix 1 (s8-vii C): G3 needs a known or conflicting, restricted-labelled row for each declared item at every check date; G2 needs one citation that is the period's CFS cash line and names restricted cash (mx-adversary A1-A4); import order.` |
| 3f335106363c7713928eb048b1da1debd68ea219 | src/deploy_vii/report_view.py, src/deploy_vii/source_context.py (one record each) | `Stage 8-vii Low batch: comment and docstring rewrap only; no behaviour change.` |

Before committing, check with `python3 -I work/build/keep/s53-B/probe_d12_strict.py "$(pwd)" 5a1d2e2f HEAD` after a temporary `git commit` is not possible — so instead commit, then run the probe with `<rev>` = your new HEAD; if it exits 1, fix the records with a further commit `docs: D12 records fix` (never amend) and rerun until exit 0.

Report as text (under 250 tokens): both SHAs, the probe's exit code and its last 15 lines, `Not verified:`.
