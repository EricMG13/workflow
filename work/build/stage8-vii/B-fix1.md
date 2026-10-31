# B fix round 1 (mx-feature, resumed builder)

Same rules and files as `B-d1-d3.md`. Work on `claude/s8-vii-b` from 0a4917ed. Commits: `test: RED D1 fix 1` (tests only) then `fix: D1-D3 fix 1` (code only).

Review: mx-precise REVISE (spec ✅). Reviewer probes: `/private/tmp/claude-501/s8b/` (`probe_mypy.sh`, `probe_omitted_czr.py`).

## Findings (rulings by the controller)
- **M1 Medium (`statement_extract.py:304-309`).** The loop variable `line` is a `str` in the earlier loop and is reassigned to an `ExtractedLine`: 4 new mypy strict errors (base had 0). Fix: rename the later variable so mypy strict on the file is clean.
- **L1 Low (D1 rule, `statement_extract.py:228-233`).** A table separator row `- | - | -` becomes an omitted candidate.
  Ruling: a candidate must also hold at least one letter or digit, so a row of only nil dashes and pipes is never a candidate. A single labelled nil row (`"Goodwill  —"`) stays a candidate. Update the docstring's D1 sentence to say so.
- **I1 Info.** SIM905 at :83-85 (word sets built with `"…".split()`): write them as literal frozensets/tuples of strings; FLY002 in the test file (:18, :32, :107, :131): use the form ruff suggests only if it keeps the page text exactly as printed (the page lines must stay byte-identical); otherwise leave them.

## Tests
RED: `- | - | -` (and `| - | - |` if the pipe rewrite allows it) between data lines gives `omitted == ()`; `"Goodwill                           —"` still gives one `OmittedLine`. Every existing test stays green, including the golden test.

Report as before (SHAs, RED node ids, `Not verified:`).
