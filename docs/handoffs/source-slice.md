# Task3-A producer — active tests-first handoff

## Producer outcome — actual positive and gap sessions retained

Implementation commit: `61187e75fa272a724ae00b5dbef1ff6206ea5209` on
`codex/source-slice`, based on `cb71b86019774dfffb808f10d8493ae402dd5602`.
LEAD integrated this implementation in main as `959e652c4d104b7aab05870ca41520473ba02a30`.
The four changed files are workflow.py, test_source_workflow.py, this handoff, and the
explicitly amended host.py guard. No other source, contract, renderer or model settings changed.

The implementation and actual runs used the frozen three-file bundle
`d9fccd16d6121abe08d6847cfb402603ec4c5a388b1f89dd9ca4c4c111f93a00`.
Prior combined 88 tests passed; the final changed-workflow run passed all 31 cases,
with two-file mypy and three-file Ruff green. Required confidence review, no-argument
rewrite tournament and independent Sol/high implementation review are closed.
Earlier pending/admission notes below are historical and superseded by these outcomes.

The current internal offline analytical participant inspected the returned SOURCE bodies
and authored its reviews through the bounded JSON-lines surface. It did not invoke the
unit fixture payload functions, inject final Modules, supply validator callbacks, run a
provider, or change analytical model/effort settings. Developer command execution was
only trusted setup and transport; the retained actual source calls, authored reviews,
real core validation/settlement and CP1 consumption are the producer evidence.
No CP1 Module or Model publication is claimed. C2 owns the remaining rendered/DOM proof.

### Retained stores and receipts (read-only consumer inputs)

- positive: execution `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/runs/task3-source-positive`; receipt `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-positive/receipt.json`.
  Receipt SHA-256 `90925e534fc895fac5bb2d9dd28e4e2d7c7d23e94dcc49378ae949a594b47e02`; final snapshot `3fda7b283bef6cb6ff753b65cebc9abf2c3f8fac1ad2372d562ccc1e2f1501a4`.
- gap: execution `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/runs/task3-source-gap`; receipt `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-gap/receipt.json`.
  Receipt SHA-256 `cf07e26d18ae733b60bee6c6dad389edbdec8fc7a2cf13e828729cc6be19d76a`; final snapshot `45bb2376b6bc3b3dae72a6674f0ba375311d4a34c367e471a9f48abb788a04ca`.

Actual source/case facts and expected outcomes are frozen in the connected manifest
`30b383bd397ecf1c99f3f49d02674605d8ad9c6868da4b4f205124942d731df1`.
Canonical positive pack: `bc15096a011a4f8d431b36489fb63e6ff1d2b6e2e607b907c12bd20d8f2ecd85`;
gap pack: `f5b1192fcfb401681b648ee2d3a4b83e738ba9c2fca8df821283e4b9eb4b0c61`.
These differ from the raw setup JSON hashes, as expected after contract defaults and
canonical serialization. The setup script is data-only:
`artifacts/source-slice-setup/prepare.py`, SHA-256
`9fa8980386ca79d521548f32452d06a6dbe73ec3434ac76423f211071aeec516`.

### Actual participant and process record

ACTUAL-SOURCE-1 was admitted once by LEAD; both case processes ran sequentially on the
same immutable implementation and setup files. Positive PID25461 started at
2026-10-26 22:23:42 UTC and exited0 on EOF by22:26:57 UTC. Gap PID25632 started then
and exited0 on EOF by22:28:09 UTC. Token released at22:28:09 UTC; both processes stopped.
The positive process used terminal session66217, gap41658. Owned PTY canonical/echo
mode was temporarily disabled to prevent long JSON reviews being truncated, then
restored before EOF. This changed transport buffering only, not code, tool permissions,
raw payload bytes, source facts or product model settings.

