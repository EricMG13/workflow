# MODULES.csv fix round 1 (stage contract; mx-feature, docs only, exact edits)

Work in your existing worktree on `claude/s6-tail` (tip 381ede5). Edit only `docs/MODULES.csv`. Review: mx-precise REVISE (one Medium, three Lows folded here).

Make each edit as an exact string replacement limited to the named row (module id = first field). Each old string occurs exactly once in that row. Add no commas and no quotes.

## Edits
1. **CP-2H, rendering** (Medium: G2 never reads `status_chip`; the chip is tested only on the view model).
   - old: `; G2 cp2h and cp3d 27 passed exit 0 on 310a49c (s5-final2 j07; ledger 19:25) with the DR.6 Not computable chip drawn (OI-13 2d12ea5: Figure.status_chip; the xfail tripwire removed); the chip is verified only through these G2 tests: no native DOM check of the chip yet)`
   - new: `; G2 cp2h and cp3d 27 passed exit 0 on 310a49c (s5-final2 j07; ledger 19:25); the DR.6 Not computable chip (OI-13 2d12ea5: Figure.status_chip; the xfail tripwire removed) is checked by tests only on the view model (tests/test_chart_render_dr6.py; fast set j12) and no G2 test reads it; CHIP_DOM)`
   - Replace `CHIP_DOM` with the text in section "Chip DOM result" below.
2. **CP-2H, next_evidence**:
   - old: `a native DOM check of the DR.6 chip on a regenerated CP-2H page`
   - new: `NEXT_CHIP` (section "Chip DOM result").
3. **CP-1, validated_output** (Low 1: the blank-refusal tests are not in the fast set).
   - old: `fast set 10505 passed 19 skipped exit 0 at s5-final2 j12 on 310a49c (ledger 19:25)`
   - new: `the blank refusals by tests/test_source_context_blank.py in the open-items fast set (10538 passed 19 skipped exit 0 at 8dafc41; open-items ledger 13:58) and the precheck by tests/test_czr_fixes.py in the fast set (10505 passed 19 skipped exit 0 at s5-final2 j12 on 310a49c; ledger 19:25)`
4. **CP-1, validated_output** (Low 3: j01 shows the refusal, not the gap count).
   - old: `(item 75; j01 reproduced it after OI-14 and OI-20)`
   - new: `(item 75; j01 reproduced the same QA Blocked refusal after OI-14 and OI-20)`
5. **CP-DR, tool_execution** (Low 2: no exit code or SHA recorded).
   - old: `gave 341 passed on the lane and exit 0 per ledger item 76)`
   - new: `gave 341 passed on the lane (item 76; exit code and SHA not recorded))`

## Chip DOM result
- `CHIP_DOM` = `the drawn chip was checked in the built-in Chromium on regenerated cp2h-fp05-ratings positive and gap pages (G2 genuine deferred 2 passed exit 0 on 310a49c; ledger 21:51): one Not computable chip in the Front Page Rating triggers block head and none elsewhere; reached by a mouse click on the Front Page rail; the chip hit-tests to itself at 1440x900 (work/build/keep/s6dom/chip-check.md)`
- `NEXT_CHIP` = `a G2 test that reads the drawn DR.6 chip`

## Checks (report each output and exit code)
- Python is refused to you in this worktree; do not work around it. Instead run `awk -F, '{print NF}' docs/MODULES.csv | sort | uniq -c` (expect 11 for every line) and `git diff 381ede5 -- docs/MODULES.csv | grep -c '^[-+][^-+]'` (expect 6: three rows changed).
- One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Use plain `git add docs/MODULES.csv` then `git commit`.

## Output (return as text, under 300 tokens)
- tip SHA; the check outputs; a `Not verified:` line.

Never use bare `git stash`.
