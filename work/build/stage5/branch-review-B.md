## Stage 5.3 whole-branch review, lens B (seams and boundaries): `4822066..9f71bfa`

**Verdict: REVISE.** There is one Medium finding, and it is about the library boundary or the requirement, not a runtime defect. Registrations, the rendered-vs-settled path and the verifier seams all hold.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s53/B/`. The extracted tree copy has been deleted, and no worktree was written.

### Medium

**M1. `src/deploy_vii/distressed_figures.py` is a new library file that neither a manifest record nor a ruling admits. It also widens the deploy_vii→deploy_workflow import direction.**
- **Where it came from:** added in 2943d7b (W2 group d), 201 lines, holding the DR.2–DR.6 figure producers. `report_view.py:2994-3001` imports it to register them.
- **What allows other library changes, and why this file isn't covered:**
  - The plan's Global Constraints allow `src/deploy_vii` changes only through D12 registrations.
  - Ruling item 8 widens that to "the renderer seam in `report_view.py` (with `charts.py` and `bindings/`)… Any `src/deploy_vii` change outside it goes to the user."
  - G1X §6 admits only new `bindings/<cp>.py` files.
  - No ruling names this file, and `docs/reuse/manifest.json` has no entry for it. Only the reason line for the group d registration in `report_view.py` (manifest :1716) refers to it.
- **The import direction:**
  - It imports `deploy_workflow.restructuring_series` (`distressed_figures.py:61`).
  - The branch adds two more such imports in `report_view.py:2940` and `:2966` (`deploy_workflow.liquidity_series`).
  - G1X §6 says "`src/deploy_vii` never imports `deploy_workflow`", and `host.py:82` repeats it.
  - Precedent: `report_view.py:1860` (the CP1 chart slice's `financial_series` import) was already there at 4822066, so the pattern existed before the branch. It is still undocumented as an exception.
- **Failure scenario:** a library file and three cross-layer imports ship without the user ruling that item 8 requires. Any later boundary audit that trusts §6 is wrong about this code.
- **Probe:** `probe_boundary.py <repo> 4822066 9f71bfa`, **exit 1**. It flags only `distressed_figures.py` and lists the three new imports.
- **Fix (docs only, no code):**
  - Record a ruling (by applied recommendation, item 39) that admits `distressed_figures.py` to the item 8 chart seam.
  - Amend G1X §6 to "`bindings/` files never import `deploy_workflow`; the chart seam's producers may lazily import `deploy_workflow.*_series` leaf modules (CP1-CHART-SLICE precedent)".
  - Then whitelist the file in the probe.
  - Not taken: moving the file. Moving it into `deploy_workflow` keeps the reverse import, and folding it back into `report_view.py` changes pinned bytes.

### Low

**L1. The Stage 2 D12 records for `bindings/shipped.py` were never corrected as round 5 item 19 requires ("The fix batch corrects the Stage 2 records against this rule").**
- **What is wrong:** in the manifest's `post_import_patches`:
  - Records #32 (8aef58d), #34 (0fa5b4a) and #42 (6b679ca) each give the pre-Stage 2 sha 4ef3f9ff as prior, so the chain forks three times.
  - Records #35 (b48a3c5) and #43 (ab89173) give the branch side as prior, not the first parent.
  - Record #30 (b22972d) names a commit that does not change the file (fp = at = 4765995a).
- **Why no earlier stage caught it:** Stages 3 and 4 ran the strict probe from 697fe8a, after `shipped.py`'s last change, so these records were never checked.
- **Related LEAD records:** eleven records lack `prior_project_sha256` (cffdf9f ×9, 1a1a140, bb4553b ×2). These may come before the rule, so they are likely the owner's.
- **What is fine:** every file's last record still equals its sha at the tip. No change goes unrecorded; only the provenance chain is broken.
- **Failure scenario:** a provenance replay of `shipped.py` cannot walk from the import to the tip.
- **Probe:** `probe_d12_strict.py <repo> 4822066 9f71bfa`, **exit 1**; output in `d12_482.out`. The same probe from 697fe8a also exits 1, but only on the owner-held report_view records (3e5b537, 24f879a, 8aef58d).
- **Fix:** correct the six `shipped.py` records' `prior_project_sha256` and `project_commit` per item 19. Or, as item 22 did with the report_view records, send them and the LEAD records to the owner (`work/build/stage2/lows.md`).

### Info

- **Registrations (Review Focus 4): clean.** `probe_registrations.py` **exit 0**. It cross-checks:
  - `OWNER_SPECS` against `_PROBES` (CP-MODEL deliberately absent: deterministic, verified by `_verify_publications`), `_QUALIFICATION`, `_CORES`, `_ENTRY_VALIDATORS`, `SUPPORTED_ANALYTICAL`, `_VIEWS`, `host._SOURCE_STEPS` and `_OWNER_SCOPES`;
  - each core's `STEP_IDS`, `probe`, `ENTRY_VALIDATOR` and `QUALIFICATION`;
  - `SHIPPED_MAPS`: one map per module, no doubled `(block, slot)`, no foreign coordinates;
  - `DELIVERY_SCOPES`: rows equal keys, match triples are unique, and every section is composed in its pathway and bound by the requested modules;
  - composition rows (no shadowed `_spec_of` rows, no orphan blocks) and figure-producer pathways.

  Two notes, both documented or older than the branch: `maturity-wall` is bound by CP-2D but lists only CP-1 as producer (Q-C1), and `transaction-summary` is bound by CP-1A.
- **Rendered vs settled (Review Focus 5).** I traced `cp2d-fp04-liquidity` end to end:
  - `Execution.head_module` checks the blob against its head.
  - `Execution.view` is computed from the heads, not read from disk.
  - `_capture` (`owner_rendering.py:735-757`) requires each view module's facts, tables, claims and limitations to equal `head_module`'s.
  - `build`, then `_cr2_figures` (`report_view.py:2932`): marks come from `_chart_fact_cell`, and a value mismatch raises (`:2889`).
  - `_sections` requires payload equal to `_expected_block_payload(build(...))` and bound facts that are members of the head's facts.

  Nothing on this path is recomputed or defaulted. The DR group draws marks straight from facts, and a missing fact becomes a gap with its G#, never 0. One limit: G2 proves payload = `build(view)` and view = head, but not cell → fact. That link rests on the frozen render oracles, so Review Focus 5 holds only jointly with the Stage 3 render-equality tests.
- **Verifier seams.** Both CP-OS `_derive` and G2 `_capture` authenticate through `verify_owner_run_receipt`:
  - `_verify` binds run, pack and snapshot at entry and exit.
  - `_verify_publication_outcome` requires a publication directory whenever `receipt.model` is set, so CP-OS's missing explicit model/directory check is covered.

  Beyond that, CP-OS checks every view status against the receipt's heads and re-checks the snapshot after rendering. The calculation link must be in `receipt.model.files`. Refusal reasons are replayed (`owner_workflow.py:1710-1723`). I found no attacker-controlled bytes accepted unchecked at these joins, except the concurrent-write TOCTOU the threat model already excludes.
- **Stubs and catch-alls.** The only new broad handler in the branch is `owner_rendering.py:984`, which cleans up, logs and re-raises. All `except Exception` sites were already there at 4822066. `earnings_workflow.py:3687` (LEAD B1) is a documented fail-closed that keeps `__cause__`.

Not verified: no genuine store, G2 or CP-OS run was made (all deferred; the controller is running them), so the Review Focus 5 trace is static plus `_liquidity_figure`'s own check. I did not check the cell→fact correspondence across the other 17 scopes. I did not check whether the eleven LEAD records were written before round 5 item 19 was ruled. ruff, mypy and pytest were not run.
