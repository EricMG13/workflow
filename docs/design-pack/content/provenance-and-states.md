# Provenance, scales and states

These are product rules, not styling. Any direction may draw them however it likes, but every one must survive. They are what lets an analyst trust a figure and a PM trust a call.

## 1. Every figure has one origin, and the reader can see which

| Origin | Meaning | What clicking it shows (the "source passport") |
|---|---|---|
| **Cited** | Read from a document in the Source Pack | File, locator (line, page or clause), and the verbatim excerpt |
| **Calculated** | Computed by a deterministic script from cited inputs | The formula, and each input as a clickable chip that opens its own passport |
| **Synthetic** | From a test portfolio file, not a real holding | The synthetic file and row |
| **Model-written** | Prose or a judgement written by the model | Marked once per block; its figures inside stay clickable to their own sources |
| **Illustrative** | A judgement no RBOT run has produced yet (scores, recommendations, theses, gate statuses, severities, chosen multiples) | Labelled "Illustrative"; derived numbers (e.g. recoveries from an illustrative EV multiple) are illustrative too |
| **n/a (gap)** | The sources cannot support the figure | The missing item in plain words and the reason; a gap id (G8) links to the module's gap list |

Rules:
- Cited, calculated and model-written content must never look alike, and the difference must not rest on colour alone (WCAG: shape, pattern, outline or text too).
- The figure itself is the button. Two clicks from any figure on any Front Page reaches its source excerpt.
- A missing value is shown as missing with its reason. Never zero, never blank, never interpolated.
- Charts carry provenance in their marks: cited and calculated marks solid; model-written and illustrative marks hatched, hollow or dashed; a gap breaks a line and shows a labelled n/a; an unexplained residual in a bridge is named "unexplained".
- Every chart has a table twin with exact values and gap reasons, a one-sentence summary and a source line. A chart the data cannot draw keeps its title and shows an n/a frame naming the missing input.
- Numbers print exactly as served (the passport shows "Served as"); negatives in parentheses as the filings print them; tabular figures in tables.

The current Report A draws these as a blue corner triangle (cited), a navy corner square (calculated), a dashed "ILLUSTRATIVE" tag and dashed outline, a dashed "Model" tag with a dotted rule, and an italic "n/a G8" chip. See `reference/report-a-current/`. The drawing is yours to redesign; the distinctions are not.

## 2. House scales (fixed vocabularies)

| Scale | Values |
|---|---|
| Recommendation (per Strategy and per instrument) | 1 - Strong OW, 2 - Modest OW, 3 - MW, 4 - Modest UW, 5 - Strong UW, Avoid, N/A |
| Valuation | V1 - Very attractive, V2 - Attractive, V3 - Fair, V4 - Unattractive, V5 - Very unattractive |
| Credit Score | 1 - Strong, 2 - Good, 3 - Fair, 4 - Weak, 5 - Stressed |
| Credit Direction | Improving, Stable, Deteriorating |
| Sector Outlook | Positive, Neutral, Negative |
| Sponsor Quality | High, Medium, Low, N/A |
| Strategies | CLO, Indexed Loans, Indexed HY |
| Portfolio Fit | Fits, Watch, Breaches |
| Module status (`qa_status`) | Pass, With limitations (data value "Restricted"), Blocked |
| Distress gate | Met, Not met, Unclear |
| Covenant / trigger status | Headroom, Tight, Breached, Not computable |
| Ordinal (pressure, probability, impact, feasibility) | High, Medium, Low, Unknown |
| Five-point (lender protection by area) | 1 to 5 |
| Compensation against risk | Attractive, Adequate, Inadequate, Unclear |
| Security preference | Preferred, Neutral, Avoid, Requires more work |
| Market vs fundamental | Aligned, Divergent, Unclear |
| Severity, confidence | High, Medium, Low |
| Calculation status | Calculated, Directional, Not computable |
| Change since a prior Report | Improved, Unchanged, Deteriorated, New, Removed |

Owner ruling (2026-10-17, superseding the 2026-10-11 neutral-scales rule): **colour is a signal**. Statuses, verdicts, directions, severities and scale positions take the signal colours set out in `colour-and-icons.md` (positive, caution, negative, neutral), by their meaning for the creditor, always paired with a word, icon or position marker. Provenance stays shape and pattern, never a signal colour.

## 3. States every design must cover

- **Module status** on every module (navigation and its view): Pass, With limitations (with the reason and its gap chips), Blocked (the view still renders its tables with gaps).
- **Conditional blocks** not shown are replaced by one line naming the condition, e.g. "What changed since the last Report: not shown, no Prior Case was accepted at Approval" or "Transaction summary: not a Primary run".
- **Steps not run** (Deep Research, What changed) appear as one line each under Limitations.
- **Absent destinations**: a Pathway without Portfolio Fit shows that destination as absent with its reason, not hidden silently.
- **Empty and n/a charts**: the n/a frame described in §1.
- **Long and short content**: the Report is rendered from data by a Python template, so every component must take a 1-row and a 20-row table, a 3-word and a 40-word cell, and 3 to 15 modules in navigation.
- **Collapsed and expanded** sections (with "Collapse all / Expand all"), the source passport popover, the "How to read a figure" key, search results, keyboard focus.
- **Print/PDF** (secondary): the Front Page on one landscape page, every other view starting on a new page with its sections open.

## 4. Figures and anchors

Each Front Page figure is numbered by its view (today "Fig. S.1" on the Snapshot, "Fig. CP-1B.2" in a module view) and keeps its first number wherever it is redrawn; every section, figure and source record has its own address (deep link), so an analyst can cite "Fig. CP-4.1" in an email and a colleague lands on it.

## 5. Language

Plain words for readers; RBOT's module codes (CP-1B) are secondary labels. Glossary terms are capitalised as in `reference/CONTEXT.md` (Source Pack, Front Page, Pathway, Recommendation, Valuation, Credit Score, Portfolio Fit, Prior Case). Sentence case for headings.
