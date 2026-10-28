# Task H1: host source mapping for owner-only and CP-3 sourced steps (build lane)

**Implementer:** general-purpose, opus. **Reviewer:** mx-adversary, because source capability gating is security-sensitive.

## Base
- Your own worktree, fast-forwarded to the lane tip named in your dispatch. The tip has G1-X merged (29c0819), so `_CORES` exists and is still empty.
- The Stage 1 cores (`owners/cp1d.py`, `cpdr.py`, `cp3d.py`, `cp3.py`) are on the lane. Do not register them in `owner_workflow.py`; that is each module's Stage 2 task.

## Inputs
| File | Why |
|---|---|
| `docs/G1X-OWNER-CORE-PROTOCOL.md` §3, §5 | The fixed host-side scope; H1 must stop `_execution_state` from calling `step_chain` for owner-only modules |
| `work/build/h1/q6-source.md` | LEAD ruling Q6: `_SOURCE_STEPS["CP-3"]`, the generic `*-submission` producer rule (`_submission_producer_inputs`), the memo |
| `docs/CP3-OWNER-LEASE.md` :25, :53-65, :261 | CP-3's prerequisite 2 (full H1) |
| `docs/CP3D-OWNER-LEASE.md` :41-46, :87 | `_SOURCE_STEPS["CP-3D"] = ("market_implied",)`; scope is market and financial only |
| `docs/CPDR-OWNER-LEASE.md` :30-31 (D-A, D-B) | `research` step; scope is the whole ready pack |
| `docs/CP1D-OWNER-LEASE.md` :30, :56, :136 | `earnings_quality` step; scope is identity, financial, bridge (statements_only: identity, financial) |
| `work/build/g1x/review-adversary.md` L3, and probe `p05_open_items.py` part 5 in its scratchpad | The failure H1 closes |
| `src/deploy_workflow/host.py` | The code to change (`_SOURCE_STEPS` :44, the producer rule :491, `_execution_state` :614-650, `from_execution`) |
| `src/deploy_workflow/owner_workflow.py` `_CORES`, `_sequence` | How an owner-only module's steps are known without `step_chain` |

## Files you may write
- `src/deploy_workflow/host.py`
- a new `tests/test_host_h1.py`
- Nothing else. If you must change `owner_workflow.py` or a lease, stop and report the exact lines.

## Behaviour to build
1. **Fixed mapping.** Add rows for CP-3 (`relative_value`), CP-3D (`market_implied`), CP-DR (`research`) and CP-1D (`earnings_quality`). Each row names the step and its readable-source scope as the leases pin it. The mapping is fixed in `host.py`, never caller-supplied, and never in `deploy_vii`.
2. **No `step_chain` for owner-only modules.** `_execution_state` and `from_execution` use the owner core's step order (via G1-X `_sequence`/`_CORES`) and the fixed scope. A live-contract module keeps today's `step_chain` path exactly. A module that is not registered still refuses `not_permitted` before any source capability opens.
3. **The `*-submission` producer rule** (Q6 (b)) as written, plus the memo per (snapshot hash, producer hash). Keep the blocked-producer acceptance, and don't add CP-4's empty-scope refusal (Q6).
4. **No regression.** CP-0, CP-1, CP-1A and CP-4 behave byte for byte as before.

## Tests (write them first; watch each fail for its cause)
- The H1 behaviour is test-only until the cores register. Use a test-only owner core registered in the test (the G1-X fake-core pattern in `tests/test_owner_g1x.py`), and assert each case:
  - a real `SourceSession` opens over the fixed scope;
  - an unread or out-of-scope source refuses;
  - an unregistered module refuses before anything opens;
  - the `*-submission` producer rule accepts a settled CP-1A or CP-2 head and refuses a forged tail.
- Run only `tests/test_host_h1.py` and `tests/test_owner_g1x.py`. List the heavy suites you would run (G1, S1a, any existing host tests) as deferred.
- Gates on the touched files, exit 0: `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict src`.
- G1-X reviewer probe `p05_open_items.py` part 5 should change. Report its exit code and output.

## Rules
- No stub or fake value standing in for real behaviour in `src`; the fake core lives only in the test.
- No catch-all that hides a failure.
- Don't invent policy. Where a lease is silent (for example, the CP-1D statements_only scope switch), fail closed and list it for LEAD.
- Commit message: `feat(h1): host source mapping for owner-only and CP-3 sourced steps`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report (return as text; the controller saves it)
- commit SHA;
- each item → code → test;
- probe exit codes;
- gates;
- deferred commands;
- open points for LEAD;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n|n/a>`.
