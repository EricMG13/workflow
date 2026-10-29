# methods/cp2g.md: CP-2G Forward credit model, recorded LEAD adaptation (D12)

Moved from the draft at Stage 2 (`docs/CP2G-OWNER-LEASE.md` Files). The r14 CP-2G SKILL.md is not in this repository, so this is a recorded adaptation, not a transcription (LEAD ruling 1, `report.md`). Oracle: `cases/cp2g-owner/` (builder `builder/build.py`). Lease: `lease-draft.md` (rev 2).

## Purpose and mapping

`methodology.json` purpose: "Builds the forward credit model: deleveraging path and forecast cases". Architecture row (`docs/reviews/owner-harness-architecture.md`): "EBITDA/FCF/net debt/leverage path; assumptions, guidance; req CP-0, CP-1, CP-2A; opt CP-1D, CP-2D". The nine registered ids map one to one to the tables composed here: T2H.1 upstream register, T2H.2 historical-to-base bridge, T2H.3 assumption register, T2H.4 operating forecast, T2H.5 debt and cash roll-forward, T2H.6 credit metrics, T2H.7 break-point timing, T2H.8 deleveraging path, T2H.9 gaps ledger. Python owns all arithmetic; the analyst supplies seven driver paths, the CP-2A scenario that defines the downside, the metric of each CP-2A watch level, a minimum liquidity (or "not assessed") and the assessment, as literal input labelled analyst assumption (D11).

## Method

- Base period: the one CP-1 T4.10 column "LTM Q4 25"; forecast years FY2026 to FY2028 (annual, three years, one fiscal year of source).
- Base case: revenue grows by the analyst rate; EBITDA is revenue x margin; cash interest is the analyst rate x opening debt; cash taxes and working capital are one share of revenue; capital expenditure is a share of revenue; free cash flow is EBITDA less those outflows; debt falls by the analyst's repayment; cash moves by free cash flow less distributions and repayment and is never floored (negative cash is an unfunded requirement, not a plug).
- Downside: CP-2A's settled scenario shock (EBITDA decline, interest increase) applied to every forecast year on the base path; every other driver is held.
- Break tests: CP-2A's settled levels re-tested along the path (free cash flow at or below zero, coverage floor, and the analyst-mapped leverage and coverage watch levels), plus the analyst's minimum liquidity. The first year a test is met is a fiscal year, "Not reached by FY2028", or missing with the root reason.
- Zero, missing, not applicable and blocked are distinct everywhere; a ratio with a non-positive denominator is missing, not zero.

## Left out of the method (LEAD ruling 1; each is a stated limitation or follow-up)

| Item | Why left out | Effect |
|---|---|---|
| Upside case | The base and downside cases are the two the CP-MODEL consumer needs; the pack has one fiscal year | No upside path or probability weighting; probability weighting is a prohibited conclusion |
| Quarterly path | One fiscal year of source; annual granularity | Intra-year troughs are not seen; own limitation "no quarterly path" |
| Perimeter split (finance company, borrower, guarantor) | Perimeters unavailable in the pack | Consolidated group only |
| New borrowing, refinancing, maturities | Not modelled; debt moves only by the analyst's repayments (see the observation below) | Own limitation "New borrowing is not modelled"; the maturity wall and funding gap belong to CP-2D and CP-3C |
| Interest on average balance | Interest is the rate on the opening balance (no circularity) | Interest is slightly overstated when debt falls during a year |
| Tax shield | Cash taxes and working capital are modelled together as one share of revenue | Taxes do not move with interest |
| Working-capital cycle | Same combined share | No days-based cycle |
| Driver-level downside | The downside is CP-2A's persistent shock, not own revenue, margin or capex paths | A richer downside doubles the submission; later schema revision (ruling 2) |
| Mitigation | No management action is modelled | The downside is gross of mitigation |
| Cash sweep | No sweep of surplus cash to debt beyond the analyst's repayments | Cash can accumulate while debt is held |
| CP-MODEL driver table | CP-MODEL is not in the plan; slots resolve through `cp1.cp_model_segment_allocation` | Deferred to the CP-MODEL lease (ruling 5) |

## Observation: FY2025 borrowing (ruling M4)

