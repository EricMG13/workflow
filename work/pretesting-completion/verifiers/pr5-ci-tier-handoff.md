# PR5 CI tier correction handoff

Task `PR5-CI-TIER-01`; exact Product source behavior and fixtures untouched.

Root cause: test selection classified `tests/test_earnings_workflow.py` as fast although it contains authentic five-stage CP1, recovery and receipt cases. CI log reached item112 after five minutes of earnings work and proceeded into actual history authentication and 21 paged manifest/projection/citation reads per 138-coordinate owner scope. The cancelled item itself remains unknown because output was buffered.

Change: selector classifies the complete earnings file as heavy; checkpoint runs it once in its existing per-file heavy matrix and removes it from eight suite shards; PR-heavy is still label-gated and now prints node IDs (`-v`). No selector dependency or test-body change, cap/timeout/fixture/skip/provider change.

Validation from this worktree: `PYTHONDONTWRITEBYTECODE=1 /Users/ericguei/Documents/Deploy Workflow/.venv/bin/python -B -m pytest tests/test_prove_affected.py -q` => exit0, 23 passed. Initial pre-correction run had one expected-test assertion failure because earnings was now correctly selected heavy; assertion was updated and focused suite then passed. `PYTHONDONTWRITEBYTECODE=1 /Users/ericguei/Documents/Deploy Workflow/.venv/bin/python -B - <<'PY' ... pytest --collect-only ... PY` => exit0, 243 nodes collected in0.29s, no bodies executed. `git diff --check` exit0.

First baseline-gate status: not all pass on first attempt (the old expected heavy list was missing the newly routed file). Final ledger uses gates-first-pass=n. No Product runtime qualification or PR/merge CI result is claimed.

Required next step: independently review this exact commit and selectively integrate only the approved files. PR5 has no `heavy-tests` label, so PR Manager must obtain an applicable heavy job after integration; fast CI alone is insufficient. Keep exact-head green checks as the merge gate. The heavy result must provide completion timing or verbose named-node evidence.
