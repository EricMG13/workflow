# CP-2E (Macro, FX and hedging sensitivity) owner lease — FROZEN by LEAD 2026-10-28 (preparation revision 3)

Amended by Modules 2026-10-29 (Stage 2 close release W2-A2): CP-2E: `expected.json` `negative_cases.blocked_cp2e.result` now reads "module blocked, the store holds a blocked head (status blocked)" instead of "module blocked, no head" (ruling Stage 2 round 2 item 8). No other leaf moves. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` 8f507e108ac3d75e4fcc3f524dcf1c31ad8ceedb2e2359fcb9de02b56f25bc86 → 08a80e96cf23de2a5acbcc8f24ba2c713a1dc02152e3f5b99417d5ced3871592; `builder/build.py` 0b0ce5602263132b5c037162a97feecea60b94515993575738a67d8ee7aa9134 → 7a145dc3ad8b46d8579d02d287931c5d379bf4999c36a28b9af67787d26a32e4.

Amended by LEAD 2026-10-28 (CP-6 freeze re-pin, `work/lead/cp6-freeze/report.md`): `src/deploy_vii/methodology.json` registers `T6-FINAL` under CP-6 `table_ids` (ruling Q7), 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 → 0932d9fbcd9272d62bcb7681e1dd16d9bc944319c64716b41dc79715699796e8; this module's builder re-pins it and its manifest records the new hash. Only pin hashes move: no other leaf of this module's oracle changes. Own files, old → new sha256: `manifest.json` af12e05064b7f7b9726ea9f18a6341f561fd2d16cb1ffa44bbac8792aa0008c7 → 4e3dab8f462c5d6968cfa3326d9f808242df7e1d34a6ca2b0383ed4752d4a6ab; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` 2242460f89a917470e00f912cf9141b9fed3dc3ce40fa67fbca7b0f9823e4bd0 → 0b0ce5602263132b5c037162a97feecea60b94515993575738a67d8ee7aa9134.

