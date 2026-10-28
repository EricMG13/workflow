# CP-3C questions (AGENTS.md: one file per module)

## Decided by the controller (module-only)
- Q1 (review M1): a facility maturing before D0 fails closed as a ValueError invariant in `_facility` until LEAD rules (fix 1, 8a45037).
- Q2 (review M2): facility ids pass to `prose.check(names=…)`; Stage 2 MC-2 passes the same names.
- Q3 (review L2): compute at the builder's prec 60; no frozen value moved.

## For LEAD (one batch; sent 2026-10-28 as items 1-4 of the Modules message)
- B1. Pre-D0 maturity: a raise, or a gap with wording?
- B2. 8-B3 scope: own line for an unstated amortisation or ranking term (CP-2D writes one for amortisation).
- B3. Empty CP-1 register with a non-empty wall: "not in the CP-1 debt register" or C-6 NO_FACILITY?
- B4. BURDEN-01 precedence when EBITDA ≤ 0 and the payable is missing.
- B5. A whitespace-only limitation passes (CP-2H B3 is the same case).
- B6. Negative principal or amortisation in the B6 state (Method and builder behave the same).
