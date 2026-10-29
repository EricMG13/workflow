# The Report as an application: shell, destinations and views

One RBOT run produces one Report: a single self-contained HTML file a PM or analyst opens from disk (no server, no network), on a desktop browser. It behaves like an application: persistent navigation, one view at a time, deep links, search. The shell is shared by all six Pathways; only the Front Page and the module list change.

## 1. Destinations (what navigation must reach without scrolling the document)

In order:

1. **Front Page**: the Pathway's summary screen (six designs: see `01`–`06`).
2. **Analysis**: one view per module the Pathway ran, in plan order, each with its plain name, its RBOT code (secondary) and its status (Pass, With limitations, Blocked). A tally line ("11 modules: 10 with limitations, 1 pass") heads the group.
3. **Model**: the deterministic financial model (financials, balance sheet, credit metrics, capital structure, EBITDA adjustments, chart strip), every cell clickable to its source or formula.
4. **Portfolio Fit**: per portfolio, the limit arithmetic and the capped Recommendation (only in Pathways that run it; otherwise shown as absent with "Not in this Pathway").
5. **Evidence**: every citation of the run (id, file, locator, excerpt, where it is used), plus the evidence-check module (CP-5) folded in.
6. **Limitations**: every known limitation (those shown at Approval, those found by the evidence check, anything unforeseen), plus one line each for steps not run (Deep Research, What changed).

### Module lists per Pathway (Full depth; plain name and code)

| Pathway | Modules in navigation |
|---|---|
| Full Credit Assessment, as built in v1 (Report A) | Source readiness CP-0; Financial analysis and capital structure CP-1; Earnings delta CP-1B; Forecast, liquidity and cash flow CP-2; Credit score and relative value CP-3; Documentation and covenants CP-4 (6) |
| Full Credit Assessment, full scope (later plans) | CP-0, CP-1, CP-1A, CP-1B, CP-1D, CP-1C, CP-2, CP-2A, CP-2E Macro and hedging, CP-4, CP-2D, CP-2G, CP-2H, CP-3D, CP-3C, CP-4C, CP-3 (17) |
| Earnings Update | Source readiness CP-0; Financials and debt CP-1; Business and events CP-1A; Earnings delta CP-1B; Earnings quality CP-1D; Credit synthesis CP-2 (6) |
| Relative Value | CP-0, CP-1, CP-1A, Earnings quality CP-1D, Peer benchmark CP-1C, CP-2, Downside paths CP-2A, Covenants and legal CP-4, Forecast cases CP-2G, Market-implied risk CP-3D, Relative value CP-3 (11) |
| Covenant & Refinancing | CP-0, CP-1, CP-1A, CP-1D, CP-2, Covenants and legal CP-4, Liquidity bridge CP-2D, Refinancing and LME CP-3C (8) |
| Distressed & Restructuring | CP-0, CP-1, CP-1A, CP-1D, CP-2, CP-2A, CP-4, CP-2D, CP-2G, Rating triggers CP-2H, CP-3D, CP-3C, Recovery and fulcrum CP-4C, CP-3 (14) |
| Portfolio Decision | CP-0, CP-1, CP-1A, CP-1D, CP-2, CP-2A, CP-4, CP-3D, CP-3 (9) |

Navigation must hold 6 to 17 modules plus the four fixed destinations, with every destination reachable at 1280×800 (today all 11 of Report A's fit without scrolling; the larger Pathways are the new design problem). Module reader questions, statuses and reasons are in `data/front-pages-data.json` → `modules`.

## 2. The Front Page

The Pathway's summary screen. Whatever the layout, it must:
- put **the call** (the Pathway's verdict, see each page doc) and the key charts in the first viewport at 1440×900, with no click;
- show the issuer, the Pathway, the period, the analysis date and whether this is a Primary (new issue) run;
- present blocks that each say what they are, collapse and expand, and link one step to the module that owns them ("Full analysis");
- replace a conditional block that does not apply with one line naming the condition.

## 3. A module view

Every module view has the same anatomy (Report A screenshot `03-module-cp-1b.png`):
1. Title (plain name) with the RBOT code as a secondary tag; view tools ("How to read a figure", "Collapse all").
2. "On this page": the view's sections as links.
3. **Question**: the module's reader question (fixed text per module).
4. **Status**: the status chip and its reason, with gap chips.
5. **Headline finding**: one model-written sentence whose figures are clickable; a Model mark; "Sources (n)" disclosure under it.
6. Sections: the module's figures and tables (in full where the Front Page shows a summary).
7. **Gaps and limitations**: always last; each gap stated once (id, missing item, reason).
8. Previous / next module.

## 4. Model, Portfolio Fit, Evidence, Limitations

- **Model**: bands (Earnings, Cash flow, Balance sheet, Credit metrics, Capital structure, EBITDA adjustments) as period tables FY-2 … LTM (PF-LTM when a pro forma exists), every cell a figure with its source or formula; the chart strip (leverage, coverage, liquidity).
- **Portfolio Fit**: per portfolio and instrument: current exposure, every limit the instrument touches (limit, Hard/Soft, current, headroom, headroom in money), max size, binding limit, verdict (Fits, Watch, Breaches), the Recommendation cap and the final per-portfolio Recommendation (rule: Breaches caps at Avoid, Watch caps at 3 - MW, Fits does not cap; final = the weaker of the uncapped call and the cap).
- **Evidence**: a searchable register of every citation: id, file, locator, excerpt, and links back to every place it is used.
- **Limitations**: at Approval, from the evidence check, unforeseen; each with what it affects and which source would lift it.

## 5. Global behaviour

- Deep links for every view, section, figure and source record; Back returns to the prior position.
- Search across the whole Report (titles, findings, figures, sources) from anywhere (shortcut `/`).
- "How to read a figure": a key to the provenance marks, scales and status marks.
- The source passport popover (see `provenance-and-states.md` §1) from any figure, chart mark or chip; keyboard reachable; Escape closes and returns focus.
- Collapse all / Expand all per view; Key findings never collapse.
- Keyboard: one tab stop per block of figures (arrows move within), one per chart (arrows move between marks).
- Print: Front Page on one landscape page; every other view on new pages with sections open.

## 6. Platform and build constraints

- Desktop browser on wide monitors; 1280×800 is the minimum; phone is out of scope.
- One self-contained HTML file: inline CSS, vanilla JS; fonts embedded (choose faces whose licence allows embedding); no CDN, no network, no external images.
- **Charts are SVG, drawn in the browser.** The Python renderer writes each chart's data, table twin and summary; a small vanilla JS kit draws the SVG at load and redraws on resize (Plan 07 ruling R1). SVG keeps every mark a focusable, source-linked element with provenance drawn in the mark, prints and zooms crisply, and takes the design tokens through CSS. Design charts as SVG components; design small in-cell visuals (headroom bars, scale meters, severity bars, bullet bars) as CSS. No canvas, no images, no charting library.
- Rendered by a Python template from run data: every component repeats with variable rows, lengths and presence. Design components, not one-off pages.
- WCAG 2.2 AA contrast; colour never the only carrier of meaning; 24px minimum targets; visible focus.
