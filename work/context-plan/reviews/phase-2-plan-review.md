# Phase 2 (identity and periods) plan: controller rulings and review, 2026-10-31

Plan: `docs/superpowers/plans/2026-10-31-phase-2-identity-periods.md` (draft, mx-feature, ~235 lines).

## Controller rulings on the draft's open questions (applied recommendations)
- **Q1** CP-0 borrower/aliases and CP-1A sector/sponsor stay render-side (`owner_rendering.py`), as the
  phases-2-8 ruling says.
- **Q2** CP-L10 with an `fy` current period refuses with `context_period_not_quarter`.
- **Q3** CP-1B refuses a submitted period pair that differs from the context pair.
- **Q4** the form's "Planned" tags for the fields Phase 2 consumes are removed in the hand-off commit
  (only those fields).

## Review (mx-autonomous, read-only), 2026-10-31: verdict fix (3 High, 5 Medium)
Probe: `scratchpad/p2probe/p2_facts.py <repo>` (exit 0; F-numbers match).
- **H1** (:69-71, :87-89) earnings sources state no borrower; CP-1 fixture has one entity `Northbridge
  Synthetic Group`, roles `["issuer"]` (tests/test_financial_workflow.py:227): ctx-match/punct/mismatch all
  give `not_supplied`. Fix: expect `not_supplied` on the earnings pack; match/mismatch from a separate pack
  whose sources state a borrower; CP-1B/CP-L10 cases keep the byte-identical sources; dedupe `found` (T4.2
  one row per scope, canonical_tables.py:206).
- **H2** (:84-85 vs :208) no `fy-2024` in the pack: `resolve` gives `None` and Task 4 refuses, contradicting
  E-NO-YOY (earnings.py:309). Fix: an unresolved prior passes as the context string (the gap); only an
  unresolved current period refuses.
- **H3** (:90-93, :226-236, :260) `earnings_update` has no CP-1A (contracts.py:52) and no delivery scope
  (owner_rendering.py:572-581, :105-364): `_capture` refuses `owner_render_scope`. Fix: render from a
  `credit_snapshot` context with `requested_modules` = the `s1a-credit-snapshot` scope's modules; drop Task 6's
  earnings delivery assertion.
- **M1** (:64) issuer is `Northbridge Synthetic Group` / `northbridge-synthetic` (cases/earnings/manifest.json).
- **M2** (:94-97, :189-191) CP-L10 runs `credit_snapshot` with `requested_modules ["CP-L10"]`; `context_facts`
  refuses on pathway (context.py:761): add a `credit_snapshot` CP-L10 context, explicit run, a `context`
  assessment in the CP-0 review; the preparer derives `expected.json` effects.
- **M3** (:96, :185) an absent Q4 2024 has no T4.14 dates: freeze an exact refusal (e.g. `unbound CP-1
  operand: q4-2024 (no CP-1 T4.14 period)`).
- **M4** (:121, :131) assumption lists also use `fld` `t:'list'` (form :785): new `t:'lines'` for aliases and
  guarantors only.
- **M5** (:102) `cases/pins.py` PATTERNS match nothing under `cases/context-identity-periods/`: extend them in
  the re-pin commit.
- Lows: O1 cites :246, :252-253; a `q4-2031` fixture in Task 0; E-QOQ-FLAT compare points only (limits clash
  with :212); `model_dump equals file` adds back `schema` (test_context.py:569).

## Controller rulings (2026-10-31)
- All findings accepted as proposed. H3: no new delivery scope (that would need a ruling); the earnings
  run's CP-1B result is asserted from the owner record, not a delivery.

## Re-review of rev 2 (mx-autonomous): fix (3 new Medium)
- H1-H3, M1-M5 and the Lows fixed (H1 :63-68, :78-81, :100-103, :179, :184; H2 :225-228, :237; H3 :71-74,
  :104, :263, :280; M1 :63-64; M2 :87, :112, :195; M3 :110, :202, :208; M4 :138, :148; M5 :118-120).
- **N1** (:72, :87) `requested_modules` in the contexts: `Run` settings forbid extra keys (context.py:65-72)
  and `preparation_request` uses only the preset. Fix: the pack's `Run` is set explicitly after
  `preparation_request`.
- **N2** (:66) CP-1 T4.2 roles come from the CP-1 review's `entities`, not source text; s1a's CP-1A also needs
  the `business` source (tests/s1a_runs.py:28, :107). Fix: pack B = `cases/snapshot` sources plus a borrower
  identity source; the CP-1 review adds a borrower entity (role `borrower`, scope-mapped).
- **N3** (:87) the CP-0 `context` assessment is required for pack B too.

### Controller rulings
- N1-N3 accepted as proposed.

## Re-review of rev 3: fix (N2 open) → controller applied
- N1 (:74-76, :91, :116), N3 (:91) fixed. N2: pack B's identity source says "No borrower ... is established";
  a second source contradicts it. Applied by the controller: pack B replaces the identity source with a
  preparer-written version carrying the borrower line; the 27 `identity` citations re-cut; new Low (business
  source "identifies no financial sponsor") noted as user-supplied, no gap. **Phase 2 plan approved.**
