# T3 scoped re-review of fix round 2 (mx-precise; saved by the controller)

Verdict: PASS with notes. N1, N2, SIM114 closed; all probes exit 0.
- Q1 (Low) affected_tests.py:174,180-181 - the D(P) clause can fill the seeds from another file holding P's basename plus a top-directory literal, which skips rule 4, so a test that globs P's own directory without naming the file is lost. Real tree: 7 of 1970 paths lose tests, none a real reader (6 docs/work rule-4 substring matches; cases/context-attachments-owner/context-mismatch.json loses tests/test_owner_preset_walks.py, which reads only cases/*/submissions.json). Probes scratchpad/t3-rereview2/probe_dir_reader_skipped.py, probe_no_new_underselection.py (exit 1).
Controller decision (recommended option, recorded here): keep as a documented limit; running rule 4 alongside rule 2 widens every data-file selection for no reader lost today. Revisit through /maintain-prove-it if a real reader is ever missed.
