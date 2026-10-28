<!-- Independent mx-precise review of the S1a and G2 lease drafts, saved by LEAD 2026-10-28. -->
## Review of the S1a owner-run lease and the G2 owner-rendering lease

**Verdicts**
- **S1a (`docs/S1A-OWNER-RUN-LEASE.md`): FREEZE WITH EDITS.** Two High findings must be fixed before freeze. One path the lease asserts cannot produce a verifiable receipt under G1, and its regression test A5 cannot pass "unchanged".
- **G2 (`docs/OWNER-RENDERING-LEASE.md`): FREEZE WITH EDITS.** Its outcome and banner rules need aligning with what S1a can actually produce, and the S1a run driver it depends on has no owner.

Diff ceiling: neither lease sets one. The 800-line cap is waived for lane integrations (6c3cd4b, AGENTS.md), so this is not a finding. The negative constraints hold: S1a makes no `src/deploy_vii` edits, and G2 creates new files only and imports the rest.

### Spec findings, S1a (ranked)

**H1. A blocked or refused CP-1A or CP-2 makes the receipt unverifiable.**
- The lease (S1A:83-84) says that if CP-1A attempt 1 is also invalid, "CP-1A settles blocked. CP-2 still begins." That part is true: the CP-2←CP-1A edge is `restricted` (I probed `edge_rule`), and `current_inputs` binds CP-1A as `blocked`.
- But G1 sets `terminal = refusals or any blocked head` (owner_workflow.py:1163; `_refused` :401). CP-MODEL needs only CP-1, so `publish()` still publishes (:685-698). `_verify_publication_outcome` then raises `identity_mismatch` whenever `receipt.model` is set and the run is terminal (:1225-1227). So `write_receipt` refuses.
- The same happens for a CP-1A or CP-2 `RefusedBegin` (CP-0 not authorising), because CP-MODEL still publishes.
- No S1a test exercises either path.
- **Edit:** add item 9 to "G1 extension":
  > "Terminal publication = CP-MODEL's required producer (CP-1) has no accepted/restricted head; a refusal or blocked head at CP-1A/CP-2 with CP-1 settled publishes and verifies (`owner_workflow.py:1163`, `:1225`)."
- Add A3:
  > "CP-1A attempts 0 and 1 both fail a rule → CP-1A head blocked; CP-2 begins with input CP-1A `status=blocked`; CP-2's inherited limitations carry the `Upstream CP-1A blocked:` prefix (execution.py:361-362); the receipt verifies."
- Alternatively, delete S1A:84's "CP-2 still begins" sentence and record "blocked CP-1A unsupported" as a limitation.

**H2. A5 "test_owner_workflow.py passes unchanged" is impossible.**
- `tests/test_owner_workflow.py:174` uses `("CP-1","CP-2","CP-MODEL")` as the *unsupported* selection. After S1a, `create` accepts it (the plan is CP-0, CP-1, CP-1A, CP-2, CP-MODEL).
- **Edit:** add `tests/test_owner_workflow.py` to Files. Change A5 to:
  > "passes with only the :174 parameter changed to `("CP-1","CP-5","CP-MODEL")`, which `_check_specs` still refuses (CP-5 has no spec and follows CP-MODEL)."

**M1. The base does not contain the pinned oracle.**
- `codex/checkpoint` (a9b829f) carries the oracle as 6e9305c, and its `manifest.json` is `9db0367f…` with status "DRAFT … not adopted".
- 49801d7 (manifest `68d591f6…`, adopted) is not an ancestor of `codex/checkpoint` (`git merge-base --is-ancestor` exit 1).
- S1A:7 still cites `9db0367f` "on codex/checkpoint", while the ruling at :227-230 pins `68d591f6`.
- **Edit:** S1A:7 should cite `68d591f6…f3f4`. Add a third prerequisite at S1A:11-13: "the manifest adoption (49801d7) integrated into codex/checkpoint". G2's ruling line 162 needs the same qualification.

**M2. The `{{FIG}}` binding test cannot tell the LTM fact from the FY2025 fact.**
- S1A:99-101 picks the fact from the CP-2 read body's `cp1_facts` and checks only `unit` and `shown`.
- `cp1_facts` exposes only `ref/label/period/unit/shown` (cp2_synthesis.py:974-983), with no `table_id` or `basis`. Both candidate facts share the period 2025-01-01 to 2025-12-31.
- expected.json `CP-1.basis` says "the spelled values are equal either way". cases/financial/manifest.json `metric_coordinate_rule` says "Do not use equal result values to conflate basis/operands."
- The labels and ids are then bound at run time (Q6, N2), so a wrong choice passes every check.
- **Edit:** replace S1A:99-101 with:
  > "select from `store.head_module(CP-1 head).facts` the unique fact whose table_id, metric row/field and basis match the oracle `cp1_coordinate` (T4.10, metric, 'twelve-month (LTM) basis ending Q4 2025'); assert its `fact_id` appears as a `ref` in `cp1_facts` with that `unit_token` and `shown`; the first task probes the CP-1 head and freezes the exact predicate strings into this lease before tests are written."

