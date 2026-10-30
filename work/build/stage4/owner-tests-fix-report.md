Causes A, B, D, E and F are fixed. All the genuine owner tests I ran now pass, and the fast set passes.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3b503dcc11b15bb2
Branch: claude/s4-owner-tests, based on ff9070e (confirmed). Tip: 18f1845ced0a752492c8a1e571431687be0f239e. The tree is clean and the `.venv` link is removed.

Changes (4 commits, each with the Co-Authored-By trailer):
- **A (418c71a):** `tests/test_owner_cp2g.py` and `tests/test_owner_cp4c.py` compare the unsettled spelling when the oracle `shown` is None. Missing expects "∅ G#" and not_applicable expects "∅ G# n.m.", chosen from the fact's `status`. The two strings are hard-coded in the test because `cell_notation` is prose, so the test cannot read them from the manifest. Otherwise the comparison is unchanged.
- **B (bacbeb3):** `bound_literal` in `tests/cp2g_runs.py` and `tests/cp4c_runs.py` is now `match[0] if hit is None else "{"+hit[0]+"|"+match[2]+"}"`.
- **D and E (4ec369b):** these are in one commit because both are in `tests/test_owner_cp3.py` and I could not split the file without interactive staging. D replaces the pack-hash marker with `closed.pack.content_hash()` before comparing, following `test_owner_s1a.py`. E compares `len(body["cp1a_signals"])` with the frozen count.
- **F (18f1845):** in `tests/test_owner_cpl10.py`, `_cites` now returns `one_per_page(...)`, imported from `deploy_workflow.owners.blank`. A copied cell expects `cp1[copied].citations` unchanged. A derived cell expects `_cites(...)`.

Gates (one pytest process at a time):

| Gate | Result | Duration |
|---|---|---|
| cp3 `-k "cp0_r3 or register_counts"` | exit 0, 4 passed | 841.70 s |
| cpl10 `-k closed_run_equals` | exit 0, 2 passed | 410.34 s |
| cp4c `-k "a1_positive or a2_gap or a3_each"` | exit 0, 37 passed | 3773.69 s |
| cp2g `-k "a1_positive or a2_gap or a2c or a3_each"` | exit 0, 39 passed | 1964.21 s |
| `test_method_cp2g`, `test_method_cp4c`, `test_method_cpl10`, `test_connect_cp2g`, `test_connect_cp4c` | exit 0, 2167 passed | 26.17 s |
| `ruff check` on the 6 files | exit 0 | not timed |
| `ruff format` | I ran it with write rather than `--check`. It reformatted `tests/test_owner_cpl10.py` before the F commit, and the other 5 files were already clean. I did not re-run `--check`. | not timed |
| `MYPYPATH=src mypy --strict` on the 6 files | exit non-zero, 2 errors, both in `tests/defect_classes.py:858` and `:863` ("Cannot infer type of lambda"). That file is not one of the 6 I changed, so I did not touch it. No errors in the 6 changed files. | not timed |
| Suppressions | noqa total 13 (≤13), type: ignore total 5 (≤5) | not timed |

The cp2g run was 39 tests, not the 16 the failed-so-far list implied for that file, because `a3_each` also selects the `a3` parametrisations. `test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2g_step` (cause C) was not run.

I did not run the pytest `--cov` or other gates beyond those listed. The agent worktree could not use Monitor, so I waited by background-task notification. No background processes remain from me. I stopped one poll loop of my own early.

Not verified: cause C (oracle change and the `_cp1_fact` seed) is untouched. The `mypy --strict` errors in `tests/defect_classes.py` are unconfirmed as pre-existing at ff9070e, because I did not check them on the base. `ruff format --check` was not re-run after the formatter wrote its change. The other cp3, cp4c, cp2g and cpl10 tests outside the `-k` selections did not run. No full suite ran.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y (every target test passed on its first run after the fix, apart from the mypy errors above)
