# CP-2D (Liquidity) owner lease - FROZEN by LEAD 2026-10-28 (draft rev 3)

Pre-code; frozen after `review-precise-3.md` (FREEZE), with its two Low notes applied as LEAD wording amendments in Acceptance 1. Pins: manifest d92861e03dc43b6e92504b10b61fdd2d4a61d243c378e2d3b4bf816b3aed4503, submissions cf0a4a773053f5925e0ab69ec64f0962e75d5e051287a1176ff994c74319946c, expected 7e998cb88b0923ca85ff2c5a3ee684525ec8a8f4445b8a5ecb2ed6aeea92950c, builder 0182af3b264292745ac77509926c167eb91aa0126c62ff9dc7b6e56c3ad0613e. Oracle: `cases/cp2d-owner/` (manifest, submissions, expected, stdlib builder). No CP-2D core exists, so this lease designs one (`src/deploy_workflow/owners/cp2d.py`); it writes no code. Every G1 seam (owner-core entry, signatures, registration, precheck) is `docs/G1X-OWNER-CORE-PROTOCOL.md`, which supersedes any signature or design statement of this lease that differs from it.

## Why

CP-2D is the liquidity bridge between the settled credit view and the covenant/refinancing pathway. Python computes sources and uses, run-rate cash flow, cash runway, the maturity wall (T4.18), revolver availability and the funding gap; the analyst judges only the horizon, the minimum cash and three short assessments. Edges: required CP-0, CP-1, CP-2 (all `block`; `methodology.json`, no `edge_rules`). Pathway FP04 (`covenant_refinancing`) names three blocks it fills: `liquidity-runway`, `maturity-wall`, `funding-gap`. Today those render through the unbound-owner path (`report_view.py:1179-1184`, `_spec_of`).

The r14 CP-2D SKILL.md is not in this repository (the same situation as CP-2, decision 0005). The table ids `T2E.1..7, T2E.9` are registered (`methodology.json`, 8 required tables) but their titles and columns are defined here as an adaptation record; LEAD confirms (open question 5).

## Prerequisites

1. S1a (`docs/S1A-OWNER-RUN-LEASE.md`) is NOT yet integrated: `owner_workflow.py` supports only CP-0 and CP-1 (`SUPPORTED_ANALYTICAL`); the S1a extension (CP-1A, CP-2, `module_context` reads, `_owner_historical`) is uncommitted. G1-X follows S1a's integration.
2. G1-X (`docs/G1X-OWNER-CORE-PROTOCOL.md`), built after S1a. CP-2D is an owner-only module (protocol section 1): `step_chain("CP-2D")` raises "has no live step contract" and stays so; `OWNER_SPECS["CP-2D"]` uses `entry="owner_core"`, `sources=False`, `inputs="module_context"`, `rules="none"`; `owner_workflow.py` gains `SUPPORTED_ANALYTICAL` += CP-2D and `_CORES["CP-2D"] = cp2d` (fixed dict). No `src/deploy_vii` registry edit and no `StepChain` for CP-2D (deploy_vii never imports deploy_workflow); the registry-derived tables (`tool_sets`, `regression_cases`, `module_route`) are therefore not touched, but `registry.plan` already places CP-2D after CP-2.
3. The core module meets protocol section 2: `QUALIFICATION`, `STEP_IDS = ("liquidity_bridge",)`, `SCHEMAS`, `probe`, `view`, `submit` (no `precheck`: validation failures journal as invalid steps, as in the Refusals section).
4. TOOL-CONTRACT.md row for CP-2D (tool use section).
5. G2 delivery scope for the run (rendering section).
6. A CP-0 literal delta: one extra consumer entry (`submissions.json#cp0_consumer_delta`).

## The run

New run `slice-cp2d-positive`: pathway `covenant_refinancing`, `requested_modules` = CP-1, CP-1A, CP-2, CP-2D; `registry.plan` gives `CP-0, CP-1, CP-1A, CP-2, CP-2D` (checked). It reuses the S1 source bytes (identity and financial from `cases/financial/manifest.json`, business from `cases/snapshot/manifest.json` positive; pins in `manifest.frozen_inputs`) and the S1 CP-0 (plus the delta), CP-1, CP-1A and CP-2 literals unchanged.

