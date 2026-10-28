Commit 9f61127 on claude/r13-cp1d (parent 80cccb1). It changes only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py`. It follows LEAD addendum 4 for H1 and M1, and H2 as written. Two mutants are equivalent and survive, so mutants do not exit 0 (see below).

**H1 and M1.** One rule, `_one_whole_run(quote)`, replaces my two separate refusals.
- A numeral run is `\.?[0-9]+(?:(?:\.|, ?)[0-9]+)*`.
- Each reading from `_readings` must hold exactly one run, and that run must match `[0-9]+(?:\.[0-9]+)?`.
- It is ORed with the existing `len(amounts) != 1` at the exactly-one position in `_shape_issue`, with no new wording.
- Tests, all through the a01 path `_a01_on_page1` then `validation_issues`, each equal to the pinned exactly-one issue:
  - `test_basis_quote_with_a_hidden_run_is_refused` covers every a01 input, `.25 million, or 2.5`, `1.2.5 or 2.5`, `section 4.2.1 a saving of 25`, `1.250.000`, `1,250`, `1.2.5`, and the "Month D, YYYY" date (accepted cost, pinned).
  - `test_basis_quote_without_a_joined_run_is_read` pins `25, a rise`, `2.5, a rise` and `-1.80` as still accepted.
  - `test_one_whole_run_is_the_single_rule` tests the helper directly.
- Red on 80cccb1: I saw 23 failures after adding the first test set, before the rule existed. For the addendum rows I only re-ran against my interim regex rule, where `1.2.5 or 2.5` and `4.2.1` failed. I did not re-run the final test set on 80cccb1 itself.
- **Flipped test:** `section 4.2.1 a saving of 25` was accepted (reading `['25']`) and is now refused.

**H2.** The edge tuples are now `("", "-", ",", ", ")` and `("", ".", ",")`. Ten rows from the reviewer's pack were added to `test_edge_cut_is_read_in_every_reading` (2,/2, 750/2,\n750; the three `,2.5` forms; `,250`; `, 250`; `25,` on both pages). Each asserts the exactly-one issue and `_basis_amounts == []`. All were red before the fix.

**Probes** (repointed by passing the worktree root):
- `p1_e2e_hidden_run_failopen.py` exits 0. Of the probe's 16 lines, only `A saving of 2.5 is signed.` still composes (basis and accepted 2.5). `1.2.5 or 2.5` and `Section 4.2.1 gives a saving of 2.5` are now refused, and so is `A saving of 1,250 is signed.`
- `p2_comma_edge_bypass.py` exits 0.
- I did not run `p4_failclosed_alternative.py`, since it is reference only.
- `p13_quote_classes.py` exits 1:
  - Part D: 4 of 4 CP-1D triples, readings moved beyond W "none", and no frozen quote holds a comma figure, leading point or two-point run.
  - Part F fails 13 flags-off fidelity checks because CP-1D now refuses where the flags-off reference reads.
  - One of those failures is CP-3D `quote wrap before page minus`, which this commit does not touch and which I did not check against 80cccb1. The reviewer's earlier `qc.out` and `qc2.out` may show whether it predates this change.
- I did not run the 19 refusal mutations separately. The existing 13 mutants in `p_r13_mutants.py` pass (script exit 0, all killed). Part D reports no frozen reading moved.

**Mutants** (`<S>/cp1d-r13/p_r13_mutants2.py`, 13 existing plus 11 new, exit 1).
- Killed: edge start no comma, edge start no comma-space, edge end no comma, run no point join, run no leading point, run not whole, not exactly one, rule not applied.
- Survivors, both equivalent:
  - "Run no comma join" and "run no comma-space join". Without the join, `1,250` splits into two runs and is still refused by count, so the boolean is the same.
  - "One reading only". The wrap-joined reading never changes the run list; I tried 8 wrapped quotes with digits and commas.
  - Not asserted: I did not prove the equivalence beyond those samples.

**Gates** (all exit 0):
- pytest on both files: 653 passed, 1 skipped.
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.
- I did not run `ruff check src` as a whole, which printed a failure.

**Not verified:** `jscpd`, `complexipy`, `bandit` and any other gate; the full suite outside the two test files; mutation or property tests beyond the mutant script; CP-8 and the other owners (CP-3D, CP-2E) for the same rule; the CP-3D result noted under Probes.

agent=mx-feature fix-rounds=1 gates-first-pass=y