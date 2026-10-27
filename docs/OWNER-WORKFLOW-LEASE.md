# Generic owner workflow (G1) lease

LEAD contract, 2026-10-27, Claude handover. Pre-code; implementation starts only
after independent review and PM integration of this file. Revision 2 applies every
finding of the independent `mx-precise` review (H1–H4, M1–M8, L1–L4); revision 3
applies its scoped re-review (R1–R4).

## Why

Each owner so far got a bespoke adapter (CP-1 1,450 lines; CP-1B WIP 3,939; A4 WIP
1,737). The analytical code in them is small; the rest is transport, receipt,
verifier and recovery written again per owner. The architecture study
(`docs/reviews/owner-harness-architecture.md`) found that every one-step shared-live
owner (CP-1A, CP-2, CP-3, CP-4, CP-5, CP-6) shares one shape: a schema,
`xx_upstream`, a validator, a Python composer and `submit_xx_step`
(`src/deploy_vii/cp2_synthesis.py:923-956`), dispatched by `submit_model_payload`
(`src/deploy_vii/live/submission.py:941-986`). CP-0 settles through
`submit_cp0_review`, CP-1 is a five-step promotion, and CP-MODEL is a deterministic
publisher. One plan-driven adapter can drive all of them, so each further owner
becomes a declared spec, its core (if new), bindings and cases.

In-flight B1, A4, L2 and D1 close as leased; they are not rewritten or imported here.

## LEAD decisions (architecture questions D1–D12)

- **D2 tool use.** A `read_inputs` record counts toward tool use for an upstream-only
  step only if its body is exactly the adopted view that `docs/TOOL-CONTRACT.md`
  grants that consumer, or a narrower one, frozen in the slice lease. A whole-context
  projection does not count. In G1 it applies only to CP-1 narrative, readiness and
  quality (the existing precedent).
- **D3 consumption.** A module is consumed only when a consumer core actually reads its
  settled output in an actual run. CP-5's review counts as consumption of module X only
  after a lease extends the CP-5 integrity scope to X, and only if the CP-5 attempt's
  inputs bind X's settled head hash and its review cites X's facts. Being bound as an
  optional input that the consumer never reads does not count.
- **D6 CP-OS.** Render-time navigation proof over a real selected run, with the rendered
  navigation page hash bound to that run's verified receipt hash. No journal head.
- **D7 blocks.** Existing qualified block owners stay (ebitda-adjustments stays
  CP-1/MODEL, `bindings/cp1.py:60`). New owners get new blocks in their slice lease.
- **D8 table ids.** New owners' tables get ids that collide with no existing id, by a
  per-lease `table_ids` registration in `src/deploy_vii/methodology.json` (D12). The
  existing CP-1/CP-4 overlap stays as it is.
- **D10 transport/recovery.** No durable resume: an interrupted generic run is refused
  and a new run starts (the financial-slice rule). Limits reuse `MAX_CALLS`,
  `MAX_MESSAGES` and `MAX_LINE` (`financial_workflow.py:77-79`); CP-1B keeps its
  8,192-byte cap. Paging is not required elsewhere.
- **D12 location.** New owner cores live in `src/deploy_workflow/owners/<cp>.py`.
  One-line registrations in `src/deploy_vii` (`registry.py` STEP_CHAINS,
  `bindings/shipped.py`, `report_view.py` compositions, `methodology.json` table ids)
  are admitted per owner lease, recorded in `docs/reuse/manifest.json`, and serialised by PM.
- **D1 CP-3B/CP-6A.** SPEC.md already decides they are distinct owners; their slice
  lease adds the rows. D4 (CP-1 edges for CP-2E/CP-L10), D5 (CP-8 prior-report input),
  D9 (per-owner source grants) and D11 (uncited analyst assumptions) are decided in
  the slice lease that first needs them, with independent review.

## G1 files and base

New files only: `src/deploy_workflow/owner_workflow.py`, `tests/test_owner_workflow.py`.
No existing file changes. Import, never edit, `financial_workflow.py`, `host.py`,
`tools/`, `workflow.py`, `tests/test_financial_workflow.py` and `src/deploy_vii`.
Base: `codex/checkpoint` at the commit that integrates this lease.

## Public API

