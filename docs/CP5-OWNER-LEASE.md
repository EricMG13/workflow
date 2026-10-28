# CP-5 (integrity review) owner run lease — FROZEN by LEAD 2026-10-28 (preparation revision 2)

Frozen after these reviews:
- `work/lead/cp5-owner-preparation/review-precise-1.md`: CHANGES REQUIRED, with F1 and F2 Medium and L1 to L3 Low, all fixed in revision 2.
- `review-precise-2.md`: PASS on F1 and F2. Its Lows L-a and L-b were applied in the freeze batch (`revision-2.md`) and checked against `scratchpad/cp5-review1/r2_checks.py` (rc 0) with no review round.

LEAD rebuilt cp3-cp6, cp5 and cp8 with `python3 -I`, and every output was byte-identical to these pins:
- manifest `605a5baed84ff9e1fb5731f56de798af5812b4e6796622735339af64441acd91`
- submissions `9effec68a97a450ae87ee7d203b36e80ee9b315e052dce9db66b2d17c6a2b8a4`
- expected `48fcd8991b858b9b08fc12e965abfcde42d467dfce2aba04a98e9edba07e92d2`
- builder `60805bcf42e26b09598a36571fbee2ff8015f067b22bca559bacc665a02394d2`
- the cp3-cp6 manifest `525c5f1b5ab0c8518b936b099621422d5fcf0424114c0a20b836964c66dd8e10`, amended in R6 only (`docs/CP3-OWNER-LEASE.md` header)
- `methodology.json` `1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6`

The `docs/TOOL-CONTRACT.md` row for CP-5 `integrity_review` now reads `TOOL_CONTRACT_ROW.amended_to`.

CP-5 runs only inside the CP-6 run (R6), and that run has no CP-MODEL. CP-5's consumption of CP-MODEL (DC-5) stays open on the CP-MODEL row, under G1-X §5. MODULES.csv moves the CP-5 row only after the R6 run.

Not verified: no pytest and no end-to-end R6 run. The view body was never built on a CP-3 head. The F2 refs were checked on the S1 positive heads.

Former draft heading follows.

# CP-5 (integrity review) owner run lease - DRAFT revision 2, not frozen

Pre-code, not frozen. Registers CP-5 as a G1 owner spec on top of the CP-3/CP-6 credit-snapshot run and unblocks the CP-6 half of
`docs/CP3-OWNER-LEASE.md`. Oracle: `cases/cp5-owner/{manifest,submissions,expected}.json`, builder
`cases/cp5-owner/builder/build.py` (stdlib; `python3 -I` reproduces all three byte for byte; the only option is `--out <dir outside the repo>`).

## Revision 2 pins (full sha256)

| File | sha256 |
|---|---|
| `cases/cp5-owner/manifest.json` | `605a5baed84ff9e1fb5731f56de798af5812b4e6796622735339af64441acd91` |
| `cases/cp5-owner/submissions.json` | `9effec68a97a450ae87ee7d203b36e80ee9b315e052dce9db66b2d17c6a2b8a4` |
| `cases/cp5-owner/expected.json` | `48fcd8991b858b9b08fc12e965abfcde42d467dfce2aba04a98e9edba07e92d2` |
| `cases/cp3-cp6-owner/manifest.json` (amended R6; pinned by the builder) | `525c5f1b5ab0c8518b936b099621422d5fcf0424114c0a20b836964c66dd8e10` |
| `cases/cp3-cp6-owner/submissions.json` (amended R6) | `eaecbcd012c3d157d96362c288b842e7c25157aabffff831e68dcd23bffe6b0b` |
| `cases/cp3-cp6-owner/expected.json` (amended R6) | `8ca60c96ac443282ac49a0ded495b751cf3b5457b9491f419a26ca59c0b3c310` |
| `src/deploy_vii/methodology.json` | `1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6` |
| S1 manifest, submissions, expected | as the builder `PINS` (`68d591f6…`, `bff9ed18…`, `d1aa1af9…`) |

