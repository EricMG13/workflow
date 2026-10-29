## Third G2 failure: `deferred_complete[s1a-credit-snapshot-positive]`

The product is right; the fault is in the test's block rule. I found it from the pytest-2291 store and fast fixtures, without rerunning anything. The same rule will also crash or fail in 9 more scopes.

### 1. Root cause
- **What S110 is.** It is a run of kind `fig` whose `ref_id` and text are both "S110". That is the synthetic-provenance chip (S prefix, `src/deploy_vii/report_view.py:62`). For a text fact that has a ref, the producer adds it as a second run (`report_view.py:1624-1626`). It is not a source chip.
- **What the oracle pins.** The oracle keeps the chip out of `text` and records it as a flag: `synthetic_ref: true` (built from `cites`, `cases/snapshot/builder/build_s1_oracle.py:739`; lease body Acceptance 1: "`synthetic_ref` = S provenance").
- **Separate fields.** Lines have no separate sources field. Cells carry `cites` and `synthetic_ref`, and no test asserts either one.
- **Why it fails.** `_line_text` (:1996) joins every run with `""`. On the genuine page, 19 transaction-summary lines carry an S chip, and all 19 fail. Those are exactly the 19 oracle lines with `synthetic_ref: true` (probe 3, exit 1).
- **Joining.** The page itself joins Front Page runs with a space (`src/deploy_vii/assets/app.js:251`, `:263`).

### 2. Other assertions that will fail (`assert_block_equals_oracle` :1999-2015)
- **(a) s1a gap case.** Gap lines are two runs, `"Date / window:"` and `∅ G7 …` (`report_view.py:1618-1621`). The oracle line text is `"Date / window: ∅ G# n.m."`. It fails twice: the runs are joined without the space, and the oracle's `G#` is a placeholder for the page's number. This is a static reading, because there is no gap store.
- **(b) Seven scopes: cp1c, cp1d, cp2a, cp2g, cp2g-gap, cp2h, cp4c.** Their oracle tabs are `{label, table_id, rows}`, and `tabs[0]` is the primary tab. The rule reads `want["tab"]`, which raises `KeyError: 'tab'`. Probe 5 shows this on the real rv3 (cp1c) and dr (cp4c) fixture pages. The labels line up only as `[tab_label, *tabs]` against the oracle's `tabs`.
- **(c) cp3d and cp8.** At `/render` the node's `primary` is a string, and cp8's `lines` is a prose string. `oracle["primary"]["tab"]` raises a TypeError (probe 5).
- **(d) cp4.** It passes, but checks nothing beyond owner and kind: its `tables` and `source` fields are not compared.

The rest of `_check_scope_run` ran clean for s1a before :2014, and the product enforces the same section, model and rail rules. The scopes cp3, cp3c, cp2e, cpdr and cpl10 have no `ORACLE_POINTERS` entry, so they skip this rule.

### 3. Fix plan (test only, `tests/test_owner_rendering.py`, append to round 3)
1. **`_line_text(line)`.** Drop the S chips, meaning runs with kind `fig` whose `ref_id` matches `^S\d+$` and whose text equals the `ref_id`. Join the remaining runs with `" "`. In the line loop, also assert that whether a chip is present equals `bool(want.get("synthetic_ref"))`.
2. **Gap placeholder.** Add a placeholder-aware compare: split the oracle text on `∅ G#`, `re.escape` each part, join the parts with `∅ G\d+`, and `fullmatch`. Use it for line text and for the known-cell branch of `_cell_ok`, so oracle `shown` values such as `∅ G# n.m.` match the page.
3. **Tabs.**
   - Where the oracle has `primary`, keep today's rule.
   - Otherwise, compare `[(tab_label, rows), *((t["label"], t["rows"]) for t in tabs)]` with `[(t["label"], t["rows"]) for t in oracle["tabs"]]`, using `strict=True`.
4. **Render-node oracles.** In `_check_scope_run`, for cp3d, cp4 and cp8, assert `owner`, and `kind` where the oracle has it. For cp3d, also assert that the tab labels equal `[label for _, label in node["tabs"]]`. Do not run the generic rule on these three.
5. **RED test.** Add one fast test that runs the rule on a copy of the pytest-2291 s1a payload pattern: one line with an S chip, one gap line and one tabs-only oracle. It must fail on ee95ffb and pass after the fix.
6. **Gates.** `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on the test file; `-k fast`; then the genuine deferred run.

Probe 6 runs this candidate rule with no failures over 903 checks: the genuine s1a positive page (146), cp1c on fixtures (258) and cp4c on fixtures (499).

### Rulings needed
- **(i)** For cp3d, cp4 and cp8, the lease (R2.5) says the block tree is asserted at secondary pointers: `#/cases/<c>/tables`, `displayed_literals`, and `lines_positive` with `#/cases/<c>`. No test asserts any of them today. Modules should rule whether round 3 checks only owner, kind and tabs (plan step 4) or adds those checks. Adding them would need a preparer to state what "equal" means for each.
- **(ii)** The lease asks for a cites normaliser (body Acceptance 1), and no test has one. Modules should rule whether that stays deferred.

No oracle change is needed.

### Probes (all in `<S>/g2-rca/`)
- `probe3_s1a_blocks.py`: exits 1, reproducing the failure.
- `probe4_oracle_survey.py`: a survey of oracle shapes.
- `probe5_block_rule_on_fixtures.py`: runs the ee95ffb rule unchanged and reports the crashes. It is report-only and exits 0.
- `probe6_candidate_rule.py`: exits 0.
- `test_ee95ffb.py.txt`: a copy of the ee95ffb test file that probe 5 reads.

Not verified: no gap-case store exists, so the s1a gap lines and the cp1c/cp4c behaviour come from code reading and fast fixtures, not genuine driver runs. The cells of cp1d, cp2a, cp2g and cp2h, cp3d's tab labels, the figure checks after the block rule for every scope except s1a, and `verify_owner_rendered_slice` were not exercised.
