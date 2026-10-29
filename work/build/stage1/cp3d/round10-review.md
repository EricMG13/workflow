## CP-3D round 10 task review (target cp3d-stage1 at a1de97d, diff 7fdddbf..a1de97d)

**Spec verdict: APPROVE.** The change is limited to `_token_once` plus tests: 2 files, +134/−3, well under the ceiling. I made no edits and the target tree is still clean.

**Quality verdict: APPROVE.** There is one Low finding. Under the project rules it rides with the next CP-3D change and does not reopen review.

### Check results
1. **Sign reading in `_token_once`** (/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp3d-stage1/src/deploy_workflow/owners/cp3d.py:173-188). It follows the rule.
   - The pattern at :182 is exactly `(?<![0-9.])(?<!(?<![A-Za-z0-9])-)` + escaped text, on `normalise(quote)` (:181).
   - The parenthesis exclusion is at :186.
   - `+` is ignored, and `1-December`, `2024-2025`, `95-96` and `S-350` are not read as signs.
   - All four readers go through it: `level_text` (:455), margin and amortisation through `_check_quoted_numeral` (:526), and `percent_text` (:590).
   - Each check stays before the shape and leading-zero checks (6b C2), and the issue frames are the existing pinned ones. No new string was added.
2. **`_labelled`** (:434-438) is not in the diff, and `_labelled("bid","95","bid -95 today")` is False.
3. **Signed analyst text in parentheses.** The tip changes which refusal fires, and the ruling does not support the change (finding L1).
4. **Parenthesis edge cases.** I found no misfire:
   - `(95-96)`: both 95 and 96 still occur.
   - `(95, 96)`: both occur.
   - `(4.30 percent)`: occurs.
   - `(4.30)` and `x (425).`: read as negative.
   - `(425) and 425`: occurs once.
   - All 13 frozen CP-3D token/quote pairs read the same under the 7fdddbf reader and at the tip.
5. **Mutants.** The implementer's runner exits 0: the control passes and all 5 mutants are killed.

### Findings
- **L1 (Low): cp3d.py:186, the parenthesis exclusion is tested at the match start, not at the first digit.**
  - The Parentheses ruling defines a parenthesised numeral as "`(` directly before the first digit". For a signed analyst text such as `-425` against the quote `margin (-425) bps`, the match starts at `-`. The `(` is before the minus, not the first digit, so under the ruling the quote reads −425 and `-425` should occur.
  - The tip excludes the match, so the result is `margin: bps_text -425 does not occur in the quote`. Today (7fdddbf) gives `margin: bps_text -425 must have at most three integer digits and four decimal places`.
  - So this is a precedence change, not "keeps today's refusal" as round 10 §1 (CP-3D bullet 4) requires. The implementer's Not verified line describes the behaviour but treats it as acceptable.
  - Both results are pinned refusals and fail closed. Observations are not affected because `_DECIMAL` fires first, and no frozen case has this form, hence Low.
  - Suggested fix: apply the parenthesis exclusion only when the match starts with a digit. Add a test: quote `(-425)` with text `-425` gets `_SHAPE`.
  - Probe: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r10-review/p_tip_sign_rule.py, check C.

I found no stub, fake value or catch-all in the diff.

### Probe exit codes
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r10/mutants_r10.py` (the implementer's runner): **exit 0**.
  - Control: 269 passed.
  - Minus lookbehind removed: killed, 18 failures.
  - Lookbehind reduced to `(?<!-)`: killed, 4 failures.
  - Parenthesis reading removed: killed, 6 failures.
  - Parenthesis reading checks only the `(`: killed, 1 failure.
  - Parenthesis reading checks only the `)`: killed, 1 failure.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r10-review/p_tip_sign_rule.py`: **exit 1**, which is the expected result: it fails only on check C, the L1 reproduction. Everything else passes:
  - A: the `−0.25 percent` case gets the pinned "does not occur" text, and the 13 frozen pairs are unchanged.
  - B: 19 direct edge cases.
  - D: `_labelled` still refuses `bid -95`.

### Gates (run from the target root, venv binaries)
- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_method_cp3d.py`: 269 passed, exit 0.
- `ruff check --no-cache` on both files: exit 0.
- `ruff format --check --no-cache` on both files: exit 0.
- `MYPYPATH=src mypy --strict --cache-dir <S>/cp3d-r10-review/mypycache` on both files: exit 0.

Not verified: LEAD's `p_sign_rule.py` was not run unchanged. It targets the lane tree and patches the old reader, so at this tip its "today validates" expectation would fail by design. I re-ran only its CP-3D part, adapted to the tip, in `p_tip_sign_rule.py`. I ran no mutants of my own beyond the implementer's runner. Non-ASCII letters before `-` (for example `é-425`) are read as a minus because the ruled pattern is ASCII-only; I did not judge that, since the pattern is the ruling's. I did not run the full suite or GitNexus `detect_changes`.
