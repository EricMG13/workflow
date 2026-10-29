# W2 group b report (mx-feature ad00e795, claude/s3-w2b 04fb724)

W2 group b is done: the RV.3 and CR.1 producers are built test-first and registered, and every gate I ran exits 0 except one `ruff check` finding that predates this work.

Worktree: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-ad00e7952dc7cca9a`, branch `claude/s3-w2b` (cut from 423f92e, confirmed). Tip: `04fb7240368710aeb97c16c0b5128304822bb399`. The tree is clean, the `.venv` symlink is removed and no background process is left.

Commits:
- 6131455: RED tests, which failed as intended.
- A producers commit.
- 04fb724: CR.1 undrawn-unit handling and the seam registry test change.

**Files changed**
- `src/deploy_vii/report_view.py`: appended a group b section at the end. The producers are `_rv3_figures` and `_cr1_figures`, with helpers `_ChartPoint`, `_settled_cell`, `_shown_module`, `_figure_of_points` and `_is_plain_multiple`. The final lines are one registration block headed `# -- group b (RV.3, CR.1) --`, so the integration pass can merge by appending. I also reworded one stale comment at line 1269.
- `src/deploy_vii/bindings/cp1c.py`: docstring only.
- New tests: `tests/test_chart_series_rv3.py`, `tests/test_chart_render_rv3.py`, `tests/test_chart_series_cr1.py`, `tests/test_chart_render_cr1.py`.
- `tests/test_chart_seam.py`: one test edited (see question 1).
- No `cases/`, lease or manifest edits. No `bindings/cp4.py` change was needed, because T4.9 was already bound to the block.

**Figures**
- **RV.3a and RV.3b** are registered on `peer-positioning` for `relative_value`.
  - Both are `range` kind, titled "Peer positioning", placed above, with series Issuer, Peer median and Peers.
  - Only peers whose T1C.1 `included` fact reads "Included" are drawn. An excluded peer's facts are never read.
  - A missing or unsettled fact becomes a gap mark `∅ G#`, never 0. With no included peers, or a module not in accepted, restricted or candidate status, there is no figure.
- **CR.1** is registered on `covenant-tests-headroom` for `covenant_refinancing`.
  - It is `bullet` kind with unit `x`, placed beside, with series Threshold, Current and Headroom.
  - The threshold is read by the strict parse. A rejected text, such as "4.00" or ">4.00x", becomes a gap with its G#.
  - A row whose comparison is neither "Not more than" nor "Not less than" is not drawn, and its comparison fact is named in the figure summary. If no row is drawn, the figure is the n/a frame with that reason.
  - No verdict words are drawn.
- Item 9's CP-1C prose move invalidated no test literal. The oracle was already reworded, and the CP-1C method and connect tests pass unchanged, so no re-pin was needed.

**Gate exit codes**
- pytest on the four new chart test files, `test_chart_seam.py`, the CP-1C and CP-4 method and connect tests, `test_legal_render.py` and `test_connected_render.py`: 651 passed (exit 0), run together.
- `python3 -I cases/pins.py --check`: exit 0, 86 paths.
- `MYPYPATH=src mypy --strict` on `report_view.py` and `bindings/cp1c.py`: exit 0.
- `ruff format --check` on the changed files: exit 0.
- `ruff check` on the changed files reports only the known SIM102 at `report_view.py:312`. I ran ruff on changed files only, because a repo-wide run reports about 130 KB of unrelated findings.
- Suppression counts are unchanged: `noqa` 13 and `type: ignore` 5.

**Questions and findings for the controller**
1. **Seam test changed.** `test_chart_seam.py::test_the_registry_ships_empty...` fails once any group registers. I rewrote it as "an empty registry leaves the dispatch with no figure of its own". The other three groups will need the same edit, and an identical text should merge cleanly.
2. **CR.1 degrades rather than raises.** `tests/test_legal_render.py::test_native_pp_and_other_current_dimensions_preserve_supplied_values` sets headroom to `pp` and current to MILLIONS. The seam's `_chart_fact_cell` would raise and abort the whole report. CR.1 now leaves such a row undrawn and names the fact, so the report still builds.
3. **Missing headroom has no unit.** In the gap case the fact has `unit=None`, so the seam's own `_chart_fact_cell` would refuse it. `_settled_cell` therefore builds the gap cell in the chart's unit class from the fact's G#. This needed no seam change.
4. **Gap companions carry no `[G#]` suffix.** I follow the oracle's label parts here. The CP-1 path still appends one.
5. **RV.3 still fails closed.** A plotted CP-1C fact with the wrong unit dimensions raises, as the CP-1 chart path does. Say if you want it to degrade like CR.1.
6. **Stale method note.** `src/deploy_vii/methods/cp1c.md:23` still says RV.3 is deferred and the block is tables only. I left it because it is method text, not a producer.

Not verified:
- The full suite, plus the `test_owner_*` closed runs and the other `test_method_*` and `test_connect_*` files.
- Browser appearance of the range and bullet figures. Tests cover SVG structure and the HTML strings only.
- Real-data runs. Only the synthetic oracle cases (positive, gap, no_peers for CP-1C; positive and gap for CP-4) were exercised.
- Mutation testing, jscpd, complexipy, and GitNexus `impact` and `detect_changes`.
- Whether the four groups merge cleanly.
- The `gap_false_same_definition` refused first submission was tested only as a CP-4 view with a blocked, unrun or stale status and no facts. The real refusal path was not driven.

ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n (the first run of the combined gates failed two pre-existing tests, the seam registry test and the legal-render `pp` test, which I then fixed).
