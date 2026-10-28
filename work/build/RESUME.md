# Module-builder lane: resume point (2026-10-28, session 3)

Lane `claude/module-dev-status-review-0981b6` at f0e4a6d or later. Module tests: 781 passed, 2 skipped, 1 xfailed. History is in `work/build/ledger.md`; the plan is `docs/superpowers/plans/2026-10-28-verified-module-builds.md`.

## Merged into the lane
- **Stage 1:**
  - nine modules: CP-2E, CP-DR, CP-3D, CP-4, CP-1C, CP-2D, CP-L10, CP-2A, CP-1D;
  - the methodology change (301fd90) and the CP-1C re-pin.
- **LEAD docs:**
  - rulings rounds 1–5 and 5b;
  - the G1-X protocol §2, §3 and §5 amendments;
  - the CP-2H and CP-4C leases and oracles.
- **Stage 1 layer review:**
  - group A merged (6b20407), report in `stage1/review-A.md`;
  - group B made no commit, report in `stage1/review-B.md`;
  - group C merged with CP-3 (b97c735), report in `stage1/review-C.md`.
- Approved and merged:
  - CP-L10 round 5 (6e63383);
  - CP-1D round 5b + 1D1 (7e29075);
  - G1-X fix 1 (29c0819; G1/S1a suites deferred);
  - CP-3D 6b (f72a8bf);
  - CP-DR round 5 (5b25007).

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 8483de4 (CP-2E E6 oracle) | the CP-2E follow-up: re-pin, and the strict xfail becomes the live E4a test |
| LEAD 40e529c (B1 integration) | Stage 2 |

## In flight (resume an agent by SendMessage to its id; worktree = `.claude/worktrees/agent-<id>` unless noted)
| Work | Agent | Next |
|---|---|---|
| H1 host source mapping | a69f811059171c714 | mx-adversary review |
| CP-8 round 6c follow-up | a3cc9818386e8861a | first mx-adversary review |
| CP-2G first adversary review (0e28916) | af5c5ac1e28b12e3e | merge after APPROVE; take the oracle-batch re-pin |
| CP-3C rulings round 5 | aa5a4817fa00cd287 | then round 6 A1/A5 after the oracle batch; first review |
| CP-4C Stage 1 build | a2c15c441717ec41c | rulings round, then first review |
| CP-3D round 6e (worktree `cp3d-stage1`) | a6f4f9bfa998a6721 | scoped review |
| CP-DR round 6e (worktree `cpdr-stage1`) | a3c578c73e0bfdae5 | scoped review |
| CP-1C round 6 B1 review (74a2c72, worktree `cp1c-stage1`) | acfbe4c6c68b01967 (mx-precise) | merge; label-case answer from LEAD rides along |

Built, waiting:
- CP-2H 5d91e7b (agent a52b5ec0919986ddb): 8 fail-closed states with LEAD. Then a rulings round with the oracle-batch re-pin, then the first review.
- CP-2D b8a5751 (agent a69f2394899aee6d5): the form-4 labels and readings are with LEAD. Its next round (A1, A5) follows the oracle batch, and one scoped review covers both.

## Queued (subagent cap 10)
- **LEAD round 6 is pending.** Group C's C-3D-1 (Medium), C-3D-2, C-3D-3, C-DR-1 and C-3-3 were sent for it, and the CP-3D follow-up waits on them. It rules group A A1–A5, group B B1–B4 and the CP-2A P1 statuses, and a CP-2A oracle amendment adds `fixture_quarter_known`. The CP-2E, CP-2A and CP-1C follow-ups wait for it so each lands in one round. CP-2D takes A1 and A5 in a round after its round 5 work.
- **Owner ruling on CP-2A P1 (option 1).** On a quarter base, every ratio and every ratio-based break is not calculated. Flows and the FCF break stay. Hold the code change until round 6 and the oracle amendment land. No Stage 2 run on a quarter base before then.
- CP-2E follow-up: E6 cherry-pick 8483de4, re-pin, xfail flip; E7, E8. Implementer a219254fe68cc1c2d.
- CP-2A follow-up: names, limitation refs. Implementer a34fec3e9469279cd.
- CP-1C follow-up: P1 plus B1, once LEAD rules B1. Worktree `cp1c-stage1`.
- With LEAD:
  - B1 and B2 (group B);
  - the group A Lows (CP-2D months, CP-2A already-reached, CP-2E negative denominators and floor limitation);
  - CP-2D facility currency (C-7 applies?).
- H1 after the G1-X re-review. It also guards `host._execution_state` (protocol §5).

## Stage 2 notes collected
These are in the plan and the review files:
- CP-1D B3 (prose-check `overall.rationale` in the validator);
- the CP-2D Facility binding;
- CP-2A L6 (`base_periods[*].kind`);
- the `methods/<cp>.md` entries named in round 5.
