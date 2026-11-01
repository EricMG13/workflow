# Phase 6 (pinned assumptions) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-6-pinned-assumptions.md` (draft, mx-feature, 225 lines).
B9 by the lease route: no `src/deploy_vii` change in Phase 6.

## Controller rulings on the draft's open questions (applied recommendations)
- **Q1** validators that return early (CP-2A base period, CP-3C stale) still append the pin issue, so a
  differing pin is never hidden behind another refusal.
- **Q2** CP-2D minimum cash keeps unlimited precision (its submission is not precision-limited); the
  reader still refuses a non-plain number.
- **Q3** `PINS_ENABLED` is keyed by module id.

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (1 High, 6 Medium)
Probes in `scratchpad/p6probe/`: pin_values_vs_positive.py, cp4c_equal_multiples.py, base_runs.py,
decimal_unvalidated.py.
- **H1** (:80-89) pins (primary-full.json) differ from the base positive submissions (CP-2A four scenarios
  0.20/0, 0.40/0, 0.40/0.20, 1.00/0; CP-2D 24/10; CP-2E hedge_absence; CP-3C 400; CP-3D 70; CP-4C 4.0/3.0/2.0, no
  frozen submission with equal multiples), so `match` cannot equal the base cell for cell; CP-0 must assess
  the new source (readiness.py:341-344). Fix: each pin at its base value (CP-2E hedge pin `""`); separate
  hedge-60 and CP-4C one-multiple match cases recomputed in the stdlib builder; state CP-0's context row and
  any limitation it adds.
- **M1** (:79, :181) four base pathways; context.py:761 compares pathway: one context-all per base run, Task 9
  names which.
- **M2** (:72-79) `context-*.json` outside PINS globs (cases/pins.py:20-30): embed sha256 in manifest.json.
- **M3** (:92, :97, :163) CP-4C line lacks a case index (`dict.fromkeys` merges): append `(valuation[i].multiple)`.
- **M4** (:43, :150, :161) T2E.7 and CP-3C's limitation table (T3D.8; cp3c.py:1542, :1738-1750) rows become
  facts (cp2d.py:1705-1711, :2435-2441; cp3c.py:2600-2615): append the row last; oracle lists new row/fact ids.
- **M5** (Q1, :147-149) pin check on submissions with content errors: plain `str` (cp2e.py:1751, :1775-1776;
  cp3d.py:130) → `Decimal()` raises: compare only after a NUM fullmatch, else emit the mismatch as typed; RED.
- **M6** (:177-179) `PIN_CHECKED` hand-kept: run each enabled module's ENTRY_VALIDATOR on the Task 0 `differs`
  case and assert its `assumptions.<m>.` line.
- Lows: `submission_form` type (:133) vs CP-2A list of dicts (:181): name body keys as submission paths; CP-2A
  line units (`pinned 0.2 (20%)`); composers raise on pin issues (`downside_report` cp2a.py:1586-1592 skips);
  PINNED_LINE grammar, blank-hedge item text; `clipped` from `deploy_vii.execution` (cp2a.py:60), import list
  :168; line drift (`number` :373; cp2e specs :618-620; repricing :624; blank import cp2a.py:70; bounds
  cp2e.py:542-543; `NOT_ASSESSED` :102; no `BASE_YEAR`, period constants cp4c.py:414-417); list the new case in
  "Left for Phase 7" (methodology re-pin); form list spec needs the strictly-increasing check.

## Controller rulings (2026-10-31)
- All findings accepted as proposed. Also from Phase 7's rulings (Q4): when `assumptions.cp4c.ev_multiple`
  is pinned, the pin wins over CP-1C's selected multiple; Phase 6 states that precedence where CP-4C's pin
  check is built (Phase 7 records the selection in CP-4C's limitation).

## Re-review of rev 2: fix (2 new Medium) → controller applied
- H1 (:86-91; pins hand-checked CP-2D 24/10, CP-3C 400, CP-3D 70), M1 (:80-84), M2 (:85), M3 (:98, :100), M4
  (:44-46, :174), M5 (:154), M6 (:190-192), precedence (:176, :223) fixed. New Mediums (probe
  `scratchpad/p6probe/strict_shape.py`, exit 0): `24.0` for an int is a strict-shape refusal (contracts.py:76),
  so the minimum cash is respelled `"10.0"`; CP-4C `multiple "abc"` is refused at shape before any pin check, so
  that case expects the shape issue only. Low: the offered-multiple RED moves to Phase 7. Applied by the
  controller, with the line drift (cp2e.py:543-544; cp4c.py:137 is correct). **Phase 6 plan approved.**
