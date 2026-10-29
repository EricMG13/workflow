# CP-1D (Earnings quality) owner lease — FROZEN by LEAD 2026-10-28 (preparation revision 3)

Amended by LEAD 2026-10-28 (CP-6 freeze re-pin, `work/lead/cp6-freeze/report.md`): `src/deploy_vii/methodology.json` registers `T6-FINAL` under CP-6 `table_ids` (ruling Q7), 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 → 0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8; this module's builder re-pins it and its manifest records the new hash. Only pin hashes move: no other leaf of this module's oracle changes. The pin is the builder constant `METH_SHA`. Own files, old → new sha256: `manifest.json` 7e1766071125b41fb459428f37e90166f9f35f2a806310a2f74baf81e926f585 → 07dd8530a7f53aa5fe2c1b4840554c0fc6392e26e53bf01ad2858458ecdfe955; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` 2fb5af98f8c7d745db17f0032c18c9fb15c5080e03336bd298d45947715a4101 → d42f88c5c2d00832d7f67648d36f6339d8851647b650bf8831a6680dad537234.

Amended by LEAD 2026-10-28 (Stage 1 release batch, `docs/rulings/2026-10-28-stage1.md`; `work/lead/stage1-release/report.md`): 1D2 follow-up (j): a Recurring add-back with an accepted source basis gets the own limitation `Recurring add-back excluded although a source amount is cited: <label>.`, per item in bridge order, after the `Proposed amount is not stated for …` lines and before the analyst-fraction line. Builder only: no frozen case reaches it, so manifest, submissions and expected are unchanged. Pass 2: round 4 (i) (a zero or negative denominator of T1D.5 and T1D.6 reads `Not meaningful: <T1D.3 row label> is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)`; no frozen case) and the `refusal_rules.partly_supported` recipe text, replaced as LEAD ruled; Fix round 1 (1D2 cell layout): a Recurring add-back, on the fraction path or the source path, shows `Rule: Supported 100%; otherwise 0; Recurring 0` with no derivation, accepted reads `Zero by rule (share accepted is 0)`, and no analyst-fraction limitation is added. `expected.json` changes only `.refusal_rules.partly_supported`. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` 6015b443603b16f9af8c5417e6fa69f7468fa243f37b64575f745aac6549bd8c → 399ce03d3842c0150643ab80607f6352f26d5a5d0bdf0d55ae1f15a6c8575565; `builder/build.py` 95b145f3aa29ab2f25ce82ddc9270bdec5cb62f19cb9895be5587064beaab7d2 → 1c37f77de159ff6bd930af486f10d435ee4da000744497d16204ffd92a5eb821. A double scratch rebuild of every builder in dependency order was byte-identical. Pin consumers: `cases/cp2g-owner/builder/build.py` pins `expected.json`, `manifest.json`, `submissions.json`. Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change.

Amended by LEAD 2026-10-28 (oracle amendment 1D1, `docs/rulings/2026-10-28-stage1.md` round 1 "Oracle amendments" item 2): `T1D.4.proposed_total.reported` and `T1D.4.mgmt_ebitda.reported` now cite their own bridge total line (`bridge`, `page:1`, quote = the totals line), in the same form as the T1D.1 citations, in both the one-sided and the both-sides branch. `expected.json` changes only by adding `citations` to `cases.positive.facts[53]` and `[57]`. LEAD rebuilt it in cascade order from a scratch copy with `python3 -I`, and the result is byte-identical. builder 1d0e534b… → 95b145f3aa29ab2f25ce82ddc9270bdec5cb62f19cb9895be5587064beaab7d2; expected 549d5ef3… → 6015b443603b16f9af8c5417e6fa69f7468fa243f37b64575f745aac6549bd8c; manifest 7e1766071125b41fb459428f37e90166f9f35f2a806310a2f74baf81e926f585 and submissions e19bc64bf6b9d388ca355fcb5de5160be1c4c0e7e27d3b348f1996a17fbd93d7 are unchanged. Pins elsewhere in this file are superseded where they differ.

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 037b3e9d… → 1d0e534b09227b9f8a35e1e5cb475acbe0585a7a0401c9002e65d847f66ea8da; manifest 842ced20… → 7e1766071125b41fb459428f37e90166f9f35f2a806310a2f74baf81e926f585; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

