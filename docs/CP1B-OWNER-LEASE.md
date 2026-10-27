# Task4-B1 — fresh earnings foundation and CP1B owner checkpoint

Frozen pre-implementation lease. LEAD admission must name the exact PM-integrated
A1/A2/A3 implementation plus this contract/oracle revision before C3 writes.
The full PLAN continues through actual CP5 and rendered/native acceptance.
B1 ends at an immutable owner checkpoint; it does not implement CP5 or final export.

## Authority and exclusive files

C3 owns ONLY NEW src/deploy_workflow/earnings_workflow.py,
NEW tests/test_earnings_workflow.py, NEW docs/handoffs/cp1b-owner.md.
No shared file, A1/math, Execution, registry, methodology, live dispatcher,
financial/source workflow or old receipt/verifier, renderer, assets or case edit.
C1 owns the separately frozen integrity bridge; C2 later owns earnings delivery.
LEAD owns cases/contracts/plan/queue/team; PM integrates. Do not revert others.
Sol/high implements/reviews this financial/stateful leaf. Uncapped implementation
retains exclusive leases, frozen inputs, one-heavy-job admission and paid/provider/
live pause. Explicit role assignment is route evidence, not hidden telemetry.

Reuse A1 lease b32b91f8fdf562d101e3c37cd14336a640f1baeac6d4ced93111fc6bc21d767d
and oracle041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599;
A2 lease da0471d83746dc67bf40e9b3e14aa7984994abfa812820265174bd8cb6964142
and oracle a8210ba05e81c3cba04634bfe82e3e7aa11525892407b41d379ebf0298413d0c;
A3 lease b0de1be5a0ae64dff442b5c6652e7a5d8f6d57328d49cc808f37ca5990a6143d
and oracle7b45f939d2d771611e9b11633f348e7c1174cb7ea0b3eb36eeb20661dc4192c4.
Independent B1 expectations: cases/earnings/owner-expected.json. Completed financial
reviews are reused; no financial re-audit or broader nonzero case is added.

Planning inputs: owner-chain-proposal532f7ea2b93b9497050295b80efd83a86effe5f1ad50faf465fd38ecc544e8a9;
integrity-chain-proposal6254cc071f9b6988f88ba93a17aca4f5557fc2860b3ab541f7031554fb9c6f9f.
Projection prerequisite: docs/CP1B-ACCESS-PROJECTION-ADDENDUM.md SHA256
dd2fc2cedacdfed37852ed827b81b03b18367c9062892ca95c78b4561b4a68d9;
cases/earnings/access-projection-expected.json SHA256
c36dc87159e132440d7f3d9d909b1969c81758c4edf9806f6a42a4ca1795add2.
The prior B1 lease4140943f773a42964051dae34166948b52c3631aee381300fb4ec1155c15d0c0
and oracle5a86d095d630eeed947be46ecbd7fa33076e0437b4216b6e0c5fd10841970b6b
are superseded for the confirmed genuine-period whole-row byte blocker. Source,
value, case descriptor, public B1 types and receipt shape remain unchanged.

After PM integrates accepted A1/A2/A3 plus these exact reviewed contracts/oracles
and descriptor, C3 may implement B1's three NEW files concurrently with C1's two
projection files under disjoint exact leases. The additive tool is called through
existing invoke(tool_name,arguments); B1 adds no new type import or stub. B1 GREEN
and actual owner runs require accepted projection code safely integrated into the
C3 clone first, preserving disjoint NEW files (no WIP copy/stub/monkeypatch counted
as integration). Every runtime job still has separate admission. Contract-before-
write does not serialize all implementation writes or create a numerical lane cap.

Static main inspected through dfbb4c9fec84e51c0cc9b8c1262dd1e07daebd9d;
this is not an automatic implementation base. A3's seeded component tests need no
A2 metadata monkeypatch: build/validate_bindings/validate_tables do not whitelist
methodology.table_ids. Actual B1 begin/access requires integrated A1/A2.

## Fresh descriptor and exact run scope

LEAD creates cases/earnings/manifest.json with exactly these keys:
schema_version='cp1b-owner-cases/1', source_manifest='../financial/manifest.json',
source_manifest_sha256 (unchanged6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432),
core_expected='expected.json', access_expected='access-expected.json',
render_expected='render-expected.json', owner_expected='owner-expected.json',
cases (the three ordered records in owner-expected.json/manifest.cases).
Each case has exactly case_id, run, prior_period_id, current_period_id, source_state.
No placeholder pages, review, hash, settled head or receipt in this descriptor.

Every Run has issuer_id northbridge-synthetic, issuer_name Northbridge Synthetic
Group, as_of2026-01-10, method_version deploy-v-r14, case_kind synthetic,
pathway earnings_update, requested_modules exactly ('CP-1B','CP-5') in that order.
IDs: E-QOQ-FLAT/slice-cp1b-flat-v1/q3-2025->q4-2025;
E-NO-YOY/slice-cp1b-no-yoy-v1/fy-2024->fy-2025;
E-REQUIRED-CP1-MISSING/slice-cp1b-missing-source-v1/q3-2025->q4-2025.
source_state is supplied,supplied,financial_missing respectively.

