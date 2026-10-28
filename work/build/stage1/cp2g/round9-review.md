**Verdict: APPROVE.** No High, Medium or Low findings.

**Findings**
- Info, `src/deploy_workflow/owners/cp2g.py:1129-1131, 2481, 2486, 2489`: the three composer wraps and `_a25` have no individual test.
  - `p_wraps.py` makes `_apply` raise `decimal.Inexact` while each of `_t2h2`, `_t2h6`, `_t2h8` and `_a25` runs.
  - Each gives the exact `ValueError("CP-2G: <operation> needs more than 38 significant digits")`: the historical-to-base bridge, the credit metrics, the deleveraging path, the FY2025 cash flow. All four are correct.
  - Probe: `<S>/cp2g-r9-review/p_wraps.py`, run as `python p_wraps.py <target root>`, exit 0.
  - I needed the probe to apply `_plain` to the payload, as the test file does.

**Checks**
1. M2 message: `cp2g.py:326-329` matches byte for byte. `{currency}` is the Fact value, so None prints as `None`. The mutant for the old wording is killed.
2. Info rule:
   - Only `decimal.Inexact` is caught, in `_exact_digits` (:236-243), and it is re-raised with `from error`. No wider catch exists.
   - `_EXACT` is used only inside `_apply` (:231). Every `_apply` caller sits inside a wrap: `forecast` (via `_year`), `_a25`, `_t2h2`, `_t2h6` and `_t2h8`. `_t2h3`, `_t2h4` and `_t2h5` have no `_apply` call.
   - `_ratio` uses its own `_RATIO` context, not the trap, so it needs no wrap.
   - No `_EXACT` block is left unwrapped.
3. L2 and L3:
   - L2 matches the ruling text. It is taken only when the supported fact is known and its period is not `LTM_PERIOD`. Otherwise `ref()` supplies the chip or the old wording.
   - L3 sits after the all-"Not reached" branch and before the mixed branch. It reads "In the {lab} case no tested break point is calculable through FY2028: [T2H.7.{tests[0].row}.{case}_first]." Here `lab` is base or downside, and the chip uses the case key (`down_first`), which is the real fact id.
   - L1 has no code change; five tests pin it.
4. `u_cp1d.basis`: `:1218-1224` takes the period of the first known fact in `run.cp1d` order (supported, total, net). It falls back to T2H.1's existing "Not applicable". The parametrised tests cover supported, total and net, and the mutant that takes the last fact is killed.
5. T2H.9 and the `Gap (` line:
   - `_spelled` (:2066-2080) uses `prose.tokenize` and `business_context.spelled`. It covers `gap`, `why_it_matters`, `affected_analysis`, `action` and the own line.
   - A reference that does not name a known upstream figure raises `ValueError`, an invariant. That is not a catch-all.
   - Frozen cells are unchanged: the oracle-equality tests in the 233-test file pass, and text without references passes through `_spelled` unchanged.
6. `p_r9_mutants.py`, run on a full `git archive` copy of 947a57d with `PYTHONDONTWRITEBYTECODE=1`: N01-N13 all killed, survivors `[]`. That covers M2, both L1 reverts, L2, L3, Info (not caught, names swapped), the three basis variants and the three gap-text variants.

**Stubs and catch-alls:** none found.

**Probe exit codes**
- `<S>/cp2g-r9-review/p_wraps.py`: exit 0.
- `<S>/cp2g-r9/p_r9_mutants.py`: exit 0 (the script's own exit code). I ran it on the copy at `<S>/cp2g-r9-review/copy`.

**Gates** (target root, with the `.venv` binaries, mypy cache in `<S>/cp2g-r9-review/mypycache`)
- `pytest -q tests/test_method_cp2g.py`: 233 passed.
- `ruff check` on both files: exit 0, "All checks passed!".
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0, no issues.

Not verified: the other Stage 1 test files and the whole-branch suite were not run. `report_view` rendering of the spelled gap texts was not exercised. Real `decimal.Inexact` from a composer other than the forecast was not produced from data; `p_wraps.py` forces the exception instead. Stage 2 readers were not checked. I did not read the implementer's round-9 report (`round9-report.md`) and did not check its line references.
