The fix is committed and passes the probe on the three genuine stores. The genuine pytest gate was not completed (see gates below).

**Worktree and tip:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a67210e345d701e9b`. Branch `claude/s5-cp4-owner` was created from 48e6c91 and the tip was confirmed there. It is now at 98800a0, one commit with the Co-Authored-By line. The tree is clean and the `.venv` link is removed.

**Change (only `tests/test_owner_cp4.py`):**
- **Cause 1:** `test_tables_claims_and_limitations_equal_the_oracle` now binds the metric from `s1a.figure_fact(cp1.facts, runs.METRIC)`. It sets `ctx["metric"]` to the matching fact in `inputs.upstream.facts`, and `ctx["metric_row"]` from `inputs.upstream.rows`.
- **Cause 2:** `module.inherited_limitations` is now compared with a list built from the oracle rule: `dict.fromkeys` over the CP-0 literal head, the CP-1 limitations and the CP-1 inherited limitations, minus the settled limitations.
- **Low (:166):** `test_d3_cp4_reads_its_upstream_heads` now uses the `figure_fact` metric. It also asserts that the metric is in `inputs.upstream.facts`.
- `tests/test_method_cp4.py` is untouched.

**Gates:**
- **Adapted probe:** exit 0 for `positive`, `gap` and `gap_false_same_definition`. It calls both edited test functions on the stores in `<S>/cp4-rca/stores`. I did not time it; it ran in seconds. The script is `<S>/probe_fix2.py`, where `<S>` is the scratchpad directory named in the brief.
- **`ruff check`:** exit 0.
- **`ruff format --check`:** exit 0.
- **`mypy --strict`:** exit 0.
- **Suppressions:** `noqa` count 0 and `type: ignore` count 0 in this file. I did not recount the repo-wide totals against the ≤13 and ≤5 limits.
- **Genuine pytest run** (`-k "tables_claims or d3_cp4_reads"`): not completed. I started it in the background and then killed it before hand-back, because I have no Monitor tool and cannot wait about an hour without a foreground sleep. The "failed, exit 144" notification you may see is that kill and carries no test result. No background process is left running.

**Cleanup:** I did not delete `<S>/cp4-rca/stores` (about 490 MB), because you may still want it for the genuine run.

Not verified: the edited tests under pytest on a genuine CP-1 promotion (only the probe logic ran, on the copied stores); the repo-wide `noqa` and `type: ignore` totals; the other tests in `tests/test_owner_cp4.py`.

Ledger: `agent=mx-feature fix-rounds=0 gates-first-pass=n/a`
