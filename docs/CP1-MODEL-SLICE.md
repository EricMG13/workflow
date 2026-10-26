# CP1 financial analysis to rendered Model — Task3-B

Authority: user authorized C1/C2/PR MANAGER coordination through full CP1 financial
analysis, rendered output and deterministic Model publication. Paid/provider/live
tests remain paused. Source base: 8d578801e2285194f98062b2d022ec94f33bb34f.

## Scope and independent cases

Complete all five actual CP1 stages (source_context, financials, narrative,
readiness, quality), real promotion, canonical envelope verification, actual
CP-MODEL publication and native rendered proof. Use cases/financial/manifest.json:
a new synthetic pack with four reported 2025 quarters and opening PERIOD_END2024
balances. No reported FY period or prior-year growth assertion. The old annual-only
case and source-only workflow remain immutable and independently scoped.

Ruling: adopted source reconciliation requires all quarters for every reported FY
and every flow member. This new case therefore provides quarterly historical
analysis and a calculated twelve-month Model. Do not weaken gates, relabel a
reported annual figure as calculated, fabricate missing source figures or claim
reported annual comparative qualification. Model readiness must actually be ready
on the positive case. Core publication has a distinct, narrower gate; preserve it.

Manifest literals and source hashes are independent inputs. Monetary source values
are USD millions; normalize and calculate with the existing Decimal core. Preserve
explicit zero versus missing COGS/gross profit and unavailable Q1-Q3 twelve-month
ratios. Q4 own-period margins use Q4 operands (7.5/30 EBITDA margin,
2.25/7.5 FCF/EBITDA); leverage/coverage and flow-to-debt use twelve-month
operands. Freeze actual claim/materiality judgments before evaluating promotion;
independently calculate the QA score from that inventory and adopted formula.
QA Restricted is promotable; do not invent a score60 gate or waive Blocked.

The negative case genuinely lacks the financial source. Actual CP0 must issue
CONDITIONAL / DO NOT RUN, actual CP1 begin must refuse, and the actual publisher
must refuse its absent promoted basis before any Model attempt/files. Do not claim
publication refusal merely because Model-readiness is blocked. Causal component
cases also cover unread/unextracted citation or omitted extracted line, wrong/stale
stage binding, QA-input/lineage tampering, foreign/tampered envelope/publication,
existing destination and interrupted publication. Preserve prior evidence/state.

## Supported APIs (discovered from exact adopted source)

- cp1_workflow.py: submit_cp1_step first four stages; promote_cp1 quality/settlement;
  cp1_registers recomputes stages; write_cp1_envelope/read_cp1_envelope export and
  authenticate the promoted selected head. Private candidate builders are not APIs.
- live/submission.py: submit_model_payload is the supported optional prefill/normalization
  path; retain raw and stored bytes/prefill mappings separately if used. One complete
  bound FinancialSubmission is supported. Parts assembly is optional, never settlement.
- cp1_quality.py: cp1_quality_inputs supplies the authentic QA scope.
- cp_model_workflow.py: publish_cp_model and verify_cp_model_publication; publisher
  owns Python candidate construction and actual journal transitions. No provider call.
- cp1_render.py: render_cp1_envelope produces verified accepted/refused output;
  canonical publisher model.html must remain byte-exact. Generic render is not an
  authentication layer. Use actual core view/build/maps, not duplicate calculations.

C1 discovery handoff lists exact signatures/line locations and copy-ready supported
sequence. C2 handoff lists output routes, binding coordinates and failure seams.
Those are discovery evidence; no new full-CP1 runtime success is implied.

## Exclusive implementation ownership

C1 branch codex/cp1-financial starts exact8d57880; preparation commit c3e09ce is docs only.
Own exactly NEW src/deploy_workflow/financial_workflow.py,
NEW tests/test_financial_workflow.py and docs/handoffs/cp1-model.md.
C1 is the sole Execution writer: actual CP0/source sessions, ordered CP1 stages,
promotion, deterministic Model publication and final receipt seal. No concurrent
C2 writer. Preserve old SourceWorkflow, SourceSliceReceipt and imported core bytes.

