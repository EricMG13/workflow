# Stage 4 CP-8 oracle re-pin (stage contract; preparer)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s4-cp8-oracle 18dc1fa` (the Stage 3 integration tip `claude/s3-i5`) and confirm the tip. Write only inside your own worktree. Python: `L/.venv/bin/python`. The disk is tight: run only the gates below.

You are the **preparer**. You edit only `cases/cp8-owner/` (through `cases/cp8-owner/builder/`, never by hand if the builder writes the file) and `cases/PINS.json`. You never edit `src/` or `tests/`. A separate builder changes the code after an `mx-precise` review approves your change.

## Inputs
| Item | File |
|---|---|
| What to move and why | `L/work/build/stage4/plan.md` §5 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` item 19 (the user approved the two-field re-pin); `L/docs/rulings/2026-10-28-stage1.md` around :490 and :505, and its A7 exception |
| The A7 precedent | `cases/cp2d-owner/builder/build.py` and `cases/cp2d-owner/expected.json` (search `A7`) |
| Oracle | `cases/cp8-owner/expected.json`, `cases/cp8-owner/builder/` |

## Process
1. Move exactly two fields of `cases.no_outcome.tables[8].rows[1].facts[0]` (`fact_id` `cp8.what_changed.outcome.value`):
   - `text` becomes the claim's token form, copied from the same oracle's `cases.no_outcome.claims[0].text` (`… [T7.3.window.realized_value] …`).
   - `shown` takes the run-time-bound `∅ G#` pattern form that CP-2D's A7 exception already uses. Copy the CP-2D mechanism (field names and how a test binds it), not new wording.
   - `claims[0].resolved` and every other value stay byte-identical.
   If the A7 mechanism cannot express this cell, stop and report; do not invent a new form.
2. Regenerate through the builder, if it writes the file. Then `python3 -I cases/pins.py` and `--check`.
3. Write the builder's targets: the exact assertions in `tests/test_method_cp8.py` (:60, :188, :269 `G#` substitution) and `tests/test_connect_cp8.py` that must change to read the moved fields, and the RED test names from plan §5.
4. Make one commit ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/pins.py --check`.
- A double fresh-copy rebuild through the builder must give identical output.
- `git diff 18dc1fa -- cases/cp8-owner/expected.json` shows only the two fields.

## Outputs (return as text, under 800 tokens)
Worktree path and tip SHA; both moved values with their source pointer; the builder targets; gate exit codes; `Not verified:` line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged.