Build new PreparedPack/Execution using literal source objects from the original
financial manifest: same source order identity,financial, exact page strings,
locators, names, source hashes, supplied-representation extraction/readiness and
source metadata. Reuse the existing financial-slice supplied-page construction:
pages become Span(locator,text); coverage=(); media_type=None; extractor=
'supplied-representation'; extraction_status='complete'; status ready and original
sha256. Identity limitation=None; financial limitation exactly 'Unaudited without
auditor; borrower, guarantor and restricted perimeters unavailable.'. Negative
financial source keeps its
source_id/name/media_type/extractor, but status missing, sha256 None, spans/coverage
empty, extraction_status blocked and limitation exactly 'Quarterly financial
statements were not supplied.'. Identity remains unchanged and must actually be
read. No terminal LF/page; U+000C joins pages for source digest. Pack hash is NEW
because Run is new; no old-run import, relabel/fork or injected Module.

Dependency closure is CP0,CP1,CP1B,CP5. B1 executes only CP0, full five-stage CP1,
CP1B; CP5 stays selected/unrun until C1. CP0 assesses selected consumers CP1,
CP1B,CP5. Publication set is exactly empty: no CP-MODEL/CP1D selection/head, Model
files, calculated-download link or fake publication receipt. Old SourceWorkflow
and FinancialWorkflow factories/receipts reject this selection and stay unchanged.
Do not bypass their selection checks using constructors/private phase fields.

## Exact public API

All following names are NEW in deploy_workflow.earnings_workflow. Existing types
are imported from their actual defining modules. New records are strict frozen
Pydantic Contract subclasses (extra forbid, finite Decimals, no mutable authority).
No new arithmetic. Type aliases below are exact, not optional proposals.

- OwnerCaseId = Literal['E-QOQ-FLAT','E-NO-YOY','E-REQUIRED-CP1-MISSING'].
- Transport = Literal['python-api','bounded-json-lines/1'].
- Phase = Literal['source_readiness','source_context','financials','narrative',
  'readiness','quality','earnings_delta','complete','failed'].
- OutcomeKind = Literal['owner_settled','cp1_not_authorized'].
- OwnerError(ValueError) exposes code:str restricted to bad_arguments,
  not_permitted,stale_binding,identity_mismatch,participation_incomplete,
  transport_limit,validation_failed,internal_error. No private quote/detail in
  CP1B-facing exceptions/responses. Unexpected programming/I/O failures propagate;
  no catch-all that turns them into valid empty output.
- EarningsWorkflow.create(directory:Path,pack:PreparedPack,*,case_manifest:Path,
  case_id:OwnerCaseId,participant:str='trusted-python',transport:Transport='python-api')
  -> EarningsWorkflow. It checks the exact descriptor/oracle/source/run pins,
  creates a fresh Execution and begins CP0. Nonempty participant is trusted setup.
- EarningsWorkflow.open(directory:Path,*,case_manifest:Path,participant:str,
  transport:Transport) -> EarningsWorkflow. Reopen only this B1 audit's exact
  run/case/participant/transport and current journal. No arbitrary existing-head
  import route. Reconstruct pending state from durable records; see recovery.
- state(self) -> WorkflowState.
- invoke(self,tool_name:str,arguments:dict[str,JsonValue]) -> dict[str,JsonValue].
  Delegates existing SourceSession in three source epochs or A2 in earnings_delta;
  otherwise refuses. Returns the original detached tool-receipt/1, persisted first.
- read_inputs(self) -> InputRead|OwnerAccessRead. Existing InputRead is from
  financial_workflow; allowed only narrative/readiness/quality. OwnerAccessRead
  allowed only earnings_delta and exposes the A2 bootstrap header, not financial
  answers or source quotes. A bootstrap read is not an actual tool invocation.
- submit_review(self,payload:str) -> ReviewOutcome. Source/foundation schemas are
  existing ReadinessReview,SourceContextReview,FinancialSubmission,NarrativeReview,
  DownstreamReview,QualityReview by phase. CP1 uses existing submit_model_payload
  normalization/prefill. earnings_delta accepts ONLY EarningsDeltaReview below.
- write_receipt(self,destination:Path) -> EarningsOwnerReceipt. Trusted destination,
  only after owner_settled or cp1_not_authorized, no pending unresolved intent.
  Verify, write immutable local canonical receipt/seal and destination, recheck
  currentness; seal the workflow against further operations. No actual CP5 call.
- submit_earnings_delta(store:Execution,ticket_id:str,payload:str) -> Attempt.
  payload is the host-built OwnerSubmissionEnvelope JSON, not actor numeric output
  or a supplied Module. Verify its durable evidence before submit_step/finish.
- verify_earnings_owner_receipt(store:Execution,receipt:EarningsOwnerReceipt) -> None.
  Public read-only verifier, described below; C1 may import these two public
  names without any B1 import of integrity_workflow or an unimplemented C1 type.
- serve_json_lines(workflow:EarningsWorkflow,reader:TextIO,writer:TextIO,*,
  destination:Path) -> None. The destination is trusted setup, not an actor field.

JsonValue is pydantic.JsonValue; JsonObject=dict[str,JsonValue]. Invoke validates
JSON before copying (no deepcopy hooks, NaN or recursive object acceptance).
All setup paths are trusted; JSON messages never supply a source/grant/output path.

## Exact new record schemas

Each bullet lists ALL fields, in serialization order. No unlisted default fields.
Unless explicitly defaulted, every field is required, including nullable fields.
Identifier,Hash,Text,Run,Head,Module,Input,SourceEvidence and existing financial
records retain their current contracts. Integer/count fields reject bool. Indices/ordinals/sequences start at1; issue
counts are nonnegative; attempt is the actual0 or1 permitted by Execution.
New schema_version fields have the stated literal default. Tuples preserve order.

