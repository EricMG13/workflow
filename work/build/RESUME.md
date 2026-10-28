# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at 4c7b6a3 or later. Fast tests: 924 passed, 2 skipped, 1 xfailed (the CP-2E E4a xfail, live once CP-2E merges). History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1 modules:** CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D, CP-3.
- **Rounds since:** CP-L10 r5 (6e63383); CP-1D r5b + 1D1 (7e29075); G1-X fix 1 (29c0819; G1/S1a suites deferred, so built, not done); CP-3D 6b (f72a8bf) and 6e/6g (fc8c505); CP-DR r5 (5b25007) and 6e (e4de446); CP-1C r6 + fix 1 (e4a0a4d).
- **Layer reviews:** A (6b20407), B (no commit), C (bb79483); reports `stage1/review-{A,B,C}.md`.
- **LEAD docs:** rulings rounds 1–6g, the owner ruling, the CP-2H/4C freeze (658a489), G1-X protocol amendments.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 8483de4 (E6) + 3674158 (round 6 oracle batch) | the CP-2A and CP-2E follow-ups, merged together |
| LEAD 40e529c (B1 integration) | Stage 2 |

## In flight (resume an agent by SendMessage to its id; worktree `.claude/worktrees/agent-<impl id>`)
| Work | Commit | Agent | Next |
|---|---|---|---|
| H1 mx-adversary review | 2bd61a7 | a72eed029a03a38bf (impl a69f811059171c714) | then H1 open points 1–6 to LEAD with the reviewer's reading |
| CP-8 first adversary review | a5c4011 | af64c7b718d678452 (impl a3cc9818386e8861a) | small round for the split-plus-missing case once LEAD rules |
| CP-2G first adversary review | 0e28916 | af5c5ac1e28b12e3e (impl a4377a7580e8e70db) | merge after APPROVE, with the 3674158 re-pin (manifest b0c8c4bc…, submissions 25a96ebb…) |
| CP-2A scoped review (r5, r6, P1-W) | 7ba456e | accf6e5d5ad04d398 (impl a34fec3e9469279cd) | merge with CP-2E; choice 5 to LEAD |
| CP-2E scoped review (E6–E8, A3, A4) | af23f7f | a6116d5fbd782f091 (impl a219254fe68cc1c2d) | merge with CP-2A |
| CP-2D scoped review (r5 + r6/6f, from f0e4a6d) | 3e099de | a9f01544fcd59ff6d (impl a69f2394899aee6d5) | 6f (e) ratio string to LEAD unless the rulings decide it |

## Built, waiting on LEAD (outbox `work/build/outbox-lead.md` plus the 4c7b6a3 message)
- **CP-3C** 9e78d63 (impl aa5a4817fa00cd287): round 5 choices 1–7 → small round → first mx-adversary review. Merges after CP-2A/2E.
- **CP-4C** 0284eca (impl a2c15c441717ec41c): 13 fail-closed states, conservation, citations, choices → rulings round → first adversary review. Merges after CP-2A/2E.
- **CP-2H** 5d91e7b (impl a52b5ec0919986ddb): LEAD round 7 (8 states, 3674158 re-pin) → first adversary review showing a killed mutant per refusal (29).
- **CP-2E A4:** fixed rate with a floor above zero fails closed; floor-not-stated has no Stage 1 path.
- **CP-3D:** leading-zero vs label check order (Info).

## Queued
- CP-1D B2 (invariant raise) rides with the next CP-1D change.
- Whole-branch review: B4 conventions; CP-L10 not_applicable value_class; CP-8 and CP-3C size; earlier surviving-mutant counts.
- Stage 4: refused-record known gap; 0d `normalise` root fix (then remove the G1-X `_fill` mapping); CP-8 `∅ G#` binding.

## Stage 2 notes collected
In the plan and review files: CP-1D B3; the CP-2D Facility binding; CP-2A L6; the `methods/<cp>.md` entries from round 5; the T4.18 currency/name reader (A5, CP-2D and CP-3C; a row with no currency fails closed); A4 floor-not-stated if the schema allows a missing floor.
