# checker-fix2

Edited only cases/goldens/check.py and tests/test_goldens_check.py. Not committed.

1. Bug: new `normalise()` (delete U+200B/C/D, U+2060, U+FEFF; collapse whitespace; strip) is used by `visible_text`, the substring search and the "printed in quote" check. Test: `<p>A</p><p>&#8203;</p><p>B</p>` with quote "A <ZWSP> B" passes.
2. Scale: added "billions". Refusal test now uses "trillions"; added a billions-accepted test.
3. Derivations: operands scaled to units (`SCALE_EXP`, null = units); non-ratio results divided into the fact's scale; ratio is unitless, x100 when value_type is percent; every op quantised half-up to the stored decimal places. Tests: thousands+millions sum into a millions fact passes, wrong value fails, percent ratio passes and fails when unscaled.

Behaviour change to note: a product of two millions-scale operands now recomputes in units, then expressed in millions (1000 x 900 -> 900000000000, not 900000). I changed the existing product test's expected value accordingly. This follows the brief literally; confirm that is intended.

Gates (all exit 0):
- pytest tests/test_goldens_check.py: 51 passed
- ruff check: pass; ruff format --check: pass
- check.py per case: bgs-relative-value 0, ihrt-distressed-restructuring 0, lth-covenant-refinancing 0 (was 1 before the fix), natl-portfolio-decision 0, shc-earnings-update 0, tdg-credit-snapshot 0

Not verified: full test suite outside this file; mixed-scale derivations on real golden data (none of the six cases appear to use them); the earlier lth exit 1 was not diagnosed beyond it now passing.
