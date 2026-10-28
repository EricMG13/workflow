# Stage 1 layer review, group C (CP-3D, CP-DR, CP-4, CP-3): mx-architect, controller-saved

## Branch
`worktree-agent-a6fe6bee590a3ee10`. Merged into the lane at b97c735, which brings in the CP-3 Stage 1 build 6ce4dd1.
- `777562f` is the lane tip 348799d plus a merge of 6ce4dd1.
- `db86798` adds the CP-4 casefold test and the CP-3 oracle pin test, and fixes seven mypy errors in `tests/test_method_cp3.py`.
- `bb79483` adds oracle pin tests for CP-3D and CP-DR.
- No `src` change.

**Probes:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage1-review-C/`

## Findings
### Medium, for LEAD
- **C-3D-1.** `cp3d.py:1423` emits "Single dealer quotation; the sheet reports no trade in the period to the quotation date" for every submission that has a market source.
  - **The problem:** the oracle pins this sentence only for the positive case. It contradicts the X1 (iii) talk-only LVL-01 text, and it is false for a sheet with two dealers or a reported trade.
  - **Probe:** `probe_cp3d_single_dealer_limitation.py` exits 1, so the contradiction is reachable.
  - **Fix:** LEAD to rule when the sentence applies.

### Low, fixed in this review
- **C-4-1.** The `lower_not_casefold` mutant now dies: `test_semantic_gate_case_folds_rather_than_lowercases_page_text` (tests/test_method_cp4.py:613). Probe: `probe_cp4_casefold_mutant.py`.
  - **Note:** pyproject sets `pythonpath = ["src", "."]`, which shadows a plain `PYTHONPATH` mutant run. An earlier mutation probe that used PYTHONPATH alone may have tested the original code, so its surviving-mutant counts are suspect. Killed counts are unaffected.
- **C-3-1.** The CP-3 oracle had no pin test. Added `test_oracle_files_are_the_pinned_revision`, red against the superseded manifest.
- **C-3-2.** `mypy --strict tests/test_method_cp3.py` gave 7 errors at 6ce4dd1. The CP-3 report's "0" covered src only. Fixed mechanically.
- **C-3D and CP-DR pins.** Added `test_oracle_files_are_the_pinned_revision` to both, using the lease-header hashes. CP-DR uses expected 36572c50….

### Low, for LEAD
- **C-3D-2.** A 4-digit margin is refused with the misleading pinned text "bps_text … does not occur in the quote": `cp3d.py:150` allows 1–3 digits, while :442 bounds the level to (0, 200]. Probe: `probe_cp3d_unpinned_level_bound.py`.
- **C-3D-3.** The prohibited-conclusion guard (`cp3d.py:581`, :612) checks only `technicals[i].text` and `summary.text`.
  - Fields not covered: `recovery.rationale`, `technicals[i].limitation`, the absence reasons and `instrument.name`.
  - CP-2A A3 widened the analogous guard.
  - Probe: `probe_cp3d_prohibited_scope.py`.
- **C-DR-1.** `cpdr.py:437` orders TDR.1 rows by submission order, not agenda order. Ruling R2 orders rule 2 but says nothing about the table. Probe: `probe_cpdr_gap_row_order.py`.
- **C-DR-2.** R4 and R5 are carried into the CP-DR round 5 follow-up.

### Stage 2
- **C-3-3.** The CP-3 test invents the CP-1 binding: label, period and `T4.10.<name>.ltm_q4_2025` (tests/test_method_cp3.py:142-149). CP-4 instead uses the oracle's `predicate_facts`.
  - Stage 2's adapter test must assert the real label and period.
  - Optionally, LEAD pins `predicate_facts` in the CP-3 oracle.

### Info and owner
- CP-4 T4C.7 `threshold_value` is shown as typed (`cp4_legal.py:546-554`); this is for the owner.
- The CP-3 module is thin and correct, and `CP3Inputs` mirrors the engine's `Upstream`.

## Calculation, inputs, boundaries
- **CP-3D:** Method 1–6 matches, including quantisation and the None and not_applicable rules.
- **CP-DR:** the 4 dp share and the empty agenda (not_applicable, never 0) match.
- **CP-4:** the gate runs before the engine.
- **Inputs:** every field can be bound.
- **Boundaries:** no I/O, no float or round, and no G1-X §2 clashes.

## Cross-group inconsistencies (report only)
1. Not-meaningful wording differs from the `(ZERO_OR_NEGATIVE_DENOMINATOR)` form; it is pinned per lease.
2. The prohibited-phrase guards differ in scope and matching.
3. The Decimal-context style differs.
4. Ownership of `shown` differs: CP-3D spells it in src (and hardcodes `∅ G#`), while CP-DR leaves it to the renderer.
5. Oracle pin tests now exist in CP-4, CP-3, CP-3D and CP-DR. The other groups may want them after the methodology re-pins.

## Reviews
- confidence-review ran inline and left nothing open.
- rewrite-tournament ran inline; the incumbents hold (`cp3d._point`, `cpdr.validate_research`).

## Tests and gates
| Module | Tests | ruff check | ruff format | mypy --strict |
|---|---|---|---|---|
| CP-3D | 183 passed | 0 | 0 | 0 |
| CP-DR | 48 passed | 0 | 0 | 0 |
| CP-4 | 23 passed | 0 | 0 | 0 |
| CP-3 | 32 passed | 0 | 0 | 0 (7 errors at 6ce4dd1) |

Not verified:
- Stages 2–4;
- the real CP-1 label and period for CP-3, and the real `cp4_upstream`;
- the CP-3D yield path on a real level;
- the rewrite-tournament ran inline, not as the skill's sub-agent roles;
- no heavy suites.

agent=mx-architect fix-rounds=0 gates-first-pass=n
