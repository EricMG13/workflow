# CP-2A fix round 1 re-review (mx-adversary)

## CP-2A fix round 1 re-review (375f651..ac97894)

**Verdict: REQUEST CHANGES.** One Medium remains: the deferred A2e test can never pass. Everything else checked is fixed.

The probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-s2-review/`. Run each as `run.sh <probe> [ref]`.

### Exit codes (at ac97894)
- **Gate set:** exit 0, 613 passed, nothing skipped. `--collect-only tests/test_owner_cp2a.py` exits 0 and collects 15 tests.
- **Requested probes:** `p10` 0, `p3` 0 (3000 cases, no counterexample), `p8` 0, `p9 ac97894` 0 (no test fails for any of the three appender edits).
- **`mutants.py ac97894`:** 37 of 38 killed. The one survivor, `validator step[0]`, is equivalent because CP-2A has one step.
  - I re-targeted the mutant the L4 edit broke, "upstream cp1 from current head". It now mutates the `head = store.result(...)` line.
  - I added 7 mutants for L4 and the round 5 unit rule. All are killed.
- **Re-runs:** `p1`, `p2`, `p5`, `p7` exit 0. `p4` exits 1 by design: its part (c) now raises the new L4 refusal. Its part (d) is split out as `r4`.

### Medium
**M1 is not fully fixed: `test_a2e_cp1_readiness_row_for_cp2a_is_ready_with_limitations` cannot pass.** Probe `r1_a2e_find_rows.py` exits 1.
- The CP-1 readiness step output is a `DownstreamReport`.
- `_find_rows(output, "CP-2A")` finds three dicts with entry "CP-2A": the `inputs.consumers` request, the `review.consumers` assessment and the `consumers` row.
- So `len(rows) == 1` fails. The first match, the request, has no `status` either.
- It would fail loudly at Stage 5, which means a heavy rerun.
- **Fix:** read `json.loads(output)["consumers"]`, and assert one CP-2A row with `canonical_module` CP-2A and status `ready_with_limitations`.

### The other M1 tests against lease :167-177
- **A1:** checks plan order, statuses, every fact's id, status, unit, period, amount and shown text, the claims, own limitations, one read, no ok call, and the tail input.
- **A2 gap:** checks the whole head against the oracle. Its leverage selector picks 6 facts, all `missing` (`r2`).
- **A2b and A2d:** the oracle keys they read exist. A4 follows the S1a pattern.
- **Fast A3 trio:** pass. The variant run uses as_of 2026-03-31 and an accepted CP-1 head, so a value hard-coded to the oracle could not pass.
- **FP05:** not covered anywhere. It is G2's.

### M2 (round 5 item 1)
The rule is correct and fails closed.
- A base is offered only when the 5 operands are MILLIONS, USD and scale 1e6.
- A `currency=None` is refused. Base, view and core come from one derivation.
- p8(b): the EUR-thousands LTM base is refused as `not an offered period`.

Skipping an unsettled operand is right.
- A missing operand stamps no amount, and every fact without an amount carries no currency (`r3_unsettled_stamp.py`, exit 0, including missing operands tagged EUR thousands).
- Checking them would only drop gap bases because of metadata on a value that is absent.
- This is narrower than the ruling's wording ("every operand fact it reads"). Record that in the lease text at the close.

No frozen value moves. The oracle-equality tests pass, `cases/` is untouched, and p1/p5 show the oracle heads' views and offered periods unchanged.

### Lows and Info
- **L1 to L3:** fixed.
- **L4:** the `module_id` check is fixed (mutant killed). The public-API forged facts remain as before: a caller-built `Upstream` with EBITDA ×10 still composes (`r4`, ebitda 300). This is Low, unchanged, and not reachable through submit, probe or view.
- **Info items:** fixed. The base_period and label lines are clipped, and the v17 skip is removed.
- **New Low:** both A3 unreplaced-figure tests assert only "invalid with issues". The real issue is the v11 `Malformed run text` line (`r2`); pin it.
- **New Info:**
  - The A4 read-body test does not isolate the view replay the way S1a's `_verify_calls_reads` assertion does.
  - The deferred claim check looks up FIG ids by label without the T4.10 filter that `cp2a_runs` applies.

Not verified: none of the 15 deferred tests or `cp2a_runs.py` has run; anything against a genuine CP-1 head, including its real T4.10 units; G2's FP05 rendering; `mutants_reg.py` was not re-run.
