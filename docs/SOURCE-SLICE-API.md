# Source slice producer/renderer interface — frozen v1

Frozen from C1 typed handoff SHA256 ae9802b45bb18aacb4a6c0e22d4a3051b4a41261b33239e98e391788d4b49279.
Shared field spellings are stable before parallel producer/renderer implementation.
Producer code review and real-run proof remain required; this document is not execution evidence.


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

