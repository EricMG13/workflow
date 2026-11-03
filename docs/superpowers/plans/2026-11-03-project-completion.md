# Project completion: workflow validation and testing

Date: 2026-11-03. Revised after the adversarial review and the user's clarification:
**Pre-Testing does all testing and related work needed to prove the workflow
functional, and nothing else.**

**End goal:** the supported workflow produces and populates the correct deliverables
with complete, accurate, source-supported information. Module and pathway completion
are judged by those delivered results, demonstrated offline and live end to end.

Session: **Pre-Testing** (`01a19e99-1022-7c82-bbd3-f970feca89ab`).
Companion: [product implementation and other completion work](2026-11-03-product-completion.md).
Evidence: [session/worktree audit](../../reviews/2026-11-03-pretesting-completion-audit.md).
Review: [adversarial findings and resolutions](../../reviews/2026-11-03-completion-plan-adversarial.md).

This replaces the earlier mixed execution plan. It preserves the 26-owner/six-pathway
completion scope and existing authorities. Writing this plan does not resume a stopped
test campaign, launch providers or qualify any product behavior.

## Ownership boundary

| Pre-Testing owns | Separate product session owns |
|---|---|
| Test strategy, coverage register, independent answer keys, fixtures and recordings | Module, source/parser, financial, state/store and orchestration implementation |
| Test/verifier code, scoring and completeness checks, test harnesses, test-run accounting and launch gates | Product defects found by tests; shared runtime defects even when exposed by the harness |
| All workflow checks: module, integration, regression, offline/live end to end, failure/recovery, CI verification and rendered/browser acceptance | Product UI/design changes, supported rendering contracts and production integration preparation |
| Failure diagnosis/reproduction, defect handoffs, retests, evidence and completion verdict | Product/status documentation updates from accepted evidence; unrelated research and comparison preparation |

Location alone does not determine ownership: testing code under `src/` still belongs
to Pre-Testing; a product bug exposed by a test still belongs to the product session.
Pre-Testing may fix its own harness, verifier or scoring defects under reviewed leases.
It does not implement a missing owner, change product behavior, redesign the UI, or
run unrelated OCR/provider research or the alternate coding-agent/API campaign.

Within Pre-Testing, oracle preparer, verifier author and test-infrastructure builder
remain different agents under CLAUDE.md. A test author cannot manufacture its own
financial expectations from the candidate. Product agents complete their required code
reviews; Pre-Testing owns test authoring, execution and acceptance, including the
development probes needed by those reviews.

## Starting evidence and completion contract

The audited baseline is `codex/checkpoint@b2dcf6a2`; CP1 candidate
`codex/cp1-chain-proof@e5a65b0f` is separate. These are snapshots to recheck at intake.
22 analytical identities are implemented; CP3B/CP6A are still aliases. Full preset
delivery and SHC comparative earnings are incomplete. Current public-fact mapping is
360/1,175. Run6522 stopped in CP1A; it did not reach CP2, Model or report. None of
these states qualifies the full workflow.

The completion universe is:
`CP-0, CP-1, CP-1A, CP-1B, CP-1C, CP-1D, CP-2, CP-2A, CP-2D, CP-2E,
CP-2G, CP-2H, CP-3, CP-3B, CP-3C, CP-3D, CP-4, CP-4C, CP-5, CP-6,
CP-6A, CP-8, CP-DR, CP-L10, CP-MODEL, CP-OS`.

For each analytical owner, prove a positive chain through actual permitted product
tools → validated/settled output → named downstream consumption → assigned rendered
output. Also prove negative/refusal behavior: actual attempts and refusal records →
the expected downstream block/gap, without inventing settlement or successful consumption.
Record offline coverage and actual live participation for every analytical owner.
CP-MODEL/CP-OS qualify deterministically within those runs.

Every complete pathway must retain frozen context/source identities, tool arguments
and results, submission/settled heads, consumer references, authenticated receipts,
report and applicable Model/calculation artifacts. Evaluate every required fact against
independent keys. Coverage and accuracy are separate: unevaluated facts cannot disappear
from the denominator. Preserve exact values, units, periods, entity/definition identity,
zero versus missing, approved rounding and citation locators.

