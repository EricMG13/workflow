# Orchestration gaps: prerequisite for model testing (2026-10-31)

User rulings (2026-10-31): the orchestrator owns the model connection; this work is "separate to the testing, as it is required before any testing and could be implemented into the context form sessions plan"; runs are "100% orchestrated, so no human should be writing prompts".

Sources: read-only reviews by mx-autonomous `abc6d3ef` (DEPLOY VII and Deploy Workflow gaps; probes `scratchpad/probe_presets.py`, `probe_presets_nomodel.py`, both exit 0) and `abf83579` (Deploy V CP-OS, saved as `deploy-v-cpos.md`). Line numbers are at worktree HEAD of branch `claude/codex-findings-review-64c673` (base 3888fe0) and need re-checking against `codex/checkpoint`.

## Headline
Only **1 of 6** pathway presets (`distressed_restructuring`) passes `OwnerWorkflow` spec checks today. The other five are refused before any model is involved (G1).

## CP-OS is not the orchestrator
- **Deploy V:** CP-OS is a read-only navigation guide; it "never independently chooses or runs a module" (`Deploy V/skills/cp-os-credit-os/SKILL.md:3,18-19`). Deploy V has no model connection: the user types each `Run CP-x` and the Copilot model follows the module's SKILL.md.
- **DEPLOY VII:** CP-OS is a catalog row with no code ("Report navigation", `methodology.json:631`; `implementation: "unrun"`); code only exempts it.
- **Deploy Workflow:** `src/deploy_workflow/owners/cpos.py` is a render-time navigation proof. Do not name the new orchestrator CP-OS.
- **Basis:** DEPLOY VII/Deploy Workflow `Execution` (hash-chained journal, two attempts, `invalidate`) + `registry` ordering, driven by `OwnerWorkflow`. Model-call discipline from DEPLOY VII `live/runner.py` and `live/ledger.py`.

## Gaps, hardest first
| Id | Gap | Where | Smallest fix |
|---|---|---|---|
| G1a | CP-MODEL ordering refuses analytical modules after CP-MODEL; `publish()` only after the whole walk; CP-5 fan-in includes CP-MODEL. Blocks credit_snapshot, earnings_update, relative_value, covenant_refinancing, portfolio_decision | `owner_workflow.py:1011-1015`, :1376; `registry.py:15,55`; `docs/QUEUE.md:771` | CP-MODEL becomes a stop in the walk: `_advance` (:1155) enters a publish phase, `publish()` resumes `_advance`; drop the :1011 refusal; extend `_verify_walk` (:1677), `_verify_publications` (:1743) |
| G1b | CP-6 has no owner. Blocks credit_snapshot, portfolio_decision | `OWNER_SPECS`, `SUPPORTED_ANALYTICAL` :125-147 | CP-6 owner core on `deploy_vii/cp6_committee.py` + `bindings/cp6.py` + `_PROBES` entry |
| G1c | CP-1B not on the owner path; `EarningsWorkflow` accepts only three synthetic run ids, "Owner checkpoint only". Blocks earnings_update (and CZR) | `earnings_workflow.py:1654-1668`, :97 | Move the CP-1B core into `_CORES` as an owner module |
| G2 | No single entry point, no pack builder, no `context.json` reader; four workflow classes each create their own `Execution` (`exist_ok=False`) | `preparation.prepare` :369 unused; `tests/czr_runs.py:118` `make_pack`; `execution.py:548` | One `run_pathway(case, context, pathway, config, cap)`: manifest + context → `PreparationRequest` → `prepare` → `OwnerWorkflow.create` → step loop → `publish` → `write_receipt` → `render_owner_slice` / `verify_owner_rendered_slice`. Needs G1 and context Phase 1 |
| G3 | First refused `begin` ends the whole walk, skipping independent modules and CP-5 | `owner_workflow.py:1117-1153`, `_refusal_code` :1362 | Record the refusal, continue with the next module that can begin; mirror in `_verify_walk` |
| G4 | No rerun after a repair: settled input sets refused, two attempts max, `_advance` forward-only | `execution.py:657-660`, :97, `invalidate` :307/:747 | Fresh run; replay retained upstream calls/payloads from the audit, run the repaired module live |
| G5 | No state or resume; receipt built from memory | `OwnerWorkflow.create` :1066; :1459-1477 | Public `state()` (module, step, ticket, attempt, inputs required/read), then `open()` from retained audit |
| G6 | Limits: `MAX_CALLS` 16 shared by both tries; `read_inputs` uncapped (CP-1 quality 16.9-21 MB, U4 open); `MAX_MESSAGES` 128 only binds JSONL | :1171-1173, :1227-1229, :347/:821, :2442 | U4 in `_inputs`; the orchestrator refuses (never truncates) and records a fault over a byte cap |
| G7 | Catch-alls hide failures: `except Exception` → `internal_error` with no log; internal `ValueError` relabelled `bad_arguments` | `owner_workflow.py:2478`, :2476 | Orchestrator lets errors reach its journal; do not copy. `publish` catch :1403 is documented fail-closed, OK |
| G8 | CP-0 must list every planned module as `Run <id>`; no prompt states the set | `execution.py:259-266` | CP-0 prompt states the plan's module set |
| G9 | Model connection absent: no provider client, tool loop or per-call record in src; `live/prompts.py` `build()` called nowhere | design §1a | Orchestrator builds prompt per step, calls the configured model, maps tool calls, validates, retries, records |
| G10 | Prompts missing for 13 owner-only steps and CP-1B; CP-5 has a prompt (`prompts.py:833-841`) but its feeding is unsettled (`build()` needs a scope block :1172-1173; owner step declares `inputs="module_context"`) | `live/prompts.py` | Agent-written from `src/deploy_vii/methods/<m>.md` + one rule per validator check + `StepSpec.schema` (as `STEP_CONTRACTS` does); CP-1B from `EarningsDeltaReview` and its lease. Deploy V SKILL.md only for reader question/drivers where they match the lease; write per-module drift into briefs |

