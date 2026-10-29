**CP-3C CP-1A consumer delta review (claude/s3-cp3c-cp1a c941672 vs ee95ffb)**

**Spec verdict: APPROVE.** I found no High or Medium findings. Every check in the contract passed.

1. **Entry fields** (`cases/cp3c-owner/submissions.json:74-85`, `builder/build.py:738-747`)
   - Every field restates the lease: the optional-edge row at `docs/CP3C-OWNER-LEASE.md:58`, the own limitation "business context (CP-1A unread)" at :169, and "Optional edges … reads none" at :235.
   - The entry claims no use of CP-1A. `citations` and `flag_topics` are empty.
   - The status is correct. The product's only definition of the shared `Readiness` enum (`src/deploy_vii/readiness.py:27`) is in `src/deploy_vii/methods/cp0.md:63-67`:
     - READY needs "adequate located evidence without relevant gaps". That is false here, because the asset_sale_or_equity path stays Insufficient Information.
     - READY_WITH_LIMITATIONS means "the owner can perform its method with bounded gaps". This fits.
     - CONDITIONAL is for "a missing source that prevents that owner's workflow" and BLOCKED is for "unusable evidence". Neither applies.
   - `methods/cp1a.md:74-75` adds no other meaning.
   - The validator compares consumers as a set (`business_context.py:682`), so appending CP-3C at the end is accepted.
2. **Scope**
   - Exactly five files changed: build.py, manifest.json, submissions.json, PINS.json and the lease. Nothing in `src/` or `tests/` changed.
   - `expected.json` is byte-identical (`git diff --quiet` exit 0).
   - The lease's old and new sha256 values equal ee95ffb's PINS and the rebuilt files: acba00f0…, c63e5314…, 1fc39647…, and c5089cff… unchanged.
3. **Rebuilds** (probe `rebuild_twice.sh`, exit 0)
   - Two fresh `git archive` copies of c941672 rebuilt identically, and both equal the committed files.
   - `python3 -I cases/pins.py --check` in a fresh copy: "matches 86 paths", rc=0.
4. **Repro** (probe `repro_delta_copy2.py`, the preparer's repro pointed at a fresh c941672 copy)
   - It ran on the lane venv interpreter (`.venv/bin/python`, 3.13) and exited 0.
   - Output: `cp1 done`, `cp1a valid []`, `cp2 valid []`, `cp2d valid []`, `cp3c valid []`. The run gets through to the first positive CP-3C submit.
5. **Driver builder targets** match the committed code.
   - `s1a.drive_cp1a` takes `text=` (`tests/s1a_runs.py:369-380`), and `cp0_text` (`tests/cp3c_runs.py:71-78`) is the model to follow.
   - `reach_cp2d` currently calls `drive_cp1a` without `text` (`tests/cp3c_runs.py:137`), which is the line to change.
   - The `PINS` at `tests/cp3c_runs.py:34-39` still hold the old digests. Three of them must move to the new values; the expected.json digest c5089cff… stays.

**Quality verdict: APPROVE, two Low wording notes.** No stub, fake value or catch-all was introduced.

- **Low: "four PINS move" overstates it** (`docs/CP3C-OWNER-LEASE.md:3`). Only three of the four `tests/cp3c_runs.py` PINS change; expected.json is unchanged, as the same paragraph says. The driver builder could misread this. Suggest "its PINS for build.py, manifest.json and submissions.json move". Evidence: the `rebuild_twice.sh` output.
- **Low: two paths named where the lease has one** (`submissions.json:78-80`, `build.py:742-744`, lease :3). The text says "owner-support and asset-sale paths" (plural), but the oracle has a single path, `asset_sale_or_equity`. Lease :58 also says "that path". The meaning holds, since owner support plausibly maps to the equity half, but the wording does not match.

Both Lows can ride with the next fix or the end batch.

Probe scripts and output are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-cp1a-review/`:
- `rebuild_twice.sh`
- `repro_delta_copy2.py`
- `repro.out`

Not verified: no pytest suites ran (`tests/test_connect_cp3c.py` and the rest); the `tests/cp3c_runs.py` change is not applied, and the repro overrides PINS in memory; gap_minimum_cash, gap_no_repricing, the blocked cases and the sealed receipt were not run; I did not re-run a negative probe showing the base literal is refused without the delta (I took that from the driver report); no ruff, mypy or suppression gate ran.
