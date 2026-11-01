# D12 final: re-cut the records on the final tip (stage contract; mx-scaffold)

Rules: `common.md` beside this file, except: step 0 is `git checkout -b claude/s8-vii-d12b <TIP>` (`<TIP>` given in the dispatch); edit only `docs/reuse/manifest.json`. Use only git and system `python3 -I` with the stdlib.

1. `git cherry-pick bc081983` (the 13 records written earlier from `D12-brief.md`; it applies cleanly: no manifest change since). Keep its message.
2. Append one more record, after the 13, in a new commit `docs: D12 record for D2/D3 fix 2` (never amend), with the same field rules as `D12-brief.md`:
   - commit `6673b51a` (resolve the full sha with `git rev-parse 6673b51a`), destination `src/deploy_vii/statement_extract.py`;
   - reason: `D2/D3 fix 2 (s8-vii B, whole-branch review): a footnote marker must also end left of the leftmost header year column; note/notes are header words.`;
   - review: `"docs/rulings/2026-10-31-s8-vii.md"`.
3. Run `python3 -I work/build/keep/s53-B/probe_d12_strict.py "$(pwd)" 5a1d2e2f HEAD`; it must exit 0. If not, fix with a further commit `docs: D12 records fix` and rerun.

Report as text (under 200 tokens): SHAs, probe exit code and its last 6 lines, `Not verified:`.