- WorkflowState: phase:Phase; module_id:Literal['CP-0','CP-1','CP-1B']|None;
  step_id:str|None; ticket_id:Identifier|None; attempt:int|None;
  prior_period_id:Identifier; current_period_id:Identifier;
  outcome:OutcomeKind|None. Complete/failed uses null active identity.
- OwnerClose: schema_version='cp1b-owner-close/1'; outcome:OutcomeKind;
  owner_receipt_sha256:Hash; owner_snapshot_sha256:Hash. JSON close returns this
  digest-only record, never the quote-bearing trusted full receipt.
- ReviewOutcome: schema_version='cp1b-review-outcome/1'; module_id:str;
  step_id:str; ticket_id:Identifier; attempt:int; disposition:Literal['valid',
  'invalid','refused']; issue_count:int; error_codes:tuple[str,...];
  snapshot_sha256:Hash; next_phase:Phase; stored_payload_sha256:Hash|None.
  error_codes uses OwnerError categories only; full trusted issues stay in audit.
- OwnerBinding: run_id:Identifier; issuer_id:Identifier; as_of:str;
  method_version:str; pack_sha256:Hash; snapshot_sha256:Hash;
  module_id:Literal['CP-1B']; step_id:Literal['earnings_delta'];
  ticket_id:Identifier; attempt:int; inputs:tuple[Input,...].
- FactReference: producer_module_id:Literal['CP-1']; producer_sha256:Hash;
  fact_id:Identifier; table_id:Identifier; row_id:Identifier; field:Identifier.
- CitationHandle: source_id:Identifier; source_sha256:Hash; locator:Text.
- OperandReference: fact:FactReference; period_id:Identifier; basis_id:Identifier;
  source_period:Text; source_basis:Text; fact_sha256:Hash;
  citation_handles:tuple[CitationHandle,...]. source_period/source_basis preserve
  the actual CP1 fact's full period/scope strings; period_id/basis_id name the
  selected reported historical coordinate, not a label/equal-value alias.
- OperandLineage: measure_id:Identifier; prior:OperandReference|None;
  current:OperandReference; companions:tuple[FactReference,...]. Exact twelve
  measure order and companion order are A1's report order; prior None ONLY when
  requested prior period is genuinely absent. Nonknown existing fact keeps its ID.
- MeasureSelection: measure_id:Identifier; prior_fact_id:Identifier|None;
  current_fact_id:Identifier; companion_fact_ids:tuple[Identifier,...].
- EarningsDeltaReview: schema_version='cp1b-review/1'; prior_period_id:Identifier;
  current_period_id:Identifier; selections:tuple[MeasureSelection,...];
  comparison_assessment:Literal['flat_sequential','comparative_not_supplied'];
  driver_assessment:Literal['not_supplied']; guidance_assessment:Literal['not_supplied'].
  Exactly twelve selections; IDs/assessment must match observed complete scope.
  No numeric answers, raw quotes, hashes, status, formula, Module or free-form
  asserted management driver. Unsupported scope/assessment is a real refusal.
- EarningsPointRecord: all fields/types/order of frozen A1 EarningsDeltaPoint,
  with FactStatus=Literal[known,missing,conflicting,not_applicable].
- EarningsReportRecord: all fields/types/order of frozen A1 EarningsDeltaReport,
  replacing points by tuple[EarningsPointRecord,...]. Conversion preserves every
  value/status/identity/limitation; it does not recalculate or change Decimal quantum.
- OwnerToolReceipt: schema_version='tool-receipt/1'; call_id:str; sequence:int;
  binding:OwnerBinding; tool:str; arguments:JsonObject; status:Literal['ok',
  'refused','error']; body:JsonObject|None; error_code:str|None;
  source_evidence:SourceEvidence. ALL four evidence tuples are empty always.
- OwnerSession: session_id:Identifier; index:int; binding:OwnerBinding;
  normalized_grant_json:Text; access_manifest_json:Text. Both JSON strings use
  compact sort_keys/ensure_ascii=False/allow_nan=False encoding; their structures
  are exactly A2's normalized v2 grant and actual bootstrap header.
- OwnerAccessRead: schema_version='cp1b-access-read/1'; session_id:Identifier;
  sequence:int; binding:OwnerBinding; access_manifest_json:Text.
- OwnerToolCall: schema_version='cp1b-owner-call/1'; ordinal:int;
  session_id:Identifier; receipt:OwnerToolReceipt. Ordinal is global across owner
  sessions; receipt.sequence is that actual A2 session's sequence.
- EarningsParticipation: schema_version='cp1b-participation/1'; binding:OwnerBinding;
  session_id:Identifier; grant_sha256:Hash; manifest_sha256:Hash;
  access_read_sha256:Hash; call_ids:tuple[str,...]; successful_call_ids:tuple[str,...];
  manifest_call_ids:tuple[str,...]; period_lookup_call_ids:tuple[str,...];
  metric_lookup_call_ids:tuple[str,...]; citation_call_ids:tuple[str,...].
  call_ids/all-successes cover the exact current ticket's full retained owner-call
  prefix across sessions; coverage lists must resolve entirely inside the selected
  complete session and have actual successful receipts. period_lookup_call_ids
  and metric_lookup_call_ids retain their exact field names but now identify
  successful read_access_projection pages supplying the corresponding table;
  they may overlap on mixed-table pages. Their union is exactly the complete
  projection-traversal page set. Optional lookup receipts do not replace either
  mandatory traversal. Verifier rederives coverage from actual tool/body/catalog.
