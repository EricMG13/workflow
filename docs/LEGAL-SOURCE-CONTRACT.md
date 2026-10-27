# Task3 legal source and independent expectation freeze

This contract adopts [cases/legal/manifest.json](../cases/legal/manifest.json) for the Task3 coherent financial/legal source and independent expected-result item only. It grants no implementation lease, source-access expansion, owner acceptance, settlement, downstream-consumption or rendered-output qualification. Actual CP4, complete selected CP5 consumption, FP04, CP2D/CP3C/CP4C and the complete covenant/refinancing pathway remain unverified. Live/paid/provider testing stays paused; later local work still requires exact ownership and the one-heavy-job gate.

The adoption starts from LEAD revision `c7471f126f5a75f01df8fd918434460aab5d8cc5` on2026-10-27. Requested source/oracle author route is GPT-6.1 Sol/high, assigned by LEAD; this records the assignment, not hidden telemetry. The separate independent Sol/high review returned **PASS for source/oracle freeze only** on the exact draft hashes below. This contract and the manifest preserve the reviewed source strings and numeric/expected-status literals; the exact final adoption bytes still receive LEAD/PR MANAGER's check.

## Reviewed identities and preservation

| Reviewed item | SHA-256 |
| --- | --- |
| Original manifest-draft.json | `0125c1baf8bb133b846a7ca3bbedd1cf581c069b0c834497b0620a27a0d65e9d` |
| Original legal-source-proposal.md | `5c2951eaf41ed04d1e60e9a74f75e6db8d07b2d6cd010e5a4f68f39a6cb132f7` |
| Independent review receipt | `f6b816587587d5eca6db808c5f8b3a2c4c60cea27bcbe1dba5d0769ddae6013a` |
| Existing cases/financial/manifest.json | `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432` |
| Existing identity source | `74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4` |
| Existing financial source | `82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429` |
| Positive legal source | `0f8accfde3ee2343306db00ead2aec8a15aed5bd84a22f5eb766dd859a6e70ec` |
| Missing-definition legal source | `ec59b199fb54fd01c4533c40871031b5bbb780e0275bf8a2fdfeae664914608c` |

The original proposal, draft and review remain under `work/legal-preparation/`; none is rewritten by adoption. `cases/legal/manifest.json` records their hashes and retains the draft's original inspected revision/file hashes as historical provenance, not a future-code certification. It includes exact copied financial oracle objects `q4_ltm_derived_source_units` and `q4_ltm_metric_oracle`, sourced from the unchanged financial manifest. No source financial number, expected financial result or financial definition is revised. There is no second financial engine or candidate-derived oracle.

Selected imported core is from committed snapshot `6441553936086c834be885e2f3d7cd7f0959aa5c` as recorded in docs/reuse/manifest.json. In particular, reviewed cp4_legal.py is SHA256 `1b2246ff9b0c0797c25d259c3e408436dfcc874b48be4cf1b2f77566c2bc4128`. Only the adopted imported files and current public adapters were read; mutable old-project files and wholesale additional imports are outside this freeze.

## Two fresh selected runs

| Field | Frozen value |
| --- | --- |
| issuer_id / issuer_name | `northbridge-synthetic` / Northbridge Synthetic Group |
| as_of / method_version / case_kind | `2026-01-10` / `deploy-v-r14` / `synthetic` |
| pathway / explicit requested_modules | `covenant_refinancing` / `(CP-4, CP-5)` |
| required dependency closure | CP0, CP1, CP4, CP5 |
| positive case / run_id | `legal-current-matching-definition` / `slice-legal-current-positive` |
| missing-definition case / run_id | `legal-current-missing-ebitda-definition` / `slice-legal-current-definition-gap` |
| source IDs in each pack | Exact unchanged `identity`, exact unchanged `financial`, one case-specific `legal-covenants` |

The explicit requested selection overrides the full pathway preset; do not silently select other owners or claim the entire pathway is complete. Each case needs a new pack and genuine CP0/CP1/CP4/CP5 chain. One legal source identity has one selected hash within each pack. Do not combine the two alternatives, rewrite a source under an active run, reuse old settled financial modules, or inject hand-built final Modules. Runtime pack/snapshot/ticket/fact/producer hashes must be genuine and retained later; this freeze does not invent them.

## Literal representation and governing locators

Each legal variant has exactly three supplied `page:1`–`page:3` text strings in the case manifest. Each page is literal UTF-8 LF text with no terminal LF. Join ordered page texts with U+000C and SHA256 those bytes. Pages1/3 are identical across alternatives. Page2 differs only in its descriptive heading and Clause2.3 definition. Retain raw page-joined bytes and exact spans in the future PreparedPack.

