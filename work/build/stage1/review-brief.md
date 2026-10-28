# Stage 1 layer review (mx-architect): brief

The layer is the Stage 1 module calculations. Each module was built by an Opus implementer, reviewed per module by mx-adversary or mx-precise (verdict APPROVE), and merged into the lane `claude/module-dev-status-review-0981b6`. This review runs once per layer. You apply and commit your own fixes, test-first (user routing, 2026-10-28).

## Inputs
| File | Why |
|---|---|
| `docs/superpowers/plans/2026-10-28-verified-module-builds.md` §Stage 1, §Rulings rounds | Scope and the four-stage goal |
| `work/build/stage1/brief.md` | The Stage 1 contract every module was built to |
| `docs/rulings/2026-10-28-stage1.md` (rounds 1–4) | LEAD rulings; a ruling beats the lease |
| `docs/<CP>-OWNER-LEASE.md`, `cases/<cp>-owner/` | Each module's lease and frozen oracle |
| `work/build/stage1/<cp>/report.md` (and `cp2a/rulings-report.md`) | Implementer reports: input-field tables, LEAD lists, `Not verified` |
| `work/build/ledger.md` | Per-module history, review verdicts and Lows that ride with the next fix |

## Process
Work in your own worktree, cut from the lane tip named in your dispatch. Review only your module group.
1. Calculation against the lease and rulings, from the Method text, not the implementation. Rounding and quantisation must match the lease exactly, and missing must never become 0.
2. Each module's input-field table against `manifest.fact_bindings` (or the lease's Public API where the manifest has none). Flag any field Stage 2 can't bind.
3. Boundaries:
   - Nothing in `src/deploy_workflow/owners/<cp>.py` does I/O or reaches into a store, the host, a session or a renderer.
   - No `src/deploy_vii` edit.
   - No name clashes with the G1-X seams (`docs/G1X-OWNER-CORE-PROTOCOL.md` §2).
4. Cross-module consistency inside your group: shared conventions (Decimal contexts, `Number` bounds, `fact_spelling`, missing and not_applicable reasons, prohibited-phrase guards). Report inconsistencies across groups as findings; don't fix them.
5. The Lows the ledger says "ride with the next fix" for your modules, and the CP-4 casefold test (lease says "case-folded"; `lower_not_casefold` mutant survives).
6. Run `confidence-review` on your group's module diff against bb8ccef. Run `rewrite-tournament` (no-argument mode) on each module's most complex function.

## Rules
- Fix test-first: write the test, watch it fail for the reported cause, then fix. Commit on your worktree branch.
- No stub or fake value standing in for real behaviour, and no catch-all that hides a failure.
- Never rewrite oracle payloads. A frozen-oracle defect is a strict xfail plus a live test of the ruled behaviour.
- Don't invent wording or policy. Where a lease or ruling pins none, the code fails closed or composes as it does now; list the case for LEAD.
- Tests: each module's Stage 1 test file runs in under 60 s: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py`. Don't run the heavy suites.
- Gates on every file you touch, exit 0: `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict`.
- Save each probe as a script under the scratchpad folder named in your dispatch, and name it in its finding.
- Files you may write: `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py` for your group's modules. Nothing else.

## Outputs
Return the report as text, and the controller saves it as `work/build/stage1/review-<group>.md`. It contains:
- Your branch and commit SHAs.
- Findings ranked High, Medium or Low, each with file:line, a failure scenario, the probe, and whether you fixed it (with the test name) or left it for LEAD or the owner.
- Cross-group inconsistencies.
- Test counts and gate exit codes per module.
- A `Not verified:` line.
- The ledger line `agent=mx-architect fix-rounds=0 gates-first-pass=<y|n>`.
