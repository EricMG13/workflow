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
- **B5 One build branch, phase hand-offs.** All of Part B and Phases 2-8 build on
  `claude/context-plan-build`; each finished phase goes to the PR Manager as a lane integration.