The cp3-cp6 amendment changes R6 only; every R3 path is byte-identical to `HEAD` (key-path diff in `revision-1.md`: 198 changed paths, all under `R6`).
Seams cite `docs/G1X-OWNER-CORE-PROTOCOL.md`; this lease adds none.

## Fixes (revision 2, review-precise-1 fix round 1)

- **F1** The quote-free assertion and the TOOL-CONTRACT row are narrowed to two conditions: no `quote` key at any depth, and no citation quote string anywhere in the body except inside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`), which are CP-3's settled market-evidence facts, not citations (`P` keeps every CP-3 fact and the positive literal names `T3.3.m01.quote`). On the positive CP-3 head those two facts equal the citation quotes of T3.1.i01 and T3.4.preference.
- **F2** Support refs and rationales (both cases): CP-2 `T2.10.kf04` adds `T2.1.assessment.limitation`; CP-1A `credit_translation.r05` adds `credit_translation.r05#c2` and `credit_translation.r03#c1`; CP-2 `T2.1.assessment` adds `T2.1.assessment.basis` and `T2.10.kf02.basis`. Marks unchanged (all `supported`).
- **L1** RT-3 also asserts each CP-1 claim's `#c1` (source_id, locator) as observed on S1: leverage financial page:4, coverage financial page:2, cash_flow_quality financial page:3, liquidity financial page:4, data_quality financial page:1, definition_risks financial page:5, key_gaps identity page:1.
- **L2** `_CORES["CP-5"]` is not registered (CP-5 is live-contract; `_CORES` is the `owner_core` dispatch).
- **L3** `runs.R6.note` of the cp3-cp6 manifest states that the shared `upstream.statuses.CP-MODEL`, `execution.statuses` and `execution.consumption.CP-MODEL` hold for R3 only; the shared paths are not edited. The cp3-cp6 manifest is re-pinned above; submissions and expected are unchanged.

## Rulings applied (LEAD, 2026-10-28)

1. **CP-MODEL: option (a).** R6 of `cases/cp3-cp6-owner` no longer requests CP-MODEL (`requested_modules`, `plan_order`, `cp1a_consumers`, the CP-0 `plan_order`, the R6 CP-1A consumer rows). `registry.plan` gives CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6. The cp5 builder asserts its run equals that R6. CP-5's consumption of CP-MODEL (DC-5) is not proved here; it stays open on the CP-MODEL row (G1-X section 5). No `--with-model` variant remains.
2. **Owner view accepted**, with the `view(historical, attempt) -> (sha256, body)` binding below and a measured size.
3. **TOOL-CONTRACT accepted**: the CP-5 row takes the owner view; `python_findings` carry the kind label plus where, no quote fragment.
4. **Run sharing accepted**: CP-5 runs only inside R6; no R5 run, no extra promotion.
5. **Mechanical findings** are run-time assertions RT-1 (the seven CP-1 narrative ids) and RT-2 (zero Python findings); analyst finding categories are not built.
6. **CP-1 citations**: run-time assertion RT-3 (each of the seven carries at least one citation).
7. **Semantic review**: review-precise-1 checks the 37 support judgments (19 positive, 18 gap) against the cited facts.
8. **MODULES.csv**: the CP-5 row moves only after the R6 run; the earnings pathway stays separate.
9. **CP-3 Q2 noted.**

## Why

CP-6 requires CP-5 (`registry.edge_rule("CP-6","CP-5") == "block"`; `plan(("CP-6",))` = CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6), and G1 `create` refuses a
plan with a module that has no spec. CP-5 already has a core (`cp5_integrity.py`: `review_scope`, `python_checks`, `validate_integrity`, `integrity_review`,
`cp5_module`, `_validate_step`, `submit_cp5_step`) and is a **live-contract module**: `registry.step_chain("CP-5")` succeeds (`registry.py:373`,
`StepChain(module_id="CP-5", cell="cp5", steps=("integrity_review",))`, `shared_live=True`, submit-only, no pack source), dispatched by
`submit_model_payload` (`live/submission.py:270`). The shipped binding map `bindings/cp5.py` and the 17 methodology `table_ids` already exist. So this lease adds one `OwnerSpec`, one
core file (probe, view, entry validator) and the oracle. No new arithmetic exists: CP-5 computes nothing, it checks (Python) and judges (analyst).