Amended by LEAD 2026-10-28 (Stage 1 release follow-up, rulings round 12, `docs/rulings/2026-10-28-stage1.md`; `work/lead/stage1-release/report.md`): the `refusal_rules.partly_supported` recipe text takes rule W (the sign sits directly before the first digit or one space before it, any whitespace, a line break included; an accounting-parenthesised numeral may hold one space inside each parenthesis). No value moves; only that text path of `expected.json` changes. Manifest and submissions are unchanged. Pin consumers: `cases/cp2g-owner/builder/build.py` pins this expected.json. Own files, old (fb371d5) → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` 399ce03d3842c0150643ab80607f6352f26d5a5d0bdf0d55ae1f15a6c8575565 → 293120368b5d791727738d56e4078129e4b4de07d5c8287cf0cef7cade2e58c3; `builder/build.py` 1c37f77de159ff6bd930af486f10d435ee4da000744497d16204ffd92a5eb821 → 2fb5af98f8c7d745db17f0032c18c9fb15c5080e03336bd298d45947715a4101. A double scratch rebuild of every builder in dependency order was byte-identical; `cases/PINS.json` was re-pinned.

Frozen after the scoped re-check of revision 3 (all review-precise-2 findings closed; one stale lease sentence, fixed here by LEAD). Pins: manifest 842ced201a3c123f327ad18ec4e24c8834d4ba3712546bce8dd9404458a9abff, submissions e19bc64bf6b9d388ca355fcb5de5160be1c4c0e7e27d3b348f1996a17fbd93d7, expected 549d5ef3dad0ceab4486f4ca351dad14051bd2c89841bc3c478d17e978223170, builder 037b3e9d3193e68ec47086b062f10f07b28a181b72d4325e4028e8c154d573d9. The manifest's `status` still names the draft; the freeze is this header, not a re-pin. `refusal_rules.order`'s "a shape failure returns alone" applies per item, in the six steps of `refusal_rules.basis_fraction_order`. The seven shape-step issue texts are this lease's own (no product helper exists); the core must emit them exactly.

Former draft heading follows.

_CP-1D (Earnings quality) owner lease: DRAFT revision 2 (fix round 1) for LEAD, 2026-10-28_

Pre-code draft by the `cp1d-owner` preparation task. Oracle: `cases/cp1d-owner/{manifest,submissions,expected}.json`, builder `cases/cp1d-owner/builder/build.py`. No product code or test written or run.

## Why

methodology.json: CP-1D (alias CP-1E) "challenges the adjusted-EBITDA bridge: tests each add-back for achievability and recurrence against evidence, reconciles adjusted EBITDA to cash, and restates leverage on the earnings the evidence supports". Required CP-0, CP-1 (edge `block`), optional CP-1B (edge `restricted`). `plan(("CP-1D",))` = (CP-0, CP-1, CP-1D). Python computes the bridge, add-back shares, CFO/EBITDA and restated leverage; the analyst gives achievability, recurrence and the accepted fraction as literal input. FP02 (earnings_update) section.

**Frozen pack finding.** The frozen financial pack carries no add-back bridge. Page:1 says "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete."; page:2 Adjusted EBITDA = Reported EBITDA = 30.0; page:5 "Adjusted EBITDA equals reported EBITDA because there are no adjustments". A real promoted CP-1 head (probe) has `T4.17` with 0 facts, and CP-1 refuses a partial or undisclosed add-back disclosure (`financial_adapter._addbacks`), so an empty T4.17 means a complete zero bridge. The frozen source cannot be edited, and an add-back claimed as an occurrence would contradict it.

**Synthetic source (the only addition).** One new pack source `bridge`, "Management financing-case EBITDA bridge" (1 or 2 pages). It carries management's PROPOSED financing-case adjustments, explicitly "not recorded in the statements": four items (procurement savings 3.00, head-office reorganisation savings 1.20, legal and advisory fees 0.80, insurance and facilities savings 1.00; total 6.00; management EBITDA 36.00) and a supporting schedule. It restates reported and adjusted EBITDA as 30.0, contradicts no frozen figure (list in manifest `synthetic_source.consistency_with_frozen_figures`) and is needed because no frozen source has an add-back to challenge. The frozen pack alone is kept as case `statements_only`.

## Live-contract or owner-only

`registry.step_chain("CP-1D")` raises "CP-1D has no live step contract" (probe; also for the alias CP-1E). CP-1D is **owner-only** (`docs/G1X-OWNER-CORE-PROTOCOL.md` §1): `entry="owner_core"`, the core supplies every §2 item, no `src/deploy_vii` registry edit. CP-0's validator accepts a CP-1D consumer row without a step chain (probe: no issues, T8 "Run CP-1D"; refused case "DO NOT RUN"), because `readiness.live_consumers` is just `plan` minus non-consumers.

## Prerequisites

1. G1 plus the S1a extension and G1-X integrated (owner_core entry, `_VIEWS`, `_CORES`, `inputs="module_context"`).
2. Host work (H1): CP-1D opens a `SourceSession` over a fixed host-side scope mapping (identity, financial, bridge; statements_only: identity, financial), per `docs/G1X-OWNER-CORE-PROTOCOL.md` §3 (an owner-only step may combine a `module_context` view with pack sources). Python and the pack tools carry the evidence; no pre-cut evidence lines.
3. Pins: financial manifest `6b3eeffe…b93432`, snapshot submissions `bff9ed18…b35c`, methodology.json `348fbc4b…8d45`.

## Files

- New `src/deploy_workflow/owners/cp1d.py`.
- `owner_workflow.py`: `OWNER_SPECS["CP-1D"]`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS` registrations.
- D12 one-line registrations: `methodology.json` CP-1D `table_ids` -> `T1D.1`..`T1D.7` (drop `T1E.*`); new `bindings/cp1d.py` (data only, D12 amendment §6) + `shipped.py`; `report_view.py`: `_EARNINGS_QUALITY` `_Spec` rows, `_spec_of` tuple, the two block ids after `ebitda-adjustments` in `earnings_update`.
- TOOL-CONTRACT row for CP-1D `earnings_quality` (LEAD amends at freeze). `methods/cp1d.md` (adaptation record).
- G2: `DeliveryScope(scope_id="cp1d-fp02-quality", pathway="earnings_update", requested_modules=("CP-1D",), sections=("earnings-quality","restated-leverage"), rails=("evidence","limitations"))`.
- New `tests/test_owner_cp1d.py`, `tests/cp1d_runs.py` (`cp1d_closed(case, root)`).

