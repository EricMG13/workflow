<!-- DRAFT for a future src/deploy_vii/methods/cp1c.md; recorded here, not installed (pre-code; LEAD ruling, review-precise-1, 2026-10-28). -->
# CP-1C — peer benchmark: metric set, thresholds and recorded omissions

Method basis: `methodology.json` CP-1C "Peer benchmark" ("benchmarks the issuer against a defined peer universe and flags outliers"; required CP-0, CP-1, no optional edge). The r14 CP-1C SKILL.md is not in this repository, so the metrics, thresholds and omissions below are a LEAD-accepted adaptation (rulings 2-4, 6, 7, 15), not a transcription. Execution split (`owner-harness-architecture.md:59`): Python owns normalised peer metrics, medians, positions and outlier flags; the analyst owns the universe and comparability judgments; the rendered section is FP03 `peer-positioning`.

## What the module does

- Four metrics, aligned to CP-1 T4.10 (LTM Q4 25): adjusted EBITDA margin (EBITDA / revenue), total leverage (total debt / EBITDA), interest coverage (EBITDA / interest expense), FFO to total debt (FFO / total debt). One division of exact decimals each, 38 digits half-even. The issuer's values are copies of the CP-1 cells.
- Universe: the analyst assesses each peer on the peer summary Comparable, Partly comparable (mandatory limitation) or Not comparable. Comparable and Partly comparable are included; Not comparable is shown, normalised and kept out of every statistic.
- Statistics (over included peers with a calculated value, at least three, otherwise the statistic is missing and never 0): median (odd: middle value; even: (a + b) / 2 on the stored values), issuer minus median (multiples in x; percent metrics in percentage points, unit pp), issuer position (1 + number of entities strictly better, ties share the position, direction per metric) of n + 1 entities, deviation from the median and outlier flag (outlier iff the relative deviation is strictly above one half; exactly one half is Within range).
- Position is descriptive. CP-1C owns it; consumers may read it but never re-rank (ruling 5).
- Derived facts over peers carry the period "Mixed: issuer LTM Q4 25, each peer's own twelve months"; each peer's own period stays on its source and metric cells.
- No peer source in the pack: the module is limitation-only (issuer cells known, every peer-derived cell missing). The synthetic peer summary is a test vector for cases and fixtures only and is never part of a product pack (ruling 1).

## Recorded omissions (each is a limitation, not a defect)

1. The median includes flagged outliers: an outlier is flagged against the median, not removed from it; the flag is a screen, not a credit judgment.
2. No calendarisation: a peer whose twelve months end on another date is the analyst's Partly comparable with a limitation; Python does not shift or prorate periods (ruling 15). Ratios are currency-neutral, so there is no FX step.
3. No size, rating, sector or business-mix universe criteria. The universe is whatever the data desk supplies, narrowed only by the analyst's comparability judgment.
4. No definition restatement. Peer ratios use the definitions the desk states, including its add-backs as the desk asserts them; the issuer line on the same summary is tied to CP-1 (definition alignment table) but no peer is restated to the issuer's basis.
5. No net leverage, free cash flow, capital expenditure, market-based or valuation metrics. The pack carries no market data and relative value belongs to CP-3 (ruling 7).
6. No dispersion statistics (quartiles, range, standard deviation). The reference Fig. RV.3 range strip would need new facts and a chart, and is deferred; the block shows tables only.
7. Medians over three or four peers are fragile: they move with a single peer. The module states this as a limitation whenever fewer than five peers are included.
8. The minimum of three included peers, the half-median outlier distance and the inclusion rule are policy constants (rulings 2-4), not findings; each is one number in the oracle builder.
