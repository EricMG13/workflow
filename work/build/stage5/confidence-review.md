## Stage 5.3 confidence review: `4822066..9f71bfa`, the six files in scope

**Verdict: REVISE.** I found one Medium defect, confirmed by a failing probe. Nothing else rose to a finding.

### Doubt list (13 points), each with its classification

1. **`src/deploy_vii/render.py:166-176` (item 45). CONFIRMED defect (Medium M1).** This hunk sends every known text fact that `prose._TOKEN` matches through `resolve()`, which fails closed. That covers facts made from analyst free text, not only CP-8's outcome fact.
2. **`src/deploy_workflow/owners/cpos.py:249`. CONFIRMED, a consequence of M1 (Low).** When `render(view)` raises, the error escapes as a raw `ValueError("Claim run text does not resolve…")`. The module docstring (:12-14) promises only `cpos_*`-prefixed refusals.
3. **`host.py:657-679`: the tail and schema of a live-contract producer (CP-1A, CP-2, CP-4) consumed by CP-3 or CP-4C. Fine statically.** Each live core's tail is `submission.content_hash()` under its `STEPS` schema (`business_context.py:1722/1792`, `cp2_synthesis.py:878/899`, `cp4_legal.py:1472/1493`). No store run exercised it.
4. **`host.py:670`: `len(attempt.steps) != 1` for owner producers. Fine.** All 13 owner cores declare `STEP_IDS = (STEP_ID,)`, and each `SUBMISSION_INPUT` is the step id with hyphens plus `-submission`, which is the `owner_tail` rule.
5. **`host.py:699-716`: the memo key leaves out `store.directory`. Fine.** On a cache hit every digest is re-read and hash-checked from the current store. The snapshot carries uuid tickets, so two stores do not share a key in practice. This is the same pattern as `_CP1_VERIFIED`, which predates the branch.
6. **`host.py:614-625`: `producer.content_hash()` against `attempt.result_sha256`. Fine.** `Execution.head_module` (`execution.py:614-630`) returns the blob unchanged unless the head is stale, and a stale head never binds.
7. **`host.py:943-944`: the owner scope keeps held sources that are not ready. By design** (rulings round 10 item 5): `SourceTools.stage` answers `unavailable`.
8. **CP-5 requires CP-MODEL, so the walk might reach CP-5 before publication (`owner_workflow.py:1112-1126`). Fine.** `_check_specs` (:1006-1011) refuses the run at create.
9. **`owner_workflow.py:2169-2176`: R6-1 with a context producer (CP-1A ← CP-1). Fine.** I checked all 18 `DELIVERY_SCOPES` and none plans CP-1 after CP-1A.
10. **`owner_rendering.py:662`: `==` here against `startswith` in `_verify_walk`. Fine.** `current_inputs` raises the exact `BLOCKED_EDGE` text (`execution.py:239,245`).
11. **`owner_rendering.py:835`: a complete outcome needs at least one bound fact per section, which an empty CP-DR agenda would not give. Fine.** The `slice-cpdr-research` scope has no sections, only rails.
12. **`cpos.py:138-160`: the model-link gates against `app.js:602-604`. Fine.** The gates are the same: first matching fact, non-empty text, anchored path regex, artifact hash, both provenance facts.
13. **`owner_workflow.py:1649-1657`: a transition can span more than one snapshot (`after > before+1`), so intermediate snapshots are checked only by R6-2. Not decidable statically.** I found no exploit, because the before/after equality in `_verify_transition` limits the net effect.

### Findings

**Medium M1. An accepted CP-DR submission whose question text holds a bracketed word (e.g. `[sic]`) yields a run whose page can never be rendered.**
- **Where:**
  - `src/deploy_vii/render.py:166-176` (item 45, d394ac1);
  - the input path: `owners/cpdr.py:110-112` (`question.text: Text`, which gets no `RunText` or token check) and `:643` (it becomes the known text fact `TDR.2.<row>.question`, bound to the Evidence rail).
- **Scenario:**
  1. The analyst writes "…after its end [sic]?". `ENTRY_VALIDATOR` returns no issues, and the head settles.
  2. `render()` reaches the fact loop. `_carries_reference` matches `[sic]`, so `resolve` raises "Unresolved reference: sic".
  3. G2 then refuses `owner_render_build` (`owner_rendering.py:750-754`) for a run the verifier accepted, and `cpos.navigation` raises an unprefixed `ValueError`.
  4. The head is settled, so there is no repair path.
- **Why it was missed:**
  - Before item 45, the text was shown as written.
  - The item 45 re-review (`work/build/stage4/batch2-fix2-rereview.md`) checked only the cp5 and cpl10 fixture texts.
  - The traceback confirms the raise comes from `render.py:170`, not from the block path. `build()` succeeds.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/conf/probe_c1_free_text_bracket_render.py`, **exit 1**.
  - Control: the oracle `partial` submission renders.
  - Changed submission: the entry validator passes it, then `render` raises.
  - Run it from a copy of `9f71bfa` with `PYTHONPATH=src:tests`.
- **Smallest fix, at the source.** This matches cpdr's own rule that no composition may raise after the binding write (`cpdr.py:322-323`).
  - In `validate_research` (via `_question_issues`, or beside `_model_text_issues`), refuse a `question.text` that `prose._TOKEN` matches or that contains `{}[]`.
  - Write a clipped `gaps[g].questions[q].text: …` line without the input value.
  - RED test: the probe's second case expects a content issue.
  - No frozen text moves. The oracle questions hold no brackets: the control case passes.
- **Owner question (not part of the fix):**
  - Item 45 widened fail-closed from bound prose facts to every known text fact, so other cores' free-text fields may have the same exposure. Two candidates I did not check are the CP-0 agenda `description` (it becomes `TDR.1.description`) and the CP-DR citation `locator` (it becomes `TDR.2.evidence`).
  - The other route is a render-side rule: respell a fact only when all its tokens bind in its module, and otherwise show it as written. That departs from the `_carries_reference` docstring, so it needs a ruling.

**Low L1, rides with M1.** CP-OS lets a render failure escape without a `cpos_*` prefix (`cpos.py:249`). It goes away when M1 is fixed at the source.

**Info.** The item 45 respelling (`render.py:168-175`) and `_token_runs` both call `resolve` without `names=(issuer_name,)`, while the claim path passes it (`render.py:180`). An answer fact holding a token plus an issuer name with digits (e.g. "3M") would raise "Bare figure" on the fact path even though its claim resolves. I did not probe this. It is consistent with the block path.

The tree copy is deleted. Only the probe remains under `s53/conf/`. No worktree was written.

Not verified: no genuine store, G2 or CP-OS run (M1 is shown by composing the real CP-DR module and calling `render`, not through `render_owner_slice`); doubt 3 has no store run behind it; whether the CP-0 agenda descriptions and other cores' free-text fields can carry token syntax; doubt 13's intermediate snapshots; ruff, mypy and pytest were not run; I read the 947-line `report_view.py` diff only at the new functions, not line by line.
