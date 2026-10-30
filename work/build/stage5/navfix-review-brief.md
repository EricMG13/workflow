# Navigator fix: scoped review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s5-navfix` `64cfca9..3c90773` (3 commits: `tests/test_shell_css.py`, `src/deploy_vii/assets/app.css`, `docs/reuse/manifest.json`). Read it with `git show`/`git diff` from `L`. For probes, extract a copy with `git archive 3c90773 | tar -x -C <S>/navfix-review/tree`, write only under `<S>/navfix-review/`, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Run fast tests only. The controller repeats the native browser check.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 61 |
| Brief and report | `L/work/build/stage5/navfix-brief.md`, `L/work/build/stage5/navfix-report.md` |

## Process
1. The CSS change is exactly `flex-shrink:0` added to `.module-list`, and nothing else in `app.css` moved. Check that it cannot hide or clip anything the shell draws:
   - the navigator is `overflow:auto`, so a long outline now scrolls;
   - the narrow-screen drawer `.navigator.open` (`app.css:266`) uses the same column;
   - `.nav-foot` has `margin-top:auto`.
   Say whether any other navigator child can still shrink over the rows. Use file:line evidence.
2. The test fails at `64cfca9` for the reported cause and passes at `3c90773`. Its parser cannot pass vacuously: the selector is missing, it matches a different rule, or the declaration only appears in a later rule that overrides it.
3. The manifest entry is in `post_import_patches`. Its fields follow the previous entries and its hashes are the file's real sha256 at `64cfca9` and `3c90773`. Run `python3 -I L/work/build/keep/stage3-review/precise/probe_d12_strict.py <tree> 697fe8a 3c90773`; the expected failures are only `3e5b537`, `24f879a` and `8aef58d`.
4. No stub, fake value or catch-all.

Save each probe as a script in `<S>/navfix-review/` and name it in the finding.

## Output (return as text, under 500 tokens)
- verdict (APPROVE / REVISE);
- findings ranked High, Medium, Low, Info, each with file:line and a probe script with its exit code;
- a `Not verified:` line.
