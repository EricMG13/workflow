# Phase 7: valuation from the context Implementation Plan

**Status:** draft 2026-10-31 on `claude/context-plan-build` (28ad7934); not started. Build after Phases 3, 4, 5 and 6 (order 2 to 8,
parent plan :339) and before Phase 8. Phase row: `docs/superpowers/plans/2026-10-31-context-file-consumption.md:330`;
questions and rulings: `work/context-plan/reviews/phases-2-8-questions.md:102-115`; user ruling B8
(`docs/rulings/2026-10-31-context-plan.md:30-32`: `src/deploy_vii/methodology.json` (CP-4C upstream CP-1C; new CP-1C EV/EBITDA
tables), `bindings/cp1c.py`, `contracts.py` (CP-1C in the distressed preset); D12 records; `mx-adversary`). Line numbers are
`HEAD` (28ad7934); each task opens with the grep in its **Sweep** line.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** a pack that holds the `context` source gets an EV/EBITDA valuation basis: CP-1C admits the user's peer comps and
precedents (`valuation.peers`, `valuation.precedents`), reads the issuer's own trading and the user's own multiple, selects one
basis by the ruled `auto` thresholds, and publishes the selected multiple and an implied EV range as Python-computed tables;
CP-4C (distressed) must use that multiple. A pack without a `context` source behaves exactly as today.

**Done when (parent row 7):** a private-issuer run with user comps produces a peer EV/EBITDA range and CP-4C uses it
(tests under "Done-when as tests").

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a context that cannot be read is a
  named validator issue, never "no valuation"); no network call; no key read. Exact `Decimal` in CP-1C's 38-digit half-even
  context (`cp1c.py:69`); empty means "not supplied", never zero (`context.py:246`).
- `src/deploy_vii`: only the three B8 files, each with a D12 `post_import_patches` record in `docs/reuse/manifest.json`
  (`project_commit` = the commit where the file hashes to `sha256`; record shape at `manifest.json:1641-1649`) and an
  `mx-adversary` review. Nothing else: not `bindings/cp4c.py`, `report_view.py`, `methods/*.md` (Ruled Q5), `readiness.py`. A change
  that needs another vii file stops BLOCKED. `src/deploy_vii` never imports `deploy_workflow` (`bindings/cp1c.py:10`).
- **Every `methodology.json` commit carries its re-pin amendment** (O7 review M2, `work/context-plan/reviews/o7-plan-review.md`):
  the file's hash is pinned in 44 files (`git grep -l <old sha256>`; 14 oracle `manifest.json`, 14 `builder/build.py`,
  `cases/PINS.json`, the leases under `docs/`); `contracts.py`'s hash is pinned too (`cases/cpos-owner/manifest.json:15`, `builder/build.py:34`, asserted by `read_pinned`), so the contracts.py commit re-pins the cpos builder and manifest, starting from the registry.py pin O1 Task 1's fix round sets (19ec267d...); the old D12 record (`manifest.json:1277`) stays as written. The amendment runs the oracle process (AGENTS.md :58-91): a **separate preparer**
  (not the builder) rewrites the pins and the lease headers, an **independent `mx-precise`** reviews, the preparer runs the product
  validators and a scratch double rebuild and reports exit codes, and `python3 -I cases/pins.py --check` exits 0, all in the same
  commit as the `methodology.json` change (precedent: the CP-6 freeze re-pin).
