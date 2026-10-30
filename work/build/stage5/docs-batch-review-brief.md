# Stage 5.3 docs batch: review (stage contract; mx-feature, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s5-docs` `07dc002..fbfc905` (`docs/G1X-OWNER-CORE-PROTOCOL.md` §6, `docs/reuse/manifest.json`). Read from `L` with `git show`/`git diff`. For probes, extract a copy under `<S>/docs-review/`, never write into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 51 |
| D12 rule | `L/docs/rulings/2026-10-28-stage2.md` "Round 5 item 19" |
| Brief and report | `L/work/build/stage5/docs-batch-brief.md`, `L/work/build/stage5/docs-batch-report.md` (note its two stated deviations) |
| Probes | `L/work/build/keep/s53-B/probe_d12_strict.py`, `L/work/build/keep/stage3-review/precise/probe_d12_strict.py` |

## Process
1. Check that §6's new text matches the brief word for word and is true. List every `deploy_workflow` import under `src/deploy_vii` at `fbfc905`.
2. For every manifest record that changed or was removed, recompute from git: `project_commit` changes the file, `prior_project_sha256` is the file's sha256 in its first parent, and `sha256` is the file's sha256 at that commit. Check that every removed record's reason survives in the record it was folded into, and that nothing is invented.
3. Judge the two deviations: folding three records outside the six, and keeping the 0d6c714 record. Are they correct under item 19?
4. Run both probes on the branch. Only the owner records should fail (cffdf9f, 1a1a140, bb4553b, 3e5b537, report_view 8aef58d and 24f879a).

## Output (return as text, under 600 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with the record or line, the evidence and the probe with its exit code; `Not verified:` line.
