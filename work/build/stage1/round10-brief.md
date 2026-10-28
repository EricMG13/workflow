# Rulings round 10, item 1: figure signs in quote readers (CP-1D, CP-3D, CP-8, CP-2E)

The Inputs, Rules and Output of `work/build/stage1/round5-brief.md` apply. This brief overrides that file's Step 0 and names what you apply. Review afterwards: mx-precise per module.

## Step 0
1. `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/<worktree>")`.
2. From the worktree root, merge the lane branch `claude/module-dev-status-review-0981b6`: `git merge --ff-only` where the table says ff, plain `git merge` otherwise. The lane carries round 10 (4fd8c24). Report any conflict; resolve none outside your two files.
3. Re-pin only a sha your test asserts that moved, confirmed with `shasum -a 256`. None is expected.

## What to apply
Read `docs/rulings/2026-10-28-stage1.md`, `# Round 10`: section 1 (your module's bullets) and, under "LEAD rulings on the For LEAD items", **Parentheses**, **Unsigned grammars** and (CP-1D only) the unstated-proposed-amount ruling. In short:
- read the figure on `quotes.normalise(quote)`;
- a `-` directly before the first digit is a minus when it starts the quote or follows a non-alphanumeric character: `(?<![A-Za-z0-9])-`; `1-December`, `2024-2025`, `95-96`, `S-350` are not signs; `+` is ignored;
- a numeral in accounting parentheses, `(` directly before the first digit and `)` directly after the last, reads as negative; `(4.30 percent)` is unaffected;
- an unsigned `*_text` against a signed or parenthesised printed figure then does not occur, and the existing pinned issue fires at its existing position. Add no new string.

| Module | Worktree | Merge | Apply |
|---|---|---|---|
| CP-1D | `cp1d-stage1` | ff | `_basis_amounts`: the signed amount pattern over the normalised quote; step 5 counts signed tokens; a basis ≤ 0 gets the pinned bounds text, also when the proposed amount is unstated (5b Y4, before the exactness test). `_bridge_amount` unchanged. |
| CP-3D | `cp3d-stage1` | ff | `_token_once`: the lookbehind `(?<!(?<![A-Za-z0-9])-)` after `(?<![0-9.])`, plus the parenthesis reading. Covers `level_text`, `margin.bps_text`, `amortisation.value_text`, `reference_rate.level.percent_text`. `_labelled` unchanged. Signed analyst text keeps today's refusal. |
| CP-8 | `agent-a3cc9818386e8861a` | merge | `_token_once`: same lookbehind and parenthesis reading. `_labelled`: `_MULTIPLE` and `_DECIMAL` take the prefix `(?:(?<![A-Za-z0-9])-)?` (and the parenthesis reading), so `total leverage -0.50x … 0.50x` gets the pinned "is not labelled" issue. |
| CP-2E | `agent-a219254fe68cc1c2d` | ff | `_once`: same lookbehind and parenthesis reading on `normalise(quote)`; `fx.foreign_ebitda_share` is the real gap. `row` unchanged. Also, from the round's Stage 1 defects: `on_page` matches with the product `quoted` that `citation_issues` uses, not `_squash`. Also the riding Low: a test that kills `a4_floor_gt_to_ne` (the negative-floor fail-closed raise), runner `<S>/cp2e-r6i-review/` or your own. |

## Tests (test-first, red seen for the reported cause)
For each reader: a quote printing `−` (U+2212), an ASCII `-`, an en dash, and a parenthesised `(N)` before the figure, each with the unsigned `*_text`, gets the pinned issue. Each non-sign form in the rule (`1-December`, `2024-2025`, `95-96`, `S-350` where your grammar can meet it) still validates. Every frozen case still passes unchanged.

## Rules
- Files: `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py` only. Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Show each new reading's revert is killed.
- The `methods/<cp>.md` lines (the sign rule; for CP-8 and CP-3D the unsigned-grammar limitation) are Stage 2 notes: list them, don't write them.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Probes under `<S>/<cp>-r10/`.

## Ledger line
`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>` (CP-2E's riding Low and defect still count 0).
