# CP-2D Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `worktree-agent-a69f2394899aee6d5`, commit `44c919c`, base 509f7db. Files: `owners/__init__.py`, `owners/cp2d.py`, `tests/test_method_cp2d.py`.
- Surface:
  - contracts MinimumCash, MinimumCashAbsence, Assessment, LiquidityBridgeSubmission;
  - Facility, Operands, Cp2dInputs;
  - `compose_bridge(*, operands, horizon_months, minimum_cash, balance_date) -> Bridge`;
  - own_limitations, check_cp1_totals, bridge_of;
  - `compute -> Cp2dResult` (T2E.1–T2E.5, T2E.6/7 ledgers, limitations, claims, status);
  - `submission_issues(*, submission, offered_refs)`.
- Inputs: T4.5 LTM Q4 25 flows; T4.6 q4-2025 balances; T4.10 cross-check metrics; T4.18 facilities via `_maturity_figure`; D0 2025-12-31; judgment (horizon, minimum cash, assessments).
- Test: 43 passed in 0.18 s. Gates 0. gates-first-pass=n (format). The RED run was not observed: the worktree guard refused the first run.
- Covered:
  - derived values, missing_not_zero and own limitations for all six cases;
  - T2E.1–T2E.5 cell for cell;
  - T2E.6/7, status, claims;
  - 13 refusals plus the valid literals;
  - blocked_cp2d issues.
- Left to Stage 2/4: T2E.9, Fact/Calculation objects, basis refs against the real view, cp0/upstream/inherited limitations, the blocked/begin-refused cases, tool use, cp2d_reader, fp04_render, probe/tamper, stale binding.
- Engine/oracle disagreements: none.
- LEAD points (the code raises where nothing is pinned):
  1. prohibited conclusions (only the spelled-out phrases are checked);
  2. undisclosed revolver claim and gap wording;
  3. the T2E.7 label for a non-zero S&U difference;
  4. non-USD facility; zero total debt;
  5. multi-facility ordering;
  6. maturity-wall citation refusal text;
  7. liquidity_to_debt unit (treated as a fraction);
  8. which closing cash Methods 3/5 use (cash_bs used);
  9. bare_figures vs the `{T2E.x|US$ m}` syntax;
  10. T2E.6/7 columns not pinned.
- LEAD Stage 2 notes recorded: the T4.13 consumers; a stale head re-raises at begin.
