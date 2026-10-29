# G2 fix round 3 scoped re-review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s3-fix3-g2` `ee95ffb..42bd134` (two commits, 08c2eec and 42bd134; `tests/test_owner_rendering.py` only). Read with `git show`/`git diff` from `L`. For probes, make fresh copies under `<S>/fix3-rereview/` with `git archive 42bd134 | tar -x -C …`; never write into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`; `pyproject.toml` sets `pythonpath = ["src", "."]`, so run from the copy's root.

This is a re-review: check only that rulings 27 and 28 are carried out, and that the change cannot pass a wrong delivery. Do not run genuine tests (the controller runs all 51 deferred genuine tests on the integration branch).

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 27 and 28 |
| Root causes and plans | `L/work/build/stage3/g2-genuine-rca.md`, `L/work/build/stage3/g2-genuine-rca-2.md` |
| Fixer's brief and report | `L/work/build/stage3/fix3-g2-brief.md`, `L/work/build/stage3/fix3-g2-report.md` |
| Lease | the G2 lease named in item 27 (Acceptance 1 and 3, R2.5) |

## Process
1. **Item 27.** The positive test still fails when G2 delivers the financial run's publication instead of its own, or a `model/` that differs from its own publication in any byte. Removing only `ticket_id` cannot hide another receipt difference. The extra-attempt test proves `begin` refuses, and the forged pending attempt really reads back pending before G2 refuses it.
2. **Item 28.** `_line_text` drops only `S\d+` fig chips (not real provenance chips) and joins with " ". `_matches_oracle_text` accepts `∅ G#` only where the oracle has the placeholder, and only against a well-formed `∅ G<n>` in rendered output. The chip-present assertion equals `bool(synthetic_ref)`. Tabs-only oracles compare every tab with `strict=True`; the line count is asserted. `assert_render_node_owner` covers cp3d, cp4 and cp8 as step 4 says, and adds no secondary-pointer checks (those are Stage 5).
3. For each rule, write a fast probe on a copy that mutates a rendered block (a wrong chip, a real chip dropped, a non-placeholder text matched as `∅ G#`, a missing tab or line, a wrong owner) and show the rule refuses it. Use the fast fixtures in the test file.
4. Run `tests/test_owner_rendering.py -k fast` on the copy and report its exit code.

Save each probe as a script in `<S>/fix3-rereview/` and name it in its finding.

## Output (return as text, under 900 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, failure scenario and probe script with its exit code; `Not verified:` line.

Rules for findings: flag any stub or fake value standing in for real behaviour, and any catch-all that hides a failure without being documented and logged.
