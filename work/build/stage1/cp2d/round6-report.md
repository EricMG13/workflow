# CP-2D round 6 and 6f report (controller-saved from the implementer's hand-back)

CP-2D round 6 (A1, A5) and round 6f are committed as **3e099de** on `worktree-agent-a69f2394899aee6d5`. 136 tests pass and all three gates exit 0. One fix follows LEAD's (e) text literally and needs a check: in the drawings-undisclosed case, the liquidity-to-debt cell now reads `Undrawn revolver not calculable: drawings undisclosed`.

**Step 0.** Done in order: merge bdad3c8, cherry-pick 8483de4 (now 4e82ef1), cherry-pick 3674158 (now 4e3af50). For CP-2D the oracle batch changes only the `months_between` description text and the lease header pins. My test pins no hashes and does not read that text, so nothing needed re-pinning; all 124 existing tests passed straight after the picks.

**Rulings and their tests** (tests written first; red observed for the right cause)
- **A1:** `months_between` is now the largest n with `add_months(D0, n) <= maturity`. Inside-horizon is unchanged.
  - `test_a1_months_is_the_largest_n_on_or_before_maturity`: 2027-06-30 gives 18, 2028-06-30 gives 30, 2027-06-29 gives 17. The four frozen maturities keep 24, 31, 48 and 60.
  - `test_a1_months_and_inside_horizon_agree_at_a_month_end`: H=17 is outside, H=18 is inside.
  - `test_a1_property_months_bound_the_horizon_test` (hypothesis, 500 examples): checks `add_months(D0, m) <= maturity < add_months(D0, m+1)`, and that months below H means inside, above H means outside. With plain random dates it passed even under the old rule, because those rarely hit month ends. I biased the dates toward month-end days; it then failed on the old rule and passes on the new one.
- **A5:** no code path changes in Stage 1, because cp2d.py has no T4.18 reader and never references `_maturity_figure`. The `Facility` docstring now records the binding: `currency` and `name` come from the row's own `currency` and `facility_name` text facts, from the same row (by `facility_id`) as the bound principal, never through `_maturity_figure`. The non-USD path through `compute` is already covered by the 2D5 and D-2 EUR tests. Building the reader is a Stage 2 obligation.
- **6f (d):** new MAT_CURRENCY: `… [T2E.3.r07] needs every facility with its currency stated, and one is not; no FX conversion is applied.` MAT_FX is kept only for a stated non-USD currency. The first facility in wall order with a currency problem decides which one applies, per reading (c). Tests: `test_6f_d_unstated_currency_takes_the_currency_frame_on_mat01`, `test_6f_d_stated_foreign_currency_keeps_mat_fx`.
- **6f (e):** RUNWAY_NO_DRAWINGS already equals the L1 string `Not calculable: revolver drawings undisclosed`, and the T2E.5.r03 resources cell carries it. REV_RATIO (`Not calculable: available liquidity missing`) was being reused for the drawings-case ratio. That is not an L1 string, so it was a defect. The ratio T2E.2.r09 now carries `Undrawn revolver not calculable: drawings undisclosed`, following the ruling text's pairing of names and strings. REV_RATIO stays for the undisclosed revolver, where the oracle pins it. Test: `test_6f_e_drawings_case_carries_only_the_l1_strings`.
  - **For LEAD:** the 2D-b first-missing rule would instead give `Available liquidity not calculable: revolver drawings undisclosed`, also an L1 string. Please confirm which one the ratio should carry.
- **6f items 1, 2(a)(b)(c)(f) and 3:** accepted as built; no change.

**Probes** (in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/`)
- **`stage1-review-A/probe_cp2d_month_asymmetry.py`:** exit 0 before the fix, exit 1 after. That is the expected change: the probe exits 0 only while the asymmetry reproduces. It now shows 18 months, outside H=17 and inside H=18.
- **`mutate_r6.py`:** this is `mutate_r5.py` run from a full copy of the worktree (all of it except `.git` and caches), plus three round 6 mutants. Exit 0, 42 of 42 killed, no skips. The new mutants are:
  - the old A1 month rule;
  - 6f (d) reverted to MAT_FX for an unstated currency;
  - 6f (e) reverted to REV_RATIO.
- **`mutate_r5.py`** unchanged (partial copy): exit 0, 39 of 39 killed.
- **Other re-runs on the round 6 source:**
  - `probes/r5_probe1.py`, `r5_probe2.py`, `r5_probe3.py`: exit 0 each;
  - `probes/r5_probe_sweep.py`: exit 0 (6000 valid inputs, 0 raised);
  - `r5_confidence.py`: exit 0;
  - `r5_prose.py`: exit 1, only from the 6 non-claim hits accepted under 6f item 3; claims have 0 hits.

**Gates:** `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files exit 0 on the first run. pytest on `tests/test_method_cp2d.py` gives 136 passed.

**Prose and bare-figure hits:** 0 in claim templates; MAT_CURRENCY passes `prose.check` with no issues. `bare_figures` on the new ratio reason finds nothing. The 6 hits outside claims are the same as round 5 and accepted by 6f item 3.

**Stage 2 notes (listed, not written)**
- `methods/cp2d.md`: the D-6 guard limit.
- **A5 reader:** build `Facility.currency` and `.name` from the T4.18 row's `currency` and `facility_name` text facts, without `_maturity_figure`, so 2D5 can be reached.
- Fill `maturity_date_refs` from the view.
- **A1 for CP-3C:** it is ruled to use the same month function, but nothing in this worktree imports `cp2d.months_between`. The CP-3C lane must adopt it itself.

**Confidence review:** no new bug.
- Before maturities and arbitrary date order are covered by the property test.
- The drawings ratio override fires only when available liquidity's reason is the drawings one; with cash also missing, the cash reason still wins.
- `months_between` has no other consumer.

Not verified: no real CP-1 head, T4.18 row facts or Stage 2 reader (the test still uses literal `name="Northbridge Term Loan"` and `currency="USD"`, because the oracle source facts carry neither); A1's effect on CP-3C; L4 "shows both" through T2E.9 (Stage 2); the optional D-6 builder sync. Only `tests/test_method_cp2d.py` was run, as the brief allows.

Diff for this round: cp2d.py +24/−7, tests +78/−0. One scoped review covers b8a5751 together with 3e099de, as the coordinator set.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
