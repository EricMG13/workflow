# Release W2-D report (mx-feature)

Lane D is done. Branch `claude/s2r-d`, tip 291fa8e, cut from fb231d4, tree clean. One commit.

(EnterWorktree was not available in this session, so I worked by absolute path in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-d`.)

**Per item**
- **CP-2H own citations (round 3):** done. 17 literal citation lists now keep one citation per page, the first input quote. These are T2R.8.p01 notches, lower_rated and outlook_match, T2R.9.total triggers, downgrade_down and not_calculable_down, across positive, gap and the fixtures. The first test failed on the old code. Changes are in `cp2h.py` `lineage` and the builder `lineage`, plus the `cell_notation.citations` text. Upstream citations already followed the rule.
- **CP-1C citations:** done. 107 calculated-fact lists (the T1C.4 facts) are reduced, and the `lineage_rule` text is restated. `cp1c._with_lineage` applies the rule. The run-time test with a CP-1 citation now expects 2 citations, not 5.
- **CP-2G citations:** done in the core (`_cite`). The oracle pins no citations, so only the `lineage_rule` text moved. `test_method_cp2g` now checks the rule through the first-quote result (debt, not debt and cash).
- **CP-4C citations (review-A L1):** done in `_Book.cells`. The oracle pins none that change, so only the `lineage_rule` text moved. The method-test oracle helper now applies the rule.
- **CP-1C `rules.direction`:** done in `expected.execution.tool_use.CP-1C.view`. It now names `direction`, matching the view and the lease key tree.
- **CP-2G blocked limitations and xfail:** done. `cases.blocked.attempt_1.limitations` is now `[assessment.rationale: Unresolved reference: T1D.6.supported.total_leverage, <High line>]`. The strict xfail is removed from `test_owner_cp2g`. The fast connect test now asserts the oracle on the `blocked` run and the oracle minus the first line on the `positive` pack. This is the fast-form test only, because the owner test is deferred.
- **CP-2G scenario name:** done. The manifest `upstream_fact_selection.CP-2A.scenario` now names `T2B.1.<row>.name`. The lease text itself is B's.
- **CP-4C v08:** done. The oracle `refusals[v08]` gains `unread_issues` (`Cited page not read through read_pages: identity page:1`), and `refusal_rules.journal` says so. I removed the `UNREAD_AT_RUN_LEVEL` pin from `test_owner_cp4c` and the hard-coded line from `test_connect_cp4c`. Both tests now read the oracle. `expected_issues` is unchanged, so the validator-level tests are unaffected.
- **CP-4C mutants (backlog :57-62):** already pinned at fb231d4 at `test_connect_cp4c.py` :119-195 and :205-229. Running them on a scratch copy killed `\d` in both patterns, the unescaped dot in the d01 pattern, the hard-coded `base_period("s03")` and `base_period` returning None. Two findings:
  - The unescaped dot in the d02 pattern survived, so I added 3 test cases (T2BX1, 1X, sXinterest) and it is killed.
  - `\d` in only one pattern is an equivalent mutant, because the other pattern still refuses. The test docstring records this.
- **View trees:** committed `cases/{cp1c,cp2g,cp2h,cp4c}-owner/<cp>-view-tree.json`, each holding top-level keys plus a shape-only tree per case.
  - CP-1C: positive, gap, no_peers. CP-2G: positive, gap, cp1d_blocked. CP-2H and CP-4C: positive, gap.
  - The shared helper is `tests/view_tree.py`.
  - A fast connect test per module checks the file against `view` over a real store. A line in each owner test checks the genuine run body.
- **Method notes:** `src/deploy_vii/methods/{cp1c,cp2g,cp2h,cp4c}.md` now state the derived-fact rule, as review-A L1 required, and the view-tree paths.
- **Lease pin headers:** added "Amended by Modules 2026-10-29 (Stage 2 close release W2-D…)" with old to new sha256 for CP1C, CP2G, CP2H and CP4C.

**Oracle values that moved, and what moved them**
- Everything moved only through the named items above. I diffed each `expected.json` structurally against HEAD. For CP-2H and CP-1C, every changed citation list is exactly the first-per-page reduction of the old list. No other frozen value or refusal moved.
- cp2g `expected.lineage_rule` text, `cases.blocked.attempt_1.limitations` (1 line to 2), and the manifest scenario text.
- cp2h `cell_notation.citations` text and the 17 lists.
- cp1c `lineage_rule`, the 107 lists, and the view text.
- cp4c `lineage_rule`, `refusals[v08].unread_issues`, and `refusal_rules.journal`.
- Pin-hash-only changes: the cp2h and cp4c manifests and builders, which pin CP-2G's `expected.json` and `manifest.json`.

**Files changed, for W3 to re-pin**
- Builders: `cases/{cp1c,cp2g,cp2h,cp4c}-owner/builder/build.py`.
- Oracles: `cases/{cp1c,cp2g,cp2h,cp4c}-owner/expected.json`, `cases/cp2g-owner/manifest.json`, `cases/cp2h-owner/manifest.json`, `cases/cp4c-owner/manifest.json`, and `cases/PINS.json` (regenerated, 69 paths).
- New: the four view-tree files and `tests/view_tree.py`.
- Src: `owners/{cp1c,cp2g,cp2h,cp4c}.py` and the four `methods/*.md`.
- Tests: `test_connect_*` and `test_owner_*` for the four modules, `test_method_cp2g.py`, and `test_method_cp4c.py`.
- Leases: `docs/CP{1C,2G,2H,4C}-OWNER-LEASE.md` (headers only).
- I did not edit `docs/reuse/manifest.json`, which C owns. C should add D12 records for `cp1c.py`, `cp2g.py`, `cp2h.py`, `cp4c.py` and the four methods files if they count as reused files.
- Cross-lane pins: the cp2h and cp4c builders now pin the new CP-2G files. W3's full chain should re-run, since no other builder pins files I changed.

**Gates (exit codes)**
- `pins.py --check`: 0.
- `ruff check` on the 15 touched `.py` files: 0. `ruff format --check`: 0.
- `mypy --strict` on the 4 `src` files: 0. It also exits 0 on `tests/view_tree.py`.
- Tests: 2855 passed, exit 0. That covers the connect and method tests for the four modules, plus `test_defect_classes_cp1`, `test_stage2_classes_batch`, `test_host_h1` and `test_cp1b_registration`. The four `test_owner_*` files collect (211 tests) but were not run, because they are the deferred genuine runs.
- `noqa` count is 13 and `type: ignore` count is 5, so both are within the limits.
- Two fresh scratch rebuilds of the 17-builder chain (`fresh_copy.py` plus `chain.sh`) were byte-identical to each other and to the committed `cases/`.

**Rulings and questions**
- No missing rulings. Nothing was skipped or stopped.
- Interpretation call: for v08 I added a separate `unread_issues` key and left `expected_issues` as the validator's one line. The alternative was a two-line `expected_issues`, which would break the validator-level method test.

Not verified:
- The four `test_owner_*` files, including the new genuine-run view-tree checks and the CP-2G blocked-limitations assertion, because they need the 11-26 minute genuine CP-1 promotion.
- The view trees come from fast real stores. Their upstream heads were settled through the product store from oracle facts, not from a genuinely promoted CP-1 head. Shape equality with a genuine run is therefore untested until Stage 5.
- No full suite, `bandit`, `complexipy`, `jscpd` or mutation gates were run. Each core now has its own small `_one_per_page` copy, so a duplication check could notice it.
- No tests apply to the lease header text or to the methods notes beyond the needle checks.
- The order of the CP-1C `rules` keys in the oracle view string is checked by one new test, but not against the lease prose.

agent=mx-feature fix-rounds=0 gates-first-pass=n
