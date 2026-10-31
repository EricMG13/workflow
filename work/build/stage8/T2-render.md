# T2: H06 + H07, owner text that renders wrong (stage contract; mx-feature)

Rules: `L/work/build/stage8/common.md`. Before any edit, run `git checkout -b claude/s8-render 61a86c10` and confirm the tip.
- Edit only `src/deploy_workflow/owners/cp2h.py` and `src/deploy_workflow/owners/cp8.py`.
- Put new tests in a **new** file, `tests/test_codex_render_fixes.py`, because T3 edits `tests/test_connect_cp8.py`.

## Inputs
- `K/CONSOLIDATED.md` rows H06 and H07.
- Probes `K/probes/v-render/probe_h06_cp2h.py` and `probe_h07_none.py` (and `run.sh`, which shows how they are run).

## Findings
- **H06:** CP-2H limitation panels show raw `{T2R…}` tokens (`cp2h.py:1862`, `:2115`; drawn by app.js :552/:593/:668). Build the gap limitation from the resolved text in `cp2h.py`, not the token template. Do not edit app.js. The test asserts the exact resolved limitation string, and that no `{T2R` token reaches the payload.
- **H07:** CP-8 accepts `None`/`none`/`null`/`nan` as text, and then render raises (`cp8.py:621` `_text`; the renderer's guard is at `src/deploy_vii/report_view.py:145`).
  - Refuse the renderer's null spellings in `_text`. Import the renderer's own constant from `deploy_vii.report_view` if one exists; you may import it but must not edit it.
  - If there is no importable constant, stop and report rather than copying the list.
  - The test asserts the exact refusal issue for each spelling, and that a normal text is still accepted.
