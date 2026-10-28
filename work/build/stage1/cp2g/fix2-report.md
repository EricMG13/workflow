# CP-2G fix round 2 report (controller-saved from the implementer's hand-back)

CP-2G fix round 2 (round 8 A-3 citations) is done. Composed facts now carry citations by the lease's lineage rule. The CP-2G test file passes (222 tests) and every gate exits 0. Ledger line at the end.

**Commits** (branch `worktree-agent-a4377a7580e8e70db`, worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db`)
- **f1f301b:** merge of `claude/module-dev-status-review-0981b6` on top of dcfcbc0.
  - It conflicted on `docs/CP4C-OWNER-LEASE.md`, a file I never edit. The lane side only added LEAD's round 8 amendment paragraph, so I took the lane's version.
  - `cases/` and that lease are now identical to the lane tip.
- **5002b6d:** the fix. It touches only `src/deploy_workflow/owners/cp2g.py` and `tests/test_method_cp2g.py`.

**What the oracle pins.** It pins the rule text, the top-level `lineage_rule` in `expected.json`. No expected fact carries a `citations` key, so the oracle has no per-fact citation values to compare against.

**The tests** (in `tests/test_method_cp2g.py`)
- **`test_citations_follow_the_lineage_rule[all 7 cases]`:**
  - It asserts that the oracle's `lineage_rule` starts with the pinned sentence, held literally in the test.
  - It then re-applies the rule independently to every composed fact and compares citations exactly.
- **`test_citations_order_and_de_duplication`** (positive case, explicit values):
  - `T2H.2.debt.value` = (debt).
  - `T2H.6.a25.net_leverage` = (debt, cash).
  - `T2H.5.b26.closing_cash` = (cash, debt): opening cash first, then debt via FCF and interest.
  - `T2H.6.b26.net_leverage` = (debt, cash): (debt) + (cash, debt), with the repeat kept once at its first place.
  - `T2H.4.a25.revenue` and the analyst input `T2H.3.a01.fy1` carry none.
- **`test_cp2a_watch_level_copies_carry_no_citation`:** with cited CP-2A cells, the T2H.7 level copy and the first-year text carry none, and the calculated required-decline copy carries the CP-2A citation.

**Red seen first.** On all cases: `T2H.2.debt.value: assert () == (Citation(... locator='page:4', quote='Total debt  45 …'),)`.

**Stand-ins.** In the Stage 1 inputs only the two CP-1 source facts (total debt, cash) carry a citation: the page-4 stand-in from my Stage 1 report. The calculated CP-1 facts and the oracle's CP-2A and CP-1D facts carry none. That does not block an exact check: the rule is tested exactly on these inputs, and the CP-2A test injects citations to cover the "watch levels carry none" branch.

**Implementation**
- `_cite(b, run)` runs after all tables are composed and before the claims.
- A known calculated fact gets `dict.fromkeys` over its `derives_from` entries, in order. An entry resolves as follows:
  - `cp1:<metric>`, `cp2a:<id>` or `cp1d:<id>`: the upstream fact's citations.
  - An own fact: that fact's resolved citations, transitively.
  - Anything else: none. Non-calculated, analyst, text and unsettled facts keep what they have, which is nothing.
- **Fail closed:** a lineage entry that names no fact, or a cycle, raises a `ValueError` invariant. No frozen case reaches it, so there was no silent-order case to list for LEAD.

**Mutants** (from a full copy at `<S>/cp2g-r5/mutcopy`; runner `<S>/cp2g-r5/p_fix2_citation_mutants.py`)
- **Runner exit 0.** All six are killed:
  - C01 drops de-duplication;
  - C02 reverses the `derives_from` order;
  - C03 de-duplicates keeping the last occurrence;
  - C04 own facts contribute nothing;
  - C05 citations are never applied;
  - C06 non-calculated facts cite their lineage. This one survived the first run and the CP-2A watch-level test kills it.
- **Fix-1 kills still hold:**
  - `p06_mutants.py` exit 0, survivors `['V07', 'S05']`, the same equivalence reasons as in my fix-1 report.
  - `p06b_mutants_followup.py` exit 0, all killed.
- `<S>` is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

**New strings:** no new user string. The only new text is the invariant message `CP-2G: lineage <path> names no settled fact`, so no prose probe was needed.

**Gates** (all exit 0, first run after the fix)
- pytest `tests/test_method_cp2g.py`: 222 passed.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict` on both files: 0.

Not verified: citations against real CP-1 heads, where calculated T4.10 facts may carry their own citations (Stage 2); the full suite and the other modules' tests after the merge (only the CP-2G test ran); a full mutmut run; whether Stage 2's Module or Claim assembly also expects claim-level citations (claims keep `citations=[]` as the oracle pins).

agent=general-purpose(opus) fix-rounds=2 gates-first-pass=y