Media is `text/plain` and extractor is `supplied-representation`; `extraction_status=complete` means complete retention of supplied pages, not a complete agreement. This is an explicitly constructed located-page representation, matching the existing financial case. `preparation.text_content` actually emits `line:N`, while current `PackTools.read_pages` requires `page:N`; do not falsely claim automatic plain-text pagination or PDF extraction. If future execution uses a real automatically extracted file, its media, raw bytes and locators must be separately frozen and reviewed rather than silently substituted.

| Legal locator and line | Frozen substance and acceptance use |
| --- | --- |
| page:1 line4 | Execution attestation December30,2025; effective December31,2025; operative with no amendment/waiver through January10,2026; supersedes earlier selected terms. CP0 executed/current classification requires this evidence. |
| page:1 lines5–6 | Borrower is the same issuer, only for this agreement; Group is exactly the unaudited IFRS consolidated financial group. No guarantor/restricted group is established. |
| page:1 line7 | Sole `term-loan`, Northbridge Term Loan, senior secured; USD50m commitment fully drawn; zero mandatory annual amortisation; contractual maturity2029-12-31 unchanged. |
| page:1 line8 / page:3 line5 | Selected provisions only; omitted security enforcement, guarantees, defaults/cure/voting/other protections. Overall package needs Insufficient Information and an explicit limitation. |
| page:2 line3 | Debt at IFRS carrying value excluding BOTH finance and operating lease obligations, no other exclusions/pro-forma adjustments; matches canonical CP1 debt basis `carrying_value_excluding_both_lease_types`. |
| page:2 line4 | All reported closing cash eligible; restricted cash0; no short-term investment/other cash-like deduction; net debt not floored at0. |
| positive page:2 line5 | Covenant EBITDA equals reported EBITDA over trailing2025; no addbacks/exclusions/synergies/pro-forma changes; underlying financials remain unaudited. |
| gap page:2 line5 | Covenant EBITDA refers to missing incorporated Schedule A; no supplied addback/exclusion/reported-definition relationship. Financial EBITDA cannot supply that missing legal definition. |
| both page:2 line6 | Maximum maintenance test: `not more than 4.00x`, every calendar quarter end starting2025-12-31; current test uses closing net debt and trailing EBITDA; governs `term-loan`. |
| page:3 line3 | Additional debt/commitment requires every lender's prior written consent; maintenance limit creates no automatic additional debt basket or funding commitment. |
| page:3 line4 | Selected terms have no mandatory asset-sale debt-prepayment sweep; fair market value condition remains. No asset sale/leakage is established. |

Financial anchors remain page:1 reporting/zero disclosures, page:2 reported FY2025 EBITDA30, page:4 debt50/cash20/restricted cash0, and page:5 sole facility/commitment/drawn50,2029 maturity, carrying-value and reported EBITDA definitions. These are USD millions and IFRS consolidated, unaudited without an auditor. The new legal borrower definition does not create borrower-only statements, audited financials or a guarantor/restricted perimeter. Fresh CP0/CP1 reviews must distinguish the original two-source note's scope from the newly supplied agreement; do not repeat a stale blanket claim that no legal borrower is known.

## Independent numerical and status expectations

Current balance/test date is2025-12-31. Trailing EBITDA covers2025-01-01 through2025-12-31, matching reported FY2025 and the four discrete calendar quarters. Independent source arithmetic is50 − 20 =30USDm net debt, divided by30USDm reported EBITDA =1MULTIPLE. Legal current definitions, financial basis and actual offered metric must all match; equal present values alone do not establish equivalence.

| Output | Positive | Missing-definition case |
| --- | --- | --- |
| threshold_text / unit / value / comparison | `4.00x` / `multiple` / `4.00` / `<=` | Same |
| metric_basis | `Same definition`, supported by current cited definitions | `Not determinable` |
| reported comparator |1MULTIPLE, actual matching current offered fact | Same1MULTIPLE comparator may be visible; no contractual equivalence |
| headroom amount / unit |3MULTIPLE, from4 −1 | null; no legal headroom amount |
| headroom share amount / unit / display |0.75PERCENT fraction /75% | null; no share amount |
| T4.9 verdict | `Within threshold on the CP-1 metric` | `Not calculable` |
| T4C.9 calculable | `Yes` | `No` |
| gap reason | Selected-package/capacity limitations still retained | `Whether the covenant definition is the CP-1 metric's is not determinable` |
| overall lender protection | `Insufficient Information`, with omitted-protections limitation | Same, plus missing Schedule A |
| capacity amount | null/unsettled | null/unsettled |
| expected CP4 settled status | restricted from own selected-scope/capacity limitations | restricted from own gaps/calculability limitations |

