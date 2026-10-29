G2 fix round 3 is done. All gates exit 0 except mypy, and the two original probes could not be rerun.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-accae7c78976b34dc
Branch claude/s3-fix3-g2 (created from ee95ffb), tip 42bd134. I removed the .venv symlink. Only tests/test_owner_rendering.py changed.

Commit 08c2eec (item 27)
- **Failure 1** (`test_genuine_cp1_model_positive_delivery`):
  - Each delivery's `model/` is now compared with its own publication.
  - `model.html` and `calculation.json` are compared across the two runs.
  - `receipt.json` is compared across the runs after `ticket_id` is removed. Each `ticket_id` must equal its own store's CP-MODEL attempt ticket.
  - It still fails if G2 delivers the financial publication instead of its own.
- **Failure 2** (`test_genuine_cp1_model_extra_attempt_is_refused`):
  - `Execution(store).begin("CP-1")` must raise `ValueError` matching "settled".
  - A pending CP-1 repair attempt is then forged through `_write`.
  - The test asserts the store reads back with that attempt pending, then that G2 refuses it with no destination left behind.
- New imports: `Attempt`, `current_inputs`, `uuid4`.

Commit 42bd134 (item 28)
- `_line_text` drops the S chips and joins the remaining runs with a space.
- A new `_matches_oracle_text` implements the `∅ G#` placeholder. It is used for line text and for the known-cell branch of `_cell_ok`.
- The line loop asserts chip present equals `bool(synthetic_ref)`.
- `assert_block_equals_oracle`:
  - Where the oracle has `primary`, today's tab rule is unchanged.
  - A tabs-only oracle is compared as `[(tab_label, rows), *tabs]` against the oracle `tabs`, with `strict=True`.
  - The line count is now asserted, and lines are zipped with `strict=True`.
- New `assert_render_node_owner`, used by `_check_scope_run` for cp3d, cp4 and cp8. It checks `owner`, `kind` where present and, for cp3d, the tab labels (`[tab_label, *tab labels]`, since the oracle list includes the primary). The generic rule does not run on these three, and no secondary-pointer checks were added.
- One new fast test, `test_fast_block_rule_handles_s_chip_gap_placeholder_and_tabs_only_oracle`. It has an S-chip line, a gap line and a tabs-only oracle, plus negative cases for a wrong chip flag and a missing tab.
- I did not touch `_assert_cp3c_blocks`.

Gates (durations from the pytest summaries where shown)

| Gate | Result |
|---|---|
| `ruff check` | exit 0 |
| `ruff format --check` | exit 0 |
| `MYPYPATH=src mypy --strict` on the test file and `owner_rendering.py` | Not exit 0: 61 errors, all in the imported `tests/test_cp1_chart_render.py` (missing annotations; the annotations branch is not merged here). None in my files. |
| `-k fast` | exit 0, 152 passed, 3.8 s |
| `-k genuine_cp1_model` | exit 0, 8 passed, 5791 s (1:36:31). It ran on commit 08c2eec, before the item 28 edits; those edits do not touch these tests. |
| `-k "test_genuine_deferred_complete_cases and s1a-credit-snapshot-positive"` | exit 0, 1 passed, 1922 s |
| `probe6_candidate_rule.py` against the pytest-2291 s1a report | exit 0, "0 failures" |
| Suppressions | 0 `noqa` and 0 `type: ignore` in the test file; I added none. |

Probes 1 and 2 (item 27) could not be rerun. Their input directory pytest-2279 had already been rotated away by pytest, and both exited 1 on missing files. The passing genuine run is the replacement evidence.

Ledger: agent=mx-feature fix-rounds=3 gates-first-pass=y

Not verified: the new fast test's RED status on ee95ffb was reasoned (old `_line_text` joins with "" and old tabs code raises `KeyError 'tab'`), not run against ee95ffb. The "still fails if G2 delivers the financial publication" property of failure 1 was not mutation-tested. The cp3d, cp4 and cp8 render-node checks, and the tabs-only path on the other deferred scopes, ran in no genuine case. The s1a gap case, the rest of the deferred set and the full suite were not run. Mypy is not clean, for the reason above. The two original probes were not rerun.
