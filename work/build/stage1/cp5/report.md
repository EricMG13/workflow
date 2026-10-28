# CP-5 Stage 1 report (controller-saved from the implementer's hand-back)

# CP-5 Stage 1 report

The CP-5 calculation now matches the frozen oracle on both cases and all 12 validator refusals. The test gives 45 passed in 1.81 s and every gate exits 0, but the format check failed on its first run, so gates-first-pass=n. The host refused the report file `work/build/stage1/cp5/report.md`, so this text is the report and the controller needs to write it.

- **Branch:** `claude/cp5-stage1`.
  - Step 0: `git cherry-pick 2682310` landed as `c019fac`. Nothing it brought was edited.
  - Commit: `4e2d687 feat(cp5): Stage 1 calculation against the frozen oracle`.
- **Files:**
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp5-stage1/src/deploy_workflow/owners/cp5.py` (new, 114 lines)
  - `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp5-stage1/tests/test_method_cp5.py` (new)
  - `owners/__init__.py` already existed. `src/deploy_vii`, `cases/` and other tests were not touched.

## Design
The lease adds no CP-5 arithmetic and no new composer. The existing engine `deploy_vii.cp5_integrity` runs the checks, validates the review and composes the tables.
- `CP5Inputs(scope: ReviewScope, submission: IntegritySubmission)`: the typed input object.
- `compute(inputs) -> CP5Result(issues, report)`: calls `validate_integrity`, then `integrity_review`.
- `candidate(result, inputs, attempt)`: calls `cp5_module`. A refused result raises `ValueError`.
- `owner_projection(scope)`: the lease's `P`. CP-1 gets `live.context.integrity_projection`; every other head keeps all its facts.
- `view_body(scope) -> (sha256, body)`: the lease's construction steps 2–6.
  - A scope with issues raises `WorkflowError("identity_mismatch")`, the lease's step-1 outcome.
  - Citations keep `ref`, `source_id` and `locator` only.
  - Each per-claim finding mark is cut at its first `": "`.
  - Top-level findings are the kind label plus where (`KIND_LABEL[f.kind] + ": " + f.where`).
  - The body is compact JSON.
- None of these names clash with G1-X §2. `QUALIFICATION`, `probe`, `view` and `ENTRY_VALIDATOR` are left for Stage 2.

## Input fields (Stage 2 source)
| Field | Type | Stage 2 source |
|---|---|---|
| scope.pack | PreparedPack | `store.pack(snapshot)`, via `cp5_integrity.review_scope` |
| scope.inputs | tuple[Input, ...] | `attempt.inputs`: prepared-pack, CP-0, CP-1, CP-1A, CP-2, CP-3 in plan order, each with its producer status |
| scope.heads | tuple[(Input, Module), ...] | `store.result(sha)` for each bound analyst input outside `NOT_EVALUATED` |
| scope.blocked | frozenset[str] | `execution.blocked_ancestors(snapshot, attempt.inputs)` |
| scope.inherited | tuple[str, ...] | `execution.inherited_limitations(snapshot, attempt, (), head_module)` |
| scope.issues | tuple[str, ...] | the stale and unreadable checks in `review_scope` |
| submission | IntegritySubmission | judgment: the `integrity_review` payload, with `{{FIG:name}}` bound to the CP-1 fact_id |

The manifest has no `fact_bindings`, because CP-5 reads whole heads.

## Test and gates
- **Test:** `PYTHONPATH=src …/python -m pytest -q -p no:cacheprovider tests/test_method_cp5.py` gives 45 passed in 1.81 s.
  - Before the core existed it failed with `ModuleNotFoundError`.
  - This is a light run with no heavy-job lock. It follows the brief, although memory says tests wait for LEAD's final phase.
- **Gates (exit codes):**
  - `ruff check`: 0
  - `ruff format --check`: 0, after one `ruff format`
  - `MYPYPATH=src mypy --strict owners/cp5.py`: 0

**Fixture.** The heads come from the oracles that `manifest.reuse.heads` names:
- CP-1A: the S1 positive head with the CP-3 oracle's R6 table deltas applied.
- CP-2: the S1 positive head.
- CP-3: the CP-3 oracle head.
- The `cp1_references` tables hold verbatim copies of the CP-1 stand-in facts.

The oracles record citations as (source, locator) only, so quotes come from the pinned literal submissions:
- A claim keeps its own literal citations, checked against the oracle's (source, locator).
- A fact citation takes the first literal quote at the same (source, locator).

The CP-1 head is a stand-in for the genuine promotion. It has:
- the 4 T4.10 LTM figures, with amounts from the financial oracle;
- 2 facility facts that no claim names;
- 7 narrative claims with the oracle's ids and limitation, label-only text, and one citation each at the RT-3 locator quoting one line of that page;
- a fixture own-limitation.

Body sizes on this fixture:
| Case | Body | CP-1 | CP-1A | CP-2 | CP-3 |
|---|---|---|---|---|---|
| positive | 155,974 B | 5,550 B | 107,997 B | 28,140 B | 12,174 B |
| gap | 150,559 B | 5,638 B | 105,736 B | 28,228 B | 8,767 B |

## Oracle sections covered
- **Pins:** the 4 lease pins and the 7 manifest pins.
- **Positive and gap cases:**
  - all 17 tables, cell by cell, with the T5.5, T5.8 and T5B.7 bound-row rules applied and every run-time marker bound;
  - table ids;
  - findings (none), report status, own limitations, evaluated and not-evaluated sets, claim count, module inputs;
  - the candidate has no claims;
  - Python checks find nothing (`expected_findings`);
  - the inherited sequence matches `flattened_without_bound_CP-1`.
- **Owner view:**
  - key tree and counts;
  - digest equals sha256 of the body; compact form; recomputing gives the same body;
  - no `quote` key, and no citation quote outside the CP-3 T3.3 `*.quote` facts the lease exempts; on the positive case those facts contain the CP-3 claim quotes;
  - CP-1 lists exactly what `integrity_projection` keeps; every other head lists every fact;
  - every literal upstream_ref appears in the body;
  - a scope with issues gives `identity_mismatch`.
- **Beyond the oracle:** one claim quote made to fail, plus a hypothesis property over generated failing quotes.
  - Top-level findings are exactly `KIND_LABEL: where`, and per-claim marks hold the kind only.
  - Neither the quote nor its prefix reaches the body.
- **Refusals:** all 12 validator refusals. 11 match the exact issue lists, and the shape refusal matches its prefix through `shape_issues`. Also tested: a refused candidate raises, and scope issues pass through `compute`.
- **Left to Stage 2/4:**
  - settled limitations, settled inherited limitations and module status;
  - RT-1 to RT-3 against the genuine CP-1 head;
  - `view(historical, attempt)`, its registration and the read_inputs digest;
  - the 4 tool-use refusals, 3 tamper refusals and the blocked case (CP-6 `RefusedBegin`);
  - CP-6 consumption, render rails and slots, the receipt and probe, and the TOOL-CONTRACT row.

## Engine/oracle disagreements
None.

## Hand mutation
Each mutant ran in a full temporary copy of the worktree (no `.git`). The baseline copy passes.

**Killed (20):**
- `compute`: no refusal return; inverted guard.
- `candidate`: no guard; attempt fixed at 0; inputs sliced.
- `owner_projection`: inverted; no projection; projection on every head; module id changed to CP-1A.
- `view_body`: issue guard removed; quote kept; citation key order changed; no per-claim cut; top level uses subject; top level keeps detail; top level shows the raw kind; default separators; `ensure_ascii=True`; wrong digest; top level not replaced.

**Survivor M14** (cut at `":"` instead of `": "`): the two only differ when a flagged ref contains `:`. Fact ids may contain `:`, but none in the bound heads does.

**Oracle one-cell mutations:** a T5.3 cell, the T5B.8 evaluated set, the view key tree and one refusal issue each fail a comparison test, not only the pin test.

## New strings
`prose.issues` and `bare_figures` report 0 hits on:
- "A refused CP-5 submission has no candidate: "
- "identity_mismatch"
- the fixture's CP-1 own-limitation text
- all 28 parts of the fixture's CP-1 claim texts

## Property tests
CP-5 has no arithmetic, so there are no arithmetic invariants to test. One hypothesis property covers the view: a failing quote never reaches the body (12 examples).

## Confidence review
1. **The view edits the dict `context_block` returns.** Fine: it is rebuilt on every call, and the test recomputes it.
2. **The mark formats are `kind: detail` and `kind on ref`.** Fine: confirmed in the engine's checker. M14 is the one edge.
3. **Import cycle through `deploy_workflow.workflow`.** Fine: `workflow.py` imports no owner module, and `owners.cp2` imports it the same way.
4. **`python_checks` runs three times per view and three times per `compute`.** The view takes 0.03 s on the fixture. Still open: the cost on a promoted CP-1 is unmeasured.
5. **The fixture's quote choice could hide a leak.** Mitigated: all quotes are real literal excerpts. 23 distinct quotes (positive) and 21 (gap) were checked.
6. **The shape refusal is checked at parse time, not through `compute`.** By design: Stage 2's step entry (`_validate_step`) does the parse, as CP-2A's Stage 1 test does.

## Rewrite tournament
- `compute`, `candidate` and `owner_projection` fall under the skill's skip bar (under about 15 lines, no new branching).
- `view_body` is one guard plus the lease's fixed six-step construction. I judged it inline and the incumbent holds; no challenger agents were run.

## Rulings needed from LEAD
1. `view_body` raises `WorkflowError("identity_mismatch")` (the lease's step-1 wording) inside the pure function instead of a plain `ValueError`. Confirm.
2. The refused-candidate message "A refused CP-5 submission has no candidate: <issues>" is not pinned; it copies the CP-3 Stage 1 wording. Confirm or pin it.
3. `python_checks` runs three times per view, because none of `integrity_projection`, `context_block` or the engine's other seams takes precomputed checks. Accept this, or add an engine seam? That would need a `src/deploy_vii` edit, which is not done here.
4. Informational: the lease's "39 facts / 28" for CP-3 leaves out the 3 `cp1_references` copies. The head holds 42 / 31.

## Probes and runners (all exit 0)
In `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-stage1/`:
- `mutate_run.py`
- `oracle_mutation_probe.py`
- `prose_probe.py`
- `stats_probe.py`

Not verified: the genuine CP-1 head (RT-1 to RT-3, its facts, citations and limitations, and the projection and body size over it); `review_scope` over a journal; `view(historical, attempt)`, its registration, the read_inputs digest and the verifier; settlement, module status and settled inherited limitations; the tool-use, tamper and blocked-case refusals; CP-6 consumption; rendering; the real fact-citation quotes of CP-1A and CP-3 (the fixture takes the first literal quote at each locator); `python_checks` cost on a promoted CP-1; the M14 `:` edge.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n

## Controller rulings before the first review (2026-10-28)
- 1 (`WorkflowError("identity_mismatch")` in `view_body`, the lease's step-1 outcome), 2 (refused-candidate message mirrors CP-3), 3 (`python_checks` three times per view; no `src/deploy_vii` seam): kept as built; sent to LEAD to confirm.
- 4 (CP-3 fact count 42/31 with `cp1_references`): information for LEAD.
