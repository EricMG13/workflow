# O1 Task 1 review (commit 5a00d7be), 2026-10-31

Probes: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-tool-use-m365-copilot-research-8ff28f/9d206924-1225-454b-b5b4-bbf09f856c4e/scratchpad/probes-o1t1/`.

## mx-precise: Spec ✅, Quality approve
- L1: add an offline unit test on `_verify_walk` that catches the mutant "pre-stop refusal always on the
  final snapshot" (receipt from the pre-stop refusal world, order CP-0, CP-1, CP-1C, CP-MODEL, MODULE;
  set `publications[0].snapshot_before_sha256` to the final snapshot's parent): probe
  `test_probe_prestop_refusal_rule.py` (run with `PYTHONPATH=src:tests:.`).
- L2: D12 record `project_commit` names the parent 01ee8514; the round-5 item-19 rule needs the commit
  where the file hashes to `sha256` (probe `probe_d12_strict.py <repo> 01ee8514 5a00d7be`, exit 1).
- L3: `test_consumer_behind_an_unrelated_module_after_cp_model_is_admitted` asserts the same thing twice:
  drop the second half or check walk order.
- I1/I2: info (FEEDS docstring; `publish()` return after resume).

## mx-adversary: fix (1 Medium)
- **M1:** `_verify_walk` (owner_workflow.py:1714-1716, with :2396-2414, :2441-2445) checks only heads of
  modules after the refused one, so a receipt that begins CP-3D after a pre-stop refusal and a terminal
  publication refusal (attempt 0 rejected, no head) verifies; 01ee8514 rejects it (regression). Fix:
  refuse `any(a.module_id in analytical[index+1:] for a in snapshot.attempts)`. Probes
  `p2_walk_past_prestop_refusal.sh` (exit 1), `p2b_regression_both_trees.sh`, `p9_fix_validation.sh`
  (with `fixcheck_plugin.py`, exit 0). Also closes I1 (pre-existing, `p7_preexisting_plan_order.sh`).
- L1: `publish()` builds its result after resuming: returns the resumed module's error code and snapshot,
  no `next_step` (probe `p8_publish_error_code.sh`, exit 1). Fix: capture the outcome before `_advance`;
  add `next_step` as `submit_review` does.
- L2: D12 `review` field is a placeholder (manifest.json:1909; probe `p6_d12_hashes.sh` exit 3).
- L3: `docs/G1X-OWNER-CORE-PROTOCOL.md:72-79` §5 still describes publication as terminal after every
  analytical module.
- I2: registry change minimal; hashes adf30a0b → 19ec267d match; no plan order change across presets
  (probe `p5_registry_blast_radius.py`, exit 0).

## Controller rulings
- Fix round 1: M1, plus all Lows above (they ride with this fix).
- D12: `project_commit` names the commit where the file hashes to `sha256` (item-19 rule, strict probe):
  set it to 5a00d7be in the fix commit; `review` names this file.

## Stale pin found by the Phase 7 plan review (2026-11-01)
- **M2 (O1 Task 1):** 5a00d7be changed `src/deploy_vii/registry.py` (adf30a0b… → 19ec267d…) but two oracle files
  still pin the old hash: `cases/cpos-owner/builder/build.py:32` (its `read_pinned` asserts it, so the cpos
  oracle rebuild fails at HEAD) and `cases/cpos-owner/manifest.json:14`. Nothing else pins a file Task 1
  changed (`docs/INTEGRATION.md:968` is a dated record, left as is). Probe:
  `scratchpad/p7probe/cpos_pins.py <tree>` (exit 1 at HEAD).
- Ruling: fix round 2 = a mechanical re-pin by a separate preparer (mx-scaffold, not Task 1's builder), who runs
  the cpos builder twice in a scratch copy plus the product's table, claim and render validators and
  `cases/pins.py --check`, and reports exit codes; reviewed by `mx-precise`. The builder's oracle content does
  not change (Task 1 changed CP-5's fan-in set, not presets); the preparer proves it by the byte-identical
  rebuild.
