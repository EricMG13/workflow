# Rulings: context-file consumption plan, build of Part B and Phases 2-8 (2026-10-31)

Plan: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` (Part B amended at a21e9c98,
merged as c545f2db). Branch `claude/context-plan-build` from `codex/checkpoint` 60191a06.
The user's goal in this session: "complete the plan".

## User rulings (the user's own word in this session, 2026-10-31)

- **B1 `src/deploy_vii` changes approved** ("Approve all listed"): the changes Part B marks
  **vii**: O1 `registry.py` fan-in, `bindings/cp6.py` and `cp6_committee.py` if the CP-6 core
  edits them; O3 `execution.py` (G4/G5); O7 `methods/cpdr.md`, registry, decision 0007,
  `execution.py` input binding, `methodology.json` and `bindings/cpdr.py`. Each change carries a
  D12 `post_import_patches` record in `docs/reuse/manifest.json` and an `mx-adversary` review.
  Any `src/deploy_vii` change not on this list goes back to the user.
- **B2 Phases 2-8 are built in this session** ("This session"), not by the Modules session: each
  phase as one batch, its questions ruled here (applied recommendations, below), its oracle
  written by a separate preparer and approved by an independent `mx-precise` review, built by
  `mx-feature`. AGENTS.md's independence rule holds: no builder of a module prepares or reviews
  its oracle.
- **B3 Test runs** ("Yes"): each task runs its affected tests plus `ruff check`,
  `ruff format --check` and `mypy` with `PYTHONPATH=src "/Users/ericguei/Documents/Deploy
  Workflow/.venv/bin/python"`; the full suite runs once before each hand-off to the PR Manager.

- **B6 Phase 3 CP-3** ("Change CP-3"): `src/deploy_vii/cp3_relative_value.py` may change so that
  Python builds market evidence from the context's quotes (research:
  `work/context-plan/reviews/phases-2-8-questions.md` Phase 3 item 3).
- **B7 Phase 5 draft authority** ("Add draft authority"): `src/deploy_vii/readiness.py` and
  `cp4_legal.py` may add a `draft` authority, admitted only when the context's `legal_documents` is
  `draft`, with a fixed draft limitation on CP-4.
- **B8 Phase 7 valuation** ("Add edge and tables"): `src/deploy_vii/methodology.json` (CP-4C upstream
  CP-1C; new CP-1C EV/EBITDA tables), `bindings/cp1c.py` and `contracts.py` (CP-1C in the
  distressed preset) may change.
- **B9 Methods texts** ("Update them"): wording-only edits to `src/deploy_vii/methods/*.md` that
  Phases 4, 6 and 8 make stale.
- B6-B9 each carry D12 records; B6-B8 get an `mx-adversary` review, B9 an `mx-feature` review.

## Applied recommendations (user, 2026-10-29: "apply your recommendations for questions")

These do not cover `src/deploy_vii` changes beyond B1, new dependencies, or config changes.

- **B4 Codex branch not merged first.** Part B said `claude/codex-findings-review-64c673` must be
  merged before its first brief cites it. That branch holds the user's unreviewed testing plan, so
  briefs instead quote the needed lines from the pinned commits Part B names (`e636f71e`
  orchestration gaps, `efe43725` design spec and testing plan, `80748343` CP-DR description), read
  with `git show`. Cost if wrong: a brief cites text the user later changes on that branch.
