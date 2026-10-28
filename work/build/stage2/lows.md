# Stage 2 Lows: one batch at the end of the stage, or riding with the module's next fix

- **[G1-X guards] Low, test gap.** No test covers a step that has a scope row while its `sources` is `False`. The mutant `==` → `<=` at owner_workflow.py:614 survives. Probe: `<S>/s2-g1x-review/p_one_direction.sh`. Source: stage2/g1x-guards-review.md.
- **[G1-X guards] Info.** The docstring lines at owner_workflow.py:563, :565 and :566 are longer than 100 characters.
- **CP-DR (fix1 re-review) Low:** reader refusals for a negative count (L2b) and a per-gap share not known (L2f) are untested; `<S>/cpdr-s2-review/review_mutants_fix1.py`.
