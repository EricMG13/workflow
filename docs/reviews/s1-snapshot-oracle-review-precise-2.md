<!-- Saved by LEAD from mx-precise re-review handback, 2026-10-27. -->
## S1 oracle re-review (mx-precise), review-precise-2

**Verdict: CHANGES REQUIRED.** Ten of the twelve findings are fixed, finding 7 is only partly fixed, and the CP-1 part of finding 3 does not hold. Two things block approval. CP-1 cannot run with the financial case's literal submissions over the three-source pack (that is the R2-Q2 answer). The `cp1_references` copies of CP-1 facts are pinned with the wrong fact id and value class. Everything else the product composes matches expected.json exactly.

I broke the run budget once. A background run (CP-1 through the quality stage, positive then gap) went past 60 s. I killed it at the 120 s tool limit. The positive case had finished; the gap case had not reached quality. No other run took more than 8 s.

- **Spec verdict: CHANGES REQUIRED** (N1, N2).
- **Quality verdict: APPROVE with two low notes** (N3, N4). The builder now checks submission keys and enums against transcribed field lists without importing the product (build_s1_oracle.py:144-212). I found no stubs or catch-alls.

### Reproducibility and imports
- I rebuilt the oracle in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-project-context-a11b1b/0917c043-263f-4fcf-9e1c-492a6fa1cd37/scratchpad/s1-review/r2/` with `python3 -I` (exit 0).
- All three sha256 match the repo files: expected 455cfb5d…a1c6, manifest 9db0367f…61b1, submissions d2fa2df9…bfbd.
- The builder imports only hashlib, json, re, sys, pathlib and `s1_data` (build_s1_oracle.py:11-20). `s1_data.py` imports nothing.

### Validator results (product, `.venv` python, `PYTHONPATH=src`)
- **`validate_review` (CP-0):** 0 issues for both cases over the three-source pack, with `pack_sha256` bound to `PreparedPack.content_hash()`.
  - `live_consumers` is (CP-1, CP-1A, CP-2).
  - `build_readiness` gives all 56 facts with ids, text and cites identical to expected. The only exception is the T7.run.preparation placeholder, which is the pack hash.
  - Limitations are identical. T8 `exact_command` is "Run CP-1", "Run CP-1A" and "Run CP-2" in both cases.
  - `settle` gives status restricted.
- **`validate_business_context` (CP-1A):** 0 issues for both cases, run against the settled CP-1 facts.
- **`validate_credit_synthesis` (CP-2):**
  - With the `{{FIG}}` placeholders unresolved it fails closed: 6 refusals in the positive case and 5 in the gap case, the same as round 1.
  - With them resolved to `{id|x}` or `{id|%}` it returns 0 issues in both cases.
- **Settlement chain.** I settled CP-0, CP-1 (a synthetic head carrying the CP1_TOKEN), CP-1A and CP-2 through the product's `settle`, `head_of` and `current_inputs`.
  - CP-1A inputs are prepared-pack, CP-0 and CP-1; CP-1A and CP-2 are both restricted.
  - Own limitations, settled limitations and the inherited lists for CP-1A and CP-2 equal expected.json exactly in both cases, with the token standing in for the CP-1 entries.
- **Composer diff:**
  - CP-1A: 410 of 410 facts (positive) and 374 of 374 (gap) identical. Claims are identical.
  - CP-2: everything matches except `cp1_references` (N2). That includes T2.11 `mechanic`/`implication`, the T2.1 claim limitation and the own limitations.
- **FP01** (rendered with `report_view.build` and the shipped maps; CP-1 left unrun in the view):
  - key-findings, company-operating-model, company-profile, strengths-weaknesses and transaction-summary match on state, owner, kind, lines, tabs and collapsed summaries in both cases. G# numbers were normalised before comparing.
  - The gap transaction-summary gap lines now match.

### The twelve round-1 findings
| # | Status |
|---|---|
| 1 | Fixed as ruled: the gap note lacks ownership and transaction content, CP-0 gives CP-1A READY_WITH_LIMITATIONS, and both "Run CP-1A" and the CP-2 ticket were verified. |
| 2 | Fixed: the validator now passes. |
| 3 | CP-0 part fixed and verified. CP-1 part not fixed: see N1. |
| 4 | Fixed (manifest `financial_pack_limitation`); composed cells match. |
| 5 | Fixed. |
| 6 | Fixed: matches the product's settle except for CP1_TOKEN (see N4). |
| 7 | Partly fixed: the table was added but its fact ids and value class are wrong (N2). |
| 8 | Fixed. |
| 9 | Fixed. |
| 10 | Fixed: the tool-use and consumption statements agree with registry.py:351-360 and execution.py:226-267. |
| 11 | Fixed. |
| 12 | Fixed: own-limitation lists are identical. |

### R2-Q2: does CP-1 need to assess the `business` source?
Yes.
- **The literal financial context fails over the S1 pack.** I ran `validate_source_context` with `tests/test_financial_workflow.py`'s `context(pack)`. It refuses with "Assess every prepared source exactly once" (source_context.py:183-187). The same refusal comes through the workflow's `source_context` stage, because cp1_workflow.py:113-116 calls that validator.
- **The rest passes once a business assessment is added.** I added one entry for `business` (classification `nonfinancial`, one cited page:1 quote, `event_scan` "unassessed"). Then `source_context`, `financials`, `narrative` and `readiness` all passed unchanged, with `readiness` given `{"consumers": []}`, in both cases (gap: 8 s). The positive case then passed `quality` and settled a restricted CP-1 head.
- **The ratios on the real head are correct.** On that head, T4.10 has the four ratios on the Q4 25, FY25 and LTM Q4 25 bases:
  - total leverage 1.6666…7 MULTIPLE, spelled 1.67x;
  - net leverage 1.0, spelled 1.00x;
  - interest coverage 6, spelled 6.00x;
  - fcf_to_debt 0.18 PERCENT, spelled 18.0%.
  
  All have `value_class` "calculated" and `decimals` None. Fact ids look like `interface-fact:<sha256>`.
- **N1 (High) follows from this.** submissions.json `cp1_submission` and expected.json `CP-1.note` say CP-1 runs with the test's literal submissions "unchanged except for the bound pack". That is false. S1 must carry its own literal CP-1 `source_context` submission that adds a `business` assessment; one passing form is the entry described above. The other stages can stay literal.
- I did not run `quality` on the gap case (budget).

### New findings
- **N1 (High):** submissions.json `cp1_submission` and expected.json `CP-1.note`, as above. Correct value: S1 ships a literal CP-1 `source_context` submission that assesses identity, financial and business exactly once.
- **N2 (Medium):** the `cp1_references` copies are misread (build_s1_oracle.py:678-684; expected.json, both CP-2 `cp1_references` tables).
  - The product copies each CP-1 fact and changes only `table_id`, `row_id` and `field`. It keeps the original `fact_id` and cites `fact_ids=(fact.fact_id,)` (cp2_synthesis.py:837-857).
  - So each copy's fact id is the CP-1 fact's own id (on a real head, `interface-fact:<sha256>`), not `cp1_references.refNN.value`. That makes the oracle's note "fact id of the copy is the table coordinate" wrong.
  - `value_class` should be "calculated", not null.
  - `cites` should be the CP-1 fact's own citations, not [].
  - The row labels stay a run-time template, as ruled under Q6. A real label looks like "LTM Q4 25 (2025-01-01 to 2025-12-31) · total_leverage_reported · LTM Q4 25: 2025-01-01 to 2025-12-31".
- **N3 (Low):** the FIGS coordinate "twelve months to 2025-12-31" (s1_data.py FIGS; submissions.json `figures`) matches two CP-1 bases with identical dates, FY25 and LTM Q4 25. The spelled value is the same either way, but the basis cell and the `cp1_references` label differ. Pin which basis, following `metric_coordinate_rule` in cases/financial.
- **N4 (Low):** expected.json keeps CP1_TOKEN in `inherited_limitations`.
  - Under R2-Q1 these entries are now deterministic. The positive CP-1 head carries 20 own limitations (ending with the synthetic-case text) and inherits only the LIMIT text ("Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable.").
  - When the token is instantiated, CP-1's synthetic-case text must drop out (it is own) and so must its inherited LIMIT, because LIMIT already appears earlier (execution.py:366).
  - The oracle can pin those entries verbatim once N1's literal CP-1 submission exists.

Not verified: the gap-case CP-1 `quality` stage and promotion, so I have no real gap CP-1 head or limitations. FP01 was rendered with CP-1 unrun and through `report_view.build`, not the owner_rendering or HTML path. CP-2 and FP01 checks used a synthetic CP-1 head; real ratio facts were inspected only on the positive run. The CP-1 run used my own business-source assessment, not a frozen S1 submission. No live model, provider or network call was made. Running the product may have refreshed `src/**/__pycache__`. One run exceeded the 60 s budget and was killed.
