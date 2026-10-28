# CP-2E Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `worktree-agent-a219254fe68cc1c2d`, commit `5b012e7`, base f2cd61f.
- Files: `src/deploy_workflow/owners/__init__.py`, `src/deploy_workflow/owners/cp2e.py`, `tests/test_method_cp2e.py`.
- Functions: `derive_sensitivity` (Decimal, 38 digits, half-even), `validate_macro_fx`, `inputs_from_submission`, `operands_of`, `cited_pages`, `own_limitations`, `compute -> MacroFxResult` (T2F.1–T2F.9, claims, own limitations; spelling via `report_view.fact_spelling`/`figure_unit`).
- Inputs: there are no manifest `fact_bindings`. The operands are `macro_fx` submission quotes checked against financial pages (total_debt, ebitda, interest, fcf, fx_cash_effect, facility terms, debt_currency, foreign_ebitda_share); judgment fields cover absences, hedge_ratio, rate/fx shocks, rationale and assessments.
- Test: 58 passed in 0.25 s. Gates: ruff 0, format 0, mypy --strict 0. gates-first-pass=n (ruff flagged 2 issues and reformatted).
- Covered:
  - both cases, cell for cell;
  - 8 fixtures;
  - cp1_cross_check;
  - 27 refusals, with `all_issues`;
  - blocked_cp2e issues for attempts 0 and 1.
- Left to Stage 2/4: hand_built_page_refusals, tool_use_refusals, tamper, RULES, cp0/inherited limitations, run behaviour, consumption, render, and Citation assembly.
- Engine/oracle disagreements: none.
- Lease gaps (each fails closed with ValueError, pinned by a test; LEAD to word):
  1. The FX claim when the foreign EBITDA share is stated: the only template puts a known number in a gap chip.
  2. The rate claim when the rate terms are stated but the shock can't be calculated (floor above zero, or floor not stated).
  3. The rate claim when baseline coverage is not_applicable (cash interest 0).
- Minor: with no facility balance but a stated debt currency, the missing reason says "currency not stated" (as the oracle states).
- Stricter than the builder: full-string regex matching, so `"40\n"` is refused.
- Not verified: Module/Citation assembly, inherited limitations, RULES/tool use, the hand-built page, tamper/probe, rendering, settled runs, and gap 1–3 wording.