The actual journal outcome must still be retained. Neither row promises a clean accepted whole-package pass. Python owns threshold parsing, arithmetic and verdict cells. Analyst prose must not author compliance/headroom conclusions or amounts; numerical financial prose uses only actual offered `{ref|unit}` references. Current CP4 does not compute monetary basket capacity. The exact capacity explanation is `Basket capacity amounts are not calculated: CP-4 quotes and interprets baskets in M8; unknown capacity is not zero`.

USD90m =4 ×30 −(50 −20) is only an independent arithmetic distance to the ratio limit. It must not be presented as a CP4 capacity result, legal debt permission, available commitment or funding. The facility is already fully drawn:50 −50 =0USDm unused commitment. Unanimous prior lender consent is required for additional debt or a commitment increase; no automatic debt basket is supplied. Unknown basket capacity and known zero unused commitment are different facts.

The future workflow lease must resolve one actual offered current CP1 T4.10 `net_leverage_reported` fact with reported EBITDA, MULTIPLE, the matching trailing2025 period and consolidated basis. Retain its exact current fact/coordinate/period/basis and operands. Equal FY/display-LTM/Q4 aliases do not permit arbitrary selection. Refuse absent, ambiguous or wrong-period identity rather than guess. For the exact missing-definition oracle, name the matching reported comparator with Not determinable; a null metric_ref would instead take the core's earlier `No CP-1 metric is matched to this test` branch and does not prove the frozen definition-specific reason. No runtime fact ID is manufactured by this contract.

## Semantic acceptance refusal is distinct from engine validation

Current cp4_legal._covenant_issues checks offered metric/unit/document/facility identity, but does not independently establish contractual definition equivalence. `_test` trusts analyst `metric_basis`. Correct Not determinable suppresses arithmetic; false Same definition on the gap source may calculate a pass. This source freeze does not claim otherwise or invent a general legal parser.

The adversarial case is the exact gap pack plus an incorrect `Same definition` judgment and its matching offered reported comparator. Its checkpoint result must be **REFUSE_SEMANTIC_ACCEPTANCE**: missing incorporated Schedule A does not support contractual EBITDA equivalence, a legal pass or headroom. Retain independent source-to-submission review that rejects that result before CP4 may qualify. This is a source-semantic acceptance condition, not an assertion that the current validator rejects it or that the journal necessarily refuses settlement. An implementation can instead receive a separate, precise, reviewed deterministic guard lease; no such guard/code change is granted here. Quote and parsed-threshold validity alone also do not prove current version, period, definition or perimeter.

## Source permissions and actual current API path

`preparedScope` is a descriptive source demand here, not an existing API field. Current objects are PreparedPack/Source/SourceAssessment/ConsumerReadiness/SourceContextReview. CP0 must assess all three prepared sources and each selected canonical live consumer CP1/CP4/CP5 exactly once, binding the new pack hash and located evidence. Legal authority is executed; financial/identity authority remains issuer. The positive and definition-gap CP4 source assessments are READY_WITH_LIMITATIONS for interpretation and honest gap reporting. Missing Schedule A prevents quantitative legal assessment but not recording the clause/gap. Intentionally gating the gap CONDITIONAL would stop execution and cannot count as CP4 gap-composition proof. CP1/CP5 retain appropriate financial/legal limitations. These are frozen readiness expectations, not already achieved outcomes.

The existing core path is registry CP4 `legal_covenants` pack-source capability → `live.context.declared_sources/readable_sources` → `cp4_legal.upstream_of(store, attempt).legal_sources` → ready pack sources classified executed/filed by bound CP0 → explicit `PackTools(pack, sources=legal_ids)` → bounded search/read and ToolRules → real `submit_cp4_step`. Never rely on the all-source fallback of a non-source step. Current public `SourceSession.from_execution` still refuses CP4 because `_SOURCE_STEPS` admits CP0/CP1 only. This is a documented missing implementation, not an existing public capability.

| Step | Required source/upstream boundary for a separately leased implementation |
| --- | --- |
| CP0 source_readiness | Read/search exact three-source set; no statement extraction. |
| CP1 source_context | Read/search current declared source map; distinguish financial consolidated and agreement-specific legal identities. |
| CP1 financials | Extract financial pages2/3/4, read financial definitions/disclosures/facility pages1/5 in that epoch; legal terms are not financial statements. |
| CP1 later stages | Existing adopted source-free projections, authentic QA and promotion. |
| CP4 legal_covenants raw | Only current ready `legal-covenants`, executed under bound CP0; search/read pages1–3; no identity/financial raw read, no extract_statements. |
| CP4 upstream | Current CP0 authority, current settled CP1 offered referencable T4.10/T4.17 figures, T4.18 facility ID/name and inherited gaps; no full Module dump. |
| CP5 integrity_review | Complete selected current CP1+CP4 producer/claim scope with producer-qualified references and separately permitted support evidence; internal complete mechanical checks; no raw-pack search/read/extract. |

