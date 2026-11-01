# Implementer contract (context plan build, every task)

Work from `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/tool-use-m365-copilot-research-8ff28f`
on branch `claude/context-plan-build`. First check `git rev-parse --short HEAD` equals the BASE your
dispatch names; if not, stop and report NEEDS_CONTEXT.

1. Read your task brief first: it is your requirements, with the exact values to use verbatim.
   Read the plan file it came from only for the sections the brief points at.
2. TDD: write the RED test(s) first, run them, see them fail for the expected reason, then
   implement until GREEN. Record both outputs.
3. Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
   Run the affected tests your brief names (and any test file whose imports you change). Gates on
   changed files: `ruff check`, `ruff format --check`, and `mypy <files>` (all via the venv's
   `-m ruff` / `-m mypy`). All must exit 0 before you commit.
4. Never: a stub or fake value standing in for real behaviour; a catch-all that hides a failure;
   a network call; reading a credential, key file or provider env var; editing `src/deploy_vii`
   except files your brief names (each such change appends one `post_import_patches` record to
   `docs/reuse/manifest.json` in the same commit: destination, imported_sha256, prior_project_sha256,
   project_commit, sha256, reason, review — copy the last record's shape; for a file not in the
   manifest's `files[]` use ruling B14's repo-authored shape); editing DEPLOY VII. For every file you
   change that other files may pin (anything under `src/deploy_vii`, `cases/`, a lease), run
   `git grep -n <old sha256>` and report each hit: a pin you leave stale breaks an oracle builder.
   You never re-pin an oracle yourself (a separate preparer does); name the hits as a concern.
5. No new dependency. No new pytest marker (pyproject has `--strict-markers`).
6. Do not dispatch subagents, not helpers and never a reviewer. Review is the controller's job.
7. Commit with plain `git` (message from your brief, ending with the line
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Do not push, merge or switch branches.
   Stage only the files you changed, by path (`git add <path>`); never `git add -A`, `.` or `-a`:
   other agents' uncommitted files (plans, reviews) are in the tree.
8. If the brief and the code disagree, or you need a decision, stop and report NEEDS_CONTEXT or
   BLOCKED with specifics. Do not guess.
9. Self-review your diff (completeness, names, YAGNI, existing patterns, tests check behaviour).
10. Write the full report to the report path in your dispatch: what you built, files changed,
    TDD evidence (RED and GREEN commands and output), gate results with exit codes, every
    `table_id`/`row_id`/`field` change you made (R7), concerns, and a last line
    `Not verified:` listing what no gate or test exercised.
11. Reply with ONLY (under 15 lines): Status DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT;
    commits (short SHA + subject); one-line test summary; concerns; the report path.
12. If resumed with review findings: fix them, run every reviewer probe named in the findings and
    the covering tests, append a fix report (changes, commands, output, probe exit codes) to the
    same report file, and reply with the same short contract.
