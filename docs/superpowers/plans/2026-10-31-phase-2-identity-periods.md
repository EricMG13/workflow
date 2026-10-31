# Phase 2: Identity and Periods (CP-0, CP-1, CP-1A, CP-1B, CP-L10) Implementation Plan

**Status:** draft for the Phase 2 oracle preparer and build; no `src/deploy_vii` change (Decision 1).
Parent plan: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` (Phase 2 row :323-324, Phase 1
Task 4 :263-292). Rulings: `work/context-plan/reviews/phases-2-8-questions.md` "Phase 2" items 1-7 and
"All phases"; `docs/rulings/2026-10-31-context-plan.md` B2, B3, B5. Phase 1 is built (`context.py`
`context_facts` :733, `RunContext`).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkboxes.

**Goal:** a pack that holds a `context` source shows the user's borrower, aliases, sector and sponsor
beside the issuer gate and the cited CP-1A rows, flags a borrower-name mismatch as a gap, and drives CP-1B
and CP-L10 from the context's periods; a pack without one behaves exactly as today.

**Architecture:** four small Python units, all in `src/deploy_workflow`: `context_periods.py` (context
period string to a CP-1 T4.14 period, pure), `identity_check.py` (context names vs CP-1 T4.2 rows, pure),
`owner_rendering.py` (a render-side "Run context" section, no `src/deploy_vii` change), and consumer edits
in `owners/cp1b.py` (to be created by Part B O1 Task 3) and `owners/cpl10.py`. The reader and form change
for rulings 2 and 3.

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a refusal
  names its field path or code); no network call; exact `Decimal`; `""` is "not supplied", never zero.
- **No `src/deploy_vii` edit.** B6-B9 do not cover Phase 2. If a task seems to need one, stop and add it to
  the hand-off note for the user; do not edit. (So no D12 `post_import_patches` record is due in this phase; the manifest
  stays untouched.)
- A pack without a `context` source (`context_facts(pack) is None`, parent plan :280) or with empty
  `current_period`/`prior_period` behaves byte-identically: every frozen case, pin and
  `cases/earnings/*`, `cases/cpl10-owner/*` oracle stays green and unchanged.
- Context figures are labelled "user-supplied" (Q-X ruling: `source` class citing the context line span plus a
  limitation); the context never overrides an identity or a CP-1 figure (a mismatch is a gap).
- Every report ends with `Not verified:` and lists table/row/field changes (R7).
- Test command: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
  Gates per task: `ruff check`, `ruff format --check`, `mypy` on changed files, exit 0.
- Part B dependency: Task 4 needs Part B O1 Task 3 (`docs/superpowers/plans/2026-10-31-part-b-o1.md`
  :212-283: `owners/cp1b.py`, `EarningsDeltaOwnerReview`, `_CORES["CP-1B"]`) built. It is not built at this
  plan's base. This plan codes against that interface as specified there; Task 4 starts only when O1 Task 3
  is merged into `claude/context-plan-build`, and re-reads the built `cp1b.py` first.

## Shared files with Part B (build in sequence)

| File | Phase 2 task | Part B |
|---|---|---|
| `src/deploy_workflow/owners/cp1b.py` | 4 (adds context pair) | O1 Task 3 creates it |
| `src/deploy_workflow/owner_workflow.py` (uncommitted edit by another session at plan time) | 4 (view hook only if O1's `view` signature needs it) | O1 Tasks 1-3, O3, O6, O7 |
| `src/deploy_workflow/host.py` `_submission_schema` | none | O1 Task 3 |
| `src/deploy_workflow/owner_rendering.py` | 5 | none found in O1/O6/O7 Files lines |
| `src/deploy_workflow/context.py`, `docs/templates/context-form.html` | 1 | later phases 3, 6 (parent order 2 -> 3 -> 6) |
| `src/deploy_workflow/owners/cpl10.py` | 3 | Phase 8 later |

## Task 0: Oracle (separate preparer; independent `mx-precise` review; frozen and pinned before Task 1)

The builder of Tasks 1-5 prepares and reviews none of this (AGENTS.md "Module builds"; ruling B2).

**New case** `cases/context-identity-periods/` (not under `cases/context/`, whose files are plain form
downloads, `cases/context/README.md`). Files: `README.md`, `manifest.json` (source hashes, run settings),
`contexts/*.json` (below), `expected.json`. Pack sources: the byte-identical identity and financial sources
`cases/earnings/expected.json` is frozen on (`source_manifest`, `source_manifest_sha256`), plus each
context file as source id `context`. No CZR context (ruling 7: `issuer_id` "CZR" fails the slug rule,
`context.py:461`).

**Two packs.** Pack E = the byte-identical earnings sources above (issuer `Northbridge Synthetic Group`,
`issuer_id` `northbridge-synthetic`, `cases/earnings/manifest.json`; its identity source states no borrower
and its CP-1 fixture has one entity, roles `["issuer"]`, `tests/test_financial_workflow.py:227`). Pack B =
the `cases/snapshot` pack (its identity, financial and `business` sources, as `tests/s1a_runs.py` `make_pack`
assembles them; CP-1A needs `business`, :28, :107), except that its identity source is replaced by a preparer-written version that adds a borrower line (`Northbridge Holdings LLC` is the borrower) in place of the financial manifest's "No borrower ... is established by this source set" sentence (a second source would contradict that page); the preparer re-cuts every snapshot submission citation of `identity` (27) against the new bytes and records the new sha256. The snapshot `business` source says it "identifies no financial sponsor": a context sponsor on pack B is shown as user-supplied with no gap (Task 0 notes it). T4.2
roles come from the CP-1 review's `entities`, not source text, so pack B's CP-1 review adds an entity
`Northbridge Holdings LLC`, role `borrower`, scope-mapped. Contexts use the issuer name/id of their pack and `as_of`
of that pack's run (read from the manifest, not invented).

**Context inputs** (all `schema: context/1`, `case_kind: synthetic`, `reporting_currency: USD`):
Pack E contexts: `run_type: earnings`, pathway `earnings_update`. Pack B contexts: `run_type: research`,
pathway `credit_snapshot`, the pack's `Run` is set explicitly after `preparation_request`
(the context's `run` takes no `requested_modules`, `context.py:65-72`; the request uses the preset only), with
`requested_modules` = the modules of the `s1a-credit-snapshot` delivery scope (`owner_rendering.py:105-364`),
CP-1A included (`earnings_update` has no CP-1A, `contracts.py:52`,
and no delivery scope, `owner_rendering.py:572-581`).

| id | `current_period` / `prior_period` | `identity` | Purpose |
|---|---|---|---|
| ctx-match (E) | `q4-2025` / `q3-2025` | borrower `Northbridge Holdings LLC`; 2 aliases; sector `Business services`, sponsor `Fictional Partners` | CP-1B pair; identity `not_supplied` (pack E has no borrower row) |
| ctx-b-match (B) | `""` / `""` | borrower `Northbridge Holdings LLC`, same aliases, sector, sponsor | match, render rows |
| ctx-b-punct (B) | `""` / `""` | borrower `Northbridge Holdings, L.L.C.` | casefold and punctuation folding: no gap |
| ctx-b-mismatch (B) | `""` / `""` | borrower `Southbridge Holdings LLC` | gap |
| ctx-fy | `fy-2025` / `fy-2024` | as ctx-match | CP-1B `comparative_not_supplied` |
| ctx-h | `h2-2025` / `h1-2025`, run_type earnings | as ctx-match | reader refusal (ruling 2) |
| ctx-mixed | `q4-2025` / `fy-2024` | as ctx-match | reader refusal (ruling 2) |
| ctx-q3 | `q3-2025` / `q2-2025` | as ctx-match | CP-L10 unbound operand |
| ctx-q2031 | `q4-2031` / `q3-2031`, earnings | as ctx-match | unresolved current period (Task 4) |
| ctx-l10 (E-sources) | `q4-2025` / `q3-2025`, pathway `credit_snapshot`; the pack's `Run` is set explicitly with `requested_modules ["CP-L10"]` | as ctx-match | CP-L10 runs under this pathway (`cases/cpl10-owner/manifest.json` run); `context_facts` refuses a pathway differing from the run (`context.py:761`), so ctx-q3/ctx-fy for CP-L10 are also `credit_snapshot` variants; every pack with a `context` source (E and B) needs a `context` assessment in its CP-0 review (authority `unknown`, D2) |
| ctx-comma | borrower `Northbridge Holdings, LLC`; aliases `["Northbridge, Inc.", "NBG"]` | | form round trip (ruling 3) |
| ctx-research | run_type `research`, periods `""` | as ctx-match | periods absent: today's behaviour |

**Expected values** (derived from the rulings and the already-frozen oracles, never from code under test):
- Reader: `ctx-h` -> `ContextRefused` with a problem on `run.current_period`; `ctx-mixed` -> a problem on
  `run.prior_period`; a research context with h-periods still loads (the rule is earnings runs only).
  The preparer states the exact problem texts here and the builder copies them.
- CP-1B (read from `cases/earnings/expected.json`): `ctx-match` -> prior `q3-2025`, current `q4-2025`, the
  `positive` points (figures and statuses) of case `E-QOQ-FLAT`; limits are NOT compared (the owner path
  stamps its own limits via O1's composer split); `ctx-fy` -> the `gap` block of `E-NO-YOY`
  (`reason`, all prior and delta values unavailable, statuses as listed). A submission whose pair differs
  from the context pair (for example `q2-2025 -> q3-2025`) -> issue code `context_period_mismatch`.
- Identity check: `ctx-match` on pack E -> `not_supplied` (no borrower row), no gap; `ctx-b-match` and
  `ctx-b-punct` -> outcome `match`, no gap; `ctx-b-mismatch` -> exactly one gap,
  code `borrower_name_mismatch`, naming both strings; the CP-0 `issuer_confirmed` gate and every CP-1 table
  are unchanged. A context with `borrower_name` `""` -> outcome `not_supplied`, no gap.
- Render (pack B, `credit_snapshot` delivery): for `ctx-b-match` the page holds one section `Run context` listing borrower, aliases, sector,
  sponsor, each marked "user-supplied" with the context source id and the line of its key; for
  `ctx-research` with empty optional fields the rows are omitted; with no context source the page bytes
  equal today's.
- CP-L10: `ctx-match` -> the four quarters of `cases/cpl10-owner/expected.json` (`Q1 25` ... `Q4 25`,
  labels with the T4.14 dates, e.g. `Q4 25 (2025-10-01 to 2025-12-31)`), all expected rows unchanged;
  `ctx-q3` -> refusal text frozen as `unbound CP-1 operand: q4-2024 (no CP-1 T4.14 period)` (the pack holds
  no 2024 quarter, so no dates exist to build a label); the preparer derives every other expected effect of
  the `ctx-l10` runs (explicit `Run` set after `preparation_request`, CP-0 review with the `context` assessment) from the rulings; `ctx-fy` -> CP-L10 offers no quarter list and refuses with code
  `context_period_not_quarter`.
- Form (ctx-comma): the reader returns `["Northbridge, Inc.", "NBG"]` unchanged; the form's list parser on
  the text `Northbridge, Inc.\nNBG` yields two items.

**Existing pins/oracles changing:** none. New pins: the new case files go into `cases/PINS.json` via
`cases/pins.py` in one re-pin commit after the review; that commit first extends `PATTERNS`
(`cases/pins.py:20-26`), which match nothing under `cases/context-identity-periods/`, with
`cases/context-identity-periods/*.json`, `.../contexts/*.json` and the pack-B sources. The preparer runs the product's table, claim and
render validators and a scratch double rebuild and reports their exit codes (AGENTS.md :58-91).

- [ ] Preparer writes the case and questions answers; [ ] `mx-precise` (not the preparer, not the builder)
  reviews; [ ] controller freezes and pins; ids recorded in the ledger.

## Task 1: Reader and form refuse h-periods and mixed kinds; one name per line (rulings 2, 3)

**Files:** modify `src/deploy_workflow/context.py` (`run_section` :440-454, `PERIOD` :36),
`docs/templates/context-form.html` (period checks in `build()` :728-731, the earlier-than rule at :730-731, help text :277-278; `fld` list parsing :680-690; list
rejoin :1265-1266; the Aliases and Guarantors inputs :256-260), `tests/product/test_context.py`
(guard at :573, `test_form_output_loads` :568); create fixtures from Task 0.

**Behaviour.** In `run_section`, when `run.run_type == "earnings"` and a period is non-empty: an `h1`/`h2`
period is a problem `run.<name>: earnings runs compare quarters or fiscal years only.`; when both are
non-empty and their kinds differ (`q` vs `fy`), a problem on `run.prior_period`: `must be the same kind as
the current period.` (texts as Task 0 fixes). Non-earnings runs unchanged. The form's `build()` mirrors both
rules with the same texts. In the form, `aliases` and `guarantors` become `<textarea>` (one name per line,
help text changed from "Comma-separated"); a new `fld` type `t:'lines'` (used by aliases and guarantors only) splits on `/\r?\n/`; `t:'list'` stays comma-split because the assumption fields use it (form :785); the load code
(:1265-1266) rejoins with `"\n"`. Assumption lists (:785, :1300) are untouched. The
reader needs no change for lists (it takes arrays).

**RED tests** (`tests/product/test_context.py`):
```python
def test_earnings_h_period_refused():     # ctx-h bytes -> problems contain "run.current_period"
def test_earnings_mixed_kinds_refused():  # ctx-mixed -> problem on "run.prior_period"
def test_research_h_period_still_loads(): # research run with h2-2025 / h1-2025 loads
def test_form_list_fields_one_per_line(): # html has textarea ids s2-aliases, s2-guarantors;
                                          # fld has a 'lines' branch with split(/\r?\n/); assumptions keep t:'list'
def test_form_rejoin_uses_newline():      # lines for aliases/guarantors setV(...join('\n'))
def test_form_mirrors_period_rules():     # html contains the two message strings
def test_comma_name_round_trips():        # ctx-comma loads; names unchanged; {"schema": SCHEMA, **model_dump} equals file (test_context.py:569)
```
`test_form_regexes_match_reader` (:573) stays and must pass unchanged (the regex literals do not move).
Run: `pytest tests/product/test_context.py tests/product/test_context_pack.py tests/product/test_context_prepare.py tests/product/test_context_readiness.py -q`.
**Commit:** `feat(context): earnings runs take quarter or fy pairs; one name per line in the form (Phase 2)`.

## Task 2: Period resolution and identity check (pure units)

**Files:** create `src/deploy_workflow/context_periods.py`, `src/deploy_workflow/identity_check.py`,
`tests/product/test_context_periods.py`, `tests/product/test_identity_check.py`.

**Interfaces.**
- `context_periods.resolve(period: str, periods: Sequence[FinancialPeriod]) -> FinancialPeriod | None`:
  `period` is `q3-2025`/`fy-2024` (`PERIOD`, context.py:36); match `period_type` (`QUARTER`/`FY`),
  `fiscal_quarter` and the four-digit year in `fiscal_year` as `earnings_workflow.py:1017-1044` does
  (`re.findall(r"\d{4}", fiscal_year) == [year]`); `None` when zero or several match (never first-match).
  `quarters_ending_at(period: str) -> tuple[str, ...]`: four quarter strings ending at a `q` period
  (`q4-2025` -> `q1-2025..q4-2025`; `q2-2026` -> `q3-2025, q4-2025, q1-2026, q2-2026`); `ValueError`
  code `context_period_not_quarter` for `fy`/`h`/`""`.
- `identity_check.compare(context: RunContext, entities: Sequence[tuple[str, tuple[str, ...]]]) ->
  IdentityCheck` where `entities` are the T4.2 `(Entity Name, Entity Role)` cells (`canonical_tables.py:46-50`, row
  cells :205-228); `Entity Role` is ONE string joined with `"; "` (`_join`, :97-98), so split it on `"; "`
  before testing for `borrower` (role literal `source_context.py:31`). `IdentityCheck(outcome: "match"|"mismatch"|"not_supplied", gaps:
  tuple[str, ...], context_borrower: str, found: tuple[str, ...])`. Fold = `casefold`, then drop every
  character that is not alphanumeric, then collapse (so `L.L.C.` equals `LLC`). Empty `borrower_name` ->
  `not_supplied`. Borrower found among folded T4.2 entities with role `borrower` -> `match`; entities exist
  but none match -> `mismatch` with the gap text `borrower_name_mismatch: context names "<x>", CP-1 locates
  "<y>"`; no `borrower` role row at all -> `mismatch`-free `not_supplied` with a note (cannot compare;
  the gap is CP-1's own). `found` is deduplicated (T4.2 has one row per entity scope, `canonical_tables.py:206`). Never raises on a mismatch, never alters identity.

**RED tests.** `resolve("q4-2025", [Q4 2025 period]) is that period`; two matching periods -> `None`;
`resolve("fy-2025", quarters-only) is None`; `quarters_ending_at("q4-2025") == ("q1-2025","q2-2025","q3-2025","q4-2025")`;
`quarters_ending_at("q2-2026")` spans the year boundary; `("fy-2025")` raises `context_period_not_quarter`.
`compare`: ctx-b-match -> `match`; pack E entities (roles `["issuer"]`) -> `not_supplied`; two scope rows of one entity -> `found` has it once; `Northbridge Holdings, L.L.C.` vs `Northbridge Holdings LLC` -> `match`;
`Southbridge Holdings LLC` -> `mismatch` with exactly one gap and `found == ("Northbridge Holdings LLC",)`;
`""` -> `not_supplied`. Hypothesis: `compare` is invariant under case and punctuation of the context name.
Run: the two new test files. **Commit:** `feat: context period resolution and borrower-name check (Phase 2)`.

## Task 3: CP-L10 offers the context quarters (ruling 6) — sensitive (figures): `mx-adversary`

**Files:** modify `src/deploy_workflow/owners/cpl10.py` (`QUARTERS` :102, `PERIODS` :124, `OPERAND_LABELS`
:154, `Upstream.__post_init__` :305-, `operand` :338, `cpl10_upstream` :1217, `context_block` :1241,
`_comparison_issues` :1011), `tests/test_owner_cpl10.py`, `tests/cpl10_runs.py`.

**Behaviour.** CP-L10 runs under `credit_snapshot` with `requested_modules ["CP-L10"]` (`cases/cpl10-owner/manifest.json`); tests build that explicit run with a context of the same pathway and a `context` assessment in the CP-0 review. Today the four 2025 quarters and the 28 `OPERAND_LABELS` are module constants. Make them
parameters of `Upstream` (`quarters: tuple[Quarter, ...]`), defaulting to the existing `QUARTERS` so the
no-context path is unchanged. `cpl10_upstream` reads `context_facts(store.pack())`; when it is not `None`
and `current_period` is non-empty, it builds the four quarters with `quarters_ending_at(current_period)`;
each `Quarter.column`/`period`/`words` comes from the T4.14 period found with `resolve` (dates from that
period's start and end, e.g. `Q4 25 (2025-10-01 to 2025-12-31)`; `words` "the fourth quarter of 2025").
`bind_operands` then binds the labels for these quarters; an absent quarter keeps the existing
`unbound CP-1 operand: <label>` refusal (no fabrication); a quarter with no T4.14 period refuses `unbound CP-1 operand: <period> (no CP-1 T4.14 period)`. A non-quarter `current_period` -> step validation
issue `CP-L10: context_period_not_quarter`. `prior_period` is not used by CP-L10. `PERIODS`/index logic in
`_comparison_issues`, `pair_screens` (:486-) and `view_topics` (:466-) read `upstream.quarters`.

**RED tests** (`tests/test_owner_cpl10.py`): `test_no_context_quarters_unchanged` (existing expected.json,
byte-equal); `test_context_q4_2025_offers_oracle_quarters` (ctx-l10 view lists the four oracle periods and
column labels); `test_context_q3_2025_refuses_unbound_operand` (exact text `unbound CP-1 operand: q4-2024 (no CP-1 T4.14 period)`);
`test_context_fy_current_refuses` (`context_period_not_quarter`); `test_submission_period_outside_context_quarters_refused`
(`comparison.from_period: not an offered period`, :1011-1017).
Run: `pytest tests/test_owner_cpl10.py tests/test_connect_cpl10.py tests/test_method_cpl10.py tests/product -q`.
**Commit:** `feat(cpl10): offer the quarters ending at the context's current period (Phase 2)`.

## Task 4: CP-1B takes the context pair (ruling 4) — sensitive (figures): `mx-adversary`; needs O1 Task 3

**Files:** modify `src/deploy_workflow/owners/cp1b.py` (built by O1 Task 3), `tests/test_owner_cp1b.py`.
`earnings_workflow.py` and `_case_parameters` (:1657-1669) are NOT edited: the frozen three-run-id path
stays (ruling 4), and `EarningsWorkflow` is not used by the owner path (O1 plan :252-253).

**Behaviour.** In the O1 interface, `view` offers the CP-1 head's periods and `EarningsDeltaOwnerReview`
carries `prior_period_id`/`current_period_id`; the validator accepts "a pair `build_earnings_delta`
accepts" (O1 plan :246). Add: when `context_facts(store.pack())` is not `None` and both context periods
are non-empty, the view offers exactly the pair `resolve(prior_period)`, `resolve(current_period)` mapped to
T4.14 `period_id`s (ruling 5), and the validator refuses any other pair with issue `context_period_mismatch`
naming both pairs. An unresolved CURRENT period is the issue `context_period_unresolved: <period>`. An
unresolved PRIOR period is passed on as the context string, so `build_earnings_delta` yields the
`comparative_not_supplied` gap (an absent prior id is "no prior", `earnings.py:309`; this is the `E-NO-YOY`
case: the pack has no `fy-2024`).
With no context, or empty periods, behaviour is O1's. The pair then passes through `build_earnings_delta`
(`earnings.py:280`; same kind, same length, no overlap, :133, :313-318) whose `ValueError` codes remain the
backstop (`incompatible_periods`). The context never supplies a figure; Python still derives the 12
selections from the report. The CP-1B limitation gains "periods taken from the user-supplied run context".

**RED tests** (`tests/test_owner_cp1b.py`, CP-1 promotion tests gated behind `RUN_PROMOTION` as O1 does):
`test_context_pair_offered` (ctx-match: view offers `q3-2025`/`q4-2025` period ids only);
`test_context_pair_composes_flat_sequential` (ctx-match: head equals the `E-QOQ-FLAT` expected values);
`test_context_fy_pair_gap` (ctx-fy, `fy-2025` resolves, `fy-2024` does not: `comparative_not_supplied`, not a refusal);
`test_other_pair_refused` (`q2-2025 -> q3-2025` -> `context_period_mismatch`);
`test_unresolvable_current_period` (ctx-q2031 -> `context_period_unresolved: q4-2031`);
`test_no_context_unchanged` (O1's own period tests still pass).
Run: `pytest tests/test_owner_cp1b.py tests/test_cp1b_registration.py tests/test_earnings_workflow.py tests/test_earnings.py tests/test_owner_presets.py -q`.
**Commit:** `feat(owner): CP-1B reads its periods from the run context (Phase 2)`.

## Task 5: Render-side "Run context" section (CP-0, CP-1, CP-1A) — `mx-precise`; verifier path, no figures

**Files:** modify `src/deploy_workflow/owner_rendering.py` (`_capture` :678 inserts after the banner built at
:757; `_ANCHOR` :65), `tests/test_owner_rendering.py`; reads `identity_check` and `context_facts`.

**Behaviour.** In `_capture`, after `pack = store.pack(snapshot)`, call `context_facts(pack)` (a
`ContextRefused` becomes `_refusal("owner_render_context")`, not swallowed). When it is not `None`, build one
escaped `<section id="run-context" class="banner" ...>` placed after the delivery banner, with three groups,
each row marked "user-supplied (context source, line N)" where N is the line of that key in the frozen
`context` source spans:
(1) CP-0: borrower and aliases beside the issuer gate (issuer name, `identity_gate` from the CP-0 head);
(2) CP-1: the `identity_check.compare` result; a mismatch prints the gap text; entities from the shown CP-1
head's T4.2 rows (`shown_modules`); (3) CP-1A: sector and sponsor, printed beside the CP-1A cited rows
(which stay required and unchanged). Empty fields are omitted; no context -> no section, bytes identical.
The section is part of `report.html`, so `files` hashes (`:786-790`) and `_verify_directory`'s two
`_capture` comparisons (:921-935) cover it; no new receipt field. No `src/deploy_vii` file changes; the
`Block` payload proofs (`_sections`, :814) are unaffected.

**RED tests** (`tests/test_owner_rendering.py`): `test_run_context_section_for_matching_context`
(ctx-b-match, pack B `credit_snapshot` delivery: section lists borrower, 2 aliases, sector, sponsor, each "user-supplied");
`test_mismatch_prints_gap` (ctx-b-mismatch: gap text present, CP-0 gate word unchanged);
`test_no_context_page_bytes_unchanged` (existing delivery bytes equal);
`test_edited_section_fails_verify` (change a byte in `run-context` -> `owner_render_delivery`);
`test_html_escaped` (a name `<b>` is escaped).
Run: `pytest tests/test_owner_rendering.py tests/test_owner_acceptance.py -q` (the second only if present;
the implementer names the acceptance file that renders a delivery).
**Commit:** `feat(owner-render): show the run context beside CP-0, CP-1 and CP-1A (Phase 2)`.

## Task 6: Done-when test and run guide

**Files:** create `tests/product/test_phase2_done.py`; modify `docs/RUN-GUIDE.md`.

**Behaviour.** Docs: the form's list fields are one name per line; the borrower check records a gap, never
overrides; periods come from the context. Test (gated behind `RUN_PROMOTION` like O1's CP-1 tests, since
it needs a promoted CP-1): prepare a pack from ctx-match with `run_id` `ctx-phase2-1` (not one of the three
test ids) via `preparation_request` + `prepare`, drive the owner path to CP-1B, assert the head's points equal the
`E-QOQ-FLAT` expected points from the owner record. No delivery assertion: `earnings_update` has no delivery scope and `_capture` would refuse `owner_render_scope`; no new scope is added (ruling). The `Run context` page is proved in Task 5 on pack B.
Run: that file plus Tasks 1-5 paths. **Commit:** `test: Phase 2 done-when; run guide`.

## Done-when as tests

| Done-when (parent plan :323) | Test |
|---|---|
| An earnings run on a non-test `run_id` reaches CP-1B with the context's periods | `test_phase2_done::test_non_test_run_reaches_cp1b_with_context_periods`; `test_owner_cp1b::test_context_pair_composes_flat_sequential` |
| CP-0 shows borrower/aliases (pack B `credit_snapshot`) | `test_run_context_section_for_matching_context` |
| CP-1A shows sector and sponsor as user-supplied beside cited rows | same test (sector/sponsor rows) |
| Mismatch is a gap, never an override | `test_mismatch_prints_gap`, `identity_check` mismatch test |
| h-periods and mixed kinds refused | `test_earnings_h_period_refused`, `test_earnings_mixed_kinds_refused` |
| Names with commas survive a form round trip | `test_form_list_fields_one_per_line`, `test_comma_name_round_trips` |
| CP-L10 offers the context quarters | `test_context_q4_2025_offers_oracle_quarters` |
| No context: nothing changes | `test_no_context_*` in Tasks 3-5; frozen cases and pins green (`pytest tests -q` once before hand-off, ruling B3) |

## Decisions (ruled by the controller, `work/context-plan/reviews/phase-2-plan-review.md`; no open questions)

1. Ruled: CP-0 borrower/aliases and CP-1A sector/sponsor stay render-side in `owner_rendering.py`; no
   `src/deploy_vii` edit (`readiness.py:467-470`, `business_context.py` untouched).
2. Ruled: CP-L10 with a non-quarter (`fy`) current period refuses with `context_period_not_quarter`.
3. Ruled: CP-1B refuses a submitted pair that differs from the context pair (`context_period_mismatch`).
4. Ruled: the form's "Planned" markers are removed in the hand-off commit, only for fields Phase 2
   consumes: the `Planned` entry `'CP-1B period pair from this form'` (form :1079) and any tag on
   borrower, aliases, sector, sponsor. All other markers (:307, :357, :419, :492-515) stay.

Not verified: no code or test was run; the exact T4.10 column-label format for
non-2025 quarters, the browser behaviour of the textarea
change are unchecked until the builder reads them; Part B O1 Task 3's built `cp1b.py` interface is assumed
from its plan; the uncommitted `owner_workflow.py` edit was not read.
