# CP-3C fix round 1, part b: LEAD round 11 rulings, applied before the re-review

LEAD round 11 supersedes two parts of fix 1 (8a45037): the pre-D0 raise and the `names` change. It also adds B2 and B5. These changes belong to fix 1, because the controller is applying the rulings before fix 1's re-review, so they do not open a new fix round. The re-review (mx-adversary, by finding id) covers fix 1 and this part together.

## Step 0
From `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287`, run `git merge claude/module-dev-status-review-0981b6`. The lane now carries round 11 (d60035b). Confirm the merge parent is the lane tip.

## Apply (`docs/rulings/2026-10-28-stage1.md`, `# Round 11`, `## CP-3C`, plus the CP-3C bullet under "LEAD rulings on the For LEAD items")
1. **B1 (Medium). A maturity before D0 is a gap, not a raise.**
   - Put it in `_facility`, in the position slot an unstated maturity date takes.
   - The maturity date stays known. Months and the inside flag become `missing` with `Not calculable: facility <id> maturity date is before the balance date`.
   - Every dependant the ruling lists takes the same reason. Total principal, shares, creditor rows and the nearest maturity date stay known.
   - Write the own line exactly as ruled (label `Facility maturity date (<id>)`, kind Limitation), and use the ruled claim cause.
   - Remove fix 1's invariant raise. Update `probe_past_maturity.py` (copy it to `<S>/cp3c-fix1b/`) so it checks the gap.
2. **Q3. Causes carry no facility id.**
   - Use the ruled frames: an unstated term, an unmatched facility, pre-D0, and FX/currency as in 8-B2.
   - Choose the frame by gap kind, never by comparing reason strings (A39).
   - Drop the `names=` change from fix 1. `prose.check` then takes no facility ids.
3. **B2 (Medium). One Gap own line per unstated term.**
   - This covers annual amortisation, secured status and seniority, with the ruled wording and labels.
   - Per-facility order: currency, maturity date (unstated or before D0), principal, annual amortisation, secured status, seniority, wall rows, then unmatched lines and path lines.
4. **B5. A blank II limitation gets the pinned text.** For an II assessment, a limitation where `not (p.limitation or "").strip()` gets the pinned `paths[<kind>].limitation: an Insufficient Information assessment states its limitation`, at its current position.
5. **Superseded probes.** The round lists `probe_empty_register.py`, `probe_burden_collision.py`, `probe_negative_amort_months.py` and `probe_past_maturity.py`. Copy each to `<S>/cp3c-fix1b/` and update it to the ruled behaviour. Retire a probe only where its state no longer exists, and say which.

B3, B4 and B6 stay as built. The controller decides Q2(f): no extra flag check, because the state is unreachable.

## Rules
- Files you may change: `src/deploy_workflow/owners/cp3c.py`, `tests/test_method_cp3c.py`.
- Test-first, and watch each test fail for the reported cause. No stub, fake value or catch-all.
- Run every new claim string through `prose.issues` and `bare_figures`, and report the hits.
- Gates: the fix 1 brief's gates (`work/build/stage1/cp3c/fix1-brief.md`).
- Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show that each ruling's revert is killed, and re-run your fix 1 runner.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Report (as text)
- Commit.
- Each ruling and its test.
- Probe exit codes, including the updated probes.
- Mutants.
- Gates.
- Stage 2 notes: the `methods/cp3c.md` entries for B3 and B6, and MC-2 needing only the issuer name.
- `Not verified:`.
- Ledger line: `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
