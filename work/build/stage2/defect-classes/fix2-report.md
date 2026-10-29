# Shared defect test fix round 2 report (mx-feature)

Fix round 2 is committed as 292b1d2 on top of 4871569, and probe `p5_verbatim_mutants.py` now exits 0. I amended my own first attempt to get one commit; it was not pushed.

**What changed.** `model_text_failures` in `tests/defect_classes.py` now records which `verbatim` patterns accepted at least one hostile value. After the loop it reports every pattern that matches payload paths but never accepted any value as `<pattern>: listed verbatim but refused every value`. Only the outcome form of the check was added, with no schema introspection. The stale-pattern check ("names no path of the payload") is unchanged.

**Test first.** I added `test_a_verbatim_path_that_refuses_every_value_is_a_failure` to the selfcheck and ran it red before touching the code. The fake there journals an issue on every `summary` while `("summary",)` is listed verbatim, and the expected failure is `summary: listed verbatim but refused every value`. A second test, `test_a_verbatim_pattern_needs_only_one_accepted_value_on_one_path`, checks that one accepted value on one path is enough for a pattern to count as used.

**Real allowlists.** `CP0_VERBATIM` and `CP1_CONTEXT_VERBATIM` both still pass the new check, so every listed path accepts at least one hostile value and nothing had to be removed from either set.

**Probe `p5_verbatim_mutants.py` (exit 0).**
- Mutant A (adding the `Claim.text` path `analysis.*.text` to `CP0_VERBATIM`) is caught as `analysis.*.text: listed verbatim but refused every value`.
- Mutant B (`allowed = True`) is caught: the selfcheck fails with 2 failed, 242 passed.
- No citation path is allowlisted.
- My first version of the fix reworded the `allowed = any(...)` line, which broke the probe's search for that exact text, so I restored it.

**Gates, exit codes.**
- Three test files together: 280 passed, exit 0.
- The shared and CP-1 files finished in 17.6 s and 48 s in the previous round; the combined run takes about 50 s, and I did not time them separately this round.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `mypy --strict` on the 4 changed files: exit 0.
- `git grep noqa -- src tests`: 13, unchanged.

Not verified: L2 (null or empty free-text fields, backlog). CP-1A and CP-2 model text through the store. CP-1 steps after `source_context`. Downstream rendering of the verbatim text beyond the build and sink types read in the source. Owner-core `submit` seams (no core registered). Runtime under heavy machine load.

agent=mx-feature fix-rounds=2 gates-first-pass=n
