# Phase 6 end batch, Part A report

Status: DONE (one finding predates and is routed, see item 2).

Files: `owners/pins.py`, `context.py`, `owners/cp2a.py`, `owners/cp2d.py`, `tests/test_pins.py`,
`tests/test_owner_cp2a_pins.py`, `tests/test_owner_cp2d_pins.py`, `tests/product/test_context.py`.

1. T4 L1 (-0 equals 0). `pins._same` reads `SNUM` (optional `-`) and compares by Decimal value.
   RED: 15 failures of `test_pins.py::test_negative_zero_equals_a_pin_of_zero` (`-0`, `-0.0`,
   `-0.00` for CP-2A, 2D, 2E, 3C, 3D; CP-4C cannot pin 0, its low is exclusive). GREEN after.
   Also added: look-alikes (`-`, `--0`, `+0`, `-0 `, Arabic-Indic digit) stay refused; `-5` never
   equals a pin of 5.
2. T4 L4 (bounded formatting). `cp2d._pin_lines` calls `pins_of` first and returns `()` when
   nothing is pinned; `_amount_text` formats plain only up to `_MAX_PLAIN_DIGITS` (100 000), else
   shows `str(amount)` (scientific, never a plain number, so never equal). RED:
   `test_nothing_is_formatted_when_nothing_is_pinned` peaked 20 MB against a 1 MB limit for
   `1E+10000000`. Bound edge tests (at and one over), and `1E-10000000`, `1E+999999999`.
   Note: `probe_huge_exponent.py` still exits 1 on its four no-context rows. The raise is in
   `compute` -> `display.format_value` ("Number is too large to display exactly" / `Overflow`),
   unrelated to the pin lines and identical on the parent (a6c, `out_huge_a6c.txt`). It predates;
   for the owner. The four pinned rows pass.
3. T4 L2/L3 (survivors). Adopted `survivor_kills.py` (label last on every frozen case incl. the two
   fixtures; CP-1 cross-check) and the `probe_spellings.py` table (as `VARIANTS`) as task tests.
   Mutant re-run against the new tests: M11, M13, M14, M25 all KILLED.
4. T4 I4. The comment before `liquidity_bridge`'s `pins_of` call now says a refused context is a
   `Context refused:` issue, so the validator returned it and the function raised above.
5. T3 L1. `no_context` / `no_pin` now compare with the frozen `cases/cp2a-owner/expected.json`
   positive case (limitations, claim ids and texts, fact ids/status/text, table ids and rows).
6. T3 adversary L1/L2. Adopted M04/M05 (label after NO_FIRST_BREAK), M14 (only ContextRefused is
   caught), M17/M18 (one clipped line) as tests. Mutants M04, M05, M14, M17, M18 all KILLED.
7. T3 L2. Same comment fix in `cp2a.downside_report`.
8. T1 L1. `_Rules.shocks` honours `req` (empty list is "required" only if `req`), `low_excl`,
   `high_excl`. RED: 3 of 6 rows of `test_shock_lists_honour_every_field_of_their_limits_row`.

Probe exit codes (worktree): `p6t1-review/shock_row_fields.py` 0 (run in the worktree);
`fix1_shock_row_fields.sh` as written 1, because it extracts the fixed old commit `ac0a66b7`, not
the worktree; `probe_spellings.py` 0; `probe_huge_horizon.py` 0; `probe_huge_pin_lines.py`
(1E+1000000, pinned) 0; `probe_huge_exponent.py` 1 (predates, above); `p6t4 survivor_kills.py` 0;
`p6t3 probe_survivors.py` 0.

Gates: ruff check and format 0; mypy on touched files: only `tests/test_connect_cp2d.py:515`
(untouched file, predates). Complexipy: no touched function over 13. pytest: test_pins,
test_owner_cp2a_pins, test_owner_cp2d_pins, test_connect/method cp2a and cp2d, product/test_context:
1117 passed. `tests/prompts/test_rules.py` (PYTHONPATH=tests): 3 failed, 230 passed: the sha test
(cp2d, pins and other lanes' files) and two coverage rows for other lanes' new functions
(`cp3d:_check_pin_label` market_implied, `cp2h:_context_lines` rating_triggers). No new issue
site from Part A.

Not verified: the slow `tests/test_owner_cp2a.py` / `test_owner_cp2d.py` promotion runs, the full
suite, and `RUN_PROMOTION`; a horizon of more than 4300 digits reaching `_pin_lines` directly
(unreachable through the journal, which refuses it as a shape error); a pin longer than 100 000
digits (now fail-closed as a mismatch); `mypy` on the whole tree.
