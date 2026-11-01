# T3 review (mx-precise; saved by the controller)

Spec: FAIL. Quality: FAIL. Probes: scratchpad/t3-review/ (each exits 1 while its defect is present; harness.py loads the script).
- H1 affected_tests.py:155 - every `*.md` is dropped before rules 4-5: src/deploy_vii/methods/cp1c.md (read by tests/test_connect_cp1c.py:221; also cp8, cp1d, cp3c, cp3d, cpdr, cpl10), tests/fixtures/model_testing/report_expected.md, cases/goldens/*/prepare-report.md select 0. Probes probe_md_test_reader.py, probe_md_fixture.py, probe_md_under_src_and_cases.py.
- C1 (Medium, confirmed, wider) :157-158 - cases/goldens/check.py loaded by spec_from_file_location in tests/test_goldens_check.py:15, test_goldens_lines.py:31, test_html_text.py:25 and src/deploy_workflow/model_testing/cases.py:40; a change selects 0 and misses 8 files. Probe probe_c1_path_loaded_py.py.
- M2 (plan gap) - cases/ .py used as data (hash pins in tests/test_method_cp1c.py:30-33, test_method_cp3c.py:42, tests/cp3c_runs.py:35; exec in cases/pins-context-owner/builder/build.py:104) select 0. Probe probe_cases_py_as_data.py.
- M3 (plan gap) - tests read docs/ (docs/MODULES.csv, docs/CP1D-OWNER-LEASE.md, docs/OWNER-RENDERING-LEASE.md; 9 tests) but step 2 ignores docs/. Probe probe_docs_consumed.py.
- M4 - ruff SIM102 :112 and format :48 fail (controller evidence).
- L1 (plan gap) - non-literal importlib (tests/test_owner_rendering.py:301 with literals at :309-331) and `python -c` strings (tests/test_cp1b_registration.py:92-99) missed. Probes probe_dynamic_import.py, probe_dotted_string_modules.py.
- L2 (plan-dictated) pr-heavy.yml:5-9 - any other label cancels a running heavy job (workflow-level concurrency). Probe probe_heavy_label_cancel.py.
- I1 pr.yml:30 needs T2's scope.py (merge). I2 graph built from the working tree, not the HEAD argument (undocumented).
Not verified (reviewer): ruff/mypy/pytest; any GitHub run; pytest exit 5 when -m "not live" deselects all.
