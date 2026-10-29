**Verdict: APPROVE.** All nine items hold in code, and every mutant they name is killed. I found no High or Medium finding. Two new Low test gaps (N1, N2) can ride with the next fix or the end batch. The target worktree is still clean at f843772.

Probe folder: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-fix1-review/ (P below). Every runner run used a full temporary copy with PYTHONDONTWRITEBYTECODE=1, and the canary failed each time as it should.

## Findings, by id
- **F1 (Q1): holds.**
  - The pattern text is exactly the ruled grammar, and it is fullmatched (`cp2h.py:142`, `:329`).
  - 39 refused forms each give `Trigger terms not found` alone, through both `parse_ratings` and `validate`. They include `4x`, `2.7x`, `2.755x`, `.75x`, `2.x`, `X`, `×`, fullwidth and Arabic-Indic digits, `±`, comma, ZWSP, soft hyphen, `10%`, `10.05%`, `.0%`, `-10.0%` and wrong units.
  - The valid forms still parse exactly.
  - Probe: P/f1_grammar.py, exit 0. C45′, C50′ and C50″ are killed.
- **F2: holds.** C28 to C35 are all killed (P/rr_spec_other.log). The first review's p06 exits 0.
- **F3 (Q2): holds.**
  - I parsed under a 3-digit ROUND_UP context with Inexact and Rounded trapped. Percents up to 60 integer digits store as the exact Fraction/100 in canonical form, and no trap fires. So nothing on the path uses a context.
  - Probe: P/f3_exact_shift.py, exit 0. F3′ and C20′ are killed.
- **F4: holds.** C25, C26, C27, C46 and G1 are killed (P/rr_spec_other.log, P/rr_spec_more.log). C45 is replaced by C45′, which is killed.
  - p09 fails only because B5 removed `cp1_status`. A ported copy, P/p09_reason_order_ported.py, exits 0.
- **Round 11 B2: holds.**
  - **Rule:** the code matches the field-count rule on every vector. A line with the header's field count is a row. A line of two or more fields with another count refuses with that block's text. That covers 4 and 6 fields, a split metric, two rows joined by CR or by U+2028, a breach on a block's first line, and register and scale breaches. Trailing double spaces and tabs, double-tab, tab+space, NBSP+NBSP and NBSP+space separators all parse as clean rows. A page in CRLF fails closed. Probe: P/b2_vectors.py, exit 0.
  - **Order:** 24 pairs, a breach against a missing header, and a breach against the agency rule all follow headers first, then scale rows, register rows, terms rows. Probe: P/b2_order.py, exit 0.
  - **Frozen blocks:** all five frozen variants and all 19 SOURCE_BREACHES cases parse identically at a7b135b and at f843772. Probe: P/b2_frozen_identical.py, exit 0.
  - **Silent drops:** a malformed row can still vanish silently, but only through a line that B2 itself treats as a block end; see the LEAD notes below.
  - **Mutants:** the B2 reverts, M1, M2, M11, M12 and M16 are killed.
- **Round 11 B3: holds.**
  - Eleven blank forms (`""`, spaces, `\n`, `\t `, `\r\n`, NBSP, U+3000, U+2028, em spaces, `\x0b\x0c`) each give `<path>: empty text` alone. That is the same frame as the existing empty-rationale refusal.
  - The check runs before `prose.check`, sits in the limitation slot of the round 7 (a) order, and `compute` refuses the payload. Null still composes.
  - Probe: P/b3_blank_limitation.py, exit 0. M3 and the B3 revert are killed.
- **B5: holds.**
  - `TriggerUpstream` and `Cp2gMetrics` no longer carry any status field.
  - All 4 composed cases × 36 bindings (and a reordered bound) give T2R.1 statuses equal to the bound Inputs'.
  - Over every record key of every composed case, the only frozen disagreement is `fixture_total_loss` `T2R.1.u_cp2g.status`, text and shown (`composer_only` against `restricted`). Own limitations match the oracle.
  - Probe: P/b5_statuses.py, exit 0. Run with `--runxfail`, the strict xfail fails on exactly that assertion, `'restricted' == 'composer_only'`.
  - Not re-ruled: it is with LEAD as B7.
- **B6: holds.** G2, G3 and C49 are killed.
- **Retargets: each is faithful.**
  - s01′ and s02′ remove the header raise for both an absent and an empty block, as s01 and s02 did. Both are killed by their own refusal tests.
  - C20′ is a one-place shift, like C20's `scaleb(-1)`.
  - C41′ is `continue` instead of ending the block, like C41.
  - C45′ adds a sign. Caveat: the new grammar has two sign sites and only the multiple one is pinned (N2).
  - C50′ and C50″ loosen the now-strict grammar, which is the right direction for the new code.
  - G4′ makes the status a literal at the `required_status("CP-1")` site.

