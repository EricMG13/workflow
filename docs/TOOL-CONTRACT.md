# Task0 supported analytical tool contract — v1

Task1 unblocks **CP-0 source readiness and CP-1 canonical financial foundation**, their
source/evidence sections, financial sections and later Model cells. Task2 unblocks
**CP-2 credit synthesis and CP-5 integrity review**, their permitted CP-1 consumption,
synthesis, QA, evidence and limitations sections. These adapters alone finish no owner.

Base: `df26ea82249fc062a8beb8dba3d51f1caf5fdf23`; imported implementation:
`6441553936086c834be885e2f3d7cd7f0959aa5c`. The independent component oracles are
[cases/source/manifest.json](../cases/source/manifest.json) and
[cases/upstream/manifest.json](../cases/upstream/manifest.json). They are distinct
microcases, not a fabricated connected source-to-financial result. Task3 must freeze
its own coherent source, arithmetic and rendered expectations before implementation.

## Authority and smallest public surface

Only trusted Python builds a session from a pending Execution ticket, its current
inputs, prepared-pack identity, admitted registry module/step, and explicit grants.
The analytical caller supplies a fixed tool name and arguments; it cannot choose
run/issuer/as-of/method, ticket, attempt, permissions, artifact bytes or selected heads.
Constructor fixtures are component evidence only. The production factory must read
and check the real Execution binding, not accept a model's assertion of authority.

C1 owns `SourceSession.from_execution(store, ticket_id, step_id)` and
`SourceSession.invoke(tool_name, arguments) -> dict`, plus
`SourceSession.bind_submission(payload: str) -> dict`. C2 owns
`UpstreamTools.from_execution(store, ticket_id, step_id, *, grants)` and
`UpstreamTools.invoke(tool_name, arguments) -> dict`. `grants` is trusted, explicit
Python configuration bounded by the consumer's adopted view below; callers
cannot extend it through tool arguments. Direct constructors may be used by tests.
Neither leaf imports the other's implementation. No shared-file write dependency.
Only C1 edits tools/__init__.py; C2 is imported directly from tools.upstream.

Factories reject absent/finished/stale tickets, a step other than the ticket's current executable admitted step (the next valid
registry step after retained predecessors; an invalid retained step may only use its
explicitly authorized repair), wrong run/issuer/as-of/method, and mismatched pack/input/result identities.
Source grants come from registry source capability plus `declared_sources` and
`readable_sources`, intersected with any narrower trusted grant. Call
`readable_sources` only after proving the step has pack-source capability: its
fallback of all pack sources is not an authority grant. Submit-only/upstream-only
steps have **no raw-pack tools**, even if the prepared pack is available internally.
Unknown registry/owner aliases fail closed; CP-3B/CP-6A/changed CP-4 duties are deferred.

## Receipt and submission binding

Every attempted invocation returns this JSON-compatible shape (no extra public keys):

```text
schema_version: "tool-receipt/1"
call_id: session-generated unique string
sequence: positive session-local integer
binding: {run_id, issuer_id, as_of, method_version, pack_sha256, snapshot_sha256,
          module_id, step_id, ticket_id, attempt, inputs}
  inputs: [{input_id, sha256, status}, ...] in bound order
  pack_sha256: PreparedPack.content_hash(); not a source hash
  snapshot_sha256: ExecutionSnapshot.content_hash() frozen by the factory
  attempt: Execution Attempt.number (0 or 1)
tool: exact admitted tool name
arguments: exact supplied JSON-compatible argument object
status: "ok" | "refused" | "error"
body: source string or upstream object on ok; null otherwise
error_code: null on ok; stable code otherwise
source_evidence: {read, extracted, surfaced, searched}
  read/extracted/surfaced: sorted unique [source_id, locator] pairs
  searched: successful search scopes in invocation order (null means all granted IDs)
```

Retain exact arguments/results, successful IDs and their binding without interpreting
a tool result as a financial artifact. Failed calls are also retained, with null body.
Error codes: `bad_arguments`, `not_permitted`, `unavailable`, `identity_mismatch`,
`stale_binding`, `render_refused`, `internal_error`. Unknown/disallowed names and
nongranted source/producer/field use `not_permitted`; malformed values use
`bad_arguments`; unavailable admitted source uses `unavailable`. Unknown identifiers
must not disclose existence beyond the grant. A reserved-block delimiter uses
`refused/render_refused`; unexpected local exceptions use `error/internal_error`.
No raw exception, private quote, partial body, hidden hash or source text in errors.
A validation failure is a successful verification result with `verdict: invalid`,
not a permission refusal. Do not catch process-control exceptions as tool success.

