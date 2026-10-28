# CP-3D (Market implied risk) owner lease — FROZEN by LEAD 2026-10-28 (draft rev 2 + revision 3)

Amended by LEAD 2026-10-28 (CP-6 freeze re-pin, `work/lead/cp6-freeze/report.md`): `src/deploy_vii/methodology.json` registers `T6-FINAL` under CP-6 `table_ids` (ruling Q7), 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 → 0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8; this module's builder re-pins it and its manifest records the new hash. Only pin hashes move: no other leaf of this module's oracle changes. It reads `cases/cp3-cp6-owner/manifest.json` without a pin (through `MARKET_FILE`); `market_source` did not change. Own files, old → new sha256: `manifest.json` bc7b29acd9f40769e63577331e17f2f11323709833f1eca1bddddc3a9fa0e070 → 2d21896a53afea7a6e42c0ae8b98b2f12be27f07550164245e04d6119586ec92; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` 09a47c870ea9436ba880aa60108ec646efb06c085b566c0dd180d368446c789b → 36d576397d9ae4c190daf07147932edb249880af7b9c6b86de8db98d7b069510.

Amended by LEAD 2026-10-28 (Stage 1 release batch, `docs/rulings/2026-10-28-stage1.md`; `work/lead/stage1-release/report.md`): X1 (i)-(v) claim branches, 6e (g) and (h): LVL-01 for bid only, offer only and talk only; PD-01 for a mid above par; YLD-01 for a quoted level with no maturity date or with no mid margin; the T3E.7 `Simple discount margin` row names the first missing cause; fix round 1 (owner-approved, pre-existing P1): the bid+offer LVL-01 line takes its date from the bid observation (the lease requires bid and offer dates to be equal) instead of `observations[0]`, so a talk-first order no longer writes `On None`. Builder only: no frozen case reaches the changed branches, so manifest, submissions and expected are unchanged. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` fb72aa38f0310ee9b40c4b97774262043f8421ab0c58a481a3a304059dd69ed8 → 09a47c870ea9436ba880aa60108ec646efb06c085b566c0dd180d368446c789b. A double scratch rebuild of every builder in dependency order was byte-identical. Pin consumers: none (no other builder pins or reads this module's files). Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change.

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 59244427… → fb72aa38f0310ee9b40c4b97774262043f8421ab0c58a481a3a304059dd69ed8; manifest dee1a8f3… → bc7b29acd9f40769e63577331e17f2f11323709833f1eca1bddddc3a9fa0e070; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

Frozen after `review-precise-2.md` (CHANGES REQUIRED: M1, L1, L2, all mechanical) and revision 3, which LEAD checked inline as that review allowed: rebuilt twice from a scratch copy with `python3 -I`, identical; structural diff of expected.json against revision 2 is only the `market-against-fundamentals` tabs (3 → 6) and the removed `unbound_tables`; lease, methods :15 and `search_pack_min` as ruled. Pins: manifest dee1a8f360852f63c530b9a0472fae913e9b5ba40b65b050ee300f827f86010d, submissions 9263752346480a48571f0065eb864595bd4489ce4ce4fd675e967b401cde86de, expected 67e8507fd28b936877d24157af29407fb63e97e87130f23190dc19765c7a89e5, builder 592444279995ff4bb37ecedc6e77f9fc5c350a4eccfebaade4f12b7e7e93c4a9; FP03 design reference sha256 89a15ee632ba4082a60ea8a895a6a9b0471e643e13e657782bdcf80e429d9a4f. The manifest's `status` still names "DRAFT revision 2"; the freeze is this header, not a re-pin. `methods-cp3d-draft.md` is committed as `docs/methods-drafts/cp3d.md`; the build moves it to `src/deploy_vii/methods/cp3d.md`.

LEAD rulings on the questions still listed open below: 2 resolved as stated; 6 accepted (methods record committed; `T3E.10` unused); 12 done (architecture row amended at freeze); 13 accepted as stated (70 percent is an unsourced analyst convention, D11, recorded in the limitations); 14 accepted (core unit test over a synthetic page, no oracle literal); 15 accepted (absence, then unread, as `ToolRules.issues`).

Former draft heading follows.

_CP-3D (Market implied risk) owner lease: DRAFT rev 2, 2026-10-28 (mx-feature preparation, pre-code; fix round 1 of review-precise-1)_

Pre-code. Nothing here is frozen or reviewed. Oracle: `cases/cp3d-owner/` (manifest, submissions, expected, stdlib builder). No CP-3D core exists, so this lease designs one (`src/deploy_workflow/owners/cp3d.py`); it writes no code. Every G1 seam is `docs/G1X-OWNER-CORE-PROTOCOL.md`, which supersedes any signature this lease states differently. The method record is `work/lead/cp3d-owner-preparation/methods-cp3d-draft.md` (becomes `methods/cp3d.md` at freeze, D12).

Rev 2 applies the LEAD rulings at the end of `review-precise-1.md` (F1-F9, Q4-Q6) and of `report.md`: the protocol `RULES` attribute for the two tool-use refusals (F1); host-side H1 scope, no precheck, Q10 wording (F2); FP03 ownership per the design reference (F3); the reference rate level validated, the level-to-kind binding, term absences, the rating limitation, and the F9 corrections (F4-F7, F9); recovery 70 percent with its rationale and limitations (Q4/F8).

## Why

CP-3D answers one question: what credit risk does the market level of the issuer's instrument imply, and how good is the evidence? Python computes price metrics, a simple discount margin (spread) and, when a recovery assumption exists, a market-implied default intensity and cumulative default probability; the analyst judges only the technicals (quote quality, trading activity, talk versus quote, rating) and one summary. The architecture row (`docs/reviews/owner-harness-architecture.md:68`) names the split.

Edges (`methodology.json`, `registry`): required CP-0 (`edge_rule("CP-3D","CP-0") == "block"`), optional CP-2H (`restricted`; CP-2H is not built, so it is unbound, never selected and never read). Purpose: "Assesses market-implied credit risk and trading technicals." CP-1 is not an edge: CP-3D cannot read facility facts from a CP-1 head, so the contractual margin and amortisation are quoted from the financial source page.

The r14 CP-3D SKILL.md is not in this repository (same situation as CP-2D, decision 0005). The titles and columns of `T3E.1..T3E.9` are this preparation's adaptation record; LEAD confirms (open question 6).

## FP03 ownership (D7) and the architecture-row conflict

Governing reference (read only, outside this repository, never edited, not depended on at run time): `/Users/ericguei/Documents/DEPLOY VII/design/reference/rbot-fp-03-relative-value.dc.html`, sha256 `89a15ee632ba4082a60ea8a895a6a9b0471e643e13e657782bdcf80e429d9a4f` (checked 2026-10-28). Its block headers assign:

| FP03 block | Header in the reference | Ruling |
|---|---|---|
| `instrument-levels` | "CP-3 - 11 rows" | stays CP-3's; deferred to a later CP-3 FP03 lease. CP-3D does not register it. |
| `yield-against-maturity` | "CP-3D - Fig. RV.1" | CP-3D's own, **deferred**: a chart with series logic, and the pack states no reference rate level so there is no yield to plot (not admitted under Q10). |
| `market-against-fundamentals` | "CP-3D", with an "ILLUSTRATIVE alignment" tag | CP-3D owns it as a dense `_Spec`. The reference draws an alignment panel (market implication against fundamental, per-row alignment chip) beside a market-implied default frame ("needs spreads and a recovery assumption"). CP-3D populates the market-implied default panel and shows the alignment half as an **honest partial** (not populated; own limitation, below). |

**Recorded conflict.** `docs/reviews/owner-harness-architecture.md:68` gives `instrument-levels` to CP-3D; the FP03 design reference gives it to CP-3. By the LEAD ruling the design reference governs. The architecture row stays stale until LEAD amends it; this lease does not edit it.

The alignment half is not populated because CP-3D reads no fundamental comparator (its only upstream is CP-0). Own limitation (T3E.9, all cases): "The alignment of the market-implied view with the fundamentals is not shown: no fundamental comparator is bound, so only the market-implied default half of the market-against-fundamentals block is populated".

## Module kind (G1-X protocol section 1)

`registry.step_chain("CP-3D")` raises "CP-3D has no live step contract" (checked 2026-10-28). CP-3D is an **owner-only module**: `OWNER_SPECS["CP-3D"]` uses `entry="owner_core"`; the core supplies every item of protocol section 2 that applies: `QUALIFICATION`, `probe`, `STEP_IDS`, `SCHEMAS`, `submit`, and, because the step has `sources=True`, `RULES(text, seen)`. `view` is not needed (`inputs="none"`); `precheck` is not used (below). No `src/deploy_vii` registry edit. `registry.plan(["CP-3D"])` already returns `('CP-0','CP-3D')` (checked).

## Prerequisites

1. S1a integrated (G1 extension for CP-1A and CP-2) then G1-X (protocol, including the `RULES` routing amendment of 2026-10-28).
2. **Pack sources.** Protocol section 3 admits `sources=True` on an owner-only step. CP-3D reads pack pages (market page:1 and page:2, financial page:5). Scope is the fixed host-side mapping built by the H1 host task: `_SOURCE_STEPS["CP-3D"] = ("market_implied",)` with readable sources **market and financial only** (the identity source is not readable by CP-3D). It is never caller-supplied and never `live/context.py` `SOURCE_SCOPES` in `deploy_vii` (not edited). The generic `*-submission` producer rule covers CP-3D's tail `market-implied-submission`. (F2: this replaces the rev 0 "every pack source" grant, which contradicted Q3.)
3. **Tool-use rules through `RULES`.** G1 routes `rules="journaled"` to the core attribute `RULES(text, seen)` at submit and in the verifier (protocol section 2). The G1 evidence rule `_evidence_issues` returns () for `market_implied`, and `ToolRules().issues` raises for a step that is not a tool-loop step, so the product path cannot produce these refusals (review-precise-1 F1, reproduced). The core reuses `live/tools.py`:
   - `unread_citation_issues(text, seen)`: `Cited page not read through read_pages: <source_id> <locator>`, one per cited `page:N` never returned by `read_pages`, **sorted by (source_id, locator)** (so `financial page:5` precedes `market page:1`);
   - `UNBACKED_ABSENCE` ("Absence claim without a recorded search"), emitted once when the payload holds any **absence object** and `seen.searched` is empty. Absence objects: `market_absence`, `terms.maturity.absence`, `terms.margin.absence`, `terms.amortisation.absence`, `terms.reference_rate.absence` (F6). `recovery_absence` is not one: it says the analyst did not assess a recovery, not that a source lacks something.
   Order follows `ToolRules.issues`: absence first, then unread citations. The oracle has no case in which both fire.
4. `docs/TOOL-CONTRACT.md` matrix row: CP-3D `market_implied`: `search_pack` and `read_pages` over the market and financial sources, no upstream view, no `read_inputs`, no `extract_statements` (the CP-1A row without extract).
5. FP03 rendering path (G2): Rendered sections below.
6. A CP-0 literal for the run (`submissions.json#readiness_review`); CP-0 is the only upstream.

## The run

New run `slice-cp3d-positive`: pathway `relative_value`, `requested_modules = ["CP-3D"]`, plan `CP-0, CP-3D` (checked against `registry.plan` and the methodology file by the builder). Pack: identity and financial bytes from `cases/financial/manifest.json`, market bytes from the CP-3 preparation's frozen sheet (`cases/cp3-cp6-owner/manifest.json#market_source`, source sha256 `c175d14b…f774b7` pinned in the builder; the file itself is not pinned because another preparation owns it). The run needs **no CP-1 promotion** (CP-1 is not an edge): CP-0 settles through its review submission and CP-3D settles through its own submit.

Cases (three CP-3D submissions; the first two share one settled CP-0 by clone):
- `positive`: bid, offer, talk quoted; margin, amortisation and maturity quoted; reference rate level absent; recovery 70 percent (D11, first-lien loan CDS convention).
- `gap_no_recovery`: the same quotes, `recovery_absence` instead of a recovery: default measures missing, discount margin still known.
- `gap_no_market`: pack without the market source (`slice-cp3d-gap-no-market`; CP-0 pins CP-3D `READY_WITH_LIMITATIONS` plus gap `missing-market-source`); `observations: []` with `market_absence`; every price-dependent figure missing, each gap reason says that no market level exists.
- Composer-only fixtures (`expected.json#fixtures`, derived values only, no run): `fixture_with_benchmark`, `fixture_above_par`, `fixture_bid_only`, `fixture_zero_recovery`, `fixture_no_margin`.

CP-MODEL is not requested (the plan would put it before CP-3D, and G1 refuses an analytical module after a deterministic one; CP-3D does not need it).

## Method (what Python computes; every value is a Decimal)

Full conventions: `methods-cp3d-draft.md` and `expected.json#arithmetic`. Summary:

1. Levels are a percentage of par, stored as `decimal_fraction` (98.50 is 0.985). Mid = (bid + offer) / 2 (98.875). Bid-offer width, discount to par at mid, and (context only) indicative talk less mid are exact differences.
2. Day count Act/365 Fixed from the quotation date (the `as_of` of the bid and offer, which must be equal) to the final maturity date: 1452 days, years = 1452 / 365. Years are **stored to 0.01 for display (3.98) but every later step uses the unrounded value** (3.97808…); with 3.98 the offer margin would be 18.8 bp, not 18.9.
3. Annualised discount to par (bp) = (100 - price) / years x 100; simple discount margin (bp) = cited contractual margin + that discount. Convention (loan-market discounted-spread form): redemption at par at final maturity, no amortisation (a cited zero is required), quotation date as settlement date (a settlement lag of about a week is ignored); **not divided by price** (dividing gives 38.3, 28.6, 19.0 bp), **not the three-year-life convention** (the remaining life is used); a floor on the reference rate does not enter a margin. Stored to 0.1 bp. Positive: bid 37.7, mid 28.3, offer 18.9.
4. All-in yield (simple) = reference rate level + discount margin / 10000. **The level is in no frozen source, so the yield is Not calculable in every pack case** (status `missing`, shown `∅ G#`, never 0, never assumed). The formula is exercised by `fixture_with_benchmark` (test vector 4.30 percent, a pure-function input, not a source figure) and, in the builder only, by a throwaway quoted level that exercises the validator, the yield cells and the yield claim (nothing of it is written out).
5. Annual default intensity (bp) = discount margin / (1 - recovery) (credit triangle); cumulative default probability to final maturity = 1 - exp(-(intensity / 10000) x years), unrounded intermediates, stored to 0.0001 and shown to two places as a percent. **Recovery 70 percent** (analyst literal, D11; rationale "first-lien loan CDS convention"; the frozen financial page:5 states "a senior secured term loan"; the 70 percent convention is the analyst's knowledge, **not sourced and not verified against a source**, and the limitations say so). Positive: intensity bid 125.7, mid 94.3, offer 62.8 bp; probability 4.88, 3.68, 2.47 percent. For comparison, the senior-unsecured CDS convention of 40 percent would give 47.1 bp and 1.86 percent at the mid. A higher recovery raises the implied intensity and probability for the same margin (own limitation). Discount margin <= 0 gives `not_applicable` (shown `∅ G# n.m.`).
6. Indicative talk enters no spread, yield or default figure. Its period is the commentary publication date, "Commentary published 2026-01-10" (page:2), not the quotation date (F9a).

Missing rule: any missing operand makes each dependent value missing with a stated reason; nothing defaults to 0 or N/A. Zero is a known value (contractual margin 0 bp is a known 0). With no market source every gap reason is "No market level: the pack holds no third-party market quotation source" (F9c). Blocked is the module-level state (a blocked or stale CP-0 refuses `begin`).

## Files

New: `src/deploy_workflow/owners/cp3d.py` (core, about 450 lines); `tests/test_owner_cp3d.py`; `tests/cp3d_runs.py` exporting `cp3d_closed(case, root)` (pack assembly, literals, run-time substitutions, tool-call sequence; G2 imports it).

`owner_workflow.py` (G1-X): `OWNER_SPECS["CP-3D"] = OwnerSpec("CP-3D", (StepSpec("market_implied", MarketImpliedSubmission, sources=True, extract=False, upstream_grant=None, inputs="none", rules="journaled"),), "owner_core", "analytical", None)`, `_CORES["CP-3D"]`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`.

D12 registrations (PM serialises; recorded in `docs/reuse/manifest.json`):
- `host.py`: `_SOURCE_STEPS["CP-3D"] = ("market_implied",)` with the fixed scope market and financial (with the H1 task).
- `bindings/shipped.py`: `CP3D` in `SHIPPED_MAPS` after `CP3`; new `bindings/cp3d.py` (FP block bindings only, no arithmetic, never imports `deploy_workflow`; protocol section 6).
- `report_view.py`: a new `_RELATIVE_VALUE` mapping with one `_Spec` row and one `_spec_of` loop entry (`report_view.py:1180`), the same shape as `_COVENANT_REFINANCING` (`:1124-1143`). Rows only, no logic: an admitted D12 registration under the Q10 ruling.
- G2 `owner_rendering.py` `DELIVERY_SCOPES` entry for `(relative_value, [CP-3D], synthetic)` (not on this branch).
- G1-X: the `RULES` routing for owner-only steps with `sources=True` (protocol section 2).
- `registry.py`: none. `methodology.json`: none (ids registered).

## Public API

```
owners.cp3d.MODULE_ID = "CP-3D"; STEP_ID = "market_implied"; STEP_IDS = (STEP_ID,); QUALIFICATION
SCHEMAS = {STEP_ID: MarketImpliedSubmission}
probe(store, snapshot, attempt) -> None                  # protocol: WorkflowError("identity_mismatch") unless the settled attempt and head rebuild exactly
submit(store, ticket_id, step_id, payload, rules) -> Submitted
RULES(text, seen) -> tuple[str, ...]                     # protocol section 2: unread_citation_issues (sorted) and UNBACKED_ABSENCE over absence objects
# internals (keyword arguments only)
cp3d_upstream(*, store, attempt) -> Upstream             # bound CP-0 head, current inputs, third_party sources from CP-0 T3, inherited limitations
validate_market_implied(*, submission, upstream, pack) -> tuple[str, ...]
compose(*, inputs) -> Derived                            # pure Decimal; no I/O
market_implied(*, pack, submission, upstream) -> MarketImpliedReport
cp3d_module(*, report, inputs, attempt) -> Module
cp3d_reader(store, head) -> Cp3dHead                     # the consumer reader (see Consumption)
```

## Submission schema (reference and judgment only; `submissions.json`)

Text fields are digit-free (figures are Python's). Quotes are verbatim page spans (`quotes.quoted`). A `*_text` value is a numeral that must occur exactly once as a whole token in its own quote; Python parses it with `Decimal`. The analyst never supplies a computed number.

| Field | Content |
|---|---|
| `instrument` | `name` plus the `quote` that contains it |
| `observations` | 0..3 of `{kind: bid|offer|indicative_talk, source_id, locator, quote, level_text, as_of_text}`; each kind at most once; the source must be a CP-0 T3 `third_party` source; `as_of_text` ("Month D, YYYY") required for bid and offer and must occur in the quote. **Level-to-kind binding (F5):** a bid or offer quote must contain `<kind> <level_text>` ("bid 98.50"); an `indicative_talk` quote must not contain `bid <level_text>` or `offer <level_text>` |
| `market_absence` | `{reason, follow_up}`; exactly one of `observations` and `market_absence` |
| `terms.maturity` | `{quote, date_text}` or `{absence}`; the date must follow the quotation date |
| `terms.margin` | `{quote, bps_text}` or `{absence}` |
| `terms.amortisation` | `{quote, value_text}` or `{absence}`; the value must be zero (the simple margin convention) |
| `terms.reference_rate` | `{name, quote, level, absence}`: `name` occurs in `quote`; exactly one of `level` and `absence`; **`level` is `{quote, percent_text}` and `percent_text` must occur exactly once as a whole token in its own verbatim `quote` (F4)** |
| `recovery` | `{percent_text, rationale}`, `0 <= x < 100`, uncited analyst assumption (D11) stored as an `analyst_judgment` fact; or `recovery_absence {reason, follow_up}`; exactly one |
| `technicals` | per aspect (`quote_quality`, `trading_activity`, `talk_versus_quote`, `rating`, each at most once): `{category: Documentary Fact|Analyst Interpretation|Insufficient Information, text, basis (quotes), limitation}`; Insufficient Information states its limitation and only it does; Documentary Fact needs a basis quote |
| `summary` | `{text}` (digit-free; becomes claim `CP-3D-VIEW-01`) |

## Composer: tables, claims, status

Fact ids `T3E.<n>.<row>.<field>`; facts carry `period` (quotation date, talk publication date, terms, or run as-of; a numeric fact requires it, `contracts.Fact`). Tables (`expected.json#cases.<case>.tables`):

| Id | Title | Content |
|---|---|---|
| T3E.1 | Market levels | bid, offer, talk: level, as-of, basis, source |
| T3E.2 | Price metrics | mid, width, discount to par, talk less mid, days, years (convention column states the unrounded use) |
| T3E.3 | Spread and yield | annualised discount, contractual margin, simple discount margin (bid, mid, offer), reference rate level (a quoted level shows as a `source` fact citing its quote), all-in yield (computed when the level is known, else a gap) |
| T3E.4 | Assumptions and terms | recovery, reference rate, maturity, amortisation, instrument |
| T3E.5 | Market-implied default | intensity and cumulative probability (bid, mid, offer) |
| T3E.6 | Technicals | analyst category and assessment per aspect, plus the summary |
| T3E.7 | Missing inputs | one row per not-calculated group with its reason (no market source: one row naming market levels and every dependent figure) |
| T3E.8 | Evidence | each cited page |
| T3E.9 | Limitations | one row per own limitation |

Claims (`CP-3D-LVL-01`, `-DM-01`, `-YLD-01`, `-PD-01`, `-VIEW-01`) hold figures only as `{<fact_id>|<unit>}` references to the module's own facts, and gaps only as `[<fact_id>]` chips. `CP-3D-YLD-01` is the gap form in every pack case and a figure form when a level is quoted (builder self-test). Findings of the claim check (Decision 0005 MC-2; `execution.py:296`): (a) a figure needs a citation or a calculation id, so the recovery assumption (uncited) can never be a figure in a claim; claims say "the analyst recovery assumption" and the number lives in T3E.4; (b) a chip must not name a known numeric fact; (c) dates are labels and pass; `Act/365` would be a bare figure, so conventions appear only in table text. Probe (read only, product `prose`): `prose.issues` and `bare_figures` on the text outside references: zero hits in all 15 claims.

Status: always `restricted` (own limitations are non-empty). Own limitations (positive): single dealer quotation with no reported trade; the rating limitation of the Insufficient Information aspect ("No rating agency has assigned a rating to the instrument", F7: every technical's limitation is also an own limitation); talk not used; reference rate level absent so no yield; recovery is an analyst assumption following the first-lien loan CDS convention, not a source figure, convention not verified against a source; a higher recovery raises the implied intensity and probability for the same margin; the simple margin convention ("not a Z-spread; not divided by price; not the three-year-life convention"); the whole spread attributed to default risk, risk-neutral, constant intensity; margin and amortisation read from the financial page, not a CP-1 fact; the alignment half is not shown; an absence is backed only by a recorded search over some source, not a search for the specific item (F6; present when any absence object is). Talk's limitation is present only when talk was observed (F9b). Inherited limitations: CP-0 head limitations (then inherited), de-duplicated, own removed.

## Refusals (wording fixed; `submissions.json#refusal_mutations`, `expected.json#refusals`)

All refusals are **journaled**: an invalid step consumes an attempt (attempt 0 is re-begun as attempt 1; attempt 1 invalid settles blocked). No `precheck` (Q4 ruling; rev 0's recommendation is withdrawn).

Validator issues: one literal mutation each (19), exactly one issue each: level not in quote; level not numeric; quote not on page; source not third_party; duplicate kind; bid level is the offer's (bid not labelled in its quote); talk cites the bid/offer sentence; as-of not in quote; maturity not after the quotation date; margin not in quote; non-zero amortisation (value_text "31" is the day-of-month numeral of "December 31" in the quote); recovery out of range; recovery both given; reference rate level not in its quote; reference rate neither level nor absence; digit in text; prohibited conclusion (buy, sell, overweight, underweight, recommend, cheap, undervalued, overvalued, outperform, attractive); Insufficient Information without limitation; observations and absence together. **Retired:** `crossed_quote` (bid above offer): with the level-to-kind binding no verbatim quote of the sheet can state a crossed pair, so the oracle cannot reach it. The core still refuses it ("observations: bid exceeds offer"); a core unit test over a synthetic page covers it.

Tool-use issues (journaled, through `RULES`, exact strings): `Cited page not read through read_pages: <source> <locator>` (one per unread page, sorted) and `Absence claim without a recorded search`. Oracle cases: unread market page:1; unread financial page:5; two unread pages (financial page:5 then market page:1); absence without a search; term absence without a search (the reference rate absence also holds in every pack case, so this shows the term absence is reached, not that it alone fires). Blocked case: attempt 0 digit in text, attempt 1 level not in quote. Run refusals: any `invoke` of `extract_statements`, any `read_inputs` is a refused `not_permitted` receipt; a snapshot change between the last read and the submit refuses `stale_binding`; `begin` refused (edge `block`, no attempt consumed) when CP-0 is blocked or stale; `requested_modules` naming CP-2H is refused at create (no spec).

## Tool use (D2)

CP-3D has pack tools and no upstream view, so no D2 exception is needed. Acceptance (`expected.json#cases.<case>.tool_use_required`): before the submit, ok `read_pages` calls cover every `page:N` the literal cites (positive: market page:1, page:2; financial page:5); at least one ok `search_pack` when the literal holds an absence object (positive: the reference rate level; gap_no_market also the market); zero `read_inputs`; `extract_statements` refused. The absence is backed only by "some search over some source" (the ToolRules precedent), not by a search for the specific item: recorded as an own limitation.

## Consumption proof (D3): stays OPEN

No consumer core reads CP-3D: `cp3_relative_value.py:100` and `cp6_committee.py:113` state they never read it; CP-5 counts only after a D3 scope lease; CP-3C (optional edge CP-3D to CP-3C, `restricted`) has no core, lease or chain. This lease makes no completion claim for consumption. It ships `cp3d_reader(store, head)` and pins what CP-3C must expose (`expected.json#consumption`: head hash, status, discount margin at mid, intensity at mid, cumulative probability at mid, recovery or its absence, own limitations). Recommend sequencing CP-3C after CP-2D and CP-4 so CP-3D can complete.

## Rendered sections (D7) and table ids (D8)

Per the FP03 ownership section: CP-3D registers **one** block, `market-against-fundamentals`, as `_Spec("Market against fundamentals", "CP-3D", "dense", ("CP-3D",), route_label="Full analysis")` in a new `_RELATIVE_VALUE` mapping. `bindings/cp3d.py` slots prefixed `cp3d-`: the six tabs listed below to `market-against-fundamentals`; T3E.8 to `evidence`; T3E.9, T3E.7 to `limitations`. The market-implied default panel is populated; the alignment panel is the honest partial (limitation in T3E.9). `instrument-levels` stays CP-3's (deferred); `yield-against-maturity` is CP-3D's own and deferred (chart, needs a yield). The six tabs of `market-against-fundamentals`, in this order, are binding rows in `bindings/cp3d.py` (one `_Spec` row, as now): T3E.5 (primary), T3E.4, T3E.6, T3E.1 (Market levels), T3E.2 (Price metrics), T3E.3 (Spread and yield) (open question 11, resolved by ruling). Rendered through G2's `owner_rendering.py`; gap cells render `∅ G<n>` with n bound at run time.

D8 collision check, run 2026-10-28: `T3E.1`-`T3E.10` appear in `methodology.json` only under CP-3D (the builder asserts no other module lists a `T3E` id; a grep of `src`, `tests`, `docs` and `cases` found no other occurrence before this preparation). `T3E.10` is registered and left unused.

## Acceptance (from `expected.json` only)

1. **Positive.** CP-0 settled restricted with facts equal `expected.cp0.positive` (40 facts, probed); CP-3D settled `restricted` with inputs `prepared-pack`, `CP-0` hash-equal to the head plus `market-implied-submission`; tables T3E.1-T3E.9 equal `cases.positive.tables` (ids, columns, `shown`, units, `value_class`, `period`, cites); claims, own and inherited limitations equal; receipt verifies; store bytes unchanged after.
2. **gap_no_recovery.** Same CP-0 clone; default measures missing (`∅ G#`), discount margin known; claim `CP-3D-PD-01` is the gap chip form.
3. **gap_no_market.** Pack without the market source; every price-dependent figure missing, never 0, each reason naming the missing market level; T3E.7 lists the group.
4. **Fixtures.** `compose` over each fixture's inputs equals `expected.fixtures.<id>.stored`.
5. **Refusals and tool use.** Each mutation yields exactly its issue; each tool-use case yields exactly its issues through `RULES` (G1 submit and verifier); blocked case settles blocked; `begin` refused on blocked CP-0; stale binding; the bid-exceeds-offer core unit test.
6. **Verifier probe.** `cp3d.probe` reruns validation on the frozen execution and gets the head hash back; tampering the retained step output or the head refuses `identity_mismatch` (a tamper must forge consistently so that probe, not an upstream hash check, refuses).
7. **Rendering.** The one block populated, owner CP-3D, tabs as above, cells equal expected `shown` (gap spelling pattern excepted).
8. **Consumption.** Recorded OPEN; no test claims it.
9. **Gates.** ruff check, ruff format --check, `MYPYPATH=src mypy --strict` on the changed files.

## Deferred test commands (build-first: not run now)

```
cd "<LEAD worktree>" && PYTHONPATH=src "../../../.venv/bin/python" -m pytest tests/test_owner_cp3d.py -x -q
python3 -I cases/cp3d-owner/builder/build.py && shasum -a 256 cases/cp3d-owner/*.json
```
plus the lease gates and `tests/test_owner_workflow.py` unchanged.

## Open questions for LEAD (with recommendation)

Resolved by ruling (kept for the record): 1 (owner-only module with pack sources and rules: protocol section 2 `RULES`, section 3), 3 (margin source: financial page, scope market + financial), 4 (journaled, no precheck), 5 (convention, with the added statements above), 7, 8, 9, 10 (rows-only registration admitted), 11 (T3E.1-T3E.3 bound as further tabs of `market-against-fundamentals` by the ruling at revision-2.md:49; tab order T3E.5, T3E.4, T3E.6, T3E.1, T3E.2, T3E.3).

2. **market-against-fundamentals.** Resolved: CP-3D owns the block, market-implied default panel populated, alignment partial with an own limitation. The comparison stays with CP-3 (reads CP-2) and CP-6.
6. **T3E design.** Titles, columns, claim wording and the use of `T3E.1-9` are this preparation's adaptation (no r14 text); `T3E.10` unused. Recommend `methods/cp3d.md` (drafted) at freeze.
12. **Architecture row.** `owner-harness-architecture.md:68` names `instrument-levels` for CP-3D against the FP03 reference; LEAD to amend the row.
13. **Recovery 70 percent.** An unsourced analyst convention (D11). Recommend a source (a recovery study or a house assumption note) before freeze, or accept as stated.
14. **Bid above offer.** Unreachable in the oracle after the binding; a core unit test covers it. Recommend accept.
15. **Issue order.** `RULES` follows `ToolRules` order (absence, then unread); the oracle never combines them. Recommend accept.

Not verified: no CP-3D core, validator or composer; the G1-X `RULES` routing and the owner-only pack-source seam are protocol text, not code, so the tool-use refusals are checked only as the product `unread_citation_issues` strings plus the oracle's own absence rule; the builder (`python3 -I`, twice, identical hashes) is the only thing run besides read-only product probes (`fact_spelling`, `prose`, `validate_review`, `build_readiness`, `unread_citation_issues`). The 70 percent recovery convention and the loan-market discounted-spread convention are not sourced. The yield cells and the validator for a quoted reference rate level were exercised only on a throwaway page in the builder. FP03 render, `G#` spelling, host scope, tamper/stale/begin-refused, journaled S1a path and `Decimal.exp` beyond 0.0001 are unexercised.
