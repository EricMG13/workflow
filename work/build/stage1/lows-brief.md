# Stage 1 riding Lows: one test-only batch

These are the Low and Info test gaps that reviews left to ride with the next change. The code is judged correct in every case, so each item is a test that kills a surviving mutant or pins accepted behaviour.

If a new test fails against the current code, that is a code defect. Stop and report it, and do not fix it here.

Review: one mx-feature review of the whole batch, checked against each reviewer's probe.

## Step 0
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/stage1-lows")`. The branch is `claude/stage1-lows`, cut at lane 76b13f0.
2. Confirm HEAD = 76b13f0, or a later docs-only lane commit merged with `git merge --ff-only claude/module-dev-status-review-0981b6`. Confirm `git diff 76b13f0 HEAD -- src tests cases docs/rulings` is empty. If either check fails, stop.

## Items
`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

Each review file is in `work/build/` and names the probe and the mutant.

| # | Module | Source | Test to add | Kill or pin |
|---|---|---|---|---|
| 1 | CP-2D | stage1/cp2d/class-review.md Low | A facility in EUR that matures before D0: T2E.3.r07 takes the FX reason. | `<S>/cp2d-class-review/mutants_review.py` "schedule: pre-D0 before currency" |
| 2 | CP-2D | stage1/cp2d/round5-6-review.md L1–L6 | One test per item, as the table there describes. First run each item's mutant at the lane tip. If it is already killed, say so and skip it. | the K-mutants named there (`<S>/cp2d-r56-review/` or the path the file gives) |
| 3 | CP-8 | stage1/cp8/class-review.md Low-1 | `assert not cp8._on_page("1.25", "1.25 -1.2", "1.25 -1.25 -1.2")` in `test_r11_b1_every_occurrence_of_the_quote_on_the_page_is_read` | `<S>/cp8-class-review/p_overlap_mutant.py` |
| 4 | CP-8 | same, Low-2 | Add `thesis.exit_trigger.absence.{reason,follow_up}` to the blank test, through an adapter that sets an absence. | `p_blank_exit_trigger.py` |
| 5 | CP-3D | stage1/cp3d/class-review.md L2, I1 | Accepted: an unwrapped quote that prints `Acme first- priority Term Loan` keeps that name. Accepted: a wrapped quote keeps `Acme Term Loan B-2`. Pin: `_whole_on_page("5", "5 .5", "x 5 .5 .5")` is False. | `<S>/cp3d-class-review/p_survivors.py` and the reviewer's R mutants in `<S>/cp3d-class/mutants.py` |
| 6 | CP-2E | stage1/cp2e/class-review.md L2, L3 | L2: an accepted twin where only the joined page reading holds the figure (the b1 page). L3: pin c1 and c3, so that `""` and `"  "` on a non-Insufficient-Information limitation get `assessments[0].limitation: empty text`. | `<S>/cp2e-class-review/mutants_extra.py` survivors "plain page spans only" and "limitation only when II" |
| 7 | CP-4C | stage1/cp4c/round11-review.md L1, L2, Info pins | L1: an issuer name with a digit, used in a class name. L2: a class name such as `Term Loan B-2` or `Q1 Notes` is accepted. Info: pin the :541 known-without-amount raise, and EV's reason first when both are unknown. | `<S>/cp4c-r11-review/mutants_review.py`: `b3_names_dropped`, `b3_lower_class_names_too`, `b2_debt_known_without_amount_settles`, `b6_cp1_reason_before_ev` |
| 8 | CP-2H | stage1/cp2h/fix1-review.md N1, N2 | N1: change `SOURCE_BREACHES["threshold_unit"]` to `Below  10.00x`. Grammar-valid with the wrong unit is still refused as before. N2: add `.75x`, `.5%` and `-10.0%` to `THRESHOLD_FORMS` as refused. | M14, M5, M6 and M7 in `<S>/cp2h-fix1-review/spec_review.py` and `n1_unit_check_unpinned.py` |
| 9 | H1 | h1/h1b-review.md Low A, Low B, Info 1–2 | A: every row test checks one shared `outside` universe (every id any row or case names, plus `business`, `board_minutes`, `market` and `bridge`, minus the row's leased ids). B: give the L3 `late` source a sha256 and a page span. Info: fix the host.py:48 comment and the test :340 comment (eight owner-only modules). | `<S>/h1b-review/p07_shared_universe_fix.py`, `p06`, `p08`, `p10` |

Item 8 changes a test input that is not frozen: `SOURCE_BREACHES` is the module's own test table. Check that it is not under `cases/`. If it is, stop.

## Rules
- **Files:** only `tests/test_method_{cp2d,cp8,cp3d,cp2e,cp4c,cp2h}.py` and `tests/test_host_h1.py`. For item 9 Info, the comment line in `src/deploy_workflow/host.py` may also change. No other src change.
- Never edit `cases/`, `tests/defect_classes.py` or `src/deploy_vii`. No stub, fake value or catch-all. Every frozen case still passes.
- **Gates** (all exit 0):
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider` on the seven test files plus `tests/test_owner_g1x.py`;
  - `ruff check` and `ruff format --check` on the changed files;
  - `MYPYPATH=src mypy --strict` on the changed test files and `src`.
- **Mutants:** run each named mutant from a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`, and report each as killed, or as already killed at the tip. Put scripts under `<S>/stage1-lows/`.
- **Commits:** one commit per module on `claude/stage1-lows`, each ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report (as text)
- the commits;
- each item, with its test and the exit code of its mutant or probe;
- any item skipped, and why;
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
