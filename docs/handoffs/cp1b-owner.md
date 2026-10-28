> **LEAD integration note, 2026-10-28.** This was integrated into the LEAD branch after fix round 9 and the F-3 test (`earnings_workflow.py` 552ea0a8b6e432feca2a553f6e3b60dacb57acb7f860ac40c5b16c2090cd4866, `tests/test_earnings_workflow.py` 149b0eab6d5b3d4916336e1c005d017ea79f9ec54069a2ccc199bbcde8eaf7df). The review trail is `review-adversary-fix-6` to `-fix-9` in the coordinator-3 clone's `work/cp1b-owner-b1/`, and rounds 7-9 ran by user decision. The text below is the implementer's work-in-progress record and is kept unedited. Its status lines predate the fixes. Tests are deferred to LEAD's final verification phase (`work/lead/deferred-runs.md`).

# Task4-B1 fresh foundation/owner checkpoint — work in progress

Exclusive branch `codex/cp1b-owner-b1`, admitted base
`4e2bce9df0e010f0795c392e8254db12fce5fcfe`. A1 branch/commit and all prior work/logs
are preserved. Exactly three NEW tracked files are leased:
`src/deploy_workflow/earnings_workflow.py`, `tests/test_earnings_workflow.py`,
this handoff. No edits to A1 math, shared APIs, Execution, registry, host, old
financial/source workflow, A2 pager, renderer, cases or future A4 module.

## Authority, route and pre-write pins

LEAD admission `C3-CP1B-OWNER-B1-IMPLEMENTATION-1` recorded2026-10-27
10:20:14.797666UTC authorizes writes/light static checks only. No runtime job is
bundled. Fresh global scan had no heavy job; load2.59/2.48/2.28. Root rehashed all
144 baseline files against LEAD `work/cp1b-preparation/projection-owner-source-before.json`
before writes: zero mismatches. All six frozen contract/case/review pins match:

| Input | SHA256 |
| --- | --- |
| B1 lease | e66aa2df765ff76c2fe9644ba2f5c003dc65572ad6060246538265171bc54071 |
| Owner oracle | c8af02d3760f0ac24a8ecd2e2e6d2f3be38f260c706d200995b12c0f3d37456d |
| Case descriptor | 60ed95782648064db7806bb7f0714fe030f9563424df50e17500803a2edfb7ec |
| Projection addendum | dd2fc2cedacdfed37852ed827b81b03b18367c9062892ca95c78b4561b4a68d9 |
| Projection oracle | c36dc87159e132440d7f3d9d909b1969c81758c4edf9806f6a42a4ca1795add2 |
| Independent contract review | f5602baaa9f1fcb0114b23bf2a3c773d649aab598fb82ad1c5671ecc1c1fcdc3 |

Explicit financial/state implementation route: reused GPT-6.1 Sol/high worker
`cp1b_core_implementation`, now assigned only the two NEW B1 code/test files.
Root owns this handoff. Actual dispatch selection is recorded; hidden model
telemetry is not asserted. Source/value/pre-code independent reviews are reused;
no new numerical audit, paid/provider/live work or product setting change.

## Execution ledger and boundaries

- Exact clean tracked base established; all144 source/test/case pins verified.
- Initial test-first draft is underway. Missing-feature baseline and any later
  focused/actual job require separate exact-source/resource admission.
- Initial test/check scope must explicitly name the unimplemented integrated
  projection dependency. Accepted A2 pager integration is required before B1
  full GREEN/actual owner; no product stubs, grants monkeypatch or copied WIP.
- Foundation must be a fresh descriptor-bound earnings run: actual CP0, every
  current-epoch source read/extraction, all five CP1 stages, new QA/promotion;
  no old-run relabel, injected head or FinancialWorkflow factory bypass.
