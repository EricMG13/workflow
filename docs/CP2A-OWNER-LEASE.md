# CP-2A (Downside pathway) owner lease — FROZEN by LEAD 2026-10-28 (draft rev 3 = preparation revision 4)

Amended by LEAD 2026-10-28 (Stage 1 release batch, `docs/rulings/2026-10-28-stage1.md`; `work/lead/stage1-release/report.md`): round 6 review L1 (the `BREAK_AT_BASE` own limitation adds `, and it is not calculated on a single-quarter base` on a gated-not-applicable base only), L2 (the net-leverage short-circuit runs only on an ungated base, A8) and L3 (a mixed quarter base is refused by an assertion), plus the comment on the derived Q4 cell text. Pass 2: A4 (a missing base FCF is named first in the T2B.3 FCF cell, formula order F before I). `expected.json` changes only `cases.fixture_quarter_known.own_limitations[7]`; manifest and submissions are unchanged. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` ad5531da7cff4eca8e9c8e9a23cef6526a982537597e6830610877bec994ff89 → 4b6138d79be7e8e0780eeade0cc09881658cf175b0c0b1cee1f0a083b1ea126a; `builder/build.py` 4c07bb4cdbfdd6a9410d1c77a4e9b35c7053b9d7e5ad73a8b593406a537b6e4b → 19d207606c47dd33b2dd1bf79269d5af3020ebdc8c9595547cc706b78adcb580. A double scratch rebuild of every builder in dependency order was byte-identical. Pin consumers: `cases/cp2g-owner/builder/build.py` pins `expected.json`, `manifest.json`, `submissions.json`; `cases/cp4c-owner/builder/build.py` pins `expected.json`, `submissions.json`. Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change.

Amended by LEAD 2026-10-28 (round 6 oracle batch, `docs/rulings/2026-10-28-stage1.md` round 6; `work/lead/r6batch-review.md` COMMIT): adds the composer-only fixture `fixture_quarter_known` (owner ruling on CP-2A P1; round 6 P1-W). Only additions are made, under `fixture_quarter_known` in all three files; no existing case moves. A scratch rebuild in dependency order was byte-identical. builder fab2a0e2… → 4c07bb4cdbfdd6a9410d1c77a4e9b35c7053b9d7e5ad73a8b593406a537b6e4b; manifest 96c6644b… → 5219f063dcb130b38b8059397a73ff890ccb14ef03f8c2a6188b971dce7ead1a; submissions 191180c2… → 4f10743e9203e2fa6e9795f93c33af46d056e3574a58b85e71948a1a206974a3; expected 457508a0… → ad5531da7cff4eca8e9c8e9a23cef6526a982537597e6830610877bec994ff89; files not listed are unchanged. Pins elsewhere in this file are superseded where they differ.

Frozen after `review-precise-4.md` (FREEZE). Pins: manifest 96c6644b8151175f3d422ffd2b4a893cbf9ac9b087c3896373495feb49044047, submissions 191180c2596c38fad13a9b190c6b0fb0103de21ff43b08d175c0f4cf38003a81, expected 457508a0643af8ca6e31bfec6103ae2a0ca9f009dfcc3bf57d29b001e88668b5, builder fab2a0e28a218dbf7ed8c4d09b0eb326c5d9f05575e518ec0919dd1b03d0d766. `methods-cp2a-draft.md` is committed as `docs/methods-drafts/cp2a.md`; the build moves it to `src/deploy_vii/methods/cp2a.md`. The manifest's `status` still names "DRAFT revision 4"; the freeze is this header, not a re-pin. The `execution.py` citation for "Ticket inputs have changed" is :768-769.

Drafted by the `cp2a-owner` preparation task and revised once (pre-code; no product code, no test written or run). Every G1 seam cites `docs/G1X-OWNER-CORE-PROTOCOL.md` (the protocol); this lease designs none of its own. Oracle: `cases/cp2a-owner/{manifest,submissions,expected}.json`, builder `cases/cp2a-owner/builder/build.py`. Implementation starts only after independent review, LEAD freeze and PM integration.

## Why

CP-2A answers "what breaks first and how far it falls" (methodology.json purpose) and heads the distressed pathway CP-2A -> CP-2G -> CP-2H -> CP-4C. It has no core and no step chain (`registry.step_chain("CP-2A")` raises). Edges (checked with `registry`): required CP-0, CP-1 (both `block`); `plan(("CP-2A",))` = `(CP-0, CP-1, CP-2A)`; the alias CP-2B canonicalises to it. CP-2G and CP-4C require CP-2A (`block`); CP-3C lists it optional (`restricted`); CP-6 never reads it (`cp6_committee.py:112`).

Python computes stressed EBITDA, cash interest, free cash flow, leverage, coverage, FCF/debt and the break points. The analyst chooses the base period, the scenarios and the shock sizes, and the watch levels, as literal submission input. No source states them, so they are labelled analyst assumptions (D11, Q1).

No `r14` SKILL.md for CP-2A is in the repo (as for CP-2, decision 0005): the nine T2B tables are composed from the contract rows below. A `methods/cp2a.md` adaptation record is requested (Q2).

## Prerequisites

1. G1 and the S1a extension integrated, then the G1-X change of the protocol (section 2 core attributes, section 3 inputs, section 4 precheck registration). CP-2A is an **owner-only module** (protocol section 1): `registry.step_chain("CP-2A")` raises, so `entry="owner_core"` and the core supplies every item of protocol section 2. No `src/deploy_vii/live/context.py` edit and no `StepSpec` in `live.submission.STEPS`.
2. L2/H1 host work is not needed: CP-2A is submit-only and opens no `SourceSession`.
3. The financial oracle (`cases/financial/manifest.json`, sha256 `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432`) unchanged.

## Files

- New `src/deploy_workflow/owners/cp2a.py` (design below; ~450 lines).
- `src/deploy_workflow/owner_workflow.py` (G1-X, protocol sections 2-3, not this lease's design): `OWNER_SPECS["CP-2A"] = OwnerSpec(module_id="CP-2A", steps=(StepSpec("downside_pathway", ..., inputs="module_context", rules="none"),), entry="owner_core", kind="analytical", publish=None)`; `_CORES = {"CP-2A": cp2a}` (fixed dict); `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS["downside_pathway"]` filled from the core's `QUALIFICATION`, `probe`, `view`. Rule mode `none`: no tool-loop rule and no `precheck` (the module's validator is the step validator, below). No CP-MODEL follows CP-2A in the plan (protocol section 5).
- One-line registrations admitted under D12, recorded in `docs/reuse/manifest.json`, serialised by PM:
  - `src/deploy_vii/methodology.json`: CP-2A `table_ids` -> `T2B.1`..`T2B.9` (D8, below).
  - `src/deploy_vii/bindings/cp2a.py` (new, FP block bindings only, no arithmetic, reads facts by table id, never imports `deploy_workflow`; admitted by protocol section 6, as `bindings/cp4.py`) and `bindings/shipped.py` (`SHIPPED_MAPS += CP2A`).
  - `src/deploy_vii/report_view.py`: a `_DISTRESSED` composition (two `_Spec` rows), the `_spec_of` tuple, and the two block ids inserted in the `distressed_restructuring` entry of `_PRESETS` (after `distress-gate`).
  - `docs/TOOL-CONTRACT.md` permission-matrix row for CP-2A `downside_pathway` (LEAD amends at freeze; Q7).
- `src/deploy_vii/methods/cp2a.md` (documentation, Q2).
- G2 (`owner_rendering.py`): one `DeliveryScope` row `cp2a-fp05-downside` (below).
- New `tests/test_owner_cp2a.py` and `tests/cp2a_runs.py` (run driver `cp2a_closed(case, root) -> (store_dir, receipt_path, None)`; owns pack assembly, literal submissions, run-time substitutions, tool-call sequence; G2 imports it).
- No other `src/deploy_vii` edit. `execution.py`, `contracts.py`, `prose.py` are imported, never edited.

## Public API (`owners/cp2a.py`; keyword arguments only except `store`)

```
MODULE_ID = "CP-2A";  STEP_ID = "downside_pathway";  SCHEMA_VERSION = "downside-pathway/1"
PROMOTED = Qualification(implementation="implemented")