## Carry over from Deploy V (as orchestrator behaviour)
- Refuse a step whose blocking upstream is missing or stale, naming it.
- Per-call record keyed by an invocation digest: run, module, step, attempt ordinal, exact upstream hashes, prompt hash, method version.
- Reject ambiguous retries; invalidate only downstream dependents on an upstream change.
- Prompt rule: never use remembered facts. CP-DR reports BLOCKED when research is unavailable.

Do not carry: Copilot memory prompt, retrieval index, `_RUNS`, Markdown handoffs, model-run scripts whose figures the model copies, model-supplied confidence counts, LITE/FULL profiles, Deploy V pathways, `REQUIRES_ANALYST_DECISION` placeholders.

## Reusable DEPLOY VII code
| Path | Verdict |
|---|---|
| `execution.py`, `registry.py`, `readiness.py` | Already vendored; keep Deploy Workflow's copies |
| `preparation.py` (`prepare`, `load_pack`) | Byte-identical; pack-builder base |
| `delivery.py` | Superseded by `owner_rendering` |
| `live/runner.py` | Port the reserve → retain raw → validate → settle → seal order, `repair_prompt` (:214), in-flight 402 handling; not the loop (no tools) |
| `live/client.py` | Port; add tool calls |
| `live/ledger.py` | Port |
| `live/cli.py` `_run_cell` | Pattern only (repair sequence) |
| `live/credential.py` | Do not use (reads the RTF; env vars only) |
| `execution_cli.py`, `live/catalog.py`, `cohort.py`, `draw.py` | Do not port |

| G11 | CP-DR is the older pack-only "resolve evidence gaps" version (`methods/cpdr.md:3`; DEPLOY VII registry :554 lists TDR.1-3, CP-0 only). The user's current CP-DR (Deploy V v2.4 for M365, built at work, not local; seen by Codex and discussed in the context-form session, https://chatgpt.com/s/cx_6ae5d71465b48191a213e58ff45b5172) differs | `methods/cpdr.md`, registry, decision 0007 :62 | Per Codex's read of v2.4: LOCAL mode needing validated CP-0 + CP-1 with matching hashes; locked versioned research brief (default 6 questions, max 32, cutoff); public/supplied evidence intake retained with hashes, locators, dates; contrary-evidence and independence review; Markdown dossier + brief JSON (TDR.1-3); attached to CP-1C/CP-2 as a supplied source, not an analytical upstream; opt-in TDR.4-6 peer pack for CP-1C, which verifies and admits peers itself. Needs a **retrieval stage in the orchestrator** (research tool that retains verifiable evidence before analysis) and a source-attachment mechanism that rehashes and refreshes consumers. Pin the v2.4 source files and hashes before claiming parity |

## Resolved
- **Peers (user, 2026-10-31):** the pack-only CP-DR is an older version. Peers come from the new CP-DR v2.4 peer pack (TDR.4-6) once built, with CP-1C admitting them; until then CP-1C reports the gap. The testing design's §10.3 now points here.

Not verified: no `PreparedPack` built and no `OwnerWorkflow.create` called (probes call `_check_specs`); no pytest; receipt verifiers' changes for G1/G3/G4 not checked; context-consumption plan (other branch) not read against these gaps; Deploy V REF bundles and leases not read.