- Owner must bind full authenticated CP1 plus complete manifest AND all19-field
  projection traversals and citations before review/envelope/settlement. Twelve
  typed lineages,44 canonical facts/three tables and one Claim follow the frozen
  oracle. Existing whole-row lookup cannot substitute for required traversal.
- Durable receipt/prefix verification includes intents/recovery and authentic
  CP5-only descendants, while actual CP5 participation/final export remain A4.
- Confidence review, no-argument changed-function tournament and independent
  sensitive implementation review are pending; no passing implementation claim.

One precise transport boundary remains reported to LEAD: the committed signature
still accepts generic TextIO, while the audit requires exact raw line bytes and
non-UTF8 rejection. A generic text wrapper can normalize CRLF or fail decoding
before B1 can retain original bytes. No policy is invented here; schemas and
nontransport foundation/owner work proceed independently pending that rule.
No actual CP1B, CP5, rendering/native or provider acceptance is claimed.

## Initial test readiness / RED request

Initial source-only test file SHA256
`ad92e71151eb4a9091837081d9160fa0571ac630697f0700b9534e41bbf827d6`,17 test
functions; AST parsed successfully. Tests cover exact API/schema/setup boundaries
from the frozen lease/oracle and literal new-run/source fixtures; no full financial
fixture, pager simulation or seeded owner artifact. Module import is delayed behind
an explicit missing-feature assertion. Production module remains absent.

Request one minimal missing-feature RED:
`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_earnings_workflow.py -k public_api`.
This selection should execute one API test, not financial/owner participation.
Full GREEN/actual owner remains dependent on accepted integrated projection code.

Fresh10:26:11.016841UTC local preflight: all144 baseline pins unchanged;
sorted/indented baseline inventory SHA256
`90445d4f14b87a39c9fa97e4b1d4ab4760c65d7fd194561ffa54133fd12eefa1`;
runtime SHA256 `7c72112b685250b1aec69081696d8fc04040ccefc34505ca56ac48ace7da8d5b`;
load2.2119140625/2.4501953125/2.3330078125; no other matching Python/static jobs.
`work/cp1b-owner-b1/red-request-preflight.json` retains this request record.
Test-only confidence review checked delayed imports, independent schema/oracle
expectations, fresh source/run fixtures and no publication/old-run leakage.
No runtime collection/pass count or implementation completion is claimed.

## Central RED and resumed implementation

LEAD centrally ran `C3-CP1B-B1-RED-1`, PID96442,
2026-10-27T10:33:47.921132Z..10:33:48.184993Z, exit1; one named missing-feature
assertion failed after successful collection,73 deselected in0.13s. No financial
engine or owner/pager behavior was evaluated. All144 baseline/test/runtime pins
unchanged; production still absent. Root read actual records/log:
`work/cp1b-owner-b1/lead-red-1-record.json` and `lead-red-1.log`, log SHA256
`0c5e4461e516a69a43efcadf4fc933e8e9574984d9f0382832cc78103a3807fd`.
Freeze/slot released; Sol/high nontransport implementation resumed immediately.

LEAD resolved the earlier transport ambiguity without changing the public TextIO
signature: trusted fresh buffer-backed TextIOWrapper endpoints only; operate
exclusively on binary buffers; preserve LF/CRLF and exact consumed frame bytes
before strict UTF8 decoding. Reject StringIO/nonbuffered setup before consumption
or mutation. Limit read toMAX_LINE+1; persist invalid EOF partial bytes or exact
oversized consumed prefix and stop without draining; empty EOF is not successful
close. Responses use UTF8 bytes plus LF through writer.buffer. The same independent
reviewer is freezing the exact clarification/raw-transport oracle; that subpiece
awaits those pins, while all other implementation continues. No old source/value/
owner receipt/schema pin is silently changed.

