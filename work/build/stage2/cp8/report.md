# CP-8 Stage 2 report (mx-feature)

CP-8 Stage 2 report. Commit da84f8d on claude/s2-cp8 (Step 0: HEAD was 3f3eba4, tree clean). Fast gates all exit 0.

FILES, with lease line -> symbol (all in worktree s2-cp8)
- src/deploy_workflow/owners/cp8.py (core extended):
  - MODULE_ID, STEP_ID, STEP_IDS (tuple of str), SCHEMAS, QUALIFICATION (implemented).
  - RULES(text, seen) -> absence rule first, then the product's unread_citation_issues. Text is read only through live.schema.json_object. No caller-quoting line of its own.
  - cp8_upstream(*, store, attempt) -> Upstream. This is the one store adapter, used by submit, probe and the entry validator. It reads the bound CP-0 (authority from T3), the run as_of, and the settled CP-6 call when CP-6 is bound.
  - validate_ledger, derive and decision_ledger were already there (Stage 1).
  - LedgerOutput (the retained step output) and cp8_module(*, report, inputs, attempt). The tail input is "decision-ledger-submission".
  - ENTRY_VALIDATOR (= _validate_step), probe (via cp1a.probe_one_step), submit (modelled on submit_cp2_step and the G1-X fake core).
  - cp8_reader(store, head) -> Cp8Head, in owners/cp8.py per Q6. It exposes head sha, status, overall label and process, direction and magnitude per measure, window days, hit rate or its absence reason, decisions recorded and required, and own limitations. A missing cell reads as None, never 0.
  - Blank-quote fix in _cite.
- src/deploy_workflow/owner_workflow.py: appended CP-8 rows only, in the import, SUPPORTED_ANALYTICAL, _CORES, _QUALIFICATION, _PROBES, _ENTRY_VALIDATORS and _default_specs. The OWNER_SPECS row is sources=True, inputs="none", rules="journaled", owner_core. No _VIEWS or _PRECHECKS row, because the lease has none.
- src/deploy_vii/bindings/cp8.py (new): cp8.what_changed -> what-changed; T7.1-T7.7 -> evidence; T7.8 -> limitations; slots prefixed cp8-.
- src/deploy_vii/bindings/shipped.py: CP8 appended last (the lease states no position).
- src/deploy_vii/methods/cp8.md (new): the frozen draft adaptation record (28 rows kept) plus a "Guard limits" section.
- tests/test_connect_cp8.py (new, 320 tests, about 2 s), tests/cp8_runs.py (driver cp8_closed), tests/test_owner_cp8.py (deferred, unrun).
- No change to report_view.py (what-changed already exists), methodology.json, TOOL-CONTRACT, cases/ or any engine.

BACKLOG ROWS
- Rule W note: done.
- Round 10 sign rule note: done.
- Unsigned-grammar limitation: done.
- Item 2 guard limit: done.
- Item 8 comma costs, including the date day: done.
- `_labelled` narrow `,<digit>` join: done.
- Each note is also pinned by a characterization test. These pass as Stage 1 stands, so a note cannot drift from the code.
- Blank citation quote: CP-8 had the defect. I inventoried 18 quote sites, and all go through _cite. The fix refuses with `<path>.quote: empty text`, after the pack, scope and source-rule checks and before the page-occurrence check. It is tested for every site against 8 blank values (the schema's own min_length already refuses ""). Medium per the backlog, now fixed.
- listed_issues/clipped row: n/a. CP-8 has no precheck. RULES reuses the product's bounded unread_citation_issues and a constant absence line, and no f-string site was added.
- "Every module" owner items (30 asserts, jscpd): not CP-8's, so not touched.
- Nothing blocked on a LEAD re-pin.

TEST-FIRST EVIDENCE
- Notes: methods file missing -> 6 red. Blank quote: 144 red with the "quote not found" issue where "empty text" was expected.
- Plug-in parts and RULES: 77 red with AttributeError (no RULES, SCHEMAS or STEP_IDS).
- Adapter, registrations, bindings and reader: red at collection (no deploy_vii.bindings.cp8). They were not individually red for the right reason, because the collection error hid them.

GATES (exit codes)
- pytest of test_connect_cp8, test_method_cp8, test_owner_g1x, test_host_h1 and test_defect_classes_selfcheck: 1224 passed, exit 0, 17 s.
- ruff check and ruff format --check on the 7 changed files: 0.
- MYPYPATH=src:tests mypy --strict on the same files: 0.
- Mutants: 28, each run against a full temporary copy of the worktree with PYTHONDONTWRITEBYTECODE=1. They cover each adapter field (as_of, authority, cp6, cp6 order), the tail input id and hash, the blank fix, the RULES rules, STEP_IDS, QUALIFICATION, the reader fields, each registration row, the shipped row and each binding. All 28 were killed. One (the RULES optional field) first survived, so I added a per-absence-site test. The script is `<S>/cp8-s2/mutants.py`.

FOR LEAD / PM (no edits made)
- Q1: DeliveryScope row: none in lease. Q8: MODULE_FAMILY: no row added or proposed.
- D2 view row for TOOL-CONTRACT: CP-8 `decision_ledger` has no view (inputs="none"). Pack tools are `search_pack` and `read_pages` over prior_case, update and market_update. `read_inputs` and `extract_statements` are refused not_permitted. The oracle pins `what-changed` as populated (not collapsed). The lease's optional `collapsed=True` change (its question 5) is not applied.
- methodology.json: no edit needed.
- docs/reuse/manifest.json was not edited (PM-serialised, and it needs the final commit sha). It needs these new sha256 values:
  - shipped.py: 197cb1f2…0a
  - bindings/cp8.py: 48e82f45…c005
  - methods/cp8.md: 04d23228…74d1
  - owner_workflow.py and cp8.py are not D12 files.
- Deviations to check:
  - cp8_module takes a LedgerOutput (pydantic, with run and submission_sha256), not the Stage 1 LedgerReport dataclass, because the step output has to be retained as text.
  - Non-object payload text gets a new issue, `(root): the payload is not a JSON object`. §5 forbids a raw model_validate_json parse on model text, so the core parses once via json_object and then validates exact_json(document).
  - The `view` and `precheck` plug-in parts and the view-tree test do not apply (inputs="none"). A test asserts neither exists.
  - Q5 (`host.py:675` raw parse) is untouched.

DEFERRED COMMANDS (for work/build/deferred-runs.md)
- `PYTHONPATH=src ".venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_cp8.py`
  - This is the store runs (positive and no_outcome), receipt verify plus probe, and the D3 reader pin. D3 is OPEN, and the test claims no consumption.
  - The driver is cp8_closed in tests/cp8_runs.py.
- Also at Stage 5: tests/test_owner_workflow.py, tests/test_owner_s1a.py, the source suites, tamper (the lease recipe) and the render runs.

Not verified: submit, probe, the entry validator against a real Execution, and the real SourceSession path were not run. No store run, receipt verification, tamper test, D3 run assertion or render run executed, and tests/cp8_runs.py and tests/test_owner_cp8.py were only type-checked and linted, never run. cp8_upstream and cp8_reader were tested against a test-only fake store and a Module built from oracle facts, not a real Execution. The no_record (CP-0 BLOCKED) path was not written. validate_bindings was exercised on synthetic Fact stand-ins built from the expected tables, with no citations. The new reuse-manifest sha values and the `∅ G#` run-time binding were not checked. docs/rulings/2026-10-28-stage2.md was not read, only the coordinator's summary. No CP-6 run-level case ran.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a
