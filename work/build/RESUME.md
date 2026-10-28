# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at b76128f or later. Fast tests 1008 passed, 2 skipped History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1 modules:** CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3.
- **Rounds since:** CP-L10 r5 (6e63383); CP-1D r5b + 1D1 (7e29075); G1-X fix 1 (29c0819; G1/S1a suites deferred, so built, not done); CP-3D 6b (f72a8bf) and 6e/6g (fc8c505); CP-DR r5 (5b25007) and 6e (e4de446); CP-1C r6 + fix 1 (e4a0a4d); CP-2E r5-6 (40a3dc6), CP-2A r5-6 + fix 1 (7276630), CP-2D r5/6/6f (b09c33d); CP-1D raw-quote fix (7c88a98); CP-2E 6i (aed93b3); CP-1C 6h (0ef2dc8).
- **Layer reviews:** A (6b20407), B (no commit), C (bb79483); reports `stage1/review-{A,B,C}.md`.
- **LEAD docs:** 8483de4 (E6), 3674158 (round 6 oracle batch), rulings rounds 1–6g, the owner ruling, the CP-2H/4C freeze (658a489), G1-X protocol amendments.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 40e529c (B1 integration) | Stage 2 |
| LEAD 2682310 (CP-5 lease frozen; cp3-cp6 R6 and CP-8 re-pins) | the CP-3 and CP-8 re-pin branches |

## In flight (resume an agent by SendMessage to its id; worktree `.claude/worktrees/agent-<impl id>` unless noted). Cap 10.
| Work | Base | Agent | Next |
|---|---|---|---|
| H1 fix round 1 (F2, L1-L4 tests) | 2bd61a7 | a69f811059171c714 | Opus re-review; F1 waits for LEAD |
| G1-X fix 2 (remove `_fill` TypeError mapping; lane + 31aeee0) | lane | a1095e3383256490c (worktree g1x-fill) | scoped mx-adversary review |
| CP-2G fix round 2 (round 8 A-3 citations), last in budget | dcfcbc0 | a4377a7580e8e70db | one Opus re-review of fix 1 + 2; merge |
| CP-8 review of fix 1 + 6h (mx-precise) | cba7f82 | see ledger (impl a3cc9818386e8861a) | one Opus review of fix 1 + 6h; merges with CP-3 and CP-5 |
| CP-2H round 7 | 5d91e7b | a52b5ec0919986ddb | first mx-adversary review, a killed mutant per refusal (29) |
| CP-3C round 8 Part B | 9e78d63 | aa5a4817fa00cd287 | first mx-adversary review |
| CP-4C round 8 Part A (money: A-1) | 0284eca | a2c15c441717ec41c | first mx-adversary review (property test, mutants) |
| CP-5 Stage 1 build | lane + 2682310 | a490ed6228f4da606 (worktree cp5-stage1) | first mx-adversary review; merges with CP-3 and CP-8 |

Built, waiting to merge: CP-3 re-pin 6c6ea02 (worktree cp3-stage1), pin-only diff checked; merges with CP-5 and CP-8.

## Built, waiting on LEAD round 9
CP-2D 6f (e) and D-1; CP-2A choice 5; CP-8 items 1–5; CP-2G L1–L3 and Info. Also with LEAD: H1 F1, I1, I2, open points 1 and 6; signs never read (CP-1D `_AMOUNT`, CP-3D `_token_once`).

## Queued
- Riding Lows: CP-3D name wrap-join (quote-6h-review Low 1); CP-2E negative-floor raise test (6i review); CP-2D L1-L6 test gaps (stage1/cp2d/round5-6-review.md).
- Whole-branch review: B4 conventions; CP-L10 not_applicable value_class; CP-8 and CP-3C size; earlier surviving-mutant counts.
- Stage 4: refused-record known gap; 0d `normalise` root fix (then remove the G1-X `_fill` mapping); CP-8 `∅ G#` binding.

## Stage 2 notes collected
In the plan and review files: CP-1D B3; the CP-2D Facility binding; CP-2A L6; the `methods/<cp>.md` entries from round 5; the T4.18 currency/name reader (A5, CP-2D and CP-3C; a row with no currency fails closed); A4 floor-not-stated if the schema allows a missing floor.
