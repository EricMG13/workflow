# G1-X fix round 1 report (controller-saved)

- **Commit:** `29c0819` on `worktree-agent-a3179638c813adbe7`. It sits on b707e6d, which is a merge of d135d48.
- **Files:** `src/deploy_workflow/owner_workflow.py` and `tests/test_owner_g1x.py`.
- **Tests:** `tests/test_owner_g1x.py` passes 20/20 in about 2.5 s. The G1 and S1a suites are deferred, so this round is built, not done.
- **Gates:** all exit 0.
  - ruff check and ruff format --check on the touched files.
  - `MYPYPATH=src mypy --strict src` (110 files).
  - Extra: mypy on the test file. Fixing it removed two type errors that predate this round.

## Fixes
Each test was seen failing first.

- **M1.** Test: `test_verifier_maps_a_forged_payload_type_error_to_identity_mismatch`.
  - In `_verify_submissions`, only the `_fill(historical, binding.binding, raw)` call maps `TypeError` to `identity_mismatch`.
  - The catch in `verify_owner_run_receipt` is not widened, and its docstring names the one mapped call.
  - A comment names the `_Walker.branch` root fix and says to remove the mapping once it lands.
- **A1.** Test: `test_every_analytical_module_but_cp0_and_cp1_has_an_entry_validator`.
  - `_check_steps` refuses `not_permitted` at create when a module has no `_ENTRY_VALIDATORS` row.
  - The G1 and S1a plans still pass `_check_specs`.
- **A2.** Test: `test_precheck_gate_serves_a_live_contract_module`.
  - This was already true; the test pins it.
  - A CP-1A gate refuses, then the corrected resubmission lands on the same ticket and attempt.
  - Removing the gate at verify gives `identity_mismatch`.
- **L1.** Test: `test_entry_follows_from_the_module`.
  - The entry is derived from the module: `owner_core`, `cp0_review` or `model_payload`.
  - A core must be registered exactly when the module is owner-only.
  - `ENTRIES` is deleted.
- **L2.** Test: `test_owner_core_must_be_complete_at_create`.
  - Each step needs `SCHEMAS[step]`, and it must be the spec's schema.
  - `submit` must be callable.
  - `STEP_IDS` must equal the spec's steps.
  - `RULES` is required only when some step is journaled. The controller confirms this: the protocol needs RULES only for journaled steps, and only `_journaled_issues` calls it.
- **L4.** Test: `test_verifier_requires_the_read_of_a_sourced_view_step` (extended).
  - The verifier's read check now runs before `_hist`, `_fill` and `_gate`.

## Reviewer probes
| Probe | Exit | Change |
|---|---|---|
| p03 | 0 | Part 2: `RAW:TypeError` becomes `identity_mismatch`. Part 3's runtime escape is unchanged (the owner's). |
| p04 | 0 | Unchanged; it calls deploy_vii directly. |
| p05 | 1 | Expected: part 1 is now refused at create, so the probe dies before part 3. Part 5, the H1 gap, is unchanged. |
| p10 | 0 | The precheck runs on `[]`, and a raising gate gives `identity_mismatch`. |
| p11 | 1 | Expected: create refuses the incomplete core. |
| f1_variants (new) | 0 | Eight variants: all accepted before, all refused after. |
| p08 | 0 | Unchanged. |

## Deferred
- `tests/test_owner_workflow.py`
- `tests/test_owner_s1a.py`
- the earlier cheap `-k` subsets

Not verified:
- the G1 and S1a suites. Plan acceptance is shown only by direct `_check_specs`.
- whole-src ruff, which has 92 findings in untouched files.
- M1 through the real CP-1 narrative path.
- the runtime escape and H1 real-session gap, which are out of scope.
- GitNexus `detect_changes`.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