- A pack without a `context` source and with explicit modules: every frozen `cases/*-owner` case, `cases/PINS.json` entry (apart from the re-pin and the
  new case's lines) and test stays green; CP-1C composes exactly T1C.1-T1C.8; no table, fact, key or limitation differs.
- Reports end `Not verified:` and list table, row and field changes (R7): this phase adds T1C.9-T1C.11 (context packs only) and
  changes no existing table id, row id or field name.
- Test command: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`. Gates on changed
  files: `ruff check`, `ruff format --check`, `mypy`; complexipy <= 15 on new functions; the full suite once before hand-off (B3).

## Assumes (checked at the tip before Task 1)

| Earlier work | Relied on | If absent |
|---|---|---|
| Phase 1 | `context_facts(pack) -> RunContext \| None`, `ContextRefused` (`context.py:733`) | stop |
| Phase 6 | `assumptions.cp4c.ev_multiple` pin binds a CP-4C submission (D4); Task 4's rule must not fight it (Ruled Q4) | Task 4 omits the pin clause and says so |
| Part B O7b-1 | CP-DR row moved ahead of CP-1C in `methodology.json` | rebase; rerun Task 1's re-pin on the new hash |
| Part B O7d | TDR.4-6 peer pack; CP-1C reads TDR.6 | public peers stay a named gap (below); no part of this phase waits |

## Design (settled by B8 and the questions file; the tasks build exactly this)

1. **Where it lives.** CP-1C owns peer admission, normalisation and implied EV (CP-DR v2.4 ownership rule, questions :115). All
   new arithmetic is a new pure module `src/deploy_workflow/owners/valuation_basis.py` (no I/O); `owners/cp1c.py` calls it from
   `_compose` (`cp1c.py:1300`) only when the context is present. The analyst submission (`PeerBenchmarkSubmission`,
   `cp1c.py:235`) does **not** change: the EV tables are Python-only, so no prompt, schema or frozen submission moves.
2. **Inputs, all from `context_facts(pack)`** (`PeerRow` `context.py:136`, `Precedent` :145, `IssuerMarket` :127, `UserMultiple` :154,
   `Valuation` :160) plus CP-1's LTM adjusted EBITDA fact (T4.10, the fact CP-4C reads as `cp1["ebitda"]`, `cp4c.py:1646`).
   Peer origin is a field of the admitted record (`user_comps` now; `cp_dr_public` rows join through the same record when O7d
   lands). Run as-of is `pack.run.as_of`.
3. **Admission** (per record; every refusal a row with its reason, never dropped): EV > 0, EBITDA > 0, a precedent has a deal date (the form leaves it optional, `context.py:534`; undated is `Excluded: no deal date, the window cannot be checked`) (context already enforces
   EBITDA > 0, `context.py:565`; EV may be 0, :564), dated on or after the window start. Window: public comps 12 months, precedents
   36 months, counted back from the run as-of by calendar month (same day, clamped to month end: as-of 2026-01-10 gives 2025-01-10
   and 2023-01-10; 2024-02-29 gives 2023-02-28). Both are ruled thresholds (questions :103-105). The window applies to explicit
   bases as well as `auto` (Ruled Q2). A record dated after the as-of cannot exist (`context.py:394-406`).
4. **Statistics:** per set, `n_total`, `n_admitted`, min, median (`cp1c.median`, :413), max, and the outlier flag from
   `cp1c.outlier` (:437; deviation above 0.5 flags, flag only, never excludes). The median needs `MIN_INCLUDED_PEERS = 3`
   admitted (`cp1c.py:72`, `peer_median` :424); below that the median is `missing` with `NO_MEDIAN`-style text. Multiples are
   shown at 2 dp (fact `decimals=2`, `contracts.py:179`).
5. **Selection** (`select_basis(requested, public, precedents, issuer, user)`): `public_comps`: public median, else gap, no fallback.
   `precedents`: precedent median, else gap. `blend`: the plain average of the two medians, both needed (Ruled Q1). `issuer_trading`:
   issuer EV / CP-1 LTM adjusted EBITDA (EV = `ev_m`, else `market_cap_m + net_debt_m`); `ebitda_basis` NTM is a named gap, because
   NTM needs CP-2G's forecast, which runs after CP-1C (questions item 3). `user_multiple`: the user's value, labelled
   "user-supplied" with its rationale; an NTM basis is carried as a label. `auto`: public comps when >= 3 admitted; else precedents
   when >= 3 admitted; else `Insufficient Information` (a gap, never 0); `blend` is never automatic (ruling, questions :103-105).
   Because the form forbids precedents unless basis is `precedents`/`blend` (`context.py:538`), `auto` meets precedents only when
   CP-DR supplies them (O7); that branch is covered by unit tests, not by a context case (Not verified).
6. **Selected multiple** = the chosen median/average/value rounded half-even to 2 dp (CP-4C's field allows 2 dp, `cp4c.py:101`);
   above 99.99 it is a gap naming the limit, never clamped. **Implied EV** = selected multiple x CP-1 LTM adjusted EBITDA;
   if CP-1's EBITDA is not a known positive amount it is a gap with that reason (as `cp4c.py:1646-1660`).
7. **User comps lack currency and period end** (`PeerRow` has name, ticker, `ev_m`, `ebitda_m`, `as_of`, `source`; questions
   item 3, `cp1c.py:294-301` needs period ends). The plan invents neither. The multiple is a ratio of two figures the form
   labels in one unit ("EV (m)", "EBITDA (m)": form :587), so currency cancels; T1C.9 shows currency and EBITDA period as the text
   `Not stated by the user` (reusing the idea of `NOT_STATED`, `cp1c.py:80`), `figures_date` as the user's `as_of`, never as a
   period end. A limitation says the peers' currency and EBITDA period are not stated and the multiple assumes EV and EBITDA share
   both, and that it is applied to the issuer's `LTM Q4 25` EBITDA (`cp1c.py:1524`, Phase 8 generalises). These records never
   enter T1C.1-T1C.6 (those need period ends and a `Basis:` clause, `cp1c.py:104`).
8. **Public peers.** `cp_dr_public` and `user_list` give no figures in the context (`context.py:557-559`, :562-571). Until O7d's
   TDR.6 pack exists CP-1C writes the named gap `No peer figures: cp_dr_public peers come from the CP-DR peer pack (Part B O7d)` /
   `... user_list peers need the peer lookup (O7d)` and applies no fallback. O7d feeds the same admitted-record type (hand-off
   list). The TDR.6 operand set must add `ev` (today `OPERANDS` has none, `cp1c.py:129`); this phase does not touch `OPERANDS`
   (that would change frozen T1C.2).
9. **Tables** (one fact per column in every row, `contracts.py:284-286` (report row cells match columns); a cell with no value is a `not_applicable`/`missing` fact
   with its reason). Registered in `methodology.json` CP-1C `table_ids` (:111-120):

| Table | Meaning | Row ids | Fields |
|---|---|---|---|
| T1C.9 EV/EBITDA records | one row per user peer and precedent | `e01..` peers, `x01..` precedents | `kind`, `name`, `figures_date`, `source`, `currency`, `ebitda_period`, `ev`, `ebitda`, `multiple`, `flag`, `result` (`Included` or `Excluded: <reason>`) |
| T1C.10 EV/EBITDA statistics | one row per set | `public_comps`, `precedents`, `issuer_trading`, `user_multiple` | `n_total`, `n_admitted`, `min`, `median`, `max`, `outliers` |
| T1C.11 Valuation basis selection | the one selection | `selection` | `requested_basis`, `selected_basis`, `reason`, `ebitda_basis`, `selected_multiple`, `issuer_ebitda`, `implied_ev` |

   Units: multiples 2 dp; `issuer_ebitda` and `implied_ev` are `MILLIONS` at 1 dp (`SHEET_DECIMALS`, `cp1c.py:112`; the exact product, rounded half-even for display only), so 210.0 here and 216.30 (2 dp) in CP-4C. A user NTM multiple is carried with its label and its `implied_ev` is a gap (an NTM multiple is not applied to LTM EBITDA); an issuer EV that is zero or negative is a gap.

   Bindings (vii): T1C.9-T1C.11 go to **Evidence** (a rail destination, composed in every pathway, `bindings/__init__.py:21-23`),
   so the distressed report, which composes no `peer-positioning` block (`report_view.py:581-600`), shows them; T1C.1, T1C.3, T1C.4, T1C.5 and T1C.8 in a
   distressed run stay bound to `peer-positioning`, which the pathway does not compose (T1C.2, T1C.6, T1C.7 sit on rails, `bindings/cp1c.py:41-45`; the five are listed as unplaced, `report_view.py:2244`; accepted, Ruled Q7).
10. **Reader.** `Cp1cHead` (`cp1c.py:2022`) exposes `READER_FACTS` (:2011). A new `EV_READER_FACTS` (`T1C.11.selection.selected_multiple`,
    `.selected_basis`, `.ebitda_basis`, `.implied_ev`) is read only when the head holds table T1C.11, so a frozen head still
    reads (`cp1c_reader` :2040 raises on a missing fact; unchanged for the old set).
11. **CP-4C.** `methodology.json` CP-4C gains CP-1C as an **optional** upstream (not required: required would put CP-1C in every
    frozen cp4c case's plan order, whose `requested_modules` is `["CP-4C"]`, `cases/cp4c-owner/manifest.json:91`; optional edges bind
    only when requested, as CP-3C does, `cp4c.py:536`). The distressed preset gains CP-1C (`contracts.py:67-69`). When the pack has
    a context and CP-1C's head is bound with a known `selected_multiple` M, every `Valuation.multiple` in the submission must
    equal M numerically (`7` equals `7.00`) or the submission is refused naming the valuation and both values; `not assessed` is
    refused too (Ruled Q3). Otherwise CP-4C applies no multiple rule (the registry consequences of Design 12 still hold). The rule is skipped when the context pins a CP-4C multiple (`assumptions.cp4c`, Phase 6): the pin rule governs (Ruled Q4). The T4E.3 multiple cell (`cp4c.py:1702`) keeps its value class and gains the
    `formula` text `analyst input, equal to the CP-1C selected multiple (T1C.11, basis <selected_basis>)`; no `derives`
    (a `cp1c:` derive needs a new reference table and binding, `bindings/cp4c.py`, which B8 does not approve). One CP-4C
    limitation states the basis, EBITDA basis and the CP-2G year it is applied to, and that no alignment is made between an
    LTM/NTM multiple and a forecast year. `context_block` (`cp4c.py:2860`) gains a `selected_multiple` key only when bound.
12. **Preset consequences (B8; H1).** CP-1C in the distressed preset has these effects, each pinned by a test (Task 1): (a) the registry
    plan is exactly `(CP-0, CP-1, CP-1A, CP-1C, CP-2A, CP-4, CP-2, CP-2G, CP-2H, CP-4C, CP-5)` (HEAD: `(CP-0, CP-1, CP-1A, CP-2, CP-2A,
    CP-4, CP-2G, CP-2H, CP-4C, CP-5)`; probe `p7probe/plan_order.py`), so CP-2 moves after CP-2A and CP-4; (b) CP-2 already lists CP-1C
    optional (`methodology.json:160-165`), so CP-2, CP-4C and CP-5 all bind the CP-1C head (`execution.py:231-247`); (c) CP-2 and CP-4C
    inherit CP-1C's limitations (`execution.py:345-365`), a blocked CP-1C restricts CP-4C (:484-489), and a missing CP-1C head stops
    CP-2 and CP-4C; (d) CP-1C needs `period_coverage` (`downstream_readiness.py:29`); (e) a distressed pack **without** context also plans
    CP-1C (no `peers` source: the no-peers design, `cp1c.py:86`, runs an analyst step). CP-2's optional CP-1C edge is not edited (outside
    B8); whether to remove it goes to the user. Frozen cases name `requested_modules` and do not change; a pack that takes the preset
    default (`contracts.py:94`) changes its pack hash, including earlier phases' distressed context packs (Task 1 finds them).

## Interactions with Part B (named)

- **O7d** edits `owners/cp1c.py`, `methodology.json`, `bindings/cpdr.py` (`part-b-o7.md` :76, :178): Phase 7 builds first or second; whichever
  lands second re-reads `cp1c.py` at its tip and re-runs the `methodology.json` re-pin on the new hash. O7d's brief gains: build
  `AdmittedRecord`s from TDR.6 (this phase's type, `valuation_basis.py`), add the `ev` operand to TDR.6, pass them to `select_basis`
  with origin `cp_dr_public`.
- **O7b-1** moves the CP-DR row in `methodology.json` (H3): same rebase and re-pin rule.
- **O1** (`owner_workflow.py`, walk): not edited here. **O6** (prompts): CP-1C's `read_inputs` view is unchanged; CP-4C's gains the
  `selected_multiple` key; O6's CP-4C prompt text should say "use `selected_multiple` when present" (hand-off, no prompt edit here).
- Shared with Phases 6 and 8 (`cp4c.py`) and Phase 8 (`cp1c.py`): build in order; Phase 8 replaces the `LTM Q4 25` strings this phase
  reuses with `basis` fields.

## Task 0: Oracle (separate preparer; independent `mx-precise` review; frozen and pinned before Tasks 1-4)

The builder of Tasks 1-4 neither prepares nor reviews it (B2). New case `cases/valuation-context-owner/` (`manifest.json`,
`contexts/*.json`, `expected.json`, `builder/build.py`, stdlib only, deriving every value from the manifest). The glob in
`cases/pins.py` (`*-owner/...`) adds its files to `PINS.json`. Pack: the frozen identity and financial sources of
`cases/cp1c-owner` (run as-of 2026-01-10, `case_kind synthetic`, USD millions; Adjusted EBITDA FY2025 = 30.0 from the financial
page) with `pathway distressed_restructuring`, `requested_modules ["CP-1C","CP-4C"]` plus their closed chain as in
`cases/cp4c-owner` (base FY2026 CP-2G EBITDA 30.90, `cases/cp4c-owner/expected.json` fact `T4E.3.v01.ebitda`), and one `context`
source from each file below via `context.prepare`. Peer and precedent names are invented and labelled synthetic. All values are
hand-derived from the rulings above.

Peers used (user_comps; `as_of`, EV, EBITDA, multiple): A 2025-11-30, 540, 60, 9.0; B 2025-09-30, 330, 55, 6.0; C 2025-12-31, 700, 100,
7.0; D 2024-12-31, 400, 50, 8.0 (before 2025-01-10); E 2025-10-15, 0, 10 (EV zero). Precedents (date, EV, EBITDA, multiple; P6 has no date, 700, 100): P1
2024-06-30, 900, 100, 9.0; P2 2023-09-15, 1250, 125, 10.0; P3 2022-12-31, 800, 100, 8.0 (before 2023-01-10); P4 2025-03-31, 1000,
80, 12.5; P5 2024-01-31, 600, 100, 6.0.

| Context file | Inputs (`context.json` fields) | Expected |
|---|---|---|
| `auto-public.json` | `peer_source user_comps`, `basis auto`, peers A-E | T1C.9: e01-e03 `Included`; e04 `Excluded: figures dated 2024-12-31 are before 2025-01-10 (12-month limit)`; e05 `Excluded: enterprise value is zero`. T1C.10 `public_comps`: n_total 5, n_admitted 3, min 6.00, median 7.00, max 9.00, outliers 0 (deviations 0.2857 and -0.1429). T1C.11: `selected_basis public_comps`, `selected_multiple 7.00`, `issuer_ebitda 30.0`, `implied_ev 210.0`. CP-4C with multiple `7.00` on all three cases: v01 EV 216.30 (30.90 x 7.00), implied LTM 7.21x; v02 and v03 (EBITDA 18.54) EV 129.78, implied 4.33x |
| `auto-thin.json` | `user_comps`, `auto`, peers A, B, D | n_admitted 2; median `missing`; T1C.11 `selected_basis Insufficient Information`, multiple `missing` with a reason naming 2 of 3 and both windows; CP-4C is not bound to a multiple: `4.00` and `not assessed` both accepted as today |
| `public-thin.json` | `user_comps`, `public_comps`, peers A, B | same counts; T1C.11 `selected_basis` gap `requested public_comps, 2 admitted of 3 required; no fallback` |
| `precedents.json` | `peer_source none`, `precedents`, P1-P6 | P3 `Excluded: ... before 2023-01-10 (36-month limit)`; P6 `Excluded: no deal date, the window cannot be checked`; n_total 6, n_admitted 4; min 6.00, median 9.50 ((9+10)/2), max 12.50; outliers: P4 (deviation 0.3158, within) none; selected 9.50; implied EV 285.0 |
| `blend.json` | `user_comps` A-C, `blend`, P1-P6 | public median 7.00, precedents median 9.50; selected 8.25 ((7+9.5)/2); implied EV 247.5. With P3-P5 removed (3 admitted needed): selected a gap naming the precedents count |
| `issuer-trading.json` | `listed_equity true`, `issuer_trading`, `market_cap_m 200`, `net_debt_m 70`, `ebitda_basis LTM`, `as_of 2026-01-05`, `source` set | EV 270; multiple 270/30.0 = 9.00; T1C.10 `issuer_trading` n 1; selected 9.00; implied EV 270.0 |
| `issuer-trading-ntm.json` | same with `ebitda_basis NTM` | selected multiple `missing`, reason `NTM needs a forecast EBITDA that CP-1C does not read` |
| `user-multiple.json` | `user_multiple value 8.5 basis LTM rationale "Mid-point of sector LBO range"` | selected 8.50, label `user-supplied`, rationale shown; implied EV 255.0; T1C.10 `user_multiple` n 1 |
| `user-list.json` / `dr-public.json` | `peer_source user_list` (names) / `cp_dr_public`, basis `public_comps` | the O7d gap texts of Design 8; no fallback; no figure invented |
| `credit-plus-comps.json` | `cases/cp1c-owner` positive pack (with its `peers` source) plus `auto-public.json` content | T1C.1-T1C.8 equal the frozen positive expected; T1C.9-T1C.11 as `auto-public` |
| `auto-public-private.json` | `auto-public` with `case_kind private` (the Done-when run) | as `auto-public`, except no synthetic-case limitation line (the run is not synthetic) |
| `pin-vs-selection.json` | `auto-public` plus `assumptions.cp4c.ev_multiple 8.5` | selection stays 7.00; CP-4C multiples `8.50` accepted on all cases (v01 EV 262.65), limitation records `CP-1C selected 7.00`; submission `7.00` (equal to the offered multiple) refused with Phase 6's pin-differs text |
| `window-edges.json` | peers dated 2025-01-10 and 2025-01-09 | first `Included`, second `Excluded` (boundary day inclusive) |

`expected.json` also holds the named CP-4C refusal ids: `ev-multiple-differs` (`auto-public`, v01 multiple `4.00` against M 7.00: text
`valuation v01: multiple 4.00 differs from the CP-1C selected multiple 7.00`), `ev-not-assessed-when-selected` (`not assessed`
when M is known), and the CP-4C limitation text for `auto-public` (basis `public_comps`, EBITDA basis `Not stated by the user`,
applied to CP-2G base case FY2026). Pins that change: the `methodology.json` and `contracts.py` re-pins of Task 1 (including the cpos-owner builder and manifest) and `cases/PINS.json`'s
new lines; no frozen oracle's expected values change. The preparer runs the product table, claim and render validators and a
scratch double rebuild and reports exit codes; `mx-precise` reviews the table against B8, the questions file and this plan; the
controller freezes it.

## Task 1 (SENSITIVE: ordering, `src/deploy_vii` diff; `mx-adversary`): registry, preset, bindings, re-pin

**Files:** Modify `src/deploy_vii/methodology.json` (CP-1C `table_ids` + T1C.9-T1C.11, :111-120; CP-4C `optional` + `CP-1C`,
:393-412), `src/deploy_vii/contracts.py` (`"CP-1C"` after `"CP-1A"` in `distressed_restructuring`, :67-69), `src/deploy_vii/bindings/cp1c.py`
(three Evidence entries `T1C.9-T1C.11`, slots `cp1c-t1c-9..11`, units `text`/`text`/`text`), `docs/reuse/manifest.json` (three D12
records; `bindings/cp1c.py` has no prior entry, so Ruled Q6); the re-pin (all 44 pin files, lease headers, `cases/PINS.json`); tests below.

**Sweep:** `git grep -l <old methodology sha256>` (the 44); `git grep -n -E "distressed_restructuring|PATHWAY_MODULES|pathways\(\)" -- tests cases/goldens cases/context`
(checked at HEAD: no test hard-codes the distressed tuple or its plan order; the readers of `requested_modules`/`PATHWAY_MODULES` are `tests/product/test_context_prepare.py:40` (credit_snapshot only), `tests/test_owner_rendering.py:158-185` and `tests/test_cp1_chart_render.py:641` (other pathways), and the distressed-named tests `test_chart_render_dr2/dr345/dr6.py`, `test_chart_seam.py:560`, `test_owner_rendering.py:1222-1281`, `test_legal_render.py:282` and `test_connect_cp{2a,2g,2h,4c}.py` read the block list, which this phase does not change; the real exposure is packs that take the preset default), then run those files once as a scratch RED to see which fail, and list them in
the report. Also list every earlier phase's context case with `pathway distressed_restructuring` and no explicit `requested_modules`
(their pack hash moves, Design 12), and every earlier context case whose plan includes CP-1C (`auto` is the form default, `context.py:529`: their CP-1C head gains T1C.9-T1C.11).

- [ ] **Step 1: RED tests** (`tests/test_phase7_registry.py`; update enumerating tests only as the sweep finds):
  `test_cp1c_registers_ev_tables` (`registry.modules()` CP-1C `table_ids` ends T1C.8, T1C.9, T1C.10, T1C.11);
  `test_cp4c_optional_cp1c_not_required` (`registry.dependencies(("CP-4C",))` unchanged and lacks CP-1C; with CP-1C requested,
  `registry.plan(("CP-4C","CP-1C"))` lists CP-1C before CP-4C); `test_distressed_preset_plans_cp1c`
  (`PATHWAY_MODULES["distressed_restructuring"]` is exactly `(CP-0, CP-1, CP-1A, CP-1C, CP-2, CP-2A, CP-2G, CP-2H, CP-4, CP-4C, CP-5)` and
  `registry.plan` of it is exactly `(CP-0, CP-1, CP-1A, CP-1C, CP-2A, CP-4, CP-2, CP-2G, CP-2H, CP-4C, CP-5)`); `test_distressed_inputs_bind_cp1c` (CP-2, CP-4C, CP-5 input sets include CP-1C; CP-4C inherits its limitations; a Blocked CP-1C restricts CP-4C); `test_other_presets_unchanged` (five other tuples
  equal their HEAD values, spelled out); `test_ev_tables_bound_to_evidence` (the three bindings are in `CP1C`, block `evidence`,
  distinct slots, `validate_bindings` clean on a view holding the new tables); `test_frozen_cases_keep_plan_order` (every
  `cases/*-owner` manifest `plan_order` still equals the registry plan for its `requested_modules`);
  `test_connect_cp1c.py` updates the four tests the new tables break (`:1409` frozen `proposed_ids` = 8 tables; `:1227-1234`; `:1248`; `:1389-1400` lease D3 "only cp1c.py calls `cp1c_reader`", now also `cp4c.py`): the frozen eight and the new three are asserted separately, and the preparer amends the CP-1C and CP-4C leases (D3). `test_pins_check` runs `python3 -I cases/pins.py --check` and asserts exit 0.
- [ ] **Step 2: run, expect FAIL.** **Step 3: implement.** **Step 4: re-pin** by the preparer/reviewer process in Global Constraints;
  the report lists old and new hashes of every re-pinned file group, the preparer's double-rebuild exit codes and the reviewer id.
- [ ] **Step 5: run, expect PASS**; the swept tests green; gates exit 0.
- [ ] **Commit:** `feat(registry): CP-1C EV tables, CP-4C optional CP-1C edge, CP-1C in the distressed preset, re-pin (Phase 7)`

## Task 2 (SENSITIVE: figures; `mx-adversary`): the valuation arithmetic

**Files:** New `src/deploy_workflow/owners/valuation_basis.py`; test `tests/test_valuation_basis.py`. No `src/deploy_vii`.

**Interfaces:** frozen dataclasses `AdmittedRecord(origin, kind, name, figures_date, source, ev, ebitda)`,
`Admission(record, multiple, included, reason)`, `SetStats(n_total, n_admitted, minimum, median, maximum, outliers)`,
`Selection(requested, selected_basis, multiple, reason, ebitda_basis, implied_ev)`; functions `window_start(as_of, months)`,
`admit(records, as_of, months)`, `stats(admissions)`, `select_basis(requested, public, precedents, issuer, user, issuer_ebitda)`.
Uses `cp1c.CTX`, `cp1c.median`, `cp1c.peer_median`, `cp1c.outlier`; imports nothing from `deploy_vii.bindings`.

- [ ] **Step 1: RED tests (inputs from Task 0's tables, written independently of the module):**
  `window_start(date(2026,1,10), 12) == date(2025,1,10)`, `(…, 36) == date(2023,1,10)`, `window_start(date(2024,2,29), 12) == date(2023,2,28)`,
  `window_start(date(2026,3,31), 1) == date(2026,2,28)`; `test_admit_boundary_day_inclusive` (2025-01-10 in, 2025-01-09 out);
  `test_admit_reasons` (EV 0 gives `Excluded: enterprise value is zero`; EBITDA <= 0 gives its own reason; stale gives the
  window text with both dates); `test_stats_peers_a_to_c` (n 3, min 6, median 7, max 9, outliers 0); `test_stats_even_count`
  (6, 9, 10, 12.5 gives median 9.5); `test_below_minimum_median_missing` (2 admitted gives `None`);
  `test_select_auto` (3 admitted -> public; 2 public + 4 precedents -> precedents; 2 + 2 -> Insufficient Information; blend never chosen);
  `test_select_explicit_no_fallback` (`public_comps` with 2 admitted -> gap although precedents exist); `test_blend_average`
  (7.00 and 9.50 -> 8.25; one side 2 admitted -> gap naming it); `test_round_half_even_2dp` (median 7.125 -> 7.12, 7.135 -> 7.14);
  `test_over_99_99_is_gap` (never clamped); `test_issuer_trading` (200 + 70 over 30.0 -> 9.00; `ev_m` wins when both given as the
  context allows; NTM -> gap with the NTM reason; EBITDA 0 or negative -> gap); `test_user_multiple_label`; `test_implied_ev`
  (7.00 x 30.0 = 210.0 exactly; 8.25 x 30.0 = 247.5); `test_zero_never_substituted` (every gap path returns no amount).
  Hypothesis: for any admitted multiples (>= 3, positive, <= 2 dp) `min <= median <= max`; `select_basis` never returns a multiple
  when fewer than 3 admitted back the chosen set; `admit` is order independent; `stats` outlier count equals the count of
  `outlier(...)` flags.
- [ ] **Step 2: FAIL. Step 3: implement. Step 4: PASS; gates.** **Commit:** `feat(cp-1c): EV/EBITDA admission, statistics and basis selection (Phase 7)`

## Task 3 (SENSITIVE: figures; `mx-adversary`): CP-1C composes the EV tables from the context

**Files:** Modify `src/deploy_workflow/owners/cp1c.py`; tests `tests/test_owner_cp1c.py` (extend),
`tests/test_cp1c_valuation_context.py` (new, runs Task 0's cases).

**Sweep:** `grep -n "_compose\|_COLUMNS\|_ROW_HEADERS\|TABLES\b\|READER_FACTS\|def _inputs\|def context_block" src/deploy_workflow/owners/cp1c.py`.

**Behaviour:** `PeerBenchmarkInputs` gains `context: RunContext | None = None` and `cp1_ebitda: Fact | None = None` (defaults keep the
Stage 1 callers and frozen tests). `_inputs` (`cp1c.py:1600`) fills them from `context_facts(pack)`; a `ContextRefused` becomes a
validator issue with its text. `_compose` (:1300), when `context` is set and has a valuation to show (peer_source `user_comps`
or `user_list`/`cp_dr_public` with a peer basis, any precedents, issuer_market, user_multiple, or basis `auto`), appends T1C.9-T1C.11
after T1C.8 through `valuation_basis`; `TABLES`, `_COLUMNS`, `_ROW_HEADERS` gain the three ids as a **separate mapping**
consulted only when present, so the frozen eight stay the default. Facts: `value_class` `source` for the user's figures (the
citation is the context file's `line:<n>` span of the field, Q-X ruling, questions :14-16), `calculated` for multiples, statistics,
selection and implied EV (with `formula`, `derives_from`), `decimals=2` for multiples. Text cells that are Python-composed are
facts with `value_class` `normalized`. Limitations (`_limitations`, :1191): the user-supplied label; the not-stated currency and
period line (Design 7); the thin-set line (reusing `THIN_UNIVERSE`, :75, if 3 or 4 admitted); each gap reason; the synthetic line
on a synthetic run as today. `Cp1cHead` gains the `EV_READER_FACTS` of Design 10. `context_block` (:1845) is unchanged.

- [ ] **Step 1: RED tests** (values from Task 0, not computed in the test): one test per row of the oracle table, asserting table
  rows, fact ids (`T1C.9.e01.multiple` ...), statuses, shown texts (`7.00x`), limitations and citations (`line:<n>` verified
  against the context bytes); `test_no_context_composes_eight_tables` (the frozen positive/gap/no-peers/refused heads equal their
  expected, byte for byte, incl. `cases/cp1c-owner/cp1c-view-tree.json`); `test_credit_plus_comps_leaves_t1c1_to_8_untouched`;
  `test_peers_source_never_feeds_ev_tables` (a `peers` source row is not an EV record); `test_context_refused_is_issue`;
  `test_reader_exposes_ev_facts_only_when_present`; `test_validate_tables_clean` (`validate_tables`, one fact per column);
  `test_tables_within_registry` (extends `tests/test_owner_cp1c.py:524-536`: composed ids are a subset of the registry's);
  `test_user_list_and_dr_public_name_the_o7d_gap`; `test_fewer_than_three_never_zero`.
- [ ] **Step 2: FAIL. Step 3: implement. Step 4: PASS** (affected: `tests/test_owner_cp1c.py`, `tests/test_connect_cp1c.py`,
  `tests/test_cp1c_valuation_context.py`, `tests/test_valuation_basis.py`); gates exit 0.
- [ ] **Commit:** `feat(cp-1c): context EV/EBITDA tables T1C.9-T1C.11 and the reader (Phase 7)`

## Task 4 (SENSITIVE: figures; `mx-adversary`): CP-4C uses the selected multiple

**Files:** Modify `src/deploy_workflow/owners/cp4c.py`; tests `tests/test_owner_cp4c.py` (extend), `tests/test_cp4c_valuation_context.py` (new).

**Sweep:** `grep -n "cp3c_status\|class Upstream\|def cp4c_upstream\|def content_issues\|def _t4e3\|def context_block\|CP3C" src/deploy_workflow/owners/cp4c.py`.

**Behaviour:** `Upstream` (:2630) gains `cp1c: Cp1cHead | None` (read through `cp1c_reader` only when the attempt binds a `CP-1C`
input, as `_bound_head` :2639 does for the others); `Cp4cContext` (:528) gains `cp1c` and `context`. `content_issues` (:938) adds
the Design 11 refusal after the existing checks (position: last, so existing issue order is unchanged for packs without context);
the stale check (`stale_issues`, :1056) already covers a changed CP-1C head. A bound CP-1C head that is `blocked` or whose
`selected_multiple` is not known has the effects Design 12(c) states (CP-4C restricted). The T4E.3 `multiple` cell's `formula` and one limitation are added
as in Design 11; `context_block` adds `selected_multiple` (value shown text, basis, ebitda_basis, head hash) only when bound. No
change to `RestructuringSubmission` (:96-140).

- [ ] **Step 1: RED tests:** `test_bound_multiple_accepted` (`auto-public`, v01 `7.00` and `7`: EV 216.30, implied 7.21x, formula text,
  limitation text from the oracle); `test_differing_multiple_refused` (`4.00`: `ev-multiple-differs` text); `test_not_assessed_refused_when_known`;
  `test_unknown_selection_changes_nothing` (`auto-thin`: `4.00` and `not assessed` accepted, no formula suffix, no extra limitation);
  `test_no_context_unchanged` (the frozen positive/gap/refused heads and `cases/cp4c-owner/*-view-tree.json` byte-equal);
  `test_cp1c_unrequested_unchanged` (CP-4C alone, a context pack: no `selected_multiple` key, no refusal); `test_stale_cp1c_head_refused`
  (CP-1C re-settled after CP-4C bound it: the existing staleness text); `test_pin_wins_over_selection` (`pin-vs-selection`: `8.50` accepted; `7.00`, equal to the CP-1C-offered multiple, refused by the pin rule; limitation names the selection); `test_all_three_cases_bound` (v02/v03 EV 129.78).
- [ ] **Step 2: FAIL. Step 3: implement. Step 4: PASS** (`tests/test_owner_cp4c.py`, `tests/test_connect_cp4c.py`, the new files); gates.
- [ ] **Commit:** `feat(cp-4c): bind valuation multiples to the CP-1C selected multiple (Phase 7)`

## Task 5: Form text and docs (mechanical; `mx-scaffold`, `mx-feature` review)

**Files:** `docs/templates/context-form.html` (the `Planned` tags on `auto` and the CP-1C EV note: lines :492, :498 say "(Planned)"; set
them to "(Python reads these; public peers need the CP-DR peer pack)" and keep `cp_dr_public` Planned), the form's `PATHWAYS` copy (:467) gains `CP-1C` in `distressed_restructuring` (a test compares it with `PATHWAY_MODULES`), :498 drops "or both" (no automatic blend) and :1082 drops "valuation basis selection" from the Planned list; `docs/RUN-GUIDE.md`
(a "Valuation from the context" section: which basis reads what, the not-stated currency and period, the 12/36-month windows,
that CP-4C refuses a different multiple), `README`/`PLAN.md` Outstanding line if the controller asks. No `src/deploy_vii` (the
method texts are unchanged, Ruled Q5). The form change touches the file Phases 2, 3 and 6 also edit: rebase, one hunk.
- [ ] Test: `tests/product/test_context.py` form-parity tests (the form's regex literals equal the reader's) still pass; commit
  `docs: valuation basis in the context form and run guide (Phase 7)`.

## Done-when as tests

| Parent Done-when | Test |
|---|---|
| A private-issuer run with user comps produces a peer EV/EBITDA range | `test_cp1c_valuation_context.py::test_auto_public` (Task 0's `auto-public-private.json`): T1C.10 `public_comps` min 6.00, median 7.00, max 9.00; T1C.11 selected 7.00, implied EV 210.0 |
| CP-4C uses it | `test_cp4c_valuation_context.py::test_bound_multiple_accepted` (EV 216.30) and `test_differing_multiple_refused` |
| No-context pack unchanged | `test_no_context_composes_eight_tables`, `test_no_context_unchanged`, `cases/pins.py --check` exit 0 |
| `auto` thresholds | `test_select_auto`, `window-edges` case |
| User comps lack currency/period | `test_credit_plus_comps_leaves_t1c1_to_8_untouched` plus the `Not stated by the user` cells in `auto-public` |
| Preset and edge | `test_distressed_preset_plans_cp1c`, `test_cp4c_optional_cp1c_not_required` |

## Ruled decisions (former open questions Q1-Q7; `work/context-plan/reviews/phase-7-plan-review.md`, B14)

- **Ruled Q1:** `blend` weights the two medians equally, each set needing 3 admitted records.
- **Ruled Q2:** the 12/36-month windows apply to explicit `public_comps`, `precedents` and `blend` too.
- **Ruled Q3:** every CP-4C valuation case, the stress case included, carries the selected multiple (fail closed). Whether a free stress multiple is wanted goes to the user in the final report.
- **Ruled Q4:** a Phase 6 pin (`assumptions.cp4c.ev_multiple`) wins over the CP-1C selection; the selection is recorded in CP-4C's limitation; a pin that differs from the selection is not an error. Task 4's `test_pin_wins_over_selection` asserts this.
- **Ruled Q5:** `methods/cp1c.md` and `methods/cp4c.md` are unchanged (outside B8 and B9); the staleness is listed for the user.
- **Ruled Q6 (B14):** `bindings/cp1c.py` gets a D12 record in the repo-authored shape: `imported_sha256` = `prior_project_sha256` = its sha256 at the commit before Task 1, `reason` beginning "repo-authored (not in files[])".
- **Ruled Q7:** the unplaced CP-1C tabs in a distressed report are accepted (a new block is outside B8).

## Not verified (to carry into each report)

No test, gate or probe run; the plan reads HEAD 28ad7934. Not exercised: the `auto` precedents branch end to end (no context supplies
precedents under `auto`); a live (model) CP-1C or CP-4C run over a context pack; the 44-file re-pin mechanics and that the swept tests stay green on the new preset (Task 1 runs them); CP-1 fact selection for adjusted EBITDA (confirmed at HEAD: `cp4c.py:417`, :1667 read `cp1["ebitda"]`); `validate_bindings`/`_unplaced` behaviour for Evidence bindings of table facts (assumed from
`bindings/__init__.py:21-23`); O7d's TDR.6 adapter; non-USD or non-2025 contexts (Phase 8); NTM multiples (a named gap).
