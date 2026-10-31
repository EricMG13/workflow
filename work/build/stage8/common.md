# Stage 8 common rules (every T-brief includes these)

- `L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only for builders).
- `K` = `L/work/build/keep/codex-review/`, which holds Codex's consolidated list (`CONSOLIDATED.md`, section 2: the finding, its location and the fix direction) and its probes (`probes/v-*/`).
- **You cannot run the project's Python.** The venv is refused in isolated worktrees, so do not work around it. The controller runs every test and gate in your worktree after you report.
- **Commits.** Use plain separate `git add <files>` and `git commit`. Make two commits per finding group:
  1. `test: RED <ids>`: tests only, failing today for the reported cause.
  2. `fix: <ids>`: code only.
  The controller runs the tests at both commits. Every commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- **Do not edit `src/deploy_vii/**`.** If a fix seems to need it, stop and report.
- Assert exact values, not shapes. No stub or fake value standing in for real behaviour. No catch-all that hides a failure.
- Never use bare `git stash`.
- **Report** as text, under 500 tokens:
  - worktree path, branch, the RED and fix SHAs;
  - per finding, what the test asserts and what the fix changes;
  - a `Not verified:` line.
