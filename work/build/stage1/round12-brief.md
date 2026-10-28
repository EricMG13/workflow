# Round 12 (LEAD c27760e, lane 688f185): rule W, B10 blank Cf, CP-2H B8, CP-4C B7

The rulings are in `docs/rulings/2026-10-28-stage1.md`, `# Round 12`. A ruling beats every brief. This is a rulings round, so `fix-rounds=0`.

## Integration
- The shared library and each module merge into the integration branch `claude/round12`, in worktree `round12`, cut at lane 688f185.
- The lane takes `claude/round12` only when every part is approved. The new library cases go red in every module until that module applies the round.
- Each module round works in its own worktree, branched from the `claude/round12` tip named in its dispatch. In Step 0, `git merge --ff-only claude/round12` and confirm HEAD equals that tip.

## Part L: library and the blank predicate (first; one Opus agent; mx-feature review)
Work in worktree `round12` on `claude/round12`.

1. **Predicate.** Add `src/deploy_workflow/owners/blank.py` with one function: `is_blank(text: str) -> bool`. It is true when every character satisfies `str.isspace()` or has `unicodedata.category(c) == "Cf"`. `""` is blank, as `not "".strip()` is today. Test it in `tests/test_owner_blank.py`, including U+200B, U+FEFF, U+00AD, U+2060, `" ​\n"`, `"a​"` (not blank) and `""`.
2. **`tests/defect_classes.py`.**
   - Add `"​"`, `"﻿"`, `"­"` and `" ​\n"` to `BLANK_VALUES`.
   - Add the rule W quote cases, each refused for a signed figure:
     - a spaced minus: page and quote `- 25`;
     - an interior `-\n` with the quote spanning the break;
     - U+2212 then NBSP;
     - `(\n25)`;
     - an edge figure after a page `- `.
     Draw the cases from LEAD's probe `p_sign_breaks.py`, part A. Its path is in round 12 "Probe".
   - Add the accepted controls: `A-\n25` and `2024-\n2025` (hyphen wrap, not a sign), `95-96`, and a line break with no minus.
   - Each W case gets its minimal accepted twin, the same as the round 11 edge cases.
   - If an existing case's expected outcome changes under W (for example a spaced range), flip it, and say which cases changed and why.
   - Update the module docstring.
3. **Selfcheck.** Update `tests/test_defect_classes_selfcheck.py` to match, so it passes.
4. **Probes.** Rerun the reviewer's reference reader, `<S>/defect-classes-review/ref_reader.py`, in a copy under `<S>/round12-lib/` with W added, and report its mismatches. Also rerun LEAD's `p_sign_breaks.py` from a copy.
5. **Gates.** Run the selfcheck and `tests/test_owner_blank.py`, plus `ruff check`, `ruff format --check` and `mypy --strict` on the changed files.
6. **Expected red.** Running `tests/test_method_*.py` now fails in the modules. List the failing modules and counts in the report, as input for the module rounds; do not fix them.

## Part M: module rounds (each from the `claude/round12` tip after Part L)
Every module replaces its blank test (`not x.strip()` or its equivalent) with `blank.is_blank(x)`, at the same position and with the same pinned frame. `""` and null handling stay unchanged, and so does the controller decision on a schema `""` refusal.

| Module | Worktree | Work beyond B10 | Review |
|---|---|---|---|
| CP-1D (first) | `cp1d-stage1` | Rule W per the round 12 CP-1D text: `_SIGNED_AMOUNT`, the parenthesised arm, and `_cut`/`_ROUND10_MINUS`. Move `tests/test_method_cp1d.py:1154` to the refused list. Run LEAD's `p_sign_breaks.py`. | mx-precise |
| B10 batch | `round12-b10` (new) | B10 only for CP-1C, CP-DR, CP-L10, CP-2G, CP-3, CP-4, CP-5, CP-2A and CP-3C: one agent, one commit per module. | mx-feature |
| CP-3D | `cp3d-stage1` | Rule W: `_MINUS`/`_tokens`, `_CUT_BEFORE`, `_cut`. | mx-precise |
| CP-8 | `agent-a3cc9818386e8861a` | Rule W: `_SIGN` in `_MULTIPLE`/`_DECIMAL`, the parenthesised arms, `_whole`. | mx-precise |
| CP-2E | `agent-a219254fe68cc1c2d` | Rule W in `_unsigned`, and the labelled reader. The `bool()` asymmetry at cp2e.py:715 (round 12 Info). | mx-precise |
| CP-2H | `agent-a52b5ec0919986ddb` | B8: `_block` sets `breached=True`; every case listed under "The lane today" is refused. B9 stays as built. B7's plain test waits for the release merge, so skip it here. | mx-precise |
| CP-4C | `agent-a2c15c441717ec41c` | Round 11 blank class on the `plain` fields (end review R3 M2: `cp4c.py:926-945`, `<path>: empty text`, `""` included). B7: refuse `{ } [ ]` in a claim name or valuation label with `<path>: reference syntax is not allowed`, at the #9 per-field step after `Bare figure`. Run LEAD's `p_cp4c_b7.py`. | mx-adversary |
| CP-2D | `agent-a69f2394899aee6d5` | B10 only. | mx-feature |

CP-3D, CP-8, CP-2E, CP-2H, CP-4C and CP-2D start after the riding-Lows batch (`stage1-lows`) is merged into the lane, and the lane is merged into `claude/round12`, because they edit the same test files.

## Rules (all parts)
- **Files:** the module's `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py`. For Part L only: `owners/blank.py`, `tests/test_owner_blank.py`, `tests/defect_classes.py` and the selfcheck.
- Never edit `cases/`, `src/deploy_vii` or the `methods/*.md` files. The guard-limit notes for W and B8 are Stage 2 notes, recorded by the controller.
- Write each test first and watch it go red for its cause. No stub, fake value or catch-all. Every frozen case still passes.
- **Gates (all exit 0):**
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py tests/test_defect_classes_selfcheck.py`;
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on the changed files.
- **Mutants:** from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show that each rule's revert is killed: W's minus space, W's parenthesis space, and B10's `Cf` test. Put probes under `<S>/<cp>-r12/`.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.
- **Commits:** end each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report (as text)
- the commit;
- each ruling with its test;
- mutant and probe exit codes;
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
