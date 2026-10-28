# Stage 2 (connections) plan for the 16 owner modules

I checked this against lane HEAD 5c9c60e, which contains bb0190e. `codex/checkpoint` is one commit ahead at b570399. That commit is the AGENTS.md "Stage closure" text, so the lane's AGENTS.md does not contain that section yet.

**Mistake to undo or ignore:** I ran one `uv run --offline python` probe and it created `.venv/` inside the worktree. It is git-ignored (`.gitignore:3`) and nothing else changed. The probe failed, so I took the live-contract list from `registry.py` instead. That registry lists step chains for CP-0, CP-1, CP-1B, CP-1A, CP-2, CP-4, CP-3, CP-5 and CP-6 (`src/deploy_vii/registry.py:285-377`). The other 13 modules are owner-only.

## 1. What "connected" means for one module

**(a) Plug-in parts in `src/deploy_workflow/owners/<cp>.py`** (protocol §2)
- **Every module:**
  - `QUALIFICATION`;
  - `probe(store, snapshot, attempt)`, which raises `identity_mismatch` unless the head rebuilds exactly. Follow `owners/cp1a.py:17-50` (`probe_one_step`) and `owners/cp2.py:30-34`;
  - `ENTRY_VALIDATOR`, as in `cp1a.py:60` and `cp2.py:27`.
- **Steps with `inputs="module_context"`:** `view(historical, attempt) -> (sha256, body)`, following `cp2.py:13-21` (compact JSON, `allow_nan=False`).
- **Owner-only modules:** `STEP_IDS` (a tuple of str), `SCHEMAS`, and `submit(store, ticket_id, step_id, payload, rules) -> Submitted`.
- **Journaled sourced steps:** `RULES(text, seen)`.
- **Optional:** `precheck`. CP-4 has one.
- **Constraints:**
  - Model text is parsed only through `json_object` or `payload_document` (§5).
  - Issue lines are built only with `listed_issues` or `clipped`.
  - The settled tail is `<step-id-with-hyphens>-submission`, whose hash is `SCHEMAS[step].model_validate_json(payload).content_hash()`. This is what `host.py:668-676` checks.
- **Already present:** only CP-L10 has any of these parts (`STEP_IDS` at `cpl10.py:40`, `SCHEMAS` at `:248`). The other 15 cores have none.

**(b) Store adapter: settled head → Stage 1 input object**
- Add a module-private function such as `_inputs(store, attempt, submission) -> <Cp>Inputs`. It reads `store.head_module(head)` of each bound upstream, using the lease's binding source (see §4), and returns the existing Stage 1 type:
  - `Cp2dInputs` (`cp2d.py:134`), `Cp3cInputs` (`cp3c.py:339`), `TriggerInputs` (`cp2h.py:537`), `Cp4cInputs`, `ForwardInputs`, `MacroFxInputs`, `CpdrInputs`, `MarketInputs`, `Cp4Inputs`, `PeerBenchmarkInputs`, `Inputs` (cp2a), `EarningsQualityInputs`, `CP3Inputs`, `LedgerInputs`, `CP5Inputs`.
- `submit`, `probe` and `view` all call this same adapter.
- A producer whose lease names one also ships `<cp>_reader(store, head)`. No reader exists yet: grepping `owners/` for `_reader` finds nothing.

**(c) `owner_workflow.py` registrations** (all inside fixed dicts)
- import line `:95`;
- `SUPPORTED_ANALYTICAL` `:100`;
- `_CORES` `:105` (owner-only modules only);
- `_QUALIFICATION` `:106-111`;
- `_PROBES` `:112-117`;
- `_VIEWS` `:120-122`;
- `_ENTRY_VALIDATORS` `:126-129`;
- the `_default_specs` schema imports `:166-173` and its returned dict `:193-249`;
- `_PRECHECKS` `:272`.

The spec text for each module is the lease's `OWNER_SPECS[...]` line.

