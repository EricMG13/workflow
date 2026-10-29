# CP-1D Stage 2 report (mx-feature)

CP-1D Stage 2 report. Commit 8a5d3d9 on claude/s2-cp1d (cut at 7a39384). Fast gates exit 0. The store-run tests are written but not run.

DEVIATIONS FIRST
- Test-first order: I wrote the L3/I2, clipping and bounded-issue tests first and watched them fail for the right cause. For the connection I wrote core and tests together. The 40 mutants stand in for red-first evidence there.
- `parse_bridge`: the lease says `parse_bridge(source)` but Stage 1 has `parse_bridge(pages)`. I kept Stage 1's.
- The lease's Public API has no `cp1d_reader` (Q6), so I built none. A test pins that the Public API names none. D3 stays open until CP-2G.
- I did not add the `docs/reuse/manifest.json` D12 record. It is outside the brief's library-boundary list.
- The hostile-text set (Q5) is not in `tests/defect_classes.py` yet, so that test is not written.
- `ENTRY_VALIDATOR` and the probe use the validator that `submit` also uses.

DeliveryScope (copied word for word from the lease): `DeliveryScope(scope_id="cp1d-fp02-quality", pathway="earnings_update", requested_modules=("CP-1D",), sections=("earnings-quality","restated-leverage"), rails=("evidence","limitations"))`. I added no `MODULE_FAMILY` row (Q8).

LEASE LINE TO SYMBOL
- `src/deploy_workflow/owners/cp1d.py` now holds `STEP_ID`, `STEP_IDS`, `QUALIFICATION`, `SCHEMAS`, `RULES`, `Upstream`, `cp1d_upstream`, `_inputs` (the one adapter), `validate_earnings_quality`, `earnings_quality`, `EarningsQualityReport`, `context_block`, `cp1d_module`, `submit`, `view`, `probe`, `ENTRY_VALIDATOR`, `SCOPE`.
- `owner_workflow.py`: appended `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES`, `_VIEWS`, `_ENTRY_VALIDATORS` and the `OwnerSpec`.
  - The step is `earnings_quality`, `sources=True`, `inputs="module_context"`, `rules="journaled"`, no precheck.
- G1-X guard: `sources=True` matches the existing `host._OWNER_SCOPES` row. A test flips it and `_check_steps` refuses.
- New `src/deploy_vii/bindings/cp1d.py` (blocks `earnings-quality` T1D.2/3/5 and `restated-leverage` T1D.6; T1D.1, T1D.4 and `cp1_references` to Evidence; T1D.7 to Limitations). It is appended last in `SHIPPED_MAPS`, since the lease states no position.
- `report_view.py`: `_EARNINGS_QUALITY`, added to the `_spec_of` loop, and both block ids inserted after `ebitda-adjustments` in the `earnings_update` preset.
- New `src/deploy_vii/methods/cp1d.md`.

BACKLOG ROWS
- Done, rule W and item 8 comma costs: notes with code in `methods/cp1d.md`, plus tests that run the same lines.
- Done, addendum 5 note: identifier and ordinal runs and non-ASCII numerals, with `2.5m`, `25bps` and `2nds` still read.
- Done, L4: the test comments and the `1.5<ZWSP>nd` expectation now agree with addendum 5.
- Done, blank quote inventory: the defect is NOT present. Blank evidence, basis and overall quotes (spaces, U+200B, U+00AD, U+FEFF, newline and tab) are refused as `Quote/locator mismatch` or as the exactly-one issue. They never compose. A regression test pins this. I did not add the `<path>: empty text` frame to quotes.
- Done, `listed_issues`/`clipped`: `_line` and `_bounded` wrap every caller- or pack-quoting issue line in cp1d. `validation_issues` now returns at most 20 lines. The 19 refusal outputs are unchanged.
- Blocked, not built: recipe text re-pin (LEAD release); the L3 non-ASCII ordinal question is superseded by the ruling below.

