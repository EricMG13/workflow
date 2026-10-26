# CP-1 financials and deterministic Model discovery

Status: documentation only; product implementation and runtime await LEAD's
contract, independent source/oracle freeze and exclusive lease.

Baseline: integrated main `8d578801e2285194f98062b2d022ec94f33bb34f`.
C1 branch: `codex/cp1-financial`, created from that exact revision. The prior
`codex/source-slice` branch and its `0014ba10b784edc84b10db9916851fb1a21e0b07`
handoff remain intact. No provider, test, product runtime or settings change was
performed for discovery.

All line references below refer to the baseline. C1 compared the bytes of all
20 cited imported core files with the exact baseline before preparing this
handoff; they matched. Public host/workflow were inspected with `git show` at
the exact baseline. These are static findings, not new qualification evidence.

## Supported sequence

`src/deploy_vii/cp1_workflow.py:67` defines the ordered promotion chain:
`source_context`, `financials`, `narrative`, `readiness`, `quality`.

| API | Location | Meaning |
| --- | --- | --- |
| `submit_cp1_step(store, ticket_id, step_id, payload) -> Attempt` | `cp1_workflow.py:201` | Actual ordered submission for the first four stages |
| `validate_cp1_stage(store, pack, attempt) -> StepValidation` | `cp1_workflow.py:195` | Trusted stage validation |
| `cp1_registers(store, ticket_id) -> CanonicalTables` | `cp1_workflow.py:296` | Recomputes all four stages and authenticates retained outputs/current inputs |
| `cp1_quality_inputs(registers) -> QualityInputs` | `cp1_quality.py:144` | Producer-owned QA scope and lineage ceilings |
| `promote_cp1(store, ticket_id, payload) -> Attempt` | `cp1_workflow.py:455` | Actual quality step, verified handoff and settlement |
| `write_cp1_envelope(store, destination) -> Path` | `cp1_workflow.py:535` | Verified selected promoted-head export |
| `read_cp1_envelope(store, directory) -> Envelope` | `cp1_workflow.py:644` | File, envelope-pair and current journal verification |
| `render_cp1_envelope(store, directory, destination, *, pathway=None) -> dict` | `cp1_render.py:108` | Actual renderer; browser acceptance remains unrun |
| `publish_cp_model(store, *, output) -> Attempt` | `cp_model_workflow.py:276` | Actual deterministic CP-MODEL begin/publication/settlement |
| `verify_cp_model_publication(store, output) -> tuple[str, ...]` | `cp_model_workflow.py:324` | Rebuilds selected publication and compares exact bytes |

All paths in this table are under `src/deploy_vii/`. Statement/register previews
at `cp1_workflow.py:213,305` are intermediate evidence. Private `_candidate`,
`candidate_module`, or direct final `Module` settlement must not become an
analytical submission bypass.

`Execution.begin` (`execution.py:612`) owns scheduler authorization, current
inputs, single pending writer and bounded module repair. The existing stage
repair semantics must remain intact. Quality settles the attempt and has no
within-attempt repair.

## Payload checklist

- `source_context.py:122`: `SourceContextReview` binds the prepared pack and
  contains entities, classified sources, reporting scopes, events and limitations.
  Entity roles and borrower/guarantor/restricted perimeter require actual source
  evidence. `ReportingScope` (`:59`) fixes dates, currency, unit, perimeter and
  accounting basis. `scope_matches_period` (`:74`) binds the actual dates/kind.
- `cp1_workflow.py:71`: `FinancialSubmission` contains
  `context_step_sha256`, `financial`, `definition`, `binding`, and optional
  `quarter_ids`. The context-step hash is the retained StepSubmission hash,
  distinct from the source-context review hash.
- `financial_contracts.py:473`: `FinancialReview` (`financial-review/5`) includes
  pack/run/issuer/as-of/method identity, books, analysis and limitations.
  `FinancialBook` (`:433`) requires exact dimensions, periods, accounts, addbacks,
  segments, KPIs, facilities, pro forma, segment allocation and addback/segment
  disclosures. Required arrays may be empty only with honest source treatment.
  Optional statement lines, identities, disclosures, cash/balance movements and
  audit explanations preserve source structure.
