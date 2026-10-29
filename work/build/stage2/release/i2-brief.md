# Stage 2 close release, I2 integration (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `R` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-release`, branch `claude/s2-release` at 5a6a746. `F` = `/Users/ericguei/Documents/Deploy Workflow Sessions/lead-cp6-freeze/work/lead/cp6-freeze` (chain tooling, read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Inputs
| Item | File |
|---|---|
| Fix reports | `L/work/build/stage2/release/fix1-report.md`, `fix2-report.md` |
| Q-C1 | `L/work/build/stage2/release/qc1-brief.md` (with its rulings), `qc1-preparer-report.md`, `qc1-review.md` |
| Fix notes | `L/work/build/stage2/release/fix-notes.md` |
| How the chain was run before | `L/work/build/stage2/release/w3-report.md` |

## Process
1. **Merge** into `R`, in this order, each with `--no-ff`:
   - `claude/s2r-f1` a50efb2;
   - `claude/s2r-f2` a8e93cf;
   - `claude/s2r-qc1` ff1dbce.

   Conflict rules:
   - Generated `cases/` files and `cases/PINS.json`: rebuild them in step 2. Never hand-merge them.
   - `cases/legal/render-expected.json`: keep Q-C1's values. They are `fixture.other_modules["CP-MODEL"]` = `unrun`, the `maturity-wall` block pin and the `responsibility_context_only` text. Its sha-valued leaves come from the chain.
   - `tests/cp2d_runs.py` and `tests/cp3c_runs.py`: re-pin to the chain's output.
   - Lease files: keep every amendment line from both sides.
2. **Chain to a fixed point** with `F` tooling, covering every builder. Take two fresh-copy rebuilds; they must be byte-identical to each other and to the tree. Then regenerate `cases/PINS.json` and run `--check`.
3. **Lease headers.** Add one "Amended by Modules 2026-10-29 (Stage 2 close release I2 chain)" line per sha the chain moved since the latest header line.
4. **Cites.** Fixer 1's source changes move the CP-1D, CP-2D and CP-L10 cites. Run `<S>/f2/refresh_view_cites.py` from the repo root to rewrite the TOOL-CONTRACT view ranges. Then check the cp2a and cp2d reader cites by hand. `<S>/f2/c1_cites_updated.py` must exit 0 once its expected cites are updated to the new lines. Also fix the stale `methods/cp1d.md:78` helper name, which must read `deploy_workflow.owners.blank.one_per_page`.
5. **Timing.** In `tests/test_readiness_linear.py`, tighten `gaps` (bound 1.5 → 1.0) and `attach` (0.5 → 0.4), so the old code fails by at least 5x. Prove it with `<S>/release-review-A/probes/a02_timing.py` on both the tip and `<S>/release-review-A/base`. If 5x cannot be met without making the fixed code flaky, keep the current bounds and report the measurements.
6. Commit after each step. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/pins.py --check`.
- **The fast set,** from `R`, using `PYTHONPATH=src:tests` and `L/.venv/bin/python -m pytest -q -p no:cacheprovider`. It covers:
  - `tests/test_method_*.py` and `tests/test_connect_*.py`;
  - `test_cp1b_registration`, `test_owner_g1x`, `test_host_h1`, `test_schema_normalise_escapes`;
  - `test_defect_classes_selfcheck`, `test_defect_classes_shared`, `test_defect_classes_cp1`;
  - `test_engine_blank_text`, `test_rule_issue_bounds`, `test_owner_blank`, `test_owner_order`;
  - `test_stage2_classes`, `test_stage2_classes_batch`;
  - `test_legal_render`, `test_connected_render`, `test_citation_blank_quote`, `test_readiness_linear`.

  It must exit 0, with the Q-C1 tripwire as its only xfail.
- **The three S1a tests** fixer 2 changed:
  - `tests/test_owner_s1a.py::test_plan_attempts_heads_and_cp0`
  - `::test_cp2_invalid_submission_without_a_read_refuses`

  They take about 11 minutes. Run them in the background and report the exit code.
- **Lint and types:**
  - `ruff format --check` and `ruff check` on the changed `.py` files. Known findings that predate the release:
    - cp4_legal TRY004;
    - source_context ISC004 :581/:583;
    - prose ISC004 :114/:127;
    - `report_view.py:293` SIM102;
    - `test_cp1b_registration.py:98` PLW1510;
    - `test_legal_render.py` C408.
  - `mypy --strict` on the changed `src/` files.
- **Suppressions:** count with `git grep noqa -- src tests | wc -l` (must be 13 or less) and `git grep "type: ignore" -- src tests | wc -l` (must be 5 or less).
- **Not yours:** the slow render suites, `test_source_tools.py` and the genuine `test_owner_<cp>.py` runs. The controller runs those.

## Outputs (report as text, at most about 1.5k tokens)
- The tip SHA.
- Each conflict and how it was resolved.
- Every sha the chain moved.
- Each step's outcome.
- Gate exit codes.
- A `Not verified:` line.
- The ledger line.

Rules: no stub or fake value standing in for real behaviour, and no catch-all that hides a failure unless it is documented and logged. Only a re-pin may move an oracle value in I2; if any value moves otherwise, stop and report it. Stop any background process before you hand back.
