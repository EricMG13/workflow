# CP-DR — deep research (LOCAL gap mode): titles and columns adaptation

Method basis: Deploy V r14 CP-DR (purpose in `methodology.json`: "Resolve material evidence gaps for named consumers, or answer a standalone issuer/sector research question"; required CP-0, no optional edge, tables TDR.1-TDR.3). The r14 CP-DR SKILL.md is not in this repository (same situation as CP-2 and CP-2D). The titles, columns and claims below are therefore a LEAD-accepted adaptation (ruling Q7), not a transcription of r14. Execution adaptation: the analyst writes research questions and, for each, a cited answer or a "not found" with its limitation; Python reads the CP-0 gap agenda, checks every quote, page and tool use, counts, divides, assigns every identifier and composes every table. Scope: gap mode only; the standalone question mode is deferred (the Run has no question field). LOCAL: only the prepared pack through `search_pack` and `read_pages`; no web, provider or credential.

Role: evidence analyst. Reader question: can the open readiness gaps be closed from the sources already in the pack, and what stays open?

## Tables (ids registered in `methodology.json`; nothing else is registered)

| Table | Title | Row header | Columns (field: label) | Rail |
|---|---|---|---|---|
| TDR.1 | Research agenda and gap status | Gap | `description`: description; `kind_severity`: kind/severity; `named_consumers`: named consumers; `questions`: questions; `answered`: answered; `unresolved`: unresolved; `answered_share`: answered share; `status`: status | Evidence |
| TDR.2 | Research questions and cited answers | Question | `gap`: gap; `question`: question; `outcome`: outcome; `answer`: answer; `evidence`: evidence; `searched`: searched | Evidence |
| TDR.3 | Research coverage totals | Total | `total` row: `gaps_total`, `gaps_resolved`, `gaps_partial`, `gaps_unresolved`, `questions_total`, `answered_total`, `unresolved_total`, `answered_share` (the only row) | Limitations |

Row ids: TDR.1 the CP-0 `gap_id`; TDR.2 the analyst's `question_id`; TDR.3 `total` only. Fact ids are `<table>.<row>.<field>`. Every cell is backed by a fact. TDR.3 holds the `total` row only so the declared `ReportTable` has uniform columns; an unresolved item's limitation is on the missing TDR.2 answer/evidence facts and in the module's own limitations.

## Rules

- Every gap in the CP-0 agenda gets 1 to 4 research questions. A question is `answered` (answer, category, at least one verbatim citation to a read page, no limitation) or `not_found` (no answer, category or citation; a limitation; the sources it searched).
- Python owns every count, status and share: questions, answered and unresolved per gap and in total; gap status Resolved (all answered), Unresolved (none) or Partially resolved; share = answered / questions as a Decimal, four places half-up (shown at one decimal as a percent).
- A question the local sources cannot answer stays unresolved: its TDR.2 answer and evidence cells are missing (`∅ G#`), never 0 or N/A. A known zero answered is a known 0.0%. With no gap and no question the counts are known 0 and the share is not applicable (`∅ G# n.m.`).
- Analyst text carries no figure (no digit character) and no prohibited conclusion; figures come from quoted source text and Python's tables. Claims quote Python's counts through `{TDR.3.total.<field>|<unit>}` references.
- Whether a quoted span answers its question is analyst judgment; Python checks verbatim location and that the page was read and the source searched.
- Module status is restricted whenever it carries a limitation (always: the local-only coverage line); inherited limitations come from CP-0.
- Consumers: none today. CP-5 is the only registry edge (restricted); it counts as consumption only after a scope lease binds the CP-DR head and cites the TDR facts.

## Guard limits (accepted costs, Stage 2)

- **Digit rule.** Any character `str.isdigit()` accepts, in a question, an answer or a limitation, is refused (`text must not contain a figure`). A year, an ordinal written with digits and a non-ASCII digit all count. The cost is that an analyst cannot write "2025" in prose; a figure reaches the reader only as a quoted source span or as Python's own count.
- **Prohibited words.** The case-insensitive substrings `recommend`, `refinanc`, `covenant` and `recovery` are refused wherever they occur in those fields, so "recommendation", "refinancing" and "covenants" are refused with the base word.
- **Blank quotes.** A citation whose quote is whitespace or Unicode format characters only is refused as `gaps[i].questions[j].citations[k].quote: empty text`, before the page-occurrence check, so the analyst is told the quote is empty and not that an empty reading was not found.
- **Cited pages.** The cited-page rule (`RULES`) judges `page:N` locators only; any other locator is left to the quote and locator check. A `not_found` question is an absence claim: each searched source needs a recorded `search_pack` over it (scoped to that source or to every source).
- **Rules are pure over the payload text.** `RULES` does not know pack membership, so a searched source or a citation source outside the pack yields its membership issue and its tool-use issue. That is one defect with two consequences, and both lines are listed.
- **Issue lines are bounded.** Lines that quote the payload are cut at 600 characters, and a list past 20 lines keeps the first 19 and a count of the rest.
- **Not here.** Rule W (spaced ranges, dash bullets), B8 and the item 8 comma costs belong to CP-1D, CP-3D, CP-8, CP-2E and CP-2H. CP-DR reads no figure, name or label from a quote.
