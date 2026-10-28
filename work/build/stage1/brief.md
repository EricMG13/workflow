# Stage 1 brief: working module calculation (one module per agent)

The dispatch message fills in `<CP>` (module id), `<cp>` (lower-case file stem), `<LEASE>` and `<CASE>`.

You are the implementer for **one** module (`general-purpose`, model opus; user routing 2026-10-28). Work in your own worktree, which is cut from the lane branch at `e8ee084` or later.

## Goal
Build the module's calculation as **pure Python functions** in `src/deploy_workflow/owners/<cp>.py`. Prove it against the frozen oracle `<CASE>/expected.json#cases` in `tests/test_method_<cp>.py`. This is Stage 1 of four (modules → connections → pathways → orchestration). Leave out every connection and orchestration concern: those are added to the same file in later stages.

## Read first
| File | Why |
|---|---|
| `<LEASE>` | What the module computes: Method, zero/missing rules, refusals that are calculation outcomes, table ids, row order and wording |
| `<CASE>/expected.json` (`cases`, plus any `method_rules`, `arithmetic`, `derivation`, `cell_notation`, `fixtures` sections) | The oracle. Never derive an expected value yourself |
| `<CASE>/manifest.json` (`fact_bindings`/frozen inputs) | Where each input comes from in Stage 2 |
| `<CASE>/builder/build.py` | Read only, to understand how the oracle was derived. Do not import it or copy its code into `src` |
| `docs/G1X-OWNER-CORE-PROTOCOL.md` §2 | Read only, so your function names don't clash with the later plug-in parts |
| Existing engines in `src/deploy_vii/` the lease names (for example `cp4_legal.py`, `cp3_relative_value.py`, `prose.py`, `contracts.py`) | Call them; never edit `src/deploy_vii` |

## Files you may write
- `src/deploy_workflow/owners/__init__.py`: create it empty if missing. An identical empty file from another branch merges cleanly.
- `src/deploy_workflow/owners/<cp>.py`
- `tests/test_method_<cp>.py`
- `work/build/stage1/<cp>/report.md`
- Nothing else. No `owner_workflow.py`, `host.py`, `src/deploy_vii`, `methodology.json`, `cases/` or other tests.

## What to build
1. **A typed input object** (frozen dataclass or pydantic `Contract`), for example `<Module>Inputs`, holding every operand the lease's Method reads, plus the analyst judgment fields the lease names.
   - Use `Decimal` for amounts and `None` for missing; missing is never 0.
   - In the report, list each field with its Stage 2 source (CP-1 table id / predicate from `manifest.fact_bindings`, or "judgment").
2. **Pure functions**, for example `compute(inputs) -> <Module>Result`.
   - They return the lease's tables (ids, titles, columns, row order, cell state known/missing/blocked, `shown` text, value class), the module's own limitations and its claim texts where the lease fixes them from templates.
   - They do no I/O and make no store, host, session or render call.
   - All arithmetic is `Decimal`, with exactly the lease's quantisation and rounding.
3. **Existing engine** (CP-4, CP-3): when the lease reuses one, the Stage 1 work is calling that engine plus any new logic the lease adds (for example CP-4's semantic gate `semantic_issues`). Prove the combined output against the oracle. If the engine disagrees with the oracle, do not patch the engine. Report the exact diff as a finding for the controller.

## Test (write it first, run it, see it fail, then implement)
- Build each `cases` entry's input object from the oracle's own source facts, manifest bindings or fixtures, never from your code.
- Assert every derived value and every table cell (state, `shown`, amount, unit) and limitations equal `expected.json`.
- Cover every case listed, including the missing/gap and fixture cases. Include the calculation-level refusals (for example invalid judgment ranges), but not tamper/forgery, tool-use or execution sections. List those as "Stage 2/4" in the report.
- Run: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py`. It must stay under 60 s. If a case needs a store or a CP-1 promotion, it is not Stage 1: skip it with a reason and list it in the report.
- Gates (exit 0), all with `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/"` prepended:
  - `ruff check src/deploy_workflow/owners tests/test_method_<cp>.py`
  - `ruff format --check` on the same paths
  - `MYPYPATH=src mypy --strict src/deploy_workflow/owners/<cp>.py`

## Rules
- No stub or fake value standing in for real behaviour, and no catch-all that hides a failure.
- If the lease and the oracle disagree, or the lease is ambiguous, stop on that point and report it with the exact lines. Do not invent policy.
- Run confidence-review on your diff, and rewrite-tournament (no-argument mode) on non-trivial functions, before reporting.
- Commit on your worktree branch: `feat(<cp>): Stage 1 calculation against the frozen oracle`, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report (`work/build/stage1/<cp>/report.md`; also return it as text)
- Branch, commit SHA and files.
- The input-field table (field, type, Stage 2 source).
- Test result line, with counts and duration.
- Gate exit codes.
- Oracle sections covered and those left to Stage 2/4.
- Engine/oracle disagreements.
- Confidence-review findings.
- `Not verified:` line.
- `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
