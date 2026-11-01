# T2 fix round 1 brief (controller)

Fix H1, L1, L2, L3 and Info 2 of work/builder-verifier/t2-review.md in cases/prove/scope.py on branch bv-t2. Only High/Medium reopen review; the Lows ride with this fix.
1. Test first: add a test in tests/test_prove_scope.py that commits `cases/x/café.json` together with `src/a.py` and expects per-commit mode to exit 1, and one where a builder range adds `.github/workflows/café.yml` and expects `--role builder` to exit 1. They must fail on 02084968 (the controller runs them).
2. H1 + Info 2: pass `-z` to `git diff-tree` and `git diff`; read stdout as bytes, split on NUL, decode each path with `utf-8` and `surrogateescape` so a non-UTF-8 name still classifies by its ASCII prefix; never let a decode error escape as a traceback.
3. L2: add `--root` to `git diff-tree`.
4. L3: class patterns match one path segment per `*` (e.g. `tests/test_goldens_*.py` only directly under tests/); keep `**` meaning any depth. Add a classify test for `tests/test_goldens_a/helper.py` -> PRODUCT.
5. L1: docstring states the bound: per-commit mode stops a careless mix only (merge commits are skipped; a builder can split commits); the controller's `--role builder` range check is the boundary.
Constraints: stdlib only; no catch-all; git failure exits 2; touch only cases/prove/scope.py and tests/test_prove_scope.py; one commit `fix(prove): scope check reads NUL-separated paths (review T2 H1, L1-L3)` ending with the Co-Authored-By line. Run the reviewer's probes (scratchpad/t2-review/*.sh, probe_classify.py) after the fix and report each exit code.
