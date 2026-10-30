# Post-release tail: RUF100 one-liner and MODULES.csv rows (stage contract; mx-feature)

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s6-tail ef37a3f` (the lane tip) and confirm the tip. Edit only `src/deploy_workflow/financial_workflow.py` (one line) and `docs/MODULES.csv`.

**Interpreter (item 72 arrangement).** Do not run Python. The controller runs every check in your worktree. Commit with plain separate `git add <files>` and `git commit -m "<message>"` commands from your worktree root, with no `&&`, `$(...)`, pipes, wrappers or symlinks. Each commit message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Use the Edit tool for edits; for the CSV, edit with exact replacements that keep 11 columns and no quoted fields.

## 1. RUF100 (OI-11, now unblocked because CZR is done, items 75 and 79)
- `financial_workflow.py:914` is `except Exception as error:  # noqa: BLE001 - finalize every owned partial publication`. ruff reports the `noqa` as unused (RUF100), because BLE001 is not enabled.
- Remove only the `noqa: BLE001` token. Keep the reason as a plain comment, for example `# fail-open by design: finalize every owned partial publication`. The except stays as it is: it is a documented fail-open.
- The noqa count drops from 13 to 12.

## 2. `docs/MODULES.csv` rows changed by items 69-80
Inputs (all in the lane, read-only):
- rulings items 69-80 in `docs/rulings/2026-10-29-stage3.md`;
- `docs/rulings/2026-10-30-open-items.md` and `work/build/open-items/closed.md`;
- `work/build/ledger.md` (lines from item 69 on);
- the run logs under `work/build/keep/s5-final/` and `work/build/keep/s5-final2/`;
- the Stage 5.4 brief `work/build/stage5/modules-csv-brief.md`, for the cell rules and wording style.

Process:
- Update only the rows whose evidence or open items changed:
  - CP-DR (items 69, 73);
  - CP-1 (CZR items 70, 74, 75 and 79; OI-14 and OI-20 blank refusals);
  - CP-2H (the DR.6 chip OI-13, and the removed placeholder);
  - CP-3D, CP-2E and CP-2A (open-items B2 validators);
  - CP-4 and CP-4C (removed placeholders);
  - any other row `closed.md` shows was changed by code.
  Leave every other row byte for byte unchanged.
- A cell says `verified: …` only when a ledger line or a kept log shows a genuine run passing on the final code. Name the test file and the ledger time or log. In particular:
  - CP-1 on real filings is verified only through `narrative`; `quality` is blocked (item 75). Say so plainly.
  - The DR.6 chip rendering has no native DOM check yet, so do not call it verified beyond the G2 tests.
- In `next_evidence` and `unblocking_task`, name what is genuinely left: the item 75 design question, the cp4c never-wedges rerun, the DR.6 DOM check, and CP-1B.
- Stay in the existing rows' plain style. Claim nothing the evidence does not show.

## Output (text, under 600 tokens)
- worktree path, branch and SHA;
- per changed row, the cells changed and the evidence for each;
- a `Not verified:` line.
