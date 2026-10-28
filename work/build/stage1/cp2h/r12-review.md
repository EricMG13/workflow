**Verdict: APPROVE.** I found no High or Medium finding. There is one Low and two Info notes, and none of them reopens review.

Target: commit add5fa8 in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb`, diff 128c3ca..add5fa8. That worktree stayed clean: `git status --short` showed nothing afterwards. Every run below used a full copy at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-r12-review/wt` with PYTHONDONTWRITEBYTECODE=1. The one exception is the author's `mutants.sh`, which makes its own copy.

## Spec verdict: PASS

**Negative constraints and diff ceiling**
- Only `src/deploy_workflow/owners/cp2h.py` and `tests/test_method_cp2h.py` changed. Nothing in `cases/`, `src/deploy_vii` or `methods/*.md` was touched.
- The diff is 186 added and 14 removed lines, about 200 in total, well under 800.
- B7 was left alone, as the brief says.

**1. B8 against the ruling**
- **The breach condition holds exactly** (`cp2h.py:244-248`). On a line that is not the block's width, `breached = len(fields) > 1 or any(len(_fields(later)) > 1 for later in rest[n+1:])`. The width is always 5 or 3, so a line of 0 or 1 field always ends the block. The breach is therefore "B2, or a later line of 2 or more fields on the page". A block that runs to the page end stays unbreached.
- **The text and its position are right.** `_rows` (`cp2h.py:371`) raises the block's pinned text. It is called at `cp2h.py:398-400` in the order scale, register, terms, and that order is unchanged. Two tests pin it: `scale_b8_before_register_b8` and `register_b8_before_terms_b8` (`tests/test_method_cp2h.py:1474-1481`).
- **All five "lane today" cases are refused** with `Trigger terms not found`. This holds both in `B8_BREACHES` (`tests:1417-1438`) and in the after-probe.
- **A header, then an end line, then rows is breached, not empty.** `_Rows.empty` (`cp2h.py:228-231`) is false when the block is breached. Each of the three `*_header_then_end_line` cases (`tests:1461-1472`) is paired with a second edit, so the expected text can only come from the rows step. My mutant `empty_ignores_breach` is killed.
- **The known limit holds.** `test_malformed_last_row_is_the_known_limit` (`tests:1504`) pins 4 triggers for both the tab and the single-space separators.
- **No frozen page breaches.** None of the 15 manifest pages does (positive, gap, boundary, register_not_found, terms_not_found), and s01 and s02 still have no header. Evidence: `after.out`.

**2. The two flipped round 11 tests**
- `test_term_block_ends_at_the_first_short_line` (`tests:1031`). Its old edit, an end line then a 5-field Zeta row, giving 5 triggers, is exactly what B8 now refuses. That edit moved to `terms_note_then_row`, so B8 supersedes it. The test still pins what remains true: notes of zero or one field after the end still compose, with 5 triggers.
- `test_one_field_line_ends_a_block` (`tests:1405`). Its old edit, a scale blank line then rows, giving `Rating not on the scale`, is the B8 scale case and now gives `Rating scale not found`. That edit moved to `scale_blank_line`, so B8 supersedes this one too. The remaining assertion, that the gap page:1 register reads 2, still pins an end at a one-field note.

**3. B9 is unchanged.** Only the `_rows` docstring changed. The rows-step order and the breach-first read are intact.

**4. B10**
- **Same frame and position.** `is_blank` replaces `not text.strip()` at `_prose` (`cp2h.py:1479`) and `_limitation` (`cp2h.py:1492`). Both keep the frame `<path>: empty text`, and `_limitation` keeps its `None` check before the blank check. `""` is still blank.
- **Field coverage is complete and the test is exact.** `BLANK_FIELDS` (`tests:1530`) lists all 10 paths. The coverage test (`tests:1561`) is a set equality, and a mutant that drops `action` from the list is killed.
- **Excluding `agency` is justified.** A blank or `Cf` agency (`""`, `"  "`, U+200B, U+FEFF) is already refused as `views[0].agency: not an agency in the rating register: …`. Removing the exclusion makes the coverage test fail (mutant killed).

**5. No stub, fake value or catch-all** in the diff.

## Quality verdict: PASS, with one Low

- **Low: the "any later line" part of B8 is not pinned beyond "next line only"** (rule at `cp2h.py:246`, cases at `tests/test_method_cp2h.py:1412-1482`).
  - In all 15 `B8_BREACHES` cases, every page's last line is row-shaped.
  - So a mutant that checks only the page's last line (`rest[-1:]`) passes the whole suite.
  - The code itself is correct: a row after the end that is followed by a trailing one-field note is refused with `Trigger terms not found`.
  - Probes: `review_mutants.sh` (mutant `after_last_line_only` SURVIVED) and `p_review_b8_last_line_and_coverage.py` part (a) for the behaviour, part (b) for the shape of the cases.
  - Fix: add a case such as `f"{LAST_TERM}\nEnd of terms.\nZeta  Watch  X  Over  1x\nSee page:1."`. It can ride with the next batch.
- **Info: the B8 rule is literally per page.** If two blocks ever shared one page, a block that ends at a blank line followed by the next block's header would breach. No frozen page does this (each block has its own page), and the ruling says "on that page". This is a note, not a defect.
- **Info: `run_in_place b2_ruled_residual.py` fails on import**, because the test module now imports `defect_classes`. The author's copy, and mine, add `ROOT/tests` to `sys.path`. Only the probe is affected, not the product.

## Probe and mutant exit codes

All files are under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-r12-review/`.

| Probe | Exit | Result | Output |
|---|---|---|---|
| `p_cp2h_b8_b10_after.py` (copy, pointed at the copy) | 0 | failures: none | `after.out` |
| `b2_ruled_residual.py` (copy) with `_probe_base.py` | 0 | all 4 variants give `Trigger terms not found` | `b2.out` |
| `author_mutants.sh` (the author's `mutants.sh`) | 0 | 7 of 7 killed; unmutated copy exits 0 | `author_mutants.log` |
| `review_mutants.sh` (my mutants) | 1 | 10 of 11 killed; `after_last_line_only` survived (the Low); unmutated copy exits 0 | `review_mutants.log` |
| `p_review_b8_last_line_and_coverage.py` | 0 | parts (a) to (d) as above | — |

Mutants killed in `review_mutants.sh`: `empty_ignores_breach`, `after_only_blank_end`, `after_only_note_end`, `after_any_line`, `after_whole_page`, `terms_rows_before_register`, `b10_isspace_only`, `b10_any_not_all`, `cov_drop_action_field`, `cov_drop_agency_exclusion`.

## Gates (on the copy, all exit 0)
- `PYTHONPATH=src … pytest -q -p no:cacheprovider tests/test_method_cp2h.py tests/test_defect_classes_selfcheck.py`: 512 passed, exit 0.
- `ruff check --no-cache` on both files: exit 0.
- `ruff format --no-cache --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0. I pointed its cache at the scratchpad so nothing was written into the copy.

Not verified: the full suite and other modules' tests; GitNexus impact and detect_changes; the `methods/cp2h.md` known-limit note and the manifest `parse_rule` text (release batch, out of scope); a page with two blocks on it, which no frozen or test page has; LEAD's original `p_cp2h_b8_b10.py`, which I did not rerun (only the inverted after-copy).