# Q-C1 preparer report (mx-feature a5f86934)

Q-C1 oracle batch is committed. Tip SHA is 80c9bb8, on `claude/s2r-qc1` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-qc1`, one commit on 5a6a746, tree clean. Only `cases/` and `docs/CP2D-OWNER-LEASE.md` were touched.

**Gates**
- `python3 -I cases/pins.py` regenerated `cases/PINS.json`. `--check` exits 0 (75 paths).
- Double rebuild: two `fresh_copy.py` copies, each run through `chain.sh`, both exit 0. The two copies are byte-identical, and equal to the committed `cases/` tree.
- `ruff format --check` on the four touched builders fails. It also fails on HEAD (checked cp4: 15 or more reformat hunks), and reformatting would move the pins. I changed single lines in the existing style and did not reformat.
- Against the unchanged `src/`, I ran only the five named test files. Result: 3 failed, 579 passed.

**Moved values and sources**
1. `cases/legal/render-expected.json`:
   - `fixture.other_modules["CP-MODEL"]` goes from `not_in_pathway` to `unrun` (brief scope 2).
   - `other_front_sections.blocks["maturity-wall"]` goes to owner `MODEL`, producers `["CP-1"]`, kind `dense`, state `not_run`, route null, note `"Not run: CP-1 has not run."`.
   - The `responsibility_context_only` text is rewritten.
   - Source: approved page `rbot-fp-04-covenant-refinancing.dc.html:42`, pack brief section 3, and `report_view.py:1099` (the `model-chart-strip` `_Spec` pattern).
   - I checked the rendered values with a scratch patch outside the repo that swaps the spec to `("MODEL", "chart", ("CP-1",))` and sets the preset to `("CP-0","CP-1","CP-MODEL","CP-1A","CP-2","CP-2D","CP-4","CP-3C","CP-5")`. `tests/test_legal_render.py` then passed 76 of 76.
   - The kind is `dense` because the unrun fallback maps `chart` to `dense`.
   - The note is "has not run" because CP-1 is `unrun`, not `not_in_pathway`, in that fixture.
2. `cases/cp2d-owner/builder/build.py`, which produces `expected.json`:
   - `fp04_render.blocks["maturity-wall"]` goes from `{CP-2D, dense, primary_tab "T2E.4", tabs []}` to `{MODEL, dense, primary_tab null, tabs ["T2E.4"], populated}`.
   - New `fp04_render.maturity_wall_note` explains the change.
3. `cases/cp4-owner/builder/build.py`: `render.other_five_sections` now says `maturity-wall (MODEL)` and gives the CP-1 "Not run" wording. The test in `tests/test_method_cp4.py` already passes.
4. Pure re-pins:
   - `cp3c-owner` `build.py` and `manifest.json`.
   - `cp4c-owner` `build.py` and `manifest.json`.
   - `PINS.json`.
   - The cp3c and cp4c `expected.json` files did not move.
5. `docs/CP2D-OWNER-LEASE.md`: new Q-C1 amendment paragraph; the Rendered sections lines (about :133-135) and acceptance 7 are updated. Old and new hashes are in the paragraph. `docs/CP4-OWNER-LEASE.md` was not touched, because it is out of my scope. It needs a one-line amendment, as the W2-A1 note at its line 3 says `maturity-wall` is CP-2D's.

**Decision: what T2E.4 becomes**
- The `T2E.4 -> maturity-wall` binding in `bindings/cp2d.py` stays unchanged, so `test_bindings_follow_the_lease` is unaffected.
- It is now a non-primary tab behind the MODEL content.
- "Unbound" is not available. `validate_bindings` (`bindings/__init__.py:111`) reports every settled fact without a binding, and `test_validate_bindings_over_the_settled_tables_is_clean` would fail.
- The pack brief lists no CP-2D maturity view on this page, so the table cannot be primary.
- The lease already says the CP-2D table "stays as it is".

**Failing tests the builder must turn green**
- `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]`. Needed: the `maturity-wall` `_Spec` becomes owner `MODEL`, producers `("CP-1",)`; and `_PRESETS["covenant_refinancing"]` in `contracts.py` gains `"CP-MODEL"` right after `"CP-1"`.
- `tests/test_connect_cp2d.py::test_run_driver_assembles_the_oracle_run` fails with "oracle drift: build.py" because `tests/cp2d_runs.py` still pins the old hashes. Re-pin there:
  - `builder/build.py` → `f8b6f607729072ea8df676506692a6dbb1d2d806b6f325223a619ed9f5d78c17`
  - `expected.json` → `969f3013d45d235d2500f019f621ccd129719d2f2cb95a503a306fe131967d79`
- `tests/cp3c_runs.py` (not in my five files, by inspection) pins hashes that moved. New values:
  - `builder/build.py` → `42b1685ac609ba4025013d1a25a8ec09db003a4f3920c9a174ad75f81a3daa93`
  - `manifest.json` → `45dacc7bc7ecee8d4e4fe40d555f6f5b5f3097601aee21bca2777a6b56180ad1`
  - Its `expected.json` pin is unchanged.
- The builder must also update `test_spec_rows_serve_the_three_blocks` in `tests/test_connect_cp2d.py`, which expects owner CP-2D for `maturity-wall`. This will go red once the spec changes.
- `tests/test_connect_cp4.py` and `tests/test_method_cp4.py` pass.

**Questions for the reviewer**
- Today `_block` builds S.4 figures only from a filled binding slot. FP-04 `maturity-wall` has CP-2D's T2E.4 as its only binding, and `_cp1_strip` / `_STRIP_FIGURES` only know `model-chart-strip` and `metric-strip`.
- So the builder likely needs a CP-1 binding into `maturity-wall` (for example T4.18 as a second placement) plus a `maturity-wall` entry for S.4 in `_STRIP_FIGURES`. I did not pin this because no `cases/` oracle covers CP-1 bindings.
- The reviewer should confirm that is intended.
- A populated `maturity-wall` render is not oracle-pinned beyond the CP-2D `fp04_render` entry.

Not verified: no populated (non-empty) MODEL `maturity-wall` render against the real code, because that code does not exist yet. The empty-state pins were checked only with the out-of-repo scratch patch. The CP-1 binding into `maturity-wall` is unpinned. `tests/test_connect_cp3c.py`, `tests/test_source_tools.py` and the full suite were not run. The `tests/cp2d_runs.py` and `tests/cp3c_runs.py` re-pins are untested. No cp4c chain test was run; the chain only rebuilt cp4c. No new-behaviour test applies to this oracle-only change, so the red tests above are the proof. The ruff format baseline of the builders is already failing.

---

Q-C1 oracle batch is committed. Tip SHA is 80c9bb8, on `claude/s2r-qc1` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-qc1`, one commit on 5a6a746, tree clean. Only `cases/` and `docs/CP2D-OWNER-LEASE.md` were touched.

