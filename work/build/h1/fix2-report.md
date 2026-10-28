## H1 fix round 2 report (round 2 of 2)

Round 10 items 2–5 are done: F1, I1, I2 and the CP-DR scope. The one test file passes, every new guard's mutant is killed, and all gates exit 0. No change to `owner_workflow.py` or any lease was needed.

**Commit:** `38f0f46` in `worktree-agent-a69f811059171c714`.
- Before editing, I ff-merged `claude/module-dev-status-review-0981b6`. HEAD then equalled the lane tip, `1371d49`, which contains 4fd8c24 (round 10) and my fix-1 commit 278f0aa.
- Files changed: `src/deploy_workflow/host.py`, `tests/test_host_h1.py`, `work/build/h1/q6-source.md`.

### Each finding and the test that covers it
I wrote the tests first. Before the fix they failed for the reported causes: `KeyError 'market_implied'` on owner heads, `_submission_schema` missing, and CP-DR leaving out the held `late` source.

- **F1 (item 2): new `host._submission_schema(module_id, step_id) -> type[Contract]`.** It is called in the settled branch right after `step = attempt.steps[0]`, before the tail checks, and replaces `STEPS[step.step_id]`.
  - **Live module:** uses `STEPS[step_id].schema`, only when the step is in `STEPS` and belongs to that module. The tail keeps `endswith("-submission")`.
  - **Owner-only module:** uses `owner_workflow._CORES[m].SCHEMAS[step_id]`, imported inside the function. It requires `STEP_IDS == (step_id,)`, the step not in `STEPS`, `SCHEMAS` a mapping and the schema a `Contract` subclass. The tail id must equal `<step_id with hyphens>-submission`.
  - **Anything else** raises `SourceError("not_permitted")` before any payload is read.
  - Tests:
    - `test_settled_owner_only_head_is_an_authentic_producer`: a fake-core CP-3D head settled through the real workflow and session with the `market-implied-submission` tail passes.
    - `test_forged_owner_only_tail_is_refused`, parametrised over a forged digest, a wrong id, `research-submission`, two tails and no tail; each is refused.
    - `test_schema_source_follows_the_producer_module` refuses:
      - CP-1B `earnings_delta` (`not_permitted`, not `KeyError`);
      - CP-1A claiming `credit_synthesis`;
      - CP-3D with no core;
      - an owner module claiming a step outside its single `STEP_IDS`, or with multiple `STEP_IDS`;
      - a schema that is not a `Contract`;
      - `SCHEMAS` that is `None` or `{}`;
      - an owner core claiming `relative_value` (a `STEPS` step).
    - `test_unsourced_settled_producer_refuses_before_any_payload_read`: raises `not_permitted`, records zero payload reads, and leaves the memo empty.
    - `test_live_cp1a_head_still_passes_under_the_schema_source`.
- **Item 5 (CP-DR scope):** `_ready_pack` is removed and replaced by `_every_held`, which is every source the pack holds. A new comment records CP-3's registry scope as the one exception.
  - Tests: `test_cpdr_held_missing_source_answers_unavailable` (the scope includes the held `missing` source; `read_pages` and `search_pack` on it answer `unavailable`; a source outside the scope answers `not_permitted`), plus the updated `test_owner_scopes_are_the_leased_sources_in_pack_order`.
  - `test_cpdr_session_reads_the_whole_ready_pack` is renamed `test_cpdr_session_reads_every_held_source`.
- **I1 (item 3):** the `_submission_producer_inputs` docstring now records the boundary. The host checks provenance only; composition is authenticated at the receipt verifier (`_verify_settlements` runs `_PROBES[m]`). No test applies; it is a docstring.
- **I2 (item 4):** the round-10 prose replaces the old failed-head sentence in `work/build/h1/q6-source.md`, word for word. No code change, and no test applies.

**Test-side change:** the fake core now takes an optional `tail`, so owner heads can carry a submission tail. The existing call sites, and the reviewer's and LEAD's probes that use it, still work.

### Mutants and probes
- **Fix-2 guard mutants: exit 0, all 11 killed, no survivors.** Runner: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-fix2/mutate_fix2.py`. It ran on a full temporary copy at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-fix2/copy` with `PYTHONDONTWRITEBYTECODE=1`. Each mutant reverts one guard:
  - F01: the single-step check
  - F02: the not-in-`STEPS` check
  - F03: the mapping check
  - F04: the live in-`STEPS` check
  - F05: the own-module check
  - F06: the `Contract` subclass check
  - F07: the exact owner tail id
  - F08: going back to `STEPS[step_id]`
  - F09: a payload read before the schema call
  - F10: CP-DR ready-only
  - F11: the owner branch never taken
- **Probes:**

  | Probe | Exit |
  |---|---|
  | Reviewer `p02_producer_forgery.py` | 0 |
  | LEAD `p_f1_schema_source.py` | 0 (no failures) |
  | Reviewer `p01_scope.py` (regression) | 0 |
  | Reviewer `p03_memo.py` (regression) | 0 |

### Gates (all exit 0)
- `pytest tests/test_host_h1.py`: 28 passed in 5.1 s.
- `ruff check` and `ruff format --check` on `host.py` and the test file.
- `MYPYPATH=src mypy --strict src`: 111 files, no issues. The test file also passes mypy strict.

**Not verified:**
- Deferred suites, not run: `tests/test_owner_g1x.py` (the brief limited this round to `tests/test_host_h1.py`), `tests/test_source_tools.py`, `tests/test_source_workflow.py`, `tests/test_owner_workflow.py` (G1) and `tests/test_owner_s1a.py` (S1a).
- No real Stage 1 owner core was used; owner-only producers were tested with the test-only fake core.
- No CP-1B head went through the host; that rule was checked only as a unit.
- No CP-3, CP-4 or CP-1D session, and no co-planned run with an owner-only producer.
- No CP-DR session over a pack holding a missing source; that was checked at the scope and `SourceTools` level.
- The receipt verifier was not run on a head with forged content.
- The reviewer's 40-mutant `mutate_h1.py` was not rerun (some of its patterns no longer exist).
- H1b (the five leased rows) and the G1-side guards are out of scope.

**Ledger:** `2026-10-28T15:07:21Z h1-fix2 pytest tests/test_host_h1.py exit=0 28 passed 0 failed; mutate_fix2.py exit=0 (11/11 killed) agent=general-purpose(opus) fix-rounds=2 gates-first-pass=y`
