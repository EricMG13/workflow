# Deploy Workflow

Read AGENTS.md, README.md and PLAN.md. They contain the current scope and routing.
This fresh repository reuses a pinned subset of Claude-derived implementations;
old project/session instructions are not inherited. Python owns arithmetic;
analytical completion requires actual tool use, consumption and rendering.

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
