# S1a credit-snapshot run lease — rev 1, FROZEN by LEAD 2026-10-28

Drafted 2026-10-28 (read-only mx-autonomous), independently reviewed (`docs/reviews/s1a-g2-lease-review.md`), frozen with the amendments at the end of this file, which override the body where they differ. Implementation starts only after the prerequisites below are integrated.

## Why

S1a is the first run with several owners: CP-0 → CP-1 → CP-1A → CP-2, with CP-MODEL published last. That is the order `registry.plan` gives (checked: `('CP-0','CP-1','CP-1A','CP-2','CP-MODEL')`), and G1 publishes only once the analytical walk is done. The run goes over the frozen S1 oracle (`cases/snapshot/*`, sha256 expected `d1aa1af9…9baa`, manifest `68d591f6…f3f4`, submissions `bff9ed18…b35c`; the adopted manifest needs 49801d7 on `codex/checkpoint`). S1a ends at verified settled heads plus a verified `OwnerRunReceipt`. FP01, the rails and G# numbering belong to G2.

## Prerequisites (base)

The base is `codex/checkpoint` with both of these integrated:
- **G1**, after fix round 1 and its re-review.
- **L2**. Its uncommitted `host.py` adds `_cp1_producer_inputs` (coordinator-1-source-host `host.py:425-447`).

**H1 trace.** CP-1A's ticket binds the CP-1 head as a context input (`execution.py:226`, `:252-258`). A CP-1A `SourceSession` therefore authenticates CP-0 and CP-1 through `_producer_inputs`.
- Today `host.py:36-37` compares `producer.inputs == current_inputs`. The promoted CP-1 module carries four extra tails: `cp1_workflow.py:389`, `model_interface.py:596-597`, `canonical_tables.py:828-829`. So the session refuses with `identity_mismatch`.
- Even before that check, `_SOURCE_STEPS` (`host.py:18`) has no CP-1A entry, so the session refuses with `not_permitted`.
- CP-2 is submit-only and opens no session. CP-MODEL does not use the host.

So S1a needs L2's CP-1 authentication plus one line in `host.py`: `"CP-1A": ("business_context",)`. The generic `*-submission` rule (full H1) is needed only once a pack-tool consumer binds CP-1A or CP-2 (S2). It is not part of S1a.

## Files

- `src/deploy_workflow/owner_workflow.py`: extend G1.
- New `src/deploy_workflow/owners/__init__.py` (empty), `owners/cp1a.py`, `owners/cp2.py`.
- `src/deploy_workflow/host.py`: the one `_SOURCE_STEPS` line, serialised by PM after L2.
- New `tests/test_owner_s1a.py`.
- No `src/deploy_vii` edits. The CP-1A and CP-2 step chains, schemas, entries and table ids already exist (`registry.py:351-360`, `submission.py:251-271`).

## Public API additions

```
StepSpec.inputs: Literal["none", "projection", "module_context"]
OWNER_SPECS += "CP-1A": OwnerSpec("CP-1A", (StepSpec("business_context",
                 BusinessContextSubmission, sources=True, extract=False, None, "none", rules=True),),
                 "model_payload", "analytical", None)
             += "CP-2":  OwnerSpec("CP-2", (StepSpec("credit_synthesis",
                 CreditSynthesisSubmission, False, False, None, "module_context", rules=False),),
                 "model_payload", "analytical", None)
owners.cp1a.probe(store, snapshot, attempt) -> None
owners.cp2.probe(store, snapshot, attempt) -> None
owners.cp2.view(store, attempt) -> tuple[str, str]   # (sha256, body)
```

The receipt schema, the JSON-lines operations and the return shapes do not change.

## G1 extension (`owner_workflow.py`)

1. **Registrations.**
   - `SUPPORTED_ANALYTICAL` (`:75`) adds CP-1A and CP-2.
   - `_QUALIFICATION` (`:78`) adds `business_context.PROMOTED` and `cp2_synthesis.PROMOTED`.
   - `_PROBES` (`:79`) adds the two owner probes.
2. **Historical binding.**
   - CP-0 and CP-1 keep `_fin` and the reused helpers.
   - Every other module uses a new `_owner_historical(store, OwnerBinding)`. It applies the checks of `financial_workflow.py:270-288`, with `sequence = step_chain(module).steps`.
   - This is used by `_activate` (`:432`) and by both verifier replays (`:960`, `:1011`).