Use source search/read/extraction only in the current supported source epochs
(CP0 source_readiness; CP1 source_context/financials). Narrative/readiness/quality
consume the existing adopted source-free projections; no new raw-pack grant.
Full typed NarrativeInputs/DownstreamInputs remain internal for validation/hash.
The analytical read_inputs body uses live.context.narrative_evidence(FinancialStage)
and live.context.readiness_inputs(DownstreamInputs), with current identity/input
hash; do not expose nested source citations/quotes or catalogue.record_json.
Quality exposes only the adopted QualityInputs/quality-scope projection. Record
actual request/body/current binding. Add causal no-quote/no-record_json disclosure
checks; no arbitrary Execution/path access or wider data grant.

Financials must actually use extract_statements on all statement pages and read
located definitions/facility/disclosure evidence in that epoch. Prior source-context
reads do not satisfy financial evidence. Reuse existing ToolRules with full
extracted-line coverage; no arbitrary minimum line count and no old provider
settings import. Trusted adapter may reconstruct Seen from its authenticated actual
receipts and use supported seen_tables(PackTools(frozen admitted pack),seen,retained
SourceContextReview). No private PackTools access or re-extraction credited as a
participant invocation. If a new source/host projection is needed, obtain an exact
named additional lease first; current source/host files are outside this lease.

Retain actual successful/refused calls, immutable raw review and composed/stored
payload identities, binding before journal write, stage disposition/output/current
inputs, QA/register/handoff/candidate/settled identities and actual publication
refusal or success. Core computed outputs must be rederived during verification.
Do not conflate raw hash, parsed content hash, step hash, candidate and settled hash.
Publish only to a trusted setup-selected new exclusive destination. Failed/partial
publisher output is quarantined and never counted as a valid delivery.

C2 branch codex/cp1-rendered starts exact8d57880. Own exactly NEW
src/deploy_workflow/financial_rendering.py, NEW tests/test_financial_render.py,
docs/handoffs/financial-rendered-slice.md. C2 is read-only with respect to Execution:
consume final C1 receipt after publication, verify it and the canonical publication,
export/read real envelope, render real selected-run financials/Model/Evidence/limits.
No imported engine/assets/bindings or old first-slice wrapper changes.

PR MANAGER alone integrates exact LEAD-admitted commits into codex/checkpoint.
LEAD owns this contract, independent cases, PLAN.md, MODULES.csv, QUEUE.md and TEAM.json.
All lanes preserve others' edits. No next owner, production or provider work.

## Frozen C1 -> C2 public interface

Module: deploy_workflow.financial_workflow (leaf import, no shared __init__ edit).

FinancialSliceReceipt is a strict typed content-addressed final run receipt. Public
fields C2 may depend on:

- schema_version: literal cp1-model-slice-receipt/1
- run: Run; pack_sha256: Hash; snapshot_sha256: Hash (final exact current snapshot)
- cp1: None or strict promoted record with ticket_id, result_sha256 and status
  (accepted/restricted). A pending/rejected attempt is never called promoted.
- model: None or strict publication record with ticket_id, result_sha256,
  cp1_result_sha256 and files: exact raw UTF8 SHA256 map for model.html,
  calculation.json and receipt.json. No absolute path is authority.
- refusal: None on success; cp1_not_authorized on the actual missing-source case.

C1 may add typed audit/stage/QA/refusal fields needed to authenticate all lineage.
Document final complete schema in handoff before integration; keep these consumer
fields/signature stable. Render status and journal qualification remain separate.

verify_financial_slice_receipt(store: Execution, receipt: FinancialSliceReceipt,
*, model_directory: Path | None = None) -> None

Raises ValueError on any forged/foreign/stale/incomplete receipt or publication.
Positive requires supplied model_directory, current exact CP1/Model/pack/snapshot,
actual five-stage recomputation/promotion and complete audit lineage; verify the
core publication plus exact raw file hashes. Negative requires model_directory=None,
actual refused CP1 begin and publisher call, no promoted CP1 or Model head/files.
Verifier replay/checks never mutate Execution or grant new sources. Copying the
store/receipt/publication to another directory must still verify.

