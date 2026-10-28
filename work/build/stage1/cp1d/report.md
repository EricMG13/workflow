# CP-1D Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `claude/cp1d-stage1`, commit `b6d83ae`, base 509f7db. Files: `owners/__init__.py`, `owners/cp1d.py`, `tests/test_method_cp1d.py`.
- Surface:
  - `parse_bridge(pages) -> Bridge | None`, `validation_issues(inputs)`;
  - `compute(inputs) -> EarningsQualityResult` (facts, T1D.1–T1D.7, cp1_references, claims, own limitations, operands, unavailable operands, bridge_source), which raises on any issue;
  - schema contracts EarningsQualitySubmission, Assessment, Overall and Gap.
- Inputs: pack sources (identity, financial, bridge); CP-1 T4.10 LTM Q4 25 figures (adjusted_ebitda, ebitda, cfo_adjusted, total_debt, net_debt, total/net leverage adjusted); judgment (assessments, overall, gaps); the cp1b binding status.
- Test: 39 passed, 1 skipped (Stage 2/4 marker) in 0.29 s. Gates 0. gates-first-pass=n.
- Covered:
  - positive/statements_only/gap: facts, tables, refs, claims, limitations, operands, bridge_source;
  - FP02 cells;
  - lineage_rule;
  - the analyst_fraction fixture;
  - refusals r01–r19;
  - blocked r06;
  - cp1b lines;
  - bridge parse fixtures.
- Left to Stage 2/4: cases.refused, tool_refusals t01–t03, blocked-head settlement, module status, settled and inherited limitations, cp1_readiness, execution, D3, D7, D8, overall prose {{FIG}} binding.
- Engine/oracle disagreements: none.
- Confidence review: two defects fixed (rationale references to module totals; basis citation now uses the analyst's located citation); a currency is now required.
- LEAD points (fail closed):
  1. lineage_rule text vs oracle citations (oracle followed);
  2. Partly supported + Recurring is unspecified (raises);
  3. EBITDA <= 0 has no status or text (raises);
  4. a bridge type other than Saving or Cost is refused;
  5. bridge parse strictness;
  6. the one-sided T1D.4 tie-out formula;
  7. a basis on an unstated amount skips shape step 6.
- Not verified: Stage 2 runs, {{FIG}} binding, RULES/Seen, blocked settlement, FP02 rendering, CP-1B inherited lines, non-positive EBITDA, Partly supported + Recurring, a basis from a non-bridge source.
