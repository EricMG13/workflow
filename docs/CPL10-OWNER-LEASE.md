# CP-L10 (Financial change screen) owner lease — FROZEN by LEAD 2026-10-28 (preparation revision 4)

Frozen after `review-feature-4.md` (FREEZE) of revision 4 (fix round 3 on `review-precise-3.md`); LEAD rebuilt twice from a scratch copy with `python3 -I`: identical. Pins: manifest e368b31b4fbe2a16bd699f8c5971905282fb2a54b783d1081305e29305ba60d1, submissions d9b9559ddb9847500c740b723e5fa14f423bae5ff82456a4d192a2a28b8a71ba, expected 6eac1ead3d15a8276ac20224cec091536a979e15226bd492e02f903ef43d900a, builder b2a7e2130b52b4c1f3b5a48e878b12b91eaef03cc49b29df608e0fdd275d0fbe. `methods-cpl10-draft.md` is committed as `docs/methods-drafts/cpl10.md`; the build moves it to `src/deploy_vii/methods/cpl10.md`.

LEAD notes at freeze: (1) D4 (CP-L10 requires CP-1) lands only in the single serialised `methodology.json` change, together with CP-1C D8 (T1C.1-T1C.7) and one re-pin pass of every builder that pins `methodology.json` (`manifest.d4_edge_change.side_effects`; untracked builders located by grep at that time); that change edits this builder at :30 and :51 and amends every frozen header it touches, this one included. (2) The CP-OS and CP-DR entries in `frozen_lease_headers` mean those headers as amended at e8ee084 (`docs/CPOS-OWNER-LEASE.md:5`, `docs/CPDR-OWNER-LEASE.md:7`). (3) `expected.rendered` pins `report_view.py` 51a6853ec0e80393a50cdf8ed577cddaf2eee8e26246609b85dea01712560e12; a later change to it re-pins that section.

Former draft heading follows.

# CP-L10 (Financial change screen) owner lease: DRAFT rev 4 for LEAD, 2026-10-28 (mx-feature preparation, pre-code; fix round 3 by mx-escalate after review-precise-3)

Pre-code; nothing here is frozen. Oracle: `cases/cpl10-owner/{manifest,submissions,expected}.json`, builder `cases/cpl10-owner/builder/build.py`; method text `work/lead/cpl10-owner-preparation/methods-cpl10-draft.md` (becomes `methods/cpl10.md`). Every G1 seam is `docs/G1X-OWNER-CORE-PROTOCOL.md`, which supersedes any statement here that differs. Revision 2 applied the LEAD rulings at the end of `review-precise-1.md` and `report.md` (`revision-2.md`); revision 3 applied the rulings at the end of `review-precise-2.md` (F1-F5, Minor; `revision-3.md`); revision 4 applies the rulings at the end of `review-precise-3.md` (C1-C4 and the CP-OS/CP-DR header rule; `revision-4.md` lists what changed).

## Why

methodology.json: CP-L10 (aliases CP-L20, CP-L23, CP-L30, CP-L40; "Financial change screen") "runs a bounded LITE screening synthesis for CP-1, CP-1B"; today required CP-0 only, no optional edge, tables TL40.x..TL10.x (20 ids). Architecture study section 4: Python = screening thresholds, analyst = flag synthesis, section = screening (no block). The module screens ONE issuer for change between two periods (not against peers), so the frozen single-issuer pack is sufficient; no synthetic source and no synthetic peer source is added.

Python rates each of seven topics (EBITDA, free cash flow, cash, total debt, net debt, total leverage, interest coverage) for its relative change between two quarters of the settled CP-1 head: Material, Watch, Stable or Not assessed, with a disposition (Upgrade to full module, Monitor, No action, Evidence needed), a priority rank and a pointer to the full owner (CP-1D, CP-2D, CP-2A). The analyst only chooses the pair of quarters and writes an assessment and a credit-transmission sentence for each topic Python rated Material or Watch, an overall judgment and gaps.

## D4 (CP-1 edges), as designed here, with every side effect

The lease file does not decide D4's content (`docs/OWNER-WORKFLOW-LEASE.md`: "decided in the slice lease that first needs them"). LEAD ruled it (report.md Q2): `src/deploy_vii/methodology.json` CP-L10 `required` `["CP-0"]` becomes `["CP-0", "CP-1"]` (edge rule `block`, the registry default for a required producer); no optional edge, no `edge_rule` entry, no CP-1B edge in v1 (reading nothing is not consumption, D3). Why CP-1 is required: Python has no other structured source of period figures; reading CP-1's settled T4.10 facts keeps arithmetic on facts that already carry citations and calculation ids.

