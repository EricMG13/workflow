# CP-3D fix round 1 re-review (mx-adversary)

## CP-3D fix round 1 re-review (9d74fc7 on d8c3512): APPROVE

M1, M2, L1 and L2 are fixed. Nothing High or Medium remains. The fast gate on the fix gives 1281 passed. `ruff check`, `ruff format --check` and `mypy --strict` on the three changed files exit 0. `test_method_cp3d.py` and `cases/` are untouched.

Probes are in P = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-s2-review/`.

**Probe exit codes**

| Probe | Exit | Note |
|---|---|---|
| `p_citation_wrong_quote.py` | 0 | was 1 |
| `p_blank_all_sites.py` | 0 | |
| `p_cited_refs_equiv.py` | 0 | |
| `p_rules_each_absence.py` | 0 | |
| `p_reader_edges.py` | 0 | |
| `p_scope_guard_isolation.py` | 0 | |
| `p_mutants.py` | 0 | see L1 |
| `p_mutants_fix1.py` | 0 | new |
| `p_fix1_cites.py` | 0 | new |
| `p_head_tamper.py` | 0 | new |

**M1 (citation quotes): fixed.**
- **Each fact's quote is its own.** All 4 terms facts and the quoted-level `T3E.3.r04.*` cite their own quote.
- **Across all three cases** (`p_fix1_cites.py`, 0 violations):
  - every fact and claim quote is one the submission gave for that page;
  - each fact has exactly one `Citation` per page;
  - each quote is the first of the cell's own quotes on that page;
  - technicals and talk cite their own quotes.
- **Derived-fact rule:** it holds as stated. A derived fact cites only its first own quote per page, for example the bid sentence and not the maturity quote for DM mid on market page:1. No quote is invented. Info: LEAD may rule whether derived facts should carry every input quote.
- **No fail-open:** `cite_of` raises when a cell has no quote for a page. My mutant F4 (a placeholder quote instead) is killed.
- **Frozen and page-level cites are unchanged:** `Cites` compares equal to the page pairs, and the oracle tests pass.
- **The Stage 1 change is limited to provenance:** the diff touches only the `Cites` type, `_trace` and the claim merge. The claim merge keeps the old page order.

**M2 (Acceptance 5–6 tests): correct.** I ran the 3 new tests: 3 passed.
- **Blocked CP-0:** CP-0 settles blocked after two invalid attempts, no CP-3D attempt is consumed, and the `BLOCKED_EDGE` refusal is recorded.
- **`stale_binding`:** uses the S1a pattern.
- **Probe tamper:** the forged step output is stored under its own hash, so `probe` itself refuses it with `identity_mismatch`, and the genuine attempt passes the same call.
- **Stale CP-0 `begin` case:** not required. Acceptance 5 names only a blocked CP-0. The Refusals line does say "blocked or stale", but I reason a stale CP-0 cannot happen in a CP-0→CP-3D run, because CP-0's only input is the fixed pack. I did not verify that.

**L1: fixed.** The original sweep now kills A1, R1–R3, R5, D1, D2, S1 and C3. Four mutants survive and are equivalent: R7, D3, S4, B1. C1 and C2 no longer apply.

**L2: fixed.** The blank-quote inventory now includes `reference_rate.level.quote`.

**Low**
- Acceptance 6 also covers tampering the head, and the suite has no test for that half. My probe shows `probe` refuses a consistent head forgery with `identity_mismatch` (`p_head_tamper.py`, exit 0).

**Info**
- **Survivors of `p_mutants_fix1.py`:** F3 (claims merge only their first cell) and F5 (merge keeps one quote per page) survive. Both are equivalent on the oracle.
- **Copying a `Cites`:** `copy.copy` or `copy.deepcopy` raises `AttributeError` (`p_fix1_cites.py`). It fails closed, and nothing in src copies cells.
- **Reader test:** the own-limitations check is now a prefix match. It could assert `[*own, synthetic]` exactly.
- **Synthetic-limitation note for LEAD:** it agrees with `execution.settle:474-488`.
  - Own limitations become the candidate's own plus "Synthetic case; not real issuer qualification", de-duplicated.
  - Inherited limitations are recomputed from the bound heads, minus own. CP-0's own limitations carry the synthetic line, so it drops out of inherited.
  - The oracle's lists are the candidate's, before settlement.

Not verified: the full `test_owner_cp3d.py` run (I ran only the 3 new tests), the full suite, the render, the PR-size gate, and that a stale CP-0 is unreachable in this run.
