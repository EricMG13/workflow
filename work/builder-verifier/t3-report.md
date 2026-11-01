# T3 report (mx-feature; saved by the controller)

Branch bv-t3, commit 625b5585 (from 50d301e4), worktree .claude/worktrees/agent-abb2e1b657aa756b8. Files: .github/workflows/pr.yml (79), pr-heavy.yml (44), cases/prove/affected_tests.py (208), tests/test_prove_affected.py (107).
Builder manual runs: 63a5bbb8 fast 106 files, heavy = the 5 HEAVY files; bad ref exit 2.
Controller gates: ruff check 1 (SIM102 at affected_tests.py:112), ruff format --check 1 (affected_tests.py:48), mypy strict 0, pytest tests/test_prove_affected.py 7 passed (1.40 s).
Controller answer key: row 3 empty exit 0 PASS; row 4 all three present PASS; row 5 test_goldens_check.py present PASS, but only via module_golden.json: stderr shows `cases/goldens/check.py -> 0`.
Controller finding C1 (Medium, under-selection): tests/test_goldens_check.py loads the checker with importlib spec_from_file_location(REPO / "cases/goldens/check.py"); a PR changing only check.py selects no test. Plan rule 5 covers only non-.py files under cases/<name>/.
Not verified: GitHub run, YAML validity, label flow, importlib-literal and relative-import paths.
