# Item 82 plan: absent-input reconciliation checks become a limitation (mx-autonomous a7f737a4, 2026-10-30)

The controller wrote this file from the planner's text report. The planner's probes are kept in `work/build/keep/s7-recon-plan/`.

## Headline
- **The change:** two files, `src/deploy_vii/canonical_audit.py` (the audit hop at :493-501) and `src/deploy_vii/canonical_gaps.py` (the period hop at :239-250). It is gated on `pack.run.case_kind == "public"`.
- **Effect on CZR:** 135 of the 138 BLOCK gaps become WARN.
- **CZR still blocks** on 3 gaps:
  - NCF_CASH_MOVEMENT fy-2025: reported -32, calculated 21, difference 53;
  - NCF_CASH_MOVEMENT h1-2026: 93 against 78;
  - `calculation_gate` ("Model requires an assessed complete add-back bridge; missing is not zero").
- **Checked:** the controller reran `probe_czr_after.py` at 23:2x, exit 0. It still raises `CP-1 QA Blocked: confidence 39`, with 3 BLOCK and 135 downgraded WARN gaps.

## Trace
1. `financial_reconciliation.py:166-167`: `_check` defaults to BLOCK.
2. `canonical_audit.py:493-501`: a non-PASS check becomes an `AuditGap` with `severity=status`.
3. `canonical_gaps.py:367-381`: the gap enters the ledger. Period checks enter at :239-250. `calculation_gate` comes in at :403-427, raised by `financial_adapter.py:196-198`.
4. `narrative.py:439-441`: any BLOCK gap makes the narrative "blocked". **This is the hop that blocks.**
5. `cp1_quality.py:67-68`: the module status follows the narrative.
6. `quality.py:221-226`: Blocked, with the score capped at 39.
7. `cp1_workflow.py:424-426`: `qa_blocked_issue`.

`_check` is left alone because the same register statuses feed `model_readiness.py:278-309`, where a WARN would let CP-MODEL go ready, and `period_reconciliation.py`.

## The change
- **Helper** `absent_input_limitation(...)` in `canonical_audit.py`. It returns None (stay BLOCK) unless all of these hold:
  - the case is public;
  - the status is BLOCK;
  - `difference is None`;
  - no term is a conflicting observation;
  - no term is FX-normalised.
  When they hold, it returns the prefix `Absent input, stated as a limitation on a public filed pack (rulings item 82): ` + the explanation + `; absent: <label (reason)>…`.
- **Applied** at the audit hop and at the period hop (`_calculation_gaps` gains `public` and `conflicting`).
- **Unchanged:** `financial_reconciliation.py`, `period_reconciliation.py`, `model_readiness.py`, `narrative.py`, `cp1_quality.py`, `quality.py`, `cp1_workflow.py`, `live/prompts.py`.
- **R2 holds already:**
  - a WARN gap makes the narrative "restricted", which caps QA at Restricted/59;
  - CP-1 can never be Passed, because `narrative.limitations` always has 4 entries;
  - the limitation reaches T4.12 and the head line "CP-1 QA Restricted: …".

## RED tests (new `tests/test_cp1_absent_input.py`)
1. A public case with segment disclosure partial gives a valid promotion: QA Restricted (score ≤59), 11 WARN gaps with the prefix, and the prefix in T4.12 and in the head.
2. The narrative is restricted and QA is not Passed.
3. Genuine CZR: `czr_closed` still raises `qa_blocked_issue(39, "Insufficient Information")`, with exactly 3 BLOCK gaps (2 NCF_CASH_MOVEMENT and 1 `calculation_gate`) and 135 WARN gaps with the prefix.
4. Guard: the same book as `synthetic` still blocks.
5. Helper unit test: it returns None for a difference, a conflicting term, an FX term, a non-public case, or a WARN status.

## Blast radius
- **Changed:** 2 src files and 1 new test file.
- **D12:** two `post_import_patches` records in `docs/reuse/manifest.json`.
- **Docs:** `cases/czr-2026q2-earnings-update/RESULT-partial.md`; `docs/MODULES.csv` row 3; the CZR entry in `lows.md`.
- **Fixtures, oracles, pins and golden hashes:** none change. Synthetic and private artifacts stay byte-identical.
- **R4:** no schema bump recommended. No public CP-1 head was ever promoted. A pending pre-change attempt fails closed. New artifacts carry the prefix.
- **Gates:**
  - suites `test_financial_workflow`, `test_source_workflow`, `test_source_tools`, `test_earnings_workflow`, `test_czr_*`, `test_defect_classes_cp1`; the fast set and `test_financial_render` at the end;
  - ruff, format and mypy;
  - suppressions;
  - `python3 -I cases/pins.py --check` (87);
  - D12 strict probe;
  - CZR replay.

## Risks
1. Under-declared disclosures (partial / not_disclosed / unknown) on a public case could hide a check that would disagree. Mitigated by the disclosure WARN gap, the T4.12 text and the Restricted cap.
2. An operator who wrongly marks a case public gets the downgrade.
3. A downgraded parent can quote a child's difference text. The child still blocks; no test covers this.
4. Conflicts still block independently.
5. Downgraded gaps leave the consumers' `blocking_gap_ids` (`downstream_readiness.py:304-311`), which changes CP-1A, CP-2 and CP-5 readiness. CP-MODEL stays blocked.

## Questions (Q1-Q5)
1. Gate on `case_kind == "public"`? Recommended.
2. Consumers stop treating downgraded gaps as blocking? Recommended.
3. Downgrade analyst-declared structural blockers literally? Recommended.
4. `calculation_gate` stays BLOCK? Recommended.
5. No schema bump? Recommended.

Not verified: no pytest was run; RED and GREEN are in-process simulations only. The hashes a schema bump would move were not enumerated. The conflicting and FX exclusions were not exercised on real data. It is unknown whether the CZR cash differences come from restricted cash or from extraction.
