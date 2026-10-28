## R1 report: Stage 2 readiness (Review Focus 3), lane commit 87b2a1a

**Verdict: FINDINGS.** There are three Medium findings and no High. Each Medium breaks the seam between a producer's actual output and the consumer's Stage 1 input. The fast lane set passes.

**Fast lane set** (run at 87b2a1a, from a `git archive` copy): exit 0. 3629 passed, 2 skipped, 1 xfailed (the xfail is cp2h B5/B7, already known).

**Probes** are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage1-end-R1/probes/`. Run each as `python -I <probe> <tree>`. Exit 0 means the finding reproduces.

| Probe | Exit |
|---|---|
| p1_cp2d_to_cp3c_seam.py | 0 |
| p2_cp4c_cp2g_lineage.py | 0 |
| p3_cp3c_cp1_status.py | 0 |
| p4_cp2d_status_collapse.py | 0 |

### Medium

**M1. CP-3C cannot read CP-2D's real output. Unruled, goes to LEAD.**
- **Where:** `cp2d.py:837-848` (`Cell`) and `:917-919` (`_gap_cell`); the consumer side is `cp3c.py:1013-1022` (`_copy`).
- **The gap:**
  - `cp2d.Cell` has no period field at all.
  - `_gap_cell` drops `value_class` and `cp1_operand`.
  - CP-3C needs a period on every known copied amount, and a `value_class` on every copy, gaps included.
  - The CP-3C test supplies both by hand: `tests/test_method_cp3c.py:150-173` uses the balance date and the known twin's class.
- **Input and wrong output (p1):** CP-2D cells exactly as `cp2d.compute` emits them, passed to `cp3c.compute`:
  - positive and gap_minimum_cash both raise `CP-3C T2E.4.r01.c1: a copied amount needs its unit and period`.
  - Even after assigning the period, gap_minimum_cash raises `CP-3C T2E.5.r07: a copied fact keeps its value_class, and none is bound`.
- **Rule it breaks:** CP3C lease :146 says these fields are "the CP-2D head fact's own, bound at run time", but the CP-2D lease and oracle pin neither (CP-3C lease :146 says so). `work/build/stage1/cp3c/report.md` item 7 lists this as open; the producer-side cause is new.
- **Fix plan:**
  1. LEAD rules what period and `value_class` CP-2D settles on each fact: balance date for balances, the twin's class for a gap.
  2. Sonnet task: `_gap_cell` keeps the `value_class` and `cp1_operand` of the cell it stands for, and the settler assigns the ruled period. This needs a CP-2D oracle re-pin.
  3. Make p1 a cp3c test that runs on `cp2d.compute` output.

**M2. CP-4C picks the CP-2A scenario from CP-2G lineage that a settled head does not store. Unruled, goes to LEAD.**
- **Where:** `cp4c.py:418-423` (`Cp2gEbitda.derives_from`) and `:1301-1311` (`_scenario_row`).
- **The gap:**
  - Product `Fact` (`deploy_vii/contracts.py:154-180`) and `Module` have no lineage field, and nothing in `src` outside the owners stores `derives_from`.
  - The `cp2g_reader` pin (CP2G lease :148) has no lineage entry.
  - The CP-4C test copies the oracle's `derives_from` by hand (`tests/test_method_cp4c.py:250`).
  - CP4C lease :52 ("T2B.1 row named by the `cp2a:` lineage of T2H.4.d26.ebitda") and :69 depend on it.
- **Input and wrong output (p2):** positive inputs with `derives_from=()`, which is all a settled head can give, raise `CP-4C: CP-2G downside EBITDA names no CP-2A T2B.1 scenario`.
- **Smallest fix:** LEAD amends CP4C lease :52 so the row comes from the settled `T2H.3.d01.source` text (`"CP-2A T2B.1.s03.ebitda_decline"`, present in the CP-2G oracle). Then a Sonnet task:
  1. replace `derives_from` with `scenario_row: str`, filled by the reader;
  2. keep the "every downside year shares it" check against the `T2H.3.d0x.source` texts;
  3. turn p2 into a test.

**M3. CP-2D loses CP-1 status: conflicting and not_applicable become "missing".**
- **Where:** `cp2d.py:96-130` (`Operands`: every field `Decimal | None`, no status), `:212-214` (`_op`) and `:940-942` (`_copy`).
- **The gap:** product `Fact.status` allows `conflicting` and `not_applicable`. The only place such a CP-1 operand can go is `None`.
- **Input and wrong output (p4):** cfo conflicting gives `T2E.1.r02` state `gap` with `Not calculable: Operating cash flow is missing`. CP-1's own status and limitation are lost.
- **Rule it breaks:** CP2D lease :102 ("Cells copied from CP-1 keep that fact's own value_class, status and citations") and the manifest `fact_bindings` rule "status is read, never defaulted". CP-1C (6g) and CP-4C (round 8 A-4) already rule how a `conflicting` copy is kept.
- **Fix plan:**
  1. LEAD rules the CP-2D display and reason for a conflicting or not_applicable operand.
  2. Sonnet task: the operand type becomes `(status, amount, limitation)`, `_op` returns a Gap that carries CP-1's limitation, and `CellState` gains the ruled state.
  3. Test: p4 inverted.

### Low

**L1. CP-3C raises on a CP-1 fact that is conflicting or not_applicable. Unruled, goes to LEAD.**
- **Where:** `cp3c.py:34` (`Status = known|missing`), `:237-245`, `:756-763` and `:774-781`.
- **Input and wrong output (p3):** adjusted_ebitda conflicting or not_applicable raises `expected a MILLIONS amount`; `term-loan.secured_status` raises `expected a text fact`.
- **Why it matters:** this fails closed, but CP-4C keeps `conflicting` on the same T4.18 facts (A-4), so the two consumers behave differently. CP3C lease :81 keeps the states distinct.
- **Fix:** a ruling, then the CP-4C pattern.

**L2. Some inputs have no named settled source; the tests fill them from oracle keys or constants.**
- **Fields:**
  - `Cp2aHead.base_period` in CP-2G (`cp2g.py:621-624`, filled at `test_method_cp2g.py:199`) and in CP-4C (`cp4c.py:447-450`, filled at test :270). Both read `CP2A_EXP["cases"][...]["base_period"]`, a case key, not a fact.
  - `Cp2aScenario.name` (`T2B.1.<row>.name`). It is in neither the manifest `upstream_fact_selection` nor CP2G lease :61.
  - `Cp3cInputs.currency`: a test constant (test :49). `Cp1Fact` has no currency.
- **Fix:** name each source in the manifest or Stage 2 brief:
  - `base_period` is the period shared by the T2B.1 decline facts (this held in every CP-2A oracle case);
  - currency is the CP-1 T4.10 `cash_closing` `Fact.currency`.
- **Test:** the Stage 2 adapter test asserts each one.

### Info
- 14 of the 16 manifests have no `fact_bindings`; only cp2d and cp3c do. The others hold their bindings under `fact_selection_rule`, `cp1_fact_selection_rule`, `upstream_fact_selection`, `upstream_facts_read` or `run_time_bindings`, so plan Review Focus 3's wording needs a rule mapping. Review-B already noted this for its three modules.
- CP-2D `CellState` spells a gap as `"gap"`, while the product Fact and CP-3C use `"missing"`. The adapter has to map it, as the cp3c test's `STATE` does.

**Fields checked, beyond layer reviews A, B and C:**
- **CP-2G:** CP-1 T4.10, 16 metrics, same as the manifest; CP-2A T2B.1 and T2B.6; CP-1D T1D.3 and T1D.6. CP-1D's statuses, unit and period are taken correctly.
- **CP-2H:** CP-2G T2H.6, 28 facts. CP-2H accepts every status CP-2G emits.
- **CP-4C:** CP-1 T4.10 and T4.18; CP-2A T2B.1; CP-2G T2H.4 and T2H.7; CP-4 T4C.11, T4.10 and T4.13.
- **CP-3C:** as in its `fact_bindings`.
- **CP-8:** CP-0 T3 authority (matches `readiness.py:459`) and CP-6 T6-FINAL.
- **CP-5:** `ReviewScope`, which the product builds.

Not verified: whether a real promoted CP-1 head ever emits conflicting or not_applicable T4.5, T4.10 or T4.18 facts, so M3 and L1 are not shown to be reachable on real data. Whether Stage 2 plans another store for lineage (a grep of `src` found none). The CP-L10 and CP-1C amended parts, which are on hold. Per-field lists for the modules the layer reviews already covered were not repeated. No gate other than the fast lane set was run.