The financial source (page 3, cash flow statement) reports FY2025 debt issuance of 5.00 (1.25 in each quarter) and debt repayment of 0, so net debt issuance is 5.00; the balance sheet (page 4) shows total debt rising from 45 at the opening 2024-12-31 balance to 50 at 2025-12-31, with no stated repayment, and the pack states no noncash debt change. The forward model assumes no new borrowing in FY2026 to FY2028 and repayments of the analyst's choosing, so "no borrowing" is a real departure from the observed FY2025 pattern, not a neutral default. The `T2H.5` new-borrowing column was dropped (it would have shown a known 0.00 for a modelling omission); the own limitation "New borrowing is not modelled" stays, and this paragraph records the observation for the reader of the adaptation.

## Tables

T2H.1 Upstream register; T2H.2 Historical-to-base bridge (CP-1 restatements as own calculated facts, the FY2025 free cash flow identity, CP-1D supported figures); T2H.3 Assumption register (analyst drivers, CP-2A shock copies, minimum liquidity); T2H.4 Operating forecast; T2H.5 Debt and cash (opening debt, repayment, closing debt, interest, opening cash, free cash flow, distributions, closing cash, undrawn revolver, accessible liquidity); T2H.6 Credit metrics (FY2025 headroom is not applicable: minimum liquidity is a forecast-year assumption); T2H.7 Break-point timing; T2H.8 Deleveraging path; T2H.9 Gaps ledger.

## Rendering

Two proposed FP05 blocks in `distressed_restructuring` only (`forward-credit-path`, `forward-breakpoints`): a design extension, because the design reference has no CP-2G block. See the lease, "Rendered sections".

## Connection notes (Stage 2)
- **One adapter.** Submit, the entry validator, probe and view reach the core only through `cp2g._inputs`: the CP-1 head's selected T4.10 LTM facts (`select_cp1`, one per metric, in the head's order; a head without exactly one fails closed), the bound CP-2A and CP-1D heads, the bound statuses and the issuer name.
- **CP-2A head.** `cp2a_of` reads every T2B.1 scenario (name, decline, increase) and T2B.6 break (origin, test, level, required decline, outcome) in register order; the name is the known text fact `T2B.1.<row>.name`. The base period is the one period the T2B.1 shocks state: a shock with no period is not a conflict, two periods raise `CP-2G: CP-2A T2B.1 facts differ in period`, and no period at all raises (fail closed).
- **Parse.** The retained payload is read only through `json_object` (bounded, storable, exact decimals); the schema validates the document's exact re-serialisation. Text `json_object` refuses keeps Pydantic's own shape issue (the frozen r14 frame).
- **Issue lines.** A `prose.issues` line quotes the analyst's text, so it is cut at 600 characters (`execution.clipped`), as is a refused `current_inputs` text; a raised composition lists at most 20 lines and a count. A rationale becomes `Claim.text`, so when `prose.issues` passes it, it is also checked as `RunText` (the type's message, never the input).
- **Staleness.** Any bound upstream that changed is reported alone, before any content check (ruling 10); through the workflow a changed head refuses `stale_binding` first.
- **Quotes.** CP-2G reads no source quote: it takes no citation from the analyst, and the view carries no `quote`, `citations` or `record_json` key. Model-typed scenario values and the minimum liquidity amount are analyst judgements (Q-SQ). Cell citations follow the lineage rule from the CP-1 facts the composer derives from.
- **View tree.** The `read_inputs` view is the lease's draft tree (`manifest.json tool_use.view_tree_draft`): `upstream`, `base`, `drivers` (the seven bounds, then `minimum_liquidity` with `may_be_not_assessed`), `cp2a`, `cp1d`, `break_metrics_offered`, `cp1_facts`, `cp1d_facts`, `inherited_limitations`. The key tree is committed in `cases/cp2g-owner/cp2g-view-tree.json` (shape only, per case), checked by the connect test against the view over a real store and by the owner test against the genuine run's body.
- **Settled form.** The reference tables carry the upstream facts verbatim under their own ids; only the table, row and field coordinates change. Claims carry no citation. The reader `cp2g_reader` returns the settled own limitations (with the synthetic line on a synthetic case); a blocked head gives its status and hash only.
- **Derived-fact citations (round 3 item 3; re-pinned at the Stage 2 close release).** A calculated fact has one `Citation` per (source, page), quoting the first quote on that page among the citations of the facts in its `derives_from` list, in that order (`deploy_workflow.owners.blank.one_per_page`, applied in `_cite`); an own fact contributes its own (transitively CP-1) citations; analyst inputs and CP-2A watch levels carry none. No quote is invented. `expected.json lineage_rule` states the same rule.
