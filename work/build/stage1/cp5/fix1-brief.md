# CP-5 fix round 1 (tests only, after the first adversary review)

**Review:** `work/build/stage1/cp5/review-adversary.md`. The reviewer's probes are in `<S>/cp5-adversary/` (called P below), where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

**Re-review:** mx-precise, by finding id.

## Step 0
- `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp5-stage1")`.
- Confirm HEAD is 4e2d687. Do not merge the lane: CP-5 lands together with CP-3 and CP-8 on 2682310.

## Fix (tests; `cp5.py` changes only if a new test shows a defect)
1. **F1 (Medium).** Add tests that kill A02 and A03, the two quote-leaking mutants.
   - **A02:** a claim with two or more failing citations. Every mark is cut at `": "`, and no quote reaches the body.
   - **A03:** a blocked optional head whose citation quotes stay out of the body.
   - `P/test_adv_cp5.py` and `P/advfx.py` show working cases. Adapt them into `tests/test_method_cp5.py`; do not import from the scratchpad.
2. **F2 (Low, riding).** Add tests that kill A01, A04, A05, A06, A09 (= M14) and A11.
   - A09 needs a bound fact id that contains a `:`, as genuine CP-1 ids do (`interface-fact:<sha256>`). Build the `kind on <ref>` mark of lease step 4 with such an id.
   - Write one line for each mutant you leave, saying why.

Not in this round (these go to LEAD): controller choices 1-3; the CP-3 fact count (42/31 against the lease's 39/28); I1 (`CP5Result` allows issues and a report together).

## Rules
- Files you may change: `tests/test_method_cp5.py`, and `src/deploy_workflow/owners/cp5.py` only if a test exposes a real defect (report it if so). Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all in product code. Test fixtures must be built the way the lease builds them.
- Gates, each must exit 0. Run nothing else.
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp5.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- Run mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Rerun `P/adv_mutate_run.py` and your `mutate_run.py`.

## Report (as text)
- the commit;
- each mutant and the test that kills it;
- exit codes of `P/adv_mutate_run.py`, `P/leak_mutant_demo.py` and your runner;
- the gates;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
