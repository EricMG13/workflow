Round 3 is built and the gates pass, except one `ruff check` finding in code I did not touch. D12 flags only the three expected commits.

Worktree: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a6031124fa7b32150`, branch `claude/s5-round3`, based on 2f345c2 (tip confirmed). Tip is `ca17721`. The `.venv` link is removed and the tree is clean. No background process was started.

**Commits**
1. `5011edf` RED. All four new tests fail at the base for the stated causes.
   - `tests/test_connect_cpdr.py`: a CP-DR question holding "[sic]?" must render. At base it raises "Unresolved reference: sic".
   - `tests/test_connect_cp8.py`: a T7.2 thesis quote of "Section 7.11 [Reserved]; see [sic] and [1]." must show as written in `display` and `table_display`. At base it raises "Unresolved reference: Reserved; sic; 1".
   - `tests/test_connect_cp8.py`: the CP-8 malformed-token control, parametrised over a typo token and an unbalanced token, on both the block path and the payload path. The unbalanced case is the new guard and fails at base with "DID NOT RAISE". The typo case passes at base, as the plan expects.
   - `tests/test_connect_cp8.py`: the "3M Company" issuer-name case. At base it raises "Bare figure: 3M".
2. `c4da4da` GREEN.
   - `report_view.py`: new private `_RUN_TEXT_TABLES = frozenset({("CP-8", "cp8.what_changed")})`. `_carries_reference(module_id, fact)` now returns true only for a fact in a registered table that holds a `prose._RESERVED` character. It has no try/except.
   - `report_view.py`: `_token_runs` takes `names`, and `_prose_lines` passes `names=(view.run.issuer_name,)`.
   - `render.py`: the fact path uses the new signature and passes `names=(view.run.issuer_name,)` to `resolve`.
3. `ca17721` D12: two `post_import_patches` records, in the same place as the 26a78ca/35809c2 precedent.
   - `report_view.py`: prior 8506ef09 to c2040a50.
   - `render.py`: prior 1887bcb2 to 9805c343.
   - Both use `project_commit` c4da4da8.

**Gates** (exit codes only; I did not time each gate)
- `probe_c1_free_text_bracket_render.py`: exit 0.
- `probe_rule.py`: exit 0.
- `probe_e_report_data_payload.py`: exit 0.
- The 11-file fast pytest set with `-m "not genuine"`: 1158 passed, 1 xfailed (the known dr6 chip xfail), about 10 s.
- `ruff format --check` on the four edited files: exit 0.
- `mypy --strict` on `report_view.py` and `render.py`: exit 0.
- `ruff check` on the four edited files: exit 1, one finding. It is SIM102 at `src/deploy_vii/report_view.py:312`, in the debt_stack validator. My diff does not touch that line, and I did not check whether it also fails at the base.
- Suppressions: `noqa` is 13 and `type: ignore` is 5, with none added in the diff.
- `probe_d12_strict.py <worktree> 697fe8a HEAD`: exit 1. It flags only 3e5b537, 24f879a and 8aef58d (item19 BAD on the first and third, chain GAP on 8aef58d). The three new c4da4da records show `chain=ok item19=ok`.
- Saved `probe_scope_markers.py`, adapted to the new signature, in `<S>/round3/` (its `_carries_reference(mod.module_id, f)` call uses the literals "CP-L10" and "CP-1" for the cpl10 and CP-1 facts). It exits 0 with no HIT lines, so no settled known text fact in the cp5 or cpl10 fast fixtures is treated as run text.

Not verified: genuine reruns (G2 cp8 x3, cpdr, CP-OS, `tests/test_owner_cp8.py`; plan step 6, not in this brief); the full suite; CP-0 `description`, CP-DR `locator` and CP-4 `definition_text` (they get the same registry treatment but were not probed); the pre-existing SIM102 finding at `report_view.py:312` on the base; the `<S>/round3/` copy of `probe_scope_markers.py` is not committed.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n (the first `ruff check` run found the SIM102 finding; all tests passed first time)
