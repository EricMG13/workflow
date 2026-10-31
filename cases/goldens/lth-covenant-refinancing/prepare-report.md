# LTH covenant_refinancing golden: prepare report

Check: `python3 -I cases/goldens/check.py cases/goldens/lth-covenant-refinancing` exit 0. `derive.py` exit 0 (7 derived facts).
Periods in context.json: calendar fiscal year, `q2-2025` current, `q1-2025` prior (Codex ids FY2025Q2/FY2025Q1).

## Fact counts (165)
- CP-4: 69 known, 5 missing, 1 conflicting. Covers the 13th, 14th and 15th amendments (date, effective date, what changed), the covenant (type, 4.75x, 30% springing test, $90.0M LC carve-out, defined terms, cure, term-loan cross-default, waiver threshold) and the operative terms at cutoff.
- CP-3C: 20 known, 2 missing. Soft call (1.00%, six months, from 2025-08-18 and the lapsed 14th one), Repricing Transaction, All-In Yield, 50 bps MFN, margin step-downs, notes call terms.
- CP-2 (2025-06-30): 55 known. Principal vs carrying amounts, revolver $650.0M / drawn 0 / LC $31.5M / availability $618.5M, cash, maturity ladder, swaps, obligors.
- CP-2D: 1 known, 2 missing (horizon, minimum cash are user input).
- CP-1A: 10 known.
- not_golden: CP-0, CP-1 (covered by financial_gold), CP-MODEL, CP-5.

## needs_user_input
`assumptions.cp2d`, `ratings` (S&P upgraded 2025-06-18 but no level is disclosed; the pricing grid keys on Ba3/BB-), `quotes` (no market price or OID), `assumptions.cp3c`.

## Judgment calls
- The 15th Amendment has Annex II changed pages only. The chain is incomplete: Maturity Date, Section 7.12, Section 8.04 and the revolver commitments are not restated. Covenant and revolver terms come from the 14th conformed text; the 2025 term loan maturity is the 14th rule (seven years after 2024-11-05, "November 2031" per the 10-Q). Recorded as `missing` "confirmed in 15th Annex II" facts.
- 13th Amendment incremental revolver split is `conflicting`: recital $175,000,000 vs Schedule A $277,500,000 (both totals reach $650,000,000).
- Before/after values come from the redline style markup; quotes show struck and inserted text concatenated (e.g. 6.504.75).
- Borrower is Life Time, Inc.; `parent_name` is LTF Intermediate Holdings, Inc. (direct parent); the listed issuer is LTH.
- The 15th is dated the cutoff date and is treated as in scope.

## Limitations
- Visible text cannot separate struck from inserted text.
- Agreement says "exceeds 30%"; the 10-Q says "30.00% or more". The agreement is used.
- Notes call terms and ownership percentages come from the 10-K (2024-12-31) only.
- The 2024-06-30 10-Q is in the folder but not in the manifest; not used.
- Redemption prices from 2027-11-15, the Engagement/Fee Letter terms and the lender elections are not in the corpus.
- Scale `thousands` is used for the 10-Q table values per the coordinator ruling.

Not verified: that the redline markup reading (struck vs inserted) is right where only the concatenated text is quoted; that the 15th Amendment leaves Sections 7.12/8.04 and the maturity unchanged (not shown in the provided pages); the amortization dollar amount and soft-call expiry date (no derive op for date or percent arithmetic, not recorded); any value outside the corpus.
