# G1-X fix round 2 report (controller-saved from the implementer's hand-back)

G1-X fix round 2 is done: the `_fill` TypeError mapping is gone, the new test was red before the removal, and all gates exit 0. The G1 and S1a suites are still deferred, so this round is built, not done.

**Commits** (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/g1x-fill`, branch `claude/g1x-fill`, on 0a8dc5a):
- `abdf53e` is the cherry-pick of 31aeee0 (LEAD's 0d). It applied cleanly and I did not edit what it brought.
- `857081c` is `fix(owner): G1-X fix round 2: remove the _fill TypeError mapping`. It touches only `src/deploy_workflow/owner_workflow.py` and `tests/test_owner_g1x.py` (+34/−29).

**Changes**
- **Mapping removed.** In `_verify_submissions` the recorded payload's fill is now a plain call, with no `except TypeError` and no comment.
- **Docstring.** `verify_owner_run_receipt` no longer names the mapped call. It now says only that programming errors (`TypeError`, `KeyError`, `StopIteration`, `AttributeError`, ...) propagate unchanged.
- **Old test replaced.** `test_verifier_maps_a_forged_payload_type_error_to_identity_mismatch` was removed. After the cherry-pick it failed at its first check ("DID NOT RAISE TypeError"), because `normalise` no longer raises on that payload.
- **Catch at about :2041 (`serve_json_lines`) left as is.** It is the transport's bad-arguments catch and was already there before fix 1 (it came in with e331a87), so it did not exist only for this case.
- **No other `_fill` call site relies on the mapping.** There are two:
  - :899, at runtime `submit_review`, was never inside the mapping.
  - :1650, in the verifier, was the mapped call.
  - The test uses of `owner._fill` (:665, :768) call it directly.

**Test:** `test_verifier_replays_a_non_str_discriminator_tag_as_invalid`
- A real run submits `{"note":"fine","parts":[{"kind":[]}]}` at the viewed step. `normalise` returns it unchanged, the step is journaled `invalid`, the dispositions are `[valid, valid, invalid, valid, valid]`, and the receipt verifies (`accepted`) with nothing raised.
- With `owner.normalise` patched to raise `TypeError`, the verifier must let that `TypeError` through.
- **Red seen with the mapping in place:** every assertion passed up to the last one. There, `WorkflowError: identity_mismatch` was raised from the mapping at `owner_workflow.py:1656`, where the test expects a `TypeError`.
- **After the fix:** `tests/test_owner_g1x.py` and `tests/test_schema_normalise_escapes.py` give 33 passed in about 10.5 s.

**Mutants:** the probe is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-fix2/mutants.py`. Each mutant runs the new test in its own full temporary copy of the worktree; the probe exits 0.

| Mutant | Exit | Expected | What it shows |
|---|---|---|---|
| M0: no mutation | 0 | 0 | The copy itself passes |
| M1: mapping restored | 1 | 1 | Caught |
| M2: mapping restored, new test's assertion dropped | 0 | 0 | That assertion is the one that catches M1 |
| M3: 0d tag guard reverted in `schema.py` (copy only) | 1 | 1 | The test also pins 0d |

**Gates** (all exit 0):
- `ruff check` on both touched files.
- `ruff format --check` on both touched files.
- `MYPYPATH=src mypy --strict src` (111 files).
- Extra: `mypy --strict` on the test file.

**Tracking note:** `docs/rulings/2026-10-28-stage1.md:856` still describes the mapping as tracked by LEAD. It is now obsolete, and docs were outside my write scope.

Not verified: the G1 suite (`tests/test_owner_workflow.py`) and the S1a suite (`tests/test_owner_s1a.py`), both deferred; whole-src ruff; GitNexus `detect_changes`; the lone-surrogate `submit_review` crash, which is out of scope and with the user.

agent=general-purpose(opus) fix-rounds=2 gates-first-pass=y