**Gates**
- `python3 -I cases/pins.py` regenerated `cases/PINS.json`. `--check` exits 0 (75 paths).
- Double rebuild: two `fresh_copy.py` copies, each run through `chain.sh`, both exit 0. The two copies are byte-identical, and equal to the committed `cases/` tree.
- `ruff format --check` on the four touched builders fails. It also fails on HEAD (checked cp4: 15 or more reformat hunks), and reformatting would move the pins. I changed single lines in the existing style and did not reformat.
- Against the unchanged `src/`, I ran only the five named test files. Result: 3 failed, 579 passed.

**Moved values and sources**
1. `cases/legal/render-expected.json`:
   - `fixture.other_modules["CP-MODEL"]` goes from `not_in_pathway` to `unrun` (brief scope 2).
   - `other_front_sections.blocks["maturity-wall"]` goes to owner `MODEL`, producers `["CP-1"]`, kind `dense`, state `not_run`, route null, note `"Not run: CP-1 has not run."`.
   - The `responsibility_context_only` text is rewritten.
   - Source: approved page `rbot-fp-04-covenant-refinancing.dc.html:42`, pack brief section 3, and `report_view.py:1099` (the `model-chart-strip` `_Spec` pattern).
   - I checked the rendered values with a scratch patch outside the repo that swaps the spec to `("MODEL", "chart", ("CP-1",))` and sets the preset to `("CP-0","CP-1","CP-MODEL","CP-1A","CP-2","CP-2D","CP-4","CP-3C","CP-5")`. `tests/test_legal_render.py` then passed 76 of 76.
   - The kind is `dense` because the unrun fallback maps `chart` to `dense`.
   - The note is "has not run" because CP-1 is `unrun`, not `not_in_pathway`, in that fixture.
