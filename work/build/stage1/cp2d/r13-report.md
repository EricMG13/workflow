CP-2D round 13 report (R1 M1 and R1 M3). All gates exit 0. The one deviation from the ruled wording is item 1's balance-date fallback when a tagged cell has no CP-1 fact (see Not verified).

**Commit:** `7f2a9a2` on `claude/r13-cp2d` (cut at d2cb626). It touches only `src/deploy_workflow/owners/cp2d.py` and `tests/test_method_cp2d.py`. No `cases/`, lease or `methods/` file was edited. Step 0 passed (worktree clean, HEAD d2cb626).

**Ruling clauses and their tests** (all in `tests/test_method_cp2d.py`)
- **Copy keeps CP-1's period verbatim:** `test_r13_m1_a_copy_keeps_the_cp1_period_verbatim` and `test_r13_m1_a_facility_principal_keeps_the_facility_period`.
- **Sum or difference takes the shared period, or raises:** `test_r13_m1_a_sum_takes_the_one_period_its_operands_share`, `..._a_sum_of_differing_periods_raises_the_invariant` (T2E.1.r05) and `..._a_difference_of_differing_facility_periods_raises_the_invariant` (T2E.2.r06). The message is `CP-2D: operands of <fact_id> differ in period`.
- **Any other known numeric fact gets the balance date:** the oracle comparison in `_assert_cell`, plus the copy test's check that a computed cell takes `_BALANCE`.
- **A gap, not_applicable or text cell carries no period:** `test_r13_m1_gap_not_applicable_and_text_cells_carry_no_period`.
- **Every cell has a `value_class`; a gap takes its twin's class and a copied gap keeps `cp1_operand` and `cp1_unit`:** `..._every_cell_carries_a_value_class_and_a_gap_takes_its_twins` (five variants against the positive case) and `..._a_copied_gap_keeps_cp1_operand_and_cp1_unit`.
- **`Operand(status, amount, period, limitation)` shape:** `test_r13_m3_operand_shape_is_status_amount_period_limitation`. I added a `__post_init__` invariant (known needs amount and period; other statuses need a limitation and no amount).
- **A copy keeps CP-1's status with its limitation verbatim:** `test_r13_m3_a_copy_keeps_the_cp1_status_with_its_limitation`, for missing, conflicting and not_applicable. Conflicting spells `∅ G<n>` and not_applicable spells `∅ G<n> n.m.`.
- **Dependants stay `gap` with the ruled reasons:** `test_r13_m3_dependants_stay_gaps_with_the_state_word`.
- **GAP_OPERAND wording:** `test_r13_m3_gap_operand_claim_names_the_status`. It is worded exactly as ruled and also passes `prose.check`.
- **First gap in formula order:** `test_r13_m3_the_first_gap_in_formula_order_names_the_claim`.
- **A non-known operand is never read as zero:** `test_r13_m3_a_non_known_operand_is_never_read_as_zero`.
- `_op` and `_gap_missing` keep their positions.

**Frozen oracle:** `cases/` is untouched.
- **Delta tables:** `_assert_cell` compares everything exactly as before and applies the delta as two named tables, `PERIOD_DELTA` and `GAP_VALUE_CLASS_DELTA`. The gap table holds the 5 gap `value_class` keys; the period table covers the 110 known numeric cells.
- **Manifest cross-check:** `test_period_delta_names_the_manifest_periods` checks the period strings against the manifest.
- **Re-pin guard:** `test_frozen_oracle_still_lacks_the_round13_delta` (name and docstring say "remove the delta at the Stage 2 re-pin") fails once `expected.json` gains the keys.
- **CP-3C:** its tests read CP-2D's frozen `expected.json`, not CP-2D code. The 6 principal-copy `q4-2025` periods remain part of the same Stage 2 delta.

**Red first**
- With the delta in `_assert_cell` and the old code, `test_tables_equal_oracle` failed 3 of 3 (`'Cell' object has no attribute 'period'`).
- Probe A on the old code listed the 5 gap cells with no class, and the p4 probe reproduced M3 (exit 0).
- The item 3 tests fail at collection with `AttributeError: no attribute 'Operand'`. That is the ruled type change itself, so this red is weaker than the others.

**Mutants:** `<S>/cp2d-r13/mutants.py`, exit 0. All 19 are killed, one or more per clause: copy period, shared sum, raise, raise wording, balance default, months period, gap class, copied-gap cp1 keys, conflicting and not_applicable states, verbatim limitation, state words, claim word, formula order, spelling, T4.10 period, facility periods, operand invariant and missing-status limitation.

**Probes** (in `<S>/cp2d-r13/`, LANE pointed at the worktree)
- `p13_cp2d_period_class.py` exits 1 only on its own part A ("M1 does not reproduce"), which assumes pre-change code. Its part D now reports `period on 110 known numeric cells`, and part C reports the same 6 CP-3C moves.
- `p13_status_prose.py` exits 1 because its part A re-runs R1 p1/p3/p4 and expects them to reproduce. Parts B and C (the prose check) pass.
- `p1_cp2d_to_cp3c_seam.py` exits 1. Its `fact()` builder never copies `Cell.period`, so its ValueError comes from the probe, not from CP-2D.
- `p4_cp2d_status_collapse.py` still exits 0. Its check, "Operands has no status field", is stale for the new shape; `cfo=None` still reads as missing with the unchanged reason.

**Gates:** all exit 0.
- pytest: `tests/test_method_cp2d.py` and `tests/test_defect_classes_selfcheck.py`, 502 passed.
- `ruff check`.
- `ruff format --check`.
- `MYPYPATH=src mypy --strict` on both files.

**Design choices to confirm**
- **Operand fields:** all 21 Operands fields became `Operand | None`, including the T4.10 metrics. `None` means no fact offered and reads as missing with the unchanged reason.
- **`Facility.period`:** I added a required `Facility.period` so the T4.18 cells can keep their CP-1 period.
- **Tagged recomputed cells:** the `undrawn_rcf`, `liquidity` and `liquidity_to_debt` cells (and T4.18 commitment less drawn) keep the CP-1 metric's period, as probe part D does.
- **Missing-status copy:** it takes CP-1's limitation verbatim as its reason. An undisclosed revolver (`None` or missing status) keeps the oracle-pinned `REV_*` texts.
- **Extra `Cell` field:** `Cell` gained `differing_periods`, used only so `_number` can raise with the fact id. It is always empty on a returned cell.

Not verified:
- The full suite, jscpd, complexipy and the other gates were not run (round-13 module gates only).
- Wording for a conflicting or not_applicable revolver commitment or drawings (T2E.2.r05, T2E.2.r07, the LIQ-01 and GAP-01 undisclosed-revolver claims, the runway reason) is untouched. Those paths still say "undisclosed", which is wrong for a conflicting revolver. The ruling words only GAP_OPERAND.
- A tagged recomputed cell whose CP-1 fact is absent or not known (for example T4.10 `undrawn_rcf` is `None`) takes the balance date, since it is not a copy. The ruling does not say what happens here.
- A real promoted CP-1 head with conflicting or not_applicable facts, and the Stage 2 adapter that builds `Operand`, were not exercised. Neither exists yet.
- The Stage 2 re-pin of `expected.json`, the CP-3C manifest and lease :104/:146 text were not touched (the controller owns them).

agent=mx-feature fix-rounds=0 gates-first-pass=y