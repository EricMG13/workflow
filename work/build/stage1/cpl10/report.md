# CP-L10 Stage 1 report (agent text; written by the controller because the host refused the agent's write)

- Branch `worktree-agent-aa6ef474a0f78ec9e`, commit `f4f3f8f`, base 509f7db. Files: `owners/__init__.py`, `owners/cpl10.py`, `tests/test_method_cpl10.py`.
- Surface: bind_operands, screen_topic, rank_key, screen_pair, view_topics, pair_screens, validate_screen, change_screen -> ScreenResult (table/row/claim records; no product Module, per F1), shown_text.
- Inputs: Run issuer_name/as_of; CP-0/CP-1 status word and result sha (F3); 28 CP-1 T4.10 facts by the selection rule (exactly one each); judgment fields.
- Test: 34 passed in 0.26 s. Gates 0. gates-first-pass=n. Mutation spot check: 7/8 killed; the survivor is case-insensitive prohibited-word matching, which the oracle does not pin.
- Covered:
  - composer and rank fixtures;
  - the positive and limited cases (topics, counts, status);
  - every fact cell for cell;
  - TL10.1–TL10.4 except the pending rows;
  - claims except the pending ones;
  - own limitations except the Gap lines;
  - view_topics with amount_exact (F2) and the six pair screens;
  - refusals r01–r12.
- Pending amendment 1 (not asserted): TL10.2 total → TL10.5; the full TL10.3 overall row; TL10.1 source_ref/scope_status (implemented per F3, not asserted); summary/overall claims; F5 citations (not implemented); F4 rules beyond "High not allowed"; Gap limitation lines.
- Left to Stage 2/4: settled and inherited limitations, the blocked/refused cases, tool use, the view hash/tree, tamper, upstream/module/submit/reader, render, the D4 methodology edit, D8.
- Engine/oracle disagreements: none.
- Unpinned choices: the scope of text-check binding; the to_period wording; the confidence template for values other than High; per-assessment check order; case-insensitive prohibited words.
- The amendment-1 rulings file was not found in git; the work followed the controller's summary.