CP4's cited-page/absence ToolRules require actual current-epoch read/search results: surfaced search snippets do not credit full page reads. Absence assertions need the admitted legal scope searched. A source attached in CP0's readiness demand does not grant that consumer raw source tools. Existing complete internal CP5 context includes quote-bearing claim citations; this source freeze grants no public quote/context dump. A later complete-scope lease must define safe sufficient upstream claim support evidence and references. Opaque citation handles alone do not prove semantic claim support.

Actual core contracts remain `cp4_upstream(pack, cp0, cp1)`, `upstream_of(store, attempt)`, `context_block(pack, upstream)`, `CovenantInterpretationSubmission`, `validate_covenant_interpretation(pack, submission, upstream, inputs)`, `covenant_interpretation(...)` and `submit_cp4_step(store, ticket_id, "legal_covenants", payload_json)`. Candidate construction via cp4_module/direct composition is component evidence only. Actual CP5 uses review_scope/python_checks/validate_integrity/integrity_review and `submit_cp5_step(..., "integrity_review", payload_json)` on the selected current journal scope. All current CP1+CP4 claims need exactly one review; CP0 is bound but not evaluated. Report status over the evaluated set and settled status with inherited limitations are distinct. Do not predeclare zero findings or accepted CP5 status.

## Remaining implementation gaps and actual closure evidence

Static review of current adapters confirms these requirements remain open:

- No public CP4 source epoch/submission-bound retained legal tool receipts. Source host `_producer_inputs` also requires non-CP0 producer inputs equal current_inputs; real promoted CP1 appends canonical provenance. CP4 admission must authenticate that genuine tail from actual promotion/envelope/retained stages, not strip it or disable validation.
- No explicitly leased bounded CP4 current-upstream view or authenticated legal workflow receipt/replay connecting tool calls to submission, validators/composer, settlement and selected consumer.
- Current CP5 v1 grants one CP1 producer and refuses claim-bearing/multi-producer integrity. Complete current CP1+CP4 selected scope, safe support evidence and actual settled integrity participation require a separate exact lease; a review JSON alone is insufficient. Reconcile with the separately planned CP1B complete CP5 work instead of creating a competing checker.
- Shipped CP4 maps exist, but report_view._spec_of defines credit/earnings compositions and falls back to Unbound/prose for FP04. Real owner-aware typed specs, authenticated selected-run rendering and native proof are still required.

The six CP4 FP04 assignments are covenant-tests-headroom→T4.9; capacity→T4.10; red-flags→T4.11; lender-protection-score→T4.13; ebitda-definition→T4C.6; documents-structure→T4.2/T4C.12. Positive cells must show3x/75% with scoped verdict and exact definition/date/quote/facility lineage; gap cells must show Not calculable, missing Schedule A and no headroom amount. Evidence must retain threshold check, metric binding, authority, source quotes, calculation trace and copied CP1 figures; Limitations must retain source scope, calculability, inherited unaudited/perimeter gaps and unsettled capacity. CP5 belongs in its Evidence/Limitations rails with real evaluated producer identities, findings/status and inherited limits.

Liquidity, maturity-wall analysis, funding gap, refinancing paths and LME creditor exposure belong to other owners. A CP4 document register can cite the unchanged2029 contractual maturity without qualifying those owners. Missing implementations cannot be disguised as source gaps. CP2D, CP3C, CP4C, full FP04 and the full pathway remain separate.

Before actual closure, retain fresh CP0 and all CP1 stages/QA/promotion; permitted legal source/current-upstream call arguments/results; raw submissions and exact successful-call bindings; genuine attempts/current inputs/settled hashes; complete CP5 scope/claim judgments/checks and actual submission/settlement; authenticated legal render receipts; native DOM/passport/source/calculation-link proof for both cases. Adversarial source-authority, unread citation/unsearched absence, stale/wrong producer, wrong threshold/metric/period/facility and false-definition cases must refuse at their stated boundaries without disclosure or manufactured evidence. No tests, engine execution or browser proof were performed in this source adoption. Future code changes require confidence-review and changed-function rewrite-tournament before completion.

Not verified: Actual CP0/CP1/CP4/CP5 participation for these new packs, settlements, complete consumer evidence, tests/engines/providers/browser, FP04 rendered/native proof, specialist owners or full pathway completion; this freeze admits no implementation lease.
