# Phases 2-8 open questions: research (mx-autonomous, read-only) and rulings, 2026-10-31

Base `claude/context-plan-build` (60191a06 + rulings). Plan = `docs/superpowers/plans/2026-10-31-context-file-consumption.md`.
"Ruling" lines are the controller's applied recommendations (user, 2026-10-29) unless marked
"user"; `src/deploy_vii` items beyond B1 go to the user (marked **vii → user**).

## All phases
- `preparation_request` never sets `requested_modules` (context.py:711-718): a context run gets the
  pathway preset (contracts.py:48-71, 91-95). CP-2E and CP-L10 are in no preset; CP-1C
  (relative_value) and CP-4C (distressed) never share one.
- A context case's pack holds `context`; CP-0 assesses it (readiness.py:341-344); the pack hash
  changes, so builders rerun the upstream chain.
- **Q-X labelling of context figures.** `Fact.value_class` has no user-supplied value (contracts.py ~185).
  Ruling: `source`, citing the context file's line span, plus a "user-supplied" limitation (no vii).
  Cost: labels re-cut in every phase's oracles.
- No existing frozen oracle changes while a pack without context behaves as today (plan :323-324);
  each phase needs new context cases (separate preparer + independent `mx-precise` review).
- No phase needs `run_pathway` (O2): packs via `preparation_request` + `prepare`. A preset walk needs O1.
- Edits to repo-authored files under `src/deploy_vii` (for example `methods/*.md`, `bindings/*.py`)
  are vii (`docs/rulings/2026-10-30-open-items.md:5`).
- Shared files (build these phases in sequence): cp4c.py (6, 7, 8); cp1c.py (7, 8); cp2h.py (4, 8);
  cp3d.py, cp3c.py, cp2d.py (6, 8; cp3d also 3); cpl10.py (2, 8); earnings_workflow.py and
  owner_workflow.py (2, 5, O1); context.py and the form (2, 3, 6).
- Sizes: P2 large, P3 medium, P4 medium, P5 medium, P6 large, P7 large, P8 large.

## Phase 2 Identity and periods
1. Borrower-name mismatch: CP-1 T4.2 rows (canonical_tables.py:205-228; Role source_context.py:31).
   Ruling: a `src/deploy_workflow` comparison read from settled T4.2, recorded as a gap, names
   compared after casefold and punctuation folding; identity stays gated by CP-0
   `issuer_confirmed` (readiness.py:419-420).
2. Period kinds: `build_earnings_delta` takes QUARTER and FY only, same kind and length, no overlap
   (earnings.py:133, 313-318); the reader allows h1/h2 and mixed kinds (context.py:36, 452).
   Ruling: the reader and form refuse h-periods and mixed kinds on earnings runs; CP-1B keeps an
   `incompatible_periods` gap as backstop. Task 2 drift guard updated.
3. Comma-split names (form:686 split, :1265-1266 rejoin). Ruling: one name per line in the form's
   list fields (form-only; the reader already takes arrays); Task 2 guard updated.
4. CP-1B pinned to frozen cases: `_case_parameters` (earnings_workflow.py:1657-1669) feeds `_case_pins`
   (:848-870) and six call sites (:2010, :2210, :2312, :2375, :2860, :3342); limitation texts
   hard-code USD/IFRS/FY2024 (:1648-1653, :1679, :1899); dimension check earnings.py:147-150.
   Ruling: the CP-1B owner core (O1) reads periods from `context_facts` when a context is present;
   the no-context path keeps the three run ids.
5. Context periods vs CP-1 periods: T4.14 `period_id`s come from the submission
   (financial_periods.py:99). Ruling: match on T4.14 period_type, fiscal_year, fiscal_quarter, as
   earnings_workflow.py:1017-1044 does.
6. CP-L10 hard-codes 2025 quarters (cpl10.py:102-124). Ruling: offer the four fiscal quarters ending
   at `current_period`, labels from T4.14 dates.
7. CZR cannot come from a context (`issuer_id` "CZR" fails the slug rule, context.py:461; CZR files
   out of scope, rulings 10-30:5). Ruling: no CZR context case.
- Borrower/aliases in CP-0 and sector/sponsor in CP-1A: Ruling: render-side in `owner_rendering.py`
  (no vii), not inside readiness.py:467-470 / business_context.py.
- Oracles: new context earnings case and CP-L10 case. Files: earnings_workflow.py, earnings.py,
  owner_workflow.py, owners/cpl10.py, owner_rendering.py, context.py, form, new identity-check module.

## Phase 3 Market evidence
1. Talk shape: CP-3 never words talk as a level (cp3_relative_value.py:5-7, 20-21). Ruling: one
   indicative_talk range row per facility, no midpoint.
2. Staleness: reader refuses only post-as-of quotes (context.py:516). Ruling: "stale quote"
   limitation and a cap below High for quotes > 30 days before as-of.
3. **Blocking, vii → user.** CP-3 takes market evidence only as model-quoted spans of a `third_party`
   source (cp3_relative_value.py:8-11, 546-547); CP-3D likewise (cp3d.py:163); D2 classes `context`
   `unknown`; plan :16 says no model quotes a context figure. Options: (a) Python-built market
   evidence in CP-3 (vii cp3_relative_value.py); (b) a derived quotes source (breaks plan :16);
   (c) CP-3 unchanged, context quotes feed CP-3D only (Python-read, deploy_workflow owner).
