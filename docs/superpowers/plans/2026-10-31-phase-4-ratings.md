# Phase 4: CP-2H reads the context's ratings Implementation Plan

**Status:** draft 2026-10-31 on `claude/context-plan-build` (e871f90c); not started. Phase row:
`docs/superpowers/plans/2026-10-31-context-file-consumption.md:327`; questions and rulings:
`work/context-plan/reviews/phases-2-8-questions.md:68-76`; user ruling B9 (`docs/rulings/2026-10-31-context-plan.md`).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** A CP-2H run whose pack holds a `context` source builds its rating register from the
context's `ratings` rows with the real agency names (S&P, Moody's, Fitch), reads the trigger terms
from an attached `ratings` source, and refuses with today's pinned texts when either is absent. A
pack without a `context` source behaves exactly as today.

**Architecture:** `RatingsSource` (`cp2h.py:239`) is what `_compose` consumes (`:1433`), and today only
`parse_ratings` (`:407`) builds it, from three synthetic pages with the fictional scale header
`Position  Alder Ratings  Brook Credit` (`:162`). A second builder, `context_ratings(context, terms_pages)`,
makes the same type from `RunContext.ratings` (`context.py:119-124`, `:239`), a fixed combined-scale table in
code, and the terms block of page:3 parsed by the existing `_block`/`_terms`. `_compose`, the tables, claims
and validators are untouched except where cells cite a `context` line instead of a `ratings` page.

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a refused
  context becomes an explicit validation issue, never an empty register); no network call; no key read.
- Python owns every figure. Scale positions, notches and headroom are Python's; the model never quotes a
  context figure.
- `src/deploy_vii`: only `src/deploy_vii/methods/cp2h.md`, wording-only edits that this phase makes stale (B9),
  reviewed by `mx-feature`, with a D12 `post_import_patches` record in the repo-authored shape (B14, Task 4). No other
  `src/deploy_vii` file changes.
- A pack without a `context` source, or with a context whose `ratings` is empty and a `ratings` source,
  behaves exactly as today: every frozen `cp2h-owner` case, `PINS.json` entry and oracle stays green and unchanged.
- Context figures are labelled per Q-X (`phases-2-8-questions.md:12-14`): `value_class="source"`, citing the context
  file's own line, plus a "user-supplied" limitation. No new authority value.
- Reports end `Not verified:` and list table, row and field changes (R7): this phase changes T2R.2 and
  T2R.8 facts for context packs only (citations, position `value_class`, "Not stated" values) and the
  CP-2H `read_inputs` view (`register.source_id`, `register.pages`).
- Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
  Gates on changed files: `ruff check`, `ruff format --check`, `mypy`; the full suite once before hand-off (B3).
- Shared files (build in sequence): `owners/cp2h.py` (Phase 8 next); `host.py` (`_OWNER_SCOPES`) is also
  edited by Part B O1 task 3 (`_submission_schema`, host.py:583-606) and O7 (CP-DR scopes): this phase touches
  only the `("CP-2H", "rating_triggers")` row (`host.py:103`), so the edits do not overlap but the file does;
  rebase on the Part B tip before Task 3. `tests/test_host_h1.py` (exact-set check `:350-359`, scope helper `:557-561`)
  and `cases/PINS.json` are shared with O7: the Task 3 `cases/PINS.json` re-pin follows O7's, or merge on top of it. O6 reads
  `methods/cp2h.md` for prompt text: land Task 4 before O6 batch 2.

## Findings carried into this phase

**Stage 8 Low, `owners/cp2h.py:1616` (`_gap_issues`).** The unsettled-reference check runs only
`if name == "gap" and not found`. A gap text with any other issue (a phrase-guard line, a blank, a
malformed reference) therefore omits the "names a fact that is not settled" line: the refusal under-reports and
the analyst needs a second round. Dropping the guard is not enough: `prose.tokenize(g.gap)` (called without the
`gaps=` set `prose.issues` passes, `prose.py:312-316`) raises `ValueError` on a syntax error, and
`bound[run.text]` raises `KeyError` on an unbound reference, so the check must tokenize as `prose.issues` does
and skip only references that are not in `bound` (`_prose` already reported those). Existing pin:
`tests/test_codex_render_fixes.py:93-102`.

## Task 0: the oracle `cases/cp2h-context-owner/`

