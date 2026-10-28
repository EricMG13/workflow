# CP-2A fix round 2 re-review (mx-adversary)

## CP-2A fix round 2 re-review (fbe2d3c): APPROVE

All three items are closed. Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-s2-review/`.

**M1 (A2e): closed.**
- `cp2a_consumer_rows` reads only the top-level `report["consumers"]`. The deferred test runs `DownstreamReport.model_validate_json` on the real output before it selects.
- **The repointed probe is not weaker.** It differs from my `.bak` only in the selector it calls; the three-CP-2A shape and the exit condition are unchanged. The original still exits 1, the repointed one exits 0.
- **Real-shape probe `r5_a2e_real_shape.py`, exit 0:**
  - Walking `DownstreamReport.model_json_schema()` finds four objects with `entry`: `inputs.consumers[]`, `review.consumers[]`, `consumers[]` and `model`. Only `consumers[]` carries both `canonical_module` and `status`.
  - A report built from the real models with the CP-2A request, the oracle review's assessment and two `ConsumerRow`s goes through the product serializer. The selector returns only the CP-2A row, `ready_with_limitations`.
  - The old walk finds 3 matches over the same JSON, so the defect reproduces.

**A3 pin: closed.** Both tests now assert an issue containing "Malformed run text". `r2_gap_and_fig.py` exits 0 and shows that line on the fast path.

**T4.10 filter: closed** (read in the diff only). `_assert_head_equals_oracle` now filters on `table_id == "T4.10"`, as `cp2a_runs` does.

**Exit codes**
- Gate set: 0, 613 passed.
- New fast selector test: 0, 1 passed.
- `--collect-only tests/test_owner_cp2a.py`: 0, 16 tests.
- `mutants.py fbe2d3c`: 0, 37 of 38 killed. The survivor is `validator step[0]`, which is equivalent, and the unmutated copy passes.
- The worktree is clean at fbe2d3c.

Not verified: none of the 15 deferred tests has run. That covers the real readiness output, the T4.10 filter on a genuine CP-1 head, and the deferred A3 pin. The A4 read-body Info is still open. `mutants_reg.py` was not re-run.
