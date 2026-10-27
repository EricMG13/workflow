# Independent CP1B A1 core contract review

Result: **PASS** for the exact pre-implementation core lease and expected component guards below. The sole arithmetic-context clarification identified during this bounded review is closed. This is not owner/workflow/permission/CP5/render or checkpoint acceptance, and introduces no new gate.

## Reviewed identities and reused authority

- `docs/CP1B-CORE-LEASE.md` SHA256 `b32b91f8fdf562d101e3c37cd14336a640f1baeac6d4ced93111fc6bc21d767d`.
- `cases/earnings/expected.json` SHA256 `041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599`.
- C3 preparation `coordinator-3/docs/handoffs/earnings-preparation.md` SHA256 `246edc7d2dfb65a8d3eaa9737be7727147295fb5241caab8b7d4bea1ad444955`, preparation commit07cf6dee33006d629cee3aab2702cbc590eb5030 as identified by LEAD.
- The source-first financial/value conclusions of C3's completed independent Sol/high preparation review are reused. Their authority remains financial manifest6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432, financial source82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429 and identity74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4. No repeated financial audit was performed.

Adopted shape references inspected only as needed: deploy_vii/contracts.py Fact and ModuleView; financial_periods._id and financial_model._basis_id. No candidate earnings code/output was inspected.

## API, identity and boundary review

The single pure build_earnings_delta(ModuleView,prior_period_id,current_period_id) API and frozen slotted report/point records are bounded and coherent. Producer hash, selected period/basis IDs, primary fact IDs and companion IDs keep the result linked to its actual selected input facts. Neither input mutation nor new accounting, source handles, quotes or invented missing-period metadata are authorized.

ModuleView's CP1, artifact-hash and accepted/restricted checks are explicitly structural. ModuleView does not contain the authenticated run/issuer/current-attempt context needed to prove stale/foreign selection or grants. The lease correctly reserves those checks for the subsequent workflow/access bridge; component acceptance must not be presented as real source/permission authentication.

Exact T4.14 reported QUARTER/FY identities and T4.10 own historical basis joins are appropriate. The adopted historical model-basis length-prefixed identity keeps rolling/FY/Q4 equal-value aliases from substituting for selected coordinates. Q3 trailing leverage remains missing while Q4's standalone selected result may be known; A1 preserves those existing CP1 ratios rather than recalculating them on quarterly earnings.

The same-kind, equal-duration, forward/nonoverlapping period rule is an explicit narrow LEAD policy. It supports the frozen Q3/Q4 equal92-day comparison without implying a universal issuer comparability rule. Same/reverse and incompatible FY/quarter requests refuse. An absent requested prior FY2024 remains a comparative gap while the actual current FY2025 values/identities survive. Opening2024 is not fabricated as an income comparator. A selected row/basis missing within an otherwise present period is incomplete_register, distinct from a genuinely absent requested comparative period.

## Units, statuses and arithmetic

Amounts remain source-native USD MILLIONS/scale1000000. Multiples and percent fractions retain scale1/currencyNone. Amount/multiple deltas use current−prior in the input unit. Margin delta is100×difference in decimal fractions, explicitly PERCENTAGE_POINTS: the artificial.20→.25 guard gives5pp, not.05pp or5percent growth. Revenue/EBITDA/adjusted-EBITDA growth alone is(current−prior)/prior as a PERCENT fraction; other growth stays not_applicable.

Known flat results remain numeric0. Known-zero prior permits a known delta but yields missing growth with ZERO_DENOMINATOR, without infinity/zero substitution. Genuine comparative absence yields null prior fact/basis/value and missing delta/applicable growth with COMPARATIVE_NOT_SUPPLIED. Existing conflicting/missing/not_applicable inputs retain their limitations and explicit precedence; nongrowth measures still have not_applicable growth. No status/QA/promotion policy is added in A1.

The original local38/no-rounding wording could inherit caller rounding/traps and was ambiguous for repeating growth. The corrected contract explicitly requires a fresh Context(prec=38,rounding=ROUND_HALF_EVEN), no display quantization or operand pre-rounding, and caller context restoration even on refusal. It does not inherit caller Inexact traps. The new explicitly artificial G-CALLER-CONTEXT guard pins prior6/current7, delta1 and growth0.16666666666666666666666666666666666667 while caller precision9/ROUND_DOWN/Inexact trap=True remains restored. Its literal was independently checked with stdlib Decimal Context only; no product implementation or test was invoked. Numeric Decimal equality is appropriate; no representation-quantum requirement is inferred.

The malformed/nonfinite known/nonknown facts, dimensions/perimeter mismatch, duplicate selected identities, incomplete coordinates and invalid source view refusal names are consistent with the contract. Refusals return no partial report. The guard cases are component controls, not disclosure or actual nonzero earnings evidence.

## Ownership and acceptance limits

C3 owns exactly earnings.py, test_earnings.py and the named new core handoff. C1/C2 future shared registration/access/render preparation is docs-only until separately leased, with PM-only integration. The user-authorized uncapped implementation policy is preserved; no numerical lane cap is reintroduced and one-heavy-job admission remains.

A1 returns a core report, assigns no Module status and performs no journal settlement, authentic tool use, downstream integrity review or FP02 render acceptance. Complete current CP5 selected-scope verification and a real settled evidence-referencing CP5 review remain an explicit later dependency; lookup/rendering cannot substitute. Fresh upstream execution cannot relabel the old credit_snapshot run into earnings_update. Guidance, causal drivers, comparative income and broader nonzero earnings/other-owner/provider/production qualification remain open and explicitly limited. These dependencies do not prevent implementation of the small pure core.

## Route and activity

LEAD explicitly assigned this reused independent Sol/high financial/state reviewer under AGENTS.md; C3's preparation records its separate explicit independent dispatch. These are route/assignment records, not hidden runtime telemetry claims. This review was confined to the new A1 API/units/status/refusal/period policy and the corrected component arithmetic guard. No tests, engines, providers, browser, actual workflow or candidate output ran. Only this exact requested review file was written; no lease, oracle, source, journal or shared file was edited by this reviewer.
