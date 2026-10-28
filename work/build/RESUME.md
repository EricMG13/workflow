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
  - group B made no commit, report in `stage1/review-B.md`.

## Held (lane stays green)
| Commit | Lands with |
|---|---|
| LEAD 8483de4 (CP-2E E6 oracle) | the CP-2E follow-up: re-pin, and the strict xfail becomes the live E4a test |
| LEAD 2ae589b (CP-1D 1D1 oracle, CP-2G/2H/4C re-pins) | the CP-1D follow-up. Merge CP-1D before CP-2G, CP-2H and CP-4C |
| LEAD 40e529c (B1 integration) | Stage 2 |

## In flight (resume an agent by SendMessage to its id; worktree = `.claude/worktrees/agent-<id>` unless noted)
| Work | Agent | Next |
|---|---|---|
| Stage 1 review group C (CP-3D, CP-DR, CP-4, CP-3) | a6fe6bee590a3ee10 | save `review-C.md`, merge; then CP-DR R4/R5 follow-up; CP-3 merges after |
| G1-X fix 1 (M1, round-4 Part A, L1, L2, L4) | a3179638c813adbe7 | scoped mx-adversary re-review on M1 and Part A |
| CP-8 rulings round 5 | a3cc9818386e8861a | first mx-adversary review |
| CP-2G rulings round 5 (plus the 2ae589b re-pin) | a4377a7580e8e70db | first mx-adversary review |
| CP-3C rulings round 5 | aa5a4817fa00cd287 | first mx-adversary review |
| CP-2H Stage 1 build (plus the 2ae589b re-pin) | a52b5ec0919986ddb | first review |
| CP-4C Stage 1 build (plus the 2ae589b re-pin) | a2c15c441717ec41c | first review |
| CP-1D round 5b Y1–Y4 + 1D1 (worktree `cp1d-stage1`) | a76b4a3f828c3458d | scoped re-review |
| CP-L10 round 5 P2, (e), (f) | aa6ef474a0f78ec9e | scoped re-review |
| CP-2D round 5 D-1..D-6, L1..L5 | a69f2394899aee6d5 | scoped re-review |

## Queued (subagent cap 10)
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
