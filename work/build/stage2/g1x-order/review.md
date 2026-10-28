# G1-X plan-order review (mx-adversary)

**Verdict: REQUEST CHANGES.** I found no defect in the source change. Both findings that reopen work are in tests, and one cheap fix closes each.

Probe directory: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-order-review/` (written `<R>/` below). The scratch trees are `<R>/branch` (3218b49), `<R>/merge-cp5` (3218b49 plus the `claude/s2-cp5` diff) and `<R>/merge-cp3`.

**M1 (Medium): the deferred published-path test is broken, so it is not deferred evidence.**
- `tests/test_owner_order.py:335-372`, `test_publication_is_last_in_the_receipt_chain_and_verifies`. With `RUN_PROMOTION=1` it fails at CP-0 after 1.5 s with `invalid ['Assess each selected canonical live consumer exactly once']`. It never reaches the promotion. Output: `<R>/deferred.out`, pytest exit 1.
- Cause: the positive readiness literal has consumer rows for CP-1, CP-1A and CP-2. CP-1A and CP-2 are not selected for (CP-1, CP-MODEL, CP-3D). Probe: `<R>/p5_deferred_cp0_cause.py`, exit 0.
- Fix: set `review["consumers"] = [cp1_row, {**cp1_row, "module_id": CP-3D}]`. With only that change, `<R>/p6_published_path_corrected.py` passes in 513 s (exit 0). `publish` runs once after the later module, the publication transition is last, and the sealed receipt verifies with the published directory. So invariant 4 holds on the published path. The report's "needs 11-26 min" claim is wrong for the test as written.

**M2 (Medium, test strength): no test has two modules after CP-MODEL.**
- Two of my guard mutants survive `test_owner_order.py` and both CP-5 selection tests. They survive on the branch and on the CP-5 merge.
  - `first_later_only`: only the first module after CP-MODEL is checked.
  - `publisher_is_previous`: the publisher is taken to be the planned module just before the one checked.
  - Script: `<R>/mut.py`. Outputs: `<R>/mut_branch.out` and `<R>/mut_cp5sel_merge-cp5.out`.
- A real plan hits this. R3 plus CP-5 plans as (…, CP-MODEL, CP-3, CP-5). Under `first_later_only` it is admitted, which fails open. `<R>/p2_two_later_real.py::test_refuses` kills that mutant on the CP-5 merge (`<R>/mut_p2_cp5.out`).
- Fix: add one consumes case with order (CP-0, CP-1, CP-MODEL, CP-3D, CP-3), where CP-3 requires CP-MODEL and CP-3D requires only CP-0. That one case kills both mutants.

**L1 (Low): the comment edits in 3218b49 name a cause that does not apply on this branch.**
- Here CP-5 has no `OWNER_SPECS` row, so `create` refuses it at `owner_workflow.py:665-666`, before the round-2 guard runs.
- Evidence: with the guard forced open (`guard_open`), both CP-5 tests still pass on the branch. On the CP-5 merge the same mutant is killed, so the round-2 rule becomes the only cause once CP-5 is registered (`<R>/p2_two_later_real.py::test_guard_is_cause`: fails on the branch, passes on the merge).
- The 0cb0ec6 wording was accurate and also cited round 2.
- In `test_owner_workflow.py` the comment also covers the `("CP-NOT-A-MODULE",)` case, which `plan` refuses with a `ValueError`.
- Suggested wording: "on this branch CP-5 has no OWNER_SPECS row; once registered, round 2's rule refuses it through the fan-in."
- Both tests do assert that nothing was written, as LEAD required.

**Info (predates this change): the refusal code is misattributed.**
- `_refusal_code()` labels a terminal publication refusal with the walk's first refusal. That refusal can now be a module planned after CP-MODEL: `<R>/p3_later_refused_real_store.py` returns `cp3d_not_authorized` while the real cause is the blocked CP-1.
- Base 93a627c does the same with CP-1A (`<R>/p4_refusal_code_predates.py`, exit 0). This goes to the owner, not into the task.

**Checked, no finding**
1. **Graph.**
   - `_upstream` walks the same `dependencies(requested)` dict that `plan` uses: required edges, optional edges only when selected, and the CP-5 fan-in, all with canonical ids.
   - Aliases are canonicalised, and every selected module is planned.
   - A cycle makes `plan` raise, which becomes `not_permitted`. `_upstream` also stops on cycles through its `found` set.
   - CP-MODEL's own upstream is computed by the same function.
   - With the real fan-in, R3 plus CP-5 refuses, and only the guard refuses it (`<R>/p2_two_later_real.py`, merge exit 0).
2. **Invariants.**
   - `publish` needs phase `walked`. Only `_finish_walk` sets it, after the last analytical outcome or a refusal that ends the walk.
   - `_terminal` reads only CP-MODEL's direct producers.
   - The verifier pins the publication to the final snapshot on both paths: after-hash equals final when published, before equals after equals final when refused. `_verify_chain` keeps the chain gapless.
   - Forcing `_phase="walked"` and publishing early makes `write_receipt` refuse with `identity_mismatch`. A refused later module on a real store produces a receipt that verifies, with the refusal bound to the publication's `before` (both in `<R>/p3_…`, exit 0).
   - There is no durable resume (module docstring), so a crash between the later module and `publish` means a new run. That is unchanged.
3. **Tests.**
   - The patched tests run the real guard over made-up graphs. The real-registry refusal is first exercised when CP-5 merges.
   - The 0.5 s blocked-CP-1 test is meaningful: it kills `publication_earlier` and `advance_last_not_walked`.
   - A cheap real check exists for the refused path only: assert `receipt.publications[-1].snapshot_after_sha256 == store.read().content_hash()`.
5. **Mutants.**
   - All seven of the implementer's mutants are KILLED when re-run (`<R>/impl_mutants.out`).
   - Of mine, `guard_open`, `required_only_graph`, `terminal_waits_on_all`, `advance_last_not_walked` and `second_det_allowed` are KILLED. Two survive (M2).
6. **Scope, stubs and gates.**
   - Exactly the four allowed files changed. There is no stub or fake value in `src`, and the diff adds no catch-all or suppression.
   - `ruff check`, `ruff format --check` and `mypy --strict` (on `owner_workflow.py` and `test_owner_order.py`) all exit 0.
   - On the branch tree, `test_owner_order.py` plus the two `-k` CP-5 tests pass (17 passed, 1 skipped), and `test_owner_g1x.py` passes. On the CP-5 merge, `test_connect_cp5.py` and `test_owner_order.py` pass (55 passed, 1 skipped).
   - Re-running `p_create.py` on my own merge with `claude/s2-cp3` gives "positive created, gap created".

Not verified: the full `test_owner_workflow.py` and `test_owner_s1a.py` files, because of their slow promotion fixtures (my background run was still going at handback). Also not verified: complexipy and jscpd (not installed), the full suite, a real CP-3 in an owner run beside a published CP-MODEL, and a blocked later module next to a publishable CP-MODEL on a real store.
