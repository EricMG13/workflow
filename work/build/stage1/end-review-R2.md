**Stage 1 end review, lens R2 (arithmetic, Review Focus 1–2), target 87b2a1a**

**Verdict: FINDINGS.** I found one Low, a breach of the CP-L10 lease, and one Info. I found nothing High or Medium.

The review was read-only, done in a full archive copy at `<S>/stage1-end-R2/tree` with `PYTHONDONTWRITEBYTECODE=1`. The worktree's git status is clean.

**Fast lane set:** exit 0. 3629 passed, 2 skipped, 1 xfailed. The xfail is the known B5 CP-2H composer-only fixture.

### Findings

**L1 (Low, unruled: goes to LEAD). CP-L10 rounds `change` at 38 digits; the lease says it must be exact.**
- **Where:** `src/deploy_workflow/owners/cpl10.py:296-300` (`_q38`), called at `:330` and `:338`.
- **Lease text broken:** `docs/CPL10-OWNER-LEASE.md:114` says "change | `b - a` (signed), one exact subtraction".
- **What the code does:** it computes `Fraction(close) - Fraction(start)` and then divides that in `Context(prec=38, ROUND_HALF_EVEN)`. Nothing traps `Inexact`, unlike the trapping contexts in cp2g, cp4c, cp1d and cp2a.
- **Concrete input:** two CP-1 ratio facts. CP-1 stores ratios as 38-digit quotients (`cp1d.py:359-360`), and two with different exponents need 39 digits for their difference.
  - start = 5/3 at 38 digits = `1.6666666666666666666666666666666666667`
  - close = 100/7 at 38 digits = `14.285714285714285714285714285714285714`
  - stored change: `12.619047619047619047619047619047619047`
  - exact change: `12.6190476190476190476190476190476190473`
- **Second input:** an amount outside any realistic range also stores a non-canonical exponent form, `1.2345678901234567890123456789012345679E+38`.
- **What is not affected:** the materiality rating and the rank use the exact Fraction, so they are correct. No frozen case is affected, because `total_leverage` and `interest_coverage` `change` are `missing` in both `positive` and `limited`. The display at 2 dp does not change.
- **Why it still matters:** at Stage 2, any pair of quarters where both ratios are known stores a value that is not exact.
- **Background:** `work/build/stage1/cpl10/design-notes.md:9` records the 38-digit quantisation as a design choice, but no ruling amends lease line 114.
- **Fix, either way:** LEAD rules that 38 digits is acceptable and amends the lease, or the code stores the exact difference (or traps `Inexact`, as cp4c `_exactly` does).
- **Probe:** `<S>/stage1-end-R2/probes/p_r2_cpl10_change_exact.py`, exit 1 (this reproduces the defect).

**I1 (Info, no action).** The module functions I probed give identical results under a hostile ambient context (prec 12, ROUND_DOWN), so a caller cannot change a stored value. The probed functions are in cp3c, cp2g, cp2h, cp1c, cpl10, cp3d (`compose` and `stored`) and cpdr. Two sites run outside a fixed context, but their results are exact for in-range inputs:
- `cp3d.py:340-341,313-315`
- `cp2e.py:429-435`

### Sweep results with no finding
1. **Missing operand never becomes 0.**
   - Every `sum(..., Decimal(0))` and every `Decimal(0)` default is guarded by a first-gap or None check:
     - `cp3c.py:418`, `cp2d.py:224`, `cp4c.py:290/2036`, `cp1d.py:1004`
     - `cp2g.py:435`: the base case's zero shock is exact by the lease.
     - `cp2e.py:238/246`: a stated fixed rate or domestic debt is a known 0.
   - The rejected-item accepted 0 in `cp1d.py:627` is lease-mandated (`CP1D` lease line 81: "an item with f = 0 has accepted known 0").
   - The empty agenda in `cpdr.py:319` returns None, not 0.
2. **No `float`.** There is no `float`, `round()` or `math` call on a Decimal in any of the 16 modules. `cp4c.py:236` uses `math.floor` on a `Fraction`, which is exact. `Contract` is `strict=True, allow_inf_nan=False`.
3. **Quantisation matches each lease.**
   - CP-3C: 60 digits, ratios at 4 dp ROUND_HALF_UP (`cp3c.py:67,430`; LEAD round 11).
   - CP-3D: 28 digits HALF_EVEN, stored values quantised HALF_UP (`expected.arithmetic.decimal_context`).
   - CP-DR: 4 dp HALF_UP.
   - CP-8: exact, with Inexact, InvalidOperation and DivisionByZero trapped.
   - CP-2G, CP-4C: 38 digits HALF_EVEN with an Inexact-trapping exact context.
   - CP-2H: 38-digit subtraction, percent converted to pp with `.scaleb(2)`.
   - CP-1C: 38 digits HALF_EVEN.
4. **Zero denominators match each lease.**
   - cp2g `_ratio`: den <= 0 is missing.
   - cp3c `_ratio` and cover with balloon 0: not_applicable.
   - cp1c `ratio`: not_applicable; outlier with median 0: None.
   - cp4c: EV / CP-1 EBITDA <= 0 is missing; EV 0 gives known 0 recoveries.
   - cpl10 zero base: Material with pct not_applicable.
   - cp3d: dm <= 0 is not_applicable; recovery < 1 and maturity after quotation are validated (`cp3d.py:634,692`).
5. **Signs match.**
   - CP-2G negates the four CP-1 outflows (`cp2g.py:290,362`).
   - CP-3C negates the cash interest outflow (`cp3c.py:895`).
   - Break comparators match CP-2G lease line 126 (`<=` for FCF and coverage, `>=` for leverage, strict `<` for liquidity).
   - CP-2H and CP-8 reach and breach tests are strict, equal is not reached (`cp2h.py:424`, `cp8.py:499`).
   - CP-4C allocation conserves the total exactly (three claims of 1 against EV 1 sum to 1).
- **Probe:** `<S>/stage1-end-R2/probes/p_r2_edges.py`, exit 0 (26 checks plus the ambient-context check).

### Probe exit codes
- Fast lane set: 0
- `p_r2_edges.py`: 0
- `p_r2_cpl10_change_exact.py`: 1 (reproduces L1)

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: the reused engines' arithmetic behind CP-3, CP-4 and CP-5 (`deploy_vii.cp3_relative_value`, `cp4_legal`, `cp5_integrity`); those modules add no arithmetic and I did not audit the engines. I only spot-checked CP-2A, CP-2D, CP-2E and CP-1D, the modules the layer reviews `review-{A,B,C}.md` already cover: their contexts, missing propagation and the `_outcome` zero path. I did not re-derive their full recipes against the leases. I did not check whether pydantic strict mode refuses JSON floats for each numeric submission field module by module. I did not exercise L1 through a real CP-1 head pair at Stage 2.
