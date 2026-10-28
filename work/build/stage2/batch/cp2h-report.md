# Parallel connector: CP-2H (general-purpose, opus)

CP-2H connector report (branch claude/s2b-cp2h, base 8d5d404)

**Commits**
- d8cad1e feat(cp2h): core Stage 2 section, backlog fixes, registrations, bindings, `tests/test_connect_cp2h.py`
- 8f7929e tests(cp2h): `tests/cp2h_runs.py`, deferred `tests/test_owner_cp2h.py`, `src/deploy_vii/methods/cp2h.md`

**Lease line → symbol** (all in `src/deploy_workflow/owners/cp2h.py` unless noted)
- MODULE_ID/STEP_ID/SCHEMA_VERSION → existing constants. STEP_IDS, QUALIFICATION, SCHEMAS, SUBMISSION_INPUT="rating-triggers-submission" → new constants.
- RULES(text, seen) → `unread_citation_issues` only.
- Upstream(bound, current, cp1, cp2g) → `Upstream` (frozen dataclass, plus `inherited`). cp2g is selected from `cp2g.cp2g_reader(store, head_of(bound blob))` with `Cp2gMetrics.select` (Q6). No CP-2H reader.
- cp2h_upstream → `cp2h_upstream`. The one store adapter is `_adapted`, used by `_inputs`.
- validate_triggers → `validate_triggers`. rating_triggers → `rating_triggers`, which returns `RatingTriggersReport`: the lease's "TriggerReport" name is already taken by the Stage 1 composer result.
- context_block → `context_block`. cp2h_module → `cp2h_module`.
- submit, view, probe → `submit`, `view`, `probe` (probe through `probe_one_step`). ENTRY_VALIDATOR → `_validate_step`.
- parse_ratings, headroom, is_reached, first_year → Stage 1, unchanged.
- OWNER_SPECS row and SUPPORTED_ANALYTICAL, _CORES, _QUALIFICATION, _PROBES, _VIEWS["rating_triggers"], _ENTRY_VALIDATORS → appended after CP-2G in `owner_workflow.py`. No _PRECHECKS row.
- `bindings/cp2h.py` CP2H map: 6 tabs in `rating-triggers`, evidence T2R.1-3 plus cp1_references and cp2g_references, limitations T2R.10, slots prefixed `cp2h-`.
- `shipped.py`: CP2H appended last. `report_view._DISTRESSED["rating-triggers"]` is the _Spec row; _PRESETS is untouched.

**Backlog rows**
- B8 "any later line" pin (`terms_row_then_trailing_note`): done; mutant `after_last_line_only` killed.
- B8 guard-limit note: done, in methods/cp2h.md.
- B7: done at base (4297ab0); no xfail remains.
- Oracle files hash-checked: `_pinned` checks against PINS.json and a tamper test was added.
- f-string sites: every line that quotes caller or pack text now uses `clipped` (agency, prose, limitation, citation, rating, metric, stale). The composed message goes through `bounded_issues`. Done.
- Blank quote → `<path>: empty text` before the page check. Before this, a blank quote failed closed as a page mismatch.
- RunText check on rationales: done.
- `json_object` parse (§5 rewire, `_parsed`): done.

**Test-first evidence**
- Deviation: I wrote the core Stage 2 section before its tests. To show red afterwards, I ran the new tests on a copy with that section removed: 86 failed, mostly `AttributeError` (no submit, cp2h_upstream, view, SCHEMAS, _inputs). Only the backlog tests, the preset test and the blocked-begin test passed.
- The registration, binding and _Spec tests were genuinely red before their rows existed (KeyError, "'CP-2H' is not in list", not_permitted, missing spec/shipped). They went green after the rows were added.
- The backlog tests were written first: 28 tests.

**Gates (final tree)**
- Gate 1 (connect_cp2h, method_cp2h, owner_g1x, host_h1, defect_classes_selfcheck): 732 passed, exit 0.
- Every `tests/test_connect_*.py` in one run: 2033 passed, 2 skipped, exit 0.
- `ruff check` on the changed files: exit 0 without report_view.py. report_view.py exits 1 on the SIM102 at :293 only, which is also present at base.
- `ruff format --check`: exit 0.
- `MYPYPATH=src:tests mypy --strict` on 9 changed files: exit 0.
- `python3 -I cases/pins.py --check`: exit 0.
- Suppressions unchanged: noqa 13, type: ignore 8.