2. `cases/cp2d-owner/builder/build.py`, which produces `expected.json`:
   - `fp04_render.blocks["maturity-wall"]` goes from `{CP-2D, dense, primary_tab "T2E.4", tabs []}` to `{MODEL, dense, primary_tab null, tabs ["T2E.4"], populated}`.
   - New `fp04_render.maturity_wall_note` explains the change.
3. `cases/cp4-owner/builder/build.py`: `render.other_five_sections` now says `maturity-wall (MODEL)` and gives the CP-1 "Not run" wording. The test in `tests/test_method_cp4.py` already passes.
4. Pure re-pins:
   - `cp3c-owner` `build.py` and `manifest.json`.
   - `cp4c-owner` `build.py` and `manifest.json`.
   - `PINS.json`.
   - The cp3c and cp4c `expected.json` files did not move.
5. `docs/CP2D-OWNER-LEASE.md`: new Q-C1 amendment paragraph; the Rendered sections lines (about :133-135) and acceptance 7 are updated. Old and new hashes are in the paragraph. `docs/CP4-OWNER-LEASE.md` was not touched, because it is out of my scope. It needs a one-line amendment, as the W2-A1 note at its line 3 says `maturity-wall` is CP-2D's.

**Decision: what T2E.4 becomes**
- The `T2E.4 -> maturity-wall` binding in `bindings/cp2d.py` stays unchanged, so `test_bindings_follow_the_lease` is unaffected.
- It is now a non-primary tab behind the MODEL content.
- "Unbound" is not available. `validate_bindings` (`bindings/__init__.py:111`) reports every settled fact without a binding, and `test_validate_bindings_over_the_settled_tables_is_clean` would fail.
- The pack brief lists no CP-2D maturity view on this page, so the table cannot be primary.
- The lease already says the CP-2D table "stays as it is".

**Failing tests the builder must turn green**
- `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]`. Needed: the `maturity-wall` `_Spec` becomes owner `MODEL`, producers `("CP-1",)`; and `_PRESETS["covenant_refinancing"]` in `contracts.py` gains `"CP-MODEL"` right after `"CP-1"`.
- `tests/test_connect_cp2d.py::test_run_driver_assembles_the_oracle_run` fails with "oracle drift: build.py" because `tests/cp2d_runs.py` still pins the old hashes. Re-pin there:
  - `builder/build.py` → `f8b6f607729072ea8df676506692a6dbb1d2d806b6f325223a619ed9f5d78c17`
  - `expected.json` → `969f3013d45d235d2500f019f621ccd129719d2f2cb95a503a306fe131967d79`
- `tests/cp3c_runs.py` (not in my five files, by inspection) pins hashes that moved. New values:
  - `builder/build.py` → `42b1685ac609ba4025013d1a25a8ec09db003a4f3920c9a174ad75f81a3daa93`
  - `manifest.json` → `45dacc7bc7ecee8d4e4fe40d555f6f5b5f3097601aee21bca2777a6b56180ad1`
  - Its `expected.json` pin is unchanged.
