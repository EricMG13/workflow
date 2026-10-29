# CP-3C oracle and lease amendment: the CP-1A consumer delta (stage contract; preparer)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-cp3c-cp1a ee95ffb` and confirm the tip. You are the **preparer**. Edit only `cases/cp3c-owner/` (through `cases/cp3c-owner/builder/build.py`), `cases/PINS.json`, and `docs/CP3C-OWNER-LEASE.md` (one dated amendment paragraph, plus the :75 sentence it corrects). Never edit `src/`, `tests/` or another worktree.

## Inputs
| Item | File |
|---|---|
| Ruling and root cause | `L/docs/rulings/2026-10-29-stage3.md` item 23; `L/work/build/stage3/cp3c-driver-report.md` |
| Lease | `docs/CP3C-OWNER-LEASE.md` :9 (amendment format), :47, :56, :70-75, :167, :197 |
| Product rule and entry schema (read only) | `src/deploy_workflow/business_context.py` :344-353 and the consumer-entry validator |
| Base literal | `cases/snapshot/submissions.json#positive.business_context` |
| Precedent | `cases/cp3c-owner/builder/build.py` `cp0_consumer_deltas` (:1277, :1283, :1320) |
| Reproduction | `<S>/cp3c-driver/repro.py` |

## Process
1. Add `cp1a_consumer_deltas` to the builder and `submissions.json`, holding one CP-3C entry. It is appended to the snapshot CP-1A literal's `consumers`. Record it in `manifest.json#upstream_literals` next to the CP-0 line.
   - Fill every field from the lease: CP-3C does not use CP-1A. Lease :56 says that path is Insufficient Information, and :167 says "business context (CP-1A unread)". Cite only sources the snapshot literal's own entries already cite, or the pack's `DownstreamInputs`.
   - If the schema demands a field the lease cannot source, stop and report it.
2. Write one dated amendment paragraph in the lease, in the :9 style, with old → new sha256 for each own file. Correct :75's "CP-1A … literals unchanged".
3. Regenerate through the builder. Then `python3 -I cases/pins.py` and `--check`.
4. Write the builder's targets: the exact `tests/cp3c_runs.py` change (`reach_cp2d` passes the delta-extended CP-1A text to `s1a.drive_cp1a`, as it does for CP-0 at :76), and the PINS digests in `tests/cp3c_runs.py` that move.
5. **Validate against the product without editing `src/` or `tests/`.** Copy `<S>/cp3c-driver/repro.py` to `<S>/cp3c-cp1a/repro_delta.py` and feed it the new literal. CP-1A must now settle `valid`. Then run on to `read_cp2` and CP-2 if the script allows it, and report how far it gets.
6. One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/pins.py --check`.
- A double fresh-copy rebuild of the builder: identical outputs, equal to the committed files.
- `git diff ee95ffb -- cases/cp3c-owner/` changes only the delta, its manifest line and the builder.
- The repro result from step 5.

## Outputs (return as text, under 900 tokens)
Worktree path and tip SHA; the CP-3C entry with a source for each field; the lease amendment text; the builder targets; gate exit codes; how far the repro got; `Not verified:` line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`.
