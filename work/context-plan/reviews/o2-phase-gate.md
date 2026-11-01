# O2 phase gate results (HEAD b54f6cbf, 2026-11-01)

Gate run, no code changed. Fast only (B16): no RUN_PROMOTION, no whole suite, cp4 tests skipped.
Python: `PYTHONPATH=src .venv/bin/python`. Probe root: the session scratchpad; logs in `scratchpad/o2gate/`.

## 1. Tests (PASS)

| File / nodes | Result | Wall |
| :--- | :--- | :--- |
| tests/test_html_text.py | 34 passed | 5 s |
| tests/test_run_inputs.py | 53 passed | 1 s |
| tests/test_run_pathway.py | 39 passed | 2 s |
| tests/test_goldens_lines.py | 6 passed | 3 s |
| tests/test_line_locators.py | 28 passed | 1 s |
| tests/test_o2_done_when.py -rs | 10 passed, 2 skipped (lines 432 and 470, full o2 walk, B16, deferred to CI) | 231 s |
| tests/model/test_loop.py | 68 passed | 6 s |
| test_financial_workflow.py `_evidence_issues` nodes (test_financial_evidence_refusal_preserves_prefix x4, test_prose_statement_mention_does_not_require_empty_note_extraction, test_actual_empty_standalone_statement_still_refuses) | 6 passed | 3 s |
| test_owner_workflow.py::test_binding_and_spec_accessors_mirror_the_private_fields, ::test_run_binds_to_reference_specs_not_callers_mapping | 2 passed | 1 s |
| tests/model (all) | 451 passed | 7 s |

## 2. Static checks (FAIL: 2 items in O2 files)

Files: the 7 src files, the 9 test files (incl. tests/o2_case.py, test_financial_workflow.py, test_owner_workflow.py), cases/o2-synthetic/builder/*.py (3 files).

| Check | Result |
| :--- | :--- |
| ruff check | exit 1, 2 findings, both in tests/test_financial_workflow.py (B023 line 470, RUF059 line 1131); O2 made no commit touching that file, so pre-existing. All O2 files clean. |
| ruff format --check | exit 1: `cases/o2-synthetic/builder/context_rows.py` would be reformatted (STATUS_SUFFIX line over length, one citations dict). Introduced by 752c397f/59646195 (Task 4c). Fixing it changes a frozen, pinned builder file, so the controller decides. |
| MYPYPATH=src mypy | exit 1, 134 errors in 2 files. 132 are in tests/test_financial_workflow.py (pre-existing, not counted). 2 are in tests/model/test_loop.py:934 (`rig.log.write_raw = disk_full`: method-assign and assignment), a line added by 63a5bbb8 (O2 Low batch). Counted as an O2 failure. |

## 3. Pins (PASS)

`python3 -I cases/pins.py --check` exit 0: "cases/PINS.json matches 179 paths".

## 4. Probes (PASS against the expected set; exit codes)

| Probe | Exit | Note |
| :--- | :--- | :--- |
| o2t2-adversary p01-p06, p08, p10, p12, p13, p14 | 0 | all 0 (p07, p07b-style p07 and p11 also run: 0) |
| o2t2-adversary p09 | 1 | accepted (object.__new__ tripwire) |
| o2t3-adversary p01-p08, p10, p13, p15, p16 | 0 | all 0 |
| o2t3-adversary p09, p11 | 1 | accepted (owner items) |
| o2t3-adversary p12_mutants | 1 | stale, not in the brief list: asserts `SRC.count(old) == 1` for `no_publish` against text the fix-1 round rewrote; superseded by p12_fix1 (ledger 07:18). Not counted. |
| o2t7-adversary probe_page_packs, probe_injection, probe_coverage, probe_seen | 0 | all 0 |
| o2t7-adversary probe_unit_bounds | 1 | accepted: case B (heading on the last line) fail-closed; A and C unmeasured=False |
| o2t6-review mutate_list.py | 0 | needs args `<repo root> <tmpdir>`; delete, made-up, duplicate, printed-drop all HELD |
| o2t1-review p7_stack_semantics.py | 0 | needs arg `<repo root>`; both inputs match check.visible_text |
| o5-phase-review ph05_raw_failure_keeps_provider_class.py | 0 | needs `PYTHONPATH=src:tests/model:.`; prints ProviderServerError 502 unknown |

First pass without those arguments/paths exited 1 (IndexError, ModuleNotFoundError); rerun with the arguments gave 0.

## 5. D12 (PASS)

Two manifest entries for `src/deploy_vii/live/tools.py` chain: f0cf47c6 (sha256 40414baa...) then fa95b834 (prior_project_sha256 = 40414baa..., sha256 a5451e47f7f57d56c3563dfa7e1ef7f9eef24d59d668b90ea5295aaac3ece). The file's sha256 is a5451e47f7f57d56c3563dfa7e1ef7f9eef24d59d668b90ea5295aaac3ece, equal to the newest entry.

## 6. Size (information)

33 O2 commits (ledger hashes: Task 4 c655792e, 9ea07820, a782ce22, 9de132e7; Tasks 1-3, 5-7, 4b, 4c, Lows, and O2 docs commits 05a30503, a050a290, f8a9ec7b, dab66fc4, 3f42ee2f). `git log --numstat`.

| Group | Insertions | Deletions |
| :--- | ---: | ---: |
| src | 1257 | 174 |
| tests | 3233 | 244 |
| docs/other | 85 | 3 |
| Excluding cases | 4575 | 421 |
| cases (oracle data, separate) | 18287 | 53 |
| Total | 22862 | 474 |

Excluding cases the sum is 4996 changed lines, above the 800-line PR cap (the cap applies to the PR, which the controller scopes).