**M3. Rule mode and `_fin` call sites are under-specified.**
- `StepSpec.rules: bool` means a financial pre-check for CP-0 and CP-1: `_evidence_issues` at owner_workflow.py:573 and :1031, with the `refused` disposition at :1035-1043. For CP-1A it is meant to be journaled.
- Item 7 refers to "journaled-rule steps", but no field distinguishes them.
- `_fin` raises for any binding whose `module_id` is not CP-0 or CP-1 (financial_workflow.py:97 Literal). The lease names only :432, :960 and :1011, but `_fin`/`_filled`/`_projection` are also reached at :525, :548, :570, :573, :985, :1012 and :1031.
- **Edit:** set `StepSpec.rules: Literal["none","precheck","journaled"]`, with CP-0/CP-1 `precheck` and CP-1A `journaled`. Item 2 lists every call site above, and item 3 applies to the verifier's `_filled` replay (:1012) as well.

**M4. The Q2 ruling amends too little.**
- TOOL-CONTRACT.md:205-208 fixes the V1 projected key set (`fact_id, label, …`) and says `record_json/citations/quote` are not exposed.
- `module_context("credit_synthesis")` adds the keys `upstream, cp1_facts{ref,shown,…}, cp1a_rows{register,row,cells}, cp1a_signals{restate,limits}, inherited_limitations` and the `*_note` strings (cp2_synthesis.py:959-1019).
- OWNER-WORKFLOW-LEASE.md:26-30 (D2) also says a whole-context projection does not count.
- **Edit to the ruling at S1A:232-234:** amend TOOL-CONTRACT.md:197 *and* :205-208 with the exact key tree of that body, and state the D2 exception explicitly.
- Strengthen the test: the body's key tree equals the frozen key tree, *and* no `quote` string from submissions.json occurs as a substring of the body. Today it checks only that three key names are absent. `cp1a_rows.cells` carry CP-1A cell text, and I did not check whether that text can contain quotes.

**L1.** The A3 test "without a business page:3 read" works only on the positive case. My probe shows gap `business_context` cites only business page:1 and page:2. **Edit:** "positive case only".

**L2.** The API block at S1A:34-38 is not valid Python: positional arguments follow keyword arguments. Write all fields by keyword.

**L3.** Line references:
- `_assert_current` at host.py:283-293 is the checkpoint file. In L2's host.py it is :697-708, with calls at :748/:750/:766/:783.
- `_cp1_producer_inputs` is at :427-440.
- L2 already rewrites `_SOURCE_STEPS` as a multi-line dict that adds CP-4 (L2 host.py:43-47). The S1a change is one entry in that dict, after L2 integrates.

### Spec findings, G2 (ranked)

**M1. The outcome and banner rules do not match the receipts S1a can produce.**
- `refused` requires "exactly one RefusedBegin, no model" (G2:60).
- That fits only a refusal at CP-1. A refusal at CP-1A or CP-2 leaves CP-MODEL publishable (see S1a H1), so G2 refuses it as "anything else".
- The oracle pins no S1a refused case, so the ruling's s1a "refused" banner (G2:180-181) can never be exercised by a test.
- **Edit:**
  > "`s1a-credit-snapshot` supports `complete` only; any S1a receipt with a refusal or blocked head is refused until a slice oracle covers it."
- Drop the s1a refused banner, or keep it and add an oracle case.

**M2. The S1a run driver has no owner.**
- G2's tests need genuine S1a runs: pack assembly from two manifests, the literal submissions, `<<PACK>>`/`{{FIG}}` substitution, and the tool-call sequence.
- Today these would exist only inside S1a's `tests/test_owner_s1a.py`.
- **Edit to the S1a Files list:** add `tests/s1a_runs.py`, exporting `s1a_closed(case, root) -> (store_dir, receipt_path, publication_dir)`.
- G2:104 then says "imports `tests/s1a_runs.py` and G1's `promoted_case`, never re-implements them".

**M3. Head qualification is not in the receipt.**
- G1's `SettledHead` has no qualification field (owner_workflow.py:230-234). G2:55 requires "ordered heads (with their qualification) equal the receipt".
- **Edit:** "store heads equal the receipt on (module_id, result_sha256, status), and `OwnerHeadResult.qualification` is the store `Head.qualification`, which the G1 verifier already checks via `head_of` (owner_workflow.py:1108)."

**L1. Code references and the payload claim.**
- The citations should be `render` at render.py:127 and `build` at :129-131, not :141-142.
- `_report_payload` also rewrites `figures` (render.py:112-118). Change G2:75 to "assigned blocks have no chart and `figures == ()`", and assert it.

