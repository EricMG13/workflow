# Task4-A2 addendum 1 — explicit shared-live capability

This pre-fix extension addresses reported C1 GREEN1 PID83700 exit1 (93 failed/7 passed): earnings_delta registration causes eager shared-live schema totality failure. Original lease SHA256 `da0471d83746dc67bf40e9b3e14aa7984994abfa812820265174bd8cb6964142` and original access oracle SHA256 `a8210ba05e81c3cba04634bfe82e3e7aa11525892407b41d379ebf0298413d0c` remain immutable. This addendum supersedes only the assumption that every registered chain has shared-live support and the original exclusion of the sixth file below. It adds no financial values, new analytical gate or owner acceptance.

## Exact authority and source lineage

C1 HEAD observed statically:85785c9fa5370d3227309462346060f0e4fe4352. Uncommitted file hashes: registry09b4c43e5124e2d9b39c22d8c56d297515eeea2203f5c1d1c3d7e690dca8ad79; upstream57766eeedaf293e47e7416c7cc8cb51217a3fa50ed8f041917015c0774bfc7ca. Unchanged live/submission.py hash6656846fab07c46e7fe60006c965065ccb0aacd6a86164081c0d25eeb3575e4a. These are file hashes, not commit identifiers. LEAD/PM integrate this exact addendum/oracle before the fix and name the later integrated exact admission base, preserving C1's admitted A2 work.

Original five-file ownership remains. Add SIXTH `src/deploy_vii/live/submission.py`, only eligible-step schema totality and the unsupported-capability schema-lookup hook. Within already-leased registry.py add the field/helper and clarify journal-versus-live descriptions. Existing tests/test_cp1b_registration.py and tests/test_upstream_tools.py own the focused guards. No other file: no Execution, host/source, live/settings/tools/context/prompts, provider, fake schema, new dispatcher or owner implementation. No blanket exception handler or name-based skip list. C1 is not alone and must preserve other edits.

## Explicit registration versus capability

Append `shared_live: bool = True` after existing StepChain fields, preserving positional compatibility. Reject non-bool values with ValueError. All existing chains retain True; CP1B alone explicitly sets False. Its earnings_delta journal step, dependencies and original empty optional sets/maps stay unchanged. False declares offline registration without shared-live schema/dispatcher support, never a financial gap or permission grant.

Add `shared_live_step_modules(chains: Sequence[StepChain] = STEP_CHAINS) -> dict[str, str]`, including steps iff their chain has shared_live=True, in registry/chain order. Keep inclusive step_modules, settling/repair/prefill/bound/projection helpers, module_route and regression_cases behavior unchanged. CP1B planned route remains CP0 + CP1's five steps + earnings_delta; a planned order is not a live capability. Existing tool classification remains structurally derived: submit-only does not supply schema, execution authority or source permission. No alternate owner/dependency map.

CP1B fixed offline UpstreamTools v2 access stays supported exactly under A2's current-CP1 grants and refusals. CP2/CP5 v1 behavior is unchanged. No raw source/quote/extra producer or coordinate authority is added.

## Strict schema set and explicit shared-live refusal

live.submission.step_definitions(schemas) compares schemas to shared_live_step_modules(), not inclusive step_modules(). Exact-set validation remains strict: any missing eligible schema raises ValueError; any unknown or offline-only schema key raises ValueError. Absence of a CP1B schema is honest, never a fake schema or silent missing-schema waiver. All prior StepDef/schema/module identities and eligible order remain unchanged.

Current live.tools directly indexes STEPS. Guarding only submit_model_payload is insufficient. Return a narrow guarded dict subclass from step_definitions, preserving its dict/Mapping iteration/items/len/membership behavior. Its missing-key hook raises ValueError containing `offline-only` for a registered step excluded by shared_live=False; genuinely unknown keys retain KeyError. Derive this distinction from registry capability, never an earnings_delta string exception. Thus submit_model_payload and existing submit_spec/tool_specs schema indexing reject offline requests before normalization, callbacks, tool assembly, journal writes or provider work, without editing live/tools.py. earnings_delta remains absent from STEPS membership/iteration; no schema sentinel is inserted. get/membership inspection can report absent and conveys no execution capability. Missing genuine eligible schemas must still fail construction.

live/settings uses inclusive step_modules to recognize optional effort keys; recognition never enables a schema/dispatcher. No settings change. No provider runner is added. Future CP1B shared-live support requires a separately leased real schema/composer/dispatcher; flipping the flag alone must encounter totality failure.

## Component checks and limits

The companion access-registration-expected.json pins component guards before the fix. Public source/upstream imports in fresh processes and either order must succeed, without provider/engine work. Existing schemas remain usable; missing genuine live schema still fails. Registered offline schema requests explicitly refuse before mutations. Preserve all original A2 permission/response limits and CP2/CP5 v1 cases.

Focused argv, only after separate fresh one-heavy-job admission from C1:

`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q tests/test_cp1b_registration.py tests/test_upstream_tools.py`

Record exact final bytes/base/runtime/PID/UTC/exit and retained RED/GREEN evidence; required confidence-review, post-edit rewrite-tournament and existing independent sensitive implementation review remain. This static freeze ran no imports/tests/engines/providers. Paid/provider/live testing stays paused. C3 actual owner, C1 A4 actual CP5 and C2 FP02 remain separate downstream leases. No actual CP1B completion follows from registration/import success.
