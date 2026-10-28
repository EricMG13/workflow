# methods/cp2d.md (DRAFT rev 1, 2026-10-28): CP-2D Liquidity, recorded LEAD adaptation (D12)

Draft for LEAD to move to `methods/cp2d.md`. The r14 CP-2D SKILL.md is not in this repository, so this is a recorded adaptation, not a transcription. Oracle: `cases/cp2d-owner/` (builder `builder/build.py`). Lease: `lease-draft.md` (rev 2).

## Purpose and mapping

`methodology.json` purpose: "Builds the near-term liquidity bridge and cash runway". `docs/reviews/owner-harness-architecture.md:62` maps it one to one: T2E.1 sources and uses, T2E.2 revolver and liquidity position, T2E.3 runway, T2E.4 maturity wall, T2E.5 funding gap; T2E.6 analyst judgments, T2E.7 gaps ledger, T2E.9 CP-1 source trace. T2E.8 is unregistered and unused. Python owns all arithmetic; the analyst supplies the horizon (1..60 months), the minimum cash (or its absence) and three short assessments.

## Method

- Inputs: settled CP-1 head facts named by `manifest.fact_bindings` (T4.5, T4.6, T4.10, T4.18); CP-0 and CP-2 heads for status and inherited limitations only. Balance date D0 = 2025-12-31; flows are the twelve months to D0.
- Run-rate F = operating cash flow + investing + financing - net debt issuance (new borrowing excluded). Held flat over the horizon: F x H / 12.
- Cash at horizon end before refinancing = closing cash + F x H / 12 - amortisation in horizon - maturities in horizon.
- Funding gap = max(0, minimum cash - (cash at horizon end + undrawn revolver)); headroom = resources - minimum cash.
- Runway (months until cash reaches minimum cash) uses run-rate cash flow alone and excludes maturities and amortisation; the wall is shown in T2E.4 and T2E.5. Minimum cash missing: the row is missing. F < 0: max(0, start) / (-F / 12), stored at 1 dp (so 0 months is '0.0'). F >= 0: "Not reached at run rate" when start >= 0, 0 months ('0.0') when start < 0. Revolver missing: "Not reached" only when F >= 0 and cash alone clears the minimum (a revolver is never negative), else the row is missing ("Not calculable: revolver undisclosed").
- Copies of CP-1 facts keep the fact's value_class and normalise unit `currency` to `MILLIONS`.
- Zero, missing and blocked are distinct: a known zero is shown as 0; a missing value is a gap cell (`∅ G<n>`) with a reason and a limitation; a blocked upstream refuses `begin`.

## Left out of the method (each is a recorded limitation or follow-up)

| Item | Why left out | Effect |
|---|---|---|
| RCF availability conditions (springing covenant, borrowing base) | CP-4 is not an upstream edge | Undrawn revolver is counted at face value; not exercised in the frozen pack (explicit zero revolver) |
| Seasonality and intra-year low point | LTM flows are annual; no quarterly path is projected | Cash at horizon end can overstate the intra-year trough; stated in "Run-rate basis" |
| Dividend flexibility | Dividends held flat | Conservative: a cut would improve F |
| Floating-rate interest | No rate path; interest stays in LTM cash flow | F does not move with rates |
| Interest after maturity | Interest is not removed when a facility is repaid | Conservative; if it stopped, long_horizon would show cash (25) and gap 35 instead of (30) and 40. Own limitation "Interest after maturity" |
| Trapped cash | No jurisdictional data in CP-1 | Restricted cash is shown, not deducted; all cash counts as available |
| Refinancing | CP-3C territory | Cash at horizon end is "before refinancing"; refinancing wording is a prohibited conclusion |
| Covenant compliance | CP-4 territory | Covenant-compliance wording is a prohibited conclusion |
| Maturities in the runway row | Option chosen by LEAD ruling M2 | Own limitation "Runway basis" |
| Forecast, growth, new borrowing | A run-rate, not a forecast | Own limitation "Run-rate basis" |

## Horizon bound

1..60 months. "Near-term" liquidity does not extend beyond five years; the frozen cases use 24 and 60 (60 reaches the 2029-12-31 maturity).

## Tables

T2E.1 Liquidity sources and uses (twelve months to D0; non-zero difference to reported closing cash is a known value plus an own limitation); T2E.2 Liquidity position; T2E.3 Cash runway; T2E.4 Maturity wall (one row per T4.18 facility); T2E.5 Funding gap; T2E.6 Analyst judgments; T2E.7 Gaps ledger (one row per own limitation); T2E.9 CP-1 source trace (includes fcf_unlevered, read and unused, missing).

Claims are run text: every figure is a `{<fact_id>|<unit>}` reference to a CP-2D table cell (MC-2); the horizon length is not spelled in a claim.

Not verified: titles, columns and claim wording are this adaptation's design; no CP-2D core, composer or validator exists to compare against the oracle.
