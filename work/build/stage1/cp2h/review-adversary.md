# CP-2H Stage 1 adversarial review (target cc1d0fb, worktree agent-a52b5ec0919986ddb)

**Verdict: CHANGES REQUIRED.** There are two Medium findings. The calculation itself is correct: an independent exact recomputation matches on all four composed cases. Every one of the 29 refusals is pinned by its own test.

## Findings

**F1 (Medium): the threshold form is wider than round 7 item 8 allows.**
- **Where:** `src/deploy_workflow/owners/cp2h.py:140` (`_THRESHOLD`) and `:315`.
- **Rule:** round 7 item 8 (`docs/rulings/2026-10-28-stage1.md:992`) says a threshold that is not N.Nx or N.N% gives `Trigger terms not found`. The manifest `parse_rule` says `'N.NNx'` / `'N.N%'`.
- **What the code does:** it keeps the builder's `[0-9]+(\.[0-9]+)?(x|%)`, so `4x`, `2.7x`, `10%`, `2.755x` and `10.05%` all compose.
- **Failure scenario:** a source term `Above  2.755x` gives a T2R.3 source fact shown as `2.76x`, while its own citation quotes `2.755x`. Likewise `10.05%` is shown as `10.1%`.
- **Tests:** no test pins either side. The mutant that requires a decimal point (C50) survives.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p01_threshold_form.py` exits 1 (six forms accepted).
- **Fix is safe for the oracle:** a strict `N.NNx|N.N%` keeps all 154 tests green (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/spec_fix_safety.py`, survives as intended).
- **Needs LEAD first:** the exact digit count. The ruling's literal "N.Nx" would refuse the frozen `2.75x`, so it reads as shorthand.

**F2 (Medium): the round 7 (a) issue order has no test, though the round 7 report says it does.**
- **Where:** `cp2h.py:1462-1512` and `:1579-1583`. The report claim is at `work/build/stage1/cp2h/round7-report.md:73` ("existing tests cover them").
- **Behaviour is correct.** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p06_issue_order.py` exits 0 on a 19-issue payload. It covers register order, unknown agencies last, agency/confidence/rationale/evidence/limitation within a view, then the missing view, overall and gaps.
- **No test pins it:** all eight reorder mutants survive (C28-C35 in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/spec_other.py`; runner exit 1).
- **Why it matters:** the issue list becomes the blocked head's limitations (`test_blocked_attempts_issue_text`), so a reorder is a visible output change.
- **Fix:** one multi-issue test; p06 is a ready template.

