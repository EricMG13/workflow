# BGS golden review (mx-precise a2f0b9d6, 2026-10-31), saved by the controller from the hand-back

**Verdict: REVISE.** No golden value is wrong.
- **Checked:** all 105 facts against the Q2 10-Q. `probe_values.py` found 0 mismatches over 60 numeric facts.
- **Gates:** derive.py exit 0. check.py exited 1 at review time on G-2 (zero-width quotes); checker fix 2 has since fixed that and the case now exits 0.

## Findings
- **BGS-R1 (Medium).** The golden's principal (Note 6 total of 2,011,375, plus per-instrument face amounts) is correct and printed. Codex's financial_gold marks `BGS:FY2025Q2:principal` missing with "do not disclose a complete outstanding-principal balance by instrument", which is wrong.
  - Fix: explain the disagreement in prepare-report.md.
  - Owner: report the Codex gap upstream. It predates this change: send it to the user or Codex.
  - Probe: `scratchpad/r-bgs/probe_codex_principal.py` (exit 1). Cash 54,084 and carrying total 1,990,481 agree with Codex.
- **BGS-R2 (Low).** The leverage covenant keeps 7.50x but leaves out the step-downs. Note 6: "7.25 to 1.00 for the quarter ending January 2, 2027, and 7.00 to 1.00 for the quarters ending April 3, 2027 and thereafter". Fix: add the step-downs.
- **BGS-R3 (Low).** CP-3C has no mandatory prepayment terms. Note 6: "the credit agreement provides for mandatory prepayment upon certain asset dispositions or casualty events and issuances of indebtedness". Fix: add them.
- **BGS-R4 (Low).** The 8.00% notes priority fact (`CP-3D.priority_structure.8.00_senior_secured_notes_due_2028.priority.2025-06-28`) leaves out ranking items (3) "effectively junior to ... future secured debt, secured by assets that do not constitute collateral" and (4) "senior in right of payment to ... subordinated debt". Fix: add both.
- **BGS-R5 (Info).** The prepare-report "checker exits 0" claim was stale at review time.
- **BGS-R6 (Info).** The "Thereafter" maturity row is stored as 0 from a printed dash. This is correct (same pattern as G-4).

## Judgment calls
Agrees with all: Q2 10-Q only; 475 and 430 kept as separate facts; carrying amount from Note 7 and principal from Note 6; hierarchy level missing except for the revolver; the 89.98% repurchase is not a quote; floors missing.

## Probes
`scratchpad/r-bgs/`: probe_quotes 0, probe_g2 0, probe_values 0, probe_corpus 0, probe_ctx 0, probe_codex_principal 1, probe_gaps 1.

## Not verified
- 10-K guarantor subsidiary names.
- The July 2025 amendment document.
