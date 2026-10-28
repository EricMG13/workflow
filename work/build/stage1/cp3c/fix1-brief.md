# CP-3C fix round 1 (after the first adversary review)

Review: `work/build/stage1/cp3c/review-adversary.md` (lane worktree). Reviewer probes: `<S>/cp3c-adversary/` (P below), `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Re-review: mx-adversary by finding id.

## Step 0
`EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287")`, then `git merge claude/module-dev-status-review-0981b6` (lane: rounds 9 and 10). Report conflicts; resolve none outside your two files (a `docs/CP4C-OWNER-LEASE.md` header conflict takes the lane's version). Round 10 puts CP-3C outside the sign class: no change for it.

## Fix (test-first; red seen for the reported cause)
1. **M1.** A facility maturing before D0 gives negative months and sign-flipped amortisation, flow and balloon (`cp3c.py:511-515`, `:569-577`, `:591`, `:799-803`). No ruling covers it. Fail closed: a `ValueError` invariant naming the facility and both dates, raised before any figure is formed. No user wording. Case: `P/probe_past_maturity.py` (it encodes the reviewer's expectation; report its exit code and whether it now checks the raise). Listed for LEAD.
2. **M2.** `prose.check` at `:1628-1632` runs without `names`, so a facility id with digits (`tl2`, `tla1`) makes `compute` raise. Pass the facility ids as `names=`. Case: `P/probe_digit_id.py`. The same names are needed at Stage 2 MC-2: list it as a Stage 2 note.
3. **M3.** Tests that kill A13 (positive CP-1 cash interest), A18 (maturity exactly on the horizon in `_facility`; frozen 2027-12-31 with H = 24), A25 (own-line order: currency, maturity date, principal), A39 (USD facility with no principal plus a EUR facility). Runner: `P/mutants.py`. State: `P/probe_survivor_states.py`.
4. **Lows riding.**
   - L1: T3D.5 Base takes the largest rank's claims (`max`), as the lease, `method_rules.lme_capacity`, the builder and the cell's formula text say (`:644-645`). Case: `P/probe_negative_principal.py`.
   - L2: correct the precision comment (`:62-65`); the builder runs at `prec = 60` (`build.py:19`). Compute under the builder's precision if every frozen value stays equal; if any moves, keep 28, fix the comment only, and report it. Case: `P/probe_precision.py`.
   - Optionally kill the Low survivors A33, A34, A40, A35, A36, A37, A41, A42, A45 where a test is cheap; one line each for any left.

Not in this round (to LEAD): the reviewer's items 1-6 (8-B3 scope for unstated terms, empty register vs unmatched, BURDEN-01 collision, blank limitation, negative principal/amortisation, unknown flag under NOT_STATED).

## Rules
- Files: `src/deploy_workflow/owners/cp3c.py`, `tests/test_method_cp3c.py`. Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Gates (exit 0): `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp3c.py`; `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files. Nothing else.
- Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`.
- New strings: none expected beyond the invariant text; run `prose.issues` and `bare_figures` over any and report hits.

## Report (as text)
Commit; finding → test; exit codes of `probe_past_maturity.py`, `probe_digit_id.py`, `probe_survivor_states.py`, `probe_negative_principal.py`, `probe_precision.py`, `mutants.py` (survivors left with reasons); gates; Stage 2 notes; `Not verified:`; ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
