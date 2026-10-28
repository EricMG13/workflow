# G1-X adversary review (mx-adversary) on d36b5ab — controller-saved

**Verdict: CHANGES REQUIRED.** There is one Medium and four Lows. Ordering, replay and the §4 gate held under every forgery tried.

Probes: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-review/`. Run them from the target worktree root with `PYTHONPATH="src:tests:<probe dir>"`. They share the setup file `g1x_setup.py`; `base67d/` holds a `git archive` copy of 67d032c.

How the reviewer checked:
- `tests/test_owner_g1x.py`: 15 passed.
- `probe_g1x.py` and `probe_s1a_cheap.py`: exit 0.
- ruff, ruff format and mypy on the changed files: exit 0.

## MEDIUM
**M1. A forged payload makes the verifier raise a raw `TypeError` instead of `identity_mismatch`.**
- **Where:** `owner_workflow.py`. `:1625` calls `_fill` on the forged raw payload before any identity check. That reaches `normalise` (:458, and `financial_workflow._filled` for CP-1). `:1978` catches only `(ValueError, OSError)`.
- **Root cause:** `src/deploy_vii/live/schema.py:700`. `_Walker.branch` looks the tag up with `mapping.get(value.get(propertyName))`, which fails on an unhashable tag.
- **Regression:** base 67d032c (:1817) mapped `TypeError` to `identity_mismatch`.
- **Probes:** `p03_r44_forged_payload_typeerror.py` and `p04_fuzz_payload_exceptions.py`. The fuzz found no other escape class.

## LOW
- **L1.** `_check_steps` doesn't tie `entry` to the module (:576-579). The verifier's `_entry_outcome` still dispatches by module id (:1450-1464). Probe: `p05_open_items.py`, part 3.
- **L2.** `_check_steps` doesn't check that a core is complete: SCHEMAS covering every step, `submit` and `RULES` present, and `SCHEMAS[step]` matching `StepSpec.schema`. A core missing a schema raises `KeyError` at :456 after the audit writes at :880-881, and the run can't be sealed. Probe: `p11_core_registration.py`.
- **L3.** A sourced owner-only step fails after writes until H1 lands, because `host._execution_state` calls `step_chain` (host.py:645, :735). It is unreachable while `_CORES` is empty. This goes to H1. Probe: `p05_open_items.py`, part 5.
- **L4.** The verifier runs `_fill` and `_gate` (:1625, :1646) before the read check (:1652); runtime runs the read check first (:861 before :882 and :887). The comment at :1650-1651 claims they match. Probe: `p10_check_order.py`.

## Open items 1–5
All are safe as built and were accepted in rulings round 4 Part A.

## Older than this change (to the owner)
- Refused records can be dropped, duplicated or reordered across tickets without detection (the same on base). Probes: `p01_refused_records.py` A/C/D and `p02_refused_records_baseline.py`.
- At runtime a payload can raise `TypeError` or `RecursionError` from `normalise` after the binding audit write, and the run can't be sealed. Probes: p03 part 3 and `p12_recursion_preexisting.py`.
- `RecursionError` escapes the verifier on base and target alike (p12).

Not verified: the heavy S1a and G1 suites; M1 end to end on a real CP-1 narrative run; real cores and H1 sessions; whole-chain forgery of steps from attempts that never became heads; mutation testing.
