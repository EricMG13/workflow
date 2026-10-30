# B2 validators report

Branch `claude/oi-b2-validators`, base 559ba54. Under ruling OI-12 the implementer ran no project Python; the controller ran every RED and gate command.

## Commits
- c2d643e RED tests for CP-3D summary reference, CP-2E empty summary, CP-2A `json_object`.
- f589c14 fixes for those three, plus the CP-DR `validate_research` order docstring (no behaviour change, no test applies).
- 008ea3f RED for the CP-3D empty summary (OI-18); ZWSP escape in the CP-2E test (ruff finding).
- a55a897 CP-3D fix: blank summary text skips the RunText and reference checks.

## Changes
1. CP-3D: a reference in `summary.text` is refused at validation (`summary.text: text carries a reference`), after the RunText check passes; the message never echoes input.
2. CP-DR: docstring names the `question_id appears twice` issue and the closing unconditional `_model_text_issues`.
3. CP-2E: `chk.run_text` does not run on text `chk.prose` refused as blank. Before: `""` gave `summary.text: empty text` plus RunText "at least 1 character". After: exactly `summary.text: empty text`. `" "` and ZWSP gave one issue before and after.
4. CP-2A: `_parsed` (same shape as `cp1d._parsed`) reads the payload only through `json_object`/`exact_json`.

## RED at c2d643e
`pytest -q` on the three connect files: 39 failed, 441 passed, exit 1.
- cp3d: both reference params and the prohibited-conclusion pairing failed (no reference issue).
- cp2e: only `[empty]` failed; `[space]` and `[zwsp]` already gave one issue.
- cp2a: the `json_object` test, the `exact_json` test and 33 frozen-payload parity params failed (missing attributes).
RED at 008ea3f (`-k empty_or_blank`): 1 failed, 2 passed; only CP-3D `[empty]` failed (two issues).

## Gates
- At f589c14: pytest 8 files 2344 passed, exit 0; ruff check exit 1 (literal ZWSP in `tests/test_connect_cp2e.py:678`); ruff format exit 0; mypy exit 0; noqa 13, type: ignore 5.
- At a55a897, all exit 0: pytest 8 files 2347 passed; ruff check clean; ruff format 7 files formatted; mypy no issues; noqa 13, type: ignore 5 (limits 13 and 5).

## Parity
Frozen CP-3D summaries carry no reference; every CP-2E refusal and valid case is unchanged; every frozen CP-2A payload gives the same schema result via `_parsed`. All guards passed. No file under `cases/` changed.

## Sibling double-issue
- CP-3D summary `""`: yes, double issue (`analyst_text` plus RunText length); fixed under OI-18.
- CP-DR answers: no. `_model_text_issues` skips an empty answer; a blank non-empty answer gets only the blank-text frame.

## Deferred genuine runs
`tests/test_owner_cp3d.py`, `tests/test_owner_cp2e.py`, `tests/test_owner_cp2a.py` (not run).

Not verified: the deferred owner suites above, G2 genuine cases and `*_runs.py` drivers; the `cpdr.py` docstring has no test; no mutation testing, jscpd or complexipy ran; whole-repo suite not run.

agent=mx-feature fix-rounds=0 gates-first-pass=n
