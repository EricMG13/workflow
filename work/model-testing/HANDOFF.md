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
