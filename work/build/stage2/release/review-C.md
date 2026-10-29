# Release review lane C (mx-adversary)

# Release review, lane C (citations and text): W2-D, W2-B, W3 hoist and text fixes

**Verdict: REQUEST CHANGES.** One Medium finding, part of which predates the release, plus three Lows. The round 3 changes in the four named cores, the hoisted helper, the oracle re-pins, the view trees, the TOOL-CONTRACT rows and MODULES.csv all check out.

Target: `R` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2-release` at 5a6a746. I made no edits there; the tree is clean. Every probe below is in `P` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-C/`. The mutation probes ran against `P/tree`, a `git archive` export of 5a6a746.

## Medium

**M1 (part predates). The round 3 derived-fact rule is not applied to CP-L10, and this release widened the gap.**
- **The rule.** Round 5 item 17 says round 3 applies to "every module whose frozen oracle carries derived-fact citation lineage that differs from round 3 … and any later module", at the close re-pin.
- **CP-L10 still uses the old rule.**
  - `src/deploy_workflow/owners/cpl10.py:573` (`_Cells.add` → `_unique` at `:556-557`) builds each derived cell's citations as the ordered, de-duplicated concatenation.
  - Its oracle rule text `rules.lineage_citations` (`cases/cpl10-owner/builder/build.py:994`) calls this "the CP-1C L3 rule". CP-1C dropped that rule in this same release.
- **What the release added (W2-A2, item 22).**
  - Missing `change`/`change_pct` cells now take `derives=` (`cpl10.py:661-671`), so they gain citation lists under the old rule.
  - The new test `tests/test_method_cpl10.py:561-563` pins `dict.fromkeys(start + close)`, which is the concatenation.
- **Failure.** The two quarter facts of a topic usually sit on one CP-1 page. In that case every change, change_pct, materiality, rank, disposition and evidence cell cites two quotes from that one page; round 3 allows one.
- **The same pattern predates the release elsewhere.**
  - `owners/cp2a.py:812-821` (`lineage`) does the same.
  - `owners/cp2d.py:2308-2310` (sum copies) does the same; that one is from reading the code only.
- **Probe:** `P/c8_cpl10_round3.py`, exit 1.
  - 87 derived CP-L10 cells across positive and limited carry repeated-page citations; 8 of them are the new missing cells.
  - `cp2a.lineage` over two page:4 quotes returns 2 citations on 1 page.
- **Fix, or a ruling.**
  - Fix: apply `owners.blank.one_per_page` at `cpl10.py:573` (and `cp2a.py:821`), update the rule text and the test. No literal oracle citation moves, because CP-L10 and CP-2A bind citations at run time.
  - Or: the owner rules these modules out of this close.
  - The CP-2A and CP-2D part goes to the owner as predating.

## Low (for the fix batch)

**L1. 15 of 51 spot-checked file:line cites in release-edited docs no longer point at their target.**
- Each was correct at a70ee52 (W2-B). They drifted 1-15 lines when the W2-C, W2-D and W3 source changes merged after it.
- `docs/TOOL-CONTRACT.md` view ranges: each range now ends 1-15 lines before `def view`. CP-1C `cp1c.py:1844-1893` (view now at 1894), CP-1D (2397), CP-2D (2607), CP-2G (3110), CP-2H (2249), CP-3C (2748), CP-4C (2924), CP-DR (855), CP-L10 (1283).
- Protocol §3 and CP-4 lease `owner_workflow.py:949` → the `_VIEWS` check is now at 950.
- CP-4C lease `cp4c.py:2686` → 2687.
- CP-3C lease `cp4c.py:1466` → 1467.
- CP-2H lease `cp2h.py:2079` → the def is now at 2081.
- CP-2G lease `cp2g.py:2641` → 2642.
- CP-8 lease `owner_workflow.py:1090-1093` and `:1454` → 1091-1094 and 1453-1455.
- Probe: `P/c1_cites.py` (output in `c1_cites.out`), exit 1.

**L2. Three method notes name helpers that commit 8915c17 removed.**
- `src/deploy_vii/methods/cp1c.md:36`, `cp2g.md:54` and `cp4c.md:37` cite `<cp>._one_per_page`. The helper is now `deploy_workflow.owners.blank.one_per_page`.
- Probe: `P/c2_stale_symbols.sh`, exit 1.