## Public API (`owners/cp1d.py`, keyword arguments except `store`)

```
MODULE_ID="CP-1D"; STEP_ID="earnings_quality"; STEP_IDS=(STEP_ID,)
QUALIFICATION; SCHEMAS={STEP_ID: EarningsQualitySubmission}; RULES(text, seen) -> tuple[str, ...]
parse_bridge(source) -> BridgeRows | None          # the lease's table rule below
cp1d_upstream(store, attempt) -> Upstream          # CP-0, CP-1 required, CP-1B status only
validate_earnings_quality(*, pack, submission, upstream) -> tuple[str, ...]
earnings_quality(*, pack, submission, upstream) -> Report     # raises ValueError on any issue
context_block(*, pack, upstream) -> dict           # the exact read_inputs view
cp1d_module(report, *, inputs, attempt) -> Module
submit(store, ticket_id, step_id, payload, rules) -> Submitted
view(historical, attempt) -> tuple[str, str]; probe(store, snapshot, attempt) -> None
```
Step `earnings_quality`: `inputs="module_context"`, `sources=True`, `rules="journaled"`; no `precheck`. `RULES(text, seen)` (G1-X §2, amended 2026-10-28) is the tool-use evidence rule: it reuses `live/tools.py` `unread_citation_issues` (exact text `Cited page not read through read_pages: <source_id> page:<n>`, product sorted order) and `UNBACKED_ABSENCE`; G1-X calls it at submit and in the verifier in place of `ToolRules().issues`. CP-1D's schema has no `ABSENCE_MARKERS` value, so only the cited-page rule can fire. All other content rules are journaled validator issues.

