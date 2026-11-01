# Phase 3 (Market evidence: CP-3, CP-3D) Implementation Plan

**Status:** draft 2026-10-31, awaiting the oracle review (Task 0). Parent plan:
`docs/superpowers/plans/2026-10-31-context-file-consumption.md` (Phases 2-8 table, row 3; D1-D5).
Questions and rulings: `work/context-plan/reviews/phases-2-8-questions.md` "Phase 3" items 1-5; user
ruling B6 (`docs/rulings/2026-10-31-context-plan.md:24`): `src/deploy_vii/cp3_relative_value.py` may
change so Python builds CP-3's market evidence from the context's quotes (item 3, option a).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use
> checkbox (`- [ ]`) syntax.

**Goal:** a CP-3 and CP-3D run whose pack holds the `context` source (D1) uses the context's `quotes`
and `deal_terms` talk as market evidence, read and cited by Python; the model cites it, never writes
or quotes a context figure, and copies none (parent plan :16; ruling M2: it refers to Python's rows by row id only). A pack without a `context` source behaves exactly as
today.

**Done when (parent row 3):** CP-3 runs on a secondary context with Python-read quotes; talk-only
evidence caps confidence (tests listed under "Done-when as tests").

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a context
  source that cannot be read is a named validator issue, never a silent "no evidence").
- No network call; no key read. Exact `Decimal`/string handling: a context figure is shown as the
  context's own string; empty means "not supplied", never zero; Python adds no arithmetic except whole
  calendar days between two ISO dates.
- `src/deploy_vii`: only `cp3_relative_value.py` (B6). No new `src/deploy_vii` file, no
  `methodology.json`, `methods/*.md` or `bindings/` edit (B9 is Phases 4/6/8). `src/deploy_vii` must not
  import `deploy_workflow` (`bindings/cp1c.py:10` rule; the vii engine reads the `context` source itself).
  D12: one `post_import_patches` entry in `docs/reuse/manifest.json` for the file (`destination`,
  `imported_sha256` 0abc723d..., `prior_project_sha256` 6c804843... (the file at HEAD e871f90c, last
  entry `project_commit` 93c1ffca), new `sha256`, `reason`, `review`); `project_commit` = the commit
  where the file hashes to `sha256`, so the controller fills it after the commit. Review: `mx-adversary`
  (B6).
- A pack without a `context` source: every frozen case and pin stays green; `context_evidence(pack, facilities)`
  returns `()` and no code path differs.
- Reports end `Not verified:` and list table/row/field changes (R7).
- Test command: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
  Gates per task: `ruff check`, `ruff format --check`, `mypy` on changed files; complexipy <= 15 on
  new functions.
- Per B3 each task runs its affected tests; the full suite runs once before hand-off.

## Design (settled by B6, the questions file and the review rulings; the tasks build exactly this)

1. **CP-3 (vii).** `cp3_relative_value.py` gains ONE function,
   `context_evidence(pack, facilities) -> ContextEvidence` (frozen `Contract`: `rows`, `issues`, `gaps`; no
   other signature). It finds source `context` (`status == "ready"`), rebuilds the bytes as
   `"\n".join(span.text ...)` (as `context_facts`, parent Task 4), parses with duplicate keys refused and
   reads only `quotes[*]` and `deal_terms[*]`. `prepare` never calls `load_context` (the engine reads
   unchecked bytes), so the engine re-checks what it uses, each a named issue: a figure that is not a plain
   number (`context.py` `NUM`), a date that is not ISO or is after `pack.run.as_of`, an identity (issuer
   id/name) differing from the run, a wrong shape: `context source unreadable: <reason>` (never a silent
   "no evidence"). It re-applies no other form rule.
2. **Python rows, T3.3 order and ids (H1).** The model's own `market_evidence` rows keep ids `m01..` and
   come first; Python rows follow as `c01, c02, ...` in context order (`quotes` then `deal_terms`), so no
   existing row id or CP-6 read changes (`cp6_committee.py:575` reads T3.3 `kind` facts: Python rows carry
   the same fact fields). Python cells are raw `Cell`s with `value_class="source"` (Q-X) and citations, not
   `out.text`. Per quote with a matched facility: kind from the quote, Source `context`, Quote cell
   `"<facility_id>: bid 98.50, ask 99.00, price 98.75, yield 8.25%, spread 340 bps"` (supplied fields,
   context strings verbatim), As-of the ISO date, Limitation `"Provider: <provider>; user-supplied figure"`
   (+ stale text). Per `deal_terms` row with a matched facility and a complete pair: one
   `indicative_talk` range row (Q1 ruling, no midpoint), Quote cell
   `"<facility_id>: spread talk 325-350 bps; OID talk 99.0-99.5"`; a lone bound is omitted and named in the
   Limitation cell; As-of the deal `as_of` or `Not stated`.