Positive: CP0 performed scoped identity search/read and financial event search plus
all three financial page reads. The participant observed issuer/group identity,
publication/fiscal year, explicit IFRS/USD/millions/consolidated metadata, all three
annual statements and the report's dated event sentence. It authored a6719-byte
ReadinessReview covering the entire selected FY canonical-foundation method, with
all missing notes/terms/perimeters and broader-work restrictions explicit. Actual
submit_cp0_review settled restricted. A new CP1 session independently repeated those
four supported calls under the selected restricted CP0 input. Its7193-byte authored
SourceContextReview mapped two FY durations and two period-end scopes, classified
financial evidence as unaudited_without_auditor/tier2b, confined no-events to the dated
report, and left borrower/guarantor/restricted roles unresolved. Actual submit_cp1_step
retained valid restricted source_context; CP1 remained pending, with no Module head.
Eight successful calls were made, four per step; no extraction/financial stage ran.

Gap: the participant independently searched/read the gap-case identity source and
attempted the financial read. The latter returned refused/unavailable with null body
and no financial page credit. It then authored a3105-byte CONDITIONAL readiness review,
using only the actually read identity quote (same unchanged source identity, independently
read in this case), naming the missing annual statements and a material source gap.
No positive financial quote, positive CP0 hash or CP1 output was reused. Core CP0 settled
restricted with exact DO NOT RUN; actual Execution.begin(CP1) raised NotAuthorized
without creating a CP1 ticket. Three calls were retained, including the unavailable read.

Each store's source-slice-audit retains the exact ToolCall JSON, authored raw payload
bytes and immutable submission binding before journal transition. Execution retains
validated candidate outputs, selected settled results and all historical snapshots.
The receipt seal authenticates the complete final receipt against that same store.

Exports beside each receipt: `tool-calls.jsonl`, `cp-0-review.json`, positive-only
`cp-1-review.json`, `requests.jsonl`, and `evidence-manifest.json`. Request exports were
reconstructed from exact retained arguments and original authored payload bytes after
the runs; they were not a replay driver. Exact original audit bytes remain in the store.
A flat coordinate summary is `artifacts/source-slice-summary.json` in this clone.

### Actual immutable coordinates

| Case / artifact | Raw payload SHA-256 | Canonical review SHA-256 | Validated step-output SHA-256 | Selected settled result SHA-256 |
| --- | --- | --- | --- | --- |
| positive CP0 | `63e8a353064e9c9038ad726b8568bbb21b4ea133174ddb066fbe5aab4b8a6183` | `95f64c6bc56c4126b090c0dfd5066f825223e1636568f67a6040596b7a419683` | `ec56ed97553208d110852a61281bbcf82a8e273bfad69639fa5c46098b4c96cd` | `c6e7f209aabe1dd6054e3c989a524220a29e63f5e18836992ed8885c1c97c9bc` |
| positive CP1 source_context | `034549236837332822133bdde9977764d1d9cc2af53dfb17d56f821539ccc4d5` | `95a6cc89a0ff8182acd006f8bf204fabe161f754574bd508e2543d8799131ec3` | `e3374cae828bf077c62cb29789296cbbb65c0788cadca073d0c91364327917f4` | none — pending, not promoted |
| gap CP0 | `997d87099abeab25febcb9b19c9191f8e8180130a9405923e630b268649e6670` | `19247c2e3d261a36cc7206c970d86e414fc4f7b98a75d505fd61715ff76a9292` | `e0b7c7dd379212f1a4f2ea722a5d0767668d82d736df188e5f3560375d67bf32` | `9a14f88e74247a9fa388cb20a47495c248da2244cf9032b7993c21b7b3819668` |

Positive CP1 ticket: `45dedb96-2443-4dda-a83d-a7a2beceeffd`. Its actual current inputs
bind the positive pack and selected CP0 result/status restricted. Gap has no CP1 ticket.
Both final snapshots contain only a CP0 head. Tool-call snapshots are the earlier
step-session snapshots; the positive CP0 post-settlement snapshot precedes CP1.begin,
and CP1's post-submit snapshot is final. No earlier call is relabeled as final-epoch use.

### Remaining scope

C2 must consume these exact immutable stores/receipts, publish actual standalone HTML,
and verify visible Evidence/CP0/Limitations/source-inspector DOM. That evidence is still
pending in this producer handoff; source/financial/model owner completion is not inferred
from component checks or the partial CP1 step. Source readiness is the only delivered
analytical slice here. CP1 financials/narrative/readiness/quality, CP1 Module promotion,
Model and other analytical owners remain unrun by this lease. No PDF/OCR, paid/provider,
production deployment or durable recovery qualification is asserted.

