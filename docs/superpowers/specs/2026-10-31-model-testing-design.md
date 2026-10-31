# Model testing framework: design

Date: 2026-10-31. Status: approved by the user 2026-10-31 ("approve and commit"). Source conversation: session "Codex findings review" (branch `claude/codex-findings-review-64c673`); state and history in `work/model-testing/HANDOFF.md`.

## 1. Intent

The user wants to run the Deploy Workflow end to end with real models and find out, per module and per pathway, whether the deliverable comes out accurately populated, and which provider does it best. In the user's words:

> all modules tested and repaired sequentially, all modules successfully populated the deliverables, and all pathways run end to end. success is accurately populated deliverables. observability and other testing infrastructure serve to compare performance between providers for performance, optimisation and identify faults. (must use context form)

Nothing has yet run the full workflow with a model. Today runs are Python replays of recorded submissions (`tests/czr_runs.py`, `tests/s1a_runs.py`, `tests/cp*_runs.py`).

## 1a. Architecture ruling: the orchestrator calls the model (user, 2026-10-31)

The user asked whether connecting the model should be "the responsibility of the orchestrator". Yes. Today the workflow orchestrator sequences modules, serves tools and validates submissions, but never calls a model, and nothing in the product calls `live/prompts.py`. The model connection is a product gap, not a testing concern.

- **Product (orchestrator), a prerequisite outside this design (user, 2026-10-31: "treat this as separate to the testing, as it is required before any testing and could be implemented into the context form sessions plan"):** for each step the orchestrator builds the prompt from the step contract, calls the configured model through a provider adapter (OpenAI, Anthropic, OpenRouter), runs the tool loop (tool calls → `invoke` / `read_inputs` / submit), validates the submission, retries within the two-tries limit, and emits a per-call record (tokens, timings, cost, ids). It also holds the agent-written prompts for every step, including the 15 that have none today. The orchestrator takes a model configuration and a spend cap as run inputs.
- **Testing framework (this design):** chooses the configuration and budget per run, feeds the case's context form output, collects the orchestrator's per-call records into the journal, scores outputs against the goldens, classifies faults, routes product faults to Modules, and writes the report. It contains no provider client, no turn loop and no prompts.

Where this document below describes adapters, the turn loop, prompts or reuse of DEPLOY VII clients (sections 7.5, 8, 10.2), read them as requirements handed to the orchestration work, which is planned and built with the context-form consumption plan (`docs/superpowers/plans/2026-10-31-context-file-consumption.md`), not in this framework's plan. The framework only drives and observes the orchestrator.

## 2. Goals

1. Every module in every pathway preset (`src/deploy_vii/contracts.py:36-71`) runs with a live model, driven by the case's `context.json` from the context form.
2. A failing module is diagnosed, repaired, and rerun before the pathway moves on (sequential).
3. Success is measured against goldens: the module populates its part of the deliverable with values that match the golden facts.
4. Every model call is recorded well enough to compare configurations on accuracy, cost, tokens, latency, retries and faults.

## 3. Non-goals

- Building new workflow modules or changing module behaviour inside this framework. Product fixes go to the Modules session.
- Judging the quality of judgment modules (CP-5, CP-6, CP-MODEL, CP-2A stress choices) by value. They get acceptance checks only (schema-valid, cites its inputs, no invented facts).
- Prompt tuning for its own sake. Prompts change only to fix a diagnosed prompt fault.
- Testing models outside the four configurations below.

## 4. Anti-goals (failure even if it "works")

- A module is marked passing because it submitted something schema-valid, not because its values match the golden.
- Spend goes past an account's cap, or a call runs with an unknown charge and the run carries on.
- The framework reads the user's key file or discovers credentials in any way.
- A run that bypasses the context form, or a context file that differs from the golden case's `context.json`.
- Edits to DEPLOY VII, or to `src/deploy_vii` without the user's own word.

## 5. Constraints

- **Live testing is paused** (`AGENTS.md:122-124`). Nothing in this design makes a provider call until the user lifts the pause by a ruling in `docs/rulings/`. All building and offline testing is allowed now.
- **Credentials:** keys only from `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`. Never read `~/Documents/OP Router.rtf`. Keys never appear in logs, journals, reports or error text.
- **Code location:** new code in `src/deploy_workflow/` (proposed `src/deploy_workflow/model_testing/`). `src/deploy_vii` changes need the user's own word plus a D12 `post_import_patches` record.
- **Dependencies:** none new. HTTP over stdlib `urllib` (the DEPLOY VII clients already do this). Allowed: pydantic, pypdf, openpyxl.
- **Python owns arithmetic:** costs, scores and derivations use `Decimal`; no model arithmetic is trusted.
- **Gates:** `.venv/bin/python -m pytest -q -p no:cacheprovider`, ruff check/format, mypy strict, `python3 -I cases/pins.py --check`, `python3 -I cases/goldens/check.py`.

