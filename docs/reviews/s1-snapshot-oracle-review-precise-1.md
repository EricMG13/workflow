<!-- Saved by LEAD from mx-precise review handback, 2026-10-27. -->
## S1 oracle review (mx-precise, independent), review-precise-1

**Verdict: CHANGES REQUIRED.** The CP-1A transcription is sound: with one input fixed, the product reproduces every expected CP-1A cell. Five things block freezing the lease:
- the gap case's expected branch depends on a live CP-0 judgment that nothing pins;
- the gap CP-1A submission fails the product validator;
- the S1 pack has no CP-0 expectations;
- one CP-2 table has the wrong field ids;
- the pack-source limitation for the financial source is not decided.

- **Spec verdict: CHANGES REQUIRED.** Findings 1, 2, 3, 4, 5 and 6 are requirement or invariant gaps. Findings 7 to 10 are coverage gaps under PLAN.md:7-8 and the completion rule at :142.
- **Quality verdict: CHANGES REQUIRED.** The builder does not check submission keys against the product schema, which is how finding 2 got through. report.md:13 says the builder checks "enum values", but `ENUMS` is only used to skip strings from the text checks (build_s1_oracle.py:115, 122-131). There is a latent mismatch in limitation order (finding 12). There are no stubs, fake values or catch-alls hiding failures. The `{{FIG:name}}` placeholders fail closed in the product, as designed: 6 refusals in the positive case and 5 in the gap case, listed under check 4.

### Checks performed
1. **Reproducibility: passed.** I copied the builder, the data file and `cases/financial/manifest.json` to `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-project-context-a11b1b/0917c043-263f-4fcf-9e1c-492a6fa1cd37/scratchpad/s1-review/` and ran `python3 -I` there (exit 0). The sha256 of all three outputs matches the repo files:
   - expected.json: a8b85c62…b680
   - manifest.json: 942c36e5…4173
   - submissions.json: 45ef989e…f20
   
   The only imports are hashlib, json, re, sys, pathlib and `s1_data` (build_s1_oracle.py:11-20). `s1_data.py` imports nothing. Nothing from `deploy_vii` is imported.
2. **Independence: confirmed by running the product composer on the oracle's own submissions.** I wrote the scratch scripts `.../s1-review/val/cp1a_check.py`, `cp2_check.py`, `fp01_check.py` and `alt_branch.py`.
   - CP-1A positive: 410 of 410 facts, table order, row labels, headers, columns, own limitations and claims are identical.
   - CP-1A gap: 314 of 314 identical, after removing the invalid key (finding 2).
   - CP-2: every text cell is identical, figure spellings included, apart from finding 5 and the template basis cells LEAD accepted under Q6.
   - FP01: identical apart from findings 8 and 9.
   - Every transcribed rule matches its source: register titles and columns (business_context.py:908-1040 against build_s1_oracle.py:167-191), keyed and unkeyed tables plus the empty-register rule (:1060, :1130-1178 against :219-248), the governance rubric (:827-864 against :309-353), signals (cp2_synthesis.py:273-297 against :419-434), and CP-2 basis order (:604-615 against :480-484).
   - I found two misreadings of the source code (findings 5 and 12). The other differences (findings 7 to 11) are content the oracle leaves out, not misreadings.
3. **Arithmetic: correct.** The FIGS values (s1_data.py:569-572) match `q4_ltm_metric_oracle` (cases/financial/manifest.json:198ff): 50/30, 30/30, 30/5 and 9/50.
   - Display rounds ROUND_HALF_UP on the exact Decimal (display.py:19, 23-27, 36-52). Multiples use 2 dp with "x"; percents are scaled ×100 and use 1 dp with "%".
   - That gives 5/3 → 1.67x, 1 → 1.00x, 6 → 6.00x and 0.18 → 18.0%. All four were confirmed through the product's `spelled()` on synthetic CP-1 facts.
   - The spelling assumes `Fact.decimals` is None (display.py:38-39) and an amount precise to at least 3 dp.
   - Zero, missing, blocked and not_applicable stay distinct, as rendered:
     - an undisclosed measure is `missing` and shows "∅ G#";
     - an empty optional register is `not_applicable` and shows "∅ G# n.m.";
     - no 0 or N/A appears.