3. **Fill.** One-step modules use `normalise(STEPS[step].schema, payload)` with an empty prefill. That is the path `submission.py:969-986` takes. The financial `_filled` would fail here: `bound_steps()` has no `business_context` entry, so `known_bindings` raises `KeyError`.
4. **Rules.**
   - CP-1A passes `rules=lambda p: ToolRules().issues("business_context", p, seen=evidence.seen(), context=None)` to `submit_model_payload` and runs no pre-check. Its rules are absence plus unread-citations (checked with `applicable_rules`).
   - CP-2 passes `rules=None`; `submission.py:967` raises otherwise.
5. **`read_inputs` for `module_context`.**
   - The body is `json.dumps(module_context(historical, attempt, step_id), ensure_ascii=False, separators=(",", ":"), allow_nan=False)` and the digest is its sha256 (`live/context.py:111`; `cp2_synthesis.py:959-1019`).
   - The existing rule stays: a session-less step needs a read on its own binding before it can submit (`:549`).
6. **`_check_specs`.** It accepts `module_context` only for a step in `MODULE_CONTEXTS` that has no pack sources. The spec still has to equal `OWNER_SPECS`.
7. **`_verify_submissions`.** For journaled-rule steps it recomputes the rule issues at the historical binding:
   - a valid step must have none;
   - for an invalid step, every recomputed issue must appear in `step.issues`.

   `_verify_calls_reads` replays CP-2 reads through `owners.cp2.view`.
8. **Probes.** Each probe follows the pattern of `financial_workflow.py:1168-1195`:
   - exactly one valid step;
   - the module's `_validate_step` on `_FrozenExecution(store, snapshot)` gives no issues, and its output bytes equal the retained output;
   - `cp1a_module` / `cp2_module(report, attempt.inputs, attempt.number)` rebuilds the candidate;
   - `settle(...)` gives back exactly the finished attempt and the head module.

## Behaviour and refusals

- **CP-1A `invoke`.**
  - `search_pack` and `read_pages` work over every pack source (ruling Q3; `context.py:85-87`, `:144-151`).
  - `extract_statements` returns a refused receipt.
  - `read_inputs` refuses `not_permitted`.
- **CP-1A failed rule.** A submit that fails a rule is journaled as invalid.
  - Attempt 0 is re-begun as attempt 1.
  - If attempt 1 is also invalid, CP-1A settles blocked. CP-2 still begins, because the CP-1A→CP-2 edge is restricted.
- **CP-2.**
  - Every `invoke` is a refused `not_permitted` receipt.
  - A submit without a read refuses `not_permitted`.
  - A snapshot change between the read and the submit refuses `stale_binding`.
- **Other refusals.**
  - `requested_modules` that include CP-5, or any module without a spec, refuse at `create` and write nothing.
  - A spec override refuses `not_permitted`.

No stub or fake value stands in for real behaviour. No catch-all hides a failure. The only documented fail-closed paths stay those of G1.

## Run-time bindings (declared by the oracle)

- `<<PACK_SHA256…>>`: `PreparedPack.content_hash()` of the S1 pack. It is used in `readiness_review`, `cp1_source_context` and the CP-0 facts.
- `{{FIG:name}}` becomes `{<fact_id>|<unit_token>}`.
  - `fact_id` is the unique entry in the CP-2 read body's `cp1_facts` that names a T4.10 fact of that metric on the twelve-month (LTM) basis ending Q4 2025, never the FY2025 column (`metric_coordinate_rule`).
  - The test asserts that its `unit` equals `unit_token` and its `shown` equals the oracle spelling (1.67x / 1.00x / 6.00x / 18.0%).
  - Zero or several candidates fail the test.
  - The same substitution applies to the expected CP-2 claims.
- **CP-1 fact ids, labels, periods and citations** in `cp1_references` and the T2.1 basis cells (Q6, N2).
- **CP-1's own and inherited limitations**, bound into the inherited lists by the oracle's order rule (R3-Q1).
- Ticket ids and call ids are compared structurally only.

**Pack.**
- identity and financial come from `cases/financial/manifest.json`, hash-checked, with the financial `LIMIT`.
- business comes from the snapshot manifest's case pages, hash-checked against `business_source_sha256`, with the fields from `common` and the case limitation.
- `Run` comes from the case `run`.

**CP-1 inputs.** CP-1 uses the S1 literal `source_context`. Its later stages are those of `tests/test_financial_workflow.py:953-1050` (`financials(pack)`, `narrative(read)`, `{"consumers": []}`, and the QA built from the read inputs), imported as G1 does.

