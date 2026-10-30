**Stage 4 review (3429790..e37b73e, `claude/s4-int2`) — Verdict: REVISE** (one Medium, class E; everything else holds). Probes: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage4-review/arch/` (tree copy deleted).

**Medium 1 (class E): the CP-8 outcome fact still reaches the reader as the raw token in the module table.**
- `src/deploy_vii/render.py:58` `table_display` and `:161-162` put `fact_spelling(fact)[2]` = `fact.text` into `report-data` for every module fact; `src/deploy_vii/assets/app.js:528` and `:567-577` draw `module.tables` cell-for-cell from `fact.table_display`. For `cp8.what_changed.outcome.value` (no_outcome) that is `"... since the decision [T7.3.window.realized_value] and every ..."`.
- Scenario: the CP-8 module panel's "What changed since the last Report" table, row Outcome, shows the bracketed token where it used to show `∅ G#`; the same string is the inspector's "Value". The what-changed *block* is correct (`∅ G26`, same `n` as `T7.3.window.realized_value`).
- Probe `probe_e_report_data_payload.py`, exit 1: block line = `[('text',…), ('gap','∅ G26','G26'), ('text',…)]` OK; token survives at `$.modules[0].facts[150].display` and `.table_display` (the `.text` survival is the stored fact and expected).
- Why nobody saw it: batch2 builder and reviewer both listed the owner-rendered page as not verified; `test_owner_cp8.py` is deferred and `owner_rendering._rails` compares the stored fact to the payload fact (both carry the token), so it would pass.
- Fix is outside item 30's scope (`render.py`, `app.js` are `src/deploy_vii`). Recommended ruling: extend item 30 to `render.py` `_report_payload` so a known text fact that `prose._TOKEN` matches gets `display`/`table_display` from `report_view.resolve` with the module's facts and `gap_refs` (the module and index are in hand at `:161`); RED test = the payload-path assertion in the probe. Alternative: the owner accepts the token in module tables and records it. Mx-feature fix round only after the ruling.

**Info 1 (class A, predates; owner):** a failed CP-MODEL publication's `attempt.issues`, `interruption` and `publication.reason` are not replayed (`owner_workflow.py` `_verify_publications`, the `elif` only requires them non-empty); attempt 1's `repair_issues` then binds to whatever text the first carried. Plan §1 deliberately scoped the publication check to begin's identity fields, so not a Stage 4 gap. No probe.

**Info 2 (probe artefacts):** `probe_e_token_leak_full_render.py` and `probe_e_page_chip_form.py` exit 1 only because the visible HTML is drawn client-side from `report-data`; the payload probe supersedes them.

**Class A (checked, no gap):** `_expected_begin` (:1520) is `Execution.begin` :647-668 line for line (pending refusal, `current_inputs` with explicit `NotAuthorized`/`ValueError` → `identity_mismatch`, `previous` rule, `Attempt(...)`); `_verify_begins` requires `after.attempts == (*before.attempts, expected)` and `begin.attempt == expected.number`; publications bind the five identity fields at their own `before`; submissions bind the after-attempt's five fields to the before-attempt (:1596-1603); `_verify` refuses a pending attempt in the final snapshot and binds the deterministic head's final `current_inputs` with the same mapping. Every recorded transition that changes a snapshot now replays its rule; refused records are class D by design.
**Class B:** `_check_specs` :1004 refuses a spec without a `_PROBES` row; test asserts `not_permitted`, no store written, then success with the row restored. `probe_b3_rows_reach_a_registry_assert.py` exit 0: 28 rows, every row reaches a registry assertion (`test_the_oracle_sections_are_found` guards ≥25 rows).
**Class C:** no code; tests sit in the fast set (exit 0).
**Class D:** docstring (:2397-2400) and protocol §4 state exactly what is checked and what is not.
**Class E otherwise:** re-pin moved only `tables[8].rows[1].facts[0].text` (builder `T(shown=)` is the regenerator); `_carries_reference` has no try/except; a mixed or foreign token fails closed (tests present); `report_view.py` is the only `src/deploy_vii` file touched, within items 30/31; D12 records appended.
**Owner fixes / CP-2G tree:** A maps `shown=None` to `cell_notation` by status and raises on any other status; B binds the payload token; D binds the pack hash and requires exactly one carrier; E compares to the oracle's frozen count (the oracle holds only a count); F copied = CP-1 citations, derived = `one_per_page`; tree: six `limitation` leaves + note, one pin. No comparison loosened beyond item 41's text.

| Class | Status |
|---|---|
| A | no gap (Info 1 predates) |
| B | no gap |
| C | no gap |
| D | no gap |
| E | Medium 1 (module-table/inspector spelling of the token) |

**Gates:** `fast.log` exit=0 (10331 passed, 19 skipped, 1 xfailed); `A.status` g2fast exit=0 (153 passed); `r-0.log` and `r-1.log` have no `exit=` line → pending.

Not verified: the deferred genuine runs (`r-0`/`r-1`, `tests/test_owner_cp8.py`, full `test_owner_s1a.py`/`test_owner_workflow.py`); `_expected_begin` equivalence beyond reading (adversary P-R not re-run); the DOM itself (app.js read, not executed in a browser); cause B's unit check in `fig_bindings`; ruff/mypy/D12 strict probe not re-run; mutation and property gates.