What the core really reads (checked in code, asserted in the oracle):

| Reads | For |
|---|---|
| every bound head of CP-1, CP-1A, CP-2, CP-3: all facts, claims, citations | citation existence and quote match, claim figure resolution, cross-module figure identity, scale/unit, unsettled-fact rule (`python_checks`) |
| CP-0 | bound as the source-readiness gate; not evaluated (`NOT_EVALUATED`) |
| the prepared pack | the citation checks only (`pack.sources`); CP-5 quotes no source and has no SOURCE block |
| `inherited_limitations` over the bound heads | T5.8 and T5B.7 inherited rows |

## What the existing CP-5 work gives this lease (reuse)

| Existing | Reused by the owner core | Not reused |
|---|---|---|
| `cp5_integrity.py` (core, `PROMOTED`, `submit_cp5_step`, `_validate_step`) | yes, unchanged: composer, validator, candidate, settlement | - |
| `live.context.integrity_projection`, `cp5_integrity.context_block` | yes: the owner view is `context_block` with the facts projection and no citation quote (ruling 2, section Owner view) | the live CONTEXT as it is (carries `citations[*].quote`, forbidden for an upstream-only step by TOOL-CONTRACT) |
| `bindings/cp5.py`, 17 `table_ids` in `methodology.json` | yes: rendering (Evidence and Limitations rails) and D8 | - |
| `docs/CP5-INTEGRITY-LEASE.md` (Task4-A4): `integrity_workflow.py`, `IntegritySliceReceipt`, `EarningsSliceReceipt`, CP5-v2 grant, `read_integrity_scope`/`verify_integrity_scope`, owner-receipt chain | **no.** That is the earnings pathway (CP-1B then CP-5, `publication_files={}`), its own offline host and receipts; `integrity_workflow.py` does not exist in the tree | the whole of it. G1 cannot verify upstream-grant calls (`owner_workflow.py` `create` refuses a spec with `upstream_grant`), so this lease uses `inputs="module_context"` and the A4 transport stays a separate lane. The two pathways settle the same core head from the same `submit_cp5_step` |
| `src/deploy_workflow/tools/upstream.py` (`UpstreamTools`, CP5-v1 and CP5-v2) and `tests/test_upstream_tools.py` | no tool call: `StepSpec.upstream_grant=None`. Its safe-field idea (no quote, no record_json) is the rule of the view | the tools; `cases/upstream/manifest.json`, `cases/integrity/expected.json` are not read by this oracle |
| `docs/CP5-FIXTURE-REFERENCE-ADDENDUM.md` | no (CP1B fixture references) | - |
| `docs/MODULES.csv` CP-5 row ("component only: scoped upstream adapter verified; owner execution unverified") | the row stays as it is until the R6 run verifies; LEAD updates it then | - |

## Prerequisites (base)

`codex/checkpoint` with all of:
1. G1 (after fix round 1), L2, S1a (run verified) and **G1-X** (`docs/G1X-OWNER-CORE-PROTOCOL.md`: `_ENTRY_VALIDATORS`, generic `_VIEWS`).
2. The amended cp3-cp6 R6 (ruling 1; Modules re-pins its CP-3 oracle-pin tests, LEAD amends the CP-3 lease header). The run does not request CP-MODEL, so G1-X needs no change for it.
3. A TOOL-CONTRACT amendment of the CP-5 row to the owner view (ruling 3), and the independent `mx-precise` review of this oracle, including the semantic review of the 37 judgments (ruling 7).
4. Full H1 is not needed: CP-5 opens no `SourceSession`.

## Files

