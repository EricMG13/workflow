# CP-3 Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `claude/cp3-stage1`, commit `6ce4dd1`, base 509f7db. The oracle hashes equal the LEAD freeze.
- Files: `owners/__init__.py`, `owners/cp3.py`, `tests/test_method_cp3.py`. `src/deploy_vii` was not edited.
- Design: no new arithmetic (the lease adds none). There is one typed input object. The engine's `Upstream` is built directly, with no store.
  - `compute -> CP3Result(issues, report)` validates, then composes.
  - `context(inputs)` is separate, so it cannot hide a validation result.
  - `candidate` wraps `cp3_module` and raises on a refused result.
- Inputs: pack, submission, bound/current inputs, the CP-0/CP-1/CP-2 heads, optional CP-1A and inherited limitations. Stage 2 sources are listed in the agent's text.
- Test: 31 passed in 0.37 s. It failed first. A one-cell oracle mutation fails the test. Gates: ruff 0, format 0, mypy --strict 0. gates-first-pass=n (format and import order).
- Covered: positive/gap CP-3 (7 tables cell by cell, cp1_references, pinned spellings, claims, own limitations, catalogue_for_CP-6, module_inputs, context checks), the blocked_cp1a_variant, and all 10 validator refusals. Extra test: a stale `current` refuses.
- Left to Stage 2/4: settled and inherited limitations, real run_time_bindings, upstream head checks, render, tool-use/tamper refusals, execution, receipt/probes, H1 session scope, and CP-6 (not frozen).
- Engine/oracle disagreements: none.
- Remaining limit: the blocked variant uses S1 positive CP-2 rows, not an A3b head.
- Not verified: real CP-1 fact ids, labels and periods (the test chose them); the blocked CP-1A limitations; real current_inputs; Stages 2–4.
- Review routing: there is no arithmetic in the diff, so no mx-adversary pass; it goes straight to the Stage 1 Fable review.