- **B10 One retry after a 5xx narrows spec §7.2 (the user's budget ruling).** A provider 5xx or a
  cut stream with no usage is "sent, charge unknown": its reservation stays held and counted. R5's
  one transient retry still goes out once per run, with a fresh reservation and the next
  `call_index`, only while the cap admits both reservations; a failed retry, a timeout or any other
  unknown charge stops the run. Spec §7.2 says an unknown charge stops the configuration; this lets
  one retry go first. Cost if wrong: one extra reservation of exposure per run, still inside the cap.
- **B11 Anthropic cache writes.** Reservations use the higher (1-hour) cache-write rate; settlement
  prices the reported `ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens` at their own
  rates. OpenAI `cache_write_tokens` are part of `input_tokens` (charged once, at the write rate).
- **B5 One build branch, phase hand-offs.** All of Part B and Phases 2-8 build on
  `claude/context-plan-build`; each finished phase goes to the PR Manager as a lane integration.
- **B12 CP-DR brief locks before analysis, not before retrieval (O7 Q9; amends OD4).** In the one-run
  design the research manifest's files enter the pack before `prepare`, so the brief cannot precede
  intake. The brief is CP-DR's first owner step, its source scope excludes every `ev-*` source, and
  it is hash-locked before the `research` step starts. OD4's aim (questions are not shaped by the
  evidence) holds; the brief does not choose what is retrieved (the user's manifest does). Cost if
  wrong: a later brief-driven web search would need retrieval moved after the brief (a second pack).
- **B13 A refused CP-DR does not stop CP-1C or CP-2 (O7 Q10).** The O3 walk continues; CP-1C and
  CP-2 run without a CP-DR input, and `run.json` records `cp_dr_state` (`refused` or `blocked`) and
  the cause, so the dossier's absence is visible. CP-5's fan-in includes CP-DR (registry.py:26), so
  a refused CP-DR makes CP-5 (and CP-6) refuse for a missing producer and no report renders: the same
  outcome as any other refused module (O3's open item, for the user). Cost if wrong: a run with a
  refused CP-DR ends without a report; the user reruns without `cp_dr=True` or after repairing it.
- **B14 D12 records for repo-authored `src/deploy_vii` files.** B1 and B6-B9 require a D12
  `post_import_patches` record for each approved file. For a file not in the manifest's `files[]`
  (repo-authored: `bindings/*.py`, `methods/cp2h.md`, `methods/cpdr.md`, `methods/cp1c.md` …) the record is
  still written, with `imported_sha256` = `prior_project_sha256` = the file's sha256 at the commit before
  the plan's first change to it, and a `reason` that begins "repo-authored (not in files[])"; the other
  fields as usual. Where another file pins its hash (`cases/PINS.json`, leases), the re-pin runs through
  the oracle process in the same commit. Cost if wrong: one manifest shape the PR Manager may ask to
  change (no test reads `post_import_patches` today).
- **B15 Test time (user, 2026-11-01: "test are taking too long").** Narrows B3. Per task: only the brief's
  affected tests, without `RUN_PROMOTION=1`, one run at a time (no duplicate or parallel copies of the same
  files); the gated tests are reported deferred (`gates-first-pass=n/a`). The promotion-gated tests and the
  hours-long files (`test_owner_workflow.py`, `test_owner_s1a.py`, `test_financial_workflow.py` full) run once
  per phase, by the controller, on a frozen export, before the full suite and the PR Manager hand-off.
  O1 Task 1 at 4725c3b6: presets, order, workflow and financial passed with `RUN_PROMOTION=1`; cp3, cp4, cpos,
  rendering, s1a were stopped and wait for the O1 phase gate.
- **B16 Fast tests only (user, 2026-11-01: "only run the fast test").** Supersedes B15 and narrows B3.
  Per task: the RED tests and the touched test functions by node id, each command under 5 minutes, never
  `RUN_PROMOTION=1`, never a whole long file. Per phase (controller, before the PR Manager hand-off): the
  union of those node ids plus `ruff`/`mypy`, not the full suite. Promotion-gated tests, the long files and
  the full suite are not run in this session; each hand-off lists them under `Not verified:` for the PR
  Manager / CI. Cost: a regression outside the touched tests is found later, at CI.
- **B17 Recommendations applied (user, 2026-11-01: "apply your recommendations for all").** Each item the
  controller had held for the user, decided by its recommended option. The `src/deploy_vii` edits below are
  approved by this ruling, each with a D12 record (B14 shape where repo-authored) and the review named.
  1. B10 (one retry after a 5xx, narrowing spec §7.2): kept.
  2. A refused module leaves CP-5 (and CP-6) refused and the run unrendered (O3(a), B13): kept, fail
     closed; no `execution.py:244-246` change, no partial rendering.
  3. Phase 3: the `relative_value` contract text in `src/deploy_vii/live/prompts.py` is edited (wording
     only) so basis entries refer to Python's context rows by id and never copy their figures; built in
     Phase 3 Task 4 with the O6 follow-through; `mx-adversary`; prompt-set hash re-pinned.
  4. Phase 5: "executed or filed" wording in `src/deploy_vii/methods/cp4.md`, `live/prompts.py:547`,
     `live/context.py:33` becomes "executed, filed or, on a draft-documents run, draft"; wording only;
     `methods/cp4.md` `mx-feature` review, the two model-facing texts `mx-adversary`.
  5. Phase 5: no CP-3 confidence cap for draft-only legal inputs (CP-4's draft limitation carries it).
  6. Phase 5: `readiness.py` refuses `executed`, `filed` or `draft` authority on the `context` source itself
     (D2: the context is `unknown`); built in Phase 5 Task 1 (B7's file).
  7. Phase 7: wording edits to `src/deploy_vii/methods/cp1c.md` and `methods/cp4c.md` for the EV tables and
     the CP-4C binding (B9 extended to Phase 7; `mx-feature` review).
  8. Phase 7: every CP-4C valuation case, the stress case included, carries the selected multiple (no free
     stress multiple); CP-2's optional CP-1C edge is kept, its distressed-run effects stated (Design 12).
  9. Phase 8: CP-1B row labels in `src/deploy_vii/bindings/cp1b.py` and the label check at
     `report_view.py:2353-2356` take the run's money unit (USD runs byte-identical); replaces the
     `cp1b_currency_label_fixed` refusal; `mx-adversary`.
  10. Phase 8: `US$`/IFRS labels outside the Phase 8 modules stay out of scope (follow-up list).
  11. O1 G1b: the frozen R6 oracle (`cases/cp3-cp6-owner`) is amended as the root-cause investigation
      recommends (CP-MODEL CP-1A judgment row, builder self-check fixed, rebuild, re-pins), by a separate
      preparer with an independent `mx-precise` review.
- **B18 (controller, applied recommendation, 2026-11-01).** B17 item 9 covers `report_view.py:2298`
  (`_cp1b_fact_shape`, the same CP-1B layout validator, called at :2385): every CP-1B money fact takes
  `("MILLIONS", C, 1e6)` with C the currency of `revenue:current`, required non-None; no US$ fallback for
  gaps; USD runs byte-identical; `mx-adversary`. Without it the label change cannot settle a non-USD run
  (review `work/context-plan/reviews/b17-amendments-review.md` finding 1). Cost if wrong: one line reverted
  and non-USD runs return to the `cp1b_currency_label_fixed` refusal.
- **B19 (controller, 2026-11-01): the owner-path CP-1B accepts only pairs its fixed prose is true of.** The shared
  earnings composer's E-* wording names q3-2025→q4-2025 (flat) and FY2024 absent→FY2025 (O1 Task 3 reviews,
  `work/context-plan/reviews/o1-task3-review.md` M1, mx-adversary H1/M2). O1 fails closed: the owner core accepts
  (q3-2025, q4-2025) only when every T1B.1 delta is zero, and (fy-2024 absent, fy-2025) as the one missing-prior
  pair; every other pair is refused with issue `unsupported_pair`; the view lists exactly the accepted pairs.
  Phase 2 Task 4 gains a step: generalise the composer prose from the report's own pair, periods and deltas
  before the owner path widens its pairs. Cost if wrong: owner runs refuse pairs until Phase 2 Task 4 lands.
- **B20 (controller, 2026-11-01): context citation rule, shared by Phases 3 and 4.** A context figure is cited by its
  key/value text only when that member is alone on its line; otherwise by the text from the row object's `{`
  through the figure when that is one unique line; otherwise the row is dropped into a named gap. Phase 3 plan
  Design 3 (:65-67) is amended to say so (Phase 3 oracle review; plan :166, :221, ruled decision 3). Phase 3 gap
  texts: `context quote for facility <facility_id> cannot be cited as one unique span; not used` and
  `context deal terms for facility <facility_id> cannot be cited as one unique span; not used`; on a residual
  key collision the later row (higher index) is dropped. CP-3D unreadable context: one issue per problem,
  `context source unreadable: <problem>`. Cost if wrong: one oracle re-cut and the helper's branch order.
- **B20a (controller, 2026-11-01, amends B20).** An object-anchored quote runs from the object's `{`, so a collision on
  a shared figure makes every colliding row's quote non-unique: every row whose cited figure is not unique in its
  span is dropped (not only the later row); Phase 3 ruled decision 3 (:274) reads the same. The gap names the
  row (1-based): `context quote row <n> for facility <facility_id> cannot be cited as one unique span; not used`
  and `context deal terms row <n> for facility <facility_id> cannot be cited as one unique span; not used`
  (Phase 3 oracle re-review: a quote matching two objects is a guessed span, Design 3 :66-68).
- **B20b (controller, 2026-11-01).** B20a drop gaps render in a module's own limitations exactly as the Design 5
  named context gaps do (same `Gap (<severity>): ` prefix and severity); the B20a text is the gap description.
- **B21 (controller, applied recommendation, 2026-11-01): O1 done-when part 2 as measured.** O1 Task 5 (526ddcf0)
  measured that on frozen fixtures five presets stop at CP-0 as an oracle gap (each union pack matches no frozen
  CP-0 document's source set) and earnings_update walks CP-0, CP-1, CP-1B, publishes, then stops at CP-1D. No
  stand-in payload is made. O1 is done when: all six presets pass `_check_specs` (Task 4); each preset's
  measured end state is pinned (`EXPECTED`, `test_step1_table`); the gated earnings walk and
  `test_no_later_module_before_publish` are written (CI, B16). The full portfolio_decision walk with
  `verify_owner_run_receipt` and `test_receipt_rejects_model_in_cp5_inputs` move to O2 Task 5 on the frozen
  `cases/o2-synthetic` (its CP-0 covers the prepared pack). Per-preset CP-0 oracles for the other presets are a
  follow-up for the owner. Cost if wrong: receipt verification for five presets stays unproven until those
  oracles exist.
