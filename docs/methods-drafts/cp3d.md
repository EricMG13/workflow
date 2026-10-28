# CP-3D market-implied risk: method record (DRAFT rev 2, 2026-10-28; becomes `methods/cp3d.md` at freeze, D12)

Python owns every number here (Decimal, 28 digits, ROUND_HALF_EVEN for division and exp; stored values quantised ROUND_HALF_UP and never fed to a later step). The analyst supplies only quoted numerals (validated by containment in a verbatim quote) and one uncited assumption (the recovery rate, D11). The worked values are `expected.json#cases.positive.derived`; the build is `cases/cp3d-owner/builder/build.py`.

## Inputs

Bid, offer and indicative talk (percent of par) from the market sheet; the quotation date; the final maturity date; the contractual margin (bp) and a zero mandatory amortisation from financial page:5; optionally a quoted reference rate level; optionally the recovery rate. A missing operand makes each dependent value missing with a stated reason; nothing defaults to 0.

## Price metrics

Levels are stored as fractions of par (98.50 is 0.985). Mid = (bid + offer) / 2 = 98.875. Width = offer - bid = 0.75 points. Discount to par at mid = 100 - mid = 1.125 points. Talk less mid (99.75 - 98.875 = 0.875 points) is context only.

## Day count: Act/365 Fixed, unrounded years

Days = final maturity date - quotation date = 2029-12-31 minus 2026-01-09 = 1452. Years = days / 365 = 3.97808219... The stored and displayed value is 3.98 (two places). **Every later step uses the unrounded 3.97808219..., not 3.98.** Using 3.98 would move the offer margin from 18.9 bp to 18.8 bp. The T3E.2 convention text and formula say so.

## Simple discount margin (the convention)

- Annualised discount (bp) = (100 - price) / years x 100. Bid 37.7066, mid 28.2800, offer 18.8533 (stored 37.7, 28.3, 18.9).
- Simple discount margin (bp) = cited contractual margin + annualised discount. The margin is 0 bp ("spread 0 basis points", financial page:5), so the margin equals the discount.
- This is the discounted-spread form used in the loan market: margin + (100 - price) / years. It is **not divided by price** (dividing by the price gives 38.3, 28.6 and 19.0 bp at bid, mid and offer) and it is **not the market's three-year-life convention** (which assumes a three-year life; this method uses the remaining life to final maturity, which is stated and fine).
- Redemption at par at final maturity; the cited amortisation must be zero ("Mandatory annual amortisation is 0"); the quotation date stands for the settlement date (a settlement lag of about a week is ignored as negligible); a floor on the reference rate does not enter a margin.
- It is not a Z-spread and uses no benchmark curve.

## All-in yield

Reference rate level + simple discount margin / 10000. No frozen source states a level, so the yield is Not calculable in every pack case (shown `∅ G#`, never 0). The pure function is exercised with a test vector (4.30 percent) in `fixture_with_benchmark`, not as a source figure.

## Recovery assumption (D11)

The recovery rate is an uncited analyst literal: **70 percent**, rationale "first-lien loan CDS convention". The frozen financial page:5 states "It is a senior secured term loan"; the 70 percent figure is the convention for first-lien loan credit default swaps. The senior-unsecured CDS convention would be 40 percent. **The convention is the analyst's knowledge: no source in the pack states it and it is not verified against a source.** It is stored as an `analyst_judgment` fact with no citation or calculation id, so no claim may state it as a figure.

Direction: a higher recovery raises the implied intensity and default probability for the same margin (intensity = margin / (1 - recovery)). At 40 percent the mid margin gives 47.1 bp and 1.86 percent; at 70 percent it gives 94.3 bp and 3.68 percent.

## Market-implied default (credit triangle)

- Annual default intensity (bp) = simple discount margin / (1 - recovery), from the unrounded margin. Bid 125.6887, mid 94.2665, offer 62.8444 (stored 125.7, 94.3, 62.8).
- Cumulative default probability to final maturity = 1 - exp(-(intensity / 10000) x years), unrounded intensity and years. Bid 0.048771, mid 0.036806, offer 0.024690 (stored 0.0488, 0.0368, 0.0247; shown 4.88, 3.68, 2.47 percent).
- A simple discount margin <= 0 gives `not_applicable` for both measures (shown `∅ G# n.m.`), never 0. Recovery must satisfy 0 <= x < 100.
- Risk-neutral: the whole spread is attributed to default risk with a constant intensity, so the measures overstate the default component if a liquidity premium is present.

## What this method does not do

No benchmark curve, no fundamentals comparison (the alignment half of the FP03 block is not populated), no Z-spread, no recommendation. Indicative talk enters no figure; its period is the commentary publication date (2026-01-10).

## Limitations recorded by the method (T3E.9)

Single dealer quotation; the rating gap; talk not used; reference rate level absent; recovery is an analyst assumption following the first-lien loan CDS convention, convention not verified against a source; direction of recovery; simple margin convention (not a Z-spread; not divided by price; not the three-year-life convention); risk-neutral attribution; margin and amortisation read from the financial page; alignment half not shown; an absence backed only by a search over some source.