LEAD also confirmed an early durable-setup seam: before any submission, existing
records lacked participant/transport authority required for reopen authentication.
The same-review supplement will add exactly one strict OwnerSetup record and
AuditEntry kind setup, persisted after genuine empty Execution S0 and BEFORE CP0
begin. It binds Run/pack/S0/case/pins/participant/transport and the frozen transport
oracle policy hash. Final inventory includes exactly that immutable typed file;
no private setup sidecar or new top-level owner receipt/OwnerPins field. Reopen
must authenticate setup/caller/current ancestry before mutation and handle only
the explicitly authorized S0/bootstrap-begin crash window. Code/tests for this
addition await the exact supplement pins; independent owner composition proceeds.

## Safely integrated bootstrap/raw supplement

LEAD subsequently admitted `C3-CP1B-B1-BOOTSTRAP-RAW-SUPPLEMENT-1`. Worker paused
writes; root fast-forwarded4e2bce9 to exact PM base
`7adb6167502a71fcb83991f04e67c714d691de59` without stash/reset/replacement.
All three owned WIP hashes stayed identical across that update:
source900803b84bead59542886596505c6a1494464372f66fcb26a32f985b55b9e140,
testsad92e71151eb4a9091837081d9160fa0571ac630697f0700b9534e41bbf827d6,
handoffaf2d8c8a3a5e5c458de416ec1d60d3163d733636defddd09927a68b3c0d91872.
All147 unowned baseline files match LEAD's bootstrap-raw-source-before.json;
proof is `work/cp1b-owner-b1/supplement-update.json`. No local runtime job occurred.

New committed supplement `docs/CP1B-RAW-TRANSPORT-ADDENDUM.md` SHA256
`4a6ddd6d348d2bd4e9a0b64532db8a4415018786cdafb4be788c74e2c088866d`,
policy oracle `cases/earnings/transport-expected.json` SHA256
`7fba44bc1cf2d2dd8b26ed941c28b04371ce29f1875f070f48dc6d12b7efa8d6`
and same-review continuation SHA256
`a8b7d34d956d16db59bcbd8aa3244abdfa78469fb50c8f52a31f33d59cc200f9`
were read and rehashed. Original owner/source pins remain unchanged. Worker
resumed immediately with setup/bootstrap/raw code and cases in the same two
owned files; no sidecar, new code file or top-level owner receipt/OwnerPins field.
Full GREEN/actual owner still requires accepted C1 projection integration.

LEAD confirmed a further nested association seam before completion: a refused
owner submission without participation/read/call activity must still bind its
actual active owner session, so later reads cannot repair the earlier refusal.
The same-review session supplement will add host-filled
`BoundSubmission.owner_session_id:Identifier|None` immediately after
participation_sha256: foundation None, owner the real persisted current session.
It must agree with any participation session; only captured prefix reads/calls
in that session may receive credit. No top-level receipt/OwnerPins/OwnerSetup/raw
policy change or actor review field. Exact field implementation/tests await
that forthcoming frozen pair; all other source/setup/raw/owner work continues.

Further admitted dependency updates were performed under one brief write pause:
7adb616→de9cd038781c1a3dce020db2139d4874a4ef8885 (exact session supplement),
then→cf5115bea38a0a953519b2be5755c0209329c6a4 (accepted C1 projection code).
All three owned WIP files were byte-identical across both updates; all149
unowned baseline and contract pins matched. Proofs:
`work/cp1b-owner-b1/session-supplement-update.json`, `pager-dependency-update.json`.
Accepted upstream SHA256 ac7ac2e121faf7a3adda6eab385b8f194d29549979c334b276199b624e0332f7;
tests a647782f2e23241e843a526d0c558d278aeccac971683835f9cc560b2706bd3b.
No stubs, copied WIP, reset, stash or duplicate runtime.

