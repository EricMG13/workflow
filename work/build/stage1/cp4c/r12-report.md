CP-4C round 12 (Stage 1 implementer) report

Step 0: I entered worktree agent-a2c15c441717ec41c and ran `git merge --ff-only claude/round12`, which fast-forwarded ed1a721 to 128c3ca. HEAD = 128c3ca, as required.

**Commit:** babfd53 on branch `worktree-agent-a2c15c441717ec41c`. It changes 2 files, +168/-8:
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2c15c441717ec41c/src/deploy_workflow/owners/cp4c.py
- /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2c15c441717ec41c/tests/test_method_cp4c.py

**Code (cp4c.py `content_issues`, the #9 per-field loop)**
- One `is_blank(text)` check now runs first for every field kind (name, run and plain), before the name checks, `prose.issues` and `guard_issues`. A blank field gets `<path>: empty text` and nothing else. `""` is included.
- Both `not text.strip()` tests are gone; `is_blank` is imported from `deploy_workflow.owners.blank`.
- Blank text cannot match a guard phrase, so skipping `guard_issues` after the empty issue changes nothing else.
- B7: a new `_RESERVED = re.compile(r"[{}\[\]]")`. In the one-line name branch, after the `Bare figure` issues, a name holding a reserved character also gets `<path>: reference syntax is not allowed`. Both issues are reported, in that order.
  - The empty and one-line checks still come first and exclude the later checks, as before.
  - `|` is not reserved.
- I updated the `_text_fields` docstring.

**Each ruling with its test (all in test_method_cp4c.py)**
- **Round 11 blank class, R3 M2 and B10:**
  - `test_blank_fields_are_every_analyst_text_field` checks that the 36 paths equal `cp4c._text_fields` of the frozen positive submission, in order.
  - `test_blank_text_is_refused` runs BLANK_CASES × 36 fields through `blank_failure` with `EMPTY_TEXT`.
  - `test_empty_string_gets_the_empty_text_frame`: `""` gives exactly the frame on every field.
  - `test_blank_text_is_the_only_issue`.
  - `test_blank_text_twin_is_accepted`: real text, and text with a ZWSP inside it, is accepted.
  - Before the fix there were 229 refused-test failures:
    - 144 Cf cases (4 values × 36 fields);
    - 68 whitespace cases (4 values × 17 plain fields);
    - 17 `""` cases on the plain fields.

    The `""` frame test failed 17 times, all on plain fields. The twins passed. Every failure had the ruled cause.
- **B7:**
  - `test_b7_reserved_character_is_reference_syntax`: each of `{ } [ ]` in 3 positions, for `claims[1].name` and `valuation[0].label`.
  - `test_b7_comes_after_the_bare_figure_issues`: `Class 2 {x}` gives `Bare figure: 2`, then the reference issue.
  - `test_b7_empty_and_one_line_come_first`.
  - `test_b7_every_name_the_validator_accepts_composes`: every ASCII punctuation mark in 3 positions, plus `A | B` and `Loan (2027 notes)`, for both fields. A name is refused exactly when it holds a reserved character; otherwise it is refused only by `Bare figure` or it composes.
  - All of these were red before the fix, because the reserved names were accepted.

**Probes**
- <S>/stage1-end-R3/p_cp4c_blank.py, run against the worktree: exit 0, failures 0.
- LEAD's p_cp4c_b7.py, copied to <S>/cp4c-r12/p_cp4c_b7.py: exit 0. It reports "names tried 204; accepted-but-raising 0; outside the rule: none".
  - The copy points LANE at my worktree.
  - It adds `tests/` to `sys.path`, because the test module now imports `defect_classes`.
  - It also exits 1 if any accepted name raises. None does, so every name the validator accepts composes.
- **A-1 unchanged:**
  - <S>/cp4c-adversary/probe_alloc_reference.py at n=500: exit 0, with 0 mismatches on seeds 3, 4 and 20261028.
  - probe_hypothesis_big.py, copied to <S>/cp4c-r12/probe_hypothesis_big.py with `tests/` added to the path, at n=300 with seeds 1 and 2: exit 0. All 5 properties pass.

**Mutants** (<S>/cp4c-r12/mutants.py: a full temporary copy at <S>/cp4c-r12/copy with no .git, `PYTHONDONTWRITEBYTECODE=1`, pytest `-x`): exit 0. The unmutated copy passes, and all 9 mutants are killed (pytest exit 1):
- the B10 Cf revert (`not text.strip()`);
- the R3 M2 revert (no blank check on plain fields);
- `""` not refused on plain fields;
- B7 removed;
- B7 without `]`;
- B7 without `{`;
- B7 that also reserves `|`;
- B7 exclusive with `Bare figure`;
- B7 before `Bare figure`.

The brief's rule W mutants (minus space, parenthesis space) do not apply, because CP-4C has no quote-sign reader.

<S> = /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad

**Gates (all exit 0, first pass)**
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp4c.py tests/test_defect_classes_selfcheck.py`: 1374 passed. I re-ran it after the commit and it still passes.
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

**Not verified:**
- The full test suite and the other modules' tests were not run.
- GitNexus `impact` and `detect_changes` were not run; that is the controller's job.
- I did not re-run LEAD's B7 probe against the pre-fix code to reproduce its "30 accepted but raising". The B7 tests going red before the fix and the "B7 removed" mutant stand in for that.
- The A-1 probes ran only at reduced counts.
- Fields outside `_text_fields`, such as `period_column` and quote texts, are not analyst prose and were not given the blank or B7 checks.
- There is no `methods/cp4c.md` entry, because methods files are out of scope.

**Ledger:** `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`