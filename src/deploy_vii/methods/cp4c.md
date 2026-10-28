# methods/cp4c.md: CP-4C Restructuring fulcrum, recorded LEAD adaptation (D12)

Written at Stage 2 (`docs/CP4C-OWNER-LEASE.md` Files); no draft existed. The r14 CP-4C SKILL.md is not in this repository, so this is a recorded adaptation from the frozen lease, not a transcription. Oracle: `cases/cp4c-owner/` (builder `builder/build.py`).

## Purpose and mapping

`methodology.json` purpose: "Models the restructuring scenario, fulcrum security and plan recovery." Required CP-0, CP-1, CP-2G, CP-4, CP-2A; optional CP-3C, which this version never reads (own limitation). The ten registered ids map one to one to the tables composed here: T4E.1 upstream register, T4E.2 claims register, T4E.3 valuation scenarios, T4E.4 waterfall allocation, T4E.5 recovery by class, T4E.6 attachment and detachment, T4E.7 fulcrum identification, T4E.8 plan treatment, T4E.9 waterfall totals, T4E.10 gaps ledger. Python owns all arithmetic. The analyst supplies claim ranks, the EBITDA basis and multiple of each valuation, the fulcrum class or classes and the plan treatment, as literal input labelled analyst assumption; the fulcrum and the treatments are checked against the waterfall.

## Method

- Claims: the secured class is the CP-1 twelve-month total debt; any other class reads its amount from the cited balance-sheet row (`financial` page:4) under the named column, or states `not_stated`. No amount is typed by the analyst.
- Enterprise value: a CP-2G forecast EBITDA (base or downside, FY2026 to FY2028, read from the CP-2G fact) times the analyst's multiple, exact. A multiple "not assessed" or a missing EBITDA leaves every figure of that valuation missing with its root reason.
- Waterfall: absolute priority by rank number; one rank shares pro rata, a partly paid rank by exact largest remainder (round 8 A-1). Recovery is paid over claim; the equity residual is what remains (a known 0 when creditors absorb all value). Missing is never 0: a missing claim blocks its rank, every lower rank and the residual.
- Value break: the first rank paid less than its claim, else equity. Attachment and detachment multiples are the claims ahead of and through a class over EBITDA (missing for non-positive EBITDA). Changes against the first valuation are in percentage points (unit `pp`).
- Distributable value is the enterprise value only: balance-sheet cash is not added and costs are not deducted unless a class states them.

## Guard limits

The phrase guard checks the product's `peer ranking` and `instrument recommendation` kinds plus two core-local kinds, `outcome certainty` and `probability weighting`, matched word-bounded; the product's `recovery conclusion` kind is skipped because CP-4C owns recovery. Cannot catch (lease, `expected.guard`):
- prose that contradicts the waterfall (only the fulcrum `class_ids` are checked);
- unlisted advice or certainty wording, such as "Holders should avoid this credit" or "The term loan is certain to be repaid";
- over-blocking of "probability of" in neutral text;
- figures in fields that are not run text (only the builder's digit assertion covers them).

## Connection notes (Stage 2)

- **One adapter.** Submit, the entry validator, probe and view reach the core only through `cp4c._inputs` over `cp4c_upstream`: the bound CP-1, CP-2A, CP-4 and CP-2G heads, each with its own bound status, and the status of a bound optional CP-3C (shown in T4E.1, never read). A required head that is blocked is refused (CP-2G's begin is already refused by the store).
- **T4.18 terms.** The term loan's `secured_status` and `seniority` are read from the CP-1 T4.18 row whose `facility_id` is `term-loan` at the QUARTER period ending on the latest T4.14 period end (manifest `fact_selection_rule.cp1_t418`). An FY alias row of the same end must state the same terms; an earlier quarter is never read. No row, no T4.14 period or a differing alias fails closed.
- **CP-2G head.** Read through `owners.cp2g.cp2g_reader` and selected into the core's own type (rulings stage2 Q6): the six T2H.4 EBITDA facts, the T2H.7.b01 first years and the two T2H.3 source texts. The CP-2A row is the one both source texts name (round 13 item 2), never a constant; its base period is the one period its two shocks state, and a shock with no period is not a conflict (round 5 item 16).
- **CP-4 head.** The lease's `cp4_reader` selection: T4C.11, T4.10 row r02 and T4.13. The core reads the facility, the rating and the additional-debt conditions from it.
- **Statement rows.** The view offers every row of a financial page under a `Period end` header whose cells line up with the header, as its label and the header's columns. Python offers rows, not amounts, and classifies no row as a liability: the analyst names the claim row and the validator reads it.
- **Cited pages.** Every cited `page:N` must be read through `read_pages` in the step (`live.tools.unread_citation_issues`, journaled after the validator issues). A citation outside the step's scope (identity) is never readable, so refusal v08 journals its validator issue and then the unread page.
- **Parse and issue lines.** The payload is read only through `json_object` (bounded, exact decimals); text it refuses keeps Pydantic's own shape issue (the frozen r12 frame). An issue line that quotes the analyst's text is cut at 600 characters; a raised composition lists at most 20 lines and a count. A rationale becomes `Claim.text`, so it is also checked as `RunText`.
- **Staleness.** Any bound upstream that changed is reported alone, before any content check; through the workflow a changed head refuses `stale_binding` first.
- **View tree.** The `read_inputs` view is the lease's draft tree (`manifest.json tool_use.view_tree_draft`), with no `quote`, `citations` or `record_json` key. The draft asks the implementer to commit `cases/cp4c-owner/cp4c-view-tree.json` from a product-settled head; `cases/` is not this task's to edit, so that file is left to the integrator.
- **Settled form.** The reference tables carry the upstream facts verbatim under their own ids; only the table, row and field coordinates change. Claims carry no citation. `cp4c_reader` gives each valuation's enterprise value, each class's recovery and the value break, with the settled own limitations; a blocked head gives its status and hash only.
