# Release W2-A1 report (mx-feature)

A1 report (CP-2D, CP-3C, CP-4, FP04). Branch claude/s2r-a1, tip 3614577 (one commit on fb231d4). Tree is clean after the commit.

Environment notes:
- EnterWorktree was not available, so I worked in the worktree by absolute paths.
- The Monitor tool was not available either.
- A bare `pkill` was denied. Two background pytest processes of mine (b0pqb3gr7 and b9fimn32k) were still running at handback, both in `tests/test_owner_cp4.py`; kill them if they are still alive.

**Per item**

CP-2D:
- Stale-head oracle wording: done. `negative_cases.begin_refused_cp2_blocked.also` now says a stale required head is not a retained refusal. `begin` re-raises ValueError and consumes no attempt. A tripwire is added to `test_a_stale_required_head_is_not_a_retained_refusal`. No other oracle value encodes a retained refusal for that case.
- Gap twins T2E.5.r04 and r07: done. Both now carry currency USD. `GAP_CURRENCY`, the `twin` stand-in and the tripwire test are removed from `test_connect_cp3c.py`. A new test checks the oracle carries the currency, and `_assert_fact` in `test_connect_cp2d.py` now compares currency when the oracle gives one.
- PERIOD_DELTA and GAP_VALUE_CLASS_DELTA: both removed.
  - The oracle now carries `period` on every known numeric cell. A copy takes its CP-1 period; a computed or recomputed cell takes 2025-12-31.
  - It carries `value_class` on the five gap cells: T2E.3.r09, T2E.5.r04 (analyst_judgment), r05, r06, r07 (calculated).
  - `test_oracle_periods_are_the_manifest_periods` and `test_oracle_gap_cells_carry_a_value_class_and_the_twins_a_currency` replace the old guard test.
- "Equity repurchases is": done. It now reads "Equity repurchases are …" (`PLURAL_LABELS` in `cp2d.py`). "RCF drawings are" was already at fb231d4 via `verb()`. No frozen text contained the old wording.
- Drawings precedence (round 5 item 4): done, test-first.
  - Commitment conflicting or not applicable plus drawings missing now gives "Not calculable: RCF commitment is <state>; RCF drawings are missing".
  - That reason reaches the undrawn, available, resources, headroom and runway cells. The claims say "needs RCF commitment, which is <state>".
  - The "drawings undisclosed" forms are no longer used on that path. The pack never reaches it, so no oracle value moves.
  - Judgment call: the ruling gives no exact wording, so I chose this form. Please confirm it.
- Backlog :41-42: already at fb231d4. The sum copy (T2E.1.r05) as a dependant gap is `test_backlog_sum_copy_is_a_dependant_gap`. The balance-date rule for recomputed cells is `test_connect_cp2d.py` at ~:60 plus `RECOMPUTED_TAGS`.

CP-3C:
- Principal periods: done. The six cells (T3D.1.r01.c1 and T3D.4.r01.c3, three cases) go from 2025-12-31 to q4-2025. The builder now reads the period from the CP-2D oracle cell (`c2d_period`). `PRINCIPAL_PERIOD_DELTA` is removed.
- CP-1A: done in `expected.cp3c_module.attempt_inputs` and `manifest edges.bound_in_attempt_inputs`. `CP1A_BOUND` is removed. `test_owner_cp3c.py` now derives its bound list from the oracle.
- `fact_copy_rule` text: done.
- `frozen_inputs[8]` names: done. They are now PROHIBITED, NEAR_INSTRUMENT and INSTRUMENT_NOUN.
- `cases/cp3c-owner/cp3c-view-tree.json`: committed. It is the key tree observed from the product view for each pack case. `test_view_key_tree_equals_the_committed_tree` checks it. The file is not in `cases/pins.py` patterns, so it is not pinned.

CP-4:
- `render.other_five_sections` (expected.json:318): done. It now names the three CP-2D blocks and the two CP-3C blocks, and says they are "no longer owner Unbound". `test_other_five_sections_are_the_cp2d_and_cp3c_blocks` checks it.

FP04:
- `cases/legal/render-expected.json` `other_front_sections` now has `blocks`. It gives owner, producers, kind, state, route and note for the five blocks, as the real render shows them.
- `CP2D_D7_DELTA`, `CP3C_D7_DELTA` and `CP2D_D7_NOTE` are removed from `tests/test_legal_render.py`. The test now reads the oracle and checks `_spec_of(...).producers`.
- I found no other render oracle or test referencing the three ids.

