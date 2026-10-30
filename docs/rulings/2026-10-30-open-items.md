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
