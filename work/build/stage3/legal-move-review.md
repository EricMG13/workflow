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
