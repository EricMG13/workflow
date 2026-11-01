# Phase 8: periods and currency from the context Implementation Plan

**Status:** draft 2026-10-31 on `claude/context-plan-build` (28ad7934); not started. Build **last** (after Phases 2, 4, 6, 7).
Phase row: `docs/superpowers/plans/2026-10-31-context-file-consumption.md:331`; questions and rulings:
`work/context-plan/reviews/phases-2-8-questions.md:112-121`; user ruling B9 (`docs/rulings/2026-10-31-context-plan.md`).
Line numbers below are `HEAD` (28ad7934) of the files; every one moves when an earlier phase lands, so each task opens
with the grep in its **Sweep** line, not with the line number.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** CP-1C, CP-1D, CP-2A, CP-2D, CP-2E, CP-2G, CP-2H, CP-3C, CP-4C, CP-L10 and CP-1B stop hard-coding
`LTM Q4 25 (2025-01-01 to 2025-12-31)`, FY2026-FY2028, `q4-2025` and USD. When the pack holds a `context` source, each
reads the base period and currency from it; a pack without one behaves byte-for-byte as today.

**Architecture:** one new module, `src/deploy_workflow/owners/period_basis.py`, holds a frozen `PeriodBasis` (every period
string the owners build today, as fields) and `period_basis(context, cp1_facts)`. `context is None` returns
`DEFAULT_BASIS`, whose fields are exactly today's literals. With a context it reads the context's `current_period`,
`reporting_currency` and the CP-1 T4.14 rows, and refuses (named `PeriodRefused`) on any disagreement. Each owner replaces
its module-level constants by `basis` fields; core functions take `basis` as a keyword defaulting to `DEFAULT_BASIS`.
No FX anywhere (ruling Q8.1): a module requires CP-1's currency to equal `reporting_currency`.

## Assumes (earlier phases, checked at the tip before Task 1)

| Phase | What Phase 8 relies on | If absent |
|---|---|---|
| 1 | `context_facts(pack) -> RunContext \| None` (plan :263-292), `ContextRefused` | stop |
| 2 | CP-1B owner core `owners/cp1b.py` (O1) reads periods from `context_facts`; the reader refuses h-periods and mixed kinds on earnings runs; CP-L10 offers the four fiscal quarters ending at `current_period` with T4.14 dates (`cpl10.py:102-124` replaced). Phase 8 then changes only CP-1B's and CP-L10's **currency**; if CP-L10 still holds 2025 quarters, Task 7 does Phase 2's job for them and says so | do CP-L10 periods in Task 7 |
| 4 | `cp2h.py` has `context_ratings` and its cells cite the context line; Task 5 leaves that code alone | rebase |
| 6 | pins in `cp2a/2d/2e/3c/3d/4c`; a pinned money value (`minimum_cash_m`) is labelled with the run currency, so Task 4 reads `basis.currency` for it | label stays "US$" in a pin text: fix in Task 4 |
| 7 | CP-1C EV tables and CP-4C's selected multiple exist; their period strings must come from `basis` too | Task 2/6 sweep catches any literal |

Shared files with those phases (questions file, "Shared files"): `owners/cp4c.py` (6, 7, 8), `owners/cp1c.py` (7, 8),
`owners/cp2h.py` (4, 8), `owners/cp2d.py`, `owners/cp3c.py` (6, 8), `owners/cpl10.py` (2, 8), `earnings_workflow.py` (2).
Part B overlap: O1 (`owner_workflow.py`, `owners/cp1b.py`) and O6 (prompt texts that quote period strings). This phase edits
neither `owner_workflow.py` nor `prompts/`; see Open question 3.

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a context the owner cannot map
  onto CP-1 is a named `PeriodRefused`, never a silent fall back to 2025); no network call; no key read.
- `DEFAULT_BASIS` is not a stub: it is the frozen-case behaviour, used only when `context_facts(pack)` is `None`. A pack that
  has a context never reaches it.
- Python owns every date and figure; the model never quotes a period or currency string it was not handed.
- `src/deploy_vii`: Task 6b (user ruling B17-9: `bindings/cp1b.py` and `report_view.py`, D12 records, `mx-adversary`, re-pins) and wording-only edits to `methods/*.md` that this phase makes stale (B9), each with a D12
  `post_import_patches` record in `docs/reuse/manifest.json` (`project_commit` = the commit where the file hashes to
  `sha256`; record shape at `manifest.json:1146-1154`) and an `mx-feature` review. No other `bindings/*.py` or
  `src/deploy_vii` change: no binding holds a period label (`git grep -nE "Q4 25|2025|LTM" HEAD -- src/deploy_vii/bindings`
  is empty for CP-1C, 1D, 2A, 2D, 2E, 2G, 2H, 3C, 4C, L10). The renderer's `_CURRENCY_LABEL = {"USD": "US$"}`
  (`report_view.py:974`) is not edited by this phase: another currency renders as its ISO code (`scale_label`, :1024-1031, "EUR m").
- A pack without a `context` source: every frozen `cases/*-owner` case, `PINS.json` entry and test stays green and unchanged.
  Pinned texts that contain `USD`/`US$`/`FY2025` are produced by formatting `DEFAULT_BASIS`, and a test asserts the output
  equals the old literal.
- Reports end `Not verified:` and list table, row and field changes (R7): this phase changes cell labels, `period`
  strings and `FactBinding` labels (T4.5, T4.6, T4.10 selection; T2H.*, T2R.*, T2E.* period columns; T1D basis line)
  **for context packs only**; no table id, row id or field name changes.
- Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`. Gates on changed
  files: `ruff check`, `ruff format --check`, `mypy`; the full suite once before hand-off (B3).

## Decisions taken from the rulings (do not reopen)

- **Q8.1 FX:** no downstream conversion. CP-1 normalises facility FX (`facility_fx.py:1`); owners require CP-1's currency
  to equal `run.reporting_currency`, else `PeriodRefused("reporting_currency EUR, but CP-1 reports USD")`. Replaces the
  USD-only gates `cp2d.py:70,300,452,1477,1548,1953`, `cp2a.py:891,1510-1514`, `cp1c.py:103-105`, `cp2g.py:358-363`.
- **Q8.2 Forecast years:** the three fiscal years after an `fy` or `q4` base, read from T4.14. Any other base
  (`q1`-`q3`, `h1`, `h2`) is a named refusal. `BASE_YEAR` (`cp2g.py:88`, `cp2h.py:93`) is `basis.base_year`.
- **Q8.3:** CP-2E (`cp2e.py:864-867`), CP-L10 (`cpl10.py:90-124`), CP-1B (`earnings.py:147-150`), CP-2A (`cp2a.py:891`) are in.
- **Q8.4:** three presets, so the Done-when needs at least three runs.
- **Ids stay.** Field ids that embed a year (`total_leverage_fy28`, `change_vs_fy25`, `cp2g.py:2049-2050`) are structural
  names of the frozen schema and keep their spelling; their *labels* and values follow `basis`. Recorded as Open question 1.

## Task 0: the oracle `cases/periods-currency-owner/`

Prepared by a **preparer** who builds none of Tasks 1-8, reviewed by an independent `mx-precise` (neither builds), frozen and
listed in `cases/PINS.json` (`python3 -I cases/pins.py`; the glob `cases/*-owner/*` picks it up, `cases/pins.py:12-21`)
before Task 1 starts. Layout as `cases/cp2g-owner/`: `manifest.json`, `submissions.json`, `expected.json`,
`builder/build.py` (stdlib only, never imports product code, `cases/cp2g-owner/builder/build.py:1-4`). The preparer runs the
product's table, claim and render validators and a scratch double rebuild (AGENTS.md :72-73) and reports exit codes.

**Construction rule (independent of code under test).** The shifted pack is the frozen `cases/financial/manifest.json`
pack with every calendar year +1 applied **once, simultaneously** to every dated source (a sequential replace would shift 2024 twice;
the only 2024 date is `2024-12-31`), so 2024->2025, 2025->2026, 2026->2027, `Published January 10, 2027`; amounts unchanged;
facility maturity `2029-12-31` -> `2030-12-31`, so every month-based interval is the same. Expected figures are therefore the
matching frozen oracle figures (`cases/cp1c-owner`, `cp1d-owner`, `cp2a-owner`, `cp2d-owner`, `cp2g-owner`, `cp3c-owner`,
`cp4c-owner` `expected.json`) read **by value from the pinned files**, with only labels, dates, years and currency mapped
by the table below. The preparer checks no day count crosses 29 February 2028 and says so. Day counts in the shifted
statements stay 365/90/91/92/92 (2026 is not a leap year).

| Quantity | Frozen (2025) | Shifted (2026) |
|---|---|---|
| LTM column | `LTM Q4 25 (2025-01-01 to 2025-12-31)` | `LTM Q4 26 (2026-01-01 to 2026-12-31)` |
| T4.5 / T4.6 / bs period | `LTM Q4 25 · 2025-01-01 to 2025-12-31` / `q4-2025 · 2025-10-01 to 2025-12-31` / `Q4 2025: 2025-12-31` | same with 2026 |
| forecast years | FY2026, FY2027, FY2028; "Not reached by FY2028" | FY2027, FY2028, FY2029; "Not reached by FY2029" |
| CP-1D basis line | `Basis: FY2025 (January 1-December 31, 2025)` | `Basis: FY2026 (January 1-December 31, 2026)` |
| CP-2E periods | `FY 2025: 2025-01-01 to 2025-12-31`, `Balance at 2025-12-31`, `Run as of 2026-01-10` | 2026; `Run as of 2027-01-10` |
| money unit token | `US$ m` | USD runs `US$ m`; EUR run `EUR m` |

**Inputs.** Pack sources `identity`, `financial` (shifted, one set in USD and one in EUR with `Currency: EUR; amounts in
millions` and the facility schedule in EUR), `peers` (shifted peer table, `Basis: ... Currency` clause in the run currency),
`bridge` (CP-1D, Basis line per table), `context`, and every other dated source the modules read: `business`
(`cases/snapshot`), `legal-covenants` (`cases/legal`) and the CP-2H `ratings` source, shifted by the same rule. The
builder recomputes each source `sha256` from the shifted bytes. Further frozen oracles that carry period strings and are
read by value: `cp2h-owner`, `cp2e-owner`, `cpl10-owner`, `cases/earnings`. The `context.json` per run (schema `context/1`, built with the form's
rules; fields not listed are defaults):

| Run | `pathway` / modules | `run.current_period` / `prior_period` | `reporting_currency` | `as_of` |
|---|---|---|---|---|
| R1 `rv-fy2026-usd` | `relative_value`: CP-1C, CP-2D, CP-3C | `fy-2026` / `fy-2025` | USD | 2027-01-10 |
| R2 `dist-q4-2026-eur` | `distressed_restructuring`: CP-2A, CP-2G, CP-2H, CP-4C; plus CP-2E and CP-L10 added through `Run.model_copy(update={"requested_modules": ...})` (neither is in any preset, `context.py:711-718`, `contracts.py:48-71`) | `q4-2026` / `q3-2026` | EUR (statements and facility schedule in EUR) | 2027-01-10 |
| R3 `earn-q4-2026-eur` | `earnings_update`: CP-1B, CP-1D | `q4-2026` / `q3-2026` | EUR (statements, facility schedule and bridge in EUR) | 2027-01-10 |
| R4 `mismatch-eur-on-usd` | R1's pack (USD statements) with `reporting_currency` EUR | `fy-2026` / `fy-2025` | EUR | 2027-01-10 |
| R5 `base-h2` | R2's pack (USD variant) with `current_period` `h2-2026` | `h2-2026` / `h1-2026` | USD | 2027-01-10 |
| R5b `base-q3` | same pack, CP-2A, CP-L10, CP-1B | `q3-2026` / `q2-2026` | USD | 2027-01-10 |
| R6 `rv-fy2026-eur` | `relative_value`: CP-1C, CP-2D, CP-3C | `fy-2026` / `fy-2025` | EUR | 2027-01-10 |

**Expected values** (statuses, limitations, gaps, refusals; figures by the construction rule):
- R1: CP-1C issuer metrics equal the frozen CP-1C issuer cells, period `Mixed: issuer LTM Q4 26, each peer's own twelve
  months`, all four T4.10 facts selected from the `LTM Q4 26 (...)` column; CP-2D and CP-3C settle with T4.5/T4.6/T4.10 facts
  bound to the 2026 periods, `SCHEDULE_PERIOD` `q4-2026`, same amounts as the frozen CP-2D/CP-3C cases.
- R2 (EUR; money tokens `EUR m`, no `US$` in any rendered cell or claim): CP-2A offers the same bases as frozen with 2026 labels; CP-2G forecast columns FY2027-FY2029 with the frozen
  values; CP-2H first-reached text "Not reached by FY2029"; CP-4C claims column `Q4 2026-12-31`, balance-date limitation
  "31 December 2026"; CP-2E periods per the table (its basis comes from its own `FY 2026` header and `run.current_period`, Task 7); CP-L10 quarters Q1-Q4 26 (Phase 2 owns the offering; Phase 8 checks the
  currency token only).
- R3 (EUR; user ruling B17-9): CP-1B settles with the dimension check passing on `EUR`/`MILLIONS`; every amount fact
  carries `currency="EUR"`; the T1B.1/T1B.2 row labels read `Revenue (EUR m)`, `Reported EBITDA (EUR m)`, `Adjusted EBITDA
  (EUR m)`, `Reported CFO (EUR m)`, `Signed capex (EUR m)`, `Levered FCF (EUR m)`, `Closing cash (EUR m)`, `Total debt (EUR
  m)`, `Net debt (EUR m)`, and the non-money labels are unchanged (labels per `bindings/cp1b.py:32-49`, nine money labels, with `US$ m` -> `EUR m`); the layout check
  accepts them. CP-1D settles in EUR: basis line parsed, claims show `EUR m`, no `US$`.
- R6: as R1's figures with `EUR m` tokens; no `US$` in CP-1C, CP-2D, CP-3C rendered output.
- R4: every one of CP-1C, CP-2D, CP-3C is `refused` at its entry validator with the issue
  `reporting_currency EUR, but CP-1 reports USD` (exact text frozen by the preparer from Task 1's `PeriodRefused` message
  contract below); no figure is produced.
- R5: CP-2G, CP-2H, CP-4C each refuse with `run.current_period h2-2026: forecast years need an fy or q4 base`; CP-2A keeps
  offering its bases (period-agnostic, `cp2a.py:160-173`). R5b (M3): a q3 base is not a refusal for the currency-only
  modules: CP-2A, CP-L10 and CP-1B (USD) settle; only the forecast/LTM-Q4 modules refuse on a non-fy/q4 base.
- **Existing pins:** none change. If the preparer finds a pin that must change, stop and report.
- **Prepare risk:** CP-1 on the shifted pack is promoted the way `tests/cp3_cp6_runs.py:10` does (11-26 minutes each). If the
  EUR pack cannot pass CP-1 (vii; not evidenced here), R3 and R2 are recorded as the CP-1 refusal and the user is told (Ruled 2).

Checkpoint: `python3 -I cases/pins.py --check` exits 0; reviewer's verdict file path in the ledger line.

## Task 1: `PeriodBasis` and `period_basis` (sensitive: figure selection, currency; `mx-adversary`)

**Files:** create `src/deploy_workflow/owners/period_basis.py`, `tests/test_period_basis.py`. Nothing else.

**Interface.**
```python
class PeriodRefused(ValueError): ...   # message names the context field path
@dataclass(frozen=True)
class PeriodBasis:
    currency: str; money_unit: str                       # "USD", "US$ m" | "EUR", "EUR m"
    base_year: int; years: tuple[int, int, int]
    ltm_start: date; ltm_end: date; q4_start: date
    ltm_tag: str            # "LTM Q4 25"
    ltm_column: str         # "LTM Q4 25 (2025-01-01 to 2025-12-31)"   cp1c.py:1523
    ltm_period: str         # "LTM Q4 25: 2025-01-01 to 2025-12-31"    cp1c.py:1524
    t45_period: str         # "LTM Q4 25 · 2025-01-01 to 2025-12-31"   cp2d.py:1854
    t46_period: str         # "q4-2025 · 2025-10-01 to 2025-12-31"     cp2d.py:1855
    schedule_period: str    # "q4-2025"                                cp2d.py:1903
    bs_period: str          # "Q4 2025: 2025-12-31"                    cp4c.py:1392
    bs_column: str          # "Q4 2025-12-31"                          cp4c.py:1391
    bridge_basis_line: str  # "Basis: FY2025 (January 1-December 31, 2025)"   cp1d.py:380
DEFAULT_BASIS: PeriodBasis      # exactly the literals above
def period_basis(context: RunContext | None, cp1_facts: Iterable[Fact]) -> PeriodBasis: ...   # fy/q4 bases only
def currency_basis(context: RunContext | None, cp1_facts: Iterable[Fact]) -> CurrencyBasis: ... # any base (M3)
```
`CurrencyBasis(currency, money_unit)`; `DEFAULT_CURRENCY` is USD / `US$ m`. CP-2A, CP-L10 and CP-1B call
`currency_basis`; CP-1C, CP-1D, CP-2D, CP-3C, CP-2G, CP-2H, CP-4C call `period_basis` (which includes the currency).
**Behaviour.** `context is None` -> `DEFAULT_BASIS`. `currency_basis` checks only that the CP-1 T4.14 `currency` equals `run.reporting_currency` (any base kind, blank
included). Otherwise `period_basis`: `current_period` must match `fy-YYYY` or `q4-YYYY`
(`PERIOD`, `context.py:36`); blank (allowed off earnings runs, `context.py:444-446`) or any other kind raises
`PeriodRefused("run.current_period <v>: forecast years need an fy or q4 base")`. From the CP-1 T4.14 rows (period rows are
read as `earnings.py:112-125` reads them: one row per `period_id`, fields `period_type`, `fiscal_year`, `fiscal_quarter`,
`start_date`, `end_date`, `currency`, matched on type/year/quarter as `earnings_workflow.py:1017-1044` does, not on the
submission-chosen id; forms at HEAD: `period_type` is `QUARTER` or `FY` (`earnings.py:127-133`); `fiscal_year` is text read
by `re.findall(r"\d{4}")` (`earnings_workflow.py:1027`), so `FY2026` and `2026` both work; `fiscal_quarter` is an `int` on
the model period (`financial_periods.py:54`), a `not_applicable` fact on an FY row (`earnings.py:154-155`) and read as the
digit `[1-4]` in a quarter row's text, never compared as a string): exactly one `FY` row of that fiscal year gives the LTM window and `base_year`; exactly one `QUARTER`
row with quarter 4 whose end equals the FY end gives `q4_start`/`bs`; zero or several raise `PeriodRefused`. The row's
`currency` must equal `run.reporting_currency`. `ltm_tag` is `LTM Q4 {yy}` (the vii label rule, `model/periods.py:356-357`).
`bridge_basis_line` is `Basis: FY{year} ({Month d}-{Month d}, {year})` from the window. `money_unit` is `US$ m` for USD
(`report_view.py:974,1024`) else `{ccy} m`.

**M5.** The Q4 row is matched by its T4.14 dates and the context year; `t46_period`, `schedule_period` and the `_bind46`
suffix are then built from the matched row's own CP-1 `period_id` (`schedule_period` and the suffix are the bare id;
`t46_period` is the T4.6 period form `"{period_id} · {start} to {end}"`, `statement_view.py:90`; T4.6 facts carry the id as label and period,
`statement_view.py:80,90`, and `cp2d.py:2015-2020` keys `ends` by it), never a string rebuilt from the year.
- [ ] **RED tests** (`tests/test_period_basis.py`, synthetic `Fact` tuples, no pack):
  - `test_default_basis_is_todays_literals`: every field of `DEFAULT_BASIS` equals the literal in the comment above.
  - `test_none_context_gives_default`.
  - `test_fy2026_calendar`: FY row 2026-01-01..2026-12-31, Q4 row 2026-10-01..2026-12-31, USD -> `ltm_column ==
    "LTM Q4 26 (2026-01-01 to 2026-12-31)"`, `years == (2027, 2028, 2029)`, `bs_period == "Q4 2026: 2026-12-31"`,
    `schedule_period == "q4-2026"`, `bridge_basis_line == "Basis: FY2026 (January 1-December 31, 2026)"`.
  - `test_q4_and_fy_base_give_equal_basis`.
  - `test_non_calendar_year`: FY 2025-07-01..2026-06-30, Q4 2026-04-01..2026-06-30 -> `ltm_column ==
    "LTM Q4 26 (2025-07-01 to 2026-06-30)"`, `t46_period == "q4-2026 · 2026-04-01 to 2026-06-30"`,
    `bridge_basis_line == "Basis: FY2026 (July 1, 2025-June 30, 2026)"`.
  - `test_other_base_kinds_refused[q2-2026, h2-2026, ""]` -> `PeriodRefused` containing `run.current_period`.
  - `test_missing_or_duplicate_period_rows_refused` (no FY row; two FY rows; Q4 end != FY end).
  - `test_currency_mismatch_refused`: T4.14 `USD`, context `EUR` -> message `reporting_currency EUR, but CP-1 reports USD`.
  - `test_eur_unit_token`: `money_unit == "EUR m"`.
  - `test_period_id_from_matched_row` (M5): rows with `period_id` `Q4-FY26` and `FYX`, the `Q4-FY26` row matched by its dates -> `schedule_period == "Q4-FY26"` and `t46_period == "Q4-FY26 · 2026-10-01 to 2026-12-31"`; RED at HEAD (fixed `q4-2025`).
  - `test_currency_basis_any_base` (M3): `q3-2026`, `h2-2026` and blank give `currency_basis` without refusal; a currency
    mismatch still refuses.
- [ ] **Gate.** `pytest tests/test_period_basis.py -q`; ruff/format/mypy on both files.
- [ ] **Commit:** `feat(periods): one PeriodBasis for the owners' period and currency strings (P8 T1)`.

## Task 2: CP-1C (`mx-adversary`)

**Files:** modify `src/deploy_workflow/owners/cp1c.py`; create `tests/test_periods_currency_cp1c.py`.
**Sweep:** `git grep -nE "Q4 25|2025|USD" -- src/deploy_workflow/owners/cp1c.py` must leave only `DEFAULT_BASIS` uses.
**Behaviour.** `MIXED_PERIOD` (:90) becomes `f"Mixed: issuer {basis.ltm_tag}, each peer's own twelve months"`;
`_CP1_COLUMN`/`_CP1_PERIOD` (:1523-1524) and `_cp1_metrics(cp1)` (:1580-1600) take `basis`; `SUPPORTED_BASIS` (:105) is keyed
`(basis.currency, "amounts in millions")` so a peers page whose Basis clause states another currency is "outside the table
rule" exactly as an unsupported clause is today (comment :101-102). `_inputs(pack, submission, upstream)` (:1600)
derives `basis = period_basis(context_facts(pack), upstream.cp1.facts)`; a `PeriodRefused` becomes the validator issue
`clipped(("Period basis: ", str(error)))` next to `_stale_issues` (:1615), never an exception out of `submit`. Phase 7's EV
tables, if present, use `basis` in the same way.
- [ ] **RED tests:** (a) `_cp1_metrics(cp1, DEFAULT_BASIS)` on the frozen CP-1 head equals today's result (reuse the
  `tests/test_owner_cp1c.py` fixture); (b) with a head whose T4.10 column is `LTM Q4 26 (2026-01-01 to 2026-12-31)` and a
  `fy-2026` USD context, the four metrics are found and the derived peer facts carry
  `Mixed: issuer LTM Q4 26, each peer's own twelve months`; (c) the same head with the 2025 `_cp1_metrics` call raises
  "0 facts, expected exactly one"; (d) a peers page `Basis: ... Currency: EUR; amounts in millions` under a USD context is
  not a table (`Peer table not found`), under an EUR context it is; (e) `PeriodRefused` -> validator issue text.
- [ ] **Run:** `pytest tests/test_periods_currency_cp1c.py tests/test_owner_cp1c.py tests/test_connect_cp1c.py -q`.
- [ ] **Commit:** `feat(cp1c): issuer period and currency from the run context (P8 T2)`.

## Task 3: CP-1D (`mx-adversary`)

**Files:** modify `src/deploy_workflow/owners/cp1d.py`; create `tests/test_periods_currency_cp1d.py`.
**Sweep:** `git grep -nE "Q4 25|FY2025|2025" -- src/deploy_workflow/owners/cp1d.py`.
**Behaviour.** `_BASIS_LINE` (:380) and `parse_bridge(pages)` (:~482-486) take `basis_line: str = DEFAULT_BASIS.bridge_basis_line`
(a bridge whose page:1 lacks the run's basis line is `Bridge table not found`, unchanged rule); `_CP1_COLUMN/_CP1_PERIOD`
(:1950-1951) and `_cp1_facts` (:2074) take `basis`; every `US$ m` token (:1597-1599 and each other `ref(..., 'US$ m')` / `{id|US$ m}` site; the ref form fails closed under EUR,
`prose.py:298`) takes `basis.money_unit`. Docstrings (:187, :484) say "the base column".
- [ ] **RED tests:** (a) frozen bridge parses with the default line (existing `tests/test_connect_cp1d.py` stays green);
  (b) a bridge with `Basis: FY2026 (January 1-December 31, 2026)` parses under `fy-2026`/`q4-2026` and returns `None` under the
  default line; (c) under EUR the supported-vs-management sentence reads `EUR m`, under USD `US$ m` (byte-equal to today);
  (d) `_cp1_facts` selects the 2026 column or raises "0 facts"; (e) under EUR no claim text contains `US$`.
- [ ] **Run:** `pytest tests/test_periods_currency_cp1d.py tests/test_connect_cp1d.py tests/test_owner_cp1d.py -q`.
- [ ] **Commit:** `feat(cp1d): bridge basis and CP-1 column from the run context (P8 T3)`.

## Task 4: CP-2D and CP-3C (`mx-adversary`)

**Files:** modify `owners/cp2d.py`, `owners/cp3c.py`; create `tests/test_periods_currency_cp2d_cp3c.py`.
**Sweep:** `git grep -nE "Q4 25|q4-2025|2025|USD|US\\$" -- src/deploy_workflow/owners/cp2d.py src/deploy_workflow/owners/cp3c.py`.
**Behaviour.** `FACT_BINDINGS` (cp2d :1871-1900, cp3c :2066-2072) become `fact_bindings(basis)` functions (`_bind45/_bind46/
_bind410`, :1859-1868, read `basis.t45_period/t46_period/ltm_period`); the module attribute `FACT_BINDINGS =
fact_bindings(DEFAULT_BASIS)` stays for the frozen path and tests that import it. `SCHEDULE_PERIOD` (cp2d :1903,
cp3c :2078) is `basis.schedule_period`. `CURRENCY = "USD"` (cp2d :70) is `basis.currency` in `_usd_millions` (:1953-1970),
`_usd_principal`/`_currency_gap` (:452), and the text constants `FX_REASON` (:300), the "every facility in USD" texts
(:1477, :1548) and cp3c `_FX_CAUSE` (:447): each is `str.format(ccy=...)` with the default producing today's string.
cp3c's docstring (:301) and the "LTM adjusted EBITDA" row labels (:1419-1512) say "LTM" generically and stay (the base is
always LTM). Every `US$ m` site becomes `basis.money_unit`: cp2d :826, 836, 1289, 1334, 1414, 1445, 1516-1529; cp3c :1324-1332,
1491-1504. A fact whose `currency != basis.currency` raises the existing `CP-2D: <name> is not in ... millions` message
with the run currency in it.
- [ ] **RED tests:** (a) `fact_bindings(DEFAULT_BASIS) == FACT_BINDINGS` for both modules (golden: the 25 cp2d keys at
  :1871-1900 keep order); (b) `fact_bindings(basis_2026)["cash_bs"] == FactBinding("T4.6", "q4-2026 · 2026-10-01 to
  2026-12-31", "Cash and cash equivalents · q4-2026")` and `["cash_closing"]` label `LTM Q4 26 (2026-01-01 to 2026-12-31) ·
  cash_closing`; (c) under a EUR basis a facility in USD gives the gap `Not calculable: facility f1 is in USD, not EUR; no
  FX conversion is applied`, under the default basis the old `... is in EUR, not USD ...` text byte-for-byte;
  (d) cp3c `FACT_BINDINGS` shares cp2d's rule (one function); (e) `_bind46` with a CP-1 `period_id` `Q4-FY26` binds the suffix
`Q4-FY26` and finds the T4.6 end date (M5); (f) one EUR RED per module: no `US$` in any cp2d or cp3c cell, claim or limitation.
- [ ] **Run:** `pytest tests/test_periods_currency_cp2d_cp3c.py tests/test_owner_cp2d.py tests/test_owner_cp3c.py tests/test_connect_cp2d.py tests/test_connect_cp3c.py -q`.
- [ ] **Commit:** `feat(cp2d,cp3c): CP-1 bindings and currency from the run context (P8 T4)`.

## Task 5: CP-2G and CP-2H (`mx-adversary`)

**Files:** modify `owners/cp2g.py`, `owners/cp2h.py`; create `tests/test_periods_currency_cp2g_cp2h.py`.
**Sweep:** `git grep -nE "LTM Q4 25|BASE_YEAR|FY2025|FY2026|FY2028|USD|YEARS" -- src/deploy_workflow/owners/cp2g.py src/deploy_workflow/owners/cp2h.py`.
**Behaviour.** `LTM_COLUMN`, `LTM_PERIOD`, `BASE_YEAR`, `YEARS` (cp2g :86-89, cp2h :91-94) are `basis` fields; the ~30 uses of
`LTM_PERIOD` as a default argument (cp2g :1075, :1109, :1134, :1564 and the `put(...)` calls :1616-1652) take `basis`
through the composer object. Text: `FY{BASE_YEAR} actual` (:1654, :1888) uses `basis.base_year`; "Not reached by FY2028"
(cp2h :464, cp2g :564) uses `basis.years[-1]`; the "minimum liquidity ... FY2025 actual" sentence (:1038) and
docstrings use `basis.base_year`; `_usd_millions`-style check (:358-363) uses `basis.currency`, money cells
`currency="USD" if amount_unit` (:1091) use `basis.currency`. Every `US$ m` site becomes `basis.money_unit` (cp2g :2325-2353 and the rest of the Sweep). Schema/field ids keep their spelling (Decision above). CP-2H
does not change `context_ratings` (Phase 4) nor its trigger parser. A CP-2G head built under one basis and read by CP-2H
under another is refused by the existing period equality (cp2g :798 `base_period != LTM_PERIOD` becomes
`!= basis.ltm_period`).
- [ ] **RED tests:** (a) default composer output equals the frozen cp2g/cp2h owner oracle on the existing fixtures
  (`tests/test_owner_cp2g.py`, `tests/test_owner_cp2h.py` unchanged and green); (b) with the 2026 basis the T2H.3 driver
  columns are FY2027, FY2028, FY2029 and `YEARS == (2027, 2028, 2029)`; (c) "Not reached by FY2029"; (d) a CP-2H built on a
  2025-basis CP-2G head under a 2026 context gives the existing stale-period issue; (e) h2 base -> `PeriodRefused` text in the
  entry validator issues of both modules; (f) EUR: no `US$` in any cp2g or cp2h cell or claim.
- [ ] **Run:** `pytest tests/test_periods_currency_cp2g_cp2h.py tests/test_owner_cp2g.py tests/test_owner_cp2h.py tests/test_connect_cp2g.py tests/test_connect_cp2h.py -q`.
- [ ] **Commit:** `feat(cp2g,cp2h): base year, forecast years and currency from the run context (P8 T5)`.

## Task 6: CP-4C (`mx-adversary`)

**Files:** modify `owners/cp4c.py`; create `tests/test_periods_currency_cp4c.py`.
**Sweep:** `git grep -nE "Q4 25|FY202|2025|USD|31 December" -- src/deploy_workflow/owners/cp4c.py`.
**Behaviour.** `ForecastYear = Literal["FY2026", "FY2027", "FY2028"]` (:108) becomes `str`, validated against
`basis.year_labels`; `LTM_COLUMN/LTM_PERIOD/YEARS` (:415-418) from `basis`; `_PINNED_COLUMN`/`BS_PERIOD` (:1391-1392) are
`basis.bs_column`/`basis.bs_period`; the claim check message (:795) and the limitation (:2358) state the balance date from
`basis` ("31 December 2025" is `ltm_end` formatted `%-d %B %Y`); `currency="USD"` (:1206) is `basis.currency`; the "FY2026 to FY2028" text (:1495) and `US$ m` sites (:2296-2297) follow `basis`. CP-4C reads
CP-2G's forecast fact by `YEARS`; the Phase 6 pin and Phase 7 selected multiple are untouched.
- [ ] **RED tests:** (a) default output equals `tests/test_owner_cp4c.py` goldens; (b) 2026 basis: years `FY2027..FY2029`,
  claim `period_column` must equal `Q4 2026-12-31` (the old `Q4 2025-12-31` is refused with that text), limitation reads "31
  December 2026"; (c) a non-December balance date (`2026-06-30`) reads "30 June 2026"; (d) `FY2026` as a forecast year under a
  2026 base is refused (it is the base year); (e) EUR: no `US$` in any cp4c cell or claim.
- [ ] **Run:** `pytest tests/test_periods_currency_cp4c.py tests/test_owner_cp4c.py tests/test_connect_cp4c.py -q`.
- [ ] **Commit:** `feat(cp4c): balance date, forecast years and currency from the run context (P8 T6)`.

## Task 6b: CP-1B row labels take the run's money unit (B17-9; sensitive: `src/deploy_vii` diff; `mx-adversary`)

**Files:** `src/deploy_vii/bindings/cp1b.py` (repo-authored, not in `files[]`), `src/deploy_vii/report_view.py` (imported),
`docs/reuse/manifest.json`, the re-pinned files below, `tests/test_periods_currency_cp1b_labels.py`.
**Smallest change.** In `bindings/cp1b.py` the nine money labels (:32-49, including `Net debt (US$ m)` at :49) are written with a `{unit}` placeholder
(`"Revenue ({unit})"`); `def cp1b_layouts(unit: str = "US$ m") -> tuple[_Layout, ...]` returns them formatted, and
`_CP1B_LAYOUTS = cp1b_layouts()` stays, so every USD caller and the module's bytes of output are unchanged. In
`report_view._validate_cp1b_layout` (:2315-2356) the unit is read from the facts, not trusted from the labels: C is the
currency of `cp1b:T1B.1:revenue:current`, required non-None, and `scale_label("MILLIONS", C)` (:1024) is the unit.
`_cp1b_fact_shape` (:2285-2300, B18) is in scope: its hard-coded `("MILLIONS", "USD", Decimal(1000000))` at :2298 becomes
`("MILLIONS", C, Decimal(1000000))` for every money fact on all nine rows (prior, current, delta); there is no "gaps with no
currency -> `US$ m`" fallback. REDs: a row in a currency other than C refuses; a None currency refuses; USD output is byte-identical. The loop at :2344 and the row at :2386 then use
`cp1b_layouts(unit)`; any label not equal to that layout's still raises "CP1B layout has invalid ordered rows or labels".
`earnings_workflow.py:1619-1635` (the producer) builds its labels from the same `cp1b_layouts(unit)` so the two cannot drift.
**D12.** `bindings/cp1b.py`: B14 shape (`imported_sha256` = `prior_project_sha256` = its sha256 at the commit before this
task, `reason` begins "repo-authored (not in files[])"); `report_view.py`: normal record (`project_commit` = the commit
where the file hashes to `sha256`, last record `docs/reuse/manifest.json:1795`, sha `5dc981...`). Review: `mx-adversary`.
**Re-pins** (found at HEAD by `git grep -n "report_view.py\|bindings/cp1b.py" -- cases tests docs/reuse`, re-run at the tip):
`cases/cpos-owner/manifest.json:10`, `cases/cpos-owner/builder/build.py:28` (`read_pinned` asserts the `report_view.py` hash) and the `cases/PINS.json` entries that follow from it (`cases/cpos-owner/builder/build.py` at :104 and any cpos-owner file it regenerates); `cases/legal/manifest.json:294,338` hold old provenance hashes, are unenforced and are not re-pinned; every `PINS.json` entry whose file changes;
each re-pin runs through the oracle process (a separate preparer regenerates, independent `mx-precise` checks, `python3 -I cases/pins.py`)
in the same commit. Chart oracles that quote `report_view.py` (`cases/charts/*`) are checked by their own tests.
- [ ] **RED tests:** (a) `cp1b_layouts()` equals today's `_CP1B_LAYOUTS` row by row; (b) a CP-1B module with EUR/MILLIONS
  facts and `Revenue (EUR m)` labels passes `_validate_cp1b_layout`; (c) the same labels over USD facts raise "invalid
  ordered rows or labels"; `Revenue (US$ m)` over EUR facts raises likewise; (d) revenue prior EUR, current USD raises; (e)
  all-gap money rows take C (the currency of `revenue:current`), and a None currency refuses.
- [ ] **Run:** `pytest tests/test_periods_currency_cp1b_labels.py tests/test_report_view.py tests/test_earnings.py -q` plus
  every test that reads the re-pinned manifests (found by the grep), and `python3 -I cases/pins.py --check`.
- [ ] **Commit:** `feat(cp1b): row labels take the run's money unit (P8 T6b, B17-9)`.

## Task 7: CP-2A, CP-2E, CP-L10, CP-1B (`mx-adversary` for CP-1B, CP-2A and CP-2E; CP-L10 rides)

**Files:** modify `owners/cp2a.py`, `owners/cp2e.py`, `owners/cpl10.py`, `owners/cp1b.py` (Part B O1; rebase on it),
`src/deploy_workflow/earnings.py`, `src/deploy_workflow/earnings_workflow.py` (Phase 2 owns `_case_parameters`; rebase);
create `tests/test_periods_currency_misc.py`.
**Sweep:** `git grep -nE "USD|US\\$|FY ?2025|2026-01-10|IFRS" -- <the six files>`; `earnings_workflow.py` hits at least :1619-1635,
1648-1653, 1652, 1679, 1899, 1923; `earnings.py:187` (USD).
- **CP-2A** (period-agnostic, `cp2a.py:160-173,1520-1560`; `currency_basis`, any base): `_in_usd_millions` (:1510-1514) and
  `currency="USD"` (:891) use `basis.currency`; `US$ m` sites (:1329-1331) use `basis.money_unit`.
- **CP-2E (H2).** CP-2E has no CP-1 input (`cp2e.py:1819`; the frozen case runs CP-0 then CP-2E), so `period_basis(context,
  cp1_facts)` has no T4.14 rows to read. CP-2E builds its **own** basis: `base_year` from `run.current_period` (`fy-YYYY` or
  `q4-YYYY`), the window and balance date from the statement's own `FY YYYY` header (`_FY_HEADER`, :541) and rows; it refuses
  (named issue) when the header year differs from the context year, or the base kind is not fy/q4. `PER_FLOW`, `PER_BAL`,
  `PER_SHOCK` (:864-867) and the "FY 2025" prose (:1219, :1228, :1419, :1447) use that basis; `PER_RUN` ("Run as of
  2026-01-10") is `pack.run.as_of`. Currency: the statement's `Currency:` clause must equal `reporting_currency`.
- **CP-L10** (`currency_basis`): `_USD`, `_MONEY` (:90-91), topic unit (:550) and `US$ m` sites (:138-142) use the currency
  basis; quarters per Phase 2 (Assumes).
- **CP-1B (B17-9).** Labels follow Task 6b. `owners/cp1b.py` and the `build_earnings_delta` callers
  (`earnings_workflow.py:1278, 2020, 2525`) call `currency_basis`; `build_earnings_delta(..., *, currency="USD")` takes
  the run currency (`earnings.py:147-150`, :187); the row labels at `earnings_workflow.py:1619-1635` and the
  `_COMMON_LIMITS` sentence are formatted from `money_unit`/`currency`. Accounting basis stays IFRS-only.
- [ ] **RED tests:** (a) default paths byte-equal (existing `tests/test_earnings.py`, `test_owner_cp2a.py`, `test_owner_cp2e.py`,
  `test_owner_cpl10.py` green); (b) CP-1B under EUR settles with `EUR m` labels that the layout check accepts, under USD and a `q3-2026` base it settles
  (M3); a USD context over an EUR T4.14 head raises `incompatible_dimensions`; (c) CP-2E
  accepts the `FY 2026` header under `fy-2026`, refuses `FY 2025` under it, refuses under `h2-2026`, with no CP-1 input
  supplied; `PER_RUN == "Run as of 2027-01-10"` for `as_of` 2027-01-10; (d) CP-2A refuses a EUR operand under USD and offers
  it under EUR, and offers a `q3` base; (e) one EUR RED per module (CP-1B, CP-2A, CP-2E, CP-L10): no `US$` in any cell or claim.
- [ ] **Run:** `pytest tests/test_periods_currency_misc.py tests/test_earnings.py tests/test_owner_cp2a.py tests/test_owner_cp2e.py tests/test_owner_cpl10.py tests/test_owner_workflow.py -q`.
- [ ] **Commit:** `feat(cp2a,cp2e,cpl10,cp1b): currency and base period from the run context (P8 T7)`.

## Task 8: methods wording (B9; `mx-feature` review; the only `src/deploy_vii` diff)

**Files:** `src/deploy_vii/methods/cp1c.md` (:9,13,29), `cp2a.md` (:31), `cp2d.md` (:32), `cp2g.md` (:11,33-39), `cp2h.md`
(:13-14), `cp3c.md` (:60), `cp4c.md` (:12 and any other FY2026-FY2028 hit); `docs/reuse/manifest.json` (one
`post_import_patches` record per file, `imported_sha256` from the file's first manifest entry, `prior_project_sha256` = the
previous patch or the import hash, `project_commit` = the commit where the new bytes hash to `sha256`, `reason` "B9: wording
only, Phase 8 period/currency", `review` = the `mx-feature` review file). Do not touch `cp0.md:90` (a digits rule, not a period).
**Behaviour.** Wording only: "LTM Q4 25" -> "the LTM Q4 column of the run's base year (LTM Q4 25 when the run has no context)",
"FY2026 to FY2028" -> "the three fiscal years after the base year", "USD" -> "the run's reporting currency (USD by default)". No rule,
number, table id or schema name changes.
- [ ] **Checks (no RED; wording-only per B9, state this in the report):** `git diff --stat` shows only the seven `.md` files and
  `manifest.json`; `git diff -U0 -- src/deploy_vii | grep '^[+-]' | grep -vE '^(\+\+\+|---)'` shows no digit-bearing rule
  changed except the period words; the test that reads `docs/reuse/manifest.json` (find it with `git grep -l "reuse/manifest" -- tests`; none was
  found by name at HEAD) exits 0, or the report says no such test exists; `python3 -I cases/pins.py --check` exits 0 (no methods file is pinned); also `pytest tests/test_connect_cp1c.py tests/test_connect_cp3c.py tests/test_connect_cp4c.py tests/test_method_cp2h.py -q`.
- [ ] **Commit:** `docs(methods): period and currency wording follows the run context (P8 T8, B9)`.

## Done-when as tests (`tests/test_periods_currency_oracle.py`, runs Task 0's frozen cases)

1. `test_r1_relative_value_fy2026`: R1 settles CP-1C, CP-2D, CP-3C; no emitted period string contains a stale unshifted literal, the list `expected.json` `runs.*.stale_period_literals_forbidden_in_emitted_period_strings` (checked for R1, R2, R3, R6, `build.py:783`) (amended 2026-11-01, frozen oracle `cases/periods-currency-owner/`: `builder/build.py:607-614, 631-657`, `expected.json:207` and `:58537`). The list is derived, not hand-listed. Rule as the builder applies it (`build.py:607-614`, `derive_stale` :631-657): a candidate is a period-bearing phrase of a frozen source oracle (a year or two-digit period label, up to two words before and one after; amounts and bare dates never match, `build.py:607-614`); it is kept only if it contains two digits and no shifted oracle or submission of any module or currency carries it (:655); then reduced to the minimal set, dropping a phrase that contains another kept phrase (:656). A bare `2025` check is not the test: a 2026 pack legitimately holds 2025 dates, e.g. the opening balance (`expected.json:58537`); figures equal
   `expected.json`.
2. `test_r2_distressed_q4_2026`: R2 settles CP-2A, CP-2G, CP-2H, CP-4C, CP-2E, CP-L10; forecast columns FY2027-FY2029.
3. `test_r3_earnings_eur`: R3 CP-1B settles with `EUR m` labels; CP-1D settles, every amount fact carries `EUR`.
4. `test_r4_currency_mismatch_refuses`, `test_r5_h2_base_refuses`: named refusals, no figure; `test_r5b_q3_base_settles` (CP-2A, CP-L10, CP-1B in USD).
5. `test_no_context_pack_unchanged`: the frozen `cases/*-owner` suites pass unchanged (`pytest tests/test_owner_*.py
   tests/test_connect_*.py -q`).
6. `test_no_hardcoded_period_left`: `git grep -nE "LTM Q4 25|q4-2025|FY2026, FY2027|\"USD\"" -- src/deploy_workflow/owners`
   matches only `period_basis.py` and an allow-list in the test (the CP-1 fact-label parsers that read vii's own format).
7. `test_eur_runs_render_no_usd_token`: the rendered output of R2, R3 (CP-1B, CP-1D) and R6 for every Phase 8 module including CP-1B contains `EUR m` and no `US$`.
Gate once before hand-off: `pytest tests -q` (full suite), `python3 -I cases/pins.py --check`, ruff/format/mypy on changed files.

## Ruled (coordinator, `work/context-plan/reviews/phase-8-plan-review.md`); no open questions remain

1. **Year-bearing ids** (`total_leverage_fy28`, `change_vs_fy25`, `cp2g.py:2049-2050`). Ruled: keep; they are frozen
   schema names, the labels follow `basis`. Renaming breaks every frozen submission.
2. **Non-USD CP-1.** No evidence here that vii CP-1 settles a EUR statement end to end. Ruled: the preparer promotes the
   EUR pack in Task 0; if CP-1 refuses, R2, R3 and R6 become the refusal cases and the user decides whether a vii CP-1 change is wanted.
3. **O6 prompt texts** may quote period strings (their inputs are `methods/*.md`, O6 plan :158). Ruled: O6 texts take the
   period from the `read_inputs` view (data), not the prompt; check at the tip, otherwise a one-line O6 follow-up.
4. **IFRS-only and `US$` in other renderers** (`financial_series.py:215,314`, `liquidity_series.py:27`, charts) are outside
   these modules. Ruled (B17-10): `US$`/IFRS labels outside the Phase 8 modules stay out of scope and are listed in the final report; Done-when 7 requires that the EUR runs' rendered output for every Phase 8 module holds no `US$`.

Not verified: no test or gate was run; the three p8probe scripts were not rerun against this text; the CP-2E statement-header and `Currency:` clause forms; `HEAD` line numbers, the T4.14 field names (`fiscal_quarter` text form), vii CP-1 on a
non-USD or non-calendar-year pack, and whether the shifted-year oracle reproduces the frozen figures are all unchecked.
