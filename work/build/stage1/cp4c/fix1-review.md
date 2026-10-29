## CP-4C fix round 1 re-review (target 3b9c3dc)

**Verdict: APPROVE.** Every finding holds: M1, L1, Q4, L2, L3 and L4. A-1 is unchanged and all four gates exit 0. The fix adds one new Low (a test-strength gap) and some Info notes, none of which reopens review.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. My probes are in `<S>/cp4c-fix1-review/`, with their outputs (`*.out`) beside them.

I exported both commits with `git archive`: `<S>/cp4c-fix1-review/old` (25c1a9b) and `<S>/cp4c-fix1-review/new` (3b9c3dc, byte-identical to the target's cp4c.py). Probes and mutants ran against those copies, with `PYTHONDONTWRITEBYTECODE=1`. The target is untouched: tracked files are clean, HEAD is 3b9c3dc, and its ignored caches were last written at 15:08, before the 15:11 commit.

### Per finding

**M1 (Q1, Q5): holds.**
- `_row_amount` (cp4c.py:520-528) builds the set of page lines that start with the quote. It reads a value only when exactly one distinct line starts with it.
- **`<S>/cp4c-fix1-review/probe_m1_cited_row.py <new> --expect`: exit 0.** All 30 cases give the Q1/Q5 outcome:
  - duplicate `Other` rows, either one quoted, each reads its own line (9, 5);
  - the suffix label is refused;
  - `Other  9` against `Other  99` is refused, while `Other  9  ` reads 9;
  - `Other` against an `Other  9` row is refused;
  - a whole-line quote reads that line, and so does a unique label-only quote;
  - `Total liabilities`, which starts two lines, is refused;
  - two trailing spaces, a leading space, tabs and a double space inside a label are refused; triple-space separators read correctly;
  - CRLF works with the frozen, CR-ending and label-only quotes;
  - a quote spanning a newline, the header, an empty quote and a mid-line-only quote are all refused;
  - identical duplicate lines read once.
- On 25c1a9b the same probe exits 1 with 10 mismatches, including both original M1 reproductions.
- My original `probe_quote_row.py` now exits 1 with 0 reproductions, which means fixed.
- **Frozen reads do not change.** `<S>/cp4c-fix1-review/probe_frozen_reads.py <old> <new>`: exit 0. All 5 cases match: 1,325 compute() cells, payload_issues, and 1,020 full-line page:4 reads.
- I found no input where the claim comes from a line other than the one that starts with the quote.

**L1 (Q2): holds.**
- cp4c.py:525 checks `len(cells) != len(header)`.
- The blank-cell row is refused with the #11 text (`probe_quote_row.py`). So are the longer rows (8 cells) in `probe_m1_cited_row.py`.

**Q4: holds.**
- `_row_amount` has exactly one `Decimal(` call, `Decimal(cell) if _FIGURE.fullmatch(cell) else None`. The pattern is the ruled ASCII grammar.
- **`<S>/cp4c-fix1-review/probe_q4_grammar.py <new> 40000`: exit 0.**
  - 40,030 fuzzed cells (Arabic-Indic, fullwidth and math digits, U+2212, NBSP, exponents, `_`, `,`, Infinity, NaN and sNaN) ran under both the default and an all-traps context. Nothing escaped.
  - Every non-None read matches an independent character-by-character matcher, and equals the cell exactly.
- `Decimal()` of 5,000-digit and 10^6-digit grammar cells does not raise with all traps on.
- Removing the `InvalidOperation` catch and the `is_finite` check is safe: no non-grammar string reaches `Decimal`.

**L2 (Q3): holds.**
- cp4c.py:1534-1535 raises `CP-4C: CP-1 EBITDA … is known without an amount; invariant`.
- `probe_cp1_known_text.py` now exits 1, with a traceback at that line. The probe expected the old "missing" reason, so this means fixed.
- The mutant that restores "missing" is killed by `test_l2_…`.

**L3: holds.**
- `probe_state14_paid_mutant.py`: exit 0, so the mutant is still distinguishable.
- `state_14_claims_only` is killed by `test_l3_state_14_on_a_payment_over_38_digits` run on its own.

**L4: holds.**
- `probe_survivors.py`: exit 0.
- `<S>/cp4c-fix1-review/mutants_adversary.py` (a copy of mine, so its temp tree lands in my folder): exit 1, baseline passes.
  - The exit 1 comes only from the 2 sites the fix removed: `row_amount_infinite_ok` and `cp1_ebitda_known_text_raises`.
  - 40 are killed. The 7 L4 targets still present are each killed by their new `test_l4_*` test.
  - The 4 survivors are exactly the equivalents I named: `later_block_overrides_reason`, `balance_only_positive`, `fulcrum_unchecked_at_compose` and `recovery_after_allocation`.
- `row_amount_infinite_ok` is now covered by `q4_infinity_allowed`, which is killed by `test_q4_…[Infinity]`.
- **`<S>/cp4c-fix1-review/mutants_fix1_review.py`: exit 0.** Of 24 mutants, all 20 with a named test are killed by that test alone, including the reverts of M1, Q5, L1, Q4 and L2. 4 survive; see the new findings below.
- The new tests are causal: run against 25c1a9b they give the reported 9 failures (in `<S>/cp4c-fix1-review/redcheck`).

**A-1 unchanged: holds.**
- The diff touches only the import, `_row_amount` and `_cp1_ebitda`.
- Outputs are in `<S>/cp4c-fix1-review/a1_*.out`. All exit 0:

| Probe | Run | Result | Exit |
|---|---|---|---|
| `probe_alloc_reference.py` | 3,000 × 6 seeds | 0 mismatches | 0 |
| `probe_state14.py` | default | holds | 0 |
| `probe_v02_frozen.py` | default | holds | 0 |
| `probe_t4e9_compute.py` | 250 × seeds 11 and 29 | 0 broken | 0 |
| `probe_hypothesis_big.py` | 2,000 × seeds 0, 1, 20261028 | 15/15 pass | 0 |

### New findings (introduced by this diff)

- **N1 (Low, test strength): the "longer row" half of Q2 is not pinned.**
  - Where: cp4c.py:525.
  - The mutant `<` for `!=` survives.
  - On a row whose label holds a double space (`Deferred  items  1  2  3  4  5.00  6`), the mutant reads 4, the Q3 column. The current code correctly refuses it.
  - Fix: add that row to the L1 test.
  - Probe: `<S>/cp4c-fix1-review/probe_new_survivors.py`, exit 0.
- **N2 (Info, test strength): other ruled clauses are not pinned.**
  - Q5's "identical duplicates count as one" (cp4c.py:520): a list mutant survives and fails closed.
  - Q4 cells `+5.00` and `.5` (cp4c.py:512): the mutants survive and would read the cell's own value.
  - The current code is correct on all three. Same probe as N1.
- **N3 (Info, for the controller, a Q1 boundary): partial-label quotes are now accepted.**
  - A quote that ends mid-label now cites a row. `Pr` reads PP&E's 60.00; 25c1a9b refused it.
  - The read follows Q1's literal wording (the one line that starts with the quote), and no frozen value moves.
  - Probe: `probe_m1_cited_row.py`, case "partial label".

### Pre-existing, for LEAD (identical on 25c1a9b)
- A quote truncated mid-figure (`Other current liabilities  10  10  10  10  1`) reads the row's 10, while the citation shows `1`. It is the same row.
- A bare CR or U+2028 inside a `\n`-line lets `Other  1  1  1  1` read the 9 that follows `X` on that same `\n`-line.
- A grammar cell of about 10^6 digits makes `payload_issues` raise `decimal.Overflow` out of `_exact`. Probe: `probe_q4_extreme_downstream.py`, exit 0, informational.

### Standing rules
- No stub, fake value or catch-all. The fix removes a handler and adds none.
- The odd `if not _payload_issues(...)` inside `pytest.raises` in the CP-2A lineage test cannot pass vacuously.

### Gates (target root, exit codes)
| Gate | Result | Exit |
|---|---|---|
| pytest `tests/test_method_cp4c.py` | 170 passed | 0 |
| `ruff check` (I added `--no-cache`) | clean | 0 |
| `ruff format --check` (I added `--no-cache`) | clean | 0 |
| `MYPYPATH=src mypy --strict` (cache in `<S>/cp4c-fix1-review/mypycache`) | clean | 0 |

Not verified: B1-B6 (with LEAD); the lane commits after 6d98bd8; the full repo suite; Stage 2 packs, including whether bare CR, U+2028 or double-spaced labels occur in real spans; mutmut (hand mutants only); the A-1 probes ran at reduced counts (18,000 reference waterfalls, 500 compute() runs, 2,000 hypothesis examples × 3 seeds), not the first review's full counts.
