# Recon: Deploy V CP-OS vs Deploy Workflow model connection (mx-autonomous abf83579, read-only, 2026-10-31)

**Premise corrected:** in Deploy V, CP-OS is not the orchestrator. It is a read-only navigation guide that "never independently chooses or runs a module" (`Deploy V/skills/cp-os-credit-os/SKILL.md:3,18-19`; Development design 2026-08-09 replaced CP-OS orchestration with a navigation guide). Orchestration is spread across CP-0 (selects work), the shared runtime (`scripts/credit_os_v/routing.py`, `prepare_invocation.py`, `handoffs.py`), the Copilot host model reading each SKILL.md, and the user issuing each `Run CP-x`. Deploy V has **no model connection** (no provider client, tool loop or per-call record). Deploy Workflow's CP-OS equivalent is `src/deploy_workflow/owners/cpos.py:1-13`, a render-time navigation proof.

## How Deploy V orchestrates
- Routing: a command resolves to one retrieval-index entry; stale/missing/ambiguous index stops dispatch.
- Sequencing: CP-0 T8 selects modules; `plan_from_cp0` (navigation.py:470-484); `dependency_order` (routing.py:20-43) adds REQUIRED/QA_GATE producers, producers before consumers; edges REQUIRED/OPTIONAL/ADVISORY/QA_GATE.
- Profiles FULL_CREDIT_32 / LITE_CREDIT_22, fixed per run, unknown fails closed.
- Inputs: `prepare_invocation.prepare` (:21-122) builds run/route-node/attempt/invocation digests and the exact upstream records; the model copies them and follows the SKILL.md.
- Payload base schema: identity, runtime_output, evidence_trace, confidence, limitation_flags, qa_status, downstream_consumers; output is Markdown with six H2 sections. Base enum lacks CP-1D, CP-3D, CP-L10.
- Reruns: affected module + dependents on CP-0 change, upstream hash change, new research question; `--ordinal`; duplicate claims rejected as AMBIGUOUS_RETRY.
- Acceptance (`handoffs.py:26-118`): validation, completeness, CP-0 source gate, identity match, exact upstream set/hashes, reproduced invocation digest.
- Missing inputs: missing blocking upstream raises; BLOCKED/RESTRICTED nodes; `[Insufficient Information]`, `Not Calculable`, null never zero.

## Transfer to the orchestrator (design 1a)
Refuse a step with missing/stale blocking upstream and name it; per-call record keyed by an invocation digest (run, module, step, attempt ordinal, upstream hashes, prompt hash, method version); reject ambiguous retries; invalidate only downstream dependents on upstream hash change; CP-DR BLOCKED when research unavailable; "never use remembered facts" prompt rule.

## Do not transfer
Copilot memory prompt, retrieval index/build_id, `_RUNS`, menus; Markdown handoffs; model-run scripts whose output the model transcribes; model-supplied counts for confidence; LITE/FULL; Deploy V pathways (differ from decision 0009); placeholder `REQUIRES_ANALYST_DECISION` rows.

## Prompt sources
Primary source is Deploy Workflow's own `src/deploy_vii/methods/*.md` (exist for the 13 owner-only modules and CP-5; CP-1B has none), written as `STEP_CONTRACTS` does (method text + one lettered rule per validator check + `StepSpec.schema`). Deploy V SKILL.md only for reader question and decision drivers where they match the frozen lease. Conflicts: CP-1C (Deploy V web peers, different tables), CP-DR (Deploy V web; Deploy Workflow pack-only gap mode, `methods/cpdr.md:3`), CP-L10 (strong conflict), CP-1B (mostly inapplicable). Partial: CP-1D (folds CP-1E), CP-2A (folds CP-2B). Fit: CP-2D/2E/2G/3C/3D/4C, CP-2H (honest gap), CP-8.
- **CP-5 already has a prompt** (`STEP_CONTRACTS[INTEGRITY]`, prompts.py:833-841); the gap is how it is fed (`build()` requires a scope block, prompts.py:1172-1173, while the owner step declares `inputs="module_context"`). Conflicts with the builder check's claim; verify.
- Version drift in table ids (CP-1B, 1C, 1D, 2A, L10) vs `methodology.json`; `docs/methodology/r14-coverage.json` absent here.

## Conflicts with Deploy Workflow rules
Model-run arithmetic; CP-3 "assume workbook up to date"; CP-1C trusts web figures; `completeness_check` disqualifies "insufficient information" (vs design 10.3); **design 10.3 contradiction:** peers cannot come from CP-DR web search, since CP-DR is pack-only and no web tool exists in `live/tools.py`.

## Ranked recommendations
1. Orchestrator is `owner_workflow` + `registry` + `execution`; nothing in Deploy V ports for adapters or the tool loop.
2. Prompts from `methods/<m>.md` + validator-check rules + schema.
3. CP-5 off the missing list; settle its feeding.
4. CP-1B prompt from `EarningsDeltaReview` and its lease.
5. User decision on CP-DR web vs peers empty before CP-1C testing.
6. Per-call invocation digests and refuse-on-stale upstream; keep two tries.
7. Per-module drift written into prompt briefs.

Not verified: no code run; REF_* bundles, per-skill scripts, leases, full step schemas not read; r14 status unconfirmed; CP-5 feeding inferred from `build()` checks.