### Definition of successful completion

| Level | Required observable result |
|---|---|
| Module | Its required facts, calculations and analytical conclusions satisfy the independent key and adopted method; its genuine downstream consumer uses those results; every assigned deliverable section, table, chart or field contains the correct resulting information. All applicable content, provenance, refusal and offline/live comparisons pass. |
| Pathway | From the supported user/context/source entry point, the complete workflow produces the exact required deliverable set for that pathway. Every required section is populated correctly, all contributing modules satisfy their contracts, and report, Model, calculation data, charts, evidence and limitations agree wherever applicable. Complete offline and live runs prove this on the qualified release. |
| Project | All 26 owners and all six pathways satisfy these contracts, including supplemental positive cases for capabilities absent from public anchors. The final acceptance index links each required delivered result to its passing comparisons and actual run evidence. |

Before acceptance, Pre-Testing freezes a **deliverable contract** for each pathway
and supplemental chain: required artifact names/types; required sections and fields;
the module and downstream consumer responsible for each; independent key file/JSON
pointers; expected values, calculations and analytical duties; source/citation rules;
and exact rendered/output locators and comparison commands. These contracts make
"correct deliverable" and "fully populated" independently checkable.

All required content must be evaluated and all required comparisons must pass.
Numerical facts/calculations use the key's explicit rounding/tolerance rules.
Qualitative analysis is assessed independently against source evidence and the adopted
method: conclusions must be supported, assumptions explicit and required reasoning
present; matching a preferred wording is not the criterion. Check consistency across
modules and across the visible deliverable and its underlying calculation data.

A missing required value, blank/placeholder section, unsupported assertion, wrong
period/unit/entity, stale result or contradictory output fails its positive case.
An unavailable input may produce a gap only where the independent contract expects
one, and required positive functionality still needs a populated positive case.
Successful execution, valid receipts, file creation or green component tests are
supporting evidence; they cannot close a module or pathway whose delivered content
fails this contract.

| Pathway | Public anchor | Observable proof |
|---|---|---|
| credit_snapshot | tdg-credit-snapshot | Credit synthesis, legal/relative-value inputs, challenge, cash-flow Model and evidence |
| earnings_update | shc-earnings-update | Actual comparable periods, deltas/quality, integrity and populated earnings output |
| relative_value | bgs-relative-value | Peer/security/market comparisons, liquidity and research consumption when selected |
| covenant_refinancing | lth-covenant-refinancing | Authorized covenant facts, maturities/refinancing and legal limitations |
| distressed_restructuring | ihrt-distressed-restructuring | Downside/forward/rating/recovery chain and honest legal refusals |
| portfolio_decision | natl-portfolio-decision | Distinct CP3B/CP6A, synthesis, challenge, history and portfolio presentation |

Public cases may lack quotes, holdings or prior outcomes. Preserve their honest-gap
keys and add independently prepared positive test inputs or authorized supplied data.
A gap-only public run cannot qualify positive functionality. Include supplemental
chains for owners omitted by presets, notably CP2E, CP-DR, CP-L10 and portfolio owners.

## T0 — reconcile testing work and ownership

- [ ] Recheck relevant heads, dirty files and existing test evidence from the audit.
  Preserve all workers and historical failures; do not merge whole old branches.
- [ ] Retain the CP1 round4 auditor worker and mechanical budget-renewal worker as
  **testing-related work in Pre-Testing**. Their starting base is `e5a65b0f`.
  Transfer any product-source change to the separate product session under an exact lease.
- [ ] Preserve the three model-testing ledger corrections and ignored review receipts.
  Ask PR MANAGER to integrate admitted records selectively; source changes already
  integrated do not need rebuilding.
- [ ] Refresh CI through the existing PR MANAGER connection. The audit saw failed
  checkpoint shard `41624475483`, pending heavy tests and cancelled tests. Retrieve
  actual failures before diagnosing; a snapshot or unavailable log is not a pass.
  Pre-Testing owns the test/CI diagnosis; route product fixes to the product session.
- [ ] Create `work/pretesting-completion/ledger.md`, a coverage register and a defect
  register. These are planned artifacts, not evidence that currently exists.

