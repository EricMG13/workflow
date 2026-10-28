# CP-3D round 6h report (controller-saved from the implementer's hand-back)

## CP-3D round 6h: applied as commit `0b0835f` on `claude/cp3d-stage1`

Recovery `percent_text` now gets the leading-zero check. The level order was already as ruled, and two new tests pin it. All gates exit 0, and all three mutants are killed.

**Commit:** `0b0835f` sits on top of `22e9166`. Step 0 merged the lane into the worktree as `7783bcb`; that merge did not touch the CP-3D files. The commit changes only `src/deploy_workflow/owners/cp3d.py` (+3/−1) and `tests/test_method_cp3d.py` (+40). No pinned refusal changes: the frozen recovery is `70`, and the pinned `recovery_out_of_range` (`100`) passes unchanged.

**Rulings and their tests:**
1. **Recovery `percent_text` gets the leading-zero check** (`_check_recovery`, cp3d.py:597-598). It uses the existing wording with the frame's path: `recovery: percent_text <x> must have no leading zero`. It runs after the `recovery.rationale` check and before the shape and bound check.
   - Test: `test_6h_recovery_percent_text_gets_the_leading_zero_check`.
   - `070` was accepted before the fix; it now gets the leading-zero issue.
   - `0100` got `recovery: percent must be at least 0 and below 100` before; it now gets the leading-zero issue, which pins "before the bound".
   - `0.5` stays valid.
   - The first two cases were red before the fix, as expected.
2. **The leading-zero check is a shape check, after occurrence and before the bid/offer label check.** The code already had this order (cp3d.py:447-456), but nothing tested it: the 6g tests use labelled tokens such as `bid 0098.50` and `offer 0200`.
   - Test: `test_6h_leading_zero_comes_before_the_label_check`, two cases with unlabelled tokens.
   - A bid quoting the offer's `0200` gets `observations[0]: level_text 0200 must have no leading zero`.
   - Talk at the bid's `0098.50` gets `observations[2]: level_text 0098.50 must have no leading zero`.
   - Both passed from the start, as guards.
3. **`observations[i]` as the path for levels:** confirmed, no change.

**Mutants** (from a full temporary copy, with no bytecode written):

| Mutant | Exit | Killed by |
|---|---|---|
| control | 0 | — |
| recovery check removed | 1 | both 6h recovery cases |
| recovery check moved after the bound | 1 | the `0100` case |
| level check moved after the label check | 1 | both order cases, and nothing else |

The script exits 0. It is at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-6h/mutants_6h.py`.

**Gates, all exit 0:**
- pytest on `tests/test_method_cp3d.py`: 234 passed.
- `ruff check`.
- `ruff format --check`.
- `MYPYPATH=src mypy --strict` on both files.

**Hits, for LEAD:** `prose.issues` and `bare_figures` flag the new string with the submitted value in it (`Bare figure: 070`, `Bare figure: 0100`). The frame with `<x>` in place of the value is clean. The existing strings hit the same way: the 6g `margin: bps_text 025 must have no leading zero` gives `Bare figure: 025`, and the pinned `recovery: percent must be at least 0 and below 100` gives `0` and `100`. These are validator issue texts, not claim prose. The probe is `prose_probe.py` in the same scratchpad folder.

I did not touch the sign issue (`−0.25` read as +0.25); it stays with LEAD.

**Not verified:**
- A recovery text that is not a number but starts with `0` and a digit (e.g. `05abc`) now gets the leading-zero issue instead of the bound issue. This matches how the other numeral fields behave, but no test covers it.
- The full suite and Stage 2 were not run, per the rules.
- The mx-precise review of both commits is still pending.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y (my first gate run came before the edit had applied, so it showed the same red; with the fix in place every gate passed the first time)
