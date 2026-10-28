# CP-2E rounds 5-6 scoped review (mx-precise; controller-saved)

## CP-2E rounds 5 and 6 review (`git diff 5fe9a1f af23f7f`, commit `af23f7f`)

**Verdict: APPROVE.** E6, E7, E8, A3 and A4 are applied as ruled. There are no High or Medium findings. The diff is 257 changed lines, well under 800, and only the two in-scope files are touched.

### Spec verdict: PASS
- **E6:** The oracle amendment in `c906687` changes builder :633-634 into the split `df is None` / `bal is None`. It also changes expected `fixture_no_rate_terms.stored.{foreign_debt, foreign_debt_share, fx[0].debt_change, debt_after, lev_after}` to "the facility balance is not stated". I read these from expected.json. `test_composer_fixture[fixture_no_rate_terms]` (tests/test_method_cp2e.py:240-243) asserts against that oracle with no xfail. My mutant `e6_reason` disables the `balance is None` branch in cp2e.py, and it is killed.
- **E7** (cp2e.py:1389-1399):
  - The claim text matches the ruling byte for byte, including the `{T2F.2.r01.value|US$ m}` and `{T2F.3.rNN.gross|US$ m}` references and the `[T2F.3.rNN.cov_after]` chip. "zero" and "negative" are filled in from the reason.
  - `cov_after` and `cov_change` are not_applicable with `Not meaningful: interest after the shock is zero/negative`, asserted at the cell level (tests:631-645).
- **E8** (cp2e.py:489, 601-602): the regex is exactly the ruled `\b(floating|fixed)[\s-]+rate\b` with IGNORECASE. Both stems or neither gives the existing issue.
- **A3** (cp2e.py:71-81 and all seven `_ratio` call sites):
  - Every divisor `<= 0` is not_applicable: base coverage, coverage after the shock, leverage, floating share, foreign-debt share, share of EBITDA, and leverage after the currency move. No other division by a value exists; I grepped for ` / `.
  - The zero reasons are byte-identical to before, since `f"{divisor} is zero"` rebuilds the old strings, and negatives read `… is negative`.
  - Negative base interest takes E3 (tests:684-689). Negative after-shock interest takes E7's "negative" claim (tests:634).
- **A4** (cp2e.py:1291-1314):
  - `_LIM_FLOOR` is emitted only when the floor is 0.
  - A floating rate with a floor above zero gets the ruled text byte for byte.
  - The not-stated text has no path, because `FacilityTerms.floor_bp` is required. The implementer flagged this for LEAD.
- **The new fail-closed raise** (cp2e.py:1305-1308):
  - **Reachable through validation:** a fixed-rate quote with "floor 25 basis points" gives `validate_macro_fx == ()`, and then `compute` raises `Floor limitation: …`.
  - **A4's text would be false there:** `gross` is a known 0 for both shocks, so "the rate shocks are not calculated" is untrue. `_LIM_FLOOR` would be false too, since it says the floor is zero.
  - **Failing closed is right:** no wording is pinned for this case, and the raise is not caught anywhere.
  - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r6-review/probe_fixed_floor_reachable.py`, exit 0.
- **Missing values, stubs and catch-alls:**
  - Missing never becomes 0. The only known 0 is the lease's existing rule that a fixed-rate facility adds a known 0 (`_gross`, :158-159), which is unchanged.
  - The diff adds no `except`, stub or placeholder value.
  - The new guards (`word not in (...)`, `_floor_limitation`) raise `ValueError`; they do not swallow anything.

### Quality verdict: PASS, with Low and Info notes
- **Low**, cp2e.py:489 (`_RATE_PHRASE` word boundaries): no test pins the ruled `\b` anchors.
  - Dropping the trailing `\b` would count "fixed rates"; dropping the leading `\b` would count "prefixed rate". The suite would not notice either change.
  - The code is correct as ruled; this is a test gap only. It can ride with the next fix as a case like "fixed rates" or "prefixed rate" that expects the neither-stem issue.
  - Mutants `e8_no_trailing_b` and `e8_no_leading_b` survive in the runner below.
- **Info**, cp2e.py:1303: changing `floor > 0` to `floor != 0` survives. This is equivalent on validated input, because `bps_text` is digits only, so a negative floor needs direct construction. It is a guard and needs no action.
- **Info**, cp2e.py:1391-1392: switching off the E7 `word not in ("zero","negative")` guard survives. The guard is unreachable today because `_ratio` only produces those two words. It fails closed, which is acceptable.
- **Info:** the E7 branch is reachable only through directly built inputs with a negative added interest. With validated inputs, base coverage is known only when interest is above zero, so after-shock interest is above zero too. The implementer's account is correct, and the test reaches it through `_negative_gross_inputs` (tests:612-620).

Mutant runner for the three findings above: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r6-review/mutants_review.sh`. It runs 15 mutants, each from a full rsync copy, and exits with the survivor count: **exit 4**. 11 are killed, including the negative and zero reason words, the A4 rate-type check, the A4 text, IGNORECASE, `len(stems)>=1`, dropping `out.known(cov)` from E7, the E7 text, the E6 reason, and the A3 divisor labels. The 4 survivors are the two word boundaries, the floor `!= 0` change and the E7 word guard.

### Gates (run from the target root)
| Gate | Exit | Result |
| :--- | :--- | :--- |
| pytest `tests/test_method_cp2e.py` | 0 | 84 passed, no xfail |
| `ruff check` (both files) | 0 | |
| `ruff format --check` (both files) | 0 | |
| `MYPYPATH=src mypy --strict` (both files) | 0 | |

### Implementer probes
- `…/scratchpad/cp2e-r6/probe_new_strings.py`: exit 0. It checked 20 claims and found no hits.
- `…/scratchpad/cp2e-r6/mutants.sh`: exit 0. All 4 of its mutants are killed.

### Points for LEAD
1. **Wording needed:** a fixed-rate facility with a floor above zero has no ruled limitation text. It now raises through validated input; 108 of the 648 grid combinations do so. Either rule the wording or have the validator refuse a non-zero floor on a fixed rate.
2. **Deviation from the literal ruling:** A4 says "Floor above 0" with no rate-type condition, so a literal reading would emit the text for fixed rates too. The implementer narrowed it to floating rates, because the text would be false for a fixed rate. I agree with the narrowing, but it needs LEAD to confirm it.
3. **Floor not stated:** A4's floor-not-stated text needs a path only if the Stage 2 schema lets the floor be missing.

Not verified: the E8 `\b` anchors (no test, see the Low finding); E7 with validated inputs (only directly built inputs reach it); A4's floor-not-stated text (no path); any test suite other than `tests/test_method_cp2e.py`; the cherry-picked oracle commits beyond the E6 fields and their builder lines; Module/Fact assembly, rendering and settled runs.
