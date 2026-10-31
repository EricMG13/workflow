# IHRT golden review (ihrt-distressed-restructuring), mx-precise

**Verdict: REVISE.** There is one High finding. Everything else is Low or Info.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/r-ihrt/probes/`. Run them from that folder with `python3 <name>.py`. They need `../txt/`, which `../dump.py` builds with check.py's `visible_text`.

## Gates
- `python3 -I cases/goldens/check.py cases/goldens/ihrt-distressed-restructuring`: exit 0.
- `derive.py`: exit 0, 0 mismatches.
- Derivation operands and operations are correct:
  - GrossPrincipal = secured + 8.375% + other unsecured = 5,236,876.
  - FiveInstrumentsPre = 5,231,609. This is the Existing Debt denominator: 4,824.2 / 5,231.609 = 92.2%, as the release prints.
  - Reduction 446.0 = old principal retired − new principal issued. Labelled "before cash", which is correct.
  - The exchange ratios exclude cash. FirstLienNew = three first-lien note series + New Term Loans = 3,703.0.

## Facts checked
I re-found about 120 of the 152 facts in visible text: CP-0, the whole Q3 Note 5 table and liquidity, every 10-K maturity, coupon and ranking, every 8-K exchange pair, cash amount, new-instrument term and lien class, the TSA %, and every credit-agreement term and remnant definition. All match except R1 to R3.
- Borrower, Holdings and parent are kept apart.
- Commitment ($2,145,724,113.92) is kept apart from the 8-K funded amount ($2,145.7m).
- Principal is kept apart from carrying amount (5,221,847).
- The $3.9bn market value is "based on market prices for which quotes were available". It is not a fair-value line, so the label is fine.

## Findings

**IHRT-R1 (High): `CP-2.liquidity.ABL.springing_trigger_availability_floor`.** The golden stores 40.0 (USD millions) as the trigger floor.
- Source: 10-K, Note 6 > ABL Facility > Certain Covenants. It reads: "If borrowing availability is less than the greater of (a) $40.0 million and (b) 10% of the aggregate commitments under the ABL Facility, in each case, for two consecutive business days (a "Trigger Event")".
- The trigger level is therefore the greater of $40.0m and 10% of commitments. On the $450.0m facility that is $45.0m.
- A model that answers "greater of $40m / 10%" or "$45m" would be marked wrong.
- Fix:
  - rename the field to a fixed-component name (for example `trigger_availability_fixed_component`);
  - add a percent fact, 10, for the commitment-based component;
  - or store the greater-of test as text.
- Probe: `r1_abl_trigger.py`, exit 1 (finding confirmed).

**IHRT-R2 (Low): `CP-2.debt_stack_pre_exchange.N8375_2027.ranking`, evidence quote.** The quote "effectively subordinated to all of iHeartCommunications' and the guarantors' existing and future indebtedness that is secured" appears 3 times in the 10-K.
- The first match is at offset 300120, inside the 6.375%/5.25% secured-notes paragraphs. The 8.375% section starts at 305805.
- So a first-match locator ties the unsecured-notes ranking to secured-notes text. The value itself is right.
- Fix: extend the quote with the text that follows it in the 8.375% paragraph, "(including the 6.375% Senior Secured Notes, the 5.25% Senior Secured Notes, the 4.75% Senior Secured Notes and borrowings under the ABL Facility and the Term Loan Facility)". I have not checked that the extended quote is unique.
- Probe: `r2_unsecured_quote.py`, exit 1.

**IHRT-R3 (Low): `CP-4.exchange_dates.Exchange.announcement_and_8k_filing_date` = 2024-12-23.** The sources disagree on the release date:
- The release reads "NEW YORK – December 23, 2024 – … today announced", and the 8-K exhibit index says "Press Release, dated December 23, 2024".
- 8-K Item 8.01 reads "On the Settlement Date, iHeartMedia, Inc. issued a press release announcing the closing". The Settlement Date is 2024-12-20.
- The 8-K signature date (December 23, 2024) does support the filing date.
- Fix: split the field into `8k_filing_date` (2024-12-23) and the announcement date, and record the announcement as `conflicting` or note the conflict.
- Probe: `r3_release_date.py`, exit 1.

**IHRT-R4 (Low): `context.json` `identity.sector` = "Media and telecom".**
- This is a suggestion from the form's datalist. No IHRT source prints it. "telecommunications" appears in the 10-K only as an advertiser category.
- The filings describe the company as "the leading audio media company in America".
- The G-8 ruling (cite the filing's description or leave sector empty and list it in needs_user_input) applies here too.
- Probe: `r4_sector.py`, exit 1.

**IHRT-R5 (Info): `CP-4C.post_exchange_classes.Rem2028Class.lien_rank` (missing).** I agree with `missing`.
- The gap_reason could also cite the credit agreement, §2.05(b) asset-sale prepayment. It reads: "other Indebtedness (other than the Existing Secured Notes (4.750%)) outstanding at such time that is secured by a Lien on the Collateral ranking pari passu with the Liens on the Collateral securing the Term Loans". This suggests, but does not state, that the 2028 notes kept pari first-lien status.
- Probe: `r5_2028_lien.py`, exit 1 (the passage is present).

## Completeness
All CP-2, exchange, CP-4, CP-4C and CP-2H items in the brief are present or correctly marked missing. Ratings: no filing names Moody's, S&P or a rating; only the step-down language appears, so `missing` is correct. Small omissions, none in scope:
- base-rate margins (TLF 2.00%, ITLF 2.25% with a 1.50% floor; CA Level 2/3 base-rate margins of 4.275% and 4.025%);
- ABL base-rate margin of 0.25–0.75%.

The Existing Term Loan remnant and the participation/total facts are under G-7 and are not re-reported.

## context.json
- The shape and enums match `build()`.
- Defaults: `peer_source` cp_dr_public, `basis` auto, empty issuer_market and user_multiple, `legal_documents` executed, assumptions null.
- run_type is research, pathway distressed_restructuring, as_of 2024-12-23. Current q3-2024 comes before prior q2-2024 in the file; both ids are valid.
- `parent_name` is iHeartMedia, Inc., which the form defines as the ultimate parent. Correct.
- Nothing is invented apart from the sector (R4).

## Judgment calls
I agree with all of them:
- Ranking taken from the 10-K: the Q3 filing does not repeat it.
- Second Lien maturity 2030: the body and the release beat the exhibit index.
- TL remnant marked missing: it is not stated, and G-7 is pending.
- 2028 lien missing: see R5.
- No assertion on the Repurchase Trigger: correct, since 44.6% < 90% is the model's inference to make.
- Section 7.11 as a maturity-tested, non-maintenance test: correct. The CA's "Applicable Consolidated Total Net Leverage Ratio" grid sets exchange prices; it is not a covenant.

## Financial gold
- FY2024Q3 cash: 431.764m in the gold, 431,764k in the golden. They agree.
- total_debt: 5221.847m in the gold, carrying 5,221,847k in the golden. They agree.
- Probe: `p5_fin_gold.py`, exit 0.

Not verified: about 30 facts were only checked by the checker's substring match, not by a second reading: the duplicate ABL rows in thousands vs millions, three TSA rows, and some CP-1A text. The redacted CA exhibits and schedules (Multi-Lien Intercreditor form J-2) are not in the corpus. I did not check that R2's extended quote is unique. Earlier 10-Qs (Q1/Q2 2024, Q3 2023) were not compared for changes to ABL or term-loan terms. I did not re-check the per-module fact counts in the prepare-report.