It is a new run, not an in-place extension of S1a: `Run` is part of `PreparedPack` (`preparation.py:48-51`), so the pack hash changes with `pathway`, `requested_modules` and `run_id`; FP04 renders only for pathway `covenant_refinancing` (`render.py:130`). CP-MODEL is left out because `plan` puts CP-MODEL before CP-2D and G1 refuses an analytical module after a deterministic one. Consequence: the S1 expected tables of CP-1A and CP-2 (which depend on CP-MODEL as a CP-1A consumer) are not reused; only upstream statuses and the CP-1 facts are asserted. The S1 CP-2 positive literal cites no consumer-dependent row (checked: no `T2D.10`/`downstream_readiness` ref), but its validity without CP-MODEL is untested.

Cost: CP-1 promotion once (11-26 minutes). The two other CP-2D cases clone the settled store before CP-2D begins (as S1a clones for A3), so they add attempts, not promotions.

## Method (what Python computes; every value is a Decimal)

All figures: USD, unit MILLIONS, entity "Northbridge Synthetic Group, IFRS consolidated group". Balance date D0 = latest period end = 2025-12-31 (the QUARTER period wins over its FY alias, rule of `financial_series._maturity_figure`). Flows: the twelve months to D0 (LTM Q4 25, equal to FY25). Operands are read from the bound CP-1 head by the predicates in `manifest.fact_bindings` (observed on a real promoted head; never chosen by the analyst).

1. **Sources and uses (T2E.1), historical.** Opening cash + operating cash flow + investing + net debt issued + equity issuance and repurchases + dividends + other investing and financing + FX effect = closing cash (calculated); compare with reported closing cash; difference shown. Positive: 15 + 19 - 10 + 5 + 0 - 9 + 0 + 0 = 20; reported 20; difference 0.
2. **Liquidity position (T2E.2).** Cash, restricted cash, revolver commitment, revolver drawn, undrawn committed revolver = commitment - drawn (equals CP-1 T4.10 `undrawn_rcf`, asserted), undrawn term-loan commitment (T4.18 commitment - drawn, shown, not counted), available liquidity = cash + undrawn revolver (equals CP-1 `liquidity`, asserted), total debt, liquidity to total debt (equals CP-1 `liquidity_to_debt`, asserted).
3. **Run-rate (T2E.3).** Annual F = operating cash flow + investing + financing - net debt issuance (new borrowing is excluded: committed undrawn funding is zero). Horizon H months (judgment, 1..60: near-term); horizon end = D0 + H months; F over horizon = F x H / 12; maturities in horizon = principal of a facility with `maturity_date` <= horizon end; amortisation in horizon = for a facility maturing later, min(annual amortisation x H / 12, principal), else 0; cash at horizon end before refinancing = closing cash + F over horizon - amortisation - maturities. The runway row reads "Months until cash reaches minimum cash from run-rate cash flow alone (excludes maturities and amortisation)" and carries its own limitation; the maturity wall stays in T2E.4 and T2E.5. start = cash + undrawn revolver - minimum cash. Minimum cash missing: the row is missing ("Not calculable: minimum cash not assessed"). F < 0: max(0, start) / (-F / 12), 1 dp half-up, stored quantised ("20.0"). F >= 0: "Not reached at run rate" when start >= 0, and 0 months when start < 0. Revolver missing: "Not reached" only when F >= 0 and cash alone clears the minimum (a revolver is never negative), else missing ("Not calculable: revolver undisclosed").
4. **Maturity wall (T2E.4).** One row per T4.18 facility at D0: principal, maturity date, whole months from D0 (positive 48), inside horizon (Yes/No), share of total debt, cumulative share.
5. **Funding gap (T2E.5).** Resources = cash at horizon end + undrawn revolver; headroom = resources - minimum cash; gap = max(0, minimum cash - resources). A computed 0 means "no gap" and is distinct from missing.
6. **Missing rule.** Any missing operand makes each dependent value missing with a limitation; nothing defaults to 0. With the revolver undisclosed only `cash_only_headroom` (cash at horizon end - minimum cash, excluding any revolver, a lower bound) stays known. Minimum cash absent: headroom, cash-only headroom and gap are missing (not 0); cash at horizon end stays known. Source-reported unlevered free cash flow is missing in CP-1 and is read, listed in T2E.9 and never used. A non-zero sources-and-uses difference (calculated closing cash less reported) is shown as a known value with the own limitation "Sources and uses differ from reported closing cash by <x>"; it never refuses.