3. **Citations are Python's.** Each figure is cited by its own JSON text inside one span (`readiness.py:145-160`):
   `"price": "98.75"` when key and value share a line, else (split key/value, or text not unique within
   its line) the text from the object's `{` through the figure when that is one line; if neither is a unique
   single-line quote the row is dropped into a named gap (`context quote ... cannot be cited as one unique
   span; not used`), never a guessed span. `_value_offsets(text)` (new) gives the offset of each
   `quotes[i].<field>`/`deal_terms[i].<field>` value; locator `line:<n>` of the offset in the rebuilt text. The object-anchored citation helper is
   `src/deploy_workflow/context_cites.py` (Phase 3 builds it for CP-3D, Phase 4 reuses it); the vii engine may not
   import `deploy_workflow`, so `cp3_relative_value.py` carries its own `_value_offsets`, tied to the helper by a
   parity test (same offsets, locators and quotes over every context file of this case).
4. **Binding by row id (M2).** `Basis` gains `context_rows: tuple[str, ...] = ()` (a deliberate default:
   the frozen submissions lack it; `Basis.quotes` stays for `third_party` rows). **N1:** `content_hash` is the
   sha256 of `model_dump_json()` (`contracts.py:78-79`), so an empty `context_rows` is omitted from the dump (a
   wrap serializer on `Basis` in this file; no `contracts.py` change) and every no-context submission and head
   keeps its hash. The model cites a Python
   row only by its id (`c01`); it copies no figure and writes no quote. `_bind_evidence` (:511) registers each
   Python row's kind under its id; `_basis_issues` (:572) refuses an unknown id (`<path>.basis.context_rows[j]:
   no context row c07`); `_talk_only` (:588), `strength()` (:507), the "market observation cites a market
   evidence quote" test (:619), the preference test (:657) and claims' citations (`out.cited`, :864) count
   context rows. A model `market_evidence` row with `source_id == "context"` is refused:
   `market_evidence[i]: context market evidence is built by Python; cite it by row id in a basis`.
   A `basis.quotes` entry quoting the `context` source is also refused (quotes only `market_evidence` rows).
   The third_party rule (:546) is unchanged for every other source.
5. **Facility binding (Q4).** A quote or deal row whose `facility_id` is not a T4.18 id (`upstream.facilities`,
   :337) yields no row and the own limitation `"Gap (Medium): context <quote|deal term> for facility <id>
   matches no CP-1 facility (T4.18); not used"`. A quote with every figure empty: no row, `"Gap (Medium):
   context quote for facility <id> carries no figure; not used"`.
6. **Staleness (Q2).** Whole days from the row's `as_of` to `pack.run.as_of`; `> 30` adds `"Stale quote:
   <facility_id> quote dated <as_of> is <n> days before the run as-of <run_as_of> (limit 30)"` to the row's
   Limitation and the own limitations, and appends the cap reason `a context quote is more than 30 days old`
   after `upstream.caps` and the talk reason in `_preference_issues` (:658-662). Exactly 30 days is not
   stale. An empty deal `as_of` is a "date not stated" limitation, never stale.
7. **Always labelled (Q-X).** Own limitation `"Market evidence rows from the context file are user-supplied
   figures"` whenever a Python row exists.
8. **CONTEXT block (M4).** `context_block` (:1228) adds `context_market_evidence`: `[{"row": "c01",
   "facility_id", "kind", "as_of", "provider", "stale": bool, "figures": "<Quote cell text>"}]` (shown so the
   model can choose; `provider` is user text, a JSON string). `confidence_caps` (:1319) gets the stale reason;
   `market_evidence_note` (:1312-1318) states, when only context rows exist, "Market evidence is the rows in
   context_market_evidence; cite one only by its row id in basis.context_rows; copy no figure", and no longer
   says "No third_party source ... Insufficient Information" while such a row exists.
