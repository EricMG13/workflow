# IHRT scoped re-review (mx-precise a2a27b85), R1 + G-7

Verdict: APPROVE (spec PASS, quality PASS). check.py 0; derive.py 0. Probes: scratchpad/probe_ihrt_g7_crosscheck.py 0 (12 checks); scratchpad/probe_pct_operands.py cases/goldens 0 (0 hits).

- R1 closed: fixed 40.0 millions, 10 percent, rule text match 10-K Note 6 "Certain Covenants and Events of Default"; old id gone; "$45.0m" scorable as max(40.0, 10% x facility_size_commitment 450.0).
- G-7 correct: participation % (exchanged / same-instrument 2024-09-30 balance; round to the 8-K one-decimal figures); TLN 6.552 = 2265.252 - 2258.7 (approximate, subject says so); AllFive 407.434767; ProForma 4790.876 = gross - 446.0 (cash not double-counted; cross-check 4790.90 within rounding); 3.9 billions; derive.py mirrors check.py.
- IHRT-RR1 (Low): AllFive subject does not say one operand (TLN) is approximate; limitations do. End batch.
- IHRT-RR2 (Info): check.py:586 scales a percent operand at face value, so product/ratio with a percent operand is 100x. Latent: no current derivation affected.

Not verified: Existing Term Loan amortisation 2024-09-30 to 2024-12-20; R2-R5 outside scope.
