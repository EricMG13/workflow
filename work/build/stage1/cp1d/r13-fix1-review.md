## CP-1D round 13 fix 1 re-review: 9f61127 against 80cccb1

**Verdict: APPROVE.** I found no High, Medium or Low finding against this round. H1, H2 and M1 are fixed through the real accept path. Two fail-opens remain, but both already exist at d2cb626, so they go to the owner (below). There is no stub, fake value or catch-all in the diff, and nothing under `cases/`, `methods/`, `docs/` or `src/deploy_vii` changed.

**1. Findings fixed.**
- `p1_e2e_hidden_run_failopen.py` exits 0 on 9f61127 and 1 on 80cccb1.
- `p2_comma_edge_bypass.py` exits 0 on 9f61127 and 1 on 80cccb1.
- Every H1, M1 and H2 quote now gets the pinned exactly-one issue and nothing composes.
- The fixer is right that only `A saving of 2.5 is signed.` composes (basis and accepted 2.5). Its runs are `[['2.5']]`: one whole run.

**2. `_one_whole_run` is the ruled rule.** It uses the run regex as ruled, checks both readings, and requires exactly one run that is whole. `p3_run_boundaries.py` exits 0 on all 44 rows:
- **Accepted by exactly-one:** `-2.5`, `- 2.5`, `−2.5`, `–2.5`, `(2.5)`, `( 2.5 )`, `-(2.5)`, `2.`, `2.5, a rise` and `2.5%`. The signed forms then get the bounds text, as expected for a saving.
- **Refused:** `1,\n250`, `1,  250`, `1 ,250`, `.5`, `5. or 2.5`, `1.2,5` and `1,2.5`.
- **Refused, spaces after the comma:** NBSP, thin space, narrow NBSP and figure space all normalise to `1, 250`. A zero-width space splits the figure into two runs.
- **Refused, other shapes:** `1'250`, `1·250`, `A1 … 2.5`, `Q4 … 2.5`, years with and without a comma, the March date, `2.5e3`, `2.5/3`, `1..5`, `1. 5`, `2.5 and 2.5`, ranges, wrapped ranges, `(1,250)`, `(1.2.5)` and `(.25)`.
- **End-to-end fuzz (`p8_e2e_fuzz_two_figures.py`):** 6,000 random lines through `_a01_on_page1`, `validation_issues` and `compute`. It exits 0 here: 242 lines compose, each with exactly one whole ASCII figure equal to the basis. The same fuzz exits 1 on 80cccb1, with 42 broken lines.

**3. The two claimed equivalent survivors are truly equivalent.**
- **"One reading only":** the wrap regex `-\n *` keeps the hyphen, so the joined reading differs from `normalise(q)` only by dropping the whitespace after a wrap hyphen. Neither `-` nor that space can be part of a run, and the character before the next run is a space or `-`, never `.`. So the run list is the same in both readings, and no wrapped quote can give a different run count. `p6_one_reading_equiv.py` exits 0: 91,651 wrapped quotes (19 hand cases plus random ones), with 0 differences in run list or verdict.
- **"No comma join" and "no comma-space join":** a run that holds a comma is never whole, and without the join it splits into two or more runs, so the verdict is the same either way. `p7_comma_join_equiv.py` exits 0 with 0 differences on 300,000 quotes for each mutant.

**4. Frozen cases do not move.**
- `p5_frozen_dump.py` and `p5_frozen_compare.py` exit 0 against both 80cccb1 and d2cb626. All 19 refusals keep byte-equal issue lists and all raise ValueError. The 3 valid cases have identical facts, and the frozen basis quote has the same reading and passes the rule.
- LEAD's `p13_quote_classes` (pointed at the copy) exits 1:
  - Part D holds: 4 of 4 CP-1D triples, readings moved by lp+cm "none", and no frozen quote holds a comma, leading-point or two-point run.
  - The Part F failures are the expected fidelity failures.
  - The CP-3D `quote wrap before page minus` failure also occurs on 80cccb1, and cp3d is untouched, so it predates this round.
- **Flipped test:** `section 4.2.1 a saving of 25` is now in `HIDDEN_RUN_LINES` and refused, as addendum 4 says. Its old `_basis_amounts` row was replaced by `-1.80`.
- **Red check:** the new tests run against 80cccb1's src give 34 failures (13 hidden-run, 10 H2 edge, 11 helper). The fixer had not re-run them on 80cccb1.
- **Call sites:** every compose path goes through `_shape_issue`, because `compute` calls `validation_issues` first.

**5. The whole-`src` ruff failure does not come from the changed file.** `ruff check src` exits 1 with 92 errors, none in cp1d.py, and the output is byte-identical on 80cccb1. The errors are in `deploy_vii/*`, `financial_workflow.py` and `tools/upstream.py`. `ruff check` and `ruff format --check` on the two changed files exit 0.

**Predating fail-opens, for the owner (not this round):**
- **Second figure in non-ASCII digits:** if the second figure is in fullwidth `１２`, Arabic-Indic `١٢` or superscript `¹²` digits, `[0-9]` does not see it, so the quote composes 2.5. `p4_unicode_digits.py` exits 1 on both 9f61127 and d2cb626. A quote holding two figures does compose here, and no ruling covers it.
- **Digits inside a word:** a single run inside a word (`Q2`, `A1`, `2nd`) is read as the basis amount and composes 2 or 1. `p9_run_in_word.py` exits 1 on both. This is not a two-figure case.

**Exit codes:**

| Run | 9f61127 | 80cccb1 | d2cb626 |
| :--- | :--- | :--- | :--- |
| Gate (653 passed, 1 skipped) | 0 | | |
| p1, p2 | 0, 0 | 1, 1 | |
| p3 | 0 | | |
| p4 | 1 | | 1 |
| p5 compare | | 0 | 0 |
| p6, p7 | 0, 0 | | |
| p8 | 0 | 1 | |
| p9 | 1 | | 1 |
| p13 | 1 (expected Part F failures) | 1 | |
| Red check (new tests) | | 1 (34 failed) | |
| ruff on `src` | 1 (identical output on 80cccb1, not from cp1d.py) | 1 | |
| ruff on the two changed files | 0 | | |

Probes, outputs and the fresh copies (`copy/` is 9f61127, `parent/` is 80cccb1, `redcheck/` is 80cccb1's src with the new tests) are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r13-fix1-review/`. Everything was run with PYTHONDONTWRITEBYTECODE=1. The d2cb626 runs used the earlier review's `basecopy/`, whose cp1d.py I confirmed byte-equal to d2cb626.

Not verified: mypy, jscpd, complexipy and bandit (not run); the full suite outside the two gate files; LEAD's `p13_refusal_mutations.py` patched-reader probe (instead I compared the 19 refusals' exact issues as built across commits); the fixer's `p_r13_mutants2.py` (I judged its survivors with my own p6 and p7); the equivalence results rest on a written argument plus random fuzz, not a formal proof; the owner items' cost on real quotes; CP-3D, CP-8 and CP-2E; GitNexus was not run.