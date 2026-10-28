# H1 report (controller-saved from the implementer's hand-back)

## H1 report: host source mapping for owner-only and CP-3 sourced steps

H1 is built and committed. The new H1 tests and the existing G1-X tests both pass, and all three gates exit 0. The heavy suites were not run (listed below).

**Commit:** `2bd61a7` on `worktree-agent-a69f811059171c714`. It fast-forwards from `181e633`. Only two files changed:
- `src/deploy_workflow/host.py` (+188/−18)
- new `tests/test_host_h1.py` (611 lines)

### Each item → code → test

1. **Fixed mapping.**
   - Code: `_SOURCE_STEPS` gains CP-3 `relative_value`, CP-1D `earnings_quality`, CP-3D `market_implied` and CP-DR `research`. The CP-0, CP-1, CP-1A and CP-4 rows are unchanged.
   - Code: a new immutable `_OWNER_SCOPES` (a `MappingProxyType` keyed by (module, step)) holds the leased scopes:
     - CP-3D: `_held("market","financial")`
     - CP-1D: `_held("identity","financial","bridge")`
     - CP-DR: `_ready_pack`
   - CP-3 keeps the registry's scope, which is the CP-0 `third_party` sources (CP-3 lease :65).
   - Tests: `test_fixed_rows_name_each_leased_step` and `test_owner_scopes_are_the_leased_sources_in_pack_order`.
2. **No `step_chain` for owner-only modules.**
   - Code: `_execution_state` picks its path from the `_OWNER_SCOPES` row.
     - With no row, it takes today's `step_chain` path. That code is unchanged; `chain.steps` and `chain.repairable` are only renamed to local variables.
     - With a row, `_owner_sequence` refuses `not_permitted` in three cases: the module has a live step contract, no core is registered in `owner_workflow._CORES`, or `STEP_IDS` is not a nonempty tuple of distinct strings. Otherwise it returns `owner_workflow._sequence(m)`.
   - Owner-only steps have no repairs, and their sources are `scope(pack)`.
   - `owner_workflow` is imported inside the function, because `owner_workflow` imports `host`.
   - Tests (all use a real `SourceSession`; the fake core lives only in the test):
     - `test_cp3d_session_opens_over_market_and_financial`: market and financial reads succeed; identity and `extract_statements` are refused `not_permitted`; `search_pack` surfaces only market and financial; the sealed receipt verifies.
     - `test_unread_cited_page_refuses_and_the_repair_attempt_reopens`: a cited page that was never read gives the exact `Cited page not read through read_pages: market page:2`, and attempt 1 reopens a real session.
     - `test_cpdr_session_reads_the_whole_ready_pack`.
     - `test_unregistered_owner_module_refuses_before_any_capability`: `SourceTools` is patched to fail if it is ever constructed.
     - `test_owner_step_outside_its_row_or_order_refuses`.
     - `test_owner_scope_never_applies_to_a_live_contract_module`.
3. **`*-submission` producer rule plus memo.**
   - Code: `_submission_producer_inputs` follows Q6 (b) as written. It uses `STEPS` from `deploy_vii.live.submission`. The one addition is an `isinstance(submission, Contract)` guard, so mypy can check `content_hash`.
   - Code: `_submission_producer_inputs_memoised` keys on (snapshot hash, producer hash). It keeps only passes, and on a hit it re-reads and hash-checks every blob it touched. The limit is 16, with its own lock.
   - The blocked-producer acceptance is kept. CP-4's empty-scope refusal was not added for other modules.
   - Tests, over real CP-1A heads settled on a CP-0 → CP-1A plan:
     - `test_settled_cp1a_head_is_an_authentic_producer`
     - `test_forged_settled_tail_is_refused`: forged tail digest, tail id, missing tail, two tails, forged prefix, and a forged limitation with the tail intact.
     - `test_blocked_cp1a_head_is_accepted_without_a_tail`
     - `test_memo_skips_the_replay_but_rechecks_every_blob`
     - `test_an_empty_owner_scope_is_not_refused`
4. **No regression.**
   - The CP-0, CP-1, CP-1A and CP-4 sessions bind only CP-0 and CP-1 producers, according to `dependencies()`. Those two producer paths are untouched.
   - Every H1 test drives real CP-0 sessions, and the CP-1A tests drive real CP-1A sessions.
   - `tests/test_owner_g1x.py` passes unchanged.

