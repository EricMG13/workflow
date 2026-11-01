# Phase 8 (periods and currency) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-8-periods-currency.md` (draft, mx-feature, 342 lines).

## Controller rulings on the draft's open questions (applied recommendations)
- **Q1** year-bearing ids (`total_leverage_fy28` and the like) stay as stable keys; every label shown
  to a reader comes from the context's periods. Cost: an id names a year the run may not use; the
  label, never the id, is the period of record.
- **Q2** the oracle preparer proves whether CP-1 settles a EUR pack; if it does not, R3 becomes a
  named refusal case and the plan says so.
- **Q3** O6 prompt texts take periods from the `read_inputs` view, never from a constant.
- **Q4** `US$`/IFRS labels outside the Phase 8 modules stay out of scope (listed for the user in the
  final report); within the Phase 8 modules' rendered output, R3 (EUR) shows no `US$` (Done-when test).

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (2 High, 4 Medium)
Probes in `scratchpad/p8probe/` (exit 1 while the problem is present): `cp1b_usd_labels.py`,
`usd_tokens_unplanned.py`, `shift_years.py`.
- **H1** (:47-48, :331, R3) CP-1B row labels ("Revenue (US$ m)" …) are pinned in `bindings/cp1b.py:32-49` and
  checked by `report_view.py:2353-2356`: EUR either refuses CP-1B or breaks Done-when 7. No vii change is
  approved for bindings.
- **H2** (:287-289) CP-2E has no CP-1 input (cp2e.py:1819; frozen case CP-0 then CP-2E): `period_basis(context,
  cp1_facts)` finds no T4.14 rows. Fix: CP-2E's own basis (base year from `run.current_period`, window from
  its `FY YYYY` header :541), refuse on disagreement, RED test.
- **M3** (:154-156 vs :123) every q1-q3/h base refuses everywhere, contradicting R5 and Phase 2's q3 runs.
  Fix: a currency-only check for any base (CP-2A, CP-L10, CP-1B); the forecast/LTM-Q4 basis fy/q4-only
  (CP-2G, CP-2H, CP-4C); extend R5.
- **M4** 33 unplanned "US$ m" sites (cp2a.py:1329-1331; cp2d.py:826, 836, 1289, 1334, 1414, 1445, 1516-1529;
  cp2g.py:2325-2353; cp3c.py:1324-1332, 1491-1504; cp4c.py:2296-2297; cpl10.py:138-142); `{id|US$ m}` fails
  closed under EUR (prose.py:298); `earnings.py:187` USD; `owners/cp1b.py` missing from Task 7 Files;
  `build_earnings_delta` calls earnings_workflow.py:1278, 2020, 2525 outside scope. Fix: `basis.money_unit` at
  every site; one EUR RED per module.
- **M5** (:146-147, :175-177) `t46_period`, `schedule_period`, `_bind46` suffix from the matched CP-1
  `period_id` (statement_view.py:80, 90; cp2d.py:2020); RED with id `Q4-FY26`.
- **M6** (:79-107) oracle inputs miss dated sources `business` (cases/snapshot), `legal-covenants`
  (cases/legal), the CP-2H `ratings` source, and oracles cp2h-owner, cp2e-owner, cpl10-owner, cases/earnings;
  one simultaneous year shift; builder recomputes sha256 from shifted bytes (only 2024 date is 2024-12-31).
- Lows: cp1c.py `_inputs` :1600, `_stale_issues` :1615, basis comment :101-102; Task 7 sweep adds
  earnings_workflow.py:1652, 1899, 1923; Task 6 names cp4c.py:1495; Task 8 also runs test_connect_cp1c.py,
  test_connect_cp3c.py, test_connect_cp4c.py, test_method_cp2h.py.

## Controller rulings (2026-10-31)
- H2, M3-M6 and Lows accepted as proposed.
- **H1:** no bindings change (outside B9). Until the user rules, CP-1B on a context whose
  `reporting_currency` is not USD refuses with a named refusal (`cp1b_currency_label_fixed`: "CP-1B's row
  labels are fixed in US$ (bindings/cp1b.py); a non-USD run needs a labels change"), never a false label.
  R3 asserts that refusal; Done-when 7 covers the other Phase 8 modules. The bindings/cp1b.py and
  report_view.py label-check change goes to the user (final report).

## Re-review of rev 2: fix (M5 reversed) → controller applied
- H1 (:123-126, :316-322, :353, :358), H2 (:121, :309-314, :325-326), M3 (:162-170, :132, :199, :357), M4 (:250,
  :272, :291, :302-328, :358), M6 (:80, :99-102) fixed. M5 was reversed (strings rebuilt from the year; a head
  with id `Q4-FY26` matches no T4.6 fact). Applied by the controller: match the Q4 row by dates, then use its
  `period_id`; both RED tests expect `Q4-FY26`.
- Confirmation: `t46_period` is the T4.6 period form `"{period_id} · {start} to {end}"` (statement_view.py:90);
  applied. `schedule_period` and the `_bind46` suffix bare `Q4-FY26` confirmed. **Phase 8 plan approved.**