**(d) `src/deploy_vii/bindings/<cp>.py`**
- Data only: no arithmetic, and it never imports `deploy_workflow` (protocol §6).
- Copy the pattern in `bindings/cp4.py:27-76`: a `_bind()` helper, a `cp<x>-` slot prefix, block rows, then Evidence and Limitations rows.
- CP-3, CP-4 and CP-5 already have maps (`bindings/cp3.py`, `cp4.py`, `cp5.py`).

**(e) `shipped.py` and `_Spec` rows**
- `bindings/shipped.py:4-16`: one import plus a position in `SHIPPED_MAPS`, as the lease places it.
- `_Spec` rows go in `src/deploy_vii/report_view.py`:
  - compositions `_CREDIT_SNAPSHOT` `:1084`, `_EARNINGS_UPDATE` `:1122` and `_COVENANT_REFINANCING` `:1142`;
  - new compositions: `_RELATIVE_VALUE` (CP-3D), `_DISTRESSED` (CP-2A) and `_EARNINGS_QUALITY` (CP-1D);
  - the `_spec_of` tuple `:1198`;
  - `_PRESETS` `:485+`, where a lease inserts block ids.
- `MODULE_FAMILY` (`:99-120`) has no CP-DR, CP-L10 or CP-8 row (see Q8).

**(f) `DELIVERY_SCOPES`**
- It does not exist yet. `src/deploy_workflow/owner_rendering.py` is absent, and G2 is Stage 3 (plan: Stage 3 G2).
- Stage 2 can therefore only record each module's intended `(pathway, requested modules, synthetic)` scope row from the lease, for G2 to add. See Q1.

**(g) Run driver `tests/<cp>_runs.py`**
- It exports `<cp>_closed(case, root)`: pack assembly, literals, run-time substitutions and the tool-call sequence. G2 imports it.
- Pattern: `tests/s1a_runs.py:27-212`.

**(h) Consumption proof (D3)**
- In the consumer module's tests, assert:
  - the attempt inputs are hash-equal to the final heads;
  - `result_sha256` equals the bound Input;
  - the `derives_from` and copied-cell lineage match `expected.json#consumption`.
- When the lease records D3 as OPEN, the module ships its reader and a test that pins what the reader exposes. Nothing claims completion.

**Also per module:**
- a new `src/deploy_vii/methods/<cp>.md` (only cp0, cp1a, cp2, cp3, cp4, cp5 and cp6 exist today);
- a `docs/reuse/manifest.json` D12 record;
- the D2 view row text for `docs/TOOL-CONTRACT.md`, handed to LEAD.

**Collision points every module edits:**
- `src/deploy_workflow/owner_workflow.py` (`:95-129`, `:166-249`, `:272`);
- `src/deploy_vii/bindings/shipped.py`;
- `src/deploy_vii/report_view.py` (compositions, `_spec_of`, `_PRESETS`, `MODULE_FAMILY`);
- `docs/reuse/manifest.json`.

Shared files that only some modules touch:
- `src/deploy_workflow/host.py` (§5 at `:675`; the H1 rows at `:51-65` and `:88-110` already exist for the 8 sourced owner-only modules);
- `docs/TOOL-CONTRACT.md` and `methodology.json`, which are LEAD's.

## 2. Dependency order and merge serialisation

These are the edges among the 16 modules from `methodology.json`, plus the optional edges a lease actually binds:
- CP-2G needs CP-2A (required) and binds CP-1D in its positive run (CP-2G lease :152).
- CP-2H needs CP-2G.
- CP-4C needs CP-2G, CP-4 and CP-2A.
- CP-3C needs CP-2D.
- CP-5 reads CP-3 (CP-5 lease :194).
- All the others need only shipped modules (CP-0, CP-1, CP-1A, CP-2).

**Stage 2.0, before any cohort** (one owner each; I could not confirm whether these are done or still pending):
1. Merge `codex/checkpoint` b570399 into the lane.
2. Land the held LEAD B1 integration, 40e529c (RESUME "Held").
3. Make one G1-X ride-along change to `owner_workflow.py`:
   - the two `_check_steps` guards from round 10 item 6 (sources must agree with `_OWNER_SCOPES`; `STEP_IDS` must be a tuple of str);
   - CP-4's `StepSpec.inputs` literal `"step_context"` (`:152`; CP-4 lease :37-38), unless LEAD keeps that in the CP-4 module.
