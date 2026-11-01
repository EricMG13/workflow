# T3 fix round 2 brief (controller ruling; last Sonnet round)

1. N1: define D(P) = every directory component of P, the first included (`cases/PINS.json` -> `cases`). Rule 2's second clause uses D(P): a literal containing B together with a literal equal to or containing a name in D(P). Rule 4 keeps A(P) (first component excluded). Nothing else in the rules changes.
2. N2: put `# shellcheck disable=SC2086` directly above the pytest command line in pr.yml and pr-heavy.yml.
3. ruff SIM114 at affected_tests.py:172.
Process: commit 1 = a test only (`test(prove): split-path literal of a one-level file (RED)`): a temp repo where a test reads `ROOT / "cases" / "PINS.json"` and another file holds the literal "cases/PINS.json"; changing cases/PINS.json must select the first test. Commit 2 = the fix (`fix(prove): rule 2 counts the top directory (re-review T3 N1, N2)`). Both end with the Co-Authored-By line. Run every probe in scratchpad/t3-review/ and scratchpad/t3-rereview/ (python3 -I / sh) after commit 2 and report each exit code; all must exit 0 except probe_shellcheck_directive.sh may report shellcheck missing (say so).
