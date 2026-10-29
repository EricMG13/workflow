# CP-4 (legal and covenants) owner run lease - FROZEN by LEAD 2026-10-28 (draft rev 2 by cp4-owner preparation; oracle sha256 pinned below)

Amended by Modules 2026-10-29 (Stage 2 close release fix batch): only pin hashes move, no oracle value changes; its builder re-pins the legal manifest. Own files, old → new sha256: `builder/build.py` 72ad8c26 → 94010ed0; `manifest.json` 6f17b943 → 2c12bf68; `submissions.json` 094425aa → f2ef2e30. `cases/legal/manifest.json` dceee076 → d6a8ec15 (its `readiness.py` inspection pin returns to the imported 1038a37a, was 01616654); `render-expected.json` 95f298a8 → 499289b9; `source-host-expected.json` 1a9db34d → 7d359fd5.

Amended by Modules 2026-10-29 (Stage 2 close release W2-A1; `work/build/stage2/release/w2-brief.md`): `expected.json` `render.other_five_sections` no longer says the five blocks stay owner Unbound: it names liquidity-runway, maturity-wall and funding-gap as CP-2D's and refinancing-paths and lme-creditor-exposure as CP-3C's, as re-pinned in `cases/legal/render-expected.json` `other_front_sections.blocks` (rulings round 4 and round 5 item 18; sha256 ad9b8ca9… → d4eadecf…). No other leaf moves. Own files, old → new sha256: `manifest.json` unchanged; `submissions.json` unchanged; `expected.json` 154fc2d09a4c8a06232a489e5a047e947ee098507969e5e11cdb1ca7f6f4f6a0 → 2b98b81bd529ef5b754dd6977b4624e2dc1359d29385be952a7afe0bd09e4a55; `builder/build.py` e0518720e6179eb1bdf33de7348be0d9f7598433914411d4a10269c2ded7312f → 8ec386bf1943e7a17729a4762e5719a2ee706ab44727a9bb05b585262b062ce3.

Amended by Modules 2026-10-29 (Stage 2 close release W1, merge of `lead/0d-d` 0daac2c onto `lead/cp6-freeze` 562a3bc; `work/build/stage2/release-plan.md`): pin hashes only, re-pinned against the merged tip: `cases/legal/manifest.json` d6a8ec15… → 3da3b746… (readiness.py imported-hash entry, 0d-d). No oracle value moves. Own files, old → new sha256: `manifest.json` 2c12bf6836f54b704201af217866002d279b51cd8f1ed6094154aec9198f6b23 → 6495ca2e5411461c7af14595b0181e0c0a0569e83bde012bd20368de362b5690; `submissions.json` f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461 → ed069b1accead9b55fc844b7a5e84f8a3f91bc87582949f2817ebd2438aaf43c; `expected.json` unchanged; `builder/build.py` 71cf075839362058f6be70140995bfb363a19228151842414200f4d961755446 → e0518720e6179eb1bdf33de7348be0d9f7598433914411d4a10269c2ded7312f.

