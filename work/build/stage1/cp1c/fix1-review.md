# CP-1C fix 1 scoped re-review (mx-precise; controller-saved)

**CP-1C fix round 1 scoped re-review** (`git diff 5c9e4e8 50da1c9`, worktree `cp1c-stage1`)

**Verdict: APPROVE.** M1 and L1 are fixed, round 6g is applied as ruled, and every mutant is killed. I found nothing new at High or Medium.

**Gates (from the target root, all exit 0):**
- pytest on `tests/test_method_cp1c.py`: 124 passed. That is the earlier 120 plus 4 new tests.
- `ruff check` on both files: passed.
- `ruff format --check` on both files: passed.
- `MYPYPATH=src mypy --strict` on both files: passed.
- The diff touches only `src/deploy_workflow/owners/cp1c.py` and `tests/test_method_cp1c.py`, with 135 lines added and 23 removed. `cases/` is untouched.

## 1. M1 and L1: fixed
- `claim_c2_before_b1` is killed by `test_b1_claim_comes_before_the_zero_median_sentence` (`tests/test_method_cp1c.py:1136`).
- `claim_b1_drops_median_guard` is killed by `test_b1_claim_sentence_skipped_when_the_median_is_missing_or_no_peer_source` (`tests/test_method_cp1c.py:1147`).
- My other L1 mutant, `accept_conflicting`, is now the ruled behaviour. It is replaced by `reject_conflicting`, which is killed (item 3).

## 2. Round 6g: applied exactly
- **Own-line label** (`cp1c.py:1170`): `{m.label[0].lower()}{m.label[1:]}`. The test pins "adjusted EBITDA margin", "interest coverage (adjusted)" and "total leverage (adjusted)". The mutant that lower-cases the whole label is killed.
- **Conflicting CP-1 fact** (`cp1c.py:747`): a fact with any status other than known, and with a limitation, takes the B1 path.
  - The copy keeps `conflicting` and CP-1's limitation (`Unsettled.status` is widened to `Status` at `:340`).
  - T1C.4 difference, position and of, and T1C.6 difference, are missing with `NOT_COMPARED`, because `c.unsettled` defaults to missing.
  - The claim gets the B1 sentence, and the own line is the B1 line.
  - An absent fact still raises (`:745`, `test_6g_absent_cp1_fact_still_raises`).
  - Peer n, median and outlier_count still equal the frozen positive values. `test_6g_conflicting_cp1_fact_takes_the_b1_path` (`tests/test_method_cp1c.py:1170`) asserts all of this.
- **Unsettled copy** (`cp1c.py:749-751`): unit, currency and scale are replaced. Every other key is copied verbatim through `model_copy`, and `copy()` passes decimals, value_class, calc id, limitation, period and citations through. The test seeds a wrong unit, a currency USD, a scale of 1e6 and decimals 2, and asserts the metric's unit, None, 1 and decimals 2 verbatim. The known path keeps its unit check (`:755`), and the known-wrong-unit mutant is killed.
- **Reading A (currency None and scale 1 for a ratio) is consistent with the ruling.** `Metric` has a unit field but no currency or scale. The module's own T1C.3 peer ratios come from `c.amount` with no source, which gives currency None and scale 1 (`cp1c.py:503-504`). The metric's currency and scale are therefore None and 1.
- **Reading B (T1C.5 issuer deviation and flag for conflicting are missing with `NOT_COMPARED`) is consistent with the ruling.** 6g says "the dependants read `Not compared: one side is not available`", and the two issuer T1C.5 cells depend on `T1C.3.issuer`. The B1 issuer wordings cover only missing and not_applicable. Status missing matches the T1C.4 and T1C.6 cells under the same reason. The check sits after the median-missing check (`cp1c.py:944-948`), so the 1C1 order holds, and it comes before the zero-median check. The `conflicting_issuer_cells_reworded` mutant is killed.

## 3. Mutants
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1c-r6-fix1/mutants_6g.py` **exits 0**: the baseline passes and all 17 mutants are killed.
- The 17 are my 11 that still apply, plus `unsettled_unit_verbatim`, `unsettled_currency_verbatim`, `unsettled_scale_verbatim`, `reject_conflicting`, `conflicting_issuer_cells_reworded` and `own_line_label_lowered_whole`.
- I first confirmed that the wrapper's `base/` copy is identical to the worktree for `src`, `tests`, `cases` and `pyproject.toml` (`diff -rq` exit 0). Each mutant runs from a fresh full copy.

## 4. My probe's last leg
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1c-r6-review/probe_b1_claim_precedence.py` still exits 0, but the last leg now passes for a different reason. It prints `conflicting raises: Figure reference names a gap: T1C.3.issuer.total_leverage_adjusted`.
- That ValueError comes from `compute`'s refusal path (`cp1c.py:1419-1420`), because the probe uses the frozen positive payload, which cites the issuer's leverage as a figure. It no longer comes from the `_cp1_facts` invariant.
- With the plain payload, the same conflicting fact gives no issues and composes the B1 path, which `test_6g_...` asserts. So that leg no longer tests "conflicting fails closed", and its old meaning is superseded by 6g.
- I could not find the implementer's written explanation in `work/build/stage1/cp1c/` or in `scratchpad/cp1c-r6-fix1/`. I confirmed the reading above independently and could not compare it with their wording.

## Low and Info
None new. The earlier I1 (digits in CP-1's limitation) is now ruled acceptable by 6g ("own lines sit outside the claim prose check").

Not verified: the full test suite, which was not run (the brief limits pytest to this file); whether the new own-line strings pass `prose.issues` and `bare_figures`, since I did not run `new_strings.py`; the implementer's written explanation of the probe leg, which I could not find; the Stage 2 rendering of a `conflicting` copied cell.
