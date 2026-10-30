## CP-1D single-tab block: root cause (item 35)

**Root cause: the G2 test rule is wrong, not the product.** The item 28 tabs-only branch in `tests/test_owner_rendering.py:2075-2081` (at 49628a0) takes the oracle's `tabs[0].label` to be the rendered `tab_label`. That only holds when a block has two or more registers.

1. **Where `tab_label` and `tabs` come from.** CP-1D binds a single table to this block, `_bind("T1D.6", "restated-leverage", "Cash conversion and leverage", ...)` at `src/deploy_vii/bindings/cp1d.py:35`. `report_view` takes the first filled slot as the primary register (`report_view.py:2055`). Its `tabs` holds only the other slots (`:2072`), and it sets `tab_label=primary.label if tabs else None` (`:2094`). The `tab_structure` validator (`:424-428`) forbids a `tab_label` with no further tabs, so a block with one tab cannot exist in the model.
   - The label "Cash conversion and leverage" appears nowhere on the page. An untabbed block shows only `h3 block.title`, here "Cash conversion and restated leverage" (`src/deploy_vii/assets/app.js:410`, `:416`). The page has no tab strip or caption for that label.
2. **What the oracle's single entry means.** It names the block's only register and is a data shape, not a page label. The builder writes every block the same way, as a list of `{table_id, label, rows}` (`cases/cp1d-owner/builder/build.py:424-425`, `:816-824`). The lease says only "`restated-leverage` (tab T1D.6)" (`docs/CP1D-OWNER-LEASE.md:124`). Its Not-verified line (`:154`) left block tabs unchecked.
   - CP-1D's own connect test already settled this reading, as Stage 2 review M2: "A one-table block renders no tab strip, so its one oracle tab label is the binding label of its one table" (`tests/test_connect_cp1d.py:319-340`, which asserts `tab_label is None and tabs == ()` at `:337-338`). The label is already checked there, against the binding.
3. **Which side is wrong.** It is the G2 rule only. The CP-1D composer, the oracle and `report_view` agree with each other. Probe 3 composes FP02 from the connect-test fast fixtures:
   - In all three cases, `restated-leverage` renders `tab_label=None`, no tabs and 3 rows, and fails at `:2081`. That is the same failure as `g2d-0.log`.
   - The rows match the oracle, so only the label comparison is wrong.
   - `earnings-quality` (3 registers) passes.

   The earlier RCA (`g2-genuine-rca-2.md`, probe 6) tested this rule on cp1c and cp4c only, never on cp1d.
4. **Other tabs-only oracle blocks with exactly one tab** (all `cases/*/expected.json`):
   - The only ones are `cp1d-owner` `cases.{positive,statements_only,gap}.FP02.blocks.restated-leverage`. The same cause applies to all three. Shards 1 and 5 show the cp1d gap and positive cases failing too, but those logs are still in progress, so I could not see the assertion.
   - Other blocks with one tab, which this cause does not reach:
     - snapshot `company-profile` and `company-operating-model`: these have `primary` plus one tab, so they render tabbed with two registers and the `primary` branch applies.
     - cp2d `liquidity-runway` and `funding-gap` (`tabs: ["T2E.1"]`, plain strings, with `primary_tab`): `cp2d-fp04-liquidity` is in `ORACLE_POINTERS` but not in `DEFERRED`, so `_check_scope_run` never runs it. It would raise a TypeError on `t["label"]` if it were ever added. That is a separate latent issue, flagged only.
     - cp3c `lme-creditor-exposure`: cp3c has no `ORACLE_POINTERS` entry.
     - cp8 render node: this is a `_RENDER_NODE_SCOPES` scope, which skips the generic rule.
5. **Smallest fix.** It goes in `tests/test_owner_rendering.py` only, inside `assert_block_equals_oracle`, right after `wants = ...` (`:2079`):
   ```python
   if len(wants) == 1:  # one register renders untabbed (report_view tab_structure); label checked in test_connect_cp1d
       wants = [(None, wants[0][1])]
   ```
   - The comparison stays strict and the rows are still checked.
   - Add a RED case to `test_fast_block_rule_handles_s_chip_gap_placeholder_and_tabs_only_oracle`: an untabbed block against a tabs-only oracle with one tab must pass, and a tabbed block against that same oracle must raise.
   - This would be the fourth G2 test change. Item 35 sends that to the user. No product, oracle, lease or `deploy_vii` change is needed.

**Probes**, in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-tab-rca/`. Each takes as its argument a copy made with `git archive 49628a0 src tests cases docs pyproject.toml`. I deleted the copy afterwards to save disk.
- `probe1_single_tab_survey.py`: exit 1 (as designed). Of the tabs-only, one-tab blocks G2 reaches, only the 3 cp1d ones fail, each with 1 binding.
- `probe2_one_page_any_shape.py`: exit 0. A report-only survey of oracle blocks with one tab in any shape.
- `probe3_cp1d_fast_block_rule.py`: exit 1 (as designed). It reproduces `:2081` on the fast fixtures for all 3 cases, and the candidate rule clears it.
- `probe4_proposed_fix.py`: exit 0. It applies the 3-line fix in memory. The existing fast test still passes and all 6 CP-1D blocks pass. It refuses 12 mutants: rows dropped, the other register's rows, a one-tab oracle against a tabbed block, and a two-tab oracle against an untabbed block, each ×3.

Not verified: I ran no genuine run. The rows check comes from fast fixtures composed from the oracle literal, and the genuine failure stopped at the labels, so genuine `restated-leverage` rows, lines and figures are unchecked. The cp1d positive and gap genuine failures (shards 5 and 1, still running) are not confirmed to share this assertion. I added no fast test, and the cp2d TypeError was traced by reading code only.
