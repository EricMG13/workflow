# CP-3C CP-1A consumer delta review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s3-cp3c-cp1a` c941672 against ee95ffb (read with `git show`/`git diff` from `L`; never write into any worktree). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. You did not prepare this change and will not build the driver change that follows it.

## Inputs
| Item | File |
|---|---|
| Ruling, root cause, preparer's contract and report | `L/docs/rulings/2026-10-29-stage3.md` item 23; `L/work/build/stage3/cp3c-driver-report.md`; `L/work/build/stage3/cp3c-cp1a-oracle-brief.md`; `L/work/build/stage3/cp3c-cp1a-oracle-report.md` |
| Lease | `docs/CP3C-OWNER-LEASE.md` (the new amendment paragraph, :56, :75, :167) |
| Product rule and schema (read only) | `src/deploy_workflow/business_context.py` (`cp1a_consumers` :344-353, the consumer-entry validator and the status enum's meaning) |
| Base literal | `cases/snapshot/submissions.json#positive.business_context` |
| Repro | `<S>/cp3c-cp1a/repro_delta.py` |

## Process
1. Check every field of the new CP-3C entry against the lease, and that it states no use of CP-1A the lease does not. Judge whether `READY_WITH_LIMITATIONS` is the status the product's enum means for an optional consumer that does not read CP-1A, or whether another value is meant. Cite the product's definition.
2. Check that only the delta, its manifest and notes, the builder and the lease changed, and that `expected.json` is byte-identical. Check that the lease amendment's sha256 values equal the files.
3. Rebuild twice in two fresh copies under `<S>/cp3c-cp1a-review/`; both outputs must be identical and equal the committed files. Run `python3 -I cases/pins.py --check` in a fresh copy.
4. Rerun the repro, with the lane venv interpreter if you can, and report how far it gets.
5. Check the builder targets for `tests/cp3c_runs.py` (the `cp1a_text` helper, the `reach_cp2d` call, the PINS digests) against the committed files.

Save each probe as a script in `<S>/cp3c-cp1a-review/` and name it in the finding.

## Output (return as text, under 800 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, with probe scripts; `Not verified:` line.
