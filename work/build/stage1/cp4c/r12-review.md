## CP-4C round 12 adversarial review (babfd53 against 128c3ca)

**Verdict: APPROVE.** The change does what B10, R3 M2 and B7 require, and I found no stub, fake value or catch-all. I found no High or Medium in the diff. There is one Medium that predates the change: it goes to the owner, with a question for LEAD. There is also one Low test gap and two Info items.

I ran everything from `git archive` copies of babfd53 and 128c3ca under `<S>/cp4c-r12-review/{copy,parent}`, with `PYTHONDONTWRITEBYTECODE=1` and `python -I -B`.

### Checks
1. **B10 / R3 M2 (blank text).**
   - At cp4c.py:935, `is_blank` runs first for every kind of field and `continue`s.
   - I tried 25 blank values on all 36 `_text_fields` paths. The set was `""`, whitespace, NBSP, U+2028/2029, U+3000, U+200B, U+FEFF, U+00AD, U+2060, U+180E, U+061C, a tag character, and mixes. Every one gives exactly `(<path>: empty text,)`.
   - Skipping `guard_issues` and `prose.issues` after the blank issue loses nothing: both return `()` on every blank value. The "blank not exclusive" mutant is equivalent and survives, which confirms it.
   - With several blank fields, the issues come out in field order. A `High` confidence issue still comes before them.
   - Probe `p_blank_exact.py`: exit 0.
   - `_text_fields` covers every analyst prose field. I walked every `str` leaf of the positive payload (`p_fields_schema.py`, exit 1, on the finding below). Every other uncovered field (ids, case ids, `period_column`, locators, source ids, treatment class ids, the `amount_quote` quote) is refused when blank, by its pattern or its own check.
2. **B7 (reference syntax).**
   - The check sits at cp4c.py:946, inside the one-line branch, after `Bare figure`. Both issues are reported, in that order. `|` is not reserved, and the frame matches CP-8 expected.json:9019 word for word.
   - `p_b7_break.py` (exit 0) tried 47 names on all 6 slots (`claims[0-2].name`, `valuation[0-2].label`). They included every combination of `{ } [ ]`, a full `{T4E.3.v01.ev|US$ m}` reference, full-width and other non-ASCII brackets, full-width digits, control and Cf characters, names of 400 and 1200 characters, label-like digits, and `{{FIG:x|y}}`.
   - Every name with a reserved character gets the issue, as its last issue. No other name gets it. Every name the validator accepts composes.
   - `p_b7_sanity.py` (exit 0) confirms that accepted non-ASCII bracket names appear in the composed claims.
   - Reserved characters in plain and run fields: plain fields accept them and compose. Run fields get the existing `prose` issue (`p_plain_reserved.py`, exit 0).
3. **Frozen cases.** Only the two named files changed; `cases/` is untouched.
   - `p_frozen_parity.py` (with `p_frozen_dump.py`), exit 0: all 40 frozen refusals and all 5 cases give the same issues, claims, own limitations and cell records as the parent.

### Findings

**Medium. Predates this change; owner. Unruled whether a quote is an "analyst text field"; LEAD.**
- **Where:** cp4c.py:779-787, the `claims[i].support[j]` loop. `q.quote not in page` passes trivially for a blank quote.
- **Input and output:** I set the positive payload's `claims[0].support[0].quote`.
  - `""`: the validator returns `()`. `compute` then raises a pydantic `ValidationError` (`Citation.quote` has `min_length=1`). So the validator accepts what `compute` refuses, and the raise is not the module's ValueError invariant.
  - `" "` or `"\n"`: accepted. The composed cell then carries a citation whose quote is `" "`, which is a fake citation.
- **Rule it may break:** round 11 "every analyst text field in every owner refuses whitespace-only text". The parent behaves identically.
- **Probes:** `p_blank_support_quote.py`, exit 1 on both the target and the parent; `p_fields_schema.py`, exit 1.

**Low. Test gap; rides with the next fix.**
- **Where:** tests/test_method_cp4c.py. No test pins that a plain field holding `{` or `[` is accepted.
- **Evidence:** a mutant that also applies the B7 refusal to plain fields survives the module test (`p_mutants_extra.py`, exit 1).
- **Why it matters:** B7 names only "a claim `name` or valuation `label`", so this over-reach would refuse valid limitations and nothing would catch it.

**Info (LEAD, unruled).**
- A name that spans more than one line and also holds a reserved character gets only `one line only`; the B7 issue is not added (`{\n}`, `[ ]`). This mirrors round 11 B3's exclusive structure. B7's "in this order" does not say whether the checks are exclusive.

**Info (LEAD, unruled, affects every module).**
- Some invisible characters are not blank under B10, so a gap text holding only one of them is accepted with `()`. Examples: `\x00` and `\x07` (Cc), U+034F and U+FE0F (Mn), U+3164, U+115F and U+FFA0 (Lo), and U+2800 (So).
- This conforms to the B10 definition ("whitespace or `Cf`").

### Probe exit codes
- Gate (`pytest` on test_method_cp4c, test_defect_classes_selfcheck and test_owner_blank, run in the copy): **exit 0**, 1395 passed (`<S>/cp4c-r12-review/gate.out`).
- `<S>/stage1-end-R3/p_cp4c_blank.py`: exit 0 on the target (0 failures); exit 1 on the parent (27 failures).
- LEAD's B7 probe as `<S>/cp4c-r12-review/p_cp4c_b7_copy.py` (LANE taken from argv):
  - target: exit 0 (204 names, 0 accepted but raising);
  - parent: exit 1 (30 accepted but raising, all holding a reserved character), which reproduces LEAD's count.
- `<S>/cp4c-r12/mutants.py`: exit 0; all 9 mutants killed.
- `<S>/cp4c-r12/probe_hypothesis_big.py` (n=300, seeds 1 and 2): exit 0; all 5 properties pass.
- My probes, all under `<S>/cp4c-r12-review/`:

| Probe | Exit |
|---|---|
| `p_blank_exact.py` | 0 |
| `p_b7_break.py` | 0 |
| `p_b7_sanity.py` | 0 |
| `p_plain_reserved.py` | 0 |
| `p_frozen_parity.py` | 0 |
| `p_fields_schema.py` | 1 (the Medium) |
| `p_blank_support_quote.py` | 1 (the Medium) |
| `p_mutants_extra.py` | 1 (the Low, plus 1 equivalent mutant) |

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: I did not run `ruff`, `mypy` or the full suite. I did not check whether the host refuses a blank support quote before CP-4C sees it. I did not check how Stage 2 renders braces in limitations or table labels. I did not re-run the A-1 `probe_alloc_reference.py`. I ran LEAD's `p_cp4c_b7.py` only as a copy pointed at the review copies, not unmodified, because its hard-coded LANE names another worktree.