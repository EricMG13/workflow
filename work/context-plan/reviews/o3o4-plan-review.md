# O3+O4 plan review (mx-autonomous, read-only), 2026-10-31: verdict fix (3 High, 7 Medium)

Target: `docs/superpowers/plans/2026-10-31-part-b-o3-o4.md` draft (252 lines), code at 5a00d7be.

- **F1 High** (:206, :44-51). Renderer missing: `owner_rendering.py:659-668` refuses a receipt with more
  than one refusal (`owner_render_outcome`), a refusal whose reason equals `BLOCKED_EDGE` (same string as
  the downstream "unrun" error, owner_workflow.py:149 → `owner_render_blocked`), and a refusal together
  with a publication. Task 7 O3(a) "render and verify pass, settled" cannot hold.
- **F2 High** (Q1 :236, Step 0 :71, test :72). No preset has an analytical module before CP-5 outside
  CP-5's fan-in (only CP-MODEL, deterministic, registry.py:24-25, 74); the fake `_world`
  (tests/test_owner_order.py:93-97) patches only `owner.plan`/`owner.dependencies` while `Execution.begin`
  and `current_inputs` use their own imports (execution.py:46-52, 230-246), so CP-5 would still be refused.
- **F3 High** (:66). `_next_analytical` does not exist; skipping to the next analytical module bypasses
  O1's CP-MODEL stop in `_advance` (owner_workflow.py:1137-1148). Fix: after a refusal call
  `_advance(module_id)`.
- **F4 Medium** (:116, Q2 :237). Torn window spans `_gate` and the journal validator
  (owner_workflow.py:1249-1283); `submit_step` writes the pending step before validating
  (execution.py:~846); resubmitting the same payload resumes validation (execution.py:826-835); the
  journal-ahead case (journal written, begins/submissions/publications not retained, ow:1112-1122, 1317,
  1437) lets `open()` re-activate a step or publish twice. Fix: `open()` walks the snapshot chain and
  requires a retained record per transition; a pending step with retained payload and binding resumes by
  resubmitting; `BeginRecord`/`RefusedBegin` rebuilt from the journal; any other gap `TornAudit`; three
  kill points (during validation, between `store.begin` and the begins retain, between `publish` and the
  publications retain).
- **F5 Medium** (:206 O3(b)). No orchestrator-level resume (call_index per digest, Budget rebuild, a held
  unknown reservation). Fix: add a `run_pathway` resume to Task 3, or narrow O3(b).
- **F6 Medium** (:159, :166, :217). Stop mapping unowned; O2 maps `WorkflowError` to `workflow: <code>`
  (o2 :210-215); O5's call-cap stop is `CallLimit` (o5 :173). Fix: Tasks 3-5 include `run_pathway.py` /
  `model/loop.py` with the exact mapping; use `CallLimit`.
- **F7 Medium** (:65, :72). `Identifier` (contracts.py:14) rejects `"CP-0:Run B"` (space). Fix: a form
  without spaces or a bounded `str`.
- **F8 Medium** (:188, :195). Without the relabelling, a lone-surrogate payload (`UnicodeEncodeError` at
  `payload.encode()`, ow:~1212) and deeply nested JSON (`RecursionError`, known H05) kill the transport as
  `InternalError`. Fix: check both before dispatch; add to the shape table.
- **F9 Medium** (:184). `SourceSession.invoke` keeps `except Exception → internal_error` (host.py:1092-1093)
  on the orchestrator's invoke path. Fix: journal an `InternalError` fault before returning the unchanged
  receipt, or a ruling that it stays.
- **F10 Medium** (Q5 :240, :161-166). Q5's premise is stale: U4 means "serve `quality_scope`", approved
  (work/codex-review/CONSOLIDATED.md:19, 31; docs/rulings/2026-10-29-stage3.md:703-731 items 85/87) and
  built in afce0b43 (financial_workflow.py:304-310); owner `_inputs` reaches it via `_projection`; tests pin
  the body under 524,288 bytes (tests/test_financial_workflow.py:1276, tests/test_earnings_workflow.py:1042);
  measured kept CZR read: 9,965 bytes of scope vs 16,886,498 full (probe
  work/build/keep/s8-t4-plan/probe_scope_size.py). Fix: rewrite Task 5's "Today" and Q5; test that the real
  CP-1 quality read is under the cap; Step 0 measures `_VIEWS` and narrative/readiness bodies.
