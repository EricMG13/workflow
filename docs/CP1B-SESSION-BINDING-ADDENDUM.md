# B1 addendum — explicit owner session on every bound submission

This is one field/association clarification in the SAME B1 state-review continuation, based on LEAD's explicit ruling from the implementation's refusal-epoch gap. It grants no new product/job ownership or financial authority. Other C3 work continues. Original B1 lease SHA256 `e66aa2df765ff76c2fe9644ba2f5c003dc65572ad6060246538265171bc54071` and owner oracle `c8af02d3760f0ac24a8ecd2e2e6d2f3be38f260c706d200995b12c0f3d37456d` remain immutable. Independent state expectations: [session-binding-expected.json](../cases/earnings/session-binding-expected.json).

Only BoundSubmission's new required nullable field and its verifier association override the original B1 declaration. Public owner APIs, top-level EarningsOwnerReceipt, OwnerPins, OwnerSetup, raw transport policy `7fba44bc1cf2d2dd8b26ed941c28b04371ce29f1875f070f48dc6d12b7efa8d6`, actor EarningsDeltaReview and all financial/source/core oracles remain unchanged. A4 imports the actual B1 typed receipt/verifier; there is no new A4 public/type boundary, runtime service or approval chain.

## Confirmed gap

A legitimate sequence is: session S1 completes its actual reads; open before retained step and with no unresolved intent creates fresh S2; an actor submits before any S2 bootstrap/call and is refused; S2 later completes its own reads and a later submission settles. Both sessions may have exactly the same OwnerBinding, normalized grant G and manifest M. The earlier refused BoundSubmission has participation_sha256=None, so the old record did not identify S2. Selecting a final/latest complete session, an earlier complete session or later calls cannot reconstruct which empty epoch the refusal observed.

## Exact schema change

Retain BoundSubmission schema_version `cp1b-bound-submission/1` and every existing field/type/order, adding HOST-FILLED `owner_session_id: Identifier | None` immediately AFTER `participation_sha256`. The field is required even when null; there is no missing-field/default/legacy inference fallback. Its exact order is:

schema_version, binding, raw_payload_sha256, stored_payload_sha256, canonical_review_sha256, call_ids, successful_call_ids, source_evidence, input_read_hashes, participation_sha256, **owner_session_id**, normalization_paths, prefilled_paths, prefilled_kinds.

- Foundation CP0/CP1 bindings MUST set owner_session_id=None. A nonnull session reference on a foundation record is invalid.
- Every earnings_delta OwnerBinding MUST name the current actual successfully persisted OwnerSession.session_id, even with no bootstrap read, no call, malformed actor review or no complete participation. Do not derive it from the first read, most recently complete session, participation success or actor payload.
- Actor EarningsDeltaReview gains no field. Any actor-supplied owner_session_id remains an extra-key/bad_arguments refusal under the existing review schema.
- No successfully persisted current OwnerSession means no qualified owner binding/submission operation can be constructed. Refuse/preserve the actual setup/begin/factory failure under existing rules; do not invent a future session ID, fake OwnerSession or owner record with null pointer. Existing raw transport capture/failure evidence may remain; no journal step or candidate is credited.

The host selects/persists its actual OwnerSession before review/participation checks and fills this pointer before retaining BoundSubmission/SubmissionIntent. Existing immutable record hashes therefore commit the selected session for refusals as well as successful submissions; no new candidate own-input tail or top-level receipt field is needed.

## Resolve authority, then restrict to the captured prefix

For an owner BoundSubmission, resolve owner_session_id to EXACTLY ONE retained actual OwnerSession in the authenticated receipt/audit. Verify its strict record/hash/inventory identity, full OwnerBinding, ticket/attempt and historical current upstream inputs/statuses/bytes. Recompute its normalized grant G and access-manifest M and bind every qualifying selected read/call to that same session and G/M. A missing/duplicate/foreign/tampered/mismatched session is identity_mismatch; existing stale-binding/currentness categories otherwise retain their meanings. A pointer is an explicit host association, not an actor choice or a timestamp inferred from final receipt state.

