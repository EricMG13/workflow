**Verdict: REVISE.** The change is built as the plan says. Step 3 found a table the registry misses, and that miss is a High.

**Spec check (steps 1, 2 and 4): matches the plan**
- `src/deploy_vii/report_view.py:1604`: the registry holds only `("CP-8", "cp8.what_changed")`.
- `report_view.py:1607-1618`: `_carries_reference` checks registry membership, then `prose._RESERVED`. It has no try/except.
- `report_view.py:1667-1669` and `src/deploy_vii/render.py:169,178`: both paths pass `names=(view.run.issuer_name,)`. No other fact is respelled.
- Brief probes, run on the ca17721 copy, all exit 0: `probe_c1_free_text_bracket_render.py`, `probe_rule.py` and `probe_e_report_data_payload.py`.
- RED/GREEN: I copied ca17721's two test files into a 2f345c2 copy. Four tests fail there. The typo case passes at base, as the plan expects. All five pass at ca17721. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/probe_red_green.sh`, exit 0.
- D12: both records are correct. Each prior hash equals the file at 2f345c2: report_view 8506ef09, render 1887bcb2. Each new hash equals the file at c4da4da and ca17721: c2040a50 and 9805c343. Both carry `project_commit` c4da4da8.

**High 1: CP-L10 analyst text with references now shows raw tokens (a regression)**
- **Where the text comes from.** `src/deploy_workflow/owners/cpl10.py:1060-1073` checks `assessment`, `credit_transmission` and `overall.rationale` with `prose_issues(text, bound, names=(issuer,))`. That check accepts `{TL10.2.<topic>.change|US$ m}` references to the module's own facts. Bare figures must be written as such references.
- **Where it is stored.** The same strings are stored word for word as TL10.3 known text facts: `cpl10.py:804` (assessment), `:809-811` (credit_transmission) and `:826` (overall rationale). They are also the claim text, at `cpl10.py:936,940`.
- **What changed.** `("CP-L10", "TL10.3")` is not in `_RUN_TEXT_TABLES` (`report_view.py:1604`). So `render.py:166-181` now sends the raw token to the module table and the inspector.
- **Failure scenario.** A submission that `change_screen` accepts has the assessment "The balance moved by {TL10.2.cash.change|US$ m} over the quarter."
  - At ca17721, `display` and `table_display` show `{TL10.2.cash.change|US$ m}`.
  - At base 2f345c2, they showed "3.75 US$ m".
- **Probe.** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/probe_cpl10_analyst_reference.py`: exit 1 at ca17721, exit 0 at 2f345c2.
- **Why the scan missed it.** The fixer's `probe_scope_markers.py` reports no HIT, but that tells us nothing here: it uses the new signature, and the CP-L10 fixtures contain no references.
- **What the fix needs to decide.** Run text and free text can share one table (TL10.3 also holds `screen_item`, `evidence` and `source_refs`), so the decision probably has to be made per field, not per table. A fix that keys on the field must still keep "[sic]"-style verbatim text safe.

**Info 1**
- The fix report says "the three new c4da4da records". The manifest adds two. The D12 records themselves are correct.

Not verified:
- The other owners whose analyst text passes `prose.issues`: cp1c, cp1d, cp2a, cp2e, cp2g, cp2h, cp4c and blank. I only established that their composed `ref()`/`slot()` strings go into claims, not facts. Whether any of them also stores reference-bearing analyst text as a known text fact was not probed.
- cp3d `analyst_text` fields and the core modules (`cp3_relative_value`/`cp6_committee` `out.text(rationale)`, `cp5_integrity` `Cell(r.rationale)`).
- The CP-L10 block path. TL10.3 is bound to the Evidence block as a table, so I did not run the block path for it.
- Genuine G2 and CP-OS runs, the full suite, ruff and mypy.
