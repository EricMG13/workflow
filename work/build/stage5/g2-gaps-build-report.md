Built the G2 coverage-gap rules. Every gate you named exited 0, including both genuine cases. Only `tests/test_owner_rendering.py` changed.

Worktree: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a543732f3e37355b5`
Branch `claude/s5-g2-gaps` from `e37b73e` (tip confirmed at checkout). Tip is `715f5a4`. The `.venv` link is removed and `git status` is clean.

**Commits**
- `3090359` (cites normaliser and cp3d tables): the helpers `_registers`, `_page_cites`, `_resolve_cell_fact`, `assert_table_cites`, `assert_cells_cite_oracle` and `assert_cp3d_tables`.
  - `_page_cites` has no fallback and uses the required-entry rule from Revision 1. It carries the comment on the strict-parse G# branch for (T4.9, threshold).
  - For s1a, the expected `calculation_id` comes from the store (see Decisions).
- `778fbb3` (cp4 pointers): `assert_cp4_pointers`.
  - It checks section tables, `displayed_literals`, the `gap_false_same_definition` values, the rail subset, and cites.
  - The limitations rule follows the oracle text word for word, using the store's CP-1 head.
- `715f5a4` (cp8 lines and rails, wiring): `_visible_line_text`, `assert_cp8_lines`, `assert_rails_cp3d` and `assert_rails_cp8`.
  - `_check_scope_run` now calls `_assert_secondary_pointers` for complete outcomes.
  - Rails limitations use the order own, SYNTH, inherited, and the test asserts the oracle's inherited list contains SYNTH.

**Fast tests**
- Each rule has one accept test on real fast pages and one set of one-field perturbations.
- Each accept test asserts at least one item was checked, so none can pass vacuously.
- Every perturbation fails with `AssertionError` only. I narrowed `_assert_rejected` to that, so a KeyError or StopIteration from a broken page cannot count as a rejection.
- Tests added: `test_fast_cp3d_tables_rule_on_real_pages`, `test_fast_cp4_pointer_rule_on_real_pages`, `test_fast_cp8_lines_rule_on_real_pages`, `test_fast_cp8_lines_gap_run_label_is_the_column_with_its_colon`, `test_fast_cites_normaliser_on_s1a_page`, `test_fast_cites_normaliser_on_real_cp3d_page`, `test_fast_rails_rule_on_real_cp3d_pages` and `test_fast_rails_rule_on_real_cp8_pages`.

**Gates (exit codes)**
- `-k fast`: 0, 170 passed in about 15 s.
- `ruff check`: 0.
- `ruff format --check`: 0 (the file was left unchanged by the last format run).
- `MYPYPATH=src mypy --strict`: 0.
- Suppressions: `noqa` 13 and `type: ignore` 5, both at the baseline, none added in this file.
- Genuine `cp3d-fp03-market-positive`: exit 0, 1 passed in 1.76 s. This is far shorter than the brief's 11 to 26 minutes.
- Genuine `s1a-credit-snapshot-positive`: exit 0, 1 passed in 1729.99 s (28:49). The s1a run exercises the store-derived calculation ids and the real passport numbering.
- I ran them one at a time. No background process is left running.

**Decisions to confirm**
- For s1a, `calculations` is built from every head module in the store, keyed by `(module_id, fact_id)`, not only the CP-1A head. It is a superset, so the lookup cannot raise a KeyError on a cell that resolves to another module.
- I added a fast check that a known uncited fact with a `calculation_id` gets a K# entry. With the store's `calculation_id` the check accepts the page. With an assumed None it is rejected.
- `_assert_rejected` asserts the perturbation list is non-empty.
- Fast cp4 and rails tests use a test-only CP-1 head, because fast pages have no store. The genuine run takes it from `store.head_module`.

Not verified: the other eight genuine ids and `test_genuine_deferred_refused_cases[cp8-fp01-what-changed-no_record]`, which the controller runs on the integration branch; the genuine cp4 CP-1 store head, the genuine cp3d and cp8 rails and settle-built limitations, and the real K# calculation passports on genuine cp8 pages; `complexipy`, `jscpd`, `bandit` and the full suite; mutation and property tests.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y (the affected fast tests and the two genuine ids ran and exited 0 on the first run of the wired code; the only red-to-green iterations were the test-first reds and one mypy typing fix before commit).
