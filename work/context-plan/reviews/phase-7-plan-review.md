# Phase 7 (valuation) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-7-valuation.md` (draft, mx-feature, 326 lines).

## Controller rulings on the draft's open questions
- **Q1** `blend` weights the two medians equally, each set needing 3 admitted records.
- **Q2** the 12/36-month windows apply to explicit `public_comps` / `precedents` / `blend` too.
- **Q3** every CP-4C valuation case, the stress case included, carries the selected multiple (fail
  closed). Whether a free stress multiple is wanted goes to the user (final report).
- **Q4** a Phase 6 pin (`assumptions.cp4c.ev_multiple`) wins over the CP-1C selection; the selection is
  recorded in CP-4C's limitation, and a pin that differs from the selection is not an error. Phase 6's
  plan is told to state the same precedence.
- **Q5** `methods/cp1c.md` / `methods/cp4c.md` wording is outside B8 and B9: unchanged, listed for the
  user (final report).
- **Q6** per ruling B14: `bindings/cp1c.py` gets a D12 record in the repo-authored shape.
- **Q7** the unplaced CP-1C tabs in a distressed report are accepted (a new block is outside B8).
- From Phase 6's review: Phase 7 carries the RED "a context with a CP-4C pin and a differing submission is
  refused even when the CP-1C-offered multiple equals the submission".

## Review (mx-autonomous, read-only), 2026-11-01: verdict fix (1 High, 4 Medium)
Probes in `scratchpad/p7probe/`: oracle_recompute.py (exit 0: 7.00, 216.30, 8.25 …), plan_order.py,
cpos_pins.py (exit 1), frozen_cp1c_asserts.py (exit 1). Optional upstreams exist (CP-4C has CP-3C optional,
methodology.json:403-405; registry.py:65), so optional CP-1C is within B8.
- **H1** (:108-121, :267-268) CP-2 already lists CP-1C optional (methodology.json:160-165): with CP-1C in the
  distressed preset, CP-2, CP-4C and CP-5 bind it (execution.py:231-247); plan order changes (CP-2 after CP-2A
  and CP-4); CP-2/CP-4C inherit CP-1C limitations (:345-365); a blocked CP-1C restricts CP-4C (:484-489); no
  CP-1C head stops CP-2/CP-4C; CP-1C needs `period_coverage` (downstream_readiness.py:29). "behaves as today"
  (:113), "adds nothing" (:268) false.
- **M1** (:29-34, :168) contracts.py's hash pinned in cases/cpos-owner/manifest.json:15 and builder/build.py:34
  (asserted by `read_pinned`): re-pin in the same commit; docs/reuse/manifest.json:1277 (old D12 record) must not
  be rewritten. The stale cpos registry pin is O1 Task 1's (see o1-task1-review.md), not pre-existing.
- **M2** four unlisted test failures: tests/test_connect_cp1c.py:1409 (frozen `proposed_ids`, 8 tables),
  :1227-1234, :1248, :1389-1400 (lease D3: only cp1c.py calls `cp1c_reader`). Fix: name them; test frozen eight
  and new three separately; preparer amends the CP-1C and CP-4C leases.
- **M3** (:111-113) CP-4C rule refuses a multiple differing from the selection, contradicting Q4/Phase 6: skip
  when `pins_of("CP-4C")` is set; Task 0 file pin 8.5 vs selection 7.00 (8.50 accepted + limitation text).
- **M4** Task 0: v02/v03 multiples and EVs missing (Q3 binds every case); Done-when `case_kind private` variant
  (:295) absent; undated precedent (date optional) needs an "Excluded" reason and an oracle row.
- Lows: L1 only five tab tables unplaced (T1C.2, T1C.6, T1C.7 on rails, bindings/cp1c.py:41-45); L2 form
  `PATHWAYS` copy (context-form.html:467) needs CP-1C (and a test), :498 "or both" vs no automatic blend, :1082
  basis selection still Planned; L3 implied-EV decimals stated (210.0 vs 216.30), user NTM multiple × LTM EBITDA
  needs a gap/label, issuer EV ≤ 0 gap test; L4 sweep earlier context cases running CP-1C (`auto` default, :529).

## Controller rulings (2026-11-01)
- All findings accepted as proposed, with:
- **H1:** the consequences are part of B8 ("CP-1C in the distressed preset"): Design 12 states each one; a
  test pins the exact distressed plan tuple and the CP-2 and CP-4C input sets. CP-2's optional CP-1C edge is
  not edited (outside B8); whether to remove it goes to the user (final report).
- **M1:** the contracts.py/methodology.json re-pins include the cpos builder and manifest; the old D12 record
  stays as written.

## Re-review of rev 2: approve
- H1 (:120-128, test :199; tuple matches plan_order.py), M1 (:31), M2 (:203), M3 (:115, :171, :286; 30.90 × 8.50 =
  262.65), M4 (:61, :160, :163, :170; 18.54 × 7.00 = 129.78; 129.78 / 30.0 = 4.33; P6; `n_total` 6), L1-L4 fixed.
  Three new Lows (:277 → Design 12(c); :177 contracts.py re-pin; :170 no synthetic limitation) applied by the
  controller. **Phase 7 plan approved.**
