**Verdict: APPROVE.** Rulings 27 and 28 are carried out as written, and the change refuses every wrong delivery I tried. I found no High, Medium or Low findings.

The probes run on a copy made with `git archive 42bd134`, at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix3-rereview/src`.

**Spec verdict: pass**
- **Item 27, positive test** (`tests/test_owner_rendering.py:697-714`).
  - Each delivery's `model/` must be byte-equal to its own publication (`model` and `fin_model`).
  - `model.html` and `calculation.json` must be byte-equal across the two runs.
  - `receipt.json` is compared after only `ticket_id` is popped, and that `ticket_id` must equal the single CP-MODEL attempt ticket in its own store.
  - If G2 delivers the financial publication, the first loop fails: that receipt's `ticket_id` differs from G2's own publication.
  - Any other receipt difference fails the final dict compare.
  - Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix3-rereview/probe27_model_equivalence.py` exits 0. It re-runs these assertions on synthetic publications with stubbed store tickets. The honest case is accepted. Three cases are refused: G2 delivering the financial publication, a receipt that differs in another field, and a non-ticket difference between the runs.
- **Item 27, extra-attempt test** (`:801-823`).
  - `begin("CP-1")` must raise "settled".
  - A pending CP-1 repair attempt is then forged through `_write`, as the plan says.
  - The test reads the store back and asserts the forged ticket is the last attempt with `status == "pending"`. `status` is a real field (`src/deploy_vii/execution.py:98`, default "pending").
  - It then calls `_refused`, which also asserts no destination is left behind.
- **Item 28.**
  - `_is_synthetic_chip` (`:2037-2040`) drops only `fig` runs whose `ref_id` is `S\d+` and whose text equals that `ref_id`. Real chips are kept: C and K are separate prefixes (`report_view.py:62`). A synthetic fig *value* (text differs from the ref) is kept too.
  - `_line_text` (`:2043-2045`) joins runs with " ".
  - `_matches_oracle_text` (`:2016-2019`) is an exact match unless the oracle text has `∅ G#`. Where it does, it accepts only `∅ G\d+`.
  - The chip-present assertion equals `bool(synthetic_ref)` (`:2090`).
  - Tabs-only oracles compare all labels, then zip rows with `strict=True` (`:2075-2083`). The line count is asserted, and lines are zipped with `strict=True` (`:2085-2086`).
  - `assert_render_node_owner` (`:2051-2059`) checks owner, kind where present, and the cp3d tab labels against the `[id, label]` pairs in `cases/cp3d-owner/expected.json`. It is wired for exactly cp3d, cp4 and cp8 (`:2321-2324`) and adds no secondary-pointer checks.
- Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix3-rereview/probe28_block_rule.py` exits 0: the baseline passes and all 22 mutants are refused.
  - **Chips:** S chip swapped for a K chip; S chip removed; extra S chip; real C chip dropped; synthetic fig value dropped.
  - **Gap placeholder:** oracle literal against a rendered gap; rendered literal `∅ G#`; rendered `∅ Gx`; gap followed by trailing text; known cell rendered as a gap; placeholder cell rendered as a literal.
  - **Tabs and lines:** missing tab; extra tab; wrong tab label; missing line; extra line; lines reordered.
  - **Render nodes:** wrong owner (cp3d and cp8); cp3d tab missing; cp3d tabs reordered; wrong kind (cp4).
- **Fast tests:** `tests/test_owner_rendering.py -k fast` on the copy exits 0 (152 passed, 59 deselected).

**Quality verdict: pass.** There are no stubs, fake values or catch-alls. The `uuid4` ticket in the forged attempt is the forgery itself, which ruling 27 allows. The edits leave the round 2 range (old :2140-2160) untouched, so the merge by hunk still holds.

**Info**
- `:2071` — where an oracle has `primary`, tab pairing still uses `strict=False`. Ruling 28 step 3 keeps that rule unchanged, so this is not a defect.
- `:823` — `_refused` pins no error code; the plan says that is optional.

Not verified: no genuine test was run (the brief defers them to the controller), so the item 27 tests did not run against real stores. The item 27 probe replays the assertion logic on synthetic files and does not exercise G2 itself. The render-node checks were probed only on hand-built nodes shaped like the oracles, not on rendered cp3d, cp4 or cp8 payloads. Mypy was not run.
