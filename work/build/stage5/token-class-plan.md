## Batch 2 round 3: which text facts are run text. Root cause and smallest fix plan

I read the code at lane HEAD 0b840ce. The lane later moved to 2f345c2, but `git diff 0b840ce HEAD -- src tests cases docs/reuse` is empty, so the findings still hold. I wrote nothing into any worktree. Probes are under `<S>/token-plan/probes/` and both tree copies are deleted.

### Root cause
Items 31 and 45 assumed that any known text fact whose text matches `_TOKEN` is producer-composed run text. The contract says otherwise. `Fact.text` is a plain `str` (`contracts.py:171`) and only `Claim.text` is `RunText` (`contracts.py:213`). `_carries_reference` (`report_view.py:1600-1607`) decides the type from syntax alone, and both paths then fail closed in `resolve` (`report_view.py:1111-1113`): the block path at `report_view.py:1654-1655` (`_token_runs` :1610) and the fact path at `render.py:166-176`. The grammar `_ID = [A-Za-z0-9][A-Za-z0-9_.:-]*` (`prose.py:56-58`) matches ordinary prose. In `probe_grammar.py` (exit 1, run at HEAD), six of nine realistic strings are flagged and all six raise: "[sic]", "Section 7.11 [Reserved].", "[Reserved]", "Credit Agreement [1]", "{a|b}" and "Credit Agreement [Amended], p. 4" (that one also raises "Bare figure: 4"). Three pass because their bracket content is not an identifier: "[Insufficient Information]", "[●]" and "[Exhibit 10.1]".

These are the ways a settled known text fact can carry the syntax with no reference meant:
- **Analyst free text.** CP-DR `question.text` becomes `TDR.2.<row>.question` (`cpdr.py:642`, analyst_judgment; the C1 probe confirms it). The CP-0 agenda `description` becomes `TDR.1.description`, and the CP-DR citation `locator` becomes `TDR.2.evidence` (not probed).
- **Verbatim source quotes.** CP-8's T7.2 thesis quotes (`cp8.py:1567`, value_class source) are an instance. `probe_rule.py` at HEAD raises "Unresolved reference: Reserved; …sic; …1" for a T7.2 quote. CP-8's own analyst text cannot hold brackets (`cp8.py:151,621-631`), but its quotes can.
- **Calculated text that embeds foreign strings.** CP-8 `evidence_id` and `source` are `"{source name}, {locator}"` (`cp8.py:1462,1572,1586-1589`, `evidence_id` is value_class calculated).
- **Core modules.** CP-4's verbatim covenant `definition_text` goes into T4C.6 (`cp4_legal.py:1095`), the ruling's own "[Reserved]" example.

### Options weighed
- **(a) The producer marks its facts.**
  - Marking by `value_class == "calculated"` is wrong: CP-8 `evidence_id` is calculated and embeds source names and locators.
  - Marking by "the fact text equals a module claim" fits the contract best, but it turns the item 31/45/49 tests red. `_what_changed_view` (`tests/test_connect_cp8.py:536-560`) builds the module with no claims and no value_class. It would also miss a line that mixes a spelled figure with a gap chip.
- **(b) A render-side registry. Recommended.**
  - `report_view` gets a private registry `_RUN_TEXT_TABLES = frozenset({("CP-8", "cp8.what_changed")})`. Every CP-8 line in that table comes from `_resolved(claim.text)` (`cp8.py:2153-2186`). Decision and summary text there cannot hold brackets (enums, and `cp8.py:621`).
  - The data it relies on is already on every fact (`table_id`), so no contract changes.
  - G1X §6 holds: it is a literal, with no `deploy_workflow` import. `report_view` already carries CP-8 literals in `_Spec`.
  - Inside a registered table, any `prose._RESERVED` character goes to `resolve`. That is stricter than `_TOKEN`, so an unbalanced `[T7.3.window` also fails closed.
- **(c) Respell only when every token binds.** This hides a failure. A producer typo such as `[T7.3.window.realized_valu]` cannot be told apart from "[sic]", so it would reach the page as written with no error. A coincidental match with a real fact id would also be respelled silently.
- **(d) Refuse at each source.** Verbatim filed text such as "[Reserved]", "[1]" or "[Amended]" must be quoted exactly and cannot be refused. Core modules in `src/deploy_vii` are pinned, and every future core would have to remember the rule.

**Contract change: none.** `Fact`, `Claim` and `Binding` are untouched, and the private signature `_carries_reference` is shared only with `render.py`. No item 39 record is needed beyond logging this plan's choice as an applied recommendation ("(b) private registry; not taken: Binding field (contract change), claim-equality (breaks item 45/49 tests)").