Amended by LEAD 2026-10-28 (Stage 1 release batch, `docs/rulings/2026-10-28-stage1.md`; `work/lead/stage1-release/report.md`): E1 (the share-known currency-move claims, with the E4a reason), E5 as amended by round 5 E8 (the rate-basis quote must match `\b(floating|fixed)[\s-]+rate\b`, case-insensitive, for exactly one of the two stems) and A4 with round 6i (the floor own limitations apply to floating-rate debt only: floor 0 keeps the pinned line, floor above zero gets the A4 line, fixed rate gets neither). Builder only: no frozen case reaches the changed branches, so manifest, submissions and expected are unchanged. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` unchanged; `builder/build.py` de0d14fcb431a965452d91311f150e7e527f7f6f877b1da19065acd93a848adf → 2242460f89a917470e00f912cf9141b9fed3dc3ce40fa67fbca7b0f9823e4bd0. A double scratch rebuild of every builder in dependency order was byte-identical. Pin consumers: none (no other builder pins or reads this module's files). Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change.

Amended by LEAD 2026-10-28 (round 6 oracle batch, `docs/rulings/2026-10-28-stage1.md` round 6; `work/lead/r6batch-review.md` COMMIT): round 6 A3: a divisor <= 0 is not_applicable, negatives read `… is negative` and the zero reasons stay byte-identical; only the `arithmetic.coverage` text changes. This amends lease :131-132. A scratch rebuild in dependency order was byte-identical. builder aaa1969f… → de0d14fcb431a965452d91311f150e7e527f7f6f877b1da19065acd93a848adf; expected 8568b1ce… → 8f507e108ac3d75e4fcc3f524dcf1c31ad8ceedb2e2359fcb9de02b56f25bc86; files not listed are unchanged. Pins elsewhere in this file are superseded where they differ.

Amended by LEAD 2026-10-28 (oracle amendment E6, `docs/rulings/2026-10-28-stage1.md` round 5): E4a governs, so a debt currency stated without a facility balance reads `the facility balance is not stated`. The builder (lines 633-637) splits the `df is None or bal is None` branch, and a domestic facility without a balance is no longer a known 0. `expected.json` changes only at `fixtures.fixture_no_rate_terms.stored.{foreign_debt, foreign_debt_share, fx[0].debt_change, fx[0].debt_after, fx[0].lev_after}.reason` and the `arithmetic.foreign_debt` description. LEAD rebuilt from a scratch copy with `python3 -I`, and the result is byte-identical. builder f32f0bd0… → aaa1969f22a83534446fc4014d0a41d9fa097ce6a7d53c6b1b20dea3224ae888; expected 9fa1767a… → 8568b1cedf975f75023c90d53b789b6c0e14ad1834c776c862a2071ebc8c4e3e; manifest af12e05064b7f7b9726ea9f18a6341f561fd2d16cb1ffa44bbac8792aa0008c7 and submissions d0e5915d1148d7a895915b70e7c56d937759f4a6eddc0feff0c5e8e163a7a804 are unchanged. Pins elsewhere in this file are superseded where they differ.

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 06f6ee61… → f32f0bd0c70a5b0d47441819a5140cd9a2bcd3aab76c866168e99ef6a1d388e9; manifest 5b5a5e53… → af12e05064b7f7b9726ea9f18a6341f561fd2d16cb1ffa44bbac8792aa0008c7; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

Frozen after `review-precise-2.md` (CHANGES REQUIRED: T1, R1, R2, fully specified) and revision 3, which LEAD checked inline: rebuilt twice from a scratch copy with `python3 -I`, identical; manifest and submissions unchanged; `expected.tamper` has the frozen CP-DR shape (keys, five steps, `expect.test_asserts`, `step_output_edit`) with the reviewer's CP-2E values; the reviser showed that removing `tamper` and the R1 probe sentence restores revision 2's expected hash. Pins: manifest 5b5a5e533728b040e6efb36e46bd3b927bd68285bfda778ae8c1d0ec29a144e0, submissions d0e5915d1148d7a895915b70e7c56d937759f4a6eddc0feff0c5e8e163a7a804, expected 9fa1767a757288035106bb33c9d1769b082e46ba922a3debfbc8e31f2ab0d9cb, builder 06f6ee613204242e591de3d7a8325cef40069b6adf4b55b8656b88e9b31393c4.

LEAD notes at freeze: (1) `expected.tamper.why_this_fact` calls the target "coverage after hedges"; the fact is interest coverage after the shock (its column title); after-hedges figures are missing in this pack. (2) No methods draft exists; the build writes `methods/cp2e.md` from this lease's adaptation list (Files, question 6). (3) Known re-pin: the builder's `methodology.json` pin moves in the single serialised methodology change (CP-L10 D4 with CP-1C D8); expected and submissions stay byte-identical, the manifest changes only in that pin, and this header is amended then. (4) CP-2E is not complete until a consumer reads it (D3 open; CP-5 scope lease after S1b).

Former draft heading follows.

_CP-2E (Macro, FX and hedging sensitivity) owner lease: DRAFT rev 2 for LEAD, 2026-10-28 (mx-feature preparation, pre-code; fix round 1 of review-precise-1)_

Pre-code; nothing here is frozen or reviewed. Oracle: `cases/cp2e-owner/{manifest,submissions,expected}.json`, builder `cases/cp2e-owner/builder/build.py`. Every G1 seam is `docs/G1X-OWNER-CORE-PROTOCOL.md`, which supersedes any statement here that differs.

## Why

`methodology.json`: CP-2E (alias CP-2F, "Macro fx hedging sensitivity") "assesses macro, FX and hedging sensitivity of the credit"; required CP-0, no optional edge, 17 table ids (`T2G.1-8`, `T2F.1-9`). Architecture study section 4: Python = FX/rate shock arithmetic, analyst = exposures and hedging, section = full analysis. No r14 SKILL.md exists in this repository (the CP-2D/CP-3D situation): the table titles, columns and claim wording below are this preparation's adaptation record, which LEAD confirms (question 6).

Python computes, from quoted FY 2025 facts of the financial source (static parallel shock, upward only with a zero floor; hedges, reset timing, the 2029 maturity, interest income on cash and the tax shield are not modelled and stated as limitations): the floating-rate debt; for each analyst rate shock the added annual cash interest, interest after, interest coverage after and its change, free cash flow after and the added interest as a share of EBITDA; the foreign-currency debt and, for each analyst currency move, the change in total debt, EBITDA and leverage; and the effect after hedges when a hedge ratio exists. The analyst supplies only the shock sizes (labelled assumptions), the reference-and-judgment assessments of three sections (interest rate, FX, hedging) and a summary. What the frozen pack does not state (reference rate level, split of earnings by currency, hedging instruments) is shown missing, never 0 (see "Sources").

## D4 (CP-1 edges), as designed here

`docs/OWNER-WORKFLOW-LEASE.md` lists "D4 (CP-1 edges for CP-2E/CP-L10)" as decided in the lease that first needs it. CP-L10's lease (Q2 ruling) decided its own edges on the rule "required edges only where the module reads facts; reading nothing is not consumption". This lease applies the same rule to CP-2E:

- **No change to `methodology.json`**: CP-2E stays `required ["CP-0"]`, no optional edge, no `edge_rules` entry (edge rule `block`, the registry default). No D12 edit for the methodology.
- Why no CP-1 edge: every operand is read by Python from a quoted page of the financial source (rate type, reference rate, spread, floor, balance, EBITDA, cash interest, free cash flow, FX effect on cash, total debt, currency). CP-1's T4.18 offers `rate_type` and `reference_rate` text cells (`cp3_relative_value.py:107`), but spread, floor and the FX effect are not observed CP-1 cells in any frozen oracle, and a CP-1 edge costs an 11-26 minute promotion per case. A required CP-1 edge that the core does not read would bind a head and prove nothing (D3). The run is CP-0 then CP-2E, seconds like CP-3D.
- If LEAD wants CP-1-sourced operands (as CP-2A/CP-2D/CP-L10 read T4.10), that is a different design: required CP-0 and CP-1 (`block`), `inputs="module_context"` view, no pack sources, the CP-L10 shape. The oracle would change its operand source (cells instead of quotes); the arithmetic is unchanged. Question 1.
- **Cross-check, no edge (LEAD ruling 1).** The builder asserts that the positive operands equal the frozen CP-1 values for the same items: EBITDA 30.0 and cash interest 5.00 (`cases/financial/manifest.json#fy2025_observations`), levered free cash flow 9 and total debt 50 (`#q4_ltm_derived_source_units`; the twelve months to Q4 2025 equal FY 2025 and the balance at 2025-12-31 in the frozen pack, `metric_coordinate_rule`), and that T2F.2 r03 and r04 (6.00x, 1.67x) equal the CP-1 ratios 30/5 and 50/30 of the pinned S1 oracle (`cases/snapshot/expected.json#CP-1.ratios`). No CP-1 head file is frozen, so the S1 oracle is the CP-1 reference. Recorded in `expected.cp1_cross_check`; assertion only, no edge and no runtime read.
- Probe (read-only, venv python, no patch): `registry.plan(("CP-2E",))` and `plan(("CP-2F",))` are both `("CP-0", "CP-2E")`; `edge_rule("CP-2E","CP-0")` is `block`; `edge_rule("CP-5","CP-2E")` and `("CP-6","CP-2E")` are `restricted`; `step_chain("CP-2E")` raises "CP-2E has no live step contract".

