## G2 coverage gaps (ruling item 28 (i) and (ii)): test specification, code at `e37b73e`

The rules below are all test-only, in `tests/test_owner_rendering.py`. No product or oracle change is needed for any pointer. Each rule passed on real fast pages and failed every one-field perturbation tried.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-gaps-spec/`, with shared helpers in `common.py`. To run one: from a `git archive e37b73e` copy, run `PYTHONPATH=src:tests <venv python> <probe> <that dir>`.

**Existing core checks.** CP-3D checks its module tables and the `fact_spelling` text (`test_connect_cp3d.py:411-436`), not the rendered page. CP-8 checks the runs of two lines in `build()` output (`test_connect_cp8.py:582-615`). For CP-4, no test checks its tables on the render. `test_method_cp4.py:420` checks the module tables, and `test_chart_render_cr1.py` checks only the CR.1 figure.

### (i) cp3d `#/cases/<c>/tables`
- **Rule.** The page has one register per entry of `render.blocks.market-against-fundamentals.tabs`: block `tab_label`/`rows` first, then `tabs[]`, in that order. Register *k* equals table `tabs[k][0]` as follows:
  - label equals `tabs[k][1]`;
  - `row_header` and column labels equal the oracle table's;
  - each row's `(row_id, label)` equals the oracle's;
  - the payload module table's `fact_ids` equal the oracle facts' `fact_id`s, and each fact's `field` equals its column field;
  - cell `state` is mapped from the oracle status: known→known, missing→gap, not_applicable→not_meaningful;
  - known cells match `shown`, with the existing `_matches_oracle_text` placeholder handling;
  - gap cells fullmatch `∅ G\d+`, or `∅ G\d+ n\.m\.` for not_applicable.
- **Evidence.** Oracle `cp3d-owner/expected.json` `#/render/blocks/.../tabs` and `#/cases/<c>/tables`. Producer: `report_view.py:1511-1557` (`_slot`) and `:2085-2131` (`_block`).
- **Probe.** `probe1_cp3d_tables_exit0.py`, exit 0. It ran on 3 cases built with `test_connect_cp3d._module`. Five perturbations each fail: known cell text, row label, column label, passport Locator, gap cell changed to 0.

### (i) cp4 pointers
- **`sections/<id>/tables`.** Owner and kind match. Register *j* equals `#/<key>/CP-4/tables[sections[id].tables[j]]` with the same checks as cp3d (tab labels excepted: the oracle has none). One difference: a known fact with `text` must match that text exactly (`cell_notation.text` = "exact displayed text"). Numeric cells are checked only by the literals below. `key` comes from `#/gap_false_same_definition/CP-4/corrected_resubmission/expected_same_as`, which gives `gap`.
- **`displayed_literals/<key>`.** For each table/field, every row's cell equals the literal. Three prose values get a closed mapping:
  - "gap spelling, a G# gap id (never 0)" and "gap spelling (G#)" mean state is gap and the cell fullmatches `∅ G\d+`;
  - "names the missing incorporated Schedule A" means the text equals the oracle T4C.6 `definition` text and contains "Schedule A";
  - any other non-literal fails loudly.
- **`gap_false_same_definition`.** Checked against the `gap` set. In addition, `covenant-tests-headroom` never shows "3.00x", "75.0%" or the verdict listed at `#/gap_false_same_definition/CP-4/semantic_acceptance/values_…_must_not_qualify`.
- **`evidence_rail_tables` and `limitations_rail_tables`.** Each is a subset of the table ids in payload `modules[CP-4].tables`, which is the lease's wording.
- **`limitations_rail_module_limitations`.** Payload `modules[CP-4].limitations` equals `dict.fromkeys(settled_limitations + inherited_limitations.literal_head_from_CP-0 + payload modules[CP-1].limitations)`. Source: `execution.py:957` and the oracle rule text.
- **Probe.** `probe2_cp4_pointers_exit0.py`, exit 0, on the 3 cases. The CP-4 bindings' evidence and limitations tables equal the oracle lists. Nine perturbations fail.

