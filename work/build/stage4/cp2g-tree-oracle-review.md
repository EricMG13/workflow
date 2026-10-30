**Verdict: APPROVE.** I found no High, Medium or Low findings in the CP-2G view-tree oracle change `claude/s4-cp2g-tree` `ff9070e..cb66e6c`. One Info item answers the preparer's open point.

**Spec (brief steps 1 to 4)**
1. **What moved.** Exactly seven paths changed in `cases/cp2g-owner/cp2g-view-tree.json`. Six are the leaves `{positive,gap,cp1d_blocked}.tree.base.operands.{cash_interest,cash_taxes}.limitation`, each going from `NoneType` to `str`. The seventh is `_note`. No key, order or other leaf changed. One pin moved, at `cases/PINS.json:36`. `pins.py --check` on the copy exits 0 (86 paths). Probe: `.../scratchpad/cp2g-tree-review-probes/probe_tree_diff.py`, exit 0.
2. **Path from CP-1's note to the view leaf.** Each step below is file:line.
   - The pack's "Cash interest paid" and "Cash tax paid" rows are positive outflows (`cases/financial/manifest.json` extraction_expectations, page:3: 1.25 x4 / 5.00 and 1 x4 / 4).
   - `model/history.py:221-222` (`_row`) negates an outflow written positive and notes it `SIGN_NORMALISED` = "sign normalised" (`model/_cells.py:33`). `statement_history.py:75` applies the same note to normalised cells.
   - The LTM `calc` keeps the note of any part that carried it (`model/_cells.py:73-85`, `canonical_kpis.py:233-253`).
   - In T4.10, `canonical_tables.py:563-574` (`_value`) passes it on as `note=_join((value.reason, value.note))` (`:130`).
   - `model_interface.py:296` writes `Fact.limitation = reason or cell.note`. For a known cell `reason` is None, so the limitation is the note.
   - `owners/cp2g.py:342-353` (`select_cp1`) picks the fact labelled T4.10 `<LTM> · <metric>`, and `owners/cp2g.py:2996-3001` (`_cell`) emits `"limitation": fact.limitation`.
   - **Same CP-1 head in every case.** The bridge cases (positive, cp1d_blocked) build their pack as `cp1d_runs.make_pack("positive")` (`tests/cp2g_runs.py:69-70`). That function starts from `_fw().make_pack()` (`tests/cp1d_runs.py:52`) and only appends a `bridge` source. The gap case uses `test_financial_workflow.make_pack(gap=False)` (`tests/cp2g_runs.py:75`), so it has the same financial source pages. All three cases submit the same `fw.financials(pack)` (`tests/cp2g_runs.py:221`), which is built from MANIFEST alone (`tests/test_financial_workflow.py:360`+).
   - **Confirmed on genuine runs.** A genuine CP-0 and CP-1 run per case shows `known` with limitation `'sign normalised'` for both metrics in positive, gap and cp1d_blocked. Probe: `.../scratchpad/cp2g-tree-review-probes/probe_cp1_sign_note.py <copy> positive gap cp1d_blocked`, exit 0 (log next to it). Every case carries the note, so all six leaves are right to move.
3. **Seed change.** The new helper is `tests/test_method_cp2g.py:102-107` and is used at `:141`. It sets "sign normalised" only on known `cash_interest` and `cash_taxes`, which matches genuine CP-1. No assertion changed. The `limitation` field in `_ref_rows_cp1` is unaffected, because no case's `cp1_references` includes these two metrics, and in every case `expected.json` holds `limitation: null` for them. Running `tests/test_method_cp2g.py tests/test_connect_cp2g.py` on the copy: 580 passed, exit 0.
4. **Genuine run.** `tests/test_owner_cp2g.py -k a1_one_ok_read` on the copy: 1 passed in 354.9 s, exit 0 (log at `.../scratchpad/cp2g-tree-review-probes/a1.log`).

**Quality**
- **Info.** The genuine test checks only the positive tree against a genuine run (`tests/test_owner_cp2g.py:201`). The gap and cp1d_blocked tree entries are checked only on seeded heads (`tests/test_connect_cp2g.py:183-186`). The change is correct for them, but on genuine runs that rests on `probe_cp1_sign_note.py`, not on a test. This predates the change.
- I found no stub, fake value or catch-all. The seed's "sign normalised" matches what the product emits, as the genuine probe shows.

I deleted the copy. The probes and logs are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2g-tree-review-probes/`. I wrote nothing into any worktree.

Not verified: the RCA probe `owner-rca/probe_cp2g_viewtree.py` (I had no saved receipt; the genuine a1 test does the same check for positive); the full view body of genuine gap and cp1d_blocked runs (my probe stops at the CP-1 head, so a mismatch in some other leaf would go unseen); `test_owner_rendering -k cp2g`; the rest of `test_owner_cp2g`; the full suite.
