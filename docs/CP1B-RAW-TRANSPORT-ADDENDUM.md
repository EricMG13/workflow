# B1 addendum — immutable bootstrap and exact raw-byte transport

This is one bounded pre-code clarification in the same B1 state/transport review. It supersedes only the raw TextIO/byte ambiguity and the missing durable early-setup authority needed by the already required open identity/mode check. It grants no new implementation ownership, product job or financial authority. C3's already authorized nontransport work may continue; raw transport code/checks consume this exact freeze under LEAD's existing admission process.

The original [CP1B-OWNER-LEASE.md](CP1B-OWNER-LEASE.md) remains immutable at SHA256 `e66aa2df765ff76c2fe9644ba2f5c003dc65572ad6060246538265171bc54071`; owner oracle remains `c8af02d3760f0ac24a8ecd2e2e6d2f3be38f260c706d200995b12c0f3d37456d`; descriptor remains `60ed95782648064db7806bb7f0714fe030f9563424df50e17500803a2edfb7ec`. Frozen raw transport expectations are [transport-expected.json](../cases/earnings/transport-expected.json). All source/numeric oracles, OwnerPins fields, top-level owner-prefix receipt fields, A4 boundaries, permissions and limits are unchanged. The only schema addition is strict OwnerSetup plus AuditEntry.kind=setup, specified below. No financial re-audit, code import or new approval chain.

## Immutable early setup authority

The original open contract requires the same participant/transport before calls. A nonterminal store previously had no declared durable authority carrying them. Add exactly one strict frozen Contract in the existing earnings_workflow module, with all fields required except the stated schema literal default, extras forbidden, and this serialization order:

- OwnerSetup: schema_version:Literal['cp1b-owner-setup/1']='cp1b-owner-setup/1'; run:Run; pack_sha256:Hash; initial_snapshot_sha256:Hash; case_id:OwnerCaseId; pins:OwnerPins; participant:Text; transport:Transport; policy_sha256:Hash.

policy_sha256 binds the SHA256 of authoritative frozen raw cases/earnings/transport-expected.json bytes. Its exact final hash is published externally in this review/LEAD admission; the oracle contains no own hash. Existing trusted case/oracle resolution and admitted code must check that authoritative freeze, never actor-selected policy bytes or a mutable self-declared hash. Do not add a public path argument, extra OwnerPins field or unlisted sidecar for it.

Extend AuditEntry.kind only with `setup`. Store EXACTLY ONE canonical model_dump_json UTF-8 OwnerSetup at `earnings-owner-audit/setup/<T(OwnerSetup)>`, with the existing write-once/atomic persistence rules, no extension. Filename, typed content hash and canonical file bytes must agree. Include exactly that setup AuditEntry in final audit_inventory. Do not add a top-level EarningsOwnerReceipt field or fake future OwnerSession to carry this authority.

Creation order: validate trusted case/pins/arguments/policy; call genuine Execution.create, yielding S0; authenticate S0.parent=None, empty heads/attempts and same Run/pack; persist unique setup BEFORE begin(CP-0); then actual CP0 begin and actual first BeginRecord. If setup persistence fails or leaves a partial create, no CP0 begin is authorized. Preserve forensic files. Missing setup on later open fails closed; do not manufacture authority or silently migrate an old store.

Open authenticates exactly one setup file, strict type/canonical bytes/hash, expected case/pins/policy, genuine S0 and same-Run/pack ancestry through the current store; then compares caller participant and transport with the frozen values BEFORE any workflow operation, projection, call or begin. Missing/extra/tampered/mismatched setup, identity, mode, pins, policy or ancestry is identity_mismatch. The frozen identity/mode cannot reset counters or become a new run on reopen. This applies equally to python-api and bounded-json-lines/1.

Matching open at still-current S0 may perform the real CP0 begin and log its actual first BeginRecord. A crash after the real first begin but before its log has one narrow existing-audit recovery exception: authenticate exact direct S0→S1 parent linkage, unchanged Run/pack, no heads, exactly one actual pending CP0 attempt0 with exact current_inputs and its real ticket; no retained step/payload/result/issues or analytical action. Rederive ONLY the first BeginRecord using those genuine before/after/ticket/attempt identities. Do not begin again or infer source/analytical call credit. Any other missing-log state uses original strict recovery or refuses; no general bootstrap/replay infrastructure is introduced.

