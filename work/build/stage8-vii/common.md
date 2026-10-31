# Stage 8-vii common rules (every brief here includes these)

- `W` = the controller worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/lead-multi-round-707c23` (branch `claude/s8-vii`; read-only for builders). Briefs are in `W/work/build/stage8-vii/`.
- `K` = `W/work/build/keep/codex-review/`: Codex's consolidated list (`CONSOLIDATED.md`, section 2) and its probes (`probes/v-*/`).
- **Authority.** These are `src/deploy_vii` changes. The user approved each group directly in the s8-vii session on 2026-10-31 ("H03 TL10.4 token", "H09 blank basis", "D1-D3 extractor", "CZR cash scope"). Edit only the files your brief lists. If the fix seems to need another `src/deploy_vii` file, stop and report it; do not edit it.
- **Never edit** `src/deploy_workflow/**`, `docs/reuse/manifest.json` (the controller adds the D12 records last), `cases/**`, or any file another session owns (`canonical_audit.py`, `canonical_gaps.py`, `tests/test_cp1_absent_input.py`, `tests/test_czr_fixes.py`, `tests/test_connect_cpl10.py`, `tests/test_connect_cp8.py`, `tests/test_connect_cpdr.py`).
- **Step 0.** You start in an isolated worktree. Run `git checkout -b <your branch> 5a1d2e2f` (brief names the branch) and confirm `git log --oneline -1` shows 5a1d2e2f.
- **You cannot run the project's Python.** The venv is refused in isolated worktrees; do not work around it (no symlink, no wrapper, no `uv run`). System `python3 -I` with stdlib-only scripts is allowed. The controller runs every test and gate in your worktree after you report.
- **Test first.** Two commits per finding group, plain `git add <files>` then `git commit`:
  1. `test: RED <ids>` — tests only, failing today for the reported cause;
  2. `fix: <ids>` — code (and docstring/doc) only.
  Every commit message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Assert exact values, not shapes. No stub or fake value standing in for real behaviour. No catch-all that hides a failure unless the fail-open is documented and logged. Match the surrounding code's comment density, naming and idiom. Keep diffs minimal.
- Never use bare `git stash`. Never push.
- **Report** as text, under 500 tokens: worktree path, branch, RED and fix SHAs; per finding, what the test asserts and what the fix changes; the exact pytest node ids the controller should run at RED and at fix; a `Not verified:` line.