## Acceptance (expectations only from `expected.json`)

**A1 positive and A2 gap.** One closed run per case:
- **Statuses.** `statuses_S1a`: every head restricted. The CP-0 T8 commands read "Run CP-1", "Run CP-1A" and "Run CP-2". CP-0's 56 facts and its limitations match.
- **CP-1A.**
  - all 23 tables: table id, title, columns, rows, and per fact the text, status, `[source_id, locator]` cites, value class and limitation;
  - claims;
  - own and settled limitations;
  - gap case: Insufficient Information ownership and transaction rows, kept as missing, never 0.
- **CP-2.**
  - all 10 tables, with the bindings above;
  - claims, signals (none in the positive case, three in the gap case), own and settled limitations, and `figures_referenced`.
- **Inherited limitations.** CP-1A and CP-2 inherited lists equal `literal_head + CP-1 head (limitations, then inherited) + literal_tail`, de-duplicated, with own findings removed (`execution.py:345-366`).
- **CP-MODEL.** Published, and `verify_cp_model_publication` returns no issues.
- **Receipt.** It verifies, and the store and model bytes are unchanged afterwards.

**Tool use** (`execution.tool_use`):
- Before each pack-tool submit, the receipt holds ok `read_pages` calls covering every `page:N` cited by that literal submission.
- CP-1 positive also holds a `search_pack` over business. CP-1A holds at least one `search_pack`, because the literal submission carries `available: No` and `Not disclosed` rows.
- CP-2 has zero ok calls and exactly one `read_inputs` per attempt before its submit.

**Consumption** (`execution.consumption`): see the next section.

**A3 tool-use refusals.** On clones of the run:
- CP-1A without a business page:3 read is invalid with an issue naming `business page:3`. It is re-begun as attempt 1 with `repair_of` set, and a valid attempt 1 then still yields a receipt that verifies.
- CP-1A with no search is invalid on the absence rule.
- CP-2 `read_pages` is refused; CP-2 submit before a read is `not_permitted`.
- CP-2 with `{{FIG}}` left unreplaced is invalid (the oracle says it "fails closed").
- A stale snapshot between read and submit gives `stale_binding`.

**A4 tamper.** Each of these makes `verify_owner_run_receipt` refuse with `identity_mismatch`:
- an edited CP-2 read body in the audit;
- an edited CP-1A step output;
- an edited CP-2 `SettledHead`.

**A5 regression.** `tests/test_owner_workflow.py` passes unchanged.

**Gates.** `ruff check`, `ruff format --check` and `mypy --strict` (`MYPYPATH=src`) pass on every changed file. Heavy tests run under the heavy-job lock.

## What proves downstream consumption

- **CP-1A attempt inputs** are exactly `prepared-pack`, CP-0 and CP-1, carrying the heads' `result_sha256` at begin. The settled module adds `business-context-submission`.
- **CP-2 attempt inputs** are `prepared-pack`, CP-0, CP-1 and CP-1A in plan order, hash-equal to the final heads. The settled module adds `credit-synthesis-submission`.
- **The CP-2 read body is the core's actual view.**
  - `cp1a_rows` length equals `catalogue_size` (70 / 62);
  - `cp1a_signals` equal the expected signals;
  - the upstream statuses are CP-0, CP-1 and CP-1A restricted;
  - `inherited_limitations` follow the inherited rule.
- **The verifier probe** reruns `cp2_synthesis._validate_step` (which reads both bound heads, `cp2_synthesis.py:339-357`) and gets the head back. The T2.1 basis names `revenue_business_mix.r01` and `credit_translation.r05`. `cp1_references` keeps the CP-1 facts' own ids and citations.
- **CP-MODEL** inputs contain no CP-1A or CP-2. No head binds CP-2 (`consumers_of_CP-2_in_S1a`).

## Test cost

- Each case needs a genuine CP-1 promotion over the three-source pack, which takes 11–26 minutes (QUEUE 2026-10-27).
- L2's CP-1 authentication probably runs again on every CP-1A tool call: two `_assert_current` calls per call (`host.py:283-293`), plus `bind_submission` and the verifier replay. I estimate about 40 re-authentications per run. I did not measure this; it is the main risk.
- **Proposal.** Use module-scoped fixtures, as L2 and the financial tests do (`test_financial_workflow.py:1077-1133`):
  - `s1_promoted[case]` runs CP-0 and CP-1 once.
  - `s1_closed[case]` clones it (store copytree plus a workflow-state clone that re-activates the CP-1A session on the clone) and finishes the run.
  - A1, A2 and A4 read `s1_closed`; A3 clones `s1_promoted` or the CP-2-ready state.
  - An optional `work/s1a-<case>/` archive may be reused, but only after its receipt verifies against the current pack hash.