4. Get LEAD's ruling on whether `host.py:675` is covered by §5.

**Cohorts.** At most about 5 implementers at a time, so that two reviews per module stay under the six-Opus cap. I did not confirm that the reviewer agents run on Opus.

| Cohort | Modules (merge order) | Why |
|---|---|---|
| 1 | CP-4, CP-2A, CP-2D, CP-3D, CP-DR | CP-2A creates `_DISTRESSED`; CP-3D creates `_RELATIVE_VALUE`; CP-2D is the producer for CP-3C; CP-4 is the producer for CP-4C |
| 2 | CP-1D, CP-1C, CP-2E, CP-8, CP-L10, CP-3 | CP-1C appends to `_RELATIVE_VALUE`, so it goes after CP-3D. CP-1D is the producer for CP-2G |
| 3 | CP-2G, CP-3C, CP-5 | CP-5 is held unless Q2 is resolved |
| 4 | CP-2H, CP-4C | Both read `cp2g_reader` |

A module also waits for its own round 13 or fix work to merge. The ledger shows these in flight: CP-1D fix1, CP-2D fix1, CP-4C r13 review.

**Merges:**
- One module merges at a time, in the cohort order above.
- Every registration hunk is append-only: add new rows at the end of each dict or tuple, and never reorder existing rows. The exception is `SHIPPED_MAPS`, where the lease's stated position applies.
- The implementer rebases on the lane tip before review.
- After approval, if the tip has moved, the implementer rebases again and reruns the fast gates and the registration test. `mx-feature` then checks the rebase diff, limited to the registration hunks.
- The controller merges and runs the fast set on the lane, and logs it in the ledger.

## 3. Per-module brief template (ICM stage contract)

**Inputs**

| Item | Value |
|---|---|
| Lane tip | `<sha>` (Step 0: `git rev-parse HEAD` must equal it; stop on mismatch) |
| Lease | `docs/<CP>-OWNER-LEASE.md` (the D12, Public API, D3 and D7 sections) |
| Protocol | `docs/G1X-OWNER-CORE-PROTOCOL.md` §2-§6 |
| Oracle | `cases/<slug>-owner/{manifest,submissions,expected}.json`, plus `cases/PINS.json` |
| Core | `src/deploy_workflow/owners/<cp>.py` (Stage 1 input type `<Cp>Inputs`) |
| Patterns | `owners/cp1a.py`, `owners/cp2.py`, `bindings/cp4.py`, `tests/s1a_runs.py`, `tests/test_owner_g1x.py:333-341` |
| Backlog | the "Every module" rows and this module's rows in `work/build/stage2-backlog.md`; notes in RESUME "Stage 2 notes collected" |
| Upstream | readers of producers that have already merged (see §4) |

**Process**
0. Enter a worktree at the lane tip and check HEAD. Stop on mismatch.
1. **Backlog first.** Apply this module's backlog rows test-first:
   - the guard-limit notes in `methods/<cp>.md`;
   - the blank-quote inventory and its fix;
   - `listed_issues` lines;
   - the per-module rows.

   A row that waits on a LEAD re-pin is reported as blocked, not worked around.
2. **Test-first for each part:** the plug-in parts, then the adapter, registrations, bindings and `_Spec` rows, then the reader, the run driver and the D3 test. Write each test, watch it fail, then write the code.
3. **No stub, fake value or catch-all in `src`.** A fake core or session is allowed only in tests. A missing operand settles as a gap, never 0.
4. **Library boundary:**
   - Do not edit `methodology.json` or `TOOL-CONTRACT.md`; report the edit instead.
   - `src/deploy_vii` changes only by the D12 one-liners plus `bindings/<cp>.py` and `methods/<cp>.md`.
5. **Gates, all exit 0:**
   - `ruff check` and `ruff format --check` on the changed files;
   - `MYPYPATH=src mypy --strict src`;
   - the fast tests below, using `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python -m pytest -q -p no:cacheprovider`.
