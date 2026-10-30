**Round 4 re-review (claude/s5-round4, ca17721..9d6b70b): APPROVE.** Round 3's High is fixed, the registry holds exactly the 7 planned keys, and my spot checks found no missed table. No new findings.

**(1) High 1 is fixed.** My probe now exits 0 on 9d6b70b: the CP-L10 assessment shows "3.75 US$ m" in both `display` and `table_display`.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/probe_cpl10_analyst_reference.py`, exit 0.
- The keep probes also exit 0 on 9d6b70b: `round4-plan/probe_cpl10_all_fields.py`, `round4-plan/probe_cp2h_gap_reference.py`, c1, rule and e.

**(2) The registry is right.** `src/deploy_vii/report_view.py:1607-1618` holds exactly the 7 keys:
- CP-8: cp8.what_changed value
- CP-L10 TL10.3: assessment, credit_transmission
- CP-2H T2R.10: gap, why_it_matters, affected_analysis, action

No free or verbatim field is registered:
- Every CP-L10 key passes `prose_issues` at `cpl10.py:1060-1073`. The overall row's assessment is `overall.rationale`, which is checked there too.
- The CP-2H fields go through `_prose` at `cp2h.py:1531`.
- The free fields in those tables stay out of the registry: TL10.3 `source_refs`/`evidence`/`screen_item` and T2R.10 `id`/`severity`.
- `_carries_reference` keeps the same shape: it tests key membership, then `_RESERVED`, with no try/except.

**(3) Survey spot checks found no miss.**
- **Class C (core composers).** `business_context.py:1097`, `cp2_synthesis.py:582` and `cp6_committee.py:989` each spell every token before the text is stored.
  - Their raw `Cell(...)` calls take only enums, ids or pack fields. In `business_context.py`, `limit()` spells `use.limitation` before joining it into the cell (around line 1195), and `s.name` comes from the pack.
  - CP-2G T2H.9 spells its gap fields before storage (`cp2g.py:2149-2179`). CP-5 text allows no references at all (`cp5_integrity.py:603-608`).
- **Class E (no reference can resolve).** CP-DR refuses any digit in text, answer or limitation (`cpdr.py:274-276`). CP-3D `analyst_text` refuses digits (`cp3d.py:556-561`), and the summary goes through it. CP-2E `chk.prose` refuses digits and `run_text` refuses any reference (`cp2e.py:628-650`). The module fact ids (TDR.*, T2F.*) all contain digits, so no token can resolve.
- **Other modules.** I went through every `prose.issues`/`RunText` call site in the owners: cp1c, cp1d, cp2a, cp2g, cp4c and cp8. Each validated field either reaches claims only, is spelled before storage, or is already registered.

**(4) RED/GREEN and D12 are correct.**
- 9d6b70b's `tests/test_connect_cpl10.py` and `tests/test_connect_cp2h.py`, copied onto ca17721, give 15 failed and 239 passed. The 15 failures are exactly the new tests; the guards pass. On 9d6b70b they give 254 passed, 1 skipped. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/probe_r4_red_green.sh`, exit 0.
- D12: the new record's prior hash c2040a50 equals `report_view.py` at ca17721, its sha256 9b152b58 equals the file at 9d6b70b, and `project_commit` is 7598805. `render.py` does not change.

Not verified: the class C/E checks and the scan of other modules were code reading, not runs. No dynamic probe ran over the core composers' fixtures or over `model_validate`-built facts. I did not exercise the prose-block path for the new keys, or run genuine/G2/owner suites, the full suite, ruff, mypy or `probe_d12_strict.py`.
