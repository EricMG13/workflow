# Task: context form (HTML)

Repo root: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/project-goals-overview-6dc197
Write exactly one file: `docs/templates/context-form.html`. Touch nothing else. Do not commit.
Report back as text (the controller writes the report file).

## Inputs (read these, nothing else needed)

- `docs/CONTEXT-FILE-PROPOSAL.md`: purpose, rulings, the `context/1` JSON shape (follow it exactly).
- `src/deploy_vii/assets/tokens.css`: the palette, type, space, radius, motion tokens. Copy the
  whole `:root` block verbatim into the form's `<style>` with a comment naming its source.
- `src/deploy_vii/assets/app.css` lines 1-25: base element styles to match (body, focus, h1-h3,
  `.num`, `.caps`, `.muted`). Same look; **different layout** from the report shell (the shell is
  rail + navigator + workbench + inspector; do not reproduce it).

## What it is

A single self-contained offline HTML file the user opens locally, fills in, and downloads as
`context.json`. No network: no CDN, no external fonts, no fetch. Add the same CSP meta as
`src/deploy_vii/assets/shell.html` but with `font-src 'self'`. Fonts: `@font-face` for
Red Hat Display/Text/Mono pointing at `../../src/deploy_vii/assets/fonts/*.woff2` (relative);
the token stacks already fall back to system-ui. Vanilla JS, no libraries.

## Layout

- Navy header bar (`--rb-navy`, text `--rb-on-navy`): title "Run context", subtitle "Tell the
  workflow what the filings can't." and a row of section chips (one per section, showing
  complete / needs attention / optional state, click scrolls to the section).
- Below: two columns. Left (max ~760px): the numbered section cards (`--rb-panel` on
  `--rb-ground`, 1px `--rb-rule`). Right (~320px, sticky): **"What this run will do"** panel.
- Under 900px wide: one column, the panel moves below the header as a collapsible `<details>`.
- A top notice (caution tint): "This form writes context.json (schema context/1). The workflow
  does not read it yet: see docs/CONTEXT-FILE-PROPOSAL.md." Options marked **Planned** get a small
  neutral tag "Planned" with a tooltip/title "Not built yet".
- Footer actions: "Download context.json" (primary, `--rb-blue`), "Load existing context.json"
  (file input, fills the form), "Reset". Download is disabled while errors exist; the error
  list links to each failing field.

## Choice pattern

Every single-choice field is a set of radio cards. Each card: label, a "Default" tag on the
default option, and one line saying what happens if chosen (texts below). The selected card
uses `--rb-select` background and a `--rb-blue` left edge. Dependent sections show or hide by
choice (hidden fields are omitted from the JSON, not sent empty).

## Sections, fields, defaults, implication texts

### 1. Run type (required)
Radio cards, default **Research**:
- Primary (new issue): "Deal terms and price talk expected. Talk alone caps relative-value
  confidence below High. Legal documents are usually drafts; CP-4 accepts only executed or filed
  documents today (draft mode Planned)." Default pathway: credit_snapshot. Shows section 4.
- Secondary (trading): "Observed quotes expected. Without them CP-3 relative value states
  Insufficient Information." Default pathway: relative_value. Shows section 5.
- Research — Default: "No market inputs needed. Relative-value and portfolio sections show
  gaps where quotes or holdings are absent." Default pathway: credit_snapshot.
- Earnings update: "Current and prior periods required; CP-1B compares them (period pair from
  this form is Planned; today only fixed test periods run)." Default pathway: earnings_update.

Pathway select (six values, labels): credit_snapshot "Credit Snapshot", earnings_update
"Earnings Update", relative_value "Relative Value", covenant_refinancing "Covenant &
Refinancing", distressed_restructuring "Distressed & Restructuring", portfolio_decision
"Portfolio Decision". It follows the run type's default until the user changes it by hand;
after that a run-type change does not overwrite it. Show the modules the pathway runs (exact
lists from `src/deploy_vii/contracts.py:48-71`):
- credit_snapshot: CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, CP-3, CP-5, CP-6
- earnings_update: CP-0, CP-1, CP-MODEL, CP-1B, CP-1D, CP-5
- relative_value: CP-0, CP-1, CP-MODEL, CP-1C, CP-2, CP-2D, CP-3, CP-3C, CP-3D, CP-5
- covenant_refinancing: CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-2D, CP-4, CP-3C, CP-5
- distressed_restructuring: CP-0, CP-1, CP-1A, CP-2, CP-2A, CP-2G, CP-2H, CP-4, CP-4C, CP-5
- portfolio_decision: CP-0, CP-1, CP-MODEL, CP-2, CP-3, CP-5, CP-6, CP-8

