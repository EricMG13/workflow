# Task4 CP1B registration/access preparation

Proposal for LEAD freeze and independent Sol/high review; no implementation or
owner acceptance. C1 owns only this NEW document. Inspected integrated base:
`d04c19cb237c4125dcb3765cb0745479913a4430`; branch
`codex/cp1b-access-preparation`. Prior chart branch `codex/cp1-chart-actual` at
`83cbf9221e118135d3b61bea2d423c91c05a0439` and all Task3 leaves are preserved.
The local integration checkout has no `main` ref; fetching that name failed,
then fetching the exact d04c19c object succeeded. No product writes, tests,
analytical engines, publication or provider calls ran during preparation.

Read C3 preparation `07cf6dee33006d629cee3aab2702cbc590eb5030`, LEAD's draft
`docs/CP1B-CORE-LEASE.md` and `cases/earnings/expected.json`. The latter two are
review inputs, not assumed integrated authority. C3 owns the pure earnings core
and later CP1B owner bridge; C2 owns binding/rendering; PM alone integrates exact
accepted commits. The user removed the implementation lane count cap; exact
exclusive leases and one-heavy-job admission remain. Paid/provider/live stay paused.

## Source and permission expectations

Reuse the unchanged financial manifest SHA256
`6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`.
The adopted literal case is consolidated IFRS USD MILLIONS, unaudited: Q3 and Q4
are distinct 92-day own quarters; revenue30/30, EBITDA7.5/7.5, cash18.75/20,
debt48.75/50, net debt30/30. Known zero earnings changes differ from unavailable
prior leverage and unavailable FY2024 income comparisons. These expectations come
from source/C3's independent preparation, not this adapter's output. C1 adds no
new financial oracle, causal explanation or status policy.

The CP1B analyst receives only explicitly granted settled CP1 fields, identities,
status/limitations and citation handles. No raw-pack tool, `Citation.quote`, source
span/text, filesystem path, hidden diagnostic or arbitrary Python/shell capability.
Python may inspect the authenticated full CP1 internally to call C3's pure core;
never manufacture a partial ModuleView carrying the full artifact's hash.

Current `business_context.referencable` removes nonknown facts and text metadata.
It is unsuitable for CP1B: Q3 missing leverage, T4.14 period identities and basis
metadata must remain visible in a specifically granted CP1B projection. Retain
CP2's existing narrower projection and existing v1 grants unchanged.

## Proposed exclusive implementation files and integration

First registration/access patch, after separate reviewed lease and admission:

- `src/deploy_vii/registry.py`: add only CP1B StepChain, cell `cp1b`, sole step
  `earnings_delta`, no within-attempt repair, pack sources/reads or extracts.
- `src/deploy_vii/methodology.json`: change only CP1B table ownership to
  `T1B.1`, `T1B.2`, `T1B.3`; retain CP0/CP1 required edges and all other records.
- `src/deploy_workflow/tools/upstream.py`: CP1B/current-CP1 access plus explicitly
  versioned complete CP5 scope access, with existing receipt/atomic refusal rules.
- NEW `tests/test_cp1b_registration.py`: step ownership/derived registry routes,
  exact table ownership and unchanged dependency/fan-in semantics.
- `tests/test_upstream_tools.py`: focused permission, identity and complete-scope
  causal cases; retain all historical v1 cases and label seeded heads component-only.

No live/submission change is needed for the proposed supported offline Python
bridge: C3's later `earnings_workflow.py` calls its own validated submit callable;
CP5 already has `submit_cp5_step`. The shared live dispatcher, prompts/context and
provider loop do not become supported for CP1B merely through registration.
If a later chosen bridge needs them, freeze a separate exact lease first.

An actual CP5 participation bridge is a separate necessary dependency. Propose
C1 ownership of NEW `src/deploy_workflow/integrity_workflow.py` and NEW
`tests/test_integrity_workflow.py`, plus the already leased handoff update at that
time. Its public session methods would be `begin`, `invoke`, `submit`, `receipt`
and `verify_receipt`, with exact typed signatures/transport/limits frozen before
code. It wraps existing CP5 validation/settlement; it binds retained calls and the
analyst payload to the same current attempt/scope, without another integrity engine.
If LEAD assigns that bridge elsewhere, registration/access alone leaves the real
consumer link open. A lookup/mock/direct composition cannot close it.

