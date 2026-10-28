H1b is done and committed as 0717fad on `claude/h1b`. HEAD was 2aaf207 and equalled `claude/module-dev-status-review-0981b6` before I started. I changed only `src/deploy_workflow/host.py` and `tests/test_host_h1.py`.

**The five rows.** Each has a `_SOURCE_STEPS` entry and an `_OWNER_SCOPES` `_held(...)` entry, in pack order. No lease line disagrees with its module's cases on a source id, so there was nothing to stop and report. I updated the `_SOURCE_STEPS` comment to list the owner-only modules.

| Row | Lease line | Scope | Case check | Test |
|---|---|---|---|---|
| CP-1C `peer_benchmark` | CP1C:31 | identity, financial, peers | step id in the lease; sourced-step citations use only those three ids | `test_cp1c_peer_benchmark_scope` |
| CP-2E `macro_fx` | CP2E:40 | financial | `macro_fx` is in the manifest; every sourced-step citation is `financial` | `test_cp2e_macro_fx_scope` |
| CP-2H `rating_triggers` | CP2H:36 | identity, financial, ratings | `rating_triggers` is in the manifest; the citations use those ids | `test_cp2h_rating_triggers_scope` |
| CP-4C `restructuring_fulcrum` | CP4C:46, :85 | financial, legal-covenants | the manifest says "no identity"; the `identity` citations in the cases are only in refused or upstream CP-0/CP-1 literals | `test_cp4c_restructuring_fulcrum_scope` |
| CP-8 `decision_ledger` | CP8:35 | prior_case, update, market_update | `board_minutes` appears only in a refusal case (r04) and one `identity` quote is in a refusal mutation; both are outside the scope | `test_cp8_decision_ledger_scope` |

The step ids for CP-1C, CP-4C and CP-8 come from their lease code blocks. Their case manifests do not name the step.

Each row test uses the shared helper `_row_session_checks`. It checks that:
- the scope is the leased sources in pack order, with the pack listing them reversed and unleased sources interleaved;
- a held leased source that is not ready answers `unavailable` on `read_pages` and `search_pack`;
- a source outside the scope answers `not_permitted`;
- a leased source the pack does not hold is simply absent from the scope.

I also extended `test_fixed_rows_name_each_leased_step` to cover the new rows.

**Riding Lows**
- **L1:** `test_schema_source_is_chosen_before_the_tail_checks` builds a head with a failing two-tail shape, unregisters the core, and expects `not_permitted` with the memo empty. It kills R4.
- **L2:** I added two forged owner tails to `_forged_owner_tails`: `market-implied-x-submission` (prefix) and `x-market-implied-submission` (suffix). They kill R2 and R3.
- **L3:** `test_cpdr_held_unreadable_source_answers_unavailable`, with a `_source(..., unreadable=True)` helper option, kills R1.
- **Docstring:** the stale `CPDR-OWNER-LEASE.md:31` now reads `:33`.

**Test-first.** The fixed-rows test failed before the host edit. The row tests would have hit `KeyError` on `_OWNER_SCOPES`, but I wrote them in the same edit as that first run, so I only saw the fixed-rows failure directly. L1, L2 and L3 passed on the unmutated code. They were proven by mutants, not by a pre-fix failure.

**Mutants.** I ran them from a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. The runner is `<S>/h1b/mutate_h1b.py`, the output is `<S>/h1b/mutate.out`, and `<S>` is the brief's scratchpad path. Pytest exit 1 means a test failed, so the mutant was killed.
- R1, R2, R3 and R4 all killed (exit 1).
- For each of the five rows, three mutants were killed (exit 1): the `_SOURCE_STEPS` entry removed, the scope mutated (CP-1C drops peers; CP-2E adds identity; CP-2H drops identity; CP-4C adds identity; CP-8 drops market_update), and the scope entry removed.
- My first scope-entry-removal mutants left a syntax error and exited 2, which was not a real kill. I reran them with `<S>/h1b/mutate_removed.py`, and all five were killed with exit 1.

**Gates (all exit 0)**
- pytest on `tests/test_host_h1.py` and `tests/test_owner_g1x.py`: 57 passed.
- `ruff check` on both files.
- `ruff format --check` on both files, after one reformat of the test file.
- `MYPYPATH=src mypy --strict src`: no issues in 114 files.

Not verified: the deferred suites (`test_source_tools`, `test_source_workflow`, `test_owner_workflow`, `test_owner_s1a`, G1 and S1a) were not run. No real owner core exists for the five modules, so no real session ran over the new rows; the tests check the scope functions and `SourceTools` only. The `from_execution` gate with the new `_SOURCE_STEPS` rows was not run end to end. The G1-side `_check_steps` follow-ups from round 10 item 6 are out of scope and not done.

agent=mx-feature fix-rounds=0 gates-first-pass=n