Expected numbers (all derived in `build.py` from the frozen page text; see `expected.json#cases`):

| Case | Horizon | Min cash | F annual | Cash at horizon end | Maturities in horizon | Headroom | Funding gap |
|---|---|---|---|---|---|---|---|
| positive | 24 | 10 | 0 | 20 | 0 (maturity 2029-12-31 > 2027-12-31) | 10 | 0 (known) |
| long_horizon | 60 | 10 | 0 | (30) | 50 (2029-12-31 <= 2030-12-31) | (40) | 40 |
| gap_minimum_cash | 24 | none | 0 | 20 | 0 | missing | missing |
| fixture_rcf_undisclosed | 24 | 10 | 0 | 20 | 0 | missing (cash-only 10 known) | missing |
| fixture_rcf_undisclosed_min_above_cash (min cash 30) | 24 | 30 | 0 | 20 | 0 | missing (cash-only (10) known) | missing; runway missing "revolver undisclosed" |
| fixture_burn (CFO 13.00) | 24 | 10 | (6) | 8 | 0 | (2) | 2, months to minimum 20.0 |

## Files

New (under `src/deploy_workflow/` and `tests/`; `src/deploy_vii` only through the D12 registrations below):
- `owners/cp2d.py`: the core (about 400-550 lines).
- `owner_workflow.py` (G1-X, protocol section 2): `OWNER_SPECS["CP-2D"]`, `_CORES["CP-2D"]`, `SUPPORTED_ANALYTICAL`, `_QUALIFICATION["CP-2D"]`, `_PROBES["CP-2D"]`, `_VIEWS["liquidity_bridge"] = cp2d.view`.
- `tests/test_owner_cp2d.py`, and `tests/cp2d_runs.py` exporting `cp2d_closed(case, root)` (pack assembly, literals, run-time substitutions, tool-call sequence; G2 imports it).

D12 registrations (PM serialises; recorded in `docs/reuse/manifest.json`):
- `bindings/shipped.py`: `CP2D` after `CP2` in `SHIPPED_MAPS`; new `bindings/cp2d.py` (FP block bindings only, no arithmetic, never imports `deploy_workflow`; protocol section 6).
- `report_view.py`: three `_Spec` rows added to `_COVENANT_REFINANCING` (D7, see Rendering).
- `registry.py`: no change. `methodology.json`: no change (table ids already registered, D8 check below).

## Public API

Seam functions are positional and exactly as protocol section 2 (the consumer reader `cp2d_reader(store, head)` is positional too and is listed under the seams); the core's internal functions take keyword arguments only.

