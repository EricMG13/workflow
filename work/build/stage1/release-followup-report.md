The fast set is green now: 3643 passed, 2 skipped, exit 0. It ran from /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/release-followup, branch claude/release-followup. Step 0 passed (HEAD was f949026 at the start). There are three commits, one per item, each ending with the Co-Authored-By line:

- 2e1eb7f test: oracle pin tests read cases/PINS.json
- 4297ab0 test: CP-2H B7 frozen CP-2G status is restricted
- a615355 fix: CP-2A break-at-base line names the single-quarter gate

**Item 1, pins (2e1eb7f).**
- **What changed:** 11 test files now read their expected hashes from cases/PINS.json: cp1c, cp1d, cp2g, cp2h, cp3, cp3c, cp3d, cp4, cp4c, cp5, cpdr. No hard-coded oracle hash is left. Each file keeps a fixed list of the paths it covers, so if a path drops out of PINS.json the test fails with a KeyError instead of quietly checking less.
- **Coverage kept or added:** every path is still pinned. cp1d now also pins builder/build.py. cp2g now also pins its own expected.json, submissions.json and manifest.json.
- **Files PINS.json does not list:** cases/financial/manifest.json (cp2g, cp4c) and cases/legal/manifest.json (cp4c) are checked against the `pins` section of the CP-2G or CP-4C manifest. Those manifests are themselves pinned by PINS.json, so the check is a chain.
- **Import-time pins:** cp2g and cp4c still assert while loading, so a mismatch still fails collection.
- **Left alone:** cpl10 `FINANCIAL_SHA` is a citation source hash, not a pin test.
- **Probe:** /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-followup/probe_pins.sh exits 0. In temporary copies it changed one byte in each of seven files and checked the covering tests: cp2a expected (cp2g and cp4c), financial manifest (cp2g and cp4c), legal manifest (cp4c), and the cp1c build, cp1d build, cp2h manifest and cp3d build. Every case was caught: rc=2 at collection for cp2g and cp4c, rc=1 for the others.

**Item 2, CP-2H B7 (4297ab0).**
- `test_frozen_composer_only_cp2g_status` is now a plain test. It asserts the frozen `fixture_total_loss` cell `T2R.1.u_cp2g.status` has text and shown equal to `restricted`, and that the computed cell matches the whole frozen record.
- I removed the strict xfail and the B5 override in `test_facts`. `test_upstream_statuses_are_the_bound_inputs` is kept. cp2h: 186 passed.

**Item 3, CP-2A (a615355).**
- **Ruling:** as you relayed from LEAD, release batch item 1 (fb371d5), applying L1 from the round 6 batch review.
- **What moved, 87b2a1a..HEAD:** in expected.json, only the `fixture_quarter_known` break-at-base own line changed. The builder now emits `BREAK_AT_BASE_NA if gate_na else BREAK_AT_BASE`. The builder also gained A4 (missing base free cash flow named first), A8 (the net-leverage short-circuit now checked after the gate) and an assert refusing quarter bases with mixed ratio statuses. None of these changed any frozen expectation, and cp2a.py already had A4 and A8. The oracle and the ruling agree.
- **Change:** cp2a.py adds `BREAK_AT_BASE_NA` and emits it when `_GATE["coverage"] in base.not_meaningful`. That is a quarter base where CP-1's interest coverage is known, the per-ratio form of the builder's gate_na. Every other case keeps the old bytes.
- **Tests (written first; 3 failed before the fix):**
  - `test_break_at_base_line_names_the_single_quarter_gate`, over the 4 frozen cases. `gap` is a quarter base without a twelve-month basis and keeps the old line.
  - `test_break_at_base_line_follows_the_coverage_break_gate`, two mixed quarter bases: total leverage gated gives the new line, interest coverage gated gives the old line.
  - The existing oracle equality test now passes. cp2a: 115 passed, 1 skipped.
- **Decision for LEAD:** on a mixed quarter base I made the clause follow the gate of the break it describes, the coverage break, not "any ratio not meaningful". The builder refuses mixed bases, so the oracle gives no answer there. This is my reading, and the second test pins it.

**Mutants.** /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-followup/mutants_cp2a.sh exits 0. It runs from a full temporary copy with PYTHONDONTWRITEBYTECODE=1, running tests/test_method_cp2a.py:

| Mutant | Exit code | Result |
| :--- | :--- | :--- |
| control (unchanged) | 0 | 115 passed |
| text always emitted | 1 | 7 failed |
| text never emitted (revert) | 1 | 3 failed |
| any_ratio (`bool(base.not_meaningful)`) | 1 | 1 failed |

**Gates.**
- The fast set (your exact command) exits 0.
- On all 13 changed files: `ruff check` passes, `ruff format --check` passes, and `MYPYPATH=src mypy --strict` reports no issues.
- `python3 -I cases/pins.py --check` exits 0 (69 paths).
- The diff touches nothing under cases/, src/deploy_vii or tests/defect_classes.py.

Not verified: the full test suite outside the fast set was not run. GitNexus impact and detect_changes were not run. Behaviour on a mixed quarter base has no oracle backing; the second item-3 test pins my reading. I did not read docs/rulings/2026-10-28-stage1.md, because LEAD confirmed the ruling through you.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
