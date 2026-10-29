## H1b adversary review (target 0717fad on `claude/h1b`, diff 2aaf207..0717fad)

**Verdict: APPROVE.** I found nothing High or Medium. Each of the five rows equals what its lease pins, in pack order, and none of them widens a session's readable set. Two Low test gaps and two Info items can ride with the next fix.

### The five checks
1. **Scope per row: confirmed.**
   - Step ids match the leases: CP1C :52 `peer_benchmark`, CP2E :40 `macro_fx`, CP2H :42 `rating_triggers`, CP4C :46/:49 `restructuring_fulcrum`, CP8 :33/:35 `decision_ledger`.
   - Scopes match the leases (:31, :40, :36, :46/:85, :35), and the owner cores agree (`cp8.SCOPE`, `cp2e.SOURCE_ID`, `cp1c.PEERS_SOURCE_ID`).
   - Case cross-check (p02): no source id outside a lease appears in any module's own-step material.
   - CP-4C: `identity` appears only in CP-0 literals (readiness review, the `refused.cp0_consumer_rows`), in upstream CP-4 `cp1_source_context`, and in refusal v08 ("support from outside the step's scope").
   - CP-8: `board_minutes` appears only in refusal r04. `identity` appears only in r30 and in the CP-0 or pack listings. Both report claims hold.
   - None of the five step ids is in live `STEPS`, and no step id repeats across modules.
2. **Widening: none found.** In a real `SourceSession` for CP-2E and CP-8, each driven through `OwnerWorkflow` with a fake core (p03, 70 checks):
   - the scope is the held leased ids in pack order;
   - CP-8's held `missing` prior_case answers `unavailable` with a null body;
   - every out-of-scope id (identity, financial, business, board_minutes) answers `not_permitted`;
   - an unscoped `search_pack` surfaces only in-scope ids and no out-of-scope bytes;
   - `extract_statements` answers `not_permitted`;
   - `from_execution` with any other module's step answers `not_permitted`, and so does a core that claims another module's step;
   - both runs seal `accepted`.

   No core is registered in product code (`_CORES` is empty), so the new rows cannot be reached until Stage 2 registers one.
3. **Existing rows: unchanged** (p04, 669,274 generated packs, each source ready, missing or unreadable).
   - The base `_SOURCE_STEPS` entries and the CP-1D, CP-3D and CP-DR scopes are identical at base and target.
   - Exactly the five keys were added.
   - Each new row equals an oracle written from its lease.
4. **Riding tests: confirmed.** With the fix2 reviewer's `mutate_review.py` on a fresh full copy, R1–R4 are all killed (exit 1). The p05 targeted runs show each is killed by its intended test: L3 kills R1, the prefix and suffix tails kill R2 and R3, and L1 kills R4.
5. **Mutants: reproduced.**
   - `mutate_h1b.py`: R1–R4 exit 1. Of the 15 row mutants, 10 exit 1. The 5 scope-entry removals exit 2, which is a syntax error and not a kill.
   - `mutate_removed.py`: those 5 removals exit 1, so they are real kills.
   - `<S>/h1b/mutate.out` holds only the first run; the removal run is reported only in the report's text, so I re-ran both.

### Findings
- **Low A, tests/test_host_h1.py:446-480 (row tests) and :407-443 (helper).** Each row test names only two ids as outside its scope, so widening a row to any other id passes the whole gate.
  - p06 finds 38 single-id widenings that survive. Examples: CP-2E plus `market`, CP-8 plus `financial`, CP-4C plus `peers`.
  - p08 runs three of them as file mutants against both gate files; all pass (gate exit 0).
  - Fix: pass one shared `outside` universe to every row test: every id any row or case names, plus `business`, `board_minutes`, `market` and `bridge`, minus the row's leased ids. p07 shows the committed helper then kills all 38 and still passes when unmutated.
- **Low B, tests/test_host_h1.py:1065-1081 (L3) and :360-363 (`_source(unreadable=True)`).** The L3 test's unreadable source has no sha256 and no spans, so its "never its bytes" claim is never exercised.
  - A mutant that lets `PackTools.ready` admit `unreadable` sources with a sha256 (src/deploy_vii/live/tools.py:308-312, which predates this diff) passes the gate. Only the reviewer probe p11 catches it (p09).
  - Fix: give `late` a sha256 and a page span. p10 shows that variant passes unmutated and fails under the mutant.
- **Info 1, src/deploy_workflow/host.py:48-49.** The comment still begins "CP-1D, CP-3D and CP-DR are owner-only (G1-X §1):" and then lists eight modules.
- **Info 2, tests/test_host_h1.py:340-341.** "the three others are owner-only" should now say eight.
- **Info 3, for the owner (predates the diff).** The existing CP-3D row test has the same weakness as Low A. CP-3D widened with `legal-covenants` passes the gate (p11 exit 1).

The diff adds no stub, fake value, catch-all or suppression. The only fake core is the existing test-only `_fake_core`.

### Probe exit codes (all in /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1b-review/, each with a matching `.out`)
| Probe | Exit | Meaning |
|---|---|---|
| p01_case_source_ids.py | 0 | inventory |
| p02_own_step_ids.py | 0 | |
| p03_real_sessions.py | 0 | |
| p04_rows_base_vs_target.py | 0 | |
| p05_kill_map.py | 0 | O4 survives (Low A); O10 predates and the suite kills it |
| p06_widening_survivors.py | 1 | Low A |
| p07_shared_universe_fix.py | 0 | fix for Low A works |
| p08_widening_gate.py | 1 | Low A |
| p09_unreadable_bytes_mutant.py | 1 | Low B; p11 kills the mutant |
| p10_l3_with_bytes.py | 0 | fix for Low B works |
| p11_cp3d_widening_predates.py | 1 | Info 3 |

The three mutant re-runs (rerun_mutate_h1b.out, rerun_mutate_removed.out, rerun_mutate_review.out) each exited 0 as runners. Every mutant ran from the full copy `.../h1b-review/copy` with PYTHONDONTWRITEBYTECODE=1, and every file was restored (diff exit 0).

### Gates (from the target root, all exit 0)
- pytest on `tests/test_host_h1.py` and `tests/test_owner_g1x.py`: 57 passed.
- `ruff check` on both files.
- `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict src`, with the cache in scratch: no issues in 114 files.

Both worktrees are unchanged (git status clean). The git-ignored `.mypy_cache` in the target dates from 15:26, before my gate runs.

Not verified: CP-1C, CP-2H and CP-4C were not run through a real session, because their plans need CP-1, CP-2A, CP-2G and CP-4 heads; only their scope functions and `SourceTools` were exercised. A not-ready financial source for CP-2E was not run in a real session, because the S1 CP-0 literal cites financial; only the unit test covers it. No real owner core exists for the five modules. The deferred suites were not run: test_source_tools, test_source_workflow, test_owner_workflow, test_owner_s1a, G1 and S1a. The implementer's test-first claim can't be reproduced after the fact. The G1-side `_check_steps` follow-ups are out of scope.