## Submission schema (reference and judgment only; no computed number)

```
EarningsQualitySubmission: assessments: tuple[Assessment,...]; overall: Overall; gaps: tuple[Gap,...]
Assessment: addback: str (exact bridge row label), achievability: Supported|Partly supported|Not supported|Insufficient evidence,
            recurrence: Non-recurring|Recurring|Not applicable|Not assessable, accepted_fraction: str|null, accepted_basis: Citation|null,
            category, rationale (refs only), evidence: tuple[Citation], limitation|null
Overall: rationale, category, confidence, limitation, evidence: tuple[Citation] (required when no bridge); Gap: gap, why_it_matters, affected_analysis, severity, action
```
Prose carries no digit outside `{ref|unit}`; refs name module facts (`{T1D.1.a01.claimed|US$ m}`) or CP-1 facts (`{{FIG:name|token}}` bound at run time). Citations are checked against the pack by `citation_issues` (verbatim quote under the located page) and against `Seen`: every cited page must have been returned by `read_pages` in the step (evidence, `accepted_basis`, `overall.evidence`).

**Partly supported (Python owns arithmetic).** Exactly one of `accepted_basis` (a citation whose quote holds exactly one source amount; Python computes the share = that amount / proposed amount, one 38-digit half-even division, and accepted = the cited amount; fact `T1D.2.aNN.basis` value_class `source`, `applied_fraction` calculated from basis and claimed) or `accepted_fraction` (analyst judgment with no source amount: value_class `analyst_judgment`, no calculation id, limitation "Accepted fractions given without a source amount are analyst assumptions without a source calculation."). Confidence is never High with a bridge present. Procurement (a01) uses the computed path: 1.80/3.00 = 60.0%. The analyst-fraction path is pinned by the composer fixture `expected.json composer_fixtures.analyst_fraction`; r05 is its only refusal literal.

## Decimal composer and rules (zero / missing / not_applicable / blocked distinct)

Bridge parsing (core rule, builder transcribes it): page:1 must start a line `Basis: FY2025 (January 1-December 31, 2025)`; the table follows the header `Item  Type  Status  Amount`; rows split on two or more spaces: 4 fields = item, 2 fields = total (`Total proposed adjustments`, `Management financing-case EBITDA`); amount is a decimal or `Not stated` (missing). Unparseable bridge: attempt invalid (`Bridge table not found`, returned alone; fixture `manifest.synthetic_source.fixtures.bridge_table_not_found`, refusal r14) -> blocked after two failures.

Operands (T4.10, LTM Q4 25 column; selection rule in manifest): `adjusted_ebitda` S, `ebitda`, `cfo_adjusted` C, `total_debt` D, `net_debt` N, `total_leverage_adjusted`, `net_leverage_adjusted`. Statement add-backs = S - ebitda.