- **First task:** time one CP-1A `from_execution` on the cached state, then decide Q5.

## Open questions for LEAD

1. **CP-1A rule mode.**
   - (a) Journaled `rules=`. This is what lease rev 3 says and is the product path (task 8.9). A missed read costs attempt 0.
   - (b) Refuse before the journal, as the financial precedent does.

   Recommend (a).
2. **CP-2 view.** TOOL-CONTRACT row `:197` admits "CP-1A catalogue only under a later exact view lease", and D2 says a whole-context projection does not count.
   - (a) Freeze `module_context("credit_synthesis")` as the exact view and amend the row. It is the live CONTEXT and holds the validator's inputs, with no quotes or citations.
   - (b) A narrower lease-specific projection.

   Recommend (a). The test asserts the body has no `quote`, `citations` or `record_json` keys.
3. **Walk after a CP-1 `RefusedBegin`.** CP-1A does not depend on CP-1.
   - (a) Begin later modules that are authorised.
   - (b) Keep G1's stop rule.

   Recommend (b) for S1a: the oracle pins no such case. Record it as a limitation.
4. **Host sequencing.**
   - (a) Wait for L2, then add one line.
   - (b) Do full H1 now.
   - (c) Bypass `SourceSession` with `PackTools`.

   Recommend (a). Reject (c), because it drops host provenance.
5. **Authentication cost.** If it is heavy:
   - (a) memoise the CP-1 authentication per immutable snapshot hash, through an L2/H1 amendment;
   - (b) accept the cost.

   Recommend: measure first, then (a) if one call takes more than 30 s.
6. **CP-1A `read_inputs`** for `business_context.context_block` (consumers and `cp1_facts`), which a real JSON-lines participant would need.
   - (a) Add it now, not counted as tool use.
   - (b) Defer it.

   Recommend (b). S1a's literal submission needs neither.
7. **Location of probes and views.**
   - (a) `owners/<cp>.py` (D12 pattern).
   - (b) Inside `owner_workflow.py`.

   Recommend (a).
8. **Oracle copy drift.** The LEAD worktree's untracked `cases/snapshot/manifest.json` (`68d591f6…`) differs from the frozen `9db0367f…` in its `status` line. Pin the checkpoint hashes in this lease and reconcile the untracked copy.

Not verified: I ran no product code apart from `registry.plan`, `dependencies`, `edge_rule`, `pack_tool_steps`, `tool_set`, `applicable_rules` and `bound_steps`. Five things were established by reading code only:
- that `_producer_inputs` refuses a promoted CP-1 today;
- that L2's CP-1 authentication accepts a CP-1A consumer and how much it costs;
- that `module_context` is deterministic and JSON-serialisable;
- that the CP-1A and CP-2 probes reproduce their heads at the final snapshot;
- that publishing CP-MODEL after CP-2 leaves its bytes unchanged.

The exact label and period spelling that separates the LTM-Q4 T4.10 fact from the FY2025 one is unchecked. The word count is approximate.

## LEAD rulings on the draft (2026-10-28) — not yet frozen; independent review pending

- Oracle pins (adopted, 49801d7): expected `d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa`,
  manifest `68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4` (status line
  now records adoption; this supersedes 9db0367f…), submissions
  `bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c`.
- Q1: (a) journaled `rules=` for CP-1A; a missed read costs attempt 0, re-begun as attempt 1.
- Q2: (a) `module_context("credit_synthesis")` is frozen as CP-2's exact view; LEAD amends
  TOOL-CONTRACT.md:197 when this lease freezes. The test asserts the body has no `quote`,
  `citations` or `record_json` keys.
- Q3: (b) keep G1's stop-after-refusal rule; recorded as an S1a limitation.
- Q4: (a) wait for L2's integration, then the one `_SOURCE_STEPS` line, serialised by PM.
  Bypassing `SourceSession` is rejected.
- Q5: measure one CP-1A `from_execution` on the cached state first; if over 30 s, an L2/H1
  amendment memoises CP-1 authentication per immutable snapshot hash.