- OwnerSubmissionEnvelope: schema_version='cp1b-owner-submission/1';
  binding:OwnerBinding; raw_review_sha256:Hash; review:EarningsDeltaReview;
  participation:EarningsParticipation. This canonical JSON is the CP1B JOURNAL
  step payload. Raw actor bytes and canonical review hash remain separate.
- EarningsOwnerStage: schema_version='cp1b-owner-stage/1'; review_sha256:Hash;
  participation_sha256:Hash; report:EarningsReportRecord;
  operands:tuple[OperandLineage,...]; candidate:Module. Candidate has no hash of
  itself/stage; stage output hashes this full typed record, separately from Module.
- BoundSubmission: schema_version='cp1b-bound-submission/1';
  binding:FinancialBinding|OwnerBinding; raw_payload_sha256:Hash;
  stored_payload_sha256:Hash; canonical_review_sha256:Hash|None;
  call_ids:tuple[str,...]; successful_call_ids:tuple[str,...];
  source_evidence:SourceEvidence; input_read_hashes:tuple[Hash,...];
  participation_sha256:Hash|None; normalization_paths:tuple[str,...];
  prefilled_paths:tuple[str,...]; prefilled_kinds:tuple[str,...]. Foundation uses
  existing FinancialBinding and real normalization/prefill; CP0 has no fill paths.
  Owner uses OwnerBinding, empty source evidence/fill paths and participation hash.
  A pre-envelope shape/participation refusal instead has stored_payload_sha256
  equal raw_payload_sha256, nullable canonical review/participation hashes as
  actually available, and no claimed envelope/step/output/candidate/result.
- SubmissionIntent: index:int; binding:BoundSubmission;
  snapshot_before_sha256:Hash. Persist before invoking any journal mutation.
- SubmissionOutcome: intent_sha256:Hash; disposition:Literal['valid','invalid',
  'refused']; issues:tuple[str,...]; snapshot_after_sha256:Hash;
  step_sha256:Hash|None; step_output_sha256:Hash|None;
  candidate_sha256:Hash|None; result_sha256:Hash|None. Refused participation has
  no step/candidate/result and unchanged snapshot. Valid nonsettling CP1 stages
  have step/output but null candidate/result. Actual finishing candidates/results
  are separate hashes. Invalid review follows existing journal rejection/repair.
- BeginRecord: index:int; module_id:Literal['CP-0','CP-1','CP-1B'];
  snapshot_before_sha256:Hash; snapshot_after_sha256:Hash;
  ticket_id:Identifier|None; attempt:int|None;
  error_code:Literal['not_authorized','not_permitted']|None.
  A refused begin changes no snapshot and invents no ticket/attempt.
- OwnerHeadRecord: ticket_id:Identifier; attempt:int; head:Head;
  candidate_sha256:Hash; step_sha256s:tuple[Hash,...]. All resolve to actual
  finished attempt/candidate/steps; no seeded result or head-only inference.
- SourceIdentity: source_id:Identifier; status:Literal['ready','missing','unreadable'];
  sha256:Hash|None. Exact identity,financial order; missing negative hash is null.
- OwnerPins: case_manifest_sha256:Hash; source_manifest_sha256:Hash;
  core_expected_sha256:Hash; access_expected_sha256:Hash;
  render_expected_sha256:Hash; owner_expected_sha256:Hash;
  sources:tuple[SourceIdentity,...]. Expected-file hashes are actual admitted bytes,
  not hashes supplied in actor text. No self-hash inside an oracle/receipt.
- TransportMessage: index:int; operation:Literal['state','invoke','read_inputs',
  'submit_review','close','invalid']; request_sha256:Hash. JSON-lines only, persist
  exact raw line bytes in payloads before handling; no analytical-read credit.
- AuditEntry: kind:Literal['transport-messages','begins','foundation-calls','foundation-reads',
  'owner-sessions','owner-reads','owner-calls','bindings','intents','outcomes',
  'participations','stages','payloads']; sha256:Hash.
- EarningsOwnerReceipt: schema_version='cp1b-owner-receipt/1'; run:Run;
  pack_sha256:Hash; owner_snapshot_sha256:Hash; case_id:OwnerCaseId;
  pins:OwnerPins; participant:Text; transport:Transport; outcome:OutcomeKind;
  cp0:OwnerHeadRecord; cp1:OwnerHeadRecord|None; cp1b:OwnerHeadRecord|None;
  cp1b_stage_sha256:Hash|None; transport_messages:tuple[TransportMessage,...];
  begins:tuple[BeginRecord,...];
  foundation_calls:tuple[FinancialCall,...];
  foundation_input_reads:tuple[InputRead,...]; owner_sessions:tuple[OwnerSession,...];
  owner_access_reads:tuple[OwnerAccessRead,...]; owner_calls:tuple[OwnerToolCall,...];
  submission_intents:tuple[SubmissionIntent,...];
  submission_outcomes:tuple[SubmissionOutcome,...];
  audit_inventory:tuple[AuditEntry,...]; publication_files:tuple[str,...].
  publication_files must be empty. Foundation records are existing strict public
  FinancialCall/InputRead types, not a FinancialSliceReceipt. owner_settled requires
  all three head records/stage; cp1_not_authorized requires cp1/cp1b/stage null and
  every owner-specific collection empty. Negative must contain the actual CP1
  begin refusal and exact CP0 restricted head, not a fabricated CP1B refusal.

