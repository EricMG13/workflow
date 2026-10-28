# CP-3 re-pin to 2682310 report (controller-saved from the implementer's hand-back)

CP-3 re-pin is done. All four oracle pins moved and now match LEAD's values. The CP-3 test file passes with no change other than the pins, and the R3-identity script exits 0.

**Commits** (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp3-stage1`, branch `claude/cp3-stage1`):
- `git merge claude/module-dev-status-review-0981b6` fast-forwarded to `b4a957f` ("docs: RESUME refresh"). The lane tip had moved on from the `d413066` snapshot, and `6ce4dd1` is an ancestor.
- `9f2c3e4` is the cherry-pick of `2682310`. Its patch-id matches the original (`45577dcf…`), so the content is identical. I did not edit anything it brought.
- `6c6ea02` is `test(cp3): re-pin to the cp3-cp6 R6 oracle (2682310)`, with the Co-Authored-By trailer. It changes `tests/test_method_cp3.py` only: 4 lines added, 4 removed, pin strings only.

**Pin values** (each checked against `shasum -a 256` of the file; each old pin matched the file at `2682310^`):
- manifest.json: `e3cb2217…` → `525c5f1b5ab0c8518b936b099621422d5fcf0424114c0a20b836964c66dd8e10`
- submissions.json: `9f8c10e9…` → `eaecbcd012c3d157d96362c288b842e7c25157aabffff831e68dcd23bffe6b0b`
- expected.json: `3c6ff67f…` → `8ca60c96ac443282ac49a0ded495b751cf3b5457b9491f419a26ca59c0b3c310`
- builder/build.py: `6dac614f…` → `67db98157b66a0861696cf25482a7aba63576025c9e25b9ada976d344ae6d952`

**Test count:** 32 passed in 0.38s, first run. `src/deploy_workflow/owners/cp3.py` is untouched.

**R3-identity script:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3-repin/r3_identity.py`
- **Exit code: 0.** Output is in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3-repin/r3_identity.out`.
- It reads `expected.json` at `2682310^` and at `2682310` from git, so it compares that commit itself rather than the working tree. It sorts every changed leaf into one of three groups:
  - R3: any `R3` or `CP-3` key, or a list item with `run=R3` or `owner=CP-3`.
  - R6: `R6`, `CP-6` or `CP-MODEL`.
  - shared: everything else.
- It also compares every R3 subtree as canonical JSON.
- Result: 31 R3 subtrees on each side with 0 differing, 0 R3 leaf diffs, 0 shared diffs, and 154 R6 leaf diffs. The R6 diffs are rows removed from `{positive,gap}/upstream/CP-1A/R6` (T2D.10 and downstream_readiness), plus changes to `CP-0/R6/plan_order`, `CP-1A/R6/catalogue_size` and `consumers_judged`, and the CP-2 R6 register counts.
- As a check that it can fail, I changed one `CP-3` claim and one `upstream.CP-0.R3` status in memory. The script's functions caught both (9 leaf diffs, 2 subtree diffs).

**Gates, all exit 0:**
- `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp3.py`: 32 passed.
- `…/.venv/bin/ruff check tests/test_method_cp3.py`: passed.
- `…/.venv/bin/ruff format --check tests/test_method_cp3.py`: already formatted.

**Not verified:**
- "R3 path" is my reading: keys named R3 or CP-3, plus refusal and tamper items with run R3 or owner CP-3. An R3 dependency stored under some other key name would be missed. The shared group was empty, so I found no such case.
- The script checks only `expected.json`. For `submissions.json`, `manifest.json` and `build.py`, R3 identity rests on the 32 CP-3 tests passing, not on a structural diff.
- I ran no suite beyond `tests/test_method_cp3.py`. GitNexus `detect_changes` was not run.

Ledger: agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