---


Exact base cb71b86019774dfffb808f10d8493ae402dd5602, branch codex/source-slice.
Task3 lease authority74efe275e8df8fcb47f854b8b512053ca615d2ef in LEAD clone.
Contract c1970233fd69aa5c7cf5b0a73156a7323eddcc894bd97a4cd558765c023dfb77;
case30b383bd397ecf1c99f3f49d02674605d8ad9c6868da4b4f205124942d731df1.
Route requested/selected Sol/high; no runtime/providermodel substitution.

## Concrete typed receipt/API freeze (producer code pending RED)

workflow.py will export SourceWorkflow.create(directory, pack), invoke(name, arguments),
submit_review(payload: str) -> dict, write_receipt(destination) -> SourceSliceReceipt;
serve_json_lines(workflow, reader, writer, *, destination, participant) and
verify_source_slice_receipt(store: Execution, receipt: SourceSliceReceipt) -> None.
The JSON-lines analytical surface has only invoke/submit_review/write_receipt; no paths.

SourceSliceReceipt schema_version source-slice-receipt/1 fields:
- run: existing Run; pack_sha256; snapshot_sha256 (final current snapshot only).
- participant: trusted setup identity; transport: python-api or bounded-json-lines/1.
- calls: tuple ToolCall (typed exact tool-receipt/1, including each historical binding).
- submissions: tuple ReviewSubmission with module_id, step_id, ticket_id, payload_sha256,
  canonical_review_sha256 (null for schema-invalid/refused raw payload), binding_sha256,
  binding (typed submission-binding/1), disposition(valid/invalid/refused),
  snapshot_before_sha256, snapshot_after_sha256. Payload/binding bytes retained in the
  fixed Execution-local source-slice audit directory by content hash.
- cp0: SettledReadiness with ticket_id, attempt, inputs, status, raw_payload_sha256,
  canonical_review_sha256, step_sha256, step_output_sha256, result_sha256.
  step_output_sha256 is validated candidate Module output; result_sha256 is selected
  settled Module, so they must not be conflated. Canonical review hash differs from raw
  payload hash when JSON formatting differs.
- cp1: SourceConsumer or null. Fields ticket_id, attempt, inputs, status(pending),
  selected_cp0_sha256, raw_payload_sha256, canonical_review_sha256, step_sha256,
  step_output_sha256, output_status. This is a retained valid source_context step only.
- cp1_refusal: not_authorized or null, from actual CP1.begin; no invented ticket on gap.

No CP1 Module/Model promotion. Trusted producer writes a fixed receipt hash seal in
Execution-local audit data; verifier also recomputes selected journal/reference lineage.
This finite audit does not add a recovery ledger or signing service.

## Pending source API compatibility probe

Static trace finds SourceSession's selected-producer check compares producer.inputs
exactly with current_inputs(CP0). Real build_readiness adds readiness-review as an
immutable provenance input; current_inputs(CP0) has prepared-pack only. A real CP0
settlement may therefore prevent the required CP1 source-context factory, although
Task1 synthetic fixture had no canonical readiness-review input. A causal test using
actual submit_cp0_review is written before any fix. No host/import/source edit is
leased; request exact RED admission first, then report reproduced conflict if confirmed.

RED-1 exact command (from exclusive C1 clone):
`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_source_workflow.py`.
Frozen test SHA25632632234ba9c0b930d2982c9e86210b93aaea8969e56bf8636ed2eb4776017c2;
workflow.py absent, all product source at exact startingbase. No runtime admitted yet.

Task3-RED-1 released PID20336;2026-10-26T21:49:47Z start/end;exit1,5failed/0.72s.
Full ignored artifacts/slice-red-1.log. Four explicit absent-workflow assertions.
One actual product conflict reproduced: actual submit_cp0_review accepted/settled
restricted CP0 with exact inputs prepared-pack/readiness-review; actual CP1.begin
succeeded; SourceSession.from_execution then raised identity_mismatch at host.py:100
because producer.inputs != current_inputs(CP0). Fixture/schema/CP0 validator passed.
Proposed narrow lease amendment: host.py selected-producer input check only, retaining
all exact required current input coordinates, and accepting only CP0's canonical
readiness-review provenance input when tied to its actual finished selected attempt,
valid source_readiness step, hash-checked raw review and candidate output. No arbitrary
superset or dropped provenance. Add causal bad-review-hash/extra-input/stale-refusal
regressions to this leased workflow test. No host edit made pending LEAD ruling.