4. **Product validators on the oracle's literal inputs.** I built the pack from the S1 manifest and ran the venv with `PYTHONPATH=src`.
   - `validate_business_context` (business_context.py:730):
     - positive: 0 issues;
     - gap: refused at shape level, `governance_and_sponsor.0.amount: Extra inputs are not permitted` (finding 2);
     - gap with the key removed: 0 issues.
   - `validate_credit_synthesis` (cp2_synthesis.py:463), against a hand-built Upstream with synthetic CP-1 facts carrying unit MULTIPLE or PERCENT, an amount and a calculation_id. It needs `referencable` CP-1 facts (business_context.py:355-364), so the placeholders do need real ids.
     - Positive, placeholders unresolved: 6 refusals:
       - assessment.rationale: malformed run text;
       - strengths[0]: no basis;
       - strengths[0].text: malformed run text;
       - strengths[1].text: malformed run text;
       - key_findings[0]: no basis;
       - key_findings[0].text: malformed run text.
     - Gap, placeholders unresolved: 5 refusals, the same list without strengths[1].
     - Both cases with `{T4.10.<name>.ltm|x or %}` substituted: 0 issues. The unit tokens "x" and "%" are accepted.
5. **Q1, Q2 and Q10**: answered below.
6. **Coverage**: see findings 7 to 10.

### Findings, by severity
1. **Critical: the gap case's expected branch is not determined by code.** expected.json:8694-8697, build_s1_oracle.py:711-716.
   - CP-0's readiness for CP-1A is the live model's judgment. The validator allows either:
     - READY_WITH_LIMITATIONS that attaches identity and financial with citations;
     - CONDITIONAL with `missing_source` (readiness.py:59-65, 364-389).
   - Python maps only CONDITIONAL or BLOCKED to "DO NOT RUN" (readiness.py:468-473).
   - The method text favours CONDITIONAL: "CONDITIONAL names a missing source that prevents that owner's workflow" (methods/cp0.md:65-66). The frozen precedent is `CP1_authorization: "CONDITIONAL / DO NOT RUN"` when a module's own source is missing (cases/financial/manifest.json:281-288).
   - Under that branch, expected.json:8697 ("CP-2 undetermined") is wrong. The correct outcome is that CP-2 cannot be ticketed (Q2).
   - FP01 for that branch, from an actual render:
     - key-findings: "Not run: CP-2 has not run."
     - company-operating-model and company-profile: "Not run: CP-1A has not run."
     - strengths-weaknesses: "Not run · Not in this Pathway: CP-2 has not run; CP-6 is not part of Credit Snapshot."
     - transaction-summary: "Absent: No module produces this block yet." (report_view.py:1092-1093, 1198-1203)
   - **Fix:** LEAD pins CP-0's expected verdict for CP-1A and CP-2 in the gap case, as cases/financial does. Then either make the "no head" branch primary, which leaves the gap CP-1A and CP-2 submissions unused in S1a, or change the gap so CP-1A stays authorizable.
2. **High: the gap CP-1A submission is invalid.** s1_data.py:238 adds a key `amount` inside `dict(G_DIVIDEND_POS, …)`, emitted at submissions.json:1140. `GovernanceItem` forbids extra keys (business_context.py:210-226).
   - **Fix:** delete s1_data.py:238. Its value equals the inherited `amount_funding_source`, so expected.json does not change. I verified that 314 of 314 facts then match.