## Finite transport and record budgets

One nonreentrant writer per workflow; do not steal Execution locks or kill writers.
MAX_LINE=4194304 UTF-8 bytes; MAX_MESSAGES=2048 JSON-lines requests per workflow
(durable TransportMessage count across reopen, not a reset); MAX_OWNER_CALLS=1024 per CP1B ticket across all
sessions; MAX_OWNER_SESSIONS=16 per ticket; MAX_OWNER_ACCESS_READS=16 per session.
Foundation maxima remain16 invokes,16 input reads and16 submissions per ticket/
step; source/tool inner bounds remain existing SourceSession/SourceTools limits.
Owner submissions max16 per ticket (including participation refusals); successful
journal settling is still once. Audit record count max16384; receipt canonical
bytes max67108864. Bounded transport sends only outcome/header/call responses,
not the full receipt/stage/Module to CP1B. Exceeding a budget is transport_limit,
not a comparative gap, clean result or silent truncation. No bound is widened.

JSON-lines support is fixed operations state,invoke,read_inputs,submit_review,close
only, with exact keys op; op/tool/arguments; op; op/payload; op respectively.
Transport dispatcher owns trusted receipt destination supplied at setup, writes
one JSON result per complete line and closes only after a terminal receipt; bad
JSON/non-UTF8/oversized/unknown/extra keys refuse without successful evidence.
Successful dispatcher delivery is exactly {status:ok,result:<method JSON value>};
transport refusal is exactly {status:refused,error_code:<OwnerError code>}. An inner
tool receipt may itself be refused; outer ok credits delivery only, never evidence.
close returns only OwnerClose; write_receipt is trusted setup, not a full-receipt
actor disclosure. The CP1B participant receives no foundation transcript/audit/
stage/receipt body; source epochs belong to their separately scoped participants.
EOF before terminal outcome preserves resumable audit and is not successful close.
No arbitrary script/argument/path dispatch. Python API remains equally qualified
when actual calls/submission/settlement are retained; no provider call is required.

Before beginning CP1B, trusted setup checks that the actual grant's records can
fit the additive fact-coordinate pager and a conservative plan inside1024 calls:
complete manifest pages, complete projection pages of ALL granted attributes,
and citation chunks, each bounded by the actual full BODY. Whole-row lookup is
optional and cannot block or replace this complete projected-record route. The
genuine frozen positive138-coordinate and gap126-coordinate grants fit at30/28
required tool calls in the static proof (7/7 manifest,16/14 projection,7/7 citation).
Even one coordinate/page and one fact/verification is414/378 calls, below1024.
Largest full projection BODY pages are7835/8096 bytes; largest single-record BODY
is1747/1745. All include producer/hash/count/offset/cursor/completion overhead and
preserve actual duplicate handles/JSON escaping. New genuinely indivisible records
or excess budgets refuse transport_limit, not absence; this is not a refusal of
the already-proven first case or a substitute for its required actual run.

## Fresh foundation and actual participation

Execution.create -> begin CP0; SourceSession.from_execution for source_readiness.
Persist actual receipts before exposing them; SourceSession.bind_submission must
match exact current binding/raw payload/all and successful call IDs/evidence.
Apply public ToolRules then submit_cp0_review. Valid CP0 authorizes selected CP1,
CP1B,CP5 under normal readiness rules, not synthetic commands injected into a head.
On source negative, actually attempt begin CP1 and retain NotAuthorized; terminal
cp1_not_authorized, CP0 only, no CP1/CP1B/CP5/Model ticket/head/output/publication.

Positive/gap CP1 uses source_context then financials with separate actual source
epochs, new SourceSession/call evidence for each. Other CP1 stages use actual
read_inputs projections before submit. All five stages source_context,financials,
narrative,readiness,quality run under existing normalization/prefill and validators;
quality routes to promote_cp1. No old payload/QA scope is assumed valid under the
new consumers. Bind and retain all original, filled and canonical review hashes,
normalization paths, reads, validation output and actual candidate/result hashes.

Carry financial_workflow's source-participation invariants using public ToolRules,
seen_tables/PackTools and existing typed contracts, without a new financial engine:
financials must extract EVERY located ready-source IS/CFS/BS page; every extracted
statement line/value must map to the exact independently reported quarter/FY/
opening column and match a submitted observation+same-source/locator citation.
Nonempty extracted tables must account for the entire required page set. No
skipped row, FY/Q4 alias, empty extraction or prior epoch read is credited. The
existing explicit header mapping semantics (Qn YYYY, FY YYYY, Opening/Qn/FY date)
apply; ambiguous/unmatched column mapping refuses, no label guess/arithmetic.
Actual current source-context classification selects the financial sources.

Recompute CP0 readiness/candidate/settlement; CP1 valid stage outputs, registers,
quality/handoff/promotion/candidate/settlement using public core APIs and local
read-only historical views. Existing CP1 envelope round-trip write/read is
permitted during an admitted actual verification job, but no Model publication.
CP1 head must match PROMOTED and its actual accepted/restricted result; no fake
QA score or qualification. Then begin CP1B, freeze/authenticate complete current
inputs and same run/issuer/as-of/method/pack/status/current head bytes.

