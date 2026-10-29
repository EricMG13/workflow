STOPPED at step 3 of the brief. No edits and no commits other than the merge. This decision goes to the user (the E1 choice).

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a7e48f47956c9ff2e. Branch claude/s4-batch2 is at tip 766ca1e. That is 4c69ebc plus the `--no-ff` merge of claude/s4-cp8-oracle (f4d1f93). `PINS.json` merged without conflict. f80d2d3 is already an ancestor of 4c69ebc, so I did not merge it. I made no `.venv` link.

Why the brief's step 3 cannot be done in `owner_rendering.py`:
- `owner_rendering.py` does not render the block. `_capture` calls `core_render.render(view)` and `report_view.build(view, pathway, SHIPPED_MAPS)`.
- It then requires `payload_blocks[id] == _expected_block_payload(block)` in `_sections`. It only verifies the page against the facts.
- The `what-changed` block is a prose block. `report_view._prose_lines` (~:1600-1640) emits a known text fact's `item.text` verbatim, as a `text` run.
- With the token stored in the fact (`[T7.3.window.realized_value]`), the page would show the raw token. The page and its payload come from `src/deploy_vii` (`report_view.build` and `render`).
- A resolve step inside `owner_rendering.py` would either not change the page, or would mismatch the payload equality check. Making it match would mean patching the rendered HTML and payload as strings, which I rejected as a workaround.
- Real resolution needs `_prose_lines` to call the public `report_view.resolve(text, bound, refs)` (:1103) for a known text fact that carries `[...]` tokens. `resolve` already gives the gap as `ClaimRun(kind="gap", ref_id=G<n>)`, and it fails closed on `prose.issues` findings. That edit is in `src/deploy_vii/`, which the brief forbids.

Reads of CP-8 files (no gates run):
- `cp8.py` `_resolved` and `GAP_PLACEHOLDER` (:104) are as the plan describes (:2156-2174).
- In the frozen oracle, `cp8.what_changed.outcome.value` has `text` equal to the token form, `shown` equal to `∅ G#`, and `claims[0].resolved` containing `∅ G#`.
- The oracle review found no E2 hits outside CP-8.

Decision for the user (E1):
- Option A: allow a `report_view._prose_lines` edit, so a known text fact with tokens is resolved via `resolve`. Batch 2 would then also touch `src/deploy_vii/`, and `report_view` tests would need to move.
- Option B: keep the placeholder literal. This is the fake the ruling names, so I do not recommend it.

If the user chooses A, I can run the whole batch: the RED tests, `cp8.py`, `tests/test_method_cp8.py` and `tests/test_connect_cp8.py`. I need the extra file scope named.

RED tests, gates and the deferred `tests/test_owner_cp8.py` command: none written or run.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n/a (BLOCKED at step 3).

Not verified: all gates, the RED tests, the claim that no other `owner_rendering.py` route exists beyond the one I read (`_capture` and `_sections`), and the pytest effect of the merge.