### (i) cp8 `lines_positive` and `#/cases/<c>`
- **Rule.** Lines map 1:1 to the `cp8.what_changed` rows of `#/cases/<c>/tables`. For positive, also assert that their `shown` list equals `lines_positive`.
- **Gap fact.** Runs are exactly `[text "<column>:", gap]`, and the gap run matches the status pattern (`report_view.py:1645-1647`; label is the column, `cp8.py:1327`).
- **Known fact, chip.** A trailing chip is a `fig` run with `ref_id` matching `[CKS]\d+` and text equal to `ref_id`. If the fact has a `calculation_id`, a K chip must be present and its passport `Calculation` equals the oracle `calculation_id`. Otherwise an S/C chip is present if and only if `cites` is non-empty.
- **Known fact, text.** The other runs are joined with " " and white space is collapsed, as the `<p>` shows them (`app.js:251-263`). The result must match `shown`. Every run is `pen` if and only if the fact is `analyst_judgment`.
- **Probe.** `probe3_cp8_lines_exit0.py`, exit 0, on the real core (`test_method_cp8.report_of`). Seven to eight perturbations fail per case, including the token gap in no_outcome.

### (ii) `cites` normaliser (Acceptance 1)
- **`_page_cites(payload, module_id, fact_id)`.** Take the `report.index.facts` entry with this `coord.module_id`/`fact_id`. Keep its `ref_ids` with a C or S prefix, in index order, with no de-duplication. Each ref maps to `[Source, Locator]` from its passport fields (`report_view.py:772-871`; allocation is per citation, in order). The result must equal the oracle cell `cites`.
- **Finding the fact for a cell.** If the register's columns are `["Value"]` and the row id is a fact id, the row id is the fact. Otherwise use the unique payload module table whose `(row_id, label)` rows and column labels equal the register's, and take `rows[r].fact_ids[c]`. If there is not exactly one match, assert.
- **Which oracles carry list `cites`.** Survey: `probe0_cites_survey_exit0.py`.
  - At a block pointer: only `s1a-credit-snapshot`, in `company-operating-model` and `company-profile`, both cases, 43 cells each.
  - At secondary tables: cp3d, cp8, and cp4 (which also has prose run-time cites).
  - None in cp1c, cp1d, cp2a, cp2g, cp2h, cp4c, cp2d, cp3, cp2e, cpdr or cpl10.
- **Probe.** `probe4_s1a_cites_exit0.py`, exit 0, on a real render of a CP-1A module rebuilt from the oracle tables. Three perturbations fail: passport Source, index ref dropped, index ref duplicated. Probe 1 also applies it to the real cp3d citations.

### Functions and tests to add
- **Helpers:** `_registers`, `_page_cites`, `_resolve_cell_fact`, `assert_cells_cite_oracle` (s1a), `assert_cp3d_tables`, `assert_cp4_pointers`, `_visible_line_text`, `assert_cp8_lines`.
- **`_check_scope_run`:** for complete outcomes, call the scope's assert after `assert_render_node_owner` (passing `payload` and the case), and call the cites check after `assert_block_equals_oracle` for s1a.
- **Fast tests** (each accepts the page, then fails a perturbation): `test_fast_cp3d_tables_rule_on_real_pages[3 cases]`, `test_fast_cp4_pointer_rule_on_real_pages[3]`, `test_fast_cp8_lines_rule_on_real_pages[2]`, `test_fast_cites_normaliser_on_s1a_page[2]` and `test_fast_cites_normaliser_on_real_cp3d_page`.
- **Gates:** `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict`, then `-k fast` on the file.

### Genuine runs to repeat
`tests/test_owner_rendering.py::test_genuine_deferred_complete_cases[...]` with these ids:
- `s1a-credit-snapshot-positive`, `s1a-credit-snapshot-gap`
- `cp3d-fp03-market-positive`, `cp3d-fp03-market-gap_no_recovery`, `cp3d-fp03-market-gap_no_market`
- `cp4-fp04-covenants-positive`, `cp4-fp04-covenants-gap`, `cp4-fp04-covenants-gap_false_same_definition`
- `cp8-fp01-what-changed-positive`, `cp8-fp01-what-changed-no_outcome`

Also `test_genuine_deferred_refused_cases[cp8-fp01-what-changed-no_record]`, which goes through the changed `_check_scope_run`.