Pin consumers: `cases/cp4c-owner/builder/build.py` pins `expected.json`, `submissions.json`. Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change. (Stage 1 release batch, LEAD 2026-10-28; none of this module's files changed.)

Amended by LEAD 2026-10-28 (amendment 1, ruling 4-1 in `docs/rulings/2026-10-28-stage1.md`): the T4.9 current and T4F.2 basis description reads `bound from the CP-1 fact (IFRS · consolidated group)`, the engine's copied `predicate_facts.basis_observed` value (builder :801, :816). Only those four `expected.json` strings changed (:827, :2800, :4083, :6089); submissions and manifest are byte-identical; the `entity` string `Northbridge Synthetic Group (IFRS consolidated group)` (builder :1109) is a different field and is unchanged. Three rebuilds (in place and two scratch copies, `python3 -I`) identical. Pins now: expected 154fc2d09a4c8a06232a489e5a047e947ee098507969e5e11cdb1ca7f6f4f6a0, builder 71cf075839362058f6be70140995bfb363a19228151842414200f4d961755446 (submissions f2ef2e30…, manifest 2c12bf68… unchanged); the expected pin a60ab627… at :259 and :290 below is superseded.

Amended by Modules 2026-10-29 (Stage 2 close release W3 chain): only pin hashes move, no oracle value changes; its builder re-pins the legal manifest. Own files, old → new sha256: `builder/build.py` 8ec386bf → 72ad8c26; `manifest.json` 6495ca2e → 6f17b943; `submissions.json` ed069b1a → 094425aa. The legal manifest `cases/legal/manifest.json` pins the new `readiness.py` (119058ff → 01616654): 3da3b746 → dceee076; `render-expected.json` d4eadecf → 95f298a8; `source-host-expected.json` 5868a06c → 1a9db34d.

Rev 1 implemented the LEAD rulings on review-precise-1 (H1, H2, M1, M2, L1-L6, Q1-Q6). Rev 2 implements the LEAD rulings on review-precise-2 (F1-F5). Pre-code. Follows `docs/S1A-OWNER-RUN-LEASE.md` (rev 1 with amendments) and
`docs/OWNER-WORKFLOW-LEASE.md` (D1-D12). The oracle is `cases/cp4-owner/{manifest,submissions,expected}.json`
(built by `python3 -I cases/cp4-owner/builder/build.py`). Nothing here changes `src/deploy_vii`.

## Why

CP-4 is the next one-step shared-live owner after CP-1A and CP-2: a schema
(`CovenantInterpretationSubmission`), `cp4_upstream`/`upstream_of`, `validate_covenant_interpretation`, the Python
composer `covenant_interpretation`, `cp4_module` and `submit_cp4_step` all exist
(`cp4_legal.py:171-1550`), registry chain `CP-4/legal_covenants` with `pack_sources` exists
(`registry.py:362-366`), the 31 tables bind in `bindings/cp4.py` and the six FP04 specs landed in
`report_view._COVENANT_REFINANCING` (commit 7317261). So this lease registers CP-4 as a G1 owner spec; it writes
no new analytical core. Plan order from `registry.plan(("CP-4",))` is `("CP-0","CP-1","CP-4")` (checked: the edges
are CP-4 requires CP-0 and CP-1, the CP-1 to CP-4 edge is `restricted`, `methodology.json`). The run ends at a
verified settled CP-4 head, a verified `OwnerRunReceipt` and the six FP04 sections; no CP-MODEL is in the plan.

## Prerequisites (base)

`codex/checkpoint` with all of these integrated:
- **G1** after its fix rounds, with the S1a amendments that generalise it (`StepSpec.rules` of `none|precheck|
  journaled`, `_owner_historical`, one-step `normalise` fill, walk continuing past a blocked head,
  `_verify_calls_reads` through per-owner views).
- **L2** host: `_SOURCE_STEPS` carries `"CP-4": ("legal_covenants",)` and refuses an empty CP-4 scope
  (`coordinator-1-source-host` `host.py:44-48`, `:658`, `:667`, uncommitted today), plus its CP-1 producer
  authentication (`_cp1_producer_inputs`, `:471`). I read it and did not edit it. This lease adds **no** host line.
- **FP04 typed sections** (`report_view._COVENANT_REFINANCING`, 7317261) - present in this tree.
- **G2** owner rendering, for the FP04 rendered proof only (the receipt-bound `build` over the verified run).

## Files

- `src/deploy_workflow/owner_workflow.py`: one `OwnerSpec` entry (below), `SUPPORTED_ANALYTICAL` += CP-4,
  `_QUALIFICATION` += `cp4_legal.PROMOTED`, `_PROBES` += `owners.cp4.probe`, `_ENTRY_VALIDATORS["CP-4"]` =
  `owners.cp4.ENTRY_VALIDATOR` (= `cp4_legal._validate_step`; the signature matches, no adapter), `_PRECHECKS["CP-4"]` =
  `owners.cp4.precheck`, `_VIEWS["legal_covenants"]` = `owners.cp4.view`, and `StepSpec.inputs` gains the value
  `"step_context"` with its `_inputs` branch and `_check_steps` clause (see Public API; built at `owner_workflow.py:272`, `:820`,
  `:949`). CP-4 is a live-contract module (`docs/G1X-OWNER-CORE-PROTOCOL.md` section 1): G1-X builds the core
  hooks (section 3 read_inputs, section 4 precheck, replay); this lease only registers CP-4 against them. The rule that
  `read_inputs` is required before `submit_review` for every step whose `inputs != "none"`, with or without a source session,
  already exists from G1-X (protocol section 3); this lease adds no G1 change for it.
- New `src/deploy_workflow/owners/cp4.py`: `probe`, `view`, `semantic_issues` (the Q1 gate, LEAD ruling option A) and the core
  `precheck(store, binding, stored)` hook (protocol section 4), which calls `semantic_issues` on the filled payload.
- New `tests/test_owner_cp4.py`; new `tests/cp4_runs.py` exporting `cp4_closed(case, root) -> (store_dir,
  receipt_path, None)` (pack assembly from the frozen manifests, literal submissions, run-time substitutions, tool-call
  sequence; G2 imports it, as for `s1a_runs`).
- D12 registrations: **none needed**. `STEP_CHAINS`, `bindings/shipped.py`, the report compositions and the table
  ids all exist (see D8 below). No `docs/reuse/manifest.json` row beyond the new files.
- No `src/deploy_vii` edit, no host edit, no case-pack byte changed.

## Public API additions (the seams are positional, protocol section 2; `semantic_issues` is keyword-only)

```
StepSpec.inputs: Literal["none", "projection", "module_context", "step_context"]
    # "step_context": the live.context CONTEXT block of the step, live/context.py:98-99
OWNER_SPECS += "CP-4": OwnerSpec(
    module_id="CP-4",
    steps=(StepSpec(step_id="legal_covenants", schema=CovenantInterpretationSubmission,
                    sources=True, extract=False, upstream_grant=None,
                    inputs="step_context", rules="journaled"),),
    entry="model_payload", kind="analytical", publish=None)
owners.cp4.probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None   # owners/cp4.py:132
owners.cp4.view(historical: Execution, attempt: Attempt) -> tuple[str, str]       # (sha256, body); owners/cp4.py:119
owners.cp4.semantic_issues(*, pack, submission) -> tuple[str, ...]                 # the Q1 gate; see Semantic gate
owners.cp4.precheck(store, binding, stored) -> tuple[str, ...]                     # core hook (protocol section 4); calls semantic_issues
```
`view` body is `json.dumps(cp4_legal.context_block(historical.pack(), cp4_legal.upstream_of(historical, attempt)),
ensure_ascii=False, separators=(",", ":"), allow_nan=False)`, digest its sha256 (as `live/context.py:111`). The
receipt schema, JSON-lines operations and return shapes do not change.

## Submission schema (reference and judgment only)

`CovenantInterpretationSubmission` (`cp4_legal.py:171`), unchanged: `documents`, `covenants`, `capacity`, `red_flags`,
`protection_score`, `gaps`. The analyst writes: the document row (family, governing entity, date, one cited quote),
the covenant row (name, kind, clause, definition text, test formula, `threshold_text` copied from a quote,
`threshold_unit`, `threshold_value` as the quote writes it, `comparison`, `metric_ref`, `metric_basis`,
`facility_ids`, `period_scope`, quotes), baskets, red flags, one protection rating and gaps. It writes no hash, no
id Python assigns, no amount, no verdict. Figures appear only as `{ref|unit}`; the literal cases use none in prose.
Literal inputs: `cases/cp4-owner/submissions.json` keys `positive`, `gap`, `gap_false_same_definition`
(`legal_covenants`), with CP-0 `readiness_review` and CP-1 `cp1_source_context` per pack. One run-time placeholder in
`legal_covenants`: `covenants[0].metric_ref = "<<FIG:net_leverage_reported>>"` (see tool use).

## Composer and zero/missing/blocked rules (Python owns arithmetic)

No new composer: `cp4_legal.covenant_interpretation` is it. Rules the tests pin from `expected.json` (never from
the code under test):
- `threshold = 4.00` parsed from the quote `4.00x`; `headroom = threshold - metric = 4.00 - 1 = 3` (unit MULTIPLE,
  period and basis of the CP-1 fact); `share = 3 / |4.00| = 0.75` (PERCENT, a fraction; displayed `75.0%`);
  `within = headroom > 0 or (headroom == 0 and comparison == "<=")` (`cp4_legal.py:338-340`; here 3 > 0); verdict `Within threshold on the CP-1 metric`. The metric `1` is the CP-1 T4.10
  `net_leverage_reported` LTM fact = `(50 - 20) / 30` (frozen `q4_ltm_metric_oracle`). String exponents follow the
  CP-1 amount (`3.00`), so compare as `Decimal == 3`.
- Missing definition (`Not determinable`): headroom and share are **missing** (status missing, reason `Not calculable:
  Whether the covenant definition is the CP-1 metric's is not determinable`), verdict `Not calculable`, T4C.9
  calculable `No`; the comparator `1.00x` stays visible; never 0, never the 3 or the 75%.
- Basket capacity: always **missing** with `Basket capacity amounts are not calculated: CP-4 quotes and interprets
  baskets in M8; unknown capacity is not zero`; never 0.
- Source context only, never a cell: arithmetic distance `4 * 30 - (50 - 20) = 90` (USD millions of net debt), its
  parent `4 * 30 = 120`, and unused commitment `50 - 50 = 0`. The 90 is not legal debt permission, capacity or funding;
  the 0 is not the unknown capacity; unanimous lender consent governs additional debt (Clause 4.1). The test asserts
  that no numeric fact has an amount Decimal-equal to 90, 120 or 0 and that no cell text equals `"90"`, `"120"` or
  `"0"` after stripping; it is not a substring test (`expected.json`
  `source_context_only.must_not_appear_as_cell_values`: values, derivations, comparison).
- A blocked CP-1 yields every headroom `not calculable` (existing core; not an oracle case here, question 4).

## Refusals

- `requested_modules` outside the specs, CP-5 or any spec-less module: refuse at `create`, write nothing (G1).
- `create` with CP-5 selected: refused by `_check_specs` (no CP-5 spec). A CP-5 consumer assessment in the CP-0
  review would also be invalid: `validate_review` requires exactly the selected live consumers.
- CP-4 `invoke`: `search_pack` and `read_pages` over `legal-covenants` only; `extract_statements` refused;
  any `source_id` other than `legal-covenants` `not_permitted`; `read_inputs` returns the `view` body.
- CP-4 submit without a prior ok `read_inputs` at the same binding: `not_permitted` (the participant has no other way
  to learn `metric_ref`; see Tool use). Stale snapshot between read and submit: `stale_binding`.
- A submit failing a journaled rule (unread cited page, unbacked absence marker) is journaled invalid; attempt 0 is
  re-begun as attempt 1 with `repair_of`; if attempt 1 also fails, CP-4 settles blocked and the receipt still verifies.
- Unresolved `<<FIG:...>>` or any `metric_ref` not in `cp1_facts`: invalid (the core's `not a CP-1 figure offered`).
- Zero or several candidates for the LTM predicate: the run driver fails the test; it never chooses among the equal
  `Q4 25`, `FY25` and `LTM Q4 25` aliases.
- False `Same definition` on the missing-definition pack: refused by the Semantic gate below, before the journal
  (the engine alone composes headroom 3.00, share 0.75, `Within threshold`, T4C.9 `Yes` for it: probe).

## Semantic gate (Q1 = A, LEAD ruling; `owners.cp4.semantic_issues`)

Deterministic, no parser. It runs as the CP-4 core `precheck(store, binding, stored)` hook (protocol section 4) on the filled payload, before `rules` of any mode and before the journal. The step keeps the single literal `rules="journaled"` (S1a M3); the gate runs first, then the journaled rules. It depends only on the submission and the pack.
- Markers (closed list, frozen from the gap legal source, `cases/legal` missing-ebitda-definition page:2 Clause 2.3,
  and absent from every positive legal page, identity page and financial page - asserted by the builder):
  `"has the meaning assigned in"`, `"is not supplied with this copy"`. Never `"defined in"` (the positive legal page:2
  reads "Group perimeter defined in Clause 1.2"), `"as defined in"` or the bare word `"incorporated"`.
- Match: whitespace runs collapsed to one space, case-folded substring.
- Scope: the covenant row's cited quote texts plus the full text of every pack page that row cites. Not the pages a
  participant read.
- Rule: for each covenant with `metric_basis == "Same definition"`, any marker matching in scope refuses the payload.
  One issue per refused covenant, markers in list order (format of `{markers}`: matched markers in list order, each in single quotes, joined by '; '), exactly
  `covenants[{i}]: metric_basis 'Same definition' is refused because the cited source text matches
  incorporation-by-reference markers: 'has the meaning assigned in'; 'is not supplied with this copy'` (as one line).
- Verifier replay: `_verify_submissions` recomputes the gate for every CP-4 submission: a refused record must reproduce exactly its
  issues; a valid step must yield none (otherwise `identity_mismatch`).
- Review: `mx-adversary` reviews the gate and the list at build. Per-case outcomes in `expected.json` `semantic_gate`:
  positive passes (no marker in scope), gap is not gated (`Not determinable`), false-same is refused.

## Tool use (D2, `docs/TOOL-CONTRACT.md`)

- `SourceSession.from_execution(store, ticket_id, "legal_covenants")` over the single scope `legal-covenants`
  (CP-0 T3 authority `executed`, `readable_sources`/`declared_sources` through `cp4_legal.upstream_of(...).legal_sources`).
- Before submit, per attempt: one ok `read_pages` of `legal-covenants` pages 1 to 3 (`first_page 1`, `last_page 3`),
  covering every cited `page:1`, `page:2`, `page:3` (rule `unread-citations`); at least one `search_pack` over
  `legal-covenants`: positive `Covenant EBITDA`, gap and false-same `Schedule A`. The rule floor is lower (an
  absence search is required only for a row carrying an `ABSENCE_MARKERS` value such as `threshold_unit` `not stated`,
  which no case does); the search is an oracle expectation for complete participation (`LEGAL-SOURCE-CONTRACT`).
- Exactly one ok `read_inputs` per attempt: the **exact view** `cp4_legal.context_block` (key tree frozen in
  `expected.json` `cp4_step_view`; no `quote`, `citations` or `record_json` key, no legal quote text). It counts as
  tool use only as a D2 exception: LEAD amends `docs/TOOL-CONTRACT.md` (matrix row "CP-4 legal_covenants" plus the
  raw-legal row: `legal-covenants` search/read, view `context_block`, no identity/financial raw, no extract) when this
  lease freezes. Without it CP-4's `metric_ref` cannot be obtained by a real participant.
- Upstream CP-0/CP-1 literal inputs: CP-0 reads `identity`/`financial` page:1 and `legal-covenants` page:1 (page:2 in
  the gap case); CP-1 `source_context` reads `identity` page:1, `financial` page:1 and `legal-covenants` page:1 (every page its
  literal cites). Later CP-1 stages are the financial case's.
- `FIG` binding (S1a rev 2 M2 predicate): select from `head_module(CP-1).facts` the facts with `table_id` `T4.10`, period
  `"LTM Q4 25: 2025-01-01 to 2025-12-31"` and label `"LTM Q4 25 (2025-01-01 to 2025-12-31) · net_leverage_reported"`;
  exactly one must match (zero or several fail the driver; the equal `Q4 25` and `FY25` aliases are never chosen). Then its
  `fact_id` must be a `ref` in the `read_inputs` `cp1_facts` whose `unit` is `x` and `shown` is `1.00x`; that id is
  substituted for `<<FIG:net_leverage_reported>>`. Not a selection from the read_inputs body by row/period/unit.

## Consumption proof (D3)

- **CP-4 reads** (proved by `attempt.inputs` and the settled tables): inputs `prepared-pack`, `CP-0`, `CP-1`
  carrying the heads' `result_sha256` at begin; the settled module adds `covenant-interpretation-submission`. CP-0 T3
  authority -> `legal_sources` = `["legal-covenants"]`; CP-1 T4.10/T4.17 referencable facts, T4.18 facility `term-loan`
  / `Northbridge Term Loan` and CP-1 limitations. The proof in the output: T4C.8, T4F.2, T4F.3 (metric operand) and the
  headroom formula carry the CP-1 fact's own id; T4.9 `Current` carries its label, period, basis, `calculation_id` and
  citations, not the id; T4F.1 carries the CP-1 head hash; T4C.11/T4C.12 name the facility; T4F.5 lists the CP-1 limitations.
- **Verifier probe** (`owners.cp4.probe`): reruns `cp4_legal._validate_step(store, pack, attempt)` (reads both bound
  heads, `upstream_of`), checks its output bytes equal the retained output, rebuilds the candidate with
  `cp4_module(report, attempt.inputs, attempt.number)` and gets the head back through `settle`.
- **Consumers of CP-4 in this run: none.** Registry edges name CP-3, CP-3C, CP-4C and CP-5; none is in
  `plan(("CP-4",))`. CP-3 reads CP-4 status and limitations only (`cp3_relative_value.py:99-104`) and needs CP-2 and
  market sources; CP-5 reviews CP-4 only after a lease extends its integrity scope to CP-4 and A4 integrates (D3).
  So CP-4's own downstream consumption **stays open** in this run (a recorded limitation, like CP-2 in S1a); the run
  proves upstream consumption by CP-4, a verified receipt and the rendered sections.

## Rendered sections (D7)

Via the verified receipt and `Execution.view` -> `report_view.build(view, pathway "covenant_refinancing", SHIPPED_MAPS)`
(G2). Run `pathway` is `covenant_refinancing`. Six FP04 sections, all owner `CP-4`, kind `dense`, route `Full analysis`,
from `report_view._COVENANT_REFINANCING` and `bindings/cp4.py` (existing; no new block, D7 keeps owners):

| Section (block id) | Table(s) |
|---|---|
| covenant-tests-headroom | T4.9 |
| capacity | T4.10 |
| red-flags | T4.11 |
| lender-protection-score | T4.13 |
| ebitda-definition | T4C.6 |
| documents-structure | T4.2 (Document register), T4C.12 (Facility coverage) |

Evidence rail (19 tables): T4.3, T4C.2, T4C.3, T4C.4, T4C.5, T4C.7, T4C.8, T4C.11, T4D.1, T4D.2, T4D.3, T4D.4, T4D.6,
T4D.7, T4D.8, T4F.2, T4F.3, T4F.4, T4F.6. Limitations rail (5): T4.12, T4C.9, T4D.5, T4F.1, T4F.5, plus
`Module.limitations`. The other five FP04 sections (liquidity-runway, maturity-wall, funding-gap, refinancing-paths,
lme-creditor-exposure) stay `Unbound`/`No module produces this block yet.` and are not claimed. Displayed literals
(`expected.json` `render.displayed_literals`): positive `4.00x`, `Not more than`, `1.00x`, `3.00x`, `75.0%`,
`Within threshold on the CP-1 metric`, capacity as a gap (`G#`, never 0), rating `Insufficient Information`;
gap `Not calculable`, headroom and share as gaps, T4C.6 naming the missing Schedule A.

## Table ids (D8 collision check)

No new ids, so no `methodology.json` registration. Checked against `methodology.json`: CP-4 declares 31 ids; seven
(T4.2, T4.3, T4.9, T4.10, T4.11 with CP-1 and CP-1C; T4.12, T4.13 with CP-1) overlap existing modules - the overlap
D8 says stays; coordinates and bindings are module-qualified (`FactCoord.module_id`). The other 24 (T4C.*, T4D.*, T4F.*)
collide with nothing.

## Acceptance (expectations only from `cases/cp4-owner/expected.json`)

**A1 positive** (`positive`) and **A2 gap** (`gap`): one closed run per pack.
- Statuses: CP-0 restricted, CP-1 restricted, CP-4 restricted (`execution.statuses`); CP-0 T3 authority and T8
  commands (`Run CP-1`, `Run CP-4`) and limitations equal `positive|gap.CP-0`.
- CP-4: all 31 tables in `table_order`, each with title, row header, columns, rows, and per fact the text, status,
  `[source_id, locator]` cites, value class, limitation; numeric cells by `Decimal` equality with unit; claims
  (`red_flags.r01`, `red_flags.r02`, `protection_score`); own and settled limitations; `python_values`;
  `source_context_only`. Values marked `bound` or `<<...>>` bind from the CP-1 head and are asserted by the
  predicate, not by literal.
- Inherited limitations: CP-0 head, then CP-1 head (limitations, then inherited), de-duplicated, own removed.
- Receipt verifies; the store is unchanged by verification.
**A3 semantic refusal** (`gap_false_same_definition`): the payload is refused before the journal with the frozen issue
string of `expected.json` `gap_false_same_definition.CP-4.refusal.issues`: the refused payload is not journaled and consumes no
attempt; the CP-4 ticket still has no step and the snapshot is unchanged. G1 records it in the owner-run audit
(payloads/<raw sha>, payloads/<filled sha>, bindings/<binding hash>, submissions/<record hash>) and in `receipt.submissions` as an
`OwnerSubmission` with disposition `refused`, issues equal to the frozen issue string, `step_sha256` and `step_output_sha256`
null, and `snapshot_after_sha256` equal to the binding snapshot; `_verify_submissions` replays it. A corrected `Not determinable`
resubmission on the same ticket then settles with exactly the tables, limitations and claims of `gap.CP-4`; `receipt.submissions`
holds two CP-4 records on the same ticket and binding: the refused one, then the valid one, whose `call_ids` include every call of
the epoch made before and after the refusal; the receipt verifies with one CP-4 step. The
values under `semantic_acceptance` (headroom 3, share 0.75, within, calculable Yes) are asserted never to settle; they are
not expected product output and no table of the refused payload is expected.
**A3b gate tests** (`semantic_gate`): positive pack settles (no false positive); gap pack settles (gate does not apply);
`_verify_submissions` recomputes the gate for every CP-4 submission (refused records reproduce exactly their issues, valid steps
yield none); tamper: build the tampered run end-to-end with the gate off (patch `owners.cp4.semantic_issues` to return `()`;
specs cannot be injected, `_check_specs` requires `OWNER_SPECS`), restore the gate, then `verify_owner_run_receipt` must refuse
`identity_mismatch` at the gate replay, store unchanged.
**A4 tool-use refusals** (clones of the positive run): unread `page:1` -> invalid with an issue naming
`legal-covenants page:1`, re-begun as attempt 1 (`repair_of` set), valid attempt 1 still yields a verifying receipt;
read of `identity` or `financial` via the CP-4 session `not_permitted`; `extract_statements` refused; submit without a
`read_inputs` `not_permitted`; stale snapshot `stale_binding`; unresolved `<<FIG>>` invalid; two LTM candidates fail the
driver.
**A5 tamper**: edited `read_inputs` body in the audit, edited CP-4 step output, edited CP-4 `SettledHead` each make
`verify_owner_run_receipt` refuse `identity_mismatch`.
**A6 regression**: `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` pass unchanged.
**A7 render**: the six sections and two rails above for both packs, from the verified run only.
**Gates**: `ruff check`, `ruff format --check`, `mypy --strict` (`MYPYPATH=src`) on the changed files.

## Deferred test commands (build-first rule: none run until LEAD's final phase)

Heavy; one job at a time under the heavy-job lock. Python `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"`:
```
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -o faulthandler_timeout=1800 -m pytest -q -p no:cacheprovider tests/test_owner_cp4.py
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PY -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py tests/test_owner_s1a.py
python3 -I cases/cp4-owner/builder/build.py \
 && shasum -a 256 cases/cp4-owner/manifest.json cases/cp4-owner/submissions.json cases/cp4-owner/expected.json   # light; compare with the pinned values below
```
Pinned sha256 (the oracle gate fails when any differs; a `git diff` gate cannot fail while the files are untracked):
`manifest.json` 2c12bf6836f54b704201af217866002d279b51cd8f1ed6094154aec9198f6b23, `submissions.json`
f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461, `expected.json`
a60ab627d353eeb8871024e0efe664cce38322fcfa3edaf7ccda9f257fdc1423.
Cost: two genuine CP-1 promotions (positive pack, gap pack; 11-26 minutes each, QUEUE 2026-10-27); the false-same case
clones the gap CP-1 head. Module-scoped fixtures `cp4_promoted[pack]` and `cp4_closed[case]` as for S1a. Per CP-4 tool
call the L2 host re-authenticates CP-0 and CP-1 (L2 memoises CP-1 per snapshot).

## LEAD rulings applied (2026-10-28; former open questions)

1. **False `Same definition`**: option A, the Semantic gate above; refusal expectation in the oracle.
2. **`requested_modules`** `["CP-4"]`; CP-5 review of CP-4 is a later lease after A4 and S1b (closes D3 for CP-4).
3. **CP-4 exact view**: `cp4_legal.context_block` is the D2 exception that counts as tool use; `StepSpec.inputs` gains
   `step_context`; one ok `read_inputs` before submit; LEAD amends `TOOL-CONTRACT.md` at freeze.
4. **Blocked CP-1 walk**: deferred and recorded as a limitation (no oracle).
5. **CP-1 predicate**: the S1a rev 2 M2 predicate above; confirmed by review-precise-1 on a promoted head, not yet on the
   legal packs' own CP-1 heads.
6. **Evidence class** `lender_sponsor` for the legal source in CP-1 `source_context`: accepted as literal analyst input. It is
   a quality tier (EvidenceClass tier 2c), not legal authority; authority is CP-0 T3 `executed` and no CP-4 output reads
   the class.
7. **Probes location**: `owners/cp4.py` (D12), as S1a Q7.

Rev 2 rulings (review-precise-2): the issue string is frozen as in `expected.json`; the refused payload is recorded by G1 as stated in A3
(former question (b) closed); the gate is the CP-4 core `precheck` hook, `rules` stays `journaled`.

Not verified: no pytest ran; no genuine CP-1 promotion over either legal pack, so CP-1 later stages (QA coverage,
score 59) over the three-source legal pack, the `FIG` predicate against that pack's own CP-1 head, L2's CP-4 admission
and authentication, the G1 integration, `owners/cp4.py`, the gate (checked only by builder substring search over the frozen sources) and the rendered FP04 sections were not exercised.

## LEAD freeze (2026-10-28)
Frozen after review-precise-1, revision 2, review-precise-2 and revision 3
(`work/lead/cp4-owner-preparation/`). LEAD rebuilt the oracle in scratch with `python3 -I` and
`cmp` matched all three files: manifest 2c12bf6836f54b704201af217866002d279b51cd8f1ed6094154aec9198f6b23,
submissions f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461, expected
a60ab627d353eeb8871024e0efe664cce38322fcfa3edaf7ccda9f257fdc1423. G1 seams follow
`docs/G1X-OWNER-CORE-PROTOCOL.md`. Build after S1a, G1-X and H1 integrate.
