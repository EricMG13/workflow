**Verdict: APPROVE.** No High or Medium findings. No weakened assertions, no frozen-input changes.

## Findings
- Low: none.
- Info 1, item 6 (CP-3D `Acme Term Loan B-2`): pinning only the absence of the B3 refusal, plus the digit refusal as the sole issue, is enough for the L2 intent. L2 was the survivors "B3 gate dropped" and "`'- '` widened"; both are now killed. A fully clean accept is impossible because of the digit rule. The cost is coupling to the `<reader>: digits are not allowed` wording; if that rule is relaxed, update the test by one line.
- Info 2, item 9 (H1 Low A): `_UNIVERSE` is hand-listed (the rows' leased ids plus business, board_minutes, market, bridge), not derived from the cases. The claim that cases name no other ids rests on the implementer. 49/49 widening mutants killed, so it is complete for the widenings tried.
- Info 3, item 2: K5 and K18 were retargeted by the implementer. K5r and K18r both exit 1 on rerun. Six `test_r9_l1..l6` tests exist in `tests/test_method_cp2d.py`. I did not re-judge whether the retargets are faithful.

## Checks
1. Each test matches its source review. The diff adds assertions. The only edit to an existing assertion is the `threshold_unit` input.
2. Each named mutant is killed: cp2d 12/12 (including "schedule: pre-D0 before currency"), cp8 2/2, cp4c 4/4, cp2h M5/M6/M7/M14 4/4, h1 49/49.
3. Skips and retargets are justified.
   - Item 2 is already killed by round 9's tests.
   - CP-3D has 2 surviving mutants, "name not normalised" and "no early return", which class-review I3 calls equivalent.
   - CP-2E has 2 surviving mutants, "raw reference_rate" and "empty-text frame after digits in prose" (frame order), which I1 calls equivalent.
   - CP-2E's L2 and L3 survivors are killed.
4. Nothing changed under `cases/`, `tests/defect_classes.py` or `src/deploy_vii`. `SOURCE_BREACHES` is in `tests/test_method_cp2h.py` only (git grep also lists two work docs, nothing under `cases/`). `threshold_unit` changed from `10.0x` to `10.00x` and is still refused with "Trigger terms not found". The H1 row tests were reshaped into a shared-universe helper, which only widens the `outside` sets.
5. The only src change is the `src/deploy_workflow/host.py` comment, "Eight modules are owner-only (G1-X §1)". The list in it has eight entries.
6. See Info 1.

## Probe exit codes
These are the implementer's scripts under `<S>/stage1-lows/`, rerun from full temporary copies with `PYTHONDONTWRITEBYTECODE=1`. Outputs are in `<S>/stage1-lows-review/*.out`. A mutant counts as killed only on pytest exit 1.

| Script | Exit | Result |
|---|---|---|
| `cp2d_mutants.py` | 0 | 12/12 killed |
| `cp8_mutants.py` | 0 | 2/2 killed |
| `cp3d_mutants.py` | 1 | 10 killed, 2 survived (both equivalent, I3) |
| `cp2e_mutants.py` | 1 | 6 killed, 2 survived (both equivalent, I1) |
| `cp4c_mutants.py` | 0 | 4/4 killed |
| `cp2h_mutants.py` | 0 | 4/4 killed |
| `h1_mutants.py` | 0 | 49/49 killed |

The exit 1 for cp3d and cp2e comes only from the equivalent survivors. My first h1 launch hit a script-name typo (exit 2), so I reran it; the table shows the rerun.

## Gates (all exit 0)
- pytest on the 8 test files: 2041 passed, 1 xfailed. The xfail is the existing strict B5 marker in cp2h.
- ruff check: exit 0.
- ruff format --check: exit 0.
- `MYPYPATH=src mypy --strict`: exit 0 on the 7 test files plus `host.py`. I did not run it on all of `src`.
- The ruff and mypy runs covered the 7 changed test files and `host.py`; they did not cover `tests/test_owner_g1x.py`. The earlier pass with that file failed from my own zsh word-splitting; the rerun is the valid one.

Not verified:
- The full repo suite and slow gates were not run.
- `tests/test_owner_g1x.py` was not linted or type-checked in the final pass.
- GitNexus `detect_changes` and `impact` were not run.
- I did not rerun the reviewers' original probe scripts (`p_survivors.py`, `p2_behaviours.py`, h1b `p06`/`p07`/`p08`/`p10`, `p_overlap_mutant.py`, `p_blank_exit_trigger.py`). I relied on the implementer's equivalents.
- I did not re-review the round 9 tests or the K5/K18 retargets.
- I did not check `_UNIVERSE` completeness against the cases.
- The mutants are hand-written, not mutmut.
