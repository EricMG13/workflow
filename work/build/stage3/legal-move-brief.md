# Stage 3 legal render oracle move (stage contract; preparer)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-legal c43b681`, the integrated Stage 3 tip of `claude/s3-int`, and confirm the tip. Write only inside your own worktree. Python: `L/.venv/bin/python`. The disk is nearly full, so run only the tests named below.

You are the **preparer**. You edit only `cases/legal/` (through its builder, if one exists) and `cases/PINS.json`. You never edit `src/` or `tests/`; a separate builder reverts the test workaround after an mx-precise review approves your change.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 13 (and items 6.1, 9, 11) |
| Oracle | `cases/legal/render-expected.json` and its generator, if any (search `cases/legal/` and `cases/*/builder/`) |
| The workaround to retire | `tests/test_legal_render.py`: `_producers_after_stage3` and `_note_after_stage3`, marked `# Stage 3 item 13` |
| What changed | the I3 report `L/work/build/stage3/int-report.md`; the frozen chart oracles `cases/charts/*-expected.json` |

## Process
1. List every value in `cases/legal/render-expected.json` that the integrated Stage 3 code now renders differently for the legal fixtures (FP-04 and any FP-05 or other fixture the file covers). Expected sources:
   - the `funding-gap` producers, now `("CP-2D","CP-3C")`, and its not-run note;
   - the `maturity-wall` kind, now `chart`;
   - any figure now drawn on a block the fixture populates, for example CR.1 on `covenant-tests-headroom` when CP-4 runs.
   Take each new value from the frozen chart oracle or the ruling, never from the code's output alone. If a moved value has no ruling or oracle behind it, stop and report it.
2. Move those values, through the generator if one exists, and keep every other value byte-identical. Regenerate `cases/PINS.json` with `python3 -I cases/pins.py` and run `--check`.
3. Write the builder's targets: the exact edits to `tests/test_legal_render.py` that remove the item 13 workaround so the test reads only the legal oracle again.
4. Make one commit ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates
- `python3 -I cases/pins.py --check`.
- If a generator exists, a double fresh-copy rebuild must be identical.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_legal_render.py`. Report the result: it may go red only where the workaround now disagrees with the moved oracle.

## Outputs (report as text, under 800 tokens)
- Your worktree path and tip SHA; every moved value with its source (ruling or oracle and pointer); the builder targets; gate exit codes; `Not verified:` line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged.
