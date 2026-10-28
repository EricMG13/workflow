# H1 fix round 1 report (controller-saved from the implementer's hand-back)

## H1 fix round 1 report

All five missing tests are added and kill their target mutants. The only mutants left alive are the ones the review already called equivalent. No `src` change was needed, and F1, I1, I2 and open points 1–6 are untouched.

**Commit:** `278f0aa`, on top of `2bd61a7` in `worktree-agent-a69f811059171c714`. It changes only `tests/test_host_h1.py`.

### Each finding and its test
- **F2 (Medium): `test_self_consistent_forgeries_reach_each_q6_check`.**
  - A new helper, `_cp1a_journal`, builds a CP-1A head through the public `Execution` API. It journals the genuine business_context payload with a bypass validator, then finishes with the genuine candidate, whose inputs each variant rewrites.
  - The multi-step variant uses a two-step sequence and journals a second step.
  - A control journal with the inputs unchanged passes (True). So each refusal comes from its own Q6 (b) check, not from the settle replay.
  - Each of these is refused (False): wrong tail digest, tail id not `-submission`, two tails, reordered prefix, two-step attempt.
  - Kills M24, M25, M26, M20 and M22.
- **L1: `test_owner_scope_never_applies_to_a_live_contract_module`.** It now registers a fake core for CP-1A (`_CORES`), so only the live-contract guard can refuse. With the core but no owner row, the session still opens. Kills M07.
- **L2: `test_owner_step_outside_its_row_or_order_refuses`.** Adds `STEP_IDS` set to `("market_implied", "market_implied")` and to `("market_implied", 7)`. Kills M10 and M11.
- **L3: `test_producer_without_a_producing_attempt_refuses`.** On a snapshot that lacks the producing attempt, the rule returns False instead of raising `IndexError`. Kills M15.
- **L4:**
  - `test_memo_keeps_passes_only`: a self-consistent forgery with a wrong digest, asked twice, is refused both times and the memo stays empty.
  - `test_memo_key_is_the_snapshot_and_the_producer`: after a pass is cached, these are both refused: another producer under the cached snapshot, and the cached producer under a snapshot without its attempt. The memo still holds only the one (snapshot hash, producer hash) key.
  - `test_memo_evicts_the_oldest_pass_beyond_its_limit`: the limit is 16. After 20 passing snapshots (differing only in `parent`), the memo holds exactly the last 16, so the oldest go first.
  - Kills M33, M35, M36 and M37.

### Mutants
I ran `mutate_h1.py` over all 40 mutants, on a full rsync copy of the worktree at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1/fix1-mut`. The runner exited 0. Output is in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1/fix1-mutants.out`.
- **The suite now kills 28:** M01–M08, M10, M11, M13–M15, M20, M22, M24–M26, M29, M32–M40.
- **12 survive:** M09, M12, M16, M17, M18, M19, M21, M23, M27, M28, M30, M31. This is exactly the review's equivalent list:
  - M09: the length check refuses an empty sequence anyway.
  - M12: owner modules have no within-attempt repair.
  - M16: a pending attempt is never selected.
  - M17: the replay refuses an interruption anyway.
  - The rest are implied by the replay or by `finished == attempt`.
- No target mutant survives.

The reviewer's probes against the worktree all exit 0: `p01_scope`, `p02_producer_forgery` and `p03_memo`.

### Gates (all exit 0)
- `pytest tests/test_host_h1.py tests/test_owner_g1x.py`: 38 passed in 6.8 s.
- `ruff check` and `ruff format --check` on the test file.
- `MYPYPATH=src mypy --strict tests/test_host_h1.py`.

**Not verified:**
- The heavy suites were not run: `test_source_tools.py`, `test_source_workflow.py`, `test_owner_workflow.py` and `test_owner_s1a.py`.
- There was no CP-3 or CP-1D session, and no CP-2 or CP-4 producer under the rule (each needs a promoted CP-1).
- The memo was not exercised through the receipt verifier.
- The mutants cover `host.py` only, not the test file.
- The forgeries use CP-1A only.

**Ledger:** `2026-10-28 h1-fix1 pytest tests/test_host_h1.py tests/test_owner_g1x.py exit=0 38 passed 0 failed; mutate_h1.py 1-40 exit=0 (12 equivalent survivors) agent=general-purpose(opus) fix-rounds=1 gates-first-pass=y`
