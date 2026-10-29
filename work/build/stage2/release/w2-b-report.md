# Release W2-B report (mx-feature)

Lane B (lease and contract text, docs only) is committed on `claude/s2r-b` at a70ee52, on top of fb231d4. No ruling was missing. One lease item (CP-2D `run_rate`) was written as text only, because the code does not match it (item 5 below). `cases/`, `src/`, `tests/` and the lease pin header lines are untouched. The tree is clean and the changes are in 15 files under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-b/docs/`.

**Per item (all done in a70ee52 unless noted)**
- **Protocol `G1X-OWNER-CORE-PROTOCOL.md`:**
  - §5 now states the round 2 ordering rule (checked at `owner_workflow.py:1004-1010`, phase `walked` at `:1157`). The heading is "5. Plan ordering after CP-MODEL (built); not in G1-X".
  - §3 now says `read_inputs` serves `step_context` as well (`owner_workflow.py:820`, `:949`, `:272`, `:476`).
  - §6 gets the synthetic-limitation line (`deploy_vii/execution.py:472-478`).
- **CP-4 lease:**
  - Files text (was :36-42) now lists the `_ENTRY_VALIDATORS`, `_PRECHECKS` and `_VIEWS` rows (`owner_workflow.py:241`, `:593`, `:196-200`). The "read before submit" rule is credited to G1-X protocol §3, and the stale `:558` and `:530` cites are gone.
  - The seams (was :63-64) are now positional (`owners/cp4.py:119`, `:132`).
  - The `view` body text now reads `historical.pack()`.
- **FP04 lease (was :84-86):** an amendment says three of the five sections are CP-2D's and two are CP-3C's (`report_view.py:1168-1190`).
- **CP-3C lease:**
  - Acceptance 1 and the D3 line now include CP-1A (`tests/test_connect_cp3c.py:894-903`).
  - The "CP-4C has no core" text is fixed (`owners/cp4c.py:536`, `:1466`).
  - The `cp3c_closed(case, root, template)` signature is in (`tests/cp3c_runs.py:183`).
- **CP-4C lease:**
  - `Claims.from_sources` is now `claim_classes(submission, context)` (`cp4c.py:609`).
  - `Upstream` gains `inherited` (`cp4c.py:2629-2642`).
  - The text now says CP-4C calls `owners.cp2g.cp2g_reader` and does not define one (`cp4c.py:2686`).
- **CP-2H lease:** `TriggerReport` is now `RatingTriggersReport` (`cp2h.py:2079`; the internal dataclass keeps the old name at `:657`).
- **CP-2G lease:**
  - `Upstream` shows `inherited` (`cp2g.py:2705-2718`).
  - The scenario name is `T2B.1.<row>.name` (`:2641`).
  - The `base_period` invariant text is in (`:2658-2663`, `:798`, `:2471-2476`).
- **CP-1C lease:** `parse_peer_source(source, *, issuer_name)` (`cp1c.py:347`).
- **CP-1D lease:** `parse_bridge(pages: Sequence[str]) -> Bridge | None` (`cp1d.py:481`).
- **CP-8 lease:** the "both recorded in receipt" sentence is reworded. A `stale_binding` refusal cannot be in a receipt, because `write_receipt` raises it (`owner_workflow.py:1090-1093`, `:1454`). The sentence is in the lease's Refusals paragraph, not at :85.
- **CP-2A lease:** the unit rule now applies to settled operands only (`cp2a.py:1510-1515`, `:1542`).
- **CP-2E lease:**
  - The `cp2e_upstream` internal is dropped; it has no `def` in the code.
  - `macro_fx(*, pack, submission) -> MacroFxReport` (`cp2e.py:1827`).
  - The Files text gains the `_ENTRY_VALIDATORS["CP-2E"]` row (`cp2e.py:1906`, `owner_workflow.py:235`).
- **CP-2D lease:** a `cp2d_reader` run-rate pin extension is added as text. The reader does not expose `T2E.3.r01` (`cp2d.py:2761-2784`); CP-3C reads it from the head cell (`cp3c.py:2331-2394`). The text says the reader code and oracle do not change in this release.
- **TOOL-CONTRACT:** 14 matrix rows added after the CP-6 row, for CP-1C, 1D, 2A, 2D, 2E, 2G, 2H, 3C, 3D, 4, 4C, 8, DR and L10. Views, step shapes and source scopes were checked against `owner_workflow.py:285-560` and `host.py:93-107`. The CP-4 row also covers the raw-legal permission.
- **MODULES.csv:** CP-1C `downstream_consumption` is now `open`. D3 closures are not recorded; they wait for the Stage 5 runs.
- **Already at fb231d4, no change:**
  - CP-3 alias text: D1 states that both aliases canonicalise (`CP3-OWNER-LEASE.md:285-288`), and there is no alias clause in the Refusals section.
  - The CP-3 and CP-6 TOOL-CONTRACT rows.

**Questions and open points for the caller (no oracle value moved)**
1. Do you want `run_rate_annual` added to `Cp2dHead` and `cp2d_reader`? That would be a code and oracle change, so the lease text only records the extension.
2. The TOOL-CONTRACT rows for CP-2A and CP-L10 cite their lease key tree, not a view-tree file, because no `cp2a-view-tree.json` or `cpl10-view-tree.json` is committed and no lane owns them. The CP-2D row cites its manifest `view_tree_draft`.
3. The CP-1C, 1D, 2G, 2H, 3C and 4C rows cite `cases/<cp>-owner/<cp>-view-tree.json`. A1, A2 and D commit those files, so the rows are only correct once they merge.
4. A comment at `cp3c.py:2368` says the oracle's consumption block names the run-rate pin. It does not at fb231d4; that is a comment, not a lease issue.

**Oracle values moved:** none.

**Pinned, builder-hashed or reused files changed:** none. `docs/` text only. No builder hashes a `docs/` file; `cases/cpl10-owner/builder/build.py:828-834` names lease files as text references only, and I did not edit the CP-3 lease.

**Gates**
- Docs-only change, so ruff, mypy and the suppression counts do not apply, and `pins.py --check` is not run for B.
- `pytest tests/test_connect_cp1d.py -k no_reader_is_named_by_the_lease` and the `MODULES.csv` check in `tests/test_connect_cp3.py` (selected with `-k csv`): exit 0, 2 passed.
- `git status` clean after commit.

Not verified: the full pytest suite was not run (only the two lease-reading tests). The new TOOL-CONTRACT rows were checked by reading the view code, not by diffing a real view body against any key tree. The six view-tree files they cite are not yet committed, and that is A1/A2/D's work. No test fails when lease text and code drift apart, so the file:line cites are unchecked beyond this read. Nothing exercised the CP-8 stale-binding behaviour; the new text relies on `fix-infra-report.md` and a read of `owner_workflow.py`. No test applies to docs fixes.

agent=mx-feature fix-rounds=0 gates-first-pass=n/a