**F3 (Low): the percent threshold is rounded in the default 28-digit context.**
- **Where:** `cp2h.py:318`, `value.scaleb(-2)` with no context. The builder does the same at `build.py:237`.
- **Failure scenario:** source `1.23456789012345678901234567891%` is stored as `0.01234567890123456789012345679`. A multiple is stored exactly.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p02_threshold_scaleb_context.py` exits 1.
- **F1 alone does not fix this:** a long integer part still rounds. Use an exact exponent shift, or at least `CONTEXT`.

**F4 (Low): pinned behaviours that are correct but untested.**
- Each is confirmed correct by a probe, and each has a surviving mutant.
- **Tightest takes the first missing year's reason** (lease :90): `:1125`, mutant C25.
- **T2R.6 takes the first unknown year's reason:** `:1167`, mutant C26.
- **Root reason is the threshold first** (lease :91): `:1000-1002`, mutant C27. Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p09_reason_order.py` exits 0.
- **(g): the date is read from the Published line:** `:245`. A hardcoded `2026-01-10` survives (G1 in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/spec_more.py`). Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p12_published_date_read.py` exits 0. The report's "(g) covered" is inaccurate.
- **Sign refusals:** `:140` and `:279`, mutants C45 and C46. Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p03_signs.py` exits 0.

**Info**
- **Untested input invariants:** the CP-2G unit/period check (`:444`, C47) and the CP-1 `T4.10` table filter (`:424`, C48).
- **Equivalent mutants:** C21 (`_canonical` on a threshold; `exact_text` normalises anyway) and C44 (`referencable` filter, equivalent while every CP-1 ratio is known).
- **Source issue texts carry invisible characters verbatim,** for example `Unrecognised trigger metric: Total debt to EBIT\xadDA`. This is the pinned `<m>` form.

## Checked clean, with probes
- **Calculation against the Method:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p08_independent_calc.py` exits 0.
  - It recomputes with Fractions and correct 38-digit rounding: headroom, pp, strict reached, tightest and its year, first year, T2R.9 counts and T2R.8. All match on positive, gap, fixture_total_loss and fixture_boundary.
  - No known zero comes from a missing input.
- **Arithmetic mutants are all killed:** operand swaps, the 28-digit context, `*100`, non-strict comparison, min to max, counts.
- **Round 7 items 1-8 and (d):** byte for byte against text extracted from the ruling file, and reachable in composed output. 21 checks; `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p07_round7_wording.py` exits 0.
- **Signs:** no negative is read as positive (`-`, `+`, parentheses, U+2212, en dash, comma, fullwidth and Arabic-Indic digits, exponent). Negative CP-2G ratios keep their sign. CP-2G makes leverage `missing` when EBITDA is zero or negative, so a negative leverage can only mean net cash. p03 exits 0.
- **Normalised-read defect class (CP-8/CP-3D): absent.**
  - Headers are matched by exact line equality, and values come from the same raw line that is cited.
  - Soft hyphens, zero-width characters, NBSP headers and CRLF all fail closed. NBSP or em-space separators parse to the clean values.
  - No value is read from `Citation.quote`.
  - `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p04_normalisation.py` exits 0.
- **Unusual valid states compose, pass `validate_tables` and pass `prose.issues`:** every threshold unstated, three agencies with one Not rated, a `0.00x` threshold. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p10_unusual_valid.py` exits 0.
- **Standing rules hold:**
  - No catch-all: only `SourceIssue`, `ValidationError` and two date `ValueError`s are caught.
  - No stub or fake value.
  - No I/O, store, host or session call. `fact_spelling` is a pure import with precedent in cp1c, cp2e, cp3d and cpl10.
  - No clash with protocol §2 names; `validate` and `compute` follow cp2a.

## Per-refusal mutants (my runner; whole-tree copy; an import canary proves the copy's `src` is the one loaded)
- **Result:** 29 of 29 killed. Each mutant failed its own `test_refusal_issues[<id>]` and no other refusal test.
- **Runner:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/runner.py`, exit 0.
- **Spec:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/spec_refusals.py`.
- **Log:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/refusals.log`.

| id | cp2h.py line | mutant | own test fails | tests failed |
|---|---|---|---|---|
| r01 | :85 | `view: View` → `str` | yes | 2 |
| r02 | :96 | Overall `confidence` → `str` | yes | 1 |
| r03 | :86 | AgencyView `category` → `str` | yes | 1 |
| r04 | :97 | `overall.limitation` default None | yes | 1 |
| r05 | :110 | TriggerSubmission `extra="ignore"` | yes | 1 |
| r06 | :1593 | drop the `(root): Invalid JSON` shape issue | yes | 4 |
| r07 | :111 | views `min_length` removed | yes | 1 |
| r08 | :89 | evidence `min_length` removed | yes | 1 |
| r09 | :89 | evidence a Citation subclass with an optional quote | yes | 1 |
| v01 | :1476 | unknown-agency check off | yes | 1 |
| v02 | :1490 | missing-view check off | yes | 1 |
| v03 | :1478 | duplicate-agency check off | yes | 1 |
| v04 | :1446 | filter `Bare figure` | yes | 1 |
| v05 | :1446 | filter `Unresolved reference` | yes | 2 |
| v06 | :1446 | filter `Unit ` | yes | 1 |
| v07 | :1446 | filter `Malformed run text` | yes | 1 |
| v08 | :1481 | view High check off | yes | 2 |
| v09 | :1500 | overall High check off | yes | 1 |
| v10 | :1443 | empty-text check off | yes | 2 |
| v11 | :1438 | filter `(peer ranking)` | yes | 1 |
| v12 | :1438 | filter `(instrument recommendation)` | yes | 1 |
| v13 | :1438 | filter `(recovery conclusion)` | yes | 1 |
| v14 | :1407 | remove "will be downgraded" | yes | 4 |
| v15 | :1418 | remove "probability-weighted" | yes | 2 |
| v16 | :1486 | filter `Quote/locator mismatch` | yes | 1 |
| v17 | :1528 | ignore CP-2G staleness | yes | 4 |
| v18 | :1528 | ignore CP-1 staleness | yes | 1 |
| s01 | :359-360 | raise removed (`register_rows or []`) | yes | 2 |
| s02 | :365-366 | raise removed (`terms_rows or []`) | yes | 4 |

**Comparison with the implementer's runner.** An unchanged copy, `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/impl/mutants.py`, exits 0 at 58 of 58, the same verdicts as its log. Its weaknesses:
- It copies part of the tree and has no import canary.
- Several refusal mutants are shared or not specific to one refusal:
  - r06 (`[1:]`) fails all nine shape refusals (13 failures).
  - r09 changes the evidence type (90 failures).
  - One mutant each covers v04-v07, v11-v13 and v17-v18.
  - s01 and s02 swap the message text instead of removing the raise.
- Mine are one mutant per refusal, and the two runs agree.

## Other mutants
`spec_other.py` killed 31 of 50 (runner exit 1); `spec_more.py` killed 0 of 4 (exit 1).
- **Killed:** all arithmetic and divergence mutants (C01-C20, C22, C23); item 1 bound line; item 4 position and wording; item 7 pages and frame; the item 8 block rule; (d) guard dropped or reordered; (f) a25 copy status.
- **Survived:**
  - (a) order, C28-C35 (F2);
  - C25-C27, G1, C45 and C46 (F4);
  - C47 and C48 (Info);
  - C21 and C44 (equivalent);
  - C49, G2, G3 and G4 (the LEAD items below).

## Pre-existing or unruled, for LEAD
1. **The pinned block rule drops published terms silently** (item 8, "ends at the first short line").
   - A malformed middle row ends the block: an omitted threshold, a qualifier column, or a double space inside a metric name.
   - With a valid figure-free payload, 3 of 5 published terms vanish, including both of Brook's (a rated agency). T2R.9 "Triggers tested" reads 2, with no issue and no own line, and the analyst can still cite the dropped lines.
   - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p05_block_truncation.py` exits 1.
   - Possible rule: a one-field line ends the block (gap page:1's note); a line of two or more fields that is not the block width refuses. That keeps all 154 tests green (`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/spec_block_safety.py`).
2. **Exact threshold pattern for F1:** the manifest's `N.NNx` / `N.N%`, or "decimal point, any digits".
3. **Empty or blank limitation:** `""` or `"   "` passes (d) and reaches `Claim.limitation` (`contracts.py:205`). No ruling covers it (p10).
4. **Lineage of a known first year:** a known `FY2026` first-year result lists a later missing CP-2G fact in `derives_from`. Lease D3 (c) asks for all three rows; the builder's "known never derives from unsettled" assertion covers own facts only. Probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-adversary/p11_known_from_missing_lineage.py` exits 0.
5. **Two sources for T2R.1 statuses (Stage 2):** `u_cp1` and `u_cp2g` take their status from fields that are not checked against the bound Inputs, while item 1 derives CP-1D from its bound Input (G4).
6. **Stale issues (Stage 2):** the order with several stale inputs, the `absent` wording and the `str` current path are untested (G2, G3, C49).

## Gates (target root)
| Gate | Exit |
|---|---|
| pytest (154 passed) | 0 |
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` (cache dir in scratch) | 0 |

The target worktree is still clean at cc1d0fb.

Not verified: Stage 2 seams, tool use, run-level outcomes, rendering and FP05 for zero-row T2R.8/T2R.10; real CP-2G core output (whether CP-2G can emit a not_applicable T2H.6 ratio, and the units on unsettled facts); the builder rebuild and pins (not run, read-only); the implementer's and LEAD's `probe_strings.py`, and `prose.issues`/`bare_figures` on new strings beyond p07; hypothesis beyond default settings; a ready source with `extraction_status="degraded"`; the full suite (only `tests/test_method_cp2h.py` was run, as instructed).