DownsideSubmission(Contract)                      # schema below
Upstream(bound, current, cp1)                     # frozen dataclass, as cp2_synthesis.Upstream
cp2a_upstream(store, attempt) -> Upstream
BaseOperands.from_cp1(cp1_facts, *, period) -> BaseOperands     # fact selection rule below
stress(*, base: BaseOperands, decline: Decimal, increase: Decimal) -> StressedRow
break_points(*, base: BaseOperands, thresholds: Sequence[Threshold]) -> tuple[BreakPoint, ...]
validate_downside(*, pack, submission, upstream) -> tuple[str, ...]
downside_report(*, pack, submission, upstream) -> DownsideReport    # raises ValueError on any issue
context_block(*, pack, upstream) -> dict[str, object]               # the exact read_inputs view
cp2a_module(report, *, inputs, attempt) -> Module
QUALIFICATION = PROMOTED                           # protocol section 2: the head_of qualification
STEP_IDS = ("downside_pathway",)                  # owner-only step sequence
SCHEMAS = {"downside_pathway": DownsideSubmission}
submit(store, ticket_id, step_id, payload, rules) -> Submitted    # journals one step; same Submitted type as submit_model_payload
view(historical, attempt) -> tuple[str, str]      # (sha256, body) of the read_inputs record; registered in _VIEWS
probe(store, snapshot, attempt) -> None           # raises WorkflowError("identity_mismatch") unless the settled attempt and head rebuild exactly
```

`stress` and `break_points` are pure (no I/O, Decimal only, context `Context(prec=38, rounding=ROUND_HALF_EVEN)` from `model/_cells.py`). They do not call `model/metrics.py`, whose `_ratio` needs a `Frame` of columns; CP-2A reuses its semantics (the `_METRICS` recipes, `ZERO_OR_NEGATIVE_DENOMINATOR`, interest as a negated outflow) and re-checks them against CP-1's own reported ratios (T2B.5, the s00 control). `probe` runs the step validator on the frozen execution, rebuilds `cp2a_module` and `settle`s back to the head (as `owners/cp1a.probe`). `submit` is a `submit_cp2_step` analogue returning `Submitted`; the verifier recomputes the validator for every submission (protocol section 4 applies only if a `precheck` is later added).

## Submission schema (reference and judgment only; every field required, no defaults)

```
DownsideSubmission
  base_period: str                     # exactly a `period` string offered by the view
  scenarios: tuple[Scenario, ...]      # 1..4
  thresholds: tuple[Threshold, ...]    # 0..3, at most one per metric
  assessment: Assessment
  gaps: tuple[SynthesisGap, ...]       # 0..n, as cp2_synthesis.SynthesisGap (no cp1a_refs)
