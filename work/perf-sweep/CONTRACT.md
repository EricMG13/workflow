# Test-suite performance sweep — contract

Kind: optimization. Step: prepare → discover → launch (test-only). Scope: whole test suite;
product code is plan-only.

| Field | Content |
|---|---|
| Authority | `~/.claude/CLAUDE.md` §4; `AGENTS.md`, `CLAUDE.md`, `README.md`, `PLAN.md`; Modules brief 2026-10-30. Since 2026-10-30 `src/deploy_vii`, new dependencies and config changes need the user's own word **in this session**; relayed or peer approval does not count. `src/deploy_workflow` product files belong to the module lanes: also plan-only here. Never edit DEPLOY VII. |
| Base | Measurement base: the Stage 5 release tip on `codex/checkpoint` (pending, asked PR manager). Discovery read at `2bbf633`; hotspot files (`contracts.py`, `execution.py`, `financial_validation.py`, `live/submission.py`, `earnings_workflow.py`, `tests/test_earnings_workflow.py`, `pyproject.toml`) are unchanged on `claude/s5-int` 64cfca9 — recheck on the tip. |
| Scope / ownership | Owned: `work/perf-sweep/**`, new `tests/conftest.py`, marker lines in `tests/*.py`. Not owned: everything under `src/`, `pyproject.toml`, `cases/`. |
| Permissions | Test-only edits: authorized by the brief. Product edits, `pyproject.toml`, dependencies (`pytest-xdist`): **not authorized** (decision rows). Runtime monkeypatch trial probes in scratch: discovery evidence only, nothing lands. |
| Protected behavior | Every hash and byte output identical; `python3 -I cases/pins.py --check` exit 0; no test weakened (a test that asserts a *fresh* execution keeps building fresh — see `reopen_component` comment, `tests/test_earnings_workflow.py:1269`); suppression baseline noqa ≤ 13, type: ignore ≤ 5. |
| Gates | Affected tests pass; `ruff check`, `ruff format --check` on changed test files; `cases/pins.py --check`. |
| Metric | Primary: wall-clock seconds per test (pytest `--durations=0`, setup+call), lower is better. Secondary (deterministic): call counts of `Contract.content_hash`, `model_validate_json`, `validate_tables` from cProfile. |
| Harness | `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider --durations=0 <nodeids>` from the worktree root; Python 3.13.15, pydantic 2.14.1. One test process at a time; record `uptime` load average before and after each run. |
| Noise | Sentinels in `noise-targets.txt` run twice on the same tree before any change; noise = max relative spread of the two runs, applied to every heavy test as a percentage. Gain accepted only if > 2 × noise and > 5 % of the test's before time. |
| Ranking | Impact bands (seconds saved per full-suite run): 1 < 60, 2 < 300, 3 < 900, 4 < 1800, 5 ≥ 1800. Confidence 1–3 and risk 1–5 per `optimization.md`. Floor: score ≥ 1.0 and confidence ≥ 2. |
| Caps | Per item: 2 attempts. Total: test-only items ≤ 3; this session stops after the written product plan. |
| State | `work/perf-sweep/register.md` (rows, evidence), `work/perf-sweep/progress.md`, raw logs `work/perf-sweep/runs/`, profiles `work/perf-sweep/profiles/`. |
| Completion | Before/after timings per change; pins check exit 0; outputs identical; affected tests pass; report with seconds saved per test and a `Not verified:` line. |