## Module kind and tools (G1-X protocol sections 1 to 3)

Owner-only: `step_chain` raises, so `entry="owner_core"`, core `src/deploy_workflow/owners/cp2e.py` supplies every section-2 item. It reads pack pages, so the step is an owner-only step with `sources=True`:

- `OWNER_SPECS["CP-2E"] = OwnerSpec(module_id="CP-2E", steps=(StepSpec("macro_fx", MacroFxSubmission, sources=True, extract=False, upstream_grant=None, inputs="none", rules="journaled"),), entry="owner_core", kind="analytical", publish=None)`. No `read_inputs` view (no `_VIEWS` entry): the pack tools are the evidence, as CP-3D.
- **Source scope (H1 host task).** Fixed host mapping `_SOURCE_STEPS["CP-2E"] = ("macro_fx",)` with scope = the **financial** source only (page:1 to page:5 in the positive run). Not the identity source (the step cites nothing from it) and never caller-supplied. A quote whose `source_id` is not `financial` is a journaled issue (`... is outside the CP-2E scope (financial)`).
- `RULES(text, seen) -> tuple[str, ...]` (protocol section 2): the absence rule (`UNBACKED_ABSENCE`, `Absence claim without a recorded search`) when any absence object is present and `seen` recorded no search, then unread citations in the product's sorted `(source_id, locator)` order (`Cited page not read through read_pages: financial page:N`). Absence objects of this step: `rate_absence`, `fx.debt_currency_absence`, `fx.operating_fx_absence`, `hedge_absence`. G1-X routes `rules="journaled"` to it at submit and in the verifier. No `precheck` (every content rule is a journaled invalid step, so the blocked case works; CP-3D Q4).

## Prerequisites

1. G1, S1a extension and G1-X integrated (owner_core entry, `_CORES`, sources=True owner-only step, `RULES` routing).
2. H1 host mapping above.
3. `docs/TOOL-CONTRACT.md` matrix row (LEAD amends at freeze): CP-2E `macro_fx`: `search_pack` and `read_pages` over the financial source only; no `extract_statements`, no `read_inputs`.
4. Pins (the builder asserts them): `cases/financial/manifest.json` `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`; `cases/snapshot/{manifest,submissions,expected}.json` `68d591f6…ca3f4`, `bff9ed18…fb35c`, `d1aa1af9…baa`; `src/deploy_vii/methodology.json` `348fbc4b877e4f0351ecc238ea005adf815291b15a6267f263459203a08f8d45`.

## Sources: what the frozen packs state and do not state

Reused unchanged (hash-checked): `cases/financial/manifest.json` sources `identity` and `financial`. The legal, snapshot business and market (`cases/cp3-cp6-owner`) sources carry no macro or FX content and are not used (the legal clause "USD 50 million" only corroborates the currency; it is not cited).

| Needed | In the frozen financial source | Result |
|---|---|---|
| Reporting currency | page:1 "Currency: USD; amounts in millions." | quoted |
| FX effect on cash | page:3 row "FX effect on cash 0 0 0 0 0"; page:1 "no ... FX cash movements ... through January 10, 2026" | known zero |
| Currency translation | page:1 equity roll-forward lists "currency translation" among zero movements | basis for the FX assessment |
| Debt, rate terms | page:5 one term loan, "floating rate type with SOFR reference rate, spread 0 basis points and floor 0 basis points", balance 50 at 2025-12-31; page:4 total debt 50.00 | quoted; rate shock computable |
| Currency of the debt | page:5 header "USD millions; consolidated group" (denomination clause not stated) | quoted; limitation |
| Reference rate level | none | missing (downward shocks refused) |
| Split of revenue or earnings by currency | none (one segment, no geography) | missing; currency effect on EBITDA missing |
| Hedging instruments, hedge ratio | none | missing; "after hedges" missing |
| EBITDA, cash interest, free cash flow (FY 2025) | page:2 and page:3 FY column: 30.0, 5.00, 9.00 | quoted |

