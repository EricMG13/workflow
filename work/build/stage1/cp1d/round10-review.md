**CP-1D round 10 task review (b7cd02e vs 7fdddbf, worktree /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp1d-stage1)**

**Spec verdict: APPROVE.** Code and rulings agree, and the frozen readings are unchanged.
**Quality verdict: APPROVE, with two Low test gaps.** Neither reopens review; they can ride with the next CP-1D fix or the end-of-branch batch.

**Negative constraints and diff ceiling**
- Only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py` changed, 141 lines in total (+133 / −8), well under 800.
- No new string was added.
- `_bridge_amount` still uses `_AMOUNT.fullmatch` (cp1d.py:410).
- There is no stub, fake value or catch-all.

**Spec checks**
1. **Amount pattern (cp1d.py:349-352, 512-521).**
   - The digits branch is exactly the rule `(?<![A-Za-z0-9])-` followed by the digit run, run over `normalise(quote)`.
   - A parenthesised branch `\(N\)` comes first and returns `-N`.
   - Step 5 counts the `finditer` matches. The sign and the brackets never add or remove a token, so counts on unsigned text cannot change.
   - `_bridge_amount` is unchanged. The `UNUSABLE_PAGES` rows `-1.00` and `(1.00)` pin this, and my "bridge uses signed" mutant was killed.
2. **Bounds text (cp1d.py:587-604).**
   - `amount <= 0` returns the pinned bounds text after the step-5 count and before the `_is_number` exactness test, so it sits at step 6 ahead of exactness. This matches the Y4 extension in section 1.
   - It also fires on an unstated proposed amount. That only reaches the Recurring path, because the 1D7 `return None` (cp1d.py:588-589) still comes first for every accepting assessment, and `_accepts` is false only for Recurring among Partly-supported rows.
   - This is the ruling's reading ("CP-1D, a Recurring Partly-supported basis on an unstated proposed amount … at the same step as when the amount is stated"). It does not change a pinned precedence: 1D7 skips step 6 as ruled.
   - Probe `p_1d7_precedence.py` confirms that an accepting row on an unstated amount with basis `-1.80`, `(1.80)` or `0` gets `Cannot accept an unstated amount` and no bounds text.
   - Rewriting the upper-bound check from `not 0 < amount < item.amount` to `not amount < item.amount` behaves the same, because amounts ≤ 0 already return earlier.
3. **Frozen readings.**
   - Probe `p_frozen_readings.py` reads all 15 frozen CP-1D `accepted_basis` quotes three ways: the old `_AMOUNT.findall`, the new `_basis_amounts`, and the literal rule regex. All three agree on every quote; nothing moved.
   - I did not run LEAD's `p_sign_rule.py`. It monkeypatches the pre-change `_basis_amounts` and expects "today: -1.80 validates", so on b7cd02e it would report a false failure. Its frozen comparison is the one my probe repeats against the real new reader.
4. **Parenthesis edge cases** (probe `p_paren_edges.py`, all as the rulings say):
   - `(1.80)` reads −1.80; `(1.80 million)` reads 1.80.
   - `(1.80-2.40)` and `(1.80 to 2.40)` read [1.80, 2.40], so step 5 refuses them.
   - `saving 1.80)` and `(saving 1.80)` read 1.80: the `(` side is required, as the ruling says.
   - `(2024) contracts` reads −2024, which matches the ruling's "unless the `)` directly follows the digits".
   - `(-1.80)` reads −1.80; `( 1.80 )` reads 1.80; `a-1.80` reads 1.80; `1.80 − 0.20` (minus followed by a space) reads 0.20 unsigned; `1.80 −0.20` reads −0.20.

**Findings**
- **Low: no test pins 1D7 ahead of the new ≤ 0 check** (cp1d.py:588-592; tests around tests/test_method_cp1d.py:632-650).
  - The code is correct (`p_1d7_precedence.py`).
  - But the mutant "<=0 check before 1D7" survives the test file, so moving the new check above 1D7 would go unnoticed. The implementer raised this as their decision for review.
  - Suggested fix: add a gap-pack row that is accepting and not Recurring, with basis `-1.80`, that expects `Cannot accept an unstated amount`.
  - Probes: `p_review_mutants.py`, `p_1d7_precedence.py`.
- **Low: the `(` side of the parenthesis reading is untested** (cp1d.py:350).
  - Mutating the pattern so that `)` alone after the digits reads negative survives the test file. Under that mutant, `saving 1.80)` would silently read −1.80.
  - The code is correct (`p_paren_edges.py`).
  - Suggested fix: add a `_basis_amounts` row such as `("saving 1.80)", ["1.80"])`.
  - Probes: `p_review_mutants.py`, `p_paren_edges.py`.
- **Info: `-(1.80)` reads −1.80, not +1.80** (cp1d.py:349-352). The leading `-` is dropped because the bracket branch wins. The rulings do not cover this form, and either reading is at or below 0, so the bounds text fires. No action needed.

**Probe exit codes** (all in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r10-review/`):

| Probe | Exit | Result |
|---|---|---|
| Implementer's `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r10/p_r10_mutants.py` | 0 | Baseline passes; all 7 mutants killed |
| `p_frozen_readings.py` | 0 | 15 quotes, none moved |
| `p_paren_edges.py` | 0 | All cases as ruled |
| `p_1d7_precedence.py` | 0 | 1D7 comes first for every amount |
| `p_review_mutants.py` | 1 (expected) | 6 of 8 killed; survivors are "<=0 check before 1D7" and "( side not required", the two Low findings |

`p_paren_edges.py` first exited 1 because one of my own expectations was wrong: a minus followed by a space is not a sign under the rule. I corrected the expectation, not the code.

**Gates** (target root, `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/`):
- pytest on `tests/test_method_cp1d.py`: 143 passed, 1 skipped (Stage 2/4), exit 0.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files, with the cache in scratch: exit 0.
- The target worktree is clean afterwards.

Not verified: only the CP-1D test file ran, so no full suite and no G1 run. LEAD's `p_sign_rule.py` was not run, because it is written against pre-change code and needs the CP-8 worktree. No CP-3D, CP-8 or CP-2E readers were checked. Quotes from real (non-synthetic) source documents were not exercised. Stale `methods/cp1d.md` text and the superseded `expected.json` recipe text were not checked; both are deferred to stage 2 or the oracle batch.
