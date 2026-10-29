**Verdict: APPROVE.** M1 is closed and I found no new findings. The fix is one regex change, at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/src/deploy_workflow/owners/cp8.py:130-132`: `_W_MINUS = re.compile(rf"(?<=.){_SIGN} (?=[0-9])")`. The tests were added at `tests/test_method_cp8.py:1851-1892`. Nothing else in the diff changed.

All runs used a fresh `git archive f99db43` copy at `<S>/cp8-r12-fix1-review/copy` with PYTHONDONTWRITEBYTECODE=1.

**Check 1: M1 is closed.**
- I re-ran `<S>/cp8-r12-review/p_wrap_split_edge.py`: **exit 0**.
- All four rows are refused with their pinned B3 issue. That covers decision text for `- 1.25 notes` and `- 2025 notes`, plus the flag span and the size span.
- The new parametrised test also pins `A- 25` and `a - b` as refused in all three fields.

**Check 2: the exemption is exactly W's minus plus the index-0 guard.**
- My probe is `<S>/cp8-r12-fix1-review/p_exemption_bounds.py`: **exit 0**. It checks `_wrap_split` against an independent oracle (W's minus applied to `normalise(value)`, with one character required before it) and against the verdict I expected for each case.
- These are refused (wrap split), failing closed: `- 1.25`, `- - 1.25` (the index-0 `- ` blocks it, though the second one is exempt), ` - 1.25`, `\n- 1.25`, `A- 1.25`, `2024- 2025`, `a - b`, `x - 1.25 - y`.
- These are exempt, as the addendum says, because the minus follows a non-alphanumeric character once normalised: `x\n- 1.25`, `x\t- 1.25`, `x<NBSP>- 1.25` (all three become `x - 1.25`), `.- 1.25`, `(- 1.25`, and `x − 1.25` (U+2212 is in `_DASHES` and maps to `-`).
- `(?<=.)` cannot be fooled by a newline, because `normalise` has already removed every newline before the regex runs.

**Check 3: the accepted case.**
- `is - 1.25 notes` on `is -\n1.25 notes.` raises no B3 issue in the instrument, flag span or size span field (same probe).
- `test_r11_shared_quote_cases[size level-w-minus-wrap-1.25]` is collected and passes in the gate.

**Check 4: mutants.**
- I re-ran `<S>/cp8-r12-fix1/mutate.py` against the copy: **exit 0**. The unmutated copy passes and all 10 mutants are killed, including "guard dropped". Output is in `<S>/cp8-r12-fix1-review/mutate.out`.

**Gate:** pytest on cp8, defect_classes_selfcheck and host_h1: **exit 0**, 802 passed. Output is in `<S>/cp8-r12-fix1-review/gate.out`.

**Exit codes:** p_wrap_split_edge 0 · p_exemption_bounds 0 · mutate 0 · gate 0.

**Info, not a finding:** the lane worktree's `docs/rulings/2026-10-28-stage1.md` (at the lane tip, which includes f99db43) does not contain "# Round 13 addendum". The addendum (a2674c4) exists only in the review and round12 worktrees, so I reviewed against that copy. The brief said the addendum was in the lane worktree; it is not there yet.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: the other B3 callers named by the addendum (CP-3D, CP-2E), since they are outside this diff; ruff, mypy and the full suite; the end-to-end figure read of the signed value `-1.25`, beyond the library case passing.