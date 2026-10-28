# Stage 1 layer review, group A (CP-2E, CP-2D, CP-2A): mx-architect, controller-saved

**Branch:** `worktree-agent-a1c69c467b8de6866`, from 348799d. One commit, `6b20407` test(cp2d), pins the first-missing operand precedence (ledger L4). It touches only `tests/test_method_cp2d.py` and was merged into the lane.

**Verdict:** every traced path matches the Method text and rulings 1–4. No missing operand becomes 0, and quantisation matches each lease. There is no High finding.

**Probes:** in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage1-review-A/`. Exit 0 means the probe reproduces its finding.

## Findings
- **Medium, pre-existing, with LEAD and the owner: CP-2A P1.** A Q4 quarter base has known CP-1 ratios, so it passes the gate (`cp2a.py:189-196`), and `stress()` (:308) then divides debt by quarterly EBITDA. Example: 6.67x against CP-1's 1.67x. Probe: `probe_cp2a_p1_quarter_gate.py`.
- **Low → LEAD: CP-2D month arithmetic is asymmetric.** `cp2d.py:232-243`: `add_months` clamps to the month end, but `months_between` subtracts a month. For D0 2025-12-31, a facility maturing 2027-06-30 shows "17 months", yet it falls outside a 17-month horizon. Proposed rule: the largest n with `add_months(D0, n) <= maturity`. Probe: `probe_cp2d_month_asymmetry.py`.
- **Low → Stage 2: CP-2D 2D-d "shows both" is not realised.** `cp2d.py:573-601`. Round 5 L4 already makes this a Stage 2 obligation through T2E.9. Probe: `probe_cp2d_shows_both.py`.
- **Low → LEAD: CP-2A ranks "Already reached at base" first with a negative required decline.** `cp2a.py:369-371`. Example: "… at an EBITDA decline of (10.0)%". No wording is pinned. Probe: `probe_cp2a_already_reached.py`.
- **Low → LEAD: CP-2E treats a negative denominator as known.** `cp2e.py:71-80`. Coverage shows (15.00)x and leverage shows a known negative value. The behaviour is lease-pinned, but it is inconsistent with CP-1, CP-2A and CP-2D. Probe: `probe_cp2e_negative_denominator.py`.
- **Low → LEAD: the CP-2E floor limitation appears with a floor above zero.** `cp2e.py:1265-1268,1293`. `_LIM_FLOOR` reads "a floor of zero is treated as not binding", even when the floor is 25 bp.
- **Low → LEAD: an unruled CP-2E `fig()` raise.** `cp2e.py:1368-1378`. It fires when base coverage is known but coverage after the shock is n.m. (24 grid cases). Round 5 E7 appears to cover this; the follow-up must check.
- **Low, fixed: CP-2D L4.** Pinned by `test_first_missing_operand_in_formula_order_wins`. The mutant `mutant_cp2d_last_gap.py` is killed.

## Input fields vs manifest
- **CP-2D.**
  - `Facility.currency` and `.name` have no binding row. The T4.18 rows carry them (`financial_series.py:210-211`).
  - `_maturity_figure` raises "Unsupported facility currency" for a non-USD row (:243-244), so the non-USD path in 2D5 can't be reached through the reader. Stage 2 needs a direct row read or a ruling.
  - Four fields are bound but not read in Stage 1: `cfo_reported`, `debt_issuance`, `debt_repayment`, `fcf_unlevered`. They belong to T2E.9 in Stage 2.
- **CP-2A.** The metric map matches the selection rule. The manifest's "sign" text says magnitude, while the code follows A7; LEAD ruled the value is the same.
- **CP-2E.** `MacroFxInputs` covers the schema, and `source_names` comes from the pack.

## Boundaries
- No I/O.
- The spelling helpers are lease-named.
- No `src/deploy_vii` edit.
- No G1-X §2 clashes.

## Cross-group inconsistencies (report only)
1. Three Decimal-context conventions across the three modules.
2. Zero or negative divisors: CP-2E checks zero only; CP-2A and CP-2D check ≤ 0.
3. Digit guards use three methods: isnumeric, isdigit and `bare_figures`. Prohibited-conclusion guards use three mechanisms.
4. None of the three modules uses `financial_contracts.Number`. CP-2D accepts a minimum cash of 1E+30.

## Reviews
confidence-review and rewrite-tournament were run as manual passes, because neither skill can be invoked from this agent. The incumbents hold.

## Tests and gates
- **Tests:** cp2e 75 passed, 1 xfailed (strict, E4a); cp2d 101 passed; cp2a 86 passed, 1 skipped.
- **Gates:** ruff, ruff format and `mypy --strict`: exit 0 on all six files.

Not verified:
- real CP-1 head facts;
- the Stage 2 adapter for `Facility.currency` and `.name`, and the non-USD path;
- FY base periods for CP-2A;
- the E4a amendment;
- no skill invocations, and no heavy suite.

agent=mx-architect fix-rounds=0 gates-first-pass=y
