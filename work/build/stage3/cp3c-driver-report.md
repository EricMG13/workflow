Stopped without a fix. The cause is in the oracle and lease, not the driver, `src/` or the test code, and the brief tells me to stop in that case.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a84136ec315fffe56. Branch `claude/s3-cp3c-driver`, tip ee95ffb. I made no edits and no commits.

**Root cause**
- The failing step is not `read_cp2`. The CP-1A step (`s1a.drive_cp1a`) is rejected, and `reach_cp2d` ignores that until `read_cp2` runs. CP-1A is the one step between CP-1's last submit and `read_cp2`.
- With `read_inputs` called on a CP-1A step that is still open, `read_cp2` hits `not_permitted` (`financial_workflow.py:593-594`) after the limit or phase check.
- My trace of CP-0 through CP-1A on this pack (`repro.py`): CP-0, source_context, financials, narrative, readiness (the new downstream review) and quality are all valid. So `drive_cp1` and the CP-0 deltas are fine.
- `business_context` then returns `invalid`: "Judge exactly the consumers listed in the CONTEXT block: CP-2, CP-MODEL, CP-3C".
- The product's rule is `business_context.py:344-353`, `cp1a_consumers(pack)`. It is CP-MODEL plus every module in the run's plan that lists CP-1A as required or optional. For this pack that includes CP-3C, because the lease's registry note says CP-3C has CP-1A as optional.
- The pinned CP-1A literal, `cases/snapshot/submissions.json#positive.business_context`, judges only CP-2 and CP-MODEL. `manifest.json#upstream_literals` and the lease (line 75) say it is reused unchanged. That is wrong for this run, and the lease probes never ran a CP-1A step ("A promotion of this pack was not run").
- The same reuse works for the CP-2D run because CP-2D is not a CP-1A consumer.

**Why I stopped**
- The fix needs a new CP-3C consumer entry in the CP-1A literal, with a status, handoff item, gap, required action and citations. That is oracle content, so it needs a separate preparer and a lease amendment.
- The digests pinned in `tests/cp3c_runs.py` PINS (the 4 oracle files) would also change. A driver-only patch would mean authoring that oracle content in `tests/`.
- Suggested shape: either add `cp1a_consumer_deltas` to `cases/cp3c-owner/submissions.json` (appended to `consumers`, like `cp0_consumer_deltas`) with a matching `drive_cp1a(text=...)` in `reach_cp2d`, or ship a full CP-1A literal for this run.

Later steps may have further defects, since nothing past CP-1A has run for this pack.

**Reproduction**
`PYTHONPATH=src:tests <lane>/.venv/bin/python /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-driver/repro.py` stops after CP-1A and prints the `invalid` outcome. It takes a few minutes, mostly the CP-1 promotion.

**Gates**
- No gate was run, because there was no change. The genuine test still fails as the brief describes.
- No background process is left running.

**Ledger**
`agent=mx-feature fix-rounds=0 gates-first-pass=n/a`. Status: BLOCKED on the oracle.

Not verified: any step after CP-1A (CP-2, CP-2D, CP-3C, and the `gap_minimum_cash` and `gap_no_repricing` cases); `tests/test_connect_cp3c.py`; ruff and the suppression counts; whether the CP-1A rejection is the only defect on the path to CP-3C.