```
owners.cp2d.MODULE_ID = "CP-2D"; STEP_ID = "liquidity_bridge"; STEP_IDS = (STEP_ID,); QUALIFICATION
SCHEMAS = {STEP_ID: LiquidityBridgeSubmission}
class MinimumCash(Contract):          amount: Decimal; rationale: Text; basis_refs: tuple[Identifier, ...]
class MinimumCashAbsence(Contract):   reason: Text; follow_up: Text
class Assessment(Contract):           section: Literal["liquidity_runway","maturity_wall","funding_gap"]
                                      category: Literal["Documentary Fact","Management Language","Analyst Interpretation","Insufficient Information"]
                                      text: Text; credit_implication: Text; basis_refs: tuple[Identifier, ...]; limitation: str | None
class LiquidityBridgeSubmission(Contract):
                                      horizon_months: int; minimum_cash: MinimumCash | None
                                      minimum_cash_absence: MinimumCashAbsence | None; assessments: tuple[Assessment, ...]
# seams (positional; protocol section 2)
probe(store, snapshot, attempt) -> None                 # raises WorkflowError("identity_mismatch") unless the settled attempt and head rebuild exactly
view(historical, attempt) -> tuple[str, str]            # (sha256, body) of the exact read_inputs view; registered in _VIEWS["liquidity_bridge"]
submit(store, ticket_id, step_id, payload, rules) -> Submitted   # live.submission.Submitted: payload, nulls_resolved, prefilled, prefilled_kinds
cp2d_reader(store, head) -> Cp2dHead                    # consumer reader for CP-3C (see Consumption); not a G1 seam
# internals (keyword arguments only)
cp2d_upstream(*, store, attempt) -> Upstream            # bound CP-0, CP-1, CP-2 heads, current inputs, inherited limitations
operands(*, cp1) -> Operands                            # the predicate reads; missing stays missing
compose_bridge(*, operands, horizon_months, minimum_cash, balance_date) -> Bridge   # pure Decimal; no I/O
validate_liquidity_bridge(*, submission, upstream) -> tuple[str, ...]
liquidity_bridge(*, pack, submission, upstream) -> LiquidityBridgeReport
cp2d_module(*, report, inputs, attempt) -> Module
context_block(*, pack, upstream) -> dict[str, object]   # the exact read_inputs view; view() hashes it
```
Reuse. `model/debt.py`, `model/metrics.py` and `facility_fx.py` operate on `Cp1Registers`/`Column`/`FinancialBook` (CP-MODEL frames, pre-promotion books), not on CP-1 head facts, so none is callable from a CP-2D core without rebuilding that frame. CP-1 already computes and settles `undrawn_rcf`, `liquidity`, `cash_closing`, `total_debt`, `liquidity_to_debt` in T4.10; the composer reads them and asserts its own recomputation equals them (a cross-check, not a second source). New arithmetic is limited to F, horizon rolls, maturities, headroom and gap. The T4.18 reader imports `deploy_workflow.financial_series._maturity_figure` (`src/deploy_workflow/financial_series.py:194`, same package: QUARTER over FY alias; alias terms must agree; one row per `facility_id`); the oracle pins the selected facts (`manifest.fact_bindings`). LEAD ruled this (former open question 1, closed). Facility FX: a facility in another currency than USD is not summed; the composer sets the maturity-wall row and every total to missing with a limitation (`debt.py` docstring rule "no FX"); not exercised by any frozen pack.

## Submission schema (reference and judgment only)

Digit-free text, no figures: figures are Python's, shown only in tables and in Python-composed claims whose figures are `{<fact_id>|<unit>}` references to CP-2D's own table cells (MC-2: `execution.py:296` runs `prose_issues` on every claim, so a claim spelling a bare figure is refused; a date is a period label). The oracle names each cell `T2E.<n>.rNN` (one value column) or `T2E.<n>.rNN.cK`; `expected.json#cases.<case>.claims` freezes each claim `template` as run text, `text` as its resolved spelling and `references` as the cell ids. The horizon length is not spelled in a claim: its cell is an uncited `analyst_judgment` fact, which a figure reference refuses (no citation or calculation). Literal examples: `submissions.json#cp2d.{positive,long_horizon,gap_minimum_cash}`. `basis_refs` are CP-1 fact ids (tokens `{{FACT:name}}` bound at run time by `manifest.fact_bindings`). Exactly one of `minimum_cash` and `minimum_cash_absence`. Exactly one assessment per section. An `Insufficient Information` assessment states its `limitation`; no other does. `minimum_cash.amount` is an uncited analyst assumption (decision D11 first needed here; open question 2): stored as a Fact with `value_class` `analyst_judgment`, never mixed into source totals.

## Composer: zero / missing / blocked

