# Review: natl-portfolio-decision (mx-precise, read-only)

Scratch: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/r-natl` (probes and visible-text dumps made with check.py `visible_text`).

**Verdict: REVISE.** One Medium finding (a printed fact is marked missing with a wrong gap_reason). All 42 sampled values are correct.

## Gates
- `python3 -I cases/goldens/check.py cases/goldens/natl-portfolio-decision`: exit 0.
- `python3 -I derive.py`: exit 0. I checked the operands and operations, not just the arithmetic. Availability is 600 − 225 − 27 = 348, which matches the printed $348m. Total debt is 1,334 + 225 + 1,350 + 3 = 2,912, which matches the printed "$2,912 million" and the six table lines. Carrying is 80 + 2,789 = 2,869; principal less carrying is 43, which equals the printed (43). Net debt is 2,912 − 412. All are sound.
- `probe_facts.py`: exit 0. It covers 42 facts across CP-2, CP-4 and CP-1. For each one it checks the value, the 2025-09-30 column (anchored on the table header or the next column's value), the subject, and principal versus carrying. All pass.

## Findings

**NATL-R1 (Medium): guarantor names are printed but marked missing.**
- Where: `CP-2.obligor_structure.subsidiary_guarantors.names` and `needs_user_input` `identity.guarantors`.
- Golden: status `missing`. The gap_reason says Exhibit 10.1 describes the guarantors "by class only".
- Source (`NATL_legal_event_restated_credit_agreement.html`, Refinancing Facility Agreement §9): "The Company and each other Loan Party party hereto (collectively, the “Reaffirming Loan Parties”) … hereby confirms its respective Guarantees …".
- The signature pages name the Loan Parties: ATM NATIONAL, LLC; CARDTRONICS HOLDINGS, LLC; CARDTRONICS, INC.; CARDTRONICS USA, INC.; CATM HOLDINGS LLC; ATM DEPLOYER SERVICES, L.L.C.; NCR FOREIGN INVESTCO 1, LLC.
- Why it matters: the proposal makes guarantor names CP-1 input ("Roles only from filings"). A model that names these entities would be scored against a `missing` fact.
- Fix:
  - Record these names as `known` (the Loan Parties reaffirming Guarantees under the 2025-09-18 agreement), quoting §9 and the signature block.
  - Fill `identity.guarantors` in context.json.
  - Drop the guarantor entry from `needs_user_input`.
  - Say in the report that the source does not show whether the list is complete.
- Probe: `probe_guarantors.py`, exit 1 (finding confirmed).

**NATL-R2 (Low): the Term B gap_reason overstates the gap.**
- Where: `CP-2.debt_stack.term_b.principal_outstanding.2025-09-30`.
- Golden gap_reason: "no filing in the corpus states one".
- Source, Exhibit 10.1 recital: Existing Term B Loans "shall be refinanced and replaced in their entirety with a new tranche … in an aggregate principal amount equal to $320,000,000". Schedule I prints "Total $ 320,000,000.00".
- Source, Q3 10-Q Note 4: "The Revolving Credit Facility and the Term B Loans are not subject to amortization".
- So $320m on 2025-09-18 is printed, though no balance is printed at 2025-09-30. Keeping `missing` is defensible.
- Fix: the gap_reason should cite the $320m at 2025-09-18, so that scoring does not penalise a model that reports it with that date.
- Probe: `probe_termb.py`, exit 1.

**NATL-R3 (Low): total debt disagrees with Codex's gold and the difference is not explained.**
- Where: `CP-2.debt_stack.total_debt.principal_stated.2025-09-30` (2912) and the derived net-debt fact (2500).
- Codex gold: `total_debt` FY2025Q3 is `missing`, because finance-lease liabilities are not located. Codex's `funded_borrowing_carrying_ex_finance_lease` is 2869, which matches the golden's derived carrying amount.
- The golden's 2,912 is the company's own "our debt totaled $2,912 million" (10-Q MD&A). It is funded-borrowing principal and excludes finance leases.
- Fix: put this scope in the subject or a limitation (principal of funded borrowings, finance leases excluded) so the golden and Codex do not read as contradictory.
- Probe: `probe_codex_debt.py`, exit 1.

**NATL-R4 (Info): ATMaaS loan capacity omitted.**
- The 10-Q (Note 4, Other Debt) prints "The total amount available under the master loan agreement is $20 million". The golden records the $3m drawn but not the $20m capacity.

## Other overlaps with Codex's gold (all agree)
Cash 412; carrying debt current 80 and noncurrent 2,789; term loan aggregate 1,334; revolver 225; notes 1,350.

## context.json
The shape matches `build()` and the proposal:
- run_type `research`, pathway `portfolio_decision`.
- portfolio_workbook and prior_case are false; both are in needs_user_input.
- legal_documents `executed`, so CP-4 is not blocked.
- The valuation defaults (`cp_dr_public`, `auto`) and the empty issuer_market are kept. Nothing is invented: no ratings, quotes or peers.
- The only breach beyond G-8 (sector) is R1 (guarantors).

## Judgment calls (prepare-report.md)
- **Restatement as CP-1 text only:** agree. The brief says not to duplicate financial_gold. The line-item lists match the 10-K/A Note 18 tables, including LT borrowings 2,855 → 2,859 and loss on extinguishment 20 → 24.
- **Post-amendment clauses only:** agree. I confirmed the Maturity Date, the Applicable Rate (a)(iii), the "From and after the First Amendment" grid, the Permitted Leverage Ratio and §2.07 against the text.
- **Term B $320m as a commitment, not a balance:** agree. See R2 for the gap_reason.
- **Revolver $600m from the 10-Q:** agree.
- **Principal kept apart from carrying:** agree.
- **Sector:** already covered by G-8.

## Completeness against the brief
Restatement, debt stack, revolver commitment, drawn and availability, cash, and agreement terms (facilities, maturities, pricing, covenant type, levels, step-up, cap, definition, effective date) are all covered. The gaps are R1 and R4.

Not verified: complete enumeration of guarantors (the signature pages may not list every Subsidiary Guarantor); the strike/underline markup of Exhibit 10.1 (only the merged extracted text was read); facts I did not sample (about 50 of the 117, mostly text facts already found by check.py's quote search); the Q1/Q2 2025 and Q3 2024 10-Qs were not mined.
