The three genuine `cp3c-fp04-refinancing` cases (positive, gap_minimum_cash, gap_no_repricing) now pass, so the comparator fix works. One gate is not clean: `mypy --strict` reports 61 errors.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a84136ec315fffe56. Branch `claude/s3-cp3c-driver`, tip 4c69ebc, which adds one commit on top of 3ac979c. I removed the `.venv` link and no background process of mine is running.

**Change** (only `tests/test_owner_rendering.py`):
- New `_cp3c_wanted()` builds the expected owner, kind, state and tabs per block from the frozen oracles. An oracle block with `state == "populated"` and `collapsed` true is expected as `"collapsed"`. The rule reads the oracle's own fields and never names a block id. Any other oracle state is unchanged.
- `_assert_cp3c_blocks` now calls `_cp3c_wanted()`.
- New `test_fast_cp3c_comparator_takes_collapsed_from_the_oracle` builds a page from the oracle. It checks the comparator accepts that page. It then sets each collapsed block to `"populated"` and checks the comparator raises `AssertionError`. It also asserts at least one collapsed block exists, so it cannot pass vacuously.

**Gates**
- `tests/test_owner_rendering.py -k fast`: exit 0, 152 passed, 4 s.
- The three genuine cases: exit 0, 3 passed, 4606 s.
- `ruff check` and `ruff format --check` on `tests/test_owner_rendering.py`: both exit 0.
- Suppressions over `src` and `tests`: `noqa` 13 and `type: ignore` 5, both at the limit.
- `MYPYPATH=src mypy --strict tests/test_owner_rendering.py src/deploy_workflow/owner_rendering.py`: failed, "Found 61 errors in 1 file".
  - I only saw the tail of the output, and the errors shown are `[no-untyped-def]` in `tests/test_cp1_chart_render.py`, not in the files I changed.
  - That file is probably followed through an import. I did not confirm that none of the 61 are in the two checked files. Per the brief, I report it as is, since the annotations are not merged on this branch.

Ledger: `agent=mx-feature fix-rounds=0 gates-first-pass=y` for the fast and genuine gates. The mypy result is as stated above.

Not verified: that none of the 61 mypy errors are in the files I changed; test mutation (I did not run `mutmut`).