Scenario:   name: str, ebitda_decline: str, interest_increase: str, category: Category,
            rationale: str, limitation: str | None
Threshold:  metric: Literal["total_leverage","net_leverage","interest_coverage"], level: str,
            label: str, category: Category, rationale: str
Assessment: rationale: str, category: Category, confidence: Confidence, limitation: str | None
```

`ebitda_decline` and `interest_increase` are decimal-fraction strings (`"0.20"` is 20%), pattern `^(0|1|0\.\d{1,4}|1\.0{1,4})$`; `level` is a positive decimal string with at most four places. No computed number appears anywhere: figures in prose are `{ref|unit}` references to the view's `cp1_facts` only (the `prose` rule of task 6.2). Scenario names, labels and every prose field carry no digit outside a reference (the validator enforces `prose.bare_figures`; names also exclude `{}[]`).

## Decimal composer, rules (zero / missing / blocked kept distinct)

**Base operands** (`BaseOperands.from_cp1`): from the bound CP-1 head, exactly one `T4.10` fact whose `label == f"{column} · {metric}"` where `column` is the base period's column label (`LTM Q4 25 (2025-01-01 to 2025-12-31)` or `Q3 25 (2025-07-01 to 2025-09-30)`; the fact's `period` is the view's `period` string) and `metric` is `ebitda`, `cash_interest`, `fcf`, `total_debt`, `cash_closing`; ratio facts `total_leverage_reported`, `net_leverage_reported`, `interest_coverage_reported`, `fcf_to_debt`. Probe (read-only copy of the S1 positive promoted head, 500 `T4.10` facts): labels are unique; FY25 differs from LTM by label and period; CP-1 stores `cash_interest` negative ("sign normalised"). Interest operand `I = -cash_interest.amount`. Net debt `ND = total_debt - cash_closing`. A fact with `status != "known"` makes the operand missing, never zero; a known 0 is a genuine zero.

**Recipes** (E, I, F, D, C = EBITDA, interest, FCF, debt, cash; s = decline, k = increase; every quotient is one division of exact decimals, so the result equals the correctly rounded rational, evaluation order cannot change it):

| Quantity | Recipe |
|---|---|
| Stressed EBITDA | `E x (1 - s)` |
| Stressed interest | `I x (1 + k)` |
| Stressed FCF | `F - E x s - I x k` (taxes, capex, working capital held; no tax shield) |
| Total / net leverage | `D / E'`, `(D - C) / E'` (calculable iff `E' > 0`) |
| Interest coverage | `E' / I'` (calculable iff `I' > 0`; `E' = 0` gives a genuine 0.00x) |
| FCF to debt | `F' / D` (iff `D > 0`; negative stays a negative figure) |
| Break: FCF at or below zero | `s* = F / E`; EBITDA at break `E - F` |
| Break: coverage at level `c` | `s* = (E - c x I) / E`; at break `c x I` (`c = 1` is the definition "EBITDA no longer covers cash interest") |
| Break: total leverage at `L` | `s* = (L x E - D) / (L x E)`; at break `D / L` |
| Break: net leverage at `L` | `s* = (L x E - ND) / (L x E)`; at break `ND / L`; `ND <= 0` -> "Not reached" (no EBITDA decline raises it) |