- Lows: L1 header says HEAD pre-O1 with 2502 lines; HEAD is 5a00d7be (2546); cites match 5a00d7be^; :68
  stale (`_finish_walk` also checks `_publisher_done`, ow:1150-1153). L2 keep the first `_refusal_kind`
  (ow:1134 overwrites). L3 `open()` must bypass `__init__` (which begins CP-0, ow:1047) and rebuild
  `_publisher_done`, `_refusal_kind`, `_participant`/`_transport`, `_epoch_calls`. L4 compare up to id
  renaming (ticket ids are uuid4, execution.py:676). L5 Q4 spike also tests retained payloads validate
  under a new `run_id`. L6 tie the refusal snapshot to the next begin's `snapshot_before`, the
  publication's `before`, or the final snapshot.
- Answers: Q1 no such module (probe); honest Done-when on distressed_restructuring: CP-0 omits
  `Run CP-4`, CP-4 refused, CP-2G and CP-2H settle, CP-4C refused (missing CP-4), CP-5 refused (missing
  CP-4, CP-4C), receipt verifies; CP-5 settles only when the refused module comes after it (CP-6, CP-8);
  settling CP-5 over a missing producer needs execution.py:244-246 (restricted edge binds only a blocked
  head), outside B1, the user's call. Q2 G3 correct once F3 fixed; G5 no double-settle but journal-ahead
  gaps (F4); G4 correct. Q3 cap = `MAX_LINE`, faults no CP-1 read. Q4 no execution.py change needed.
  Q5 the stand-in is the fake world (F2); F9. Q6 cites correct at 5a00d7be^ (`NotAuthorized` at
  execution.py:268). Q7 accept once F8 fixed.

## Controller rulings (2026-10-31)

- All findings accepted as proposed, with:
- **F1:** no new render behaviour in O3. O3(a) becomes: the receipt verifies and the run ends
  `stopped: render: owner_render_*` (as O2 Q4). Rendering a run with refusals (a report with named gaps)
  is a product decision left for the user. Cost: a run with a refused module renders no report yet.
- **F2/Q1:** O3's Done-when "a run with one refused module still settles CP-5" is restated as the
  reviewer's distressed_restructuring case: the walk continues past the refused module, settles every
  module that does not need it, refuses each dependent with its named missing inputs, and the receipt
  verifies. Settling CP-5 over a missing producer (execution.py:244-246) is not built; it goes to the user
  in the final report. The fake `_world` is not used for this test; it runs on the real registry.
- **F5:** add the `run_pathway` resume to Task 3 (call_index continues per digest; Budget rebuilt from the
  reservation markers; a held unknown reservation stops the run as O5 rules).
- **F7:** a bounded `str` of the form `CP-0:Run-CP-4` style is not needed: use `tuple[str, ...]` of module
  ids plus a separate `missing_commands: tuple[str, ...]`, each bounded at 200 characters.
- **F9:** journal an `InternalError` fault before returning the unchanged receipt.
- **F10/Q3:** cap = `MAX_LINE`; Step 0 measures the view, narrative and readiness bodies; a body over the
  cap goes to the user.

## Amendment 2026-10-31 (from the O7 re-review, N1)
- Task 4's L5 spike would fail for every rerun: CP-0 `pack_sha256` and CP-1 `financials.run_id` bind the
  earlier run. Ruled: identity rebinding of exactly those two paths (`REBOUND_FIELDS`), pack must differ
  only by `run_id` (`ReplayPackChanged` otherwise), `rebound` recorded, guard test from probe
  `work/context-plan/probes/p5_replay_identity_fields.py`. See work/context-plan/reviews/o7-plan-review.md.
