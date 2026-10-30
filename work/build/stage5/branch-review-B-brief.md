# Stage 5.3 whole-branch review, lens B: seams and boundaries (stage contract; mx-autonomous, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Branch under review: `4822066..9f71bfa`. `4822066` is the commit that added the plan; `9f71bfa` is the lane after the Stage 4 release. The diff is about 43k lines of `src`, so review by tracing paths and searching, not line by line. Read from `L` with `git show 9f71bfa:<path>`, `git diff`, `git grep … 9f71bfa`. For probes, extract a copy with `git archive 9f71bfa | tar -x -C <S>/s53/B/tree`, write only under `<S>/s53/B/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Run fast tests and probes only; the controller is running the genuine suites now.

You did not build or stage-review this code. Another Opus reviewer covers calculation invariants (lens A); stay on lens B.

## Inputs
| Item | File |
|---|---|
| Plan: goal, constraints, Review Focus 4-5 | `L/docs/superpowers/plans/2026-10-28-verified-module-builds.md` :1-60 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` (items 30, 31, 45 allow `src/deploy_vii` edits; the rest for context) |
| Library-boundary record | `docs/reuse/manifest.json` (`post_import_patches`); the D12 probe `L/work/build/keep/stage3-review/precise/probe_d12_strict.py <tree> 697fe8a HEAD` |
| Earlier stage reviews (do not re-report their findings; report a regression of one) | `L/work/build/stage2/g1x-guards-review.md`; `L/work/build/stage3/review-precise.md`, `review-arch.md`; `L/work/build/stage4/review-arch.md`, `batch1-adversary.md`, `batch1-fix1-adv.md` |
| Owner-held findings (do not re-report) | `L/work/build/stage2/lows.md` |

## Process
1. **Library boundary.** Every `src/deploy_vii` change in the branch is either a D12 registration or a patch that a ruling allows, and each has a manifest record (run the D12 probe on your copy). List any change with neither.
2. **Registrations (Review Focus 4).** The merged tables (`OWNER_SPECS`, `_PROBES`, `_VIEWS`, `host._SOURCE_STEPS`, G2 `DELIVERY_SCOPES`, block bindings) hold exactly one consistent row per module, with no duplicate or orphan key. Write a probe that cross-checks them.
3. **Rendered vs settled (Review Focus 5).** Trace one delivery scope end to end, from settled head through `owner_rendering` and `report_view` to the page payload. Every rendered fact must come from `store.head_module(head)`, with nothing recomputed or defaulted on the way.
4. **Verifier seams.** `owner_workflow` receipt verification, G2's render receipt and verifier, and the CP-OS navigation: does anything they accept depend on bytes the threat model says the attacker controls without a check? Do not redo the Stage 4 class analysis; look at the joins between components.
5. Across all of these, look for any stub or fake value standing in for real behaviour, and any catch-all that hides a failure without a documented, logged fail-open.

Save each probe as a script under `<S>/s53/B/` and name it in its finding.

## Output (return as text, at most about 2k tokens)
Verdict (PASS / REVISE); findings ranked High, Medium, Low, Info, each with file:line, the failure scenario and the probe script with its exit code; `Not verified:` line.