| Quantity | Recipe |
|---|---|
| applied fraction f | Supported 1; Partly supported = basis / proposed (source path) or accepted_fraction (analyst path); Not supported 0; Insufficient evidence 0; Recurring forces 0 |
| accepted_i | 0 if f = 0 (known; derives from applied_fraction, never from a missing claimed), the cited basis amount on the source path, else claimed_i x f (analyst path) |
| claimed, accepted | sums; claimed missing if any amount is Not stated; without a bridge `claimed` is not_applicable and `accepted` is a known 0 (derives from `[]`); an item with f = 0 has accepted known 0 deriving from its `applied_fraction` |
| management EBITDA / supported EBITDA | S + claimed / S + accepted |
| shares | claimed/management (iff > 0), accepted/supported, accepted/claimed (claimed = 0 -> not_applicable "No add-backs claimed") |
| cash conversion, leverage | C/EBITDA, D/EBITDA, N/EBITDA per basis (statements, management, supported), iff EBITDA > 0 |

Each quotient is one division of exact decimals (38 digits half-even). Controls: statement-basis leverage recomputed equals CP-1's reported ratio exactly (difference 0); stated bridge totals tie to the recomputed rows ("Reconciled"/"Differs"/"Not compared"). A missing amount never becomes 0; a known 0 (accepted = 0 by rule, statements add-backs = 0) is shown as 0.

Expected values (positive): claimed 6.00, management 36.00, accepted 1.80 (the cited contracted amount; share 1.80/3.00 = 60.0%), supported 31.80, not accepted 4.20; shares 16.7% / 5.7% / acceptance 30.0%; CFO conversion 63.3% / 52.8% / 59.7%; total leverage 1.67x / 1.39x / 1.57x; net 1.00x / 0.83x / 0.94x. `statements_only`: add-backs known zero, management basis not_applicable, supported = 30.00, 1.67x. `gap`: claimed, management, shares and management leverage missing; accepted 0 (all Insufficient evidence); supported = 30.00.

## Refusals

Nineteen literal invalid payloads (`submissions.json refusals`, issues in `expected.json refusals`): unknown add-back; add-back not assessed; fraction missing / unexpected / out of range; evidence required; recurrence does not fit the type (Saving requires Not applicable; Cost requires Non-recurring, Recurring or Not assessable; Not assessable only with Insufficient evidence; so the gap legal-fees row Cost / Not assessable / Insufficient evidence is valid); bare figure (the core calls `prose.issues(rationale, bound)` and emits `Bare figure: 1.2` unchanged; a settled-claim path prefixes `Claim T1D.2.a02: `); unlocated quote (`Quote/locator mismatch: quote not found under bridge page:2 (`, text probed on the product function); confidence High (refused whenever a bridge is present: the management basis); accepting an unstated amount; assessment with no bridge (own text `Assessment given without a bridge in the pack: <label>`, no Unknown add-back issue); bridge table not found; evidence required with no bridge; basis and fraction both given; basis amount not below the proposed amount; basis quote without exactly one amount; basis on another achievability. The per-assessment basis/fraction rules are shape rules checked in a fixed order, the first failure returned alone for that item and its prose not checked (`refusal_rules.basis_fraction_order`): basis or fraction on another achievability (basis first); both given; neither given; fraction range; basis quote exactly one amount; basis bounds. With no bridge, `overall.evidence` (a located citation) is required (confirmed rule, r15), so tool use is never vacuous. The analyst-fraction path has a composer fixture (`expected.json composer_fixtures.analyst_fraction`). Basis-or-fraction missing on Partly supported replaces the old fraction-missing text. Each is an invalid attempt 0, re-begun; two failures (`blocked`: r06, r06) settle the head blocked. Tool-level (`submissions.tool_refusals`): `cited_page_not_read` (invalid attempt 0 with `Cited page not read through read_pages: bridge page:2`, re-begun with `repair_of`), invoke of any non-pack tool `not_permitted` (refused receipt recorded; no step journaled; no attempt consumed), submit without `read_inputs` a raised `WorkflowError("not_permitted")` (`expected_error`; nothing written); snapshot change `stale_binding`; CP-1 missing -> `RefusedBegin` (refused case).

## Tool use (D2)