PM applies only accepted exact patches onto the subsequently named integrated
contract/case revision. Record imported-file changes in the reuse manifest through
PM's separately owned patch. No C1 push/merge or old publication replay. C3/C2 may
work independently in their disjoint files; shared interface changes integrate
serially. This preparation's base is d04c19c, not an implementation admission.

## Proposed access API for freeze

Preserve `UpstreamTools.from_execution(store, ticket_id, step_id, *, grants)` and
`invoke(tool_name, arguments) -> detached tool-receipt/1`. Freeze a v2 grant schema
selected only by trusted setup: each producer record has `module_id`, exact
`sha256`, exact `(fact_id, table_id, row_id, field)` coordinates, allowed output
fields and claim IDs. Never union producer row/field/claim grants. A reused fact ID
in CP1B cannot satisfy CP1 permission, or vice versa. Grants cannot widen in args.

CP1B v2 admits only its exact current bound accepted/restricted CP1. Freeze the
minimum selected T4.10 measures, complete T4.14 period index, canonical historical
basis coordinates and selected dimension/limitation facts with C3's owner bridge.
`lookup_upstream` retains its current producer/hash/table/row/field argument shape;
coordinates are checked as tuples, not independent Cartesian allowlists. Missing
comparatives are established by a completely enumerated authorized period index,
not by interpreting `not_permitted` as source absence. Python validates selected
IDs and recomputes values from the authenticated producer; the analyst supplies
IDs/commentary rather than numeric answers or replacement provenance.
Propose detached `session.access_manifest` metadata for trusted host delivery:
bound producer/hash, grant digest and complete T4.14 row/field identities (including
an explicit complete marker), plus the granted coordinate descriptors. It contains
no values or quotes; the analyst performs actual bounded lookups for values.
If that descriptor exceeds the frozen transport limit, page it explicitly before
implementation rather than hiding available periods or enlarging limits silently.

Propose two explicit additions for CP5 only (v2; no implicit permission for CP1B):

1. `read_integrity_scope({scope_sha256, cursor, limit})`: bounded deterministic
   pages from the frozen trusted scope. First page requires cursor null; subsequent
   opaque cursors bind attempt/scope/projection and traversal position. Return
   selected bound inputs/statuses, evaluated/blocked identities, claim keys/text/
   limitations, permitted fact/claim-citation handles, inherited limitations and
   sanitized Python findings as typed page records; complete manifests/counts and
   next cursor let the host prove traversal. Claim text is explicitly granted
   analytical output, never a citation quote. Output bytes remain <=8192 and rows
   <=20; indivisible over-limit records refuse rather than truncate silently.
2. `verify_integrity_scope({scope_sha256})`: execute existing `review_scope` and
   `python_checks` over the WHOLE scope, with a bounded summary/counts and manifest
   hash; full sanitized finding records are read by the first tool. Return only
   category and producer-qualified affected claim/fact/citation references, never
   raw finding detail containing quote prefixes. Preserve every check category;
   unknown or unresolvable references return `internal_error`, without partial body.

The factory/session binding supplies the initial scope hash and manifest identity;
the analyst cannot choose a new scope. Existing per-producer `verify_upstream`
citations remains available; v1 single-producer integrity retains its frozen
meaning. A v2 whole-scope check is never reported as a per-producer pass.
Every emitted reference is `(producer_module_id, producer_sha256, ref)`; preserve
claim keys and all affected owners for cross-module identity findings. C3 should
use CP1B-owned fact IDs/calculation IDs and T1B coordinates for new values, retaining
operand producer/hash/fact IDs separately, so copies do not collide with CP1 facts.
Do not change CP5's existing identity comparison rules to conceal a collision.

## Complete current CP5 scope and settlement

`registry.dependencies` makes CP5 follow every selected analyst; `current_inputs`
binds exact current hashes/statuses and CP0 authorization. `review_scope` excludes
CP0 from evaluation but retains its gate; `validate_integrity` requires every
material claim exactly once and resolves each review's refs within its producer.
Reuse those trusted functions and `submit_cp5_step`; do not write a weaker validator.

