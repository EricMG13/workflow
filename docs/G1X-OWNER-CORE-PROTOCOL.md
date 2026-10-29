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
| `ENTRY_VALIDATOR(execution, pack, attempt) -> StepValidation` | every analytical module except CP-0 and CP-1 | The validator the module's entry (or its owner core's `submit`) hands `Execution.submit_step`; registered in the fixed dict `_ENTRY_VALIDATORS[m]` (as `cp1a.ENTRY_VALIDATOR`). The verifier replays an invalid step through it on the historical snapshot (S1a R4-2). `_check_specs` refuses `not_permitted` at create a spec whose module has no row, so an invalid step can never be journaled unverifiable (LEAD amendment 2026-10-28, rulings round 4 A1). |
| `precheck(store, binding, stored) -> tuple[str, ...]` | optional | A gate on the filled payload, registered in the fixed dict `_PRECHECKS[m]` for live-contract and owner-only modules alike (CP-4 registers `owners.cp4.precheck`). See §4. |
| `STEP_IDS: tuple[str, ...]` | owner-only | The step sequence `_owner_historical`, `_activate` and the verifier use where `step_chain` has none. |
| `SCHEMAS: Mapping[str, type[Contract]]` | owner-only | Model-facing schema per step; `_fill` normalises through it when the step is not in `live.submission.STEPS`. A settled owner-only head adds exactly one input after its attempt inputs, `<step id with hyphens>-submission`, whose sha256 is `SCHEMAS[step].model_validate_json(<retained step payload>).content_hash()`. The H1 host chooses the schema by the producer's module (`host._submission_schema`): `STEPS` for a live-contract module's own step, `_CORES[m].SCHEMAS` for an owner-only core with that single step id, and otherwise `not_permitted` before any payload read (LEAD amendment 2026-10-28, rulings round 10 item 2, H1 review-adversary F1). |
| `RULES(text, seen) -> tuple[str, ...]` | owner-only steps with `sources=True` | The tool-use evidence rules of the step (cited page read, absence backed by a search), pure over the payload text and the session's `Seen`; reuses `live/tools.py` (`unread_citation_issues`, `UNBACKED_ABSENCE`) and returns issues in the product's sorted order. With `rules="journaled"`, G1-X calls it in place of `ToolRules().issues` (which raises for a step that is not a tool-loop step) both at submit and in the verifier (LEAD amendment 2026-10-28, CP-3D review-precise-1 F1). |
| `submit(store, ticket_id, step_id, payload, rules) -> Submitted` | owner-only | Journals one step and returns the same `live.submission.Submitted` type `submit_model_payload` returns, so G1's identity check (`payload`, `nulls_resolved`, `prefilled`, `prefilled_kinds`) and step lookup stay unchanged. |

Registration is a fixed dict in `owner_workflow.py` (`_CORES = {"CP-2A": cp2a, ...}`), never
caller-supplied; `_check_specs` requires `entry == "owner_core"` exactly for owner-only modules.
`OwnerSpec.entry` gains the literal `"owner_core"`; `submit_review` dispatches it to
`_CORES[m].submit`.

## 3. Inputs
- `inputs="module_context"` is accepted for any step with a `_VIEWS` entry (S1a accepted only
  `MODULE_CONTEXTS` steps). The name stays. Any step, live-contract or owner-only, may combine
  `module_context` with `sources=True` (CP-3 `relative_value`; rulings round 4 A4) (CP-DR:
  the view is its agenda, the pack tools its evidence; LEAD amendment 2026-10-28); its pack scope is a
  fixed host-side mapping built by the H1 host task, never caller-supplied.
- `read_inputs` is required before `submit_review` for every step whose `inputs != "none"`,
  with or without a source session (CP-4 review-precise-2 F5). `read_inputs` serves
  `projection`, `module_context` or `step_context` (the last two serve `_VIEWS[step]`,
  `owner_workflow.py:820`; a step that declares either without a `_VIEWS` row is refused `not_permitted`
  at create, `:949`).
