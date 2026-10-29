## Stage 3 fix round 1: scoped re-review

All three branches pass. Every fixed finding meets item 22, and every reviewer probe now fails to reproduce its defect. No High or Medium findings are open.

### Verdicts
- **`claude/s3-fix1-g2` (ee95ffb): APPROVE**
  - **Arch M1:** fixed. The row is at `src/deploy_workflow/owner_rendering.py:285-299` with the lease tuple and banner. `GATED_IDS = ("cp6-fp01-committee",)`, and that gated test stays. Probe `arch/p2_cp3c_scope_refused.py` exits 1, which by its own convention means the run is now matched to `cp3c-fp04-refinancing`.
  - **Precise M1:** fixed. `tests/test_owner_rendering.py:1308-1334` requires the oracle text exactly. A suffix must be the exact ` (∅ G<n>, …)` form, its refs must be distinct, every ref must be a `gap_ref` cited by the block's own cells, and only a gap case (oracle `reference` set) may carry one. Probe `precise/probe_g2_title_and_reason_fix1.py` exits 0: all three forged inputs are refused. `arch/p3_dr6_gap_refs_resolve.py` exits 0.
  - **Precise L1 / arch L2:** fixed. `title_pattern` uses `re.fullmatch` with the ruled regex, and the FP-04 fixture title is compared exactly. The same fix1 probe refuses the "junk" title.
- **`claude/s3-fix1-rest` (2823590): APPROVE**
  - **M2:** fixed. In `tests/test_owner_cpos.py:131-159`, the cache key is now `tree_digest(store)`, the receipt hash, `tree_digest(publication)` and the publication path. The digest covers relative paths and bytes, so an in-place edit changes the key. Probe `precise/probe_cpos_cache_path_key.py` exits 1 (`ValueError: store changed`), so the defect is not reproduced.
  - **M3:** fixed. The record moved, values unchanged, to the end of `post_import_patches` (`docs/reuse/manifest.json:1719-1727`). `precise/probe_d12_strict.py L 697fe8a 2823590` still exits 1. Every Stage 3 record passes (statement_extract, bindings/cp1, charts, and report_view @80ab9f5..f5477b4). The only failures are report_view @3e5b537, @24f879a and @8aef58d, which item 22 sent to the owner.
  - **M4 / L3:** fixed. `tests/test_legal_render.py:393-414` now asserts the T4.9 fact-id index lookup, per-mark text equality (gap marks against `gap_ref_pattern`), and the in-order twin-label `label_parts` rule. Probe `precise/probe_legal_cr1_twin_labels.py` exits 1: the forged labels are refused in both cases.
  - **Arch L1:** fixed. `ruff format --check` on the 7 changed files exits 0. The cp3c builder has no diff from 18dc1fa (restored at 2823590). Only the cp1c and cp4c builder pins moved in `cases/PINS.json`.
- **`claude/s3-mypy-chart` (e43aad9): APPROVE.** The diff is annotations and `cast` calls only. The one removed `passport` assertion and the two `_strip(report).note` assertions are re-added unchanged except for the `cast`, which keeps the same behaviour at run time.

### Findings
- **Low L1.** `tests/test_owner_rendering.py:1872-1882` (`exact_titles`): the composer strip test compares the fixture's off-form title exactly, so no fast test checks the ruled regex on that strip. Fix: change `tests/test_cp1_chart_render.py:150` to "principal at" and drop the `exact_titles` override. That file belongs to the mypy branch, so do it after merge. Same evidence as the S.4 ruling below; no separate probe.
- **Info I1.** The genuine `cp3c-fp04-refinancing` run fails in `tests/cp3c_runs.py` before it reaches G2 (`read_cp2` is refused with `not_permitted`). This is item 23's CP-1A literal problem, already ruled and deferred. Nothing changes in G2.

### S.4 fixture ruling
The producer and the ruled regex ("principal at") are right. The producer (`src/deploy_workflow/financial_series.py:212`), the frozen S.4 oracle (item 20 Q1, `s4fp04-expected.json`) and the regex all say "principal at". The "current principal" title at `tests/test_cp1_chart_render.py:150` is a hand-built composer fixture that matches no producer or oracle. Comparing it exactly (stricter than the regex) is an acceptable stopgap, not a weakened check (L1).

### Cross-checks
- **No weakened assertions.** The only assertions removed across the three diffs are the old prefix and strip checks, replaced by stricter ones, plus the mypy re-adds.
- **Disjoint files.** The G2 branch touches `owner_rendering.py` and `test_owner_rendering.py`. The rest branch touches the builders, `pins.py`, `PINS.json`, `financial_series.py`, `manifest.json`, `test_legal_render.py` and `test_owner_cpos.py`. The mypy branch touches `test_cp1_chart_render.py`. No file is shared.
- **Merge check.** I applied all three patches to a fresh 18dc1fa copy (`<S>/fix1-rereview/merged`); all applied cleanly (exit 0). On that copy:
  - `ruff format --check` exits 0.
  - `ruff check` on the cpos and G2 test files: "All checks passed".
  - `mypy --strict` on the G2 test pair: "no issues found".
  - G2 `-k fast`: 151 passed, exit 0.
  - Legal and cp1 chart tests: 115 passed, exit 0.
  - `cases/pins.py --check`: exit 0, 86 paths.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Probes are in `<S>/stage3-review/{arch,precise}/` and the fresh copies in `<S>/fix1-rereview/`.

No stubs, fake values or catch-alls were added.

Not verified: any genuine owner run (cp3c, cp1-model S.4 regex on real output, and the CP-OS suite, which I was told not to rerun); the cp1c, cp4c and cp3c owner suites against the new builder pins; the builders' byte-identical rebuild (I took it from the F2 report); `ruff check` on the builders; and the exit codes of `ruff check` and `mypy` in the merge check, since their output was piped through `tail` and I read only the printed result.