Exact phase transitions after submit: valid source_readiness -> actual begin CP1
and source_context (or complete/cp1_not_authorized on actual refusal); valid
source_context -> financials -> narrative -> readiness -> quality; valid quality
promotion -> actual begin CP1B/earnings_delta; valid earnings_delta settlement ->
complete/owner_settled. A refused participation/shape leaves the current phase and
ticket pending. A core-invalid repairable step with pending attempt reactivates
that same step with its retained repair history. A finished invalid attempt0
begins the same module's actual number1 repair and restarts its first step with
NEW epoch evidence; a finished invalid attempt1 goes failed, no owner receipt.
All begins/outcomes are durable; no extra retry, partial chain or fake terminal
receipt. An interrupted pending validation resumes its exact bytes before any
phase advance. Failed state may be inspected/reopened for audit, but cannot close
as owner_settled or bypass consumed journal repair.

## Exact grant and actual-read closure

Use A2 UpstreamTools.from_execution only CP1B/earnings_delta with its exact v2
grant. Setup derives complete actual T4.14 coordinates and ONLY field_0,field_1
plus selected prior/current historical basis values in T4.10 for twelve A1 measure
rows. Absent requested prior contributes no metric value coordinate. Grant all19
A2 projection attributes, lexically sorted for normalization, no raw sources.
Resolve field_1 metric IDs and exact period identities/model-basis construction;
never trust labels, same date/value or a partial facts object with full CP1 hash.

Require one chosen current owner session with bootstrap read; contiguous actual
read_access_manifest traversal offset0..TOTAL AND contiguous actual
read_access_projection traversal offset0..TOTAL at the same binding/G/M. Projection
entries must match EVERY granted coordinate and ALL19 granted projected attributes,
including exact values/nulls/statuses and original duplicate citation handles.
No actor field filter, omitted attribute or whole-row splitting workaround. The
pager's largest-fitting contiguous entries/full8192-byte BODY and20-entry ceilings
apply. Complete permission metadata alone is not value-read proof. Optional old
lookup_upstream remains available unchanged but cannot substitute for these two
complete traversals. Conflicting repeated returned attributes refuse
identity_mismatch. Require citations verification verdict valid covering all
granted fact IDs, chunks<=20 and8192 bytes. Keep all actual argument/body/ID/
sequence records. Refused/error/oversized/unread pages count no coverage.

COMPARATIVE_NOT_SUPPLIED is legal only after complete T4.14 coordinates and their
actual returned period values establish requested prior absence. Preserve current
FY2025 values including balances20/50/30, opening-2024 as existing balance data,
and null requested prior identities. Unfinished read, malformed/missing selected
row in a present period, ambiguous coordinate, wrong hash/status, permission or
transport failure is a real refusal. CP1B has no source tools/raw quote projection;
trusted full-pack checks do not credit actor source reads.

Every operation validates current snapshot, executable ticket, grant/input/head
status and full producer bytes before projection and immediately before return or
submit. A newly selected head is never followed within an existing session. The
trusted A1 input is the FULL current ModuleView from authenticated complete CP1
Module bytes at the same checked snapshot, not an A2 partial projection.

## Validation, exact candidate and output semantics

Actual tool results precede actor review. Verify review's twelve MeasureSelections
and comparison assessment against complete returned scope and recomputed A1; raw
actor supplied numbers/quotes/hashes/formulas or extra keys refuse bad_arguments.
A1 remains the sole numeric delta/growth implementation and exact refusal authority.
No numeric answer is accepted from the actor or renderer. Same/reverse/incompatible
pairs refuse before a candidate; zero-prior growth stays missing/ZERO_DENOMINATOR.

Build OwnerSubmissionEnvelope and BoundSubmission/SubmissionIntent from actual
record prefix, persist before store.submit_step. The step validator parses retained
envelope, reauthenticates historical participation/full producer, calls A1 and
composes EarningsOwnerStage. Then rederive and finish only the exact candidate.
A crash after retained valid step resumes exact same envelope and rederives stage;
changed raw payload cannot replace it. Malformed/extra-key/raw-number review shapes are retained as refused audit with
no envelope/step and leave the ticket pending. Insufficient/stale participation
also refuses before a journal step. A well-shaped review with incorrect selections/
assessment/comparability enters the retained envelope validator and produces real
invalid StepValidation under existing rejected/blocked one-repair semantics;
no valid step or candidate is manufactured.
No submit_model_payload CP1B entry or shared edit is required.

Candidate identity comes from actual Run/ticket/attempt, status candidate, inputs
EXACTLY (*attempt.inputs, Input('earnings-review',review.content_hash()),
Input('earnings-participation',participation.content_hash())). No other own tails.
Candidate contains exactly44 A3 facts/three layouts in frozen order and exactly
ONE Claim, described below. No self-hash in candidate/stage/inputs. Settled head
uses existing settle; own real gap/scope limits make it restricted; inherited
CP0/CP1 limits are retained. CP1B finish supplies no invented Qualification/QA
step/score; head.qualification=None. Preserve all source numbers and provenance.

