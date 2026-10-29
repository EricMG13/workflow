CP-4C round 13 is done and committed as 805315e on claude/r13-cp4c. The gates pass, but the mutants and probes are not all clean, and three LEAD probe expectations assume the old code.

Step 0 held: the worktree was clean at 7d536cf. I merged claude/round12 (d193096) as asked. The commit is one commit and carries the co-author line.

**Files:** `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py` only.

**HEAD pin test:** the module's tests were green at HEAD (1374 passed), so the b10 lease-pin test is not red here.

**Item 2 (R1 M2)**
- `Cp2gEbitda.derives_from` is removed. `Cp2gHead` gains `down_ebitda_source` and `down_interest_source`, both Facts for `T2H.3.d01.source` and `T2H.3.d02.source`.
- The test helper `_cp2g` is what returns the two source texts. There is no `cp2g_reader` in `src`.
- `_scenario_row(cp2g)` fullmatches the two texts against the ruled patterns and requires the same row. Otherwise it raises exactly `CP-4C: CP-2G T2H.3.d01 and T2H.3.d02 sources name no single CP-2A T2B.1 row`.
- I dropped the unused `run_values` parameter. The compute call site and the validator call site are both kept.
- The frozen-case tests are unchanged and all 5 buildable cases compose as today.
- New tests cover:
  - row s03 and a changed row s02;
  - 17 invalid pairs: mismatched rows, a text that does not fullmatch, one or both sources missing (status `missing`, no text);
  - the compute site and the validator site raising the same invariant.
- I replaced the old "another CP-2A scenario" lineage test, because that check is gone by ruling.

**Item 5 (`base_period`)**
- `Cp2aHead.base_period` is now a method, `base_period(row)`. It reads the row's `ebitda_decline` and `interest_increase` periods and raises `CP-4C: CP-2A T2B.1 facts differ in period` if they differ. The T4E.1 row calls it with `run.scenario_row`.
- Tests: in every buildable case it equals the old `base_period` key. Differing periods raise at the method and at compute. A differing period on another row is not read.

**Riding Low**
- A new test pins that `{`, `}`, `[` and `]` are accepted in every plain field. A second test pins a bracketed assessment limitation composing into the claims.
- The reviewer's "B7 also on plain fields" mutant is killed.

**Task 4: blank quotes**
- Every Quote in the payload is covered: `claims[i].support[j].quote` and `claims[i].amount_quote.quote`.
- A blank quote now gets `<path>: empty text` before the page-occurrence check, and it is the only issue for that quote. Because it is an `elif`, a blank support quote with an out-of-scope `source_id` gets only the blank issue.
- Tests, written first, were red: 28 failures on HEAD. They run every `BLANK_CASES` value through `blank_failure` on each path, check `""` is refused by the validator and not raised in compute, include a non-blank twin, and check the three paths are every quote the positive payload holds.
- The reviewer's `p_blank_support_quote.py` exits 0.

**Gates**
- pytest on the two test files: 1501 passed.
- `ruff check` and `ruff format --check` are clean on both files (the format run reformatted, no check failures).
- `MYPYPATH=src mypy --strict` reports no issues on both files.

**Mutants and probes** (scripts and outputs are in `<S>/cp4c-r13/`)
- `<S>/cp4c-r12/mutants.py`: exit 0, all 9 killed.
- `<S>/cp4c-r13/mutants13.py` has 12 mutants: one per ruled clause (the two fullmatches, same row, each source checked, the field names, `base_period` reading only one fact or taking the first period, the support and amount blank checks). Its exit is 1, and 11 are killed. The one survivor, "d01 row accepts `s[0-9]+`", is equivalent: the d02 pattern still requires `s[0-9]{2}` and the two rows must agree.
- `<S>/cp4c-r12-review/p_mutants_extra.py` exits 1. "B7 also on plain fields" is killed. "blank not exclusive" survives; the reviewer already called it equivalent.
- `probe_alloc_reference.py` at n=200 exits 0 with 0 mismatches.
- `p13_l2_sources.py` exits 0.
- `p13_cp4c_source_row.py` exits 1, because parts B and C assume the old code.
  - Part A (oracle only) holds: in all 7 CP-2G cases with a downside, the source row equals the lineage row. This part does not call CP-4C code.
  - Part B calls `replace(e, derives_from=())`, which no longer exists.
  - Part C patches `_scenario_row` with a two-argument lambda, which no longer matches the one-argument function.
  - The frozen-case tests replace parts B and C.
- `p_blank_support_quote.py` assumes the pre-change code (it expected exit 1) and now exits 0 as intended.

**Not verified:**
- No full-suite or other-module run.
- No GitNexus `detect_changes` run.
- Stage 2 lease and manifest text (CP-4C :56 and :73, CP-2G :75 and :152) is not touched.
- A CP-2A head with a gap period on the row's two facts raises the same period invariant. No frozen case exercises that.
- A blank `amount_quote` on a non-`source_row` class gets only the existing "only a source_row class cites an amount row" issue, not the blank issue.

ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n