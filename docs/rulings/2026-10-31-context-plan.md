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
