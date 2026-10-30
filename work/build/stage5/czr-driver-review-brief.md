# CZR driver: review (stage contract; mx-precise, read-only)

Change: `claude/s5-czr-driver2` `cf4c0ec..9ec5eca` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a49f08eb1911e17e7`. It touches only `tests/czr_runs.py` and `tests/test_czr_driver.py`.
- RED: b8612b5, then ce3582d. The controller ran it: 17 failed for the predicted causes.
- Implementation: 8ee31c4. Gate fixes: 9ec5eca.
- Controller gates on 9ec5eca: the CZR driver, case and fixes suites gave 289 passed and 7 skipped; ruff check and format exit 0; `MYPYPATH=src mypy --strict tests/czr_runs.py` exit 0; suppressions 13 and 5. Logs: lane `work/build/keep/czr-driver-red.log`, `czr-driver-gates.log`, `czr-driver-gates2.log`.
- Brief: lane `work/build/stage5/czr-driver-brief.md`, including its Addendum. Rulings: items 70-72, plus the run id ruling `czr-2026q2-earnings-update-no-cp1b-v1` (it must differ from the case manifest's id because the run omits CP-1B).

Write probes only under lane `work/build/keep/czr-driver-review/`. Run Python as one plain command from the change's worktree root. If it is refused, stop and report it; do not work around it. Run no genuine owner run.

## Check
1. **The docstring is a complete, truthful contract** for Workflow Test, which writes `submissions.json` from it alone:
   - stage order;
   - `read_inputs` (which steps must call it: every step whose spec `inputs` is not `none`, and that includes the CP-1 `financials` step);
   - `figures` selectors;
   - FIG binding only in JSON read bodies;
   - refs from every `{ref}` list, with conflicting display raising;
   - `PACK_PLACEHOLDER`.

   Check each claim against `owner_workflow.py`.
2. **The plan.** `plan(["CP-1", "CP-2", "CP-5"])` gives CP-0, CP-1, CP-1A, CP-2, CP-5, and `OwnerWorkflow.create` accepts the pack. Probe it.
3. **Binder correctness.** Exactly one match; no fallback; the head is settled (accepted or restricted) and exactly one. Facts come from the right head. The ref must be in the stage's own read body, with unit and spelled matching. Check that `_read_body`'s narrow `except json.JSONDecodeError` cannot hide a failure for a JSON-body step.
4. **Stage loop.** It reproduces S1a's semantics: calls, then submit, with the token replaced after binding. `require_read` reads the live spec. A refused submit raises. `finish` publishes and seals.
5. **Tests are real.** No fake standing in for the workflow, beyond the declared `read_inputs` spy. Check whether that spy hides behaviour.
6. **Policy.** No stub, no catch-all.

## Output (text, under 600 tokens)
- verdict (APPROVE or REVISE);
- findings ranked High, Medium, Low, each with the probe path and exit code;
- a `Not verified:` line.