Prepared by a **preparer** that is not the builder of Tasks 1-4, reviewed by an independent `mx-precise`,
frozen and listed in `cases/PINS.json` (`python3 -I cases/pins.py`; the glob `cases/*-owner/*` picks it up,
`cases/pins.py:12-21`) before Task 1 starts. Layout as `cases/cp2h-owner/`: `manifest.json`, `submissions.json`,
`expected.json`, `cp2h-context-view-tree.json`, `builder/build.py` (stdlib only, never imports `deploy_vii`),
plus the context files `context-*.json` saved in the form's layout (`JSON.stringify(o, null, 2)`, as
`cases/context/primary-full.json`). The preparer runs the product's table, claim and render validators and a scratch
double rebuild before handback and reports their exit codes (AGENTS.md "Module builds").

**Run and upstream.** Run `cp2h-context-owner-*`, issuer `northbridge-synthetic`, as-of 2026-01-10,
pathway `distressed_restructuring`, case kind `synthetic`: the same run, financial pack, CP-0/CP-1/CP-2A/CP-2G
closed chain as `cases/cp2h-owner/manifest.json` `cases.positive`, so every CP-2G metric and CP-1 ratio is
the already frozen value. Each context carries `run.as_of` 2026-01-10 and the same issuer, or `context_facts`
refuses (`context.py:733-770`).

**Combined scale (the ruling's fixed table; the preparer writes it in the manifest from the agencies' public
scales, the reviewer checks every row).** 1 AAA/Aaa, 2 AA+/Aa1, 3 AA/Aa2, 4 AA-/Aa3, 5 A+/A1, 6 A/A2, 7 A-/A3,
8 BBB+/Baa1, 9 BBB/Baa2, 10 BBB-/Baa3, 11 BB+/Ba1, 12 BB/Ba2, 13 BB-/Ba3, 14 B+/B1, 15 B/B2, 16 B-/B3,
17 CCC+/Caa1, 18 CCC/Caa2, 19 CCC-/Caa3, 20 CC/Ca, 21 C/C, 22 SD/RD (S&P SD, Fitch RD), 23 D (S&P, Fitch only). S&P and Fitch share
the letter symbols; Moody's has the numeric ones. `Withdrawn` and `Not rated` have no position (as `UNRATED`, `cp2h.py:164`).