9. **CP-3D (deploy_workflow, `owners/cp3d.py`).** Quotes only (Q1; deal talk is a range, not a price level).
   `MarketContext` (:159-166) gains `context_observations: Mapping[str, Observation]` (ids `o01..`),
   `context_dates` and `context_error: str | None`. `Observation` gains `context_row: str | None = None`, omitted from the dump when None (wrap serializer in
   this file, as `Basis` in Design 4; N1).
   Python builds the listed observations from `context_facts(pack)`: an `observed` quote gives `bid` (its
   `bid`) and `offer` (its `ask`), an `indicative_talk` quote gives `indicative_talk` (its `price`); each with
   `source_id "context"`, the figure's JSON text as `quote`, `level_text`, `as_of_text` `Month D, YYYY`.
   The model submits `Observation(kind, context_row="o01")` with every other field empty; Python expands it
   to the listed one before `submission_issues` (an unknown id or a filled field is the issue
   `observations[i]: context_row must stand alone and name a listed row`). An expanded observation skips only
   the `third_party` (:600), `_labelled` (:617-625) and `as_of_text occurs in quote` (:637) checks; `on_page`,
   `occurs`, shape, range (0, 200] and bid <= offer still run. `context_dates` feeds `published` so the talk
   period reads `Commentary published <date>` (:1088-1095). All observations of a submission share one
   `facility_id` (Q2 ruling; issue `observations mix context facilities`). `upstream_of` (:1938) catches
   `ContextRefused`, stores `context_error` and the validator emits `context source unreadable: ...` (no
   exception escapes). `own_limitations` (:1672) takes `run_as_of`: stale (> 30 days) adds the Design 6 text;
   `_single_dealer` (:1655-1660) says, for context observations, `Single dealer quotation from the context
   file (user-supplied); trading activity is not read` instead of "the sheet reports no trade". CP-3D has no view and no
   CONTEXT block (`owner_workflow.py:212-225`, :402-405), so Task 2 adds a pure function
   `context_observations_data(upstream) -> list[dict]` (ids, kinds, dates, level texts) to `cp3d.py`; Task 4
   embeds it in the prompt.

## Interactions with Part B (named)

- **O6 prompts (`part-b-o6.md` H2 :114, O3, M6 :116):** `relative_value` is an existing O6 step with its
  contract unchanged (o6 :109) and today's rule `CP3_EVIDENCE_RULE` (`live/prompts.py:583-587`: basis quotes
  repeat a `market_evidence` row; quotes only from `market_evidence_sources`) conflicts with by-id context
  rows. `src/deploy_vii/live/prompts.py` is changed (wording only) in Task 4 under user ruling B17 item 3. O6 rule
  O3 (the model never cites `context`) stays: the model cites by row id, not by quote. O6's M6 no-leak
  sentinel test forbids context figures anywhere in a prompt; it is exempted for exactly one fenced data block
  (Task 4). O6's `run_context_block` whitelist is unchanged. CP-3D's rule list comes from
  `cases/cp3d-owner/expected.json` refusals (ids [0..18]) so it misses the new checks until Task 4.
- **O1 owner walk (`part-b-o1.md` :88-89, :140):** edits `tests/cp3_cp6_runs.py` and `owner_workflow.py`; this
  phase edits neither. Journaled runs of the new case wait for O1; engine-level tests do not.
- **O7:** `owners/cp1c.py`, `cpdr.py`; no shared file. **Other phases:** `cp3d.py` is shared with Phases 6
  and 8; `context.py`/the form with 2 and 6. Phase 3 does not change `context.py` (a drift test pins the
  30-day limit) and changes the form only in Task 3.
- **`live/prompts.py` (B17 item 3):** the `relative_value` contract text (`CP3_EVIDENCE_RULE`, :582-587, used
  at :826) changes in Task 4, wording only, with a D12 record and `mx-adversary` review.

## Task 0: Oracle (separate preparer; independent `mx-precise` review; frozen and pinned before Tasks 1-4)

The builder of Tasks 1-4 neither prepares nor reviews it (B2). New case `cases/cp3-context-owner/`
(`manifest.json`, `contexts/*.json`, `submissions.json`, `expected.json`; every file added to
`cases/PINS.json`). Run: `northbridge-synthetic`, as-of 2026-01-10, `synthetic`, `credit_snapshot`; CP-1
facility `term-loan` (`cases/cp3-cp6-owner/builder/build.py:788`). Pack = the R3 pack. Its `market` source
is `third_party` and the R3 positive submission carries observed and talk rows on it and a restricted CP-2
(`cases/cp3-cp6-owner/submissions.json`, `expected.json`; probe `p3probe/probe_phase3.py` P1), so these cases
use the pack **plus** a `context` source built by `context.prepare`, and a case submission (`submissions.json`)
that sets `market_evidence: []` and cites only `context_rows` (except `with-market-row`). Because CP-2 is
restricted, every cap test pins the **full** issue string, never a bare "High refused". Values are hand-derived
from the rulings, never from code.