3. **High: there are no CP-0 expectations for the S1 pack.**
   - The S1 pack has three sources, `requested_modules` [CP-1, CP-MODEL, CP-1A, CP-2], and live consumers CP-1, CP-1A and CP-2 (readiness.py:158-160).
   - The frozen financial CP-0 covered two sources and the consumer CP-1 only (cases/financial/manifest.json `run.requested_modules` [CP-1, CP-MODEL]). The pack hash differs, so CP-0 and CP-1 are not "already verified" for S1.
   - Expected for the positive case:
     - CP-0 restricted, since it is a synthetic case (readiness.py:526-528);
     - T8 `exact_command` "Run CP-1", "Run CP-1A" and "Run CP-2";
     - CP-1's four ratio values unchanged by the extra business source.
   - For the gap case, see finding 1.
4. **Medium: the financial pack-source limitation is undecided.** The oracle sets it to null (build_s1_oracle.py:57-58; manifest.json:83-95). The established construction gives it the limitation "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable." (tests/test_financial_workflow.py:22, 48-52; cases/earnings/owner-expected.json:96).
   - With it, `source_classification.r02.limitation` and `T2D.1.r02.limitation` both become "Unaudited; borrower, guarantor and restricted-group perimeters are not established; Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable." (business_context.py:1192-1196; verified by run).
   - It also enters CP-0's limitations (readiness.py:520) and from there every inherited list.
   - LEAD should pin one choice explicitly.
5. **Medium: wrong T2.11 field ids.** The builder derives fields from the labels with `snake()` (build_s1_oracle.py:457, 526-532), which gives `risk_mechanic` and `credit_implication`. The product fields are `mechanic` and `implication` (cp2_synthesis.py:524-533).
   - Affected: expected.json:7187-7236 (positive, r01-r03) and 13632-13681 (gap, r01).
   - **Correct:** `T2.11.rNN.mechanic` and `T2.11.rNN.implication`. The labels "Risk mechanic" and "Credit implication" stay as they are.
6. **Medium: inherited limitations are not pinned** (Q10). `settled_limitations` (build_s1_oracle.py:401, 565) holds own limitations plus the synthetic one only.
   - Pin the deterministic members: the pack-source limitations, verbatim. In the gap case that includes "Business and ownership note was not supplied".
   - Check model-authored CP-0 text only by inclusion.
7. **Low to Medium: the CP-2 `cp1_references` table is missing.** The product emits it (cp2_synthesis.py:837-860) and binds it to Evidence (bindings/cp2.py).
   - Expected: title "CP-1 facts referenced in CP-2 text", row_header "CP-1 fact", rows in first-spelling order. Positive: ref01 to ref04 (total leverage, net leverage, interest coverage, fcf_to_debt). Gap: ref01 and ref02 (total, net).
8. **Low: the transaction-summary gap lines are wrong.** The builder writes null text for the empty events_timeline (build_s1_oracle.py:602-607; expected.json:14311).
   - The product renders five gap lines (report_view.py:1407-1410): "Date / window: ∅ G# n.m.", "Event: …", "Credit relevance: …", "Status: …" and "Source: …".
   - The collapsed-block summary is also missing (report_view.py:1651):
     - positive: "Northbridge Term Loan: the only borrowing of the group, a senior secured term loan with final maturity on December 31, 2029; no new financi…"
     - gap: "Transaction context not established: no transaction source was supplied [Insufficient Information]"
9. **Low: strengths-weaknesses note wording.** build_s1_oracle.py:621 says "CP-6 has not run". In S1a CP-6 is `not_in_pathway` (registry.py:95-105).
10. **Low: coverage under the completion rule is incomplete.** Expected values are missing for:
    - tool use: CP-1A gets the pack tools plus submit (registry.py:351-356, pack_sources); CP-2 is submit-only (registry.py:360);
    - consumption: the CP-2 attempt binds the CP-1A and CP-1 head hashes (execution.py:247-249); CP-1A binds CP-1 as context (execution.py:226, 253-258), because plan order is CP-0, CP-1, CP-1A, CP-2, CP-MODEL;
    - a statement that nothing consumes CP-2 in S1a;
    - a statement that CP-MODEL does not read CP-1A. CP-MODEL requires CP-1 only, and cp_model_workflow has no CP-1A path. The CP-MODEL handoff row is analyst input only.
