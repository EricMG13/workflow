# Adversarial review: P1 17e07ba, P3 4af08ce (mx-adversary; returned as text, saved by the controller)

Verdicts: P1 approve · P3 approve · High none · Medium none

## Low
- L1 (P3) `execution.py:545-550`, `:621-623`: callers now share one cached Module; a write that
  bypasses `frozen=True` (`m.model_fields_set.discard(...)`, `object.__setattr__`) would reach later
  readers and break `result()`'s canonical promise; `result(s) is result(s)` now True. Exposure
  today none (AST scan of src/ and tests/: no such writes on contracts; no `is`/`id()` logic over
  Modules; `head_module` stale path uses `model_copy`, `probes/adv_p3_stale_head.py` exit 0; host
  `_ParsedExecution` already shares). Fix: comment that returned Modules are shared and must never
  be written through. Probe `probes/adv_p3_shared_state.py` (exit 0 at both commits, outputs differ).
- L2 (P3) `execution.py:543-545`: memory figure too low. Four distinct CP-1-size canonical blobs
  filled the cache: +1,290 MiB RSS (≈322 MiB/entry); each lru key also keeps the 43.9 MB raw alive;
  host `_PARSED_MODULES` parses its own copies: combined +2,579 MiB, peak RSS 3.41 GB (register F1
  said 1.6–1.9 GiB). Fix the comment and F1. Optional (owner): key on sha256 only (−≈168 MiB).
  Probe `probes/adv_p3_memory.py` exit 0.

## Checked and holding
- P1: `producer` never rebound; only production caller `_owner_stage` (`:2066-2080`); `_full_cp1`
  (`:1252`) already requires `producer.content_hash() == head.result_sha256`; no other callers.
  Real 44 MB CP-1 blob, E-QOQ-FLAT parameters, `probes/adv_p1_real_cp1_operands.py`:
  points 0:5 → 115 refs, before 115 hashes 21.99 s, after 1 hash 0.17 s, lineage sha `860fd8d1…`
  identical; points 5:12 → 161 refs, 161 hashes 27.02 s vs 1 hash 0.16 s, `25f5863f…` identical.
  Error order unchanged (content_hash on a validated Module does not raise).
- P3: key (sha256, raw) with raw = the bytes `_load` just verified; exact byte equality on hit;
  Decimal trap (§P4) avoided. Real blob after warm hit: one-byte tamper, another canonical module's
  bytes under the old name, deleted file → pre-P3 messages; warm hit equals independent parse;
  cold 0.74 s, warm 0.039 s (`probes/adv_p3_real_blob_cache.py` exit 0). Exceptions not cached.
  Subclasses (`_FrozenExecution` earnings/financial, `_RecordingExecution` records via `_load`,
  `_ParsedExecution` overrides `result`, test doubles) unaffected. No test patches
  `Module.model_validate_json` outside the new file. 8 threads cold: 5 parses, equal results, one
  entry (`probes/adv_p3_threads.py` exit 0; GIL build).
- Gates (all exit 0): new tests + P1 test 5 passed; test_upstream_tools, test_source_tools,
  test_host_h1, test_connect_cpdr together 553 passed in 37 min (separately host_h1 37,
  upstream 219, cpdr 161); ruff check/format on the 4 changed files; mypy --strict on
  execution.py and earnings_workflow.py; `cases/pins.py --check`.

## Out of scope, for the owner (P2)
`cases/cpos-owner` builder and manifest pin `src/deploy_vii/contracts.py` = `3b33bfc…` (b0ac40c's
file); after P2 it is `618229c…`. The same builder's `report_view.py` and `render.py` pins were
already stale at b0ac40c. No test reads these pins.

Not verified (reviewer): heavy earnings owner tests incl.
`test_known_core_blob_integrity_failures_map_identity_and_never_recreate_bytes`; full suite; RSS on
a loaded machine (load 9–12) incl. allocator overhead; free-threaded Python; multi-process writes.
