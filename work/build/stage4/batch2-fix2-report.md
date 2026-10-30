Fix round 2 is done: the CP-8 module table and inspector no longer show the raw token. Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-abd740dfc43433f04, branch claude/s4-batch2-fix2, tip 35809c2 (based on e37b73e, confirmed). The tree is clean and the .venv link is removed.

**Change** (commits 119b20b RED, d394ac1 GREEN, 26a78ca and 35809c2 manifest, 6cd1a88 lint)
- **RED, `tests/test_connect_cp8.py`:** two new tests read the `report-data` payload.
  - `test_the_module_table_and_inspector_spell_the_outcome_as_the_block_does` checks that `cp8.what_changed.outcome.value` has `display` and `table_display` with no `[`…`]`. Both must spell `∅ G26` and equal the what-changed block line.
  - `test_a_known_window_figure_is_spelled_in_the_module_table_as_the_block_does` is the positive control: "Window 109 days after the decision."
  - Both failed at e37b73e because the token survived in the payload.
- **GREEN, `src/deploy_vii/render.py`:** in the module-fact loop, a known text fact for which `_carries_reference` is true gets `display` and `table_display` from `resolve(fact.text, prose.bind(module.facts), module_refs(...))`, with the run texts joined. `_carries_reference` is imported from `report_view`, not copied. There is no try/except, so a malformed mix or a foreign token fails closed. Every other fact keeps its spelling.
- **Manifest:** the `render.py` patch record (item 45) went in at first as the last entry of the wrong list. D12 flagged it MISPLACED, so I moved it into `post_import_patches` in 35809c2.

**Step 3 scope list**
- Probe: `<S>/batch2-fix2/probe_scope.py`, where `<S>` is the brief's scratchpad directory.
- The only rendered known text fact with a token is CP-8 `cp8.what_changed.outcome.value`. It appears in the cases/cp8-owner oracle and in the connect view, and it is the intended change.
- The probe also matches `{{PLACEHOLDER}}` template literals in `cases/cp5-owner/expected.json` (21 facts, e.g. `T5.1.r00N.bound_*`, `T5B.1.r013/r014.upstream_refs`) and `cases/cpl10-owner/expected.json` (4 facts, `TL10.1.cp*.…`). These are unsubstituted oracle templates, not rendered facts. I did not check whether the cp5/cpl10 owner builders substitute every one before render. Those owner suites are not in the fast set and I did not run them.

**Gates**

| Gate | Result |
|---|---|
| `probe_e_report_data_payload.py` | exit 0, a few seconds; the only survival is the stored `facts[150].text`, block bound to G26 |
| 14 render suites, `-m "not genuine"` | all exit 0 (run as 14 parallel processes) |
| `ruff check` and `ruff format --check` on `render.py` and `test_connect_cp8.py` | exit 0 |
| `MYPYPATH=src mypy --strict src/deploy_vii/render.py` | no issues |
| suppressions | `noqa` 13, `type: ignore` 5 |
| D12 strict probe | exit 1; the only failures are `3e5b537` and `24f879a` (item19=BAD) and `8aef58d` (chain=GAP) |

- **Render suites:** passed counts are 7, 11 (+1 xfailed), 10, 7, 56, 104 (+1 skipped), 61, 682, 14, 36, 90, 79, 622 and 22. All finished in 6 s or less except `test_financial_render`, which took 3042 s. That slow run is not caused by my change, since its 22 tests don't touch the token path, but I did not time it at e37b73e.
- **Repo-wide ruff:** `ruff check src tests` reports many unrelated pre-existing ISC004 findings (e.g. `canonical_audit.py`). I did not touch them.

**Not verified:** the DOM, since `app.js` was not run in a browser; `tests/test_owner_cp8.py` and the other owner suites (deferred); the cp5/cpl10 placeholder substitution described above; mutation and property gates; the full suite; `test_financial_render` timing at e37b73e.

Ledger: `agent=mx-feature fix-rounds=1 gates-first-pass=n` (the first manifest placement and one ruff FURB167 finding were fixed before the final run).
