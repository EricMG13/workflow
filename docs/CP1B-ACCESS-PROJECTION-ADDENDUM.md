# CP1B A2 addendum — bounded fact-coordinate projection pages

Frozen additive capability for the existing cp1b-upstream-grant/2. This changes
neither authority nor original A2 tool/response/grant semantics. LEAD's exact
PM-integrated base/resource admission precedes C1 product writes. Independent
expectations: cases/earnings/access-projection-expected.json. B1 consumes this
capability before actual owner acceptance; the old B1 whole-row attribute plan
is superseded, not presented as a passing genuine-case transport.

## Confirmed requirement and ownership

A genuine CP1 artifact has six T4.14 rows of15 facts. Each fact has two original
Citation records whose exposed handle triples happen to match. With mandatory
identity-five fields plus citation_handles alone, one whole row is8267..8280
compact UTF-8 BODY bytes, above8192. Splitting field groups cannot fix that lower
bound. Distinct valid page handles could make it larger. Preserve duplicates and
canonical field values; no deduplication, quote loss, source rewrite, shortened
hash, cap increase or valid-case-as-unsupported workaround.

Only future C1 tracked files: src/deploy_workflow/tools/upstream.py and
 tests/test_upstream_tools.py. Required nonproduct work/handoff stays in the
subsequently admitted C1 work directory. No original A2 lease/oracle, registry,
methodology, source/host/Execution, financial/earnings math, B1, A4, renderer,
assets or other product file edit. PM integrates; LEAD issues exact base/lease/
resource admission. The uncapped-lane/one-heavy-job/paused-provider rules remain.
Sol/high handles this consequential parser/provenance/state change and review.

Original A2 lease SHA256 da0471d83746dc67bf40e9b3e14aa7984994abfa812820265174bd8cb6964142;
original access oracle a8210ba05e81c3cba04634bfe82e3e7aa11525892407b41d379ebf0298413d0c.
Those artifacts and existing tools remain unchanged. No new financial audit.

## Exact additive API

UpstreamTools.from_execution(store,ticket_id,step_id,*,grants), access_manifest,
receipts and invoke remain their current interfaces. Only a valid current
CP1B/earnings_delta v2 session may additionally invoke 'read_access_projection'.
No new grant schema/version, producer, coordinate, raw source or projected field
permission is introduced. Original read_access_manifest, lookup_upstream and
verify_upstream outputs/semantics/bounds are unchanged, including duplicate
citation_handles. CP2/CP5/v1/other-consumer sessions refuse this new tool with
not_permitted/null body/empty source evidence. A4 cannot use it.

Exactly five request keys, same names/types as read_access_manifest:
producer_module_id, producer_sha256, manifest_sha256, cursor, limit.
producer_module_id='CP-1'; producer_sha256 and manifest_sha256 must match this
session's authenticated producer/manifest. cursor is None initially or a returned
projection-cursor token; limit is a non-bool integer1..20. Extra/missing keys,
actor fields/coordinates/filters, malformed hashes/cursors or bool/out-of-range
limit refuse bad_arguments. Wrong well-formed producer/manifest digest refuses
identity_mismatch. No actor-supplied field filter or subset can bypass exact grant.

The complete sorted catalog is the SAME normalized granted coordinate sequence
committed by A2's manifest_sha256, ordered by(table_id,row_id,field,fact_id).
Resolve each complete tuple from that normalized coordinate sequence; do not
iterate the existing _facts global(field,fact_id) order, which differs from the
manifest order. Each entry is the existing safe Fact projection for that coordinate, containing
ALL granted projected_fields in lexical order. Every granted field is present,
including nulls, explicit statuses, original text, exact Decimal JSON strings,
currency/scale/basis/limitation/calculation metadata and citation_handles. Mandatory
fact_id,table_id,row_id,field,status are included. Citation handles remain only
source_id/source_sha256/locator with exact existing order/duplicates. No quote,
raw span/path/full Fact or Module JSON/diagnostic is added. No copying other
same-row facts, Cartesian siblings, hidden attributes or changed units/numbers.

Successful BODY has exactly these keys:

```
{
 "producer":{"module_id":"CP-1","sha256":H,"status":ACTUAL_STATUS},
 "projection":"granted_fact_projection",
 "grant_sha256":G,"manifest_sha256":M,
 "coordinate_count":TOTAL,"offset":OFFSET,
 "entries":[SAFE_FACT_PROJECTION,...],
 "next_cursor":PROJECTION_CURSOR_OR_NULL,"complete":BOOLEAN
}
```

H/G/M/status/counts/entries are actual current/session values, not literals from
this notation. No table_id at body top because a page may cross table/row boundaries;
each projected entry retains complete identity. This is the tool-receipt/1 BODY,
not the outer receipt. The receipt envelope/binding/sequence/call ID/source_evidence
remain the original A2 contract. source_evidence always has four empty arrays.

## Exact paging, bytes and token semantics

