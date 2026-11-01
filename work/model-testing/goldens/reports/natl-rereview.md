# NATL scoped re-review (mx-feature a84b0092), R1 + G-8

Verdict: APPROVE. check.py exit 0. Probe scratchpad/probe.py exit 0 (22 of 22 evidence quotes re-found).

- R1: seven guarantor names match the signature blocks of NATL_legal_event_restated_credit_agreement.html, in print order, NCR Atleos Corporation excluded; §9 quote correct; needs_user_input entry gone; identity.guarantors is a flat list as build() writes; completeness limitation present (in a not_golden note).
- G-8: 13 CP-0 facts re-found (value, subject, period); sector "Financial technology (self-directed banking solutions)" paraphrases 10-Q Note 1; nothing invented.
- NATL-RR1 (Low): Loan Party status of the seven is inferred (§9 + parties clause + only non-Company/agent/lender signatories); the facts do not state the inference. Optional wording tweak; rides with the end batch.

Not verified: whether the seven are all the Loan Parties (Schedule 1.01 not checked); rest of the fix round; build() not executed.