**Exit:** each open testing task, product dependency and historical result has one
owner and an evidence-backed state. Do not reopen closed stages for Low-only findings.

## T1 — build the independent proof before product dispatch

Pre-Testing owns this preparation; product implementation waits only for the keys and
comparisons needed by its own lease, not for every unrelated test to be complete.

- [ ] Freeze owner × pathway × case × mode × configuration coverage, including
  dependency closure, assigned blocks, positive cases and failure/gap cases.
- [ ] Freeze each deliverable contract above. Map every required delivered field,
  section, chart and analytical duty to its producer, consumer, independent expected
  result and runnable comparison. Missing mappings block the affected acceptance.
- [ ] Preparers resolve semantic questions from adopted sources and write pinned
  answer keys before evaluating candidate output. Independent precise review checks
  financial/stateful expectations. LEAD resolves cross-module/oracle questions.
- [ ] Author runnable comparisons for CP3B/CP6A, SHC Q2/Q2 CP1B, full preset delivery,
  supplementary consumption, browser-visible values and complete fact coverage.
  Use the project's create-prove-it process. A missing comparison blocks that build.
- [ ] Finish all required fact mappings from the 360/1,175 starting point; add new
  owner/fixture facts to the denominator. Independently justify any true non-goal.
  The completeness check must fail when a required fact is unevaluated.
- [ ] Prove comparisons reject removed facts, wrong unit/period/entity, stale producers,
  zero changed to missing and absent assigned sections. Test known-good cases too.
  Do not weaken a key or label a broken positive case a gap to obtain a pass.
- [ ] Prepare complete offline recordings/fixtures with source hashes, provenance and
  expected tool/consumer effects. Record whether responses are retained live transcripts
  or scripted offline inputs. Scripted responses drive the real product tool and
  settlement loop; they are not proof of live model quality. Do not inject final heads,
  receipts, pass scores or composer outputs. Offline preparation must not depend on a
  future successful live run; an incomplete recording blocks only its case.
- [ ] Qualify the claimed source profiles, including real native-text PDFs and the
  requested bounded OCR fallback. Keep VMO2 mixed-entity/uncovered rows explicit.
  If image-only support is required for a named case, give it independent source keys
  and positive/refusal tests; product implementation goes to the product session.
  A broad OCR benchmark or engine-selection exercise is outside this plan.
- [ ] Complete the approved RUN-P5 fourth auditor round under its existing lease and
  frozen wording proposal, with confidence-review, rewrite-tournament where applicable,
  named probes and scoped reviews. Do not reset its fix count or authorize a fifth.
  Finish the separate budget-ruling/checksum renewal and test its launch controls.
- [ ] Prepare exact run cards using the admitted revision's actual CLI/API. Each names
  cases/configurations, offline inputs or live authority, absolute output/accounting
  roots, expected terminal states, comparison argv and estimated maximum cost.
  If the current CLI cannot select the authorized bounded matrix, fix/test the harness
  here before launch; do not improvise unsupported flags or broaden the run.

**Exit:** reviewed frozen keys, working comparisons, usable fixtures, reviewed testing
infrastructure and an executable run card for each admitted scope. This is test readiness,
not a product pass.

## T2 — admit a fixed candidate

The product session supplies the source/review handoff described in its companion plan.
Pre-Testing assembles `work/pretesting-completion/releases/<release-id>/manifest.json`
and an admission record. Paths here specify future handoff artifacts, not new executable
commands or an already implemented validator.

The manifest records:

- Product commit and runtime/render asset hashes; dependency lock hash; testing/verifier/
  scoring revision and hashes; source/context/recording/key/mapping hashes.
- Deliverable-contract version/hash and the complete artifact/section/content inventory.
- Exact admitted scope, owner/consumer/block matrix, key file and JSON pointers,
  runnable comparison argv, expected statuses and authorized run cards.
- Product and test review receipts, cumulative fix-round counts, required CI/local checks
  and any explicit unresolved dependency. No unresolved High/Medium in the tested scope.
- Output and shared ledger roots; authority references, permitted config/case matrix and
  budget/attempt constraints. No secrets or credential values.