- Q6: (b) defer CP-1A `read_inputs`.
- Q7: (a) probes and views in `src/deploy_workflow/owners/<cp>.py` (D12).
- Q8: resolved by the pins above.

## Rev 1 amendments (LEAD, 2026-10-28) — override the body

From the independent review (`docs/reviews/s1a-g2-lease-review.md`); every edit it proposed is
adopted.
- **Prerequisites:** add a third: the manifest adoption (49801d7) integrated into
  `codex/checkpoint`.
- **H1 (terminal publication):** add G1 extension item 9: publication is terminal only when
  CP-MODEL's required producer (CP-1) has no accepted or restricted head. A refusal or a
  blocked head at CP-1A or CP-2, with CP-1 settled, publishes and verifies
  (`owner_workflow.py:1163`, `:1225-1227` change accordingly). Add acceptance A3b: CP-1A
  attempts 0 and 1 both fail a rule, so the CP-1A head is blocked; CP-2 begins with input
  CP-1A `status=blocked`; CP-2's inherited limitations carry the `Upstream CP-1A blocked:`
  prefix (execution.py:361-362); the receipt verifies.
- **H2:** Files add `tests/test_owner_workflow.py`. A5 becomes: it passes with only the :174
  parameter changed to `("CP-1","CP-5","CP-MODEL")`, which `_check_specs` still refuses.
- **M2 (FIG binding):** select from `store.head_module(CP-1 head).facts` the unique fact whose
  table_id, metric row/field and basis match the oracle `cp1_coordinate` (T4.10, metric,
  twelve-month (LTM) basis ending Q4 2025); assert its `fact_id` appears as a `ref` in
  `cp1_facts` with that unit token and `shown`. **Task 1** probes a real CP-1 head and reports
  the exact predicate strings; LEAD freezes them into this lease before tests are written.
- **M3 (rule mode):** `StepSpec.rules: Literal["none","precheck","journaled"]`; CP-0 and CP-1
  `precheck`, CP-1A `journaled`, CP-2 `none`. Item 2 covers every `_fin`/`_filled`/
  `_projection` call site (`owner_workflow.py:432, 525, 548, 570, 573, 960, 985, 1011, 1012,
  1031`); item 3 also applies to the verifier's `_filled` replay (:1012).
- **M4 (CP-2 view):** **Task 1** also reports the exact key tree of
  `module_context("credit_synthesis")` for both cases. LEAD then amends TOOL-CONTRACT.md:197
  and :205-208 with that key tree and states the D2 exception (this whole-context projection
  is CP-2's exact view and counts as tool use). The test asserts the body's key tree equals the
  frozen tree and that no `quote` string from submissions.json occurs as a substring.
- **L1:** the A3 "no business page:3 read" case is positive-case only.
- **L2:** the API block is written with keyword arguments only.
- **L3:** host references are to L2's host.py (`_assert_current` :697-708, calls :748, :750,
  :766, :783; `_cp1_producer_inputs` :427-440); the S1a change is one entry in L2's
  multi-line `_SOURCE_STEPS` dict. L2 now memoises CP-1 authentication per snapshot (its
  fix round 1), which answers Q5.
- **Run driver (G2 review M2):** Files add `tests/s1a_runs.py`, exporting
  `s1a_closed(case, root) -> (store_dir, receipt_path, publication_dir)`; it owns pack assembly,
  the literal submissions, run-time substitutions and the tool-call sequence. G2 imports it.
- **Limitations recorded:** CP-2 has no consumer in S1a, so its downstream consumption stays
  open until S1b (CP-5, D3); a real JSON-lines CP-1A participant has no `read_inputs` for
  `cp1_facts`/consumers (Q6 deferred); model blocks (`model-chart-strip`, `capital-structure`,
  `financials-credit-metrics`) render but are outside the S1 oracle. LEAD updates
  `docs/MODULES.csv` when S1a and G2 verify.

## Rev 2 amendments (LEAD, 2026-10-28) — task 1 answers, override the body and rev 1

