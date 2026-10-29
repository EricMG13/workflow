# Stage 3 CP-OS build (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Worktree `../s3-cpos`, branch `claude/s3-cpos`, cut at release ab9777f. Python: `L/.venv/bin/python`.

## Inputs
| Item | File |
|---|---|
| Lease (frozen; re-pinned at e8ee084 and by the Stage 2 close chain) | `docs/CPOS-OWNER-LEASE.md` |
| Rulings on its open questions | `L/docs/rulings/2026-10-29-stage3.md` item 1 |
| Oracle (values only from here) | `cases/cpos-owner/expected.json`, builder `cases/cpos-owner/builder/build.py`; pins in `cases/PINS.json` |
| S1a fixtures | `tests/s1a_runs.py` (`s1a_closed`) |
| G1 verifier | `src/deploy_workflow/owner_workflow.py` (`verify_owner_run_receipt`, `OwnerRunReceipt`) |

## Process
1. Test first: write `tests/test_owner_cpos.py` with the lease's acceptance A1-A6 (and every case the lease lists), reading every expected value from `cases/cpos-owner/expected.json`. Confirm it fails for the missing module.
2. Build `src/deploy_workflow/owners/cpos.py` per the lease's Public API and Behaviour. Edit nothing outside the lease's Files list. If the lease requires a pinned file to change (for example a D12 registration in `report_view.py`), stop and report it; do not re-pin.
3. Commit after the RED test and after the build. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/cpos-owner/builder/build.py && git diff --exit-code -- cases/cpos-owner`; `python3 -I cases/pins.py --check`.
- `ruff check`, `ruff format --check` on both files; `MYPYPATH=src mypy --strict src/deploy_workflow/owners/cpos.py`.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cpos.py`. It builds genuine S1a runs and may take 15+ minutes: run it in the background and wait for it; report the exit code and the counts.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (report as text, at most about 1.5k tokens)
- Tip SHA; files; the A3b/A3c derived CP-2 states as observed (ruling item 1.1); gate exit codes; questions; `Not verified:` line; ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n>`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Values come only from the oracle. Stop any background process before you hand back.
