# Stage 2 fix batch (one batch; three parallel fixers, then one integration and one scoped Opus re-review of the Medium fixes)

Inputs: `batch/findings.md`, `batch/review-{A,B,C}.md`, `stage2/lows.md`, and the probes each finding names (`<S>` = scratchpad). Every fix is test-first. A Medium code fix begins with a test that fails for the reported cause. A test-strength Medium is shown closed by the reviewer's mutant script now killing its mutant. Each fixer runs the probes for its items and reports their exit codes. Do not edit `cases/`, `methodology.json` or TOOL-CONTRACT. No stub, fake or catch-all. No new `noqa` (13) or `type: ignore` (8).

## Fixer 1, `claude/s2-fix-src` (src defects)
- **M (class test).** CP-DR `gaps.*.questions.*.answer` and CP-3D `summary.text` must be checked as `RunText` in the validator (one TypeAdapter, `<path>: <msg>`, bounded), so nothing raises after the binding write. Then remove both strict xfails in `tests/test_stage2_classes.py`. Probe: `<S>/stage2-classes/verify_findings_owner.py`.
- **Low.** CP-2G `cp2g_reader`: `next(...)` without a default on T2H.7 raises StopIteration. Make it a `ValueError` in the module frame.
- **Low (protocol §6).** CP-2D and CP-1D `_validate_step` parse with raw `model_validate_json`. Route both through `json_object` as the other cores do. Shape issues stay unchanged; check them against the frozen refusals.
- **Low.** CP-1D L1: skip Cf/Mn/Me over the whole tail before taking the 32-char ordinal window. `<S>/cp1d-s2-review/p4_ordinal_identifier_edges.py` (with root arg copies in `<S>/cp1d-batch-probes/`) must exit 0. The frozen compare `p5` must still show moved 0.
- **Low.** CP-1D L6: the CP-1 reference note admits references that assessment rationales refuse. Align `cp1_facts_note` with the core by saying where CP-1 references bind. This is a text-only change. Probe: `p9_cp1_ref_in_assessment.py`.

## Fixer 2, `claude/s2-fix-tests` (test strength)
- **M.** CP-3C (review-B M1): kill all 8 survivors of `<S>/stage2-review-B/b5_cp3c_mutants.py` with varied fixtures:
  - the alias presence check;
  - alias currency, rate_type and scale;
  - the CP-2D scale check;
  - the view run-id check;
  - the reader `total_principal_payable` and `base_claims` with values that differ from the oracle.

  `b9_cp3c_alias_untested.py` must refuse on the tip.
- **M.** CP-2G (review-A M1): seed a CP-1D head whose `T1D.3.supported.value` and `T1D.6` facts differ from the oracle, and assert that `T2H.2.*_supported` and `T2H.8.*.ebitda_fy26_vs_supported` follow it. Fix the docstring `:10-11`.
- **M.** CP-4C (review-A M2): seed a CP-2G head with a scaled `T2H.4.b26/d26.ebitda`, a CP-2A head with a different `s03` decline, and a CP-4 head with a different facility text. Assert that the T4E.3 and T4E.2 copies follow. Fix the docstring.
- `<S>/stage2-review-A/p4_d3_status_only_mutants.sh` must kill m1, m3, m7 and m8b.
- **Low.** CP-4C `_required_module` blocked refusal for CP-1, CP-2A and CP-4. Pin it with a unit test (`p5_cp4c_required_head_refusal.sh`).
- **Low.** CP-3C `GAP_CURRENCY` tripwire: a test that fails once the CP-2D oracle gap twins carry a currency (`b12_gap_currency_target.py`).
- **Low.** CP-1C A1 (`tests/test_owner_cp1c.py:198-203`): ids equal `[prepared-pack, CP-0, CP-1]`, and the pack sha equals `snapshot.pack_sha256`.
- **Low.** `methods/cp2g.md` and `methods/cp4c.md` state the derived-fact citation rule and the round 5 item 17 hold.

## Fixer 3, `claude/s2-fix-infra` (integration and test infrastructure)
- **Low.** `tests/test_owner_g1x.py:523` and `:640` use `hide_row` instead of `delitem` (`<S>/stage2-review-C/pi2_*`, `pi3_*`).
- **Low.** Pin the Stage 1 `SHIPPED_MAPS` base prefix order (`pi1_shipped_order_mutant.py` must kill).
- **G1 I2.** Pin with a test: a valid step that carries forged issues is refused by `StepSubmission.coherent_state`, and the verifier returns `identity_mismatch` after a consistent reseal (`pg1_forged_valid_step_issues.py`). Then close the backlog row.
- **Low (round 5 item 19).** D12 provenance: for Stage 2 records #27, #34, #29, #37, #39 and #40, set `prior_project_sha256` to the file's sha256 in the first parent of `project_commit`, and `project_commit` to a commit whose change brings that file to `sha256`. `pd3_prior_vs_parent.py` must pass for Stage 2 records.
- **Info.** Fix the stale comments at `tests/test_legal_render.py:36-38` and `:44`. Remove the unreachable `UNBOUND_FALLBACK` and the self-comparing note fallback.
- **Lows from `stage2/lows.md`:**
  - CP-8 L-a and L-b;
  - CP-1D L2, L3 and L5 (L5: remove the 3 `type: ignore`);
  - the shared defect test Info (`:529`).
