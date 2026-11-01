# Builder-Verifier gate and PR CI

User approval 2026-11-01 (open-items session): adopt the Builder-Verifier proposal with the
adversarial review's fixes 1-10; "use CI only for GitHub PRs ... test only the changed code.
Prior test took multiple hours."

Base: `codex/checkpoint` bd11a454. Branch: `claude/do-nothing-2d383c` (this worktree).
Ledger: `work/builder-verifier/ledger.md`. Reports: `work/builder-verifier/t<N>-report.md`.

Every brief: no stub or fake value standing in for real behaviour; no catch-all that hides a
failure unless the fail-open is documented and logged. Every report ends with a
`Not verified:` line. Builders run no project venv Python (refused in this harness); system
`python3 -I` for stdlib scripts is allowed. The controller runs ruff, mypy and pytest.

Why the suite took hours: single end-to-end tests run real CP-1 promotions and pathway runs
(`work/build/keep/i6/g2d-0.log`: 8 tests of `tests/test_owner_rendering.py`, 1:37:00;
`work/build/keep/s6dom/regen.log`: 2 tests, 0:38:11). Selection alone does not help when a
core module changes, so heavy files are tiered out and run only on a label.

## T1 - Docs, skills and global rules (mx-scaffold; review mx-feature)

Files: `CLAUDE.md`, `AGENTS.md`, `.claude/skills/{create,maintain,audit}-prove-it/SKILL.md`,
`~/.claude/CLAUDE.md` (outside the repo; not committed). Write the texts below exactly.

### 1a. Append to `CLAUDE.md`

