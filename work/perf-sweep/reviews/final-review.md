# Whole-branch review 05c3b27..455e4ef (mx-precise; returned as text, saved by the controller)

Spec PASS · Quality APPROVE · High none · Medium none.
- Diff 740+/10− (750 < 800); no lock/pyproject change; src/deploy_vii edits limited to P2
  (contracts.py:265-267, 294) and P3 (execution.py:17, 540-553, 625); deploy_workflow only P1
  (earnings_workflow.py:1685-1728). Suppressions 13/5 at both ends (src+tests). Public API unchanged.
- Cross-task: P3 cache hit skips a validate_tables pass already fixed by verified bytes; errors not
  cached. P1 producer from cache or model_copy hashes the same (no instance cache). _FrozenExecution
  error mapping unchanged; _ParsedExecution bypasses the base cache (F1).
- Low 1 progress.md RSS range misstated (5.00–5.35 GiB). Low 2 product-plan.md:73 stale 233 MiB.
  Low 3 CONTRACT.md lacks the P1–P3 authorization. Low 4 identity claim had no saved log.
  Info: P3 key hashes the 42 MiB bytes per call (unmeasured, small vs parse).
- Triage: Task 1/2 minors and adversary L1/L2 closed (66cce2a). F1 double cache: owner should
  acknowledge memory before merge. F2 cpos-owner pin: owner, not a blocker (build.py already fails on
  the report_view.py pin at base; no test reads these pins).
- Confidence list: shared Module mutation refuted; process-global cache vs patched validators refuted
  for the current suite (future patchers need cache_clear); tamper via cache refuted; P1 error order
  refuted (content_hash cannot raise on a validated model); P2 None/empty table refuted; identity on
  E-NO-YOY only (real limitation, stated); memory regression real (F1).
Not verified (reviewer): no pytest; could not reproduce identity (trees in scratchpad, not $TMPDIR);
heavy timings pending; bytes-key hash cost unmeasured; identity only for E-NO-YOY.
