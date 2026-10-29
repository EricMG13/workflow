# Stage 2 Lows: one batch at the end of the stage, or riding with the module's next fix

- **[G1-X guards] Low, test gap.** No test covers a step that has a scope row while its `sources` is `False`. The mutant `==` → `<=` at owner_workflow.py:614 survives. Probe: `<S>/s2-g1x-review/p_one_direction.sh`. Source: stage2/g1x-guards-review.md.
- **[G1-X guards] Info.** The docstring lines at owner_workflow.py:563, :565 and :566 are longer than 100 characters.
- **CP-DR (fix1 re-review) Low:** reader refusals for a negative count (L2b) and a per-gap share not known (L2f) are untested; `<S>/cpdr-s2-review/review_mutants_fix1.py`.
- **CP-2E (fix1 re-review) Info:** `tests/test_owner_cp2e.py` docstring :5-6 still says tamper/stale/blocked/begin-refused are not written; `Cite` breaks `copy.deepcopy`/`asdict` (no src path does it; also CP-3D `Cites`); empty summary gets two issues.
- **CP-2A (close release, lease text).** Round 5 item 1's unit rule checks settled operands only; an unsettled operand carries no amount and no currency. Lease text "every operand fact it reads" narrows to "every settled operand". Source: cp2a/fix1-review.md M2; `<S>/cp2a-s2-review/r3_unsettled_stamp.py`.
- **CP-2A Low (unchanged).** Public-API caller-built `Upstream` with forged facts composes (`r4`); not reachable through submit, probe or view.
- **Shared defect test Info.** `test_a_verbatim_pattern_needs_only_one_accepted_value_on_one_path` (`test_defect_classes_selfcheck.py:529`) repeats `:519`; it never shows a second refusing path excused. End batch. Source: defect-classes/fix2-review.md.
- **CP-8 L-a.** `test_identity_is_outside_the_host_scope` asserts only `status != "ok"`; pin `refused`/`not_permitted` (`<S>/cp8-s2-rereview/p14_run_level_refusals.py`).
- **CP-8 L-b.** The `not_permitted`/`stale_binding` tests do not assert "neither consumes an attempt; both recorded in the receipt"; the stale test uses `interrupt`, which consumes the attempt itself. Test gap only (p14 exit 0).
- **CP-1D L1.** The 32-char ordinal window is cut before Cf/Mn/Me are skipped; `2`+31 marks+`nd` reads 2. Skip over the whole tail first (`<S>/cp1d-s2-review/p4_ordinal_identifier_edges.py`). Fails closed under the Source quotes freeze as a guard limit if not fixed.
- **CP-1D L2.** Surviving mutants: constant upstream status, `attempt.inputs` for `current_inputs`, the view's `known` filter removed (`p7_review_mutants.py`).
- **CP-1D L3.** The deferred tamper test does not show the verifier reaching `_PROBES["CP-1D"]`; add a `monkeypatch.setitem` spy as CP-2A does; no edited step output case.
- **CP-1D L5.** `type: ignore` 0 → 3 in tests (`test_connect_cp1d.py:623,625`, `test_owner_cp1d.py:100`); suppressions may only fall.
- **CP-1D L6 (predates).** CP-1 references refused in assessment rationales while `cp1_facts_note` admits them; align the note or the core (`p9_cp1_ref_in_assessment.py`).
- **CP-1D I1.** `context_block` docstring overstates `inherited_limitations` (computed with own=()).
- **CP-2G Info (batch).** `cp2g_reader` uses `next(...)` without a default on T2H.7; a head without the table raises StopIteration, not ValueError. Source: batch/cp2h-report.md release 3.
- **CP-2D (protocol §6).** `_validate_step` uses raw `model_validate_json`, not the `json_object` path. Source: batch/cp3c-report.md item 7.
- **Tests.** `s1a_runs.drive_cp1` hard-codes the readiness literal; `cp3c_runs` and `cp4_runs` duplicate `drive_cp1` (jscpd).