**Limitation, not a synthetic source (recommendation, question 2).** The pack states currency USD, no FX cash movements and no currency translation, so the frozen pack gives a known-zero for FX cash and foreign-currency debt, and *nothing* for operating currency exposure or hedging. A synthetic macro source stating a non-zero foreign-currency revenue share or a hedge would have to be consistent with every frozen figure (one segment, `Currency: USD`, FX effect 0, no translation, other non-operating income 0): a non-zero exposure is at best strained by those, and a synthetic "no exposure" note would add a sourced claim the real world cannot give. No rate or index level is invented. Composer fixtures (`expected.json#fixtures`) carry test vectors for the branches the pack cannot reach (hedge 40 percent, 20 percent of EBITDA abroad, foreign-currency debt) and are marked as test vectors, never as source figures.

**Gap case.** `gap_no_facility_schedule`: the same financial source without page:5 (the facility schedule): pages 1 to 4 byte for byte, source sha256 recomputed by the pack rule (`0179b1bf…93d294`), a derived variant (question 4). Total debt, EBITDA, interest and FX effect stay known; the rate terms and the currency of the debt are absent: floating debt, every added-interest, coverage-after and debt-effect figure shows `∅ G#`, baseline coverage and leverage stay known.

## Files

- New `src/deploy_workflow/owners/cp2e.py` (about 450 lines).
- `owner_workflow.py` (G1-X): the spec above; `_CORES`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES` and `_ENTRY_VALIDATORS["CP-2E"]` = `owners.cp2e.ENTRY_VALIDATOR` (`owners/cp2e.py:1906`, registered at `owner_workflow.py:235`; protocol section 2 requires it of every analytical module but CP-0 and CP-1, as ruled for CP-4 in rulings round 1 Q3).
- D12 registrations: `host.py` `_SOURCE_STEPS` (H1); new `src/deploy_vii/bindings/cp2e.py` and `bindings/shipped.py`: one binding per table T2F.1 to T2F.9 (`expected.render.bindings`: T2F.1 to T2F.6 and T2F.8 to the `evidence` rail as `bindings/cp5.py` does, T2F.7 and T2F.9 to `limitations`, `unit_class` text, slot prefix `cp2e-`), because `validate_bindings` needs every fact of a restricted module bound exactly once and `report_view.build` raises otherwise. `cp2e_module` ships `Module.tables`: T2F.1 to T2F.9 as `ReportTable` layouts (`expected.cases.<case>.module_tables`). No `methodology.json`, `registry.py` or `report_view.py` edit.
- `methods/cp2e.md` adaptation record (shock conventions, table titles and columns; question 6).
- G2 `owner_rendering.py`: one `DeliveryScope` for `slice-cp2e-sensitivity` (module page and rails).
- New `tests/test_owner_cp2e.py`, `tests/cp2e_runs.py` (`cp2e_closed(case, root)`).

## The run

`slice-cp2e-positive`: pathway `credit_snapshot`, `requested_modules = ("CP-2E",)` (explicit value overrides the preset; no pathway lists CP-2E), plan `CP-0, CP-2E` (no CP-1, no CP-MODEL). Pack: identity and financial unchanged. CP-0 = `submissions.json#readiness_review.positive` (one consumer row, CP-2E, source `financial`, cites the facility sentence). The gap case is its own run `slice-cp2e-gap-no-facility-schedule` (different pack hash, its own CP-0 `readiness_review.gap_no_facility_schedule` with gap `missing-facility-schedule`). Both CP-0 literals were run through the product: `validate_review` returns no issues and `build_readiness` facts (32) and limitations equal `expected.cp0` for both packs (hand-built `PreparedPack`s, no run).

## Public API (`owners/cp2e.py`; keyword arguments except the seams)

```
MODULE_ID = "CP-2E"; STEP_ID = "macro_fx"; STEP_IDS = (STEP_ID,); QUALIFICATION
SCHEMAS = {STEP_ID: MacroFxSubmission}
probe(store, snapshot, attempt) -> None                         # identity_mismatch unless the settled attempt and head rebuild exactly
RULES(text, seen) -> tuple[str, ...]                            # absence rule, then unread citations (sorted)
submit(store, ticket_id, step_id, payload, rules) -> Submitted
# internals
# no `cp2e_upstream`: it was an internal with no consumer (rulings round 3 item 4). `settle` derives the inherited limitations, `submit_step` refuses changed inputs and `begin` binds CP-0.
validate_macro_fx(*, submission, pack) -> tuple[str, ...]       # quotes on page, whole-line rows, labelled values, ranges
derive_sensitivity(*, operands, rate_shocks_bp, fx_shocks, hedge_ratio) -> Sensitivity   # pure Decimal; no I/O
macro_fx(*, pack, submission) -> MacroFxReport                  # owners/cp2e.py:1827
cp2e_module(*, report, inputs, attempt) -> Module
cp2e_reader(store, head) -> Cp2eHead                            # consumer reader (D3), not a G1 seam
```

## Submission schema (reference and judgment only; every field required, `null` where an alternative is used)

