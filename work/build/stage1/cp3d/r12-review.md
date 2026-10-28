CP-3D round 12 review (rule W and B10), commit 504d084 in /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp3d-stage1, diff 128c3ca..504d084

**Verdict: APPROVE.** No High or Medium findings. One Low (a gap in the tests) and one Info; neither reopens review.

All probes are in /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r12-review/ (called `R/` below). They ran against a full `git archive 504d084` copy at `R/copy` with PYTHONDONTWRITEBYTECODE=1.

## Spec verdict: PASS

**W in `_tokens` (src/deploy_workflow/owners/cp3d.py:198-206)**
- The second lookbehind is `(?<!{_MINUS} )`. With the existing lookbehinds it is exactly the ruling's fixed-width exclusion.
- `_parenthesised` (:182-185) accepts `(`/`( ` before the figure and `)`/` )` after it. `_tokens` (:205) and `_cut` (:237) both call it.
- The B2 digit-start condition (:202) is unchanged. `(-425)` and `( -425 )` still occur as `-425`, and `(425)` and `( 425 )` are not occurrences of `425`.
- Probe: `R/p_closure_and_edges.py`, exit 0.

**`_CUT_BEFORE` (cp3d.py:177)**
- It is `(?:[0-9.]|{_MINUS} ?)\Z`, as the ruling requires.
- A page `- 25` and a page `-\n25` cut an edge quote. A page `A-\n25` and a page `2024-\n2025` do not.
- A spaced range on the page is cut, which is the accepted cost.

**Plain versus joined readings**
- I found no input where the two readings disagree on sign.
- Fuzz on the real `cp3d._tokens`: 22763 random wrapped texts over the alphabet `-`, `-\n`, `-\n  `, U+2212, NBSP, a thin space, CRLF, a tab, a soft hyphen, the parentheses, `+`, letters and `.`. The plain and joined token counts never disagree for `25`, `0.25`, `5` or `2`.
- Hand-picked cases all read as the ruling says: a double minus, `.-`, `(-`, CRLF, `− `, `S- 350` and `+ 25`.
- `A-\n25` and `2024-\n2025` stay unsigned. `95 - 96`, `2024 - 2025` and a dash bullet are refused.
- Probe: `R/p_closure_and_edges.py`, exit 0.

**Labelled reader (bid)**
- tests/test_method_cp3d.py:1732-1752 covers `bid - 1.25` and `bid -\n1.25` with their twins. The issue is exactly the occurrence issue, and the labelled issue is absent.
- With the `_tokens` minus space reverted, this test alone fails. Probe: `R/p_review_mutants.py`, mutant 5 killed.

**B10 (cp3d.py:497)**
- `is_blank(text)` replaces `not text.strip()` at the same position, with the same `<path>: empty text` frame and the same `text is not None` guard.

**Frozen readings and scope**
- No frozen reading moved: 15 CP-3D triples, and 4, 15 and 40 for the other readers (`R/p_sign_breaks_cp3d.out`, part D).
- Only the two allowed files changed. Nothing under `cases/`, `src/deploy_vii` or `methods/` was touched. The diff is 96 changed lines.
- There is no stub, fake value or catch-all.
- The build matches CP-1D's approved `_SIGNED_AMOUNT`/`_W_MINUS` on claude/round12.

## Quality verdict: PASS, with one Low and one Info

**Low (a gap in the tests, not a code defect): the guard in `_CUT_BEFORE`'s new space arm is not pinned by any test.**
- Location: cp3d.py:177.
- The mutant `(?:[0-9.]|{_MINUS}|- )\Z` drops the letter-or-digit guard before the spaced minus. It survives both gate files.
- Under that mutant, a page with `A-\n25 percent` and the edge quote `25 percent` would be refused wrongly. That fails closed, so it is not a bypass, but it breaks the ruling's "`A-\n25` stays a hyphen wrap".
- The code is correct today: `R/p_closure_and_edges.py`, case "edge start after page 'A- ' (hyphen wrap)", returns True.
- Fix: add a `_MARGIN_CLASS` case with the page `... A-\n25 percent ...`, the quote `25 percent ...` and accepted=True, plus the `2024-\n2025` twin.
- Probe: `R/p_review_mutants.py`, mutant 2 SURVIVED.

**Info: a signed value_text is still matched on the plain reading only.**
- Location: cp3d.py:212.
- For `margin -\n425 bps`, the value_text `-425` gives no occurrence on the plain reading (`- 425`) but would occur on the joined one (`-425`).
- Both paths refuse, with "does not occur" instead of the shape issue. Neither reading takes the unsigned `425`, so the sign does not flip.
- No ruling covers spaced signed value_texts, and no frozen case has one. This is noted only.
- Probe: `R/p_signed_value_text.py`, exit 0.

## Probe and mutant exit codes

| Probe | Exit | Notes |
|---|---|---|
| `cp3d-r12/p_r12_mutants.py` (output in `R/p_r12_mutants.out`) | 0 | The unmutated copy passes; all 7 mutants are killed. |
| `p_sign_breaks_cp3d.py` (copy in `R/`, LANE pointed at `R/copy`) | 0 | D: none moved. E: 1759 disagreements under round 10, 0 under W. |
| `cp3d-class-review/p_wrap_minus_and_edges.py` | 0 | |
| `cp3d-r10-review/p_tip_sign_rule.py` (B2) | 0 | 0 FAIL lines. |
| `R/p_closure_and_edges.py` | 0 | |
| `R/p_review_mutants.py` | 1 | The unmutated copy passes. 5 of 6 mutants are killed: the spaced-lookbehind guard dropped, `_parenthesised` with `or`, B2 `accounting = True`, the bid test alone, and `(  ` in place of `( `. The `_CUT_BEFORE` space-arm guard survives (the Low). |
| `R/p_signed_value_text.py` | 0 | |

## Gates (all exit 0, run in the worktree)
- pytest on `tests/test_method_cp3d.py` and `tests/test_defect_classes_selfcheck.py`: 1016 passed.
- `ruff check` (no cache) on both files.
- `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files, with the cache in `R/mypycache`.
- The worktree was still clean afterwards.

Not verified: the full test suite and `tests/test_host_h1.py` were not run. The `methods/cp3d.md` guard-limit note is not written; it is the controller's Stage 2 note. W was checked on frozen triples only through the probe's inventory, not on every page a builder makes. No GitNexus `impact` or `detect_changes` was run. The fuzz covers only the listed alphabet and value_texts of up to two integer digits.