6. **Fast tests (under about 60 s each).** These go in a new `tests/test_connect_<cp>.py`:
   - `tests/test_method_<cp>.py` stays green;
   - the registration rows equal the lease, and `_check_steps(m, OWNER_SPECS[m])` passes;
   - `SCHEMAS` round-trips and gives the tail digest on the oracle literals;
   - `RULES` and `precheck` reproduce the oracle refusals;
   - the adapter, over `Module` objects built from frozen oracle facts, returns exactly the Stage 1 test's input object;
   - `view` matches `view_tree_draft` keys and contains no quote strings;
   - `validate_bindings` over the expected tables returns `()`, and `_spec_of(block)` returns the row;
   - `tests/test_owner_g1x.py` and `tests/test_host_h1.py`. These are in the H1b gate (`h1b-brief.md:39`), but I did not confirm they run under 60 s.
7. **Deferred to Stage 5** (write them, do not run them): `tests/test_owner_<cp>.py` store runs, `tests/<cp>_runs.py`, the D3 run assertions, receipt verification, promotion, `test_owner_workflow.py`, `test_owner_s1a.py`, the source-tools and source-workflow suites, and render runs. List the exact commands for `work/build/deferred-runs.md` (that file does not exist yet).
8. Run confidence-review, then commit.

**Outputs**
- Commit SHA, files, and each lease line → symbol.
- Backlog rows, each done or blocked.
- Test-first evidence and the gate exit codes.
- Any `methodology.json` or TOOL-CONTRACT text for LEAD.
- The deferred commands.
- Reviews: `mx-adversary` reviews the adapter, reader and D3 test; `mx-precise` reviews the rest. Fix rounds go to `mx-feature`.
- The report ends with `Not verified:` and then `agent=mx-feature fix-rounds=<n> gates-first-pass=<y|n>`. Use `n/a` per AGENTS.md when the affected tests are deferred.

## 4. Per-module specifics

