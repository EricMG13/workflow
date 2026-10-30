# G2 coverage gaps build: review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s5-g2-gaps` `e37b73e..715f5a4` (3 commits, `tests/test_owner_rendering.py` only). Read it with `git show`/`git diff` from `L`. For probes, extract a copy with `git archive 715f5a4 | tar -x -C <S>/g2-gaps-build-review/tree`, write only under `<S>/g2-gaps-build-review/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Run fast tests only; the controller is running the genuine ones.

You did not prepare the specification, review it, or build this.

## Inputs
| Item | File |
|---|---|
| Specification (frozen) | `L/work/build/stage5/g2-gaps-spec.md` (rules, controller rulings, then Revision 1, which replaces the parts it names) |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 46, 47 |
| Builder's report | `L/work/build/stage5/g2-gaps-build-report.md` |
| Spec probes | `L/work/build/keep/g2-gaps-spec/`, `L/work/build/keep/g2-gaps-spec-review/` |

## Process
1. Check each helper against its rule in the specification; Revision 1 governs where it differs. In particular, check that `_page_cites` has no fallback and follows the required-entry rule, and that cp4 limitations follow the oracle text with the store's CP-1 head. Check the rails order (own, SYNTH, inherited) and that cites cover every oracle table, with at least one checked.
2. Check that `_check_scope_run` calls each assert for the right scopes on complete outcomes only, and that no assert can pass vacuously on a genuine page (zero registers, zero lines, zero cites).
3. Check the builder's decisions: s1a `calculations` built from every head module in the store; `_assert_rejected` narrowed to `AssertionError` with a non-empty list; the test-only CP-1 head in the fast tests, which must stay out of the genuine path.
4. Show that at least one new fast test fails when its rule is weakened (on the copy).
5. Report anything that hides a failure, or any stub or fake value on the genuine path.

Save each probe as a script under `<S>/g2-gaps-build-review/` and name it in its finding.

## Output (return as text, under 800 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, the failure scenario and the probe script with its exit code; `Not verified:` line.