- `financial_contracts.py:81`: a known `Observation` requires amount and located
  citations. Missing/conflicting/not-applicable observations require null amount
  and a reason; conflicts require located alternatives. Zero is a known amount,
  never a substitute for a missing observation. Periods (`:112`) require fiscal
  and actual date identity; stated expense presentation requires evidence.
  Statement outflow magnitudes (`:308`) need sign citations; BS balances are
  signed balances.
- `canonical_audit.py:51`: `DefinitionReview` contains
  `financial_review_sha256`, `book_id`, `assessments`, `events`, `limitations`.
  It has no pack hash. Each assessment (`:24`) has metric/canonical and issuer
  definitions, aligned/conflict status, observation references, citations,
  materiality, downstream impact and recommendation.
- `context_binding.py:25`: `FinancialContextBinding` binds financial and
  source-context review hashes and every book to an entity. Validation (`:34`)
  checks all source/financial contracts, references, date scopes and exact
  dimensions.
- `narrative.py:88`: retained `NarrativeInputs` contains the ledger, an exact
  prior-evidence catalogue and scope. `NarrativeReview` (`:123`) contains the
  input hash, findings, dimension coverage, required stories, funding assessment
  and limitations. Findings (`:95`) require title, evidence, risk mechanic and
  credit implication. Passage discriminators are `kind=prose` with `text`,
  `kind=evidence` with `evidence_id`, and `kind=issuer` with no entity field.
  Literal financial figures in prose and invented catalogue references are
  refused. The seven dimensions (`:29`) are leverage, coverage, cash-flow
  quality, liquidity, data quality, definition risks and key gaps. Funding and
  material event stories require evidence-backed assessment.
- `downstream_readiness.py:50`: valid narrative produces `DownstreamInputs`
  with requested consumers, narrative, deterministic Model readiness and book.
  `DownstreamReview` (`:80`) binds those inputs and supplies the exact requested
  consumer requirement and gap assessments. Incomplete requirements need actions;
  evidence IDs and integrity gaps are validated (`:203`). Derive the consumer
  scope from these inputs, including actual infrastructure treatment of Model.
- `quality.py:156`: `QualityReview` contains input hash, materiality/lineage
  judgments for claims, and findings. Scores, bands and statuses are computed,
  never analyst supplied. `cp1_quality.py:144` defines required register/cell,
  dimension, story, funding, analytical-finding and canonical-handoff coverage.
  Producer ceilings cannot be upgraded. `quality.py:200` calculates confidence
  and determines Passed/Restricted/Blocked. A score band is not a new promotion
  gate. `cp1_workflow.py:398` rejects QA Blocked and verifies the envelope handoff.

## Submission and retained inputs

Complete stored schemas may enter through the core APIs. Alternatively,
`live/submission.py:928` supplies the supported adapter:

```python
submit_model_payload(
    store, ticket_id, step_id, payload,
    on_normalised=None, rules=None,
)
```

It normalizes model-facing defaults, prefills trusted pack/source/context/review
hashes and scope dimensions, then enters the same stage/promotion journal APIs.
`known_bindings` (`:482`) and `quality_inputs` (`:471`) derive current bindings.
Do not combine stripped model-facing schemas with raw core submission expecting
all stored bindings.

`FinancialStage` (`cp1_workflow.py:81`) retains `narrative_inputs`, a calculated
Model or `model_issues`, and unrun analytical qualification. The narrative step
retains `DownstreamInputs`. Source-free context access should expose only these
authenticated typed inputs and recomputed QA inputs, not arbitrary store paths.

Optional bounded financial assembly already exists in `live/submission.py`:
`Parts` (`:1254`), `Parts.submit(kind,payload)`, `assemble(parts)` (`:1297`),
`partial_schema` (`:1139`) and `check_part` (`:1237`). Kinds are frame, IS, CFS,
BS and other. Assembly alone does not submit or settle. One-shot complete
FinancialSubmission is supported; the old provider loop is unnecessary here.

Copy-ready core call order, assuming an authorized ticket and complete bound
payloads (not executed during discovery):