```
StepSpec(step_id, schema, sources, extract, upstream_grant, inputs, rules)
OwnerSpec(module_id, steps: tuple[StepSpec, ...], entry,
          kind: Literal["analytical", "deterministic"], publish)
OWNER_SPECS: Mapping[str, OwnerSpec]   # G1 ships CP-0, CP-1, CP-MODEL only
OwnerWorkflow.create(directory, pack, *, specs=OWNER_SPECS, publication_directory=None)
  .invoke(tool, arguments) / .read_inputs() / .submit_review(payload)
  .publish() / .write_receipt(destination) -> OwnerRunReceipt
verify_owner_run_receipt(store, receipt, *, publication_directory=None) -> None
serve_json_lines(workflow, reader, writer, *, destination, participant); main()
```

JSON-lines operations: `invoke`, `read_inputs`, `submit_review`, `publish`,
`write_receipt` (`publish` replaces the financial slice's `publish_model`).

Return shapes match the financial slice: `invoke` returns the `tool-receipt/1` call
dump; `read_inputs` returns the read-record dump with `body`; `submit_review` returns a
dict with the keys of `financial_workflow.py:725-735` (`status`, `issues`, `step_id`,
`refusal`, `snapshot_sha256`, `next_step`, `stored_payload_sha256`, `prefilled`);
`publish` returns the keys of `:817-823`.

`write_receipt` requires every planned analytical module to be settled (head) or
refused (`RefusedBegin`, or attempt 1 blocked), and, if CP-MODEL is planned, exactly
one terminal `publish` (published, or refused by `CpModelRefused`); otherwise it
refuses `not_permitted`.

### Create

`create` refuses `not_permitted`, writing nothing, if `registry.plan` raises (an
unknown id makes `canonical()` raise, `registry.py:45-49`), if any planned module
(canonical id) lacks an `OWNER_SPECS` entry, or if an `analytical` spec's module lacks
a `step_chain`. `deterministic` specs (CP-MODEL) need no chain. If CP-MODEL is planned
and `publication_directory` is None, already exists, equals the run directory or lies
inside it, `create` refuses (the checks of `financial_workflow.py:514-519`).

### Walk

- Analytical modules are taken in plan order via `Execution.begin`/`submit_step`/
  `finish`. A rejected attempt 0 is re-begun; attempt 1 settles blocked
  (`financial_workflow.py:716-724`).
- A `NotAuthorized` or blocked-edge begin is retained as a `RefusedBegin` (snapshot,
  `str(error)`). In G1 no later analytical module is independent of CP-1, so the walk
  begins nothing more after it; `publish()` still calls `publish_cp_model` once, which
  raises `CpModelRefused` before any begin or write, and that call is retained as one
  refused publication (as in `test_missing_source_requires_actual_begin_and_publisher_refusal`
  and `_verify` at `financial_workflow.py:1084-1126`). Continuing past a refusal with a
  truly independent module is deferred to the first slice lease shipping such a spec.
- For `deterministic` specs the walk never calls `begin`; the publisher owns begin and
  finish (`cp_model_workflow.py:294`; `execution.py:616-617` refuses a second pending attempt).

### Operations

- `invoke` uses `SourceSession` for pack-source steps (CP-0/CP-1 in G1, `host.py:18`)
  and `UpstreamTools` where a grant is declared; any other call is retained as a
  refused `not_permitted` receipt (`financial_workflow.py:560-572`).
- `read_inputs` (no arguments) returns, for CP-1 narrative/readiness/quality only, the
  `_projection` body (`financial_workflow.py:291-298`); elsewhere it refuses.
- `submit_review` reuses the CP-0/CP-1 path of `financial_workflow.py:599-736`. For other
  existing owners (none in G1) it calls `submit_model_payload` with `rules=` only for
  `registry.pack_tool_steps()` and `rules=None` otherwise (`submission.py:967-968`).
  Offline-only steps (CP-1B; `submission.py:218-221`) are not supported in G1.
- `publish` reuses `publish_cp_model`/`verify_cp_model_publication` and the quarantine
  behaviour of `financial_workflow.py:737-823`.

### Reused private helpers

Import `_binding`, `_historical`, `_projection`, `_filled`, `_evidence_issues`,
`_snapshot`, `_FrozenExecution`, `_verify_cp0`, `_verify_promotion` and
`_verify_model_settlement` from `financial_workflow.py`. `OwnerBinding` has the 11
`FinancialBinding` fields with `Identifier` module/step ids; for CP-0/CP-1 it is
converted with `FinancialBinding.model_validate(owner_binding.model_dump())` before each
helper call. Audit files go under `owner-run-audit/`. The inline checks of
`financial_workflow.py:904-1003` (ancestor chain, audit inventory equality, call
replay with call-id substitution at `:980`, read replay) and `:1077-1163`,
`_publication_history` (`:1198-1256`), and the audit helpers `_audit`/`_retain`/`_raw`
(`:213-225`, bound to `financial-slice-audit`) cannot be reused as they are. They are
re-implemented in `owner_workflow.py` with the same rules over `owner-run-audit/`.

### Receipt and verification

`OwnerRunReceipt` (`owner-run-receipt/1`) records bindings, calls, reads,
submissions, begins, refusals, publications and settled heads.

`verify_owner_run_receipt` is read-only and structural, as `_verify` is: it loads each
recorded before/after snapshot from `snapshots/`, checks step and head hashes, replays
calls and reads, runs the existing settle probes (`_verify_cp0`, `_verify_promotion`,
`_verify_model_settlement`), checks begins structurally (as `_publication_history`,
`financial_workflow.py:1198-1256`) and publication refusal reasons by prefix
(`:1220-1224`). It does not replay submissions. Known run-specific values (ticket ids,
call ids, `UpstreamTools` nonce, quarantine suffix, output paths in refusal reasons)
are compared structurally, never byte-for-byte across runs.

## Acceptance (independent expectations; none derived from the new code)

1. **Equivalence, positive.** In one test, run `completed_financial_case(tmp/financial)`
   from `tests/test_financial_workflow.py` afresh (never `genuine_closed_case`). Then run
   `promoted_case(tmp/owner)` with `start` monkeypatched (pytest `monkeypatch.setattr` on
   the same module object whose `promoted_case` is called) to
   `lambda root, gap=False: (OwnerWorkflow.create(root/'store', p := make_pack(), publication_directory=root/'model'), p)`,
   and call `.publish()`. Assert:
   - `model.html` and `calculation.json` are byte-equal across the two runs, and
     `receipt.json` is equal after removing only `ticket_id`;
   - the CP-0, CP-1 and CP-MODEL head `result_sha256` values are equal across the stores;
   - CP-0 is restricted; CP-1's stages equal `CP1_PROMOTION`; the CP-1 head is
     restricted; `downstream.model.status == "ready"` with 4 selected quarters;
     `publication_files` match;
   - `handoff.quality.confidence` has `confidence_score == 59` (equal to the independent
     formula in `quality_ready_case`), `qa_status == "Restricted"`, `confidence_band ==
     "Low"` (source of these values: `docs/MODULES.csv` CP-1 row);
   - `verify_cp_model_publication` returns no issues.
2. **Equivalence, gap.** For the missing-financial case assert: CP-0 is valid and
   restricted; exactly one `RefusedBegin` whose reason equals `str(NotAuthorized)`;
   CP-0 is the only attempt; exactly one publication with status refused, `ticket_id`
   None and no files; the publication directory does not exist; the receipt verifies
   with `publication_directory=None`.
3. **Refusals.** Unsupported selection, unknown id and a bad publication directory write
   nothing. A snapshot change between read and submit refuses. A tampered audit file,
   receipt field or foreign store makes verification refuse.
4. **Read-only verifier.** The set of relative paths and the bytes of every file under
   the run directory and the publication directory are identical before and after
   verification.
5. **Gates.** `ruff check`, `ruff format --check` and `mypy` (strict, `MYPYPATH=src`)
   pass on both new files; focused tests run under the heavy-job lock.

No stub or fake value stands in for real behaviour; no catch-all hides a failure.

## Next leases this unblocks (not admitted here)

- **H1 (`host.py`, after L2 integrates):** replace the per-producer provenance branch
  (`host.py:33-37`) with one rule for every producer with a `*-submission` tail.
- **G2 (`owner_rendering.py`):** generalise `financial_rendering.py` to any verified
  owner receipt.
- **S1 credit snapshot:** CP-0 → CP-1 → CP-MODEL → CP-1A → CP-2 rendered FP01, then
  CP-5 once A4 integrates and a lease extends its integrity scope (D3).

Not verified: twin-run byte equality of `model.html`/`calculation.json` and whether
`render()` embeds a path were established by reading code only
(`cp1_render.py:91-104`, `cp_model_workflow.py:139-238`, `execution.py:59-130`); the
G1 equivalence test is the first execution of that claim.
