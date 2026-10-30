# Open items rulings (session open-items-fd69c5, 2026-10-30)

Scope: the owner items in `work/build/stage2/lows.md` not marked **Closed**, the deferred user items in `docs/rulings/2026-10-29-stage3.md` item 64 (minus the CZR run), and CP-3D's copy of the item 73 reference gap. Branch `claude/open-items-fd69c5`, cut from the Modules lane at 559ba54. Modules folds `work/build/open-items/closed.md` into `lows.md` when it merges.

Limits (the user's 2026-10-30 narrowing): no `src/deploy_vii` change, no DEPLOY VII import, no dependency, permission or config change without the user's own word. CZR files are out of scope while Workflow Test writes the submissions. Items that need any of these go to the user with a recommendation, unbuilt.

## OI-1 (CP-3D reference in `summary.text`: fix)
- The Modules brief for this session lists CP-3D's copy of the item 73 gap. It is a `src/deploy_workflow` change only. Every CP-3D fact id has digits and `analyst_text` refuses digits, so a reference in `summary.text` can never resolve; refusing any reference equals refusing an unresolved one, as CP-2E and CP-DR do. Triage found 0 of 4 frozen summaries carrying a reference. Built in batch B2, test-first, mx-precise review.

## OI-2 (CP-2A raw `model_validate_json`: fold into B2)
- Triage T2 found `cp2a.py` `_validate_step` still parses the raw payload, the same protocol §6 class the owner list names for CP-2D, CP-1D and CP-3D (all three fixed in 545e28a and 30a1f7a). AGENTS.md treats a defect class as shared, so the fourth copy is fixed with them rather than left as a new owner item. Cost if wrong: one small `src/deploy_workflow` change outside the list, and `tests/test_owner_cp2a.py` joins the deferred runs.

## OI-3 (CP-2E Info: `Cite`/`Cites` break `copy.deepcopy`/`asdict`: decided, leave)
- Nothing in `src` copies or `asdict`s either type (triage T1). `__reduce__` would fix copying but not `asdict`, so the fix would be speculative and partial. Revisit when a caller needs it.

## OI-4 (CP-2A Low: caller-built `Upstream` with forged facts composes: decided, leave)
- It is reachable only through the public functions, never through submit, probe or view; G1 builds `Upstream` only through `cp2a_upstream`. The lease's v17 validator-only recipe builds one by hand on purpose, so making it unforgeable would move a frozen case.

## OI-5 (Stage 4 Info 1, `_verify_publications`: consistency check)
- A failed publication's attempt must carry exactly `issues == ("Interrupted: <interruption>",)`, which `Execution.interrupt` always writes; anything else is `identity_mismatch`. Binding `interruption` to `publication.reason` is not attempted: the text comes from exception messages and G1's suffixes and cannot be replayed exactly. Receipt verifier, so mx-precise and mx-adversary review; genuine `tests/test_owner_s1a.py` and `tests/test_owner_workflow.py` are deferred runs. The three remaining >100-character lines in `owner_workflow.py` (:12, :211, :259; E501 is not selected) are reflowed in the same batch.

## OI-6 (D12 records: the chain follows the lane's first-parent history)
- The 12 LEAD records (cffdf9f ×9, 1a1a140, bb4553b ×2) and the three report_view records (3e5b537, 24f879a, 8aef58d) are corrected as items 51-52 corrected `bindings/shipped.py`: priors computed from git, missing intermediate records inserted, a forked record folded into its successor with its reason kept and labelled "folded". Where two histories pass the probe, the lane's first-parent line wins (item 51 precedent). Gate: `work/build/keep/s53-B/probe_d12_strict.py` over df26ea8..HEAD exits 0. Preparer mx-feature, reviewer mx-precise.

## OI-7 (CP-1 chart oracle pin)
- `cases/pins.py` gains the literal `cases/charts/expected.json` (not a wider glob); `cases/PINS.json` gains exactly that entry. No oracle value moves. Preparer and reviewer are different agents (batch B4).

## OI-8 (three "blocked on G2" placeholders: removed)
- G2's genuine deferred cases cover each (cp4c-fp05-recovery, cp4-fp04-covenants, cp2h-fp05-ratings) and ran green in Stage 5. An always-skipped empty test claims coverage it does not give. Each is replaced by a comment naming its G2 cases. The cp4c placeholder's "every other FP05 block idle" is dropped: nothing asserts it, and it is not lease text.

## OI-9 (`tests/test_shell_css.py`: every applying rule)
- The check reads every rule whose selector list names `.module-list` in its last compound, including descendant selectors, and asserts the last `flex-shrink` is 0.

## OI-10 (cp2d plain-string `tabs`, item 35: decided, leave flagged)
- cp2d is not in G2's `DEFERRED`, so `assert_block_equals_oracle` never meets the shape (items 36, 44). The branch belongs with the change that adds cp2d to `DEFERRED`, which also brings its genuine cases.

## OI-11 (`financial_workflow.py:914` RUF100 unused `noqa`: blocked by CZR)
- The file is in flight for the CZR run. Removing the unused `noqa: BLE001` drops the noqa count from 13 to 12; it goes to Modules for after the CZR run.

## Closed before this session (owner list not updated)
Recorded per entry in `work/build/open-items/closed.md` with the commit that closed it.

## OI-12 (the user, directly, 2026-10-30: "Yes, you run them")
- Build agents in isolated worktrees are refused the venv interpreter (B2's builder, 12:44, the same refusal text as items 71-72). The controller runs each builder's RED and gate commands in the builder's worktree, one pytest process at a time, and sends the output. Builders run no Python and commit with plain git. No symlink, wrapper or permission change.

## OI-13 (the user, directly: DR.6 chip, "Draw the chip")
- Items 12 and 19 deferred the "Not computable" chip to after Stage 5. It is drawn now: an optional `Figure.status_chip` in `src/deploy_vii/report_view.py` (the brief preferred `Figure` over `Block` because the producer returns the figure), set by the DR.6 producer `distressed_figures.rating_trigger_figures`, rendered by `app.js` in the block head; the strict xfail tripwire XPASSes and its marker is removed. `src/deploy_vii` change approved directly; D12 records for every reused file touched. Deferred: G2 genuine `cp2h-fp05-ratings` cases and a native DOM recheck of the CP-2H page.

## OI-14 (the user, directly: CP-1 blank limitation, "Fix in source_context")
- `validate_source_context` (`src/deploy_vii/source_context.py`) refuses a blank (`is_blank`) scope or source limitation, test-first, with a D12 record. CZR's CP-1 validates through it; only a blank limitation is newly refused.

## OI-15 (the user, directly: item 55 rewrites, "Leave unapplied")
- Decided: the three verified readability patches stay in `work/build/keep/s53-rt/` and are not applied. They give no behaviour gain, and two touch the receipt verifier, which would reopen mx-adversary review and every genuine owner suite. Apply with the next functional change to those functions.

## OI-16 (ruff findings in `src/deploy_vii`: decided, leave)
- `statement_extract.py` TRY004 (:234-263) and `report_view.py` SIM102 (:312) are import-era style findings under ruff's default rules; the project gate checks changed files only. TRY004's fix changes the public exception type of `extract_pack_statements`; SIM102's moves report_view bytes for no behaviour gain. A `noqa` would breach the cap. The user can overrule; it would need their word for `src/deploy_vii`.

## OI-17 (B4: bb4553b and 1a1a140 kept as records)
- The preparer filled their chains from the lane's first-parent history rather than folding them; both pass the strict probe. Folding would discard records that are consistent once the chain is filled.

## OI-18 (CP-3D empty summary: same double issue as CP-2E, folded into B2)
- B2's builder found by reading that `cp3d.py` gives `""` the same two issues as CP-2E (`summary.text: empty text` from `analyst_text`, then RunText's "at least 1 character"). It is the owner item's defect class in the file B2 already changes, so the same rule applies there, test-first. CP-DR does not have it (an empty answer skips `_model_text_issues`).

## OI-19 (B1 review: the shell-css checker models what can undo `flex-shrink:0`)
- Review M1: a `flex` shorthand (`flex:1`, `flex:1 1 auto`) resets shrink and the checker missed it; `flex:none` was refused though correct. M2: a scoped descendant rule alone (`.x .module-list{flex-shrink:0}`) satisfied the check while the base list could shrink.
- Rule, fail closed: (1) a rule whose selector list holds the plain `.module-list` exists, and the last effective shrink among plain `.module-list` rules (outside `@media`) is 0; (2) no other rule that applies to `.module-list` (compound, descendant, comma, inside `@media`) sets a non-zero effective shrink, whatever its order (a more specific or later rule would win). Effective shrink comes from `flex-shrink` and from the `flex` shorthand by the CSS grammar (`none` → 0; `auto`, `initial`, one number → 1; `<grow> <shrink> [<basis>]` → `<shrink>`; `<grow> <basis>` → 1); any value the checker cannot read (`inherit`, `unset`, `var(...)`) fails. Property names are case-insensitive; `!important` is stripped from the value before reading it; pseudo-elements (`::before`) do not count as the list. CSS nesting is not modelled (app.css has none): a rule body with `{` inside fails the check.
- Addendum: importance fails closed. Any applying rule that declares a non-zero effective shrink with `!important` fails the check, whatever its order (an important declaration beats the plain 0).

## OI-20 (B6 review Info, new owner item: blank `event_scan_explanation`)
- B6's reviewer found that a blank `event_scan_explanation` passes `validate_source_context` and renders a blank `event_scan` gap row (`source_context.py:107`, :513-518; probe `scratchpad/review-b6/probe_event_scan_blank.py`, exit 1). It predates this branch and is an explanation, not a limitation, so OI-14 does not cover it. It is a `src/deploy_vii` change: not built; it goes to the user with the recommendation to refuse it the same way (one `is_blank` check, test-first, D12 record).
