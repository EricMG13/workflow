<!-- LEAD copy of work/lead/s1-preparation/report.md (derivation, LEAD rulings); reviews: s1-snapshot-oracle-review-precise-{1,2,3}.md. -->
<!-- Saved by LEAD from the S1 preparation agent handback, 2026-10-27. -->
I could not write `work/lead/s1-preparation/report.md`. The Write tool refused it ("Subagents should return findings as text, not write report files"). I did not work around that, so the full report is below for you to save. The other files are complete.

Paths (all under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-project-context-a11b1b`):
- `cases/snapshot/manifest.json`
- `cases/snapshot/submissions.json`
- `cases/snapshot/expected.json`
- `work/lead/s1-preparation/s1_data.py`
- `work/lead/s1-preparation/build_s1_oracle.py`

Summary:
1. I reran `python3 -I work/lead/s1-preparation/build_s1_oracle.py` and all three JSON files came out byte-for-byte identical (same sha256 before and after). The run is far under 60 s, so no heavy-job lock was needed. There were no network or provider calls.
2. The builder imports no product module. It uses stdlib only (hashlib, json, re, sys, pathlib) plus the local `s1_data.py`. I read the product sources and transcribed their composition rules by hand. The builder also checks its own inputs: frozen source hashes, quotes against page text, bare digits in run text, prohibited phrases, CP-1A reference existence, signal restatement and the confidence cap.
3. One new synthetic source, `business` (3 pages, sha256 `f79a1ce9093e39f61e1e863b92bd842250ce715f6f9db26b66fa1d62889e1d49`), is consistent with the frozen financials. The existing sources have no business, ownership or transaction content. The frozen identity and financial sources are untouched and hash-verified.
4. Positive and gap cases give literal CP-1A and CP-2 submissions and the expected rows. They cover all 23 CP-1A registers and CP-2's T2.1, T2.7, T2.10, T2.11, T2.12 plus its four Front Page tables. FP01 key-findings, company-operating-model, company-profile and strengths-weaknesses are covered, plus transaction-summary and the Evidence and Limitations rails. Governance composite is 3 (Medium), with 4 of 9 dimensions scored.
5. CP-0, CP-1 and CP-MODEL are covered only by reference to the frozen `cases/financial/manifest.json`. The four CP-1 ratios CP-2 uses are 50/30 = 1.67x, 30/30 = 1.00x, 30/5 = 6.00x and 9/50 = 18.0%. Later CP-5 is not composed. The oracle assumes `requested_modules` = CP-1, CP-MODEL, CP-1A, CP-2, which gives CP-1A the consumers CP-2 and CP-MODEL. Adding CP-5 adds a CP-5 row to downstream_readiness and T2D.10.

How each expected value was derived:
- New source text is invented to match the frozen figures: one segment, quarterly dividends, maintenance-only capex, one term loan maturing December 31, 2029, and nothing pending at 2026-01-10.
- Submission sentences are analyst judgment and are inputs, not oracle claims. Expected cells are the documented Python rules applied to them:
  - category labels appended on non-documentary rows;
  - Python-built source traces and sequential row ids (r01.., CP-2C-FLAG-001, CP-1A-GAP-001);
  - basis cells in CP-1A catalogue order;
  - gap cells for null measures;
  - the governance rubric (1/3/5, composite needs at least 4 dimensions);
  - READY/GAP snapshot rows.
- Figures in CP-2 text are `{{FIG:name}}` placeholders. They are replaced mechanically with the real CP-1 fact id once the CP-1 head exists. Unreplaced, they are malformed run text and fail closed.
- Zero, missing and blocked stay distinct: an undisclosed measure is a missing cell, an empty optional register is not_applicable, and nothing is shown as 0 or N/A.
- Gap case, business source missing. If CP-0 authorizes CP-1A, CP-1A settles restricted with Insufficient Information rows for business description, country, sector, ownership and transaction. Both snapshot and CP-2 then show gaps, and the Critical gap and Critical disclosure item feed CP-2's signals. If CP-0 does not authorize CP-1A, the expected outcome is a sketch only: no head, and FP01 shows "Not run: CP-1A has not run."

Open semantic questions for LEAD:
1. Does CP-0 authorize CP-1A when the business source is missing? The expected gap case assumes yes. The alternative (CONDITIONAL / DO NOT RUN, no head) is only sketched.
2. If CP-1A has no head, may CP-2 be ticketed? The registry edge CP-1A to CP-2 is "restricted", but I could not tell from reading how `current_inputs` treats an unrun CP-1A.
3. Which CP-0 source classes may CP-1A read? `live/context.py:85-87` falls back to all sources. The oracle assumes identity, financial and business are all in scope, and that CP-1A must assess every pack source exactly once.
4. Is the legal-covenants source part of the S1 pack? I assumed not.
5. Does the S1 run include CP-5 in `requested_modules` from the start? That changes the consumer rows.
6. CP-1 fact ids, labels and periods for the four ratios are not frozen anywhere. CP-2 basis cells therefore carry a template. I assumed percent facts are stored as fractions (0.18) and multiples as exact decimals; the 18.0% and 1.67x spellings depend on that.
7. G# gap numbers are report-wide and depend on module order in the view. The oracle writes "G#" without a number.
8. Is the transaction-summary block (owner "Primary") in S1 scope? CP-1A's binding map places two registers there, but the brief does not name it.
9. Is a governance composite of Medium on four thin dimensions acceptable, or should S1 expect "Not Scorable"? The choice comes from the analyst input I wrote, not from a product rule.
10. Both modules are expected to carry "Synthetic case; not real issuer qualification". Inherited limitations from CP-0 and CP-1 are not pinned.

Not verified: no product code, validator, renderer or test was run. The submissions are unproven against `validate_business_context` and `validate_credit_synthesis`. My transcription of the composition rules could share a misreading with the code under test. CP-1 fact ids and spellings, inherited limitations, G# numbers, the CP-5 variant, CP-0 authorization and the alternate gap branch were not checked. FP01 content was derived by reading `report_view.py`, not by rendering.

## LEAD rulings (2026-10-27)
- Q1, Q2: settled from code by the independent mx-precise review (CP-0 authorization of
  CP-1A without a business source; whether CP-2 may be ticketed when CP-1A has no head).
- Q3: keep the existing fallback (`live/context.py:85-87`): CP-1A reads every CP-0 pack
  source and assesses each exactly once. Per-owner source grants (D9) stay deferred.
- Q4: the legal-covenants source is not in the S1 pack (CP-4 is S2).
- Q5: S1a `requested_modules` = CP-1, CP-MODEL, CP-1A, CP-2. S1b is a separate run that
  adds CP-5; its oracle delta (CP-5 rows in downstream_readiness and T2D.10) is written
  with the S1b lease.
- Q6: CP-1 is verified, so CP-2 basis cells take fact ids from the verified CP-1 head at
  run time (identities, not values under test). The ratio values and spellings
  (1.67x, 1.00x, 6.00x, 18.0%) stay pinned in the oracle.
- Q7: the oracle pins the ordered list of gaps; G# numbers must be sequential in that
  order, not fixed literals.
- Q8: transaction-summary is in scope because CP-1A's binding map assigns registers there.
- Q9: keep Medium on four dimensions; it is the rubric's minimum and tests that boundary.
- Q10: the reviewer reports where inherited CP-0/CP-1 limitations come from; if the
  frozen financial oracle pins them, S1 pins the same text.

## LEAD rulings on review-precise-1 (2026-10-27)
- Finding 1 / Q1 / Q2: the gap case changes so CP-1A stays authorizable. The business
  source is present but omits ownership and transaction content; the literal CP-0
  submission pins READY_WITH_LIMITATIONS for CP-1A with a gap naming the missing content
  (method-consistent: the missing content limits, it does not prevent, CP-1A). CP-1A then
  settles restricted with Insufficient Information rows and CP-2 is ticketed. A wholly
  missing module source (CONDITIONAL / DO NOT RUN) is already covered by the financial
  precedent and is not repeated in S1.
- Finding 2: delete the extra `amount` key (s1_data.py:238).
- Finding 3: add literal CP-0 submissions (positive and gap) over the three-source S1 pack
  and their expected outputs: verdicts, T8 commands ("Run CP-1", "Run CP-1A", "Run CP-2"),
  restricted status; CP-1 runs on the S1 pack with the financial case's literal
  submission and the same four ratio values.
- Finding 4: the financial pack source carries the established limitation "Unaudited
  without auditor; borrower, guarantor and restricted perimeters unavailable." (as in
  tests/test_financial_workflow.py:22).
- Finding 5: T2.11 field ids are `mechanic` and `implication`.
- Finding 6 / Q10: with literal CP-0 submissions every inherited limitation is
  deterministic, so pin them all verbatim, in the product's order.
- Findings 7–12: fix all (cp1_references table; transaction-summary gap lines and
  collapsed summary; strengths-weaknesses note uses `not_in_pathway` for CP-6; tool use,
  consumption, no consumer of CP-2 in S1a and CP-MODEL not reading CP-1A stated as
  expectations; `assessment.limitation` on T2.1; gap limitations before composition).
- The builder must check submission keys against the product schema field names it
  transcribes (the quality gap behind finding 2), still without importing product code.

## Revision 2 (2026-10-27, after review-precise-1)
Preparation agent implemented all twelve findings and the rulings. New sha256:
expected.json 455cfb5d…a1c6, manifest.json 9db0367f…61b1, submissions.json d2fa2df9…bfbd.

LEAD rulings on its new questions:
- R2-Q1: CP-1's own limitations are pinned from the literal financial CP-1 submission
  (input text); CP-1's inherited list follows execution.py:345-366 over the S1 CP-0 head.
- R2-Q2: whether CP-1's source_context/readiness stages must assess the `business`
  source is settled by the re-review running the CP-1 validators over the three-source
  pack; if they must, S1 carries its own literal CP-1 submission.
- R2-Q3: CP-0 review prose is literal analyst input, so pinning it verbatim is allowed.

## LEAD rulings on review-precise-2 (2026-10-27)
- N1: S1 ships its own literal CP-1 `source_context` submission assessing identity, financial
  and business exactly once (the business entry classified and cited from the case pages, as
  the method requires); the other CP-1 stages stay the financial case's literal submissions.
  CP-1's note in expected.json must say so.
- N2: `cp1_references` copies keep the CP-1 fact's own `fact_id`, `value_class` "calculated"
  and the CP-1 fact's own citations (cp2_synthesis.py:837-857); ids and cites bind to the
  CP-1 head at run time, like the Q6 basis cells.
- N3: pin the FIGS basis per `metric_coordinate_rule` in cases/financial.
- N4: once N1 exists, pin CP-1's own and inherited limitations verbatim and drop CP1_TOKEN,
  applying execution.py:345-366 (own synthetic text and the repeated LIMIT drop out).

## Revision 3 (2026-10-27) and LEAD rulings
New sha256: expected.json 1aa49dd7…70f4, manifest.json 9db0367f…61b1 (unchanged),
submissions.json bff9ed18…b35c. N1 (S1 CP-1 `source_context` with a `business` entry),
N2 and N3 implemented; N4 replaced CP1_TOKEN with the execution.py:345-366 filtering rule.
- R3-Q1 (N4): option (a). CP-1's own and inherited limitation text binds from the CP-1 head
  at run time, as CP-1 fact ids do under Q6; the oracle pins the CP-0 literal part, the
  CP-1A/CP-2 tails and the de-duplication rule. Freezing product output (b) or hand-deriving
  CP-1's QA score (c) are rejected.
- R3-Q2: the gap `business` entry's `event_scan` of `unassessed` is confirmed: the reduced
  note makes no event disclosure, so `no_events_identified` would be unsupported.

## Revision 4 (frozen, 2026-10-27)
Applies review-precise-3 L1 (documentation only): `CP-1.business_entry.positive` and the
CP-1 tool-use expectation now name the reads, "read_pages business page:1 and page:3 and
search_pack over business before submit" (expected.json:31, :76). New sha256: expected.json
d1aa1af9…9baa; manifest.json and submissions.json unchanged. This is the frozen revision
(6e9305c) that the S1a lease pins. It was not re-reviewed after L1, and no revision 3 copy
survives to diff against.
