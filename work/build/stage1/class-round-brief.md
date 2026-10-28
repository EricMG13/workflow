# Defect-class round (round 11: edge cut, wrap refusal, blank text) plus riding items

This round applies the shared defect-class cases (AGENTS.md rule 3) to one module. The module's own test file runs the library cases through an adapter, and the module code is fixed until they pass. A fix that only applies ruling text counts as a rulings round (`fix-rounds=0`).

Reviews:
- mx-precise for the four quote readers (CP-1D, CP-3D, CP-8, CP-2E).
- mx-feature for a module with blank-text changes only.

## Step 0
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/<worktree>")`.
2. From the worktree root, run `git merge claude/module-dev-status-review-0981b6`. This brings in the library `tests/defect_classes.py` and round 11.
3. Confirm the merge parent, or HEAD after a fast-forward, equals the lane tip named in your dispatch.

## Inputs
| File | Section | Why |
|---|---|---|
| `docs/rulings/2026-10-28-stage1.md` | `# Round 10` §1 + Parentheses; `# Round 11` "Quote readers" B1, B3; "Blank text is one defect class" | The rules |
| `tests/defect_classes.py` | all | The cases, the `Adapter` protocol, `quote_failure`, `blank_failure`, `EMPTY_TEXT` |
| `work/build/stage1/defect-classes-report.md` | your module's inventory row and field list | What fails today |
| `<S>/defect-classes/adapters/<cp>.py`, `<S>/defect-classes/inventory-detail.out` | your module | A working probe adapter, and the exact failing inputs |

## Process
1. **Adapter test first.** In `tests/test_method_<cp>.py`, add an adapter that runs the library cases through your reader (quote cases) and over every analyst text field (blank cases). Parametrise it over the library's case lists. Start from the probe adapter, but bring it under the repo's ruff and mypy gates. Watch the failing classes go red.
2. **Fix to the rulings, with no new wording.**
   - **B1 edge cut.** A figure that touches an edge of `normalise(quote)` occurs only if the page holds the same unsigned whole figure there. Check every occurrence, in every page reading, as round 11 B1 specifies. Use the pinned "does not occur" issue. In CP-1D the amount is not counted, so the pinned exactly-one issue fires.
   - **B3 wrap.** If `quotes.hyphen_wrapped(quote)` and `"- "` occurs in `normalise(value)` for a name or text value, the value does not occur. Use the field's existing issue.
   - **Blank text.** Every analyst text field refuses whitespace-only text with the module's pinned empty-text frame. Where none is pinned, use `<path>: empty text` (`defect_classes.EMPTY_TEXT`). Controller decision: when a `Text` field's pydantic schema already refuses `""` with its existing shape issue, that refusal stands. The frame is required for whitespace-only text.
3. **Riding items** for your module (table below). Write each test first.

| Module | Worktree | Merge | Classes | Riding |
|---|---|---|---|---|
| CP-3D | `cp3d-stage1` | ff | B1, B3, blank | Quote B2 (controller): `(-425)` with `-425` keeps the `_SHAPE` refusal. Apply the parenthesis exclusion only when the match starts with a digit (round 10 review L1, probe `<S>/cp3d-r10-review/p_tip_sign_rule.py` check C). |
| CP-8 | `agent-a3cc9818386e8861a` | ff | B1, B3 (blank passes) | Round 10 review Lows: `s-1.80x` and `_token_once("350", "s-350")` (lowercase guard); `_token_once("1.80", "(see 1.80)")` is True (close-only parenthesis). |
| CP-2E | `agent-a219254fe68cc1c2d` | ff | B1, B3, blank | none |
| CP-1D | `cp1d-stage1` | ff | B1, blank | Round 10 review Lows: an accepting non-Recurring row on an unstated amount with basis `-1.80` gets `Cannot accept an unstated amount` (1D7 first); a `_basis_amounts` row `("saving 1.80)", ["1.80"])`. |
| CP-1C | `cp1c-stage1` | ff | blank | none |
| CP-2D | `agent-a69f2394899aee6d5` | ff | blank | Round 11: a maturity before D0 gets the CP-3C B1 rule. The months and inside-horizon cells become `missing` with `Not calculable: facility <id> maturity date is before the balance date`, and their dependants take the same reason. Own line `Facility <id> maturity date is before the balance date; maturity-wall figures that need it are not calculated.`, label `Facility maturity date (<id>)`, kind Limitation. The claim cause in the L5 frame is `… needs every facility to mature on or after the balance date, and one does not`. Include a D0 − 1 day case and an on-D0 case. |
| CP-2G | `agent-a4377a7580e8e70db` | ff | blank (the 9 `*.limitation` fields) | Round 11 Q12: an explicit `raise ValueError("CP-2G: CP-1D <label> must be USD MILLIONS at scale 1000000, not <currency> <unit> at scale <scale>")` where the CP-1D EBITDA is read, in M2's place. No `assert`. |
| CP-DR | `cpdr-stage1` | ff | blank | none |
| CP-L10 | `agent-aa6ef474a0f78ec9e` | ff | blank (`overall.limitation`, `gaps[0].why_it_matters`, `.action`; and whitespace-only text in the others) | none |

Use `ff` when your branch is already merged into the lane, so the merge is a fast-forward. If it is not a fast-forward, do a plain merge and report it.

## Rules
- Files: `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py` only. Do not edit `tests/defect_classes.py`. If a library case looks wrong, stop and report it.
- Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Every frozen case still passes unchanged.
- Gates (all exit 0):
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show that each rule's revert is killed.
- Put probes under `<S>/<cp>-class/`.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Report (as text)
- The commit.
- Class by class: each case group, then pass or fixed.
- Each riding item and its test.
- Mutant exit codes.
- Gates.
- Stage 2 notes (`methods/<cp>.md`).
- `Not verified:`.
- The ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
