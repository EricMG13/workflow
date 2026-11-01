# Scoped re-review of branch-review fixes (mx-precise; saved by the controller)

Verdict: PASS with notes. M1 PASS (probe_compare vs OLD and FD: 0 dropped; probe_ignored_readers 0; distribution >20: 0; pytest 34 passed). 50 FLAG lines: none a real reader lost (scratchpad/m1-rereview/flags.txt, probe_flag_readers.py 0 suspect). I2 PASS. M2, I1 PASS.
- Low create-prove-it/SKILL.md:43: "a `cases/prove/` script is run by the controller, never by PR CI" is literally false (PR CI runs scope.py and affected_tests.py); intended: "a `cases/prove/<surface>.py` comparison". Rides with the end batch.
Out of scope: rule 0 needs every directory as a segment, so a recursive glob misses deeper files (documented Q1 limit).
