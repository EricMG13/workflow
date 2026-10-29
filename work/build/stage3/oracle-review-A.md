# Chart oracle review, half A (mx-precise a1ce38fb, s3-oracles 6288196)

## Stage 3 chart oracles, half A: independent review (R = s3-oracles at 6288196)

**Spec verdict: REVISE.** One Medium finding. **Quality verdict: sound.** The values are right, the rebuild is deterministic, there is no stub or fake value and no catch-all that hides a failure. The remaining findings are Low and Info.

Probes are saved under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/oracle-review-A/`:
- `p1_rebuild.sh` exited 0. It rebuilt from a fresh `git archive 6288196`, and all four files were byte-identical to the tree. `pins.py --check` matched 86 paths. It ran in under 1 s.
- `p2_spotcheck.py` exited 0.
- `p3_gaps_and_twins.py` exited 1, on purpose: it flags L1 below.
- `p4_feasibility.sh` exited 0. It is a grep of the code facts behind the feasibility list.

### Checks
1. **Values: pass.**
   - RV.3: all 24 positive and 20 gap points equal the CP-1C fact `shown` strings. p05 is never plotted.
   - CR.1: 4.00x, 1.00x and 3.00x, with headroom_share 75.0%. These match the CP-4 `displayed_literals`.
   - S.4: 50 at 2029-12-31. The T2E.4 cells equal the CP-2D oracle.
   - S.5: revenue 30 and adjusted EBITDA 7.5 per quarter, from the manifest. The basis ids equal `tests/test_financial_series.py` `BASES`.
   - The builder types no values. `build_a.py:91` and `:585` assert the spelling against the oracles' own `shown` text.
2. **Gaps: pass.** Every gap mark has amount null and a non-null reason. The adversarial cases cover CP-1C (gap, no_peers, refused) and CP-4 (gap, gap_false_same_definition).
3. **Form and owner:** pass, except M1. Each inference is flagged in the `form` sections.
4. **Rulings 3 and 5:** applied as written (5.1–5.6 and the S.4 tripwire rewrite at `build_a.py:919-931`).
5. **Moves:** half A moves no frozen oracle. The pins are regenerated. L3 is a move nobody has ruled on yet.
6. **Feasibility:** see the list below.
7. **No stub or fake value: pass.** `∅ G#` is a documented pattern; the number is assigned when the report renders.

### Findings
**M1 (Medium). S.5 lands on FP-02 with no oracle or target saying so.** `build_a.py:293-303`. `financials-credit-metrics` is one `_Spec` shared by `credit_snapshot` and `earnings_update` (`report_view.py:495`, `:519`, `:1102`). On the approved FP-02 page that block is collapsed and has no S.5 (`rbot-fp-02-earnings-update.dc.html:113`).
- Failure: the oracle and its targets cover only `credit_snapshot` (`:302` names only the metric-strip). A builder can pass every target and still draw S.5 on FP-02, against the approved page.
- Fix: add an `earnings_update` render expectation and a builder target, either "not drawn" or "drawn, recorded as a design deviation". Group B's CR.2 placement precedent is ruling 6.3.

**L1. The S.4 companion order differs from the producer.** `build_a.py:792-805` puts `period_id` last. `financial_series.py:210` (required, minus principal) puts it third. The oracle claims "the same S.4 record … no new producer" (`:855`). No target asserts the order today. Fix: build the order from the producer's order. Probe: `p3_gaps_and_twins.py`.

**L2. The S.5 and S.4 twin rows leave out companion label parts.** `build_a.py:221` and `:861` pass `companions: []`. But `_cp1_strip` (`report_view.py:1687-1693`) adds companion labels to every twin row label, and S.5 lists 11 companions. A test written from `label_parts` would fail. Fix: mark the label parts as a prefix and say the companion parts are added at run time, or drop `label_parts`. Probe: `p3_gaps_and_twins.py`.

**L3 (cross-file, needs a ruling). Frozen CP-1C prose becomes false.** `cases/cp1c-owner/expected.json:6847`, `:11200` and `:13042` say "range strip Fig. RV.3 … is not populated (table form only)". That stops being true once RV.3 lands. It is the same situation as ruling 6.7 for CP-4C, but no ruling covers CP-1C, and the preparer did not raise it. No test reads it. Fix: Modules rules a rewording through the CP-1C builder.

**L4. The CR.1 target's tab wording contradicts the Block validator.** `build_a.py:753` says "tab_label as before (T4.9 'Covenant tests and headroom'), no tabs". `report_view.py:408` requires `tab_label` to be None when there are no tabs. Fix: assert `tab_label is None` and `tabs == ()`.

**L5. Adversarial case missing: CP-2D settled, CP-1 not settled, in `maturity-wall`.** Once the spec kind is `chart`, `report_view.py:1807-1808` draws the n/a strip and T2E.4 becomes the primary tab. That breaks the oracle's `model_first` case (`build_a.py:873`), and the oracle does not pin this case. Fix: add the case and its expected state.

**I1. `cases/charts/expected.json` is not pinned.** S.5 and S.4 read it, but `*-expected.json` does not match the plain `expected.json`. Its sha256 is recorded in `source_authority`. This predates the change, so it goes to the owner.

### Feasibility (check 6): changes beyond the existing chart path that the wiring needs
- `ChartKind` (`report_view.py:56`) gains `range` (RV.3) and `bullet` (CR.1), and `charts.py` needs geometry for both. The brief names new `ChartKind` values as an example of a change outside the chart seam, so they need a scope ruling before wiring.
- `_chart_fact_cell` refuses the percent unit class (`:1616-1617`), which RV.3a needs. It also refuses a known fact with no amount (`:1618`), which is how CR.1's threshold text "4.00x" arrives. A new strict-parse mark path is needed.
- `_block` draws figures only for `chart` specs and only through the CP-1 path (`:1807`). S.5 (a `period_grid` block), RV.3 (CP-1C) and CR.1 (CP-4) need producer dispatch in that seam.
- `_cp1_strip` requires exactly S.1 to S.4 (`:1652`) and expects kind `line` for everything except S.4 (`:1665`). S.5 needs both checks changed, or its own entry point.
- The S.4 fixture gap (`cp1_module` lacks the T4.14 and T4.18 fields) is already flagged in the oracle.
- No target needs a `cases/` change. The RV.3 panels are two figures, which `Block.figures` already supports, so no two-panel `ChartSpec` is needed.

Not verified: no pytest or wiring was run against `src/`. I did not open the pack brief lines (01:36, 03:36, 04:27, 04:31); I read the design pages only for S.5 and FP-02. Whether `view.modules` always holds CP-1 (the L5 path) is unchecked. Half B and its moves were not reviewed.
