# Release scoped re-review (mx-precise aee778f4)

**Scoped re-review of the Stage 2 close release fix batch (s2-release c752e59, fix diff 5a6a746..c752e59)**

**Verdict: APPROVE.** Both Medium findings (C M1, B M1) are fixed, and the Q-C1 code matches its rulings. I found no High or Medium issue. Two Lows below can ride with the next batch.

**1. Lane C M1 (fixer 1, a50efb2)**
- `c8_cpl10_round3.py` exits 0: 0 repeated-page derived cells, and `cp2a.lineage` gives 1 citation per page.
- **Mutation check:** `release-rereview/mutate_round3.py` exits 0. In a scratch copy of the tip I put the old `dict.fromkeys` concatenation back at `cpl10.py:558`, `cp2a.py:821` and `cp2d.py:2346`. Each new test failed:
  - `test_derived_cells_cite_one_quote_per_page`
  - `test_missing_change_cells…`
  - `test_lineage_cites_one_quote_per_page_the_first`
  - `test_sum_copy_cites_one_quote_per_page_the_first`
- A "last quote on the page" mutant in `blank.py:22` also failed the cp2a and cp2d tests. With the code restored, all 5 pass.
- **Oracle:** fixer 1 changed only `claim_citations` and `lineage_citations` in `cases/cpl10-owner` `expected.json`, plus pin shas. No literal citation moved.
- CP-1D imports the shared helper (`cp1d.py:76,2168`), and the test asserts it is the same function.
- **CP-2D claims (`cp2d.py:2511`):** not a finding. Round 3 (`docs/rulings/2026-10-28-stage2.md:225`) covers a "derived fact". A CP-2D claim is not a fact; its citations are the citations of the sourced CP-1 facts it names. CP-2G and CP-4C claims carry no citation at all.
  - CP-L10 claims did switch to `one_per_page`, because `_claim` shares `_unique`. Its rule text was updated with it, which the allowance for CP-L10 rule text covers.
  - So CP-L10 and CP-2D now use different claim rules. This is consistent with the ruling, but the owner may want to know.

**2. Lane B M1 and the I2 D12 records**
- `probe_d12_chain.py <repo> HEAD` over all 12 reused files changed since f1544a3 exits 0: business_context, contracts, cp3_relative_value, cp4_legal, execution, live/submission, live/tools, methodology.json, prose, readiness, report_view, source_context.
- `release-rereview/d12_records_preserved.py` exits 0 for f1544a3→HEAD and for 5a6a746→HEAD:
  - every older record is byte-identical and in the same order;
  - the top-level keys are unchanged;
  - the only new records are the 4 restored ones and the 2 for ff1dbce.
- The ff1dbce records follow item 19: the prior shas ee1b27f9 and 5c71a311 are the files at `ff1dbce^`, and the new shas 3b33bfc2 and c6b5b931 equal the files at HEAD.

**3. Q-C1 (ff1dbce)**
- The `_Spec` matches the ruling exactly (`report_view.py:1174`).
- CP-MODEL is placed right after CP-1 (`contracts.py:56-66`).
- **Blast radius:** run creation defaults `requested_modules` to the preset (`contracts.py:94`). A default covenant_refinancing plan therefore gains exactly one module, CP-MODEL, which depends on CP-1. CP-5's dependencies also gain CP-MODEL, as they already do in the four other Model pathways.
  - The other pathways are unchanged. `pathway_has_model_block` is true exactly where CP-MODEL is in the preset, for all 6 pathways.
  - Runs that set an explicit module list are unaffected, including the `test_source_tools.py:700` fixture and the cp2d and cp3c runs.
  - `rendering.py:98` needs CP-MODEL to be `not_in_pathway` only in the source slice, and that run sets its modules explicitly.
- **Tripwire:** I ran it with `--runxfail`. It fails at `test_connect_cp2d.py:1196`, the figures check: `figures == ()`, owner MODEL, CP-2D settled. That is the stated reason.
  - `Block.figures[].fig_id`, `Block.tabs[].label` and `Block.tab_label` all exist. A Stage 3 render with S.4 first and T2E.4 as a tab would therefore satisfy all four asserts, XPASS, and fail under strict.
- The `pathway_has_model_block` test is real. It is true for covenant_refinancing and credit_snapshot and false for distressed_restructuring, and it would be red if the owner were reverted to CP-2D.

**4. I2**
- **Oracle values moved only through Q-C1:**
  - cp2d `fp04_render`/`maturity_wall_note`;
  - cp4 `other_five_sections`;
  - render-expected CP-MODEL `unrun` and the maturity-wall owner, producers and note;
  - everything else is a pin sha, including the legal manifest pin from B L1.
- The cpos changes are sha-only: the report_view and contracts pins in its builder and manifest. The cpos `expected.json` is untouched.
- **Rebuilds:** I ran two fresh-copy rebuilds (`fresh_copy.py` + `chain.sh`) from an archive of c752e59. Both chains exit 0. The rebuilds are byte-identical to each other and to the tip's `cases/` (`diff -r` exit 0).
- `pins.py --check` reports "matches 75 paths", exit 0.

**Findings**
- **Low L1, docs:** `src/deploy_vii/methods/cpl10.md`, `cp2a.md` and `cp2d.md` do not state the derived-fact rule.
  - **Requirement:** round 3 (rulings :228) says "each module's methods/<cp>.md states the derived-fact rule". Item 17 now brings these three modules under round 3. cp1c, cp1d, cp2g, cp2h, cp4c and cp8 already state it.
  - **Probe:** `grep -l -i "one_per_page\|per (source, page)\|one citation per" src/deploy_vii/methods/*.md` does not list these three.
  - **Cost:** the cpl10 builder pins `cpl10.md`, so fixing it means a pin cascade.
- **Low L2, failure-hiding:** the tripwire's `xfail(strict=True)` at `tests/test_connect_cp2d.py:1178` has no `raises=AssertionError`.
  - Any exception counts as the expected failure. That includes a `make_upstream` or build crash, or the KeyError from `kind="chart"` that the ruling warned about.
  - **Scenario:** a broken S.4 wiring in Stage 3 would keep it xfailing silently instead of failing.
  - **Fix:** add `raises=AssertionError`. Check with `--runxfail`, which today gives an AssertionError at :1196.

**Gate exit codes**
- c8: 0. `mutate_round3.py`: 0.
- `probe_d12_chain` over 12 files: 0. `d12_records_preserved` (both bases): 0.
- Double rebuild: chain 0/0, diff 0. `pins.py --check`: 0.
- pytest on `test_method_cpl10`, `test_method_cp2a`, `test_connect_cp1d` and `test_connect_cp2d` (scratch copy of the tip): 618 passed, 1 xfailed, exit 0.
- `test_pathway_has_model_block…`: passed.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-rereview/` (`mutate_round3.py`, `d12_records_preserved.py`, `reused_changed.txt`, and the `tree`, `rb1` and `rb2` copies).

Not verified:
- The render suites, `test_legal_render.py` as a whole, `test_source_tools.py`, the `test_owner_<cp>.py` runs and the full suite (the controller's runs).
- Whether a real CP-1 head puts two quotes on one page for a CP-2D sum copy or a CP-2A operand (covered by fixtures only).
- The XPASS is reasoned from the Block fields, not simulated with a wired S.4.
- The legal-case jsons are not rebuilt by `chain.sh`, so the double rebuild covers only the `*-owner` builders.
- `ruff`/`mypy` were not rerun.
- I did not check that the lease-header amendment lines match the shas.
