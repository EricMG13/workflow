Verdict: APPROVE. I found no High or Medium findings, and one Low.

Spec checks, read from the diff d2cb626..d688c6b:
- **`change`:** it is now `_EXACT.subtract(close, start)`, with `_EXACT = Context(prec=200, traps=[Inexact, Rounded, InvalidOperation])`, at cpl10.py:49, 338, 341 and 349. There is no rounding on this path.
- **Bounds:** the lease bounds are about 28 digits, far under 200. The traps cannot fire there.
- **`pct`:** `_q38(signed)` is unchanged.
- **Rating and rank:** these still use the Fraction `change`, so they are unchanged. The display path (`amount=s.change`, `decimals=2` for MILLIONS) is untouched.
- **Stubs and catch-alls:** none.
- **New tests:** the reviewer's pair is covered by `test_change_is_stored_exactly_not_rounded_to_38_digits`. The ±999999999999999999.9999999999 bound pair and the zero-base case are covered by `test_change_is_exact_at_the_bound_magnitudes_and_after_a_zero_base`. That test also covers a known base with a 76-digit value.

Gates, run in the temporary copy:
- pytest on `tests/test_method_cpl10.py` and `tests/test_defect_classes_selfcheck.py`: 365 passed.
- `ruff check`: exit 0.
- `ruff format --check`: clean.
- `mypy --strict` on both files: no issues.
- I took exit codes from the output tails, not from `$?` of each command directly.

Mutants, each applied alone:
- **Zero-base branch reverted to `_q38(change)`:** killed. `test_change_is_exact_at_the_bound_magnitudes_and_after_a_zero_base` fails at test_method_cpl10.py:193.
- **Known branch reverted to `_q38(change)`:** killed. Both new tests fail.
- The copy's source was restored afterwards.

`p13_cpl10_exact.py`:
- I ran it from `.../scratchpad/cpl10-r13/`.
- Its exit was masked by `| tail` and the script itself exited 0, so I can't confirm part A's exit 1.
- Part A printed "does not reproduce" in its `failures` list, which is the expected post-fix result.
- Part B passed: 60 frozen pairs checked, none moved.
- Part C passed: bound-magnitude pairs are exact.
- I did not re-run all 60 frozen pairs separately. They are covered by the 365 passing tests and by part B.

Findings:
- **Low:** `_EXACT.subtract` can now yield a signed zero or an exponent form. Before the change, `_q38(Fraction)` always gave a plain value.
  - `start=0, close=Decimal("-0")` gives `change=Decimal('-0')`.
  - `start=Decimal("1E+3"), close=0` gives `Decimal('-1000')`.
  - `start=Decimal("0.10"), close=Decimal("0.1")` gives `Decimal('0.00')`.
  - A `-0` would only matter if the render path prints the sign of a zero. I did not check whether CP-1 can emit `-0`, or how the render path shows it, so I can't say whether it is reachable.
  - Location: cpl10.py:338 and 341.
  - The edge-case probe is `cpl10-r13-review/edge.py` (saved in the scratchpad `cpl10-r13-review/` directory).

Not verified:
- Whether CP-1 can emit `Decimal("-0")`, and how the render path shows a signed zero.
- Exponent-form rendering of `change`.
- Part A's exit code of 1.
- The full test suite, the other lanes, and downstream consumers that read `change` (the `claim` and `facts` paths).