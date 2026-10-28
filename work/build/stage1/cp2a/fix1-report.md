# CP-2A fix round 1 report (controller-saved from the implementer's hand-back)

CP-2A fix round 1 is committed as **88526a1** on `worktree-agent-a34fec3e9469279cd`, on top of 7ba456e. Tests: 108 passed, 1 skipped (v17). The one code change is L3; M1, L1 and L2 add tests only. 12 of the reviewer's 13 mutants are killed now; the 13th, `quarter_line_rows_only`, survives and I think it is an equivalent mutant (reason below).

**Findings and their tests:**
- **M1** (`test_p1w_gate_precedes_the_short_circuits_and_the_zero_check`), on a quarter `BaseOperands` whose four CP-1 ratios are known:
  - **Breaks:** with interest -1, and separately with total debt 0, b02, b03, b04 and b05 all read "Not meaningful on a single-quarter base" with the P1-W reason. Without the gate they would get `INTEREST_NOT_POSITIVE`, the total-debt short-circuit or the net-debt short-circuit.
  - **Stressed ratios:** with a 100% decline (E' = 0), and separately with interest -1 and debt 0, all four ratios are `not_applicable` with the P1-W reason rather than the zero-denominator texts.
  - It kills `break_gate_after_short_circuit` and `stress_gate_after_zero`.
- **L1** (`test_p1w_own_line_from_rows_alone`): the fixture's facts with cash interest missing and no watch level.
  - b02 is the operand's Not calculable, so no break shows P1-W, while s00 shows it for total leverage, net leverage and FCF/debt. The own line still appears exactly once.
  - It kills `quarter_line_points_only`.
  - I agree `quarter_line_rows_only` is equivalent: a P1-W break needs its ratio gated with every operand present, and the s00 control row runs the same checks in the same order on the same ratio, so that row is P1-W too.
- **L2** (`test_round5_names_line_separators_and_padded_reserved_label`): U+2028 and U+2029 in a name are refused, and " Base (no stress) " is reserved. It kills `control_cc_only` and `reserved_unstripped`.
- **L3** (`test_blank_threshold_labels_are_not_reported_as_duplicates`): before the fix it failed with the extra `thresholds:   appears more than once`. The fix guards the duplicate-label check with `label.strip()`, as the scenario-name check already does; two blank labels now give only their two `empty text` issues.

**Mutants and probes:**

| Run | Exit | Result |
|---|---|---|
| Reviewer `cp2a-r6-review/mutants.py` | 1 | 12 of 13 killed; the only survivor is `quarter_line_rows_only` (equivalent, see L1) |
| My `cp2a-r6/mutants.py` | 0 | 9 of 9 killed |
| `probe_p1w_order.py` | 0 | |
| `probe_names_edges.py` | 0 | Now prints only the two `empty text` issues for the blank labels |

In my mutant script I re-targeted `labels_duplicate_off` to the new guard line and added `labels_duplicate_blank` (it drops the guard), which is the ninth.

**Gates:**
- pytest on `tests/test_method_cp2a.py`: 0
- `ruff check`: 0
- `ruff format --check`: 0, after one reformat of a new test line
- `MYPYPATH=src mypy --strict` on both files: 0

Choice 5 (raw references in gap texts) stays with LEAD, untouched.

Not verified: rendering and G2 paths (the `∅ G# n.m.` chip, and how a spelled limitation shows in the report); real promoted CP-1 head facts (the fact ids are test-only stand-ins); FY base periods; a Cf character in a name; whether `quarter_line_rows_only` is equivalent (I reasoned it, no test can tell them apart); any suite other than `tests/test_method_cp2a.py`.

Ledger: 2026-10-28, cp2a-r5-6-fix1, `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_method_cp2a.py`, exit 0, 108 pass / 1 skip, agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