```python
from deploy_vii.cp1_workflow import (
    submit_cp1_step, cp1_registers, promote_cp1,
    write_cp1_envelope, read_cp1_envelope,
)
from deploy_vii.cp1_quality import cp1_quality_inputs
from deploy_vii.cp1_render import render_cp1_envelope
from deploy_vii.cp_model_workflow import (
    publish_cp_model, verify_cp_model_publication,
)

submit_cp1_step(store, ticket_id, "source_context", source_context_json)
submit_cp1_step(store, ticket_id, "financials", financial_submission_json)
# Author narrative from authenticated retained FinancialStage.narrative_inputs.
submit_cp1_step(store, ticket_id, "narrative", narrative_json)
# Author readiness from authenticated retained DownstreamInputs.
submit_cp1_step(store, ticket_id, "readiness", readiness_json)
qa_inputs = cp1_quality_inputs(cp1_registers(store, ticket_id))
# Author quality_review_json bound to qa_inputs.content_hash().
promote_cp1(store, ticket_id, quality_review_json)
write_cp1_envelope(store, envelope_directory)
verified = read_cp1_envelope(store, envelope_directory)
render_receipt = render_cp1_envelope(store, envelope_directory, render_directory)
publication = publish_cp_model(store, output=model_directory)
publication_issues = verify_cp_model_publication(store, model_directory)
```

An implementation must check every invalid/finished/refused result before
continuing and retain actual permitted source-tool and submission-binding
evidence. This order is not a wrapper implementation or permission grant.

## Export and Model boundaries

The CP-1 export writes `envelope.md`, `envelope.json` and last-written
`complete.json` into a new directory. The reader verifies files, typed/Markdown
agreement and journal binding (`cp1_workflow.py:601,644`). Candidate handoff
hashes differ legitimately from exported settled-head envelope hashes. Raw
payload, parsed review, step content/output, registers, candidate and settled
head identities must stay separate.

Model publication requires explicit `CP-MODEL` selection in the immutable run,
promoted accepted/restricted CP-1 with retained quality/financial handoff,
calculated Model, no pending attempt and new output directory. It uses the actual
renderer and writes `model.html`, `calculation.json`, `receipt.json`. Verification
rederives actual selected publication bytes. Failed/partial output is not a
successful publication receipt.

`cp_model_workflow.py:74` does not require Model readiness `ready`. Readiness
blocked alone is not a publication-refusal oracle. LEAD ruled that the new
positive must independently satisfy readiness ready, while preserving publisher
semantics. Actual `financial_model.py:263` is
`model_report(pack, review, book_id, *, exclude_unrealised=False)`;
`quarter_ids` selects readiness, not this calculation API. ModelReport limitations
and implementation-only qualification do not become analytical acceptance merely
because publication succeeds.

The old positive run selected only CP-1. Its immutable identity cannot be changed
to qualify Model; create a new independently frozen CP1+CP-MODEL run.

## Current public gaps

At baseline `host.py:18`, raw source capabilities cover CP0/source_readiness and
CP1/source_context,financials. Financials extraction is already admitted.
`SourceSession.from_execution` (`:279`) authenticates the pending ordered prefix,
current inputs and canonical blobs. `invoke` (`:321`) stages permitted source
leaves; `bind_submission` (`:348`) binds evidence/payload but does not submit.

`workflow.py:450` permits only requested_modules=(CP-1,). Its source workflow
ends after source_context (`:577-579`). Existing SessionBinding/SourceSliceReceipt
and verifier intentionally represent that slice. Preserve them.

Missing full workflow responsibilities: bounded stage activation/submission,
typed source-free inputs, current financials epoch source-rule integration,
promotion/export, actual Model publication and final verified receipt.

`live/tools.py:1143` ToolRules has optional line-count/extracted-coverage floors;
defaults import no old settings. `seen_tables` (`:994`) uses only financial pages
shown in the current financials epoch. Earlier source_context reads do not count
for financials evidence. If a frozen floor requires tables, add an explicitly
leased bounded authenticated projection; do not reach into private PackTools.
Raw narrative/readiness/quality are currently denied by the public matrix. Any
change requires LEAD's adopted contract; typed prior inputs need no raw extension.

## Minimum source viability for the new positive

Hard requirements from `model_readiness.py:98-344`:

- Four or more discrete complete, contiguous, nonoverlapping fiscal quarters;
  consecutive fiscal slots and each four-quarter window spanning 364-371 days.
- Located known quarterly flows: revenue, cogs, opex_including_da,
  depreciation_amortization, ebitda, adjusted_ebitda, cash_interest_paid,
  cash_lease_payments, cash_taxes_paid, cfo_ncfo, working_capital_change,
  capex_and_intangible_investment, acquisitions_disposals, net_debt_issue_repay,
  net_equity_issue_repay, dividends_paid, other_investing_financing,
  net_cash_change, lease_payments_in_financing, interest_paid_in_financing
  (`:22`). Source-supported by-nature presentation exempts cogs.