```
MacroFxSubmission:
  reporting_currency: {source_id, locator, quote, code_text}
  rate_exposure: {facility_balance{quote,value_text}, rate_basis{quote,rate_type FLOATING|FIXED,reference_rate},
                  spread{quote,bps_text}, floor{quote,bps_text}} | null          # exactly one of rate_exposure / rate_absence
  rate_absence: {reason, follow_up} | null
  earnings: {ebitda, interest, fcf, total_debt}: {quote, value_text} each        # statement rows
  fx: {fx_cash_effect{quote,value_text},
       debt_currency{quote,code_text} | null, debt_currency_absence{reason,follow_up} | null,   # exactly one
       foreign_ebitda_share{quote,percent_text} | null, operating_fx_absence{reason,follow_up} | null}  # exactly one
  hedge_ratio: {percent_text, rationale} | null,  hedge_absence: {reason, follow_up} | null  # exactly one
  rate_shocks_bp: [str]  (1 to 3 whole bp, 1 to 1000, strictly increasing; analyst assumption, D11)
  fx_shocks_percent: [str]  (1 to 3 whole percent, 1 to 50, strictly increasing; analyst assumption, D11)
  shock_rationale: str
  assessments: [{section interest_rate|fx|hedging, category, text, basis[quote], limitation|null}]  # each section once
  summary: {text}
```
Rules (all journaled issues, exact wording in `expected.json#refusals`): every quote is a verbatim span of a `financial` page. A **statement row** is quoted as a whole page line, starts with its label (`Reported EBITDA`, `Cash interest paid`, `Levered free cash flow`, `Total debt`, `FX effect on cash`), the page header ends in the FY column and `value_text` is the row's last value; a **sentence operand**'s `value_text` occurs once as a whole token and follows its label (`balance of`, `spread`, `floor`); `rate_type` must agree with the word in the quote and `reference_rate` occur in it. All text is digit-free (so no figure can be spelled), assessments and summary carry none of `recommend, buy, sell, overweight, underweight, downgrade, upgrade, covenant breach`, `Insufficient Information` states its limitation and only it, `Documentary Fact` has a basis quote. Literals: `submissions.json#positive`, `#gap_no_facility_schedule`.

Analyst-typed numerals validated by containment follow the accepted CP-3D precedent (its Q7); a Python page parser is the alternative (question 5).

## Decimal composer (zero, missing, not applicable, blocked kept distinct)

Context 38 digits, half-even; stored exactly (trailing zeros dropped), shown half-up. Per-value state known | missing (with reason) | not_applicable (with reason). **Currency and scale (review M2).** Every fact with unit MILLIONS carries currency = the quoted reporting currency (`USD`) and scale `1000000`, as CP-1's facts and the CP-L10 oracle do; a MULTIPLE, PERCENT or basis_points fact carries none and the default scale 1 (`expected` fact fields `currency`, `scale`). The unit of a figure in a claim is the one `report_view.figure_unit` derives from the fact (MILLIONS in USD: `US$ m`; MULTIPLE `x`; PERCENT `%`; basis_points `bp`); without the currency `prose.issues` reports six unit issues, which is why the currency is pinned. **Operand bound.** A sentence operand (balance, spread, floor) is accepted only as 1 to 3 digits with at most 4 decimals (`NUM_RE`, at most 999.9999): a balance of 1000 or more cannot be quoted by this step. That is a validator bound, not a source limit.

| Quantity | Rule |
|---|---|
| floating-rate debt | facility balance if the quoted rate type is floating; 0 if fixed (known zero); missing if no rate terms |
| added interest, before hedges (shock k bp) | floating debt x k / 10000, annual. Only for upward shocks (the validator refuses k below 1) and only if the floor is quoted as 0 (reference rate level unknown): a floor above 0 or not stated is missing; a fixed-rate facility is a known 0 |
| after hedges | gross x (1 - hedge ratio); missing without a hedge ratio |
| interest after | cash interest paid + gross |
| interest coverage | EBITDA / cash interest (before) and EBITDA / interest after; change = after - before; zero divisor not_applicable |
| free cash flow after | levered free cash flow - gross (no tax shield); share of EBITDA = gross / EBITDA (EBITDA 0 not_applicable) |
| foreign-currency debt | facility balance if the quoted currency differs from the reporting currency; 0 if equal (known zero); missing if the currency is not stated |
| currency move m (foreign currency strengthens) | change in debt = foreign-currency debt x m; change in EBITDA = EBITDA x foreign share x m (missing without a share); total leverage after = (debt + change) / (EBITDA + change), missing if either change is missing |

