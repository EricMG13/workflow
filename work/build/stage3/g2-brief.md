# Stage 3 G2 build: generic owner rendering (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Worktree `../s3-g2`, branch `claude/s3-g2`, cut at the frozen G2 rev 2 commit on `claude/s3-g2scope`. Python: `L/.venv/bin/python`.

You build G2. You did not write its lease, and you never edit the lease or `cases/`.

## Inputs
| Item | File |
|---|---|
| Lease (rev 0 body, rev 1 and rev 2 amendments override in that order) | `docs/OWNER-RENDERING-LEASE.md` |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 2, 4 and 7 |
| Producers to import, never edit | `src/deploy_workflow/owner_workflow.py` (`OwnerRunReceipt`, `verify_owner_run_receipt`), `financial_workflow.py`, `financial_rendering.py`, `src/deploy_vii` (`render`, `build`, `SHIPPED_MAPS`) |
| D1 mechanisms to generalise, not copy | `src/deploy_workflow/earnings_rendering.py` if present, otherwise the lease's "D1 mechanisms" section |
| Oracles (every expected value) | `cases/snapshot/expected.json`, the financial case, and each rev 2 row's `cases/<cp>-owner/expected.json` pointer |
| Run fixtures | `tests/s1a_runs.py`, G1 `promoted_case`, and each row's `tests/<cp>_runs.py` driver |

## Process
1. Test first. Write `tests/test_owner_rendering.py` from the lease's acceptance (rev 1 tests 1-7 plus the rev 2 per-scope additions). Every expected value is read from the oracle, never from G2. Mark tests that build genuine owner runs with one marker or naming scheme, so the fast tests can run on their own.
2. Build `src/deploy_workflow/owner_rendering.py` per the Public API and Behaviour sections: the `DELIVERY_SCOPES` table exactly as rev 2 lists it, gated rows left out with a comment naming the gate. Create only those two files. If any other file must change, stop and report it.
3. Commit after the RED tests and after the build. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files.
- The fast tests: refusals, read-only checks, determinism, and the scope table against the oracles and drivers. Run them with `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_rendering.py -k <fast selection>`.
- The `cp1-model` scope's genuine tests: run them in the background and report the exit code.
- Add the remaining genuine-run tests' exact commands to `L/work/build/deferred-runs.md` in your report (list them; the controller writes the file).
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (report as text, at most about 1.5k tokens)
- Tip SHA; files and line counts; scopes built; tests run and their counts; deferred commands; questions; `Not verified:` line; ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n|n/a>`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Stop any background process before you hand back.
