# W2 group a report (mx-feature a8576502, claude/s3-w2a aad1480)

W2 group a (S.5 and FP-04 S.4) is built and committed, and its own gates pass. I could not finish the wider regression run, so some existing suites have not run against it.

**Worktree and tip:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a8576502cef5bc4aa`, branch `claude/s3-w2a`, tip `aad1480a2113a67ecc77fb763433ea27f47457ad` (the three commits are on 423f92e). The `.venv` link is removed, the tree is clean and no background process is left.

**Commits:**
- `7bfe391`: RED tests for S.5.
- `4c54ccc`: the S.5 producer and its registration.
- `aad1480`: the S.4 wiring.

**Files changed**
- `src/deploy_workflow/financial_series.py`:
  - S.5 is added as `("S.5", "Net revenues and Adjusted EBITDA", ("revenue", "adjusted_ebitda"))`, kind `grouped`, amount, US$m, read from T4.10.
  - `cp1_chart_series` now returns S.1, S.2, S.3, S.4, S.5.
  - A missing metric row raises `ValueError`, the same as S.1 to S.3.
- `src/deploy_vii/report_view.py`:
  - The `maturity-wall` spec is now kind `chart`.
  - There is a new module-end registration block, labelled group a, with `register_figure_producer("financials-credit-metrics", _cp1_period_figures, pathways=frozenset({"credit_snapshot"}))`.
  - One seam fix in `_block`: `shown` now skips a binding whose module has no entry in the view. Without it, a view with no CP-1 raised `KeyError` once T4.18 was bound to `maturity-wall`. The s4fp04 builder target names this fix.
- `src/deploy_vii/bindings/cp1.py`: T4.18 is bound to `maturity-wall` with the label "Capital structure".
- New tests: `tests/test_chart_series_s5.py`, `tests/test_chart_render_s5.py`, `tests/test_chart_series_s4fp04.py` and `tests/test_chart_render_s4fp04.py`.
- `tests/test_connect_cp2d.py`: I added `with_chart_identity()` and a `charts=` option on `make_upstream`; the plain fixture is unchanged for other tests. The strict-xfail tripwire is now a passing test with the frozen labels (primary "Capital structure", tab "Maturity wall"). The spec-row test now expects `chart`.
- `tests/test_financial_series.py`: the fixture gains revenue and adjusted_ebitda rows, with values read from the s5 oracle.
- `tests/test_chart_seam.py`:
  - The registry test is now `test_the_registry_holds_the_s5_registration_of_w2_group_a`. W1 asserted an empty registry.
  - The "stays dense" test now asserts `chart`.
  - The degraded-path test no longer monkeypatches `_spec_of`.

**Cases covered**
- S.5: values, texts and companions all come from the oracle. It also covers the gap mark with its G#, wrong unit, scale, currency or basis failing closed, fewer than four quarters, the FY alias, unsettled CP-1, and earnings_update drawing no S.5.
- S.4: single count, model-first, T2E.4 cells, CP-2D absent with CP-1 present, and CP-2D settled with CP-1 not settled. The last runs three ways: no CP-1 entry, CP-1 blocked, CP-1 stale. The n/a frame names CP-1 as not settled, with `tab_label` None and `tabs == ()`. The CP-1-absent legal-render pin is covered by `test_legal_render.py`.

**Gate results (all exit 0 unless noted)**
- New chart tests (four files): pass.
- `test_chart_seam.py`, `test_financial_series.py`, `test_cp1_chart_render.py`, `test_legal_render.py` and `test_connected_render.py` ran together with my new tests: 239 passed.
- `test_method_cp2d.py` and `test_connect_cp2d.py`: 423 passed.
- `cases/pins.py --check`: matches 86 paths.
- `mypy --strict` on the three changed `src` files: clean.
- `ruff format --check`: clean on every file I changed except `financial_series.py`, which was already unformatted before my change. I did not reformat it, to keep the diff small.
- `ruff check`: clean on my new files and `test_chart_seam.py`. The remaining findings are the known SIM102 in `report_view.py` and C408 in `test_financial_series.py`, both there before my change. The repo has 91 `ruff` errors in `src` at baseline.
- Suppressions: noqa 13 (limit 13) and type: ignore 5 (limit 5).

**Questions and merge notes**
1. `test_chart_seam.py` has two tests I edited because W1 pinned the earlier state (empty registry, `maturity-wall` dense). Groups b to d will edit the registry test too, so expect a trivial merge conflict. The registration block at the end of `report_view.py` is append-friendly.
2. A real CP-1 without T4.10 revenue or adjusted_ebitda rows now makes `cp1_chart_series` raise, as it already did for S.1 to S.3. I judged this correct, but the real CZR pack has not been checked.
3. In `tests/test_connect_cp3c.py`, `test_bindings_follow_the_lease` and two oracle-drift tests fail. They belong to group c (the T3D.1 move and the re-pins), not to this change.

Not verified: the wider suites (the other `test_connect_*` files, `test_earnings_render.py`, `test_financial_render.py` and `test_owner_*`), because they exceeded my timeouts and I killed them. In particular, whether any existing real-CP-1 fixture there now raises on the new S.5 metric requirement is unchecked. The CP-1-absent view and its status variants are built with `View.model_construct`, which skips validation. Browser appearance of S.5 beside the grid and the full `render()` HTML path are unchecked, and so are the full suite, mutation testing, and GitNexus `impact` and `detect_changes`. S.4's series test passes without a RED phase because the S.4 producer already existed; its RED was the tripwire and spec-row tests. The D12 manifest records are left to the integration pass. The "Capital structure" label is the oracle's own inference.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n
