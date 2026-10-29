# The Model view

Owner, 17 October 2026: no Excel output, but every Report carries a full financial model. RBOT computes it with a deterministic calculator (`rbot model`, a port of caos-databricks's credit-model maths: interfaces spec §6). How the model is **presented** is RBOT's own design. caos shows its model inside a live, multi-user web workbench with a server, editable rate decks and a dark trading-desk grid. RBOT shows it inside a single offline Report that a PM or analyst opens from disk, reads (never edits), links to from the Front Page, and sometimes prints. Design for that.

## What the Model view is for

1. **The evidence behind every Front Page number.** A reader clicks "3.29x" on the Front Page and lands on the cell that produced it, with its formula and inputs, and can walk back to the filing line.
2. **The analyst's check.** An analyst scans the periods for breaks (a quarter that does not reconcile, a null with a reason, a pro forma column that changes the story) without leaving the Report.
3. **The PM's trend read.** Leverage, coverage, liquidity and margins over time, history and (when projected) Base and Downside, at a glance.

It is not a spreadsheet to work in: no editing, no recalculation, no server, no user-chosen assumptions.

## Content (fixed by the calculator; interfaces spec §6)

- **Periods:** fiscal years (FY-2, FY-1, FY), prior and current year-to-date (PYTD, YTD), LTM, **PF-LTM** when the pack states a new issue's debt, quarters when reported, and **projected years** for a **Base** and a **Downside** case when the Forward Model module ran (three years after the latest LTM).
- **Twelve bands of lines:** operating KPIs; revenue by business unit (with growth); gross profit; operating expenses to EBITDA; Adjusted EBITDA and its add-backs; Adjusted EBITDA to free cash flow; net cash flow, cash and liquidity; debt stack by payment rank (facility terms: benchmark, spread or coupon, floor, maturity, amortisation; debt-like items as memo rows); debt roll-forward; interest by facility; working capital; credit metrics (leverage on reported, adjusted, senior secured and lease-adjusted bases; interest, EBITDAR and capex-adjusted coverage; FFO and FCF to debt; liquidity to debt; margins; growth).
- **House view** on the snapshot column (PF-LTM, else LTM): Reported → Structuring EBITDA (every add-back in) → House EBITDA (unrealized add-backs out); PF interest and cover; Structuring and House multiples; adjusted debt (plus debt-like items) and adjusted leverage; EV and % EV per facility. (Report A labels the house basis "SSIM"; the owner sets the label.)
- **Every cell**: value as served, its basis (Reported, Calculated, Pro forma, Projected, Driver), the stated figure where it differs, a note, and its sources (file, locator, excerpt) or its formula with input cells. **Every null names its reason**: not projected, not applicable, not sourced, component missing (naming it), zero or negative denominator, not stated. Never a zero.
- **Model limitations and reconciliation faults**, e.g. "no PF-LTM: the merger's new debt is not stated".
- Scale: up to 64 columns and 400 lines in the data; a typical CZR run has about 6 historical columns and 120 lines.

## What RBOT's design must solve (the brief for this view)

- **Arrival from a figure.** Most readers arrive by clicking a figure elsewhere. The view must open on that line and column, highlight it, show its passport, and offer the way back.
- **Summary before the grid.** Open on what matters for credit: the house view ladder (EBITDA to multiples to EV), the credit-metric trends, and the limitations. Put the full twelve-band grid behind them, not in front.
- **Readable periods.** Default to the snapshot periods (FY-2 … LTM, PF-LTM); quarters, PYTD/YTD and projected cases are opt-in column groups. Base and Downside must never be mistaken for history: projection is a visible, labelled state, not a colour tint alone.
- **Wide and deep without losing the reader.** Sticky row labels and column heads, band navigation, horizontal scroll inside the grid (never the page), keyboard movement between cells, and search that can land on a line.
- **Charts beside the numbers.** Each section can show its trend (the leverage, coverage and liquidity strip; revenue and EBITDA; the maturity wall), each chart with its table twin, sharing the provenance marks of `provenance-and-states.md`.
- **Honest emptiness.** Projected columns, PF-LTM and quarterly cash flows are often unavailable. Their absence is shown with the reason, compactly, without filling the screen with n/a.
- **Print.** One readable printed form: the house view and credit metrics on one landscape page, the full bands after it.
- **Offline, one file, template-rendered.** Lines and columns vary per run; components must take them as data.

## CZR data available for the Model mock

From `data/rbot-data-base.json`: `tables.financials` (FY2023, FY2024, FY2025, H1 2025, H1 2026, LTM), `tables.balanceSheet`, `tables.creditMetrics`, `tables.capitalStructure` (facilities with terms, cumulative multiples, % EV), `tables.ebitdaAdjustments` (Reported → Structuring → House), `tables.liquidity`, `tables.maturities`, `tables.segments` (Q2 2025 and Q2 2026 segment revenue and Adjusted EBITDA); charts `leverage`, `coverage`, `liquidity`, `revenueEbitda`, `maturityWall`, `ebitdaBridge`. The real CAOS run's CP-1 and CP-2G outputs (`data/caos-runs/full-credit-assessment-2026-10-06/`) show the registers behind it and the forward model's status.

What CZR cannot fill, shown with reasons: quarterly cash flows (six-month only, G1–G3), gross profit (not reported, G23), PF-LTM (merger debt unstated, G8 and G21), unrealized add-backs (G22), and the projected Base and Downside columns (no guidance or rate deck; the real CP-2G was accepted as Restricted with "numeric forecast assumptions not supported").

Current reference: Report A's Model view (`reference/report-a-current/04-model.png`) is the incumbent to improve on.