Positive: floating debt 50.00, share of total debt 100.0%; coverage 6.00x, leverage 1.67x; shock 100 bp: +0.50 (exact 0.5), interest 5.50, coverage 5.45x (30/5.5), change (0.55)x, free cash flow 8.50, 1.7% of EBITDA (1/60); shock 200 bp: +1.00, 6.00, 5.00x, (1.00)x, 8.00, 3.3%; after hedges missing (no hedge ratio). Foreign-currency debt 0.00 (known), 0.0%; currency move 10%: change in debt 0.00, total debt 50.00, change in EBITDA and leverage after missing. Gap: floating debt, every shock figure and the foreign-currency debt missing; coverage 6.00x and leverage 1.67x known. Eight composer fixtures pin the branches (hedged 40 percent: 0.3 and 0.6; floor 25 bp: missing; fixed rate: known 0, coverage unchanged; zero interest: baseline not_applicable, after 60; zero EBITDA: coverage known 0, leverage not_applicable; foreign debt with 20 percent of EBITDA abroad: 55, 0.6, 30.6, leverage 1.7973…; no rate terms; **partial facility** (LEAD ruling 9): a quoted balance 30 below total debt 50 gives floating debt 30, floating share 60.0% (known, balance / total debt), added interest 0.3 and 0.6, and the own limitation `fixture_partial_facility.own_limitation_added`).

**Facility balance versus total debt (LEAD ruling 9, review M4).** The validator raises `rate_exposure.facility_balance: value_text <balance> exceeds total debt <total debt text>` when both values parse and the balance is above total debt; it comes after the `earnings.total_debt` row check (the example is a balance of 55 against 50.00). A balance below total debt is valid: the shock figures cover the quoted facility alone, the floating share stays known, and an own limitation names the remainder whose rate type no source states. No new case: the frozen pack has balance equal to total debt (no remainder), so the literal is a hand-built variant of page:5 (`submissions.json#hand_built_page_refusals`: sentence "closing facility balance of 55", with the page text sha256 and the recomputed pack source sha256) outside the 27 frozen-page literals, and the partial case is the fixture.

Tables (D8 ids registered already): T2F.1 sourced operands (12 rows), T2F.2 baseline exposure, T2F.3 interest rate shock (one row per shock), T2F.4 currency shock, T2F.5 hedging, T2F.6 assessments (+ shock basis, summary), T2F.7 missing inputs, T2F.8 evidence, T2F.9 limitations. Claims: one per rate shock (known form with three figures and a chip-free text, or a gap chip), one FX, one hedge, one summary; figures only as `{fact|unit}` references to the module's own facts (units derived by `figure_unit`: `US$ m`, `x`, `%`, `bp`), gaps as `[chip]`. Analyst-judgment numbers (shocks, hedge ratio) are uncited facts and never a claim figure. Own limitations: static parallel shock on closing balances and FY flows; interest income on the cash balance is not shocked (page:2 "Interest income 0" on the closing cash, so the added interest is not offset by higher income on cash); the quoted facility is only part of total debt when the balance is below it (remainder's rate type not stated; absent in the frozen pack); no reference rate level (floor 0 treated as not binding upward, downward not tested); hedging undisclosed (or the hedge ratio is an assumption); no split by currency; the currency of the debt read from the schedule header; macro drivers beyond rate and currency not sourced; unaudited statements. Module status `restricted`.

## Refusals

27 literal one-defect payloads (`submissions.json#refusal_mutations`, issues in `expected.json#refusals`), each the positive literal with exactly one defect (review M6: the row literal is two whole page lines in one quote, the rate-type literal names SOFR and states neither floating nor fixed, the foreign-share literal quotes the "Profit before tax" row whose 20 is valid in isolation, and the repeated-section literal appends a fourth `interest_rate` assessment, so it raises two issues of the one class and none for a missing section), each an invalid attempt 0 re-begun as attempt 1; plus **one hand-built-page refusal** (`submissions.json#hand_built_page_refusals`, `expected.hand_built_page_refusals`): a page:5 variant with closing balance 55, balance above total debt, exact issue `rate_exposure.facility_balance: value_text 55 exceeds total debt 50.00`, which is the only issue: quote contents (code, balance, label, floor, rate type, reference rate), row shape (not a whole line, wrong label, value not last, off page), scope (identity source; this class also hides a "quote not found" and the scope issue is the one pinned), exclusive-or fields (rate, debt currency, foreign share, hedge), ranges (hedge percent, shock 0, shocks not increasing, too many, currency move too large), text (digit, prohibited conclusion, Insufficient Information without limitation, Documentary Fact without basis), assessments (section missing, repeated). Every issue string is this draft's proposal, frozen when LEAD accepts. Tool-use refusals (journaled `RULES`): unread financial page:3, unread financial page:5, absence without a search. `blocked`: attempt 0 digit in text, attempt 1 floor not in quote, head blocked, no tables. G1-level: any `invoke` of `extract_statements` and any `read_inputs` is a refused `not_permitted` receipt; a snapshot change between read and submit is `stale_binding`; `begin` is refused (edge `block`) when CP-0 is blocked or stale.

Tamper (acceptance 5): the literal recipe is `expected.json#tamper` (CP-DR shape, `docs/CPDR-OWNER-LEASE.md:161`): on the closed positive store, forge fact `T2F.3.r01.cov_after` from 5.45x to 6.00x in the result Module, a new snapshot and `current`, the receipt and the settling `OwnerSubmission`, so that only `cp2e.probe`'s rebuild refuses with `identity_mismatch`.

## Tool use (D2)