**L2. Scope match.** Specify that the scope matches on the exact `requested_modules` tuple as stored in the Run. The financial run and the S1 runs are both `credit_snapshot`/`synthetic` and differ only in that tuple.

**L3. Model blocks without proof.** `model-chart-strip`, `capital-structure` and `financials-credit-metrics` render populated on the S1a page (report_view.py:1071-1083). They are in no scope section, and the oracle's FP01 has no entry for them. Record this as an S1a scope limitation.

**L4. Prerequisite 4 owner.** The ruling (G2:163-164) assigns "analytical after deterministic" to "the S1a/S1b G1-extension lease", but S1a does not take it. Name S1b.

### Agreement between the leases (check 3)
- The receipt shape is unchanged.
- G2 relies on the G1 verifier, which S1a extends with probes for CP-1A and CP-2. The public verifier uses the default `OWNER_SPECS`, so the two are consistent.
- On blocked heads, S1a produces them and G2 refuses them (Q6), which is consistent once G2 M1 is applied.
- Exactly one gap is owned by neither lease: the S1a run driver (G2 M2).
- The TOOL-CONTRACT amendment is owned by LEAD.

### File ownership (check 4)
- **G1 lane:** S1a edits `owner_workflow.py` only after G1 integrates, and must also own `tests/test_owner_workflow.py` (H2).
- **L2:** S1a's `host.py` change is serialised after L2. L2's own lease covers only `host.py` and `tests/test_source_tools.py`, so there is no clash.
- **D1:** G2 does not import D1.
- **A4:** A4 is integrated on checkpoint as `tools/upstream.py`, and neither lease touches it.
- **New files:** `owners/` is new and does not exist on checkpoint.

### Completion-rule gaps (check 5)
- **CP-2 consumption.** Per the oracle, no module consumes CP-2 in S1a (`consumers_of_CP-2_in_S1a`). Both leases should state that CP-2's downstream consumption stays open until S1b's CP-5 and D3, so the module matrix does not mark it complete.
- **CP-1A for a real participant.** A real JSON-lines CP-1A participant gets no `read_inputs` for `cp1_facts` or the consumers it must declare (Q6 deferred). S1a should record this as a limitation.
- **Rails.** The rail tables appear only on module pages (Q4); this is recorded.
- **Module matrix.** Neither lease names who updates MODULES.csv.

### LEAD rulings (check 6)
- S1a Q1, Q3, Q4, Q6 and Q7 are consistent with the code: submission.py:966-968, RULED_ENTRIES and `_with_rules` (rejected attempt, then re-begin), and the walk rule.
- The pins ruling is inconsistent with the base (M1).
- The Q2 ruling is incomplete (M4).
- Q5 makes a conditional mid-lease amendment to L2/H1 files. That is acceptable only if PM sequences it.
- G2 Q1, Q3, Q4 and Q5 are consistent: app.js:601-603 and :636-649/:803, and financial_rendering.py:213 is a relabelling catch-all.
- The G2 "prerequisite 3 met" ruling holds only on the LEAD branch.
- The Q6 s1a-refused banner is not reachable as specified (G2 M1).

### Claims confirmed by reading or probing
These were checked by reading the code, plus probes for `plan`, `edge_rule` and `ToolRules`:
- The plan order is CP-0, CP-1, CP-1A, CP-2, CP-MODEL; adding CP-5 appends it after CP-MODEL. The manifest's `consumers_note`, which says otherwise, is wrong.
- CP-1A is bound as a context input (execution.py:226, :252-258).
- Today's host has `producer.inputs == expected` (host.py:36-37) and no CP-1A entry in `_SOURCE_STEPS` (:18).
- CP-1 carries the four extra input tails.
- `KeyError` in `BOUND_STEPS` / `PREFILLED`.
- submission.py:967.
- `module_context` (context.py:111) and `step_sources`/`readable_sources`.
- The `cp2_upstream` reads (:339-357) and the signatures of `cp2_module` and `cp1a_module`.
- `PROMOTED` exists in both cores.
- The rules over the literal submissions: no-evidence runs give 10 issues (positive) and 9 (gap); CP-1A's rules are absence plus unread-citations.
- The G2 checks at :75, :79-82, :1172, :310-325 and :785.
- The `store.view` call at execution.py:884.
- `SHIPPED_MAPS` at shipped.py:15 and `envelope_view` re-drawing the head.

Not verified: no pytest or product run of CP-1A/CP-2 was executed. The H1 blocked/refused-path failure is established by reading code only. Also unchecked: whether L2's `_verify_cp1_attempt` accepts a CP-1A consumer, and what it costs; that `module_context` is deterministic; whether CP-1A `cells` text can contain source quotes; whether the S1a probes reproduce at the final snapshot; that renders are byte-deterministic; the exact LTM and FY T4.10 fact labels; and whether G1's fix-round code changes before integration.