`bind_submission` returns a separate `submission-binding/1` record containing this
binding, SHA-256 of exact UTF-8 payload, ordered successful_call_ids, all attempted
call_ids and source_evidence snapshot. It cannot create accepted status or settle a
module. Bindings are immutable snapshots; later calls cannot alter an earlier binding.
bind_submission uses the same current-binding, pre-return snapshot equality and
single-writer/reentrancy guards as invoke; stale submission binding refuses without
creating a submission-binding record.
Part assembly, validator submission, journal settlement and render attachment are
Task3's responsibility. Crash durability/retry settlement is not claimed by v1.

Sessions are single-writer and refuse reentrant invocation; no source beneath a
running check may be edited. Stage evidence and complete output per invocation.
Before returning success, re-read the ExecutionSnapshot and require its content hash
and current inputs/heads to equal the frozen binding; any change refuses stale_binding
with no new evidence or partial result. Only then publish the result/evidence receipt.
This is conservative snapshot equality, not durable concurrent settlement.

Each invocation checks the ticket's current selection against its frozen binding;
if it changed, refuse stale_binding. Never silently follow a newer producer. Check
artifact content hashes and all identity/status coordinates before selecting data.
Read-only checks never change heads, inputs, artifact bytes, grants or source evidence.
Upstream receipts always have empty source_evidence. Call/receipt IDs are host-owned;
no model-supplied arithmetic, shell, arbitrary code or general file tools are supported.

## Source search, read and extraction

Reuse `PackTools(pack, sources=explicit_ids)` and `ToolRules` from live/tools.py.
No implicit `sources=None`. Adopt the existing signatures and bounds:

| Tool | Required arguments | Optional | Bounds / result |
| --- | --- | --- | --- |
| search_pack | query: nonempty string | source_id: string or null; max_hits: int | hits 1..15, default 10; existing case-insensitive deterministic ranking and snippets |
| read_pages | source_id: string; first_page: int; last_page: int | none | 1 <= first <= last, at most 5 pages; exact SOURCE blocks |
| extract_statements | source_id: string; locators: list[str] | none | financials step only, 1..8 distinct exact page:N locators; existing Python extracted lines |

Reject unknown keys and bool-as-int. Search null/omitted scope means only admitted
IDs. Preserve existing snippet width (300 characters either side of the first match).
Search credits surfaced locators and successful search scope; it never grants full
read credit. Read/extraction credits only returned located pages. Preserve the legacy
successful missing-read-span message, with no credit for that span; a valid empty
extraction is honest empty output, not completeness. Do not synthesize units, currency,
period IDs, financial item mappings, or accepted status from printed columns.

**Atomicity:** build the complete result before adding any read/extracted/surfaced/
searched evidence. A failed read/search/extraction changes none of those collections,
including when an earlier page/hit in the same call rendered successfully. Preserve
all evidence from earlier successful invocations. Do not clear the entire session to
repair a failure. Keep delimiter rejection and verbatim citation behavior. Prove the
known failure before a narrow correction to live/tools.py; extraction is not presumed
broken merely because read/search are. Historical reuse manifest hashes remain the
import baseline; any product deviation must be listed in C1's handoff and reviewed.

## Frozen upstream lookup and verification

Task2 exposes exactly two tools. All integer limits reject bool. Unknown keys refuse.

`lookup_upstream` arguments:
`{producer_module_id: str, producer_sha256: str, table_id: str,
row_ids: list[str], fields: list[str]}`. One producer/table, 1..20 distinct rows,
1..16 distinct projected fields, no implicit all, wildcard, query language or cursor.
The complete upstream body must fit 8192 UTF-8 bytes after deterministic compact
JSON serialization (ensure_ascii=False, separators=(",", ":")); oversized output
refuses bad_arguments with no partial result.
All requested rows/fields must exist and be permitted; one forbidden target refuses
the entire request. Bound status/hash/run/issuer/as-of/method must match the selected
frozen artifact and ticket. Preserve request row/field order in the returned result.

Successful body: `{producer: {module_id, sha256, status}, table_id, rows}`;
each row is `{row_id, facts}`; each fact contains only the requested projected keys.
A field is a Fact attribute allowlisted by the consumer, not arbitrary object traversal.
The grant also restricts the canonical Fact.field coordinate (for the case, `value`);
that coordinate is distinct from projected attributes such as `amount` and `unit`.
All returned facts retain their canonical identity: requests must include fact_id,
table_id, row_id, field and status. Decimal amounts/scales serialize as exact strings;
null and known zero stay distinct. Values remain unscaled in the lookup, alongside
unit/scale/currency/period. Python owns any subsequent represented-value arithmetic.

