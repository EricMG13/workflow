# Item 82/83: absent-input reconciliation checks become a limitation on public cases (stage contract; mx-feature, test first)

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s7-absent-input e7d2857` and confirm the tip. `L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only for you).

**You cannot run the project's Python here.** The venv is refused to isolated worktrees, so do not work around it. The controller runs RED and every gate in your worktree. Commit with plain separate `git add <files>` and `git commit` commands. Every commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 75, 82, 83 (Q1-Q5 are decided there) |
| Plan | `L/work/build/stage7/recon-plan.md`: trace, change, RED tests, risks |
| Working models of the change and the fixtures (in-process simulations) | `L/work/build/keep/s7-recon-plan/probe_synth_public.py` (synthetic financial case run as public with segment partial; `planned` mode simulates both hops); `probe_czr_after.py` (CZR replay); `probe_head_t412.py`; `probe_czr_recon.py` |
| Code | `src/deploy_vii/canonical_audit.py` (:476-501), `src/deploy_vii/canonical_gaps.py` (:162-250, :367-431), `src/deploy_vii/narrative.py` (:439-451, read only), `tests/test_financial_workflow.py` (`make_pack`, `financials`), `tests/test_connect_cpl10.py:45` (importlib loading pattern), `tests/czr_runs.py` (`czr_closed`), `cases/czr-2026q2-earnings-update/submissions-partial.json` |
| D12 | `docs/reuse/manifest.json` `post_import_patches` (see the last record for the shape); `L/work/build/keep/s53-B/probe_d12_strict.py` header for the rules |

GitNexus has no index for this repo. The blast radius in the plan comes from grep: only these two src files change, and no fixture, oracle, pin or golden hash moves.

## Phase A: RED (then stop and report)
Write `tests/test_cp1_absent_input.py` and nothing else. Commit it as `test: RED absent-input downgrade (item 82)`. Then stop and report; the controller runs it at this tip.
1. `test_public_absent_input_is_a_limitation_not_a_qa_block`: synthetic financial case with `run.case_kind="public"` and `segment_disclosure.status="partial"`.
   - Promotion is valid.
   - Handoff QA is `Restricted` with score ≤ 59.
   - Every segment gap is WARN and its description starts with the prefix.
   - The head's T4.12 facts carry the prefix, and the head's first limitation starts `CP-1 QA Restricted:`.
2. `test_downgrade_restricts_not_passes`: same fixture. The narrative status is `restricted` with no BLOCK gaps, `QualityInputs.module_status == "restricted"`, and the QA status is not `Passed`.
3. `test_public_disagreeing_cash_check_still_blocks` (genuine CZR, about 1 min):
   - `czr_closed` on `submissions-partial.json` still raises with `qa_blocked_issue(39, "Insufficient Information")`.
   - The rebuilt gap ledger has exactly 3 BLOCK gaps: NCF_CASH_MOVEMENT for fy-2025 and h1-2026, and 1 `calculation_gate`.
   - 135 WARN gaps carry the prefix.
4. `test_synthetic_case_still_blocks` (guard; passes today): fixture 1 with `case_kind="synthetic"` still refuses as QA Blocked.
5. `test_absent_input_limitation_refuses_non_absent_cases`: helper unit test. Import `absent_input_limitation` and `ABSENT_INPUT_PREFIX` **inside the test function**, so a missing helper fails only this test. The helper returns None for:
   - a check with a difference;
   - a conflicting term;
   - an FX-normalised term;
   - a non-public case;
   - a WARN status.
   It returns the prefixed text for a public BLOCK check with an absent term.

Use the exact prefix `Absent input, stated as a limitation on a public filed pack (rulings item 82): `. Patch fixtures with pytest's `monkeypatch`, not module-level assignment. Assert exact values, not shapes. Tests 1-3 and 5 must fail today for the reported cause: a QA block, a blocked narrative, 137 BLOCK gaps, or a missing helper. They must not fail on import errors at collection.

## Phase B: GREEN (when the controller sends RED results)
Implement the plan's change in `canonical_audit.py` and `canonical_gaps.py` only:
- `ABSENT_INPUT_PREFIX` and `absent_input_limitation(...)` in `canonical_audit.py`;
- the audit hop at :493-501;
- `_calculation_gaps` gains `public` and `conflicting` and applies the helper to period checks;
- pass both in from :429-431;
- `calculation_gate` is unchanged.

Commit as `feat: absent-input reconciliation checks downgrade on public cases (item 82)`. Then, in a second commit, add one `post_import_patches` record per file to `docs/reuse/manifest.json`:
- `prior_project_sha256` = the file's sha before your change; this is the imported sha if the file has no record yet;
- `project_commit` = your feat commit;
- `sha256` = the file at that commit;
- `review` = `docs/rulings/2026-10-29-stage3.md`.
Compute shas with `shasum -a 256`.

## Rules
- No stub or fake value standing in for real behaviour.
- No catch-all that hides a failure.
- Do not change `financial_reconciliation.py`, `period_reconciliation.py`, `model_readiness.py`, `narrative.py`, `cp1_quality.py`, `quality.py` or `cp1_workflow.py`.
- Never use bare `git stash`.

## Output (text, under 500 tokens, after each phase)
- worktree path and tip SHA;
- what you wrote;
- a `Not verified:` line.