At a valid cursor position return the largest NONEMPTY contiguous prefix of
remaining projected entries that fits requested limit AND8192 compact UTF-8 bytes
for the WHOLE BODY, including producer, hashes, projection marker/counts/offset,
entry key strings/JSON escaping, cursor and completion fields. Serialize with
ensure_ascii=False,separators=(',',':'),allow_nan=False; no clipping/truncation,
string splitting, attribute omission or changing count/limit. Key order does not
change length; preserve full JSON escaping. Entry count <=20. complete iff this
page reaches TOTAL; then next_cursor=None. Otherwise next_cursor has exact form
'projection-cursor:' followed by64 lowercase hexadecimal characters. Evaluate every candidate prefix1..min(limit,remaining), constructing its OWN
terminal/nonterminal cursor/completion wrapper, and choose the greatest fitting
count. Do not assume a nonterminal wrapper's size also proves the terminal one
or stop before checking the terminal candidate. No empty advancing page. If one indivisible entry plus its body wrapper cannot fit, refuse
bad_arguments/null body and commit no cursor/page; do not call it source absence.

Projection cursors have a separate issued-token store/namespace from manifest
access-cursor tokens, bound to session/ticket/attempt/snapshot/producer/G/M and
next offset. No token transfers across namespaces, sessions, attempts, snapshots
or manifests. The new tool classifies a well-formed foreign/manifest token as
stale_binding; malformed tokens are bad_arguments. Original manifest tool's token
classification is unchanged (a projection-cursor passed to the original manifest
tool remains bad_arguments under its existing access-cursor grammar). A valid
access-cursor passed to this new tool is stale_binding. Only actually issued
projection tokens are valid.
Use the existing private session nonce or an equivalent session-issued token
mechanism, with a distinct projection domain; no credential or caller nonce.

Same valid cursor+same limit under unchanged binding returns byte-equivalent BODY
(including next_cursor), but a new actual receipt/call ID/sequence. Another valid
limit may give another maximal prefix; each issued next offset is authenticated
and retained. Null cursor starts/restarts offset0; replay never establishes
coverage without the actual successful receipt path. Complete traversal is actual
contiguous offsets0..TOTAL with each exact coordinate once along the chosen path;
repeated pages are harmless receipts, not permission/read widening.

## Atomic currentness and durable consumer proof

Perform every existing A2 currentness/authentication check before building and
immediately before returning/retaining response or committing cursor state:
executable pending CP1B ticket, exact inputs/statuses, same snapshot/pack/current
head/full bytes/run/issuer/as-of/method and unchanged copied grant authority.
Never follow a new head/session within a request. Single-writer/reentrant refusal
and detached grant/receipt mutation rules stay unchanged.

Stage response and any token issuance without mutating authority; check final
currentness and serialize/validate full size before commit. Retain the detached
actual receipt successfully before making newly issued cursor state observable;
the invoke.finally staged-cursor path must be stream-qualified: original manifest
tokens commit only to its existing manifest store, projection tokens only to the
new projection store. Never place all staged tokens into the old _cursors store.
If receipt construction/retention/currentness fails, expose no provisional body/
token, commit no usable cursor, preserve earlier receipts and release locks.
Failure responses have null body, appropriate existing A2 refusal category and
empty source evidence. Unexpected errors remain error/internal_error/null, never
success/empty projection. BaseException interruption semantics and receipt
preservation remain existing behavior; do not hide programmer failures as gaps.

The owner host still persists actual tool receipts to its immutable audit before
returning them to the actor. An in-memory A2 receipt is not itself durable journal
settlement. B1 historical verification recomputes exact projected records/page
wrappers/maximal prefixes and session-issued token graph from the authentic
producer+grant; it does not naively replay private nonce tokens in a new session.
Projection and manifest traversal proofs are distinct, both bound to the same
G/M/binding; neither catalog header alone proves actual values were read.

## Independent source-only cases and later check

Frozen oracle includes the genuine reviewed source artifact identity, exact safe
projection byte measurements for all actual selected coordinates and complete
wrapped manifest/projection pages, plus conservative actual citation-verification
call sizing under the existing20-ID/8192-byte limits. The two cases are selected
Q3/Q4 and absent FY2024/current FY2025, not new financial calculations.64-character
size sentinels may model unpredictable G/M/session tokens ONLY in static byte
proof; they are explicitly not actual grant/settlement authority. Raw genuine
source facts/statuses/values/duplicate handles remain unchanged.

Causal cases: full ordered mixed-table projection coverage; known0/nonknown null/
period metadata; all19 field presence; duplicate handles retained; max20 and
largest UTF-8/escaping-aware prefix; last-page null cursor; indivisible record;
foreign/manifest/stale cursor and wrong digest; extra arguments/field filtering;
wrong consumer/v1; grant/response mutation; mid-page snapshot/head/status/byte
race; retention/serialization failure has no provisional token; same-page replay;
prior-success preservation/lock release; all original A2/v1 tests unchanged.

No tests/imports/engine/provider calls in this freeze. Later focused argv after
separate exact-base/resource admission, from C1 clone:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_upstream_tools.py`

Record exact source/runtime/base/oracle hashes, argv/PID/UTC/exit/full causal logs.
No sync/broad suite. Confidence-review, changed-function no-argument rewrite-
tournament and the existing independent sensitive review are required. This is
one bounded A2 capability prerequisite, not an added financial gate or review chain.

Not verified: product implementation/tests, currentness/retention race behavior, actual B1 tool use/settlement, CP5 consumption or selected-run/native export.