LEAD RULINGS APPLIED
- L3/I2 remedy: after a run, skip Cf/Mn/Me, NFKC-fold the window, match st/nd/rd/th with no letter after it. A left neighbour touches the run if its category is L*, Mn, Mc, Me or Cf, or its NFKC fold holds a letter. Tests are in `test_method_cp1d.py`.
- Frozen cases: `p5_frozen_compare` reports moved 0 (19 refusals, 3 cases, 1 frozen basis quote), exit 0. The `a7_r1_ordinal_identifier.py` probe exits 0.
- `a1_residual_bypass.py` still exits 1. The remaining composing lines are `1.5<combining macron>x` (the ruling skips Mn only before an ordinal match) and the rule-W forms `Q-1.5`, `1.5-Q`, `Q-\n1.5` and `1.5-\nnd`. All were in the baseline output except the macron line. The ruling does not cover them. Please confirm.
- Round 3 citations: `_one_per_page` keeps the first quote per (source, page) in input order for calculated facts only; sourced facts keep their own citations. First-quote and last-quote mutants are killed.
- Round 3 model text: assessment and overall rationales go through a `RunText` `TypeAdapter` and report `<path>: <msg>` without the input. Any `ValidationError` while composing becomes an issue line, so nothing raises after the binding write.
- Round 3 synthetic limitation: pinned by a head built with `settle`. Settled own limitations are the oracle `own_limitations` then the synthetic line, and equal `settled_limitations` for the positive case. No reader returns it, since there is none.
- Round 3 aliases: nothing needed in cp1d. Real-store `begin` canonicalises already.

TESTS AND GATES (all exit 0)
- Gate pytest, `test_connect_cp1d` + `test_method_cp1d` + `test_owner_g1x` + `test_host_h1` + `test_defect_classes_selfcheck`, plus `test_rule_issue_bounds`, `test_owner_blank`, `test_engine_blank_text` and `test_cp1b_registration`: 978 passed, 1 skipped.
- Render tests (`test_cp1_chart_render`, `test_earnings_render`, `test_legal_render`, `test_connected_render`): 216 passed.
- `ruff check`, `ruff format --check` and `mypy --strict` pass on the 9 changed files plus `report_view.py`. `ruff check` on the whole `report_view.py` shows one SIM102 at line 293 in code I did not touch.
- New `tests/test_connect_cp1d.py` has 103 tests, about 2.5 s. It covers:
  - registrations;
  - the adapter over varied CP-1 heads (scale, FY25 decoy with the same label, T4.17 row counts) and three CP-1B states;
  - 19 refusals, RULES, stale and swapped inputs;
  - candidate checks and `settle` per case;
  - the view's key tree, with no quote strings;
  - `validate_bindings`;
  - a real-store `submit`, `probe`, blocked-after-two-failures and unread-page run built without a CP-1 promotion. The probe tamper test is here; the other deferred acceptance items are covered by the deferred tests below.
- Mutants: `<S>/cp1d-s2/mutants.py` (S is the scratchpad path above), 40 mutants over adapter fields, registration rows, bindings, the citation rule, RULES and the validator, from full copies. All killed. Two survivors in the first pass were fixed with new tests.
- I also ran the new driver's CP-0, source_context, financials, narrative and readiness literal for all three cases. All came back valid.

FOR LEAD (text only)
- `methodology.json` needs no change; the CP-1D table_ids are already T1D.1–T1D.7.
- TOOL-CONTRACT row for `earnings_quality`: the `read_inputs` view is `{upstream, bridge{state,source_id,pages,items,totals}, cp1_facts, cp1_t417_rows, cp1_facts_note, inherited_limitations}`. `cp1_facts` lists only the 7 selected operands, and the view has no quote text.
- `cases/cp1d-owner/cp1d-view-tree.json` is not committed, because `cases/` is not editable.

DEFERRED COMMANDS (for `work/build/deferred-runs.md`)
- `PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp1d.py`
  - One genuine CP-1 promotion per case (11–26 minutes), 29 tests: tamper at verifier level (consistent forged read body, SettledHead edits, probe on a swapped step), stale_binding, submit before read_inputs, non-pack invoke, blocked with receipt and status-only head, unread page then repair, store bytes unchanged, the D3 check (no reader; consumption open).
  - The driver is `tests/cp1d_runs.py`, with `cp1d_closed(case, root)`. Its quality step, the CP-1D submit and `write_receipt` are unrun.
- Also deferred: `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py`, `tests/test_earnings_workflow.py` and the source suites.

Not verified: any real CP-1 promotion or closed CP-1D run, including the driver's quality step, the CP-1D submit and `write_receipt` without CP-MODEL; the verifier-level tamper cases, stale_binding and the OwnerWorkflow-level submit-before-read; the real fact ids and spelling of a promoted CP-1 head, since the fast fixtures use hand-built T4.10 facts with unit `MILLIONS`; FP02 rendering of the new blocks; the full `test_owner_workflow.py`; GitNexus `detect_changes`; the hostile-text set (not landed); the recipe-text re-pin.

agent=mx-feature fix-rounds=0 gates-first-pass=n
