# H1 fix 1 scoped re-review (mx-precise; controller-saved)

## H1 fix round 1: scoped re-review (commit 278f0aa against 2bd61a7)

**Verdict: APPROVE.** Spec: pass. Quality: pass. I found nothing at High, Medium or Low.

### Spec verdict: pass
- **The diff stays in scope.** It changes only `tests/test_host_h1.py` (+164/−2), with no `src` change (`git diff --stat 2bd61a7 278f0aa -- src` is empty). The two deleted lines are the old `for steps in (...)` loop header at :467 and the old docstring line at :475. Both were widened, not weakened: the malformed tuple at :467-474 is a superset of the old one, and :492-493 adds a core and asserts again. No existing assertion was removed or loosened. F1, I1, I2 and open points 1–6 are untouched, as the brief required.
- **F2 (Medium), fixed:** `tests/test_host_h1.py:630-694`.
  - `_cp1a_journal` (:630-669) builds each head through the real `Execution.submit_step` and `Execution.finish`, then reads it back with `store.read()` and `head_module`.
  - The control journal with unchanged inputs passes (`is True`, :682). So the real settle replay accepts these journals, and each `False` comes from that variant's own Q6 (b) check at `src/deploy_workflow/host.py:589-611`.
  - The `bypass` validator (:648) is the attacker in the review's failure scenario (calling `submit_step` with a bypass validator). It does not stand in for host behaviour, and there is no fake core on this path.
  - The prefix-reversal variant works only because the CP-1A prefix has more than one input. A one-input prefix would equal the control, and the control assertion would then catch it.
  - Each of M24, M25, M26, M20 and M22, applied alone, fails this test at the variant assertion (:694).
- **L1–L4 are fixed.** Each mutant, applied alone, fails its named test:

| Finding | Test | Mutants killed |
|---|---|---|
| L1 | `test_owner_scope_never_applies_to_a_live_contract_module` (:492-493) registers a fake core for CP-1A, so only the guard can refuse | M07 |
| L2 | malformed `STEP_IDS` at :472-473 | M10, M11 |
| L3 | `test_producer_without_a_producing_attempt_refuses` (:697) | M15 |
| L4, passes only | `test_memo_keeps_passes_only` (:733): refused twice, memo stays `{}` | M33 |
| L4, key | `test_memo_key_is_the_snapshot_and_the_producer` (:742): another producer under the cached snapshot, and the cached producer under another snapshot, are both refused, and the key set is pinned | M35, M36 |
| L4, eviction | `test_memo_evicts_the_oldest_pass_beyond_its_limit` (:764): limit pinned at 16; after 20 passes the memo holds exactly the last 16, in order, so the oldest go first | M37 |

  The memo is reset per test by the autouse fixture at :195-198, so the tests do not depend on each other.
- **Survivors match the review exactly.** The 12 left alive are M09, M12, M16, M17, M18, M19, M21, M23, M27, M28, M30 and M31, which is the review's equivalent list.

### Quality verdict: pass
- No stub, fake value or catch-all was added. The only fake core is the existing `_fake_core` (:75), which the H1 review already accepted, used at :492 to isolate the guard.
- Info only, no action needed: M35 and M36 fail first at the key-set assertion (:747), which pins the key's exact shape. The refusal assertions after it would also catch them, by the test's logic, but the run stops at the first failure.

### Exit codes
- **Review probes on the target:** `p01_scope` 0, `p02_producer_forgery` 0, `p03_memo` 0.
- **`mutate_h1.py 1 40`:** exit 0. It ran on a full rsync copy at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-rr1/copy`, with output in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-rr1/mutants.out`.
  - The suite kills 28: M01–M08, M10, M11, M13–M15, M20, M22, M24–M26, M29 and M32–M40.
  - The 12 survivors are listed above.
- **Targeted probe** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/h1-rr1/targeted.py`: exit 0. It applies each of the 13 target mutants alone and runs only the test named for it. All 13 are killed.
- The target worktree is still clean at 278f0aa.

### Gates (target root, venv `bin/`)
- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_host_h1.py tests/test_owner_g1x.py`: exit 0, 38 passed.
- `ruff check tests/test_host_h1.py`: exit 0.
- `ruff format --check tests/test_host_h1.py`: exit 0.
- `MYPYPATH=src mypy --strict tests/test_host_h1.py`: exit 0.

Not verified: the heavy suites (`test_source_tools.py`, `test_source_workflow.py`, `test_owner_workflow.py`, `test_owner_s1a.py`) were not run, per the brief. The forgery and memo tests cover only CP-1A, with no owner-only or CP-2/CP-4 producer. F1, I1 and I2 are still open for LEAD and were out of scope here. The mutants cover only `host.py`, not the test file.
