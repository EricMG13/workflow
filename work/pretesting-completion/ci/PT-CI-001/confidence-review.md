## Confidence review — PT-CI-001 golden oracle pin

Least confident about (ranked):

1. The replacement digest may not represent the adopted CPL10 expected oracle.
   investigated → Independently hashed `cases/cpl10-owner/expected.json`; SHA-256 is `631f44385947f16cd9d0fa02e263ae5a8ce9eadfe194b0866dbd97febb08f48d`, matching the reviewed frozen answer key and intended replacement.
   verdict → fine (the focused test compares the golden digest with `rules.golden_document()`; it passed).
   patch → replaced only the stale digest literal.
2. A broad golden refresh may have altered unrelated rule text or pins.
   investigated → Parsed base and edited JSON and compared structures; exactly one oracle digest leaf differs. `rules`, `cores`, and all remaining oracle entries are equal. `git diff` shows only the one literal.
   verdict → fine.
   patch → n/a.
3. The test result may be incomplete or hide an environment issue.
   investigated → The main project venv exists and ran both focused tests; captured pytest exit code 0, `2 passed in 0.16s`. The worktree has no local `.venv`, so the explicitly approved main environment was used with this worktree first on `PYTHONPATH`.
   verdict → fine for these focused comparisons; this does not exercise the full suite or CI workflow.
   patch → n/a.

Fixed: stale CPL10 expected-oracle digest pin.
Verified fine: exact JSON leaf-only change; rule list and other pins unchanged; targeted metadata and rule text comparisons pass.
By-design: no source, oracle, rule text, or other golden entry changed, as prescribed by the frozen remedy.
Still open: full project checks and CI workflow execution were not part of the scoped task.
