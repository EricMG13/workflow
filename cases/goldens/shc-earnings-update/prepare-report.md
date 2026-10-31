# SHC earnings_update gap-layer preparation report

Case `shc-earnings-update`; cutoff and as_of 2025-08-08; preparer mx-feature.

## Coverage
- CP-0: 16 known facts (registrant identity, ticker, file number, shares at 2025-07-29, sponsors from the FY2024 10-K, borrower Sotera Health Holdings, LLC vs listed parent, guarantor class, segments, document dates, unit).
- CP-1B: 49 known + 2 missing. Current (3 months to 2025-06-30) vs prior (3 months to 2024-06-30) for consolidated revenue, Sterigenics/Nordion/Nelson Labs revenue and segment income, net income, Adjusted EBITDA; 9 derived changes (`derive.py`, printed $ change used as cross-check only). Debt facts: Refinancing Term Loans gross 1,498,030 vs net 1,470,889 (thousands), original principal $1,509,350,000, margins/floor/step-down, weighted average rates, maturity; secured notes; revolver commitments $600.0m, drawn nil, LCs $14.2m, availability $585.8m. Missing: margin tier in force at 2025-06-30; FY2025 guidance.
- CP-1D: 30 known facts: 15 reconciliation lines x 2 periods (net income to Adjusted Net Income to Adjusted EBITDA).
- not_golden: CP-1 (financial_gold), CP-MODEL, CP-5.

## Period labelling
Calendar fiscal year. Context uses q2-2025 / q2-2024. Prior is q2-2024 because the 10-Q prints the two quarters side by side; same kind and earlier, as the form requires. Codex cp1b_delta_inputs.json uses Q1-2025 vs Q2-2025 instead; that sequential pair is not covered.

## Judgment calls
- Amounts printed in USD thousands are stored as printed (e.g. "294341", scale thousands); millions-printed amounts stay millions. derive.py converts mixed scales exactly.
- Brief dates Amendment No. 4 at 2024-08-05; that is the filing date of the 10-Q carrying it. The amendment is dated 2024-05-30.
- The revolver commitment of $600.0m is from Amendment No. 5 (2025-04-30), after Amendment No. 4.
- Printed dash recorded as 0 (Illinois EO settlements, Q2 2024).
- Guidance recorded missing; the 2024-05-30 8-K 2024 interest outlook is stale and noted only in gap_reason.
- Context: peer_source left at the form default; `basis` is `auto` by choice because no market data exists (the form default for a listed issuer is `issuer_trading`); listed_equity true with market data empty; management_bridge false; guarantors lists only the parent; sponsor from the 10-K risk factor.
- Debt facts are tagged module CP-1B (no debt module in this pathway).

## Checks run
`python3 -I derive.py` exit 0 (all derivations and subtotal checks agree). `python3 -I cases/goldens/check.py cases/goldens/shc-earnings-update` exit 0.

## Open questions
See `needs_user_input` in module_golden.json (market data, ratings, quotes, guarantor names, guidance, bridge).

Not verified: Q2 2024 as-originally-filed values vs the recast prior-year column: only the CP-1D Business optimization / Secondary offering costs split (593 + 20 = 613) is recorded as a limitation; other lines were not compared; the margin tier at 2025-06-30; no independent re-extraction of quotes beyond the checker; nothing live-run against a model.
