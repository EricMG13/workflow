# CP-3 (relative value) owner run lease - CP-3 half FROZEN by LEAD 2026-10-28 (draft rev 3); CP-6 half DRAFT rev 0, not frozen

Pin consumers: `cases/cp3d-owner/builder/build.py` reads `manifest.json` without a pin (through `MARKET_FILE`); `cases/cp5-owner/builder/build.py` pins `expected.json`, `manifest.json`, `submissions.json`; `cases/cp8-owner/builder/build.py` pins `manifest.json`. Every builder except cp2d and cp4 also pins `src/deploy_vii/methodology.json`, which this batch does not change. (Stage 1 release batch, LEAD 2026-10-28; none of this module's files changed.)

Amended by LEAD 2026-10-28 for the CP-5 owner lease freeze (`docs/CP5-OWNER-LEASE.md`; `work/lead/cp5-owner-preparation/report.md` ruling 1 and `review-precise-1.md` L3). The change is in the CP-6 half only. R6 drops CP-MODEL so that CP-5 can begin: `requested_modules` is CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6; `plan_order` and the CP-0 `plan_order` follow; `cp1a_consumers` is CP-2, CP-3, CP-5, CP-6. `runs.R6.note` records that the shared `upstream.statuses.CP-MODEL`, `execution.statuses` and `execution.consumption.CP-MODEL` hold for R3 only. Every R3 path is byte-identical: a key-path diff against the previous commit puts all 180 changed leaves under R6. Hashes move as follows: manifest e3cb2217… → 525c5f1b5ab0c8518b936b099621422d5fcf0424114c0a20b836964c66dd8e10; submissions 9f8c10e9… → eaecbcd012c3d157d96362c288b842e7c25157aabffff831e68dcd23bffe6b0b; expected 3c6ff67f… → 8ca60c96ac443282ac49a0ded495b751cf3b5457b9491f419a26ca59c0b3c310; builder 6dac614f… → 67db98157b66a0861696cf25482a7aba63576025c9e25b9ada976d344ae6d952. The CP-6 half stays draft.

Re-pinned by LEAD 2026-10-28 in the serialised `methodology.json` change (branch `lead/methodology-serialised`; `work/lead/methodology-serialised/review.md` COMMIT): `methodology.json` 348fbc4b… → 1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6 (CP-L10 required + CP-1 and TL10.5; CP-1C T1C.1-T1C.8; CP-1D drops T1E.*; CP-2A drops T5.*); two scratch rebuilds identical. builder 80450c52… → 6dac614feb4fbd1a9a0fa7aa6b6c59ec5234f1b25c1829e3f555a2cba3bbcf7a; manifest 2cb324be… → e3cb221737a3930278924eb16ad67208d9967cad455043565a79b24dcfae25c6; expected unchanged; submissions unchanged. Pins elsewhere in this file are superseded where they differ.

**Revision 3 (CP-3 half only; revisions 1 and 2 below, then `review-precise-r3-2.md` findings 1 and 2 and the Info note).** Revised after `review-precise-r3-1.md` and the LEAD rulings in `report.md` (M1 `column` of
front-table facts, M2 tamper, M3 scope refusal, M4 CP-2 view counts, L1 blocked CP-1A, L2 pinned methodology, L3, L4). Awaiting a
scoped re-review. The CP-6 half is unchanged draft rev 0 except where the generic M1 builder fix moved its front-fact `column`
values (listed in the revision report); it is frozen only after S1b. CP-3 is a **live-contract module** under
`docs/G1X-OWNER-CORE-PROTOCOL.md` §1: this lease cites that protocol for every G1 seam (spec registration, `OWNER_SPECS`,
`_QUALIFICATION`, probes, receipt and verifier) and adds no seam of its own.

Pre-code, not frozen. Registers CP-3 (relative value) and CP-6 (committee challenge) as G1 owner
specs on top of the S1 credit-snapshot run. Oracle: `cases/cp3-cp6-owner/{manifest,submissions,expected}.json`
(sha256 in the report), builder `cases/cp3-cp6-owner/builder/build.py`. S1 files are referenced by path and
sha256 only (`cases/snapshot/manifest.json` 68d591f6…a3f4, `submissions.json` bff9ed18…b35c, `expected.json`
d1aa1af9…9baa; `cases/financial/manifest.json` 6b3eeffe…3432).

## Why

CP-3 and CP-6 already have cores that follow the one-step shape of CP-2: a schema, `cp3_upstream` / `cp6_upstream`,
a validator, a Python composer, `cp3_module` / `cp6_module` and `submit_cp3_step` / `submit_cp6_step`
(`cp3_relative_value.py:1155-1222`: `cp3_module` :1155, `_validate_step` :1175, `submit_cp3_step` :1189; `cp6_committee.py:1337-1410`); both are dispatched by `submit_model_payload`
(`live/submission.py:256-283`) and both have shipped binding maps (`bindings/shipped.py`: CP3, CP6) and FP01 block
specs (`report_view.py:1088`, `:1096`). No new core, no new block and no registry change is needed. The lease adds
two `OWNER_SPECS` entries, two probes, one CP-6 view and the oracle. The `host.py` change CP-3 needs belongs to the separate H1
task (ruling Q6), not to this lease.

What the cores really read (checked in code, asserted in the oracle):

| Core | Heads it reads | Read for | Never read |
|---|---|---|---|
| CP-3 | CP-0 (T3 `authority` = `third_party` selects market sources), CP-1 (T4.18 facilities, referencable facts), CP-2 (rows of T2.1, T2.7, T2.10, T2.11, T2.12; input status for the confidence cap) | content | CP-3C, CP-3D, CP-4C, CP-2D (`cp3_relative_value.py:99-104`) |
| CP-3 optional | CP-1A, CP-4 | status and limitations only (CONTEXT `optional_upstream`; a blocked one adds an own limitation) | — |
| CP-6 | CP-0, CP-1, CP-2 (rows, challengeable rows, claim rows), CP-3 (rows T3.1/T3.3/T3.4/T3.9/T3.10, claim rows, `insufficient` from T3.3 kind and T3.4 confidence), CP-5 (T5.9, T5B.2/3/4/6/7/8, status) | content | CP-2A, CP-2E, CP-2D, CP-3C, CP-3D; CP-4 is no CP-6 edge |
| CP-6 optional | CP-1A | status and limitations only | — |

**Consumption (D3).** CP-6 is the consumer that proves CP-2 and CP-3 consumption: its basis cells name `CP-2 <ref>
(<label>)` and `CP-3 <ref> (<label>)` rows, its challenge table has one row per challenged CP-2 row, and in the gap
case the CP-3 head's T3.3/T3.4 cells force the CP-6 action bias to Insufficient Information. CP-3 itself consumes
CP-2 (basis cells, confidence cap). CP-5 is not claimed as consumer of CP-2 or CP-3 until its own lease extends the
integrity scope (D3). **CP-6 has no consumer inside the product** (only the call band and rails render it); say so
in the receipt notes.

**CP-6 cannot run without CP-5.** `registry.edge_rule("CP-6","CP-5")` is `block` and `plan(("CP-6",))` is
`CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6`. G1 `create` refuses a plan with a module lacking a spec, so the CP-6
run needs the CP-5 owner (S1b). See Q1.

## Prerequisites (base)

`codex/checkpoint` with all of:
1. G1 (after fix round 1), L2 and the S1a lease integrated, and the S1a run verified (CP-0, CP-1, CP-1A, CP-2 owners
   and CP-MODEL publication).
2. **Full H1** (the generic `*-submission` producer rule in `host.py`): a CP-3 `SourceSession` must authenticate the
   CP-1A and CP-2 heads as producers (S1a lease: the one-line `_SOURCE_STEPS` entry sufficed only because CP-1A bound
   CP-0/CP-1; CP-3 binds CP-2, whose module carries a `credit-synthesis-submission` tail).
3. The manifest adoption of this oracle after independent `mx-precise` review.
4. For the CP-6 part only: the CP-5 owner (S1b: `owners/cp5.py`, A4 integrated) and a D3 lease extending the CP-5
   integrity scope to CP-2 and CP-3. The CP-3 part does not need it (R3 run).

## Files

- New `src/deploy_workflow/owners/cp3.py`, `owners/cp6.py` (probes; CP-6 view). `owners/__init__.py` exists after S1a.
- `src/deploy_workflow/owner_workflow.py`: `OWNER_SPECS` +CP-3 +CP-6; `SUPPORTED_ANALYTICAL`, `_QUALIFICATION`
  (`cp3_relative_value.PROMOTED`, `cp6_committee.PROMOTED`), `_PROBES` +2. Registrations admitted under D12.
- No `host.py` edit in this lease: H1 (the generic `*-submission` producer rule plus `_SOURCE_STEPS["CP-3"]`) is its own task after
  L2 and S1a (ruling Q6; its code is saved in `review-precise-r3-1.md`). CP-6 opens no session. The session scope is already
  `readable_sources(store, attempt, step_id)`, which for CP-3 is the CP-0 `third_party` sources only (`live/context.py:115-151`).
- `src/deploy_vii/methodology.json`: optionally add `T6-FINAL` to CP-6 `table_ids` (Q7). No other `src/deploy_vii` edit.
- New `tests/test_owner_cp3.py`, `tests/test_owner_cp6.py`, run driver `tests/cp3_cp6_runs.py` exporting
  `cp3_closed(case, root)` and `cp6_closed(case, root)` -> `(store_dir, receipt_path, publication_dir)`; G2 imports it.
- No edit of `src/`, `tests/` or `docs/` by this preparation; LEAD amends `docs/TOOL-CONTRACT.md` when the lease freezes (Q5).

## Public API additions (keyword arguments only)

```
OWNER_SPECS += "CP-3": OwnerSpec(module_id="CP-3",
                 steps=(StepSpec(step_id="relative_value", schema=RelativeValueSubmission, sources=True,
                                 extract=False, upstream_grant=None, inputs="none", rules="journaled"),),
                 entry="model_payload", kind="analytical", publish=None)
             += "CP-6": OwnerSpec(module_id="CP-6",
                 steps=(StepSpec(step_id="committee_challenge", schema=CommitteeSubmission, sources=False,
                                 extract=False, upstream_grant=None, inputs="module_context", rules="none"),),
                 entry="model_payload", kind="analytical", publish=None)
owners.cp3.probe(store=..., snapshot=..., attempt=...) -> None
owners.cp6.probe(store=..., snapshot=..., attempt=...) -> None
owners.cp6.view(store=..., attempt=...) -> tuple[str, str]   # (sha256, body)
```

Receipt schema, JSON-lines operations and return shapes do not change.

## Submission schema (reference and judgment only)

Exactly the product schemas; no field is added.
- `RelativeValueSubmission`: `instruments` (facility id, fundamental view, market observation or `none`, basis = CP-2 row
  ids + `market_evidence` quotes, limitation), `market_evidence` (source, kind `observed|indicative_talk|none`, quote or
  null, as-of text, limitation), `preference` (ordering of facility ids, rationale, basis, confidence, limitation),
  `risks`, `gaps`. The model writes no price, spread, yield, rating or ranking number; figures are `{ref|unit}` references
  to CP-1 facts; market levels appear only inside quoted source text.
- `CommitteeSubmission`: `recommendation` (action bias, rationale, conditions, confidence, limitation, basis),
  `thesis_challenges` (CP-2 row id, counter case, evidence for/against, what would change the view, basis),
  `recovery_view`, `risks`, `gaps`. Basis = CP-2, CP-3, CP-5 row ids; figures as `{ref|unit}`; no pack quote.
- Literal values: `submissions.json` (`positive` and `gap`: `relative_value`, `committee_challenge`; the upstream deltas
  `readiness_review`, `cp1_source_context`, `business_context`; `refusal_mutations`; `cp5_premise`).

## Python composer and its zero, missing and blocked rules

No CP-3 or CP-6 arithmetic exists, so there is no new Decimal composer (checked: neither core imports `Decimal` or
computes a ratio, price, spread or yield). The only numbers shown are Python-spelled CP-1 facts (`business_context.spelled`
over Decimal facts: 50/30 = 1.67x, 30/30 = 1.00x, 30/5 = 6.00x, 9/50 = 18.0%, each from
`cases/financial/manifest.json` `q4_ltm_metric_oracle`) and source quotes. The composition rules the owner relies on:
- Missing is never 0 or N/A: no market evidence -> a `none` market-evidence row with its limitation, the preference
  Insufficient Information with an own limitation, T3.3 kind `None`; an empty required register -> a `missing` cell and
  an own limitation (`_empty`); an empty optional register -> `not_applicable` with the reason (not used by the cases).
- Blocked: CP-3 refuses to begin on a blocked CP-2 (`registry.edge_rule("CP-3","CP-2") == "block"`), so CP-3 never composes over a
  blocked CP-2; a blocked optional CP-1A or CP-4 is never a halt: it caps confidence below High (`confidence_caps` gains "CP-1A is
  blocked"), adds the own limitation "Optional upstream CP-1A blocked: CP-3 reads no business and transaction context" and makes
  settlement inherit its limitations prefixed "Upstream CP-1A blocked: " (`execution.py:361-362`). Exercised by the A3b analogue
  below (oracle `CP-3.blocked_cp1a_variant`). CP-3 and CP-6 refuse to begin when a required head is unrun, stale or blocked
  (`execution.current_inputs`); CP-6 additionally refuses a required head that is neither accepted nor restricted.
- Gap propagation: CP-6 action bias is forced to Insufficient Information when CP-3 has no observed or indicative market
  evidence or an Insufficient Information preference; confidence is capped below High while CP-5 is not accepted.

## Refusals (all from the oracle; `expected.json` `refusals`)

18 validator refusals (a mutated literal is refused with the stated issue, nothing settles; 10 are CP-3), 6 tool-use refusals (4 CP-3,
including the two scope refusals below) and 3 CP-3 tamper refusals.
Examples: CP-3 preference High (capped by restricted CP-2), observed row quoting talk, unknown facility, missing
ordering entry, action phrase, basis quote not in market evidence, unknown CP-2 row, talk worded as a level; gap: a
preference with no evidence, a fabricated market quote when CP-0 classes no source `third_party`; CP-6 High
confidence, a bias despite no market evidence, non-challengeable thesis ref, duplicate challenge, recovery view without
CP-4 evidence, trade term, unknown CP-3 row, bias/confidence mismatch. Plus: unread cited page (`Cited page not read
through read_pages: market page:2`) -> invalid attempt 0 re-begun as attempt 1; CP-3 read of a source outside the session scope (positive `financial page:1`; gap any source) -> refused receipt `not_permitted`
(`tools/source.py:46-47`; gap evidence of scope only, not of completion); CP-6 submit before a read, CP-6 pack tool call, stale
snapshot. Spec override, an alias in `requested_modules` (CP-3B, CP-6A), CP-4C/CP-3D/CP-2D/CP-3C in a
CP-3 run and any request that plans CP-5 without a CP-5 spec refuse at `create` and write nothing.

## Tool use (D2, TOOL-CONTRACT)

- **CP-3 (pack-tool step).** `registry.tool_set("relative_value")` is `pack`; scope = the CP-0 `third_party` sources
  (market only). `applicable_rules("relative_value") == ("unread-citations",)`: there is no absence rule, so a
  `search_pack` is not required (a real participant is still expected to search; the gate is the read). Positive case: ok
  `read_pages` for `market page:1` and `market page:2` before the submit. **Gap case: no readable source (market scope is empty) and the literal cites no locator: the gap case makes no ok call and only refused scope calls (`cp3-out-of-scope-read-gap`); tool-use completion rests on the positive case.**
  `read_inputs`: none (pack-tool step; the CP-1 ids come from run-time substitution, deferred like S1a Q6). **Scope refusal
  (review M3).** The session scope is market-only (`SOURCE_SCOPES`, `live/context.py:127-130`; host `_execution_state`): a
  `read_pages financial page:1` in the positive CP-3 session is refused `not_permitted`; in the gap session (empty scope) any
  `read_pages` is refused the same way. Oracle: `refusals.tool_use_refusals` `cp3-out-of-scope-read`, `cp3-out-of-scope-read-gap`.
- **CP-6 (submit-only step).** No pack tool. One `read_inputs` per attempt before the submit, body =
  `module_context("committee_challenge")` with `heads[*].claims[*].citations` removed (narrower than the live CONTEXT,
  D2; Q5). The TOOL-CONTRACT matrix has no CP-3 or CP-6 row; LEAD adds both when this lease freezes.
- Upstream chain tool use (CP-0, CP-1, CP-1A, CP-2): S1a counts plus `read_pages market page:1` in CP-0, CP-1 and CP-1A
  (positive case). **CP-2 read body (review M4).** Not "unchanged": the S1a assertion on `cases/snapshot/cp2-view-tree.json` is
  parameterised by the oracle (`execution.tool_use.CP-2.register_counts_by_case_and_run`; the file is sha256-pinned in the builder).
  R3: positive `source_classification` 4, `T2D.1` 4, `downstream_readiness` 3, `T2D.10` 3, `cp1a_rows` 74; gap 3, 3, 3, 3, 72. R6 (CP-6
  half, draft): positive 4, 4, 5, 5, 78; gap 3, 3, 5, 5, 76. Every other register count, the key tree and the status list equal the S1
  positive tree; `cp1a_rows` length equals `catalogue_size`. This covers normal R3 runs only; the blocked-CP-1A variant's empty CP-1A
  catalogue belongs to S1a A3b (review 2 Info).

## Consumption proof

- CP-3 attempt inputs: `prepared-pack`, CP-0, CP-1, CP-1A, CP-2 (plan order, hash-equal to the final heads at begin);
  the settled module adds `relative-value-submission`. CP-MODEL, CP-4, CP-3C, CP-3D, CP-4C, CP-2D are not inputs; the
  optional producers that stay unread are shown by that inputs list and by the CONTEXT `optional_upstream` (CP-1A with its
  limitations, CP-4 `not in this run`); the test asserts none of the four ids occurs in the body.
- CP-6 attempt inputs: `prepared-pack`, CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5; adds `committee-submission`. CP-MODEL is not an
  input.
- The verifier probes re-run `cp3_relative_value._validate_step` and `cp6_committee._validate_step` on `_FrozenExecution`
  (they read the bound heads: `cp3_upstream` / `cp6_upstream`), rebuild the candidate with `cp3_module` / `cp6_module` and
  `settle`, and get the head back.
- **Blocked CP-1A (review L1, A3b analogue).** Oracle `positive.CP-3.blocked_cp1a_variant`: CP-1A attempts 0 and 1 both fail a rule,
  the CP-1A head is blocked, CP-2 begins with CP-1A `blocked` (S1a A3b), then CP-3 begins with CP-1A `blocked` in its inputs and
  settles restricted: `confidence_caps` ["CP-2 is restricted", "CP-1A is blocked"], own limitation added "Optional upstream CP-1A
  blocked: CP-3 reads no business and transaction context", inherited entries from the blocked head prefixed "Upstream CP-1A blocked: ",
  tables and claims as the positive case. The CP-3 session must authenticate the blocked producer, which is H1's failed-producer
  branch, so this also exercises that branch.
- D3 proof for CP-2 and CP-3 is the CP-6 head (cells named above) in the R6 run. CP-3's consumption is therefore open
  until the CP-6 lease run verifies.

## Rendered sections (D7: no new block; D7 owners stay)

CP-3: FP01 `relative-value` (owner CP-3, prose, collapsed; line 1 = preference, then each instrument), Evidence rail
(T3.1, T3.3, T3.4, T3.9, `cp1_references`), Limitations rail (T3.10 and the module limitations). CP-6: FP01
`committee-challenge` (owner CP-6, collapsed; line 1 = action bias), `strengths-weaknesses` CP-6 side (owner
`CP-2 · CP-6`; thesis, strengths, weaknesses lines beside the CP-2 row of the same key), the call band (Action bias text
and the confidence meter: Insufficient Information 1, Low 2, Medium 3, High 5), Evidence rail (T6-FINAL, T6A.4, T6A.6, T6A.7,
`cp1_references`), Limitations rail (T6A.11 and the module limitations). FP03 blocks (instrument-levels,
market-against-fundamentals, compensation-preference) have no block spec (`report_view.py:1179-1184`) and are out of scope;
FP06 portfolio blocks belong to the deferred CP-3B/CP-6A owners.

## Table ids and D8 collision check

CP-3: T3.1, T3.3, T3.4, T3.9, T3.10 (registered to CP-3 only in `methodology.json`), plus the composed `cp3.relative_value`
and `cp1_references`. CP-6: T6A.4, T6A.6, T6A.7, T6A.11 (CP-6 only), the composed `T6-FINAL`, `cp6.committee_challenge`,
`cp6.thesis_challenge`, `cp6.strength_challenges`, `cp6.weakness_challenges` and `cp1_references`. Checked by the builder
over every module's `table_ids`: no id is shared with another module (the only registry overlaps remain the existing
CP-1/CP-1C/CP-4 T4.x and CP-2A/CP-5 T5.x sets). The composed ids are unregistered by design today; `cp1_references` is
shared by every module. CP-0's `T3` and `T6` ids are different strings from `T3.x` and `T6-FINAL`.

## Acceptance (expectations only from `expected.json`)

For each case (`positive`, `gap`) and run (`R3` for CP-3, `R6` for CP-6), one closed run:
- **Upstream.** CP-0 facts, limitations and commands equal `upstream.CP-0.<run>` (the builder checks this transcription
  against the frozen S1 CP-0 section); CP-1A tables equal the S1 positive tables except the listed `replace_table` /
  `append_row` deltas and `catalogue_size` (74, 78 positive; 72, 76 gap); CP-1 `source_context` per the literal; CP-2 equals
  S1 positive CP-2; every head restricted.
- **CP-3.** All five tables, the `cp3.relative_value` table and `cp1_references` (cell text, status, `[source, locator]`
  cites, value class, limitation), claims, own and settled limitations, inherited list (`literal_head` + CP-1 bind +
  `literal_tail_after_CP-1`), module inputs, CONTEXT checks, status restricted.
- **CP-6.** All tables listed in `CP-6.tables` in order, claims, own and settled limitations (with the CP-5 binding),
  inherited list (CP-1 bind, literal tail, CP-5 bind), call band values, forced-insufficient reasons (gap), status restricted.
- **Rendering.** `render` blocks and rails as in `CP-3.render` / `CP-6.render`. Front-table facts (`cp3.relative_value`, and the CP-6 front tables) carry the **row label** as
  `column` (`cp3_relative_value.py:928`; review M1), for example `cp3.relative_value.preference.value` -> "Preference" and
  `cp3.relative_value.i01.value` -> "Northbridge Term Loan".
- **Receipt.** `verify_owner_run_receipt` passes; store and publication bytes unchanged; CP-MODEL published (its inputs
  contain none of CP-3, CP-5, CP-6).
- **A4 tamper (review M2; S1a lease A4 pattern, `docs/S1A-OWNER-RUN-LEASE.md` A4).** On clones of the closed R3 positive run, (oracle
  `refusals.tamper_refusals`; review 2 finding 1): (a) forge a consistent CP-3 call: a receipt copy whose `read_pages market page:2`
  OwnerCall has an edited `body`, the audit `calls` file rewritten under the edited call's content hash, `receipt.sha256` rewritten;
  `_verify_audit` passes on the forged copy, `_verify_calls_reads` refuses `identity_mismatch` at the SourceSession replay
  (`owner_workflow.py:983-985`), and `verify_owner_run_receipt` refuses `identity_mismatch` (shape of
  `s1a-build/tests/test_owner_s1a.py:896-917`); (b) an edited CP-3 `relative_value` step output, caught by the store's own blob hash
  check, not by the CP-3 probe's output comparison (recorded limitation, S1a R3-5); (c) a receipt copy with the CP-3 head's `status`
  changed, and one with `result_sha256` set to `"0"*64`, both refused at `owner_workflow.py:1120`, before the seal check.
- **A3b analogue (review L1).** The blocked-CP-1A variant above: the receipt verifies and the CP-3 head is re-derived.
- **Refusals.** Every `refusals` entry (validator, tool-use including the scope refusals, tamper).
- **Tool use / consumption.** `execution.tool_use` and `execution.consumption`.
- **Gates.** `ruff check`, `ruff format --check`, `mypy --strict` (`MYPYPATH=src`) on every changed file.

## Deferred test commands (build-first rule; none run by this preparation)

```
"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -I cases/cp3-cp6-owner/builder/build.py   # reproduces the three JSON files; light, no lock
mkdir /tmp/deploy-workflow-heavy-job.lock && { PYTHONPATH=src pytest -q -p no:cacheprovider -o faulthandler_timeout=1800 tests/test_owner_cp3.py; rc=$?; rmdir /tmp/deploy-workflow-heavy-job.lock; exit $rc; }
mkdir /tmp/deploy-workflow-heavy-job.lock && { PYTHONPATH=src pytest -q -p no:cacheprovider -o faulthandler_timeout=1800 tests/test_owner_cp6.py; rc=$?; rmdir /tmp/deploy-workflow-heavy-job.lock; exit $rc; }
```
Last known cost: each case needs a genuine CP-1 promotion (11-26 min, QUEUE 2026-10-27). The pack hash includes
`requested_modules`, so R3 and R6 are different packs and share no CP-0/CP-1 head with each other or with S1a: four
promotions in all. Use module-scoped fixtures (`promoted[(run, case)]`, then clone) as S1a proposes; if CP-3 is accepted on
R6 only (Q1), two promotions.

## Open questions for LEAD (with recommendations)

1. **CP-5 dependency and sequencing.** CP-6 requires CP-5 (block edge). Recommend: freeze and run the CP-3 part on R3 now;
   freeze the CP-6 part only after the CP-5 owner and its D3 scope lease are integrated; CP-3 consumption (D3) closes only
   with the R6 run. Alternative (single R6 lease for both) saves two promotions but delays CP-3 behind S1b. No honest bypass
   of the CP-5 edge exists.
2. **CP-5 premise.** The oracle fixes only what CP-6 reads of CP-5 (`submissions.json` `cp5_premise`): restricted, zero
   unsupported and contradiction rows, nothing flagged, no CP-4 rows; findings and limitations are bound at run time. The
   CP-5 lease must produce a head satisfying it, or the CP-6 expected values for caps change. Also reconcile the CP-5 and
   CP-6 consumer entries this oracle authored in the CP-0 and CP-1A literals with the CP-5 lease's own.
3. **The new market source changes the S1 pack.** CP-3 needs a CP-0 `third_party` source with dated quotations; no frozen
   source has one. The positive case therefore adds source `market` (2 pages) and re-derives CP-0, CP-1 source_context and
   CP-1A deltas; every delta was validated by the product validators on the literals (probes below). The gap case uses the
   unchanged S1 three-source pack. Recommend accept.
4. **One instrument only.** Frozen `financial` page:5 states exactly one debt facility, so CP-3 orders one instrument and
   cross-instrument relative value is untestable; adding a second instrument would contradict frozen figures. Recommend
   accept and record as a limitation; do not edit the frozen source.
5. **CP-6 view (D2).** `module_context("committee_challenge")` includes every bound head's claims with citation quotes
   (including CP-3's market quotes), which the TOOL-CONTRACT upstream-only scope forbids. Recommend the narrower view above
   (citations removed), frozen as CP-6's exact view, a probe task to report its key tree, and the test that no pack quote
   string occurs in the body. CP-3 has no view (pack-tool step).
6. **Host (ruled).** `_SOURCE_STEPS["CP-3"]` needs the full H1 rule (prerequisite 2). Ruling Q6: H1 is its own `host.py` task after L2 and
   S1a; the reviewed host code is in `review-precise-r3-1.md`. This lease carries no host edit.
7. **`T6-FINAL`.** Composed by the core but absent from `methodology.json` `table_ids`. Recommend a one-line D12
   registration under CP-6 (no collision).
8. **CP-3 CONTEXT for a JSON-lines participant.** No `read_inputs` view exists for `cp1_facts` / `cp2_rows`. Recommend defer
   (S1a Q6 analogue); the literals use run-time substitution.
9. **Third case.** A talk-only market source (confidence cap and the level-wording rule) is covered by the refusal
   `cp3-talk-worded-as-level` but has no positive case. Recommend a later optional case, not a gate.
10. **CP-0 gap form.** The gap case pins `READY_WITH_LIMITATIONS` for CP-3 with a CP-0 gap (so CP-3 runs and settles
    Insufficient Information), not `CONDITIONAL / DO NOT RUN` (that path, a `RefusedBegin`, is the financial precedent).
    Recommend keep.
11. **D1.** This lease registers CP-3 and CP-6 only. `requested_modules` containing `CP-3B` or `CP-6A` canonicalises to
    CP-3/CP-6 (`registry.canonical`); the lease test asserts receipts and `docs/MODULES.csv` count no completion for the
    aliases. Recommend LEAD keeps the two rows unregistered until their own lease.

Not verified: no end-to-end run (a genuine CP-1 promotion and the owner harness) and no pytest; CP-1's `narrative`,
`readiness` and `quality` stages were assumed unaffected by the extra source and the larger `requested_modules`, as S1
assumed; the CP-1 T4.18 facility cells (`term-loan`, `Northbridge Term Loan`) come from the financial literal, not from a
CP-1 head; the FP01 and rail renderings and the collapsed-summary clip were derived from code reading and the S1 precedent,
not rendered; host session scope for CP-3 and the H1 rule were read, not executed; the CP-5 head was not built. Rev 1 additions: the blocked-CP-1A variant was probed on a real CP-1A head forced `blocked` and a stub snapshot for
settlement inheritance, not on an A3b-produced CP-2 head (whose rows must still resolve `T2.11.r01`, `T2.1.assessment`,
`T2.7.s01`); tamper and scope refusals are expectations from the S1a pattern and the code, not executed; the R6 CP-2 view counts
are derived from the CP-1A deltas, not observed.

## LEAD freeze of the CP-3 half (2026-10-28)
Frozen after review-precise-r3-1, revision 2, review-precise-r3-2 and revision 3
(`work/lead/cp3-cp6-owner-preparation/`). LEAD scratch rebuild matched byte for byte: manifest
2cb324becaeab80ff7d00e5a0ca3b33ef79a3d559fa7e25f5909b3d5eda3d87b, submissions
9f8c10e9e31e88f15f797c89102c6cf2d938b25a1878d2b5aafe5354786dde38, expected
3c6ff67f22e7c1d0cf843050610cb3fe67c01814d6851360fcd6e385ec04d0a0, build.py
80450c52d4ae878ca091c4fdde992cf79b71168533a609c2a8d295368f393e37. Verifier line numbers cite the LEAD
branch at 41c08cb and move when S1a integrates; tests assert refusal codes. G1 seams follow
`docs/G1X-OWNER-CORE-PROTOCOL.md` (CP-3 live-contract). Build after S1a, G1-X and H1 integrate. The
CP-6 half is not frozen: it waits for S1b (CP-5) and its D3 scope lease.
