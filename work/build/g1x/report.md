# G1-X owner-core protocol: build report (build-only, tests deferred)

The implementer returned this as text and the controller saved it here.

## Commit
- Branch `worktree-agent-a3179638c813adbe7`, commit **d36b5ab**, fast-forwarded from 67d032c.
- `src/deploy_workflow/owner_workflow.py` (+245/−84) and a new `tests/test_owner_g1x.py` (821 lines). `tests/test_owner_workflow.py` is unchanged.

## Protocol item → code (owner_workflow.py at d36b5ab) → tests (tests/test_owner_g1x.py)
1. **§1/§2 entry and registration.**
   - `OwnerSpec.entry` gains `"owner_core"` (:162), and `_CORES: dict[str, ModuleType] = {}` is added (:107).
   - `_check_steps` (:555), called from `_check_specs`:
     - an owner-only module needs `entry == "owner_core"` and a registered core;
     - a live-contract module needs an entry in `ENTRIES` and no core;
     - step ids must equal `_sequence`.
   - `_sequence` (:403) returns `step_chain(m).steps`, falling back to `_CORES[m].STEP_IDS`. `_owner_historical` (:414) and the advance in `submit_review` (:964) use it.
   - `submit_review` dispatches `owner_core` to `_CORES[m].submit(store, ticket, step, payload, rules)` (:906).
   - `_fill` (:445) normalises through `core.SCHEMAS[step]` when the step is outside `STEPS`.
   - Tests:
     - `test_owner_only_spec_must_be_served_by_its_core`
     - `test_owner_core_submit_walks_step_ids_and_seals`
     - `test_owner_core_result_must_match_what_g1_retains`
     - `test_owner_historical_follows_core_step_ids`
     - `test_fill_normalises_through_core_schemas`
     - `test_fake_module_is_owner_only_and_plans_after_cp0`
2. **§2 RULES routing.**
   - `_journaled_issues` (:462) calls `core.RULES(text, seen)` for owner-only modules and `ToolRules` otherwise. Submit and `_verify_submissions` (:1675) both use it.
   - A journaled owner-only step with no sources is refused.
   - Tests:
     - `test_rules_route_to_the_core`
     - `test_rules_at_submit_journal_an_invalid_step_and_the_verifier_replays_it`
     - `test_verifier_recomputes_rules_for_a_valid_step`
3. **§3 inputs.**
   - `module_context` is accepted for any step with a `_VIEWS` entry (:602).
   - A read is required for every step whose `inputs != "none"`, at runtime (:861) and in the verifier (:1652). The verifier checks this before the refused branch.
   - Tests:
     - `test_module_context_read_required_with_and_without_a_session`
     - `test_verifier_requires_the_read_of_a_sourced_view_step`
4. **§4 precheck gate.**
   - `_PRECHECKS` is a module-keyed registry (:274).
   - `_gate` (:475) runs the precheck on the filled payload against the same read-only binding-snapshot view at submit and in replay. The precheck-mode evidence rules run next, then the journaled rules.
   - A refused submission gets no journal step, no attempt and no head. The audit and receipt are recorded, and the ticket stays open.
   - `_verify_submissions` (:1646) recomputes the gate:
     - a refused record must reproduce its exact issues;
     - a journaled step must recompute none.
   - Tests:
     - `test_precheck_refusal_consumes_no_attempt_then_corrected_resubmission`
     - `test_verifier_recomputes_the_gate`
5. **R4-4.**
   - `verify_owner_run_receipt` (:1959) maps only `(ValueError, OSError)` to `identity_mismatch` (:1978).
   - Lookups that a forged record can reach are now explicit checks: `_attempt_of` :386, `_result_attempt` :395, `_settled`, `_step` :546, `_hist`, `_verify` :1804, and the head check :1935.
   - Tests:
     - `test_verifier_programming_errors_propagate`
     - `test_verifier_tamper_causes_map_to_identity_mismatch`

The fake core is defined only in the test file and stands in for CP-3D, whose plan is CP-0 → CP-3D. It has steps `g1x_sourced` and `g1x_viewed` and reads through a test-only `_FakeSession`, because owner-only host scope belongs to H1.

## Deferred pytest commands (build-first; none run)
1. `uv run pytest -q tests/test_owner_g1x.py`
2. `uv run pytest -q tests/test_owner_s1a.py -k "oracle_pins or figure_predicate or unreplaced_figure or cp5_selection or genuine_blocked or forgery_a_blocked or forgery_b or genuine_valid or valid_cp1a_turned or appended_snapshot or invalid_step_output or invalid_step_inputs or conditional_cp0 or transient_cp0 or extra_cp0 or unplanned_module"`
3. `uv run pytest -q tests/test_owner_workflow.py -k "not equivalence_positive and not tamper_and_foreign and not verifier_is_read_only and not publish_failure"`
4. `uv run pytest -q tests/test_owner_g1x.py tests/test_owner_workflow.py tests/test_owner_s1a.py`. Heavy: G1 takes about 13 min, and S1a 11–26 min per CP-1 promotion.

RED: on 67d032c the new tests error at the `g1x` fixture, because the registries are absent. That is a fixture failure, not a behavioural RED.

## Gates
- `ruff check` and `ruff format --check` on the two changed files: exit 0.
- `MYPYPATH=src mypy src` (strict): exit 0, 101 files.
- `ruff check src` as a whole exits 1, with 92 findings in untouched files; the base has the same.
- Light probes in the scratchpad: `probe_g1x.py` (fake-core happy, precheck-refused and RULES-invalid runs seal and verify, 0.3 s) and `probe_s1a_cheap.py` (genuine S1a valid and blocked runs still seal and verify, 1.3 s).

## Confidence review
- **Fixed:**
  - The precheck now sees the same view at submit and in replay.
  - `_sequence` follows "where `step_chain` has none" literally.
  - Explicit checks replace the lookups that the narrowed R4-4 catch would have let escape.
- **Verified:**
  - The new read rule is equivalent for every existing spec.
  - The verifier reorder still gives `identity_mismatch` for the S1a callers.
  - `_ENTRY_VALIDATORS` captures validators at import safely.
- **Rewrite tournament:** `_check_steps` holds; `_verify_submissions` computes `journaled` after the refused branch.

## Open for LEAD
1. **Validator seam.** §2 has none for R4-2's invalid-step replay. G1-X adds a module-keyed `_ENTRY_VALIDATORS`, seeded with CP-1A and CP-2. Until a module adds its row, an invalid step of that module is refused `not_permitted` at the verifier. §2 needs an amendment.
2. **Precheck registration.** Module-keyed `_PRECHECKS` was chosen, so live-contract cores (CP-4) can register.
3. **Added fail-closed spec guards.**
   - Owner-only steps: no extraction, no id inside `live.submission.STEPS`, and journaled requires sources.
   - Non-CP-0/CP-1 modules: no `precheck` rules and no `projection` input.
4. **`module_context` with sources** is accepted for live-contract steps too, on this reading of §3.
5. **H1 dependency.** An owner-only sourced step cannot open a real `SourceSession` until H1 lands.

Not verified: no pytest ran, so no new or regression assertion has executed. The heavy S1a and G1 runs were not done. The owner-core paths were exercised only through a fake core and a fake session. The tournament winner is checked by probes, not tests.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n (the first `ruff format` run rewrapped lines)
