## Round 4: where known text facts hold run text (survey and plan)

Code read at ca17721; base is 2f345c2. I wrote nothing into any worktree, and the lane is clean. The tree copies are deleted. Probes and survey output are in `<S>/round4-plan/`, where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

Round 3 missed two tables, not one. Besides the reviewer's CP-L10 TL10.3, CP-2H T2R.10 also shows raw reference tokens at ca17721. Keying the registry by (module, table, field) fixes both. A prototype of that change, in `report_view.py` only, passes every probe and the affected fast tests.

### Survey: what each kind of text field does

To find the locations I ran a pytest plugin over all 16 `test_method_*` files (`probes/survey_plugin.py`; summary script `probes/survey_summary.py`). It records every text that `prose.issues` or `RunText` checks and every known text fact that is built. I then confirmed each hit by reading the code.

| Class | (module, table_id, field) | Validated / composed | Stored | At ca17721 |
|---|---|---|---|---|
| **A. Composed run text** | (CP-8, cp8.what_changed, value) | `_resolved(claim.text)` keeps `[gap]` chips, `src/deploy_workflow/owners/cp8.py:2153-2186`; the summary row is checked as CP-8-VIEW-01 at :2145-2150 | raw | registered, correct |
| **B. Analyst run text stored raw** | (CP-L10, TL10.3, assessment) on topic rows and the overall row; (CP-L10, TL10.3, credit_transmission) | `prose_issues` at `cpl10.py:1060-1073` | :804, :809-811, :826 | **raw token (regression)** |
| B | (CP-2H, T2R.10, gap / why_it_matters / affected_analysis / action) | `_prose` at `cp2h.py:1523-1541` and `:1608-1614`; it binds the module's cells plus CP-1 copies kept under their own ids (:1655-1659, :2063) | raw at `cp2h.py:1413-1424` | **raw token (regression, new)** |
| C. Validated, but spelled before storage | CP-2A T2B.9 (`cp2a.py:1199-1211`, `_spelled` :1272); CP-2G T2H.9 (`cp2g.py:2149-2178`); the core composers' `text()`: `business_context.py:1099`, plus the matching method in `cp2_synthesis`, `cp3_relative_value`, `cp4_legal` and `cp6_committee` (T3.*, T4.*, T4C.*, T4D.*, T4F.* and others) | yes | spelled; no token stored in any fixture | shown as written, correct |
| D. Run text that reaches claims only | rationales in cp1c (`:1326-1376`), cp1d (`:1588`, `:1618`), cp2a (`:1320`, `:1341`), cp2g (`:2307-2386`), cp2h views and overall (`:1730-1743`), cp4c (`:2287-2338`); every `ref()`/`slot()` string (cp2d and cp3c claims use the template) | — | not facts | — |
| E. `RunText` type, but no reference can resolve | CP-DR TDR.2 answer (digit check `cpdr.py:274-276`, stored :657); CP-3D summary; CP-2E text (`digit_free` `cp2e.py:632-635`). Every one of the module's own fact ids contains a digit, so the digit ban leaves no token that can resolve. | — | raw | free text, correct |
| F. Free or verbatim text | CP-1C T1C.7 gaps (prohibited-word check only, `test_method_cp1c.py:812`); CP-DR question, description and locator; CP-8 T7.2 quotes; CP-4 T4C.6 definitions; CP-5 rationale (no references allowed, `cp5_integrity.py:604-608`); the core's label brackets such as "[Insufficient Information]" and "[Management Language]" | — | raw | as written, correct |

Free text in the same tables as class B:
- **TL10.3:** screen_item (topic label), evidence (composed fact ids), screening_implication (disposition), confidence (enum) and source_refs ("CP-1 <label>").
- **T2R.10:** id ("CP-2H-GAP-nnn") and severity (enum).

### The rule

- **Key:** (module_id, table_id, field), taken from `Fact.table_id` and `Fact.field` (`contracts.py:164-171`).
  - A table key is too wide: TL10.3 and T2R.10 mix run text and free text in different columns.
  - A field name alone is ambiguous: `value` is everywhere, and `gap` also exists in T2B.9 (spelled) and T1C.7 (free).
  - row_id varies by topic or gap row, so it can't be part of the key.
- **Behaviour:** inside a registered field, any `prose._RESERVED` character sends the text to `resolve`, which fails closed (unchanged). Every other field is shown as written.
- **Mixing:** no field mixes free text and run text.
  - Every row of each registered field passes the prose check at entry, and that check refuses "[sic]" and "[Reserved]" as unresolved references. This includes CP-L10's overall row (`overall.rationale`) and CP-8's summary row; CP-8's decision row is built from enum words.
  - If a field ever did mix the two, the producer would have to spell its run text before storing it, as class C does. The registry can't split one field.

### Plan: one mx-feature task, built on ca17721

