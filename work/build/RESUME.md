# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at 7fdddbf or later (rounds 9 and 10 on it). Fast tests 1797 passed, 2 skipped (fast set now includes tests/test_schema_normalise_escapes.py). History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1 modules:** CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3, CP-2G, CP-8, CP-5, CP-4C.
- **Rounds since:** CP-L10 r5 (6e63383); CP-1D r5b + 1D1 (7e29075); G1-X fix 1 (29c0819; G1/S1a suites deferred, so built, not done); CP-3D 6b (f72a8bf) and 6e/6g (fc8c505); CP-DR r5 (5b25007) and 6e (e4de446); CP-1C r6 + fix 1 (e4a0a4d); CP-2E r5-6 (40a3dc6), CP-2A r5-6 + fix 1 (7276630), CP-2D r5/6/6f (b09c33d); CP-1D raw-quote fix (7c88a98); CP-2E 6i (aed93b3); CP-1C 6h (0ef2dc8); CP-3D quote fix + 6h (0b0835f); CP-2D r9 (e3e1277); H1 + fix 1 (278f0aa; F1 fails closed); CP-2A r9 (aa4ab01); CP-3D r10 (a1de97d); G1-X fix 2 + LEAD 0d (857081c; G1/S1a deferred); CP-1D r10 (b7cd02e); CP-2G Stage 1 + fixes 1-2 + r9 (947a57d); CP-2E r10 + fix 1 (a1b50c8); CP-3 re-pin (6c6ea02), CP-8 through r10 (dae85ed), CP-5 + fix 1 (81e8c0b), with LEAD 2682310; H1 fix 2 (38f0f46; deferred suites pending); CP-4C + r8 + fix 1 (3b9c3dc).
- **Layer reviews:** A (6b20407), B (no commit), C (bb79483); reports `stage1/review-{A,B,C}.md`.
- **LEAD docs:** 8483de4 (E6), 3674158 (round 6 oracle batch), rulings rounds 1–6g, the owner ruling, the CP-2H/4C freeze (658a489), G1-X protocol amendments.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 40e529c (B1 integration) | Stage 2 |

## In flight (resume an agent by SendMessage to its id; worktree `.claude/worktrees/agent-<impl id>` unless noted). Opus cap 6 (LEAD AGENTS.md proposal); ruling-text diffs reviewed by mx-feature.
| Work | Base | Agent | Next |
|---|---|---|---|
| CP-2H fix 1 + 1b mx-adversary re-review | f843772 | impl a52b5ec0919986ddb | merge |
| CP-4C round 11 (cp4c/round11-brief.md) | lane | a2c15c441717ec41c | mx-adversary by ruling id, merge |
| H1b, five leased rows + H1 fix 2 Lows (h1/h1b-brief.md) | ebc8294 (worktree h1b) | mx-feature, see ledger | mx-adversary review, merge |
| CP-3C fix 1 + 1b mx-adversary re-review | b9972fd | impl aa5a4817fa00cd287 | merge |
| Shared defect-class library + inventory (stage1/defect-classes-brief.md) | lane | see ledger (worktree defect-classes) | per-module fix rounds from the inventory |


## Next when a slot frees
- G1-side guards (round 10 item 6 follow-ups) ride with the next G1-X change.
- Ride with the next change: CP-2D pre-D0 gap (round 11); CP-2G I1 explicit raise (round 11); per-module quote-edge (B1) and wrap (B3) fixes and blank-text fixes from the defect-class inventory.

## Queued
- Riding Lows: CP-8 r10 (lowercase guard; close-only parenthesis); CP-2E r10 L1 (in fix 1); CP-3D r10 L1 (parenthesis tested at match start, `(-425)`); CP-1D r10 (1D7-before-≤0 unpinned; `(` side untested); CP-3D name wrap-join (quote-6h-review Low 1; needs a public joined-reading helper in deploy_vii.quotes, with LEAD); CP-2D L1-L6 test gaps (stage1/cp2d/round5-6-review.md).
- Whole-branch review: B4 conventions; CP-L10 not_applicable value_class; CP-8 and CP-3C size; earlier surviving-mutant counts.
- Stage 4: refused-record known gap; 0d `normalise` root fix (then remove the G1-X `_fill` mapping); CP-8 `∅ G#` binding.

## LEAD questions
Open questions live in `work/build/stage1/<cp>/questions.md` (cp2h, cp3c, cp4c, cp5) and `stage1/quote-sign-questions.md`. One pointer to LEAD every 20 minutes at most.

## Stage 2 notes collected
In the plan and review files: CP-1D B3; the CP-2D Facility binding; CP-2A L6; the `methods/<cp>.md` entries from round 5; the T4.18 currency/name reader (A5, CP-2D and CP-3C; a row with no currency fails closed); A4 floor-not-stated if the schema allows a missing floor; round 10 sign rule in methods/cp1d, cp3d, cp8, cp2e; unsigned-grammar limitation in methods/cp8 and cp3d; CP-3C facility ids as prose names at MC-2; CP-8 item 2 guard-limit note.
