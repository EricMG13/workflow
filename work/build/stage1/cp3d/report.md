# CP-3D Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `claude/cp3d-stage1`, commit `a80aa23`, base f2cd61f. Files: `owners/__init__.py`, `owners/cp3d.py` (1,583 lines after format), `tests/test_method_cp3d.py`.
- Built:
  - `MarketImpliedSubmission`, `MarketContext` (pages, names, third_party, per-page Published dates, run as_of), `MarketInputs`, `inputs_from_submission`;
  - `compose -> Derived` (28 digits half-even, with unrounded intermediates; stored half-up: years 0.01, bp 0.1, probability and yield 0.0001; recovery 0.7 per D11);
  - `submission_issues` (19 mutations, plus bid>offer and different dates);
  - `market_implied_result` (T3E.1–T3E.9, the claims LVL/DM/YLD/PD/VIEW-01, own limitations);
  - helpers.
- Inputs: no manifest fact_bindings. The operands are submission quotes on CP-0 third_party pages plus the financial page:5 terms; recovery is judgment. The full table is in the agent's text.
- Test: 46 passed in 0.23 s. Gates 0. gates-first-pass=n. There are no type: ignore, noqa or fmt: skip markers.
- Covered:
  - three pack cases, field by field;
  - missing_not_zero, claims, own and inherited limitations;
  - 5 fixtures and 19 refusals;
  - blocked_cp3d issues;
  - consumption.reader_pinned_for_cp3c positive values;
  - synthetic tests for bid>offer, the yield path and a missing Published date failing closed.
- Left to Stage 2/4: tool_use(_refusals)/RULES, case metadata, the CP-0 run facts, the claim_literal_text prose probe, execution/tamper/probe, render/table_id_check, cp3d_reader.
- Engine/oracle disagreements: none.
- LEAD points:
  1. The terms/talk period is built from the cited page's "Published" date (the builder hardcodes it), and it fails closed if no date is given.
  2. Claim dates come from the submission, not the builder's hardcoded or index-based values.
  3. A missing quote reports the existing "does not occur in the quote" wording; the lease does not cover this.
  4. Module status (always restricted) is left to Stage 2.
- Not verified: Stages 2–4, the period rule beyond the oracle's two pages, complexipy, and Decimal.exp precision beyond 0.0001.
