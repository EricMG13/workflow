# Round 13 (LEAD 7ee9c8b, lane 76d7820): Stage 1 end-review rulings

The rulings are in `docs/rulings/2026-10-28-stage1.md`, `# Round 13`, which includes the "LEAD rulings on the For LEAD items" section near the end. Where the draft and the LEAD section differ, the LEAD section wins; item 8's comma-space join is one such case. A ruling beats every brief. This is a rulings round, so `fix-rounds=0`.

**Routing (user):** the implementers are Sonnet (`mx-feature`). Reviews follow the table below.

## Integration
- Round 13 stacks on round 12. Each module works in its own worktree, on branch `claude/r13-<cp>`, cut at the `claude/round12` tip named in its dispatch. The controller made these worktrees.
- Approved work merges into `claude/round12`. That branch reaches the lane once every round 12 and round 13 part is approved.
- **Step 0:** the worktree is clean, and HEAD equals the tip named in your dispatch. If either check fails, stop.
- Every Bash command starts with `cd "<worktree>";`.

## Module tasks
| Module | Ruling items | Work | Review |
|---|---|---|---|
| CP-1D (first) | 7, 8 (W is already in) | Replace the digits arm of `_SIGNED_AMOUNT` with item 7's amended round 10 pattern, comma guards included. Add the LEAD item 8 comma-space join: `<digit>,` and `<digit>, ` join the run in the token, `_cut` and `_CONTINUES`. So `.25`, `-.25`, `(.25)`, `1.2.5`, `1,250`, `1, 250` and `1,\n250` give no figure, and `section 4.2.1 a saving of 25` reads `['25']`. Issue: the pinned exactly-one issue. **Riding Low:** pin the `\Z` anchors in `_W_MINUS` and `_OPEN_PAREN` with the two reviewer cases (`work/build/stage1/cp1d/r12-review.md` Low; probe `<S>/cp1d-r12-review/p_anchor_survivors.py`). | mx-adversary (money) |
| CP-3D | 8 | Tokens: add `(?<![0-9],)` and the comma-space join, with the trailing guard `(?![0-9]|[.,][0-9])` and the comma-space equivalent. `_CUT_BEFORE` and `_CUT_AFTER` take the item 8 forms plus the LEAD comma-space join. **Riding Low** (`work/build/stage1/cp3d/r12-review.md`): pin the guard on `_CUT_BEFORE`'s spaced-minus arm with a `_MARGIN_CLASS` case. The page holds `A-\n25 percent`, the quote is `25 percent …`, and it is accepted. Add its `2024-\n2025` twin. The reviewer's surviving mutant 2 in `<S>/cp3d-r12-review/p_review_mutants.py` must be killed. | mx-precise |
| CP-2D | 1, 3 | **Item 1:** `Cell.period` is set in `_num`. A copy keeps CP-1's period verbatim. A sum or difference takes the one period its operands share, or raises `CP-2D: operands of <fact_id> differ in period`. Any other known numeric fact gets `balance_date.isoformat()`. A gap, not_applicable or text cell gets no period. Every cell carries a `value_class`; a gap takes its twin's class, plus `cp1_operand` and `cp1_unit` for a copied gap. **Item 3:** `Operands` becomes `(status, amount, period, limitation)`. A copy keeps CP-1's status, with its limitation verbatim, and adds `CellState.conflicting`, spelled `∅ G<n>`; a not_applicable copy is spelled `∅ G<n> n.m.`. The dependant reasons and the GAP_OPERAND claim are worded exactly as in the ruling. `_op` and `_gap_missing` keep their positions. | mx-precise |
| CP-3C | 4, 5 (`currency`) | **Item 4:** `Status` takes all four product statuses, and `CellStatus` adds `conflicting`. `_amount` and `_stated_text` return no value for an unknown status. `_op` uses the C-2 frame `Not calculable: <label> is <missing|conflicting|not applicable>`. `_copy` keeps the status, with CP-1's limitation verbatim. `_check_value` requires a reason and no value for every unknown status. **Item 5:** `Cp3cInputs.currency` is CP-1 T4.10 `cash_closing` `Fact.currency`. It must be set, and equal on every MILLIONS fact CP-3C reads; otherwise raise an invariant. Word it in the `CP-3C: …` frame of the module's existing invariants, and say the wording in the report. | mx-precise |
| CP-L10 | 6 | `change` = `close - start` in `Context(prec=200, traps=[Inexact, Rounded, InvalidOperation])`, as cp1d `_EXACT` does. It is never rounded. `_q38` stays for `pct`, and the 2 dp display is unchanged. Test the reviewer's pair (R2 L1, `work/build/stage1/end-review-R2.md`) and a bound-magnitude pair. | mx-feature |

Queued until the module's round 12 is approved and merged: CP-8 (items 7 and 8; `_labelled` joins only on `,<digit>`), CP-2E (item 8), and CP-4C (item 2, plus item 5 `base_period`).

## Frozen oracles (CP-2D item 1)
The CP-2D oracle keys (`period`, and the gap `value_class`) are re-pinned at the Stage 2 release, not now. Never edit `cases/`.
- Where a frozen-case test compares CP-2D output with `expected.json`, apply exactly the ruled delta in the test, as one named table: the added `period` on known numeric cells, and the 5 gap `value_class` keys listed in the ruling. Assert everything else exactly as today.
- Add one test that fails once the oracle is re-pinned. It asserts that the frozen `expected.json` still lacks the delta, and its name and docstring say "remove the delta at the Stage 2 re-pin".
- If CP-3C's tests run CP-2D code rather than reading CP-2D's frozen oracle, say so in the report. The 6 CP-3C principal-copy periods (`q4-2025`) are part of the same Stage 2 delta.

## Rules (all tasks)
- **Files:** the module's `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py` only. Never edit `cases/`, `src/deploy_vii`, `tests/defect_classes.py` or any `methods/*.md`. The guard-limit notes for the item 8 comma costs are Stage 2 notes, which the controller records.
- **TDD:** write each test first and watch it go red for the ruled cause. No stub, no fake value standing in for real behaviour, and no catch-all that hides a failure. Every frozen case still passes, apart from the declared CP-2D delta.
- Every new string is worded exactly as the ruling words it. Where the ruling gives no wording, use the module's existing frame, and say so in the report.
- **LEAD probes:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-review-wip-worktrees-0145fe/d412fa37-e0cf-4abc-a174-1970a42cd5dc/scratchpad/round13/`. These include `p13_quote_classes.py`, `p13_comma_space_join.py`, `p13_cp2d_period_class.py`, `p13_status_prose.py`, `p13_cpl10_exact.py` and `p13_l2_sources.py`. Copy the probes for your item into `<S>/<cp>-r13/`, point LANE at your worktree, and report the exit codes. If a probe's expectation assumes the pre-change code, say which check, and why.
- **Gates** (all exit 0):
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py tests/test_defect_classes_selfcheck.py`;
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- **Mutants:** from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show that each rule's revert is killed: one mutant per ruled clause. Put scripts under `<S>/<cp>-r13/`.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.
- **Commit:** one commit, ending `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Report (as text, at most about 1.5k tokens)
- the commit;
- each ruling clause with its test;
- the mutant and probe exit codes;
- the gates;
- `Not verified:`;
- the ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n>`.