## Mutant runs
| Spec | Killed | Exit | Notes |
|---|---|---|---|
| spec_refusals | 27/29 | 1 | Only s01 and s02 fail, because their sites are gone; s01′ and s02′ are killed. All 29 refusals stay pinned. |
| spec_fix1b_retarget | 3/3 | 0 | |
| spec_fix1_retarget | 5/5 | 0 | |
| spec_fix1b | 7/7 | 0 | |
| spec_other (mine) | 44/50 | 1 | Not killed: C20, C21, C41, C45 and C50, whose sites are gone, and C44, which is equivalent. |
| spec_more (mine) | 3/4 | 1 | G4's site is gone; G4′ is killed. |
| P/spec_review.py (new) | 6/12 | 1 | Survivors: M5, M6, M7, M14 (N1, N2), M8 and M9 (below). |

- **M8 is equivalent.** It reads the status from `current`. A composition only runs when nothing is stale, so `current` then matches `bound`. Duplicate input ids are refused by the `ModuleResult` contract (`contracts.py:307`).
- **M9 is unruled.** It moves a register breach after that block's own row checks. See the LEAD notes.

## New findings (both Low; the fix itself introduced them)
- **N1 (Low): the unit-class refusal lost its only killing test.**
  - The site is `cp2h.py:329`, `(text[-1] == "x") != (metric.unit_class == "multiple")`.
  - The pinned case `SOURCE_BREACHES["threshold_unit"]` (`tests/test_method_cp2h.py:993`, `Below  10.0x`) is now refused by the F1 grammar before the unit check runs. So deleting the unit check survives (M14).
  - The live code is still correct: it refuses `10.00x` on a percent metric and `2.8%` on a multiple one.
  - Fix: change the case to a grammar-valid form with the wrong unit, such as `Below  10.00x`.
  - Probe: P/n1_unit_check_unpinned.py, exit 1.
- **N2 (Low): the F1 grammar tests leave three parts of the grammar unpinned.**
  - `THRESHOLD_FORMS` (`tests/test_method_cp2h.py:1222`) does not pin:
    - the required integer digit for a multiple (M5, which accepts `.75x`);
    - the required integer digit for a percent (M6);
    - the sign on the percent branch (M7, which accepts `-10.0%`).
  - The code refuses all three (f1_grammar.py).
  - Fix: add `.75x`, `.5%` and `-10.0%` to the forms.

## For LEAD (ruled or unruled; not defects of this diff)
- **The B2 block end still drops later rows silently.** Any 0- or 1-field line inside a block ends it, as the ruling says. That includes a blank, whitespace-only or lone-CR line, a row separated by single tabs, single spaces, single NBSPs or ZWSPs, a one-field subheading, and a second header after a blank line.
  - With the first review's figure-free payload, the terms block then composes with "Triggers tested" 2 of 5, including both of Brook's terms, with no issue and no own line.
  - This is the failure class that B2's "Why" names. Probe: P/b2_ruled_residual.py, exit 1.
- **Order inside one block's rows step is unruled and untested.**
  - The code raises a breach before an earlier row's own issue. For example, `Unrecognised trigger metric` in row 1 plus a breach in row 5 gives `Trigger terms not found`. The same happens with an off-scale register rating (b2_order.py info lines).
  - M9 survives.
- **Invisible-only limitations pass B3.** A limitation of only ZWSP, BOM or soft hyphen is outside B3's `not text.strip()` wording, so it composes into the claim draft's limitation. Probe: P/b3_invisible_info.py, exit 1. The blank-text defect-class task may want to cover it.

## Standing rules
- The fix commits 87f2d9d and f843772 touch only cp2h.py and its test file. Neither lane merge touched the module or oracle files.
- There is no stub, fake value or catch-all. The only new raise is the invariant `ValueError` in `required_status`.
- The `test_facts` override substitutes exactly one cell, beside the strict xfail; that is documented as B7.

## Gates (target root)
| Gate | Result | Exit |
|---|---|---|
| pytest `tests/test_method_cp2h.py` | 185 passed, 1 xfailed | 0 |
| `ruff check` (both files) | clean | 0 |
| `ruff format --check` (both files) | clean | 0 |
| `MYPYPATH=src mypy --strict` (both files, cache in P/mypycache) | clean | 0 |

## First review's probes, rerun
- p01, p03 to p08, p10 and p12 exit 0.
- p02 exits 1 because F1 now refuses its form.
- p09 exits 1 because of the removed `cp1_status` argument; the ported copy exits 0.
- Their outputs are in P/first_*.out.

Not verified: the B7 outcome (the frozen `composer_only` cell is with LEAD); the builder and manifest sync for B1 and B2 (not run, read-only); how T2R.3 displays a percent threshold longer than 38 digits (only storage was probed); Stage 2 binding of real CP-1 and CP-2G heads; the full suite (only `tests/test_method_cp2h.py` was run, as instructed).