```markdown

## Verifier gate (user, 2026-11-01)

Applies to plans and leases written from 2026-11-01. Work dispatched earlier finishes under
its own plan, and a closed stage reopens only for a High or Medium finding.

Before a build is dispatched, its plan or lease names per behaviour:
- **Surface**: where a user or consumer sees it: rendered `report.html`/`model.html`/
  `calculation.json`, the financial_workflow CLI, `verify_financial_slice_receipt`, the
  sealed store/receipt, or a `cases/` artifact.
- **Answer key**: a pinned file the builder did not write: `cases/*/expected.json`,
  `cases/goldens/*`, `cases/charts/*-expected.json`, `src/deploy_vii/methodology.json`.
- **Comparison**: a test or `cases/prove/*.py` check that compares the surface with the key.

The plan ends with an Answer Key table:
`| # | User / system action | Surface | Expected observable result | Comparison |`.
Expected results cite the key by file and JSON path (for example
`cases/cp4-owner/expected.json#render/sections/capacity`) instead of restating values. A row
with no runnable comparison blocks the build: run `/create-prove-it` first.

Oracle preparer (writes keys), verifier author (writes `cases/prove/`, `.github/` and the
prove-it skills) and builder (writes `src/` and `tests/`) are different agents. A builder's
test is evidence when it compares directly with a pinned key and the task reviewer confirms
it does not weaken that comparison. `python3 -I cases/prove/scope.py` enforces the path
split: PR CI per commit, the controller per builder range with `--role builder`. The
controller runs every check; a builder's report is not evidence. A task is done when its
gates and its plan's comparisons exit 0; a module is complete only as AGENTS.md defines it.
An escaped bug goes to `/maintain-prove-it`, not to a new rule here.

PR CI (`.github/workflows/pr.yml`) runs on pull requests only and runs only the tests a PR
affects (`cases/prove/affected_tests.py`). Files in its `HEAVY` list run in
`.github/workflows/pr-heavy.yml`, only while the PR carries the `heavy-tests` label.
```

### 1b. `AGENTS.md`

In "Small tasks and independent expectations", after the sentence ending
`LEAD's rulings are applied to a draft before its first independent review.`, add on the
same paragraph: `These expectations are the answer key of CLAUDE.md's Verifier gate.`

### 1c. `.claude/skills/create-prove-it/SKILL.md`

```markdown
---
name: create-prove-it
description: Use before building a new feature, surface or refactor in Deploy Workflow, or when a plan or lease Answer Key row has no runnable comparison. Maps surfaces, picks answer keys and has a verifier written for them.
---
# create-prove-it

The controller runs this skill and writes no code. Agents: oracle preparer, verifier author
and builder are three different agents (CLAUDE.md, Verifier gate).

1. **Surfaces.** List the ones the change touches; add new ones.
   | Surface | Reach offline | Comparison today |
   |---|---|---|
   | Owner oracle outputs | module tests vs `cases/<slug>-owner/expected.json` | `python3 -I cases/pins.py --check`; builder double rebuild |
   | Public goldens | `cases/goldens/<case>/` | `python3 -I cases/goldens/check.py cases/goldens/<case>/` |
   | Chart blocks | `report_view.build` + `render` | `tests/test_chart_render_*.py` vs `cases/charts/*-expected.json` |
   | CLI JSON-lines | `python -m deploy_workflow.financial_workflow` (argv: docs/RUN-GUIDE.md) | none |
   | Sealed receipt | `verify_financial_slice_receipt` | tamper tests |
   | Rendered HTML | `render_financial_slice` -> `report.html`, `model.html`, `calculation.json` | none automated; native DOM checks are manual |
2. **Reach.** Run each surface once on a frozen case. Record argv, exit code and wall time.
   No provider or live calls.
3. **Answer keys.** Present `| Method | Answer key | What it catches | Setup cost |`, in this
   order of preference:
   - an existing pinned oracle;
   - for a refactor that must not change output: the output of the pre-refactor commit,
     frozen by the oracle preparer (never `src/deploy_vii` run beside its own wrapper: it is
     on the call path and not qualified, AGENTS.md);
   - a visible-text check of a rendered section against the plan's table rows, following
     the visible-text rules in `cases/goldens/check.py` (reuse them; do not copy them);
   - evaluator judgment, only for rows no script decides: a fresh agent, told nothing about
     the build, inspects the surface; the controller drives the built-in browser for it.
4. **Stop for the owner's approval of the table.**
5. **Key.** The oracle preparer writes any new key under `cases/`, adds it to
   `cases/pins.py` PATTERNS and re-pins, in a commit that touches no `src/` or `tests/` file.
   `mx-precise` reviews the key without reading the build.
6. **Comparison.** The verifier author (`mx-feature`, not the builder) writes
   `cases/prove/<surface>.py` (stdlib where it can; one failure per line:
   `<surface>: <key path>: expected <x>, got <y>`) and, when the check is reusable, a
   `.claude/skills/prove-<surface>/SKILL.md` naming when to run it and its exact argv.
   `mx-precise` reviews it.
7. **Smoke.** The controller plants one bug the comparison must catch, confirms exit 1,
   and reverts it.
8. **Record.** Fill the plan's Comparison column with the argv. A comparison over 5 minutes
   goes into `HEAVY` in `cases/prove/affected_tests.py`.

Failure lines go into the builder's next fix brief; the key file is never pasted there.
```

### 1d. `.claude/skills/maintain-prove-it/SKILL.md`

```markdown
---
name: maintain-prove-it
description: Use when a bug escaped the verifiers in Deploy Workflow (found in review, a native check, a user report or a live run). Hardens the comparison for the bug's class before the product fix.
---
# maintain-prove-it

The controller runs this skill and writes no code.

1. **Freeze the input.** The oracle preparer (not the fixer) freezes the failing input and
   its expected result under `cases/` and re-pins.
2. **Find the gap.** Run the comparisons the plan names for that surface on the frozen
   input. If they pass, classify why: surface not covered, input class missing (for example
   a soft hyphen or U+2212), key lacks the field, comparison too loose (subset instead of
   exact), or environment missing.
3. **Fix the class.** The verifier author upgrades the comparison for the whole class, not
   the instance (the `tests/defect_classes.py` pattern: one shared case every module runs).
4. **Red.** The controller confirms the upgraded comparison fails on the unfixed code.
5. **Fix.** Only then is the product fix dispatched. Done is the comparison exiting 0.
6. **Ledger.** `escaped=<bug> gap=<class> verifier=<commit>` in the lane ledger.

Never add a CLAUDE.md or AGENTS.md rule for the instance.
```

### 1e. `.claude/skills/audit-prove-it/SKILL.md`

```markdown
---
name: audit-prove-it
description: Use at each stage close or after a comparison changes in Deploy Workflow. Plants one realistic bug and checks the plan's comparisons catch it.
---
# audit-prove-it

The controller runs this skill. Mutations are never committed or pushed.

1. **Target.** A `src/` file changed since the last audit (lane ledger); prefer money,
   ordering and receipt code.
2. **Plant.** A planter agent (`mx-feature`) in its own worktree edits ONE site with a
   realistic mutation: off-by-one period, sign or parentheses flip, Decimal to float, zero
   and missing swapped, a dropped submission or render field, an inverted refusal or
   readiness condition, a skipped hash check. It does not commit. It reports the file, line
   and mutation to the controller only.
3. **Run.** In that worktree the controller runs, unchanged, the comparisons the plans name
   for that file's surfaces and the affected tests
   (`python3 -I cases/prove/affected_tests.py --tier fast <base> HEAD`, with the working
   tree's change committed to a throwaway local commit only if the script needs one).
   Judgment rows only: a fresh evaluator agent, told nothing about the mutation, inspects
   the surface.
4. **Score.** Caught means a comparison exits 1 on the affected surface. Then discard the
   worktree and confirm no branch or commit with the mutation remains.
5. **Missed** goes to `/maintain-prove-it` with the mutation as the escaped bug.
6. **Ledger.** `audit target=<file> mutation=<kind> caught=y|n comparison=<argv>`.

`mutmut` on sensitive files (global rules §3) stays; this is the end-to-end complement.
```

### 1f. `~/.claude/CLAUDE.md` (global; four edits, nothing else)

1. Line starting `- "Done" means the project's gates ran and exited 0.`: replace
   `the project's gates ran and exited 0.` with
   `the project's gates, and the comparisons its plan names, ran and exited 0.`
2. Line starting `- Every task brief and reviewer prompt includes:`: after
   `no catch-all that hides a failure unless the fail-open is documented and logged` insert
   `; the task's answer key and comparison, which the implementer does not edit`.
3. Line starting `- A fix for a code defect starts with a test`: after
   `and lands only with that test.` insert
   ` The test reads the cause at the surface where it was seen and compares with an answer key the fixer did not write (a reviewer's probe or a frozen oracle); where the project defines a verifier gate, follow it.`
4. Table row `| Test strength |`: before the closing ` |` append
   ` · a blind mutation audit (\`audit-prove-it\`) where the project ships one`.

Report the `diff` of the global file against
`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-open-items-fd69c5/c8389da7-7468-41f1-b496-de45232b3ad7/scratchpad/global-CLAUDE.md.bak`.
Commit the repo files only: `docs(verifier): Builder-Verifier gate and prove-it skills`.

## T2 - `cases/prove/scope.py` (mx-feature; review mx-precise)

Files: `cases/prove/scope.py`, `tests/test_prove_scope.py`. Stdlib only; runs as
`python3 -I cases/prove/scope.py ...` from the repository root.

Path classes (repository-relative, POSIX):
- ORACLE: `cases/**`, `src/deploy_vii/methodology.json`, `.claude/skills/**`, `.github/**`,
  `tests/test_goldens_*.py`, `tests/test_prove_*.py`.
- PLAN: `docs/superpowers/plans/**`, `docs/superpowers/specs/**`, `docs/*-LEASE.md`,
  `docs/*-ADDENDUM.md`.
- PRODUCT: `src/**` and `tests/**` not in ORACLE.
- Everything else is neutral.

Modes:
- `scope.py BASE HEAD`: for each non-merge commit in `BASE..HEAD`
  (`git rev-list --no-merges`), list its paths with `git diff-tree --no-commit-id -r
  --name-only --no-renames <sha>`. Exit 1 if a commit has both a PRODUCT and an ORACLE path.
- `scope.py --role builder BASE HEAD`: paths of `git diff --name-only --no-renames
  BASE...HEAD`; exit 1 on any ORACLE or PLAN path.
- `scope.py --role oracle BASE HEAD`: same paths; exit 1 on any PRODUCT path.
- Output: one line per violation, `<sha or range> <path>: <class> in <mode>`; on success one
  line `scope: <n> commits/paths checked, 0 violations`. A git failure exits 2 with git's
  stderr; it never passes.

Test (`tests/test_prove_scope.py`, pytest, temporary git repositories via `subprocess`):
one mixed commit fails per-commit mode; separate product and oracle commits pass it; a
builder range touching a lease or `methodology.json` fails `--role builder`; an oracle
range touching `src/` fails `--role oracle`; a bad ref exits 2.

Commit: `feat(prove): scope check separating builder and oracle paths`.

## T3 - PR CI with affected-test selection (mx-feature; review mx-precise)

Files: `cases/prove/affected_tests.py`, `tests/test_prove_affected.py`,
`.github/workflows/pr.yml`, `.github/workflows/pr-heavy.yml`. Stdlib only for the script.

`python3 -I cases/prove/affected_tests.py --tier fast|heavy BASE HEAD` prints the selected
test files, one repository-relative path per line, sorted; empty output means none. A
summary of why (changed file -> count) goes to stderr. Git failure exits 2.

1. Changed paths: `git diff --name-only --no-renames BASE...HEAD` (deleted files included).
2. Select every test file (`tests/**/test_*.py`) when a changed path is `pyproject.toml`,
   `uv.lock`, `.python-version`, any `conftest.py`, anything under `.github/`, or
   `cases/prove/affected_tests.py`, or is a path not covered by steps 3-5 and not under
   `docs/`, `work/`, `.claude/` and not a `*.md` file.
3. Import graph over every `.py` under `src/`, `tests/` and `cases/` (`ast`, all nodes, so
   function-level imports count; `importlib.import_module("<literal>")` counts). Module
   names: `src/a/b.py` -> `a.b` (`__init__.py` -> the package); `cases/x/y.py` ->
   `cases.x.y`; a file under `tests/` is also importable by its bare stem from any test.
   `import a.b.c` and `from a.b import c` depend on `a`, `a.b` and `a.b.c`; relative
   imports resolve against the importing file's package. A changed `.py` selects every test
   file that reaches it in the reverse graph, and itself if it is a test file.
4. A changed non-`.py` file under `src/<dir>/` counts as a change to every `.py` module in
   that directory.
5. A changed non-`.py` file under `cases/<name>/` or `tests/fixtures/<name>/`, or a data file
   directly under `tests/`, selects (through the reverse graph) every `.py` file under
   `tests/` or `cases/` whose source contains `<name>` (for a file directly under `tests/`:
   its file name) as a literal substring.
6. `HEAVY` is a module-level tuple, initially `tests/test_owner_rendering.py`,
   `tests/test_owner_workflow.py`, `tests/test_owner_s1a.py`,
   `tests/test_financial_workflow.py`, `tests/test_financial_render.py`. `--tier fast`
   prints selected minus `HEAVY`, `--tier heavy` selected and in `HEAVY`.

Test (`tests/test_prove_affected.py`, temporary git repositories): a changed module selects
its transitive test importer and not an unrelated test; a function-level import counts; a
changed `cases/x-owner/expected.json` selects the test naming `x-owner`; `pyproject.toml`
selects all; a docs-only change selects none; a `HEAVY` file lands only in `--tier heavy`.

`.github/workflows/pr.yml` (name `pr`), `on: pull_request` with default types only:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number }}
  cancel-in-progress: true
permissions:
  contents: read
```