From S1a task 1 (`work/lead/s1a-task1/report.md` in the LEAD worktree), run on a real promoted
CP-1 head over the S1 positive pack.
- **M2 frozen predicate.** For each FIG name in `submissions.json` `figures` (the names are the
  T4.10 metric names: `total_leverage_reported`, `net_leverage_reported`,
  `interest_coverage_reported`, `fcf_to_debt`), select from
  `store.head_module(<CP-1 head>).facts` the facts with `table_id == "T4.10"`,
  `period == "LTM Q4 25: 2025-01-01 to 2025-12-31"` and
  `label == "LTM Q4 25 (2025-01-01 to 2025-12-31) · <metric>"` (U+00B7 with one space each
  side). Exactly one must match; zero or several fail the test. The FY25 fact with the same
  dates has period `FY25: …` and is never selected. Then assert the selected `fact_id` is a
  `ref` in the CP-2 read body's `cp1_facts` whose `unit` equals the figure's `unit_token` and
  whose `shown` equals its `spelled`. This replaces body line 99 (`cp1_facts` carries no
  `table_id`, so the body alone cannot select).
- **M4 frozen view tree.** `cases/snapshot/cp2-view-tree.json` (added beside the pinned oracle;
  the three pinned hashes are unchanged) freezes, per case, the top-level keys in order, every
  element shape, and the ordered CP-1A registers with their `cells` fields and row counts
  (positive 70 rows over 21 registers, no signals; gap 62 rows over 20 registers, no
  `events_timeline`, three five-key signals). The test asserts the observed body's shape equals
  the frozen one for its case, that no key is `quote`, `citations` or `record_json`, and that no
  `quote` string from `submissions.json` occurs in the body. The tree is a shape observed on
  product-settled heads, not a value oracle. Caveat: the gap tree was observed with the gap
  CP-1A over the positive CP-1 head (no gap CP-1 promotion under build-first); its register
  keys were cross-checked on a real gap-pack CP-1A, and code argues CP-1 cannot change keys.
- **TOOL-CONTRACT.md :197 and :205-208** are amended in the same commit: CP-2 credit_synthesis
  is granted exactly `module_context("credit_synthesis")` with the frozen tree, as a D2
  exception that counts as tool use.
- **Deferred (build-first):** the gap CP-1 promotion and every S1a test run move to LEAD's final
  verification phase.

## Rev 3 amendments (LEAD, 2026-10-28, on S1a build review-precise-1)
- **R3-1 (H1 refusal branch).** The refusal half of rev 1 H1 stands. `_verify_walk` compares
  `refusal.snapshot_sha256` with `receipt.publications[0].snapshot_before_sha256` when the receipt
  holds a publication, otherwise with the final snapshot; `_verify_publications`' chain check
  stays. Acceptance A3c: a CP-0 review whose T8 does not command CP-1A (CP-1A CONDITIONAL, a valid
  CP-0 submission; test input, not oracle) refuses CP-1A at begin; CP-2 is not begun (the walk ends
  at the first refusal; LEAD, on S1a review-precise-2); CP-MODEL publishes; the receipt seals and verifies. Deferred (one CP-1
  promotion).
- **R3-2 (journaled replay is exact).** `_verify_submissions` reruns the module's ruled validator
  on the historical snapshot with the attempt holding the step and requires
  `step.issues == bounded_issues(tuple(dict.fromkeys((*validator_issues, *journaled))))`; the
  subset rule of item 7 is replaced. A forged invalid step with invented issues refuses.
- **R3-3 (notation).** Front Page (`cp2.*`) facts carry the line's own fact label as `column`;
  other tables the column label. `<label and period of FIG:x>` binds as `"<label> · <period>"`
  (`cp2_synthesis.py:853`), a declared run-time binding. The business Source carries
  `media_type="text/plain"`, `extractor` and `extraction_status` from the manifest `common`;
  `representation_scope` is not a Source field; the pack hash is a run-time binding.
- **R3-4 (A3b input).** The blocked-CP-1A CP-2 submission is a reviewed literal fixture
  `cases/snapshot/cp2-blocked-cp1a-submission.json` with its sha256 pinned here at freeze; the test
  loads it and checks the hash, never derives it.
- **R3-5 (A4).** The CP-2 read-body tamper forges a consistent read (receipt copy with edited
  `read.body` and `inputs_sha256`, audit file under its new hash, `receipt.sha256` rewritten) and
  must refuse `identity_mismatch` at the view replay. The step-output tamper is caught by the
  store's own blob hash check, recorded as a limitation.
- **R3-4 pin (LEAD, 2026-10-28, from S1a fix-1).** `cases/snapshot/cp2-blocked-cp1a-submission.json`
  sha256 `0616a4a278104665122a474b434d3122637934845c0593290ddc68317cdb06e3` (file bytes).