- Located quarterly balances: cash_and_equivalents, rcf_commitment, rcf_drawn,
  senior_secured_debt, unsecured_debt, total_debt, net_accounts_receivable,
  inventory, accounts_payable (`model/history.py:154`).
- Each quarter needs effective_tax_rate or both pretax_income and
  income_tax_expense; all selected facility and present segment/addback series
  must have located known values.
- Nonempty complete carrying-value facility schedule. `FacilityObservation`
  (`financial_contracts.py:221`) carries classifications, amounts and located
  terms. Missing rate type/amortisation/maturity adds WARN, not an invented
  automatic BLOCK. A same-currency fixture avoids unnecessary FX conversion.
- Mandatory quarterly comparisons: SEGMENT_REVENUE, EBITDA_BRIDGE,
  ADJUSTED_EBITDA_BRIDGE, CFO_IDENTITY, NCF_IDENTITY, DEBT_TOTAL_EX_LEASES,
  NCF_CASH_MOVEMENT. Applicable FY/quarter/source-statement/balance checks also
  apply. BLOCK discrepancies/conflicts prevent ready; WARN alone does not.
- Source-supported opening/closing cash and an explicit cash-movement bridge
  or no-adjustment assessment; no balancing plug. Explicit source zero/no-activity
  disclosures where appropriate; honest addback/segment disclosures and located
  statement identities/classifications/definitions.

Recommended smallest source shape: one synthetic entity/book/currency/unit/basis/
perimeter, four reported quarters plus opening period-end evidence and complete
located statements/facilities/disclosures. A consistent FY control is useful but
is not claimed as a hard minimum. Independent oracle must freeze values, signs,
units, dates, citations and expected reconciliation/credit effects first.

Existing annual-only source cannot support this positive. Genuine negative
triggers available under adopted semantics include unrequested Model, absent or
unpromoted CP1, QA Blocked, no retained calculated Model, foreign/changed envelope,
or changed publication bytes. Freeze one actual trigger and public refusal code.

## Ownership and shared seam

LEAD ruling: C1 is the sole Execution writer and performs actual core Model
publication before sealing the receipt. C2 consumes read-only verified results.
No writer cycle or concurrent publication is needed.

Proposed exclusive product lease, not yet active:

- New `src/deploy_workflow/financial_workflow.py`.
- New `tests/test_financial_workflow.py`.
- This `docs/handoffs/cp1-model.md`.
- Conditional narrow host/source-tool changes and causal tests only if the frozen
  capability/coverage contract requires them.

Preserve old workflow/receipt and imported core bytes. LEAD owns shared contract,
oracle/case freeze, PLAN and QUEUE; C2 owns its separately leased consumer/render
files.

LEAD's proposed public seam:

```python
FinancialSliceReceipt
verify_financial_slice_receipt(
    store, receipt, *, model_directory: Path | None = None
) -> None
```

C2 uses only run, pack_sha256, snapshot_sha256; optional promoted cp1 record
(ticket_id/result_sha256/status); optional model publication
(ticket_id/result_sha256/cp1_result_sha256/files); optional fixed-code refusal.
Model files are exact raw SHA mappings for model.html/calculation.json/receipt.json.
Positive verification authenticates supplied model_directory; negative uses None.
C1 may retain additional typed call/submission/stage/QA/audit evidence internally.
Final snapshot follows actual Model publication and verification. `publish_model()`
is the proposed public transition; it must call existing core, retain actual
attempt/files and expose success only after final verification. Names beyond
LEAD's stated seam require the frozen handoff before C2 implementation.

Remaining freeze points: source capability matrix, optional financials floor,
exact negative/refusal meaning, final receipt schema and complete fixture/oracle.

## Confidence and route evidence

Static signature/sequence and gate distinctions are high confidence. Full payload
viability, positive QA result, adapter repair paths, source-rule policy and actual
DOM consumption remain unqualified until admitted implementation/runtime.

`docs/TEAM.json` and the native C1 initial instruction request GPT-6.1 Sol/high.
Current read_thread exposes no selected model/effort telemetry; hidden runtime
selection is not independently asserted. No product setting changed. No code was
modified, so code-edit confidence-review and rewrite-tournament gates were not
triggered by this discovery.