Host amendment received from LEAD: exact authenticated canonical readiness-review tail
only, no generic input superset, no fallback for a genuine recorded review lacking tail.
Implemented guard/helper and added six corruption variants. Workflow bridge implemented
after absent-feature RED. Independent reviewer hypothesis: audit-write failure may avoid
the16-call budget because count increments only after publication. Added causal probe,
no budget patch before reproduction.
RED2 three-file source/test bundle `ef72423d59c534b5bd18b1fe376bab31fe3eff24a4fcb8f8163e840f58eea1b8`; algorithm sorted path,NUL,bytes,NUL concatenation SHA256.
Exact same focused workflowpytest command; full artifacts/slice-red-2.log. No runtime started.

## Priority host-path GREEN request (supersedes pending full RED2)

Frozen5file bundle `ad11e4a3bd183d2926fc35108eb6a3ac284e88b76bd0c5b463b8bba22dce6d31`; sortedpath/NUL/bytes/NUL algorithm.
Paths: host.py,workflow.py,tools/source.py under src/deploy_workflow plus
tests/test_source_tools.py and tests/test_source_workflow.py. No source changed since
prior freeze; the job scope narrows to the real host positive and six provenance
corruptions plus existing58source-hostcases. Exact command:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 main .venv/bin/python -m pytest -q tests/test_source_tools.py tests/test_source_workflow.py::test_real_cp0_review_extra_input_is_accepted_by_cp1_source_factory tests/test_source_workflow.py::test_real_cp0_provenance_cannot_be_dropped_or_forged`

Use the full absolute main interpreter path from prior commands; capture
artifacts/slice-host-green-1.log. Full workflow RED2/audit-bound probe remains queued,
not yet run. No runtime slot held.

HOST-GREEN-1 released PID22093,start2026-10-26T21:58:58Z,
end21:59:00Z,exit0:65passed/0.94s. Full artifacts/slice-host-green-1.log.
Actual CP0-core -> realCP1-source factory now passes with canonical review tail;
six malformed provenance variants refuse;58existing source hostchecks remaingreen.
No source/test edits during run. No full workflow run yet.

Full workflow RED2 now requested after hostpriorityGREEN. Added causal CP1invalid
repair-issuecount probe, frozenAPI refused-canonical-null case, audit/seal bytecorruption
and sealedreceipt mutation. Auditfailure17call test remains unpatched for reproduction.
Threefile sortedpath/NUL/bytes/NUL bundle `7cc509dd9a2d5577bf0e2324e5f092e7abd64a607e5514787b8e92d17b9fe5b0`.
Exact focused workflowpytest command; full artifacts/slice-red-2.log. No run started.

## Confidence review — investigation underway, not closed

1. Real CP0 provenance vs scheduler inputs: confirmed by actualcoreRED; amended helper
   now65focusedchecks green, including genuine positive and six malformed-tail refusals.
   Full selected-attempt/step/canonical/candidate/settled relationship will receive final
   independent sensitive review and changed-path verification.
2. Audit-write failure and callbudget: reviewer gave concrete17delegation probe. Root
   suspicion: bound counts _epoch_calls after persistence, not executed attempts. Causal
   test pending full RED2; no patch inferred without reproduction.
3. CP1 invalid first source_context: actualcore records step issues in step_repairs,
   not attempt.issues. Sanitized issue_count may be zero despite invalid result. Causal
   wrong-pack context test pending full RED2; no patch yet.
4. Raw/canonical/hash/status coordinates: typed fields deliberately separate exact raw
   payload, canonical review, validated candidate step output and settled result. Frozen
   API says refused review canonical hash is null. Causal finalreceipt assertion pending;
   no consumer API spelling or signature changed.
5. Verifier trust seam: current, foreign, forged journal outputs, corrupted audit blobs
   and changed seal probes written. Public verifier never trusts receipt alone; fixed
   audit seal and actual core recomputation required. Runtime outcomes still pending.
6. Actual analytical participant: unit payload fixtures are component tests only. A
   separate retained offline host-agent session must actually read supported results
   and author raw reviews; no canned final Module, fixture validator, paid/provider run
   or CP1/Model promotion can count as connected proof.

Task3-RED-2 released PID22293,start2026-10-26T22:02:11Z,
end22:02:13Z,exit1:26passed/3failed in2.02s. Complete artifacts/slice-red-2.log.
Confirmed exactly3rootissues: auditfailure allowed17actualdelegations because budget
counted publishedcalls; invalidCP1firstrepair reported0issues from wrong aggregate;
frozenAPIrefusedcanonicalhash wasnonnull despite no validation. Real positive/gap,
CP0provenance variants, unread/absence gating, binding/forged/stale/audit/seal checks
passed. No source/test changes duringrun. Correct roots without changing stableAPI.

Confirmed RED2roots patched: attemptbudget consumed before delegated sourcecall,
retained-current-repair issue count used when attempt aggregate is empty; refused
review canonicalhash null per frozenAPI (including verifier semantics). ExactcallIDs/
evidenceprejournal equality guard retained. Added only typedModule parameter and
equivalentdictliteral formatting; noAPIspelling/signaturechange.
GREEN1 threefile bundle `88ed7badeee74c6e2dc43fc5a2e399339c052716f42e25aa816ba5f761931ad1`; same focusedworkflowpytest plus
narrowmypy/ruff requested, no runstarted.

Unrun GREEN1 withdrawn before runtime to prioritize independently found host
no-stepfallback hypothesis: a genuine reviewedCP0 with omitted step and missing
resultprovenance might enter legacyfixture path despite originalcandidate payload.
Added omitted_steps corruptionvariant before any fix. RED3 focusedworkflowfile
threefilebundle `6f9dd9923599ba60fb58f9447d6cb22e784992a9c7878da4643cb84622c7a175`, full artifacts/slice-red-3.log. No runtime started.

RED3 PID23392,22:07:02Z..22:07:04Z,exit1,29passed/1failed1.83s;
sole omitted_steps bypass reproduced. No-stepfallback now hashchecks finishedcandidate,
requires exactschedulerinputs in candidate and result, and core-settle recomputes
finishedattempt/selectedresult. No generic tail/lostprovenance fallback.
Threefile finalcandidate bundle `3a62675e66330129b0523bd31569272b20af7a9ef883112d33375e2b673966da`; nextrequest combined58source+30workflow
focusedcases then2filemypy/3fileruff. No source changes duringRED3; no slotheld.

Task3-FINAL1 released:pytestPID24375,22:09:46Z..22:09:49Z,exit0,
88passed2.31s. mypyPID24380 at22:09:49Z exit1,14Any-related errors because
--follow-imports=skip erases imported Contract/Execution/Pydantic types (8Any-base
classes,6Any-return). RuffPID24385 sameend,exit1 onlyUP047generichelperstyle.
Logs slice-final1-{pytest,mypy,ruff}.log. Proposed next exact2-owned-file mypy
--follow-imports=silent to resolve actual base/method types without claiming imported
core diagnostics/qualification; no ignores weakening the publicreceipt modeltypes.
This checker flag needs LEAD runtime admission. No source edits duringbatch.

## No-argument rewrite tournament — final candidate

Targets after gitdiff/explicit newfile scope: host._producer_inputs and
SourceWorkflow.submit_review. Actualimpact: _execution_state->SourceSession current
checks; fixedtransport/tests->submit_review->actualcoreCP0/CP1submit and CP1.begin;
C2frozenreceiptconsumer. Separate staticroles rewrite_incumbent/speed/memory/readability
and blind emptycontext slice_rewrite_arbiter; none ranruntime or editedsource.
Speedcandidate A disqualified: substituted finishedcandidate payload coordinate for
raw step review, violating provenance. Memorycandidate B (one encoded payload buffer)
beat C(readability incumbent) then D(incumbent); hosthelper incumbentholds.
Winner applied narrowly: encode after bind_submission succeeds, reuse same bytes for
hash/audit. Justification: fewer duplicateallocations; exactUTF8payload/effectorder
preserved; singlelocalbinding improvesclarity withoutpolicychange. Actualtransport
line bound is1048576characters, not a universal1MiBbyte bound; no measuredspeedclaim.
Backup artifacts/slice-before-tournament.py. Final code is currentleasedfunctions;
focusedtests mustverifycandidate beforeacceptance.
UP047fixedmechanically withPEP695generichelper, nointerfacespellingschanged.
Final2threefilebundle `9ec9e960675575baf14097061648e978350511573380c616deaa2fef66624d93`; combined88tests plus2filefollow-imports=silent
mypy and3fileruff requested. Source/tests frozen untiladmittedbatch completes.

FINAL2released:pytest24822 22:14:25..28Z,88passed2.30s; mypy24827
22:14:28..29Z,2filesgreen;ruff24834 at22:14:29Z onlyUP049 (_T->T), nowmechanicallyfixed.
Finalself/independentreview found narrow post-submit historicalreference gap:
positiveCP0 post-snapshot neither callbinding nor final was not read by verifier.
Added causaltest deletesonly thatreferencedhistoricalsnapshot, seal/receipt/current
unchanged. No verifierpatch before RED4. Threefilebundle `456c18923c45d02de5abdf622a3cbe3833fa54ac6f3e5101dddb6c42c3a7d0ba`;
nexttargetedtestonly, full artifacts/slice-red-4.log. No runtime started.

RED4PID24980 22:16:54..55Z exit1, missinghistoricalCP0postreference
confirmed0.68s. Verifiernowhashloadsallrecordedaftersnapshots, validatescanonical/run/
pack and actualpostticket/selectedheadstate; CP0postmustprecedeCP1begin and CP1post
mustbefinal. Beforebindingrefscontinueusingthesamehashloader. No unrelatedancestry
recovery/stateframework orAPIchange. Final3threefilebundle `d9fccd16d6121abe08d6847cfb402603ec4c5a388b1f89dd9ca4c4c111f93a00`;
request31workflowcases +2filefollow-silentmypy +3fileruff; sourcehostunchangedfrom
88green. Full slice-final3logs; source/tests frozen,no runtime started.

## Final implementation validation and confidence closure

FINAL3 released:pytestPID25197 2026-10-26T22:19:12Z..22:19:14Z,
exit0,31passed2.01s; mypyPID25202 at22:19:14Z exit0 exact2targets;
RuffPID25207 sameend exit0. Full slice-final3-{pytest,mypy,ruff}.log.
Previous88combinedcases and unchanged58host cases remain valid; no redundantre-run.
Runtime/type/lint sourcebundle d9fccd16d6121abe08d6847cfb402603ec4c5a388b1f89dd9ca4c4c111f93a00.

Confidence-review final verdicts before implementation commit:
1. CP0provenance/currentness: realcoreRED1 + omittedstepsRED3 confirmedroots; narrowly
   authenticated canonicaltail/candidate/core-settlement fixes now pass including7forged
   variants and58legacyhostcases. No provenance lost, generic supersets or fixturebypass.
2. Evidence-before-submission: real ToolRules/currentbinding/callID/evidence matching
   refuses unread or absence claims before journal writes. Refusal keeps exactaudited
   rawpayload/binding and no canonicalvalidatedhash; validlaterdistinctbinding mayproceed.
3. Partial-I/O/callbudget: RED2 reproduced17actualdelegations; attemptedcountercharged
   beforedelegate fixesroot while retaining the prejournalrecord/evidenceequalityguard.
4. Invalidreviewfeedback: actualCP1 firstinvalidstep issues live in step_repairs;
   retainedmatchingstepissues now counted, never emptyaggregate or rawdiagnosticecho.
5. Durableidentityreferences: receiptseals/auditpayload/call/binding bytes, selectedCP0
   candidatevssettledresult, CP1trustedrecomputation, foreign/staleforgery alltested.
   RED4deletionprovedmissingpostref; every explicitbefore/after/finalreference nowhashloads
   and verifiesactualphase/ticket/headstate. No unrelatedancestry/recoveryprogramme.
6. Error/trust/bounds: fixedJSONRPCpaths fromtrustedsetup only,16actualtoolattempts/step,
   twoanalyticalsteps/64messages/1048576charactersperline; no shell/code/pathtool. Scoped
   sourcehostunchanged; no payer/provider/modelsetting change. Locksrelease in finally;
   rawexceptionsarenotRPCoutput and processcontrol BaseExceptions propagate.
7. Types/callers/tournament: meaningful2targetfollow-silentmypy resolvesrealContracttypes
   (importedcore diagnostics are not a gate). Rootdisqualified speedcandidate's wrongraw
   reviewcoordinate; memorybytebuffer winner verified by88then31focusedcases. Corehost
   guard and submit_reviewpublicsignature/effectorder preserved. No measuredspeedclaim.

Independent source_sensitive_review (configured Sol/high, separate read-only execution)
independently recomputed finald9fccd... bundle, approved finitepostreferenceguard and all
previous state/permission fixes, no remaining materialissue. Its onlypendingconditions
were finalchecks and no furthermaterialchanges; checks nowgreen. Reviewer ran no tests.
Hiddenprovidertelemetry notclaimed. By-design: immutablelocal/singlewriter receipts are
not generalizedconcurrentsettlement/recovery; fixturepayloads arecomponentcases only.
Stillopen: actualparticipantpositive/gap retainedsessions and C2render/browserproof.
Implementation-ready is not an analytical ownercompletion claim.

## Actual participant execution plan — awaiting fresh admission

Trusted setup JSON prepared solely from frozenrawcasebytes (not testpayloadfunctions):
- artifacts/source-slice-setup/positive-pack.json rawfilesha489e1b1fb5d8e8612de2a1eed84ec3808e94342a8661e494b935f60f7186f04c
- artifacts/source-slice-setup/gap-pack.json rawfilesha19f89b563f33ebdfad9feedaa481653ca7946bf490f0c4886955e4d3456dc925
These are rawsetupfilehashes, not PreparedPack.content_hash() after defaults/canonicalization.

From this exclusiveclone, each process is sequential and fixed-path:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -u -m deploy_workflow.workflow --directory '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/runs/task3-source-positive' --pack '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-setup/positive-pack.json' --receipt '/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-positive/receipt.json' --participant 'C1/offline-analytical-host-agent'
```

