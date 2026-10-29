# Stage 2 close release, wave 2 (stage contract)

The Stage 2 close release is the one place where `cases/`, `methodology.json`, lease text and TOOL-CONTRACT may change. Modules owns it; LEAD has stopped. Five `mx-feature` agents run in parallel. Each works in its own worktree, cut from W1 tip fb231d4 on `claude/s2-release`. W3 merges them, runs the full pin chain and runs every gate.

`L` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (the lane; read-only for you).
`F` = `/Users/ericguei/Documents/Deploy Workflow Sessions/lead-cp6-freeze/work/lead/cp6-freeze` (LEAD's re-pin tooling: `chain.sh`, `repin.py`, `fresh_copy.py`, `headers.py`, `edit_lease.py`, `edit_builder.py`, `report.md`; read and reuse, do not edit).
`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Inputs
| Item | File | Why |
|---|---|---|
| Item list | `L/work/build/stage2/close-release.md` | every release item, with its source |
| Lows | `L/work/build/stage2/lows.md`, `L/work/build/stage2-backlog.md` ("Added from LEAD" and the per-module table) | C's and A's Low items |
| Rulings | `L/docs/rulings/2026-10-28-stage2.md` rounds 1-5 (items 1-19), `L/work/build/stage2/questions.md` | settled; do not re-raise |
| W1 | `L/work/build/stage2/release/w1-report.md` | what W1 already re-pinned |
| Batch reports | `L/work/build/stage2/batch/*.md` | builders' release notes (for example `cp2g-report.md` release 1) |
| Contract | `AGENTS.md` (Source quotes, Stage closure), `docs/G1X-OWNER-CORE-PROTOCOL.md`, `docs/<CP>-OWNER-LEASE.md` | the spec |

## Setup (every agent)
- Step 0: `cd` to your worktree; the tree must be clean and HEAD must be fb231d4.
- Call `EnterWorktree(path=<your worktree>)` before writing. If Edit or Write still refuses a path, edit from Bash with Python.
- Python is `L/.venv/bin/python` with `PYTHONPATH=src:tests` from your worktree root.
- Commit on your branch. Commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Lanes (disjoint files; touch only your own)
### A1, covenant chain: CP-2D, CP-3C, CP-4, FP04. Worktree `../s2r-a1`, branch `claude/s2r-a1`
- **CP-2D oracle and core:**
  - re-pin the stale-head oracle wording (round 5 item 15);
  - re-pin the `T2E.5.r04`/`r07` gap twins with the missing currency, then remove `GAP_CURRENCY` and its tripwire;
  - fix the verb agreement in "RCF drawings is" and "Equity repurchases is" (cp2d.py:225, 826, 1390, 1394), then re-pin;
  - apply the drawings precedence ruling (round 5 item 4, cp2d.py:617), test-first, then re-pin;
  - check backlog :41-42 (sum copy T2E.1.r05 as a dependant gap; the copy period rule for recomputed cells) against the tip, and apply whatever is not yet built.
- **CP-3C:**
  - principal periods to q4-2025, then remove `PRINCIPAL_PERIOD_DELTA`;
  - CP-1A in `expected.cp3c_module.attempt_inputs` and `manifest edges.bound_in_attempt_inputs`, then remove `CP1A_BOUND`;
  - `fact_copy_rule`;
  - the `frozen_inputs[8]` names: PROHIBITED, NEAR_INSTRUMENT, INSTRUMENT_NOUN;
  - commit `cases/cp3c-owner/cp3c-view-tree.json`.
- **CP-4:** `expected.json:318` `other_five_sections`.
- **FP04:** re-pin `cases/legal/render-expected.json` with the CP-2D blocks and the CP-3C `refinancing-paths` and `lme-creditor-exposure` blocks, then remove `CP2D_D7_DELTA` and `CP3C_D7_DELTA` (round 5 item 18).
- **Lease pin headers:** CP-2D, CP-3C, CP-4 and any legal lease whose pin moves.

### A2, independent re-pins. Worktree `../s2r-a2`, branch `claude/s2r-a2`
- **CP-3D:** `amortisation_nonzero`.
- **CP-1D:**
  - the recipe text in `expected.json $.refusal_rules.partly_supported` and builder :1025, with the comma-space wording;
  - commit `cases/cp1d-owner/cp1d-view-tree.json`;
  - lows.md I1, the `context_block` docstring.
- **CP-L10:** the missing-change lineage.
- **CP-2E:** the blocked wording.
- **Leftover deltas:** every named delta not owned by A1 or D (grep `tests/` for `_DELTA`, `PERIOD_DELTA`, `GAP_VALUE_CLASS_DELTA`, `STAGE2_REFUSAL_DELTA`). Re-pin, then remove each one.
- **Lease pin headers:** for those modules.
- Do not touch `cp3d.py` (C owns it). If an item needs a change there, report it.

### B, lease and contract text (docs only). Worktree `../s2r-b`, branch `claude/s2r-b`
Every "Leases and contract text" and "From LEAD's dispatch queue" item in close-release.md, plus the round 5 lease list (CP-4 :36-42, :63-64 and FP04 :84-86; CP-3C :185; CP-4C :60; CP-3 alias, if the freeze has not done it; CP-2E internals and the Files row; protocol §5 round 2 and §6 synthetic line; CP-8 :85; CP-2A settled operands). Add each module's TOOL-CONTRACT row. In `MODULES.csv`, set CP-1C `downstream_consumption` to `open`; D3 closures wait for the Stage 5 runs.
- Do not touch lease pin header lines (A1, A2 and D own them), `cases/`, `src/` or `tests/`.

### C, product items and Lows. Worktree `../s2r-c`, branch `claude/s2r-c`
Each item is test-first.
- **`prose.is_blank`:** add Cc, default-ignorables and U+2800. The `owners/blank.py` re-export inherits it.
- **`readiness.citation_issues`:** refuse a blank or whitespace-only quote.
- **0d-c Lows** (backlog :45-49; source `L/work/build/stage1/0dc/r13-review.md`):
  - R1, the exact summary count;
  - R8-R11, c05 and c08: state the real worst-case record bound;
  - the tools.py:33-35 complexity claim;
  - the `clipped` docstring needs limit >= 1.

  Round 5 names them "Q1, F1, F3 and Q4". Reconcile the two lists in your report.
- **CP-DR `question_id`:** a 155-160 character id makes `Fact` raise after the binding write (owner item; fix approved). Refuse it at validation, before any write. Probe: `<S>/stage2-rereview/rr2_cpdr_long_question_id.py` must exit 0.
- **CP-DR and CP-3D:** run the RunText check unconditionally, as CP-2E does. Probe: `<S>/stage2-rereview/rr4_cpdr_masked_runtext.py` must exit 0. No frozen text may move.
- **CP-3D `_validate_step`:** use the `json_object` path, as CP-2D and CP-1D now do. Also fix the `_whole_on_page` docstring (cp3d.py:258, :260-261).
- **lows.md:**
  - G1-X guards: the test gap for the `==` → `<=` mutant at owner_workflow.py:614, and the docstrings over 100 characters;
  - CP-DR L2b and L2f tests;
  - the CP-2E Info docstring in `tests/test_owner_cp2e.py` :5-6;
  - the `drive_cp1` duplication. Touch only the `drive_cp1` code in `cp3c_runs.py` and `cp4_runs.py`; A1 edits their pin lines.
- **Backlog:**
  - the CP-2E `w-minus` test strength;
  - shared defect test L2, a schema-driven hostile fill for null or empty free-text fields.
- **`docs/reuse/manifest.json`:** only C edits it. Add a D12 record for each reused file you change (round 5 item 19 provenance).
- **Report:** list every pinned or builder-hashed file you change, so W3 can re-pin it.

### D, own citations: CP-2H, CP-1C, CP-2G, CP-4C. Worktree `../s2r-d`, branch `claude/s2r-d`
- **Round 3 citations:** switch each module's own derived-fact citations to the round 3 rule (round 5 item 17: one citation per page, quoting the first input quote). Re-pin each oracle and fixture with its change: CP-2H (the facts listed in close-release.md), CP-1C, CP-2G and CP-4C (review-A L1, concatenation lineage).
- **CP-2G:**
  - `cases.blocked.attempt_1.limitations`: remove the strict xfail;
  - the scenario name;
  - commit `cases/cp2g-owner/cp2g-view-tree.json`.
- **CP-4C:**
  - the v08 two-line form: remove the pins in both test files;
  - commit `cases/cp4c-owner/cp4c-view-tree.json`;
  - pin the surviving mutants in backlog :57-62.
- **CP-2H:** commit `cases/cp2h-owner/cp2h-view-tree.json`.
- **CP-1C:**
  - add view `rules.direction` to `expected.execution.tool_use.view`;
  - commit `cases/cp1c-owner/cp1c-view-tree.json`.
- **Lease pin headers:** for those four modules.

## Process (every agent)
1. For each item, check the tip first. If it is already built, record "already at fb231d4" with the line. Do not redo it.
2. **Frozen values:** only the named change may move one. If any other frozen value or refusal moves, stop that item and report it with the diff. Do not widen the change.
3. **Missing rulings:** if an item needs a ruling that is not recorded, skip it and report the question. Do not guess.
4. **Re-pinning your modules:** re-run the builders with `F` tooling (two fresh rebuilds must be byte-identical), regenerate `cases/PINS.json` (`python3 -I cases/pins.py`), and amend your lease pin headers ("Amended by Modules 2026-10-29 (Stage 2 close release W2-<lane>)", old → new sha). Cross-module pins go stale between lanes; W3 runs the full chain.
5. No stub or fake value standing in for real behaviour. No catch-all that hides a failure unless the fail-open is documented and logged.

## Gates (every agent; report each exit code)
- `ruff check` and `ruff format --check` on the files you touch. Known pre-existing findings: cp4_legal TRY004 :404, source_context ISC004 :581/:583, `test_cp1b_registration.py:98` PLW1510.
- `mypy --strict` on the touched `src/` files.
- The test files your change affects: the module's `test_method_*`, `test_connect_*` and `test_owner_*` files, plus anything `git grep` shows importing what you changed.
- `python3 -I cases/pins.py --check` (not B).
- `git grep noqa -- src tests | wc -l` must stay at 13 or below. `git grep "type: ignore" -- src tests | wc -l` must stay at 5 or below.

## Outputs (report as text, at most about 2k tokens)
- Branch tip SHA.
- Per item: done (commit), already at fb231d4, skipped with a question, or stopped with a frozen-value diff.
- Every oracle value that moved, and the named item that moved it.
- Every pinned, builder-hashed or reused file you changed.
- Gate exit codes.
- A closing `Not verified:` line.
- A ledger line: `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n|n/a>`.
