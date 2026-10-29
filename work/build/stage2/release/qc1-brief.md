# Q-C1 batch: FP-04 maturity wall becomes MODEL-owned (stage contract)

Approval: the user, 2026-10-29, relayed by the "LEAD multi-round behavior" session after the inventory report on lane 4b2d77b.
- Q-C1 is reversed. The FP-04 maturity wall is MODEL-owned, as the design says (approved page `rbot-fp-04-covenant-refinancing.dc.html:42` "MODEL · Fig. S.4"; pack brief `04-covenant-refinancing.md:31`).
- It lands as one batched oracle change in the Stage 2 close release, in one re-pin commit through the shared pin manifest.
- It follows the chart-oracle rules (AGENTS.md "Chart oracles", c62004e): a separate preparer, an independent mx-precise review, and a builder who is not the preparer. The ledger records all three agent ids.

Order of authority (user, 2026-10-29):
1. The approved front pages (`/Users/ericguei/Documents/DEPLOY VII/design/reference/`) decide what appears and how it looks.
2. The pack content briefs (`/Users/ericguei/Documents/Deploy Workflow Sessions/rbot-design-pack-2026-10-20/uploads/rbot-claude-design-pack/content/`) decide the provider and the data paths.
3. Inferences come last.

Values always come from settled module facts, never from the pack's numbers.

Worktree `../s2r-qc1`, branch `claude/s2r-qc1`, cut at release 5a6a746.

## Scope of the batch
1. **Ownership.** The `maturity-wall` `_Spec` (`src/deploy_vii/report_view.py:1171`, in `_COVENANT_REFINANCING`) gets owner MODEL. `pathway_has_model_block` (`:1900`) then adds CP-MODEL to covenant_refinancing (`contracts.py:44-56`). FP-04 reuses the built S.4 (the CP-1 chart slice, `docs/CP1-CHART-SLICE.md`; `report_view.py:1262-1270`, the `cp1_chart_series` producer). It adds no CP-2D figure.
2. **Oracles that move:**
   - `cases/legal/render-expected.json:1956`: `fixture.other_modules["CP-MODEL"]` changes from `not_in_pathway` to `unrun`.
   - The release's `other_front_sections.blocks["maturity-wall"]` pin in `cases/legal/render-expected.json`: owner, producers, kind, state, route and note, as the real render will show them.
   - `cases/cp2d-owner/expected.json:2541` and `cases/cp2d-owner/builder/build.py:1056`: CP-2D no longer owns the maturity-wall block. State what CP-2D's T2E.4 binding becomes (a table twin, or unbound) per the pack brief and the CP-2D lease.
   - `cases/cp4-owner/expected.json:318`, `other_five_sections`.
   - The CP-2D lease text (`docs/CP2D-OWNER-LEASE.md`, Rendered sections, and :126).
   - Any other pin the shared pin manifest or the chain moves.
3. **Not in scope.** The CP-2D maturity-wall table stays as it is everywhere else. Make no other chart change.

## Roles
- **Preparer (mx-feature, this dispatch):**
  - Writes the oracle and lease changes above, from the approved page, the pack brief, the CP-2D and CP-4 leases and CP1-CHART-SLICE. It changes builders and `cases/` and the CP-2D lease text only, never `src/` or `tests/`.
  - Runs `python3 -I cases/pins.py` to regenerate, then `--check`. Rebuilds the touched builders twice from fresh copies (the `F` tooling in `w2-brief.md`); the two rebuilds must be byte-identical.
  - Lists every value that moved and the reason for each.
  - Writes down the exact failing-test expectations the builder must meet.
- **Reviewer (mx-precise, later):** approves the oracle diff before any builder starts.
- **Builder (mx-feature, a different agent, later):** changes the `_Spec` owner and anything in `src/` and `tests/` needed to meet the frozen oracle, test-first. It never edits `cases/` or the lease.

## Gates (preparer)
- `pins.py --check` exits 0.
- The double rebuild is identical.
- `ruff format --check` passes on the builder files it touches.
- Report the tests that now fail against the unchanged `src/` (expected red; run only `tests/test_legal_render.py`, `tests/test_method_cp2d.py`, `tests/test_connect_cp2d.py`, `tests/test_method_cp4.py` and `tests/test_connect_cp4.py`). These are the builder's targets.

## Outputs (report as text, at most about 1.5k tokens)
- The tip SHA.
- Every oracle value that moved, with its source line (page, brief or lease).
- The failing tests the builder must turn green.
- Gate exit codes.
- Any question.
- `Not verified:`.
