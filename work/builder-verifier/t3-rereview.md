# T3 scoped re-review of fix round 1 (mx-precise; saved by the controller)

Verdict: FAIL (new Medium from the ruling). H1, C1, M2, M3, L1, L2, I2, the -z/surrogateescape class and pytest exit 5: fixed (all 9 t3-review probes exit 0).
- N1 (Medium) affected_tests.py:163,174,179-180 - A(P) drops the first component, so for `cases/PINS.json` rule 2's second clause never fires and rule 4 is skipped once any file holds the full-path literal; tests reading `ROOT / "cases" / "PINS.json"` (tests/test_method_cp4.py:29, test_method_cp5.py:93, test_method_cpdr.py:50, test_method_cp3d.py:37, test_method_cp1d.py:940) are missed (625b5585: 153 selected; fd970fc0: 34). Probe scratchpad/t3-rereview/probe_toplevel_split_literal.py (exit 1).
- N2 (Low) pr.yml:78, pr-heavy.yml:42 - shellcheck directive above `rc=0`, not the pytest line. Probe scratchpad/t3-rereview/probe_shellcheck_directive.sh (exit 1).
- N3 (Info) rule 1 only for .py under src/, tests/, cases/ (documented :16).
- Known: ruff SIM114 :172.
