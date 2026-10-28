# CP-2G fix round 1 (after the first adversary review)

Review: `work/build/stage1/cp2g/review-adversary.md` (lane worktree). Reviewer probes: `<S>/cp2g-adversary/` (P below) where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Step 0 (merge, oracle batch, re-pin)
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db")`.
2. `git merge claude/module-dev-status-review-0981b6` (lane tip).
3. `git cherry-pick 8483de4`, then `git cherry-pick 3674158` (LEAD's E6 and round 6 oracle batch). Never edit their content.
4. Re-pin only CP-2G's pins that moved. Expected: manifest `b0c8c4bc…`, submissions `25a96ebb…`. Confirm each against `shasum -a 256` of the file and report the full values.

## Fix (test-first; red seen for the reported cause)
1. **M1.** A CP-1 figure named by its calculation id validates (`prose.bind` maps fact ids and calc ids) but `_references` (cp2g.py:2063-2068) and `Claim.references` (:2148, :2154) match fact ids only, so the composed claim cannot be resolved. Resolve both through the same `bind` map, as CP-2A `_figure_refs` (cp2a.py:889) and `cp2_synthesis._figures` (:390) do. Case: `P/p03_calc_id_reference.py`.
2. **M2.** CP-1 unit, scale and currency are never checked (`Operands.from_cp1`, :329-338, :984-986). The lease says "All amounts USD, unit MILLIONS". Fail closed: raise a `ValueError` invariant when a selected CP-1 amount fact is not USD MILLIONS, as CP-1D does (cp1d.py:155-165). No new user wording. Case: `P/p11_unit_currency_unchecked.py`.
3. **M3.** Add tests that kill A10 (accessible liquidity `cc + u`; use undrawn > 0 and assert liquidity), A22 (`_compared` "Differs from CP-1"), A18 (a zero change reads "Flat"). Runner: `P/p06_mutants.py`.
4. **L4.** A G-7 row whose unsettled CP-2A level has no unit raises `KeyError('None')` at :1868. Make it a `ValueError` invariant. Case: `P/p10_g7_unitless_level.py`.
5. **L5.** Add tests that kill the survivors whose rule a lease or ruling pins: A13, B10, B13, B14, B15 (6d level cause for leverage kinds only), V03, V04, V05 (probability guard), V06, V11, V12, V13, V08, V09, S01, R01, R04, R05b, R06, R07, A23. For any you judge equivalent or not pinned, one line each saying why. Runners: `P/p06_mutants.py`, `P/p06b_mutants_followup.py`.

Not in this round (with LEAD): L1 (G-5 vs L5/G-7 precedence), L2 (G-9 non-LTM CP-1D leverage), L3 (G-5 `T2H.7.down` wording), the Info `decimal.Inexact` at 16+ places.

## Rules
- Files: `src/deploy_workflow/owners/cp2g.py`, `tests/test_method_cp2g.py` (plus the pin strings in step 0). Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Gates (exit 0): `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp2g.py`; `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files. Nothing else.
- Run mutants only from a full temporary copy of the worktree.
- New strings: run `prose.issues` and `bare_figures` over them and report hits.

## Report
Commits (step 0 and fix); full pin values; finding → test; exit codes of `p03`, `p11`, `p10`, `p06_mutants.py`, `p06b_mutants_followup.py` and survivors left with reasons; gates; `Not verified:`; ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
