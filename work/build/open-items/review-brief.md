# Open items task review (reviewer contract; read-only)

You review one batch of the open-items branch in the Deploy Workflow repo. You did not build it. Read-only: write nothing in the repo. Save every probe you run as a script under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-open-items-fd69c5/7a3d4eea-24de-4c3f-a6a4-0645dfde9f6b/scratchpad/review-<batch>/` and name it in the finding it supports. Probes run under 60 s each. Run no pytest suite yourself beyond a probe; the controller already ran the gates (outputs are in the builder's report and below).

Inputs per batch (paths in your dispatch): the brief (requirements), the rulings (`docs/rulings/2026-10-30-open-items.md` on `claude/open-items-fd69c5`; read by absolute path `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/open-items-fd69c5/docs/rulings/2026-10-30-open-items.md`), the builder's report in its worktree, and the review package (commits, stat, full diff with context). The builder's worktree holds the branch tip for running probes; the project interpreter is `"/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"` (run from the builder's worktree root; `pyproject.toml` puts `src` and `.` on the path). If the harness refuses it, say so and review by reading.

Check, in order:
1. **Spec:** each change matches the brief and its ruling; nothing missing, nothing extra.
2. **RED genuineness:** each new test fails for the reported cause on the base and passes on the tip (the controller's RED outputs are in the report; spot-check one by reasoning or a probe).
3. **Quality:** no stub or fake value standing in for real behaviour; no catch-all that hides a failure; no new suppression (`noqa` ≤ 13, `type: ignore` ≤ 5 over `src` and `tests`); no frozen oracle under `cases/**` moved; the code reads like its neighbours.
4. **Blast radius:** who else calls the changed functions; could a genuine (deferred) run now refuse something it accepted before? Name the deferred runs that would show it.

Verdict APPROVE or REVISE. Findings as High / Medium / Low / Info, each with file:line, the failure scenario and the probe. Only High or Medium reopen the batch. Return as text (under 700 tokens), ending with a `Not verified:` line.