The public owner verifier requires this unique setup entry, crosschecks run/pack/case/pins/participant/transport against the receipt and initial ancestor, and validates the same policy authority. Final owner-prefix/final-slice semantics otherwise remain unchanged. A4 imports the actual B1 receipt/verifier; this additional existing-owner inventory kind requires no A4 top-level field or new type boundary. All prior audit/message/record/receipt limits remain in force; required first-case counts have ample capacity for this one additional setup record.

## Public signature and trusted setup

Preserve exactly:

`serve_json_lines(workflow:EarningsWorkflow, reader:TextIO, writer:TextIO, *, destination:Path) -> None`

For transport `bounded-json-lines/1`, trusted setup supplies fresh, unused standard-library `io.TextIOWrapper` objects with open binary `.buffer` streams: reader buffer is readable; writer buffer is writable. Reject StringIO, nonbuffer text objects, non-TextIOWrapper objects, closed buffers or wrong-direction streams with `bad_arguments` before consuming input or mutating workflow/audit. This is a runtime restriction of the existing TextIO signature, not a new public reader class/import or receipt schema.

After setup validation, use only the underlying binary buffers for I/O. Never invoke the text wrappers' readline/read/write, implicit decoder or newline translation. Reader/writer text encoding, errors and newline settings cannot change transport bytes because those text facilities are unused. Freshness is a trusted caller precondition; do not claim public TextIO state proves that no text method previously prefetched/decoded data. Supply fresh unused wrappers again on a later dispatcher invocation; keep all existing durable workflow counters/history.

The Python API transport is unaffected. Paths/destination stay trusted setup, never actor fields. No new stream/session identifier, importable custom reader, general runtime, automatic redelivery or additional actor operation is introduced. OwnerSetup above records existing workflow identity; it is not a reader/session class or actor operation.

## Bounded framing and exact capture

Keep `MAX_LINE=4194304` and `MAX_MESSAGES=2048`. MAX_LINE counts raw bytes of an admitted complete frame INCLUDING its LF terminator and any preceding CR. Before reading another frame, enforce the original durable message budget; exhaustion is `transport_limit` and does not permit a message2049 or a reset on reopen.

Perform one bounded `reader.buffer.readline(MAX_LINE + 1)` for the next frame. The bound applies to bytes returned/consumed by this binary buffer call; any bytes still buffered internally or remaining in the source are unread input, not handled frames. Do not call unbounded readline/read or drain a rejected suffix.

- Empty result is EOF with no frame: no TransportMessage, no refusal reply solely for EOF, no successful close or manufactured receipt. Preserve existing resumable audit.
- Nonempty result of at most MAX_LINE bytes ending LF is a complete frame. LF and CRLF are both permitted; retain their distinct exact bytes. Decode this frame separately using strict UTF-8, then apply existing finite JSON/type/exact-key operation validation. Do not strip/recreate a terminator, use replacement/ignore decoding, or re-encode decoded text as the captured request.
- Nonempty result of at most MAX_LINE bytes without terminal LF is a partial EOF frame. Retain exactly the observed bytes as invalid, refuse `bad_arguments` if output succeeds, then stop. Never dispatch even if those bytes form an otherwise valid JSON object.
- Result of MAX_LINE+1 bytes is oversized. Retain exactly that consumed bounded prefix as invalid, refuse `transport_limit` if output succeeds, then TERMINATE this dispatcher invocation. Do not drain, inspect, process or dispatch the unread suffix or any following control frame. This remains invalid even if the prefix happens to end LF or splits a UTF-8 sequence. Never claim the whole oversized logical line was retained. MAX_LINE+1 is only bounded forensic capture proving overflow, not a relaxed accepted-message limit.

For each nonempty observed frame/prefix, persist exact raw bytes in the existing audit payload namespace under SHA256 of those bytes and retain the existing `TransportMessage(index, operation, request_sha256)` BEFORE any product dispatch/action. Parsing/classifying the recognized operation may precede metadata construction when needed, but it may not perform the operation. A failed payload or metadata write cannot dispatch or return success.

A structurally valid recognized operation uses its existing operation enum. Non-UTF8, malformed/nonfinite JSON, wrong types or extra/missing keys use operation `invalid` and refuse `bad_arguments`; an unknown operation uses `invalid` and refuses `not_permitted`. A complete invalid frame may be followed by another separately retained frame within the existing budget. Partial EOF and overflow always stop. No invalid frame earns analytical read/selection/settlement evidence.

