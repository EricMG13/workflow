# T4 plan (mx-autonomous a0d5907d, 2026-10-31; written by the controller from the planner's text report)

The line numbers are from T6's tip 88fbda46.

1. **Where the quality read is served.** There are two functions; each verifier recomputes through them.
   - `financial_workflow.py:305-307` (`_projection`). Two workflows reach it:
     - the CP-1 financial slice: `read_inputs` :741 and its verifier :1151;
     - the CP-1 owner workflow: `owner_workflow._inputs` :824, `read_inputs` :1208, and verifiers :1852-1861.
   - `earnings_workflow.py:972-974` (`_projection`): the read :4001, and verifiers :2257, :2793 and :3320.
   - `host.py:461`, `financial_workflow.py:1429` and `earnings_workflow.py:1183` are promotion and handoff checks over the full inputs. They are not reads, and they stay unchanged.
2. **Validity.** The review must cover every claim with its exact evidence ids, keep lineage at or below each ceiling, keep inherited findings, and put any new references inside `references` (`quality.py:267-292`; `cp1_workflow.py:415-419` adds the canonical-handoff slot). The scope carries everything an analyst needs:
   - Coverage is not answered by the analyst.
   - `inputs_sha256` is prefilled (`live/submission.py:525-526`).
   - Gap and `qa-cell` ids are dropped, so a new finding cannot cite them. References are optional, so this is a loss of detail, not a validity gap.
   - No `src/deploy_vii` change is needed.
   - **Conflict:** `quality_scope` adds `record_json` and `citations`/`quote` under `evidence[*].record` (`prompts.py:1083-1085`). That is forbidden by `docs/CP1-MODEL-SLICE.md:83-87`, `docs/handoffs/cp1-model.md:87-89` and `tests/test_financial_workflow.py:977`. Ruling item 87 settles it.
3. **The change.** Add `_quality_read(registers) -> tuple[str, str]` in `financial_workflow.py`:
   - compute `inputs = cp1_quality_inputs(registers)` once;
   - compute `scope = quality_scope(registers, inputs)`, narrowed per item 87;
   - return `(inputs.content_hash(), json.dumps(scope, sort_keys=True, separators=(",", ":")))`.

   Both `_projection` sites become `return _quality_read(cp1_registers(historical, attempt.ticket_id))`. Earnings imports `_quality_read` through its existing `from deploy_workflow.financial_workflow import (...)` (:87). `owner_workflow.py`, `host.py` and `promote_cp1` are unchanged.
4. **Tests, written first.**
   - **RED 1** (`tests/test_financial_workflow.py`). On a clone of `genuine_quality_case[0]`, call `read_inputs()` and assert:
     - `inputs_sha256 == cp1_quality_inputs(cp1_registers(store, ticket)).content_hash()`;
     - the body equals the canonical narrowed scope JSON, and a second read gives the same bytes;
     - `"coverage_cells"` is in the body and `"references"` is not;
     - the body is under 524,288 bytes and under 1/20 of the full inputs JSON;
     - there is no `record_json`, `citations` or `quote` key at any depth.
   - **RED 2.** The same shape and binding assertions at `tests/test_earnings_workflow.py:1093-1094`.
   - **Changes.** `test_financial_workflow.py:1013-1014` (coverage from `inputs["coverage"]`) changes to:
     - present = present non-cell slots + the `slots` of the present cell groups;
     - total = non-cell slots + all cell-group `slots`.
   - These drivers keep working: `s1a_runs.py:324`, `cp1d_runs.py:196`, `cp2g_runs.py:197`, `cp2h_runs.py:175`, `test_earnings_workflow.py:1094-1097`.
5. **Risks.**
   - `PromptError` on a `qa-cell` slot cannot fire when the scope comes from the same registers. The transports' existing sanitising handlers cover it, so add no new catch.
   - `sort_keys` keeps the bytes deterministic, and the verifiers compare body bytes.
   - On CZR the scope is 9,965 bytes without record entries, against 16,886,498 for the full read (probe `work/build/keep/s8-t4-plan/probe_scope_size.py`).
   - Peak memory does not drop.

Not verified (planner): `quality_scope` itself was not computed (system python lacks the deps); the synthetic size and the 512 KiB bound are unmeasured; no pytest was run.
