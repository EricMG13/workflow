# T3 fix round 1 brief (controller ruling)

H1, C1, M2, M3 and L1 are one defect class: a test depends on a file through a reference other than a Python import. Fix the class with one rule set, not per site. The rules below replace plan T3 steps 2-5; steps 1 and 6 stay.

Definitions. P = a changed path from `git diff -z --name-only --no-renames BASE...HEAD` (NUL-split, decoded utf-8 with surrogateescape: the T2 H1 defect class, shared). B = basename of P. A(P) = P's directory names except the first component (for `cases/goldens/x/m.json`: `goldens`, `x`). L(F) = the string literals of a `.py` file F under `src/`, `tests/`, `cases/` (ast.Constant str and the constant parts of f-strings).

ALL (every test file): P is `pyproject.toml`, `uv.lock`, `.python-version`, any `conftest.py`, anything under `.github/`, or `cases/prove/affected_tests.py`.

Seeds(P), applied to every P whatever its type or location:
1. P is `.py`: P's module(s) in the import graph, plus every F with a literal equal to one of P's module names (dotted name; bare stem for files under tests/) - L1.
2. Every F with a literal containing P, or a literal containing B together with a literal (same F) equal to or containing a name in A(P) - C1, M2, M3, H1.
3. P is non-`.py` under `src/<dir>/...`: every `.py` in P's own directory (old step 4).
4. Seeds still empty and P non-`.py`: every F with a literal containing a name in A(P) (old step 5, generalised).
5. Seeds still empty: nothing when P is under `docs/`, `work/`, `.claude/` or ends in `.md`; otherwise ALL.
Tests = test files (tests/**/test_*.py) reached from the seeds through the reverse import graph (a seed that is a test file counts). Document in the docstring that the graph and literals are read from the working tree, which must be HEAD (I2).

Also: M4 (ruff SIM102 and format); L2: move pr-heavy's concurrency block to job level; pr.yml and pr-heavy.yml treat pytest exit 5 (all selected tests deselected by `-m "not live"`) as success with a printed message, any other non-zero fails.

Process: commit 1 = new tests only (`test(prove): selector misses non-import references (RED)`), one per class case: a path-loaded .py under cases/, a .py pinned by a hash literal, a docs/ file read by a test, a .md under src/<pkg>/<dir>/ read via split path parts, a fixture .md, a module named only in a string literal, a quoted (non-ASCII) path. Commit 2 = the fix (`fix(prove): selector follows path and name literals (review T3)`). Both end with the Co-Authored-By line. Touch only cases/prove/affected_tests.py, tests/test_prove_affected.py, .github/workflows/pr.yml, .github/workflows/pr-heavy.yml. After commit 2 run every probe in scratchpad/t3-review/ with system python3 -I and report each exit code (each must exit 0), and report the fast/heavy counts for `63a5bbb8~1 63a5bbb8` and `d3e27e74~1 d3e27e74` and the stdout of `fc7fe5c5~1 fc7fe5c5`.
