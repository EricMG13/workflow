# Test-suite performance sweep — contract

Kind: optimization. Step: prepare → discover → launch (test-only). Scope: whole test suite;
product code is plan-only.

| Field | Content |
|---|---|
| Authority | `~/.claude/CLAUDE.md` §4; `AGENTS.md`, `CLAUDE.md`, `README.md`, `PLAN.md`; Modules brief 2026-10-30. Since 2026-10-30 `src/deploy_vii`, new dependencies and config changes need the user's own word **in this session**; relayed or peer approval does not count. `src/deploy_workflow` product files belong to the module lanes: also plan-only here. Never edit DEPLOY VII. |
| Base | Measurement base: Stage 5 release `05c3b27` (local `codex/checkpoint`, PR manager 2026-10-30; not yet on origin). Branch merged it at `5ee6c9b`; Stage 5 touched no P1–P3 file (src changes: `assets/app.css`, `render.py`, `report_view.py`). Snapshots (`git archive`, scratch): T0 = 05c3b27; T1 = T0 + P2 `contracts.py`; T2 = T1 + P1 `earnings_workflow.py`; T3 = branch HEAD (P2+P1+P3). |
| Scope / ownership | Owned: `work/perf-sweep/**`, new `tests/conftest.py`, marker lines in `tests/*.py`. Not owned: everything under `src/`, `pyproject.toml`, `cases/`. |
| Permissions | Test-only edits: authorized by the brief. Product edits, `pyproject.toml`, dependencies (`pytest-xdist`): **not authorized** (decision rows). Runtime monkeypatch trial probes in scratch: discovery evidence only, nothing lands. |
| Protected behavior | Every hash and byte output identical; `python3 -I cases/pins.py --check` exit 0; no test weakened (a test that asserts a *fresh* execution keeps building fresh — see `reopen_component` comment, `tests/test_earnings_workflow.py:1269`); suppression baseline noqa ≤ 13, type: ignore ≤ 5. |
| Gates | Affected tests pass; `ruff check`, `ruff format --check` on changed test files; `cases/pins.py --check`. |
| Metric | Primary: wall-clock seconds per test (pytest `--durations=0`, setup+call), lower is better. Secondary (deterministic): call counts of `Contract.content_hash`, `model_validate_json`, `validate_tables` from cProfile. |
| Harness | `probes/time_tests.sh` (`TREE=<snapshot> HEAD_LABEL=<id>`): one pytest process per target line, `--durations=0`, `/usr/bin/time -l` peak RSS, load average before/after; venv Python 3.13.15, pydantic 2.14.1; no project install in the venv, so pytest's `pythonpath` loads the snapshot's `src`. Runs go in **concurrent pairs on the same quiet machine** (10 cores, 64 GiB, load ≈ 2 at start): noise = T0 ∥ T0; heavy = T0 ∥ T3; sentinel = T1 ∥ T2. Both sides of every comparison see the same background. |
| Noise | `noise-targets.txt` (s1a tampering[gap], fresh owner E-NO-YOY) run twice concurrently on T0; noise = max relative spread of the two runs, applied to every test as a percentage. Gain accepted only if > 2 × noise and > 5 % of the test's before time. |
| Ranking | Impact bands (seconds saved per full-suite run): 1 < 60, 2 < 300, 3 < 900, 4 < 1800, 5 ≥ 1800. Confidence 1–3 and risk 1–5 per `optimization.md`. Floor: score ≥ 1.0 and confidence ≥ 2. |
| Caps | Per item: 2 attempts. Total: test-only items ≤ 3; this session stops after the written product plan. |
| State | `work/perf-sweep/register.md` (rows, evidence), `work/perf-sweep/progress.md`, raw logs `work/perf-sweep/runs/`, profiles `work/perf-sweep/profiles/`. |
| Completion | Before/after timings per change; pins check exit 0; outputs identical; affected tests pass; report with seconds saved per test and a `Not verified:` line. |
