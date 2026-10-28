# CP-DR fix round 1 re-review (mx-adversary)

## CP-DR fix round 1 re-review: commits 1e3942a..28b2dce, worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-cpdr`

**Verdict: APPROVE.** M1, L1, L2 and L3 are all fixed, and no High or Medium finding remains. Three new Low/Info notes are below; per the ladder they ride with the end batch and don't reopen review.

**Reruns, all exit 0:**
- `tests/test_owner_cpdr.py`: 30 passed in 4.9 s.
- The fast set plus `test_owner_cpdr`: 561 passed.
- `ruff check`, `ruff format --check` and `mypy --strict` on the 4 changed files.
- My four probes, each exit 0: `probe_closed_run.py`, `probe_run_refusals.py`, `probe_rules_only_receipt.py`, `probe_reader_edges.py`. The last now refuses all three forged shapes, and a stale head still reads `stale`.

### M1: fixed
Each missing acceptance item now has a test that asserts the right thing:
- **Tamper:** `_verify_audit` is asserted directly on the forged copy. A spy shows the CP-DR probe was reached. Every earlier `_verify` step (begins, attempts, walk, chain, calls/reads, submissions) runs before `_verify_settlements`, so reaching the probe means they passed. With `cpdr.probe` made a no-op, this test fails on its own, so it is the probe that refuses (`probe_tamper_noop.sh`, exit 0 = killed).
- **stale_binding:** an `interrupt` between read and submit gives `stale_binding`.
- **Submit before read_inputs:** `not_permitted`.
- **`extract_statements`:** refused `not_permitted`.
- **Blocked case:** run through `OwnerWorkflow`; the receipt verifies, the head is blocked, the reader returns status only, and there are no tables or claims.
- **Store bytes:** identical before and after verifying the receipt, for all three cases.
- **D3 reader:** called on the closed-run head and checked against the oracle's bookkeeping and unresolved ids.
- **`replay` spans:** `expect_spans` and `expect_matching_spans` are compared with the parsed body. The oracle lists are non-empty, so the comparison really runs.

### L1: fixed
`review_mutants.py` against the 28b2dce tree exits 0:
- A1, A13, A2, A3, R11 and R12 are now killed.
- Only A7 and A16 survive, both equivalent as I said before.
- R1, R9 and R13 were skipped because the code moved. I re-targeted R9 and R13 in `review_mutants_fix1.py` and both are killed.

### L2: fixed
The reader now refuses each case without coercing it: a known share carried as text, a non-integral count, a missing per-gap `unresolved` or `answered_share` fact, and a per-gap unresolved count that is not questions minus answered (mutants L2a, L2c, L2d, L2e, L2g killed).

The extra TDR.1 answered-share refusal is correct. Every agenda gap has 1 to 4 questions (validator rule 2), and `bookkeeping` raises on 0, so a per-gap share always has a denominator and must be a known amount.

### L3: fixed
The `shipped.py` record has the right prior hash (4ef3f9ff…) and current hash (4765995a…, matching the file), and the manifest parses.

### New Low/Info
- **Low:** two of the new reader refusals have no test. Mutant L2b (drop the negative-count check) and L2f (drop the per-gap "share is not known" check; only the absent-fact path is tested) both survive. The code itself is correct.
- **Info:** the record's `project_commit` is b22972d, but `shipped.py` changed in 1e3942a, not b22972d. The controller sets the merge SHA anyway.
- **Info:** the stale_binding test reads the private `workflow._binding`. It is test-only.

### Files
All in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/`:
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/review_mutants.fix1.out`
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/review_mutants_fix1.py` (exit 0) and its output `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/review_mutants_fix1.out`
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpdr-s2-review/probe_tamper_noop.sh`
- The probe outputs end in `*.fix1.out`.

Not verified: `test_owner_workflow.py`, `test_owner_s1a.py` and the render suites were not run. Neither were the other tamper variants (an edited step output, a receipt-only rewrite) or the oracle builder rebuild.
