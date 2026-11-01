# O1 Task 3 review (dbcfbadb) — mx-precise a34fe7b2, 2026-11-01

Written by the controller from the reviewer's text hand-back (reviewer is read-only).
Probes: scratchpad/o1t3-review/ (red_at_base.sh 2, red_partial.sh 1, probe_false_prose.py 1,
q5_blame.sh, probe_byte_identity.py 0). Diff 797 changed lines (ceiling 800); no src/deploy_vii change.

Spec: not compliant (M1). Quality: fix (M1) + Lows.

- **M1, `src/deploy_workflow/owners/cp1b.py:230`, `:87`; `earnings_workflow.py:1648-1683`, `:1929`, `:1962`.**
  Brief F6: the Northbridge `_COMMON_LIMITS` are false on the owner path, yet the owner path still stamps
  them (only the checkpoint line was dropped). `cp1b.py:87` labels any pair with a prior `flat_sequential`
  without looking at the deltas. probe_false_prose.py exits 1: on the Northbridge register q2-2025→q4-2025 is
  accepted and the head says "Requested FY2024 comparison basis is absent; current FY2025 values remain
  known"; on a register where q3→q4 revenue moves (+10) the pair is accepted as `flat_sequential` and the
  claim says "is flat". Phase 2 Task 4 has no prose-generalisation step.
- **L1, `tests/test_owner_cp1b.py:354`.** The RUN_PROMOTION pair test omits the brief's E-NO-YOY real-head case
  and the table/claim equality with EarningsWorkflow; it checks only T1B.1 deltas.
- **L2.** `test_cp1b_candidate_is_the_receipt_path_candidate` compares compose_delta with itself; no committed
  test pins the split's byte identity. No RED messages recorded (plan requires them).
- **Info, `cp1b.py:39`.** Imports private `_operands`, `_own_limits`.

Answers:
1. RED: HEAD's tests at dbcfbadb~1 fail to collect (no cp1b) and host_h1:999 / presets[earnings_update]
   fail; with the new core but no wiring, 5 fail for the right cause, 14 core-only tests pass (can fail at
   BASE only via the import); none vacuous.
2. Period-code deviation correct: `earnings.py:303-308` refuses an unknown current with
   `incomplete_register` and treats an unknown prior as no prior; E-NO-YOY needs it; the brief's rule is
   "named by the existing ValueError code".
3. False prose: yes (M1), severity Medium.
4. Single `*-submission` tail input correct (`host.py:656`, G1X protocol §2); dropping the checkpoint line
   matches F6; `implemented` matches the other owner-only cores.
5. Both failing tests are O1 regressions, not pre-existing:
   - `tests/test_upstream_tools.py::test_integrity_v2_dynamic_model_is_mandatory_and_not_pooled`: passes at
     01ee8514, fails from 5a00d7be (Task 1: `src/deploy_vii/registry.py:25` `_NOT_CP5_FAN_IN` gained
     CP-MODEL) against `tests/test_upstream_tools.py:2303`. The plan should have listed it as a Task 1 caller
     and updated it to the B1 fan-in.
   - `tests/test_connect_cp1d.py::test_registrations_are_appended_at_the_end`: passes at e871f90c, fails at
     0914762e: fdaae9e0 added the CP-6 row at `owner_workflow.py:390` before CP-MODEL, against
     `tests/test_connect_cp1d.py:281`. Fix in code (append CP-6 at the end), not the test.
6. Byte identity of the split `_compose`: true on the literal fixture (232248 and 137586 bytes).

Fast affected set at HEAD: 215 passed, 2 skipped, exit 0.

Not verified: the 2 RUN_PROMOTION tests; the 91 E-* receipt pins on real promoted bytes; test_owner_order,
test_owner_cp1d, test_connect_cp1d beyond the blamed node id; mypy on tests; CP-1D/CP-5 consuming an
owner-path CP-1B head in a walk.