- `_check_specs` refuses (`not_permitted`) an owner-only step that offers statement extraction,
  uses a step id in `live.submission.STEPS`, or has `rules="journaled"` without `sources=True`; and
  any step outside CP-0/CP-1 with `rules="precheck"` or `inputs="projection"` (those take the
  11-field financial binding) (rulings round 4 A3). CP-4's `inputs="step_context"` is built
  (`StepSpec.inputs`, `owner_workflow.py:272`; `OWNER_SPECS["CP-4"]`, `:476`).

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

## 5. Plan ordering after CP-MODEL (built); not in G1-X
- (Round 2 of `docs/rulings/2026-10-28-stage2.md`, built at `owner_workflow.py:1004-1010`.)
  An analytical module may follow the deterministic CP-MODEL in a plan only when neither
  consumes the other, directly or through `plan`'s producer graph (`_check_specs`); anything
  else refuses `not_permitted`. Publication stays terminal: it runs once, in phase `walked`,
  after every planned analytical module has its outcome. `_refused` and `_terminal` look only
  at CP-MODEL's own required producers; the analytical walk order is `planned` with the
  deterministic module skipped; at most one deterministic module per plan.
- An owner-only `sources=True` step opens a real `SourceSession` only through the H1 fixed host
  mapping; until H1 lands, such steps are exercised by test-only sessions and no Stage 2 run of
  them is admitted (rulings round 4 A5; build order unchanged). A `_SOURCE_STEPS` row alone is not
  enough. H1 must also stop `host._execution_state` (host.py:645) from calling `step_chain` for owner-only
  modules, which have none (LEAD amendment 2026-10-28, G1-X review-adversary L3).

## 6. D12 amendment
A new `src/deploy_vii/bindings/<cp>.py` holding only FP block bindings (no arithmetic, reads
facts by table id from the store, never imports `deploy_workflow`) is admitted alongside the
one-line registrations, following `bindings/cp4.py`. `src/deploy_vii` never imports
`deploy_workflow`.
- **Composition is authenticated at the receipt verifier, not the H1 host.** `_verify_settlements` runs `_PROBES[m]` on every settled head. The host's job is provenance (`docs/OWNER-WORKFLOW-LEASE.md:193-194`), so it does not repeat the rebuild (rulings round 10 item 3, H1 I1).
- **The H1 failed-head branch** accepts a rejected or validator-blocked producer: no tail, non-empty issues, no interruption. It refuses an interruption-blocked producer, which therefore fails closed. A lease that interrupts an analytical step adds the interruption to this replay in its own amendment (rulings round 10 item 4, H1 I2).
- **`_check_steps` refuses `not_permitted` at create** in two cases (rulings round 10 item 6; rides with the next G1-X change):
  - an owner-only step whose `sources` disagrees with the H1 `_OWNER_SCOPES` row;
  - a core whose `STEP_IDS` is not a tuple of str.
- **A core reads model payload text only through `deploy_vii.live.schema.json_object` or `payload_document`.** This covers its `RULES`, its `_PRECHECKS` gate and its `submit`. Those are the bounded, storable parse that 0d-b (1a1a140) installed; no raw `json.loads` of model text is allowed. Because of this, a payload cannot raise after the binding audit write (LEAD amendment 2026-10-28, 0d-b plan §3).
- **A core builds a caller-quoting issue line in its `RULES` or `_PRECHECKS` gate only with `deploy_vii.execution.listed_issues` and `clipped`, or by reusing the `deploy_vii.live.tools` rules.** `listed_issues` keeps at most 20 lines of at most 600 characters and formats only the lines it shows, so a payload cannot make the gate's issue text outgrow the payload after the binding write (LEAD amendment 2026-10-28, 0d-c plan §5 item 5).
- **Oracle limitation lists are pre-settle.** Settled-equality tests and readers use `execution.settle`'s lists (synthetic run line in own): on a `case_kind: synthetic` run it appends "Synthetic case; not real issuer qualification" to the module's own limitations (deduplicated) and leaves it out of inherited (`deploy_vii/execution.py:472-478`; rulings round 3 item 5).
