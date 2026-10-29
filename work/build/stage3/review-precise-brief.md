# Stage 3 batch review of the unreviewed builds (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. The integrated tip is `claude/s3-i5` 18dc1fa, checked out at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i4` (read it there; never write there). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

Spec compliance first, then code quality. One review covers all four builds (no per-module rounds).

## Builds and their specs
| Build | Diff | Spec |
|---|---|---|
| G2 `owner_rendering.py` | `c43b681..ce17c2f` (includes 234dfae and the patch commit) | `docs/OWNER-RENDERING-LEASE.md` body + rev 1-3; rulings items 2, 4, 7, 15, 16, 20; `L/work/build/stage3/g2-report.md`, `g2c-report.md` |
| CP-OS | `5af00fe` against its base (`git log --first-parent claude/s3-i5` finds the merge) | `docs/CPOS-OWNER-LEASE.md`; rulings item 1; `L/work/build/stage3/cpos-report.md` |
| CZR driver and fixes | merge-base of `claude/s3-czr` and `claude/s3-i5`, up to `57d3caf` | rulings items 10, 14, 19 (the user: "Stop at pack"); `L/work/build/stage3/czr-brief.md`, `czr-report.md` |
| Legal test | `724a0ad..2e06b2a` | rulings items 13, 18 |

## Known points to settle
1. **CP-OS:** the test's verifier-cache fixture. A cache of genuine runs must be keyed on content, so it can never hide an in-place store change.
2. **D12:** the CZR record for `src/deploy_vii/statement_extract.py` sits in `local_patch_lineage`, not `post_import_patches` (round 5 item 19, `L/docs/rulings/2026-10-28-stage2.md` :345). The probe `<S>/release-review-B/probe_d12_chain.py` never asserts that the last record's sha256 equals the file at rev. Write a stricter probe that does, and run it over every reused file changed since `697fe8a`.
3. **G2:** rulings item 20 Q1 (the S.4 title regex) and the Q3 suffix constraint.
4. **CZR and CP-OS** were written through Bash around the worktree guard. The user accepted them; review them as usual.
5. **Global:** no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged; test-first evidence for each fix.

Gate runs are in progress at `<S>/i5/*.status`. Read them last and report each step as passed, failed, or pending.

Save each probe you run as a script in `<S>/stage3-review/precise/` and name it in the finding.

## Output (return as text, at most about 2k tokens)
Verdict per build (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, failure scenario and probe script; `Not verified:` line.
