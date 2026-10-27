# Task4-A2 — CP1B registration and current-CP1 access lease

## Authority, base and exact ownership

The active goal remains the full PLAN.md. A2 is one prerequisite implementation slice, not CP1B/checkpoint acceptance. The user added C3 and uncapped active implementation; exact disjoint ownership, one-heavy-job admission, independent sensitive review and paused paid/provider/live tests remain. Reuse C3's independent financial conclusions and the frozen A1 oracle; no new source values or financial policy is introduced here.

Source-lineage/implementation starting main: `2463dcb6776404e0bafe6c9b30a25c699db288d4`. C1 preparation: commit08fd113, `coordinator-1/docs/handoffs/cp1b-access-registration.md`. PM integrates this exact reviewed contract/oracle first; LEAD admission names the resulting exact checkout commit. C1 creates a fresh branch there, preserving preparation and previous work. No product writes before admission.

C1 owns exactly these five tracked implementation/test files:

1. `src/deploy_vii/registry.py` — only the CP1B chain described below.
2. `src/deploy_vii/methodology.json` — only CP1B.table_ids.
3. `src/deploy_workflow/tools/upstream.py` — narrowly versioned CP1B/current-CP1 access.
4. NEW `tests/test_cp1b_registration.py`.
5. `tests/test_upstream_tools.py` — targeted additions, existing v1 cases retained.

No CP5 v2/multi-producer/integrity-scope bridge, live/submission/context/prompt, source/Execution/host, earnings core/workflow, FP02/binding/render, Model, __init__, case or other tracked file is leased. Required nonproduct logs/reviews go only in the subsequently admitted C1 work directory; return the exact commit/handoff through coordination. LEAD owns cases/contract/PLAN/QUEUE/TEAM; PM alone integrates and records imported-file patch provenance. C1/C2/C3 are not alone and must preserve others' edits.

## Registration-only changes

Add `StepChain(module_id="CP-1B", cell="cp1b", steps=("earnings_delta",))` with every optional set/mapping empty: no repairable step, prefill, prior-step projection, pack source/read/extract, one_shot or part-submit. Derived registry maps/routes must follow this single chain; do not add duplicate dispatch maps. Existing CP2/CP5 and all other chains retain their meanings. Registration does not implement a live submission schema or supported owner execution.

Change only the CP1B methodology record's table_ids to exactly `["T1B.1","T1B.2","T1B.3"]`. Its module_id/title/aliases/purpose/required CP0+CP1/optional edges and every other metadata record remain unchanged. CP5's existing dependency/fan-in logic remains unchanged and unqualified for the new actual consumer chain until A4.

## Supported A2 public surface and versions

Preserve `UpstreamTools.from_execution(store, ticket_id, step_id, *, grants)` and `invoke(tool_name, arguments)` and detached tool-receipt/1 shape. Existing unversioned v1 CP2/CP5 grants, lookup, citation verification and narrow CP5 integrity behavior/tests are unchanged. Never reinterpret v1 Cartesian allowlists as CP1B authority. CP1B supports only v2 below and only at earnings_delta; CP2/CP5 cannot use v2 in A2.

For v2 only, add detached, bounded `session.access_manifest` bootstrap metadata and `invoke("read_access_manifest", arguments)`. A v1 session's access_manifest/read_access_manifest is not_permitted. Preserve lookup_upstream/verify_upstream argument key sets; no caller argument may supply or widen grants. This is read-only access, not durable receipt storage, analyst submission or settlement. Later owner transport must retain actual calls; bootstrap inspection alone is not analyst-tool acceptance.

## Exact trusted v2 grant

Factory grants are a JSON-compatible mapping with exactly:

```
{
  "schema_version": "cp1b-upstream-grant/2",
  "consumer_module_id": "CP-1B",
  "step_id": "earnings_delta",
  "producers": [{
    "module_id": "CP-1",
    "sha256": "<exact current bound CP1 result SHA256>",
    "coordinates": [
      {"fact_id":"...", "table_id":"...", "row_id":"...", "field":"..."}
    ],
    "projected_fields": ["..."]
  }],
  "raw_source_ids": []
}
```

There is exactly one producer entry, CP1; no claim grants, raw_source_ids, integrity_internal_inspection or extra keys. Every coordinate has exactly the four shown nonempty string keys, and belongs as a complete tuple to that same authenticated producer/hash. Reject duplicate tuples, duplicate fact IDs or conflicting selected coordinates. Limit trusted coordinate count to100000, as a setup bound, not a response-size exemption. No Cartesian product of separately granted rows/fields/fact IDs and no cross-producer pooling is allowed.