Pack tools plus the view (G1-X §3): `read_inputs` serves the exact view `context_block`, and `read_pages`/`search_pack` over the host-mapped sources (identity, financial, bridge) carry the evidence. The view carries no evidence lines. Key tree (shape; the implementer commits `cases/cp1d-owner/cp1d-view-tree.json` from product-settled heads):
```
upstream: [{module_id, status}]
bridge: {state: present|absent, source_id, pages: [locator], items: [{row, label, type, status, claimed_ref|null, claimed_shown|null}], totals: {...}|null}
cp1_facts: [{ref, label, period, unit, shown}]   cp1_t417_rows: int   cp1_facts_note: str   inherited_limitations: [str]
```
Acceptance: exactly one ok `read_inputs` before the submit and ok `read_pages` calls covering every cited `page:N` (S1a lease :131 pattern). Literal sequences: `submissions.json <case>.tool_calls` (positive: read_inputs, read_pages bridge page:2; statements_only: read_inputs, read_pages financial page:1, cited by `overall.evidence`; gap: read_inputs, read_pages bridge page:1, no citation). Rules mode: `rules="journaled"` with the core `RULES(text, seen)` above.

## Consumption proof (D3)

No consumer core exists. `methodology.json` lists CP-1D optional for CP-2, CP-2G, CP-2H, CP-3 and CP-4; CP-2G requires CP-2A and CP-2H requires CP-2G, and both are unleased; the shipped CP-2 core reads CP-1 and CP-1A, CP-3 `READ_OPTIONAL` is CP-1A and CP-4, `methods/cp4.md` ruling 5 has CP-4 not read CP-1D; CP-6 has no edge; CP-5 counts only after a lease extends its scope. **Consumption stays open** until a consumer reads the settled head: the consumer's attempt inputs bind `Input("CP-1D", head.result_sha256, status)` and a consumer fact or claim derives from `T1D.3.supported.value`, `T1D.6.supported.total_leverage` and `T1D.6.supported.net_leverage` (consumed through the CP-1D head, not CP-1). A lease amendment that has CP-2, CP-3 or CP-4 read CP-1D, or leases CP-2G/CP-2H, closes D3. First run closes at settled head, verified receipt, rendered FP02. `docs/MODULES.csv`: `downstream_consumption: open`.

## CP-1B (optional upstream)

- **Unbound** (every case; G1 cannot drive CP-1B): inputs prepared-pack, CP-0, CP-1; own limitation (unbound wording) "CP-1B (earnings update) is not part of this run, so its variance evidence is not read."
- **Settled**: bound with the head's status; v1 reads no CP-1B fact (reading nothing keeps D3 honest); own line (bound wording) "CP-1B is bound but its variance evidence is not read in this version."; inherited limitations carry CP-1B's.
- **Blocked** (S1a A3b pattern): restricted edge, so CP-1D begins with input CP-1B `status=blocked`; own line is the bound wording above, followed by the inherited lines `Upstream CP-1B blocked: <each CP-1B limitation>`; head restricted. Not run-testable until CP-1B is a G1 spec (B1); the literal fixture is `expected.json cp1b.blocked.fixture` for a hand-built snapshot test of `current_inputs`/`inherited_limitations`.

## Rendered sections (D7)

`ebitda-adjustments` stays CP-1/MODEL. New blocks, owner CP-1D, kind dense, producers `("CP-1D",)`, route "Full analysis", inserted after `ebitda-adjustments` in `earnings_update`: `earnings-quality` (tabs T1D.2, T1D.3, T1D.5) and `restated-leverage` (tab T1D.6). Evidence rail T1D.1, T1D.4, `cp1_references`; limitations rail T1D.7. Block state `populated`; non-known cells spelled by `fact_spelling` (`expected.json cases.<case>.FP02`).

## Table ids (D8)

