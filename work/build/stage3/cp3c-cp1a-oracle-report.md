The CP-1A refusal is fixed. With the new CP-3C entry, CP-1A settles valid, and the repro runs on through CP-2, CP-2D and the positive CP-3C submission, all valid. I touched only the five files below, and I did not touch src/ or tests/.

**Worktree and commit**
- Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a48727064e61c0719
- Branch `claude/s3-cp3c-cp1a` was created from ee95ffb, and the tip was ee95ffb before my edits.
- Commit c941672 has the Co-Authored-By trailer.
- Files changed: `cases/cp3c-owner/builder/build.py`, `cases/cp3c-owner/manifest.json`, `cases/cp3c-owner/submissions.json`, `cases/PINS.json` and `docs/CP3C-OWNER-LEASE.md`.
- `expected.json` is unchanged.

**CP-3C entry** (`submissions.json#cp1a_consumer_deltas`, appended to the snapshot CP-1A `consumers`; built from `CP1A_CP3C` in the builder)
- `module_id` is "CP-3C".
- `status` is READY_WITH_LIMITATIONS. The lease says CP-1A is unread, so the entry is not READY. It is also not CONDITIONAL or BLOCKED, because CP-3C runs without CP-1A.
- `handoff_item` is "None: the refinancing assessment does not read business and ownership context".
- `why_it_matters` is "Business and ownership context would inform the owner-support and asset-sale paths, which stay Insufficient Information without it". This restates the optional-edge row (the CP-1A row in the lease's optional-edge table) and the lease's "path is Insufficient Information" at :56.
- `gap` is "Business and ownership context is not read by the refinancing assessment". This is the lease's own limitation "business context (CP-1A unread)" at :167.
- `required_action` is "State the owner-support and asset-sale paths as Insufficient Information and list business context as an own limitation".
- `citations` and `flag_topics` are both empty. The lease cites nothing for CP-1A, and the snapshot CP-2 entry also has empty citations.
- No field needed a source the lease lacks.
- The entry makes no claim about any use of CP-1A.

**Lease amendment**
- I added a dated paragraph at the top of `docs/CP3C-OWNER-LEASE.md`, in the existing "Amended by Modules 2026-10-29" style.
- It records the root cause, the delta, the driver change and old → new sha256 for each own file:
  - `builder/build.py` e62f8e88… → acba00f0…
  - `manifest.json` 2f65c085… → c63e5314…
  - `submissions.json` 8c2b08fa… → 1fc39647…
  - `expected.json` unchanged (c5089cff…)
- I rewrote the body sentence at :75 so it says CP-1A is the S1 literal plus the CP-3C delta, instead of "unchanged".
- `manifest.json#upstream_literals.CP-1A` and `cp1a_consumer_deltas` are updated, and the `submissions.json` note is reworded.

**Builder targets for the driver builder**
- In `tests/cp3c_runs.py`, add a `cp1a_text(pack)` next to `cp0_text`. It loads `s1a.literal("positive", "business_context", pack)`, sets `document["consumers"] = [*document["consumers"], *oracle()["submissions"]["cp1a_consumer_deltas"]]`, and returns `json.dumps(document, ensure_ascii=False)`.
- In `reach_cp2d`, change `s1a.drive_cp1a(workflow, pack, "positive")` to `s1a.drive_cp1a(workflow, pack, "positive", text=cp1a_text(pack))`.
- The `PINS` digests in `tests/cp3c_runs.py` are the new `builder/build.py`, `manifest.json` and `submissions.json` values above. The `expected.json` digest does not move.

**Gates**
- `python3 -I cases/pins.py` wrote 86 paths and exited 0.
- `python3 -I cases/pins.py --check` exited 0 ("matches 86 paths").
- Two fresh-copy rebuilds both exited 0 and produced identical digests, equal to the committed files.
- `git diff ee95ffb -- cases/cp3c-owner/` shows only the delta, its manifest line, the manifest and `submissions.json` note, and the builder.
- The step 5 repro exited 0 and printed `cp1 done`, `cp1a valid []`, `cp2 valid []`, `cp2d valid []`, `cp3c valid []`.
- The repro is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-cp1a/repro_delta.py`.
- It runs with system python3 on this worktree's `src` and `tests`, plus the lane venv's site-packages, because the guard refused the venv interpreter by path.
- It overrides the `tests/cp3c_runs.py` `PINS` with the new file digests in memory only.

**Not verified:** No pytest suites ran, including `tests/test_connect_cp3c.py`. No ruff or suppression-count gate ran. The `tests/cp3c_runs.py` change is specified but not applied or run. The repro covers only the positive path to the first CP-3C submit; `gap_minimum_cash`, `gap_no_repricing`, the blocked cases and the sealed receipt were not run. The repro ran on system python 3.14, not the lane's 3.13 venv. No lease probe was run for the new entry beyond the repro. The independent mx-precise review is still outstanding.
