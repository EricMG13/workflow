# HANDOFF: Codex findings review → model-testing goldens → testing framework

Written 2026-10-31 ~11:40 UTC by session "Codex findings review" (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673`, branch `claude/codex-findings-review-64c673`, based on 3888fe0; `codex/checkpoint` is now 3aaeb35 locally and on origin). The session's usage ran out. Pick up from here.

## 1. What the user asked for, in order
1. Review Codex's findings (4 ChatGPT share links). **Done:** `work/codex-review/CONSOLIDATED.md` holds every finding and its verdict, the user's decisions U1–U11, and the session inventory. Probes are in `work/codex-review/probes/`.
2. Consolidate with the active sessions' outstanding items. **Done.** The user's decisions were relayed to Modules (local_d457766d) and the PR manager (local_73a216ba). The PR manager merged the perf branch as 3aaeb35 and pushed. Modules owns the fixes (H01/H02/H08 are one task under ruling item 84). The src/deploy_vii items (U3, U8) need the user's own word in the Modules session.
3. **Current request** (user, verbatim): "review the testing codex session (and deply VII testing sessions) to create your own testing framework to build on, or refine or compliment that one (check for re-usable testing, observability, issuer corpus and infrastructure). when all fixes from consolidated are applied, i want to begin testing using GPT (6.1 sol medium & high), Claude (Opus 5.5 medium and high), open router (DeepSeek V4.1 Flash 1017 (Max)) api keys."
   - **Test goals** (user): "all modules tested and repaired sequentially, all modules successfully populated the deliverables, and all pathways run end to end. success is accurately populated deliverables. observability and other testing infrastructure serve to compare performance between providers for performance, optimisation and identify faults. (must use context form)".
   - **"Context form"** = `docs/templates/context-form.html`, which writes `context.json` (schema context/1), commit 5325c20 on codex/checkpoint. Details: `work/model-testing/recon/context-form.md`. The consumption plan (`docs/superpowers/plans/2026-10-31-context-file-consumption.md`, commits 4fd966f and 0a284ff on branch `claude/workflow-context-file-db27f3`) is approved but **not started and not merged**; the PR manager is waiting on the user's own word to merge it. Nothing reads context.json yet, so it is a prerequisite for testing.
   - The user then said **"build goldens now"**, then "check if codex has not already made goldens", then chose **"Reuse + fill gaps (Recommended)"**: Codex's financial goldens are the CP-1 layer, and we build only the missing layers.

## 2. Recon (done; read these first)
`work/model-testing/recon/`:
- `codex-framework.md`
- `deploy-vii.md`
- `deploy-workflow-harness.md`
- `context-form.md`
- `codex-goldens.md`

Key facts:
- **Live provider testing is paused** (AGENTS.md:122-124). Lifting it needs a user ruling recorded in docs/rulings, plus a credential rule: keys from environment variables only. The user keeps keys in a plaintext RTF (U10); never read it.
- **Nothing has run the full workflow with a model.**
- **Reusable:**
  - DEPLOY VII A2B `src/deploy_vii/live/client.py` (OpenRouter), `devtools/hybrid_cp1.py` (Anthropic SSE), `live/ledger.py`, the retention layout, and the recorded failure fixtures;
  - Codex `journal`, `scoring`, `corpus`, `readiness`, `fault_registry`, plus the OpenAI preflight and budget logic.
- **Gaps in this repo:** no prompts for 13 owner-only modules; the 128-message JSONL cap; the uncapped quality read (U4 approved); no tokens or timings in receipts.

## 3. Goldens: state at handoff
- **Corpus** (gitignored, stable): `/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1/` (36 SEC files, sha256-verified against `manifest.csv`).
- **Codex gold snapshot:** `.../artifacts/public-corpus/v1-codex-gold-20261031/`. TDG and SHC were on Codex's 3rd fix round (PG-06, PG-07) when snapshotted; re-snapshot them when Codex freezes them (source: `~/.codex/worktrees/deliverable-design/Deploy Workflow/work/evaluation/public-campaign/source-gold/`).
- **Stage contract:** `work/model-testing/goldens/CONTEXT.md`. Briefs are in `goldens/briefs/<issuer>.md`, the review brief is `goldens/REVIEW-BRIEF.md`, controller findings G-1..G-6 are in `goldens/controller-findings.md`, and the ledger is `work/model-testing/ledger.md`.
- **Checker:** `cases/goldens/check.py` and `tests/test_goldens_check.py`; 46 tests pass and ruff is clean. Run it as `python3 -I cases/goldens/check.py cases/goldens/<case>`.
  - **Pending checker change (NOT yet dispatched; my message failed).** Give it to a fresh mx-scaffold:
    1. **Bug:** the quote is not whitespace-collapsed after zero-width deletion. BGS quotes like "001-32316 ​ B&G" fail. Normalise the quote and `printed` exactly as the text: delete ZW characters, map Unicode spaces to a space, collapse whitespace, strip.
    2. Allow scale `billions`; refuse "trillions" instead.
    3. Mixed-scale derivations: convert operands to units by scale (thousands 1e3, millions 1e6, billions 1e9), express the result in the derived fact's scale; ratio and percent are unitless (percent = ratio × 100 only when value_type is percent); quantise half-up to the stored decimals.
- **Cases** (`cases/goldens/<case_id>/`: context.json, module_golden.json, derive.py, prepare-report.md):

| Case | Preparer | Checker | Review |
|---|---|---|---|
| tdg-credit-snapshot | done (172 facts; no prepare-report.md, finding G-5) | exit 0 | mx-precise running when the session ended (report not saved) |
| shc-earnings-update | done (97 facts) | exit 0 | mx-precise running |
| bgs-relative-value | done (105 facts) | **exit 1** (ZW quote bug, checker fix 1) | mx-precise running |
| ihrt-distressed-restructuring | done (153 facts) | exit 0 | **not started** |
| lth-covenant-refinancing | was running | ? | not started |
| natl-portfolio-decision | done (118 facts; CP-0 wrongly in not_golden: finding G-8) | exit 0 | not started |

- **Controller findings** (add these to each case's fix round):
  - G-1: thousands stored as printed (SHC rescaled to millions; BGS used scale null).
  - G-2: zero-width characters.
  - G-3: BGS peer_source should be `cp_dr_public`.
  - G-4: SHC dash = 0 is OK.
  - G-5: TDG prepare-report.md is missing.
  - G-6: TDG legal_documents should be "executed".
  - G-7: IHRT may add the derived facts it omitted (participation, post-exchange totals) once the mixed-scale checker lands, and store the "$3.9 billion" market value as decimal 3.9 with scale billions.
- Review reports from agents that were running are lost with this session. **Rerun mx-precise reviews for all six cases** with `goldens/REVIEW-BRIEF.md`, and tell them about G-1..G-7. One fix round per case: mx-feature with that case's reviewer plus controller findings, then a scoped re-review. Then run the checker on all cases, then commit `cases/goldens/`, `tests/test_goldens_check.py`, `work/model-testing/` and `work/codex-review/`, then record ledger lines.

## 4. After goldens: resume the framework design (brainstorming in progress)
Established with the user:
- The goals above.
- The context form is mandatory.
- Goldens are the accuracy oracle.
- Providers: GPT 6.1 Sol medium/high (OpenAI), Opus 5.5 medium/high (Anthropic), DeepSeek V4.1 Flash 1017 via OpenRouter ("Max"). Confirm exact ids, effort parameters and prices from current docs (Context7 or provider docs). Ids used in DEPLOY VII were `openai/gpt-6.1-sol`, `deepseek/deepseek-v4.1-flash-1017` and `claude-opus-5-5`; Codex used `gpt-6.1-sol` direct.

My working guesses (the user has not confirmed them):
- Modules run in pipeline order on all 5 configurations, from the same frozen upstream input.
- Faults are classified as product, prompt, harness or model; the first three are fixed and the module rerun.
- A module passes when at least one configuration populates its part accurately.
- The pathways are the six issuers; CZR and the synthetic cases are warm-ups.

Still to ask (one question at a time, per superpowers:brainstorming), then a written design `docs/superpowers/specs/2026-10-31-model-testing-design.md` with a builder check, then superpowers:writing-plans:
- spend ceiling per provider and in total;
- whether to drive the workflow in-process (Python API) or over JSONL (128-message cap);
- who writes prompts for the 13 owner-only modules;
- repair loop ownership (Modules builds product fixes);
- report format.

Prerequisites before any live run:
- consolidated fixes applied (Modules);
- context consumption Phase 1 plus each module phase;
- U4 quality_scope;
- U3 cash scope;
- the pause lifted by user ruling.

## 5. Rules that bind the next session
- **Global CLAUDE.md:** the controller writes no code; dispatch mx-* agents (mx-feature for builds, mx-precise for reviews, mx-scaffold for mechanical work). Ledger lines record `agent= fix-rounds= gates-first-pass=`.
- **src/deploy_vii** changes need the user's own word in the session plus a D12 manifest record. Never edit DEPLOY VII. No credential discovery. No provider calls until the pause is lifted.
- **Memory:** `~/.claude/projects/-Users-ericguei-Documents-Deploy-Workflow/memory/MEMORY.md`.

## 6. Status update (~11:50 UTC); this supersedes section 3's agent states
- **Checker fix:** the 3 changes were dispatched after all (mx-scaffold). The report goes to `work/model-testing/goldens/reports/checker-fix2.md`. If that file is missing, the change did not finish: redo it from section 3.
- **Reviews:** all agents were told to write their reports to `work/model-testing/goldens/reports/<issuer>-review.md`. Mid-run delivery of that instruction is not guaranteed for tdg, shc and bgs.
  - Running: tdg, shc, bgs, ihrt, natl.
  - LTH: the preparer was still running. When it finishes, it needs a review.
- **Missing report:** if any `<issuer>-review.md` is absent, rerun that review.
- **Next:** one fix round per case with mx-feature, using its review plus G-1..G-8, then a scoped re-review, `check.py` on all six, and the commit.
- **LTH done (~11:55):** 165 facts, check.py exit 0, prepare-report.md written. Its review was dispatched; report to `goldens/reports/lth-review.md`. G-9 recorded.
- **Checker fix 2 done (~12:00):** 51 tests pass, ruff is clean, and **all six cases pass check.py** (exit 0). Report: `goldens/reports/checker-fix2.md`.
  - Info: a product now recomputes in units (scale-aware). That is correct for money × unitless rate, which is the only meaningful product.
- **Remaining:** the six reviews (tdg, shc, bgs, ihrt, natl, lth) were running; their reports go to `goldens/reports/<issuer>-review.md`. Rerun any that are missing. Then run the fix round per case (G-1..G-9 plus the review findings), re-review, and commit.

## 7. Status at ~12:15 UTC (latest)
- **Reviews saved** in `goldens/reports/`: tdg (REVISE: R1, R2 Medium), shc (APPROVE: R1 Low, R2 Info), bgs (REVISE: R1 Medium, a Codex gap; ours is correct).
  - mx-precise reviewers will not write files; the controller saves their hand-back text as `reports/<issuer>-review.md`.
- **Reviews still running at handoff:** ihrt and natl, then lth. Their reports are lost if this session ends: rerun them with `goldens/REVIEW-BRIEF.md` (known findings G-1..G-9).
- **Fix round 1 running at handoff** (mx-feature): tdg, shc, bgs. Their briefs are the review reports plus controller-findings.md.
  - **Check on resume:** run check.py and derive.py per case, and the reviewer probes in `scratchpad/r-<issuer>/` (scratch may be gone; then rerun the review).
  - **Next for each case:** a scoped re-review of the Medium fixes only (mx-feature or mx-precise).
- **Then:**
  - fix rounds for ihrt, natl and lth once their reviews land;
  - run check.py on all six;
  - commit;
  - re-snapshot Codex TDG/SHC gold when Codex freezes them;
  - report BGS-R1 (Codex marks BGS FY2025Q2 principal missing, but Note 6 prints 2,011,375) to the user, since it is Codex's defect;
  - resume the framework design (section 4).
- **SHC done (~12:20):** fix round 1 applied; check and derive exit 0; no re-review needed (Low/Info only).
- **BGS done (~12:30):** fix round 1 applied; check and derive exit 0. **TDG:** fix round 1 applied (check 0); scoped re-review of R1/R2 running.
- **TDG done (~12:35):** scoped re-review APPROVE. **Three goldens done (TDG, SHC, BGS).** Left: IHRT, NATL, LTH (reviews then fix rounds).
- **11:14 status:** all six reviews in (reports in goldens/reports/). NATL fix 1 committed a10e83c8, scoped re-review (R1 + G-8) running. IHRT fix 1 running (R1 High: ABL greater-of trigger; then mx-precise re-review). LTH fix 1 running (G-9 + R1 Medium; then scoped re-review). After those: check.py on all six, commit, then framework design (section 4).
- **Scoring notes from the goldens (for the framework spec):**
  - Entity names: LTH stores guarantor names in title case ("LTF Club Operations Company, Inc.", the all-caps signature text stays in `printed`); NATL stores them all-caps as printed. Scoring must compare names case-insensitively (controller ruling; no golden change).
  - Codex-gap notes (BGS-R1, LTH-R6, NATL-R3): where Codex marks a metric missing and our golden holds it, scoring takes our module fact; not a conflict.
  - check.py `product` reads a percent operand as its printed number (10, not 0.10); IHRT re-review is assessing whether that is a checker defect.
- **11:17:** NATL DONE (3e8f103a). IHRT fix 1 committed c16d87fb, mx-precise re-review running. LTH fix 1 committed 1a5478a2, scoped re-review running.
- **11:19:** **All six goldens approved** (TDG, SHC, BGS, NATL, IHRT, LTH; one fix round each). End batch running: NATL-RR1, IHRT-RR1, LTH-RR1 wording + LTH 15th date check + check.py refuses percent/bps operands in product/ratio (test first). After it: commit, then framework design (section 4).
- **11:20: Goldens stage complete.** End batch committed; check.py all six 0; derive.py all six 0; pytest 54 passed. Next: framework design (section 4), brainstorming one question at a time.
- **Spend ceiling (controller proposal, 2026-10-31; not a ruling until the user confirms):** one full round (6 pathways x 5 configurations) estimated at about USD 471, so the proposed ceiling is USD 700 per round with per-configuration caps (Sol medium 55, Sol high 75, Opus medium 235, Opus high 335, DeepSeek 15). Run a pilot first: earnings_update on all five configurations (estimated about USD 59) to measure real per-module cost before the full round. Repair reruns are charged against the same ceiling. Basis: DEPLOY VII observed CP-1 costs (Sol medium 2.07, Sol high 2.99, Opus medium 9.46, the last computed rather than billed); Opus high scaled by Sol's high/medium ratio; DeepSeek at USD 0.30/1.20 per M x1.5 for reasoning; each downstream module guessed at 25% of CP-1. Prices: OpenAI gpt-6.1-sol 2.00/0.10/10.00 (above 272K input: 4.00/0.20/15.00); Opus 5.5 4/20, cache read 0.20; DeepSeek V4.1 Flash 1017 listed at 0.15/0.60 to 0.30/1.20 by aggregators (OpenRouter page not readable). Script: scratchpad cost/estimate.py.
- **Budget plan (supersedes the USD 700 proposal; user 2026-10-31: remaining credits OpenAI USD 130, Anthropic USD 150, OpenRouter USD 20). Controller proposal, not confirmed:**
  - Keep a 10% reserve per account (usable: OpenAI 117, Anthropic 135, OpenRouter 18). The runner stops a configuration at its cap; an unknown charge stays reserved (DEPLOY VII ledger rule).
  - OpenAI: Sol medium + Sol high on all six pathways, estimated 82.72; about 34 left for repair reruns.
  - OpenRouter: DeepSeek on all six, estimated 9.97; about 8 left for reruns.
  - Anthropic cannot fund a full round even at one effort (Opus medium all six estimated 154.65). Plan: pilot (earnings_update) at both Opus efforts, 47.58; then Opus medium only on portfolio_decision, credit_snapshot and covenant_refinancing, 77.33; total 124.91 of 135. Opus does not cover relative_value or distressed_restructuring unless the pilot measures it cheaper than estimated, or the user adds credit (about USD 100 more covers Opus medium on all six).
  - Order: pilot on all five configurations first; re-estimate from measured per-module cost; then the rest.
- **Recommended budget plan (controller, 2026-10-31; supersedes the line above; user asked for my suggestion, not yet confirmed):**
  - Split the work in two passes. **Repair pass** on the cheap configurations (DeepSeek, Sol medium): run every pathway end to end, fix faults, rerun until the deliverables match the goldens. **Comparison pass** on the fixed product: Sol high and Opus medium run each pathway once, with no repair reruns.
  - **Drop Opus high.** The medium/high effort comparison comes from Sol; Opus high costs about 1.44x medium and would squeeze Opus coverage to the pilot.
  - OpenAI (usable 117): Sol medium about 2 rounds incl. reruns (67.68) + Sol high once (48.88) = 116.56.
  - OpenRouter (usable 18): DeepSeek about 1.8 rounds incl. reruns.
  - Anthropic (usable 135): Opus medium once on 5 pathways, cheapest first (earnings_update, portfolio_decision, credit_snapshot, covenant_refinancing, relative_value) = 125.72; distressed_restructuring only if the measured cost allows (all six = 154.65).
  - earnings_update goes first on all four configurations as the pilot; re-estimate from measured cost before continuing.
- **Ruling (user, 2026-10-31, "Adopt it"):** the recommended budget plan above is adopted. Repair pass on DeepSeek + Sol medium; comparison pass on Sol high + Opus medium; Opus high dropped; earnings_update pilot first; 10% reserve per account.
- **11:29:** design draft written: docs/superpowers/specs/2026-10-31-model-testing-design.md; builder check running. Next: sort its questions (answered / minor / user's), one round of user questions, then superpowers:writing-plans.
- **11:32:** builder check returned 6 questions (+1 low). Controller calls added as spec section 9a (mapping table as oracle, repair stop rule, inherited errors, provenance for all modules, CP-MODEL deterministic if confirmed, pin Codex gold). Two put to the user: absent user inputs (blocked = pass, or supply test inputs) and prompt ownership for 15 modules (13 owner-only + CP-5 + CP-1B).
- **11:33 ruling (user):** "100% orchestrated, no human should be writing prompts"; context form and code changes land before the plan. Spec section 10 rewritten: agents fill the form, agents write the 15 prompts in src/deploy_workflow, honest-blocked = pass for inputs no filing supplies (controller call).
- **11:41 ruling (user):** the orchestrator owns the model connection (prompts, provider adapters, tool loop, per-call records); Modules builds it as product work. Framework = configuration, budget, journal, scoring, faults, report. Spec section 1a.
- **11:43 ruling (user):** design approved ("approve and commit"). Next: review M365 Deploy V CP-OS orchestrator files, then superpowers:writing-plans.
- **11:49 ruling (user):** orchestration (model connection + other orchestration gaps) is separate from testing, a prerequisite, and may go into the context-form session's plan. Spec 1a/§6 updated. When the Deploy V CP-OS and DEPLOY VII/gaps reviews return: write work/model-testing/recon/orchestration-gaps.md and hand it to the context-form session (local_8803e348). The testing plan covers the framework only.
- **11:57:** orchestration gaps G1-G11 (recon/orchestration-gaps.md, commit e636f71e) sent to CONTEXT FORM session (local_8803e348) for its plan; awaiting its reply on which it takes. Next here: testing-framework plan (superpowers:writing-plans) against design §1a's orchestrator interface.
- **11:59:** CONTEXT FORM took G1-G11 as Part B (O1-O7) of docs/superpowers/plans/2026-10-31-context-file-consumption.md (branch claude/workflow-context-file-db27f3, unmerged; Part B awaits user approval). O7 blocked until v2.4 CP-DR sources are supplied and pinned. It asks that this branch (orchestration-gaps.md, design §1a) be merged into codex/checkpoint before Part B's first brief: needs the user's OK; route via PR manager (U1).
- **12:04:** CONTEXT FORM updated O7 (commit 2e582b4d, local): built to cp-dr-v2.4-codex.md @ 80748343 as O7a contracts + decision 0007, O7b LOCAL research + retrieval, O7c source attachment + CP-1C/CP-2, O7d TDR.4-6; recorded as not v2.4 parity. Part B awaits user review; src/deploy_vii parts need the user's word + D12; this branch still to be merged (user's OK pending).
- **12:05 ruling (user):** "there will be no work version set, it need to make its version based on my intend usage and the information provided." Relayed to CONTEXT FORM: drop the v2.4-parity condition; CP-DR is this repo's own version from the user's intended usage + cp-dr-v2.4-codex.md; record gap-filling decisions in the plan.
