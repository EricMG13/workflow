# SHC golden review (mx-precise a906417d, 2026-10-31), saved by the controller from the hand-back

**Verdict: APPROVE.** No High or Medium findings.
- **Checked:** 96 of 97 facts re-found in the source (value, sign, scale, period and subject). Nothing in scope is omitted.
- **Gates:** derive.py exit 0; check.py exit 0.
- **context.json:** passes the form rules; nothing is invented.
- **Judgment calls:** agrees with the amendment date 2024-05-30, the revolver from Amendment No. 5, guidance recorded as missing, and debt facts tagged CP-1B.
- **Codex financial_gold, FY2025Q2:** agrees on revenue 294.341, NI 7.962, adjusted EBITDA 150.735, revolver availability 585.8 and total principal 2248.030. Codex DA 34.948 = depreciation 23.024 + amortisation 11.924.

## Findings
- **SHC-R1 (Low).** prepare-report.md says the basis was "left at form defaults". For a listed issuer the form default is `issuer_trading` (context-form.html:529, :1120). `auto` is the right value because there is no market data. Fix: correct the report wording only.
- **SHC-R2 (Info).** CP-1D `Business optimization expenses.amount.2024-06-30` = 0.613 follows the restated prior column in the Q2 2025 10-Q. The as-filed Q2 2024 10-Q shows 593 plus a separate "Secondary offering costs" line of 20. Fix: add a limitation saying the prior column is the restated one. Probe: `scratchpad/r-shc/prior_asfiled.py` (exits 1 by design).

## Not verified
- Margin-label naming ("Senior Secured Leverage Ratio" in the 10-Q vs "Senior Secured First Lien Net Leverage Ratio" in the amendment).
- The sector and country labels are inferred, not printed.
- The Codex comparison covers FY2025Q2 only.
- Amendment No. 5 is not in the corpus.