- Zero is a known value (explicit-zero revolver, zero amortisation, a computed funding gap of 0). Missing is a Fact with `status` `missing`, `amount` None and a `limitation`; it displays as the report's gap spelling with a `G#`, never `0` and never `N/A`. Blocked is the module-level state: a blocked or stale required upstream edge refuses `begin` (`NotAuthorized`/`ValueError`, edge_rule `block`).
- Cells copied from CP-1 keep that fact's own `value_class` (T4.5 statement-history facts `calculated`, so the eight T2E.1 copies are `calculated`; T4.6 and T4.18 `source`), `status` and citations, and normalise the unit `currency` to `MILLIONS` (both USD, scale 1e6; the product mixed-unit check in `report_view.py:1288-1294` would otherwise refuse T2E.1, T2E.2 and T2E.5); expected cells record the normalisation as `cp1_unit`. Computed cells are `calculated` with the formula in `Fact.formula` and `calculation_id`; judgment cells `analyst_judgment`.
- Module status `restricted` (own limitations are non-empty: run-rate basis always, plus the minimum-cash line). Own limitations (`expected.json#cases.<case>.own_limitations`, one T2E.7 row each): always "Run-rate basis" and "Runway basis" (the runway excludes maturities and amortisation); "Minimum cash is an analyst assumption, not a source figure." or, when not assessed, "Minimum cash was not assessed, so headroom and funding gap are not calculated."; "Interest after maturity" when a maturity falls inside the horizon (cash interest stays in F after the maturity date: conservative; if it stopped, long_horizon would show cash (25) and gap 35); "Sources and uses differ from reported closing cash by <x>" only when the difference is non-zero; "Funding gap on cash alone" when the revolver is undisclosed (the gap is provably 0 on cash alone when cash-only headroom is non-negative; it is reported missing, conservatively, with cash-only headroom as the lower bound). Claims are references, not spelled figures (see Submission schema). Zero, missing and blocked stay distinct in data and in claim wording: a missing gap reads "The funding gap is not calculated: the minimum cash has not been assessed."; the absence of a revolver reads "because there is no revolving credit facility" (an explicit zero in the source), never "not disclosed".
- Inherited limitations: CP-0 literal part + CP-1 head (limitations, then inherited) + CP-2 head (limitations, then inherited), de-duplicated, own removed (`execution.py:345-366`); CP-1A is not an edge and is not read (the view tree lists CP-0, CP-1, CP-2 only). Bound at run time (as S1a R3-Q1).

## Refusals (wording fixed; `expected.json#refusals`)

