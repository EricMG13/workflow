# G2 genuine cp1-model failures: root cause and smallest fix plan (stage contract; mx-autonomous, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Code: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i4` (`claude/s3-i5` 18dc1fa; read only, never write there). The G2 test file at the fix-round tip is `git show ee95ffb:tests/test_owner_rendering.py`. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

G2 has had two Sonnet fix rounds (rulings items 22 and 26). By the ladder you find the root cause and write the smallest fix plan; a fresh `mx-feature` carries it out. You write no code.

## The failures (`<S>/i5/g2cp1.log`; 6 passed, 2 failed, 86 min)
1. `test_genuine_cp1_model_positive_delivery` (`tests/test_owner_rendering.py:676` at 18dc1fa). The lease test 3 equivalence: `(destination / "model" / name)` differs from `(fin_model / name)` for a `model/` file, first byte difference at index 357 (`b` vs `6`). The banner-free report HTML compares equal just before. `fin_model` comes from `runs["fin_positive"]`, a separate financial run, and is not derived from the store G2 rendered.
2. `test_genuine_cp1_model_extra_attempt_is_refused` (:766). The test calls `Execution(store).begin("CP-1")` on the settled store to make an extra attempt. The product refuses it (`src/deploy_vii/execution.py:660`, "Input set is settled or its one repair has been consumed"), so G2 is never reached. The G2 continuation report had already flagged this test.

The run's stores may still exist under `/private/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/pytest-of-ericguei/pytest-2279/` (`g2-cp1-model0/`, `test_genuine_cp1_model_positiv0/`). Use them before rerunning anything; a rerun of one case takes 10 to 20 minutes.

## Inputs
| Item | File |
|---|---|
| Lease | `docs/OWNER-RENDERING-LEASE.md`: the body's acceptance tests (test 3, the equivalence with `render_financial_slice`; the extra-attempt refusal), and rev 1-3 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 2, 4, 7, 16, 20, 22, 25, 26 |
| Code | `src/deploy_workflow/owner_rendering.py`, `src/deploy_workflow/financial_rendering.py`, `src/deploy_vii/execution.py` (`begin`), and the `runs`/`inputs` fixtures in `tests/test_owner_rendering.py` |

## Process
1. For failure 1, diff the two `model/` files and name the differing field. Then decide which is wrong:
   - G2's delivery;
   - the test's choice of comparison input. The lease may mean the same store, receipt and model, rendered both ways;
   - a genuine difference the lease does not allow.
   Cite the lease text.
2. For failure 2, state what the lease means by an "extra attempt". Say how a test can legitimately produce one under the threat model (attacker-controlled store bytes), or whether the product's refusal already covers the case. Cite the lease.
3. For each failure, write the smallest fix plan:
   - the files and functions;
   - the RED test;
   - the gates;
   - whether a lease or oracle change is needed. If one is, it goes to a separate preparer, so say so plainly.
   Save each probe as a script in `<S>/g2-rca/`.

## Output (return as text, at most about 1.2k tokens)
Root cause for each failure, with file:line evidence; the fix plan for each; lease or oracle needs; probe scripts; `Not verified:` line.