Numeric Fact IDs/coordinates/labels/headings/units/decimals/period descriptors are
A3's exact contract and oracle. Prior/current copy source amount/status/value_class,
source_amount/stated_amount/calculation_status/denominator/citations when supplied,
while using CP1B-owned identity and selected period_id presentation descriptor.
OperandReference retains original source-period/scope and actual fact hash.
Prior/current calculation_id and formula are None: these are selected upstream
values, not a new calculation pretending to own the upstream calculation ID.
Missing prior has no source amount/stated amount/denominator/citations/reference.
Derived facts have value_class calculated, source_amount/stated_amount None,
calculation_id `cp1b-calc:{prior_period_id}:{current_period_id}:{measure_id}:{field}`,
calculation_status equal their status. Formula is exactly 'current - prior',
'100 * (current - prior)' for margin delta, '(current - prior) / prior' for growth.
Do not assign a calculation to not_applicable nongrowth cells. Derived basis is
canonical compact JSON of that point's OperandLineage; no numeric operand copies.
Derived citations are original prior then current citation tuples, deduplicated
by complete Citation identity in first occurrence order. Missing reasons preserve
A1 reason; nongrowth limitation exactly 'GROWTH_NOT_APPLICABLE'. Margin delta maps
PERCENTAGE_POINTS to Fact pp as presentation only, no arithmetic/quantization.

Assessment facts remain amount None/unit,currency None/scale1. Exact fixed text,
reasons and limitations are in owner-expected.json/assessments; evidence.inputs.text
is compact canonical JSON object with keys producer_module_id='CP-1',
producer_sha256,prior_period_id,current_period_id,prior_basis_id,current_basis_id,
operands (all twelve OperandLineage records); no copied numeric answers. Canonical
JSON uses sort_keys/ensure_ascii=False/separators comma-colon/allow_nan=False.
All current leverage operands/selected nonknown prior IDs survive in this record
and the typed stage, without extra numeric table rows.

Claim ID exactly 'cp1b-comparison'. Positive text exactly:
'Flat sequential earnings comparison: [cp1b:T1B.1:revenue:delta] [cp1b:T1B.1:ebitda:delta] [cp1b:T1B.1:adjusted_ebitda:delta]. Current balance observations: [cp1b:T1B.2:cash_closing:current] [cp1b:T1B.2:total_debt:current] [cp1b:T1B.2:net_debt:current].'
Gap text exactly:
'Current earnings observations: [cp1b:T1B.1:revenue:current] [cp1b:T1B.1:ebitda:current]. Requested prior income comparison is unavailable [cp1b:T1B.1:revenue:prior] [cp1b:T1B.1:revenue:delta] [cp1b:T1B.1:revenue:growth].'
Chip syntax is existing prose grammar; no bare numeric answer or fake driver.
Claim.citations is first-occurrence union of the referenced facts' actual Citation
records, never invented. Claim.limitation is exactly the corresponding
owner-expected.json/claim.limitations value, including an explicit gap limitation
for the no-YoY claim. CP5 can then review this actual claim and canonical refs.

Candidate.limitations equals the seven ordered owner-expected.json own-limit
strings for the case. These replace neither inherited source limits nor A1 raw
report limitations (the latter remain unchanged in typed stage). In particular,
A1's core-only assurance is not relabelled as actual CP5/native acceptance. Module
settlement adds existing synthetic limitation and inherited limits normally.
A3 Evidence rail remains source inventory/source passports; Full analysis exposes
the evidence record/operand references; Limitations uses Module.limitations.
No rail visibility inferred from binding alone; B1 proves canonical production,
not selected-run/native rendering.

## Durable audit, recovery and owner-prefix verifier

Namespace earnings-owner-audit. Every Contract record is canonical
model_dump_json().encode('utf-8'), filename its content_hash without extension.
Raw payload bytes use SHA256; AuditEntry kind payloads names those exact bytes.
Kinds/records: transport-messages/TransportMessage (empty for python-api);
begins/BeginRecord; foundation-calls/FinancialCall;
foundation-reads/InputRead; owner-sessions/OwnerSession; owner-reads/OwnerAccessRead;
owner-calls/OwnerToolCall; bindings/BoundSubmission; intents/SubmissionIntent;
outcomes/SubmissionOutcome; participations/EarningsParticipation;
stages/EarningsOwnerStage; payloads/original+filled/envelope/candidate JSON bytes.
Record inventory equals the exact unique set implied by embedded receipt records,
intents/outcomes and their referenced payload/stage/participation bytes. Sort
AuditEntry by(kind,sha256); no duplicate/extra/missing file/record is accepted.
Directory creation/write-once is atomic, immutable existing content must agree;
write failure cannot return success or erase prior records. Journal stores its
own blobs as usual; audit copies must equal those exact referenced bytes.

Write owner-receipt.json (canonical EarningsOwnerReceipt bytes) and LAST
owner-receipt.sha256 (receipt.content_hash ASCII, no terminal LF). They are not
AuditEntry records/self-references. External destination receives byte-identical
canonical receipt; reject an existing different destination. Seal only terminal
outcome; no new B1 calls/submissions after sealing. New C1 audit namespace is
separate and cannot mutate the owner namespace.

All operations use durable counters/prefixes. Source-session replay on open uses
historical frozen snapshot and actual recorded calls; compare reconstructed body/
status/evidence with recorded receipt, allowing only original call_id to replace
new UUID. Restore current epoch state by replay; no previous epoch credit.
Foundation projection/normalization/prefill/validation and settled candidates are
rederived, not trusted because a hash string exists. Local historical Execution
views must forbid _write and never point live mutations at a shadow store.

