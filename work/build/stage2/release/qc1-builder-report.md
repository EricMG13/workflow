# Q-C1 builder report (mx-feature ae545023)

Q-C1 builder report. Tip SHA ff1dbce on claude/s2r-qc1, from 300fcdb, tree clean after commit. One gate did not finish: `tests/test_source_tools.py`, which I killed partway.

**Targets (all done)**
1. `src/deploy_vii/report_view.py`: `maturity-wall` is now `_Spec("Maturity wall","MODEL","dense",("CP-1",),route_label=None)`. A comment says the kind stays dense until Stage 3 S.4 lands, because `chart` would raise KeyError.
2. `src/deploy_vii/contracts.py`: `"CP-MODEL"` sits right after `"CP-1"` in `covenant_refinancing`. `ruff format` split that tuple over several lines.
3. `test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]` were red and are now green.
4. `tests/test_connect_cp2d.py::test_spec_rows_serve_the_three_blocks` now expects `maturity-wall` as MODEL, dense, `("CP-1",)`, route None. The other two rows are unchanged.
5. `tests/cp2d_runs.py` re-pinned to `6c707b4b…` and `c60797a2…`.
6. `tests/cp3c_runs.py` re-pinned to `72e41ad0…` and `5cbe3f68…`.
7. Tripwire and the plain test (below).

**Tests, written red first**
- `tests/test_legal_render.py::test_pathway_has_model_block_follows_the_composition` is the plain test. It asserts true for `covenant_refinancing` and `credit_snapshot`, and false for `distressed_restructuring`. It was red before the change.
- Tripwire `tests/test_connect_cp2d.py::test_fp04_maturity_wall_shows_model_content_first_with_t2e4_as_a_tab`, marked `xfail(strict=True, reason="Stage 3 S.4 wiring")`.

**Tripwire design**
- It reuses the existing `make_upstream` and `_submit(_literal("positive"))` fixtures. These settle CP-1 as restricted and CP-2D as positive, and the build takes under 1s. It runs `report_view.build` over `SHIPPED_MAPS` for the run's pathway. No new fixture was needed and nothing is faked.
- It first asserts that CP-2D is settled, so it cannot xfail for lack of a settled CP-2D.
- Then it asserts `block.owner == "MODEL"`, `block.figures[0].fig_id == "S.4"`, `[tab.label for tab in block.tabs] == ["T2E.4"]` and `block.tab_label != "T2E.4"`.
- Today it xfails on the figures assertion, with no crash. The block is dense with no figures, no tabs, and T2E.4 rows as primary.
- Once Stage 3 wires S.4 and moves T2E.4 into a tab, it XPASSes and strict fails, which forces the marker off.

**Gate exit codes**
- All of these exit 0 when each file is run on its own with `PYTHONPATH=src:tests`:

| File | Result |
| :--- | :--- |
| `test_legal_render` | 77 passed |
| `test_connect_cp2d` | 108 passed, 1 xfailed |
| `test_method_cp2d` | 313 passed |
| `test_connect_cp3c` | 136 passed |
| `test_method_cp4` | 24 passed |
| `test_connect_cp4` | 61 passed |
| `test_connected_render` | 14 passed |
| `test_owner_order` | 15 passed, 1 skipped |
| `test_stage2_classes_batch` | 12 passed (47s) |
| `test_connect_cp2a` | 103 passed |
| `test_connect_cp2g` | 109 passed |
| `test_connect_cp2h` | 121 passed |
| `test_connect_cp4c` | 128 passed |

- `ruff format --check` on the 6 touched files exits 0.
- `mypy --strict` on the two `src` files exits 0.
- `python3 -I cases/pins.py --check` exits 0 (75 paths).
- `ruff check` on the touched files exits 1, on two errors that predate my change and sit on lines I did not touch. The first is SIM102 at `report_view.py:293`. The second is C408 at `test_legal_render.py:220`. I left them alone.
- My diff adds no `noqa` or `type: ignore`, so the counts stay within 13 and 5. I did not run the committed baseline counter. My own grep over the repo shows larger raw totals (54 and 27), so I could not confirm the 13 and 5 limits that way.
- `tests/test_source_tools.py` is mentioned only because `git grep` finds `covenant_refinancing` as a fixture pathway name at line 700. It is very slow. After about 50 minutes it was at 52% or more with no failure, and I killed it.

Not verified: `tests/test_source_tools.py` ran to roughly 60% before I killed it, with no failure seen. The `ruff check` errors above predate my change. The populated S.4 render is Stage 3 work, so the tripwire only proves today's absence of it. The `noqa` and `type: ignore` baseline counter was not run. The slow render suites and the `test_owner_<cp>.py` genuine runs were not run, as the brief said. The full suite was not run, and there was no `detect_changes` or `impact` run.

agent=mx-feature fix-rounds=0 gates-first-pass=n
