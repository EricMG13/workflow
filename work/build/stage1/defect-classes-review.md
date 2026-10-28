**Verdict: CHANGES REQUIRED.** One Medium finding (blank-text helper). Every expected outcome is correct. Two Low findings and two Info notes.

**Check 1: expected outcomes.**
- I wrote an independent reference reader from the ruling text. It covers the round 10 sign rule, the parenthesis rule, B1 edge cuts on all readings, and B3. I ran it over every figure case, every text case, and the labelled cases for both figures. It agrees with every `accepted` flag (0 mismatches).
- B1 start and end edges: all correct. `edge-end-decimal` (`25` from `25.5`) is right: the page text after the figure is `.` plus a digit, which B1's end rule refuses. `edge-end-digit` (`25` from `250`) is right: a digit follows.
- `edge-mid-*` is accepted, as the ruling's `mid-25` example requires. `edge-stop-*` (`25.` at the end) is accepted, which B1 allows ("nothing or only `.` after it").
- `wrap-split` matches B3 exactly: the quote is wrapped and `"- "` is in `normalise(value)`. `wrap-joined` is accepted correctly, because the quote has no wrap and the joined page reading contains it.
- Sign and parenthesis lists follow round 10. Not signs and accepted: `1-December`, `2024-2025`, `95-96`, `S-350`, `+25`, and `(25 percent)` with the `)` not directly after the digits. Refused: `-`, U+2212, en dash and em dash before a figure after a space, and `(25)`.
- `sign-label` (the label is followed by a signed figure, the unsigned value occurs elsewhere) is refused. That follows round 10 (`bid -95`) and the CP-8 "is not labelled" example. The refusal is the module's labelled frame, not "does not occur". The docstring only says "pinned refusal", so a module must pass the labelled frame there.

**Check 2: outcomes the rulings leave open.**
- None are encoded. `(2024)` before a word is correctly omitted: the ruling text is self-contradictory there, since the `)` directly follows the digits. The module docstring also excludes a value carrying its own soft hyphen and a joined value against a wrapped quote.
- No ruling example is missing. All of these are present: B1's `425`, `10 percent`, `-0.25`, `(25)` split in two, and the genuine edge figure and `mid-25` accepts; the four non-sign examples; `(1.80)`-style parentheses; `+`.

**Check 3: the twin check.**
- It is not vacuous: it fails if the twin's quote sits on the refused page and the values match. It is weak, though (Low, below).
- Probe `twin_and_blank.py` shows that a deliberately wrong "refused" flag on `sign-plus-25` (a case the ruling accepts) still passes the twin check.
- So the self-check catches a refused case that contradicts its twin. It does not catch a wrong expected outcome. The reference-reader probe is what supports the outcomes.

**Check 4: imports and collection.**
- `tests/defect_classes.py` imports only the stdlib (`collections.abc`, `dataclasses`, `typing`). No owner is imported.
- `pytest --collect-only` over the whole repo gives 0 nodes from `tests/defect_classes.py`. Only the self-check is collected (144 nodes).

**Check 5: blank text. The helper forces the frame for `""`.**

**Findings**
1. **Medium, `tests/defect_classes.py:324` and `:393`.** `BLANK_VALUES = ("", ...)` puts `""` in `BLANK_CASES`. `blank_failure` accepts only `expected in issues` and never makes an exception for `""`.
   - A module whose `Text` field keeps pydantic's `min_length=1` refusal of `""` (the controller's decision) will fail the `blank-0` case.
   - Probe: a reader that refuses `""` with a pydantic message and `   ` with `text: empty text` gets `blank-0 '': expected 'text: empty text', got [...]`.
   - Fix: split out `""`, or give `BlankCase` a `whitespace_only` flag, or let `blank_failure` take the module's `""` refusal. The helper then requires the frame only for `value.strip() == ""` with `value != ""`.
   - The self-check test `test_blank_cases_are_whitespace_only` (`tests/test_defect_classes_selfcheck.py:130`) and the module docstring need updating to match.
2. **Low, `tests/defect_classes.py:28`.** The docstring says every refused case has an accepted twin "with the same value". `wrap-split` has a different value (`first- priority` against `first-priority`), as do `sign-label` (value) and the edge cases (twin has a different quote). The self-check handles the value difference ("or the two values differ"), but the docstring is wrong.
3. **Low, `tests/test_defect_classes_selfcheck.py:55-66`.** The twin check only proves the twin's quote is not on the refused page. It does not prove the pair differs only in the defect. Edge-cut cases use the generic `genuine-N` twin, not the minimal twin (`edge-start-N` or `edge-end-N`, which exist as untwinned accepted cases).
4. **Info.** The self-check docstring promises a "refused case is a trap" check (`quoted(c.value, c.quote)`). That check holds for all cases, including edge cases whose quote is cut.
5. **Info.** `label_cases` raises on a figure outside `FIGURES`, so a module cannot run label cases on `0.25`. That is deliberate and documented.

No stub, fake value, or catch-all was found. The two helpers return `None` or a message, with no exception handling.

**Probes** (all under `<S>/defect-classes-review/`, where `<S>` is the scratchpad directory from the brief)
- `ref_reader.py`: exit 0. It runs the independent reference reader over every case.
- `twin_and_blank.py`: exit 1 by design. It shows the weak twin check (Finding 3) and the `""` blank failure (Finding 1).

**Gates** (target worktree at c032752; exit codes taken separately from the piped runs)
- pytest self-check: exit 0, 144 passed.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict`: exit 0, cache in scratch.

**Not verified:** I ran no owner module through the library. B1's check at every occurrence against wrapped quotes and wrapped pages is not covered by any case, and I only reasoned about it. The reference reader is my own reading of the ruling text, so an error in the rulings themselves would not show. The `[2024]`/`(2024)` parenthesis ambiguity is unresolved. I did not check the quote-normalise brief or the owner code.
