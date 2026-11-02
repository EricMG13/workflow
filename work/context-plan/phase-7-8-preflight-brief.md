# Pre-flight for Phases 7 and 8 (controller, 2026-11-01)

Use `work/context-plan/phase-preflight-brief.md` exactly: the same inputs, checks, output and rules. Where the two differ, this file wins. Your dispatch names your phase.

## What changed since that brief was written

- **Phase 2 is complete** (identity and periods; ledger `.superpowers/sdd/2026-10-31-phase-2-identity-periods/progress.md`). For Phase 8, read its rulings:
  - **P2T4b-R1.** CP-1B's literal pair pins in `owners/cp1b.py` `supported()` stay until Phase 8. Phase 8 removes them with keys for the other pairs. First it must generalise the opening-row guard to the derived year, and decide `_no_earlier_series`.
  - **The owner items for Phase 8**, in `work/context-plan/o5-readiness-and-owner-items.md` under "Phase 2 owner items" and "For Phase 8".
- **Phase 5 Tasks 1, 2 and 6 are complete.** Tasks 3-5 are pending.
- **B29, B30 and B34 are complete.**
- The golden refresh runs before Release 2.

## In-flight and queued lanes (replaces item 3 of the base brief)

- **O3 Task 6, fix round 2, in re-review:** `src/deploy_workflow/owner_workflow.py`, `tests/test_owner_guards.py`, `tests/test_owner_resume.py`.
- **Queued, serial on `owner_workflow.py`:** Phase 5 Task 3, then O3 Task 7, then O6 Task 6 (`run_pathway.py`), then O7b.
- **Single-writer files:** `tests/prompts/rule_lists.golden.json`, `docs/reuse/manifest.json` (D12) and `cases/PINS.json`.

For each task, say whether it touches any of these. If it touches `owner_workflow.py`, name the exact functions, so that the controller can order it in the queue.

## For Phase 7 only

The oracle froze at 5485b8be, under the ruling that Phase 6's oracle freezes first. Check the plan's use of Phase 6's `pinned_line('CP-4C')` against HEAD's `owners/pins.py`.

## For Phase 8 only

The oracle froze at 6534ab95. Its R3 depends on Phase 2 Task 4 (B19), which is now done: check it against HEAD's `earnings_workflow.py` and `owners/cp1b.py`. Also check its stale-literal list (cp2e, cp2h, cpl10), which was derived mechanically at freeze, against HEAD.