Owner opaque cursors are session-issued: verifier never reinvokes old token in a
new A2 session. Authenticate recorded chosen session binding/grant/header and
rederive exact canonical manifest/digest/counts and full safe projected catalog,
each manifest/projection page's maximal bounded
contiguous prefix, offset/entry/body/currentness identities and issued-token
relationships, with separate manifest/projection issued-token streams. First
cursor null; next_cursor from an earlier successful page in that same session/
stream only; final null iff complete; shapes access-cursor:64lowerhex and
projection-cursor:64lowerhex;
the same issued cursor/limit must return same page; another valid limit may give
another maximal prefix. Token issuance graph and actual bodies are bound by the
immutable transcript digest in journal review/candidate, not a hidden restored
nonce API. Recompute lookup projections/citation verdicts and complete coverage
from authentic full producer/grant; do not trust claimed success/traversal lists.

On reopen before owner step retention AND with no unresolved submission intent,
start a NEW A2 session and require new
complete chosen-session manifest AND projection traversals; retain old session/call history and durable
budgets, never transfer an issued cursor. Once an envelope/step is retained, no
new tool epoch; only revalidate/finish identical raw/envelope bytes. An unresolved persisted intent likewise freezes its
existing evidence/envelope: do not open a new A2 session before resolving it. An unmatched
persisted intent with no journal change can resume its same bytes; with pending/
valid journal step, match retained payload and derive exact outcome before any
advance. After completed mutation but interrupted outcome write, reconstruct the
unique outcome from the pre-intent and authenticated historical journal, never
invoke finish twice. Conflicting/ambiguous intent or evidence refuses. Terminal
receipt requires every intent resolved; no lost invalid/refused submission.

Public verify_earnings_owner_receipt re-parses strict receipt, checks seal/local
canonical bytes/inventory/pins/cases, every referenced snapshot/blob hash, complete
ancestor chain with same Run/pack, exact prefix attempts/heads and all source/
financial/owner participation/validation/settlement above. It is read-only. It
rejects deleted/tampered/extra records, forged source evidence, wrong canonical
review/step/candidate/result identities, missing CP1 promotion, stale/foreign
full CP1, grant/manifest/cursor/coverage drift and self-asserted readiness flags.

At owner_snapshot_sha256, owner_settled heads are EXACT CP0,CP1,CP1B, no pending
attempt, cp1b restricted/qualification None and no CP5 result. Negative heads CP0
only; actual begin CP1 refused unchanged. Current snapshot may equal this anchor
or be a CP5-ONLY authentic descendant for owner_settled: all prefix attempts,
source pack and CP0/CP1/CP1B heads/bytes/inputs/statuses/qualifications unchanged;
additional attempts only CP5, within existing repair policy; additional head only
CP5. Do NOT reseal owner receipt at the later pointer or reject merely because
CP5 began/pended/rejected/repaired/settled.

Authenticate descendant journal transitions with existing Execution/CP5 core:
CP5 begin has exact current_inputs and one pending attempt; retained payload/step
transitions bind actual bytes, correct one-step chain and existing budgets;
valid/invalid outputs rederive via review_scope/validate_integrity/integrity_review;
finished valid candidate via cp5_module and pure settle, including actual PROMOTED
qualification; rejected/blocked outcomes via existing invalid-step settlement.
Pending retained validation may remain pending; it never counts as CP5 acceptance.
No other snapshot mutation/unselected producer/changed prefix is permitted. B1
imports only existing deploy_vii.cp5_integrity for this journal authentication,
never future integrity_workflow; it asserts no actual CP5 tool-participation pass.
C1's verifier must independently establish its actual complete scope reads/review.
Negative owner receipt admits no descendant mutations: missing foundation cannot
become an authenticated owner by adding heads later.

## Separate C1 final-slice composition and remaining acceptance

C1 may import EarningsOwnerReceipt and verify_earnings_owner_receipt exactly.
Its begin takes trusted owner_receipt Path, parses the actual canonical bytes and
requires outcome owner_settled for positive progression. For cp1_not_authorized,
C1 may perform an actual begin(CP-5) refusal probe with unchanged snapshot and
no ticket/head/output; its record belongs only to C1 audit/negative receipt and
never mutates the B1 owner prefix/namespace. Its IntegritySliceReceipt/final EarningsSliceReceipt
may embed this immutable object and call the public verifier against later CP5
snapshots. C1 owns actual complete CP1+CP1B scope tools, claim-complete review,
settlement, IntegritySliceReceipt and final EarningsSliceReceipt/seal. B1 contains
NO import or call to an unimplemented C1 module and does not invent its type.

Final C1 composition must bind owner anchor, authentic integrity receipt, exact
FINAL current snapshot/requested+head set CP0/CP1/CP1B/CP5 and empty publication
set. C2 later consumes that public final verifier before/rebefore staged export.
No final slice seal or CP5/native/FP02 acceptance follows from B1 or direct pure
facts tests. Actual positive/no-YoY/refusal chains need separately admitted fresh
internal offline runs and later actual selected consumer/export/native proof.

## Verification and handoff

Static freeze only: NO product imports, tests, engines, providers or browser here.
Later focused B1 source-only argv, after exact integrated-base/resource admission:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_earnings_workflow.py`

Record exact base/source/runtime/case/oracle hashes, argv, PID/UTC/exit/full logs,
causal refusal/recovery evidence and changed files. No environment sync/broad
suite bundled. Confidence-review and no-argument changed-function rewrite-
tournament plus independent Sol/high review precede completion/commit. PM only
integrates exact reviewed bytes. Author handoff distinguishes pure component
checks from actual retained source/owner participation and remaining CP5/render.

Not verified: implementation or focused tests, actual source/CP1B participation/settlement, durable recovery, CP5 consumption/final slice, export/native rendering or providers.
