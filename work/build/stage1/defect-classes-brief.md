# Shared defect-class cases: case library and inventory (AGENTS.md rule 3; LEAD round 11)

This task builds the shared test library and takes an inventory of which modules fail it. It changes no owner code. After it merges, each failing module gets its own fix round that runs these cases from its own test file. In this task, implement no owner fix.

## Step 0
1. `git worktree add "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/defect-classes" -b claude/defect-classes claude/module-dev-status-review-0981b6`, run from the lane worktree.
2. `EnterWorktree(path=".../defect-classes")`.
3. Confirm that HEAD equals the lane tip.

## Inputs
| File | Section | Why |
|---|---|---|
| `docs/rulings/2026-10-28-stage1.md` | `# Round 10` §1 and Parentheses; `# Round 11`: "Quote readers" B1, B3; "Blank text is one defect class" | The rules each case encodes |
| `work/build/stage1/quote-normalise-brief.md` | all | The raw-read-after-normalised-match class |
| `src/deploy_vii/quotes.py` | `normalise`, `quoted`, `reading`, `hyphen_wrapped` | The public functions the cases use |
| `src/deploy_workflow/owners/{cp1d,cp3d,cp8,cp2e}.py` | the quote readers | Where the quote-reader cases run |
| every `src/deploy_workflow/owners/*.py` | analyst text fields | Where the blank-text cases run |

## Build
1. **`tests/defect_classes.py`.** This is a helper module, not a test module: name it so pytest does not collect it. It holds the cases as data, plus small assertion helpers. Each case gives:
   - a page text and a quote;
   - the analyst value;
   - the expected outcome (accepted, or refused with the module's pinned "does not occur" issue).

   The cases:
   - **soft hyphen:** U+00AD inside a figure, label or name;
   - **dashes and minus:** U+2212, en dash and em dash inside or before a figure;
   - **NBSP:** U+00A0 between a label and a figure, and inside a name;
   - **signs and parentheses (round 10):** `−25`, `-25`, `–25` and `(25)` refused for an unsigned `25`; `1-December`, `2024-2025`, `95-96`, `S-350`, `mid-25`, `+25` and `(25 percent)` accepted;
   - **edge cut (round 11 B1):**
     - refused: `25` cut from page `425`, `0` from `10 percent`, `0.25` from `-0.25`, and `25)` and `(25` from `(25)`;
     - accepted: a genuine edge figure;
   - **wrap refusal (round 11 B3):** when `hyphen_wrapped(quote)` holds and `"- "` occurs in `normalise(value)`, the name or text value does not occur;
   - **blank text:** `""`, `"   "`, `"\n"`, `" "` and `"\t "` in every analyst text field get the module's pinned empty-text frame, or `<path>: empty text` where none is pinned.

   Each module runs a case through its own reader with its own adapter. The library defines the adapter protocol, as a typed callable: (page, quote, value) to issues. It does not import any owner.
2. **Inventory probe, `<S>/defect-classes/inventory.py`.** Run every case against every applicable module's current lane code, and print a table: module × class → pass/fail, with the failing input. The quote-reader cases apply to CP-1D, CP-3D, CP-8 and CP-2E, plus any other owner you find that reads a value from a quote. The blank-text cases apply to every owner with an analyst text field.
   - List each owner's analyst text fields: path, type, and whether whitespace-only text passes today.
   - For a module that has no pinned empty-text frame, say so.
3. **Self-check.** `tests/test_defect_classes_selfcheck.py` tests the library itself: the cases are well-formed, and every expected-refused case really differs from its accepted twin under `quotes.quoted`. It must not depend on any owner.

## Rules
- Files you may write: `tests/defect_classes.py`, `tests/test_defect_classes_selfcheck.py`. Nothing else. Do not edit owners, `cases/` or `src/deploy_vii`.
- No stub or fake value. A case whose expected outcome the rulings do not pin is left out and listed.
- Gates, each exit 0:
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_defect_classes_selfcheck.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- Commit on `claude/defect-classes`, ending the message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Report (as text)
- the commit;
- the case list, with each case's ruling source;
- the inventory table (module × class → pass/fail, with a failing example);
- the per-owner analyst text fields;
- cases left out, and why;
- the gates;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