## 6. Prerequisites before the first live call

These belong to other sessions; the framework is built in parallel but cannot run live until each lands.

1. The CONSOLIDATED fixes (`work/codex-review/CONSOLIDATED.md`) applied by Modules, including H01/H02/H08 (ruling item 84) and H05 (a lone-surrogate or deep frame poisons the session).
2. Context consumption Phase 1 (`docs/superpowers/plans/2026-10-31-context-file-consumption.md`): the `deploy_workflow.context` reader, pack preparation and CP-0 accepting the context source. Each module's own consumption phase must be merged before that module is tested, or its context fields are ignored.
3. U4 `quality_scope` (the CP-1 quality read is 16.9–21 MB today) and U3 cash scope.
4. The pause lifted by user ruling, with the credential rule above.
5. The orchestrator's model connection and the other orchestration gaps (section 1a; findings in `work/model-testing/recon/orchestration-gaps.md` once written), delivered through the context-form session's plan.

## 7. Decided

### 7.1 Configurations (user ruling 2026-10-31, "Adopt it")

| Config id | Provider | Model id | Effort | Role |
|---|---|---|---|---|
| `sol-medium` | OpenAI direct | `gpt-6.1-sol` | medium | repair pass + comparison |
| `sol-high` | OpenAI direct | `gpt-6.1-sol` | high | comparison pass |
| `opus-medium` | Anthropic direct | `claude-opus-5-5` | medium | comparison pass |
| `deepseek-max` | OpenRouter | `deepseek/deepseek-v4.1-flash-1017` | max | repair pass + comparison |

Opus 5.5 high is dropped (budget). Ids, effort parameters and prices must be re-confirmed from current provider docs when the adapters are built.

### 7.2 Budget (user ruling 2026-10-31)

Remaining credits: OpenAI USD 130, Anthropic USD 150, OpenRouter USD 20. A 10% reserve is held per account, so the usable caps are 117, 135 and 18.

- **Repair pass** on `deepseek-max` and `sol-medium`: run each pathway end to end, repair, rerun until accurate. Estimated about 2 rounds of Sol medium (67.68) and 1.8 rounds of DeepSeek.
- **Comparison pass** on the fixed product: `sol-high` once (48.88) and `opus-medium` once on five pathways, cheapest first: earnings_update, portfolio_decision, credit_snapshot, covenant_refinancing, relative_value (125.72). distressed_restructuring on Opus only if measured cost allows (all six estimated 154.65).
- **Pilot first:** earnings_update on all four configurations; re-estimate from measured per-module cost before anything else runs.
- The runner holds a reservation before each call (input tokens × input rate + max output × output rate), settles on the reported usage, and stops a configuration at its cap. An unknown charge stays fully reserved and stops that configuration.

Basis of the estimates: `work/model-testing/HANDOFF.md` (budget lines) and the Decimal script recorded there.

### 7.3 Cases and oracles

- One public case per pathway, the six goldens in `cases/goldens/`:

| Pathway | Case |
|---|---|
| credit_snapshot | `tdg-credit-snapshot` |
| earnings_update | `shc-earnings-update` |
| relative_value | `bgs-relative-value` |
| covenant_refinancing | `lth-covenant-refinancing` |
| distressed_restructuring | `ihrt-distressed-restructuring` |
| portfolio_decision | `natl-portfolio-decision` |

