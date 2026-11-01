# Build progress: context plan Part B and Phases 2-8

Recovery map for the controller (goal "complete the plan", user 2026-10-31). Trust this file and
`git log` over memory after a compaction. Rulings: `docs/rulings/2026-10-31-context-plan.md`.
Branch `claude/context-plan-build` from `codex/checkpoint` 60191a06; rulings commit 3451eec5.

Order: O1 → O5 → O2 → O3 → O4 → O6 → O7a-d; Phases 2-8 after O2 (2 → 3 → 4 → 5 → 6 → 7 → 8).
Each phase: detailed plan (mx-feature draft) → plan review (mx-autonomous) → rulings → SDD build
(mx-feature implements; mx-precise reviews; mx-adversary on money/ordering/security; src/deploy_vii
diffs too) → phase gate → PR Manager.

| Phase | Plan file | State | Commits | Sent to PR Manager |
|---|---|---|---|---|
| O1 | docs/superpowers/plans/2026-10-31-part-b-o1.md | plan approved 8e17789b (2 review rounds); building: Task 1 reopened for a stale cpos registry pin (fix 2 = re-pin by a separate preparer); Task 2 building (BASE e871f90c) | 5a00d7be, 4725c3b6 | — |
| O5 | docs/superpowers/plans/2026-10-31-part-b-o5.md | plan approved 01ee8514 (3 rounds); provider docs in work/context-plan/provider-docs-2026-10-31.md; builds after O1 | — | — |
| O2 | docs/superpowers/plans/2026-10-31-part-b-o2.md | plan approved 5032faaa (2 rounds; new oracle cases/o2-synthetic) | — | — |
| O3+O4 | docs/superpowers/plans/2026-10-31-part-b-o3-o4.md | plan approved (2 rounds) + N1 amendment (identity rebinding, whole-pack equality) | — | — |
| O6 | docs/superpowers/plans/2026-10-31-part-b-o6.md | plan approved (2 rounds) | — | — |
| O7a-d | docs/superpowers/plans/2026-10-31-part-b-o7.md | plan approved (3 review rounds; N1 identity rebinding moved into O3 Task 4); rulings B12-B13 | — | — |
| Phase 2 | docs/superpowers/plans/2026-10-31-phase-2-identity-periods.md | plan approved 563391aa (3 rounds); Task 4 after O1 Task 3 | — | — |
| Phase 3 | docs/superpowers/plans/2026-10-31-phase-3-market-evidence.md | plan approved 563391aa (3 rounds); builds context_cites.py; O6 follow-through task | — | — |
| Phase 4 | docs/superpowers/plans/2026-10-31-phase-4-ratings.md | plan approved 8e2392ea (3 rounds) | — | — |
| Phase 5 | docs/superpowers/plans/2026-10-31-phase-5-attachments-modes.md | plan approved 563391aa (2 rounds) | — | — |
| Phase 6 | docs/superpowers/plans/2026-10-31-phase-6-pinned-assumptions.md | plan approved fa92d0a0 (2 rounds); turns on O6 pins per module | — | — |
| Phase 7 | docs/superpowers/plans/2026-10-31-phase-7-valuation.md | plan approved ad322a4d (2 rounds); needs O7d | — | — |
| Phase 8 | docs/superpowers/plans/2026-10-31-phase-8-periods-currency.md | plan approved 13df6b4c (3 rounds); builds last | — | — |

Notes:
- Modules (2026-10-31): not editing owner_workflow.py or the listed modules. Overlap risks:
  its `claude/s8-vii` merge touches `src/deploy_vii` (cash_bridge, financial_contracts,
  financial_reconciliation, period_reconciliation, report_view, source_context, statement_extract,
  statement_validation) and `docs/reuse/manifest.json`; avoid `source_context.py`, expect manifest
  append conflicts. Handed to us: Stage 8 Low `owners/cp2h.py:1616` gap-text masking (take into
  Phase 4). Tell Modules before touching `financial_workflow.py` precheck (`_statement`/`_months`);
  it then holds its item 3.

Final-report items: all decided by the user's "apply your recommendations for all" (2026-11-01) — ruling B17 in
docs/rulings/2026-10-31-context-plan.md (11 items). Remaining for the final report: what B17 decided, the Plan B
hand-off items (work/context-plan/part-b-review-2026-10-31.md), the unanswered ChatGPT-link review, and the
slow/promotion tests left to CI (B16).
B17 plan amendments review (mx-autonomous aa2f06f2): P3/P5/P7 approve, P8 fix (H: report_view.py:2298 USD literal → ruling B18 2fa3457d; H: re-pin list; M: nine labels; L x3). Plan fixer mx-feature ad789fb6. (00:46 UTC)
Phase 8 plan fix 2 73e254fd approved (aa2f06f2). Phases 3, 5, 7, 8 B17 amendments: approved (d6508410, 73e254fd). Preparers: P3 ab25fc2b, P4 a86eb9b2, P5 a5601db8 (mx-feature). (00:48 UTC)
Preparers: P6 a9445071, P7 a6370cff, P8 afe48384 (mx-feature), dispatched 00:48 UTC. Builders of Phases 3-8 must be other agents.

Plan amendments pending (apply before each phase's build; one docs dispatch + mx-feature review), 01:19 UTC:
- Phase 2 Task 4: B19 step — generalise the CP-1B composer prose before the owner path widens pairs.
- Phase 3 Design 3 (:65-67) and ruled decision 3 (:274): B20/B20a/B20b (member alone on its line; every colliding row dropped; gap names row n; Design 5 prefix).
- Phase 5 Task 3: "ten cases" = 15 ids incl. legal-draft-missing(+gap) with the ruled draft-missing text.
- Phase 6 Tasks 5/7 REDs: pinned row also T2F.9.r08.text (CP-2E) and T3E.9.r12.text (CP-3D).
- Phase 8 Done-when 1: no stale unshifted literal (derived list), not "no 2025".
Pre-existing defects for the owner (final report): cases/cp4c-owner/builder/build.py:51 stale CP-3C manifest pin 2f65c085 (10ec5231) and class-by-class division vs the lease's largest-remainder; docs/CP5-OWNER-LEASE.md:43 methodology 1bb6c0bc vs 0932d9fb; tests/test_upstream_tools.py ruff C408 x14 + mypy; earnings.py:315-318 raw-day period-length comparison (FY2024 leap year; Q2 91 vs Q3 92 days); O1/B1: no CP-5/integrity check of CP-MODEL head identity (only publish_cp_model).
All Task 0 oracles frozen (Phases 2-8, o2-synthetic); cases/pins.py --check 0 (176 paths) at 5485b8be. (01:21 UTC)
