# CP-4 Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `worktree-agent-a137244cd727ee164`, commit `4c6fa03`, base 509f7db. Files: `owners/__init__.py`, `owners/cp4.py` (MARKERS, markers_in_scope, semantic_issues, Cp4Inputs, Cp4Result, compute), `tests/test_method_cp4.py`. `src/deploy_vii` was not edited.
- compute runs the semantic gate, then `cp4_legal.validate_covenant_interpretation`, then `covenant_interpretation`.
- The test builds `Upstream` from oracle values (ruling 2). The stand-ins are test-only: head hashes, the CP-1 fact/calculation/row ids, one CP-1 citation, CP-1 limitations.
- Test: 20 passed in 0.35 s. Gates 0. gates-first-pass=n (one unused variable).
- Covered:
  - positive/gap CP-4: 31 tables in order, claims, own limitations, attempt and settled inputs, python_values, source_context_only;
  - run-time-bound cells by rule (11 positive, 9 gap);
  - semantic_gate per_case, plus a page-text scope test;
  - gap_false_same_definition refusal plus the corrected resubmission;
  - the FIG predicate;
  - the cp4_step_view key tree;
  - the unresolved-FIG refusal.
- Engine/oracle disagreements: none.
- Review points:
  1. The gate scope skips a cited page that is absent from the pack (the engine refuses such a citation later).
  2. The page-text scope is exercised only by the added test.
  3. Extra public helper `markers_in_scope`.
  4. Double validation.
- Left to Stage 2/4: cp4_upstream over real heads, view/probe/precheck, settled and inherited limitations, execution, receipt/replay, tool-use/tamper, render, D8.
