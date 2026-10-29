# Release W2-C report (mx-feature)

## W2-C report (product items and Lows)

Branch `claude/s2r-c`, tip `c8b708b05e323d3f683dc386f9fd3aa54dd1f16f`, cut from fb231d4. The tree is clean. The diff is 23 files, +657/-134.

Setup: `EnterWorktree` was not available to me. I worked by absolute path from Bash in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-c` instead.

### Per item

- **`prose.is_blank`**: done (30a1f7a). It now counts Cc, the round 13 addendum 3 default-ignorable set (U+034F, U+115F, U+1160, U+17B4, U+17B5, U+180B-F, U+3164, U+FE00-F, U+FFA0, U+E0100-E01EF) and U+2800. The `owners/blank.py` re-export inherits it.
  - Tests in `tests/test_owner_blank.py`: 275 new tests (the 32 existing ones still pass) fail before the change.
  - I updated the old-definition oracle in `tests/test_engine_blank_text.py`.
- **`readiness.citation_issues` blank quote**: done (30a1f7a).
  - A quote that `is_blank` gives `Quote/locator mismatch: blank quote under <source> <locator>`.
  - It sits after the source and locator checks and before the page match.
  - A quote of invisible characters used to be accepted when the span held the same characters.
  - Whitespace-only quotes were already refused, with the old "quote not found" wording. I found no frozen blank-quote line in `src`, `tests` or `cases`.
  - Tests: `tests/test_citation_blank_quote.py`.
- **0d-c Lows**: all four done.
  - Reconciliation of the two lists:
    - Q1 is the R1 exact summary count.
    - F1 is R8-R11/c05/c08, the real worst-case record bound.
    - F3 is the tools.py:33-35 claim.
    - Q4 is the `clipped` docstring (limit >= 1).
    - Q2 and Q3 were Info items with no action. F2, F4 and F5 are not on either list.
  - Q1: `tests/test_rule_issue_bounds.py` now asserts the exact summary line per shape, through a `MATCHES` table. A mutant that wrote `rest(total)` instead of `rest(total - 19)` is now killed.
  - F1: I added `test_the_real_worst_case_record_bound_holds_for_escaped_characters`. It asserts 64 KiB < size <= `WORST_CASE`, which is 2x20x600x6 B plus 16 KiB. It builds its payload with `json.dumps`. The ASCII-only `LIMIT` is now commented.
  - F3: the `live/tools.py` docstring says issue text and memory are bounded, and the walk is O(nodes x depth) in time.
  - Q4: the `execution.clipped` docstring states `limit >= 1` and the `limit=0` difference. These are comment-only changes.
- **CP-DR `question_id`**: done (30a1f7a).
  - New `QUESTION_ID_MAX` is 145. It is derived from the longest `TDR.2.<id>.<field>` against the 160-character Identifier cap.
  - Ids of 146-160 characters are refused in `_question_issues`, with `question_id is too long to compose its fact ids (at most 145 characters): <id>`.
  - Tests: 145 composes, 146 makes `Fact` raise (so the bound is tight), and the validator refuses both 146 and 160.
  - Probe `rr2_cpdr_long_question_id.py` exits 0.
- **CP-DR and CP-3D RunText unconditional**: done.
  - CP-DR no longer skips the check when there are content issues. CP-3D `validate_market_implied` now returns the content issues and the summary RunText issues together.
  - Probe `rr4_cpdr_masked_runtext.py` now prints both issues.
  - The oracle refusals did not move (`test_method_cp3d/cpdr` and `test_connect_cp3d/cpdr` pass).
- **CP-3D `_validate_step`**: done.
  - New `_parsed` reads the payload through `json_object`/`exact_json`. It is the same as CP-2D/CP-1D, including the `(root): not a bounded JSON object` wording.
  - Test: a monkeypatched `json_object` returning None is refused.
  - **`_whole_on_page` docstring**: already at fb231d4 (cp3d.py:289-304 names `_EDGE_BEFORE` and the comma).
- **lows.md**:
  - **G1-X scope guard**: done.
    - New case "scope row without sources" in `tests/test_owner_g1x.py`. The old case of that name was really the other direction, so I relabelled it.
    - The `==` -> `<=` mutant at owner_workflow.py:939 is now killed.
    - The docstring lines 887-890 are reflowed to 100 characters or less. Other long lines in that file (12, 211, 259, 1412, 2393) were not named, so I left them.
  - **CP-DR L2b and L2f**: done. Tests are `test_reader_refuses_a_negative_count` and `test_reader_refuses_a_per_gap_share_that_is_not_known`. Both pass against the existing reader.
  - **CP-2E docstring**: done. `tests/test_owner_cp2e.py` lines 3-6 now name the four written tests.
  - **`drive_cp1` duplication**: done.
    - `s1a_runs.drive_cp1` gains the keyword options `business_search`, `narrative_tool_check`, `readiness` and `quality`. The defaults are unchanged.
    - `cp3c_runs.drive_cp1` and `cp4_runs.drive_cp1` now call it, which removes the copies. I touched only the `drive_cp1` code in those two files.
    - A throwaway equivalence script (`<S>/c_equiv.py`) compared the call traces of the old and new drivers against fb231d4 for cp3c, cp4 positive/gap and s1a positive/gap. All five are EQUAL. The slow real-store runs were not executed.
- **Backlog**:
  - **CP-2E `w-minus` test strength**: already at fb231d4. `tests/test_method_cp2e.py:1347-1348` uses the wrapped quote, and disabling the exemption kills it.
  - **Shared defect test L2**: done.
    - `defect_classes.py` gains `absent_free_text_paths`, `with_absent_text` and `model_text_failures(fill_absent=False)`. The default is off.
    - Six self-check tests; a validator that skips a null field is caught only with the fill on.
    - Wired into the CP-0 and CP-1 `source_context` tests (`fill_absent=True`). That surfaced three paths that accept hostile text:
      - `consumers.*.missing_source`
      - `sources.*.scopes.*.limitations.*`
      - `sources.*.limitations.*` (new in the CP-1 test only; the CP-0 test already listed it as verbatim)
    - `missing_source` is read nowhere except the prohibited-text check, and the scope limitations are `canonical_gaps` labels. I added them as sink-documented verbatim entries, not as fixes. Please confirm that reading.
    - Fields behind a list of objects the positive leaves empty (CP-0 `gaps.*.citations.*.quote`, CP-1 `events.*...`) are not reachable by this fill. This is documented in the helper.
- **Not done, outside my brief or lane**: the Info in `test_defect_classes_selfcheck.py` (the verbatim-pattern test repeating an earlier one), CP-8 L-a/L-b, CP-1D L1-L6, and the CP-2G `next(...)` default (CP-2G src). CP-2D and CP-1D `_validate_step` already use `json_object` at the tip.

### Oracle values that moved
None. The 41 + 3 refusals are unchanged.

### Pinned, builder-hashed or reused files changed (for W3)
- **Reused files**, each with a D12 record in `docs/reuse/manifest.json` (project_commit 30a1f7a, prior sha = fb231d4 sha; I checked the current sha matches each record):
  - `src/deploy_vii/prose.py`
  - `src/deploy_vii/readiness.py`
  - `src/deploy_vii/execution.py` (docstring only)
  - `src/deploy_vii/live/tools.py` (docstring only)
- **Pinned**: `src/deploy_vii/readiness.py` is pinned at `cases/legal/manifest.json:290`. The old sha is `119058ff8a238f29…` and the new one is `01616654…`. W3 or the legal lane must re-pin it. I did not touch `cases/`. `cases/pins.py --check` still passes, because that pin is not in `PINS.json`.
- No other changed file's old sha appears in `cases/`, `docs/` or the leases. `cp3d.py`, `cpdr.py` and `owner_workflow.py` are new-project files with no hash pins.

### Gates
- **Targeted tests**: all `test_method_*` and `test_connect_*`, plus `test_owner_g1x`, `test_owner_blank`, `test_defect_classes_*`, `test_engine_blank_text`, `test_rule_issue_bounds`, `test_citation_blank_quote`, `test_readiness_linear`, `test_stage2_classes*` and `test_legal_render`: 9311 passed, 3 skipped, 1 failed.
  - The one failure was my own F1 test, whose payload had a raw control character. I fixed it and `test_rule_issue_bounds.py` now passes (25 passed). I did not re-run the whole batch afterwards.
  - `test_financial_workflow.py` and `test_readiness_linear.py` passed in the earlier background run (73 passed). `test_defect_classes_cp1.py` and the CP-0 test passed after the fill was wired in.
- **ruff format --check**: exit 0 on the 22 touched `.py` files.
- **ruff check**: exit 1, but only for `prose.py:114` and `:127` ISC004. Those two lines are unchanged from fb231d4 (a pre-existing finding outside the brief's known list). My own findings are fixed.
- **mypy --strict** on the 7 touched `src` files: exit 0.
- **`cases/pins.py --check`**: exit 0 (69 paths).
- **Suppressions**: noqa is 13 and type-ignore is 5, so both are within their limits.
- **Size**: the diff is 791 changed lines, under 800. `uv.lock` is untouched.
- **Mutants** (`<S>/c_mut.py`): 8 of 8 killed. They were count-off, blank check off, no Cc, no U+2800, qid max+1, CP-DR RunText conditional, CP-3D RunText conditional, and CP-3D raw parse.
- **Probes**: `rr2_cpdr_long_question_id.py` exits 0 and `rr4_cpdr_masked_runtext.py` exits 0.

Not verified: the slow store-run tests (`test_owner_*` runs, S1a/CP-3C/CP-4 real `drive_cp1` in a real workflow, which are deferred to Stage 5); the full suite and CI; the docstring-only changes (execution, tools, G1-X docstring, CP-2E docstring), for which no test applies; whether `missing_source` and the scope limitations really have no downstream sink beyond the ones I read; the three `methods/*.md` files that still say "whitespace and Cf only" (cp1d.md, cp2e.md and cp1c.md, owned by other lanes); pin consistency with the other lanes' re-pins (W3).

agent=mx-feature fix-rounds=0 gates-first-pass=n