`citation_handles` returns only `{source_id, source_sha256, locator}` for a citation,
only when that metadata is granted. Source/locator metadata permission does not grant
quote or raw-text permission. The v1 upstream-only scope never exposes `citations`,
quote, raw pack text or record_json, including through error details or contexts.
For existing step views, reuse live.context typed projections as an upper bound.
Task0 deliberately adds a distinct CP-5 bounded canonical fact/status view (including
missing facts) as frozen in the permission matrix; this is not integrity_projection,
whose clean no-claim fixture would expose no facts. Do not return an unfiltered
`module_context`, `integrity_scope` or full Module dump. No whole-pack search fallback.

`verify_upstream` arguments:
`{producer_module_id: str, producer_sha256: str, kind: "citations" | "integrity",
fact_ids: list[str]}`; 1..20 distinct permitted fact IDs. Successful body:
`{producer: {module_id, sha256, status}, kind, verdict: "valid" | "invalid",
issue_count: int, issues: [{code, fact_ids}]}`. Codes are fixed categories from the
underlying checks: citation failures map to fact_citation; the v1 integrity findings
are fact_citation, scale_unit and figure_identity. Any unexpected finding kind is
an internal_error, not silently discarded. No prose/quote/error echo, hidden-record
counts or hidden IDs.

For citations, trusted Python may use the pack internally with readiness.citation_issues
and quotes.quoted, returning only the sanitized verdict/categories. No caller-asserted
citation payload, arbitrary quote query, raw source retrieval or new citation authority.
For integrity, reuse CP5 review_scope/python_checks **only after** asserting scope.issues
is empty, every evaluated producer/record/field is granted, and identities are current.
Partially readable or stale scopes refuse as a whole, before running or exposing checks.
The complete CP5 scope is the target of integrity verification: fact_ids must equal
all evaluated fact IDs of this single-producer v1 scope, not select a favorable subset.
V1 requires an empty blocked-ancestor set and refuses multi-producer, claim-bearing
or partially granted integrity scopes. Its
independent clean case is U-integrity in the manifest. No successful broader integrity
claim is authorized. Do not implement another arithmetic engine.

## Initial consumer permission matrix