Jobs `checks` (timeout 15 min) and `tests` (timeout 30 min), in parallel, each: 
`actions/checkout@v5` with `fetch-depth: 0` and `persist-credentials: false`;
`astral-sh/setup-uv@18d369b23da25a81e9458561248e1aafff6a70fa # v10.3.1` with
`version: "0.12.5"`, `python-version: "3.13.15"`, `enable-cache: true`; `uv sync --locked`.
Base ref in steps: `BASE="origin/${{ github.base_ref }}"` via `env`, never interpolated into
a script body from PR-controlled text.
- `checks`: `uv run --frozen python -I cases/prove/scope.py "$BASE" HEAD`;
  `uv run --frozen python -I cases/pins.py --check`;
  `uv run --frozen python -I cases/goldens/check.py cases/goldens/*/`; then, for changed
  `*.py` files outside `src/deploy_vii/` (`git diff --name-only --diff-filter=d
  "$BASE...HEAD"`), `ruff check`, `ruff format --check` and
  `mypy --follow-imports=silent` on those under `src/deploy_workflow/`, `cases/prove/`;
  skip each when its list is empty.
- `tests`: `files=$(uv run --frozen python -I cases/prove/affected_tests.py --tier fast
  "$BASE" HEAD)`; when empty, print `no affected fast tests` and exit 0; else
  `uv run --frozen pytest $files -m "not live" --durations=25`.

