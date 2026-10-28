# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at 6ba071b or later. Fast tests: 990 passed, 2 skipped. History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1 modules:** CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3.
- **Rounds since:** CP-L10 r5 (6e63383); CP-1D r5b + 1D1 (7e29075); G1-X fix 1 (29c0819; G1/S1a suites deferred, so built, not done); CP-3D 6b (f72a8bf) and 6e/6g (fc8c505); CP-DR r5 (5b25007) and 6e (e4de446); CP-1C r6 + fix 1 (e4a0a4d); CP-2E r5-6 (40a3dc6), CP-2A r5-6 + fix 1 (7276630), CP-2D r5/6/6f (b09c33d).
- **Layer reviews:** A (6b20407), B (no commit), C (bb79483); reports `stage1/review-{A,B,C}.md`.
- **LEAD docs:** 8483de4 (E6), 3674158 (round 6 oracle batch), rulings rounds 1–6g, the owner ruling, the CP-2H/4C freeze (658a489), G1-X protocol amendments.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 40e529c (B1 integration) | Stage 2 |
| LEAD 2682310 (CP-5 lease frozen; cp3-cp6 R6 and CP-8 re-pins) | the CP-3 and CP-8 re-pin branches |

## In flight (resume an agent by SendMessage to its id; worktree `.claude/worktrees/agent-<impl id>` unless noted). Cap 10: full.
| Work | Base | Agent | Next |
|---|---|---|---|
| H1 mx-adversary review | 2bd61a7 | a72eed029a03a38bf (impl a69f811059171c714) | H1 open points 1–6 to LEAD with the reviewer's reading |
| CP-8 fix round 1 (M1 raw quote, L1 mutants) | a5c4011 | a3cc9818386e8861a | Opus re-review; then 6h split-and-missing + 2682310 re-pin |
| CP-2G fix round 1 (M1–M3, L4, L5; merge, oracle batch, re-pin) | 0e28916 | a4377a7580e8e70db | Opus re-review; then round 8 A-3 citations (test-first); merge |
| CP-1D raw-quote fix review | 7c88a98 | aa7fe668e36cb82b8 (worktree cp1d-stage1) | merge after APPROVE; signed-basis defect to LEAD |
| CP-3D raw-quote check | lane | a5aa3f0ca842029cd (worktree cp3d-stage1) | scoped review if code changed; then 6h percent_text leading zero |
| CP-2H round 7 | 5d91e7b | a52b5ec0919986ddb | first mx-adversary review, a killed mutant per refusal (29) |
| CP-2E round 6i review (mx-feature) | aed93b3 | see ledger (impl a219254fe68cc1c2d) | merge |
| CP-3C round 8 Part B | 9e78d63 | aa5a4817fa00cd287 | first mx-adversary review |
| CP-4C round 8 Part A (money: A-1) | 0284eca | a2c15c441717ec41c | first mx-adversary review (property test, mutants) |
| CP-1C round 6h (a) | lane | ad161c52418d5cb9a (worktree cp1c-stage1) | scoped review, merge |

## Built, waiting on LEAD round 9
CP-2D 6f (e) and D-1; CP-2A choice 5; CP-8 items 1–5; CP-2G L1–L3 and Info. H1 points follow its review.

## Queued
- CP-3 re-pin to 2682310 (worktree cp3-stage1; cp3-cp6 manifest 525c5f1b…, submissions eaecbcd0…, expected 8ca60c96…, builder 67db9815…).
- CP-5 Stage 1 build (lease `docs/CP5-OWNER-LEASE.md`, oracle `cases/cp5-owner/` in 2682310), one Opus implementer, when a slot frees.
- G1-X `_fill` TypeError mapping stays until LEAD says 0d is integrated.
- Riding Lows: CP-2E E8 `\b` anchors test; CP-2D L1-L6 test gaps (stage1/cp2d/round5-6-review.md).
- Whole-branch review: B4 conventions; CP-L10 not_applicable value_class; CP-8 and CP-3C size; earlier surviving-mutant counts.
- Stage 4: refused-record known gap; 0d `normalise` root fix (then remove the G1-X `_fill` mapping); CP-8 `∅ G#` binding.

## Stage 2 notes collected
In the plan and review files: CP-1D B3; the CP-2D Facility binding; CP-2A L6; the `methods/<cp>.md` entries from round 5; the T4.18 currency/name reader (A5, CP-2D and CP-3C; a row with no currency fails closed); A4 floor-not-stated if the schema allows a missing floor.
