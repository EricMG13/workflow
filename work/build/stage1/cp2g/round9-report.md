CP-2G round 9: all rulings are applied and every ruling's revert is killed.

**Commits** (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db`, branch `worktree-agent-a4377a7580e8e70db`)
- Step 0 merge `4a6daef`: `git merge claude/module-dev-status-review-0981b6` from lane tip 7fdddbf. It merged with no conflicts, including the `docs/CP4C-OWNER-LEASE.md` header. Round 10 needs no change in CP-2G.
- Round 9 commit `947a57d`. It touches only `src/deploy_workflow/owners/cp2g.py` and `tests/test_method_cp2g.py`.
- Test-first: I saw the new tests red before the fix. 11 failed on the old behaviour; the L1 tests passed without a code change, as the ruling expected.

**Rulings and tests** (`tests/test_method_cp2g.py`)
- **M2 wording:** `test_m2_cp1_amount_must_be_usd_millions`.
  - The message is now `CP-2G: CP-1 <metric> must be USD MILLIONS at scale 1000000, not <currency> <unit> at scale <scale>`.
  - The test checks it from both `payload_issues` and composition, for four books: THOUSANDS/1000, EUR, scale 1000, and currency None.
- **L1:** `test_l1_minimum_liquidity_cause_before_g5` and `test_l1_g7_and_unknown_level_causes_before_g5`.
  - Under G-5, the d26–d28 headroom and `m01.down_first` keep the "minimum liquidity not assessed" reason.
  - b01 keeps G-7, b03 keeps "Level not stated", and b04 carries G-5.
  - The code already did this, so these are tests only.
- **L2:** `test_l2_non_ltm_cp1d_total_leverage_claim`.
  - When CP-1D's supported total leverage is known but for a period other than LTM, `T2H.2.cp1d` says it is for another period and gives the reported total leverage.
  - A second variant has total debt missing (chip).
- **L3:** `test_l3_no_test_calculable_claim`.
  - When no test is calculable, `_first_claim` says no tested break point is calculable through FY2028 and chips the first test.
  - Cases: downside under G-5, and base with gap revenue missing.
- **Info:** `test_info_more_than_38_digits_fails_closed`.
  - Only `decimal.Inexact` is caught, and it raises `ValueError("CP-2G: <operation> needs more than 38 significant digits")`.
  - The base forecast is tested through compute; the downside forecast through `forecast()` directly.
- **`T2H.1.u_cp1d.basis`:** `test_t2h1_cp1d_basis_is_the_first_known_fact_period`.
  - The basis is "Base period <period>" from the first known CP-1D fact, otherwise "Not applicable".
  - Four parametrizations: supported FY2025; supported missing gives LTM; first two missing gives net FY2024; all missing gives "Not applicable".
- **T2H.9 gap texts:** `test_t2h9_gap_texts_spell_references`.
  - The gap, why-it-matters, affected-analysis and action cells, and the own `Gap (<severity>): …` line, are spelled as rendered: each known figure reference is replaced with `business_context.spelled(fact)`.
  - A reference that is not a known upstream figure raises `ValueError("CP-2G: stored text reference <text> does not name a known upstream figure")`.

**Probes**

All are under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-r9/` unless a full path is given. Mutants ran only on the full copy `…/cp2g-r9/copy`, with `PYTHONDONTWRITEBYTECODE=1`.

| Probe | Exit | Result |
| :--- | :--- | :--- |
| `p_r9_strings.py` | 0 | 345 M2 variants, 0 mismatches; L2 and L3 claims clean under `prose.issues` |
| `p_r9_mutants.py` | 0 | All 13 ruling reverts killed (list below) |
| `p06_mutants.py` (copy) | 0 | Survivors V07 and S05, as in earlier rounds |
| `p06b_mutants_followup.py` (copy) | 0 | All killed |
| `p_fix2_citation_mutants.py` (copy) | 0 | All killed |
| `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-fix-review/q02_m2_book_units.py` (re-review probe) | 0 | 672 variants, 0 bad |

The 13 reverts killed by `p_r9_mutants.py`:
- N01: M2 old wording.
- N02 and N03: L1 order.
- N04: L2 branch.
- N05: L3 branch.
- N06: Info catch.
- N07: Info names swapped.
- N08: basis hard-coded to LTM.
- N09: basis taken from the last known fact.
- N10: basis fallback to LTM.
- N11, N12 and N13: raw gap cells, action and own line.

**Gates:** all exit 0 on both files, first pass. pytest gave 233 passed. `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` are clean.

**Prose and bare-figure hits:** none in claims. Non-claim strings have these `bare_figures` hits, which I did not reword:
- Basis text "Base period LTM Q4 25…": `25`.
- M2 message: `1000000`.
- Info messages: `38`.

The `_spelled` message and "Not applicable" are clean.

**Flags for LEAD**
1. The ruling's "that row's fallback" for `u_cp1d.basis` is ambiguous. I used the row's existing "Not applicable".
2. Info operation names and where they apply:
   - "the base case forecast" and "the downside case forecast" (around `forecast()`);
   - "the FY2025 cash flow" (`_a25`);
   - "the historical-to-base bridge" (T2H.2), "the credit metrics" (T2H.6) and "the deleveraging path" (T2H.8), around those composers.

   Only the forecast names, plus the revert that removes the catch, are tested. The three composer wraps are not tested one by one.
3. The `_spelled` invariant message is my own wording, since the ruling does not give one.

**Stage 2 notes**
- Gap own-line order is unchanged.
- The basis rule is "the first known CP-1D fact's period".
- The G-5 text is the amended text from round 9.

**Not verified:**
- The 38-digit fail-closed on the T2H.2, T2H.6 and T2H.8 composer wraps and on `_a25`, case by case. Only the forecast paths are tested.
- The rendered output end to end beyond the method tests (Stage 2).
- Whether the "Not applicable" fallback is the reading LEAD intended.

`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