## Original operations and binary replies

Only existing operations state, invoke, read_inputs, submit_review and close, with their frozen exact key sets, remain supported. Recognized transport syntax is not a valid analytical review: for example a UTF-8 payload string may still fail the existing product schema. Only the existing method and validators decide its outcome.

Keep existing reply objects: successful delivery `{status:ok,result:...}` and refusal `{status:refused,error_code:...}`. Serialize the existing JSON reply using strict UTF-8, append one LF, and write/flush via `writer.buffer` exclusively. Do not use writer text encoding/newline settings, emit CRLF through text translation, expose trusted full receipts/stages to CP1B, or add output schema fields. The oracle's compact sample reply is a byte-level buffer example; it does not introduce a new JSON key-order/insignificant-whitespace canon beyond existing reply object shapes.

A short/None binary write or write/flush exception is visible I/O failure, not successful complete reply delivery. Do not loop/drain unrelated input or continue dispatch to conceal it. A `close` frame is retained before the existing terminal write_receipt/OwnerClose operation; EOF/invalid/oversized input never synthesizes close. The digest-only OwnerClose remains unchanged.

## Audit verification, failures and recovery

TransportMessage.request_sha256 resolves RAW BYTES and may point to invalid UTF-8 or an oversized captured prefix. The public owner verifier must read these forensic payloads with read_bytes, hash/classify them under this rule and match exact metadata/index/order. Do not run raw framing blobs through a UTF-8-only journal JSON loader or mistake them for a retained analytical submission. Other B1 typed review/envelope/journal payload contracts remain unchanged.

The existing payload kind stores these raw bytes without a new receipt field; only the setup kind is added for early authority above. Each captured frame adds its actual existing records and consumes the original durable budget. Raw request hash authenticates capture, not successful method execution, analytical evidence or output delivery. Existing submission intents/outcomes and genuine journal transitions establish product effects independently.

Unexpected read/I/O/retention/programming failures stay visible under B1's existing policy. Before raw bytes and TransportMessage are durable, no dispatch occurs. If payload bytes were written but metadata retention failed, preserve that evidence; do not invent metadata or silently erase an orphan to pass the inventory. Existing recovery must uniquely validate/recover what it already permits or refuse closure; this addendum promises no new automatic repair algorithm.

If output fails AFTER a real action/journal transition, preserve the exact input record and real intent/outcome/transition. Do not claim rollback, return complete-response success, erase a valid transition or blindly repeat dispatch to replace a lost reply. Reopen and pending/retained-step resumption use the original B1 recovery/one-settlement rules. An interrupted reply does not authorize a new actor source grant or code path.

This unchanged receipt schema records frames and workflow lineage, not dispatcher-invocation IDs, external stream freshness, unread external suffix bytes or successful reply-delivery acknowledgments. Portable verification must not claim those absent facts. Fresh wrappers and stop/no-drain behavior are direct dispatcher requirements checked by the bounded BytesIO component cases; no new schema/runtime is invented to imply stronger evidence. A later explicit invocation can resume the workflow with fresh wrappers and the original durable counters, without automatic replay of old raw frames.

## Frozen evidence and implementation boundary

The oracle uses exact small byte literals and explicit repeated-byte chunks for boundary-sized inputs, with full input/consumed-prefix/unread-suffix lengths and SHA256 values. Cases cover LF/CRLF distinction, Unicode, invalid UTF-8/JSON/nonfinite/extra arguments, complete-invalid then valid control, exact MAX_LINE including terminators, oversized bounded prefix with an unread later control, empty/partial/bare-CR EOF, setup refusal, retention/read/write failures and terminal close. Failure cases are required implementation expectations, not claims that product failures were exercised here.

The source/state review traced Execution.create/current_inputs/begin and the B1/A4 declared types statically, and checked the raw-byte ruling using only standard-library BytesIO/TextIOWrapper and JSON/hash byte observations. Text readline under universal-newline mode changes CRLF; direct buffer readline preserves it, and direct buffer writes bypass text newline/encoding. No product import, test suite, engine/provider/browser or heavy job ran. Later implementation remains subject to the same confidence-review, changed-function rewrite-tournament, source/job admission and sensitive checks; this is the same B1 review continuation.

Not verified: Product setup/bootstrap/transport/audit/error/recovery implementation, focused tests, actual owner or CP5 participation, reply delivery or native rendering.