- Each case supplies `context.json` (context/1, from the form's rules), `module_golden.json` (module-golden/1, checked by `cases/goldens/check.py`), and points at Codex's `public-financial-gold/1` file for CP-1 history.
- Sources are the SEC files in `artifacts/public-corpus/v1/` (sha256 in `manifest.csv`). The run pack is built from those files plus the context file, and its hash is recorded.
- CZR and the synthetic owner cases are offline warm-ups for the harness only; they do not count toward the goals.

### 7.4 Scoring

- **Per module fact:** the module's published output is mapped to golden facts by `fact_id` (module, topic, subject, field, period). Each fact scores match, mismatch, missing-in-output, or extra.
  - Decimals compare after scale conversion to units, exactly (no tolerance) unless the golden stores fewer decimals, in which case the output is quantised half-up to the golden's places.
  - Text facts compare after the checker's `normalise()` and case-insensitively. Entity names compare case-insensitively (LTH stores title case, NATL all caps).
  - A golden `missing` fact passes when the output also marks it missing or absent, and fails when the output invents a value.
  - A golden `conflicting` fact passes when the output raises an issue for it, or picks one of the evidenced values and says it conflicts.
  - Where Codex's gold marks a metric missing but our module golden holds it (BGS principal FY2025Q2, LTH principal FY2025Q2, NATL total debt FY2025Q3 scope), our module fact wins.
- **Judgment modules:** acceptance checks only (schema-valid, every cited input exists in the pack, no figure absent from the pack or context).
- **A module passes** on a configuration when all of its known golden facts match and its judgment checks pass. **A pathway passes** when every module passes and the deliverable renders and verifies (`owner_rendering.render_owner_slice`, `verify_owner_rendered_slice`).
- Scores are computed in Python with `Decimal`; no model grades another.

### 7.5 Driving the workflow

- **In-process** through the public `OwnerWorkflow`, `FinancialWorkflow` and earnings workflow methods (invoke, read_inputs, submit_review, publish, write_receipt), not over the JSONL CLI, because `MAX_MESSAGES` 128 is too few for a multi-module run.
- One adapter turn loop per module step: build the prompt, offer the step's tools (`search_pack`, `read_pages`, `extract_statements` where allowed), `read_inputs` when the step has inputs, and one submit tool carrying the step schema. Map tool calls to workflow calls; respect the two-tries-per-attempt limit (`execution.py:775-782`) and `MAX_CALLS` 16.
- Modules run in pipeline order per pathway. Downstream modules of the repair pass consume the upstream outputs that the same configuration produced. For the comparison pass, each configuration also runs its own upstream; there is no cross-provider frozen input.

### 7.6 Faults and repair

- Each failed module run gets one fault class:
  - **product** (workflow code or contract wrong) → brief to the Modules session, which owns product fixes;
  - **prompt** (instructions or tool descriptions wrong) → fixed in the framework;
  - **harness** (adapter, turn loop, scoring) → fixed in the framework;
  - **model** (the configuration got it wrong with correct product, prompt and harness) → recorded, not fixed.
- After a product, prompt or harness fix, the module is rerun on the repair-pass configurations, then the pathway continues. Model faults do not block the pathway: it continues on the configuration's own output.
- A fault record holds: case, pathway, module, step, configuration, class, evidence (call ids, the mismatching facts), fix reference (commit or Modules brief), rerun result.

### 7.7 Observability

Per call, append to a JSONL journal (one file per run, fsync, Decimal money as strings):

- run id, case, pathway, module, step, attempt, configuration, provider, requested and reported model id, requested effort;
- request and response ids, HTTP status, timings (queue, first byte, total);
- tokens: input, cached read, cache write, output, reasoning;
- reserved and settled USD, and whether cost was billed or computed;
- tool calls made (name, arguments hash, result size), refusals and their codes, the submit payload hash;
- the error class when a call fails, without the key or the raw request headers.

Raw request and response bodies are kept per call under the run directory (gitignored), so a failure can be replayed offline.

### 7.8 Report

Per run, one Markdown report generated by Python from the journal and scores:

- one table per pathway: rows are modules, columns are configurations, cells show pass/fail, facts matched of known, cost, tokens, wall time;
- a totals table per configuration (accuracy, cost, tokens, latency, retries);
- the fault log, grouped by class;
- spend against each account's cap.

## 8. Reuse

| Component | From | Verdict |
|---|---|---|
| OpenRouter client | DEPLOY VII A2B `src/deploy_vii/live/client.py` | port the client only into `src/deploy_workflow`; keep `provider.ignore: ["open-inference"]` for DeepSeek |
| Anthropic SSE adapter | DEPLOY VII A2B `devtools/hybrid_cp1.py` :402-850 | port with changes: adaptive thinking, `output_config.effort`, `tool_choice` auto (forced tool choice is a 400 on Opus 5.5), streaming, 120 s idle limit |
| OpenAI adapter | Codex `providers` | port the token-count preflight, budget reservation, no-redirect HTTPS and key-reflection guard; drop the hard-coded model and prices |
| Spend ledger | DEPLOY VII `live/ledger.py` | port: append-only JSONL, lock, reserve/settle, unknown cost stays reserved |
| Tool specs, strict schema | `src/deploy_vii/live/tools.py:226`, `live/schema.py` | call as is (no change to `src/deploy_vii`) |
| Prompts for plan steps | `src/deploy_vii/live/prompts.py:1120` `build()` | call as is for the steps it covers |
| Journal, scoring ideas, fault registry | Codex framework | reuse the shapes; our scoring replaces Codex's rubric |
| Goldens checker | `cases/goldens/check.py` | reuse `visible_text`, `normalise`, scale handling in scoring |

Observed provider behaviour to design for (DEPLOY VII, recon `deploy-vii.md`): 16k max output truncates reasoning models (use up to 128k); DeepSeek reports reasoning tokens above completion tokens; one transient retry after a mid-stream 502; Anthropic's 5-minute cache misses after calls over 300 s; cached and uncached draws are reported apart.

## 9. Left to the builder

- Module layout inside `src/deploy_workflow/model_testing/`, class and function names.
- The exact request shapes per provider, from current docs fetched into the briefs (Context7 or provider docs) before the first task.
- How the pack is built from the corpus files and `context.json` (follow the context-consumption plan's pack preparation once Phase 1 lands; until then, build against the CZR helpers in `tests/czr_runs.py`).
- The offline test strategy: recorded provider responses (from DEPLOY VII fixtures and new captures) replayed through the adapters; no live call in tests.
- Retry and timeout values within the limits above.
- The run directory layout under `artifacts/model-testing/<run_id>/` (gitignored).

## 9a. Controller's calls after the builder check (the user can overrule)

1. **Output-to-golden mapping.** The goldens are not keyed to module output schemas (each preparer chose its own topic vocabulary; subjects are free text). The framework keeps a mapping and alias table per module and case: output path → golden (topic, field), plus subject aliases for instrument and entity names. The table is an oracle: its preparer, its reviewer (mx-precise) and the scorer's builder are different agents, recorded in the ledger. No loose subject matching; an unmapped golden fact is reported as unmapped, not as missing.
2. **Repair stop rule.** In the repair pass a module is accurate when it passes on at least one repair configuration. If one passes and the other fails with the same product, prompt and harness, the failure is a model fault. Each module gets at most two fix rounds per fault class; after that the open faults go to the user. A reviewer agent assigns the fault class from journal evidence and the controller confirms it. A product fault waiting on Modules stalls only that pathway; other pathways continue.
3. **Inherited errors.** A downstream mismatch whose operand comes from an upstream fact that already mismatched on the same configuration is recorded as `inherited`, shown in the tables, and left out of that module's accuracy figure. The scorer needs the mapping from 1 to trace operands.
4. **Provenance for every module.** Every figure in any module's output must trace to the pack, the context file, or an upstream module output; an untraced figure fails the module. Unmatched-but-traced figures are reported as `unscored`, not `extra`.
5. **CP-MODEL.** If the builder confirms CP-MODEL makes no model call (Python composition from the CP-1 handoff), it is scored as a deterministic consumer and costs nothing.
6. **Codex gold for TDG and SHC.** Scoring pins the `v1-codex-gold-20261031` hashes now and rescores offline once Codex freezes the files.

## 10. Rulings on the open questions (user, 2026-10-31)

The user: "the context form will be available and related changes made to the code before the plan begins. this should be 100% orchestrated, so no human should be writing prompts."

1. **Fully orchestrated.** No human step in a run. An agent fills each case's context form, from the filings and the case's `context.json`; the form's output is what the run consumes.
2. **Prompts are written by agents.** The 15 steps without a prompt (CP-1C, CP-1D, CP-2A, CP-2D, CP-2E, CP-2G, CP-2H, CP-3C, CP-3D, CP-4C, CP-8, CP-DR, CP-L10, plus `integrity_review` CP-5 and `earnings_delta` CP-1B) get prompts generated by framework build agents from each step's `StepSpec.schema` and module contract, stored in `src/deploy_workflow/model_testing/prompts/`, and reviewed by a different agent. `src/deploy_vii` is not changed.
3. **Inputs no filing supplies** (controller's call under the same ruling). Quotes, ratings, issuer market data, the portfolio workbook and the prior case cannot be sourced without inventing them, so the orchestrating agent leaves them empty. A module whose required input is empty passes when it reports the gap honestly (blocked or Insufficient Information, naming the missing input) and invents nothing. Peers come from the new CP-DR v2.4 peer pack (TDR.4-6), admitted by CP-1C, once the orchestration work builds it (`work/model-testing/recon/orchestration-gaps.md` G11); until then CP-1C reports the gap.