**L3. The item 21 heading names the wrong module.**
- `docs/rulings/2026-10-28-stage2.md:354` reads "Round 5 item 21 (CP-3C drawings precedence wording)".
- The wording is CP-2D's: round 5 item 4, A1 3614577, built in `cp2d.py`. `cp3c.py` never mentions "RCF commitment". The W3 notes and the review brief both say CP-2D.
- Probe: `P/c2_stale_symbols.sh`.

## Info
- **CP-4C v08 `unread_issues`: I accept this reading.**
  - The oracle holds both lines.
  - `refusal_rules.journal` states that the run-level issues are `expected_issues` followed by `unread_issues`, which is the close-release "two-line form", and the limitations equal those issues.
  - Both test files read the oracle.
  - `test_connect_cp4c.py:943-945` asserts that no other refusal carries the key.
  - `expected_issues` keeps the validator's single line, so the validator-level tests stay true.
- **cp1d keeps its own `_one_per_page`.** It differs from the hoisted helper only in its docstring. W3 left it because the brief scoped the hoist to the four cores.
- **The view trees use three shape conventions.**
  - `tests/view_tree.py`: distinct element shapes, `NoneType`.
  - cp1d: the first element's shape, `null`.
  - cp3c: a merged shape joined with `|`.
  - This is consistent within each tree and is not a defect.

## Verified, no finding
- **Round 3 in the four cores (cp1c, cp2g, cp2h, cp4c).**
  - The hoisted `one_per_page` is identical to the four removed copies.
  - `P/c3_mutants.py` and `P/c3b_last_quote_per_module.py`: 10 mutants, all killed, both probes exit 0.
    - A last-quote mutant of the shared helper is killed in each module's own tests.
    - Reverting each core to the old concatenation is killed in that core's tests.
- **Oracle moves.** `P/c4_oracle_moves.py`, exit 0.
  - cp1c changed 107 citation lists and cp2h 17. Each new list is exactly the first-per-page reduction of the old list, on a derived fact.
  - Every other moved leaf traces to a named item: the lineage_rule texts, the cp1c view `direction`, the cp2g blocked limitations, the scenario-name manifest text, the v08 key and journal text, and pin hashes.
  - CP-2G and CP-4C pin no citation list that changes. I confirmed both have zero derived facts with repeated pages, before and after.
- **View trees.** `P/c5_view_trees.py`, exit 0.
  - All six are in `PINS.json` (75 paths).
  - None has a `quote`, `citations` or `record_json` key at any depth.
  - Each has one top-level key list across its cases, which matches the manifest draft keys where a draft exists.
  - Each one's TOOL-CONTRACT row cites it.
- **TOOL-CONTRACT rows.** `P/c6_tool_contract_rows.py`, exit 0. All 14 new rows agree with `OWNER_SPECS` inputs and sources, `_VIEWS` and `host._OWNER_SCOPES`.
- **Lease pin headers.** `P/c7_lease_headers.py`, exit 0. The 2026-10-29 headers for CP-1C, CP-2G, CP-2H and CP-4C chain correctly and end at the tip shas.
- **MODULES.csv.** CP-1C `downstream_consumption` is `open`, matching CP-1C lease :124. All 26 rows have 11 fields.
- **Protocol text.** The §5 rule matches `owner_workflow.py:1004-1010`. The §6 synthetic line matches `execution.py:472-478`.

## Gate exit codes (run from `R`)
- `python3 -I cases/pins.py --check`: 0 (75 paths).
- pytest over `test_connect_{cp1c,cp2g,cp2h,cp4c,cp1d,cp3c,cp3}`, `test_method_{cp1c,cp2g,cp2h,cp4c}` and `test_citation_blank_quote`: 0, with 3158 passed and 1 skipped (`P/gate_lane.out`).
- `test_owner_blank`: 0, 308 passed.
- `ruff check` and `ruff format --check` on the 18 lane `.py` files: 0 and 0.
- `mypy --strict` on the 6 lane `src` files plus `tests/view_tree.py`: 0.

Not verified: the `test_owner_<cp>.py` genuine runs, including their view-tree and CP-2G blocked assertions, and the render suites, all as instructed. That a real CP-1 head puts two quarters of a metric on one page: M1 relies on the CP-L10 fixtures and the old cp2g.md note. The CP-2D sum-copy part of M1 is from reading the code only. jscpd, bandit, complexipy and the full suite were not run. The double rebuild belongs to lane B and I did not rerun it. Of the doc cites, I checked 51 (TOOL-CONTRACT, protocol, and the CP-4, 4C, 3C, 2H, 2G, 1C, 1D, 8, 2A, 2E and 2D leases), not every cite.
