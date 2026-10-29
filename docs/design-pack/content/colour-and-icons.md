# Colour as a signal, and where icons beat text

Owner, 17 October 2026: a clean, modern SaaS look in the company colours; **colour is a signal**; use icons where they serve the reader better than words. This supersedes the 11 October ruling that kept every scale neutral.

## 1. Colour roles

**Brand (structure and action, never a verdict)**
- Deep navy `#000533`: the application frame (navigation, headers), primary text.
- Electric blue `#0017E5` (logo field `#001AFF`): primary actions, links, focus, selection, the issuer's own series in charts.
- A cool neutral ramp for surfaces, borders and secondary text.

**Signal (meaning; one hue per meaning, used everywhere the same way)**

| Signal | Meaning | Applies to |
|---|---|---|
| Positive | good for the creditor; no action needed | Pass; Fits; Headroom; Improving; overweight calls (1 - Strong OW, 2 - Modest OW); Attractive and Very attractive Valuation; Credit Score 1–2; Low severity or pressure; Aligned |
| Caution | watch; limited; close to a line | With limitations; Watch; Tight; Stable-with-risk; 3 - MW; V3 Fair; Credit Score 3; Medium severity or pressure; Unclear gate; Divergent; stale data |
| Negative | bad for the creditor; act or avoid | Blocked; Breaches; Breached; Deteriorating; underweight calls (4, 5) and Avoid; V4–V5; Credit Score 4–5; High severity; distress gate Met; fulcrum class; unexplained residual |
| Neutral / info | no verdict | N/A; Not computable; not run; absent; informational notes |

Rules:
- **Colour follows credit meaning, not arithmetic sign.** Leverage up is negative; cash up is positive; a revenue rise with a margin fall is shown by the metric that matters, not by every delta turning green.
- **Never colour alone.** Every signal colour is paired with an icon, a word or a position marker (WCAG 2.2: 1.4.1). Contrast AA for text, 3:1 for marks.
- **Provenance is not a signal.** Cited, calculated, model-written, illustrative and synthetic stay distinguished by shape and pattern (marks, dashed and dotted treatments, tags) in neutral or brand tones, so they never compete with the verdict colours.
- **Charts:** series use a colour-blind-safe categorical set built from the brand (issuer = electric blue, comparison = a contrasting hue); signal colours appear in charts only for thresholds, breaches and fulcrums.
- **Restraint:** colour marks the few things that need attention; a screen where everything is coloured has no signal. Most of the surface stays neutral.

## 2. Where icons serve better than text (candidates, for Claude Design to confirm)

Icons come from one consistent set, drawn as inline SVG (the Report is offline), one stroke weight, each with an accessible name and a tooltip. Icon-only is fine in dense tables and navigation once the "How to read a figure" key teaches it; the full word stays in headers, popovers and print.

| Where | Today (text) | Icon candidate |
|---|---|---|
| Module status in navigation and tables | "Pass", "With limitations", "Blocked" | tick, half-filled circle, slashed circle (with signal colour) |
| Portfolio Fit verdict, covenant status, distress gate | "Fits / Watch / Breaches", "Headroom / Tight / Breached", "Not met / Unclear / Met" | tick, warning triangle, cross; gauge or gate glyph for the distress gate |
| Credit Direction, Sector Outlook, period deltas, prior-case change kinds | "Improving / Stable / Deteriorating", "Up / Flat / Down", "Improved / Unchanged / Deteriorated / New / Removed" | up, flat and down arrows; plus and minus for New and Removed |
| Severity, pressure, likelihood, confidence (High / Medium / Low) | words in table cells | three-step signal bars or a dot meter |
| Provenance in dense tables | "[C12]", "= K3", "Model", "ILLUSTRATIVE", "SYNTHETIC" | corner marks and small glyphs (document for cited, function for calculated, sparkle or pen for model-written, dashed outline for illustrative, flask for synthetic); the words stay in the passport and key |
| Gaps | "n/a G8" | an empty-set or dashed-circle glyph plus the gap id; the reason on hover and in the gap list |
| Actions | "Show table", "Collapse / Expand", "How to read a figure", "Sources (4)", "Full analysis →", search, print, copy link | table/chart toggle, chevron, question mark, document stack with count, arrow-into-view, magnifier, printer, link |
| Navigation destinations | text rows | a family icon beside each label (Front Page, financials, earnings, liquidity, covenants and legal, market and relative value, recovery, portfolio, Model, Evidence, Limitations); an icon-only collapsed rail on narrower screens |
| Source documents (Evidence, source inventory) | file names | document-type icons (filing, legal agreement, earnings release, market page, portfolio file, fetched web source) |
| Instrument rank and level basis | "Senior secured", "Unsecured", "Market / Talk / Image-Read" | lock or shield for secured; tag icons for talk and image-read levels; clock for stale levels |
| Conditions and not-run steps | condition sentences | a muted "skipped" glyph with the sentence |

**Keep as text:** house scale values (Recommendation, Valuation, Credit Score) as their words with a position marker; every number; gap reasons; module and section names (icon plus label, never icon alone in headings); the call's one-line facts.
