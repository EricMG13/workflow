# Scoped review: CP-2G/2H/4C driver fix and G2 round 4 (stage contract; mx-feature, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Two small test-only changes, both from `claude/s3-i7` a020996:
- `claude/s3-cp2g-driver` `a020996..419295e` (`tests/cp2g_runs.py`, `tests/cp2h_runs.py`, `tests/cp4c_runs.py`, new `tests/test_cp2g_driver.py`);
- `claude/s3-fix4-g2` `a020996..65e233c` (`tests/test_owner_rendering.py`).

Read them with `git show`/`git diff` from `L`. For probes, make a fresh copy under `<S>/fix-drivers-r4-review/` with `git archive <rev> | tar -x -C …`; never write into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`; `pyproject.toml` sets `pythonpath = ["src", "."]`. Run no genuine (real-data) tests; the controller is running them on the integration branch.

The two agents were stopped by a PC restart before they reported. The controller has since run: `tests/test_cp2g_driver.py` 5 passed; `tests/test_owner_rendering.py -k fast` 153 passed; ruff, ruff format and mypy --strict exit 0 on the changed files; suppressions 13/5; `<S>/cp1d-tab-rca/probe3_cp1d_fast_block_rule.py` and `probe4_proposed_fix.py` exit 0 on a copy of 65e233c.

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 34, 35 and 36 |
| Briefs | `L/work/build/stage3/cp2g-driver-brief.md`, `L/work/build/stage3/fix4-g2-brief.md` |
| Root cause (round 4) | `L/work/build/stage3/cp1d-tab-rca.md` |

## Process
1. **Driver fix.** `readiness_payload` submits exactly `inputs_sha256` and `consumers`, drops only `note`, and fails closed on any other key or a missing payload key. Confirm with file:line that the producer's readiness payload schema forbids extra keys (the fixer's comment says `DownstreamReview`, `extra="forbid"`). Check that the fast test cannot pass vacuously (for example, if no case held a `cp1_readiness`), and that the cp2h and cp4c drivers use the same helper.
2. **Round 4.** The one-entry rule applies only to a tabs-only oracle with exactly one entry; every other comparison stays strict; rows are still checked. The three new fast assertions fail without the rule (show it on a copy).
3. Report anything that hides a failure, a stub or a fake value.

## Output (return as text, under 600 tokens)
Verdict (APPROVE / REVISE) per branch; findings ranked High, Medium, Low, Info, each with file:line and a probe script with its exit code; `Not verified:` line.
