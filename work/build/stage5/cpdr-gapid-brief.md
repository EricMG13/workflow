# CP-DR: refuse an agenda gap id too long to compose (stage contract; mx-feature, test-first)

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s5-cpdr-gapid 6e5f6a3` (the lane tip) and confirm the tip. Ruling: `docs/rulings/2026-10-29-stage3.md` item 69.

## Inputs
| Item | File | Why |
|---|---|---|
| Defect | `work/build/stage2/lows.md`, the "CP-DR gap id of 139-153 characters" line | what wedges |
| Owner code | `src/deploy_workflow/owners/cpdr.py`: `IDENTIFIER_MAX`/`QUESTION_ID_MAX` (:449-457), `_question_issues` (:216), `validate_research` (:284-316), `_parse_gap`/`parse_agenda` (:160-210), every id built from `gap.gap_id` (`_agenda_cells` :588, the per-gap rows :590-630, `compose` :704-780, calculation ids `cpdr-{row}-{field}` :506-556) | where ids are composed |
| Pattern to follow | `tests/test_connect_cpdr.py:1112-1155` (the three `question_id` length tests) | the same shape for gap ids |
| Identifier limit | `src/deploy_vii/contracts.py:14` (`max_length=160`) | read only; do not edit `src/deploy_vii` |

## Process
1. **RED first.** Add tests to `tests/test_connect_cpdr.py` beside the `question_id` tests. You will need a CP-0 module whose agenda carries a gap id of a chosen length. Build it from the existing helpers (`cp0_module`), not a fake.
   - `test_the_longest_accepted_gap_id_composes`: with an agenda gap id of `GAP_ID_MAX` characters and a matching submission, `check` is empty and `compose` returns facts.
   - `test_a_gap_id_too_long_to_compose_is_refused_at_validation`: parametrised over +1 and the 160-character `Identifier` maximum. The validation issue is exactly `gap_id is too long to compose its fact ids (at most <GAP_ID_MAX> characters): <id>`. `ENTRY_VALIDATOR` returns no output and carries that issue.
   - `test_gap_id_max_is_the_longest_id_the_composer_accepts`: at `GAP_ID_MAX + 1`, `compose` raises (so the constant is tight).
   - Run them and record that they fail for the reported cause (the constant is missing, or `compose` raises) before any fix.
2. **Fix.**
   - Add `GAP_ID_MAX`, derived like `QUESTION_ID_MAX` from the longest id built from a gap id. Check every family: `TDR.1.<gap>.<field>` over `TDR1_COLUMNS`, the calculation ids, and any other id. Use a comment as short as the `QUESTION_ID_MAX` one.
   - In `validate_research`, add the issue once per agenda gap whose id is longer, in the rule-2 position (per agenda gap), using `_line` as the question rule does.
   - No other behaviour changes. Frozen texts and oracles must not move.
3. **Gates** (report each command, its output tail and exit code):
   - the new tests, and then all of `tests/test_connect_cpdr.py`;
   - `tests/test_method_cpdr.py`;
   - `ruff check` and `ruff format --check` on the two changed files;
   - `mypy --strict src/deploy_workflow/owners/cpdr.py`;
   - suppression counts: `git grep -c "noqa"` and `git grep -c "type: ignore"` totals stay ≤ 13 and ≤ 5.
   - Python: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests <lane>/.venv/bin/python -m pytest -q -p no:cacheprovider <files>`, where `<lane>` is `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Do not run `tests/test_owner_cpdr.py` (genuine runs; the controller runs it).
4. **Commits.** One commit for the RED tests and one for the fix, each ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Rules
- No stub or fake value standing in for real behaviour.
- No catch-all that hides a failure.
- Edit only `src/deploy_workflow/owners/cpdr.py` and `tests/test_connect_cpdr.py`.
- Never use bare `git stash`.
- If any action is denied, stop and report it. Do not ask the controller to perform it.

## Output (return as text, under 600 tokens)
- worktree path, branch and tip SHA;
- the RED evidence (test node names and failure lines);
- the value of `GAP_ID_MAX` and the id family that sets it;
- each gate's command, tail and exit code;
- `Not verified:` line;
- ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n>`.