T1E.1-T1E.6 and T1D.1-T1D.7 are listed only under CP-1D in `methodology.json`; no other module lists either family; no definition exists in the repo or the DEPLOY VII docs. No collision. Register **T1D.1-T1D.7** (matches the module id) and drop T1E.*. Tables: T1D.1 add-back register, T1D.2 assessment, T1D.3 bridge, T1D.4 tie-out and CP-1 reconciliation, T1D.5 add-back share, T1D.6 cash conversion and restated leverage, T1D.7 gaps ledger, plus `cp1_references`.

## Acceptance (expectations only from `expected.json`)

A1 positive, A1b statements_only, A2 gap: plan CP-0, CP-1, CP-1D; heads restricted; CP-1D facts, tables, claims, own limitations, FP02 equal expected; inherited limitations per `execution.py:345-366`. A2b refused. A3: refusals above, blocked, tool-use refusals on clones. A4 tamper: edited read body (forged consistently), step output, `SettledHead` -> `identity_mismatch`. A5 `test_owner_workflow.py`/`test_owner_s1a.py` unchanged. Gates: ruff check, ruff format --check, mypy --strict (`MYPYPATH=src`).

## Deferred test commands (build-first)

`PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_owner_cp1d.py` (heavy: a genuine CP-1 promotion per case, 11-26 min, module-scoped fixtures, one job under the lock). Oracle rebuild: `python3 -I cases/cp1d-owner/builder/build.py`, then compare sha256 of the three files.

## CP-1 readiness for CP-1D (LEAD ruling S6)

The run requests the consumer CP-1D, so the CP-1 `readiness` step carries the literal in `submissions.json <case>.cp1_readiness` instead of `{"consumers": []}`: one `consumer_specific_cp1_sufficiency` requirement, status `limited`, evidence the FY-2025 KPI records for adjusted_ebitda, ebitda, cfo_adjusted, total_debt, net_debt, and one `relevant` gap assessment over every `inputs.narrative.gaps[*].gap_id` in order. Ids are bound at run time (selection: the first catalogue record of kind `kpi` with that key whose `value.observation_ids` contains an id ending `-fy-2025`; `inputs_sha256` prefilled). Probe on a copy of the S1 positive head: `validate_downstream_review` returns no issues; `_assess_consumers` gives `ready_with_limitations`, no unassessed requirement, 0 unassessed gaps, no blocking gap (1132 gaps, all WARN).

## Open questions for LEAD (all ruled 2026-10-28; recorded for traceability)

1. Evidence access: pack tools in a `SourceSession` over the H1 mapping plus the `module_context` view (ruled).
2. Synthetic source as management proposals "not recorded", now stating they are not pro-forma adjustments (ruled).
3. Supported basis keeps accepted unrealised savings, statements basis shown, two limitations (ruled).
4. Insufficient evidence = accepted 0 as a rule outcome (ruled).
5. CP-1B bound: read nothing in v1.
6. CP-1 readiness literal (above).
7. Run without CP-MODEL: `registry.plan(("CP-MODEL","CP-1D"))` = (CP-0, CP-1, CP-1D, CP-MODEL), so CP-MODEL would follow CP-1D; it precedes CP-1D only when CP-1B is also planned, which G1 refuses (analytical after deterministic) until a lease supports it. Model-owned FP02 blocks stay idle in these cases.
8. Fractions: Python computes the share from a cited source amount; a fraction with no source amount is an analyst judgment with a limitation and confidence never High.
9. `cfo_adjusted` is the CFO operand.

Not verified: no CP-1D core, composer, renderer or run exists, so table layout, claim templates, block tabs and the view tree are checked only by product `Fact`, `fact_spelling`, `prose.issues`, `citation_issues`, `validate_review`, `validate_source_context` and `validate_downstream_review` probes; bridge handling by CP-1's later stages, the readiness literal on a pack with the bridge source, whether a block may bind three tabs, the CP-1B settled/blocked paths, the host mapping, `Seen` checks and `RULES` at run time are unchecked; issue texts other than the citation, bare-figure and `Cited page not read` ones are this draft's own proposal.