Pre-Testing records admission only after checking these fields. It runs from its own
clean checkout of the admitted code, never an actively edited product worktree. Mutable
run outputs are outside the source snapshot. A recorded revision mismatch, missing key,
missing comparison, failed prerequisite or active writer rejects the affected admission.

Freeze the test instruments for the run as well as the product. A harness, scoring or
oracle correction creates a new version and independent review; retain the old result.
Re-score immutable outputs when that is sufficient. Rerun execution when tools, inputs,
behavior or relevant runtime code changed. Record exactly which downstream owners and
pathways lose qualification. Branch names alone never establish equivalence.

There are two admissions: a **bounded CP1 proof** can proceed on its reviewed candidate
and keys while unrelated preparation continues; **full workflow acceptance** requires
the complete integrated product and coverage. Do not mistake one for the other.

## T3 — finish the bounded CP1 foundation proof

- [ ] On the admitted round4/budget candidate, pass named offline probes and the
  gate's offline prerequisites first. Preserve authenticated parent/scope, period,
  unit, raw replay, consumer and render checks.
- [ ] Generate/verify the fresh schema-3 launch gate from reviewed bytes and the
  locked shared ledger. Reconcile actual settled/reserved/unknown exposure at launch.
- [ ] Use the **one already approved fresh USD25-capped TDG attempt** through the
  reviewed bounded driver. Its attempt allowance is shared across sessions; a new
  thread, gate, release or retry never renews it. No automatic second attempt.
  Do not substitute the broad campaign pilot.
- [ ] Prove CP0 → five-stage CP1 → CP1A → CP2, actual selected fact consumption,
  authenticated Model/report publication and browser-visible output against the
  pinned `cases/cp1-chain/expected.json` and financial reference.
- [ ] Exercise the actual SourceSession/history route. Cold component checks do not
  replace the missing retained-run/warm-cache/full-chain evidence.
- [ ] Return proof or a classified defect to the product session and PR MANAGER.
  Run6522's CP1A identity mismatch and the separate auditor wording defect stay
  distinct unless a reproduction establishes a shared cause.

**Exit:** successful bounded evidence or an explicit failed attempt with accounted calls
and a defect handoff. Neither outcome silently authorizes another paid attempt.

## T4 — prove the complete workflow offline

- [ ] Run all six public anchors through `run_pathway` using qualified recorded
  adapters, real permitted tools, real settlement and actual consumer/render paths.
- [ ] Run supplementary positive and negative chains until every owner is covered.
- [ ] Exercise missing/stale/foreign/conflicting inputs, units/periods/entities,
  legal/research authority, changed-upstream invalidation, interruptions/resume and
  bounded repair replay. Check no duplicate settlement/publication or false success.
- [ ] Rehash local corpus and independent goldens. CI omits the local public corpus.
  Run all applicable module, integration, regression and promotion/store/heavy checks
  in their supported tiers. Preserve deferred test obligations; skips/timeouts/cancels
  and unavailable logs are unverified. Do not kill unrelated jobs or restart quiet tests.
- [ ] Inspect fresh report/Model/calculation outputs in the browser for all pathways:
  values, scale, periods, citations, chart/table twins, source inspector, keyboard/focus,
  search/downloads and receipt identity. Evaluate the integrated design against the
  existing 32/40 target; all design changes go to the product session.
- [ ] Verify outcome/status, completed coverage, receipts and comparisons explicitly.
  The current model-testing CLI can exit 0 with stopped/failed outcomes; shell exit 0
  alone cannot pass a case.

**Exit:** all six offline pathway passes, all-owner positive/negative proof, complete fact
comparisons, browser evidence and required checks with no unresolved High/Medium in scope.

## T5 — prove the workflow live within existing authority

Authority: [Nov 2 ruling](../../rulings/2026-11-02-model-testing-live.md), subsequent
DeepSeek removal and the separate Nov 3 bounded CP1 allowance. Pre-Testing's prior
stop is not lifted merely by issuing this plan. When execution resumes, reuse existing
authorization within its exact bounds; do not ask again for already approved actions.

- [ ] Before calls, verify current official API/model/effort/pricing against adapters.
  Keys come only from approved environment variables; stop with the missing variable
  name if absent. Do not search credentials, read old key files or expose values.
