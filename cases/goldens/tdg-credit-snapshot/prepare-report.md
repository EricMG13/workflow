# tdg-credit-snapshot prepare report

Pathway credit_snapshot, issuer TransDigm Group Incorporated, cutoff 2025-02-04. Periods use the issuer's fiscal labelling: current_period q1-2025 (quarter ended 2024-12-28), FY ends 30 September. Sources: Q2FY24, Q3FY24 10-Qs, FY2024 10-K, Q1FY25 10-Q.

## Fact counts per module (178 total)
- CP-0: 17
- CP-1A: 32 (includes the two Amendment No. 15 and No. 16 term-loan events added in fix round 1)
- CP-2: 116
- CP-3: 1
- CP-4: 12
- Not golden: CP-1 (financial_gold), CP-MODEL, CP-5, CP-6.

## Judgment calls
- Borrower is TransDigm Inc. (10-K exhibit index 10.37), parent TransDigm Group Incorporated; borrower and parent are kept distinct.
- Revolver drawn balance is derived (commitments - letters of credit - availability), as no drawn amount is printed.
- Covenant ratio_definition is conflicting: the covenant paragraph says net debt to EBITDA As Defined; the non-GAAP paragraph says secured indebtedness to Consolidated EBITDA. Value is null with both quotes.
- The acquisition amount is recorded as purchase_price (source: "total purchase price"), not cash paid.
- attachments.legal_documents is "executed" (ruling G-6).

## Limitations
- The Credit Agreement, indentures and Exhibit 22.1 are not in the corpus; CP-4 rests on 10-K/10-Q descriptions only.
- Guarantors: the full list is in Exhibit 22.1; only classes named in the debt note are filled. "TransDigm UK" is as printed; its legal name is unconfirmed.
- Covenant text was identical in all four filings; only 2024-12-28 is cited.
- Debt-stack total excludes the securitization facility; the maturity schedule excludes finance leases and securitization.
- Hedging, swaps and other leases are not covered.

Not verified: the FY2024 annual-report PDF; the legal name of TransDigm UK; the Q2/Q3 FY2024 filings for each financing event; about 124 facts covered only by the checker's quote match; Exhibit 22.1 guarantor list; the credit agreement text.