Validator issues (the step is invalid; attempt 0 re-begun as attempt 1, attempt 1 invalid settles blocked): horizon outside 1..60 (a non-integer horizon is a schema type error owned by G1's generic schema refusal, not a CP-2D validator class); negative minimum cash; both or neither of `minimum_cash`/`minimum_cash_absence`; section missing or repeated; any digit in a text field; a prohibited conclusion (refinancing path, LME, recommendation, recovery outcome, covenant breach, and covenant-compliance wording: "covenant test is met", "in compliance with", "covenant compliance": CP-3C/CP-4/CP-3/CP-6 territory, CP-4 is not an upstream edge); a `basis_refs` id the view does not offer; Insufficient Information without limitation, or a limitation without it. Maturity-wall statements cite `T4.18 maturity_date`. Run refusals: any `invoke` is a refused `not_permitted` receipt; a submit without its own read is `not_permitted`; snapshot change between read and submit is `stale_binding`; `begin` is refused (edge_rule `block`, no attempt consumed) when CP-2 is blocked or stale. Negative cases in `expected.json#negative_cases`: `blocked_cp2d` (attempts 0 and 1 both invalid, module blocked, `submissions.json#cp2d_blocked`) and `begin_refused_cp2_blocked`.

## Tool use

CP-2D has no pack source and no pack tool (`pack_sources` empty). The only evidence of tool use is `read_inputs`, so a D2 exception is needed, exactly as CP-2's: add to TOOL-CONTRACT.md's matrix "CP-2D liquidity_bridge: exactly the view `owners.cp2d.view(historical, attempt)` registered in G1's `_VIEWS["liquidity_bridge"]` (`module_context()` has no such entry and deploy_vii cannot register a deploy_workflow core): the bound CP-1 facts named by `manifest.fact_bindings` (`ref`, `name`, `label`, `period`, `unit`, `shown`, `status`, `limitation`) including missing ones, upstream statuses, the horizon (1..60) and minimum-cash bounds and the inherited limitations; no quote, citation or record_json at any depth; key tree frozen in `cases/cp2d-owner/manifest.json#view_tree_draft` after a probe on the first product-settled core". Missing facts are offered with their status (unlike CP-2's `referencable`), because zero and missing must be distinguishable to the analyst. Acceptance: zero ok calls; exactly one `read_inputs` per attempt before the submit; its body shape equals the frozen tree; no `quote` string of the S1 literals occurs in it. The view tree in the manifest is a draft proposal, not an observation.

## Consumption proof (D3)

No consumer core reads CP-2D today: `cp3_relative_value.py:100` and `cp6_committee.py:113` state they never read it; CP-5 counts only after a D3 scope lease. The planned consumer is CP-3C (required edge CP-2D -> CP-3C; methodology `covenant_refinancing`: CP-2D then CP-4 then CP-3C); it has no core, no lease and no registry chain. Therefore consumption of CP-2D stays OPEN in this lease and no completion claim covers it. This lease ships the reader CP-3C will bind (`cp2d_reader`) and pins what it must expose (horizon, minimum cash or its absence, maturity-wall rows, funding gap or missing, head hash and status; `expected.json#consumption`). Recommend LEAD sequences CP-3C next so CP-2D can complete; do not weaken the rule.

CP-2 consumption: CP-2D binds the CP-2 head (edge) and inherits its limitations and status only; it reads no CP-2 content. That does not advance CP-2's own consumption. Open question 6.

## Rendered sections (D7) and table ids (D8)

Blocks exist as names only; no `_Spec`, no CP-2D binding map exists. This lease adds (admitted D12 one-liners):
- `report_view.py` `_COVENANT_REFINANCING` rows: `liquidity-runway` ("Liquidity and cash runway"), `maturity-wall` ("Maturity wall"), `funding-gap` ("Funding gap"), each `_Spec(title, "CP-2D", "dense", ("CP-2D",), route_label="Full analysis")`. `liquidity-runway` also appears in `distressed_restructuring`; `_spec_of` is by block id, so the same spec serves it. Whether CP-2G should share ownership there is open (MODULE_FAMILY puts both in "liquidity").
- `bindings/cp2d.py`: slots prefixed `cp2d-` (unique across SHIPPED_MAPS): `T2E.3` -> `liquidity-runway` (primary, "Cash runway") and `T2E.1` -> `liquidity-runway` ("Sources and uses"); `T2E.4` -> `maturity-wall`; `T2E.5` -> `funding-gap` (primary) and `T2E.2` -> `funding-gap` ("Liquidity position"); `T2E.6`, `T2E.9` -> `evidence`; `T2E.7` -> `limitations`.
- Who renders: G2 `owner_rendering.py` with a new `DELIVERY_SCOPES` entry for `(covenant_refinancing, [CP-1, CP-1A, CP-2, CP-2D], synthetic)`, sections `liquidity-runway`, `maturity-wall`, `funding-gap` and the two rails. The other FP04 blocks are unasserted (CP-4 not requested; CP-3C has no core), as the CP-4 FP04 lease does.

D8 collision check, run 2026-10-28: `T2E.1`-`T2E.7` and `T2E.9` appear only in the CP-2D entry of `methodology.json`, in no other module's `table_ids` and in no other file under `src/` or `tests/`; `T2E.8` is unregistered and stays unused. No new registration is required.

## Acceptance (from `expected.json` only)

1. **Positive.** CP-0, CP-1, CP-1A, CP-2 settled restricted; CP-0 facts for CP-2D equal `cp0_with_cp2d`; CP-1 facts bound by `fact_bindings` have the amounts and statuses of `source_facts`; CP-2D settled `restricted` with inputs `prepared-pack, CP-0, CP-1, CP-2` hash-equal to the final heads plus `liquidity-bridge-submission`; tables T2E.1-T2E.7, T2E.9 equal `cases.positive.tables` (ids `r01..`, columns, `shown`, units, value classes, currency USD on every amount cell, and a citation (CP-1 copy) or `calculation_id` (own computed cell) on every cell a claim references; LEAD amendment, review-precise-3 L1); each `Claim.text` equals `cases.<case>.claims[].template`, and the resolved rendering of the claim equals `text` (review-precise-3 L2); own limitations equal; the receipt verifies; store and model bytes unchanged afterwards.
2. **long_horizon.** Same upstream clone; funding gap 40, headroom (40), maturities in horizon 50, `Inside horizon` Yes.
3. **gap_minimum_cash.** Headroom, cash-only headroom, gap missing (gap spelling, never 0); runway row, headroom, cash-only headroom, gap missing; funding-gap claim reads "The funding gap is not calculated: ..."; T2E.7 lists Minimum cash as Gap; module still settles restricted.
4. **Fixtures (composer, no run).** `compose_bridge` over `fixture_rcf_undisclosed`, `fixture_rcf_undisclosed_min_above_cash` (runway missing, not "not reached") and `fixture_burn` equals `cases.<fixture>.derived` (the fixtures carry no tables; `fixture_burn` shows sources and uses difference (6) and its own limitation).
5. **Refusals.** Each of `submissions.refusal_inputs` is a full literal payload (`base_case`, `payload`, no mutation directive) and produces the issue text in `expected.refusals`; `cp2d_blocked` attempts 0 and 1 are full literal payloads too; zero ok calls; read-before-submit rule; stale binding; `blocked_cp2d` settles blocked; `begin` refused when CP-2 is blocked.
6. **Verifier probe.** `cp2d.probe` reruns validation on the frozen execution and gets the head hash back; tampering with the retained read body, the step output or the head makes `verify_owner_run_receipt` refuse with `identity_mismatch`.
7. **Rendering.** The three blocks are populated, owner CP-2D, with the tabs of `fp04_render`, cells equal to expected `shown`; gap cells render `∅ G<n>` (the product spelling, display.py); the expected `shown` of a gap cell is the pattern `∅ G#` with n bound at run time, an A7 exception.
8. **Consumption.** Recorded as OPEN; no test claims it.
9. **Gates.** ruff check, ruff format --check, mypy strict on the changed files.

## Deferred test commands (build-first: not run now; LEAD's final phase)

```
cd "<LEAD worktree>" && PYTHONPATH=src "../../../.venv/bin/python" -m pytest tests/test_owner_cp2d.py -x -q      # heavy lock, one CP-1 promotion
python3 -I cases/cp2d-owner/builder/build.py && shasum -a 256 cases/cp2d-owner/*.json                            # oracle reproduces byte for byte
```
Plus the lease's own gates (`ruff`, `MYPYPATH=src mypy` on the changed files) and `tests/test_owner_workflow.py` unchanged (G1 regression).

## LEAD rulings applied (2026-10-28; `report.md`, rulings and rulings on review-precise-1)

1. Undisclosed revolver stays a composer fixture; the pack-run gap is missing minimum cash; a synthetic financial variant is deferred.
2. D11: minimum cash is allowed as an `analyst_judgment` Fact, always with a recorded limitation, never a source figure.
3. Core layering: `docs/G1X-OWNER-CORE-PROTOCOL.md` (owner-only module, `entry="owner_core"`, positional seams); no `src/deploy_vii` registry edit.
4. T2E titles, columns and claim wording: accepted as a recorded LEAD adaptation in `methods/cp2d.md` (draft: `methods-cp2d-draft.md`); the left-out items are listed there.
5. CP-2 content: CP-2D reads status and inherited limitations only; D3 stays open until CP-3C; `cp2d_reader(store, head)` is pinned for CP-3C.
6. A separate `covenant_refinancing` run without CP-MODEL for this slice.
7. Run-rate runway: the row reads "from run-rate cash flow alone (excludes maturities and amortisation)" with its own limitation; horizon 1..60; the other review-precise-1 corrections (value classes and units, missing minimum cash, fixture tables dropped, covenant wording, gap wording, limitations, blocked cases) are in the sections above.

## Open questions for LEAD (with recommendation)

1. **T4.18 reader.** CLOSED by LEAD ruling: import `deploy_workflow.financial_series._maturity_figure`; the oracle pins the selected facts.
2. **Horizon anchor.** Horizon starts at the balance date 2025-12-31, not `as_of` 2026-01-10 (cash is a balance-date figure). Recommend keep.
3. **Run-rate basis.** LTM held flat, no growth, no new borrowing, dividends held flat: a method choice, not a source fact. Recommend keep as the standing limitation.
4. **`liquidity-runway` in the distressed pathway.** Shared id; CP-2G/CP-2A may need to share or split. Recommend leave to the distressed lease.

Not verified: the G1-X seams are cited from the protocol, not built; no CP-2D code, validator or composer exists, so no expected value has been compared with product output; the builder (`python3 -I`, twice, identical hashes) is the only thing run besides read-only probes of a real promoted CP-1 head (predicates, fact statuses, display spellings via `fact_spelling`) and `registry.plan`/`edge_rule`/`step_chain`. CP-0 delta fact ids copy the S1 CP-2 pattern and were never settled. The view tree is a proposal. The `G#` display, the 0 dp half-up spelling of negatives and the months arithmetic follow `display.py` read, not run, for CP-2D's own facts.