- [ ] Reconcile shared settled/reserved/unknown charges, including historical holds.
  USD117 OpenAI / USD135 Anthropic / USD18 OpenRouter are ceilings, not balances.
  The separate USD25 attempt is not extra account credit. Preserve UnknownCharge refusal.
- [ ] Pass the offline pilot, then the earnings live pilot on the active configurations:
  Sol medium, Sol high, Opus medium. Retain exact valid prior cells; re-estimate the
  remaining matrix from measured usage and report spend through the established lane.
- [ ] Execute sequential Sol-medium baseline/repair coverage in order: credit, earnings,
  relative value, covenant/refinancing, distress, portfolio. Include required supplemental
  owner cases in the costed run cards; case additions do not create spending authority.
- [ ] At failure, preserve artifacts and classify product, prompt, harness, oracle or
  model behavior. Product/prompt changes go to the product session. Pre-Testing fixes
  its own testing defects with independent keys/reviews, then admits the new versions.
  Prove the affected repair offline before the corresponding live rerun.
- [ ] Obtain one valid complete baseline live run per pathway on the final qualified
  product release, plus the all-owner live coverage. A complete earlier pilot/repair
  run already on that release may count; do not repeat it solely because a phase ended.
  Partial replay cannot substitute for a required complete run. Changes invalidate
  affected pathways using the recorded dependency closure; rerun those full pathways.
  Carry unaffected evidence only with a documented comparison of the relevant bytes,
  inputs, keys and configurations. Never relabel an old run's original revision.
- [ ] Complete approved comparisons: Sol high on six pathways; Opus medium on earnings,
  portfolio, credit, covenant and relative value; distress only if measured budget
  allows. Each config consumes its own upstream outputs. Genuine model failures remain
  comparison results, never baseline product passes.

Before each pass, compare its remaining costed matrix with current available authority.
If it cannot fit, stop that pass and report exact unfinished cells and measured need.
Do not trim required functionality, pool the alternate campaign's budget or silently
repeat a consumed single-attempt authorization.

**Exit:** complete baseline live proof for six pathways and every analytical owner;
deterministic publication/navigation verified; approved comparison outcomes and every
provider call accounted for.

## T6 — acceptance, defect handoffs and closure

For each failure, retain a defect ID, admitted release, case/run ID, key pointer,
expected/actual observable result, reproduction command, evidence paths, affected
dependencies and cumulative fix-round count. Hand product defects to the other session;
Pre-Testing keeps verification ownership. The repair handoff names the finding IDs.
A fix, merge or model refusal alone does not close a defect; its prescribed comparisons do.

Publish an acceptance index with all 26 owners and six pathways, positive/negative
offline/live coverage, exact versions, tool/consumer/receipt references, facts evaluated,
browser evidence, CI/local checks, spend and remaining limitations. Required cells may
be PASS, FAIL, BLOCKED or NOT RUN; only complete required passing coverage closes the
product. Legitimate negative-case refusals pass their own expected-outcome comparison.

Include a deliverable acceptance matrix: pathway/case → artifact → section/field or
analytical duty → responsible module/consumer → independent expected result → actual
visible output → comparison result → offline/live run evidence. Publish required,
evaluated, correct, failed and missing content counts. An aggregate score cannot hide
a failed or unassessed required result. Closure requires accurate populated deliverables,
not only a complete list of test runs.

Send the accepted evidence to the product documentation owner and PR MANAGER for status
updates/integration. Pre-Testing verifies the final integrated candidate's relevant
identity and required checks. It does not take over documentation, design or deployment.
Historical records remain immutable. Optional research and broad production work are
not added to workflow acceptance.

## Execution references and ledger

Use the existing public `run_pathway`, `OwnerWorkflow` invocation/consumption/publication,
receipt verification and `render_owner_slice` / `verify_owner_rendered_slice` paths.
Reuse `recorded_adapter`, `live_adapter`, `export_recording` and the current scoring
framework. Do not introduce a second product tool loop.

