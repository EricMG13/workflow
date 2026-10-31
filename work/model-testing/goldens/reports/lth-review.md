# LTH review: lth-covenant-refinancing (mx-precise, read-only)

**Verdict: REVISE** (one Medium; no High).

Gates: `python3 -I cases/goldens/check.py cases/goldens/lth-covenant-refinancing` exit 0; `python3 -I derive.py` exit 0 (7 OK).
Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/r-lth/` (redline renderer `redline.py` marks [-struck-] / {+inserted+} from the line-through and blue-underline styles).

## Sample checked (62 facts, all match)
- **CP-4.** 49 facts checked against my own redline rendering. Struck and inserted readings are all correct: 6.50→4.75; LC carve-out $20.0M→$90.0M; L/C sublimit $65M→$90M; revolver maturity 2026-12-02→2029-09-20; revolver SOFR margin 4.25→2.50; TL grid 4.25/3.25→2.50/1.50 and 4.00/3.00→2.25/1.25; floor 0.50→0.00; liquidity covenant of $100,000,000 struck; 15th flat 2.00/1.00 with the ratings grid struck; soft call No. 14→15; amortization dates; MFN 50 bps with the one-year sunset.
- **Other modules.** Dates, $995M/$205,528,469.96, Schedule A totals, and Sections 8.01(2), 8.04(1)-(3) and 7.12(2) also match. CP-2 (all 10-Q table rows, maturity ladder, revolver/LC/availability, cash, swaps, 5.659%) and CP-1A/CP-3C 10-K items (62.7%, 42.5%, 103%, 106%, make-whole) match on value, sign, period and subject.
- **Codex overlap.** Cash 175.509 and carrying debt 1515.911 agree.

## Findings
- **LTH-R1 (Medium): missing in-scope covenant change.** Topic: CP-4.financial_covenant.13th_amendment_financial_covenant_changes_section_7_12.
  - Source: a13, Annex I > "First Lien Net Leverage Ratio". The 13th strikes the numerator add-back: "pari passu in priority with the Liens securing the Obligations, [-plus, Existing Mortgage Debt and Capitalized Lease Obligations or any Refinancing Indebtedness thereof ...-]minus, the aggregate amount of cash".
  - The same amendment also rewrites "Test Period" ("{+financial statements were required to and have been delivered pursuant to Section 6.01(1) or (2) (or, at the Borrower's option, ...+}internal financial statements are available").
  - It also deletes the Covenant Modification Period carve-out and the Run-Rate EBITDA annualization proviso in 7.12(1)(a).
  - The brief requires the defined-term changes for each amendment. The golden records none of these, and `test_period` gives only the post-amendment text without the change.
  - Probe: `r1_13th_covenant_definitions.py`, exit 1.
- **LTH-R2 (Low): guarantor names mis-cased.** Facts: CP-2.obligors.subsidiary_guarantor_* (13 facts).
  - The values read "Ltf Club Operations Company, Inc." and so on. Source a15, signature pages: "LTF CLUB OPERATIONS COMPANY, INC., as Guarantor". The legal name is "LTF ...", as context.json has it.
  - Probe: `r2_guarantor_name_case.py`, exit 1.
- **LTH-R3 (Low): cure timing.** Fact: `...section_7_12_1_a_first_lien_net_leverage_covenant.cure_mechanism`.
  - The value says the Cure Amount is "received after the last Business Day". Source a13/a14, Section 8.04(1)(a): "actually received by the Borrower (i) on or after the last Business Day of the applicable fiscal quarter".
  - Probe: `r3_cure_timing.py`, exit 1.
- **LTH-R4 (Low): 13th revolver before-values missing.**
  - Source: a13, Annex I > "Applicable Rate" (b)(i): "(B) [-3.25-]{+1.50+}% for Base Rate Loans and (C) [-0.50-]{+0.25+}% Commitment Fee Rate". The 10-K confirms "from 50 basis points to 25 basis points".
  - Only the SOFR before-value (4.25) is a fact. The pre-13th leverage-only grid (>3.50x 4.25%, >3.00x 4.00%, ≤3.00x 3.50%) is also not recorded.
  - Probe: `r4_13th_revolver_before_values.py`, exit 1.
- **LTH-R5 (Info): stale limitation (G-1 tail).** Limitation 2 still says thousands values "carry scale null", but 22 facts now use `scale: "thousands"`. Update the text with the G-1 fix.
  - Probe: `r5_stale_scale_limitation.py`, exit 1.
- **LTH-R6 (Info): Codex principal gap.** Codex `LTH:FY2025Q2:principal` is `missing`, while the golden holds 1,534,149 (q225, "Total future maturities of long-term debt $ 1,534,149", equal to the component sum).
  - The golden is supported by the source. The report should note the difference so scoring does not treat it as a conflict.
  - Probe: `r6_codex_overlap.py`, exit 1.

## Completeness
CP-4/CP-3C/CP-2/CP-1A scope is otherwise covered. Two absent facts are acceptable omissions: the swap expiry (2028-04-05, notional amortizing) and the springing revolver maturity triggers. The triggers name instruments that the 14th's use of proceeds retired; the golden records the proviso text but not that it is moot.

## context.json
- **Form rules.** It complies with the build() shape: period format, enums, `peer_source` default, `legal_documents: "executed"`, null assumptions and empty quotes/ratings.
- **Valuation basis.** With `listed_equity: true` the form default basis is `issuer_trading` (BASIS_DEFAULT, form :529). That basis requires market data the user has not given, so `auto` is the defensible choice; no valuation module is in this pathway (Info).
- **Supported values.** Sponsor, sector, country, aliases and guarantors are all supported by the filings, and nothing is invented.

## Judgment calls
- **Agree.** Chain incomplete at the 15th: I confirmed that Annex II has no Maturity Date, 7.12 or 8.04 page.
- **Agree.** 13th split `conflicting`: Schedule A refinancing of $372.5M is less than the $475M that the recital says is "refinance[d] in full", and the corpus cannot reconcile them.
- **Agree.** `cashless_converted_principal` missing: Schedule A excludes Converting Lenders, and the Administrative Agent may allocate lesser amounts.
- **Agree.** "exceeds 30%" taken from the agreement over the 10-Q.
- **Agree.** The 15th is in scope at the cutoff.
- **Agree.** Borrower vs parent.

Not verified: the 2024-09-30 and 2025-03-31 10-Qs (no sampled fact cites them); the 14th Annex I beyond 7.12, 8.01, 8.04, Applicable Rate, Floor, Maturity Date, 2.07, 2.14(8) and 2.18; that no other 13th definition used in 7.12 changed beyond those my renderer flagged (the check covered the named terms only); the CP-1A cover-page facts (address, NYSE listing) beyond the quote check that check.py runs.
