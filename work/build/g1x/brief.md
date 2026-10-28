# Task 1.1: G1-X owner-core extension (build lane)

Implementer: general-purpose, model opus (user routing, 2026-10-28). Reviewer: mx-adversary (ordering and replay); Opus fix rounds. mx-architect reviews only at the end of Layer 1 (G1-X, G2, H1 all committed) and applies its own fixes.

## Base
- **Commit:** S1a was integrated at `235c208` (fix round 4) on `claude/review-wip-worktrees-0145fe`. The lane branch `claude/module-dev-status-review-0981b6` merges it at the commit named in your dispatch.
- **Worktree:** your own isolated worktree, fast-forwarded to that lane commit (step 0 of the dispatch).
- **Deferred S1a gaps** (`docs/reviews/s1a-owner-run.md`) belong to Stage 4. Don't fix them here, but don't make them worse.
- **Stage 1 cores:** they live on separate branches and are not on your base. G1-X serves them later; don't import them.

## Inputs (read these and nothing else first)
| File | Why |
|---|---|
| `docs/G1X-OWNER-CORE-PROTOCOL.md` | The whole contract, §1–§6 |
| `docs/S1A-OWNER-RUN-LEASE.md` R4-4 | Verifier exception mapping deferred to G1-X |
| `src/deploy_workflow/owner_workflow.py` | Code to extend (S1a version) |
| `src/deploy_workflow/owners/cp1a.py`, `owners/cp2.py` | Existing `probe`/`view` shapes |
| `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py` | Existing test style |
| `docs/CP2A-OWNER-LEASE.md`, `docs/CP2D-OWNER-LEASE.md`, `docs/CP3D-OWNER-LEASE.md` Files sections | The first consumers of each seam; read only |

## Files you may write
- `src/deploy_workflow/owner_workflow.py`
- `tests/test_owner_workflow.py`
- New `tests/test_owner_g1x.py`, if separation helps.
- Nothing else. In particular no `owners/<cp>.py` for any module, no `src/deploy_vii` edit, and no case files.

## Behaviour to build (protocol references)
1. **§1/§2 owner-core entry and registration.**
   - `OwnerSpec.entry` gains `"owner_core"`.
   - Add a fixed `_CORES: dict[str, ModuleType]`. It starts empty, and module tasks add their rows.
   - `_check_specs` requires `entry == "owner_core"` exactly for owner-only modules (those where `step_chain` raises "has no live step contract").
   - `submit_review` dispatches owner-core steps to `_CORES[m].submit(store, ticket_id, step_id, payload, rules)`, which returns `live.submission.Submitted`.
   - `_owner_historical`, `_activate` and the verifier use `core.STEP_IDS` where `step_chain` has none.
   - `_fill` normalises through `core.SCHEMAS[step]` when the step is not in `live.submission.STEPS`.
2. **§2 RULES routing.** With `rules="journaled"` on an owner-only step with `sources=True`, call `core.RULES(text, seen)` in place of `ToolRules().issues`, both at submit and in the verifier.
3. **§3 inputs.**
   - `inputs="module_context"` is accepted for any step with a `_VIEWS` entry.
   - `read_inputs` is required before `submit_review` for every step whose `inputs != "none"`, with or without a source session.
4. **§4 precheck gate.**
   - It runs on the filled payload after `_fill`, before any rules and before the journal.
   - Issues give disposition `refused`: no journal step, no attempt consumed, no head, and the audit and receipt are recorded.
   - The ticket stays open within `MAX_CALLS`.
   - `_verify_submissions` recomputes the gate. A refused record reproduces its exact issues, and a valid or invalid step yields none.
5. **R4-4.** The verifier exception mapping follows the lease text exactly.

## Tests (write them RED first; do not run pytest)
To exercise every seam, use a test-only fake core module that is defined inside the test file and registered by monkeypatching `_CORES`. It is not product code, so it does not count as a stub in `src`. The tests cover:
- Owner-core submit path.
- `STEP_IDS` walk.
- `SCHEMAS` normalisation.
- `RULES` at submit and in the verifier.
- `module_context` read required.
- Precheck refusal that consumes no attempt, followed by a corrected resubmission.
- Verifier recompute of a forged refused record, which must fail.
- R4-4 mapping.

## Rules
- Build first: **run no pytest**. Run `ruff check`, `ruff format --check` and `mypy src` (all exit 0).
- No stub or fake value standing in for real behaviour in `src`, and no catch-all that hides a failure.
- Python owns arithmetic, and Decimal stays exact.
- Run confidence-review on your diff, and rewrite-tournament (no-argument mode) on non-trivial changed functions, before you report.
- Commit on your worktree branch with message `feat(owner): G1-X owner-core protocol (build-only, tests deferred)`.

## Report (write `work/build/g1x/report.md`, return its path)
- Commit SHA and changed files.
- Each protocol item mapped to code line and test name.
- The exact deferred pytest commands (cheap `-k` subset first, then the whole files).
- Confidence-review findings.
- `Not verified:` line.
- `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