Existing offline checks include `uv sync --locked --offline`,
`.venv/bin/python -I cases/pins.py --check` and
`.venv/bin/python -I cases/goldens/check.py --corpus artifacts/public-corpus/v1`
with all six explicit golden directories. Run cards must give complete argv and paths.

The current campaign CLI supports `pilot`, `repair`, `comparison`, `score`, `report`
with `--out`, `--runs-root`, `--recordings` or authorized `--live --ruling`.
Checkpoint has no `--through` / `--config`. The separate CP1 driver accepts
`--check`, `--run`, `--offline-gate`, `--data-root`; use its reviewed gate procedure.
Do not launch any command from an incomplete example or unset path.

After every run append the AGENTS ledger line: UTC, run name, exact command, exit,
pass/fail counts, agent, cumulative fix rounds and first-pass-gate status.
Confidence-review follows testing-code changes; rewrite-tournament follows non-trivial
changed functions. Preserve exact leases, independent reviews and scoped re-reviews.

## Answer Key gate

This is the controlling test plan, not a claim that missing keys/comparisons exist.
T1 closes each row's gaps before the corresponding build or acceptance dispatch.
Every release manifest expands these references to exact key JSON pointers, hashes
and runnable comparison argv. No placeholder row grants a pass.

| # | User / system action | Surface | Expected observable result | Comparison |
|---|---|---|---|---|
| 1 | Submit frozen TDG sources | CP1 facts, actual CP1A/CP2 consumer, Model/report | Candidate `cases/cp1-chain/expected.json` and pinned `tdg-financial-reference.json`; T1 records exact pointers | Existing candidate runtime audit and `tests/test_chain_runtime.py`; finish approved round4 and audit fresh actual run |
| 2 | Extract supported PDF/OCR profiles | Source rows and financial gate | Candidate `cases/pdf-header-periods/expected.json`; independent image-only key required for any required OCR profile | Existing `cases/prove/pdf_headers.py`; Pre-Testing adds missing profile comparisons before related build |
| 3 | Run SHC comparative earnings | CP1B output and FP02 | `cases/goldens/shc-earnings-update/module_golden.json#facts`, `cases/earnings/expected.json#comparison_rule`; independent Q2/Q2 extension | Pre-Testing authors actual owner-to-render comparison before product widening |
| 4 | Request portfolio fit/recommendation | CP3B/CP6A, consumers and assigned blocks | Distinct SPEC duties; new independent holdings/security/decision keys required | Pre-Testing authors positive/refusal owner and full-pathway comparisons before product build |
| 5 | Score complete public output | Facts, coverage and accuracy | Each `module_golden.json#facts`, pinned financial gold and mapping `#entries` / `#unmapped` | Existing scorer plus new completeness comparison; missing-fact mutation must fail |
| 6 | Run a full preset or supplementary chain | Tools, heads, consumer reads, receipt and rendered sections | Independent full-pathway/chain key and each source/context/golden; exact pointers required | Real public route, receipt/render verifiers, full coverage and browser comparison; author missing checks in T1 |
| 7 | Inspect/navigate actual output | Charts, table twins, source inspector, rails/downloads | `cases/charts/expected.json#chart_series`, `#lineage_and_rendering`; `cases/cpos-owner/expected.json#dom_expectation` / `#cases`, independently extended | Existing render/navigation checks plus actual selected-cell and six-pathway browser proof |
| 8 | Change context or interrupt/resume | Facts, refusal, selected heads, journal, delivery and budget | `cases/periods-currency-owner/expected.json#module_oracles`, `cases/context-attachments-owner/expected.json#cases`; pinned O3/O4/replay/budget cases | Existing cases plus missing public-chain comparisons; exact crash points and refusal states frozen before run |
| 9 | Admit/revise a candidate | Release manifest and historical evidence | T2 identity, scope, authority and invalidation contract; reviewed admission checklist | Verify exact bytes, keys, argv and review receipts before dispatch; preserve original results |
| 10 | Declare workflow complete | Deliverable acceptance matrix and final integrated output | All 26 owners and six pathways satisfy the module/pathway/project definitions above and their pinned deliverable contracts | Every required delivered result is evaluated and correct under its independent key; all comparisons and evidence checks pass; no missing cells or unresolved High/Medium |