Allowed projection attributes are exactly: fact_id, label, table_id, row_id, field, amount, text, status, unit, currency, scale, period, basis, denominator, limitation, calculation_id, value_class, calculation_status, citation_handles. The grant must include the sixteen except denominator/value_class/calculation_status; it may additionally include any of those three. This lets the full authorized period index actually be read. Tool calls still request at most16 attributes. `fields` means these output attributes; a coordinate's `field` is a different identity and grants no projection attribute.

The coordinate universe is: ALL actual facts of the nonempty canonical T4.14 period index, plus a trusted-selected subset of T4.10 facts belonging to the twelve A1 measure rows (revenue, ebitda, adjusted_ebitda, ebitda_margin, cfo_reported, capex, fcf, cash_closing, total_debt, net_debt, total_leverage_reported, net_leverage_reported). Grant only selected reported QUARTER/FY historical-basis value coordinates and their required metric-name/category/identity companions in those rows; no trend/analyst-note, rolling-value or other-table coordinates. Resolve row identity from the canonical T4.10 field_1 (Metric Name) text fact; field_0 is KPI Category. Select value facts by their exact historical ModelBasis field. Resolve selected historical basis from exact T4.14 identities/adopted length-prefixed basis construction, never labels/equal dates/values. The trusted setup selects the pair; A2 performs no new accounting. An unknown/ambiguous row or basis cannot widen authority.

Factory validates that the grant contains every actual T4.14 coordinate, not merely every row's period_id field. Missing index table/rows, any omitted index coordinate, or missing required projection attributes refuses not_permitted before metadata disclosure. Additional grant coordinates outside the stated universe refuse not_permitted. A malformed/duplicate current producer identity is identity_mismatch. These checks do not turn a partial projection into a complete producer object.

Normalize validated grants only for hashing: coordinate tuples sort by(table_id,row_id,field,fact_id), projected_fields sort lexically; no duplicates are silently discarded. Preserve exact strings and the one producer identity/hash. `grant_sha256` is SHA256 of compact canonical UTF-8 JSON of the normalized entire grant, using ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False. No secrets or credentials are needed.

## Authentication and currentness

Reuse existing Execution/current_inputs/dependency/CP0 authorization semantics. The consumer ticket must be the current pending CP1B attempt, exact earnings_delta chain, no retained step/repair/payload. Validate every scheduler-bound input, pack identity and current producer head/status/hash/run_id/issuer_id/as_of/method_version before access. CP1 must be the exact bound accepted/restricted head; a selected but unbound producer is not authority. CP0 may be inspected internally for authentication but is not an analyst-granted producer.

Freeze snapshot/attempt/grant and copied immutable authority at construction. Revalidate snapshot, executable attempt, selected input hashes/statuses, producer bytes and authorization before projection AND immediately before returning metadata/body or committing a cursor. A changed snapshot is stale_binding even if the interesting financial numbers are unchanged. Never follow a new current head within the session. An ended/interrupted/superseded old ticket or a ticket with a retained step/step repair/payload refuses new access. A fresh executable repair attempt permitted by the existing journal may be used with its actual number; do not invent a number0-only policy. Returned metadata/receipts and caller grant mutations cannot mutate session authority.

CP1B has no raw-pack/source tool permission. Trusted authentication/citation checks may inspect complete producer/source data internally; only the explicit projection and citation handles are returned. A later trusted C3 host may independently obtain the FULL authenticated current CP1 ModuleView for build_earnings_delta. Never create a partial ModuleView/facts tuple carrying the full producer artifact_sha256 and present it as authenticated full input. A2 returns no ModuleView and introduces no such construction API.

## Bootstrap and safely paginated manifest

`session.access_manifest` is a detached dict with exactly this header:

```
{
 "schema_version":"cp1b-access-manifest/1",
 "consumer":{"module_id":"CP-1B","step_id":"earnings_delta"},
 "producer":{"module_id":"CP-1","sha256":"H","status":"accepted|restricted"},
 "snapshot_sha256":"S", "ticket_id":"T", "attempt":0,
 "grant_sha256":"G", "manifest_sha256":"M",
 "period_index":{"table_id":"T4.14","authorized_complete":true,
                 "row_count":N,"coordinate_count":K},
 "coordinate_count":TOTAL,
 "projected_fields":["..."],
 "max_page_entries":20,"max_body_bytes":8192
}
```

