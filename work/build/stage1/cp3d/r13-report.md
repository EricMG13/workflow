CP-3D round 13: the item 8 comma and comma-space join is implemented and committed, but it is BLOCKED. One frozen refusal test goes red, and I did not work around it.

**Commit:** fcd7db2 on `claude/r13-cp3d` (cut at d2cb626, worktree clean at Step 0). It touches only `src/deploy_workflow/owners/cp3d.py` and `tests/test_method_cp3d.py`. Rule W from round 12 is kept.

**The block.** `tests/test_method_cp3d.py::test_refusal_mutation_yields_exactly_its_issue[amortisation_nonzero]` fails.
- The frozen mutation edit in `cases/cp3d-owner/submissions.json` uses the quote `Mandatory annual amortisation is 0; final maturity is December 31, 2029` with `value_text` `31`. Today it yields the zero-amortisation issue.
- With the comma-space join, `31, 2029` is one run, so `31` is no token. The issue becomes `amortisation: value_text 31 does not occur in the quote`.
- The ruling's frozen check only covered the 74 triples, not this refusal mutation. Its cost list names "a figure right after a year" but not a "Month D, YYYY" day number.
- I cannot edit `cases/` and I did not invent a date exception. LEAD needs to rule one of three ways: accept the changed frozen refusal text (a Stage 2 oracle change), exempt "Month D, YYYY", or re-pin the mutation.
- Gates are therefore not all exit 0, and `gates-first-pass=n`.

**Code** (found by name):
- `_tokens` has the lookbehinds `(?<![0-9],)(?<![0-9], )` after `(?<![0-9.])`. Its trailing guard is `(?![0-9]|[.,][0-9]|, [0-9])`.
- `_CUT_BEFORE` is `(?:[0-9.]|[0-9], ?|{_MINUS} ?)\Z`.
- `_CUT_AFTER` is `[0-9]|[.,][0-9]|, [0-9]`.

**Tests.** All are in `test_method_cp3d.py` under `# LEAD round 13 item 8`.
- `test_r13_item8_a_whole_quote_figure_in_a_comma_run_does_not_occur` has 10 cases. `1,25`, `1, 25`, `1,\n25`, `25,5`, `25, 5` and `25,\n5` are refused. Four twins are accepted: `25, a`, `25,a`, `up, 25` and `25 basis points, 5`.
- `test_r13_item8_a_page_comma_run_cuts_an_edge_figure` has 10 cases. On the page, start-edge `1,25`, `1, 25`, `1,\n25` and end-edge `25,5` and `25, 5` cut the figure. The twins `up, 25` and `25, a` are accepted.
- The riding Low is in the same test. `A-\n25 percent` and `2024-\n25 percent` are accepted, and `-\n25 percent` is refused.
- Red for the ruled cause: before the fix, the 11 comma cases failed and the 9 twin and guard cases passed.

**Mutants** (`<S>/cp3d-r13/mutants.py`, from temporary copies, exit 0). Nine mutants, all KILLED:
- `_tokens` lookbehind dropped, and its comma-space part alone;
- `_tokens` trailing guard reverted, and its comma-space part alone;
- `_CUT_BEFORE` comma arm dropped, and its comma-space part alone;
- `_CUT_AFTER` reverted to `\.[0-9]` (the comma-digit change undone), and its comma-space part alone;
- the `_MINUS` guard on `_CUT_BEFORE` dropped (the reviewer's surviving mutant 2).

**Probes** (copied to `<S>/cp3d-r13/`, LANE pointed at `r13-cp3d`):
- `p13_quote_classes.py` exited 1. Its failures are CP-3D rows (thousands, decimal comma, list, year comma, quote wrap before page minus) reading `lane False ref True`, plus one CP-1D row. The probe assumes the pre-change code (flags off), and this lane now refuses those rows by design. The CP-1D row is not mine.
- `p13_comma_space_join.py` exited 1 on `a frozen moved`.
  - Part (d) for CP-3D/2E shows `True -> False`, as intended.
  - Part (a) shows CP-3D's 15 frozen triples unmoved.
  - The failure comes from the CP-8 `_labelled` check (279 of 563 labelled checks move under the broad join). That is CP-8, not CP-3D, and the ruling keeps `_labelled` narrow.
- `p13_comma_wrap_limit.py` was copied but not run.
- Neither probe covers the refusal-mutation block above.

**Gates.** pytest on `tests/test_method_cp3d.py` and `tests/test_defect_classes_selfcheck.py`: 1035 passed, 1 failed (the block above). `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files all exit 0.

Not verified: the full suite and `test_host_h1`; CP-8, CP-2E and CP-1D readers; the `methods/cp3d.md` guard-limit note (the controller's Stage 2 note); GitNexus `impact` and `detect_changes` were not run; the Info about signed spaced `value_text`.

agent=mx-feature fix-rounds=0 gates-first-pass=n