Initial implemented schemas/setup/source-replay/raw/session-field component scope
was centrally exercised as `C3-B1-EARLY-COMPONENT-1`: PID5520,
11:17:05.226471–11:17:06.485775UTC, exit0,111 passed in1.06s. All151 source/test/
case/owned pins and runtime unchanged; log SHA256
`4e86e36504d0c8434a0ad30122f5d9d811a24d27018ef4a012fb4bcbc8755f55`.
Root read actual `lead-early-component-1-record.json/.log` before using this result.
It does NOT prove full owner settlement,17 real session sequences, receipt,
CP5 descendant or recovery behavior. Those tests/cases remain in progress.

Independent static reviews of the exact bb0acaf/5b51cb early source/test snapshots
are in `work/cp1b-owner-b1/foundation-sensitive-review.md` (no material finding)
and `owner-state-sensitive-review.md` (P2 post-refusal reopened host loses live
upstream session; P3 known core-blob validation errors escape typed identity
boundary). These are investigated with causal checks/fixes before closure;
no reviewer ran imports/tests/jobs or asserted analytical qualification.

LEAD separately confirmed the original known numeric-chip claim strings fail
adopted prose/candidate validation even for zero. After another WIP-preserving
pause, C3 fast-forwarded cf5115→f3b9b371d0a24528f63474fc3c70a245ed196dbf;
all149 unowned pins and three owned WIP hashes stayed correct. Proof:
`work/cp1b-owner-b1/native-reference-update.json`. Current owner oracle is now
`a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d`;
claim addendum3341de531ec2d20ebac3c30bb3a753c2fc00e60b2fdaa95ef065e6c774160bcf,
same-review8d48c5060b813df59cad38fc3eee6447934e5d2bcb5438ba647e754ea87ac2ed.
Only six positive and two gap-current monetary refs become same-ID MILLIONS
figures; three nonknown gap refs remain chips. Values/counts/lineages/citations/
limits/APIs are unchanged; new OwnerPins/OwnerSetup use current oracle bytes.
Original e66/c8 authority remains historical for unchanged rules, raw7fba/session
7c policies unchanged. Old temporary/component evidence is not relabelled.


## First full-foundation causal prerequisite run

Central admission `C3-B1-CAUSAL-RED-1`, PID12679,
2026-10-27 11:42:31.209073–11:42:44.373293UTC, exit1,
three setup errors in12.96s. Root read real record/log and retained journal:
actual fresh CP0 plus CP1 source_context,financials,narrative advanced; the
new downstream readiness helper supplied nested prose arrays where the public
DownstreamReview rationale/actions require strings. This fixture failure occurs
BEFORE P2/P3, so it proves neither causal regression. No force-valid/core/oracle
change is authorized. All152 source/test/case/owned pins and runtime plus fixed
backup remained unchanged. Log SHA256
98470cefd25085e2850c172a2c6bdc42477a7072418878a0396c4ceacf266583.
Root preserved all66 failed-store files byte-identically under
`work/cp1b-owner-b1/causal-red-1-prerequisite-store` with inventory.
LEAD released freeze/slot; test fixture correction and remaining causal test
materialization resume, with pre-fix product retained for another separately
admitted causal job. No automatic retry or unadmitted runtime occurred.

Required post-edit tournament considered _owner_session_proof and
_complete_intent; impact set/callers read via rg (no GitNexus). Distinct Sol/high
incumbent,speed,memory,readability and blind-arbiter roles ran static-only,
maximum three active including implementation worker. SpeedA won first bracket
but root rejected it after two real full-module mypy errors (tuple(ids) loses
string narrowing); corrected MYPYPATH separated import-path diagnostics from
candidate errors. Blind surviving bracket BvsC→BvsD chose memoryB: ownerproof
unchanged and only two step/repair matching scans avoid expanded tuples.
B full-source candidate mypy/Ruff passed. Product application, backup and focused
runtime verification remain pending causal reproduction; static ranking alone
is not tournament completion. Reports/candidates remain under
`work/cp1b-owner-b1/tournament`. Root confidence ledger ranks12 uncertainties and
preserves static/runtime distinctions; full exact-source closure is pending.