attempt is the actual number, including1 when applicable, not hardcoded0. No values, source quotes, source paths, claims, full Module/Fact JSON or coordinate array is embedded in the header. Header compact canonical UTF-8 bytes must also fit8192. `authorized_complete` means the grant covers the actual full T4.14 index; it is NOT proof that the analyst read every page or period value.

The manifest's sorted coordinate list is exactly the normalized grant coordinates. `manifest_sha256` hashes canonical JSON `{"header": HEADER_WITHOUT_manifest_sha256, "coordinates": ALL_SORTED_COORDINATES}` using the same canonicalization above. This commits exact counts/completeness, binding and authority without returning an unbounded list.

read_access_manifest accepts exactly producer_module_id, producer_sha256, manifest_sha256, cursor, limit. Producer must be CP1/H, manifest must be M, first cursor null and integer limit1..20 (bool is not integer here). Each successful receipt body is:

```
{
 "producer":{"module_id":"CP-1","sha256":"H","status":"accepted|restricted"},
 "grant_sha256":"G", "manifest_sha256":"M", "coordinate_count":TOTAL,
 "offset":0, "entries":[{"fact_id":"...","table_id":"...","row_id":"...","field":"..."}],
 "next_cursor":"access-cursor:<64 lowercase hex>"|null, "complete":false|true
}
```

Return the largest nonempty contiguous prefix of remaining entries that fits the requested limit AND the existing8192-byte compact UTF-8 BODY ceiling, including all paging/header/cursor overhead. At most20 coordinate entries, no truncation of an entry/string. complete is true iff this page reaches TOTAL; next_cursor is then null. No empty advancing page is valid. If an indivisible entry/header cannot fit, refuse bad_arguments with null body. Do not enlarge limits or claim completion with omitted entries. Short-ID25-entry component fixture yields20 then5; longer UTF-8 entries may require more pages.

Cursors are opaque session-issued tokens bound to this session/attempt/snapshot/producer/grant/manifest and next offset. An implementation may hash a private session nonce plus these identities/position; no new credential system. Accept only issued current-session tokens; replay with the same issued token AND same valid arguments in the unchanged session is read-only and returns the same page, with a new receipt. A different valid limit may return a different bounded prefix from the same offset; completion is established by actual contiguous offsets, not request count. Foreign/old well-formed tokens refuse stale_binding; ill-shaped tokens refuse bad_arguments. Cursor advancement is staged and committed only after final currentness checks and successful response construction. Failures must not strand the writer lock or expose a provisional page/cursor.

The downstream host must establish contiguous successful traversal from offset0 through TOTAL and actual authorized period-value lookups before treating a requested prior period as absent. Permission failure, truncated/unfinished traversal, missing selected coordinate or body-limit refusal never means COMPARATIVE_NOT_SUPPLIED. Full T4.14 still distinguishes opening PERIOD_END2024 from FY2024 income. A2 does not emit a new financial gap verdict itself.

## Lookup, citation checking and bounds

lookup_upstream keeps exact arguments producer_module_id, producer_sha256, table_id, row_ids, fields. Require1..20 distinct rows,1..16 distinct projection attributes, the existing five identity attributes fact_id/table_id/row_id/field/status, and grant-authorized requested attributes. Return only complete-tuple-granted facts in each requested row, never Cartesian siblings. A row with no granted coordinate refuses not_permitted; mixed permitted/forbidden requests refuse atomically. Row order follows request order; facts sort by(field,fact_id). No numeric/status/limitation filtering: known0, missing/conflicting/not_applicable nulls and legitimate textual period metadata remain visible as actually granted.

v2 lookup body is producer metadata plus `projection:"granted_fact_projection"`, grant_sha256, manifest_sha256, table_id and rows:[{row_id,facts:[projected attribute dict]}]. Citation handles contain only source_id/source_sha256/locator; no Citation.quote or raw spans/diagnostic detail. The projection marker and full-producer metadata do not claim the projected facts themselves hash to H.

verify_upstream keeps exact arguments producer_module_id, producer_sha256, kind, fact_ids, with1..20 distinct tuple-granted fact IDs. CP1B supports kind="citations" only, using the existing read-only citation checks internally. Body is producer metadata, grant_sha256, manifest_sha256, kind, verdict valid|invalid, issue_count and issues:[{code:"fact_citation",fact_ids:[...]}]. Bad citations produce invalid with safe granted fact IDs, not a clean pass or quote prefix. CP1B kind="integrity" and every CP5 scope tool are not_permitted. Nothing changes existing v1 CP5 kind=integrity behavior.

