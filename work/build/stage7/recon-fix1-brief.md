# Item 82 fix round 1 (stage contract; mx-feature, test first)

Work in your existing worktree on `claude/s7-absent-input` (tip 5e5e00c). `L` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). You still cannot run Python; the controller runs RED and the gates. Use plain separate `git add`/`git commit`; every commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Results that opened this round
- **The controller's GREEN run of `tests/test_cp1_absent_input.py` at 5e5e00c: 2 failed, 3 passed. Both failures are test defects; the product is right.**
  - Test 1, `cells = … f.text.startswith(PREFIX)` gives 0 where 11 is expected. The T4.12 fact text is `"<gap_id>: <description>"`, for example `cp1-gap:c9ae…: Absent input, stated as a limitation …`. The controller checked the stored head: 11 T4.12 facts contain the prefix.
  - Test 3, `"NCF_CASH_MOVEMENT" in g.model_dump_json()` is False. A cash gap carries its source check id in `metric` (for example `recon:93ffc100…`) and the period in `periods[0].reference` (`fy-2025`). The check type is not in the gap. Seen with `L/work/build/keep/s7-review/cash_gap_json.py`.
- **mx-adversary REVISE, M1 (Medium), confirmed by the controller.** Probe `L/work/build/keep/s7-review/adversary/probe_h_shadow.py` exits 1. On a public case, an explicit `missing` account row for (period, metric) shadows a known printed statement line, because explicit accounts win (`statement_validation.py:329-341`). A real disagreement then becomes "absent input" WARN, and CP-1 promotes as Restricted 59. The end-to-end scenario is `L/work/build/keep/s7-review/adversary/probe_h_e2e.py`: the synthetic case, q2-2025 segment revenue 31 against revenue 30, plus an explicit missing `revenue` account for q2-2025.
- **L1 (adversary, Low).** A parent check whose blocker text quotes a child's computed difference is labelled "Absent input". The blocker sites are `financial_reconciliation.py:485-486` and `period_reconciliation.py:214-217`, `:249-250`. Probe: `adversary/probe_a_parent_child.py`.
- **L2 (both reviewers, Low).** The period hop cannot see FX normalisation, because `PeriodTerm` has no normalisation field. Probes: `precise/p2_period_fx.py` (exits 1 while open), `adversary/probe_f_fx.py`.

## Phase A: tests (commit, then stop and report)
Edit only `tests/test_cp1_absent_input.py`. Commit as `test: RED item 82 fix round 1`.
1. **Test 1:** for every prefixed gap `g`, the head's T4.12 facts include one whose text is exactly `f"{g.gap_id}: {g.description}"`. The number of T4.12 facts containing `PREFIX` equals `SYNTHETIC_PREFIXED_GAPS`.
2. **Test 3:**
   - also spy on `deploy_vii.canonical_audit.reconcile_financials` to capture the report;
   - map `check_id -> (check_type, period_id)`;
   - assert the two non-gate BLOCK gaps' `metric` values map to exactly `{("NCF_CASH_MOVEMENT", "fy-2025"), ("NCF_CASH_MOVEMENT", "h1-2026")}`.
3. **New `test_shadowing_missing_account_keeps_the_disagreement_blocked`** (M1). Build the `probe_h_e2e.py` "shadow" input with `monkeypatch`, on a public case. Assert:
   - promotion is refused with `qa_blocked_issue(…)`;
   - the narrative still holds at least one BLOCK gap;
   - no gap that cites the shadowed explicit account's id carries the prefix.
4. **New unit tests for the helper:**
   - **L1:** a public BLOCK `Reconciliation`, difference None, explanation carrying a child-difference blocker text exactly as `financial_reconciliation.py:485-486` builds it. The helper returns None.
   - **L2:** a public BLOCK `PeriodCheck` whose term's `observation_ids` include an id in the new FX-normalised set. The helper returns None.
   - **M1 unit:** a public BLOCK check whose term's observation id is in the new shadowed set. The helper returns None.

   Import the new names inside the test functions, so a missing name fails only that test.

## Phase B: code (after the controller sends RED)
Edit `src/deploy_vii/canonical_audit.py` and `src/deploy_vii/canonical_gaps.py` only.
- **M1:** add `shadowed_account_ids(book) -> frozenset[str]`: explicit accounts with no amount whose (period, metric) has a known value in `statement_accounts(book)`. The helper takes it as a keyword argument, `shadowed`, and returns None when any term cites one of those ids. This works like `conflicting` and applies at both hops.
- **L2:** add `fx_normalised_ids(book) -> frozenset[str]`: the observation ids that feed `normalize_facilities(book)`, the FX-normalised inputs. The helper takes it as `normalised`. A `PeriodTerm` whose `observation_ids` intersect it returns None, and the `ReconciliationTerm.normalization` rule stays.
- **L1:** the helper returns None when the explanation contains a child-difference blocker text. Match on the exact phrases those sites build. Name each phrase as a module constant, with a comment giving its source line.
- Update the D12 records for both files: a new `post_import_patches` record per file, chained from the 157dc6d sha, with `project_commit` = your new feat commit. Make this a second commit.

## Rules
- No stub or fake value standing in for real behaviour.
- No catch-all that hides a failure.
- Do not touch `financial_reconciliation.py`, `period_reconciliation.py`, `statement_validation.py`, `narrative.py`, `quality.py`, `cp1_quality.py` or `cp1_workflow.py`.
- Never use bare `git stash`.

## Output (text, under 500 tokens, after each phase)
- tip SHA;
- what changed;
- a `Not verified:` line.