1. **RED tests** (expected results at ca17721):
   - `tests/test_connect_cpl10.py`: the reviewer's CP-L10 probe as a test, parametrised over `TL10.3.<t>.assessment`, `.credit_transmission` and `TL10.3.overall.assessment`. `display` and `table_display` must equal "…3.75 US$ m…". Fails now.
   - Same file: a malformed reference in `.assessment`, both a typo (`…chang|US$ m}`) and an unbalanced one (`…change|US$ m`). Must raise "does not resolve". Fails now (no raise).
   - Same file: "CP-1 Cash [sic]" in `.source_refs` shows as written. Passes now; it guards against over-registering.
   - `tests/test_connect_cp2h.py`: `{T2R.4.t01.headroom|x}` in each of the four T2R.10 fields renders "1.08x". Fails now. Plus "CP-2H-GAP-001 [sic]" in `T2R.10.g01.id` shows as written (a guard).
   - A unit test of `_carries_reference` over synthetic facts: true for every registered key when the text holds a bracket; false for (CP-L10, TL10.3, source_refs), (CP-2A, T2B.9, gap), (CP-1C, T1C.7, gap) and (CP-2H, T2R.10, id). Fails now on the CP-L10 and CP-2H keys.
2. **GREEN:** change `src/deploy_vii/report_view.py` only (`render.py` does not change):
   - Replace `_RUN_TEXT_TABLES` (:1604) with:
     ```python
     _RUN_TEXT_FIELDS = frozenset({
         ("CP-8", "cp8.what_changed", "value"),
         ("CP-L10", "TL10.3", "assessment"), ("CP-L10", "TL10.3", "credit_transmission"),
         ("CP-2H", "T2R.10", "gap"), ("CP-2H", "T2R.10", "why_it_matters"),
         ("CP-2H", "T2R.10", "affected_analysis"), ("CP-2H", "T2R.10", "action"),
     })
     ```
   - In `_carries_reference` (:1615), test `(module_id, fact.table_id, fact.field) in _RUN_TEXT_FIELDS`.
   - Rewrite the comment and docstring to name the sources, with the file:line refs above.
   - No try/except. The signature is unchanged.
   - Exact prototype: `probes/apply_round4_prototype.py`.
3. **D12:** one `post_import_patches` record for `report_view.py`.
   - prior = `c2040a50d5cb912cc9f9addcd1db9cccc164db143fa57e00974067fbf5d2704b` (ca17721).
   - imported_sha256 = `c934d501…` (as in the round 3 record); project_commit = the GREEN commit.
   - Run `probe_d12_strict.py`. It should flag only 3e5b537, 24f879a and 8aef58d.
4. **Must stay green:**
   - `test_connect_cp8` (item 31, 45 and 49 tests and round 3's tests), `test_connect_cpdr`, `test_connected_render`, `test_legal_render`, `test_earnings_render`, all `test_chart_render_*`, `test_method_cpl10`, `test_method_cp2h`, `test_connect_cpl10`, `test_connect_cp2h`.
   - Probes c1, rule, e and `token-plan/probe_scope_markers_round3.py` exit 0.
   - `ruff format --check` and `mypy --strict` pass.
   - `ruff check` keeps one SIM102 at `report_view.py:312`. It already fails at base 2f345c2, so it goes to the owner.
5. **Genuine reruns:**
   - G2 cp8 ×3, plus cpdr, cpl10 and cp2h.
   - `tests/test_owner_cpos.py`, `test_owner_cp8.py`, `test_owner_cpl10.py` and `test_owner_cp2h.py`.
   - These also cover round 3's step 6, which has never run.

### Probes and exit codes (base 2f345c2 / ca17721 / prototype)

| Probe | Base | ca17721 | Prototype |
|---|---|---|---|
| `keep/round3-review/probe_cpl10_analyst_reference.py` | 0 | 1 | 0 |
| `keep/s53-conf/probe_c1_free_text_bracket_render.py` | 1 | 0 | 0 |
| `keep/token-plan/probe_rule.py` | 1 | 0 | 0 |
| `keep/stage4-review-arch/probe_e_report_data_payload.py` | 0 | 0 | 0 |
| `keep/token-plan/probe_scope_markers_round3.py` | not run | not run | 0 |
| `<S>/round4-plan/probes/probe_cpl10_all_fields.py` | 1 ([sic] raises; unbalanced token not refused) | 1 (3 fields raw, malformed not refused) | 0 |
| `<S>/round4-plan/probes/probe_cp2h_gap_reference.py` | 1 ([sic] raises); 0 with `--no-sic` (spelled 1.08x) | 1 (4 fields raw) | 0 |
| `<S>/round4-plan/probes/probe_block_table_raw.py` | 0 | 0 | not run |
| Survey: 16 `test_method_*` files with the plugin | — | all exit 0 | — |
| Prototype fast tests: 8 files from step 4, `-m "not genuine"` | — | — | 1621 passed, 1 xfailed, exit 0 |
| Prototype: `test_connect_cpl10` + `test_connect_cp2h` | — | — | 232 passed, 1 skipped, exit 0 |

`probes/run_survey.sh` reads a tree at `<S>/round4-plan/tree`, which is now deleted; re-extract ca17721 there before rerunning it.

Not verified: the core composers' fixtures for cp2_synthesis, cp6_committee and business_context were not run under the survey plugin; I traced them statically. The plugin does not record facts built through `model_validate`. The CP-DR and CP-3D claim that no reference can resolve is static reasoning, not probed. The prose-block path (`_prose_lines`) for the new keys was not exercised: TL10.3 and T2R.10 are bound as table blocks, not prose blocks. The RED tests are specified, not written. There was no genuine, G2 or CP-OS run, no full suite and no D12 strict probe.
