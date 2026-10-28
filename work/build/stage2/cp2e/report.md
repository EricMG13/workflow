# CP-2E Stage 2 report (mx-feature)

CP-2E Stage 2 report. Commit 1ea0065 on claude/s2-cp2e (cut at lane tip 3f3eba4).

Done. The store runs and D3 run assertions are written but not run, as the brief says. Diff is 1438 lines, over the 800 cap; tests are 880 of them.

**Files**
- `src/deploy_workflow/owners/cp2e.py`: schema, `RULES`, `submit`, `probe`, `ENTRY_VALIDATOR`, report/module builders, reader, and the backlog fixes.
- `src/deploy_workflow/owner_workflow.py`: registration rows only.
- `src/deploy_vii/bindings/cp2e.py` (new), `bindings/shipped.py`, `src/deploy_vii/methods/cp2e.md` (new).
- `tests/test_connect_cp2e.py` (new, 107 tests), `tests/cp2e_runs.py` (new, with `cp2e_closed`), `tests/test_owner_cp2e.py` (new, deferred).
- `tests/test_method_cp2e.py`: one line (backlog Info 2).

**Lease line to symbol**
- Public API: `STEP_IDS`, `SCHEMAS`, `QUALIFICATION`, `probe`, `RULES`, `submit` and `cp2e_reader` are in `owners/cp2e.py`. The submission schema is `MacroFxSubmission`.
- `macro_fx` is `macro_fx(*, pack, submission)`. `cp2e_module(*, report, inputs, attempt)` and `validate_macro_fx` are unchanged in name.
- Not built: `cp2e_upstream`. CP-2E reads no operand from CP-0, and `settle` already carries the CP-0 limitations, so it would be unused code.
- Adapter: `_inputs(pack, submission)` fills the Stage 1 `MacroFxInputs`. The binding source (manifest `run` and `step_scope`) is the pack plus the financial scope. `submit`, `probe` and `ENTRY_VALIDATOR` all go through `_validate_step`.
- `OWNER_SPECS["CP-2E"]` is exactly the lease line, with `sources=True` (matching `_OWNER_SCOPES`, so the G1-X guard passes). Rows were added to `SUPPORTED_ANALYTICAL`, `_CORES`, `_QUALIFICATION`, `_PROBES` and `_ENTRY_VALIDATORS`, all append-only.
- No `_PRECHECKS`, `_VIEWS` or `precheck`, per the lease. The "view matches view_tree_draft" test does not apply because the step has `inputs="none"`.
- `SHIPPED_MAPS` gets `CP2E` at the end. The lease states no position.
- The nine bindings: T2F.1-6 and T2F.8 go to the Evidence rail, T2F.7 and T2F.9 to the Limitations rail, slot prefix `cp2e-`. The rails need no `_Spec` row, and no `MODULE_FAMILY` row was added.

**Backlog**
- Done: guard-limit notes in `methods/cp2e.md` (rule W, the round 10 sign rule, and the five item 8 comma costs), written with the code.
- Done: both r13 Infos. Info 1 now compares the normalised `reference_rate` with the normalised quote. Info 2 is the `w-minus` case, which now uses a wrapped quote. Removing the exemption in `_split` turns it red.
- Done: blank-quote inventory. Inventory result: no accepted-blank defect. A blank quote was already refused, but as "quote not found". It is now `<path>.quote: empty text`, raised before the page check. A scope error still comes first.
- Done: `listed_issues`/`clipped`. `RULES` lines are fixed text, or come from the sanctioned `unread_citation_issues`; a 50-page payload is bounded to at most 20 lines of at most 600 characters.
- Blocked on LEAD, not built: the label-decimal question (`spread 25.5`) and the owner's `fx.` paths item.
- Blocked on LEAD: U+2800 and Cc/default-ignorable blanks wait on the `is_blank` batch. My tests use `""`, spaces, U+200B and a newline.

**Rulings**
- Q1, `DeliveryScope` row: the lease says only "G2 `owner_rendering.py`: one `DeliveryScope` for `slice-cp2e-sensitivity` (module page and rails)." The run is pathway `credit_snapshot`, `requested_modules = ("CP-2E",)`.
- Q5: no schema class has a custom validator, and a test asserts it. Hostile text (8 cases) raises only `ValueError` subclasses.
- Q6: `cp2e_reader` stays in `owners/cp2e.py`.

**Test-first**
- Backlog tests were red first (blank quote: "quote not found" instead of "empty text"). Every connection test was red until the code existed (the collection error for the missing bindings module).
- Info 2 is a test-strength change, shown by the mutant above rather than by a red test of its own.

**Gates (all exit 0)**
- `ruff check` and `ruff format --check` on the 8 changed files.
- `mypy --strict` on the changed src files and tests.
- The fast pytest set: 893 passed in 17.6s.
- Mutants, from a full temporary copy: 47 killed, 0 survived. They cover each adapter and report field, each registration row, `SHIPPED_MAPS`, each binding row, the reader coordinates, and the blank and `reference_rate` fixes. The script is at `<S>/cp2e-s2/mutants.py`. 7 survived the first pass and were killed with new tests.

**For LEAD**
- `methodology.json`: none.
- `docs/TOOL-CONTRACT.md`: the matrix row from the lease prerequisite 3. CP-2E `macro_fx` gets `search_pack` and `read_pages` over the financial source only, no `extract_statements`, no `read_inputs`.
- D2 view row: none, because there is no view.
- Protocol §5 follow-up: `_validate_step` parses model text only via `json_object` then `exact_json` then `model_validate_json`. The `host.py:675` Q5 question is untouched.

**Deferred commands for `work/build/deferred-runs.md`**
- `PYTHONPATH=src "<venv>/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp2e.py`
- `python3 -I cases/cp2e-owner/builder/build.py && shasum -a 256 cases/cp2e-owner/*.json`
- `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py`, and the render runs.

**Not verified:**
- `submit`, `probe` and the `OwnerWorkflow` registration were never exercised against a real `Execution`. The fast tests use duck-typed stores, so `submit_step`, `finish`, `_with_rules` and `probe_one_step` are untested live.
- The settled-run assertions are written but unrun: `tests/test_owner_cp2e.py` and `cp2e_closed`.
- The oracle cases are not written: tamper, `stale_binding`, blocked, begin-refused, `extract_statements` and `read_inputs` refusals as an integrated run, and the hand-built-page refusal. A first draft of the tamper and stale tests was a placeholder, so I removed it.
- D3 is OPEN; the reader test only pins what is exposed.
- A citation quote is chosen as the first submission quote for that page. The oracle does not pin it; I tested only that it is a verbatim span, via `citation_issues`.
- No browser or render run, and `report_view.build` was not run.
- Info 1 widens what the validator accepts (a U+2212 name now occurs). Please confirm that is wanted rather than just no longer a fail-closed Info.
- The 800-line PR cap and `jscpd` were not run; no CP-2E `Calculation` or `MODULE_FAMILY` question arises.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a (store runs deferred; fast gates passed first time after test fixes, so y for those)