For the smallest actual consumer case, propose requested modules `(CP-1B, CP-5)`:
closure includes CP0/CP1; CP5 evaluates all current CP1 AND CP1B claims/facts,
retaining restrictions/gaps. If CP-MODEL or any other analyst is selected, it also
joins the actual core scope; never omit it to retain this two-producer assumption.
Freeze the complete fresh run selection/publication ordering with LEAD/C3/C2 before
execution. Existing CP-MODEL publishes CP1 only; a CP1B render or CP5 read does not
establish new canonical Model publication semantics.

Remove the v1 adapter's one-producer/no-claim limitation only inside reviewed v2
scope handling. Trusted Python checks cover blocked/empty evaluated sets, fact and
claim citations, scale/unit, claim figures, unsettled facts and figure identity.
Trusted submission/composition also covers unsupported/partly-supported claims,
contradictions and gaps. Enumerate all current `KINDS`; no unsupported-category
pass. Scope omissions refuse access; supported verdicts over flagged refs and
incomplete/duplicate claim reviews remain invalid at settlement. Citation validity
alone does not prove material support or CP1B arithmetic/operand lineage.

No concrete safe alternative current analytical consumer is established: CP1D is
unimplemented and the renderer is deterministic. If the above CP5 bridge/scope
cannot be leased, report that exact open dependency and keep module acceptance open.

## Independent refusal cases to freeze before candidate code

| Case | Expected behavior |
| --- | --- |
| Correct CP1B Q3/Q4 current grants | Return exact known values plus missing leverage/limitations and period identities; no quote fields |
| FY2024 absent from complete period index | Retain known current FY values and source-supported comparative gap; not zero or permission failure |
| Wrong step/consumer, raw tools/quote field, extra producer/coordinate | `not_permitted`, null body, no source evidence credit |
| Wrong digest/issuer/run/as-of/method or bound status | `identity_mismatch`; no disclosure |
| Changed snapshot/current head, ended/repaired attempt, old cursor/scope | `stale_binding`; earlier successful receipts retained |
| Duplicate/ill-shaped IDs, malformed cursor, oversize page | `bad_arguments`; no partial/truncated success |
| Same row/fact ID in both producers; grant only one | Other producer stays hidden; qualified refs never pooled |
| CP1B missing/blocked or CP0 does not authorize | Actual begin refuses under existing required edge; no fabricated output |
| CP5 grant omits current CP1 or one required claim/finding | Refuse complete-scope setup/read; never silently narrow review |
| CP5 changed CP1B, foreign ref or duplicate/missing claim review | Stale/identity refusal or trusted submission invalid, respectively; no settlement |
| Valid current CP5 actual claim-bearing review | Retain whole scope, actual calls, evidence refs, payload, trusted validation and settled artifact; lookup alone fails completion |
| Bad citation, scale, figure token, unsettled claim, cross-producer mismatch | Each existing trusted category survives sanitization and forbids an unjustified supported verdict |

Use small handwritten component inputs to trigger causal errors, labeled separately
from literal issuer acceptance. Later retain initial failures and RED-to-GREEN logs;
one admitted focused job at a time. Proposed commands are the existing pinned
Python `-m pytest -q tests/test_cp1b_registration.py tests/test_upstream_tools.py`,
then separately the new integrity bridge tests when leased. No command ran here.
After product edits require confidence-review, no-argument rewrite-tournament and
independent Sol/high sensitive review. Actual fresh CP0/CP1/CP1B/CP5 positive/gap
and native FP02 acceptance are later admitted work, preserving all Task3 evidence.

## Preparation confidence review

Traced five risks: nonknown facts lost by `referencable`; Cartesian/producer grant
pooling; hidden quotes from existing CP5 `context_block`/finding diagnostics;
partial CP5 claim set; and reuse of old settled runs as new owner proof. Proposed
explicit projections/tuple grants, quote-free scope pages, unchanged core complete
validation and fresh execution address them. The existing context block cannot be
returned verbatim because it includes citation quotes. Trusted checks still inspect
all bound facts even if an analyst sees a bounded projection. Permission to inspect
internally never grants raw-pack access to the analyst.

Open for LEAD/independent review: exact v2 schema/cursor/page records; C3 selected
coordinate and T1B column contracts; CP5 bridge ownership/signatures/receipt binding;
complete fresh run selection/publication order; committed implementation base and
per-job admission. These are proposed interfaces, not implemented guarantees.
Docs-only change: code review workflows/tournament are exempt; root independently
reviews this sensitive proposal before granting any product-file lease.