| Module | Kind / step | Upstream | Binding source (manifest key) | Driver | Notes, backlog and risks |
|---|---|---|---|---|---|
| CP-2E | owner-only `macro_fx`; sources, `inputs="none"`, journaled | CP-0 | `run`, `step_scope` | `cp2e_runs.py` | D3 OPEN (lease :156). No block, module page only (:162). Methods: rule W and item 8 notes. `fx.` paths. Label-decimal question still open with LEAD |
| CP-DR | owner-only `research`; sources and module_context | CP-0 | `upstream_facts_read`, `cp0_delta` | `cpdr_runs.py` | D3 OPEN (:177). Rails only (:36). f-string issue sites. No `MODULE_FAMILY` row |
| CP-3D | owner-only `market_implied`; sources | CP-0 (CP-2H unbound) | `run`, `market_source_pin` | `cp3d_runs.py` | D3 OPEN (:162). Creates `_RELATIVE_VALUE`. Re-pin `amortisation_nonzero`, then remove `STAGE2_REFUSAL_DELTA` (LEAD). Signed value_text Info |
| CP-4 | live-contract `legal_covenants`; precheck | CP-0, CP-1 | `frozen_inputs`, `requested_modules` | `cp4_runs.py` | Its bindings and `_Spec` rows already exist (`report_view.py:1142-1161`). Adds `step_context`. Its `_ENTRY_VALIDATORS` row is not in the lease file list (:36-41) (Q3). The lease cites `owner_workflow.py:558` and `:530`, which are stale. T4C.7 display is open |
| CP-1C | owner-only `peer_benchmark`; sources and module_context | CP-0, CP-1 | `cp1_fact_selection_rule`, `host_scope` | `cp1c_runs.py` | D3 OPEN (:118). `peer-positioning` row, after CP-3D. f-string sites |
| CP-2D | owner-only `liquidity_bridge`; module_context | CP-0, CP-1, CP-2 | `fact_bindings` (manifest.json:87) | `cp2d_runs.py` | Ships `cp2d_reader`; D3 is closed by CP-3C. Three `_COVENANT_REFINANCING` rows. Re-pin, then remove `PERIOD_DELTA` and `GAP_VALUE_CLASS_DELTA`. Plan notes: T4.13 reads `not_ready`; the stale-head re-raise is now at `owner_workflow.py:770-774`, not the plan's :452-456. `liquidity-runway` is shared with distressed |
| CP-L10 | owner-only `change_screen`; module_context | CP-0, CP-1 | `fact_selection_rule`, `run_time_bindings` | `cpl10_runs.py` | D3 OPEN (:165). Rails only. Backlog: `-0`/exponent, missing-change lineage, L10-b note. §5 rewire at `cpl10.py:935-937` (`json.dumps` then `model_validate_json`). No `MODULE_FAMILY` row |
| CP-2A | owner-only `downside_pathway`; module_context | CP-0, CP-1 | `fact_selection_rule`, `run_time_bindings` | `cp2a_runs.py` | D3 is closed by CP-2G (:138). Creates `_DISTRESSED`, the `_spec_of` entry and the `_PRESETS` insert (:32). f-string sites; L6 |
| CP-1D | owner-only `earnings_quality`; sources and module_context | CP-0, CP-1 (CP-1B optional) | `cp1_fact_selection_rule`, `plan` | `cp1d_runs.py` | D3 is closed by CP-2G (:110). Creates `_EARNINGS_QUALITY`. Recipe-text re-pin (LEAD). 1D4 and rule W notes |
| CP-3 | live-contract `relative_value`; sources and module_context | CP-0, CP-1, CP-2 (reads CP-1A) | `cp3-cp6-owner` `runs` | `cp3_cp6_runs.py` (`cp3_closed`) | The D3 consumer is CP-6, whose half of the lease is still draft rev 0 (lease :1) (Q2). Optional `T6-FINAL` methodology edit (Q7) |
| CP-2G | owner-only `forward_credit_model`; module_context | CP-2A, CP-1D | `fact_selection_rule`, `upstream_fact_selection` | `cp2g_runs.py` | Closes D3 for CP-2A and CP-1D (:152). `cp2g_reader` also returns the T2H.3 sources (:3). Backlog: `base_period` invariant, `Cp2aScenario.name`, I1 raise. §5 rewire at `cp2g.py:841` |
| CP-8 | owner-only `decision_ledger`; sources, `inputs="none"` | CP-0 (CP-6 not exercised) | `run`, `synthetic_sources` | `cp8_runs.py` | D3 OPEN (:93). Binds to `what-changed` (`report_view.py:1117`). Several methods notes. No `MODULE_FAMILY` row |
| CP-5 | live-contract `integrity_review`; view | CP-0; reads CP-1, CP-1A, CP-2, CP-3 | `run_time_bindings` | shared `cp3_cp6_runs.py` (`cp6_closed`, lease :111) | It is the D3 proof for CP-1, CP-1A, CP-2 and CP-3 (:194). No `_CORES` row (:52). Its driver needs CP-6 (Q2) |
| CP-4C | owner-only `restructuring_fulcrum`; sources and module_context | CP-2G, CP-4, CP-2A | `fact_selection_rule`, `sources` | `cp4c_runs.py` | Proves D3 for CP-2G, CP-4 and CP-2A (:76-77). Two `_DISTRESSED` rows. §5 rewire at `cp4c.py:959`. Its `Cp2gHead` (`cp4c.py:427`) and the lease's `cp2g_reader` type may diverge (Q6) |
| CP-2H | owner-only `rating_triggers`; sources and module_context | CP-2G | `cp1_fact_selection_rule`, `upstream_fact_selection` | `cp2h_runs.py` | Proves D3 for CP-2G (:119). `rating-triggers` row. Backlog: B8 note, the B8 later-line Low, B7 xfail to a plain test, and the cp2g expected hash check. §5 rewire at `cp2h.py:1629` |
| CP-3C | owner-only `refinancing_risk`; module_context | CP-2D | `fact_bindings` (:142), `cp0_consumer_deltas` | `cp3c_runs.py` (imports the `cp2d_runs` helpers) | Proves D3 for CP-2D (:183). `refinancing-paths` and `lme-creditor-exposure` rows. Info items 1-3. Re-pin the 6 periods; `fact_copy_rule`. The funding-gap ownership conflict is still open (lease question 2). Line :185 "CP-4C has no core" is stale |