Outcome of a break: `s* <= 0` "Already reached at base"; `0 < s* <= 1` "Reached at the stated decline"; `s* > 1` "Not reached by a decline of up to 100%" (status `not_applicable` with limitation, not 0); an input missing -> "Not calculable" (status `missing`, limitation names it). A scenario crosses a break iff its stressed metric is at or beyond the level (`<=` for FCF and coverage, `>=` for leverage); a metric that is not calculable gives "Not calculable", never infinity, never "Not crossed". Ranking (T2B.7): reached breaks ascending by `s*`, ties in register order.

**Gating.** A ratio (leverage, coverage, FCF/debt, ratio-based breaks) is calculable only if CP-1's own fact for that ratio and base period is known; otherwise it is `missing` with the limitation "Not calculable: CP-1 has no twelve-month basis for this period (<CP-1 limitation text>)". This reuses CP-1's twelve-month judgment (`metrics.py`: a quarter reads the LTM ending it; CP-1 marks Q1-Q3 `COMPONENT_MISSING`) instead of annualising. Operand reasons come first in formula order, then the CP-1 gate.

**Facts.** Amounts: unit `MILLIONS`, currency USD, scale 1000000, `decimals=2`; multiples `MULTIPLE`; fractions `PERCENT`. Fact id `<table>.<row>.<field>`; calculated facts carry `calculation_id = "calc:<fact_id>"`, a `formula`, and **lineage**: each lists the CP-1 metrics it derives from (`derives_from` in `expected.json`) and its citations are those CP-1 facts' citations, ordered and de-duplicated in that order (`tuple(dict.fromkeys((*first, *second)))`, the `cp4_legal._computed` pattern); a stressed FCF lists cash interest only when the interest increase is non-zero; a known fact never derives from a CP-1 fact that is not known. Analyst inputs are `value_class="analyst_judgment"` with no lineage. **Level cells:** `T2B.8.<sNN>-<bNN>.level` copies the `T2B.6.<bNN>.level` fact's own `value_class` (`analyst_judgment` for the analyst watch levels, no `calculation_id`). The two methodology-definition constants, `T2B.6.b01.level` (free cash flow of zero) and `T2B.6.b02.level` (EBITDA equal to cash interest, 1.00x), are definitions, not calculations: they carry `value_class` None, no `calculation_id` and no lineage, and keep the definition text as their `formula`; their `T2B.8` copies carry `value_class` None, no `calculation_id`, no lineage, formula `From T2B.6` (probed: `contracts.Fact`, `validate_tables` and `prose.issues` accept them; `report_view` treats only `analyst_judgment` specially, and `cp4_legal` also uses None for non-judged cells). Every `calculated` fact carries lineage. **`cp1_references`** (module table, `cp2_synthesis` mechanism): one row per CP-1 fact the prose names ({{FIG}} references in reading order: scenarios, thresholds, assessment, gaps) and then the four reported ratios T2B.5 compares, each CP-1 fact once, copied verbatim (its own fact_id, value_class, status, limitation); `expected.json` keys the rows by FIG name with unit, shown, cell text and period literal and the fact_id bound at run time. `T2B.5` holds `recomputed`, `difference`, `result`; CP-1's reported ratio is the `cp1_references` row. No stored text spells a CP-1 figure.

