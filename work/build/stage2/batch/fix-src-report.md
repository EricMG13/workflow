# Fix batch, fixer 1: src (mx-feature)

All five source-defect items are fixed in one commit, `545e28a`, on `claude/s2-fix-src`. Step 0 held: the tree was clean and HEAD was a1a0574. The Edit tool was not needed for src; I edited with Python from Bash and used `sed` only for inspection.

**Items (test first, then fix)**
1. **Class test (Medium).** I removed both strict xfails in `tests/test_stage2_classes.py`; `FINDINGS` is now `{}`.
   - Red: with the xfails gone and no fix, the CP-DR and CP-3D cases failed with pydantic `ValidationError` from `Claim.text`.
   - Fix: `cpdr.validate_research` now checks each answer as `RunText` through a module-level `TypeAdapter`. `cp3d.validate_market_implied` does the same for `summary.text`. Both emit `<path>: <msg>`, clipped, with no input echoed, and only after the content rules pass.
   - Green: both cases pass.
2. **CP-2G reader (Low).** I added `test_reader_refuses_a_settled_head_without_the_break_table` in `tests/test_connect_cp2g.py`.
   - Red: it failed with `StopIteration`.
   - Fix: `next(..., None)` plus a `ValueError("CP-2G: the settled head has no table T2H.7")`. The test now passes.
3. **CP-2D and CP-1D `_validate_step` (Low).** Both now go through a new `_parsed`, copied from the cp4c pattern. It uses `json_object` and parses `exact_json(document)`. Text `json_object` refuses is refused with the pydantic shape issue for the same text, or `(root): not a bounded JSON object`.
   - Test: `test_validate_step_reads_the_payload_only_through_json_object` in `tests/test_connect_cp2d.py` and `tests/test_connect_cp1d.py`.
   - Red: both failed with AttributeError on the `json_object` monkeypatch target. I reverted the two src files to confirm this, then restored them.
   - Green: both pass.
   - The frozen shape-refusal tests in the method and connect suites still pass.
4. **CP-1D L1 (Low).** `_ordinal_after` now takes the first 32 non-Cf/Mn/Me characters of the whole tail, using `itertools.islice` over a filter. I added rows to the `test_one_whole_run_is_the_single_rule` parametrisation in `tests/test_method_cp1d.py`: 31 and 40 combining marks before `nd`, 40 ZWSP before `th`, and 40 marks before `nds` (still readable).
   - Red: the 31-mark and 40-mark rows failed before the fix.
   - Green: all four new rows pass.
5. **CP-1D L6 (Low).** `cp1_facts_note` now says CP-1 references bind in the overall rationale only, and that assessment rationales reference module figures only. I added `test_cp1_facts_note_says_where_cp1_references_bind` in `tests/test_connect_cp1d.py`, which failed before the change and passes now. The core is untouched.

**Probes**
Copies are under `<S>/s2-fix-src/`, with the root passed as an argument. The scratchpad `_h.py` default was hard-coded to the s2-cp1d worktree, so I copied the `cp1d-batch-probes/_h.py` variant that takes a root argument. Copied: `p4_ordinal_identifier_edges.py`, `p9_cp1_ref_in_assessment.py`, `p5_fp02_render_vs_oracle.py`, `_h.py`, `verify_findings_owner.py`.

| Probe | Exit |
| --- | --- |
| `p4_ordinal_identifier_edges.py` (`fail-open: 0`) | 0 |
| `p9_cp1_ref_in_assessment.py` | 0 |
| `p5_fp02_render_vs_oracle.py` (`bad: 0`) | 0 |
| `verify_findings_owner.py` (run from the worktree with `PYTHONPATH=src:tests`) | n/a |

`verify_findings_owner.py` is a print script, so I read its output instead of an exit code. Both hostile values return an invalid step with a `<path>: Value error, Malformed run text...` issue. The follow-up is then `valid`, so the run is no longer wedged.

p9 refuses at the validator, so it exits 0 by design. I could not find a "frozen compare p5 ... moved 0" script. I used `p5_fp02_render_vs_oracle.py` from `cp1d-batch-probes` as the p5 check; it shows `bad: 0`.

**Gates (exit codes)**
- pytest on the full gate list (`test_stage2_classes`, `test_stage2_classes_batch`, `test_connect_*` and `test_method_*` for cpdr, cp3d, cp2g, cp2d, cp1d, plus `test_owner_g1x` and `test_host_h1`): 0, with 2965 passed and 1 skipped. The skip is the existing store/promotion test at `tests/test_method_cp1d.py:1528`.
- `ruff check`: 0.
- `ruff format --check`: 0, after I formatted one test file.
- `mypy --strict` on the 10 changed files: 0.
- `python3 -I cases/pins.py --check`: 0.
- No new `noqa` or `type: ignore`.

**Not verified:** the rest of the full suite, the slow render and end-to-end gates, and the other fixers' files. Also unexercised:
- The CP-3D `_validate_step` still parses with raw `model_validate_json`; it was not in my items.
- The cp1d/cp2d `json_object` tests use a stub store, so the full live submit path through those validators runs only in the existing connect tests.

`agent=mx-feature fix-rounds=1 gates-first-pass=n` (the first format check failed on one test file).
