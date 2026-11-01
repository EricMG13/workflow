# LTH covenant_refinancing golden: prepare report

Check: `python3 -I cases/goldens/check.py cases/goldens/lth-covenant-refinancing` exit 0. `derive.py` exit 0 (7 derived facts).
Periods in context.json: calendar fiscal year, `q2-2025` current, `q1-2025` prior (Codex ids FY2025Q2/FY2025Q1).

## Fix round 1 (review LTH-R1..R6, findings G-8/G-9)
- CP-0 added (15 facts): legal name, ticker, exchange, state, offices, file number, filer status, fiscal year end, business description, borrower entity, 10-Q and 10-K period covered, 13th/14th/15th agreement dates. CP-0 removed from `not_golden`. `identity.sector` in context.json now uses the 10-Q's own wording ("premium health, fitness and wellness experiences"); no sector label is printed.
- Redline reading note added to `limitations` (concatenated quotes such as 6.504.75; post-amendment value in each non-"before" fact).
- R1: 4 facts `CP-4.financial_covenant.13th_amendment_covenant_definition_changes.*` (numerator add-back struck, Test Period rewrite, Covenant Modification Period carve-out deleted, Run-Rate annualisation proviso deleted).
- R2: the 13 guarantor values now read `LTF ...` as in context.json (signature pages print them in capitals; `printed` keeps the capitals).
- R3: `cure_mechanism` uses 8.04(1)(a) "on or after the last Business Day of the applicable fiscal quarter", with a second evidence quote.
- R4: `revolver_initial_margin_base_before` 3.25, `revolver_commitment_fee_before` 0.50 (10-K confirms 50 to 25 bps), `revolver_margin_grid_before` (the struck leverage-only grid is printed in full).
- R5: stale scale limitation replaced (scale `thousands` is used).
- R6: Codex marks `LTH:FY2025Q2:principal` missing while this golden holds 1,534,149 (thousands; "Total future maturities of long-term debt $ 1,534,149"). Scoring must not treat that as a conflict.

## Fact counts (165 before fix round 1; now 187 incl. CP-0 and the added CP-4 facts)
- CP-4: 69 known, 5 missing, 1 conflicting. Covers the 13th, 14th and 15th amendments (date, effective date, what changed), the covenant (type, 4.75x, 30% springing test, $90.0M LC carve-out, defined terms, cure, term-loan cross-default, waiver threshold) and the operative terms at cutoff.
- CP-3C: 20 known, 2 missing. Soft call (1.00%, six months, from 2025-08-18 and the lapsed 14th one), Repricing Transaction, All-In Yield, 50 bps MFN, margin step-downs, notes call terms.
- CP-2 (2025-06-30): 55 known. Principal vs carrying amounts, revolver $650.0M / drawn 0 / LC $31.5M / availability $618.5M, cash, maturity ladder, swaps, obligors.
- CP-2D: 1 known, 2 missing (horizon, minimum cash are user input).
- CP-1A: 10 known.
- not_golden: CP-1 (covered by financial_gold), CP-MODEL, CP-5.

## needs_user_input
`assumptions.cp2d`, `ratings` (S&P upgraded 2025-06-18 but no level is disclosed; the pricing grid keys on Ba3/BB-), `quotes` (no market price or OID), `assumptions.cp3c`.

## Judgment calls
- The 15th Amendment has Annex II changed pages only. The chain is incomplete: Maturity Date, Section 7.12, Section 8.04 and the revolver commitments are not restated. Covenant and revolver terms come from the 14th conformed text; the 2025 term loan maturity is the 14th rule (seven years after 2024-11-05, "November 2031" per the 10-Q). Recorded as `missing` "confirmed in 15th Annex II" facts.
- 13th Amendment incremental revolver split is `conflicting`: recital $175,000,000 vs Schedule A $277,500,000 (both totals reach $650,000,000).
- Before/after values come from the redline style markup; quotes show struck and inserted text concatenated (e.g. 6.504.75).
- Borrower is Life Time, Inc.; `parent_name` is LTF Intermediate Holdings, Inc. (direct parent); the listed issuer is LTH.
- The 15th is dated the cutoff date and is treated as in scope.

## Limitations
- Visible text cannot separate struck from inserted text (see the redline limitation in module_golden.json).
- Agreement says "exceeds 30%"; the 10-Q says "30.00% or more". The agreement is used.
- Notes call terms and ownership percentages come from the 10-K (2024-12-31) only.
- The 2024-06-30 10-Q is in the folder but not in the manifest; not used.
- Redemption prices from 2027-11-15, the Engagement/Fee Letter terms and the lender elections are not in the corpus.
- Scale `thousands` is used for the 10-Q table values per the coordinator ruling (limitation text updated).

Not verified: that the redline markup reading (struck vs inserted) is right where only the concatenated text is quoted; that the 15th Amendment leaves Sections 7.12/8.04 and the maturity unchanged (not shown in the provided pages); the amortization dollar amount and soft-call expiry date (no derive op for date or percent arithmetic, not recorded); any value outside the corpus.

## Batch fixes
LTH-RR1 Low wording: ...run_rate_adjusted_ebitda_annualisation_proviso_deleted value completed from the struck text (third Test Period: preceding three fiscal quarters times four thirds); quote unchanged and still contains printed. Checked CP-0.documents.15th_Amendment.agreement_date 2025-08-18: its quote prints "dated as of August 18, 2025"; no change needed.
