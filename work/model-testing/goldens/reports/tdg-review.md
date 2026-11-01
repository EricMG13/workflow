# TDG golden review (mx-precise aa8d24aa, 2026-10-31), saved by the controller from the hand-back

**Verdict: REVISE.** 2 Medium, 2 Low, 1 Info. No wrong value or wrong subject.
- **Gates:** check.py exit 0 (174 facts); derive.py exit 0 (3 derivations, 6 tie-outs).
- **Probe:** `scratchpad/r-tdg/probe_tdg.py` exit 0 (run `vt.py` first).
- **Checked:** about 50 facts against the source (Note 8, Note 10, tranches, revolver, securitization, covenants, CP-1A). All match.
- **Codex spot-check, FY2025Q1:** cash 2,459, total debt 25,049, current 98 and LTD 24,302 all equal.
- **Derivations:** all correct (25,228 = 24,578 + 650; drawn = 910 − 61 − 849 = 0; 24,319 = 24,581 − 262 finance leases).

## Findings
- **TDG-R1 (Medium).** `CP-0.identity.Term_Loans_Facility_and_revolving_credit_facility.borrower_entity` is marked missing, but it is printed.
  - Source: 10-K FY2024 exhibit index, exhibits 10.37-10.40: "Amendment No. 2 to the Second Amended and Restated Credit Agreement, dated as of March 6, 2017, among TransDigm Inc., as borrower, TransDigm Group Incorporated, as guarantor".
  - Fix: set it known, value "TransDigm Inc.".
- **TDG-R2 (Medium).** CP-1A financing_events omit two in-scope events, both from the 10-K MD&A "Significant Transactions of Fiscal 2024":
  - Amendment No. 15, 2024-03-22: "repriced all of its $4,525 million in existing Tranche I term loans … and replaced all of its $1,708 million in existing Tranche H term loans due February 2027 with new Tranche K term loans maturing March 2030".
  - Amendment No. 16, 2024-06-04: "repriced all of its $997 million in existing Tranche J term loans … and (ii) amended and extended $2,644 million in existing Tranche I term loans … converting such loans into Tranche J term loans maturing February 28, 2031".
  - Fix: add both.
- **TDG-R3 (Low).** The covenant `ratio_definition` is known as net debt / EBITDA As Defined, but the Q1FY25 MD&A says "ratio of the amount of our secured indebtedness to the amount of our Consolidated EBITDA". Fix: mark it conflicting with both quotes.
- **TDG-R4 (Low), context.json.**
  - `parent_name` should be "TransDigm Group Incorporated" (the 10-K says "our wholly-owned subsidiary, TransDigm Inc.").
  - `guarantors[1]` should be "TransDigm UK" as printed, not "TransDigm UK Holdings plc".
- **TDG-R5 (Info).** `CP-1A.acquisitions.Product_lines_acquired_in_Q1_FY2025.cash_paid` = 29: the source says "total purchase price". Rename the field to purchase_price.

## Judgment calls
Agrees with 1, 3, 4, 5, 6 and 7. Disagrees with 2 on the parent only (see R4).

## Not verified
- The annual-report PDF.
- The FY2024Q2/Q3 filings for each event.
- The legal name of TransDigm UK.
- About 124 facts covered only by the checker's quote match.
