# CZR Q2 2026 earnings update: partial run (BLOCKED at CP-1 quality)

Status: **BLOCKED**. The run is rulings item 70 (CP-0, CP-1, CP-1A, CP-2, CP-5; no CP-1B; run id `czr-2026q2-earnings-update-no-cp1b-v1`). It stopped by the user's ruling, item 75 ("Record the proof, stop"; "Yes, commit the partial"), in `docs/rulings/2026-10-29-stage3.md`.

`submissions-partial.json` is deliberately not named `submissions.json`. `tests/czr_runs.py` `czr_closed` treats `submissions.json` as a complete recorded run.

## Result

Run 11, re-run on the committed file at `3e86d50`, takes 57.0 s and ends with the same refusal:

```
RuntimeError: submission not valid: invalid ['CP-1 QA Blocked: confidence 39 (Insufficient Information); a Blocked handoff is not promoted']
```

The refusal comes from `src/deploy_vii/cp1_workflow.py:346`.

| Step | Result |
|---|---|
| CP-0 `source_readiness` | accepted |
| CP-1 `source_context` | accepted |
| CP-1 `financials` | accepted: `extract_statements` on 7 statement pages (10-Q page 2, 4 and 9; 10-K page 54, 56 and 60; release page 6), 10 periods, 469 observations |
| CP-1 `narrative` | accepted, scope `data_quality_only` |
| CP-1 `readiness` | accepted: `{"consumers": []}`, provisional (synthetic precedent) |
| CP-1 `quality` | **refused**: QA Blocked |
| CP-1A, CP-2 (and its FIG binding), CP-5 | **not reached** |

## Why QA is Blocked

The narrative read body lists 138 reconciliation BLOCK gaps:

| Check | BLOCK gaps |
|---|---|
| `FY_QUARTERS` | 78 |
| `DEBT_TOTAL_EX_LEASES` | 10 |
| `SEGMENT_REVENUE` | 7 |
| `EBITDA_BRIDGE` | 7 |
| `ADJUSTED_EBITDA_BRIDGE` | 7 |
| `CFO_IDENTITY` | 7 |
| `NCF_IDENTITY` | 7 |
| `NCF_CASH_MOVEMENT` | 7 |
| `BALANCE_MOVEMENT` | 7 |
| `calculation_gate` | 1 |

Most of these need inputs that the three filings do not print:
- **No reported EBITDA line and no cost of sales line.** "Cost of sales" appears only in segment-expense prose (10-Q line 911, 10-K line 3088).
- **No four separate quarters for any fiscal year.**
- **No balance sheets at 2023-12-31, 2025-06-30 or 2026-03-31.**

The comparative columns cannot be left out, because the CP-1 precheck maps every printed column to a period.

A submission could clear only `calculation_gate`, `SEGMENT_REVENUE` and `CFO_IDENTITY`. Clearing those does not clear QA. The severity change that would let a public filed pack through is a design question on the owner list (item 75).

## Qualification keys

- **CP-1:** the key lines `Net revenues | 2,993 | 2,907 | 5,863 | 5,701` and `Operating income | 513 | 526 | 1,013 | 1,014` appear in the financials observation citations (10-Q page 4, release page 6). No CP-1 handoff settled, so no key is met.
- **CP-1A, CP-2, CP-5:** not exercised.
- **Out of scope:** the CP-1B keys, `decision_scope: FULL` and `FULL_CREDIT_32`.

## Reproduce

Run these from the repository root, using the lane Python:

```bash
python cases/czr-2026q2-earnings-update/partial-builder/run.py <empty-dir> cases/czr-2026q2-earnings-update/submissions-partial.json
```

To rebuild the stages:
- **`st0`, `st1`, `st2` and `st4`** rebuild byte-identically with `build.py <out.json> st0 st1 st2 st4`.
- **`st3` (narrative) and `st5` (quality)** read the read bodies from `partial-builder/dumps/`, which is not committed. `quality` alone is 16.9 MB.
  - To regenerate them, run `run.py` above and copy `read-1-narrative.txt`, `read-2-readiness.txt` and `read-3-quality.txt` to `dumps/narrative.txt`, `dumps/readiness.txt` and `dumps/quality.txt`.
  - On re-run, these read bodies were byte-identical to the dumps the stages were built from.
- **`st5`** builds `quality` mechanically from the read body's producer ceilings, with every claim marked material. It is provisional, like `readiness`.

## Not verified

- **That no submission could pass `quality`.** The unclearable gaps were classified by reading `financial_reconciliation.py` and checking the documents. No best-effort book with every fixable gap closed was built.
- **The provisional `readiness` and `quality` content**, beyond the fact that the workflow accepted `readiness`.
- **The documents against their SEC originals.**