| Consumer step | Producer/view admitted by v1 | Source permission |
| --- | --- | --- |
| CP-0 source_readiness | none | explicitly declared ready/missing sources; search/read only |
| CP-1 source_context | none | explicitly declared sources; search/read only |
| CP-1 financials | validated earlier source_context by existing step projection | explicitly declared sources; search/read/extract |
| CP-2 credit_synthesis | exactly `module_context("credit_synthesis")`: bound CP-1 referencable facts (`ref`, `label`, `period`, `unit`, `shown`), the CP-1A catalogue rows and signals, upstream statuses and inherited limitations, with the per-case key tree frozen in `cases/snapshot/cp2-view-tree.json` (S1a lease rev 2; a D2 exception that counts as tool use) | none |
| CP-3 relative_value | none (pack-tool step; no `read_inputs` view, docs/CP3-OWNER-LEASE.md) | the CP-0 `third_party` sources only (`readable_sources`, market only), search/read only (no extract); a `read_pages` outside that scope is refused `not_permitted` |
| CP-5 integrity_review | exactly the owner view of docs/CP5-OWNER-LEASE.md: cp5_integrity.context_block over the bound heads (every fact of the non-CP-1 bound heads; for CP-1 the facts integrity_projection keeps), no `quote` key at any depth and no citation quote string outside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`; CP-3's settled market-evidence facts, not citations), python_findings reduced to the kind label plus where; served by read_inputs on the G1 pathway only. The v1 and CP5-v2 upstream-tool grants stay for the earnings pathway | none |
| CP-6 committee_challenge | exactly the owner view of docs/CP3-OWNER-LEASE.md (CP-6 half): cp6_committee.context_block over the bound heads (module_context("committee_challenge")) with every heads[*].claims[*].citations removed, key tree frozen in cases/cp3-cp6-owner/expected.json execution.tool_use.CP-6.view_key_tree; no `quote` key at any depth except cp3_rows[*].cells.quote and no citation quote string anywhere outside those cells (CP-3's own T3.3 settled market-evidence quote facts, not citations); served by read_inputs on the G1 pathway only | none |
| CP-1C peer_benchmark | exactly the view `owners.cp1c.view(historical, attempt)` registered in `_VIEWS["peer_benchmark"]` (`owners/cp1c.py:1845-1894`): upstream statuses, the peer sheet (state, source id, page locators, rows as the table rule reads them, issuer line), the four CP-1 facts (`ref`, `label`, `period`, `unit`, `shown`, `value_class`), the policy rules including `direction`, and the inherited limitations; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp1c-owner/cp1c-view-tree.json` | `search_pack` and `read_pages` over the identity and financial sources and, when the pack holds it, the peers source (`host.py:99`); no `extract_statements` |
| CP-1D earnings_quality | exactly the view `owners.cp1d.view(historical, attempt)` registered in `_VIEWS["earnings_quality"]` (`owners/cp1d.py:2318-2388`): `upstream`, `bridge` (state, source id, pages, items, totals), `cp1_facts` (the known selected CP-1 operands: `ref`, `label`, `period`, `unit`, `shown`), `cp1_t417_rows`, `cp1_facts_note`, `inherited_limitations`; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp1d-owner/cp1d-view-tree.json` | `search_pack` and `read_pages` over the identity, financial and bridge sources, whichever the pack holds (`host.py:93`); no `extract_statements` |
| CP-2A downside_pathway | exactly the view `owners.cp2a.view(historical, attempt)` registered in `_VIEWS["downside_pathway"]` (`owners/cp2a.py:1719-1774`): `upstream`, `base_periods` (operands and ratios as cells), `cp1_facts`, `cp1_facts_note`, `scenario_bounds`, `threshold_metrics`, `inherited_limitations`; no `quote`, citation or `record_json` at any depth; key tree: the shape in `docs/CP2A-OWNER-LEASE.md` Tool use (no `cp2a-view-tree.json` is committed yet) | none (session-less, source-free) |
| CP-2D liquidity_bridge | exactly the view `owners.cp2d.view(historical, attempt)` registered in `_VIEWS["liquidity_bridge"]` (`owners/cp2d.py:2573-2609`): `upstream`, `cp1_facts` (`ref`, `name`, `label`, `period`, `unit`, `shown`, `status`, `limitation`; missing facts included), `cp1_facts_note`, `bounds` (horizon months, minimum cash), `inherited_limitations`; no `quote`, citation or `record_json` at any depth; key tree: the draft in `cases/cp2d-owner/manifest.json#view_tree_draft` | none (session-less, source-free) |
| CP-2E macro_fx | none (no `read_inputs` view, no upstream tools) | `search_pack` and `read_pages` over the financial source only (`host.py:101`); no `extract_statements` |
| CP-2G forward_credit_model | exactly the view `owners.cp2g.view(historical, attempt)` registered in `_VIEWS["forward_credit_model"]` (`owners/cp2g.py:3019-3110`): `upstream`, `base` (operands and ratios), `drivers` (bounds), `cp2a` (base period, scenarios, breaks), `cp1d` (state and the supported figures when bound), `break_metrics_offered`, `cp1_facts`, `cp1d_facts`, `inherited_limitations`, missing facts offered with their status; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp2g-owner/cp2g-view-tree.json` | none (session-less, source-free) |
| CP-2H rating_triggers | exactly the view `owners.cp2h.view(historical, attempt)` registered in `_VIEWS["rating_triggers"]` (`owners/cp2h.py:2163-2249`): `upstream`, `register` (state, source id, pages, agency rows), `triggers` (terms only), `cp2g` (status and the 28 ratio facts as cells), `cp1_facts`, `inherited_limitations`; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp2h-owner/cp2h-view-tree.json` | `search_pack` and `read_pages` over the identity, financial and ratings sources, whichever the pack holds (`host.py:103`); no `extract_statements` |
| CP-3C refinancing_risk | exactly the view `owners.cp3c.view(historical, attempt)` registered in `_VIEWS["refinancing_risk"]` (`owners/cp3c.py:2706-2748`): the required edges' statuses, the bound CP-1 and CP-2D facts named by `manifest.fact_bindings` (`ref`, `name`, `source`, `label`, `period`, `unit`, `shown`, `status`, `limitation`) including missing ones, the facility list (text fields only), the unread optional edges, the repricing, path-kind and feasibility bounds and the inherited limitations; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp3c-owner/cp3c-view-tree.json` | none (session-less, source-free) |
| CP-3D market_implied | none (no `read_inputs` view) | `search_pack` and `read_pages` over the market and financial sources (`host.py:95`); no `extract_statements` |
| CP-4 legal_covenants | exactly the view `owners.cp4.view(historical, attempt)` registered in `_VIEWS["legal_covenants"]` and served for `inputs="step_context"` (`owners/cp4.py:119`, `owner_workflow.py:820`): `cp4_legal.context_block` over the pack and the bound CP-0 and CP-1 heads, key tree frozen in `cases/cp4-owner/expected.json` `cp4_step_view`; no `quote`, `citations` or `record_json` key and no legal quote text | `search_pack` and `read_pages` over the `legal-covenants` source only (`cp4_legal.upstream_of(...).legal_sources`); no identity or financial raw text; no `extract_statements` |
| CP-4C restructuring_fulcrum | exactly the view `owners.cp4c.view(historical, attempt)` registered in `_VIEWS["restructuring_fulcrum"]` (`owners/cp4c.py:2860-2924`): upstream statuses, `claims_offered` (the secured claim and the statement rows), `ebitda_offered` (the CP-2G EBITDA facts), `cp2a` (the applied scenario), `cp4` (facility, lender protection, additional-debt conditions), `bounds`, `cp1_facts`, `cp2g_facts`, `inherited_limitations`, unsettled facts offered with their status; no `quote`, citation or `record_json` at any depth; key tree frozen in `cases/cp4c-owner/cp4c-view-tree.json` | `search_pack` and `read_pages` over the financial and legal-covenants sources (`host.py:105`); no identity; no `extract_statements` |
| CP-8 decision_ledger | none (no `read_inputs` view; `read_inputs` and `extract_statements` refuse `not_permitted`) | `search_pack` and `read_pages` over the prior_case, update and market_update sources (`host.py:107`) |
| CP-DR research | exactly the view `owners.cpdr.view(historical, attempt)` registered in `_VIEWS["research"]` (`owners/cpdr.py:829-855`): the gap agenda, source ids and statuses, question limits and the bound CP-0 status; no `quote`, citation or `record_json` at any depth | `search_pack` and `read_pages` over every source the prepared pack holds, a source that is not ready answering `unavailable` (`host.py:97`); no `extract_statements`; no upstream tools |
| CP-L10 change_screen | exactly the view `owners.cpl10.view(historical, attempt)` registered in `_VIEWS["change_screen"]` (`owners/cpl10.py:1241-1284`): upstream statuses, the four quarters, the topics with their values as Python spells them, the rated pair screens, the rules and the inherited limitations; no `quote`, citation or `record_json` at any depth; key tree: the shape in `docs/CPL10-OWNER-LEASE.md` Tool use (no `cpl10-view-tree.json` is committed yet) | none (session-less, source-free) |