- New `src/deploy_workflow/owners/cp5.py` (`QUALIFICATION`, `probe`, `view`, `ENTRY_VALIDATOR`; `view` is the owner view below).
- `src/deploy_workflow/owner_workflow.py`: `OWNER_SPECS` + CP-5; `SUPPORTED_ANALYTICAL`, `_QUALIFICATION["CP-5"] = cp5_integrity.PROMOTED`, `_PROBES["CP-5"]`,
  `_VIEWS["integrity_review"]`, `_ENTRY_VALIDATORS["CP-5"]` (the fixed dicts of G1-X section 2; D12 registrations). No `_CORES` row: CP-5 is live-contract and has no `submit`.
- No `src/deploy_vii` edit: `STEP_CHAINS`, `bindings/shipped.py` (CP5 is in `SHIPPED_MAPS`), `report_view` and the 17 `table_ids` exist. D8: none to register (checked below).
- New `tests/test_owner_cp5.py`; the run driver is the shared `tests/cp3_cp6_runs.py` (`cp6_closed(case, root)`), which G2 also imports.
- No edit of `src/`, `tests/` or `docs/` by this preparation; LEAD amends `docs/TOOL-CONTRACT.md` when the lease freezes (ruling 3, text in `expected.json` `execution.tool_use.CP-5.tool_contract_row`).

## Public API additions (positional, per G1-X section 2; live-contract module so `entry="model_payload"`)

```
OWNER_SPECS += "CP-5": OwnerSpec(module_id="CP-5",
                 steps=(StepSpec(step_id="integrity_review", schema=IntegritySubmission, sources=False,
                                 extract=False, upstream_grant=None, inputs="module_context", rules="none"),),
                 entry="model_payload", kind="analytical", publish=None)
owners.cp5.QUALIFICATION = cp5_integrity.PROMOTED
owners.cp5.probe(store, snapshot, attempt) -> None         # probe_one_step(validate=ENTRY_VALIDATOR, build=_candidate)
owners.cp5.view(historical, attempt) -> tuple[str, str]    # (sha256, body); docs/G1X-OWNER-CORE-PROTOCOL.md section 2; see Owner view
owners.cp5.ENTRY_VALIDATOR(execution, pack, attempt) -> StepValidation
    = cp5_integrity._validate_step(execution, attempt)     # adapter: the core's validator takes (store, attempt), not (store, pack, attempt)
```

`ENTRY_VALIDATOR` is the validator the CP-5 entry hands `Execution.submit_step` (`cp5_integrity.submit_cp5_step` passes `lambda _pack, current: _validate_step(store, current)`).
`review_scope(store, attempt)` reads `store.read()`, `store.pack(snapshot)`, `store.result(sha)` and `store.head_module`, all available on `_FrozenExecution`, so the verifier replays an invalid
step on the historical snapshot. `_candidate(output, attempt)` = `cp5_module(IntegrityReport.model_validate_json(output), attempt.inputs, attempt.number)`.
Receipt schema, JSON-lines operations and return shapes do not change. `rules="none"`: no `precheck`, no tool-loop rules (`registry.tool_set("integrity_review")` is submit-only, `applicable_rules == ()`).

## Submission schema (reference and judgment only)

Exactly `cp5_integrity.IntegritySubmission`; no field is added: `claim_reviews` (`claim_ref`, `producer_module`, `support` supported|partly_supported|unsupported, `rationale`, `upstream_refs`),
`contradictions` (`claim_refs`, `nature`, `rationale`, `severity`), `gaps` (`gap`, `why_it_matters`, `affected_modules`, `severity`, `action`). Text is labels only: no figure, no reference
syntax, no claim id (`prose.issues` against no facts). `upstream_refs` are fact ids of the claim's own module head or its citation refs `<claim_id>#c<n>`. Python writes every finding, id and status.
Literal values: `submissions.json` (`positive`, `gap`, `refusal_mutations`). A `{{FIG:name}}` reference is replaced at run time like the S1 and CP-3 oracles.

## Python composer and its zero, missing and blocked rules

