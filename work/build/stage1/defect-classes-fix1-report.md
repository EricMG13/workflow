## Library fix round 1: report

All three review findings are fixed in commit `33edfcc` on `claude/defect-classes`, on top of c032752. The lane was not merged. I changed only `tests/defect_classes.py` and `tests/test_defect_classes_selfcheck.py`, in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/defect-classes`.

**Reviewer probe `twin_and_blank.py`: exit 1, as expected.** Exit 0 is not possible after this fix.
- Before the fix it printed two problems: the wrong "refused +25" passed the twin check, and blank case `blank-0 ''` failed for a reader whose schema refuses `""`.
- After the fix the blank part prints `[]`.
- Its part (a) still prints True. That part shows the twin check cannot prove an outcome, which you accepted as a limit; it is now stated in both docstrings (Low 2 below).

**Medium (blank `""`), test first.** I wrote five tests first and watched them fail for the expected reasons (missing attribute, `ValidationError` propagating, frame forced for `""`). Then I changed the library:
- `BlankCase` has a new field `whitespace_only`, set to `value != ""`.
- `blank_failure` now requires the frame only for whitespace-only text.
  - For `""`, any non-empty issue list passes, or a pydantic `ValidationError` whose errors are all `string_too_short`.
  - Any other `ValidationError` still propagates, so this is not a catch-all.
  - An empty issue list for `""` fails with "expected a refusal".
- The library now imports `pydantic.ValidationError`. pydantic is already a pinned dependency, and no owner is imported.
- `test_blank_cases_are_whitespace_only` is now `test_blank_cases_split_empty_from_whitespace_only`.
- New tests:
  - `""` passes with a raised schema refusal, an issue-reported refusal, or the frame;
  - `""` with no refusal still fails;
  - a schema-style refusal of whitespace still fails.
- The module docstring records your decision.

**Low 1 (twin wording).** The docstring no longer says every twin has the same value. It now says the twin keeps the value, except `wrap-split`, whose twin holds the joined spelling. The reviewer also listed `sign-label`, but its twin `label-genuine` does have the same value, so the docstring does not make an exception for it.

**Low 2 (edge twins and what the twin check proves).**
- Each edge cut now twins with the nearest accepted edge case:
  - `edge-prefix`, `edge-minus` and `edge-close-paren` twin with `edge-start-<f>`;
  - `edge-open-paren` and `edge-end-digit` twin with `edge-end-<f>`;
  - `edge-10` twins with a new `edge-start-0`, `edge-minus-0.25` with a new `edge-start-0.25`, and `edge-end-decimal` with `edge-end-25`.
- The twin check is restated as the property it proves: page, quote and value are not all equal under `quotes.quoted`. The twin also keeps the value, except for B3.
- Both docstrings say it does not prove the expected outcome.
- A new test checks that each edge twin is the start or end case that matches the cut. For `edge-prefix-25`, `edge-minus-1.25`, `edge-10` and `edge-minus-0.25`, it checks the twin has the identical quote, so only the page differs.

**Gates (all exit 0):**
- `PYTHONPATH=src … pytest -q -p no:cacheprovider tests/test_defect_classes_selfcheck.py`: 152 passed.
- `ruff check`: clean.
- `ruff format --check`: clean.
- `MYPYPATH=src mypy --strict` on both files: clean.

**Also run:**
- **Reference reader:** the reviewer's `ref_reader.py` exits 0 with 0 mismatches, including the two new edge cases.
- **Inventory:** re-run; exit 1 by design, because owners still fail the round 11 classes.
  - Blank-text fail counts fell only by the `""` cases that now pass, for example CP-1D 34/40, CP-2D 24/30, CP-DR 12/15 and CP-L10 12/35.
  - Every whitespace-only failure is unchanged.
  - Edge-cut totals grew by the two new accepted cases, which pass.

Not verified: no owner's own test file runs the library yet. The `""` path that takes a schema refusal is tested only with a hand-built `ValidationError` and the inventory adapters, not with each owner's `Text` model in a module test. The twin check still proves only that a refused case is not a spelling variant of its twin; the expected outcomes rest on the rulings and the reviewer's reference reader. The probe-side adapters were not re-reviewed.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n (ruff check flagged one import-order issue, fixed with `ruff check --fix`; tests, format and mypy passed on the first run)
