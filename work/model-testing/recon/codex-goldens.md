# Recon: Codex financial goldens (checked 2026-10-31 10:53 UTC)

Location (untracked, still being edited by an active Codex session):
`~/.codex/worktrees/deliverable-design/Deploy Workflow/work/evaluation/public-campaign/source-gold/<issuer>/`

Snapshot taken at 10:53 to `/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1-codex-gold-20261031/` (gitignored; sha256 of each `financial_gold.json` printed in the session log). The SEC corpus was copied to `artifacts/public-corpus/v1/` (36 acquired files, sha256-verified against Codex's manifest) and Codex's history reviews to `artifacts/public-corpus/v1-codex-history-reviews/`.

## What exists (schema `public-financial-gold/1`, contract `financial-gold-contract.md`)
| Issuer | Pathway | Cutoff | Facts | Status counts | Review state |
|---|---|---|---|---|---|
| TDG | credit_snapshot | 2025-02-04 | 108 | 98 known, 10 missing | 3rd fix round open (PG-06 header mapping, PG-07 exact quotes) |
| SHC | earnings_update | 2025-08-08 | 156 | 137 known, 19 missing | 3rd fix round open (PG-06, PG-07); has `cp1b_delta_inputs.json` |
| BGS | relative_value | 2025-08-04 | 106 | 98 known, 8 missing | PASS after fix round 1 (BGSLTH-01–05) |
| LTH | covenant_refinancing | 2025-08-18 | 111 | 84 known, 27 missing | PASS after fix round 1 |
| IHRT | distressed_restructuring | 2024-12-23 | 90 | 80 known, 10 missing | PASS (S1, S2, Q1, Q2 closed) |
| NATL | portfolio_decision | 2025-11-06 | 90 | 59 known, 8 missing, 23 conflicting | PASS; the 23 conflicts are restatement originals vs revised; adjusted EBITDA Q4 revised to USD 218m |

**Metrics covered for 4 quarters + FY:** revenue, operating profit, net income (total and parent), reported EBITDA, adjusted EBITDA, D&A, CFO, capex (payment and signed), cash, total debt, principal, current assets, current liabilities, total assets, total liabilities, total equity. Some issuers add lease, revolver and principal splits.

**Method:**
- Independent of candidate parsers and model output.
- Each fact carries iXBRL tag/context/unit evidence plus the visible DOM table, row and column, and a quote.
- Arithmetic is exact Decimal with ordered operand receipts; a missing value stays missing.
- Reviews are under `public-campaign/reviews/`.

## Not covered (gaps for "accurately populated deliverables")
- **Context form:** no `context.json` per issuer.
- **Debt stack:** facility list, maturities, margins, floors (CP-2, CP-3C, CP-4).
- **Covenants:** LTH covenant definitions, levels and springing triggers from amendments 13–15 (CP-4, CP-3C).
- **IHRT exchange:** pre/post exchange debt and terms (CP-2G, CP-2H, CP-4C).
- **BGS fair values:** loan and bond fair values (CP-3, CP-3D); there are no executable prices.
- **NATL portfolio:** holdings, NAV and limits are absent by design (user-supplied).
- **Downstream modules:** no goldens for module outputs other than CP-1 or for deliverable blocks. Judgment modules (CP-5, CP-6, CP-MODEL) need acceptance checks, not values.