- The builder must also update `test_spec_rows_serve_the_three_blocks` in `tests/test_connect_cp2d.py`, which expects owner CP-2D for `maturity-wall`. This will go red once the spec changes.
- `tests/test_connect_cp4.py` and `tests/test_method_cp4.py` pass.

**Questions for the reviewer**
- Today `_block` builds S.4 figures only from a filled binding slot. FP-04 `maturity-wall` has CP-2D's T2E.4 as its only binding, and `_cp1_strip` / `_STRIP_FIGURES` only know `model-chart-strip` and `metric-strip`.
- So the builder likely needs a CP-1 binding into `maturity-wall` (for example T4.18 as a second placement) plus a `maturity-wall` entry for S.4 in `_STRIP_FIGURES`. I did not pin this because no `cases/` oracle covers CP-1 bindings.
- The reviewer should confirm that is intended.
- A populated `maturity-wall` render is not oracle-pinned beyond the CP-2D `fp04_render` entry.

Not verified: no populated (non-empty) MODEL `maturity-wall` render against the real code, because that code does not exist yet. The empty-state pins were checked only with the out-of-repo scratch patch. The CP-1 binding into `maturity-wall` is unpinned. `tests/test_connect_cp3c.py`, `tests/test_source_tools.py` and the full suite were not run. The `tests/cp2d_runs.py` and `tests/cp3c_runs.py` re-pins are untested. No cp4c chain test was run; the chain only rebuilt cp4c. No new-behaviour test applies to this oracle-only change, so the red tests above are the proof. The ruff format baseline of the builders is already failing.

---

New tip is ed627ef on `claude/s2r-qc1`. It adds one "Amended by Modules 2026-10-29 (Q-C1, user-approved)" line to `docs/CP4-OWNER-LEASE.md` only, saying `maturity-wall` is MODEL-owned in FP-04 (producer CP-1) and the CP-2D T2E.4 table is a non-primary tab. The line points to the FP04 amendment at `docs/CP4-FP04-BINDING-LEASE.md` :84-98, but I did not edit that file because you said to touch only the CP-4 owner lease. Line 92 of the FP04 file still calls `maturity-wall` CP-2D's. I did not add the CP-1 binding into `maturity-wall` or the `_STRIP_FIGURES` entry, per your ruling. Not verified: no gate applies to a lease-text amendment, and none was run on this change.

---

New tip is ed627ef on `claude/s2r-qc1`. It adds one "Amended by Modules 2026-10-29 (Q-C1, user-approved)" line to `docs/CP4-OWNER-LEASE.md` only, saying `maturity-wall` is MODEL-owned in FP-04 (producer CP-1) and the CP-2D T2E.4 table is a non-primary tab. The line points to the FP04 amendment at `docs/CP4-FP04-BINDING-LEASE.md` :84-98, but I did not edit that file because you said to touch only the CP-4 owner lease. Line 92 of the FP04 file still calls `maturity-wall` CP-2D's. I did not add the CP-1 binding into `maturity-wall` or the `_STRIP_FIGURES` entry, per your ruling. Not verified: no gate applies to a lease-text amendment, and none was run on this change.

---

New tip is 67b8a23 on `claude/s2r-qc1`. It adds a Q-C1 amendment to `docs/CP4-FP04-BINDING-LEASE.md`, directly after the W2-B amendment. The note says `maturity-wall` is MODEL-owned in FP-04 (producer CP-1) and that CP-2D owns only `liquidity-runway` and `funding-gap`. It also says the T2E.4 table is a non-primary tab. I did not rewrite the original CP-2D wording at :92 or :85; the new note sits beside it, matching how the file's other amendments work, and no other line in that file called `maturity-wall` CP-2D's. Not verified: no gate applies to a lease-text amendment, and none was run on this change.
