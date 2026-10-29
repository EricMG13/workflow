# Chart oracle review, half B (mx-precise a802522e, s3-oracles 6288196)

## Stage 3 chart oracles, half B: independent review (R = s3-oracles at 6288196)

**Verdict: REVISE.** One High and one Medium finding. Both are in the builder targets, where the oracle meets the code. The values themselves are clean.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/oracle-review-B/`:
- `p1_rebuild.sh` exited 0. It rebuilds `build_b.py` and the cp3c and cp4c owner builders from a fresh `git archive` copy (about 1 s), and all 11 outputs are byte-identical to the tree. `pins.py --check` matches 86 paths.
- `p2_mark_text.py` exited 1 (see H1).
- `p3_values.py` exited 0. All 157 points (CR.2, CR.3 including the fixtures, DR.2, DR.3-5) equal their module-oracle fact in shown text, exact value and state. The numbers typed into the adversarial prose match too: burn 20/-12/8; CR.3 4.5/-8.5/-14; DR conservation 123.60/55.62/37.08; recoveries 100/18.7/74.2.

### Findings

**H1 (High): every DR.3-5 figure fails ChartSpec's own check.**
- Where: `cases/charts/dr345-expected.json:5` ("Marks carry the settled two-decimal texts") and the points, e.g. `:550` `"shown": "43.60"`; source `cases/charts/builder/build_b.py:1101`. The check is `src/deploy_vii/report_view.py:286`: `mark.text != format_value(mark.value, self.unit_class, "known")`.
- Scenario: the `amount` unit class shows 0 dp with no `decimals` override (`display.py:23`). So all 42 known DR.3-5 marks fail, e.g. "3.75" against "4" and "123.60" against "124" (probe p2). A wiring builder cannot construct any DR.3-5 `ChartSpec` without changing that shared check or the texts, and the oracle names neither. Brief check 6 requires it to be named. CR.2, CR.3 and DR.2 pass.
- Fix: in dr345, name the seam change, i.e. `ChartSpec`/`ChartMark` carries the facts' declared `decimals` and passes it to `format_value` (which already takes `decimals`). Or have the owner rule which spelling the marks carry.

**M1 (Medium): the DR.6 render target contradicts ruling 6.5, and the code has no field for a frame G#.**
- Where: `cases/charts/dr6-expected.json:29` (builder `build_b.py:1354`): "the frame cites a gap reference spelled '∅ G<n>'". This is required for both runs, but `cases.positive.cited_gap_fact_ids` is `[]` (`dr6-expected.json:121`), and ruling 6.5 says the positive case cites no G#.
- Scenario: a test written to this target forces a fake G# onto the positive frame. Separately, `ChartSpec` and `Figure` have no ref field, and an n/a frame has zero marks (`report_view.py:252-325`, `charts.py:624`). So the gap-case citation needs an unnamed seam change.
- Fix: make the target per case (positive: no ref; gap: the cited facts' G<n>), and name the field that carries it.

**L1 (Low): stale "no chart" sentence in DR.2.** `dr2-expected.json:1306` (`build_b.py:1051`) says the cp4c `d7_rendering.decision` "still reads 'no chart' … (the owner oracle is not edited)". Ruling 6.7 edited it in this same merge (`cases/cp4c-owner/expected.json:52`), so the two files now contradict each other. Fix: delete or reword the sentence.

**L2 (Low): CR.2 forged-view target conflicts with "no recompute".** `cr2-expected.json:54` (`build_b.py:438`) says a forged view that drops only r07 makes r08 a gap. But r08 is a settled fact, and the same assert requires each value to equal `Fact.amount`. Fix: the forged view drops r07 and r08 together (per the missing rule), so a plain read stays correct.

**L3 (Low): hand-typed CR.3 fixture reason, not flagged.** `build_b.py:528` types "Not calculable: a required operand is missing" as the gap reason and the n/a reason. The cp3c fixture carries no reason, and only `fact_id_basis` and `shown_basis` are flagged as inferred. The fixture categories (`notes`, `term-loan`) are facility ids, while the pack cases use row labels; that is also unflagged. Fix: flag both as inferred, or do not pin the text.

**L4 (Low): hatching needs a seam change the oracle does not name.** DR.2 pins `hatched: true` and the legend "hatched = illustrative" (`dr2-expected.json:40`). `charts.py:83` hatches only `S` refs, and a recovery fact is calculated. This is a chart-seam change (in scope), but the oracle should name it.

**L5 (Low): no adversarial case for refused or blocked producer runs.** The module oracles have `refused`, `blocked` and `cp2g_blocked` cases (cp4c, cp2h). DR.2, DR.3-5 and DR.6 do not say whether a figure or frame appears when the producer is blocked or refused. Fix: add one case each ("no figure; the block keeps its honest state", or rule otherwise).

### Clean
- **Rulings:** 6.1 (binding move, lease amendment, cr3 `funding` render, refinancing-paths tabs read from the moved oracle), 6.2, 6.3 (`scope_limits`), 6.4, 6.5 (per-case `frame_reason`), 6.6 and 6.7 are applied.
- **Gaps:** gaps are never 0, every builder gap is a gap point with value None, and `kind_or_na` gives the n/a frame. No catch-all hides a failure; the builder uses bare asserts that fail loudly.
- **Moves:** only the Q-C2 change in cp3c and the 6.7 wording in cp4c moved. Both went through their builders, and PINS was regenerated.
- **Feasibility:** CR.2 and CR.3 marks pass the text rule. `Block.figures` holds several figures, and "beside" is a valid `FigurePlacement`. The T3D.1 binding move and the funding-gap producers change are named.

Not verified: no product code was run against the oracles (there are no producers), so render and `validate_bindings` behaviour was read, not run. I did not check the design-page and brief line citations or their sha256 values against D or P. Half A files were not reviewed.
