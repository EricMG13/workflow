# CP-L10 Financial change screen: method (LEAD adaptation)

Purpose (methodology.json): a bounded LITE screening synthesis for CP-1 (aliases CP-L20, CP-L23, CP-L30, CP-L40). CP-L10 screens ONE issuer for change between two quarters of one fiscal year, computed in Python from settled CP-1 T4.10 facts. The analyst chooses the pair of quarters and writes an assessment and a credit-transmission sentence for each topic Python rates Material or Watch, an overall judgment and gaps; the analyst writes no figure.

## Topics
Seven, in register order: EBITDA, free cash flow, cash, total debt, net debt, total leverage, interest coverage. Each points to the full owner it would upgrade to (EBITDA to CP-1D; free cash flow, cash, total debt and net debt to CP-2D; the two ratios to CP-2A).

## The rule (one rule for amounts and multiples)
For a topic with CP-1 starting value `a` and closing value `b`:
- change `= b - a` (signed); change on starting level `= (b - a) / abs(a)` (signed).
- **Material** when `abs(b - a) * 10 >= abs(a)`; otherwise **Watch** when `abs(b - a) * 20 >= abs(a)`; otherwise **Stable**.
- The rating is made on the EXACT value, never on the rounded quotient or the percentage shown: a change of 99/2000 shows 5.0% and is Stable. A value exactly on a threshold rates up (10 to 11 is Material, 20 to 21 is Watch).
- `a = 0`: change 0 is Stable; any other change is Material and the change on starting level is not applicable (never infinity, never 0).
- `a` or `b` missing in CP-1: **Not assessed**, evidence Missing, disposition Evidence needed; change and change on starting level are missing with CP-1's own limitation text. A missing value is never read as 0.
- Dispositions: Material, Upgrade to full module; Watch, Monitor; Stable, No action; Not assessed, Evidence needed.
- Priority rank 1 to 7: Material (a zero-base Material first), Watch, Not assessed, Stable; inside a class the larger absolute change on starting level first, then register order. Not assessed ranks above Stable because an unscreened topic needs attention before a screened-quiet one.

## Policy literals (D11)
The two thresholds (1/10 and 1/20 of the starting level), the single rule for every topic and the rank order are screening policy that no source states. They are literals of this method, recorded as such with an own limitation, never presented as sourced, and they are not covenant or credit tests.

## What is held or left out (each recorded as an own limitation)
1. **Thresholds** are screening rules, not covenant or credit tests.
2. **Two quarters only.** No trend, seasonality or annual comparison; the pack has no prior-year statements.
3. **Ratios** are compared only where CP-1 carries a known value for both quarters (CP-1 gives leverage and coverage a twelve-month basis only for the quarter that ends the year).
4. **Movement, not quality.** No recommendation, covenant, recovery or refinancing conclusion.
5. **Exact rating, rounded display.** The rating uses the exact change on the starting level; the percentage shown is rounded, so a shown value at a threshold can carry the lower rating.
6. **Small and negative bases.** A small starting level inflates the relative change; a negative starting level is measured on its absolute value. The rating reads the size of movement, not its economic meaning.
Also recorded: one "Not screened" line per topic CP-1 cannot supply, one line per analyst gap, and (settled) `Synthetic case; not real issuer qualification`.

## Tables
TL10.1 scope and sources, TL10.2 topic screen, TL10.3 screen items, TL10.4 upgrade triggers, TL10.5 screen totals (topic counts per materiality). Column labels are the field names in words (`change_pct` reads "Change pct"); Python composes every table and the analyst writes no figure. TL20, TL23, TL30 and TL40 of the same entry are not produced by this slice (LEAD Q3); a later slice or a methodology coverage check decides their fate.

## Review challenge
The independent review must challenge the thresholds and rank order as policy (Q1); the rule itself is exact and pinned by fixtures at 1/10, 1/20 and 99/2000.

## Recorded limits (Stage 2)
- **Substring match of prohibited words (L10-b).** The analyst text is refused when it contains `recommend`, `recovery` or `covenant` anywhere, as a substring of any word. An operating "Recovery" (for example "cash recovery in the quarter") is therefore refused. Word boundaries would not fix it and a phrase guard would change the pinned refusal r10, so the limit is accepted and stated here (LEAD ruling L10-b).
- **Exact change in plain form.** The stored change is one exact subtraction of CP-1 decimals, kept in plain notation: zero is `0` (never `-0` or `0E+2`) and a whole number has no positive exponent. A magnitude below one millionth still prints in scientific notation (the decimal text form); the rating always uses the exact value.
- **Consumption (D3) is open.** `cpl10_reader` exposes status, per topic id, materiality, evidence, disposition, rank and change, and the counts. No consumer core reads CP-L10, so no completion is claimed.

