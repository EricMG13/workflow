## G2 genuine cp1-model: root causes and fix plan

Both failures are defects in the tests. G2's product code is right in both cases. Code read at `s3-i4` 18dc1fa; the line numbers match the failure log.

### Failure 1: `test_genuine_cp1_model_positive_delivery` (tests/test_owner_rendering.py:675-679)
**Evidence.** Probe 1 compared the model files the failed run left on disk:
- `model.html` and `calculation.json` are byte-equal across all four copies: G2's input, G2's delivery, the financial publication and the financial delivery.
- `receipt.json` differs only in `"ticket_id"` (line 11). G2's is `be6cc6b8-…` and the financial run's is `6b1fd12e-…`. `head_sha256`, `cp1_head_sha256` and `pack_sha256` are equal.
- Each `ticket_id` is the CP-MODEL attempt ticket of its own store. The ticket is `str(uuid4())`, minted at `src/deploy_vii/execution.py:662`.
- G2's `model/` is byte-equal to its own G1 publication, and the financial delivery is byte-equal to its own publication.

**Cause.** The assertion `destination/model/name == fin_model/name` compares two independent producer runs, and every run mints a fresh random ticket. It cannot pass for `receipt.json` on any run.

The "same store rendered both ways" reading is not possible: `render_financial_slice` takes a `FinancialSliceReceipt` and a store with a `financial-slice-audit` log (financial_rendering.py:31-108), while G2 takes an `OwnerRunReceipt` and a store with an `owner-run-audit` log. So the test's choice of comparison input is wrong. G2's delivery is not, and nothing differs that the lease forbids.

**Lease text.**
- Body, Acceptance 3 (lease :115): "the model files are byte-equal". It does not say what they must equal.
- Body, Outputs: "`model/{model.html,calculation.json,receipt.json}` byte-equal to the G1 publication". That holds today.

**Fix plan (test only, `mx-feature`).** In `test_genuine_cp1_model_positive_delivery`, replace :675-679 with:
- For each of the three files: `destination/model/n == model/n` (G2's own G1 publication) and `fin_destination/model/n == fin_model/n`.
- `model.html` and `calculation.json`: byte-equal across the two runs.
- `receipt.json`: parse both. Assert each `ticket_id` equals the CP-MODEL attempt ticket in its own store (`Execution(store).read().attempts`, and the same for `fin_store`). Assert the dicts are equal once `ticket_id` is removed.

**RED test.** The current test at :676 fails for exactly this cause (log: "index 357 b != 6"), and probe 1 reproduces it from disk. After the fix, it must still fail if G2 copies the financial publication instead of its own.

**Lease or oracle.** No oracle change. Modules needs to rule on what Acceptance 3's "byte-equal" means before the fixer starts: "each delivery's `model/` is byte-equal to its own G1 publication; across the two runs the content is equal except the per-attempt `ticket_id`". If Modules wants the lease text itself changed, that goes to a separate preparer.

### Failure 2: `test_genuine_cp1_model_extra_attempt_is_refused` (:762-767)
**Cause.** On the settled positive store, CP-0, CP-1 and CP-MODEL are each finished with no issues (probe 2). `begin` therefore refuses every planned module ("Input set is settled…", `execution.py:659-660`), and `current_inputs` refuses any module outside the plan (`:231-232`). The product cannot produce an extra attempt here, so the test fails while setting up and never reaches G2.

**What the lease means.** The Store refusal (lease :119) is "an extra attempt": a store that holds an attempt the receipt does not account for. The Capture clause requires "no attempt is pending", plus the snapshot hash and begins checked against the receipt.

Under the threat model the store bytes are attacker-controlled, so the legitimate test forges the attempt. The D1 precedent is `store._write(snapshot.model_copy(...))` at `tests/test_financial_render.py:285`. The product's `begin` refusal covers the honest path only.

Probe 2 forged a pending CP-1 repair attempt (number 1, `repair_of` the first ticket). The forged store still reads back, and `render_owner_slice` refuses it with `owner_render_unauthenticated` and leaves no destination.

**Fix plan (test only).** In `test_genuine_cp1_model_extra_attempt_is_refused`:
1. Assert `pytest.raises(ValueError, match="settled")` on `Execution(store).begin("CP-1")`. This records why forging is needed.
2. Build `Attempt(ticket_id=str(uuid4()), module_id="CP-1", inputs=current_inputs(snap, "CP-1"), number=len(prev), repair_of=prev[-1].ticket_id)`, then call `Execution(store)._write(snap.model_copy(update={"parent": snap.content_hash(), "attempts": (*snap.attempts, extra)}))`.
3. Assert that the store reads back and that its last attempt is the pending forged ticket.
4. Call `_refused(tmp_path, store, receipt, model, "extra-attempt")`. Pinning `code="unauthenticated"` is optional; it was observed only on this store.

New imports: `Attempt`, `current_inputs` and `uuid4`.

**RED test.** The failure at :766 shows the current setup cannot create the case.

**Lease or oracle.** None needed.

### Gates for both fixes
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on `tests/test_owner_rendering.py` (lease test 7).
- `pytest tests/test_owner_rendering.py -k genuine_cp1_model`. The last run took 86 minutes; run it under the lock.
- The fixer runs both probes and reports their exit codes.

### Probe scripts
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-rca/probe1_model_diff.py` (argument: the pytest dir). It exits 0 when G2's `model/` equals its own input publication, and it prints the diff across runs.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2-rca/probe2_extra_attempt.py` (arguments: `<code-root> <pytest-dir> <scratch>`). It works on a scratch copy only and exits 0.

Both exited 0 on pytest-2279.

Not verified: no pytest run. The rest of failure 1's test (:680-691: `assert_scope_figures`, the head and section checks, `verify_owner_rendered_slice`) has never run, because the test stops at :676 and could still fail after the fix. The `owner_render_unauthenticated` code was seen on one store only. I did not check whether the newer branch ee95ffb changes these two tests; its diff against 18dc1fa touches neither hunk, judging by the hunk list.