Gap command is identical except positive->gap in directory/pack/receipt paths.
Internalparticipant will inspectactual returned SOURCE bodies and authorrawReadinessReview
and SourceContextReview through submit_review, never send a canned Module/acceptedstatus,
use a fixturevalidator or add a provider/model loop. Onlyfixedinvoke/submit_review/
write_receiptoperations are sent; write_receipt takes nopath. Stopprocess onEOF.

## Tournament final code (selected2symbols)

```python
def _producer_inputs(store: Execution, snapshot: ExecutionSnapshot, producer: Module) -> bool:
    """Recognize only CP0's authenticated final canonical-review provenance tail."""
    expected = current_inputs(snapshot, producer.module_id)
    if producer.module_id != "CP-0":
        return producer.inputs == expected
    selected = [
        a
        for a in snapshot.attempts
        if a.module_id == "CP-0" and a.result_sha256 == producer.content_hash()
    ]
    if len(selected) != 1:
        return False
    attempt = selected[0]
    if (
        attempt.status != "finished"
        or attempt.issues
        or attempt.interruption is not None
        or attempt.number != producer.attempt
        or attempt.inputs != expected
    ):
        return False
    if not attempt.steps:
        # A removed review step must not hide provenance still held in its candidate.
        if attempt.payload_sha256 is None or producer.inputs != expected:
            return False
        candidate_json = store.payload(attempt.payload_sha256)
        candidate = Module.model_validate_json(candidate_json)
        if candidate.inputs != expected:
            return False
        finished, result = settle(
            snapshot,
            attempt,
            candidate_json,
            lambda _: (),
            pack=store.pack(snapshot),
            load=store.head_module,
        )
        return finished == attempt and result == producer
    if len(attempt.steps) != 1:
        return False
    step = attempt.steps[0]
    if (
        step.step_id != "source_readiness"
        or step.status != "valid"
        or step.inputs != expected
        or step.output_sha256 is None
        or attempt.payload_sha256 is None
    ):
        return False
    review = ReadinessReview.model_validate_json(store.payload(step.payload_sha256))
    if producer.inputs != (
        *expected,
        Input(input_id="readiness-review", sha256=review.content_hash()),
    ):
        return False
    pack = store.pack(snapshot)
    candidate = build_readiness(pack, review, attempt=attempt.number)
    candidate_json = candidate.model_dump_json()
    if (
        step.output_sha256 != candidate.content_hash()
        or store.step_output(step.output_sha256) != candidate_json
        or store.payload(attempt.payload_sha256) != candidate_json
    ):
        return False
    finished, result = settle(
        snapshot,
        attempt,
        candidate_json,
        lambda supplied: () if supplied == candidate else ("CP0 candidate differs",),
        pack=pack,
        load=store.head_module,
    )
    return finished == attempt and result == producer

def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            if self._done or type(payload) is not str:
                raise WorkflowError("not_permitted")
            binding = _parse(SubmissionBinding, self._session.bind_submission(payload))
            payload_bytes = payload.encode()
            expected_evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            if (
                binding.binding != self._epoch
                or binding.payload_sha256 != _digest(payload_bytes)
                or binding.call_ids != tuple(c.call_id for c in self._epoch_calls)
                or binding.successful_call_ids
                != tuple(c.call_id for c in self._epoch_calls if c.status == "ok")
                or binding.source_evidence != expected_evidence
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _put(
                _audit(self._store, "bindings", binding.content_hash()),
                binding.model_dump_json().encode(),
            )
            issues = ToolRules().issues(
                self._epoch.step_id, payload, seen=binding.source_evidence.seen(), context=None
            )
            self._current()
            module, step_id, ticket = (
                self._epoch.module_id,
                self._epoch.step_id,
                self._epoch.ticket_id,
            )
            if issues:
                disposition = "refused"
                validation_issues = issues
            else:
                attempt = (
                    submit_cp0_review(self._store, ticket, payload)
                    if module == "CP-0"
                    else submit_cp1_step(self._store, ticket, step_id, payload)
                )
                disposition = (
                    "valid"
                    if not attempt.issues and attempt.steps and attempt.steps[-1].status == "valid"
                    else "invalid"
                )
                validation_issues = attempt.issues
                if disposition == "invalid" and not validation_issues:
                    rejected = [
                        s
                        for s in (*attempt.steps, *attempt.step_repairs)
                        if s.step_id == step_id
                        and s.status == "invalid"
                        and s.payload_sha256 == binding.payload_sha256
                    ]
                    if len(rejected) != 1:
                        raise WorkflowError("identity_mismatch")
                    validation_issues = rejected[0].issues
            after = self._store.read()
            record = _parse(
                ReviewSubmission,
                {
                    "module_id": module,
                    "step_id": step_id,
                    "ticket_id": ticket,
                    "payload_sha256": binding.payload_sha256,
                    "canonical_review_sha256": None
                    if disposition == "refused"
                    else _canonical(step_id, payload),
                    "binding_sha256": binding.content_hash(),
                    "binding": binding.model_dump(mode="json"),
                    "disposition": disposition,
                    "snapshot_before_sha256": before.content_hash(),
                    "snapshot_after_sha256": after.content_hash(),
                },
            )
            self._submissions.append(record)
            self._current_sha256 = after.content_hash()
            if disposition == "valid" and module == "CP-0":
                try:
                    self._activate(self._store.begin("CP-1"), "source_context")
                except NotAuthorized:
                    self._cp1_refusal = "not_authorized"
                    self._done = True
            elif disposition == "valid" or disposition == "invalid":
                self._done = True
            return {
                "schema_version": "review-outcome/1",
                "status": disposition,
                "error_code": "evidence_refused"
                if issues
                else "validation_failed"
                if disposition == "invalid"
                else None,
                "issue_count": len(validation_issues),
                "module_id": module,
                "step_id": step_id,
                "ticket_id": ticket,
                "snapshot_sha256": self._current_sha256,
                "cp1_refusal": self._cp1_refusal,
            }
```
