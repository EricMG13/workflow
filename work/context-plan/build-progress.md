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

Final-report items for the user (collected 2026-10-31/11-01):
- B10 narrows spec §7.2 (one retry after a 5xx).
- CP-5 settles over a missing producer only with an execution.py:244-246 change (not built); refused runs do not render (O3(a), O7 B13).
- Phase 3: `live/prompts.py` relative_value contract text ("basis quotes repeat a market_evidence row") vs Python-built rows (vii outside B6).
- Phase 5: "executed or filed" wording in methods/cp4.md, live/prompts.py:547, live/context.py:33 (vii outside B7); a CP-3 cap for draft-only legal inputs (outside B6); `executed` assessment of the `context` source (pre-existing).
- Phase 7: methods/cp1c.md, cp4c.md wording (outside B8/B9); free stress multiple wanted?; CP-2's optional CP-1C edge binds CP-1C in distressed runs (removal needs a ruling).
- Phase 8: CP-1B row labels fixed in US$ (bindings/cp1b.py, report_view.py:2353-2356) → CP-1B refuses non-USD; US$/IFRS labels outside the Phase 8 modules.
- Plan B hand-off items (work/context-plan/part-b-review-2026-10-31.md); the unanswered ChatGPT-link review.