| Context (run_type) | Inputs | Expected |
|---|---|---|
| `observed-and-talk` (secondary) | q1 term-loan `observed` bid 98.50 ask 99.00 price 98.75 yield_pct 8.25 spread_bps 340, 2026-01-09, "Dealer A"; q2 term-loan `indicative_talk` price 99.25 spread_bps 335, 2026-01-10, "Dealer B" | T3.3 rows `c01` (Observed, 5 citations) and `c02` (Indicative talk, 2 citations), cells per Design 2, locators verified per file; strength {observed, indicative_talk}; limitation 7 |
| `talk-only` | q2 only; `market_evidence: []` | one row `c01`; own limitation `Market evidence is indicative talk only, not an observed market level`; issue for High: `preference.confidence: capped below High because CP-2 is restricted; the market evidence is indicative talk only` |
| `stale` | two observed term-loan quotes, 2025-12-11 ("Dealer A", 30 days) and 2025-12-10 ("Dealer B", 31 days) | rows `c01`, `c02`; only `c02` carries `Stale quote: term-loan quote dated 2025-12-10 is 31 days before the run as-of 2026-01-10 (limit 30)`; High issue ends `...; a context quote is more than 30 days old` |
| `unmatched` | q1 plus an observed quote for `revolver-x`, and a term-loan quote with every figure empty | one row; the two gap limitations of Design 5 verbatim |
| `deal-talk` (primary) | one deal row term-loan, talk_spread_bps 325-350, talk_oid 99.0-99.5, 2026-01-08; no quotes | one `indicative_talk` row `c01`, `term-loan: spread talk 325-350 bps; OID talk 99.0-99.5`, 4 citations, no midpoint |
| `with-market-row` | `observed-and-talk` plus the R3 positive `market` rows in the submission | order `m01, m02, c01, c02`; existing m01/m02 cells equal the R3 positive oracle |
| `no-quotes` | `quotes: []` | no Python row, no limitation; report equals the R3 positive CP-3 head for the same submission except `pack_sha256` (the pack gained a source) |
| `minified` | `observed-and-talk` on one line | as `observed-and-talk`; locator `line:1`; object-anchored quotes (Design 3) |
| `bad-bytes` | a `prepare`d pack (no `load_context`) with quote `price "98,75"`, an as_of after the run, a different `issuer_id` | issues `context source unreadable: quotes[0].price is not a plain number` / `...as_of ... after the run as-of` / `...issuer_id differs from the run` |

`expected.json` also names the model-side refusals with their full strings: `context-row-submitted`,
`context-quote-cited` (a `basis.quotes` entry quoting `context`), `unknown-context-row` (`c07`),
`talk-level-wording` (talk-only rationale "trades at 99.25", existing level rule :127-144), and for CP-3D on
`observed-and-talk`: offered `o01` bid 98.50 ("January 9, 2026"), `o02` offer 99.00, `o03` indicative_talk
99.25 ("January 10, 2026", published 2026-01-10), refusals `cp3d-filled-context-row`,
`cp3d-unknown-context-row`, `cp3d-mixed-facilities`, `context-unreadable`, and the context single-dealer and
stale limitations. Existing oracles and pins: none change. The preparer runs the product validators and a
scratch double rebuild and reports exit codes; `mx-precise` reviews against B6, the questions file and this
plan; the controller freezes and re-pins.

- [ ] Preparer writes and self-checks the case; independent reviewer approves; controller freezes.

## Task 1 (SENSITIVE: figures, `src/deploy_vii` diff; `mx-adversary`): CP-3 context evidence in the engine

**Files:** modify `src/deploy_vii/cp3_relative_value.py`, `docs/reuse/manifest.json` (D12); create
`tests/test_cp3_context_evidence.py`. **Behaviour:** Design 1-8. Thread `context_evidence` through
`validate_relative_value` (:702), `relative_value` (:1076), `_market` (:970), `_evidence_limitations`
(:1066), `_preference_issues` (:645), `_instrument_issues` (:600) and `context_block` (:1228).
`owners/cp3.py` needs no code (`compute`/`context` call the engine with the pack, :78-90); `ENTRY_VALIDATOR`
is the engine's `_validate_step` (:1178), so live and probe paths agree. The schema change (`Basis.context_rows`)
is in the sent schema: check CP-6's reading of CP-3 (T3.3 facts, `cp6_committee.py:575`) and the CP-3 render.