Pack tools, no upstream view, so no D2 exception. Acceptance (`expected.cases.<case>.tool_use_required`): before the submit, ok `read_pages` cover every cited page (positive: financial page:1 to page:5; gap: page:1 to page:4); at least one ok `search_pack` (the absence objects); zero `read_inputs`; `extract_statements` refused. As CP-3D, an absence is backed by "some search over some source" only (the ToolRules precedent); recorded as a limitation of the rule.

## Consumption proof (D3): OPEN

No consumer core exists or reads CP-2E: `cp6_committee.py:112-114` states CP-2A, CP-2E, CP-2D, CP-3C and CP-3D "are never read, whatever the run binds" and the frozen CP-3 lease (`docs/CP3-OWNER-LEASE.md:32`) lists CP-2E among the CP-6 optional inputs that are not read; `registry.edge_rule("CP-6","CP-2E")` is `restricted` but unread. CP-5 (fan-in, `restricted`) counts only after a D3 scope lease and has no core (S1b). This lease therefore makes **no consumption claim**, and **CP-2E is not complete until a consumer reads it** (PLAN.md:8: actual downstream consumption); `docs/MODULES.csv` (row CP-2E) stays open on consumption (LEAD ruling 7; `expected.consumption.completion`). The CP-5 scope lease follows S1b; the frozen CP-3 lease is not amended. It ships `cp2e_reader(store, head)` and pins what a consumer must read (`expected.consumption`: head hash, status, floating debt, per shock the added interest before hedges, coverage after and the state of the after-hedge value, foreign-currency debt, hedge ratio or absence, own limitations). Recommend sequencing the CP-5 scope lease after S1b and not weakening D3; a CP-6 amendment would reopen the frozen CP-3 lease (question 7).

## Rendered sections (D7) and table ids (D8)

**D7 assignment (LEAD ruling, review M1).** No Front Page block exists for macro/FX (`report_view.py` has only `MODULE_FAMILY["CP-2E"] = "synthesis"`), no pathway lists CP-2E and no design reference assigns a macro/FX block, so none is added. CP-2E's assigned rendered deliverables for v1 are: (1) its **module page** (route `#CP-2E`; `renderModule` in `assets/app.js` draws the claims, then one panel per `Module.tables` layout with every cell a fact button, then facts of undeclared tables; the Analysis coverage link opens it; `render.py` serialises every non-rejected module) carrying T2F.1 to T2F.9 as the layouts of `expected.cases.<case>.module_tables`; and (2) the **Evidence and Limitations rails** of the scope `slice-cp2e-sensitivity` (`expected.render.bindings`: T2F.1 to T2F.6 and T2F.8 evidence, T2F.7 and T2F.9 limitations, slot prefix `cp2e-`). The Evidence view shows sources only and the inspector one fact on click, so the module page is where the analysis tables are read. Whether a module page alone satisfies PLAN.md:8's assigned rendered section is LEAD's D7 call; this lease states the assignment above and adds no Front Page block.

D8 collision check (the builder asserts it from `methodology.json`, and `grep -rl 'T2F\.\|T2G\.'` over src, tests, docs, cases, work and the root docs on 2026-10-28 found only `methodology.json` before this preparation): `T2F.1-9` and `T2G.1-8` appear only in the CP-2E entry. Registration: none changed. `T2F` is used (the alias CP-2F depth); `T2G.1-8` stay registered and unproduced (question 6).

## Acceptance (from `expected.json` only)

1. Positive (every MILLIONS fact carries USD and scale 1000000): CP-0 settles restricted with facts equal `expected.cp0.positive`; CP-2E settles `restricted` with inputs `prepared-pack`, `CP-0` (hash-equal to the head) plus `macro-fx-submission`; tables T2F.1 to T2F.9 equal cell for cell (ids, shown, units, value classes, periods, cites; `∅ G#` bound at run time); claims, own and inherited limitations equal; receipt verifies; store bytes unchanged afterwards.
2. Gap: the same on `expected.cases.gap_no_facility_schedule` with its own CP-0 and pack hash.
3. Composer fixtures (8) over `expected.fixtures` equal the stored values; the partial-facility fixture also adds its own limitation. The CP-1 cross-check (`expected.cp1_cross_check`) holds.
4. Refusals (27), the hand-built-page refusal (1, `balance_exceeds_total_debt`, run on the variant page with its pinned page and pack sha256), tool-use refusals (3), blocked, G1-level refusals.
5. Verifier and tamper case (`identity_mismatch` only from `probe`).
6. Rendering: `validate_bindings` of the shipped maps plus the CP-2E map (one binding per T2F table) is empty for both cases; `report_view.build` and `render` succeed; module-page probe: the rendered report data carries CP-2E with `tables` ids T2F.1 to T2F.9 whose rows and fact ids equal `expected.cases.<case>.module_tables`, claims equal the expected claims, every fact's table display equals its expected `shown` (gap numbers normalised), module status restricted; T2F.1 to T2F.6 and T2F.8 are bound to the Evidence rail and T2F.7 and T2F.9 to the Limitations rail (bound, not rendered there); the Limitations rail renders the module's own plus inherited limitations.
7. Consumption: recorded OPEN; CP-2E is not complete until a consumer reads it; no test claims it.
8. Claim check: `prose.prose_issues` empty for every expected claim (probe below).
9. D4: `registry.plan(("CP-2E",))` equals `expected.plan.plan`; `methodology.json` unchanged.
10. Gates: ruff check, ruff format --check, mypy strict on changed files.