### Open questions for the reviewer
1. **cp8 decision line.** The page shows "Value: ∅ G#", but `lines_positive[0]` is just "∅ G#". The rule expects the product's label run, the same convention the s1a oracle builder writes (`build_s1_oracle.py:741-744`). Is that "equal"?
2. **cp8 white space.** The rule collapses white space as the browser does. Token runs carry their own spaces (`test_connect_cp8.py:588-592`).
3. **`cites` beyond s1a.** The lease requires `cites` only for s1a, and R2.8 cell fields exclude it. Should cp3d and cp8 tables also be checked? It costs nothing extra.
4. **CP-1 part of the cp4 limitations.** It is read from the page's CP-1 module. The oracle says "bound at run time".
5. **s1a fast fixture.** The fixture uses test-only quotes, because the oracle stores none and the normaliser ignores quotes. Is that acceptable under the no-stub rule?
6. **Rails for cp3d and cp8.** The R2.8 item 2 rails for cp3d and cp8 are outside this brief and are not asserted beyond fact membership.

Not verified: no genuine runs were done. The rules ran only on fast pages that hold just the owner's module (no CP-0 or CP-1), so on a real page the passport numbering differs and the CP-1 part of the cp4 limitation rule (the payload CP-1 list) was never tested. The s1a resolver ran on a CP-1A module rebuilt from the oracle, not a real one. The cp4 subset rule only covers the lease wording. I wrote no test code.

---

## Controller rulings on the open questions (item 46; applied before review)
1. **cp8 decision line.** "Equal" means two checks. The product's label run equals the oracle column label, exactly. The remaining runs match `shown`. Neither check is dropped.
2. **cp8 white space.** Collapse white space as the browser shows it (the `<p>` the reader sees). The collapsed text must match `shown` exactly.
3. **`cites` beyond s1a.** Yes. Apply `_page_cites` wherever an R2.5 oracle cell carries list `cites`: s1a, cp3d, cp8, and cp4's list cites. cp4's prose run-time cites stay out.
4. **CP-1 part of the cp4 limitations.** Take it from the run's store, not the page: the CP-1 head's settled `limitations` via `store.head_module(head)`, as `owner_rendering.py:701` does. This checks the page against the store.
5. **s1a fast fixture quotes.** Accepted. The fast test proves the comparator; the genuine s1a cases are the real proof. Comment the quotes in the fixture as test data that the normaliser ignores.
6. **Rails for cp3d and cp8.** Add them in this batch. Their R2.5 pointers name `rails`, and R2.8 item 2 requires them. Use the same shape as cp4: the oracle's evidence and limitations tables are present on the module's payload, and module limitations equal the oracle's, split as the oracle splits them. Add a fast accept-plus-perturbation test for each. A rails gap in any other scope is noted for the whole-branch review (5.3), not built here.

---

## Revision 1 (replaces only the parts below; the rest of `g2-gaps-spec.md` stands)

I applied all seven items. Two of the requested rules contradict the code, so I changed them; both are marked **[deviation]** with evidence and need your sign-off. All six probes exit 0, and every new perturbation fails as it should.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-gaps-spec/`. Run lines, from a `git archive e37b73e` copy:
- probe0: `python3 probe0_cites_survey_exit0.py <tree root>` (corrected).
- probes 1-5: `cd <tree root> && PYTHONPATH=src:tests <venv python> <probe> <probe dir>`.

**Medium 1: `cites` on every table.**
- `assert_table_cites(payload, module_id, tables)` covers every oracle fact whose `cites` is a list of pairs, looked up by the oracle `fact_id`. Prose cites in cp4 are skipped. The count of non-empty cites checked must be at least 1.
- Pointers:
  - cp3d: `#/cases/<c>/tables`
  - cp8: `#/cases/<c>/tables`
  - cp4: `#/<key>/CP-4/tables`
- Non-empty cites checked:

| Scope | Case | Count |
|---|---|---|
| cp3d | positive | 45 |
| cp3d | gap_no_recovery | 39 |
| cp3d | gap_no_market | 7 |
| cp8 | positive | 58 |
| cp8 | no_outcome | 21 |
| cp4 | each of the 3 cases | 61 |