- [ ] **RED tests** (fail today; values read from `expected.json`):
  `test_observed_and_talk_rows`; `test_talk_only_issue_string`; `test_stale_31_days_limits_and_30_does_not`;
  `test_unmatched_and_empty_quote_are_named_gaps`; `test_deal_talk_one_range_row_no_midpoint`;
  `test_lone_bound_is_omitted_and_named`; `test_with_market_row_order_m_then_c`;
  `test_model_context_row_refused`; `test_basis_quoting_context_refused`; `test_unknown_context_row_refused`;
  `test_unreadable_and_bad_bytes_are_issues` (on a plain `prepare` pack); `test_unciteable_quote_is_a_gap`;
  `test_minified_context_cites_one_line`; hypothesis `test_offsets_agree_with_json_loads`;
  `test_context_block_lists_rows_and_caps_and_note` (Design 8, including the context-only note);
  `test_reader_parity_with_context_module` (engine fields equal `load_context` over `cases/context/*.json`
  and this case; pins the 30-day constant).
- [ ] **Guards** (pass today, kept green; not RED): `test_no_context_source_is_unchanged` (the R3 positive
  submission's `content_hash` and head equal the values at HEAD, so the omitted empty fields hold; head equal
  except `pack_sha256` when a context source is added with no rows),
  `test_third_party_basis_quotes_unchanged`.
- [ ] Run `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest
  tests/test_cp3_context_evidence.py tests/test_method_cp3.py tests/test_connect_cp3.py -q`, plus mutation
  testing on the changed functions. Commit `feat: CP-3 builds market evidence from the context quotes (B6)`;
  the controller writes the D12 entry (commit hash, review path).

## Task 2 (SENSITIVE: figures; `mx-adversary`): CP-3D context observations

**Files:** modify `src/deploy_workflow/owners/cp3d.py`; create `src/deploy_workflow/context_cites.py`, `tests/test_cp3d_context.py`, `tests/test_context_cites.py` (incl. the parity test with `_value_offsets`). **Behaviour:**
Design 9. Context bytes come only from the frozen pack.

- [ ] **RED tests:** `test_offered_observations_equal_oracle`; `test_context_row_expands_and_composes` (talk
  period reads `Commentary published 2026-01-10`); `test_filled_context_row_refused`;
  `test_unknown_context_row_refused`; `test_mixed_facilities_refused`; `test_context_not_third_party_ok_only_
  when_listed`; `test_unreadable_context_is_an_issue_not_an_exception`; `test_stale_limitation_has_run_as_of`;
  `test_single_dealer_text_for_context`; `test_context_observations_data` (the pure function above).
