# H1 fix round 2: round 10 items 2-5 (F1 schema source, I1, I2, CP-DR scope)

**Round budget.** This is round 2 of 2 under the shared budget. Re-review: mx-adversary, by finding id only. If anything High or Medium remains after it, it goes to the owner.

## Step 0
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a69f811059171c714")`.
2. `git merge --ff-only claude/module-dev-status-review-0981b6`. The lane carries round 10 (4fd8c24) and G1-X fix 2 with LEAD 0d.
3. Before you edit, confirm HEAD equals the lane tip named in your dispatch.

## Inputs
| File | Section |
|---|---|
| `docs/rulings/2026-10-28-stage1.md` | `# Round 10`, sections 2, 3, 4 and 5, and the H1 line under "LEAD rulings on the For LEAD items" |
| `docs/G1X-OWNER-CORE-PROTOCOL.md` | §2 SCHEMAS row and §5 (amended by LEAD in round 10) |
| `docs/CPDR-OWNER-LEASE.md` | D-B (amended) |
| `work/build/h1/review-adversary.md`, `fix1-report.md`, `fix1-review.md` | Prior rounds; the reviewer's probes are in `<S>/h1-review/` |
| LEAD probe `p_f1_schema_source.py` | `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/round10/` |

## Fix (test-first; watch each test fail for the reported cause)
1. **F1 (item 2).** Add `_submission_schema(module_id, step_id) -> type[Contract]` to `host.py`, exactly as ruled:
   - **Where it is called:** in the settled branch of `_submission_producer_inputs`, right after `step = attempt.steps[0]` and before the tail checks. It replaces `STEPS[step.step_id]`.
   - **Live-contract module:** `STEPS[step_id].schema`, used only when `step_id in STEPS` and `STEPS[step_id].module_id == module_id`. The tail keeps `endswith("-submission")`.
   - **Owner-only module:** `owner_workflow._CORES[module_id].SCHEMAS[step_id]`, used only when the core is registered, `STEP_IDS == (step_id,)`, `step_id not in STEPS`, and the schema is a `Contract` subclass. Import `owner_workflow` inside the function. The tail id must equal `<step_id with "_" as "-">-submission`.
   - **Anything else** raises `SourceError("not_permitted")` before any payload read. That includes CP-1B `earnings_delta`.
   - **Tests:**
     - a settled fake-core owner head passes;
     - each of these is refused: a forged digest, a wrong id, another `*-submission` id, two tails, no tail;
     - `_submission_schema("CP-1B", "earnings_delta")` raises `SourceError` `not_permitted`, not `KeyError`;
     - an owner module claiming a `STEPS` step is refused;
     - a live module claiming another module's step is refused;
     - the CP-1A live head still passes.
2. **Open point 1 (item 5).** CP-DR's scope moves from `_ready_pack` to every source the pack holds. A held source that is not ready answers `unavailable`, never its bytes. CP-3 keeps its registry scope; that is the one recorded exception, so say so in a comment.
   - Test: a CP-DR pack with a held `missing` source answers `unavailable`.
   - Remove `_ready_pack` if nothing else uses it.
3. **I1 (item 3).** Record the boundary in the `_submission_producer_inputs` docstring. Composition is authenticated at the receipt verifier (`_verify_settlements` / `_PROBES`); the host checks provenance only.
4. **I2 (item 4).** Replace the Q6 prose in `work/build/h1/q6-source.md` with the round's text, word for word. No code change.

Not in this round:
- H1b (the five leased rows, item 6). It is a separate task that runs after this one.
- The G1-side guards. They ride with the next G1-X change.

## Rules
- **Files:** `src/deploy_workflow/host.py`, `tests/test_host_h1.py`, `work/build/h1/q6-source.md`. If `owner_workflow.py` or a lease must change, stop and report the exact lines.
- No stub, fake value or catch-all. The fake core lives only in the test.
- **Tests:** `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_host_h1.py` only. The heavy host, G1 and S1a suites stay deferred; list them.
- **Gates (exit 0):** `ruff check` and `ruff format --check` on the touched files, and `MYPYPATH=src mypy --strict src`.
- **Mutants:** only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Each new guard's revert must be killed. Rerun the reviewer's `<S>/h1-review/p02_producer_forgery.py` and LEAD's `p_f1_schema_source.py` and report their exit codes.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Put probes under `<S>/h1-fix2/`.

## Report (as text)
- commit;
- each finding and the test that covers it;
- mutant and probe exit codes;
- gates;
- a `Not verified:` line that lists the deferred suites;
- the ledger line `agent=general-purpose(opus) fix-rounds=2 gates-first-pass=<y|n>`.
