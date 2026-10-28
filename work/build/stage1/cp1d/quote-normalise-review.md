# CP-1D raw-quote fix review (mx-precise; controller-saved)

## CP-1D quote-normalise fix review (commit 7c88a98, diff c8dbd05..7c88a98)

**Verdict: APPROVE.** I found no High, Medium or Low findings.

### Spec verdict: PASS
- **Allowed files only.** The diff touches only `src/deploy_workflow/owners/cp1d.py` (+3/−2) and `tests/test_method_cp1d.py`. `git diff --stat c8dbd05 7c88a98 -- cases src/deploy_vii` is empty, so no frozen file was edited.
- **Fix shape.** It matches the brief: the read now runs on `quotes.normalise(quote)` and adds no new wording.
- **Check 1, the fix is correct and complete.** I read the file myself, not the report.
  - `_basis_amounts` (cp1d.py:503-506) is the only place that reads an analyst quote's text. Its four callers are :533 (Recurring kept basis), :541 (source path), :570 (shape count) and :573 (bounds amount).
  - The other `quote` uses are not reads of an analyst quote after a match:
    - `_cite` (:765) builds citations from `item.line`, which is span text Python made.
    - :816-825 stores the citation as given, without reading it.
    - :883 joins only source_id and locator.
- **Check 4, the dash and minus guard asserts the ruled r18 text.** test_method_cp1d.py:717-719 expects "Accepted basis quote must contain exactly one amount: Procurement programme savings". That is the same text as cases/cp1d-owner/expected.json:284, submissions.json:3169 and builder/build.py:373.
- **Check 5, no frozen outcome changes.** The full CP-1D file passes, including the oracle-equality tests.

### Quality verdict: PASS
- **Check 2, "no wrong value could be stored, only false refusals".** I tried to break this claim and it holds.
  - **Why it holds.** `_AMOUNT` reads only ASCII digits and `.`, so only deleting U+00AD can change the result, and it can only join adjacent runs. Mapped dashes, the minus sign, quote marks and whitespace collapse never delete a digit or a `.`, and neither do hyphen-wrap joins (the hyphen is kept). So when the raw quote has exactly one amount, the normalised quote has the same one.
  - **Wrap-joined needle.** It holds the same amounts as `normalise`, so reading the plain normalised text is right even when the match was made through the joined quote.
  - **Widening.** Some quotes the old code refused for holding two amounts are now read as one, for example `1­2` read as `12`. That is exactly the text `citation_issues` matched against the normalised page, so the composed amount is the one the matched page text states. This is the intended behaviour, not a defect.
  - **Probe.** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-quote-review/p_reading_agrees.py`, exit 0. It checked 300,000 random quotes built from digits, `.`, U+00AD, all of `_DASHES`, NBSP, newlines, `-\n  ` wraps and letters. It found no case where a single raw amount differs from the normalised reading, and no case where `_needles` disagrees with `normalise`. 3,042 quotes are newly read as one amount, which is the intended widening.
- **Check 3, each new test fails without the fix, for the stated cause.**
  - I reverted the fix in the scratch copy at `.../scratchpad/cp1d-quote-review/worktree-copy`. That is a temporary copy, not the worktree. 7 tests then fail:
    - the 3 composes-the-page-amount cases and the recurring `0.­20` case, which gain the shape refusal "Accepted basis quote must contain exactly one amount";
    - the 3 bounds cases, where the shape text replaces r17's bounds text.
  - Those are the stated causes. The dash guard passes with or without the fix, as the report says it should.
  - The `2­026` comment, "the first run (2) would compose", describes only the bounds-only mutant. That mutant does kill it (2 failed).
- **Check 6, stubs and catch-alls.** None in the diff. `_replaced` asserts that the substitution happened, so a test cannot silently run with no edit made.
- **Info.** The signed-amount defect reproduces: a page line `-1.80` composes 1.8. It predates this change, is out of scope and is already with LEAD.

### Probe and mutant exit codes
- **mutate.py: exit 0.** I ran it with the review dir as its scratch, and the copy's `src` was the one imported.
  - control: 16 passed;
  - revert: 7 failed;
  - :541: 2 failed;
  - :533: 1 failed;
  - :570: 7 failed;
  - :573: 2 failed.

  Every mutant was killed.
- **p_signed_basis.py: exit 1, as expected.** It reproduces the pre-existing sign defect (composes 1.8). My first call omitted the worktree argument and exited 1 with an IndexError. I reran it with the argument and got the real result.
- **p_reading_agrees.py (mine): exit 0.**

### Gate exit codes (from the target root)
- **pytest on tests/test_method_cp1d.py: exit 0.** 111 passed, 1 skipped (the Stage 2/4 placeholder).
- **ruff check on both files: exit 0.**
- **ruff format --check on both files: exit 0.**
- **MYPYPATH=src mypy --strict on both files: exit 0.**

ruff and mypy are not on PATH, so I ran them from `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/`. The first attempt on bare PATH exited 127 because the commands were not found.

Not verified: the full suite and other owners' tests, which the brief said not to run; non-ASCII digits, which `_AMOUNT` ignores and which is not normalisation-class; a quote that starts in the middle of a page number (`1.80` cited out of `11.80`), which is pre-existing and not caused by normalisation; that shape issues pre-empt `citation_issues` (cp1d.py:1563-1569), which only changes which of two refusals is reported; Stage 2 citation checks and rendering of a basis citation that holds U+00AD; GitNexus detect_changes.