### Plan (one mx-feature task, test-first)
1. **RED** (expected to fail at HEAD).
   - `tests/test_connect_cpdr.py`: the C1 probe's case as a test. The `partial` submission with " [sic]?" renders, and the question fact's `display` equals the text as written.
   - `tests/test_connect_cp8.py`: put "Section 7.11 [Reserved]; see [sic] and [1]." in `T7.2.t01.thesis`. Both `display` and `table_display` equal the text as written, and the block renders.
   - `tests/test_connect_cp8.py`, the CP-8 malformed control: both `[T7.3.window.realized_valu]` and the unbalanced `[T7.3.window.realized_value` in `cp8.what_changed.outcome.value` raise "does not resolve" in both `_what_changed_lines` and `_payload_facts`. The first case passes at HEAD; the unbalanced case is the new guard.
   - Info: the outcome text "…for 3M Company…[T7.3.window.realized_value]…" with `issuer_name="3M Company"` renders on both paths. At HEAD it raises "Bare figure: 3M".
2. **GREEN.**
   - `src/deploy_vii/report_view.py`: add `_RUN_TEXT_TABLES` above `_carries_reference`. Change it to `_carries_reference(module_id: str, fact: Fact) -> bool`, returning registry membership and `fact.text is not None` and `prose._RESERVED.search(fact.text)`, with no try/except. Rewrite the docstring.
   - In `_prose_lines` (:1654), call `_carries_reference(module.module_id, fact)`, and pass `names=(view.run.issuer_name,)` through `_token_runs` to `resolve`.
   - `src/deploy_vii/render.py:166`: use `fact.status == "known" and _carries_reference(module.module_id, fact)`, and add `names=(view.run.issuer_name,)` to that `resolve` call.
   - My prototype of exactly this change is `<S>/token-plan/probes/apply_prototype.py`. It does not include the `names=` change.
3. **D12.** Append two `post_import_patches` records to `docs/reuse/manifest.json`:
   - `report_view.py`, prior 8506ef09… (record 67);
   - `render.py`, prior 1887bcb2… (record 68).
   - Run `work/build/keep/stage3-review/precise/probe_d12_strict.py`. It should flag only 3e5b537, 24f879a and 8aef58d.
4. **Low 1.** Make no change to CP-OS. After the fix, free and verbatim text never raises. The remaining raise needs malformed CP-8 composed text, and CP-8 compose refuses that before a head settles (`cp8.py:2145-2148`). A `cpos_render` code would amend the frozen refusal order in `docs/CPOS-OWNER-LEASE.md:73-78`.
5. **Must stay green.**
   - All of `tests/test_connect_cp8.py`, including the item 45/49 tests (:617, :632) and the item 31 tests (:639, :646).
   - `test_connect_cpdr.py`, `test_connected_render.py`, `test_legal_render.py`, `test_earnings_render.py` and the `test_chart_render_*` files.
   - `probe_e_report_data_payload.py` must exit 0.
   - ruff and `mypy --strict` on the two files.
6. **Genuine reruns:** G2 cp8 ×3, cpdr and CP-OS (`tests/test_owner_cpos.py`), plus `tests/test_owner_cp8.py`.
7. **Superseded probe.** `work/build/keep/fix2-rereview/probe_scope_markers.py` calls `_carries_reference(text)` and will raise TypeError. The fixer saves a copy that calls the new signature.

### Probes and exit codes
| Probe | At HEAD | After the prototype |
|---|---|---|
| `probe_c1_free_text_bracket_render.py` | 1 | 0 |
| `<S>/token-plan/probes/probe_rule.py` | 1 | 0 |
| `probe_e_report_data_payload.py` | 0 | 0 |
| `<S>/token-plan/probes/probe_grammar.py` | 1 | not rerun; it uses the old signature |
| `<S>/token-plan/probes/probe_info_names.py` (prototype without `names=`) | not run | 1, confirming the Info |
| Fast tests on 8 files (cp8, cpdr, connected, legal, earnings, chart s5/cr1/dr6) | not run | 1051 passed, 1 xfailed, exit 0 |

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Note, not a finding: a CP-8 line mixing a spelled figure with a gap chip would raise "Bare figure" on the spelled digits. No CP-8 claim mixes them today; OUT-01 holds only a gap chip.

Not verified: no genuine store, G2 or CP-OS run; the `names=` change and the RED tests were not built (only the registry rule was prototyped); CP-0 `description`, CP-DR `locator` and CP-4 `definition_text` are traced statically, not probed; whether CP-4's prose checks already refuse brackets; how the cpos, legal and earnings builders' `report_view.py`/`render.py` hash pins are enforced (they already differ from HEAD: c6b5…/7bf8… against 8506…/1887…); the D12 strict probe; ruff and mypy; the full suite.
