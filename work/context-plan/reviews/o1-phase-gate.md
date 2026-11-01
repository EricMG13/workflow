# O1 phase gate results

Range 5a00d7be~1..HEAD. Venv python. Fast tests only (B16), no RUN_PROMOTION. Run 2026-11-01.

## Static gates (six changed src files)
| Command | Exit | Result |
| :-- | :-- | :-- |
| ruff check | 0 | All checks passed |
| ruff format --check | 0 | 6 files already formatted |
| mypy | 0 | no issues in 6 source files |

## Whole files
| File | Exit | Passed | Skipped | Failed |
| :-- | :-- | :-- | :-- | :-- |
| tests/test_owner_presets.py | 0 | 10 | 0 | 0 |
| tests/test_owner_cp1b.py | 0 | 34 | 3 | 0 |
| tests/test_owner_preset_walks.py | 0 | 23 | 2 | 0 |
| tests/test_host_h1.py | 0 | 37 | 0 | 0 |
| tests/test_owner_cp6.py | 0 | 3 | 2 | 0 |
| tests/test_owner_order.py | 0 | 21 | 1 | 0 |
| tests/test_connect_cp1d.py | 0 | 119 | 0 | 0 |
| tests/test_connect_cp3.py | 0 | 102 | 1 | 0 |
| tests/test_cp1b_registration.py (only registration file) | 0 | 15 | 0 | 0 |
| tests/test_owner_cp3.py | stopped (SIGTERM) | - | - | - |

tests/test_owner_cp3.py exceeded 5 minutes whole, so it was stopped. The only O1-changed hunk is in the `blocked` fixture, so the three tests using it were run by node id (test_blocked_cp1a_receipt_verifies_and_the_head_is_re_derived, test_blocked_cp1a_variant_equals_the_oracle, test_an_alias_run_counts_no_alias_completion). That run also exceeded 5 minutes and was stopped. No result: deferred to CI.

## By node id (long files)
One command, exit 0, 5 passed:
- test_owner_workflow.py: test_unsupported_and_unknown_selection_write_nothing, test_cp5_with_cp_model_is_admitted_now_that_the_fan_in_excludes_it
- test_owner_s1a.py: test_cp5_selection_is_admitted_and_spec_overrides_refuse_before_writing
- test_upstream_tools.py: test_integrity_v2_final_recheck_discards_body_and_cursor, test_integrity_v2_cp5_fan_in_excludes_cp_model_b1
- test_earnings_workflow.py: no test function in a changed hunk; nothing run.
- Names seen in the log but no longer present (removed or renamed): test_cp5_selection_and_spec_overrides_refuse_before_writing, test_integrity_v2_dynamic_model_is_mandatory_and_not_pooled.

## Pins
`python3 -I cases/pins.py --check`: exit 0, "cases/PINS.json matches 176 paths".

## git status --short
No O1-touched file uncommitted. Remaining entries are not O1: modified work/context-plan/build-progress.md; untracked work/context-plan/preparer-contract.md, provider-docs-o5-controller.md, reviews/o1-task3-review.md; and a staged .superpowers/sdd/2026-10-31-part-b-o5/task-2-report.md (not from this gate).

## Deferred to CI
- RUN_PROMOTION-gated skips (real CP-1 promotion, 11-26 min): test_owner_cp1b.py x3, test_owner_preset_walks.py x2, test_owner_cp6.py x2, test_owner_order.py x1.
- One other skip: test_connect_cp3.py:512 (CP-5 has a spec; expected).
- tests/test_owner_cp3.py whole file and its three blocked-fixture tests (over 5 minutes).
- Long files not run whole: test_owner_workflow.py, test_owner_s1a.py, test_upstream_tools.py, test_earnings_workflow.py (only the node ids above ran).

## Failures
None. Two runs were stopped on the time limit (test_owner_cp3.py), not failed.