**The edit lands in the CP-L10 build commit, together with every side effect below, nothing silent. This preparation edits none of them** (not the test, not another builder, not a lease header, not `methodology.json`, not `docs/reuse/manifest.json`). Each is also recorded in `manifest.json#d4_edge_change.side_effects`. **The methodology change is one serialised change** carrying CP-L10 D4 and CP-1C D8 (T1C.1-T1C.7) together, with one re-pin pass of every builder that pins `methodology.json`; neither lands alone.

1. **Test pin.** `tests/test_cp1b_registration.py:34` (`test_only_cp1b_table_ownership_changes`) pins the sha256 of the methodology rows with the CP-1B `table_ids` popped: `0573968460da16ff13f4590b3f65edc4ebe06685c2e2840c8001b229747d86c6` today, `2f9aa78646dce706adf5c536e0863a558b0f73c712ef3b5b93d59af909b74c90` after the edit (probe on a scratch copy of the rows). The build commit updates the pin (a deliberate registry change); otherwise the test fails.
2. **Methodology-pinning builders (one re-pin pass).** Grep of `cases/*/builder/build.py` for the hash `348fbc4b...8d45`: ten other builders pin it and each refuses after the edit. Tracked builders, line re-grepped for revision 4: `cases/cp1d-owner/builder/build.py:36`, `cp2e-owner:31` (frozen at ac82330; asserted :60), `cp3-cp6-owner:31`, `cp3d-owner:34`, `cpdr-owner:30` and `cpos-owner:25` (both re-pinned at e8ee084 after 0d and 0d(c); lines re-grepped at that commit). Untracked or still-moving builders, no line pinned: `cp1c-owner`, `cp2g-owner`, `cp3c-owner`, `cp8-owner` are located by grep for the hash `348fbc4b...8d45` at build time (LEAD ruling on C2; cp8's pin sat at :38 in revision 3 and at :45 when revision 4 grepped). cp2a, cp2d and cp4 mention `methodology.json` in prose only. The build commit updates every pin in one pass, rebuilds each and compares: `expected.json` and `submissions.json` byte-identical; `manifest.json` differs only in the methodology pin value (each builder writes the pin into its manifest, so a byte-identical manifest cannot hold; key-limited diff). Any other output change comes back to LEAD.
   **This builder (F4).** After D4 `cases/cpl10-owner/builder/build.py` fails at `:51` (`assert CPL10["required"] == ["CP-0"]`) as well as at `:30`. The build commit edits both (`:51` to `["CP-0", "CP-1"]`), keeps the literal `348fbc4b...8d45` as `sha256_before` in `D4_SIDE_EFFECTS` (a literal, independent of `PINS`, so re-striking the pin at `:30` leaves it at the before-hash) and re-hashes the CP-L10 `manifest.json`.
3. **Reuse manifest.** `docs/reuse/manifest.json` needs a new entry for `src/deploy_vii/methodology.json` (new sha256, the D12 one-line registration reason, a review pointer); append it to the end of `local_patch_lineage` (the convention); the previous hash `348fbc4b...` is recorded at lines 1063-1069, which is not a place to insert after.
4. **Run behaviour (Answer 6 probe, venv python, `registry.modules` patched in memory only).**
   - `plan(("CP-L10",))` and `plan(("CP-L20",))`: `(CP-0, CP-L10)` becomes `(CP-0, CP-1, CP-L10)`; with CP-5: `(CP-0, CP-L10, CP-5)` becomes `(CP-0, CP-1, CP-L10, CP-5)`.
   - `edge_rule("CP-L10","CP-1")` raises `ValueError: No dependency edge from CP-1 to CP-L10` today and is `block` after; `edge_rule("CP-5","CP-L10")` stays `restricted`; no module requires or lists CP-L10 as optional, before or after.
   - `idle_statuses`: a run requesting CP-L10 has CP-1 in scope and unrun (in-scope unrun CP-0, CP-L10 becomes CP-0, CP-1, CP-L10).
   - `readiness.live_consumers`: `('CP-L10',)` becomes `('CP-1', 'CP-L10')`, so the CP-0 review must assess CP-1 as well as CP-L10 (a CP-L10-only review is refused "Assess each selected canonical live consumer exactly once").
   - `cp1_workflow.consumer_entries`: CP-1's readiness stage now requests the CP-L10 entry, routed to `consumer_specific_review` with requirement `consumer_specific_cp1_sufficiency` (see Readiness below).
   - Front Page: for a run requesting CP-L10 the three CP-1 blocks (`model-chart-strip`, `capital-structure`, `financials-credit-metrics`) read `not_run` ("Not run: CP-1 was not requested in this run.") today, `not_run` ("Not run: CP-1 has not run.") once D4 applies and CP-1 is unrun, `populated` once CP-1 settles (Rendered sections; probed on the committed report_view).
   - `business_context.py:351` is unaffected.
5. **Frozen lease headers (F3, C1).** The build commit amends these six headers under a LEAD note, because the builder pin and the methodology hash they name change: `docs/CP1D-OWNER-LEASE.md:3` (and `:27`, which names the methodology hash), `docs/CP2E-OWNER-LEASE.md:3` (frozen at ac82330; `:42` names the methodology hash; its `:5` note (3) already announces this re-pin), `docs/CP3D-OWNER-LEASE.md:3`, `docs/CP3-OWNER-LEASE.md:286-289`, `docs/CPOS-OWNER-LEASE.md:3` and `docs/CPDR-OWNER-LEASE.md:3` (each as amended by the 0d re-pin, landed at e8ee084: the re-pin paragraphs at CPOS `:5` and CPDR `:7` carry the current pins, which this side effect amends again; LEAD supplies the post-re-pin hashes and none is copied here), and the methodology hash at `docs/INTEGRATION.md:969`. Recorded in `manifest.json#d4_edge_change.side_effects.frozen_lease_headers`.

## Module kind and tools (G1-X protocol sections 1 and 3)

`registry.step_chain("CP-L10")` raises "CP-L10 has no live step contract". CP-L10 is an **owner-only** module: `entry="owner_core"`, core `src/deploy_workflow/owners/cpl10.py` supplies every section-2 item; no `src/deploy_vii` StepChain.

**No pack tools.** One step `change_screen`, `inputs="module_context"`, `sources=False`: the only evidence is the settled CP-1 head, read by Python (the CP-2A/CP-1D shape). Pack tools would let the analyst quote source text, but a change screen cites no page; every figure is a CP-1 fact and the analyst writes no figure. Page evidence can be added later with the CP-DR host mapping (question 6).

## Prerequisites

1. G1, the S1a extension and G1-X integrated (owner_core entry, `_VIEWS`, `_CORES`, `module_context`).
2. D4 methodology edit and its five side effects above (D12 one-line registration, serialised by PM together with CP-1C D8).
3. Pins: `cases/financial/manifest.json` sha256 `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`; `src/deploy_vii/methodology.json` `348fbc4b877e4f0351ecc238ea005adf815291b15a6267f263459203a08f8d45` (before the D4 edit; this oracle builder asserts it at `:30` and `:51`, so the pin and the `required` assertion are re-struck with the edit).

## Files

- New `src/deploy_workflow/owners/cpl10.py` (about 350 lines).
- `owner_workflow.py` (G1-X, not designed here): `OWNER_SPECS["CP-L10"] = OwnerSpec(module_id="CP-L10", steps=(StepSpec("change_screen", ..., inputs="module_context", rules="none"),), entry="owner_core", kind="analytical", publish=None)`; `_CORES`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["change_screen"]`. No `precheck`: every content rule is a journaled validator issue (so the blocked case works).
- D12 registrations: `methodology.json` (D4 edit; table ids unchanged, see D8); new `src/deploy_vii/bindings/cpl10.py` (rails bindings only, protocol section 6) and `bindings/shipped.py`.
- D4 side-effect files (above): `tests/test_cp1b_registration.py`, the ten other pinning builders and this one (`:30`, `:51`), the six frozen lease headers and `docs/INTEGRATION.md:969`, `docs/reuse/manifest.json`.
- TOOL-CONTRACT matrix row for CP-L10 `change_screen` (LEAD amends at freeze). `methods/cpl10.md` adaptation record from `methods-cpl10-draft.md` (thresholds, exact comparison, rank, dispositions, TL10 columns, limitations).
- G2 `owner_rendering.py`: one `DeliveryScope` for `slice-cpl10-screen` (rails only).
- New `tests/test_owner_cpl10.py`, `tests/cpl10_runs.py` (`cpl10_closed(case, root)`).

## The run

Run `cpl10-owner-positive`: pathway `credit_snapshot`, `requested_modules = ("CP-L10",)` (explicit value overrides the preset), plan `CP-0, CP-1, CP-L10` (no CP-MODEL: protocol section 5). Pack = identity + financial sources unchanged. The `limited` case clones the settled CP-0/CP-1 heads before CP-L10 begins.

**CP-0 (validated).** The test literal with one consumer row for CP-L10 (`submissions.json#cp0_consumer_row_cpl10`, no `provenance` key: the schema forbids it) next to the unchanged CP-1 row. Probe: `validate_review()` with D4 patched, status `candidate`, T8 commands `Run CP-1`, `Run CP-L10`; CP-0 settles `restricted` through `Execution.begin` / `submit_cp0_review`. Without D4 the same two rows fail "Assess each selected canonical live consumer exactly once".

**CP-1 readiness (validated; Answer 5).** CP-L10 is not in `downstream_readiness._DEPENDENCIES` (:27-39), so its entry routes to `consumer_specific_review` with the one requirement `consumer_specific_cp1_sufficiency`; the dependency requirements of revision 1 (`cash_flow_metrics`, `liquidity_data`) are refused as "Duplicate or unknown requirement". The literal `submissions.json#cp1_downstream_review`: `inputs_sha256` (prefilled content hash), one requirement, status `limited`, 20 evidence ids, the rationale and action recorded in the file, and one gap block over every `narrative.gaps[*].gap_id` (relevance `relevant`, no evidence ids). Evidence-id selection rule (marker `{{EVID:kpi <K>, quarter <N>}}`, N = 1..4 outer, K = ebitda, fcf, cash_closing, total_debt, net_debt inner): the FIRST catalogue record, in catalogue order, of kind `kpi` whose `record_json` key is K and whose non-empty `value.observation_ids` all end in `-q<N>-2025` (the Q4 cash, total debt and net debt records have a later LTM match; the rule picks the quarter record). Probe on the real head with `consumer_entries=("CP-L10",)`: `validate_downstream_review()`, `_assess_consumers` row `ready_with_limitations`, 0 unassessed requirements, 0 unassessed gaps, 1132 relevant gaps, no blocking gap.

## Public API (`owners/cpl10.py`; keyword arguments except `store`)

```
MODULE_ID = "CP-L10"; STEP_ID = "change_screen"; STEP_IDS = (STEP_ID,); QUALIFICATION
SCHEMAS = {STEP_ID: ChangeScreenSubmission}
cpl10_upstream(store, attempt) -> Upstream            # CP-0 and CP-1 heads bound; T4.10 facts by label
screen_topic(*, start, close) -> TopicScreen          # pure, Decimal/Fraction; the rule below
validate_screen(*, submission, upstream) -> tuple[str, ...]
change_screen(*, submission, upstream) -> Report      # raises ValueError on any issue
context_block(*, upstream) -> dict                    # the exact read_inputs view
cpl10_module(report, *, inputs, attempt) -> Module
submit(store, ticket_id, step_id, payload, rules) -> Submitted
view(historical, attempt) -> tuple[str, str]; probe(store, snapshot, attempt) -> None
cpl10_reader(store, head) -> Cpl10Head                # the consumer reader (Consumption)
```

## Submission schema (reference and judgment only; every field required) and its field types

```
ChangeScreenSubmission: comparison: {from_period: Text, to_period: Text}   # exact period strings of the view, from earlier than to
                        assessments: tuple[Assessment, ...]
                        overall: {rationale: Text, category: Category, confidence: Confidence, limitation: Text|null}
                        gaps: tuple[{gap, why_it_matters, affected_analysis, action: Text, severity: Severity}, ...]
Assessment: topic_id: Text, assessment: Text, credit_transmission: Text, category: Category, confidence: Confidence
```
Types are the product's, pinned because they decide shape versus content: `Text` = `contracts.Text` (`str`, `min_length=1`; contracts.py:21), `Category`, `Confidence` (`Literal["High","Medium","Low","Insufficient Information"]`) and `Severity` from `business_context.py` (:75-80). Consequences (probed): an empty string is a SHAPE issue (`<path>: String should have at least 1 character`, returned alone); whitespace-only text passes the type and is a CONTENT refusal (r11); `confidence == "High"` passes the type and is a CONTENT refusal (r07, as CP-2A); a missing field is shape (r12, `comparison.from_period: Field required`).

Rule: exactly one assessment for each topic Python rates Material or Watch (the view's `pair_screens` shows Python's rating for every offered pair); none for Stable or Not assessed. `confidence` is Medium or Low, never High (a screen is not a decision). Analyst text carries no bare figure, no unresolved reference and none of CP-1A's prohibited conclusions (recommend, recovery, covenant); the literal submissions are digit-free with no reference syntax. Literals: `submissions.json#positive`, `#limited`.

**Validation order (one stated order).** (1) shape, alone. (2) comparison: an issue here ENDS validation (the ratings depend on the pair; r01, r02). (3) assessments in submission order (unknown topic, not assessable, repeated, confidence), then the missing-assessment check. (4) analyst text of each assessment and the overall rationale: `prose.check(text, refs=<fact ids and unique calculation ids of the module built for the submitted pair>, gaps=(), names=(issuer name,))` (the product `prose` path, so a reference that resolves against the module's bound facts is accepted and one that does not is refused with the product text), then prohibited conclusions and empty text. (5) overall. (6) gaps.

## Decimal composer (zero, missing, not applicable, blocked kept distinct)

Operands: CP-1 T4.10 facts, label `<column> · <metric>` (exactly one match or the operand is unbound), for the quarter columns `Q1 25 (2025-01-01 to 2025-03-31)` .. `Q4 25 (2025-10-01 to 2025-12-31)` and metrics `ebitda`, `fcf`, `cash_closing`, `total_debt`, `net_debt`, `total_leverage_reported`, `interest_coverage_reported`. Per topic with start value a and close value b:

| Quantity | Rule |
|---|---|
| change | `b - a` (signed), one exact subtraction; unit and decimals of the topic (amounts MILLIONS, 2 dp; multiples MULTIPLE, 2 dp) |
| change on starting level | `(b - a) / abs(a)` (signed, PERCENT, 1 dp shown); one division of exact decimals (38 digits, half-even) |
| materiality (exact comparison) | Material iff `abs(b - a) * 10 >= abs(a)`; else Watch iff `abs(b - a) * 20 >= abs(a)`; else Stable. Rated on the exact value, NOT on the rounded quotient or the shown percentage (20 to 20.99 is 99/2000, shows 5.0% and is Stable). One rule for amounts and multiples. Boundaries rate up (10 to 11 Material, 20 to 21 Watch) |
| a is zero | change 0: Stable; change not 0: Material, change on starting level `not_applicable` (never infinity, never 0) |
| a or b missing | change and change on starting level `missing` with CP-1's own limitation text; materiality Not assessed; evidence Missing; disposition Evidence needed. Never 0 |
| disposition | Material: Upgrade to full module; Watch: Monitor; Stable: No action; Not assessed: Evidence needed |
| priority rank | Material (a zero-base Material first), Watch, Not assessed, Stable; inside a class larger abs(change on starting level) first, then register order; ranks 1 to 7 |
| counts | topics per materiality (unit `topics`) |

**Copied CP-1 cells** (`from_value`, `to_value`) are the CP-1 fact verbatim: its `value_class` (observed on the real head: ebitda, cash_closing, total_debt `source`; fcf, net_debt and every ratio fact `calculated`, a missing ratio fact included), its status and limitation, its citations and its OWN `calculation_id` (`canonical-kpi:<sha256>`, present on every T4.10 fact, source-class too), bound at run time (oracle marker `{{CP1_CALCULATION_ID}}`); the module fact id is its own. Every MILLIONS fact (copied or own) carries `currency: "USD"` and `scale: 1000000`, as CP-1's facts do; ratio facts carry neither (default scale 1). The copied cell is shown at the module's 2 dp (`decimals: 2`), never CP-1's 0 dp cell text. Calculated own facts (`change`, `change_pct`, materiality, evidence status, disposition, rank, counts) carry `calc:<fact_id>` and list the two CP-1 labels they derive from, in that order. A `not_applicable` cell reads `∅ G# n.m.`, a missing one `∅ G#` (`report_view.fact_spelling`). A missing change fact carries the compared pair as its period.

Fixtures in `expected.json#fixtures` pin the rule at its boundaries (exact 1/10 and 1/20 with the cross-multiplication test, 99/2000 with its shown 5.0%, negative fall, zero base with and without change, negative base, missing ends) and the rank order over seven rows (Watch, two Material, a zero-base Material, Not assessed, two Stable ties: expected order e, d, b, a, f, c, g).

Positive (Q1 to Q4): cash 16.25 to 20.00, change 3.75, 3/13 = 23.1% Material (rank 1); total debt 46.25 to 50.00, change 3.75, 3/37 = 8.1% Watch (rank 2); total leverage and interest coverage Not assessed (CP-1 has no known value for the starting quarter; ranks 3, 4); EBITDA 7.50 to 7.50, free cash flow 2.25 to 2.25, net debt 30.00 to 30.00 Stable with a known zero change (ranks 5 to 7). Counts 1, 1, 3, 2. Limited (Q2 to Q3): cash 17.50 to 18.75, 1/14 = 7.1% Watch; total debt 47.50 to 48.75, 1/38 = 2.6% Stable; both ratios missing at both ends; counts 0, 1, 4, 2.

Tables (D8 ids registered already): TL10.1 scope and sources (rows cp0, cp1), TL10.2 topic screen (seven topics plus `total`), TL10.3 screen items (assessed topics plus `overall`), TL10.4 upgrade triggers (every topic not Stable; target module, its methodology title, blocking Yes only for Material; decision impact is the analyst's sentence or, for a topic with no assessment, a `missing` cell). Claims: one Python template per topic (known, or cannot-be-screened with a chip), one summary with the four counts, one claim per analyst assessment and one for the overall rationale. Module status `restricted`.

**Own limitations** (the candidate's, exact): (1) thresholds are screening rules, not covenant or credit tests; (2) two-quarter comparison only, no prior-year pack; (3) ratios only where CP-1 carries a known value for both quarters; (4) a screen rates movement, not credit quality; (5) each topic is rated on the exact change on its starting level and the percentage shown is rounded, so a shown value at a threshold can carry the lower rating; (6) a small starting level inflates the relative change and a negative one is measured on its absolute value; then one "Not screened" line per missing topic and one line per analyst gap. **Settled limitations** = the own list plus `Synthetic case; not real issuer qualification` (execution.py:440-446, case_kind synthetic), de-duplicated; inherited limitations are bound at run time.

## Refusals

Twelve literal invalid payloads (`submissions.json#refusals`, issues in `expected.json#refusals`), each the positive submission with exactly one defect and one expected issue, each an invalid attempt 0 (re-begun): r01 starting period not offered; r02 closing period not after starting; r03 unknown topic (a third assessment `gross_margin` appended, so the two required ones stay: `assessments[2].topic_id: unknown topic: gross_margin`); r04 Stable topic assessed; r05 Watch topic left unassessed; r06 topic assessed twice; r07 confidence High (content); r08 bare figure (`Bare figure: 20`); r09 a reference that resolves to no bound fact (`{TL10.2.cash.nothing|US$ m}` gives `Unresolved reference: TL10.2.cash.nothing`); r10 prohibited conclusion; r11 whitespace-only overall rationale (content, `overall.rationale: empty`); r12 shape (`comparison.from_period: Field required`). Product-produced spellings are r08's and r09's (probed with `prose.check`, recorded as `issue_spelling: product`); every other issue string is this draft's proposal, frozen when LEAD accepts (the same stance as the CP-1D draft). `blocked`: attempt 0 r01, attempt 1 r08, head blocked, no tables, limitations = attempt 1's issues.

**Refused (frozen case; CP-1 missing).** The CP-2A pattern: financial source missing (`cases/financial/manifest.json#negative_case`: no pages or hash, extraction blocked), CP-0 with two CONDITIONAL rows (CP-1 and CP-L10, `submissions.json#refused`) and a gap row naming both. Probe: `validate_review()`, status `candidate`, T8 `DO NOT RUN` for both, CP-0 settles `restricted`; `store.begin("CP-1")` raises `NotAuthorized` ("CP-0 has not authorized this consumer's source readiness"). Expected: exactly one `RefusedBegin` for CP-1 (kind `not_authorized`, reason `str(NotAuthorized)`), attempts and heads CP-0 only, CP-L10 never begun, receipt verifies.

**Blocked CP-1 (lease statement for the build's test, not a frozen case).** CP-1 blocked: `store.begin("CP-L10")` raises `ValueError("Required upstream is unrun, stale or blocked")` (`owner_workflow.BLOCKED_EDGE`, :78) while a head has status `blocked`, so `OwnerWorkflow._begin` (:447-456) retains exactly one `RefusedBegin` for CP-L10, kind `blocked`, reason that text; CP-1 has attempts 0 and 1; no CP-L10 attempt, head or table; receipt verifies. A CP-1 head that is missing with no blocked head is NOT retained (`_begin` re-raises), which is why the frozen case is the CP-1-missing variant. Search of the repository's fixtures: no frozen blocked-CP-1 history for the financial pack exists. `tests/test_source_tools.py` `legal_history(root, blocked=True)` (:683-721) builds one in code on the LEGAL pack (two invalid `source_context` submissions of `{}` per attempt, attempts 0 and 1, result blocked) inside the session fixture `legal_histories`; there is no `tests/*.json` fixture; `tests/test_owner_workflow.py::test_rejected_then_blocked_walk_retains_refusal` blocks CP-0, not CP-1. The build's test therefore builds the financial-pack equivalent in code.

G1-level: `invoke` is a refused `not_permitted` receipt; submit before `read_inputs` is `not_permitted`; a snapshot change between read and submit is `stale_binding`.

Tamper (acceptance 6): edit the stored step output so Cash reads Stable instead of Material, forged consistently (payload blob, output blob, step `output_sha256`, head `result_sha256`, audit inventory, receipt record) so audit and blob checks pass and only `cpl10.probe`'s rebuild refuses with `identity_mismatch`.

## Tool use (D2)

CP-L10 is session-less and source-free. `read_inputs` returns the exact view `context_block`, a D2 exception frozen here (as CP-2A). Key tree, shape only (the implementer commits `cases/cpl10-owner/cpl10-view-tree.json` from product-settled heads):
```
upstream: [{module_id, status}]                       # CP-0, CP-1
periods: [{period, column}]                           # the four quarters, in order
topics: [{topic_id, label, cp1_metric, unit, values: [{period, status, shown, limitation|null}]}]   # equals expected.cases.positive.view_topics
pair_screens: [{from_period, to_period, topics: [{topic_id, materiality}]}]   # six pairs; equals expected.cases.positive.view_pair_screens
rules: str  (thresholds named in words, exact comparison, rank order, assessment rule)   inherited_limitations: [str]
```
`values[].shown` is Python's spelling of the CP-1 AMOUNT at 2 dp (`7.50`, `1.67x`; a missing value `∅ G#` with CP-1's limitation), never CP-1's own 0 dp cell text (which reads `8` for 7.5). No quote, citation, free text from a source page, or record_json at any depth. Acceptance: exactly one ok `read_inputs` before the submit; zero pack calls; every `invoke` a refused `not_permitted`.

## Consumption proof (D3): OPEN

Consumer named: CP-5 (fan-in, `registry.edge_rule("CP-5","CP-L10") == "restricted"`). It counts only after a CP-5 scope lease extends the integrity scope to CP-L10 and the CP-5 attempt binds the CP-L10 head hash and cites CP-L10 facts. No consumer core exists. This lease ships `cpl10_reader(store, head)` and pins what a consumer must read (status, per topic id/materiality/evidence/disposition/rank/change, counts; `expected.consumption`). No completion claim covers consumption.

## Rendered sections (D7) and table ids (D8)

No Front Page block (architecture study: "screening (no block)"; no pathway lists CP-L10). Rails only, as CP-DR: `bindings/cpl10.py` slots `cpl10-` prefixed: TL10.1, TL10.2, TL10.3 to `evidence`, TL10.4 to `limitations`. Assigned section for completion: Evidence and Limitations of the scope `slice-cpl10-screen` (question 4).

**Render states pinned (D4-patched in memory, `requested_modules=("CP-L10",)`, `credit_snapshot`; re-probed in revision 3 on the committed product after 0d at 41a8fdb and 0d(c) at b4ae187, `docs/reviews/0d-product-defects.md`; `src/deploy_vii/report_view.py` sha256 `51a6853ec0e80393a50cdf8ed577cddaf2eee8e26246609b85dea01712560e12`).** Rule of the product: a preset module the override excludes (in `registry.dependencies(PATHWAY_MODULES[run.pathway])` but `not_in_pathway`) reads "Not run: <modules> was not requested in this run." (state `not_run`, call band `not_requested`); a module outside the closure keeps "Not in this Pathway". Probed: `call_withheld = "not_requested"`, call item `Assessment pending`. `not_run` "was not requested": `key-findings` (CP-2), `company-operating-model` (CP-1A), `strengths-weaknesses` (CP-2 and CP-6), `relative-value` (CP-3), `company-profile` (CP-1A), `committee-challenge` (CP-6). `what-changed`: `not_in_pathway` ("CP-8 is not part of Credit Snapshot", CP-8 is outside the preset). `transaction-summary`, `portfolio-fit`: `absent`. `model-chart-strip`, `capital-structure`, `financials-credit-metrics`: `not_run` "CP-1 was not requested in this run." without D4; `not_run` "CP-1 has not run." with D4 and CP-1 unrun; `populated` with D4 and the settled CP-1 head (CP-L10 unrun in the probe). The CP-L10 rail population itself is not probed (no bindings exist). The override-slice wording defect and the call-band defect are closed by 0d and 0d(c).

**Navigator and module status words pinned (C3; `report_view.navigator`, `report_view.module_display`, same report_view sha, same three views; `expected.rendered.front_page_states.navigator`).** Rows in registry order, 25 in every state; a module is numbered iff its status is not `not_in_pathway`, the rest are footer rows. Without D4: 1 CP-0 "Not run", 2 CP-L10 "Not run"; CP-1 sits in the footer as "Not run". With D4 and CP-1 unrun: 1 CP-0, 2 CP-1, 3 CP-L10, all "Not run". With D4 and CP-1 settled (restricted): 1 CP-0 and 2 CP-1 "With limitations", 3 CP-L10 "Not run". Footer word groups in every state: "Not run" for the preset modules the override leaves out (CP-1A, CP-2, CP-3, CP-4, CP-5, CP-6, CP-MODEL; plus CP-1 without D4); "Not in this Pathway" for the fifteen outside the closure (CP-1B, CP-1C, CP-1D, CP-2A, CP-2E, CP-2G, CP-2H, CP-4C, CP-8, CP-DR, CP-MEMO, CP-OS, CP-2D, CP-3D, CP-3C). `module_display` spells the same word for the module payload: the CP-1 status word is "Not run" while CP-1 is `not_in_pathway` (without D4) or `unrun` (D4, before CP-1 runs) and "With limitations" once CP-1 settles restricted. The words are written into the builder as literals (no product import).

D8 collision check (builder asserts it from `methodology.json`; repo grep `TL10\.` found only methodology.json): `TL10.1` to `TL10.4` appear only in the CP-L10 entry. Registration: none changed. TL20/TL23/TL30/TL40 ids of the same entry stay in place and unproduced (LEAD Q3; this lease states they are unproduced).

## Acceptance (from `expected.json` only)

1. Positive: CP-0 and CP-1 settle restricted; CP-L10 settles `restricted` with inputs prepared-pack, CP-0, CP-1 hash-equal to the heads; tables TL10.1 to TL10.4 equal cell for cell (ids, shown, units, value classes, currency, scale; `∅ G#` / `∅ G# n.m.` pattern; copied CP-1 cells equal the real CP-1 fact including its own `calculation_id`; head statuses bound at run time); claims equal; own and settled limitations equal; receipt verifies; store bytes unchanged afterwards.
2. Limited: same, with `expected.cases.limited`.
3. Fixtures: `screen_topic` over `fixtures.composer` and the rank order over `fixtures.rank` equal the expected values.
4. Refusals r01 to r12, blocked, tool-use refusals, the CP-1-missing `RefusedBegin` (frozen) and the blocked-CP-1 `RefusedBegin` (lease statement above, built in the test).
5. Verifier and tamper case (`identity_mismatch` only from `probe`).
6. Rendering: the rails are populated with owner CP-L10; Front Page states, call band, navigator rows (numbers and words per D4 state), footer word groups and the CP-1 module status word as pinned above (committed report_view `51a6853e...0e12`; `expected.rendered.front_page_states` including `.navigator`).
7. Consumption: recorded OPEN; no test claims it.
8. Claim check: `prose.prose_issues` empty for every expected claim (probe below).
9. D4: `registry.plan(("CP-L10",))` equals `expected.refused.plan_order`; `edge_rule("CP-L10","CP-1")` is `block`; `tests/test_cp1b_registration.py` passes with the new pin; the ten other pinning builders reproduce `expected.json` and `submissions.json` byte-identical and a `manifest.json` that differs only in the pin value, with their re-struck pins; this builder passes at `:30` and `:51`; the six frozen lease headers and `docs/INTEGRATION.md:969` are amended.
10. Gates: ruff check, ruff format --check, mypy strict on changed files.

## Deferred test commands (build-first: not run now; LEAD's final phase)

```
PYTHONPATH=src "../../../.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cpl10.py tests/test_cp1b_registration.py   # heavy lock; a genuine CP-1 promotion per module-scoped fixture
python3 -I cases/cpl10-owner/builder/build.py && shasum -a 256 cases/cpl10-owner/*.json                # oracle reproduces byte for byte
for b in cp1c cp1d cp2e cp2g cp3-cp6 cp3c cp3d cp8 cpdr cpos; do python3 -I cases/$b-owner/builder/build.py; done   # after the one re-pin pass; expected/submissions byte-identical, manifest differs only in the pin
```
Plus ruff, `MYPYPATH=src mypy` on changed files, `tests/test_owner_workflow.py` unchanged.

## Open questions for LEAD (recommendation first)

1. **Thresholds and ranking** (ruled: screening-policy literals, D11, own limitation, never sourced). Open only if LEAD wants other fractions (two constants).
2. **D4**: ruled and detailed above.
3. **Unproduced table ids**: ruled keep; this lease states they are unproduced.
4. **Rails only, overridden `requested_modules`**: ruled as CP-DR; render states pinned above.
5. **Readiness literals**: closed (validated; Answer 5).
6. **Page evidence**: no pack tools in v1 (ruled).
7. **Pair choice**: analyst picks any ordered pair; the view's `pair_screens` shows Python's rating (ruled).
8. **Units**: counts and rank use units `topics`/`rank` ("1 topics", "1 rank"; ruled cosmetic).
9. **Net debt value class**: closed (`calculated`, observed on the real head).

## Probes run (read-only, build-first rule; revision-2.md and revision-3.md have the outputs)

`python3 -I cases/cpl10-owner/builder/build.py` twice (identical). Venv python, `PYTHONPATH=src`, scratch copies of the store and a scratch pack only, each under 1 s, `registry.modules` patched in memory only (nothing written under `src/`): real-head comparison of all 28 copied cells (0 differences), strictly built facts through `prose.issues` on all 21 claims (0 issues) and `fact_spelling` (0 mismatches), `prose.bare_figures` on every literal analyst text (0 hits), `prose.check` on r08/r09, CP-0 and CP-1 readiness literals (above), refused-case CP-0 rows and `NotAuthorized`, `registry.plan`/`edge_rule`, the pinned-digest recomputation; in revision 3 the render states and call band on the committed report_view (scratch copy of `src/`, venv python, under 60 s); in revision 4 the navigator rows, footer word groups and `module_display` words on the same committed report_view (reviewer's probe construction, scratch copies of `src/` and of the settled store, under 5 s). No pytest, no heavy job.

Not verified: no product code exists, so no expected value was compared with product output of CP-L10; the view tree, issue wording other than r08 and r09, thresholds and G1-X behaviour for a plan without CP-MODEL are design only; the blocked-CP-1 `RefusedBegin` is read from `owner_workflow.py`, not walked; the CP-L10 rail population and the settled CP-L10 render states (navigator row 3 once CP-L10 settles) are not probed; the D4 side effects are listed from probes and grep, not applied; the CP-OS and CP-DR header hashes after the 0d re-pin (e8ee084) are not copied here; LEAD supplies them.
