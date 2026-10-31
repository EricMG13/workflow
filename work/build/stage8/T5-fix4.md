# T5 third fix (stage contract; a fresh mx-feature, test first), from the root-cause plan

Include `work/build/stage8/common.md`. Execute `L/work/build/stage8/T5-plan.md` exactly. Its probes are in `L/work/build/keep/s8-t5/root-cause/`, and `rc_fix.py` has the proposed `invoke`.

## Setup
In your isolated worktree, run `git checkout -b claude/s8-h05b af9ceea1`.

## Commits
1. **`test: RED T5 replay matrix`.** Make the plan's step 3 matrix and the two python-api cases in `tests/test_host_frames.py`, plus the step 4 pin updates in `tests/test_source_tools.py` (`:526` and `:1474`).
2. **`fix: T5 replay-consistent refusals`.** Make the plan's step 2 changes, in `src/deploy_workflow/host.py` `SourceSession.invoke` and the new one-line `SourceTools.offers` in `src/deploy_workflow/tools/source.py`. Touch no other src file.

Asserting exact values matters here: each case asserts the reply tuple and that the receipt seals and verifies.