**Mutants**
29 of 29 killed, harness exit 0, run on a full copy with PYTHONDONTWRITEBYTECODE=1. They cover:
- every adapter field: scope, names, bound, current, cp1 filter, cp1 order;
- reading the CP-2G current head instead of the bound blob; inherited; never-refused current;
- appended citations: last quote on the page, first quote only, all quotes;
- every registration row: supported, core, qualification, probe, view, entry validator, spec rules, spec sources, core order;
- shipped; binding placement, label, row, slot prefix; _Spec owner and row;
- B8.

Scripts are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-batch/`: `mutate.py`, `mutants.json`, output in `mutants_run.txt`. The red run is in `red_run.txt` there.

**DeliveryScope row (verbatim)**
`DeliveryScope(scope_id="cp2h-fp05-ratings", pathway="distressed_restructuring", requested_modules=("CP-2H",), sections=("rating-triggers",), rails=("evidence","limitations"))`

**Close-release text**
1. Citation-rule conflict, oracle vs round 3 item 3. The frozen CP-2H expected.json gives several derived facts more than one quote from the same page:
   - positive: T2R.8.p01.notches, T2R.8.p01.lower_rated, T2R.8.p01.outlook_match, T2R.9.total.triggers, T2R.9.total.downgrade_down;
   - gap: T2R.9.total.triggers;
   - fixtures: the same set, plus not_calculable_down in fixture_total_loss.
   
   Round 3 would keep only the first quote per page. I applied "no frozen value moves": own citations stay the frozen concatenation. The run-time upstream citations (cp1:/cp2g: lineage, which the oracle does not enumerate) follow round 3: one per (source, page) not yet cited, first in `derives_from` order. Needs a ruling: re-pin the oracle, or accept this split.
2. `manifest.json tool_use.view_tree_draft` says the implementer commits `cases/cp2h-owner/cp2h-view-tree.json` from a product-settled head. It is not committed, because cases/ is off limits and no settled run exists yet. Owner: LEAD at Stage 5.
3. Info (merged CP-2G): `cp2g_reader` uses `next(...)` with no default on T2H.7, so a head without that table raises StopIteration rather than ValueError.
4. Rename: the lease's `TriggerReport` became `RatingTriggersReport` (the lease text needs amending). TOOL-CONTRACT row: LEAD at freeze.

**Reused files touched (D12 records for PM; the manifest is not edited)**
- `src/deploy_vii/bindings/shipped.py`:
  - imported 304230a5…f951; prior 0899560e…1fd08; new 66fa9e74aad4d5ee309c67d4cbb63230d470dac8d5a89e077d65c1f339eabc5c; commit d8cad1e;
  - reason: SHIPPED_MAPS += CP2H, appended last.
- `src/deploy_vii/report_view.py`:
  - imported c934d501…fa98; prior a073edd7…010e; new 2fe4d4673b5c638f784358255759d8e1d445f5eb6f71055929ad57f0df89c03c; commit d8cad1e;
  - reason: one `rating-triggers` _Spec row in _DISTRESSED plus a comment; the preset is unchanged.
- `owner_workflow.py` is not a reused file. New files: `bindings/cp2h.py`, `methods/cp2h.md`.

**Deferred commands (Stage 5)**
- `PYTHONPATH=src:tests python -m pytest -q -p no:cacheprovider tests/test_owner_cp2h.py`: 48 tests. They collect; only the fast driver/manifest check was run.
- G2 imports `cp2h_runs.cp2h_closed(case, root)`, with cases positive, gap, refused, blocked, cp2g_blocked.

**Not verified**
- `cp2h_runs.py` and `test_owner_cp2h.py` never ran end to end. A smoke run showed:
  - the CP-0 literal and the CP-1 source-context literal validate on the positive and gap packs (which include the ratings source);
  - refused CP-0 returns `cp1_not_authorized`.
- Unexercised:
  - the CP-1 promotion and readiness literal on the ratings pack (open question 2);
  - the CP-2A and CP-2G drivers on this pack;
  - CP-2H through OwnerWorkflow: host SourceSession, Seen from real read_pages, journaled rules, stale_binding, the t02/t03 receipts;
  - `verify_owner_run_receipt` with the CP-2H probe, and the A4 forge;
  - G2 rendering (Stage 3);
  - the binding `unit_class` choices, which no renderer reads in these tests.
- The fast store tests use seeded heads. CP-2G is settled through the real core only in the D3 test.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