`.github/workflows/pr-heavy.yml` (name `pr-heavy`): `on: pull_request` with
`types: [labeled, synchronize, reopened]`, its own concurrency group
`${{ github.workflow }}-${{ github.event.pull_request.number }}` with cancel-in-progress,
`permissions: contents: read`, one job (timeout 360 min) with
`if: (github.event.action == 'labeled' && github.event.label.name == 'heavy-tests') ||
(github.event.action != 'labeled' && contains(github.event.pull_request.labels.*.name,
'heavy-tests'))`, the same setup, and `--tier heavy` with the same empty-list handling.

Commit: `ci: PR-only workflows running affected tests; heavy tier on a label`.

## Whole-branch review

`mx-architect` on `bd11a454..HEAD`, then `confidence-review` (global §1). No push or PR
without the user's OK.

## Answer Key

| # | User / system action | Surface | Expected observable result | Comparison |
|---|---|---|---|---|
| 1 | `python3 -I cases/prove/scope.py df26ea82 bd11a454` (per-commit mode, 1794 non-merge commits) | stdout, exit code | exit 1; the violating SHAs (first 8 hex) equal `work/builder-verifier/scope-key.txt` (18 lines, the controller's independent shell count, 2026-11-01) | controller runs it |
| 2 | `scope.py --role builder` on a range adding a line to `docs/CP4-OWNER-LEASE.md` | exit code | 1 | `tests/test_prove_scope.py` + controller probe |
| 3 | `affected_tests.py --tier fast fc7fe5c5~1 fc7fe5c5` (docs/work only) | stdout | empty, exit 0 | controller runs it |
| 4 | `affected_tests.py --tier fast 63a5bbb8~1 63a5bbb8` | stdout | contains `tests/model/test_loop.py`, `tests/test_run_inputs.py`, `tests/test_run_pathway.py` | controller runs it |
| 5 | `affected_tests.py --tier fast d3e27e74~1 d3e27e74` | stdout | contains `tests/test_goldens_check.py` | controller runs it |
| 6 | Any selection containing a `HEAVY` file | `--tier fast` vs `--tier heavy` | the file appears only under `heavy` | `tests/test_prove_affected.py` |
| 7 | Open a PR | GitHub checks | `pr` runs `checks` and `tests`; `pr-heavy` is skipped without the label | needs the user's OK to push |
