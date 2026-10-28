# Module-builder lane: resume point (2026-10-28, usage limit)

Lane branch `claude/module-dev-status-review-0981b6`. Plan: `docs/superpowers/plans/2026-10-28-verified-module-builds.md` (§Rulings rounds). Log: `work/build/ledger.md`. Rulings: `docs/rulings/2026-10-28-stage1.md` (rounds 1–3, all merged).

## Merged into the lane (Stage 1)
CP-2E, CP-DR, CP-3D, CP-4 (including the 4-1 re-pin), CP-1D (fix 1).

## Paused work (every agent finished and committed on its own branch; nothing is running)
| Module / task | Branch | Worktree (`.claude/worktrees/…`) | Next step |
|---|---|---|---|
| G1-X (Stage 2): **done d36b5ab** (build-only; gates 0; light probes pass; report `work/build/g1x/report.md`) | `worktree-agent-a3179638c813adbe7` | agent-a3179638c813adbe7 | mx-adversary review (ordering and replay), then H1. Send LEAD the 5 open items in the report (validator seam needs a §2 amendment) |
| CP-8 Stage 1: **done 1cf8b93** (102 passed, gates 0; report `work/build/stage1/cp8/report.md`) | `worktree-agent-a3cc9818386e8861a` | agent-a3cc9818386e8861a | LEAD rules the 12 raising states and points 13–23 first, then a rulings round, then adversary review |
| CP-2G Stage 1: **done 53816b7** (147 passed, gates 0; report `work/build/stage1/cp2g/report.md`) | `worktree-agent-a4377a7580e8e70db` | agent-a4377a7580e8e70db | LEAD rules the 9 raising states and the decisions to confirm, then a rulings round, then adversary review. The methodology merge re-pins its builder and manifest |
| CP-3C Stage 1: **done 09d9ee7** (96 passed, gates 0; report `work/build/stage1/cp3c/report.md`) | `worktree-agent-aa5a4817fa00cd287` | agent-aa5a4817fa00cd287 | LEAD rules points 1–8 (COST-01 at 0 bp first), then a rulings round, then adversary review. The methodology merge re-pins its builder and manifest |
| CP-1C fix 1 + amendment 1 + rulings: **done 190eae7** (98 passed, gates 0, 15/15 reviewer mutants killed; probe1 exits 1 only because ruled refusals now refuse its inputs) | `worktree-cp1c-stage1` | cp1c-stage1 | adversary re-review. Send LEAD: page:2 duplicate label (provisional `Peer table not found`); peers source not `ready` refused before parse (agent's extension); C1 gap-field order gap by gap; 1C2 cell choices (period, unit, value class) |
| CP-L10 fix 1 + amendment 1 + L10-a/c: **done 394fdc3** (55 passed, gates 0, 14/14 mutants in adapted `l10_mutate_r1.py`; test-first not followed, made up for by 23 failures against f4f3f8f) | `worktree-agent-aa6ef474a0f78ec9e` | agent-aa6ef474a0f78ec9e | adversary re-review. Send LEAD: assessment confidence Insufficient Information accepted (Rule says Medium or Low; step 5 refuses only High); B6 unit check may refuse real missing facts whose unit is None |
| CP-1D rulings (1D1–1D10, 1D2 follow-up, 1D-x, L-a/L-b): **done 85a2095** (71 passed 1 skipped, gates 0; probe7 exits 1 only because 1D9 now refuses its zero-item bridge) | `claude/cp1d-stage1` | cp1d-stage1 | adversary review of the ruling diff, merge. Send LEAD: 1D3 label choice (T1D.3 row labels); 1D2 limitation position; the agent's own 38-digit bound on amounts; partial-mode residuals (a chip to a would-be-known full-only fact is not flagged) |
| CP-2D rulings (2D1–2D9, 2D-a–d, N2/N3): **done c8660ab** (100 passed, gates 0, probes 0, 25/25 re-targeted mutants killed in `scratchpad/mutate_r3.py`; nothing valid raises; test-first not followed, red was only a collection error) | `worktree-agent-a69f2394899aee6d5` | agent-a69f2394899aee6d5 | adversary re-review (N1 settled by 2D-a), merge. Send LEAD: unruled T2E.7 labels; inferred GAP-01 wordings and their precedence; facility-term and empty-schedule reasons; negative debt reuses the "zero" reason; no refusal for a maturity-wall assessment without the date ref; amend-and-extend and distressed exchange not on the list |
| CP-2A rulings (A1–A8) + M4: **done fe44e52** (86 passed 1 skipped, gates 0; report `work/build/stage1/cp2a/rulings-report.md`; the branch copy of report.md is stale) | `worktree-agent-a34fec3e9469279cd` | agent-a34fec3e9469279cd | adversary re-review of M4 and the ruling diff; a third fix goes to mx-autonomous plus a fresh implementer. On merge, keep the lane's report |
| CP-3D rulings (D1–D3, X1, Low A): **done 9b871a7** (174 passed, gates 0, probes 0; nothing valid raises) | `claude/cp3d-stage1` | cp3d-stage1 | mx-precise review of the ruling diff, merge. Send LEAD: YLD-01 with a quoted level, known maturity and missing mid margin uses an unruled neutral form `The all-in yield is not calculated: [T3E.3.r05.mid] is not available.`; T3E.7 "Simple discount margin" row names the wrong cause for bid/offer/talk-only and absent maturity (builder parity) |

If an agent stopped mid-task, its worktree holds the uncommitted work: inspect it with `git status` and `git diff` before re-dispatching.

## Not started
- Rulings rounds for CP-2E (E1–E5) and CP-DR (R1–R3), on their branches `worktree-agent-a219254fe68cc1c2d` and `claude/cpdr-stage1`.
- CP-3 waits for the Stage 1 review.
- Stage 1 review (mx-architect, once all Stage 1 modules are merged). It carries the CP-4 casefold test and the merged modules' Low notes.

## Methodology change (landed, not merged into the lane)
`lead/methodology-serialised` at a48990d (ede9ffe is the change; mx-precise COMMIT). Merge it before any Stage 2 build. It re-pins the builder and manifest of CP-1C, CP-1D, CP-2E, CP-2G, CP-3, CP-3C, CP-3D, CP-8, CP-DR, CP-L10 and CP-OS, plus CP-L10 expected (L2/L3 text only). Every module test that pins those hashes needs a re-pin in the same merge: one mechanical batch, checked by the controller running the affected Stage 1 tests. Next from LEAD: the CP-1D 1D1 amendment and the CP-2G, CP-2H and CP-4C re-pins.

## Stage 2 notes collected
- `methods/<cp>.md` notes: cp1d (1D4), cpl10 (L10-b), cp2d (the 2D-a stem list).
- CP-2A `validate` raises on CP-1 head integrity, which needs a G1-X precheck.
- CP-4 T4C.7 display is open in QUEUE (engine-side; the owner decides).

## LEAD state
LEAD is paused too. The G1-X open items and the open Stage 1 points for CP-1C, CP-L10, CP-3D and CP-1D are queued for rulings in LEAD's `work/lead/RESUME.md`. Until then each case keeps failing closed or composing as now.

## First steps next session
1. Merge `lead/methodology-serialised` (a48990d) into the lane, with one re-pin batch for module tests whose builder or manifest hashes changed. Verify it by running the affected Stage 1 tests.
2. Send LEAD the open points it doesn't yet hold: CP-8 (12 raising states plus points 13–23), CP-2G (9 plus 8 decisions), CP-3C (1–8), CP-2D (the inferred wordings in the CP-2D row above), CP-2A (M4 wording and the items in `work/build/stage1/cp2a/rulings-report.md`). Each module report lists them.
3. Reviews, as slots allow:
   - adversary re-reviews of CP-1C, CP-L10, CP-2D and CP-2A;
   - adversary reviews of the CP-1D ruling diff and of G1-X;
   - mx-precise review of the CP-3D ruling diff.

   Merge each approved branch.
4. Rulings rounds for CP-2E (E1–E5) and CP-DR (R1–R3).