Filing status (`case_kind`) radio, default **public**: public "Filings are public (10-K/10-Q)",
private "Private lender materials", synthetic "Synthetic test case: every section carries a
synthetic-case limitation".

### 2. Issuer identity
- issuer_name (required): "Issuer (company name)". Help: "The marketing or group name. May
  differ from the borrower."
- issuer_id: auto slug of issuer_name (lowercase, `[a-z0-9-]`), editable.
- borrower_name: "Borrower (legal entity)". Help: "The entity that signs the credit agreement.
  Left blank, CP-1 looks for it in the filings and records a gap if not found."
- parent_name, guarantors (comma list → array), aliases (comma list → array; help: "Other
  names and tickers, so peer tables and filings match the issuer").
- listed_equity radio, default **No (private)**: No "Valuation uses peer multiples (section 7)";
  Yes "Give the issuer's market cap and net debt in section 7". ticker shown when Yes.
- sector (text with a `<datalist>` of ~15 broad sectors), country, sponsor (help: "Private
  equity owner, if any").

### 3. Dates, periods, currency
- as_of (required, `<input type="date">`, default today): help "Sources and quotes dated after
  this are refused."
- current_period, prior_period: pattern `^(q[1-4]|h[12]|fy)-\d{4}$` (e.g. q3-2026, fy-2025).
  Both required when run type is Earnings update. prior must be earlier than current when both
  are the same kind (compare year, then quarter/half).
- reporting_currency (3 uppercase letters, default USD). If not USD, implication: "CP-2D
  liquidity treats non-USD facilities as Not calculable today (USD fixed)."

### 4. Deal terms and price talk (shown for Primary)
Repeatable rows ("Add facility"): facility_id, instrument (select: Term loan B, Term loan A,
Revolver, Senior secured notes, Senior unsecured notes, Other), currency, size_m, tenor_years,
talk_spread_bps_low/high, talk_oid_low/high, floor_pct, call_protection, use_of_proceeds,
as_of, provider. Low ≤ high where both given. as_of ≤ run as_of.

### 5. Market quotes (shown for Secondary; optional "Add quotes" link for other run types)
Repeatable rows: facility_id, kind radio (observed default / indicative_talk), bid, ask, price,
yield_pct, spread_bps, as_of (required per row), provider (required per row). bid ≤ ask.
as_of ≤ run as_of.

### 6. Ratings (optional)
Rows: agency (select S&P, Moody's, Fitch, Other), scope (issuer / facility), rating (text),
outlook (Positive, Stable, Negative, Developing, Watch), as_of. Implication when empty and the
pathway runs CP-2H: "CP-2H ratings: 'Rating register not found'." Note tag Planned: "CP-2H reads
real agency names (today only the synthetic test headers parse)."

### 7. Valuation and peers
peer_source radio, default **CP-DR finds public peers** (`cp_dr_public`, Planned): "CP-DR
researches listed peers; CP-1C computes their EV/EBITDA (Planned)". Others: `user_list` "I'll
name the peers" (shows rows: name, ticker), `user_comps` "I'll give peer figures" (rows: name,
ticker, ev_m, ebitda_m, as_of, source; shows each row's EV/EBITDA computed for display only,
labelled "display only, Python recomputes"), `none` "No peers: CP-1C has no peer universe and no
peer multiple is formed".

basis radio. Default depends on listed_equity: No → **auto**; Yes → **issuer_trading**.
- auto: "Uses public multiples, private-deal multiples or both, by evidence quality and
  availability; states Insufficient Information if neither qualifies (Planned)".
- public_comps: "Listed peer EV/EBITDA only".
- precedents: "Private-transaction multiples only (web-sourced by CP-DR, Planned, or rows you
  add)". Shows precedent rows: target, acquirer, date, ev_m, ebitda_m, source.
- blend: "Both, combined".
- issuer_trading (only selectable when listed_equity is Yes): "The issuer's own EV/EBITDA from
  the market data below". Shows issuer_market: market_cap_m, net_debt_m, ev_m (help: "give EV,
  or market cap and net debt"), ebitda_basis (LTM / NTM), as_of, source; at least EV or both
  market cap and net debt required.
- user_multiple: "My own multiple". Shows value (0 < x ≤ 99.99), basis (LTM/NTM), rationale
  (required).
The auto default follows listed_equity until the user picks a basis by hand.

### 8. Pinned assumptions (collapsed `<details>`, optional)
One block per module, each a radio: **"Let the analyst model choose" (default)**: "Labelled
analyst assumption" vs "Use my values": "Labelled user-supplied assumption". A rationale field
is required when "Use my values" is chosen. Bounds (from code):
- CP-2A downside: 1-4 scenarios, each ebitda_decline_pct 0-100 and interest_increase_pct 0-100.
- CP-2D liquidity: horizon_months integer 1-60; minimum_cash_m ≥ 0.
- CP-2E macro/FX: rate_shocks_bps 1-3 values each 1-1000; fx_shocks_pct 1-3 values each 1-50;
  hedge_ratio_pct 0-100 (optional).
- CP-3C refinancing: repricing_bps 0-1000.
- CP-3D market: recovery_pct 0 to < 100.
- CP-4C recovery: ev_multiple 0 < x ≤ 99.99.
JSON: the module key is `null` when the model chooses, otherwise an object of the values plus
`rationale`. All this section's options carry the Planned tag.

### 9. Other inputs you will attach
Checkboxes (default unchecked) and one radio:
- portfolio_workbook: "Portfolio workbook (docs/templates/portfolio.template.xlsx)".
  Implication when unchecked and pathway is portfolio_decision: "Portfolio fit shows gaps."
- prior_case: "Prior decision record". Implication when unchecked and the pathway runs CP-8:
  "CP-8 is blocked: it needs the prior decision."
- management_bridge: "Management EBITDA bridge". Unchecked + CP-1D in modules: "CP-1D: every
  management-bridge cell is not applicable."
- legal_documents radio: executed (default) "Executed or filed documents" / draft "Drafts only:
  CP-4 refuses them today (draft mode Planned)" / none "No legal documents: CP-4 has no
  sources".

### 10. Research questions (optional)
Up to 10 rows: text (required in a row), focus_module (select of module ids, optional).
Planned tag: "CP-DR answers your questions (today it researches only the gaps CP-0 finds)."

## "What this run will do" panel (live, recomputed on every input)

Shows: run type and pathway; the module list as chips; then a list of consequences, each with
a signal colour + icon/text (never colour alone: prefix with "Blocked", "Limited", "OK"):
- Blocked (`--rb-neg`): CP-8 without prior case; CP-4 with draft or no legal documents when CP-4
  runs; issuer_name missing ("CP-0 cannot confirm the issuer").
- Limited (`--rb-caut`): CP-3 runs and there are no quotes and no price talk → "Insufficient
  Information"; only talk → "confidence capped below High"; non-USD currency with CP-2D; no
  ratings with CP-2H; no bridge with CP-1D; peer_source none with CP-1C; portfolio workbook
  missing on portfolio_decision; any Planned option selected ("needs a Planned feature: <name>").
- OK (`--rb-pos`): pinned assumptions count ("3 module assumptions pinned by you"),
  valuation basis summary.
Only show consequences for modules in the current module list.

## Output

`context.json` exactly in the proposal's `context/1` shape, keys in that order, numbers as
strings of plain decimals as typed (trim spaces; no thousands separators accepted: show an
error), empty optional fields as `""`, empty lists as `[]`. Pretty-printed, 2 spaces. Loading a
file with a different `schema` value shows an error and changes nothing.

## Quality bar

- Accessibility: every input has a `<label>`; radio cards are real `<input type="radio">` in a
  `<fieldset><legend>`; errors use `aria-describedby` and an `aria-live` region; visible focus
  (`--rb-focus`); hit targets ≥ 24px; works by keyboard alone.
- No stub or fake value standing in for real behaviour; no catch-all that hides a failure
  (a malformed loaded file shows its parse error).
- Keep it one file, plain and readable; no framework-like abstractions.
- Self-check: include no test framework. Before returning, open the file with a headless
  check if available (e.g. `python3 -c` HTML parse for well-formedness) and report what you ran.

## Report (as text, end with this line)

Files changed, how each section's defaults behave, anything in this brief you could not do,
and a final `Not verified:` line listing what you did not exercise (e.g. real browser
rendering, file download).
