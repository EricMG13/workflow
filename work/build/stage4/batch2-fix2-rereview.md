**Verdict: APPROVE.** Medium 1 is fixed. I found no new findings. Scope: `claude/s4-batch2-fix2` `e37b73e..35809c2`.

**Spec (Medium 1, ruling item 45)**
- **Fix:** `src/deploy_vii/render.py:166-176`. When a fact is known, has text, and `_carries_reference` matches it, the fact's `display` and `table_display` both get the joined run texts from `resolve(fact.text, prose.bind(module.facts), module_refs(report.index, module.module_id))`.
- **Same inputs as the block path:** `report_view._token_runs` (`report_view.py:1610-1627`) builds its refs by filtering `_refs_by_fact(index)` (`:2497`) by module. `module_refs` (`:1089-1093`) does the same filter. Both calls use the same binding and pass no `names`.
- **Other facts:** the earlier assignments at `render.py:162-165` are unchanged, so every other fact's spelling stays as it was.
- **No try/except** anywhere in `render.py`.
- **Not copied:** `_carries_reference` is imported (`render.py:16`).
- **Probe** `L/work/build/keep/stage4-review-arch/probe_e_report_data_payload.py`, run on the `35809c2` copy: exit 0. The only surviving token is the stored `facts[150].text`, and the block is bound to G26.
- **RED test:** `<S>/fix2-rereview/probe_red.sh` puts the `e37b73e` `render.py` into the copy. Both new tests then fail (pytest exit 1, probe exit 0), and the script puts the fixed file back. With the fix, both pass. All 682 non-genuine tests in `tests/test_connect_cp8.py` pass (exit 0).

**Point 2: `{{…}}` placeholders in the oracles**
- `prose._TOKEN` (`src/deploy_vii/prose.py:56-58`) does match the inner `{ID}` of most of these literals: `{{PACK_SHA256}}`, `{{STATUS:CP-0}}`, `{{SHA256:CP-1A}}`, `CP-0:{{CP0_RESULT_SHA256}}` and `{{CP0_STATUS_WORD}}`. Examples are at `cases/cp5-owner/expected.json:197,221,230` and `cases/cpl10-owner/expected.json:1973,2006`. `{{TRACE:CP-1 …}}` does not match, because a space is not allowed in `_ID`.
- These are oracle-side markers only. The tests swap each one for a plain value before comparing:
  - cp5: hash, status word, fact_id, trace string (`tests/test_method_cp5.py:585-596`)
  - cpl10: hash or "With limitations" (`tests/test_owner_cpl10.py:159-162`)
- None of those values contains braces. The product's facts hold the values, not the markers.
- **Probe** `<S>/fix2-rereview/probe_scope_markers.py`, exit 0. It checks every known text fact in the cp5 fast fixtures (positive 947, gap 921: all heads plus the CP-5 candidate) and the cpl10 composed cells (positive 103, limited 88, plus the upstream CP-1 facts). None carries a reference, so no cp5 or cpl10 page changes or fails closed.

**Point 3: manifest**
The item 45 record is the last entry of `post_import_patches` (index 75 of 76) in `docs/reuse/manifest.json:1746-1754`, and it names the change. Its `sha256` `1887bcb2…` equals the hash of `render.py` at `35809c2`.

**Quality:** no stub, fake value or catch-all. A malformed mix of tokens or a foreign token still fails closed through `resolve`.

The scratch copy is deleted. Both probes are kept under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix2-rereview/`.

Not verified: the genuine CP-8, CP-L10 and cp5 owner runs (the controller is running CP-8 and CP-L10); the browser DOM (`app.js` was not run); whether the manifest record's `prior_project_sha256` matches the earlier chain (D12 was not re-run); ruff and mypy were not re-run; mutation and property gates.
