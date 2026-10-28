# G1-X fix round 1: brief

Implementer: the G1-X implementer, resumed (opus). Re-review: scoped mx-adversary on M1 and the Part A items (Medium).

## Step 0
From your worktree root (`worktree-agent-a3179638c813adbe7`, d36b5ab), run `git merge 4b46e19` (the lane tip; merge-tree shows it is clean). It brings in the round-4 amended `docs/G1X-OWNER-CORE-PROTOCOL.md` and the methodology change. The lane didn't touch `owner_workflow.py` or the owner tests after 67d032c.

## Inputs
| File | Why |
|---|---|
| `work/build/g1x/review-adversary.md` | Findings and probe paths |
| `docs/G1X-OWNER-CORE-PROTOCOL.md` §2 and §3 (amended) | Rulings round 4 Part A |
| `docs/rulings/2026-10-28-stage1.md` Round 4 Part A | The same, as LEAD's ruling |
| `docs/S1A-OWNER-RUN-LEASE.md` R4-4 | "tamper causes map to `identity_mismatch`, programming errors propagate" |

## Controller ruling on M1 (under R4-4)
A stored payload is tamperable data, so a `TypeError` while the verifier fills it (`_fill` at :1625) is a tamper cause.
- Map that `TypeError` to `identity_mismatch` at that call site only, and only for the recorded payload. Don't widen the `verify_owner_run_receipt` catch.
- Correct the docstring at :1968-1972 so it names this one mapped call.
- The root fix is a tag-type guard in `deploy_vii/live/schema.py` `_Walker.branch`. That file is read-only here and goes to LEAD; once it lands, this mapping can come out.
- The runtime escape is pre-existing and goes to the owner: `normalise` raising after the binding write. Leave it.

## Fixes (test-first; watch each new test fail for the reported cause)
1. **M1:** as ruled above.
2. **Part A1:** `_check_specs` refuses `not_permitted` at create a spec whose module needs a validator and has no `_ENTRY_VALIDATORS` row. Which modules need one: §2, "every analytical module except CP-0 and CP-1". Check that the G1 and S1a plans still create.
3. **Part A2:** `_PRECHECKS[m]` is registered for live-contract and owner-only modules alike. Confirm that it already holds and pin it with a test if none does.
4. **L1:** `_check_steps` ties `entry` to the module, so it can't drift from the verifier's `_entry_outcome` dispatch.
5. **L2:** at create, the registered core must be complete: `SCHEMAS` covers every `STEP_IDS` step, `submit` and `RULES` exist, and `SCHEMAS[step]` matches `StepSpec.schema`. Otherwise it is refused before anything is written.
6. **L4:** the verifier runs the read check before `_fill` and `_gate`, as runtime does. Make the comment true.
- L3 is not in this round; it goes to H1.

## Rules
- No stub or fake value standing in for real behaviour.
- No catch-all that hides a failure unless the fail-open is documented and logged. The M1 mapping fails closed.
- Don't edit `src/deploy_vii`, the owner cores or the cases.
- Files you may write: `src/deploy_workflow/owner_workflow.py`, `tests/test_owner_g1x.py` and `tests/test_owner_workflow.py`.
- Tests: run only `tests/test_owner_g1x.py` (fast). The G1 and S1a suites stay deferred; list them.
- Gates on the touched files: ruff check, ruff format --check, `MYPYPATH=src mypy --strict src`.
- Run the reviewer's probes p03, p04, p05, p10 and p11 and report each exit code. Say which exits are expected to change.

## Output
Return your report as text. It contains:
- the commit SHA;
- each fix with its test name;
- the probe exit codes;
- the gates;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