Lease pin headers: added to CP2D, CP3C and CP4 (old → new shas inside). No legal lease records the render-expected sha, so I added no header there.

**Oracle values moved, and the item that moved each**
- CP-2D `expected.json`: `period` on known numeric cells and `value_class` on the five gap cells (R1 M1 re-pin); `currency` USD on T2E.5.r04 and r07 (GAP_CURRENCY); the stale-head `also` text (round 5 item 15).
- CP-3C `expected.json`: six principal periods, and CP-1A in `attempt_inputs`.
- CP-3C `manifest.json`: CP-1A in `bound_in_attempt_inputs`, `fact_copy_rule`, `frozen_inputs[8].use`, and the CP-2D pins.
- CP-4 `expected.json`: the `other_five_sections` text only.
- `render-expected.json`: `other_front_sections`.
- Nothing else moved. CP-2D, CP-3C and CP-4 submissions, the CP-2D and CP-4 manifests, and all pack numbers and claims are unchanged.

**Pinned, builder-hashed or reused files changed** (new sha prefixes)
- `cases/cp2d-owner/expected.json` ed36f120 and `builder/build.py` ea673c0c
- `cases/cp3c-owner/expected.json` 168e3bee, `manifest.json` 235ee364 and `builder/build.py` 8480e98a
- `cases/cp4-owner/expected.json` 2b98b81b and `builder/build.py` 8ec386bf
- `cases/legal/render-expected.json` d4eadecf
- `cases/PINS.json` regenerated (69 paths)
- `tests/cp2d_runs.py` and `tests/cp3c_runs.py` pins
- `src/deploy_workflow/owners/cp2d.py`: not pinned by a builder.

Stale pins left for W3, in other lanes' files:
- `cases/cp4c-owner/builder/build.py` pins cp4 `expected.json` (154fc2d0 → 2b98b81b) and cp3c `manifest.json` (e8aaf2eb → 235ee364).
- `tests/test_method_cp4c.py` references cp4 `expected.json` and passes, because it reads `PINS.json`.
- `cases/cpl10-owner/builder/build.py` names cp3c `builder/build.py` but did not need a re-pin in my scratch chain.
- W3 will see these at the pin-chain run.

**Double rebuild**: two fresh-copy chains over all 17 builders, with cross-pins re-pinned in the copies only, are byte-identical. The cp2d, cp3c and cp4 outputs equal the committed files. In the copies, cp4c's builder and manifest differ from the committed ones, as expected (cp4c is lane D's).

**Gates (exit codes)**
- `cases/pins.py --check`: 0.
- `ruff format --check`: 0 on touched files, after `ruff format` reformatted two of my test files.
- `ruff check` on touched files: only `tests/test_legal_render.py` C408 (`dict(` at ~:219), which is also in HEAD.
- `mypy --strict src/deploy_workflow/owners/cp2d.py`: 0.
- noqa count 13, type-ignore count 5.
- Tests: 1171 passed in one run (`test_connect_cp3c`, `test_stage2_classes`, `test_stage2_classes_batch`, `test_earnings_render`, `test_legal_render`, `test_method_cp2d`, `test_connect_cp2d`, `test_method_cp3c`, `test_method_cp4`, `test_connect_cp4`).
- Separate runs: `test_owner_cp2d` (431 passed with the method and connect files, 9 skipped), `test_owner_cp3c` (13 passed, 11 skipped), `test_method_cp4c` (1296 passed).

Not verified: `tests/test_owner_cp4.py` and `tests/test_probe_cp4.py` (the owner file's slow CP-1 promotion fixtures take 11-26 minutes each; the run was still going at handback); the Stage 5 store-run groups (the skipped tests); the full suite; mutation, complexity and jscpd gates; the Opus review; the claim wording of the drawings-precedence path beyond the cell and runway reasons; `test_connect_cp4c` and `test_connect_cp2h` against the stale cp4c pins; the pin text in lease bodies (CP3C lease :154 still repeats the old `fact_copy_rule` sentence, lane B's text). Also the Low `cases/legal` lease sha, the `docs/reuse/manifest.json` (not mine), and the empty `shown` for currency on the other gap cells (r05, r06 carry no currency in the CP-2D oracle; only r04 and r07 were named).

agent=mx-feature fix-rounds=0 gates-first-pass=n
