# Legal oracle move review (mx-precise a802522e, 9ac76c6)

## Legal oracle move 9ac76c6 (claude/s3-legal): REVISE

The funding-gap move is right. The move is incomplete, though: the legal fixture now draws a CR.1 figure that the legal oracle does not record.

**1. funding-gap: correct.**
- Producers `["CP-2D","CP-3C"]` match `src/deploy_vii/report_view.py:1242-1243`.
- The note format is confirmed. Producers are joined with " · " at `report_view.py:1399`, and "Not run: {codes} was not requested in this run." is built at `:1427` when every producer was not requested.
- The test passing with the workaround also shows the literal matches what renders.

**2. maturity-wall kind: the preparer is right.**
- The spec row says `chart` (`report_view.py:1240`), but the rendered not-run block is `dense` in both legal cases (probe p4).
- The oracle compares against `block.kind`, so `dense` stays.

**3. A figure was missed (Medium).**
- Probe p4 renders both legal fixture cases. Each draws a populated `covenant-tests-headroom` block with figure `['CR.1']`.
- `cases/legal/render-expected.json` has no `fig_id` or figure expectation anywhere. Ruling 13 names "any figure the FP-04 or FP-05 fixture now draws" as part of this move.
- The report's "Figures on populated blocks: none to move" is wrong. The test stays green only because it never asserts figures.
- Fix: add a CR.1 expectation for `covenant-tests-headroom` in each case. It should cover fig_id, placement, kind, marks and twin, taken from the fixture's T4.9 rows under the `cases/charts/cr1-expected.json` rules. Add a builder target that asserts it.

**4. Builder targets: yes.**
- Once `_producers_after_stage3` and `_note_after_stage3` are deleted and lines 358 and 365 assert against `want`, the only remaining read outside the legal fixtures is `cases/charts/cr3-expected.json` at `tests/test_legal_render.py:375`, and that read goes away with the helpers.
- `json` and `ROOT` stay in use (`:30-34`, `:177`).

The probe is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/oracle-review-B/p4_legal_figures.py`. It exits 1 because the fixture draws a figure and the oracle records none.

Not verified: the CR.1 mark values in the legal render were not compared with any oracle, because none exists yet. I did not run `tests/test_legal_render.py` with the helpers removed. FP-05 blocks are outside this fixture's pathway.

## Scoped re-check of 724a0ad

## Legal CR.1 re-check (724a0ad): APPROVE

The Medium finding is fixed. Both legal cases now pin the CR.1 figure, and the pinned values match what the fixture renders.

**Probe p5** (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/oracle-review-B/p5_legal_cr1.py`) exited 0 with 0 mismatches. It renders each case and compares it with `cases[i].cr1_figure`, value by value:
- **Figure and block:** block kind and state, tab_label None, no tabs, one figure, fig_id, placement beside, kind bullet, series, unit x and unit class multiple all match.
- **Marks:** series, category "Maintenance leverage test", text and Decimal value match, in order.
- **Gap case:** Headroom renders `∅ G1` with value None, which matches `gap_ref_pattern`.
- **Twin:** cell texts equal the mark texts. Each label starts with `label_parts[0]` and contains the later parts in order, with the run-time `[S1]` and `G2` filled in.
- **No other legal block** carries a figure.

**Against the fixture and the CR.1 rules (by reading)**
- The values come from `fixture.shared_rows[2]`: threshold text 4.00x, current 1, headroom 3, share 0.75, comparison "Not more than", and the CP-1 metric text.
- The gap overrides are applied as `cases[1].overrides` gives them: headroom and share missing with their limitation, and the test text "Not calculable".
- The companion ids and labels follow `cases/charts/cr1-expected.json` positive and gap exactly. They differ only where this fixture's own facts differ: the category label, the CP-1 metric text, and headroom 3 rather than 3.00.
- The threshold keeps its settled text and strict-parse rule.
- The gap reason is the fixture's limitation, copied verbatim, not typed.

**Builder target:** `cr1_builder_target` asserts the figure, the marks, the twin and that no other block has a figure. It reads only the legal oracle.

Not verified: the target has not been turned into test code, so `tests/test_legal_render.py` still has no figure assertions and was not re-run. The `source` prose field was read only in part.
