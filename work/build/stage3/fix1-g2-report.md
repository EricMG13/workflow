F1 (G2 owner_rendering): two of three findings are fixed and the fast gates pass. The genuine run for the new row FAILED, and the failure is outside G2.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a66d44aeb0c45fc3a
Branch claude/s3-fix1-g2, based on 18dc1fa. Tip is ee95ffb (3 commits: 83bb3de, 011dc35, ee95ffb).
Files changed: src/deploy_workflow/owner_rendering.py and tests/test_owner_rendering.py only.

**Changes**
- **Arch M1 (cp3c-fp04-refinancing):**
  - Tests were written first and the scope test went red.
  - Added the row with the lease tuple, the sections funding-gap, refinancing-paths and lme-creditor-exposure, and the complete-only banner. It sits after cp2d in `_DELIVERY_ROWS`.
  - Dropped it from `GATED_IDS`. The cp6-fp01-committee gated test stays.
  - New tests:
    - A lease-row parse test.
    - A `_cr3_figures` loader with `FIGURE_CASES` for positive, gap_minimum_cash and gap_no_repricing.
    - A real-page CR.3 test over the three cases.
    - The cr3 oracle pointers.
  - Item 7 is checked by `assert_funding_gap_heads` (CP-2D for cp2d, CP-2D plus CP-3C for cp3c), with accept and reject cases.
  - Added a genuine `_cp3c` adapter and DEFERRED entry, plus `_assert_cp3c_blocks`. It checks the funding-gap block against cr3 and the other two blocks against `cp3c-owner#/fp04_render`.
  - I did not add the row to `ORACLE_POINTERS`: `fp04_render` holds only the two CP-3C blocks, so `_block_nodes` could not find all three sections.
- **Precise M1 (DR.6 suffix):**
  - `_assert_reason` requires the oracle text exactly.
  - A gap case may add only ` (∅ G<n>, …)` with distinct refs, and every ref must be a `gap_ref` in the block's own cells. A positive reason takes no suffix.
  - Gap or positive is read from the dr6 `reference` field.
  - The real DR.6 gap page cites G23 to G34 and passes.
- **Precise L1 / arch L2 (S.4 title):**
  - `title_prefix` is replaced by `title_pattern`, set to the ruled regex via `re.fullmatch`.
  - A new test compares the title exactly on the FP-04 fixture, using the real `maturity-wall` block from `test_chart_render_s4fp04`.
  - **Deviation:** the composer fixture behind `test_fast_figure_rule_on_the_real_s1_to_s4_strip` (`tests/test_cp1_chart_render.py:150`) spells S.4 "current principal". The producer (`financial_series.py:212`) and the ruled regex say "principal at", so the regex fails on that fixture. I compare that fixture's title exactly (stricter than the regex) via `_real_check(exact_titles=…)`. That file is out of scope.

**Gates**
- `ruff check` exit 0 and `ruff format --check` exit 0, on both files.
- `mypy --strict`: exit 0 on both files with `--follow-imports=silent` ("no issues found in 2 source files"). Without that flag it exits 1, with 61 errors, all in the imported `tests/test_cp1_chart_render.py`.
- `tests/test_owner_rendering.py -k fast`: 151 passed, exit 0. `test_chart_seam`, `test_chart_render_cr3` and `test_chart_render_dr6`: 77 passed, 1 xfailed (the existing DR.6 chip tripwire), exit 0.
- Suppressions: noqa 13 and type-ignore 5, both at the limit and unchanged from 18dc1fa.
- **Genuine test FAILED** (`-k "test_genuine_deferred_complete_cases and cp3c-fp04-refinancing and positive"`): exit 1, 199.85s.
  - It stops inside `tests/cp3c_runs.py` `reach_cp2d` → `s1a.read_cp2` → `workflow.read_inputs()`, which raises `WorkflowError: not_permitted`.
  - G2 is never reached, so the new row's genuine path is unproven.
  - I did not touch the driver. That file's own docstring says it was never run before Stage 5.
- **Probes:**
  - `p2_cp3c_scope_refused.py` exits 1 by its own convention, meaning the triple is now matched (`cp3c-fp04-refinancing`) and no longer refused.
  - `probe_g2_title_and_reason.py` could not run as written: it uses the removed `title_prefix` field. I ran an adapted copy, `probe_g2_title_and_reason_fix1.py` in the reviewer's scratchpad `precise/` directory. It exits 0, with all three forged inputs refused.

**Not verified:**
- The genuine run of any cp3c case, including the `_assert_cp3c_blocks` and `assert_funding_gap_heads` calls on real settled output. The driver fails first.
- The other two cp3c cases (`gap_minimum_cash`, `gap_no_repricing`).
- That a genuine page's CP-3C funding-gap facts are bound as I expect.
- The producer-form S.4 title against the ruled regex on a genuine cp1-model run.
- The original probe file, which is stale against the new API.

ledger: agent=mx-feature fix-rounds=1 gates-first-pass=n (genuine cp3c run fails in the driver; fast gates passed)