| Case | Context `ratings` rows | `ratings` source | Expected |
|---|---|---|---|
| `positive` | S&P issuer BB, Negative, 2025-11-14; Moody's issuer Ba3, Stable, 2025-10-02 | the `cases/cp2h-owner` positive page:3 with `Alder Ratings`->`S&P`, `Brook Credit`->`Moody's`; pages 1-2 present and ignored | T2R.2: positions 12 and 13, instrument `Not stated`, each text field `value_class` `source` citing its own object-anchored span of source `context` (locator and quote pinned per field); position `value_class` `calculated`, `derives_from` the rating fact, formula `position of the rating on the fixed combined scale`, period `Rating dated 2025-11-14`; T2R.8: notches 1, lower rated `Moody's`, outlooks `Different`, period `As of the rating register, publication date not stated` (the existing undated text); T2R.3-T2R.6, T2R.9 headroom, reached flags and first years equal the frozen `cp2h-owner` positive values row for row (same thresholds, same CP-2G metrics); limitations include the user-supplied line and the fixed-table line (below) |
| `gap` | S&P BB, Negative, `as_of` `""`; Moody's `Withdrawn`, Stable, 2025-10-02 | as the `cp2h-owner` gap page:3 (one threshold `Not stated`), agencies renamed | S&P date `Not stated`, S&P position period `Rating date not stated`; Moody's position, notches, lower rated, outlooks `not_applicable` (as the frozen gap case); the unstated threshold missing with its root reason; both source limitations plus `The rating date is not stated for S&P.` |
| `outlook_unstated` | S&P BB, outlook `""`; Moody's Ba3, Stable | positive terms | outlook `Not stated`; T2R.8 `outlook_match` `not_applicable` (status) with reason text `An outlook is not stated for S&P` (two unstated outlooks must not read `Same`) |
| `no_ratings` | `ratings: []` | none | refusal `Rating register not found` (today's, `cp2h.py:154`) |
| `no_terms` | S&P BB, Moody's Ba3 | none, or no page:3 terms header | refusal `Trigger terms not found` (`cp2h.py:156`) |
| `off_scale` | `Other`, rating `A` | positive terms | refusal `Rating not on the scale: Other A` (`cp2h.py:353`) |
| `duplicate_agency` | S&P issuer BB; S&P facility BB- | positive terms | refusal `Rating register not found` (`_register` duplicate-agency rule, `cp2h.py:346-348`) |
| `terms_agency_unrated` | S&P BB; terms name Fitch | terms with a Fitch row | refusal `Trigger terms not found` (`parse_ratings` agency rule, `cp2h.py:431-432`) |
| `context_mismatch` | positive rows, context `run.as_of` 2026-01-11 | positive | `Context refused: run.as_of: context has '2026-01-11' but the run has '2026-01-10'` (the `context_facts` text, `context.py:764`) |
| `minified` | the positive rows, the whole context minified to one line (one span `line:1`) | positive | as `positive`; every context citation has locator `line:1` and a quote from the row object's `{` through the cited value, unique in the span (M5) |
| `uncitable_row` | positive rows where a row's cited text is not unique in its span | positive | `context-uncitable.json` in the form's layout where row 2 (Moody's) has its `"rating": "Ba3"` and `"outlook": "Stable"` values both on the same line as another `"Ba3"`/`"Stable"` text and its object cannot be quoted on one line (the preparer fixes the exact bytes); refusal `Context rating row 2 (Moody's) cannot be cited as one unique span; ratings not used`; no raise |
| `view` | positive | positive | `read_inputs` register block: `state` `present`, `source_id` `context`, agencies with `position` 12 and 13, triggers as the frozen positive view |

Every string, field and `value_class` the Task 3 tests compare is written into `expected.json` here and nowhere else. Pins that change: none. New pins: the new case's files and builder, plus `cases/PINS.json` (re-pinned with O7's). Existing frozen cases are re-run unchanged
as the regression gate (Task 5).

## Task 1: gap-text masking (Stage 8 Low)

**Files:** modify `src/deploy_workflow/owners/cp2h.py` (`_gap_issues`, `:1608-1625`);
test `tests/test_codex_render_fixes.py` (beside `:93`).

- [ ] **RED** (1 and 3 fail today): using `_bound_of("gap")` and `m2h.raw_payload("gap")` as `:93-102` does, with `ref`
  an unsettled fact id:
  1. gap `f"Our rating is weak [{ref}]."` -> `validate(...)` equals the `prohibited conclusion` line(s) **and**
     `gaps[0].gap: reference {ref} names a fact that is not settled`.
  2. gap `f"Coverage [{ref}] is missing {{"` (unterminated brace) -> a returned issue tuple, no exception, no
     "not settled" line for the unparsed text. (Passes at `HEAD` by design: it guards the `try`, per the review.)
  3. gap `f"Coverage is missing [{ref}] and [T2R.2.zz.nope]."` -> both the unbound-reference issue from `_prose` and the
     not-settled line for `ref`; no `KeyError`.
  4. The existing `:93-102` test and `test_h06_gap_limitation_spells_a_chip_naming_a_settled_fact` stay green.
- [ ] **Implement:** compute `gaps = {r for r, f in bound.items() if f.status != "known"}`; for `name == "gap"` call
  `prose.tokenize(g.gap, gaps=gaps)` inside `try ... except ValueError: continue` (the syntax error is already reported by
  `_prose`; a comment says so) and append the not-settled line for each non-text run whose `run.text in bound` and is in `gaps`;
  remove the `not found` guard. Dedupe stays with `dict.fromkeys` in `validate`.
- [ ] Run `tests/test_codex_render_fixes.py tests/test_method_cp2h.py tests/test_owner_cp2h.py -q`; gates.
- [ ] Commit: `fix(cp2h): gap text reports an unsettled reference beside its other issues (Stage 8 Low)`.

## Task 2: the context register builder (pure; sensitive: figures)

**Files:** modify `src/deploy_workflow/owners/cp2h.py`; test new `tests/test_cp2h_context_register.py`.
Depends on Task 0 (expected values), Task 1 (same file).

**Behaviour.**
- `COMBINED_SCALE: Mapping[str, Mapping[str, int]]` for `S&P`, `Moody's`, `Fitch` per the oracle table; a module comment
  states it is a code table, uncited (the ruling's recorded cost).
- `context_ratings(ratings: Sequence[Rating], terms_pages: Sequence[str]) -> RatingsSource` (`Rating` from
  `deploy_workflow.context`): rows in context order, one `RegisterRow` each with `instrument` `"Not stated"` (the context
  has no instrument field), `date` `"Not stated"` when `as_of == ""`, `outlook` `"Not stated"` when `""`, `position` from
  `COMBINED_SCALE[agency].get(rating)` (None for `UNRATED`), and `line` set to `str(i)` (the row index; the cell builder resolves the citation, Task 3) and `source` `"context"`. A rating not on the agency's scale, or an agency without a scale (`Other`), raises
  `SourceIssue(clipped(("Rating not on the scale: ", agency, " ", rating)))`; a repeated agency raises
  `SourceIssue(REGISTER_NOT_FOUND)`; an empty `ratings` raises `SourceIssue(REGISTER_NOT_FOUND)`.
- Terms: the existing `_block(page3, TERMS_HEADER, 5)`, `_rows`, `_terms` and the rated-agency rule, so every existing
  terms refusal text is unchanged; a missing page, header or empty block is `Trigger terms not found`.
  `register_published` is `PUBLICATION_NOT_STATED` (a context row carries its own date); `terms_published` from page:3.
- `RegisterRow` gains `source: Literal["ratings", "context"] = "ratings"` (default keeps every constructor call as is); every branch on origin tests `source`, never `scale_line is None` (`_agency_register`, `cp2h.py:951`).
- Refusal order: the register (empty, duplicate, off-scale) before the terms, as `parse_ratings` orders them.
- `possessive(name)` helper: `name` unchanged when it already ends in `'s`, else `name + "'s"`; used at the three sites `cp2h.py:953`, `:1264`, `:1877` so text reads "Moody's rating", not "Moody's's"; every frozen text is unchanged. RED `test_possessive` compares the oracle's pinned strings (M3).

**RED tests** (each fails with `ImportError`/`AttributeError` first; inputs from Task 0 `positive`, `gap`, `outlook_unstated`):
`test_positive_positions` (BB -> 12, Ba3 -> 13, `Withdrawn` -> None); `test_not_stated_values` (`as_of ""` -> `Not stated`,
instrument `Not stated`); `test_scale_table_matches_oracle` (the code table equals the manifest's table entry for entry, no extra symbol); `test_off_scale_refused` (`Other`/`A` -> the exact text); `test_duplicate_agency_refused`;
`test_empty_ratings_refused`; `test_terms_missing_refused`; `test_terms_agency_unrated_refused`; a hypothesis property: for any
two listed S&P symbols `a`, `b` the notch count `abs(pos(a) - pos(b))` equals the index distance in the oracle's symbol list.

Run: `tests/test_cp2h_context_register.py tests/test_method_cp2h.py -q`; gates. Commit:
`feat(cp2h): register from context ratings on a fixed combined scale`.
Review: `mx-adversary` (positions and notches are figures).

## Task 3: wiring, citations, scope and view (sensitive: what the model reads, citations)

**Files:** modify `owners/cp2h.py` (`PackScope` `:557`, `_Book` `:724`, `_agency_register` `:931`, `_divergence` `:1242`,
`_own_limitations` `:1860`, `validate` `:1669`, `ratings_source` `:1642`, `_parsed_source` `:2167`, `SCOPE` `:1941`,
`_adapted` `:1999`, `context_block` `:2190`, the `SCOPE` comment `:1939`, extend Phase 3's `context_cites.py` (`ratings[i]` paths) per item 3); modify `src/deploy_workflow/host.py` (the `("CP-2H", "rating_triggers")` row and its comment `:102`) and `docs/CP2H-OWNER-LEASE.md:46` (scope wording);
tests `tests/test_cp2h_context_wiring.py`, extend `tests/test_host_h1.py` (the CP-2H rows `_LEASED_ROWS` `:460`, `:496-498`; exact-set `:350-359`) and
`tests/test_connect_cp2h.py`.

**Behaviour.**
1. `PackScope` gains `context: RunContext | None = None` and `context_refusal: str | None = None` (defaults keep every
   existing constructor call). `_adapted` calls `context_facts(pack)`; a `ContextRefused` becomes
   `context_refusal = clipped(("Context refused: ", "; ".join(problems)))`, never swallowed. `SCOPE` and the host row
   become `identity, financial, ratings, context` (`_held` returns only held sources, so a pack without `context` is unchanged).
2. One selection helper `register_source(scope) -> (Source, RatingsSource)` (context path when `context is not None and
   context.ratings`, else `ratings_source` + `parse_ratings`) is used at all three sites that parse today: `validate`
   (`:1683`), `compute` (`:1904`) and `_parsed_source` (`:2175`) (M1; a `compute` that kept `parse_ratings` would raise on a
   context pack). `validate` order: stale upstream, then `context_refusal` alone, then register refusals (empty, duplicate,
   off-scale, uncitable row) before terms refusals, then content issues. A context with no
   rows and no `ratings` source is today's `Rating register not found` (`ratings_source` `:1646-1650`); a context with
   rows and no `ratings` source is `Trigger terms not found`.
3. `_Book` takes an optional context `(source_id, sha256)`. Citations are **object-anchored** and come from Phase 3's
   `src/deploy_workflow/context_cites.py` (Phase 3 rev 3 builds it for CP-3D, `phase-3-market-evidence.md:70-73`;
   Phase 4 **imports** it and builds after Phase 3; if Phase 4 is ever built first it builds the helper to Phase 3's contract
   there). The helper gives, for a context field path, a `Citation` quoting the key/value text on its own line when unique there,
   else the text from the object's `{` through the value when that is one line (a minified file is one `line:1` span), else
   `None`. Phase 4 adds the `ratings[i].<field>` paths to it (Phase 3 covers `quotes` and `deal_terms`) with a test in
   `tests/test_context_cites.py`; the vii-side parity test is Phase 3's. A `None` for any cited row field is the named issue
   `Context rating row <n> (<agency>) cannot be cited as one unique span; ratings not used` (a `SourceIssue` in the context
   path), never a raise or a guessed locator. `instrument` and a `Not stated` date or outlook are text facts with
   `value_class="source"` citing the row's `rating` value. The position is a calculated number (`derives` = the rating
   fact), formula `position of the rating on the fixed combined scale`, no scale citation. T2R.3 terms still cite `ratings`
   `page:3`.
4. T2R.2 position period `Rating date not stated` and `Not stated` values as in Task 0; `outlook_match` is `not_applicable` when either
   outlook is `Not stated`.
5. `_own_limitations` (M2): on a context run the false fixed lines are **replaced in place**, as `out[7]` is for CP-1D
   (`cp2h.py:1869`): `out[0]` (synthetic agencies, `:1801-1802`) becomes `Agency ratings and outlooks are user-supplied in
   the context file; trigger terms are read from the attached agency source.` and `out[6]` (source's combined scale, `:1826`)
   becomes `The notch difference is measured on the module's fixed combined scale; outlook weighting and sub-notch
   differences are not modelled.` Then it appends:
   `Scale positions come from a fixed combined-scale table in the module, not from an agency source.`; one
   `The rating date is not stated for <agency>.` per `Not stated` date; one `Rating scope: <scope> (<agency>).` per row (Q1).
6. `context_block`: `register.source_id` `context`, `pages` `[]` for a context register; unchanged for a source register.

**RED tests** (Task 0 cases; each fails on `HEAD`): `test_positive_matches_oracle` (every cell of T2R.2, T2R.8 and the
limitations equals `expected.json cases.positive`; T2R.3-T2R.6, T2R.9 equal the frozen `cp2h-owner` positive cells apart from
agency names); `test_gap_matches_oracle`; `test_outlook_unstated`; `test_refusals` (table above, one assert per row, exact text);
`test_context_mismatch_refused_not_swallowed`; `test_citations_resolve` (`citation_issues` over the pack returns `()` for
every context citation, and the quote is the oracle's pinned quote); `test_minified_context_cites` (`minified` case: locator `line:1`, no raise); `test_uncitable_row_named_issue`; `test_compute_on_context_pack` (`compute` returns the oracle report, M1); `test_possessive_texts` (the oracle strings for `Moody's`); `test_view_register_block` (equals the oracle view tree);
`test_host_scope_holds_context` (`host._OWNER_SCOPES[("CP-2H","rating_triggers")]` over a pack with `context` returns it,
and over a pack without returns exactly `identity, financial, ratings` as today); `test_pack_without_context_unchanged`
(`PackScope` built as before: `compute` output equals the frozen `cases/cp2h-owner/expected.json` cells and limitations for each case, not a re-run of the code under test). Real CP-2H rows are `_LEASED_ROWS` (`tests/test_host_h1.py:460`, `:496-498`); update them with the exact-set check.

Run: `tests/test_cp2h_context_wiring.py tests/test_host_h1.py tests/test_connect_cp2h.py tests/test_method_cp2h.py tests/test_owner_cp2h.py -q`;
gates. Commit: `feat(cp2h): rating register from the context, real agency names (Phase 4)`.
Review: `mx-adversary` (citations, the model's read scope, the refusal ordering). Task 1 review: `mx-precise`.

## Task 4: methods text (repo-authored `src/deploy_vii` file; B9)

**Files:** `src/deploy_vii/methods/cp2h.md`, `docs/reuse/manifest.json`. No test can fail for a wording cause; the report
says so under `Not verified:`. Nothing pins the md hash (`grep -rn 9e809987 cases docs tests` finds no pin), so no re-pin runs.

- [ ] Wording-only edits to the lines Phase 4 makes stale: purpose paragraph (`cp2h.md:7`, "parsed from the agency source
  (`ratings`)": add "or, in a run with a context file, taken from its `ratings` rows, with scale positions from a fixed table");
  Method (`:15`, notches: the combined scale is the fixed S&P/Moody's/Fitch table for context rows); one adapter bullet
  (`:29`, sources gain "and, when held, context"); the citations bullet (`:33-34`: a context row cites its object-anchored span of the
  `context` source); view tree bullet (`:35`, register `state`/`source_id`). Add no rule, number or table id.
- [ ] Append the B14 D12 record to `post_import_patches` in a follow-up commit: `destination` `src/deploy_vii/methods/cp2h.md`,
  `imported_sha256` = `prior_project_sha256` = `9e8099872e66...d618` (the file's sha256 before this edit), `project_commit` = the
  md commit, `sha256` = the new hash, `reason` beginning `repo-authored (not in files[])`, `review` = the mx-feature review file.
- Review: `mx-feature` confirms the diff is wording-only. Commit: `docs(cp2h): method text names the context ratings path (B9)`.

## Task 5: done-when as tests, and hand-off gates

- A CP-2H run on the `positive` context states `S&P` and `Moody's` with positions 12/13 and the frozen trigger values:
  `test_positive_matches_oracle`.
- No ratings -> `Rating register not found`: `test_refusals[no_ratings]`; no terms source -> `Trigger terms not found`:
  `test_refusals[no_terms]`.
- No context -> every frozen case unchanged: `test_pack_without_context_unchanged`, `python3 -I cases/pins.py --check` exit 0.
- Gap masking: Task 1 RED 1-3.
- Once, before hand-off: full suite `PYTHONPATH=src ".../python" -m pytest -q`, `ruff check`, `ruff format --check`,
  `mypy`, `python3 -I cases/pins.py --check`, `jscpd`-style duplicate check if the repo's gate set has it.

## Ruled decisions (Q1-Q5 ruled as recommended, `work/context-plan/reviews/phase-4-plan-review.md`)

No open questions remain. Each decision is also applied in the task it governs.

- **Q1 Ruled:** instrument is `Not stated` (the context has no instrument field); each row's `scope` is recorded only in a
  user-supplied limitation line `Rating scope: <scope> (<agency>).` (Task 3 item 5; one extra line per row).
- **Q2 Ruled:** two rows for one agency are refused with `Rating register not found` (Task 2, `duplicate_agency`).
- **Q3 Ruled:** terms are read from `page:3` only this phase; a page-agnostic search is deferred (needs `terms_page` on
  `RatingsSource` and a Phase 8 oracle change); the run guide (Phase 5 doc task) tells the user the layout.
- **Q4 Ruled:** an empty outlook reads `Not stated` (Task 0 `outlook_unstated`, Task 2).
- **Q5 Ruled:** `context` joins the CP-2H read scope (Task 3 item 1); O6's no-leak test (`part-b-o6.md:127`) lists `context` as
  read for CP-2H; the Task 3 reviewer confirms.

Not verified: nothing here ran (no test, gate or rebuild); the oracle values, the scale table, every line cite and the
`context_facts` behaviour with a three-line `ratings` array are read from `git show HEAD` only; whether `host.py`
and the `host._OWNER_SCOPES` pin tests need more than the CP-2H row, and the `jscpd` gate name, are unchecked; the `context_cites.py` contract is Phase 3's text, not its code (Phase 3 must build first).
