# CP-2G fix round 1 report (controller-saved from the implementer's hand-back)

CP-2G fix round 1 is done. M1, M2 and L4 are fixed test-first, the M3 and L5 mutants are killed except V07 and S05, and all gates exit 0.

**Commits** (branch `worktree-agent-a4377a7580e8e70db`, worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db`)
- d296c34: merge of the lane tip `claude/module-dev-status-review-0981b6`.
- bb6f228: cherry-pick of 8483de4. 5d70287: cherry-pick of 3674158. Both applied cleanly, content unedited.
- b98109c: re-pin in my test.
- **dcfcbc0: the fix.**

**Pins** (each confirmed with `shasum -a 256`)
- CP-2G manifest: `b0c8c4bcdf3c0e00e33c41cc124d8ca86c47db14c82077c7d40504cc2bf6eee7`
- CP-2G submissions: `25a96ebb6c0a16fca291684407161d53a4b1ee48c5fa7963bcc59d4d7f3bc69e`
- CP-2G expected (unchanged): `97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c`
- **Re-pinned in my test:** `cases/cp2a-owner/expected.json` 457508a0… → `ad5531da7cff4eca8e9c8e9a23cef6526a982537597e6830610877bec994ff89`. It is the only pin my test asserts that moved, and it equals the builder's new pin.
- Unchanged: CP-1D expected `6015b443…bd8c` and financial manifest `6b3eeffe…32`.

**Findings and their tests** (`tests/test_method_cp2g.py`)
- **M1** `test_m1_cp1_figure_named_by_calculation_id`. It failed first because `claim.references` was `()`.
  - The fix adds `_named(text, bound)`, which resolves through the validator's own `prose.bind(ctx.prose_facts())`. That map is stored as `_Run.bound` and used by both `_references` and `Claim.references`.
- **M2** `test_m2_cp1_amount_must_be_usd_millions[thousands, EUR, scale]`. It failed first with "DID NOT RAISE".
  - `_usd_millions` raises a `ValueError` invariant when a selected known CP-1 amount is not USD MILLIONS at scale 1000000. Validation therefore fails closed. No user wording was added.
- **L4** `test_l4_unitless_unmapped_level_fails_closed`. It failed first with `KeyError: 'None'` at :1868. It now raises a `ValueError` naming `T2B.6.b01.level`.
- **M3**
  - A10: `test_m3_accessible_liquidity_adds_undrawn_revolver` (undrawn = 5).
  - A22: `test_m3_t2h2_check_differs_from_cp1[fcf, total, net]`.
  - A18: `test_m3_zero_leverage_change_is_flat`.
- **L5**
  - A13 and B13: `test_ratio_reason_is_the_numerator_first`. B14: `test_net_leverage_cause_follows_formula_order`.
  - B10: `test_g8_ebitda_cause_before_level_cause`. B15: `test_g8_level_cause_is_for_leverage_only`.
  - V03–V05: `test_probability_guard_every_phrase_any_case` over a literal copy of the lease list, plus `test_probability_phrases_are_the_lease_list`. My first version read the list from the module, so a dropped phrase dropped its own test; the literal list fixes that.
  - V06 and V11: `test_issue_order_within_a_driver_and_the_assessment`. V08: `test_whitespace_prose_is_empty`.
  - V12 and V13: `test_prose_paths_are_checked`. V09: `test_stale_input_compares_status_too`.
  - S01: `test_selection_ignores_other_tables`. R01: `test_g5_decline_named_before_increase`.
  - R04, R05b and R06: `test_own_line_order_round_6d`, which builds every kind of own line at once and checks the 6d order.
  - R07: `test_g9_cp1d_supported_not_known`, now with a non-LTM period.
  - A23: `test_amounts_are_canonical[all cases]`.
  - A26 also survived my first run. `test_g5_fy26_comparison_names_the_forecast_first` now kills it (gap case: unknown shock with CP-1D unbound).

**Probes**
- `p03_calc_id_reference.py`: exit 0.
- `p11_unit_currency_unchecked.py`: exit 1. `p10_g7_unitless_level.py`: exit 1.
  - Both now die on the new uncaught fail-closed `ValueError`. Their defect conditions (silent USD-millions composition, `KeyError`) no longer happen.
  - Through my wrapper `<S>/cp2g-r5/expect_valueerror.py`, which expects the `ValueError`: p11 exit 0, p10 exit 0.
- `p06_mutants.py`, run on a full copy at `<S>/cp2g-r5/mutcopy`: exit 0, survivors `['V07', 'S05']`.
- `p06b_mutants_followup.py`: exit 0. R05b, A28, A29, A30 and R19 are all killed.
- `<S>` is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

**Survivors left**
- **V07 (no de-duplication):** effectively equivalent. Every content issue carries a distinct path, index or row id, so only a CP-2A head with duplicate row ids could produce two identical issues. The brief did not list it.
- **S05:** equivalent, as the reviewer noted. The `Fact` validator forbids an amount on an unsettled fact.

**New strings**
- `<S>/cp2g-r5/probe_fix1_prose.py`: exit 1. The two new strings are the invariant `ValueError` messages, not user text.
  - The M2 message hits on `1000000` and `1000`.
  - The L4 message hits on `T2B.6.b01.level`.

**Gates** (all exit 0)
- pytest `tests/test_method_cp2g.py`: 213 passed.
- `ruff check`: 0 on the second run. The first run failed on one ISC004 in a new test, which I fixed.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict`: 0.

Not verified: the full suite and the other modules' tests after the merge and the two cherry-picks (only the CP-2G test ran); a full mutmut run (only the reviewer's 84 targeted mutants); Stage 2 binding against real heads; whether a real T4.10 book is ever non-USD or not in millions; L1, L2, L3 and the Info item, which stay with LEAD.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
