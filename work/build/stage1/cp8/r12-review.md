**CP-8 round 12 review: commit 8cecd09, diff 128c3ca..8cecd09. Verdict: FINDINGS (one Medium, one item for LEAD).**

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r12-review/`, called `R/` below. They ran against full archive copies: `R/copy` (8cecd09) and `R/parent` (128c3ca), with PYTHONDONTWRITEBYTECODE=1.

## Spec verdict: PASS on every ruled site; one unruled change needs LEAD

- **Rule W, `_MULTIPLE`/`_DECIMAL` (cp8.py:128-129).** The patterns are `(?:{_SIGN} ?)?…` and `\( ?… ?\)`, as round 12's CP-8 text requires.
- **Rule W, `_whole` (cp8.py:402-408).** It equals the ruled fixed-width exclusion `(?<![0-9.])(?<!…-)(?<!…- )`, plus the spaced-parenthesis exclusion.
- **Plain and joined readings agree on sign.** I fuzzed the real `_whole`, `_DECIMAL` and `_MULTIPLE` on 20403 random wrapped texts and found 0 disagreements. 17 hand cases (`A- 1.25`, `95 - 1.25`, `( 1.25)`, `(1.25`, `S- 1.25`, `+ 1.25`, …) all read as ruled. Probe: `R/p_fuzz_readings.py`, exit 0.
- **B10.** `_text` (:590) and `_decision_text` (:630) call `is_blank` at the same position with the pinned `<path>: text is empty`. Extending it to `flag_quote` (:898, `Flagged Risk Materialized needs flag_quote`) is correct. That line was already CP-8's blank check for this analyst text field, and B10 says "each module's existing blank check" under round 11's one blank class. On the lane, a U+00AD flag_quote normalised to "" and was accepted, so this change closes a real hole. Probe: `cp8-r12/p_flag_quote_cf.py`, exit 0.
- **Scope.** Only the 2 allowed files changed (140 lines). Nothing under `cases/`, `deploy_vii` or `methods/` was touched. No new xfail, skip, catch-all, stub or fake value. The frozen `expected.json` cases pass inside the gate.
- **Unruled `_wrap_split` change (cp8.py:444-448).** See the Medium finding and the LEAD item below.

## Quality verdict: FINDINGS

**Medium: the `_wrap_split` W exemption reads the minus on the value, not on the quote, so a value that starts at a hyphen wrap escapes B3.**
- **Location:** cp8.py:130 and :448. The code is `_W_MINUS.sub("-", normalise(value))`, where `_W_MINUS = rf"{_SIGN} (?=[0-9])"`.
- **Cause:** at index 0 of the value, the `(?<![A-Za-z0-9])` lookbehind always succeeds. It never sees the page character before the `-`.
- **Inputs and wrong outputs:**

| Field | Cited quote / downside | Value | 8cecd09 | 128c3ca |
|---|---|---|---|---|
| `decision.instrument` | `The instrument is Term Loan A-\n1.25 notes.` | `- 1.25 notes` | `()`, accepted | `decision.instrument: text - 1.25 notes does not occur in the quote` |
| `decision.instrument` | page `…2024-\n2025 notes.` | `- 2025 notes` | accepted | refused |
| flag span | downside `…A-\n1.25 notes default.` | `- 1.25 notes default` | pinned span issue missing | pinned span issue present |
| size span | same | same | pinned span issue missing | pinned span issue present |

- **Rulings broken:**
  - Round 12 W: "After a letter or digit (`A-\n25`, `2024-\n2025`) it stays a hyphen wrap, which is not a sign."
  - Round 11 B3: "the value does not occur in the quote."
- The accepted text also spells a page hyphen as a minus before a figure.
- **Probe:** `R/p_wrap_split_edge.py`: exit 1 on the copy, exit 0 on the parent (`.copy.out` and `.parent.out`).
- **Fix that fails closed:** exempt a `- ` only when a non-alphanumeric character inside the value comes before it. A `-` at value index 0 then stays a wrap split. Better still, drop the exemption entirely (next item).

**For LEAD: is the `_wrap_split` exemption implied by W? Not clearly.**
- **Why it is not clearly implied:**
  - W is a figure-sign rule: "applies in the four quote readers only".
  - B3 is a text-spelling rule, and says "Figures are unaffected".
  - `quotes.hyphen_wrapped` and the joined reading still treat ` -\n1.25` as a wrap that joins to `-1.25`. So `is - 1.25` is still a spelling the joined page does not print, even though both readings give the same sign.
- **Inconsistent with the siblings.** CP-3D `_name_occurs` (cp3d.py:268-271) and CP-2E `_split` (cp2e.py:649) keep B3 strict after their W builds. A CP-3D name `X - 1.25` on a wrapped quote is refused, while CP-8 now accepts the same text. Round 11 says one class rule.
- **Why the change was made.** It only exists to turn library case `w-minus-wrap-1.25` (size level) from the span refusal into the level refusal. Both are refusals, so B3 strict is not a bypass.
- **Fail-closed alternative:** revert the exemption (keep B3 as ruled). LEAD then rules that for CP-8 size level, `w-minus-wrap-*` is satisfied by the earlier true refusal `thesis.downside_sizes[0].quote: not a span of the recorded downside paths`, or it is excluded through the adapter as `held()` does. This needs a LEAD ruling either way.

No pre-existing (owner) defects found.

## Probes and mutants

| Probe | Exit | Note |
|---|---|---|
| `cp8-r12/mutate.py` (rerun on `R/copy`) | 0 | Unmutated copy passes; all 9 mutants killed (`R/rerun_mutate.out`). |
| `cp8-r12/p_flag_quote_cf.py` | 0 | |
| `R/p_sign_breaks_cp8.py` (LEAD's probe, LANE pointed at the copy) | 1 | Reversal on purpose (below). |
| `cp8-class-review/p_unpinned_linebreak_minus.py` | 1 | Reversal on purpose (below). |
| `cp8-class-review/p_edge_refute.py` | 1 | Reversal on purpose (below). |
| `R/p_edge_refute_w.py` (its reference amended by W, a superset of the same seed) | 0 | 22096 pairs, 0 disagreements. |
| `p_b3_owner_built`, `p_blank_exit_trigger`, `p_frozen_on_page`, `p_overlap_mutant` | 0 | |
| `R/p_fuzz_readings.py` | 0 | |
| `R/p_wrap_split_edge.py` | 1 | The Medium. |

The three exit-1 probes from earlier rounds fail only where W reverses them, as ruled:
- **`p_sign_breaks_cp8.py`:** every failure is a part A or C expectation of pre-W code. D shows 40 CP-8 triples unmoved; E shows W=0 disagreements.
- **`p_unpinned_linebreak_minus.py`:** cases A (`bid -\n1.25`) and B (`(-\n1.25)`) are now refused. These are round 12's class cases "`-\n` with the quote spanning the break" and "`(-\n`".
- **`p_edge_refute.py`:** its 78 disagreements are all explained by W, because the W-amended reference has 0.

## Gates (run once in `R/copy`, all exit 0)
- pytest on `test_method_cp8.py`, `test_defect_classes_selfcheck.py` and `test_host_h1.py`: 787 passed.
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

Not verified: the full suite and CI; GitNexus impact; any CP-8 text field other than the instrument decision field, flag span and size span for the Medium (by reading, decision_maker_role and the other decision text fields take the same path); the fuzz covers only my listed alphabet; the `methods/cp8.md` W guard-limit note (the controller's Stage 2 step).