# CP-2G fix rounds 1 and 2: adversarial re-review (target `5002b6d`, worktree `agent-a4377a7580e8e70db`)

**Verdict: APPROVE.** I found no High, Medium or Low findings. M1, M2, L4, M3/L5 and the round 8 A-3 citation change all hold, every probe and runner reproduces, and all gates exit 0. There are three Info notes. One predates the change and goes to the owner. I edited nothing in the target, and `git status` is still clean at 5002b6d.

My probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-fix-review/`, called F below. The mutant copy is `F/copy`, a `git archive` of 5002b6d, restored after every run.

## Checks
1. **M1 holds** (`cp2g.py:1110`, `:1196`, `:2076-2091`, `:2172-2173`). `F/q01_m1_reference_ids.py` exit 0.
   - These validate and resolve: a CP-1 fact id, a CP-1 calc id, a source fact id, a CP-1D fact id and a CP-1D calc id. Each one shows up in `claim.references` and in a reference table, and the claim passes `prose.issues` against the module's facts and references.
   - These fail validation as expected: a CP-2A id, an unknown id, a calc id shared by two CP-1 facts, a calc id shared by CP-1 and CP-1D, and a CP-1D id when CP-1D is unbound.
   - I found no reference that validates but does not resolve.
2. **M2 holds** (`:309-316`, `:347`). `F/q02_m2_book_units.py` exit 0 over 672 variants (7 cases × 10 amount metrics and 6 ratios × 6 books).
   - Every known CP-1 amount in EUR, THOUSANDS, UNITS, no currency, scale 1000 alone, or lower-case `usd` raises "USD MILLIONS" from both `payload_issues` and `compute`.
   - Ratios are never checked. An unknown amount in another book leaves the output unchanged. A scale written as `1E+6` passes.
3. **M3 and L5 hold.** `F/q06_named_kills.py` exit 0.
   - Each mutant was run against only the test the fix reports name, with bytecode caching off. All 31 are killed by their named tests: A10, A22, A18, A13, B13, B14, B10, B15, V03–V06, V08, V09, V11–V13, S01, R01, R04, R05b, R06, R07, A23, A26 and C01–C06.
   - The V07 and S05 equivalence claims hold (`F/q05_v07_s05_equivalence.py` exit 0). For V07, CP-2G's prohibited kinds never repeat a (kind, phrase) pair and every other issue carries a distinct path, index or row. For S05, `Fact` refuses an unsettled fact that carries an amount.
4. **L4 holds** (`:1881-1885`). `F/q03_l4_level_unit.py` exit 0.
   - A missing level with no unit, a not_applicable level with no unit, and a known level in TIMES each raise a ValueError naming `T2B.6.b01.level`.
   - Levels in mapped units still compose.
5. **A-3 holds** (`:2388-2424`, called at `:2442`). `F/q04_citations_rule.py` exit 0: 92,200 cell checks (7 cases × 40 seeds) with no mismatch.
   - **Method:** I gave every upstream fact random citations from a shared pool, with repeats within and across facts. The expected values come from the oracle's own `derives_from`, flattened fully and de-duplicated once, keeping the first occurrence.
   - **Results:** no fact's citations come out in an order the rule doesn't give. Code `derives_from` equals the oracle's. Non-calculated and unsettled facts carry none. Every lineage entry resolves, and the own-lineage graph is acyclic.
   - **No calculated cell cites a CP-2A watch level** (`F/q07_cp2a_lineage_classes.py` exit 0). Level copies are `analyst_judgment` or None.
   - **The invariants are unreachable from valid inputs here.** The reviewer's fuzzers, re-run against the fix, raised nothing: p04 exit 0, p05 exit 0 (435 composed, 65 refused, 0 failures).
6. **No missing value becomes 0** (p04 and p05 clean). The diff adds no stub, fake value or catch-all. The membership filter in `_named` never drops anything for validated text, because the validator requires every figure to be in the same map.

## Info notes (none reopens review)
- **I1 (predates the change, goes to the owner).** CP-1D supported EBITDA is consumed with no currency or scale check (`cp2g.py:1146-1155`, used at `:1351` and `:2040`).
  - Failure: a CP-1D T1D.3 fact restated in EUR, or in EUR thousands, composes silently. `T2H.2.ebitda_adjustment` came out as 31770 labelled USD MILLIONS.
  - A consistent run cannot reach this. CP-1D forces MILLIONS and one currency (`cp1d.py:157-166`), and a non-USD CP-1 already fails CP-2G's own M2 check.
  - `F/q08_cp1d_book.py` exit 1, meaning the gap is real.
- **I2.** CP-1D lineage uses the literal `CP1D_IDS` (`:1338`, `:1359`, `:2040`), while `_cite` keys CP-1D by each bound fact's own id (`:2398`).
  - A `Cp1dHead` whose facts carry other ids validates and then raises `lineage … names no settled fact`. That is fail-closed, and a reader that takes the facts by id, as the lease says, cannot produce it.
  - `F/q09_cp1d_id_contract.py` exit 0.
- **I3 (probe harness).** The runners `p06_mutants.py`, `p06b_mutants_followup.py` and `p_fix2_citation_mutants.py` don't disable bytecode caching.
  - A mutant the same size as the previous file, written within the same second, can run stale bytecode and give a false kill or a false survive.
  - I reproduced this: my first q06 run showed 8 false survivors (exit 1). The rerun with `PYTHONDONTWRITEBYTECODE=1` (exit 0) is the evidence I rely on. Set that variable in those runners before reusing them.

## Probe exit codes
- **Reviewer probes:**
  - `p03` exit 0.
  - `p11` and `p10` each exit 1 raw, because they now die on the approved fail-closed ValueError. Through `cp2g-r5/expect_valueerror.py` both exit 0.
  - `p06_mutants.py` exit 0 (it always exits 0): 77 of 79 killed, survivors `['V07', 'S05']`.
  - `p06b` exit 0, all 5 killed.
  - `p04` exit 0, `p05` exit 0.
- **Implementer probe:** `p_fix2_citation_mutants.py` exit 0, C01–C06 all killed.
- **My probes:**
  - q01, q02, q03, q04, q05, q07 and q09 exit 0.
  - q06 exit 0 on the rerun (the first run's exit 1 was the bytecode artefact in I3).
  - `q06b_who_kills.py` exit 0.
  - q08 exit 1, which is I1.

## Gates (target root, all exit 0)
- pytest `tests/test_method_cp2g.py`: 222 passed.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict` on both files: 0. Its cache went to scratch.

Not verified: Stage 2 (readers, module and claim assembly, claim-level citations, real CP-1 heads whose calculated T4.10 facts carry citations); the round 9 rewording of the M2 message; a full mutmut run; the full suite and other modules' tests; whether "analyst inputs carry none" is meant to cover CP-2A analyst shocks that carry citations (the code inherits them, as the literal rule reads, and the frozen CP-2A facts carry none); exactness of the 77 "killed" results in p06 outside the named set (subject to I3).
