Verdict: APPROVE

I reviewed commit 4c4892c (diff 12e9dcf..4c4892c) read-only. I found no High or Medium findings, and all gates and probes exit 0.

**Check 1, blank text**
- The 9 `*.limitation` fields are covered: 7 drivers, `downside` and `assessment`. `_limitation_issues` refuses `""` and whitespace-only text with `<path>: empty text`, and `None` passes.
- The tests run all 24 fields against `BLANK_CASES` and `blank_failure`, plus 24 twins that must not be refused.
- Placement does not move a frozen order. Each new issue sits directly after its field's rationale issue. The assessment limitation lands before the High issue. This is unpinned, and all 227 earlier tests pass unchanged.
- The schema-walk test checks that `BLANK_FIELDS` equals every plain `str` or `str | None` field with no pattern. I read the schema and the walk matches it:
  - `Downside.scenario`, `MinimumLiquidity.amount` and `BreakMetric.break_id` have patterns, so they are not analyst text.
  - The tuple handling reaches the gaps fields.
  - The test is exact set equality, so a new text field fails it.

**Check 2, Q12**
- The raise reads `CP-2G: CP-1D <label> must be USD MILLIONS at scale 1000000, not <currency> <unit> at scale <scale>`. That matches the ruling's frame exactly.
- It is a plain `raise ValueError` inside `_usd_millions`, called in `_supported` before the period check.
- Under `python -O` it still raises.
- `<label>` comes from `_t1d_label`, which is the running-text label (first letter lower-cased), so the text reads "CP-1D supported adjusted EBITDA". The ruling only says `<label>` and does not define it. This matches the module's other CP-1D frames.
- M2's text is unchanged. The `CP-1 {metric}` prefix moved into the caller, and the M2 test plus the "CP-1 prefix lost" mutant confirm it.
- The currency-None case is tested and reads `not None MILLIONS at scale 1000000`, which is consistent with M2's existing behaviour.
- Placing the raise before the period check is deliberate. A known fact for another period is still copied into T2H.2 as US$ m, so the book check must run first. A dedicated test pins this.

**Check 3, scope**
- No frozen case changed. The diff only adds tests.
- I found no stub, fake value or catch-all.

**Findings**
- Info: `validate_forward` does not read CP-1D, so Q12 fires only on compose, unlike M2, which fires in both. The report already says so. No action.
- Info: The Q12 path is unreachable from a real CP-1D head, which forces USD and MILLIONS. The tests reach it by `model_copy`. This matches the ruling's "unreachable".
- Info: The leverage facts in CP-1D get no book check. The ruling does not ask for one.

**Probes** (saved in `<S>/cp2g-class-review/`; the probes themselves are the implementer's, in `<S>/cp2g-class/`)
- `<S>/cp2g-class/p_mutants.py`, run on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`: exit 0. All 9 mutants were killed (pytest exit 1 for each).
- `<S>/cp2g-class/p_q12_optimised.py`, run with `python -O` from a full temporary copy: exit 0. It printed the raise text.
- Both reviewer reruns were launched from the cp2g-class paths. I wrote no new probe scripts, so `<S>/cp2g-class-review/` exists but is empty.
- The first optimised run failed with exit 1. It was a module-path error (`ModuleNotFoundError`) caused by my invocation, not a code defect. It passed once I set `PYTHONPATH=src:tests`.

**Gates** (all exit 0)
- pytest `tests/test_method_cp2g.py`: 379 passed, exit 0.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0, no issues.

Not verified: the full suite and other modules' tests; GitNexus impact; Stage 2 rendering or reading of the blank-limitation refusal; the ruling's `<label>` meaning beyond the running-text reading; the Q12 path against a real CP-1D head; mutation coverage beyond the 9 hand-picked mutants.
