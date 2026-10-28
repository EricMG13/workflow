CP-1D class round (round 11 B1 edge cut, blank text, round 10 review Lows) is committed on `claude/cp1d-stage1` as **48267a0**. All gates exit 0 and all 21 mutants are killed.

**Commit:** 48267a0, parent 864ffe3 (the lane tip you accepted). Step 0 was a fast-forward from b7cd02e. Only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py` changed (+383/−20). No frozen pin moved.

**Class by class** (the library runs through an adapter in `tests/test_method_cp1d.py`, built on the gap pack's a04 made Partly supported + Recurring, with a one-span `defect` source):
- **Quote cases (`FIGURE_CASES`):** 44 cases apply; 12 cannot apply, and `test_defect_class_cases_not_applicable` pins that list:
  - accepted cases with a value of 0;
  - the refused soft-hyphen prefix case (CP-1D has no analyst figure to contradict);
  - accepted quotes that print two figures (exactly-one refuses them by design).
  - Each case also checks what `_basis_amounts` reads: the page's figure when accepted, `[]` for an edge cut, `-<v>` for a sign.
  - **genuine, soft_hyphen (inside), dashes, nbsp, signs and parentheses:** passed before the change and still pass.
  - **edge_cut: fixed.** 13 refused cases were red (including `edge-10`, `edge-minus-0.25` and `edge-end-decimal`) and now get the pinned exactly-one text. Accepted edge cases still compose.
- **Blank text (`BLANK_CASES` × 11 field paths):** fixed. This covers `assessments[0|3].rationale`, `assessments[0|2].limitation`, `overall.rationale/.limitation`, `gaps[0].{gap, why_it_matters, affected_analysis, action}`, and `overall.rationale` on statements_only (the path with no bridge).
  - Whitespace-only text now gets exactly `(<path>: empty text,)`.
  - `""` on a `Text` field keeps the schema refusal (`string_too_short`).
  - `""` on a `limitation` gets the frame.
  - `compute` raises on a blank field.
- **Extra B1 tests** for forms the library does not reach:
  - the joined page reading (a minus at a line end);
  - a wrapped quote found only once its wrap is joined (this also checks the end-edge offset shift);
  - `25` cut from `0.25`;
  - `25.` cut from `25.5`;
  - a cut at any one occurrence is enough;
  - twins where the figure is whole on the page.

**Code:**
- `_basis_amounts(citation, sources)` now drops an edge figure that some occurrence shows cut, so step 5 fires.
- An edge figure has nothing or only `-` before its digits, or nothing or only `.` after them.
- Occurrences are searched for both quote readings in both page readings. The page is found through `_cited_text`, the same lookup `citation_issues` uses.
- `_shape_issue` and `_outcome` now take `sources`.
- Blank-text issues are added at the end of `validation_issues`, in submission order.

**Decisions for review:**
1. **Quote not on its page.** I count its figures (no occurrence, so no cut), and the citation check refuses it. LEAD's `p_edge_pages.py` treats this case as not counted. My reading keeps the existing `_basis_issues` tests unchanged, and the submission is refused either way.
2. **Quote starting with `-25`.** Read literally, B1 gives exactly-one, not bounds, when the page prints a minus there. On `4-25` it reads `-25` and gives bounds. Either way it is refused; `test_edge_with_a_stop_or_a_sign` pins both.
3. **Where blank issues go.** They come last, after overall evidence citations; the rulings pin no position. `Bridge table not found` still returns alone. `addback` is left out (it is a bridge label, and a blank one gets `Unknown add-back`), as in the inventory.

**Riding items:**
- **1D7 before "above 0":** `test_unstated_amount_rule_precedes_the_bounds_text`. On gap a04, Partly supported and not Recurring, bases `-1.80`, `(1.80)` and `0` all get `Cannot accept an unstated amount` with no bounds text. It passed first, because the code was already right; it is what kills the mutant that moves the check.
- **`(` side required:** a new row `("saving 1.80)", ["1.80"])` in `test_basis_amounts_read_the_printed_sign`.

**Mutants:** `<S>/cp1d-class/p_class_mutants.py` exits 0. Each mutant runs in a full temporary copy of the worktree with `PYTHONDONTWRITEBYTECODE=1`; the unmutated copy passes (exit 0), and every mutant gives pytest exit 1:
- B1 removed;
- start-edge checks: `.`, digit, page minus, any hyphen treated as a minus;
- accounting parentheses;
- end-edge checks: digit, `.` plus digit;
- edge definitions: sign prefix, stop suffix;
- joined page reading dropped; joined quote needle dropped; end-edge shift dropped; first occurrence only;
- blank: removed, only `""` refused, limitations skipped, gap texts skipped, overall skipped;
- riding: the 1D7 order, the `(` side.

The first run had one survivor (the `.` start check), so I added the `0.25` row and re-ran.

**Other probe:** `<S>/cp1d-class/p_frozen_readings.py` exits 0. It reads every frozen CP-1D `accepted_basis` quote against the three packs (45 readings) and none moved.

**Gates** (all exit 0):
- `PYTHONPATH=src …/python -m pytest -q -p no:cacheprovider tests/test_method_cp1d.py`: 263 passed, 1 skipped (Stage 2/4).
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.
- Also run: `test_method_cp2g.py`, `test_method_cp2h.py` and `test_defect_classes_selfcheck.py`: 570 passed, 1 xfailed (an existing CP-2H B5 marker).
- Red first: 13 edge-cut and 51 blank assertions failed for the reported cause before the fix.

**Stage 2 notes for `methods/cp1d.md`** (listed, not written):
- the B1 edge rule: page readings, the decision on a quote not on its page, the leading-sign reading;
- the blank-text rule: the `<path>: empty text` fallback, `addback` excluded, issues placed last;
- the round 10 sign rule, still pending from the last round;
- the builder recipe text `$.refusal_rules.partly_supported` is still superseded and waits for the next CP-1D oracle batch.

Not verified:
- Only the three test files above ran: no full suite, no G1 or Stage 2 run.
- No real (non-synthetic) source text was used.
- One pathological case was reasoned, not tested: a raw quote whose own wrap sits right before its first digit (`-\n25`). Its plain reading is not an edge, but its joined reading would be.
- B3 is not CP-1D's class and was not applied: CP-1D reads no name or text value from a quote.
- No GitNexus `detect_changes` was run (I have no MCP index for this worktree).
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
