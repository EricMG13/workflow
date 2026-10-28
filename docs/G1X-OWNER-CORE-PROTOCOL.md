# G1-X owner-core protocol (LEAD ruling, 2026-10-28)

The one contract every owner core in `src/deploy_workflow/owners/<cp>.py` (D12) meets, and the
G1-X change to `src/deploy_workflow/owner_workflow.py` that serves it. Leases for CP-2A, CP-2D,
CP-3, CP-4 and CP-6 cite this file instead of designing their own seams. It builds on the S1a
extension (`docs/S1A-OWNER-RUN-LEASE.md` rev 1–2) and is built only after S1a integrates.
Sources: review-precise-1 of CP-2A and CP-2D, review-precise-2 of CP-4
(`work/lead/<slug>-preparation/`), read against the S1a build.

## 1. Two kinds of module
- **Live-contract modules** (`registry.step_chain(m)` succeeds; today CP-4 `legal_covenants`,
  CP-3 `relative_value`, CP-6 `committee_challenge`): `entry="model_payload"` as now; the core
  supplies only the items of §2 marked *all*.
- **Owner-only modules** (`step_chain` raises "has no live step contract"; CP-2A, CP-2D):
  `entry="owner_core"`; the core supplies every item of §2. No `src/deploy_vii` registry edit.

## 2. Core module attributes (positional signatures, matching G1's call sites)
| Attribute | Who | Contract |
|---|---|---|
| `QUALIFICATION` | all | The `head_of` qualification used by `_verify` (`_QUALIFICATION[m]`). |
| `probe(store, snapshot, attempt) -> None` | all | Raises `WorkflowError("identity_mismatch")` unless the settled attempt and head rebuild exactly (as `owners/cp1a.probe`). Registered in `_PROBES[m]`. |
| `view(historical, attempt) -> tuple[str, str]` | steps with `inputs="module_context"` | `(sha256, body)` of the exact `read_inputs` view; registered in `_VIEWS[step]`. |
| `precheck(store, binding, stored) -> tuple[str, ...]` | optional | A gate on the filled payload. See §4. |
| `STEP_IDS: tuple[str, ...]` | owner-only | The step sequence `_owner_historical`, `_activate` and the verifier use where `step_chain` has none. |
| `SCHEMAS: Mapping[str, type[Contract]]` | owner-only | Model-facing schema per step; `_fill` normalises through it when the step is not in `live.submission.STEPS`. |
| `submit(store, ticket_id, step_id, payload, rules) -> Submitted` | owner-only | Journals one step and returns the same `live.submission.Submitted` type `submit_model_payload` returns, so G1's identity check (`payload`, `nulls_resolved`, `prefilled`, `prefilled_kinds`) and step lookup stay unchanged. |

Registration is a fixed dict in `owner_workflow.py` (`_CORES = {"CP-2A": cp2a, ...}`), never
caller-supplied; `_check_specs` requires `entry == "owner_core"` exactly for owner-only modules.
`OwnerSpec.entry` gains the literal `"owner_core"`; `submit_review` dispatches it to
`_CORES[m].submit`.

## 3. Inputs
- `inputs="module_context"` is accepted for any step with a `_VIEWS` entry (S1a accepted only
  `MODULE_CONTEXTS` steps). The name stays. An owner-only step may also have `sources=True` (CP-DR:
  the view is its agenda, the pack tools its evidence; LEAD amendment 2026-10-28); its pack scope is a
  fixed host-side mapping built by the H1 host task, never caller-supplied.
- `read_inputs` is required before `submit_review` for every step whose `inputs != "none"`,
  with or without a source session (CP-4 review-precise-2 F5). `read_inputs` serves
  `projection` or `module_context`.

## 4. Precheck gate
- Runs on the filled payload after `_fill`, before `rules` of any mode and before the journal.
  Issues → disposition `refused`: no journal step, no attempt consumed, no head; G1's audit and
  receipt record the refused submission exactly as for today's `precheck` rules
  (CP-4 review-precise-2 §4). The ticket stays open; a corrected resubmission on the same
  ticket is allowed within `MAX_CALLS`.
- `StepSpec.rules` keeps one literal (S1a M3). A step may have `rules="journaled"` and a core
  `precheck`; the gate runs first.
- `_verify_submissions` recomputes the gate for every submission of the module: a refused
  record must reproduce exactly its issues; a valid or invalid step must yield none.

## 5. Not in G1-X
- Analytical modules after the deterministic CP-MODEL in a plan: no current lease needs it
  (CP-2D runs without CP-MODEL). Add when a lease does.

## 6. D12 amendment
A new `src/deploy_vii/bindings/<cp>.py` holding only FP block bindings (no arithmetic, reads
facts by table id from the store, never imports `deploy_workflow`) is admitted alongside the
one-line registrations, following `bindings/cp4.py`. `src/deploy_vii` never imports
`deploy_workflow`.
