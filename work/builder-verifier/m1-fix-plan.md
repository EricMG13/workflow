# M1 fix plan (mx-autonomous; saved by the controller) - T3 round 3, executed by a fresh mx-feature

Root cause: for docs/, work/, .claude/ paths the selector seeds from substring matches against every string literal, docstrings included (rule 2 second clause :174 with "docs"/"work"; rule 4 :180-181 short dir names such as "build", "plans", "reuse"; literals() :151-157 includes docstrings). False seeds spread through the reverse import graph; 830 of 1316 tracked docs/work/.claude paths select >20 tests.

Rule change (replaces, for P under docs/, work/, .claude/ only, fix-1 rules 2-5 and the fix-2 D(P) clause; every other P unchanged):
P under docs/, work/ or .claude/: Seeds(P) = every F with a code literal containing P, or whose code literals, split on "/", hold every name in D(P) as a whole segment, plus B when P sits directly in its top directory (docs/X.md). Code literals = L(F) without docstrings (the leading string statement of a module, class or function body). Rules 1-4 do not apply. Empty seeds select nothing. literals() stays unchanged for code paths.

Code: literals(source, docstrings=True) with a skip set of docstring node ids when docstrings=False (functools.cache keyed on the flag); seeds_for: the IGNORED_PREFIXES block before `lits = ...` (see the mx-autonomous report text in the controller transcript; reproduced in scratchpad/m1-plan/candidate_final.py); docstring: define D(P) beside A(P) and add the rule. I2: scope.py:84 `shas = "\n".join(git("rev-list", "--no-merges", f"{base}..{head}")).split()`.

RED tests (commit 1), synthetic names exactly as given:
1. work/bld/ledger.md with tests/test_bldr.py "K = 'bldr_targets'\n" -> [] (today [test_bldr]).
2. docs/rx/manifest.json with tests/test_man.py "M = 'cases/fin/manifest.json'\nN = 'docstring'\n" -> [].
3. docs/X-LEASE.md with src/pkg/noted.py '"""Implements docs/X-LEASE.md."""\n' and tests/test_noted.py "from pkg import noted\n" -> [].
4. docs/rl/r.md with tests/test_glob.py "FILES = (ROOT / 'docs' / 'rl').glob('*')\n" and tests/test_named.py "P = 'docs/rl/r.md'\n" -> [tests/test_glob.py, tests/test_named.py].
5. Guard: docs/L-NOTE.md with tests/test_note.py "P = ROOT / 'docs' / 'L-NOTE.md'\n" -> [test_note].
6. I2 (tests/test_prove_scope.py): a git shim on PATH that exits 129 on `rev-list ... -z` and execs the real git otherwise; run(repo, base, "HEAD") exits 0 (today 2).

Files: cases/prove/affected_tests.py, tests/test_prove_affected.py, cases/prove/scope.py, tests/test_prove_scope.py.
Probes (scratchpad/m1-plan/; WT = executor worktree; OLD = agent-abb2e1b657aa756b8 selector = 922bb227; FD = scratchpad/t3-rereview2/old_fd970fc0.py):
- probe_red_cases.py WT/cases/prove/affected_tests.py: before 1, after 0.
- probe_i2_shim.py WT/cases/prove/scope.py: before 1, after 0.
- sh run_t3_probes.sh WT: 10 x exit=0, rc 0.
- probe_compare.py WT FD WT/cases/prove/affected_tests.py --allow docs/ work/ .claude/ cases/context-attachments-owner/context-mismatch.json: exit 0, 0 dropped.
- probe_compare.py WT OLD WT/cases/prove/affected_tests.py --allow docs/ work/ .claude/: exit 0, 0 dropped.
- probe_ignored_readers.py WT: exit 0. probe_ignored_distribution.py WT: `>20: 0`.
- probe_dropped_mentions.py WT OLD ...: exit 1 with ~43 FLAG lines (inspected: none a real reader).
- branch-review/probe_selection_counts.sh from WT root: exit 0; fc7fe5c5 0/0, 0150b1b1 0/0, 1af5176e 1/0, a0c45dcf 1/0, 6e798e3d 1/0, 73cf6399 3/0, e37d8ae2 7/0, 48d27efd 1/0, 9a85a694 103/5, fa95b834 104/5, 63a5bbb8 106/5, cd23907d 5/0.
Expected to keep failing (not gates): branch-review/probe_rule_fires.py; t3-rereview2/probe_dir_reader_skipped.py (Q1 limit).
Commits: 1 `test(prove): docs and work paths select only their readers (RED)`; 2 `fix(prove): docs/work paths need a code literal naming them (branch review M1, I2)`.
Owner notes: AGENTS.md selects 58 tests (only via tests/defect_classes.py); .gitignore selects all 154 (rule 5).
