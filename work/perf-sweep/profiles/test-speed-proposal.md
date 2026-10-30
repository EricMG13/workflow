# Proposal: cut full-suite time (PR MANAGER, 2026-10-30)

Evidence: full suite on 410afa2 took 10h09m (log /private/tmp/claude-501/pm-pytest2.log); ~15 tests take 480-1900 s each, mostly tests/test_earnings_workflow.py. cProfile of
test_fresh_actual_owner_cases_settle_exact_values_lineage_claim_and_immutable_receipt[E-NO-YOY] on 2bbf633: /private/tmp/claude-501/prof3.out (1727 s under profile, 1277 s plain).
Earlier L2 profile (same pattern): /private/tmp/claude-501/prof2.out.

## Hotspots (E-NO-YOY)
- pydantic to_json 325 s / 3.73M calls; validate_json 453 s cum / 187K calls
- contracts.py:78 content_hash 415 s cum / 2.03M calls (re-serialise + sha256 on the same models)
- contracts.py:254 validate_tables 157 s / 5,281 calls
- financial_validation.py:42 records 126 s cum / 47.7M recursive calls
- callers: earnings_workflow._verify_outcome 1051 s (20), _propose_submission 856 s (56), cp1_workflow._stage_registers 609 s (39), _validate_stage 426 s (217), promote_cp1 397 s (14), write_receipt + verify_earnings_owner_receipt ~450 s.

## Proposed changes (in order)
1. Cache content_hash() on immutable models (src/deploy_vii/contracts.py). Only safe if models are frozen or never mutated after hashing: NOT checked.
2. Memoise validate_tables by content hash (contracts.py:254).
3. Skip re-verifying unchanged state in _stage_registers / known_bindings / quality_inputs.
4. Build the expensive owner history once per session as a fixture (copy per test) where tests do not mutate it.
5. pytest-xdist (-n 8; 10 cores): needs a dependency decision record; tests sharing scratch paths/state may collide; floor = slowest single test.
6. Tier markers: fast set per change, heavy ~15 tests once per release.

## Not verified
Profiled one earnings test only; savings unmeasured. src/deploy_vii changes are the user's call per AGENTS.md. Any change needs a failing-first or before/after timing and must keep every hash/byte output identical (pins, oracles).
