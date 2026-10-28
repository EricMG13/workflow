# CP-8 round 6h report (controller-saved from the implementer's hand-back)

# CP-8 round 6h report (with the re-pin)

Round 6h is applied test-first and committed as `cba7f82`, on top of fix 1 (`9f2b2f5`). No `_unpinned` raise remains: the last one is replaced by the ruled row and the unused helper is deleted. All 144 tests pass, and every gate exits 0.

## Commits (branch `worktree-agent-a3cc9818386e8861a`)

| Commit | What it is |
|---|---|
| `be3a09f` | Merge of `claude/module-dev-status-review-0981b6` (rounds 6h, 7, 6i, 8 and the CP-1D fix). No conflicts; `cp8.py` and the test were untouched by it. |
| `5fc0d81` | Cherry-pick of LEAD's `2682310` (CP-5 lease; cp3-cp6 R6; CP-8 re-pin). Clean. |
| `cba7f82` | "feat(cp8): apply LEAD round 6h (split quotation beside a missing side)", ending with the Co-Authored-By line. Only `cp8.py` and `tests/test_method_cp8.py` changed. |

Files:
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/src/deploy_workflow/owners/cp8.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/tests/test_method_cp8.py`

## Pins (`shasum -a 256`, after the cherry-pick)

| File | Value | Change |
|---|---|---|
| `cases/cp8-owner/builder/build.py` | `4c8304f6cfc5b8c10dc910e87cf9cfa6b85f1e108fa958fbac2a4ecc0eeef736` | Was `8b98e0374daab59af36fc5f199eb6623a5ba6a2a6ac77b3e683b042699fb771a`; matches LEAD |
| `cases/cp8-owner/manifest.json` | `365c751c0b02d69bea132b24b89ce3ddade8ba9da5af5a2b3132403ff0021b35` | Was `270d2bb0ae56d69da80c5aac3cc97a33f5bb5131499744288c4c1f5ee3d2aacd`; matches LEAD |
| `cases/cp8-owner/submissions.json` | `5112fe69502ad3451aeab409ce7bb0d183d3c09838bf2987bc04fe9cb0b1af9b` | Unchanged |
| `cases/cp8-owner/expected.json` | `3382e7adc47b808939ad2ca0be61a889b5e5be45694dd8f987f701bb478e3e0d` | Unchanged |

- Neither of my files pins the builder, the manifest or a methodology sha, so nothing there moved.
- The `docs/CP8-OWNER-LEASE.md` header is LEAD's own re-pin, which came with the cherry-pick. I made no oracle edits.

## Ruling and its test

**Round 6h CP-8:** `test_6h_one_side_split_and_the_other_missing`, parametrised over both directions. Red first: both cases raised `_unpinned("a loan_mid row with a split and a missing side")`.

| Direction | Second clause of the follow_up |
|---|---|
| Expected split, realized missing | "supply a dated post-decision source that states the quotation" |
| Realized split, expected missing | "cite the expected quotation from the Prior Case record" |

The test asserts:
- the five T7.8 `not_compared_loan_mid` fields, with the side names filled in;
- the T7.4 cells per 8-7 and 8-1/8-2 (the split side's dated reason, the missing side's reason, direction not calculable);
- the unchanged "Measures not compared" limitation;
- the T7.3 bid row per 6c (a): missing with "dealer bid" when the realized side is missing, known otherwise.

The two earlier fail-closed tests for this state are now this live test.

## Mutants

`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r5/mutate_r5.py` exits **0**: 44 of 44 mutants killed, plus the control.
- It runs from a full temporary copy, with a baseline check and a control mutant.
- New 6h mutants:
  - split beside missing takes the split-only row;
  - sides swapped in missing_item;
  - the follow-up clause of the split side;
  - why_it_matters naming one side only.
- One anchor was updated (`if split:` is now `elif split:`). A first run, before that fix, exited 1 on that stale anchor alone.

## Gates (both files)

All three exited 0 on their first run.
- `ruff check`
- `ruff format --check`
- `MYPYPATH=src mypy --strict`

`ruff format` had reformatted the test once before the first check. pytest: 144 passed.

The worktree guard refuses the `PYTHONPATH=src "<abs venv>/python"` form, so I ran `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp8.py`: the same interpreter, with pyproject's `pythonpath` supplying `src`.

## Prose and bare-figure hits

`probe_prose.py` exits 1. It now covers both 6h scenarios and checked 71 new strings.
- **The one hit:** the 8-3 rails line "Total leverage was recorded at 1.67x and is now 1.67x, unchanged." gives `Bare figure: 1.67x`. Round 6c already rules rails text outside the claim check.
- **Clean:** every round 6h string, in both directions.

LEAD's round 9 items ("to LEAD" 1–5) are untouched.

Not verified: no frozen oracle case reaches the 6h state, so the expected strings come from the ruling text alone, and the realized split relies on my longer verbatim span of the frozen market page; T7.8 cells are table text, so only `bare_figures` was applied to them, not `prose.issues`; the reviewer's p01–p12 probes were not re-run this round.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