All successful lookup/verify/page BODY values remain <=8192 compact UTF-8 bytes. The existing limit bounds body, not the outer receipt or trusted grant input. Existing row20/field16/fact-id20 limits remain. Oversized lookup/citation result refuses the WHOLE request with bad_arguments, no partial/truncated body or new evidence/cursor. Each operation remains single-writer; concurrent/reentrant invocation is not_permitted. Detached earlier successful receipts survive later refusal unchanged and sorted by sequence. source_evidence is always exactly read/extracted/surfaced/searched empty arrays, including internal verification successes.

## Frozen public refusal categories

Factory/property failures raise ValueError(category) with no private detail. Valid-JSON invocation failures produce tool-receipt/1 status refused, body null, error_code below, empty source_evidence; unexpected failures are status error/internal_error with null body. Preserve existing non-JSON/recursive argument behavior: early ValueError(bad_arguments), never deepcopy arbitrary hooks. Existing v1 semantics are not reclassified.

- bad_arguments: ill-shaped/extra/missing tool arguments, malformed hashes/cursors, duplicate/empty argument IDs, bool/out-of-range page limit, row/field/fact count excess, malformed/duplicate v2 grant shape, result-byte overflow.
- not_permitted: wrong consumer/step/tool/version; v1 CP1B or v2 CP2/CP5; extra producer, unbound producer or unauthorized coordinates/attributes; incomplete authorized period index; raw/quote/claim/integrity scope request; unavailable producer permission.
- identity_mismatch: validly formed wrong producer/manifest digest, wrong producer run/issuer/as_of/method/hash/status, forged/tampered current bytes or duplicate ambiguous current producer identities. Keep existing same-hash/wrong-bound-status handling.
- stale_binding: changed session snapshot/head/current inputs or nonexecutable attempt; well-formed cursor foreign to this current session/binding. A digest mismatch on an otherwise current invocation is identity_mismatch, not a false source absence.

Any refusal reveals no nongranted provisional values or quote text. No partial permission success, implicit grant extension or fabricated comparative is permitted.

## Independent component cases and qualification limits

`cases/earnings/access-expected.json` fixes schema/guards before implementation. Handwritten permission fixtures deliberately include known zero, a missing comparison, a hidden nongranted sibling, same-ID foreign producer and private quote sentinel. They are component evidence only; dynamic H/S/ticket/grant/manifest/cursor hashes bind actual fixture/current data during setup, not old accepted issuer evidence. Source-native financial semantics remain governed by unchanged A1/source oracles.

Require causal cases for registration/methodology isolation; exact tuple grants; complete versus omitted T4.14 index; pagination count/bytes/Unicode/cursor/currentness; known0 versus null/metadata; nongranted/foreign/stale/malformed/status/body-limit refusals; citation invalid sanitization; grant/receipt mutation and single-writer atomicity; all old CP2/CP5 v1 tests. A missing/blocked CP1 or unauthorizing CP0 must fail actual component begin/setup under the existing required edge; registration does not bypass it. No direct developer seed becomes actual analytical acceptance.

Exact focused argv (separate fresh job admission required) from the C1 clone:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q tests/test_cp1b_registration.py tests/test_upstream_tools.py`

No environment sync, provider or broad suite. Record exact runtime/base/source/case hashes, PID/UTC/exit and retained RED->GREEN logs. Initial lease admission authorizes writes only; one heavy job requires LEAD admission. Require confidence-review, no-argument post-edit rewrite-tournament, independent Sol/high sensitive review and exact final-byte checks before completion/commit. Financial/provenance/state implementation and review use the explicitly dispatched Sol/high route, with assignment evidence and no hidden telemetry claims.

## Remaining full-plan links

A1 financial core remains C3's independent work. Later C3 owner/workflow lease must authenticate full current CP1 internally, retain actual CP1B begin/tool/projection/submission/validation/settlement and complete fresh upstream lineage. Later C1 A4 must safely implement complete selected CP5 multi-producer/claim scope and actual settled integrity participation; none is authorized here. Later C2 FP02 bindings/render/native proof must consume actual CP1B-owned tables and operand passports. No CP1B/FP02/CP5 owner acceptance, QA gate, old-run relabel/import, live dispatcher support or broad qualification follows from A2. These explicit dependencies do not block disjoint preparation/implementation under their own reviewed leases.