11. **Low: the CP-2 claim `T2.1.assessment` lacks its limitation** (build_s1_oracle.py:566 against cp2_synthesis.py:864-869). It should be `assessment.limitation`.
12. **Low (quality): limitation order differs.** The product adds gap limitations before composing (business_context.py:1673, cp2_synthesis.py:833). The oracle adds them after the empty-register ones (build_s1_oracle.py:226-228 against :297). There is no effect in these cases because no required register is empty.

### Q1, Q2 and Q10, answered from code
- **Q1. Code does not decide.** CP-0 authorizes CP-1A only if the live review judges it READY or READY_WITH_LIMITATIONS. Then T8 reads "Run CP-1A" (readiness.py:467-473) and `current_inputs` checks it (execution.py:259-267).
  - Both verdicts pass `validate_review`. In the gap case the review cannot attach the missing business source (readiness.py:365-376), and cannot be READY if a gap names CP-1A (:395-397).
  - CONDITIONAL leaves CP-1A with no ticket and no head: `begin` raises `NotAuthorized` (execution.py:210-219, 612-619).
  - The method and the precedent point to CONDITIONAL (finding 1).
- **Q2. No, CP-2 cannot be ticketed.** CP-1A is a required producer of CP-2 (methodology CP-2 requires CP-0, CP-1 and CP-1A).
  - `current_inputs` calls `bound("CP-1A")`. With no head it raises `ValueError("Required upstream is unrun, stale or blocked")` (execution.py:236-240).
  - The "restricted" edge applies only to a settled `blocked` head (execution.py:243-244). A blocked head comes only from a failed repair attempt (execution.py:436), which needs an authorized CP-1A ticket first.
  - This raise happens before the CP-0 check, so it is a plain ValueError, not NotAuthorized.
  - The lease walk begins nothing more after a refusal (OWNER-WORKFLOW-LEASE.md:105-110).
- **Q10. Source: `execution.inherited_limitations`** (execution.py:345-366), called at settle (:447).
  - For each bound input head it takes `module.limitations` plus `module.inherited_limitations`, de-duplicated, minus own limitations. The synthetic-case text is part of own (:441-446), so it drops out.
  - CP-1A inherits from CP-0, plus CP-1 when CP-1 is bound as context. CP-2 inherits from CP-0, CP-1 and CP-1A.
  - CP-0's limitations (readiness.py:518-531) are, in order:
    1. pack-source limitations;
    2. the review's source limitations;
    3. the review's consumer limitations;
    4. gap descriptions;
    5. the synthetic-case text.
    
    Items 2 to 4 are model-authored.
  - **cases/financial does not pin this text.** `required_limits` (manifest.json:290-295) are theme statements, and no test reads them. The exact "Unaudited without auditor…" string is a pack-construction input (tests/test_financial_workflow.py:22), not CP-0 output.
  - S1 should pin the pack-source strings verbatim and the rest by inclusion.
- **Which gap branch to expect:** pin CP-0 CONDITIONAL / DO NOT RUN for CP-1A, which matches the method text and the financial precedent. The "Not run" FP01 outcome under finding 1 then becomes the expected one. The current "primary" branch is only valid if LEAD instead pins CP-0 to READY_WITH_LIMITATIONS for CP-1A.

Not verified: no real CP-1 head was used. The fact ids, labels, periods, `decimals` and exact amount precision of the four ratios (and so their spelling on a real head) were checked only with synthetic Facts. No live CP-0 run was done, and no CP-0 or CP-1 output over the 3-source S1 pack exists. The inherited-limitation text and the `RefusedBegin` handling of the CP-2 plain ValueError were read from code, not executed. FP01 was rendered with `report_view.build` over a hand-built View (CP-1 left unrun) through the shipped bindings, not through owner_rendering or the HTML path. G# numbers were normalised before comparing. No repo files were edited; running the product under `PYTHONPATH=src` may have refreshed `src/**/__pycache__`. No run took more than 60 s, and there were no network or provider calls.