## Deferred test commands (build-first: not run now; LEAD's final phase)

```
PYTHONPATH=src "../../../.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp2e.py   # light: no CP-1 promotion
python3 -I cases/cp2e-owner/builder/build.py && shasum -a 256 cases/cp2e-owner/*.json                 # oracle reproduces byte for byte
```
Plus ruff, `MYPYPATH=src mypy` on changed files, `tests/test_owner_workflow.py` unchanged.

## Open questions for LEAD (recommendation first)

1. **Operand source and D4.** Recommend pack pages, required CP-0 only, no methodology edit (above). Alternative: CP-1 T4.10/T4.18 cells with required CP-0 and CP-1 (CP-L10 shape).
2. **Sources the packs lack.** Recommend limitation plus known-zero/missing, no synthetic source (above); fixtures carry the unreachable branches. Alternative: a synthetic treasury or segment note, only if LEAD wants a non-missing FX or hedge result; it must not contradict `Currency: USD`, FX effect 0, no translation, one segment.
3. **Rendering. Resolved by LEAD (review M1).** Module page `#CP-2E` plus the evidence and limitations rails; every T2F table bound; no Front Page block. Open for LEAD only if a module page alone is judged not to satisfy PLAN.md:8: then a D7 block in a new pathway composition.
4. **Gap pack variant.** The gap pack is the financial source minus page:5 with a recomputed hash (a derived variant of frozen bytes, not a frozen source). Recommend accept; the alternative (analyst absence over the full pack) would contradict the page.
5. **Analyst-typed numerals.** Containment validation (row = whole line + last value; sentence = unique labelled token). Recommend accept (CP-3D Q7); alternative a Python parser reusing `financial_series`.
6. **Titles and T2G.** T2F.1-9 titles/columns are an adaptation (no r14 text); recommend `methods/cp2e.md`; recommend leaving `T2G.1-8` registered and unproduced (or trim in a later D12 edit if a coverage check demands).
7. **D3.** Open; recommend CP-5 scope lease after S1b. Alternative: amend the frozen CP-3 lease so CP-6 reads the CP-2E sensitivity (its own lease and review).
8. **Policy literals.** Shock bounds (1 to 1000 bp, 1 to 50 percent, at most 3) and the direction conventions (upward rate only; foreign currency strengthening) are screening policy no source states; the shock sizes in the literals (100 and 200 bp, 10 percent) are analyst assumptions (D11). Recommend accept; the oracle rebuilds from the constants.
9. **Facility balance versus total debt. Resolved by LEAD (ruling 9).** Validator rule and hand-built-page literal added (above); balance below total debt valid with an own limitation, one fixture, no new case.
10. **Hedge-ratio run.** The hedge-ratio branch is covered by a fixture and two refusals, not by a third run. Recommend accept; add a clone case if LEAD wants a settled run with an assumption.
11. **Currency of the debt.** Read from the schedule header ("USD millions"), not a denomination clause; own limitation states it. Recommend accept.
12. **Cosmetics.** Negative multiples show as "(0.55)x" (as transcribed by the CP-L10 oracle from `display.format_value`, not a render); a claim reads "the first rate shock tested" because the shock size is an uncited judgment fact.

## Probes run (read-only, build-first rule)

Revision 2: `python3 -I cases/cp2e-owner/builder/build.py` twice (identical sha256). Scratch probes (venv python, `PYTHONPATH=src` on a scratch copy of `git archive HEAD src` so `report_view.py` and `assets/app.js` are HEAD's, not the working tree's other-task patch; each under 60 s): independent Decimal re-derivation of every derived value and fixture; `validate_bindings` over `SHIPPED_MAPS` plus the full CP-2E map (T2F.1-9, 0 issues, both cases) and over a rails-only map (73 unbound-fact issues, which is why every table is bound); `report_view.build` and `render` of a view carrying the CP-2E module with `Module.tables` layouts: report data lists T2F.1-9 and equals `module_tables`, table displays equal `shown`; `prose.issues` over the 10 expected claims with currency USD and scale 1000000: 0 issues (6 with currency None); `fact_spelling` 0 mismatches; `prose.bare_figures` over 40 literal analyst, own and fixture texts: 0 hits, control `Bare figure: 20`; tool-use refusal, quote verbatim and registry probes as in revision 1. No pytest, no heavy job, nothing written under `src/`.

Not verified: no CP-2E core, validator or composer exists, so no expected value was compared with product output; the G1-X sources=True/`RULES` seams and the H1 host scope for CP-2E are proposals; the CP-2E consumer row in CP-0 was validated by `validate_review`/`build_readiness` only (revision 1), not settled in a run; display spelling of negative multiples and the percent `decimals` override is transcribed from the CP-L10 oracle (the revision-2 render probe built a view from oracle facts, not a settled run); `∅ G#` numbering of the rails, tamper, stale-binding and begin-refused cases are design only; no browser rendering of the module page (the Node/DOM path was not run); the module-page deliverable under PLAN.md:8 is LEAD's D7 call.
