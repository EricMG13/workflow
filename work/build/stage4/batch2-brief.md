# Stage 4 batch 2: CP-8 rails gap chip, class E (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit:
1. Run `git checkout -b claude/s4-batch2 4c69ebc` (`claude/s3-cp3c-driver`: G2 with its fix rounds 1-2, plus the CP-3C fixes).
2. Run `git merge --no-ff f80d2d3` only if `git merge-base --is-ancestor f80d2d3 4c69ebc` fails.
3. Run `git merge --no-ff claude/s4-cp8-oracle` (f4d1f93, the frozen CP-8 oracle). If `cases/PINS.json` conflicts, regenerate it with `python3 -I cases/pins.py`.
4. Confirm the tip.

Edit only `src/deploy_workflow/owners/cp8.py`, `src/deploy_workflow/owner_rendering.py`, `tests/test_method_cp8.py` and `tests/test_connect_cp8.py`. Do **not** edit `tests/test_owner_rendering.py` (another fix round is editing it), `cases/`, `src/deploy_vii/` or a lease.

## Inputs
| Item | File |
|---|---|
| The plan (follow it) | `L/work/build/stage4/plan.md` §5 and §6 batch 2 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` item 19 (E1: resolve in `owner_rendering.py`; E2), item 21 (frozen oracle and the RED-test rule) and item 29 |
| Oracle review (the RED-test rule) | `L/work/build/stage4/cp8-oracle-review.md` |
| How claims resolve chips | `src/deploy_vii/report_view.py` around :1050 (`ClaimRun(kind="gap", ref_id=item.gap_ref)`), read only |

## Process (test first)
1. Write the RED tests first and confirm they fail:
   - `tests/test_method_cp8.py::test_no_settled_cp8_fact_carries_a_gap_placeholder_literal`, under the item 21 rule: product facts only, with a guard against a vacuous pass;
   - a render test next to `tests/test_connect_cp8.py::test_the_what_changed_block_is_cp8s`: the outcome cell shows `∅ G<n>`, where `n` is the gap reference the page gives `T7.3.window.realized_value`; the positive case shows the window figure unchanged.
2. In `cp8.py`:
   - `_what_changed` stores the claim's token text;
   - `_resolved` stays for known figures only;
   - remove `GAP_PLACEHOLDER`.
3. In `owner_rendering.py`, resolve that cell's token into runs against the module's facts and refs, using the same rule `report_view` uses for claims:
   - a known fact gives its figure;
   - a gap fact gives the page's `∅ G<n>`;
   - a token that names a fact outside the module fails closed.
   If this cannot be done in `owner_rendering.py` without editing `src/deploy_vii/`, stop and report. That decision goes to the user.
4. Update the `tests/test_method_cp8.py` comparisons as item 21 says. `oracle_cell` compares this known fact's `text` directly.

Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `pytest tests/test_method_cp8.py tests/test_connect_cp8.py tests/test_connected_render.py`;
- `tests/test_owner_rendering.py -k fast` (run only; do not edit);
- `python3 -I cases/pins.py --check`;
- `ruff check` and `ruff format --check` on the changed files;
- `MYPYPATH=src mypy --strict` on `cp8.py` and `owner_rendering.py`;
- suppressions noqa ≤ 13, type: ignore ≤ 5;
- the plan's E2 grep (`∅ G#` in any known fact `text` or `shown` across `cases/*-owner` runs);
- **Deferred:** `tests/test_owner_cp8.py`, listed as an exact command.

## Outputs (return as text, at most about 1k tokens)
Worktree path and tip SHA; the changes; RED evidence; gate exit codes; deferred commands; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