There is no CP-5 arithmetic (checked: `cp5_integrity.py` imports `Decimal` only for the exact-value comparison of the identity check; no ratio, sum or rounding is produced), so there is no new composer.
The rules the owner relies on (all in `cp5_integrity`):
- Missing is never 0 or N/A: an empty register gets one `none` row of `not_applicable` cells with the reason "None in this CP-5 review (<title>)" (`_Tables.add`); this is the
  expected form of T5.6, T5.9, T5B.2 and T5B.3 (and, with no blocked head, no T5.8 own row). CP-6 counts a row only when a cell is known (`cp6_committee._register_rows`), so these empty tables are 0 rows.
- Known zero: a numeric fact of value 0 is a known zero (`exact_value`, `amount is None` is the only unsettled form); the identity check compares exact value, unit, currency and period.
- Blocked: CP-5 begins with a blocked *optional* head (`edge_rule("CP-5", m) == "restricted"`): it is bound, listed as a `blocked_upstream` finding (T5.8, T5B.6, T5.1 "Blocked upstream: outside the evaluated set") and is not
  evaluated. CP-5 refuses to begin when a required head (CP-0) is unrun, stale or blocked. CP-6 refuses to begin on a blocked CP-5 (block edge).
- The synthetic entry: every head of a synthetic run carries "Synthetic case; not real issuer qualification" (`execution.settle`), so CP-5 is always `restricted` in these cases whatever its report status.

## Refusals (all from the oracle; `expected.json` `refusals`)

12 validator refusals, each one literal invalid payload with the exact `validate_integrity` issue list (or prefix): unreviewed claim; doubly reviewed claim; unresolved `claim_ref`; `producer_module` not evaluated
(lists `CP-1, CP-1A, CP-2, CP-3`); unresolved `upstream_ref`; `supported` naming no ref; a figure in a rationale (`Bare figure: 5`); a claim id in a rationale (`Bare figure: T2.10.kf01`); empty rationale;
contradiction naming one module; gap naming an unbound module; shape error (unknown `support`, prefix `claim_reviews.<i>.support: `). 4 tool-use refusals (read before submit; pack tool; upstream tool; stale snapshot).
3 tamper refusals (consistent read-body forgery; step output; settled head status/hash). One **blocked case**: attempt 0 and attempt 1 both invalid (for example the unreviewed-claim payload twice) so CP-5 settles `blocked`;
G1 then retains exactly one `RefusedBegin` for CP-6 (`BLOCKED_EDGE`), begins nothing more, and the receipt verifies. Unexercised: `supported` over a Python finding (needs a mechanical finding, none occurs in the cases) and the three analyst finding categories (all reviews are `supported`; see Q5).
The 12 issue lists were checked against the product validator on a structural stand-in scope (report, probe 1).

## Owner view and tool use (D2, TOOL-CONTRACT; rulings 2 and 3)

**CP-5 is a submit-only step.** No pack tool, no upstream tool. Exactly one `read_inputs` per attempt before the submit; its body is the owner view.

**Binding.** `owners.cp5.view(historical, attempt) -> (sha256, body)`, registered in `_VIEWS["integrity_review"]` (`docs/G1X-OWNER-CORE-PROTOCOL.md` section 2, as `owners.cp2.view`).
`historical` is the G1 historical `Execution` of the ticket's snapshot (`owner_workflow._inputs` passes `_owner_historical(store, binding)`), so the view is recomputed from the journal, never from the live store. The digest is the sha256 of the UTF-8 body; `read_inputs` returns it, the journal records it, and the verifier recomputes `view(historical, attempt)[0]` and refuses `identity_mismatch` on a forged read (`cp5-tamper-read-body`).

