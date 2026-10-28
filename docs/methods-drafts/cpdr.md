<!-- DRAFT for a future src/deploy_vii/methods/cpdr.md; recorded here, not installed (pre-code; LEAD ruling Q7, 2026-10-28). -->
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
