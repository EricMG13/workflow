Both steps are committed. The G1X §6 text is replaced as specified. The shipped.py D12 chain is corrected, but not in the shape the contract describes, so please check the deviations below. The two probes and `pins.py --check` match the contract's gates.

**Worktree** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a501135c78cafb479`, branch `claude/s5-docs`, tip `fbfc905`. I checked out from 07dc002 and confirmed the tip. Commits: `2f037db` (G1X §6), `fbfc905` (manifest). Only the two named files changed.

**§6** The last sentence now reads: "`bindings/` files never import `deploy_workflow`. The chart seam's figure producers (`report_view.py`'s chart registrations and `distressed_figures.py`, rulings 2026-10-29 items 8 and 51) may lazily import `deploy_workflow.*_series` leaf modules, as the CP1 chart slice does; no other `src/deploy_vii` module imports `deploy_workflow`."

**Import list under `src/deploy_vii`** (real imports only; the `bindings/*.py` matches are docstrings saying they never import it):
- `distressed_figures.py:61` imports `restructuring_series`.
- `report_view.py:1860` imports `financial_series`.
- `report_view.py:2940` and `report_view.py:2966` import `liquidity_series`.

Nothing falls outside those two files, so the clause is true at my tip.

**Records for `src/deploy_vii/bindings/shipped.py`**
The lane's first-parent commits that change the file are df26ea8 (bootstrap import), 683499d, e1d0630 and f1544a3. Each sha256 below was computed from git, not copied.
- **b22972d, now e1d0630:** prior `4ef3f9ff` and sha256 `99fbe495`. This is a merge record folding b22972d, 883a595, 0fa5b4a, b48a3c5, fb7819b and b9d937e. The reasons are concatenated and the text says so. The b22972d record had its first parent already at `4765995a`, so it was not the commit that made the change.
- **883a595, 0fa5b4a, b48a3c5, fb7819b, b9d937e:** removed, folded into the e1d0630 record. 883a595, fb7819b and b9d937e are outside your named six. Their priors chain through the removed b22972d state, so they cannot stay.
- **8aef58d** (prior `4ef3f9ff` → `0b74f88e`, chain GAP): removed. Its reason is appended to the 24f879a record, whose other fields are untouched. 24f879a's second parent is the 8aef58d branch.
- **6b679ca:** removed, folded into ab89173.
- **ab89173:** prior `2be6922a` → `f51954d7` (its first parent's file); sha256 `11185049` unchanged. Its reason now also carries the 6b679ca reason, and the text says so.

**Deviations from the contract**
- I did not collapse the records after e1d0630 into a single f1544a3 record. The Stage 2 branch records (24f879a, 7831ef1 … 64bf670) stay as individual records. Each satisfies the item 19 rule on its own, and your gate lists 24f879a as an expected failure.
- The 0d6c714 record is kept. It is not a first-parent commit; 683499d is a single-parent commit with the same file sha256 `4ef3f9ff`. The probe passes it, and it sits outside your six. If strict first-parent is wanted, repoint it to 683499d.

**Gates**
- Probe `s53-B` (4822066..HEAD) exits 1. No `shipped.py` line fails. The remaining failure lines are the owner records for other files:
  - `cffdf9f` ×9 (BAD)
  - `1a1a140` (BAD)
  - `bb4553b` ×2 (BAD)
  - `3e5b537` (BAD)
  - `8aef58d` report_view (GAP: prior `51a6853e` → `4edad0a3`)
  - `24f879a` report_view (BAD: first-parent file `09ab059d`, record sha256 `8ed326cb`)
- Probe `stage3-review` (697fe8a..HEAD) exits 1, with only these three lines:
  - `3e5b537` (BAD)
  - `8aef58d` report_view (GAP)
  - `24f879a` report_view (BAD)
- The manifest JSON loads, exit 0. `cases/pins.py --check` exits 0 ("matches 86 paths").

Not verified: the pytest suite, ruff and mypy were not run (docs-only change, and no test exercises the manifest prose). No other manifest consumer was checked for the removed records. The reuse-manifest checks outside the two probes were not run.

Ledger: `agent=mx-feature fix-rounds=0 gates-first-pass=y` (the probes show only the expected owner failures).
