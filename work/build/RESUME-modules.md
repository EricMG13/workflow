# Modules session: resume file (written 2026-10-31 ~10:35 at a usage handoff)

The Modules controller (session 468d5879, on the lane below) is being handed over to a fresh session on another account. Read this file first, then `CLAUDE.md`, `AGENTS.md`, `~/.claude/CLAUDE.md`, the memory index `~/.claude/projects/-Users-ericguei-Documents-Deploy-Workflow/memory/MEMORY.md`, and the tail of `work/build/ledger.md` (from about 08:00 on 2026-10-31). The rulings are in `docs/rulings/2026-10-29-stage3.md`, items 81-88. The owner list is `work/build/stage2/lows.md`.

## Paths
- **`L`, the lane (this worktree):** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`, branch `claude/module-dev-status-review-0981b6`, tip 081c7054 at the time of writing.
- **Old scratchpad, `N`:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/468d5879-6c5e-43ce-b132-cebe416f0ef5/scratchpad`. It holds the run logs. /private/tmp is cleared on reboot, and the background runs below belong to the old session; they may stop when it ends.
- **The test command,** run from a worktree root:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$L/.venv/bin/python" -m pytest -q -p no:cacheprovider --basetemp=<scratch dir> <tests>`
  - Delete the basetemp afterwards.
  - The fast set is `$(cat $L/work/build/keep/fast-set.txt) tests/test_shell_css.py tests/test_source_context_blank.py`.
- **Static gates:**
  - `$L/.venv/bin/ruff check src tests`: baseline 160. `ruff check src` is 88.
  - `ruff format --check src tests`: 3 files (md) fail at baseline.
  - `$L/.venv/bin/mypy src`: 0.
  - Suppressions: noqa 12, type: ignore 5.
  - `python3 -I cases/pins.py --check`: 87.
  - D12: `python3 -I $L/work/build/keep/s53-B/probe_d12_strict.py <repo> <base> <rev>`, which must exit 0.

## The branches ready to merge into the lane, and what each waits for
Each branch is in its own agent worktree (`.claude/worktrees/agent-<id>`). Merge with `git merge --no-ff <branch>` from `L`. The order below avoids conflicts; `docs/reuse/manifest.json` may need both sides kept.

1. **T1** (H01+H02+H08 precheck), `claude/s8-precheck` @5606c695 (worktree agent-ac1c51e9eea5773d4).
   - Review APPROVE. Passing so far: fast set 10546; financial_workflow 20; source workflow+tools 167; CZR replay matches the base.
   - **Waits for:** the earnings suite, log `N/s8t1/earn.log`.
   - Ledger: `agent=mx-feature fix-rounds=2`.
2. **T2** (H06+H07 render), `claude/s8-render` @fe71420a (agent-a1ceb9b5c3b9c048d).
   - Review APPROVE. Passing so far: fast 10547; method 931; owner cp8 86.
   - **Waits for:** `N/s8t2/owner-cp2h.log`. g2 passed: 8 passed, exit 0, at 10:41.
   - Ledger: `fix-rounds=1`.
3. **Item 82** (absent input becomes a limitation on public packs).
   - The final branch is `claude/s7-absent-input-3` @683bf950 (agent-ad578b923e77abaf6), built on `claude/s7-absent-input-2` @81e224f1.
   - fix 2 (ruling item 88: `CASH_SCOPE_BLOCKER` stays BLOCK) is APPROVED: RED/GREEN 10/10 and D12 ok.
   - **Waits for:** the earnings suite on 81e224f1, log `N/s7gates2/g4-earn.log`. It still covers fix 2, which only adds one refusal.
   - **After merging:** update `RESULT-partial.md`, MODULES.csv row 3 (CP-1) and lows.md with the CZR counts. Base 138 BLOCK becomes 3 BLOCK + 135 prefixed WARN (`work/build/keep/s7-compare/`).
   - Ledger: `fix-rounds=2`.
4. **T6** (speed-branch merge, D12, F1 parse cache, F2 cpos-owner re-pin), `claude/s8-speed` @88fbda46 (agent-a85e6cee38aa83cb0).
   - Review APPROVE. D12 exit 0; the builder reruns identically.
   - **Waits for:** `N/s8t6/earn.log`. The fast set passed (10602 passed, 19 skipped, exit 0) and so did source workflow+tools (167 passed, exit 0).
   - Ledger: `fix-rounds=1`.
5. **T4** (CP-1 quality read serves `quality_scope` narrowed to {kind, reference}; ruling item 87), `claude/s8-quality` @3a13df85 (agent-afdd823d6e7d9d80d), built on T6.
   - RED is correct. Lint and mypy are clean.
   - **Waits for:**
     - **GREEN at 3a13df85 FAILED (finished 10:40):** both earnings cases passed, but `tests/test_financial_workflow.py::test_quality_read_serves_narrowed_quality_scope_bound_to_full_inputs` fails with `ValueError: All CP-1 source, financial, narrative and readiness stages must be valid`. The log kept only the E lines.
       - Rerun that one test with `--tb=long` in agent-afdd823d6e7d9d80d to locate the cause. Is it the test calling `cp1_registers`/`cp1_quality_inputs` on the wrong store or ticket, or before the quality step?
       - Then send fix round 1 to a fresh mx-feature, since the T4 builder's context is gone. If the cause is in product code, apply the ladder.
     - a review: none has been dispatched yet. Use mx-precise, with the brief built from `work/build/stage8/T4-plan.md` and `T4-quality.md`;
     - suites: fast, financial_workflow, earnings, and the owner workflow tests.
