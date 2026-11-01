# Whole-branch review (mx-architect; saved by the controller)

Verdict: CHANGES REQUIRED. Probes: scratchpad/branch-review/ (probe_selection_counts.sh, probe_rule_fires.py, probe_heavy_comparison.py, probe_docstring_noise.py).
Integration: scope.py on the branch 26 commits, 0 violations; pins and goldens checks exit 0; checks job should pass; tests job on the first PR selects 149/154 (ALL by design: .github/ and the selector change).
- M1 affected_tests.py:174,180-181 - docs/work-only PRs select near the full fast suite (work/build/ledger.md -> 143, docs/reuse/manifest.json -> 103, a plan+spec commit -> 103; code commits 3-7). Rule 4 substring-matches short directory names ("build" hits 138 via docstrings and builder_targets). Cheapest fix: skip rule 4 for IGNORED_PREFIXES paths; exclude docstrings from literals() (138 -> 55, 13 -> 4/7). Re-run t3-rereview2/probe_no_new_underselection.py after.
- M2 create-prove-it/SKILL.md:42 vs affected_tests.py:129-134,232-233 - "a comparison over 5 minutes goes into HEAVY" has no effect for cases/prove scripts (probe_heavy_comparison.py).
- M3 (pre-existing, owner) tests/test_stage2_classes_batch.py:133 - CP-1B in owner_workflow._CORES (:171) but in neither case map; known failure (work/build/ledger.md:747); the first PR's tests job will fail on it.
- L1 (owner) pr-heavy.yml:21-22 - six RUN_PROMOTION-gated files have no CI path even with the label.
- I1 CLAUDE.md:30 builder writes tests/ but tests/test_goldens_*.py and tests/test_prove_*.py are ORACLE. I2 scope.py:84 `rev-list -z` needless (git >= 2.49 floor). I3 mypy --follow-imports=silent does not re-check callers. I4 global edits = the four planned hunks.
Efficiency: code commits 1-7 files; core-module changes 103-106 of 149 (acceptable; the hours came from the five HEAVY files). Selector ~8.5 s.
Rewrite-tournament: scope.py leave alone; affected_tests.py leave alone (M1 is a rule-scope fix). Over-engineering: drop rev-list -z; compute the literal table once in main instead of functools.cache; exclude docstrings.
Not verified (reviewer): any GitHub run; pytest on any selection; setup-uv SHA and Python 3.13.15/uv 0.12.5 availability on the runner.