**Exact body construction** (`expected.json` `view.binding.construction`):
1. `scope = cp5_integrity.review_scope(historical, attempt)`; a non-empty `scope.issues` raises `WorkflowError("identity_mismatch")`.
2. `P(head)` = `live.context.integrity_projection(scope)(head)` for the CP-1 head (facts a claim names as `{ref|unit}`, identity-group members, references a Python check flags) and `head.facts`, **every fact**, for every other head.
3. `block = cp5_integrity.context_block(scope, facts=P)`.
4. For every `modules[*].claims[*]`: each citation keeps `ref`, `source_id`, `locator` only (the `quote` key is deleted), and each `python_findings[i]` is cut at its first `": "` (the kind, or `kind on <ref>`, with no detail).
5. `block["python_findings"][i]` = `KIND_LABEL[f.kind] + ": " + f.where` over `python_checks(scope).findings` (ruling 3: no `detail`, which for a citation finding can carry a quote fragment).
6. `body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)`; return `(sha256(body.encode()).hexdigest(), body)`.

Key tree frozen in `expected.json` `view.key_tree`; no `quote` key at any depth. The view carries no citation `quote`; the one exemption is CP-3's own T3.3 `*.quote` facts, whose `shown`/`text`/`label` hold CP-3's settled market-evidence quotation text (not a citation).
Why `P` keeps every non-CP-1 fact: with the live projection alone a claim that has neither a figure token nor a citation (CP-2 T2.10.kf02-kf04, the CP-3 gap claim) shows the reviewer no fact, and `supported` requires a named ref, so such a claim could only be marked `unsupported`.

**Size (measured).** On a scratch copy of the S1 positive store (`slice-snapshot-positive`: CP-0, CP-1, CP-1A, CP-2 restricted; S1 has no CP-3 head), `ReviewScope` built from the stored heads, probe 3.3 s, original store untouched:
owner view body **147,174 bytes** (CP-1 11 facts and 7 claims 11,744 B; CP-1A 410 facts and 5 claims 103,479 B; CP-2 106 facts and 5 claims 30,794 B), sha256 `424adb04…92e8` of that body. The live projection with quotes was 26,989 bytes. CP-3 (39 facts and 2 claims positive; 28 and 1 gap) is not in S1: about 11 KB more at CP-2 density, an estimate, not measured. Of the 24,884 citations in the three heads none of the quote strings occurs in the body. The size is informational: the run recomputes it and no bound is asserted (none was ruled).

**TOOL-CONTRACT (ruling 3).** The CP-5 row (`docs/TOOL-CONTRACT.md:198`) changes from "explicitly granted bound CP-1 canonical fact/status view; includes missing facts; single-producer no-claim integrity scope" to "exactly the owner view of the CP-5 lease: `cp5_integrity.context_block` over the bound heads (every fact of the non-CP-1 bound heads; for CP-1 the facts `integrity_projection` keeps), no `quote` key at any depth and no citation quote string outside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`; CP-3's settled market-evidence facts, not citations), `python_findings` reduced to the kind label plus where; served by `read_inputs` on the G1 pathway only. The v1 and CP5-v2 upstream-tool grants stay for the earnings pathway". The exact row text is `expected.json` `execution.tool_use.CP-5.tool_contract_row`; LEAD edits the doc when the lease freezes. This counts as tool use for an upstream-only step under D2 only because the body is exactly this view.

**Assertions (test).** The body key tree equals `view.key_tree`; no `quote` key at any depth and no citation quote string of a bound head occurs in the body outside CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`); no `python_findings` string carries a finding detail (top level exactly `<KIND_LABEL>: <where>`, per claim no `": "`); `claims_to_review` equals `positive.claims_to_review` / `gap.claims_to_review`; each literal `upstream_ref` that is not a CP-1 fact appears in the body as a fact `ref` or a citation `ref`; the recorded digest equals sha256 of the body.
Upstream chain tool use (CP-0, CP-1, CP-1A, CP-2, CP-3) is the CP-3/CP-6 lease's, unchanged.

## Run-time assertions (rulings 5 and 6; `manifest.json` `run_time_bindings`)

The CP-1 head is a genuine promotion, so these cannot be derived in the oracle. The owner test asserts them against the actual run; a failure is reported to LEAD, never absorbed:
- **RT-1** the bound CP-1 head's claim ids are exactly `cash_flow_quality, coverage, data_quality, definition_risks, key_gaps, leverage, liquidity` (seven, no other), each with the shared narrative limitation text.
- **RT-2** `python_checks(scope)` returns zero findings: the view's `python_findings` is `[]` (top level and per claim), `blocked_upstream` is `[]`, T5.9 holds only its `none` row, no `CP-5-FINDING-NNN` exists.
- **RT-3** each of the seven CP-1 claims carries at least one citation, so the `<claim>#c1` ref and the T5.3 trace row exist; and each `#c1` (source_id, locator) equals the S1 observation (L1 above).
Analyst finding categories (unsupported, partly supported, contradiction) are not built; they stay for an optional later case.