**Medium 2: no fallback in `_page_cites`. [deviation]** I removed `or [{"ref_ids": []}]`. I did not use the requested wording ("a known fact has exactly one entry; a gap fact may have none"), because the code does the reverse:
- `build_index` (`report_view.py:780-871`) always gives a gap fact an entry, because it allocates a G# for it.
- A known fact with no citations and no `calculation_id` gets no entry.
- Under the requested wording, a known uncited fact would fail on every real page.

The rule I used instead is driven by the oracle fact:
- an entry is required if status is not known, or `cites` is non-empty, or `calculation_id` is set;
- if required, assert exactly one entry; otherwise assert none, and the cites are `[]`.

It accepts every table fact in cp3d, cp8 and cp4. For s1a the expected fact is `{status: known, cites: <cell cites>}`; only known cells carry `cites` (`build_s1_oracle.py:703`).

**Low 3: rails for cp3d and cp8.**
- Pointers:
  - cp3d: `render.blocks["evidence rail"]` and `["limitations rail"]`
  - cp8: `render.rails.evidence` and `.limitations`
- Each listed table must be one of the table ids on that module's payload.
- **[deviation]** For limitations I used `dict.fromkeys(own_limitations + [SYNTH] + inherited_limitations)`, with SYNTH in the middle for a synthetic run. SYNTH is "Synthetic case; not real issuer qualification". The test asserts that the oracle's `inherited_limitations` contains it.
  - Why: settle moves SYNTH into `own` (`execution.py:476-481`). `inherited_limitations` then drops it from the inherited list (`:366`), and the view joins own then inherited (`:957`).
  - The requested rule, `dict.fromkeys(own + inherited)`, puts SYNTH last. On a page with settle-built limitations it was not equal in all 5 cases (probe5 prints this). The reviewer's probe passed only because the fast cp3d fixture leaves SYNTH in `inherited`.

**Low 4: CP-1 part of the cp4 limitations.** The rule follows `#/<key>/CP-4/inherited_limitations/rule` word for word:
- `inherited = [x for x in dict.fromkeys(literal_head_from_CP-0 + cp1.limitations + cp1.inherited_limitations) if x not in settled_limitations]`
- page = `dict.fromkeys(settled + inherited)`
- `cp1` is `store.head_module(<CP-1 head>)`, per ruling 4.

**Low 5:** the label run's text is exactly `"<column>:"` with the colon, for example `"Value:"`.

**Low 6:** the cp4 field check now compares with the field of the oracle column named by `wf["column"]`. Probe2 is fixed to match.

**Probe exit codes:** probe0 0, probe1 0, probe2 0, probe3 0, probe4 0, probe5 0 (`probe5_rails_cp3d_cp8_exit0.py`, new).

**New perturbations (all fail as they should):**
- probe1, cp3d, each of 3 cases:
  - the reviewer's Medium 2 perturbation: index entry removed for a fact whose oracle cites are `[]`;
  - index entry of a gap fact removed;
  - index entry duplicated.
- probe2, cp4, each of 3 cases:
  - rail-table cited fact: index entry removed;
  - rail-table cited fact: passport Locator changed;
  - CP-1 inherited-only limitation dropped from the page;
  - fact `field` changed.
  - The rule without CP-1 `inherited_limitations` disagrees with the product-built page.
- probe3, cp8, both cases:
  - rail-table cited fact: index entry removed;
  - rail-table cited fact: passport Locator changed;
  - rail-table fact: ref order reversed.
- probe5, cp3d (3 cases) and cp8 (2 cases):
  - a rail table missing;
  - an inherited limitation dropped;
  - an own limitation reworded;
  - the limitations reversed.

**Builder changes:** add `assert_table_cites`, change `_page_cites` to the rule above, and add `assert_rails_cp3d` / `assert_rails_cp8` with fast tests that accept a page and fail a perturbation. Call them from `_check_scope_run` for complete cases. The genuine ids to rerun are unchanged.

Not verified: no genuine run was done. Probe5 rebuilds the settled limitations by copying `execution.py:476-481` and calling the real `inherited_limitations`. Probe2's CP-1 head is a probe-only module, not a store head. The required-entry rule was checked on fast pages of cp3d, cp4 and cp8, and on the oracle-built s1a page, not on genuine pages of every scope.