**Claims** (Python templates, no analyst figure): one per scenario rationale `T2B.1.sNN` (the analyst's text with `{ref|unit}` references resolved through `cp1_references`; the scenario limitation is the claim's limitation), one per scenario `T2B.4.sNN` ("Under the <name> scenario, stressed EBITDA is {..|US$ m} against {..|US$ m} at base, free cash flow is {..}, net leverage is {..|x} and interest coverage is {..|x}."), `T2B.7.first` when a break is ranked, and the analyst's `T2B.1.assessment`. An unsettled fact is written as a chip `[fact_id]`, a known one as `{fact_id|token}` (`prose._fact_issues`); the claim text in `expected.json` is exact.

**Own limitations** (exact strings in `expected.json`): analyst shock sizes uncited; watch levels not covenants (only when thresholds exist); static stress (debt and cash held, no forward path, CP-2G owns it); taxes/capex/working capital held; liquidity not tested (the liquidity runway is CP-2D's); no covenant test (CP-4); no maturity or refinancing wall (CP-2D, CP-3C); break points hold cash interest at base and the EBITDA-equals-interest break is gated like a ratio; a metric not calculable under a scenario shows Not calculable even where its break lies below that decline (only when such a cell exists); one line per missing base operand; the CP-1 gate line when ratios are gated; `Gap (<severity>): <gap>` per analyst gap; "No break point is calculable..." when nothing ranks. Inherited limitations follow `execution.py:345-366` (bound at run time).

**Confidence.** The assessment's confidence is never `High` (uncited assumptions). Status: restricted (own limitations always non-empty; synthetic case).

## Refusals (validator issues; attempt 0 rejected, re-begun as attempt 1; two failures settle blocked)

Each refusal class has one literal invalid payload and its exact issues in `cases/cp2a-owner/{submissions,expected}.json` `refusals` (ids r01-r14 shape, v01-v17 content). Shape issues are Pydantic messages in `shape_issues` form (`scenarios.0.ebitda_decline: String should match pattern '...'`), returned alone; content issues are `<path>: <issue>` in the order base_period, scenarios, thresholds, assessment, gaps. Classes: unparseable or ill-shaped payload; decline or increase outside [0, 1] / more than four places / not a decimal string; 0 or more than 4 scenarios; unknown or non-decimal watch level, unknown metric; confidence outside the enumeration; base_period not offered; base EBITDA missing or not positive (composer-only: no frozen period has it); duplicate scenario name; more than one threshold per metric; level not positive; digit or brace in a name or label; bare figure, unresolved reference, unit-mismatched reference, unreplaced placeholder, empty prose; `confidence == "High"`; CP-1A's prohibited conclusions (peer ranking, instrument recommendation, recovery conclusion); stale inputs (`Stale input CP-1: bound restricted <12 hex>, current restricted <12 hex>`: validator-only, v17, below). **Validator-only classes (v02, v17; `composer_only` in `submissions.json`).** v02 (base EBITDA missing or not positive) is exercised on the composer with the positive CP-1 facts and EBITDA set to missing. v17 is exercised on `validate_downside(pack=..., submission=<positive payload>, upstream=Upstream(bound=attempt.inputs, current=<the bound tuple with only the CP-1 Input replaced by the literal Input in submissions.json refusals v17 upstream_literal>, cp1=<bound CP-1 facts>))`: `bound` is the attempt's inputs bound at run time (the `prepared-pack`, CP-0 and CP-1 `Input` records, CP-1 status `restricted`); the current CP-1 `Input` has `sha256` = sha256 of `cp2a-owner v17: a different CP-1 head` and status `restricted`, prepared-pack and CP-0 stay equal; the result is exactly `Stale input CP-1: bound restricted <first 12 hex of the attempt's bound CP-1 input sha256>, current restricted 7b28303b61b0`. **Run-level outcome of a superseded CP-1 head** (a run cannot reach the module validator with a stale head, so v17 is validator-only and no run-level refusal id exists for it): through G1, a CP-1 head change after begin refuses `stale_binding` at the next G1 call (`owner_workflow.py:423-427`); a direct `Execution.submit_step` caller gets `ValueError("Ticket inputs have changed")` (`execution.py:768-769`); neither consumes an attempt or journals a step. The module's own `Stale input` check is defence in depth (as `cp2_synthesis._stale_issues`). Not refusals: base operands other than EBITDA missing, gated ratios, a break not reached: these compose honest gaps. **Blocked path:** `expected.json` `blocked`: attempt 0 payload r01 settles rejected, attempt 1 payload v13 settles blocked (head `blocked`, no tables, limitations = attempt 1's issues); CP-2G and CP-4C cannot begin.

