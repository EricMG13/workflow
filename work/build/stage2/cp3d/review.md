# CP-3D Stage 2 review (mx-adversary)

## CP-3D Stage 2 review (d8c3512 on lane 83c0d12): REQUEST CHANGES

Two Medium findings reopen the task: wrong citation quotes on facts (M1) and three lease acceptance tests that were never written (M2). The rest of the connection meets the lease.

I re-ran the fast gate: 1263 passed. `ruff format --check` and `mypy --strict` on the 9 changed files exit 0. `ruff check` exits 1 only on the SIM102 at `report_view.py:293`, which predates the change (I reproduced it on the 83c0d12 copy); the other 8 files pass.

Probe directory (P): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-s2-review/`. Each probe takes the worktree path as its argument.

### Medium
**M1. Citation quotes: facts carry quotes that do not support them, in the frozen positive case itself.** (Probe: P/p_citation_wrong_quote.py, exit 1.)
- **Cause:** `page_quotes` keeps the first submitted quote for each page, and `cite_of` attaches it to every fact that cites that page.
- **Positive case:**
  - `T3E.4.r04` (amortisation "Zero, as stated") and `T3E.4.r02` ("SOFR") both cite "spread 0 basis points".
  - `T3E.4.r03` (final maturity) and `T3E.4.r05` (instrument) cite the bid/offer sentence, not the maturity/instrument quote.
- **Lease contradiction:** with a quoted reference rate level, `T3E.3.r04.*` (4.30%) cite "spread 0 basis points". Lease T3E.3 says "a quoted level shows as a `source` fact citing its quote".
- **Nothing catches it:** `candidate_issues` → `citation_issues` checks only that the quote is verbatim on the page.
- **No test pins it:** my mutant C1 (keep the last quote on the page instead of the first) survives.
- **Not supported:** neither the lease nor the protocol supports the first-quote reading. The oracle pins page-level cites only.
- **Fix route:** either per-cell provenance (the Stage 1 composer keeps the ref, not just `_trace`'s page pair, which justifies reopening it for this Medium) or a LEAD ruling on what `Citation.quote` means. The implementer flagged this for LEAD; it was not ruled before review.

**M2. Lease Acceptance 5–6 tests are not written.**
- Missing: `begin` refused on a blocked or stale CP-0, `stale_binding`, and the consistent-forgery probe tamper.
- Brief §7 requires the store-run tests to be written now and run at Stage 5. The lease requires the tamper to forge consistently "so that probe, not an upstream hash check, refuses". That tamper is CP-3D's only test of the composition check at the receipt verifier (protocol §6).
- Patterns to copy: `tests/test_owner_s1a.py:795` (stale) and `:898` (tamper).
- Evidence: grep of `tests/test_owner_cp3d.py` (no stale or tamper test); no probe needed.

### Low
**L1. Test strength: my mutants that survive** (P/p_mutants.py, run on a full temp copy).
- **Absence rule:** removing the maturity, margin, amortisation or market-absence entry from `_ABSENCE_PATHS` survives (R1–R3, R5). Only the reference-rate path is pinned. The code itself is correct: P/p_rules_each_absence.py exits 0, each absence alone fires and `recovery_absence` does not.
- **Reader:**
  - D2: returning `Reading("missing", None)` for an absent pinned fact, instead of `identity_mismatch`, survives. So the "never a default" rule is unpinned.
  - D1: dropping the `module_id` check survives, because another module's head fails later on its missing facts anyway.
- **Other survivors:**
  - S1: `_settle` without its `retained_as` check;
  - A1: `_third_party` without the `authority` field check;
  - C3: `page_quotes` skipping technicals basis quotes.
- **Killed:** 15 of 27 (A2–A7, R4, R6, D4, C2, S2, S3, B2). The rest are equivalent (R7, D3, S4, B1).

**L2. The blank-quote inventory misses the eighth quote site, `terms.reference_rate.level.quote`.**
- The positive literal has no level, so the inventory walk never sees it, and the test's claim "a new quote field would fail here" is false for it. The report also counts seven sites.
- The fix itself is central in `on_page` and covers the site: all 9 `BLANK_VALUES` at all 8 sites are refused (P/p_blank_all_sites.py, exit 0).

### Info
- **Reader edge cases** (P/p_reader_edges.py): on a stale head, `own_limitations` includes the staleness note; on a genuine blocked head it raises `identity_mismatch`. CP-3C's lease should rule on both.
- **Scope-guard test:** `test_check_steps_refuses_a_spec_that_differs_in_its_source_flag` never reaches the `_OWNER_SCOPES` clause, because other clauses refuse both bad specs (P/p_scope_guard_isolation.py). The guard itself works, and G1-X's own test covers it.
- **`test_host_h1.py` one-line change:** the test is still meaningful. It still checks "no core → not_permitted", then registers the fake core, and monkeypatch restores the real one. The real-core schema is covered by test_connect.
- **Report housekeeping:** the report cites the pre-rebase SHA 094b1ef instead of d8c3512. The change is about 1,870 lines, over the 800-line PR cap, but that gate is not in the brief.

### Passed checks
- **Adapter:** the result equals the Stage 1 `MarketContext` for all three cases.
  - A missing or doubled CP-0 binding gives `identity_mismatch`.
  - The CP-0 module is read from its hash-verified blob.
  - The only exception handler is `except ValidationError` → `shape_issues`.
  - Gaps stay `None` and are never 0.
- **Reader:** exposes exactly the 7 pinned fields. D3 is OPEN and nothing claims completion.
- **Registrations:**
  - Rows are appended at the end, and the `OWNER_SPECS` row equals the lease.
  - There is no `_VIEWS` or `_PRECHECKS` row, and the lease agrees.
  - The `_OWNER_SCOPES` guard passes.
  - `SHIPPED_MAPS` puts `CP3D` directly after `CP3`.
  - `_RELATIVE_VALUE` and its `_spec_of` loop entry are both last, so CP-1C can append `peer-positioning` without reordering.
- **Deviations: all admissible.**
  - `validate_market_implied` without `pack`: the pages travel in `Upstream`.
  - The optional `pack` on `cp3d_upstream` is equivalent in practice.
  - `upstream_of` is a pure helper.
  - The `cited_refs` refactor preserves behaviour: P/p_cited_refs_equiv.py compared 28 submissions with 0 differences, exit 0.
- **Backlog rows:**
  - Blank quotes now get `<path>: empty text` before the page check, at all 8 sites.
  - The guard-limit notes are accurate; I probed the sign rule.
  - The `_whole_on_page` docstring is fixed.
  - `STAGE2_REFUSAL_DELTA` is untouched.
- **Library boundary:** held. The only `src/deploy_vii` changes are `bindings/cp3d.py`, one import and position in `shipped.py`, `methods/cp3d.md` and the `report_view.py` composition. There are no edits to `cases/`, `methodology.json` or TOOL-CONTRACT.

Not verified: the store runs (`tests/test_owner_cp3d.py`, `tests/cp3d_runs.py`) are deferred to Stage 5 and were not run or collected. Settlement through `Execution.finish` with real citations, the verifier probe on a real store, the FP03 render, the full suite and the PR-size gate were not run.
