# PT-CI-001 report

Implemented the approved TEST-METADATA repair in `tests/prompts/rule_lists.golden.json`: updated only `/sha256/oracles/cases~1cpl10-owner~1expected.json` from the stale pin to the independently reviewed CPL10 oracle digest.

- Worktree start verified: `a4549ed54d6dc8a00f50188757dbbdfbe09315a8`.
- Independent oracle SHA-256: `631f44385947f16cd9d0fa02e263ae5a8ce9eadfe194b0866dbd97febb08f48d`.
- Structural comparison: JSON parses; exactly one leaf differs; rules, cores, and all other oracle leaves unchanged.
- Targeted pytest: exit 0, 2 passed in 0.16s (digest pin and full rule-list metadata test).
- `git diff --check`: exit 0.
- Confidence review: `work/pretesting-completion/ci/PT-CI-001/confidence-review.md`.

Not run: full test suite, full CI workflow, source or product checks. No provider or credential activity. No integration performed.
