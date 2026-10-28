# CP-2G rulings round 5 report (controller-saved)

- **Commit:** `34ea23b` on `worktree-agent-a4377a7580e8e70db`. The two commits below it:
  - 769b740, a merge of f02637c;
  - 8a3e144, a cherry-pick of 2ae589b. The CP-2H and CP-4C files were absent on this base (modify/delete), so the cherry-pick carries the CP-1D and CP-2G files only. The lane already has the full 2ae589b.
- **Pins:** the test asserts the CP-1D expected sha 6015b443…. The CP-2G manifest is now 1c36928c…, which the test does not assert.
- **Tests:** 174 passed. 28 of the 30 new tests failed first on the cited raises.
- **Gates:** ruff check, ruff format --check and `mypy --strict` all exit 0.

## Rulings and their tests
All in `tests/test_method_cp2g.py`:

| Ruling | Tests |
|---|---|
| G-1 | `test_g1_missing_operand_words[...]`, `test_g1_unverified_cause_words[...]` |
| G-2 | `test_g2_single_first_test_claim` |
| G-3 | `test_g3_fy28_known_peak_not_calculated`; `test_g3_peak_known_fy28_not_calculated` (the template only, since compute cannot reach that state) |
| G-4 | `test_g4_margin_on_non_positive_revenue` |
| G-5 | `test_g5_unknown_cp2a_shock[...]` |
| G-6 | `test_g6_bound_cp2d` |
| G-7 | `test_g7_other_definition_wording_settles` |
| G-8 | `test_g8_non_positive_base_ebitda[...]`, `test_g8_non_positive_cp2a_level[...]` |
| G-9 | `test_g9_cp1d_supported_not_known[...]`, `test_g9_cp1d_supported_other_period`, `test_g9_cp1d_leverage_not_known_uses_chip` |
| G-decisions | `test_g_decisions_unknown_cp2a_copy_keeps_status` |

## Choices
**Confirmed by the controller:**
1. G-5 is read literally: every d26–d28 downside cell is missing, but the `T2H.8.down.downstream` label stays known.
2. G-6: the T2H.1 `u_cp2d` status shows the bound status.
3. G-7: the level copy takes its unit from CP-2A's level fact.
4. 6: `ebitda_fy26_vs_supported` takes the first missing operand in formula order.

**Sent to LEAD:**
- G-7: an analyst-named metric on an unmapped Definition row returns "… is a definition break with a fixed metric".
- G-8: level ≤ 0 counts only for the leverage kinds, and the net-debt guard has been removed from `break_decline`.
- G-9: the `<T1D label>` taken verbatim stutters: "CP-1D supported Supported adjusted EBITDA".
- The order of the own lines is not pinned.

## Probes (scratchpad `cp2g-r5/`)
- `probe_r5_prose.py` exits 1: 35 of 73 new strings hit. Every hit is in a cell limitation or an own line, on the period label `25` or a row id (b01, b03–b05, s03). The pinned frames hit the same way.
- `probe_r5_pinned.py` exits 0.

## Builder syncs (optional, LEAD)
- unknown CP-2A copies;
- the G-7 settle path;
- the G-9 copy period.

## Stage 2 notes (`methods/cp2g.md`)
- the G-1 to G-9 wordings and the own-line order;
- `stale_issues` returned alone;
- the T2H.1 CP-1D basis comes from the CP-1D head;
- the bound CP-2D Input;
- the 1D1 re-pin.

Not verified:
- the full suite;
- Stage 2 binding;
- the choices still with LEAD;
- collisions with other modules' pinned cells.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
