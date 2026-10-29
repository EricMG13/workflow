# CP-4C questions (AGENTS.md: one file per module)

## Decided by the controller (module-only, from the lease; recorded in the ledger)
- **Q1 (review M1, cited row).** The lease says claims are "read from the cited balance-sheet row". The cited row is the page line that **starts with** the quote. When no line starts with it, the claim gets the existing `claims[<i>].amount_quote: the quoted row has no number under <column>`. The amount is read from that line, never from the first line that shares the label. No new wording. The builder's `row_cells` uses first match on the label; on the frozen page:4, where every label is unique, the two readings are identical. Builder sync is for LEAD (B1 below).
- **Q2 (review L1, blank cell).** A row whose cell count differs from the header's (two-space split) has no number under any column, so it gets the same #11 text. Every frozen row has 7 cells.
- **Q3 (review L2).** A known CP-1 EBITDA with no amount is an upstream contract break. It raises a `ValueError` invariant, as CP-1 total debt (:537) and CP-2G EBITDA (:593) already do.
- **Q4 (round 10, Stage 1 defect).** The quoted cell must fully match the ASCII grammar `-?[0-9]+(\.[0-9]+)?` before `Decimal`; otherwise it gets the #11 text. Comma figures (`1,234.00`) are refused (review I1). The wording stays as pinned.
- **Q5 (fix 1, confirmed by the controller).** A quote that starts two different page lines names no single cited row, so it gets the #11 text. Identical duplicate lines count as one line. This follows from Q1 and adds no wording.
- **Q6 (fix 1 re-review N3, plus a pre-existing truncated-figure case).** A quote must cover whole cells: its two-space cells form a prefix of the cited line's cells, each one equal. `Pr` against `PP&E …` is refused, and so is a quote that cuts the last figure. Both take the #11 text.
- **Q7 (pre-existing: bare CR or U+2028 inside a line).** The cited line must be one physical line. Otherwise it takes the #11 text.
- **Info, no action.** A grammar cell of about 10^6 digits raises `decimal.Overflow` out of `_exact`. It fails closed, and no real pack has one.

## For LEAD (one batch)
- **B1.** Builder sync for Q1 and Q2: `row_cells` / the two-space split in build.py:158-171. No frozen value moves.
- **B2.** CP-1 total debt `not_applicable` is still a fail-closed ValueError, because A-2 #6 words only the missing and conflicting cases.
- **B3.** Under A-2 #9, a valuation label with a figure ("Base FY2026") passes `payload_issues`, and then `compute` raises. The ruling keeps it as an invariant. Does the validator need a repair issue?
- **B4.** Raw quote matching is stricter than the product's `citation_issues`, so at Stage 2 a quote the host accepts can still be refused.
- **B5 (Info).** Under A-1, a class can get a distribution of 0 while its rank's recovery is positive. This needs 38-digit amounts.
- **B6.** The implied-multiple choice: EV's reason wins, and a not_applicable CP-1 EBITDA takes "missing". See round8-report.md.

## Ruled by LEAD round 11 (d60035b)
See `docs/rulings/2026-10-28-stage1.md` `# Round 11`, `## CP-4C`. Modules-decides items are recorded in the ledger (2026-10-28 round 11 line).

## Open for LEAD (after round 11)
- **B7.** A claim name or valuation label holding reserved prose characters (`A {x}`, `A [y]`, `A}`) passes `payload_issues`, then `compute` raises an invariant. This is the same reachability class as A-2 #9 before B3. Should it get a refusal, and with which wording? See probe cp4c-r11/probe_names_compose.py.
- **Info.** Q6's whole-cells rule also refuses three cases with the #11 text: a cell-boundary quote with an empty last cell (`Other  9  `), a line whose last cell has one trailing space, and a quote that carries a CR on a CRLF page. All three fail closed.