## Consumption proof (D3)

This lease is the D3 extension of the CP-5 integrity scope to CP-1, CP-1A, CP-2 and CP-3. CP-5's consumption of CP-MODEL (DC-5) is not proved: R6 does not request CP-MODEL (ruling 1) and DC-5 stays open on the CP-MODEL row. For module X it is satisfied only when all three hold in the actual run:
1. the CP-5 attempt inputs bind X's settled head hash (`T5.1` row `X`, `module_inputs` in the oracle);
2. the settled review cites X's facts (T5B.1 `Upstream refs` cell names X's fact ids or citation refs, as in the literal);
3. the verifier probe re-runs `cp5_integrity._validate_step` on `_FrozenExecution`, which reads exactly those heads, rebuilds the candidate with `cp5_module` and `settle`, and gets the head back.
CP-5 is consumed by **CP-6**: the CP-6 attempt inputs bind the CP-5 hash; CP-6 reads `cp5_catalogue` (T5.9, T5B.6, T5B.7, T5B.8 rows), `cp5_review` (findings, flagged claims from T5B.4/T5B.3, unsupported count from T5B.2, verdict from T5B.8) and the status; the expected reads are in `execution.consumption`
(findings (), flagged (), unsupported 0, contradictions 0, cp4_rows (), verdict "Restricted over the evaluated set" / "CP-1, CP-1A, CP-2, CP-3" / "CP-0"), probed on the product `cp5_review`. Visible effect in the CP-6 head: its own limitation "CP-5 handoff caps the confidence below High: CP-5 is restricted" (no `; findings` suffix) and the
confidence cap `CP-5 is restricted`. Negative: a blocked CP-5 makes CP-6's begin a `RefusedBegin`. CP-5 has no consumer inside the product other than CP-6; say so in the receipt notes. CP-2's and CP-3's D3 closes with the same run: CP-6 reads them, and now CP-5 as well.

## Rendered sections (D7: no new block)

CP-5 has no Front Page block (`bindings/cp5.py`; `docs/frontend-direction-c.md` CP-5 row). Evidence rail: T5.1, T5.2, T5.3, T5.4, T5.5, T5.6, T5.7, T5.8, T5B.1, T5B.4, T5B.6, T5B.8. Limitations rail: T5.9, T5B.2, T5B.3, T5B.5, T5B.7 plus the module limitations (own settled).
Slots `cp5-<table id lower, dots to hyphens>` (`expected.json` `render.slots`). Whether a rail shows an all-`none` table was read from the binding (membership by binding, not by content), not rendered.

## Table ids and D8 collision check

T5.1-T5.9 and T5B.1-T5B.8, registered to CP-5 in `methodology.json` (serialised change 1bb6c0bc…: CP-2A no longer lists T5.*). The builder compares the 17 ids with every other module's `table_ids` (no collision; CP-0's `T5` is a different string) and asserts the transcribed
registers equal the CP-5 methodology entry exactly. No composed id is unregistered (CP-5 composes no `cp1_references`, no front table). **No D8 change is proposed.**

## Acceptance (expectations only from `expected.json`)

