# methods/cp3c.md (DRAFT rev 2, 2026-10-28): CP-3C Refinancing and liability-management risk, recorded LEAD adaptation (D12)

Draft for LEAD to move to `methods/cp3c.md` (LEAD ruling 7). The r14 CP-3C SKILL.md is not in this repository, so this is a recorded adaptation for this one-facility pack, not a transcription. Oracle: `cases/cp3c-owner/` (builder `builder/build.py`). Lease: `lease-draft.md` (rev 2).

## Purpose and mapping

`methodology.json` purpose: "Assesses refinancing and liability-management risk before or during distress." `docs/reviews/owner-harness-architecture.md:67`: Python "refinancing need/cost, LME capacity from CP-4"; analyst "path, LME likelihood". Python owns all arithmetic; the analyst supplies one margin step-up (or its absence) and exactly one assessment for each of five refinancing paths. T3D.1 refinancing need by maturity, T3D.2 burden, T3D.3 cost sensitivity, T3D.4 creditor position, T3D.5 LME capacity (Base / LME / Stress), T3D.6 refinancing paths, T3D.7 analyst judgments, T3D.8 gaps ledger, T3D.9 upstream trace. T3D.10 and T3D.11 are registered and unused.

## Method

- Inputs: settled CP-1 head facts (T4.10 cash, undrawn revolver, adjusted EBITDA, cash interest; T4.18 secured status, seniority, annual amortisation) and the settled CP-2D head (horizon, run-rate annual flow, minimum cash or its gap, funding gap or its gap, maturity-wall rows). Balance date D0 = 2025-12-31; flows are the twelve months to D0.
- Facilities in ascending months from D0 (CP-2D's whole-month rule), ties by facility id.
- Principal payable at maturity = principal less amortisation to the maturity date (annual amortisation x months / 12, capped at principal).
- Resources at maturity = cash + undrawn revolver - minimum cash + run-rate flow x months / 12 - amortisation of all facilities to that date - principal paid from resources at earlier maturities. Resources applied = min(principal payable, max(0, resources)). Refinancing need = principal payable - resources applied; a computed 0 is "no need", distinct from missing.
- Cost sensitivity: one analyst margin step-up (basis points, 0..1000) applied to the whole principal payable at maturity; added annual cash interest = principal repriced x step-up / 10000; pro forma interest cover = adjusted EBITDA / (cash interest + added interest). A 0 bp step-up is a known 0; an unassessed step-up makes the cost cells missing.
- Creditor position: rank = (secured before unsecured, then seniority); claims at or ahead = principal of facilities ranking at or ahead; a NOT_STATED flag makes every claims cell missing. T3D.5 Base is the largest claims at or ahead.
- Zero, missing, not_applicable and blocked stay distinct; nothing defaults to 0 or N/A.

## Left out of the method (each is a recorded limitation or follow-up)

| Item | Why left out | Effect |
|---|---|---|
| LME capacity (priming, drop-down, uptier, basket headroom) | CP-4 is not read: the frozen CP-4 oracle always shows basket capacity amounts missing, and CP-4 runs on a different pack | T3D.5 LME and Stress columns are permanent gaps; the liability-management path is forced to Insufficient Information; own limitation "Liability-management capacity" |
| Need versus principal repriced | The whole principal payable at maturity (50) is repriced, not the refinancing need (40) | Conservative: added interest and the interest-cover fall are overstated relative to repricing the need only |
| Pro forma interest | Interest saved on amortised principal and the cost of refinancing an earlier shortfall are ignored | Pro forma interest is approximate; an earlier shortfall is not refinanced (own limitation "Resources basis") |
| Revolver availability | The undrawn revolver is assumed available at every maturity, even where it matures earlier; its own maturity is not read | Own limitation "Revolver availability"; not exercised in the frozen pack (explicit zero revolver) |
| All-in rate | No reference rate level in any source | Only a margin step-up over current terms is shown (own limitation "Reference rate level") |
| Maturity concentration by year | One facility in the pack; the per-facility table is not a year bucket view | No concentration measure; multi-facility ordering exercised only by composer fixtures |
| Covenant headroom interplay (CP-4) | CP-4 is not read | No link between a refinancing cost and covenant headroom; covenant-compliance wording is a prohibited conclusion |
| Stressed case (CP-2A) | CP-2A is not read | Stress column is a gap (own limitation "Stress case") |
| Guarantees and structural subordination | No guarantor or entity-level data in CP-1 | Ranking follows secured and seniority flags only (own limitation "Ranking basis") |
| Forecast, growth, new borrowing | A run-rate, not a forecast | The CP-2D annual flow is held flat to each maturity, including dates after the CP-2D horizon (own limitation "Run-rate basis") |
| Market access, owner support, asset sales | CP-3D and CP-1A are not read | Feasibility rests on credit metrics alone; those paths are Insufficient Information (own limitations "Market access", "Business context") |

## Prohibited conclusions

A path text, credit implication, limitation or repricing rationale is digit-free and states no prohibited conclusion: `business_context.prohibited_issues` with its default kinds (peer ranking, instrument recommendation, recovery conclusion) plus a core-local check for covenant-compliance wording (compliance, breach, "covenant met", sufficient headroom) and refinancing-outcome wording ("will be refinanced", "refinancing is assured", "will default"). A phrase guard, not a semantic review: a conclusion no listed phrase names is not caught (recorded in `expected.prohibited_probe`).

## Tables

Claims are run text: every figure is a `{<fact_id>|<unit>}` reference to a CP-3C table cell (MC-2); gaps are `[<fact_id>]` chips. Every amount cell in US$ m carries currency USD.

Not verified: titles, columns and claim wording are this adaptation's design; no CP-3C core, composer or validator exists to compare against the oracle.