C1 exposes a bounded trusted-setup workflow/JSON-lines transport for actual internal
offline host-agent participation: create, invoke, source-free projected read_inputs, submit_review,
publish_model and write_receipt. Setup owns paths and finite budgets; analytical
callers receive fixed operations, not filesystem/journal constructors. Actual actor
must inspect genuine returned source/extraction/prior-input bodies and author raw
reviews; test payload helpers or injected final Modules are not actual acceptance.

C2 public function:
render_financial_slice(execution_directory: Path, receipt_path: Path,
model_directory: Path | None, destination: Path) -> Path

Authenticate receipt/store/publication before reading view, after rendering and
before staged publication. Refuse stale or forged state without exposing a mixed
report. Single trusted writer/newdestination precondition as in first slice; no
cross-process atomic no-replace claim. Refuse existing destination and preserve it.

## Render output and actual browser acceptance

Destination contains report.html plus exact source financial receipt and a render
receipt with raw file/selected-run identities. Positive report is actual verified
CP1 financial output. Co-locate exact calculation.json with any report whose Model
panel links that basename. Copy the canonical three-file Model publication unchanged
into destination/model/, with model.html#CP-1 and #CP-MODEL functional. Canonical
Model HTML gets no injected banner/default-route script because its verifier
rederives its exact bytes. A separately rendered report may use honest scoped copy.

Negative produces an honest actual selected-run report (CP0 restricted, CP1/Model
unrun/refused) with the actual missing-source limitation; no Model directory or fake
financial section. Stale/forged receipts or mixed/tampered positive publications
refuse the wrapper entirely rather than being relabeled as negative acceptance.

Actual native IAB proof on immutable positive and negative outputs must check:
- Financials/capital-structure/chart destinations from actual CP1 maps, CP1 Model
  panel, canonical model.html#CP-1 and publication #CP-MODEL, Evidence/Limitations.
- Sourced revenue and explicit zero, missing gross profit, normalized outflow,
  Python-calculated Q4 twelve-month EBITDA/FCF and exact metric numerator/denominator.
- Dates/period kind/currency/units/scale/source hash/locator/quote, exact CP1 result
  passport, actual Model/CP1/pack identities and retained computation trace.
- Click calculation.json relative link; content/hash agrees with canonical receipt.
- Actual ready row/selected quarters/reconciliations, honest QA/restrictions and
  negative no-publication state. Remaining owners/forward projections stay unrun.

## Execution phases and resource/check contract

1. Freeze literal cases/shared API after independent Sol/high expectation review;
   integrate exact LEAD docs/data. Release two disjoint implementation lanes.
2. C1/C2 implement with causal RED->GREEN for material behavior, independent sensitive
   review, confidence-review and no-argument post-edit rewrite-tournament. Preserve
   failures and smallest relevant checks; no broad imported suite or policy redesign.
3. LEAD admits at most one heavy local job after fresh process/load/source-hash check;
   source is frozen throughout that job. Record command/PID/UTC/exit/full logs/hashes.
   Static disjoint work may overlap. Quiet tests are not restarted or killed.
4. Integrate reviewed exact C1 source; run actual internal offline positive/gap
   source-to-full-CP1/promotion/publication using frozen inputs and finite operations.
   Final QA raw judgments/input inventory are frozen and independently checked before
   promotion output is evaluated. Release owned CLI processes/slot on EOF.
5. C2 consumes exact integrated C1 API and genuine final stores/receipts; focused
   render checks, then separately admitted actual renders/native DOM proof. Close
   owned tabs/server, preserve hashes and release slot.
6. PR MANAGER integrates exact reviewed renderer; one justified assembled focused
   check on frozen integrated code. Package portable stores/receipts/envelope/Model/
   reports/native evidence and update only proven matrix links. Full source-to-Model
   chain evidence, rather than mocks/review files alone, closes this slice.
