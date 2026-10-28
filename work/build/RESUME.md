# Module-builder lane: resume point (2026-10-28, usage limit)

Lane branch `claude/module-dev-status-review-0981b6`. Plan: `docs/superpowers/plans/2026-10-28-verified-module-builds.md` (§Rulings rounds). Log: `work/build/ledger.md`. Rulings: `docs/rulings/2026-10-28-stage1.md` (rounds 1–3, all merged).

## Merged into the lane (Stage 1)
CP-2E, CP-DR, CP-3D, CP-4 (including the 4-1 re-pin), CP-1D (fix 1).

## In flight when paused (each commits on its own branch; check `git log` there)
| Module / task | Branch | Worktree (`.claude/worktrees/…`) | Next step |
|---|---|---|---|
| G1-X (Stage 2) | agent branch, see `git worktree list` | agent-a3179638… | adversary review, then H1 |
| CP-2G, CP-8, CP-3C Stage 1 builds | agent branches | agent-a4377a75…, agent-a3cc9818…, agent-aa5a4817… | answer open questions (LEAD), then adversary review |
| CP-1C fix 1 + amendment 1 + 1C/C/1C-x rulings | `worktree-cp1c-stage1` | cp1c-stage1 | adversary re-review |
| CP-L10 fix 1 + amendment 1 + L10-a/c | `worktree-agent-aa6ef474a0f78ec9e` | agent-aa6ef474a0f78ec9e | adversary re-review |
| CP-1D rulings (1D1–1D10, 1D2 follow-up, 1D-x) | `claude/cp1d-stage1` | cp1d-stage1 | adversary review of the ruling diff, merge |
| CP-2D rulings (2D1–2D9, 2D-a–d, N2/N3) | `worktree-agent-a69f2394899aee6d5` | agent-a69f2394899aee6d5 | adversary re-review (N1 settled by 2D-a), merge |
| CP-2A rulings (A1–A8) + M4, fix-rounds=2 | `worktree-agent-a34fec3e9469279cd` | agent-a34fec3e9469279cd | adversary re-review; a third fix goes to mx-autonomous plus a fresh implementer |
| CP-3D rulings (D1–D3, X1) | `claude/cp3d-stage1` | cp3d-stage1 | mx-precise review of the ruling diff, merge |

If an agent stopped mid-task, its worktree holds the uncommitted work: inspect it with `git status` and `git diff` before re-dispatching.

## Not started
- Rulings rounds for CP-2E (E1–E5) and CP-DR (R1–R3), on their branches `worktree-agent-a219254fe68cc1c2d` and `claude/cpdr-stage1`.
- CP-3 waits for the Stage 1 review.
- Stage 1 review (mx-architect, once all Stage 1 modules are merged). It carries the CP-4 casefold test and the merged modules' Low notes.

## Waiting on LEAD
`lead/methodology-serialised` commit. Merge it before the Stage 2 builds of CP-L10, CP-1C, CP-1D and CP-2A. No module edits `methodology.json`.

## Stage 2 notes collected
- `methods/<cp>.md` notes: cp1d (1D4), cpl10 (L10-b), cp2d (the 2D-a stem list).
- CP-2A `validate` raises on CP-1 head integrity, which needs a G1-X precheck.
- CP-4 T4C.7 display is open in QUEUE (engine-side; the owner decides).
