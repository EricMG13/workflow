**Verdict: APPROVE.** Spec and quality both pass, with no High, Medium or Low findings. I made no edits or commits.

Target: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/release-followup`, `f949026..a615355`, 13 files, +158/-148, well under the 800-line ceiling.

**Spec verdict: PASS**

1. **Pins (2e1eb7f)**
   - **No hard-coded hash remains.** In `tests/test_method_*.py` the only 64-hex literal left is `tests/test_method_cpl10.py:40` `FINANCIAL_SHA`, a citation hash and not a pin test. Other `tests/*` files outside the brief also contain hex literals; I did not check whether any is an oracle pin.
   - **Every old path is still pinned.** `probe_old_pins.py` takes every path/hash pair from the 11 base test files at f949026. All 49 are still covered: 46 by `cases/PINS.json` and 3 by the manifest chain (financial in cp2g; financial and legal in cp4c). Every current hash matches its pin. Coverage grew: cp1d now pins `builder/build.py`, and cp2g pins its own expected, submissions and manifest.
   - **A missing path fails loudly.** `probe_missing_pin.sh` drops 6 keys from PINS.json in temp copies. Each covering test fails with a `KeyError`: rc=2 at collection for cp2g and cp4c, rc=1 for the rest. The fixed `PINNED` tuples are what make this hold (e.g. `tests/test_method_cp1c.py:30-33`).
   - **The chain is sound.**
     - `tests/test_method_cp2g.py:52-57`: the cp2g manifest is checked against PINS.json at import, then `FIN` is checked against `MANIFEST["pins"]`.
     - `tests/test_method_cp4c.py:62-67`: the same pattern for FIN and LEGAL.
     - `tests/test_method_cp4c.py:77-81`: this test re-checks both manifests.
     - A tampered financial or legal manifest fails at collection (rc=2).
   - **Rerun of `probe_pins.sh`:** exit 0. All 9 tamper/test pairs were caught.
2. **B7 (4297ab0)**
   - `tests/test_method_cp2h.py:1431-1441` asserts the frozen `text == shown == "restricted"`, then `_assert_cell(got, want)` against the whole frozen record.
   - The B5 override is gone from `test_facts` (`:288-293`). Nothing live is hidden: the cell is now compared to the frozen record with no substitution. This matches the ruling (`docs/rulings/2026-10-28-stage1.md`, Round 12 :88-91 and :168).
   - `test_upstream_statuses_are_the_bound_inputs` (`:1420`) is kept.
3. **CP-2A (a615355)**
   - The new line is built at `src/deploy_workflow/owners/cp2a.py:776` and chosen at `:1330-1332`.
   - **Equivalence with the builder holds on every frozen case.**
     - In the builder, `gate_na` is True only for `fixture_quarter_known` (`cases/cp2a-owner/builder/build.py:500`, Q4 with `cp1_ratios: True`).
     - In the module, `not_meaningful` holds the ratios that are known on a quarter base (`cp2a.py:213`).
     - `fixture_quarter_known`: interest coverage is known, so the new line, matching the builder.
     - `gap` (Q3): the ratios are not known, so the old line.
     - `positive` and `interest_undisclosed` (LTM bases): the set is empty, so the old line.
     - The builder emits `BREAK_AT_BASE_NA if gate_na else BREAK_AT_BASE` (`build.py:824`). Its text (`:592-594`) is byte-identical to `BREAK_AT_BASE[:-1] + ", and it is not calculated on a single-quarter base."`.
   - **Mixed quarter bases.** The builder refuses them (`build.py:644-646`), so the implementer's reading contradicts neither the builder nor the ruling text. Not flagged.
   - **Rerun of `mutants_cp2a.sh`:** exit 0. Every mutant was killed (table below).
4. **Constraints**
   - The diff stat is empty for `cases/`, `src/deploy_vii` and `tests/defect_classes.py`. The only changed source file is `src/deploy_workflow/owners/cp2a.py`.

**Quality verdict: PASS**
- I found no stub, fake value or catch-all. The two new CP-2A tests (`tests/test_method_cp2a.py:922-958`) hard-code the expected text instead of importing it from the module, so they check it independently.

**Findings**
- Info: `tests/test_method_cp2h.py:36-41` still loads `cases/cp2g-owner/expected.json` and `cases/financial/manifest.json` without checking the hash at load time. This predates the change, and the cp2g file is covered by `test_oracle_pins`. Owner item, not for this task.

**Probe exit codes** (scripts in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-followup-review/`; log in `probes.out` there)

| Probe | Exit | Result |
| :--- | :--- | :--- |
| `probe_pins.sh` (rerun copy) | 0 | 9/9 tampers caught |
| `mutants_cp2a.sh` (rerun copy) | 0 | control 0 (115 passed); always 1 (7 failed); never 1 (3 failed); any_ratio 1 (1 failed) |
| `probe_missing_pin.sh` (new) | 0 | 8/8 dropped-key checks failed with `KeyError` |
| `probe_old_pins.py` (new) | 0 | 49/49 old paths covered |

**Gates (run on the target worktree)**

| Gate | Exit | Result |
| :--- | :--- | :--- |
| Fast set | 0 | 3643 passed, 2 skipped |
| `python3 -I cases/pins.py --check` | 0 | 69 paths |
| `ruff check` on the 13 changed files | 0 | |
| `ruff format --check` on the 13 changed files | 0 | |
| `MYPYPATH=src mypy --strict` on the 13 changed files | 0 | |

Not verified: the full test suite outside the fast set; GitNexus impact and detect_changes; behaviour on a mixed quarter base, which has no oracle backing (the ruling on that has gone to LEAD); whether the hex literals in other `tests/*` files outside the brief's scope are oracle pins; whether `cases/pins.py --check` itself covers the manifest `pins` chain.