- [ ] **Guards:** `test_other_sources_keep_third_party_rule` (existing refusals [0..18] of
  `cases/cp3d-owner/expected.json`), `test_no_context_packs_unchanged` (also pins one frozen CP-3D submission's hash as at HEAD). Known fail-safe: in a minified file where bid equals ask, the anchored quote holds the number twice and CP-3D refuses the observation it offered (stated in the oracle, not a defect).
- [ ] Run `... pytest tests/test_cp3d_context.py tests/test_method_cp3d.py tests/test_connect_cp3d.py -q`
  (journaled `test_owner_cp3d.py` stays deferred). Commit `feat: CP-3D offers the context quotes as
  Python-built observations`.

## Task 3: Docs (mechanical; `mx-scaffold`, `mx-feature` review)

Modify `docs/CONTEXT-FILE-PROPOSAL.md` (:124), `docs/templates/context-form.html` (:1086 planned text
`quotes replacing rv_quotes` -> `quotes as CP-3 and CP-3D market evidence`), `docs/RUN-GUIDE.md`
("Start from the context form": CP-3/CP-3D read quotes and deal talk; 30-day stale limit; an unknown
facility id is a gap) and the parent plan's row 3. `src/deploy_vii/inputs/rv_quotes.py` and its manifest
rows stay (Q5 of the questions file). The form drift tests (parent Task 2) must pass.
- [ ] Edit; run the form/doc tests; commit `docs: context quotes are CP-3 market evidence`.

## Task 4: O6 follow-through (after O6 is built; separate writer for text and rule lists, `mx-precise` review)

**Files:** O6's `prompts/compose.py`, `prompts/fence.py`, `prompts/texts/relative_value.md` and
`market_implied.md`, `prompts/rule_lists/relative_value.json` and `market_implied.json`, their tests; and
`src/deploy_vii/live/prompts.py` (SENSITIVE: `src/deploy_vii` diff; `mx-adversary`).
- **`live/prompts.py` (B17 item 3):** reword `CP3_EVIDENCE_RULE` (wording only; read the text at :582-587 with
  `git show HEAD:`): a `basis` refers to Python's context rows by id (`basis.context_rows`) and never copies
  their figures; `basis.quotes` still repeats a `market_evidence` row's quote for `third_party` rows only; no
  other contract text changes. D12 `post_import_patches` record in `docs/reuse/manifest.json` (prompts.py is an
  imported file: normal shape, `project_commit` filled by the controller after the commit); re-pin the O6
  prompt-set hash (`STEP_CONTRACTS` pins) in the same change.
- The composer embeds Python's evidence rows (`context_market_evidence`; CP-3D's `context_observations_data`) as one
  fenced `data_block("CONTEXT", "context-evidence", ...)` for those two steps, with the step rule "rows from
  the context are Python's; refer to them by row id; never copy their figures".
- O6's M6 sentinel test exempts exactly that block: sentinels may appear inside it and nowhere else.
- O6 rule O3 stays (the model never cites `context`); a test asserts the rule text still forbids a `context`
  quote.
- The rule lists gain this oracle's refusal ids (Task 0) through the O6 rule-list process.
- [ ] RED: composed `relative_value` prompt names row-id references (`basis.context_rows`) and no longer says
  basis quotes repeat a `market_evidence` row for every basis; contains the block and the rule; the M6 test passes with only the
  block exempt; the rule lists cover every new refusal id. Run O6's `tests/prompts` suite.

## Done-when as tests

| Done-when | Test |
|---|---|
| CP-3 on a secondary context with Python-read quotes | `test_observed_and_talk_rows`, `test_minified_context_cites_one_line` |
| Talk-only caps confidence | `test_talk_only_issue_string`, `test_deal_talk_one_range_row_no_midpoint` |
| Context dates; quote as-of vs `Run.as_of` | As-of cells; `context.py:516`; `bad-bytes` test |
| Staleness limit; facility binding | `test_stale_31_days...`, `test_unmatched_and_empty_quote_are_named_gaps` |
| Model never writes or copies a context figure | `test_model_context_row_refused`, `test_basis_quoting_context_refused`, `test_filled_context_row_refused` |
| CP-3D market evidence from the context | Task 2 tests |
| Packs without context unchanged | the Guards; all frozen cases |
| `rv_quotes` retired from docs | Task 3 |

## Ruled decisions (former open questions Q1-Q5; ruled as recommended, `work/context-plan/reviews/phase-3-plan-review.md`)

1. Ruled: deal talk feeds CP-3 only; CP-3D offers `quotes` only (Design 9; Task 2).
2. Ruled: all observations of a CP-3D submission share one context `facility_id`; the instrument name is not matched to it; CP-1 is not added as a CP-3D input (Design 9; Task 2 `test_mixed_facilities_refused`).
3. Ruled: object-anchored citations (Design 3); a residual key collision with different content drops the later row into a gap (Task 1).
4. Ruled: a quote with every figure empty yields no row and the gap `context quote for facility <id> carries no figure; not used` (Design 5; Task 1 `test_unmatched_and_empty_quote_are_named_gaps`).
5. Ruled: prompt text is O6's; Phase 3 adds Task 4 (O6 follow-through) and edits the `relative_value` contract in `live/prompts.py` (B17 item 3).
6. Ruled (M2): no model copies a context figure; it refers to Python rows by id (Design 4, 9).


## Not verified (to carry into each report)

Journaled (store) CP-3/CP-3D runs on the new case (wait for O1 and Stage 5; engine tests only); live model
behaviour with the by-id rows and the reworded `live/prompts.py` contract (paused);
CP-3D tool-use read of the `context` page (`unread_citation_issues`) in a real run; Task 4 until O6 is built;
the exact CP-3D CONTEXT/view location; oracle values are unreviewed drafts until Task 0.