All other source/upstream view pairs refuse until explicitly leased. CP-1 narrative/
readiness/quality remain source-free and use only their existing adopted projections.
CP-2 cannot retrieve missing numeric facts merely because CP-5 can inspect their status.
The Task2 component fixture uses CP-5 so that zero and missing can both be queried.
CP-2 lookup smoke must separately prove its narrower referencable filter.
V1 projected keys are fact_id, label, table_id, row_id, field, amount, text, status,
unit, currency, scale, period, basis, denominator, limitation, calculation_id,
value_class, calculation_status and citation_handles. Grants may narrow these.
Formula/source_amount/stated_amount/record_json/citations/quote are not exposed.
The CP-2 view above is not the V1 projection: its keys are only those in its frozen tree,
and it carries no quote, citations or record_json at any depth.
The matrix grants citation handle metadata explicitly for these two upstream views;
it never grants citation quote fields. Tables/rows/canonical fields must be a subset
of the trusted view index (not arbitrary trusted strings). CP-5 income/value and the
three case rows are admitted only for the frozen synthetic component fixture; real
run grants use that run's validated canonical coordinates.
A complete integrity grant authorizes the checker to inspect all stored metadata
and citations internally; it never authorizes returning quote/raw text or diagnostics.

## Evidence and review boundary

Sources for adopted APIs: live/tools.py PackTools, Seen, ToolRules, tool_specs;
live/context.py declared_sources/readable_sources, upstream_text, integrity_projection;
cp5_integrity.py ReviewScope/review_scope/python_checks; readiness.py citation_issues;
quotes.py quoted; contracts.py Contract.content_hash/Module/Fact; execution.py Attempt.
These are local pinned sources; provider interfaces and mutable old-project code are
outside the contract. Source compatibility is not functional qualification.

Source cases freeze exact bytes/hash/line numbers/quotes and prior-state invariants.
Upstream cases freeze a complete synthetic Module serialization/hash, exact Decimal
values, zero/missing distinction and identity/scope refusals. C1/C2 add fixture/test
files under their lease, then independent sensitive implementation review, confidence
review and non-trivial rewrite-tournament. No provider/paid/live tests. Task3 must
retain actual analytical calls -> validated submissions/settled artifacts -> actual
selected consumers -> assigned visible sections, including limitations/citations/status.
Direct constructors, developer-agent tools and these fixtures cannot finish a module.