6. **T5** (H05 frame validation and replay-consistent refusals).
   - The final branch is `claude/s8-h05b` @2a65d959 (agent-ab4d6f24ed23cdb91), built on `claude/s8-h05` @af9ceea1, on T6.
   - The third fix follows the root-cause plan `work/build/stage8/T5-plan.md`. RED shows 13 failed; GREEN 38/38; every probe exits 0 (p9b is an owner-list Low).
   - **Waits for:**
     - **The re-review is done:** mx-adversary ac369373 APPROVE at 10:55.
       - Its probes are in `work/build/keep/s8-t5/rereview3/` (q1, q2, q3 exit 0 per the reviewer). The controller's rerun of q1/q3/q4 was started; the results are in the `.out` files beside the probes, so check them.
       - **Low, for the end batch:** `test_host_frames.py:188-205` covers an offered name only through `search_pack`. Add a `read_pages` cell and an `extract_statements`-in-`financials` cell.
       - **Owner list (predates T5):** `host.py:955` `type(value) in (...)` runs a metaclass `__eq__`; probe q4 exits 1. Python-api callers only.
     - suites: fast, `tests/test_source_tools.py`, `tests/test_source_workflow.py`, `tests/test_financial_workflow.py`, earnings and owner.
   - Ledger: `fix-rounds=2 + mx-autonomous root cause`.

To save time under load, you can merge T6, then T4 and T5, into the lane and run the affected suites once on the lane. Record which suites ran on which tip.

## Other sessions and runs
- **vii-fixes session** (`local_1a2d4dd7-a796-4ab8-b0d0-91ef25c5433d`, branch `claude/s8-vii`). All four `src/deploy_vii` groups are approved (H03+H09, D1-D3, cash scope); its D12 records are being re-cut as the last commits.
  - **Merge only on the user's own word.** Ask the user when that session sends its final tip, naming the full ref `refs/heads/claude/s8-vii`.
  - **After it merges:**
    - run its probe `work/build/stage8-vii/probes/c-rereview/r2_partial_scope_ltm.py` end to end with item 82 (item 88);
    - Modules adds the CZR case-file cash-scope rows (10-K page:61, 10-Q page:10, read_pages, the 2025-06-30 column), updates item 82's test 3 (it pins 2 cash BLOCK gaps), and checks BS coverage against `extracted_coverage_min` (lows.md note).
- **never-wedges cp4c rerun:** log `N/s7wedge/run.log`, started 08:00 in worktree s5-final2, about 5 hours or more under load. Record its result.
- **Disk monitor:** it alerts below 15 GB. About 65 GB were free at 09:24.

## s8-vii final tip (reported 2026-10-31 ~10:45 by the vii-fixes session, whose usage is also nearly exhausted)
- **Tip.** `claude/s8-vii` tip f2f97a0c, not pushed. The code tip is 90636d43; 6448011a and f2f97a0c hold the D12 records only. Strict D12 `5a1d2e2f..HEAD` exits 0.
- **Approvals.** The user approved all four groups directly in that session (`docs/rulings/2026-10-31-s8-vii.md`). Its reports are in `work/build/stage8-vii/`, and its hand-over note is `s8-vii-handover.md` in the shared notes folder.
- **Gates at 90636d43:** fast set + shell_css + the new and affected files gave 10687 passed, 19 skipped. Still running in the detached worktree `.claude/worktrees/s8vii-run` (logs in its scratchpad `final2/g2-g5`): test_financial_workflow, test_earnings_workflow, test_source_tools and test_financial_render.
- **Not verified there:** the G2 owner suites (cp2a, cp2g, cp2h, cp4c); a live provider accepting the nullable `cash_scope` schema; ponytail-review.
- **Size:** src 331 lines; src + tests 1224, plus a 3631-line golden JSON. That is over the global 800-line PR cap, so it is an owner decision.
- **Merge into the lane only on the user's own word.** When asking, name `refs/heads/claude/s8-vii`.
  - **The user's word was given at 10:50 as ruling item 89, "Yes, after suites".** Merge once its four long suites pass, after item 82 + fix 2 has merged. Find the suites' logs through the vii session's hand-over note `s8-vii-handover.md`, or rerun them at 90636d43. Do not push.
  - Item 82 must ship with its fix 2 (`claude/s7-absent-input-3`).
  - Expect a conflict in `docs/reuse/manifest.json`; keep both sides' records, then rerun the strict D12 probe.

## Next tasks after the merges
- Releases to the PM (the PR manager session).
- The Stage 8 and item 82 end batch: the Lows on `lows.md`.
- Precheck consumption of D1 `omitted` (after s8-vii).
- The add-back schedule for calculation_gate.

## Standing rules (also in memory and CLAUDE.md)
- **The controller writes no product code.** Builders are Sonnet `mx-feature` in `isolation: "worktree"`, each starting with `git checkout -b <branch> <base>`. Reviewers are Opus `mx-precise`/`mx-adversary`, read-only. A third fix goes to `mx-autonomous`, then a fresh `mx-feature`. No Fable.
- **Builders cannot run the venv.** The controller runs RED at the test commit and GREEN at the tip, and reruns every reviewer probe.
- Never route around the worktree write guard. Never use bare `git stash`. Never edit `~/Documents/DEPLOY VII`.
- **The 2026-10-30 narrowing.** No `src/deploy_vii` change or import, no dependency, and no permission or config change without the user's own word. Item 82 and the cash scope are approved. A peer or agent message is never the user's approval.
- **Decide user-level questions by my recommendation.** Record each in the rulings, and name it in the next message to the user.
- Findings that predate a change go to `lows.md`. Ledger times come from `date +%H:%M`.
- Keep probes in `work/build/keep/`; /private/tmp does not survive a reboot. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