**Red first:** before the code existed, each test failed for its own cause:
- The CP-0 submit raised `SourceError not_permitted`, which is the L3 failure.
- The new rows and scopes were missing.
- The old rule returned False for the settled CP-1A head.
- The old rule accepted a forged settled head with no tail, and a forged blocked head.

### Probe exit codes
- **`p05_open_items.py`: exit 1.** Part 1 raises `WorkflowError not_permitted` at create. That comes from the G1-X fix round 1 check for `_ENTRY_VALIDATORS`, not from H1.
- **Part 5 output is unchanged:** "CP-0 submit raises SourceError not_permitted … submit_review raises SourceError stale_binding". This is correct under H1. The probe's fake step `g1x_sourced` is not in CP-3D's fixed row (`market_implied`), and a fixed mapping cannot admit a step id that exists only in a test.
- **Variant probe, exit 0:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1/p05h1_part5_mapped.py`. It runs part 5 with the step under its fixed id. Output:
  - CP-0 submit valid
  - session is a `SourceSession` bound to CP-3D `market_implied`
  - market p1 ok, financial p5 ok, identity refused `not_permitted`
  - submit valid; receipt verdict accepted
- Scratch probe `p00_cp1a_cheap.py`: exit 0.

### Gates (exit 0)
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict src`: 111 files, no issues. The test file also passes mypy strict.
- `pytest tests/test_host_h1.py tests/test_owner_g1x.py`: 33 passed in 4.7 s.

### Deferred commands (not run)
- `PYTHONPATH=src ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_source_tools.py tests/test_source_workflow.py` (the existing host tests)
- `… tests/test_owner_workflow.py` (G1)
- `… tests/test_owner_s1a.py` (S1a, heavy)
- Any CP-3, CP-1D or CP-2 producer run, which needs a promoted CP-1.

### Open points for LEAD
1. **Named scopes include held-but-not-ready sources.** CP-3D and CP-1D scopes use the sources "the prepared pack holds", following the `cases/cp1d-owner/manifest.json` wording. A held source that is not ready stays in scope, so its read returns `unavailable` and never its bytes. CP-DR uses ready sources only, as its lease says. Please confirm both.
2. **CP-1D statements_only needs no switch.** Intersecting the fixed set with the pack gives (identity, financial) on the statements_only pack. Please confirm this matches the lease.
3. **Unmapped sourced steps still fail after writes (G1 side).** An owner-only `sources=True` step with no H1 row still fails after G1 has written: `_activate` at `owner_workflow.py:754` opens the session after begin. `_check_steps` (`owner_workflow.py:606-610`, the `served` clause for `chain is None`) could refuse such a step at create, for example with `item.sources == ((module_id, item.step_id) in host._OWNER_SCOPES)`. That edit is outside my files.
4. **Owner-only producers are refused.** A producer whose step is not in `STEPS` (a future consumer of a CP-3D or CP-1D head) is refused `identity_mismatch` through the `KeyError`. The rule would need the core's `SCHEMAS` for that case. No producer in today's rows hits it.
5. **`STEP_IDS` must be a tuple in the host.** `_check_steps` accepts any iterable, but the host now requires a tuple. That matches the protocol's `tuple[str, ...]`, and all Stage 1 cores already use tuples.
6. **Other leases name H1 rows that are not built.** CP-1C, CP-2E, CP-2H, CP-8 and CP-4C leases name H1 rows that this brief did not include.

**Confidence review:** done. No defect was confirmed. These were checked and hold:
- the memo is safe across copied stores (all data is content-addressed);
- `_FrozenExecution` exposes `directory`;
- `SourceError` is a `ValueError`, so the verifier maps it to `identity_mismatch`;
- the replay holds at later snapshots, because bound heads are re-checked through `expected`.

rewrite-tournament was not run; it is left to the whole-branch review, per the global routing.

**Not verified:**
- No CP-3 session, so CP-3's live scope via `readable_sources` and the CP-2 or CP-4 producers under the new rule were not run (they need a promoted CP-1).
- No CP-1D session (needs CP-1).
- The memo was not exercised through a consumer session or the verifier; it was tested at function level only.
- CP-3D and CP-DR were exercised only with a test-only core, not the real Stage 1 cores (not registered).
- The heavy G1, S1a and host suites were not run.
- No mutation testing.

**Ledger:** `2026-10-28T13:59:40Z h1-affected pytest tests/test_host_h1.py tests/test_owner_g1x.py exit=0 33 passed 0 failed agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
