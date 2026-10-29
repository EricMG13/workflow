# CP-3C round 6 report (controller-saved from the implementer's hand-back)

CP-3C round 6 is done: A1 and A5 are applied and the oracle-batch pins are updated. All tests, gates and probes exit 0.

**Commit:** `9e78d63` on `worktree-agent-aa5a4817fa00cd287`. Only two files changed:
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287/src/deploy_workflow/owners/cp3c.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287/tests/test_method_cp3c.py`

My round 5 commit `196b174` is still on the branch.

**Step 0:**
- `git merge bdad3c8` gave merge commit `31aa699`, with no conflicts.
- `git cherry-pick 8483de4` gave `70ca1a5`.
- `git cherry-pick 3674158` gave `3a3b068`.
- The file shas now match the coordinator's: manifest `7a0056a1…`, builder `b2cdb63c…`; expected `50ef4a7f…` and submissions `8c2b08fa…` are unchanged.
- I re-pinned only those two values in `PINS`, with no oracle edits.
- The manifest's `frozen_inputs` check passes against the new CP-2D expected (`0f07bc75…`) and CP-2D builder (`c274ce84…`).

**Rulings and their tests:**
- **A1:** months is now the largest n with `add_months(D0, n) <= maturity`. `wall_position` changed, so amortisation × months / 12 uses the new value too. C-4's `(maturity_date, facility_id)` order is unchanged. Tests:
  - `test_a1_months_are_the_largest_n_with_d0_plus_n_on_or_before_the_maturity`: Dec 31 to Jun 30 is 30 months, superseding lease note :218.
  - `test_a1_wall_position_over_every_day_of_four_years`: a sweep over four D0s (including month-end and Feb 29) and four horizons, checked against the test's own month arithmetic. It checks D0+m ≤ maturity < D0+m+1, inside exactly when maturity ≤ D0+H, and A1's scope (months < H is inside, months > H is outside).
  - `test_a1_amortisation_runs_for_the_largest_n_months`: a 2028-06-30 maturity at 12 a year amortises 30, not 29, and CP-2D's 30 months agree with the recomputed position.
  - All three failed against the old day-of-month rule before the fix.
- **A5:** this round has no behaviour change for it, so I wrote no failing test first. `FacilityTerms.currency` is documented as the T4.18 row's own `currency` text fact, never read through `_maturity_figure`; this amends C-7. The `_facility` comment cites A5. `test_c6_a_facility_in_another_currency_uses_the_2d5_wording` now states the A5 point: the non-USD case is reached while the CP-2D wall principal is missing. The facility name was already the T4.18 `facility_name` text fact.

**Probes** (scripts in the scratchpad):
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/mutate.py` exited 0. All 17 hand mutants were killed, including two new A1 ones (the old day-of-month rule, and `>` changed to `>=`). The source was restored by sha.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/prose_probe.py` exited 0 with no hits outside the Stage 2 citation class.

**Gates:** pytest gave 132 passed. ruff check, ruff format --check and `MYPYPATH=src mypy --strict` on both files all exit 0, each on the first run.

**Prose and bare-figure hits:** none. This round adds no user-facing strings, only docstrings and comments.

**Points for LEAD:**
- A frozen CP-2D months cell computed under the old rule would now trigger the C-6 wall-disagreement line for a maturity like Dec 31 to Jun 30. No frozen case has such a maturity: per the ruling, all frozen maturities give the same months under both rules.
- A T4.18 row with no `currency` fact is still unruled for CP-3C. The Stage 1 input type requires a string, so the Stage 2 reader has to fail closed there.
- My round 5 choices ("For LEAD" 1–7) are kept as built.

**Stage 2 notes:**
- The T4.18 reader takes `currency` and `facility_name` by `facility_id` from the row that gives the principal. It applies the manifest's QUARTER-over-FY selection without calling `_maturity_figure`, which raises on non-USD (A5).
- The round 5 notes still stand: `methods/cp3c.md` records the T3D.7–T3D.9 headers (C-4) and the trace locator (C-5).

**Not verified:**
- The Stage 2 T4.18 reader for currency and name (A5).
- A1 against a CP-2D head built by the round 6 CP-2D code.
- A1's amortisation effect on any frozen case, since none has a non-month-end maturity.
- Everything listed in round 5: Stage 2 bindings, `prose.issues` with citations, "shows both", `cites_from` for unmatched facilities, the repo-wide suite, mutmut (mutation was by hand), and size.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
