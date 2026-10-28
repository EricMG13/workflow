# CP-2A round 9 scoped review (mx-feature; controller-saved)

**Verdict: APPROVE.** I found no findings.

**Checks**
1. All four T2B.9 cells (`gap`, `why_it_matters`, `affected_analysis`, `action`) go through `_spelled` (cp2a.py:1169-1184). The own line is `Gap (<severity>): <spelled gap>`. The new test asserts the exact spelled strings and that no `{` remains in any T2B.9 cell or limitation line. `id` and `severity` are unchanged, and the cells keep `analyst_judgment`.
2. The round-5 limitation paths are unchanged. The `None` handling moved to the call sites (scenario and assessment limitations in `_claims`), and `_spelled` now takes `str`. The mutants that revert those two call sites are killed by the existing round-5 test.
3. `cp1_references` still holds the referenced facts. The test asserts that the `total_debt_ltm` and `total_leverage_reported` fact ids are in the table.
4. No frozen value changed. The diff touches only `_gaps`, `_spelled` and call sites. The error text is reworded to `Stored text reference …` as the ruling says.
5. The tests fail without the change. The runner mutants reverting each field, the own line and `_spelled` itself (identity) are all killed.
6. There are no stubs, fake values or catch-alls. The `ValueError` is kept as an invariant, as the ruling says.

**Gate exit codes** (run from the target root)
- Runner `mutants.py`: exit 0. I had to pass an output directory as its argument. All 8 mutants were killed.
- pytest: 109 passed, 1 skipped. I read this from the summary line, because the pipe to `tail` hid pytest's own exit code.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `mypy --strict` on both files: "Success: no issues found in 2 source files". I did not capture its exit code, since `tail` was in the pipe.

Not verified: the `p_cp2a_gap_refs.py` check that no frozen gap text holds a reference (I took the ruling's word for it). Anything outside `tests/test_method_cp2a.py` (the full suite, other modules that consume CP-2A `Result`). The `mypy` exit code itself.