G1-level refusals (not this module's): every `invoke` is a `not_permitted` receipt; a submit without the read refuses `not_permitted`; a snapshot change between read and submit refuses `stale_binding` (through G1, a CP-1 head change after begin refuses `stale_binding` at the next G1 call, `owner_workflow.py:423-427`, before the module's validator; a direct `Execution.submit_step` caller gets `ValueError("Ticket inputs have changed")`, `execution.py:768-769`; neither consumes an attempt or journals a step); `requested_modules` naming a module without a spec refuses at `create`.

## Tool use (D2)

CP-2A is a session-less, source-free step. `read_inputs` returns the exact view `context_block` (a D2 exception frozen here, as CP-2's `module_context`; LEAD amends TOOL-CONTRACT). Key tree to freeze (shape only; the implementer observes it on product-settled heads and commits `cases/cp2a-owner/cp2a-view-tree.json`):

```
upstream: [{module_id, status}]                                   # CP-0, CP-1
base_periods: [{period, kind: "quarter"|"fy"|"ltm",
                operands: {ebitda|cash_interest|fcf|total_debt|cash_closing: {ref|null, shown|null, status, limitation|null}},
                ratios:   {total_leverage|net_leverage|interest_coverage|fcf_to_debt: {ref|null, shown|null, status, limitation|null}}}]
cp1_facts: [{ref, label, period, unit, shown}]                    # referencable operands and ratios only
cp1_facts_note: str
scenario_bounds: {decline: {min, max, places}, increase: {min, max, places}}
threshold_metrics: [str]
inherited_limitations: [str]
```

No `quote`, `citations` or `record_json` key at any depth. Acceptance: exactly one ok `read_inputs` before the submit; zero ok pack calls; a refused `read_pages`.

## Consumption proof (D3)

No consumer core exists in the first run. CP-2G (required CP-2A edge) is planned, not leased; CP-4C (required) and CP-3C (optional) come after it; CP-6 never reads CP-2A; CP-5 counts only after a lease extends its integrity scope to CP-2A and its inputs bind CP-2A's head hash (D3). Therefore **consumption stays open until CP-2G lands**. The first run closes at: settled head, verified receipt, assigned rendered section. `docs/MODULES.csv` records `downstream_consumption: open`. When CP-2G is leased it must read CP-2A's settled `T2B.1` scenarios and `T2B.6` breaks (not only its status) and its attempt inputs must bind the CP-2A head hash; the CP-2A head's `result_sha256` equals that bound input.

## Rendered sections (D7)

FP05 (`distressed_restructuring`) has no downside block. New blocks, owner code CP-2A, kind `dense`, producers `("CP-2A",)`, route label "Full analysis":
- `downside-stress`: tab "Earnings and cash flow" <- `T2B.3`; tab "Credit metrics" <- `T2B.4`.
- `break-points`: tab "Break-point register" <- `T2B.6`; tab "First-break ranking" <- `T2B.7`.
- Evidence rail: `T2B.1`, `T2B.2`, `T2B.5`, `T2B.8`, `cp1_references`. Limitations rail: `T2B.9`.

Renderer: G2 `render_owner_slice` via a new `DeliveryScope(scope_id="cp2a-fp05-downside", pathway="distressed_restructuring", requested_modules=("CP-2A",), case_kind="synthetic", sections=("downside-stress","break-points"), rails=("evidence","limitations"))`; the other FP05 blocks keep their idle wording. `contracts.PATHWAY_MODULES["distressed_restructuring"]` is the full pathway; the run requests only `("CP-2A",)` (a run may request fewer, as the financial manifest does with `credit_snapshot`). Cell spelling per `report_view.fact_spelling`: block state `populated`; a missing cell is state `gap` text `∅ G#`, a not_applicable cell (a "Not reached" break) is state `not_meaningful` text `∅ G# n.m.` (number not literal). Expected block content: `expected.json` `cases.<case>.FP05`.

## Table ids (D8)

**Collision confirmed.** `methodology.json` lists `T5.1`-`T5.7` for both CP-2A and CP-5; CP-5 defines them (`methods/cp5.md:59-66`, `cp5_integrity.py`; `bindings/cp5.py` names only T5.9) and CP-6 reads CP-5's `T5.9`. CP-2A has no definition of its own for them. **Resolution:** the CP-2A entry registers `T2B.1`-`T2B.9` only and drops `T5.1`-`T5.7`. No other id of CP-2A collides (checked against every module). The nine tables:

| Id | Content | Python / analyst |
|---|---|---|
| T2B.1 | Scenario register (name, decline, increase, category, basis); the rationale is claim `T2B.1.sNN` | analyst input, Python spelling |
| T2B.2 | Base operands (EBITDA, cash interest outflow, FCF, debt, cash, net debt) with CP-1 source | Python |
| T2B.3 | Stressed EBITDA, interest, FCF and changes per scenario (s00 = base control) | Python |
| T2B.4 | Stressed total/net leverage, coverage, FCF/debt per scenario | Python |
| T2B.5 | Base reconciliation: recomputed ratio, exact difference to the CP-1 reported ratio (a `cp1_references` row), result | Python |
| T2B.6 | Break-point register (origin, test, level, required decline, EBITDA at break, outcome) | Python; levels analyst |
| T2B.7 | First-break ranking | Python |
| T2B.8 | Scenario x break: stressed value, level, Crossed / Not crossed / Not calculable | Python |
| T2B.9 | Gaps ledger (`CP-2A-GAP-NNN`) | analyst |

## Acceptance (expectations only from `cases/cp2a-owner/expected.json`)

- **A1 positive** (pathway `distressed_restructuring`, requested `("CP-2A",)`, pack identity + financial as `make_pack()`, CP-0 consumers CP-1 and the literal `cp0_consumer_row_cp2a`): plan order CP-0, CP-1, CP-2A; all heads restricted; CP-2A tables T2B.1-T2B.9, every fact (id, status, unit, `amount_exact`, `shown`), claims, own limitations, `FP05` blocks equal `expected.json`. Base `ebitda 30, interest 5, fcf 9, debt 50, cash 20`; s00 reproduces CP-1's reported 1.6666666666666666666666666666666666667x / 1.00x / 6.00x / 18.0% exactly (T2B.5 "Reconciled", difference 0). Scenario results: s01 24 / 3 / 2.08x / 1.25x / 4.80x / 6.0%; s02 18 / (3) / 2.78x / 1.67x / 3.60x / (6.0)%; s03 18 / (4) / 2.78x / 1.67x / 3.00x / (8.0)%; s04 0 / (21) / leverage Not calculable / coverage 0.00x / (42.0)%. First break: FCF at or below zero at 30.0%.
- **A2 gap** (same pack and CP-1 construction, base Q3 25): ratios, coverage and the leverage break are Not calculable with CP-1's `COMPONENT_MISSING` text, never 0; flows and the FCF break stay (EBITDA 6 / FCF 0.75; 4.5 / (1.00); FCF break 30.0% at EBITDA 5.25); first break FCF; the gate limitation is present.
- **A2b refused**: financial source missing: CP-0 only (literal rows in `submissions.json` `refused`; T8 commands `DO NOT RUN` for CP-1 and CP-2A; settled `restricted`); exactly one `RefusedBegin` for CP-1 with reason "CP-0 has not authorized this consumer's source readiness"; no CP-2A attempt/head; receipt verifies.
- **A2d blocked**: `expected.json` `blocked` (two invalid submissions, head blocked).
- **A2e CP-1 readiness**: the CP-1 readiness stage submits `cp1_downstream_review` with the markers bound by the frozen predicates of `manifest.json` `run_time_bindings.cp1_readiness` (the one `LTM Q4 25` basis with column_key `LTM:fy-2025`, scope `historical`; its `fcf` and `cash_closing` kpi records; every narrative gap id); the product validator gives no issue and the CP-2A row is `ready_with_limitations`.
- **A2c composer-only** (`interest_undisclosed`): the pure composer on the positive CP-1 facts with base interest missing: coverage Not calculable, FCF Not calculable only where an interest increase is requested.
- **A3 tool-use refusals** (clones): CP-2A `read_pages` refused; submit before read `not_permitted`; stale snapshot `stale_binding`; `{{FIG}}` left unreplaced invalid; each refusal id r01-v17 has a case (v02 and v17 validator-only, as above; the superseded-CP-1-head run-level outcome is the clone of the stale-snapshot case). **A4 tamper:** an edited read body, step output or `SettledHead` makes `verify_owner_run_receipt` refuse `identity_mismatch`. **A5 regression:** `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` pass unchanged.
- Run-time bindings: `{{FIG:name|token}}` -> `{<CP-1 fact_id>|<token>}` by the selection rule in `manifest.json` (unique fact per name; its unit equals the token and `shown` equals `figures.<name>.spelled`; zero or several candidates fail the test); pack hash; inherited limitations; ticket and call ids (structural only).
- Property tests (hypothesis, pre-approved): over random operands, `stress(s=0,k=0)` equals the base ratios; a break `s*` fed back gives exactly the level **in `Fraction` over the Decimal inputs** (the round trip is stated exactly; a 38-digit Decimal `s*` can miss the level by one unit in the last place, so no Decimal equality and no tolerance is asserted); monotonicity in `s`.
- Gates: `ruff check`, `ruff format --check`, `mypy --strict` (`MYPYPATH=src`) on changed files.

## Deferred test commands (build-first; none run)

`PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_owner_cp2a.py` (heavy: a genuine CP-1 promotion, 11-26 min per case; module-scoped fixtures as S1a; one job under the heavy-job lock). Oracle rebuild check: `python3 -I cases/cp2a-owner/builder/build.py` then `cmp` the three files.

## LEAD rulings applied

D8: T2B.1-T2B.9 only. Q1 uncited analyst assumptions allowed (limitation always recorded, confidence never High). Q2 static single-period stress accepted, recorded in `methods/cp2a.md` (draft committed as `docs/methods-drafts/cp2a.md`, five left-out items named; lands in `src/deploy_vii/methods/` with the build). Q3 bounds kept. Q4 new blocks. Q5 the oracle carries the CP-1 readiness literal (validated). Q6 superseded by the G1-X protocol (`entry="owner_core"`). Q7 view as a D2 exception, key tree frozen once a composer produces it. Q8 quarter bases allowed. Q9 "at or beyond" crossed. Q10 composer-only. Q11 no CP-5 extension. Review-precise-1 M1-M7 and L1-L8 per the report's rulings section.

## LEAD rulings on the open questions (2026-10-28)

1. **Shape refusals are journaled invalid steps** that consume an attempt (protocol section 2: `submit` returns what `submit_model_payload` returns, which journals shape issues). No `precheck`. The two-failure blocked case relies on it.
2. **Shape messages.** The venv's locked pydantic 2.14.1 is the reference. The CP-2A build compares the real `SCHEMAS` messages with the oracle's r01-r14; any mismatch comes back to LEAD for a ruling, never a silent oracle edit.
3. **v02 and v17 are validator-only.** v02: the composer on the positive CP-1 facts with base EBITDA missing. v17: `validate_downside` with a literal `Upstream` (bound = the attempt's inputs, current = a different CP-1 `Input`), giving exactly `Stale input CP-1: bound restricted <12 hex>, current restricted <12 hex>`; the run-level outcome is stated under Refusals.

Not verified: no code was written or run in the product; the nine-table layout and block tabs are not validated by a CP-2A composer (only by `Fact`, `validate_tables`, `prose.issues`, `bare_figures`, `fact_spelling` probes on `expected.json`); whether a block may bind four tabs; the view key tree; G1-X behaviour for CP-2A (the protocol is not yet built); the Pydantic refusal messages against the real `Contract`.