4. Facility binding: Ruling: a context quote's `facility_id` must match CP-1 T4.18; unmatched → named gap.
5. `rv_quotes` (`inputs/rv_quotes.py`, vii): Ruling: leave the code; drop it from the docs.
- Files: owners/cp3.py, owners/cp3d.py, context.py.

## Phase 4 Ratings
1. Trigger terms: parser needs a three-page synthetic source with a fixed scale header
   (cp2h.py:157-163, 407-421). Ruling: register from context rows; terms from an attached source;
   no terms source → "Trigger terms not found" (:154).
2. Combined scale: Ruling: a fixed S&P/Fitch/Moody's position table in code (cost: uncited table).
3. Optional fields (form:718 vs :218-224). Ruling: "Not stated" for missing date and instrument.
- Also carry the Stage 8 Low from Modules: `owners/cp2h.py:1616` gap-text masking.
- vii: methods/cp2h.md wording (optional). Files: owners/cp2h.py.

## Phase 5 Attachments and modes
1. **Draft authority, vii → user.** No draft authority (readiness.py:28-30); CP-4 cites only executed
   or filed sources (cp4_legal.py:89, 470-482). Options: add `draft` (readiness.py, cp4_legal.py) with
   a fixed limitation, or defer draft mode (today's refusal stays).
2. "High confidence for draft-only CP-4": CP-4 has no confidence field. Ruling: restated as a
   downstream cap where CP-3 already caps on a blocked input (cp3_relative_value.py:23-26).
3. Attachment matching: fixed ids `portfolio` (portfolio.py:604), `prior_case` (cp8.py:74), `bridge`
   (cp1d.py:79). Ruling: a CP-0 `_PRECHECKS` gate (owner_workflow.py:597) refuses a review with no
   `source` gap for a declared but absent id; legal documents checked through CP-0 T3 authority.
4. CP-DR `research_questions`: superseded by O7b (OD2). Ruling: dropped from Phase 5.
- Files: owner_workflow.py, a new CP-0 precheck module.

## Phase 6 Pinned assumptions
1. D4: Ruling: fail closed, Decimal after unit conversion; an absence variant counts as differing
   (`repricing_absence` cp3c.py:143-144, `minimum_cash_absence` cp2d.py:112-113, multiple "not
   assessed" cp4c.py:101, `hedge_absence` cp2e.py:1774).
2. Prompt: O6 puts pins in prompts as data (plan :367). Ruling: settled by O6.
3. Precision: pins unlimited decimals vs submissions (cp2a.py:77, 90-91 4 dp fractions; cp3c.py:123
   whole bps; cp3d.py:193 and cp4c.py:101 2 dp). Ruling: the form and reader limit each pin to its
   submission's precision.
4. Matching: CP-2A pins in order and by count; a CP-4C pin binds every valuation case
   (cp4c.py:131-137); a blank hedge pin is a partial pin. Ruling: as found; stated in each lease.
- vii: methods/*.md "analyst assumption" wording (avoidable by recording semantics in the leases).
- Files: owners/cp2a.py, cp2d.py, cp2e.py, cp3c.py, cp3d.py, cp4c.py, context.py, form.

## Phase 7 Valuation
1. `auto` thresholds. Ruling: public comps when ≥ 3 included peers dated within 12 months (CP-1C's
   three-peer median, cp1c.py:93); else precedents when ≥ 3 within 36 months; else Insufficient
   Information; `blend` never automatic.
2. **Blocking, vii → user.** CP-4C's upstreams lack CP-1C (methodology.json:393-405) and they share no
   preset (contracts.py:48-71). Options: (a) add the edge and CP-1C to the distressed preset (vii);
   (b) CP-4C reads `user_multiple` / the cp4c pin (Phase 6); (c) CP-4C recomputes peers (breaks
   CP-1C ownership).
3. User comps lack currency and period end (context.py:136-142); CP-1C needs period ends
   (cp1c.py:294-301), shows ≤ 1 dp (:112, 290), operands are credit figures not EV (:129-135); NTM
   needs CP-2G's forecast.
4. **vii → user.** New CP-1C EV tables need methodology.json (tests/test_owner_cp1c.py:534) and
   bindings/cp1c.py. `user_list` peers wait for O7d (form:493).
- Files: owners/cp1c.py, cp4c.py, methodology.json, contracts.py, bindings (vii).

## Phase 8 Periods and currency
1. FX: CP-1 normalises facility FX (facility_fx.py:1). Ruling: no FX downstream; modules require
   CP-1's currency to equal `reporting_currency`, else a named mismatch (replaces cp2d.py:70,
   cp2a.py:1510-1514, cp1c.py:103-105).
2. Forecast years: CP-2G `BASE_YEAR = 2025` (cp2g.py:86-92), CP-4C likewise (cp4c.py:415-418).
   Ruling: the three fiscal years after an fy or q4 base from T4.14; other bases → named refusal.
3. Missing from the row: CP-2E (cp2e.py:864-865), CP-L10 (cpl10.py:90-124), CP-1B (earnings.py:147-150),
   CP-2A (USD only). Ruling: added to Phase 8.
4. Three presets → Done-when needs at least three runs. Ruling: so stated.
- vii: methods cp2g/cp2h/cp4c/cp1d.md period wording (cp2g.md:11; cp4c.md:12).
- Files: owners/cp1c, cp1d, cp2a, cp2d, cp2e, cp2g, cp2h, cp3c, cp4c, cpl10, earnings.py.

Not verified (researcher): no code or tests run; CP-1 period ids in real runs; JSON byte identity
JS vs Python for the Q-X citation; CP-2D minimum-cash unit; CP-4 with no legal source; form line
numbers read once.
