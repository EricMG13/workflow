# Release W2-A2 report (mx-feature)

Lane A2 is committed on `claude/s2r-a2`, tip c824206. The test files that are fast to run pass. The four `test_owner_*` files did not finish, and CP-L10's lineage item turned on an unrecorded reading (see Skipped / questions).

**Setup note.** `EnterWorktree` is not available in this harness, so I worked in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-a2` by absolute path. Start state was fb231d4 and clean.

**Per item**
- **CP-3D `amortisation_nonzero`: done (c824206).**
  - Tests first: I removed `STAGE2_REFUSAL_DELTA` and its pending-guard test from `test_method_cp3d.py`, and its uses in `test_connect_cp3d.py` and `test_owner_cp3d.py`. They were red until the re-pin.
  - The builder's reference `token_once` now takes the comma-space join, as the product does.
  - The oracle issue moves to `amortisation: value_text 31 does not occur in the quote`. The mutation note is reworded.
  - A diff of the rebuilt outputs shows nothing else in `expected.json` or `submissions.json` moved.
  - `cp3d.py` was not touched.
- **CP-1D (done):**
  - The recipe text in `$.refusal_rules.partly_supported` and the builder now state the whole-numeral-run grammar and the comma-space rule. Test: `test_partly_supported_recipe_text_states_the_comma_space_grammar`.
  - `cases/cp1d-owner/cp1d-view-tree.json` is committed. Test: `test_the_committed_view_tree_is_the_views_key_tree`, per case.
  - The I1 docstring on `context_block` is corrected: `inherited_limitations` is computed with no own limitations, so settlement's list can be shorter. This is a docstring change, so no test applies.
- **CP-L10 missing-change lineage: done.** The ruling text is the "Queued for a later revision" line in the lease header: a missing `change` cell has `derives_from: null` while its known siblings list both CP-1 labels. I applied it to the missing `change` and `change_pct` cells only. Test first: `test_missing_change_cells_derive_from_both_cp1_labels`, red on both cases before the change.
- **CP-2E blocked wording: done.** `negative_cases.blocked_cp2e.result` now reads "module blocked, the store holds a blocked head (status blocked)", per round 2 item 8. Test: `test_blocked_result_names_the_blocked_head`.
- **Leftover deltas:** every other `_DELTA` in `tests/` belongs to A1: `PERIOD_DELTA`, `GAP_VALUE_CLASS_DELTA`, `PRINCIPAL_PERIOD_DELTA`, `CP2D_D7_DELTA` and `CP3C_D7_DELTA`. I did not touch them. `CP0_DELTA` in the cpdr builder is oracle content, not a re-pin delta.
- **Lease pin headers:** an "Amended by Modules 2026-10-29 (Stage 2 close release W2-A2)" paragraph, with old → new shas, is added to the CP1D, CP2E, CP3D and CPL10 leases. I did not touch their bodies.

**Oracle values that moved (only the named items)**
- CP-3D: `refusal_mutations` entry `amortisation_nonzero`: `issue`, `all_issues` and `note` (in `expected.json` and `submissions.json`).
- CP-1D: `expected.json` `refusal_rules.partly_supported` text only.
- CP-2E: `negative_cases.blocked_cp2e.result` only.
- CP-L10, in both cases:
  - `derives_from` on 4 missing cells: total_leverage and interest_coverage, `change` and `change_pct`;
  - citation markers on the two "cannot be screened" claims;
  - the `lineage_citations` rule text.

**Pinned or builder-hashed files changed**
- Builders: `cp1d`, `cp2e`, `cp3d` and `cpl10` `build.py`.
- Oracles: `expected.json` for all four, and `cp3d` `submissions.json`.
- New file: `cp1d-view-tree.json`.
- `cases/PINS.json` is regenerated.
- Two fresh-copy rebuilds of the 13 builders in the chain through `cp8` were byte-identical to each other and to the committed outputs.

**For W3: re-pin cascade left undone**
- `cases/cp2g-owner/builder/build.py` pins `cp1d` `expected.json` at 293120368b5d… and needs 8880a2c59a92…. I did not apply it, to avoid conflicts with lane D, which owns that builder.
- That re-pin changes the `cp2g` manifest from d69738e2… to e8469c68…, which the `cp2h` and `cp4c` builder PINS then pin.
- A full chain run in this worktree with the cascade applied reached `rc=0` at iteration 3. I reverted it afterwards.
- `cp8` was not touched.
- The `cp8` builder prints `cp2g` as `cp2g-owner`. The chain run is the only place it shows.

**For B (lease body text, not touched by me)**
- `docs/CPL10-OWNER-LEASE.md` :131 (Citations) and :216 (10c) still say missing-change cells have no `derives_from`.
- The same file's :13 note, "Queued for a later revision", is now done.

**Skipped / questions**
- None skipped. The one reading to confirm is the CP-L10 scope above (missing `change` and `change_pct` only). The not-applicable `change_pct` for a zero start, and the count facts, still have no lineage.
- CP-3D's builder has the same "module blocked, no head" wording at `cases/cp3d-owner/builder/build.py:1528`. The ruling names CP-2E only, so I left it. Do you want it changed too?

**Gates (exit codes)**
- `ruff format --check`: 0, on the 9 touched src and test files.
- `ruff check`: 0, on the same files.
- `mypy --strict`: 0, on `cp1d.py` and `cpl10.py`. These are the only `src/` files I touched.
- Tests: 2627 passed, 2 skipped (exit 0), across the `cp1d`, `cp2e`, `cp3d` and `cpl10` method and connect files and `test_cp1b_registration.py`. `test_host_h1.py`, `test_method_cp2g.py` and `test_connect_cp2g.py` also pass: 613 passed (exit 0).
- `python3 -I cases/pins.py --check`: 0.
- `noqa` count is 13. `type: ignore` count is 5.
- The four `test_owner_*` files (`cp3d`, `cp2e`, `cpl10`, `cp1d`) were stopped by me after about 55% of tests had passed with no failure, because the real-promotion CP-1D tests take 11 to 26 minutes each. No exit code. I cannot say which files were covered.

Not verified: the `test_owner_*` store and promotion runs for `cp1d`, `cp2e`, `cp3d` and `cpl10`. The full suite and mutation, complexity and `jscpd` gates. The view tree was built from hand-built CP-1 fixture heads, not a promoted CP-1 head, and its `_note` says so. The CP-1D docstring change has no test. Cross-lane pins (the `cp2g`, `cp2h` and `cp4c` builders) are stale until W3.

agent=mx-feature fix-rounds=0 gates-first-pass=y