The RESUME §5 line numbers have drifted: cp2g 840 → 841, cp4c 953 → 959, cpl10 926 → 935-937, cp2h 1623 → 1629.

## 5. Stage 2 end review

An Opus reviewer (`mx-precise` or `mx-autonomous`) reviews the merged lane. Findings go to `mx-feature` fix rounds.
1. **Core seams.** Each core's parts match protocol §2, including the §5 parse rule and the `listed_issues` rule. Grep for any `json.loads` or `model_validate_json` on raw text.
2. **Registration rows.** Every dict in `owner_workflow.py:95-272` has exactly one row per module, `entry=="owner_core"` holds exactly for the owner-only modules, and a fresh import passes `_check_steps` for every spec.
3. **Edges.**
   - For each run, the CP-0 consumer delta literal assesses every live consumer exactly once (`readiness.py:319-325`).
   - Attempt inputs equal `registry.plan` order.
   - Upstream edges match `methodology.json`.
4. **Block chain.** Binding slot → block id → `_Spec`, with one row per block id, checked across all compositions and `_spec_of`; `validate_bindings(SHIPPED_MAPS)` returns `()`. Then each binding → `DELIVERY_SCOPES`, which is deferred to G2 (Q1).
5. **D3.** Each consumer's D3 test matches its lease. Every OPEN D3 has a reader and no completion claim.

## 6. Open questions for LEAD or the owner

1. **Q1.** `DELIVERY_SCOPES` and `owner_rendering.py` do not exist, so the plan's Stage 2 review item 4 cannot fully close. Should it close at `_Spec`, with the scope rows going to G2 in Stage 3?
2. **Q2.** The CP-6 half of the CP-3 lease is draft rev 0. That blocks CP-3's D3 and CP-5's driver (`cp6_closed`). Should we freeze CP-6, or give CP-5 its own driver?
3. **Q3.** Protocol §2 requires a CP-4 `_ENTRY_VALIDATORS` row, but the CP-4 lease file list omits it. Confirm.
4. **Q4.** The `step_context` literal: does it go in the CP-4 module or in the G1-X ride-along?
5. **Q5.** Is `host.py:675` (`schema.model_validate_json(store.payload(...))`) covered by §5?
6. **Q6.** Reader types: consumers already define `Cp2gHead`, `Cp2aHead` and `Cp4Head` (cp4c, cp2g), while the leases put `<cp>_reader -> <Cp>Head` in the producer. Which module owns each type?
7. **Q7.** `methodology.json`: the only pending edit I found is CP-3's optional `T6-FINAL`. CP-1C, CP-1D and CP-L10 already landed in ede9ffe.
8. **Q8.** Is a `MODULE_FAMILY` row for CP-DR, CP-L10 and CP-8 an admitted D12 one-liner?
9. **Q9.** Some backlog rows wait on LEAD's release re-pins: CP-2D and CP-3C deltas, CP-3D `amortisation_nonzero`, the CP-1D recipe text, and `is_blank` Cc. When is that release?
10. **Q10.** Should one owner of the `report_view.py` compositions (CP-2A for `_DISTRESSED`, CP-3D for `_RELATIVE_VALUE`) create them first? Or should one D12 commit add the empty compositions so that later modules only append rows?
11. **Q11.** Do we build the shared quote-reader helper under `owners/` before the cohorts (it waits on the M3, M4 and L1 rulings), or leave it out of Stage 2?

**Not confirmed:**
- the fast-set command, and whether `test_owner_g1x.py` and `test_host_h1.py` run under 60 s;
- whether the reviewer agents count against the Opus cap;
- the CP-4C and CP-2H own-consumption status beyond lease :76-77 and :119.

### Critical Files for Implementation
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/src/deploy_workflow/owner_workflow.py
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/src/deploy_vii/report_view.py
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/src/deploy_vii/bindings/shipped.py
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/docs/G1X-OWNER-CORE-PROTOCOL.md
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/tests/s1a_runs.py