For each case (`positive`, `gap`), one closed run (the CP-6 run R6, amended; rulings 1 and 4):
- **Inputs.** Attempt inputs equal `module_inputs` (prepared-pack, CP-0, CP-1, CP-1A, CP-2, CP-3, integrity-submission); each bound hash equals the head's `result_sha256` at begin.
- **Tables.** All 17 tables equal `tables` (columns, row ids, labels, cell text, status, value_class, limitation), with the run-time bindings of `run_time_bindings` substituted; the bound rows of T5.5, T5.8 and T5B.7 per their `bound_rows`/`inherited_limitations` rules; table shape: one fact per column in every row.
- **Findings and status.** No `CP-5-FINDING-NNN` row; report status restricted; own limitations equal `own_limitations`, settled limitations equal `settled_limitations`; settled inherited equals the sequence minus own entries; module status restricted; the head has no claims.
- **Rendering.** `render` rails as listed.
- **Receipt.** `verify_owner_run_receipt` passes; store bytes unchanged.
- **Refusals.** Every `refusals` entry, including the blocked case and the tamper cases (forged consistently, so the check named is the one that refuses).
- **Tool use / consumption.** `execution.tool_use` and `execution.consumption`, the owner view assertions, RT-1 to RT-3, and the CP-6 reads above.
- **Semantic review (ruling 7).** review-precise-1 independently checks the 37 literal support judgments against the cited facts before the lease freezes.
- **Prose.** Every claim passes `prose.prose_issues`; probe: `deploy_vii.prose.bare_figures` returns zero hits on every rationale and gap text (done, report).
- **Gates.** `ruff check`, `ruff format --check`, `mypy --strict` (`MYPYPATH=src`) on every changed file.

## Deferred test commands (build-first rule; none run by this preparation)

```
"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -I cases/cp5-owner/builder/build.py   # reproduces the three JSON files; light, no lock
mkdir /tmp/deploy-workflow-heavy-job.lock && { PYTHONPATH=src pytest -q -p no:cacheprovider -o faulthandler_timeout=1800 tests/test_owner_cp5.py; rc=$?; rmdir /tmp/deploy-workflow-heavy-job.lock; exit $rc; }
```
Cost: no new promotion (ruling 4); the CP-6 run needs a genuine CP-1 promotion per case (11-26 min each). The prepared-pack hash is a run-time binding (`{{PACK_SHA256}}`); no literal pack hash exists in the cp3-cp6 or cp5 oracle, so the R6 amendment re-keys none.

## Resolved questions (LEAD rulings, applied above)

1. CP-MODEL and the CP-5 fan-in: option (a) taken (ruling 1). 2. Owner view: accepted as `P` (ruling 2). 3. TOOL-CONTRACT row: amended, `python_findings` reduced (ruling 3). 4. Run sharing: R6 only (ruling 4). 5. Mechanical findings: run-time assertions RT-1, RT-2 (ruling 5). 6. CP-1 citations: RT-3 (ruling 6). 7. Semantic review: review-precise-1, 37 judgments (ruling 7). 8. MODULES.csv: moves after the R6 run only (ruling 8). 9. CP-3 lease Q2: noted; the CP-0 literals already list `CP-5`, the premise is met and `{{CP5_FINDINGS_SUFFIX}}` is `''` in both cases (ruling 9).

Not verified: no end-to-end run (no CP-1 promotion, no owner harness, no G1-X code, no pytest); CP-1's seven narrative claims, their citations and every mechanical Python finding over the CP-1 head are asserted from reading code (RT-1 to RT-3 are run-time assertions, not observed); the view size was measured on the S1 positive CP-1, CP-1A and CP-2 heads only, CP-3's addition is an estimate, and `python_checks` cost over a promoted CP-1 beyond the 3.3 s probe is unmeasured; the owner view code (`owners.cp5.view`) does not exist, the probe applied the construction in a scratch script; the product-validator probe stubbed `citation_issues` (no pack), so citation and quote checks were not exercised; the rail rendering of an all-`none` table is read from the bindings, not rendered; the tamper and tool-use refusals are expectations from the S1a pattern, not executed; `supported` over a Python finding and the three analyst categories are unexercised; the semantic correctness of the 37 judgments awaits ruling 7's review.
