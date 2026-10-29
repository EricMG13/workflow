# Stage 3 CZR real-data case: code fixes and run driver (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Worktree `../s3-czr`, branch `claude/s3-czr`: release ab9777f plus Workflow Test's case commit 7a5a861 (`cases/czr-2026q2-earnings-update/`, `tests/test_czr_case.py`). Python: `L/.venv/bin/python`.

You fix two code gaps and build the run driver. You never write submissions and never edit `cases/czr-*/**` or `tests/test_czr_case.py`; Workflow Test owns them.

## Inputs
| Item | File |
|---|---|
| User ruling and roles | `L/docs/rulings/2026-10-29-stage3.md` item 10 |
| Scope check (gaps, file:line) | `L/work/build/stage3/czr-scope.md` |
| Case | `cases/czr-2026q2-earnings-update/` (`manifest.json`, `qualification.json`, `expected.json`, `documents/*.txt`) |
| Run drivers to follow | `tests/s1a_runs.py` (`PreparedPack`, `Source`/`Span`, submissions with run-time tokens), `tests/cp1d_runs.py` |
| D12 reuse manifest rule | `docs/reuse/manifest.json`; rulings `L/docs/rulings/2026-10-28-stage2.md` round 5 item 19 |

## Process
1. **Gap 1 (approved by the user).** The CP-1 `financials` precheck heading regex (`src/deploy_workflow/financial_workflow.py:351-364`, copy at `earnings_workflow.py:1108`) accepts the filed SEC headings in the case ("CONSOLIDATED CONDENSED BALANCE SHEETS", "CONSOLIDATED CONDENSED STATEMENTS OF OPERATIONS", the cash-flow heading and any other statement heading the documents use), and every heading the synthetic sources use today. It maps each heading to the same statement kind as before. Test first: a RED test on the real document headings, plus a test that the synthetic headings still match the same kinds.
2. **Gap 2 (approved by the user).** `src/deploy_vii/statement_extract.py` splits ` | `-delimited table rows into cells, as well as the current two-or-more-space rows. Separator rows (`|---|`) give no line. Test first on real document rows. A row in the current format extracts exactly as before.
3. **D12.** If any edited file is listed in `docs/reuse/manifest.json`, append a `post_import_patches` record per round 5 item 19.
4. **Driver `tests/czr_runs.py`.**
   - Build `PreparedPack(run, sources)` from the three documents. The run is `case_kind="public"`, `pathway="earnings_update"`, `requested_modules=("CP-1",)`, with a new run id and `as_of` from the manifest.
   - Split each `.txt` into `page:N` spans by one deterministic, documented rule derived from the exact file bytes (the files have no form feeds); statement headings start a page, so the precheck can locate statement pages. Keep `Source.sha256` equal to the file hash in `qualification.json`. Workflow Test writes its locators from this rule alone, so it must be computable from the bytes without running the driver (for example, a page starts at line 1 and at each line matching a stated regex).
   - State the rule in the driver's docstring, word for word as Workflow Test will need it to write locators.
   - Provide `czr_closed(root)`. It runs `OwnerWorkflow` to a written receipt using `cases/czr-2026q2-earnings-update/submissions.json`, with run-time token substitution as `s1a_runs.py` does. Until that file exists, the function raises `FileNotFoundError` naming the file; it never substitutes data.
5. **Tests now (`tests/test_czr_driver.py`).**
   - The pack builds deterministically.
   - Source hashes equal the qualification hashes.
   - The CP-1 precheck locates statement pages in the 10-Q and the 10-K.
   - `extract_statement_lines` returns lines for each located statement page.
   - Every CP-1 `matched_text` in `qualification.json` (or one of its alternatives) lies within exactly one page.
6. Commit after the RED tests and after each fix. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- No synthetic oracle moves: `python3 -I cases/pins.py --check`. Run with `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider`:
  - `tests/test_financial_workflow.py`, any `tests/test_statement_extract*.py`, `tests/test_earnings_workflow*.py` if present;
  - `tests/test_czr_driver.py`;
  - `tests/test_czr_case.py`.

  Run the long ones in the background.
- `ruff check` and `ruff format --check` on changed files; `MYPYPATH=src mypy --strict` on changed `src/` files.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (report as text, at most about 1.5k tokens)
- Tip SHA; the page rule verbatim; the headings the regex now accepts; tests and counts; D12 records; questions; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Stop any background process before you hand back.
