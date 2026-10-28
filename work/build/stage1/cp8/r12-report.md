CP-8 round 12 (rule W + B10) is done and committed. All gates exit 0. One change goes beyond the ruling's list of CP-8 sites, and LEAD or the reviewer should rule on it (item 3 below).

**Commit:** 8cecd09 on `worktree-agent-a3cc9818386e8861a` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a`. Step 0: the ff-merge of `claude/round12` gave HEAD = 128c3ca, as required. At that point there were 121 expected failures: 116 blank, 5 W. Files changed: `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py` only.

**Rulings and their tests**
1. **Rule W in `_SIGN`, the parenthesised arms and `_whole`.**
   - `_MULTIPLE` and `_DECIMAL` now read `(?:{_SIGN} ?)?`, and their arms are `\( ?… ?\)`.
   - `_whole` adds `(?<!{_SIGN} )` and the spaced-parenthesis lookahead `(?!(?:(?<=\()|(?<=\( )){v} ?\))`.
   - Tests:
     - The 5 library W cases now pass: size-level w-minus-space, w-minus-wrap, w-minus-nbsp, w-parens-wrap and w-edge-minus-space.
     - `test_r12_w_a_spaced_signed_observation_figure_does_not_occur`, `test_r12_w_a_spaced_signed_first_figure_after_the_label_is_not_the_value` and `test_r12_w_a_spaced_signed_size_level_does_not_occur`. These cover 6 spaced forms: `- `, U+2212 + space, `-`+NBSP, `( x )`, `( x)` and `(x )`.
     - `test_r12_w_the_whole_figure_reads_the_spaced_sign`. It includes the accepted cost: `95 - 96` is refused.
2. **The labelled W cases (dispatch notes).** `test_r12_w_labelled_realized_bid`, end to end through `realized_bid`:
   - Refused with the pinned `observations[6]: value_text 1.25 does not occur in the quote`: `bid - 1.25.`, `bid -\n1.25.`, U+2212 CRLF, `(-\n1.25)` and `(\n1.25)`.
   - The signed labelled figure (`bid - 1.25, against 1.25…`, plus its `-\n` and `(\n` forms) is refused with the pinned `…is not labelled loan_bid in the quote`.
   - Edge quotes after a page `- ` or `-\n` are refused.
   - Accepted twins: `bid 1.25.`, `bid \n1.25.` and `bid A-\n1.25.`.
   - All were red before the fix, except the `-\n` edge quote, which round 11 B1 already refused.
3. **Beyond the ruling's site list: `_wrap_split` (round 11 B3).**
   - The problem: after W, the library case w-minus-wrap-1.25 was still red on the size level. A size quote holding `-\n1.25` got `thesis.downside_sizes[0].quote: not a span of the recorded downside paths` before the level check. B3 counted the `- ` from normalising that wrap as a wrap split.
   - What I changed: the ruling says `-\n<digits>` after a space or at the start is a minus, not a hyphen wrap. So `_wrap_split` now ignores a `- ` that `_SIGN` reads as a minus with a digit next (`_W_MINUS = rf"{_SIGN} (?=[0-9])"`). `A-\n`, `first-\nline` and `is -\nline` (no digit) still count as wrap splits.
   - Side effect: a text value such as `is - 1.25` on a page printing `is -\n1.25` now passes the occurrence step in decision text, flag spans and size spans. Before, B3 refused it.
   - Test: `test_r12_w_a_wrapped_minus_is_not_a_wrap_split`.
4. **B10.**
   - `_text` (cp8.py:590) and `_decision_text` (:630) now call `is_blank`, keeping the pinned frame `<path>: text is empty`.
   - I applied it also to the `flag_quote` blank check (:898, frame `Flagged Risk Materialized needs flag_quote`). On the lane, a U+00AD flag_quote was accepted, because it normalises to "", which counts as a span of anything. A U+200B, U+FEFF or U+2060 flag_quote got the span refusal instead.
   - Tests: the 116 `test_r11_blank_text_gets_the_pinned_frame` cases now pass. `test_a_blank_flag_quote_is_refused` now runs over BLANK_CASES; blank-5 to blank-8 were red before.

**Mutants** (`<S>/cp8-r12/mutate.py`, full temporary copy, PYTHONDONTWRITEBYTECODE=1): exit 0. The unmutated copy passes, and every mutant is killed (pytest exit 1):
- W minus space in the labelled reader, and in `_whole`;
- W parenthesis space in the labelled reader, and in `_whole`;
- the `_wrap_split` exemption;
- the B10 Cf test at all three sites together, and at each site alone.

Output is in `<S>/cp8-r12/mutate.out`.

**Probes**
- **LEAD `p_sign_breaks.py`**, copied with LANE pointed at my worktree (`<S>/cp8-r12/p_sign_breaks.py`, output `.out`): exit 1. Every failure is a part A or C check that assumes the pre-W code, for CP-8 and CP-1D (CP-1D's W is already in `claude/round12`).
  - For CP-8, the code now equals the W reference on every class case and control: 11 refused, 4 accepted.
  - The CP-8 end-to-end realized_bid case `bid -\n1.25.` is now refused with `observations[6]: value_text 1.25 does not occur in the quote`.
  - Part D: CP-8's 40 frozen triples are unmoved, with no disagreement on frozen.
  - Part E: W=0.
- **`<S>/cp8-class-review/p_unpinned_linebreak_minus.py`:** exit 1. Its pinned expectation is the pre-W behaviour, which W reverses on purpose: A (`bid -\n1.25.`) and B (`bid (-\n1.25).`) are now refused. Controls C (refused) and D (accepted) are unchanged.
- **New `<S>/cp8-r12/p_flag_quote_cf.py`:** exit 0 (it was exit 1 on the lane).

**Gates** (all exit 0):
- `pytest tests/test_method_cp8.py tests/test_defect_classes_selfcheck.py`: 750 passed.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both changed files.
- `tests/test_host_h1.py`, which imports cp8: 37 passed.
- `tests/test_method_cp3d.py` still has its 124 expected round-12 failures. That is not my module.

Not verified: the `methods/cp8.md` guard-limit note for W (left to the controller, per the Rules); GitNexus impact and detect_changes (the controller's step); the full suite and CI. The `_wrap_split` change in item 3 is my derivation from the W ruling and has not been ruled on.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`. It is `n` because w-minus-wrap-1.25 stayed red after the ruled sites were changed, until the `_wrap_split` change.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`