Preserve the original full ticket/binding call/read prefix for forensics and its exact ordering/all-successes accounting. For participation credit, intersect ONLY that captured prefix with the explicitly selected session. Inspect OwnerToolCall.session_id and OwnerAccessRead.session_id; equal OwnerBinding/G/M/header contents across two sessions are insufficient. Qualifying call IDs must be in BoundSubmission.call_ids (and actual successes where required), not merely somewhere in final owner_calls.

input_read_hashes resolve actual whole typed read records in the captured prefix. For owner reads that means T(OwnerAccessRead), including session_id/sequence/binding/access_manifest_json, NOT a shared access_manifest_json/body digest. If the existing field is interpreted as body-only hashes, the pointer is insufficient: later S2 bootstrap can share S1's body digest and incorrectly appear captured. This addendum makes the existing typed-record-hash/prefix interpretation explicit; do not add a new field or alias a body hash to a later read. Foundation read prefix rules remain unchanged.

When participation_sha256 is present, resolve the exact existing EarningsParticipation and require its session_id equal owner_session_id, with identical binding/G/M. Its access_read_sha256 must resolve the selected-session whole read record inside the captured input_read_hashes; every coverage-specific page/citation ID must be inside the captured successful selected-session calls. Original EarningsParticipation.call_ids/successful_call_ids may retain the full cross-session prefix as already required, but coverage lists never pool sessions. Both complete manifest/projection traversals, all granted values/attributes and citation checks must be observed in the selected captured epoch under the existing contract.

When participation_sha256 is None, the session pointer is STILL mandatory. Evaluate the recorded shape/participation refusal only from that selected session's captured read/call prefix. The earlier S2-empty refusal remains participation_incomplete with unchanged snapshot and no step/candidate/result even if S1 was complete and S2 later becomes complete. A later well-formed submission can qualify with a NEW captured prefix containing actual complete S2 evidence; it does not upgrade the earlier intent.

The verifier must never use final session completeness/latest calls, equal manifest body hashes, the latest global OwnerSession.index, or successful later participation to retroactively credit an earlier intent. The persisted pointer plus captured record hashes supply the association. Cryptographic artifact checks and actual host/session creation rules remain necessary; this is not a claim that the pointer independently proves wall-clock ordering.

## Reopen, pending intent and refusal semantics

Original recovery rules remain: with no unresolved intent/retained owner step, a reopen starts a new actual session, preserves previous evidence/counters and requires new full chosen-session reads. A resolved refusal can be followed by more reads in the same still-active process/session; another reopen instead creates its actual next session. No old cursor/read transfers.

An unresolved persisted intent freezes its owner_session_id, raw bytes, selected prefix and envelope/proof state. Open does NOT create a replacement session before resolving it. Revalidate/rederive the exact refusal or retained-step outcome at that captured prefix; no new calls may repair historical participation. Once a valid envelope/step is retained, exact existing session/proof/payload resume and one settlement apply; never relabel the intent to a new session. Conflict/tamper refuses rather than losing the earlier intent or invoking finish twice.

Live absence of active session refuses existing not_permitted/capability handling before a qualified owner record; a persisted owner BoundSubmission with missing/null/unknown/ambiguous/mismatched pointer fails identity_mismatch. A real persisted session with insufficient selected prefix refuses participation_incomplete before a journal step, as before. Well-shaped incorrect analytical selections still take original retained core invalid/repair semantics; this change is not a new accounting gate.

## Completion and qualification boundary

The frozen oracle names the exact S1-complete/S2-empty-refusal/later-S2-complete sequence, before/after reopen, unresolved and retained intent, raw-shape refusal, missing setup, foundation nullness, actor injection, duplicate/foreign IDs, body-digest alias and tampered pointer/prefix cases. They are independent state-graph expectations, not fabricated analytical outputs or canned completion flags. Implementation checks must use real retained sessions/records and the existing source oracles; no developer lookup or symbolic fixture counts as owner acceptance.

No source values, delta/growth arithmetic,44-fact/12-lineage/one-claim composition, currentness/grant policy, source permissions, one-heavy-job limits or paid/provider pause changes. The owner verifier enforces this nested field inside the actual typed owner receipt; A4's exact public import/composition remains sufficient. Later implementation remains under the existing confidence-review/rewrite-tournament and sensitive review. This static continuation performs no product imports/tests/engines/providers.

Not verified: Product field capture, actual refusal/reopen/retained-step recovery, tamper enforcement, owner/CP5 execution or rendered/native delivery.
