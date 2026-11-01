# Phase 6: Pinned assumptions Implementation Plan

**Status:** draft 2026-10-31 on `claude/context-plan-build` (28ad7934); not started. Phase row:
`docs/superpowers/plans/2026-10-31-context-file-consumption.md:329`; D4 (`:49`, settled: fail closed);
questions and rulings: `work/context-plan/reviews/phases-2-8-questions.md:88-96`; user ruling B9
(`docs/rulings/2026-10-31-context-plan.md`); Part B O6 Task 2 and Q4 (`docs/superpowers/plans/2026-10-31-part-b-o6.md:116,213`,
review `work/context-plan/reviews/o6-plan-review.md`). All `file:line` below are `git show HEAD:<file>`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** When a pack's `context` source pins an assumption for CP-2A, CP-2D, CP-2E, CP-3C, CP-3D or CP-4C,
that module's owner refuses a submission whose value differs from the pin (Decimal, after unit conversion;
an absence variant counts as differing) and labels a pinned value "user-supplied assumption". The pin also
enters the module's model prompt as O6's fenced `pinned-assumptions` block, switched on module by module.

**Architecture:** One new pure module `src/deploy_workflow/owners/pins.py` reads `context_facts(pack)`
(`context.py:733`), converts each module's `Assumptions` slice (`context.py:174-219`) to `Decimal` in the
submission's unit, and offers three things: `pin_issues(...)` (the comparison), `pinned_labels(...)` (which
fields are pinned, for the limitation line) and `submission_form(...)` (the exact strings O6 renders). Each
owner's `_validate_step` (cp2a `:1638`, cp2d `:2635`, cp2e `:1895`, cp3c `:2773`, cp3d `:2150`, cp4c `:2943`; the
validator the verifier replays and `ENTRY_VALIDATOR` exports) appends `pin_issues` after the content issues, and
each composer adds one limitation where it already states its "analyst assumption" line. The reader and form gain
a decimal-places limit per pin (ruling 3) so no pin is unsatisfiable. A pack without a `context` source, or whose
context has no pin for the module, behaves exactly as today.

## Global Constraints

- No stub or fake value standing in for real behaviour; no catch-all that hides a failure (a context the
  reader refuses surfaces as `ContextRefused` from `context_facts`, never as "no pin"); no network call; no key read.
- Python owns every figure: the pin is compared as `Decimal`; the model is told the value only as O6's data block.
- **`src/deploy_vii`: no change.** The questions file (`phases-2-8-questions.md:96`) says the "analyst assumption"
  wording in `methods/*.md` is avoidable by recording semantics in the leases; this plan takes that route (Task 9:
  a "Pinned assumptions" section in `docs/CP2A-OWNER-LEASE.md`, `CP2D`, `CP2E`, `CP3C`, `CP3D`, `CP4C`). B9's
  `methods/*.md` edit, its D12 `post_import_patches` record and `mx-feature` review are therefore **not used**. Why it
  is safe: the method files describe the submitted value's class (`analyst_judgment`, uncited), which a pinned value
  keeps (below); the model learns the pin from the prompt block, whose rule overrides (O6 rule O3, `part-b-o6.md:111`).
  Cost if wrong: a prompt reader sees "analyst assumption" beside a pin; the block's rule says to submit the pin.
- Fact labelling: a pinned submission field keeps `value_class="analyst_judgment"` and no citation (the context is
  never cited, O6 rule O3); the only new output is one limitation line per pinned item (Q-X, `phases-2-8-questions.md:12-14`).
- A pack without a `context` source behaves exactly as today: every frozen `cases/*-owner` oracle, `PINS.json` entry
  and module test stays green and unchanged (Task 10 runs them).
- Reports end `Not verified:` and list table, row and field changes (R7): this phase adds one limitation row to
  CP-2A `limitations`, CP-2D `T2E.7`, CP-2E limitations, CP-3C `T3D.8`, CP-3D own limitations and CP-4C limitations,
  for context packs with a pin only, and adds validator issue lines. Where limitation rows are tables whose rows become facts
  (T2E.7: `cp2d.py:1705-1711,2435-2441`; CP-3C limitation table T3D.8: `cp3c.py:1542,1738-1750,2600-2615`), the pinned row is
  appended **last** and `expected.json` lists its row and fact ids; no existing row or fact id moves. Also: CP-0 gains a `context` row
  for context packs (`readiness.py:341-344`, authority `unknown`).
- Tests: `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest <paths> -q`.
  Gates on changed files: `ruff check`, `ruff format --check`, `mypy`; the full suite once before hand-off (B3).
- Shared files (build in sequence, rebase on the tip first): `context.py` and the form are also edited by Phases 2
  and 3 (periods and quotes; this phase touches only `_Rules.number`, `_Rules.shocks`, `_num_message` and
  `assumptions_section`, `context.py:366-415,585-643,663-698`, and the form's `numMsg`/`asm` specs, `context-form.html:660,782-788`);
  `cp4c.py`, `cp3d.py`, `cp3c.py`, `cp2d.py` are also edited by Phases 7 and 8 (see "Left for Phases 7 and 8");
  `prompts/compose.py` is O6's (Task 9 edits one function there).

## What each pin binds (D4, ruling items 1, 3, 4)

Unit conversion happens in `pins.py`; the pin is compared with `Decimal(submitted) == pin` (trailing zeros do not matter).

| Module | Pin (`context.py`) | Submission field (unit) | Conversion | Differing includes | Pin precision limit |
|---|---|---|---|---|---|
| CP-2A | `cp2a.scenarios[i].ebitda_decline_pct`, `interest_increase_pct` (`:169-177`, percent 0-100) | `scenarios[i].ebitda_decline`, `interest_increase` (fraction, `DECLINE_PATTERN` `cp2a.py:77`, 4 dp) | `pct / 100` | a different count or order of scenarios (pins bind by position and count; 1 to 4 scenarios, `context.py:589-590`) | 2 dp |
| CP-2D | `horizon_months`, `minimum_cash_m` (`:179-182`) | `horizon_months` (int), `minimum_cash.amount` (US$ m, `cp2d.py:2603`) | none | `minimum_cash_absence` set (`cp2d.py:112-113`) | whole months; amount none |
| CP-2E | `rate_shocks_bps`, `fx_shocks_pct`, `hedge_ratio_pct` (`:185-189`) | `rate_shocks_bp`, `fx_shocks_percent` (strings; bounds `cp2e.py:542-543`), `hedge_ratio.percent_text` (`:539`) | none | different count or order of shocks; for a non-blank hedge pin, `hedge_absence` (`:1774`); a blank hedge pin binds nothing (partial pin) | rate whole; fx whole; hedge 2 dp |
| CP-3C | `repricing_bps` (`:192-194`) | `repricing.bps` (int, `cp3c.py:121-123`) | none | `repricing_absence` set (`:143-144`) | whole |
| CP-3D | `recovery_pct` (`:197-199`) | `recovery.percent_text` (`cp3d.py:760`, `_RECOVERY` 2 dp, `cp3d.py:193`) | none | `recovery_absence` set | 2 dp |
| CP-4C | `ev_multiple` (`:202-204`) | `valuation[i].multiple` for every case (`cp4c.py:137`, `MULTIPLE_PATTERN` 2 dp) | none | `"not assessed"` (`NOT_ASSESSED`, `cp4c.py:102`) in any case | 2 dp |

Ruling item 4 stands as found: CP-4C's pin binds every valuation case (so a pin forces equal multiples across
cases; the lease says so); CP-2A binds by order and count.

## Task 0: the oracle `cases/pins-context-owner/`

Prepared by a **preparer** who is not the builder of Tasks 1-9 (`docs/rulings/2026-10-31-context-plan.md` B2; AGENTS.md
"Module builds"), reviewed by an independent `mx-precise`, frozen and added to `cases/PINS.json` (`python3 -I cases/pins.py`;
the glob `cases/*-owner/*` takes `manifest.json`, `submissions.json`, `expected.json`, `builder/build.py`) before Task 1.
The preparer runs the product's table, claim and render validators and a scratch double rebuild and reports their exit codes.

**Inputs.** For each module, the closed chain and pack of its existing oracle's positive case plus one extra `text/plain` source `context` (the saved
`context.json`, layout of `cases/context/primary-full.json`). The base runs have four pathways (`cases/*-owner/manifest.json`): `distressed_restructuring`
(CP-2A, CP-4C), `covenant_refinancing` (CP-2D, CP-3C), `credit_snapshot` (CP-2E), `relative_value` (CP-3D); all `as_of` 2026-01-10, `case_kind` synthetic.
`context_facts` compares pathway, issuer, as-of and case kind with the run (`context.py:733-785`), so there is one file per base run:
`context-distressed_restructuring.json`, `context-covenant_refinancing.json`, `context-credit_snapshot.json`, `context-relative_value.json`, each pinning all six
modules (only the run's modules are read; Task 9 uses the file of the module under test: CP-3C -> covenant_refinancing). The context files are outside the
`PINS.json` globs (`cases/pins.py:20-30`), so `manifest.json` embeds each file's sha256.
**Pin values are each module's existing positive submission value** (probes in the review): CP-2A four scenarios decline/interest percent `20/0`, `40/0`, `40/20`,
`100/0` (fractions `0.20/0`, `0.40/0`, `0.40/0.20`, `1.00/0`); CP-2D `24` months and the positive `minimum_cash` (read from `submissions.json`); CP-2E rate `100, 200`,
fx `10`, hedge pin `""` (the base submits `hedge_absence`); CP-3C `400`; CP-3D `70`; CP-4C `4` (the base cases are `4.0`, `3.0`, `2.0`, so no frozen submission matches a pin). Two
extra match submissions are recomputed in the stdlib builder (never from code under test): CP-2E `hedge60` (context hedge pin `60`, `hedge_ratio` 60) and CP-4C `one_multiple`
(every case at `4.0`). The extra source changes the pack hash, so hash-bearing fields are rebuilt by the builder as in the existing builders; CP-0's own output gains the `context` row
and whatever limitation it adds (the preparer states both in `expected.json`); every module cell is otherwise unchanged.

**Expected values** (`expected.json`, per module `cases.<name>`):

| Case | Submission | Expected |
|---|---|---|
| `match` | the base positive submission, numbers respelled with other trailing zeros (`0.2000`, `70.00`, `400`, `24`); CP-2E `hedge60`, CP-4C `one_multiple` as above | no pin issue; tables, facts and claims equal the base positive case cell for cell (CP-2E `hedge60`, CP-4C `one_multiple`: builder-recomputed values); limitations = base plus one `pinned_lineS` sentence (`pinned_line`, Task 2), appended last, with its row and fact ids listed (T2E.7, T3D.8) |
| `differs` | each pinned field changed by the smallest step its precision allows (CP-2A first scenario `0.21`, CP-2D `25`, CP-2E rate `101`, CP-3C `401`, CP-3D `70.01`, CP-4C `4.01`) | refused with exactly `assumptions.<module>.<field>: pinned <pin as typed>; submitted <submitted>` (CP-2A: `pinned 0.2 (20%)`, units of the submission; CP-4C: `assumptions.cp4c.ev_multiple (valuation[i].multiple): pinned 4; submitted 3`), one line per differing field/case, listed after any content issues |
| `absence` | `minimum_cash_absence` / `repricing_absence` / `recovery_absence` / (CP-2E `hedge60` context) `hedge_absence` instead of the value | refused `... pinned <pin>; submitted absence` |
| `not_assessed` | CP-4C base `gap` case (third multiple `not assessed`) | refused `assumptions.cp4c.ev_multiple (valuation[2].multiple): pinned 4; submitted not assessed`, plus the `valuation[1]` line (the index keeps `dict.fromkeys` from merging) |
| `count_order` | CP-2A: scenarios 1 and 2 swapped; one scenario only; CP-2E: shocks `200, 100`, one shock | refused naming the count or the index and field |
| `blank_hedge` | CP-2E context hedge pin `""` (the base file), submission hedge `40`, and the base `hedge_absence` | both accepted; the sentence names shock sizes only |
| `non_numeric` | CP-2E `rate_shocks_bp ["abc"]`, CP-3D `percent_text "x"` | the content issue plus the pin mismatch as typed (`... submitted abc`); no exception. CP-4C `multiple "abc"` is refused at shape by `MULTIPLE_PATTERN` (cp4c.py:101) before any pin check: the case expects that shape issue only |
| `no_pin` | context present, module's pin `null` | base positive case unchanged, no extra line |
| `no_context` | the base pack | base positive case unchanged (`expected.json` of the existing oracle) |
| `multi_case` | CP-4C `one_multiple` with the second case at `4.5` | refused only for `valuation[1]` |
| `view` | `read_inputs` view of each module with a context pack | unchanged (a pin is not an input; the prompt carries it) |

`prompt` cases (Task 9): `submission_form` strings from the same pins (normalised, no exponent, `format(d.normalize(), "f")`): CP-2A scenarios `0.2/0`, `0.4/0`, `0.4/0.2`, `1/0`; CP-2D `24`, minimum cash; CP-2E `["100","200"]`, `["10"]`; CP-3C `400`; CP-3D `70`; CP-4C `4`.

Pins that change: none. Oracles that change: none. New pins: the new case's files and builder. Preparer ≠ builder ≠ reviewer; ids in the ledger.

## Task 1: reader and form limit each pin to its submission's precision [mx-feature]

**Files:** modify `src/deploy_workflow/context.py`, `docs/templates/context-form.html`; test `tests/product/test_context.py`
(next to `test_form_rules_refused` `:552` and `test_form_regexes_match_reader` `:573`).

**Behaviour.** `_Rules.number` (`context.py:373`) and `_num_message` (`:663`) gain `places: int | None`; a value with more
decimal places is refused `use at most <n> decimal places.` Applied in `assumptions_section` (`:585-643`): `cp2a` decline and interest
`places=2`; `cp2d.horizon_months` already `whole` (`:606-612`); `cp2e.rate_shocks_bps` whole (`:618`, unchanged), `fx_shocks_pct` becomes
whole (today `False`, `:619`; the submission takes a whole percent, `cp2e.py:543-544`, lease `CP2E-OWNER-LEASE.md:120`), `hedge_ratio_pct` (`:620`)
`places=2` (`cp2e.py:539`); `cp3c.repricing_bps` becomes `whole=True` (today any decimal, `:624`; `StepUp.bps` is an int, `cp3c.py:123`);
`cp3d.recovery_pct` `places=2` (`cp3d.py:193`); `cp4c.ev_multiple` `places=2`. `shocks()` (`:414`) also refuses duplicate or non-increasing
lists (the owner already requires strictly increasing shocks, `cp2e.py:728-729`; the reader must match so a pin is satisfiable): `"<item>": values must increase.`
The form's `numMsg` (`context-form.html:660`) gets `r.dp` and `readSpec`/`asm` specs (`:782-788`) the same limits; the `t:'list'` branch of `fld` (`:690`) gets the strictly-increasing check (today only each item is checked); help texts (`:370-397`) name them.

- [ ] **RED** (all fail today): (a) `assumptions.cp2a.scenarios[0].ebitda_decline_pct = "20.123"` -> refused `assumptions.cp2a.scenarios[0].ebitda_decline_pct: use at most 2 decimal places.`;
  `"20.12"` loads. (b) `cp3c.repricing_bps "50.5"` -> `enter a whole number.`; `"50"` loads. (c) `cp2e.fx_shocks_pct ["10.5"]` -> `"10.5": enter a whole number.`
  (d) `cp2e.rate_shocks_bps ["200","100"]` and `["100","100"]` -> `...: values must increase.`; `["100","200"]` loads. (e) `cp3d.recovery_pct "65.123"`, `cp4c.ev_multiple "8.555"`, `hedge_ratio_pct "60.123"` each refused with the 2 dp text; `"65.12"`, `"8.55"`, `"60.12"` load.
  (f) `test_form_regexes_match_reader` extended: the form's `dp` literals equal the reader's; the saved fixtures `cases/context/primary-full.json`, `research-minimal.json` still load (they satisfy every new rule).
- [ ] Implement; run `tests/product/test_context.py tests/product/test_context_pack.py -q`; gates. Commit `feat(context): limit each pinned assumption to its submission's precision`.

## Task 2: the pin module `owners/pins.py` [sensitive: figures, mx-adversary]

**Files:** create `src/deploy_workflow/owners/pins.py`; test `tests/test_pins.py` (incl. a `hypothesis` property).

**Interface.**
```python
def pins_of(module_id: str, pack: PreparedPack) -> Mapping[str, Decimal | tuple[Decimal, ...]] | None
    # None when context_facts(pack) is None or the module's pin is None; keys are the context paths
def submission_form(module_id: str, pack: PreparedPack) -> Mapping[str, JsonValue] | None   # O6's body; keys are submission paths
    # CP-2A {"scenarios": [{"ebitda_decline": "0.2", "interest_increase": "0"}, ...]}, CP-2D {"horizon_months", "minimum_cash.amount"},
    # CP-2E {"rate_shocks_bp": [...], "fx_shocks_percent": [...], "hedge_ratio.percent_text"}, CP-3C {"repricing.bps"},
    # CP-3D {"recovery.percent_text"}, CP-4C {"valuation[*].multiple"}
def mismatch(path: str, pinned_as_typed: str, submitted: str | None, *, at: str = "") -> str
    # `<path>[ (<at>)]: pinned <pin>; submitted <value|absence>`
def pinned_line(module_id: str, *, hedge_pinned: bool = False) -> str   # one finished sentence per module:
    # CP-2A "Scenario shock sizes are user-supplied assumptions pinned in the context file; the submission equals the pins."
    # CP-2D "The horizon and minimum cash are ..."; CP-2E "The shock sizes[ and hedge ratio] are ..."; CP-3C "The margin step-up is a user-supplied assumption pinned ... equals the pin."; CP-3D "The recovery rate is ..."; CP-4C "The EV multiple is ..."
```
`module_id` in `{"CP-2A","CP-2D","CP-2E","CP-3C","CP-3D","CP-4C"}`; any other raises `KeyError` naming it. `pins_of` reuses `context_facts` so a context
that differs from the run raises `ContextRefused` (`context.py:733-785`): not caught (the step validator surfaces it as a validator issue in each owner, Tasks 3-8).
`mismatch` formats the line with `submitted` clipped (`clipped` from `deploy_vii.execution`, as `cp2a.py:60`).
Percent -> fraction only for CP-2A (`Decimal(pct) / Decimal(100)` under `Context(prec=60)`, exact for 2 dp); its mismatch line shows the pin in the submission's units with the typed percent (`pinned 0.2 (20%)`). `submission_form` rounds nothing. **Submitted values may be junk** (plain `str` fields: `cp2e.py:1751,1775-1776`, `cp3d.py:130`, `cp4c.py` `multiple`): a submitted string is converted to `Decimal` only after a `context.NUM` full match (`context.py:34`); otherwise the line is emitted with the text as typed, never an exception.

- [ ] **RED**: (1) no `context` source -> `pins_of(..) is None` for all six ids; context with `assumptions.cp3c = null` -> `None` for CP-3C, a value for the others pinned. (2) CP-2A `("20","10")` -> `(Decimal("0.2"), Decimal("0.1"))`. (3) `submission_form` of `cases/context/primary-full.json` values: CP-4C `{"valuation[*].multiple": "8.5"}`, CP-2E `{"fx_shocks_percent": ["10"], "hedge_ratio.percent_text": "60", "rate_shocks_bp": ["100","200"]}`, CP-2A a list of dicts; `"100"` -> `"100"` (not `1E+2`), `"0"` -> `"0"`. (4) `mismatch("assumptions.cp3c.repricing_bps","400","401")` == `assumptions.cp3c.repricing_bps: pinned 400; submitted 401`; with `None` -> `... submitted absence`; with `at="valuation[1].multiple"` the text `(valuation[1].multiple)` follows the path. (4b) a junk submitted value (`"abc"`, `"1e5"`, `""`) is compared as typed and does not raise. (4c) `pinned_line` of each module ends with a full stop, agrees in number, and CP-2E names the hedge only when `hedge_pinned`. (5) a context whose `as_of` differs from the pack run raises `ContextRefused`. (6) property: for `d` in a 2-dp decimal strategy, `Decimal(submission_form(d)) == d` and the compare is unaffected by trailing zeros. (7) unknown module id -> `KeyError`.
- [ ] Implement; `tests/test_pins.py -q`; gates. Commit `feat(owners): pinned-assumption reader and comparison`.

## Tasks 3-8: one module each [sensitive: figures, mx-adversary on each diff]

Same shape per module: **Files** `src/deploy_workflow/owners/<m>.py`; test `tests/test_owner_<m>_pins.py` using the Task 0 case. Behaviour: in `_validate_step`
(cited above) after the content issues, `issues = (*content, *pin_issues(pack, submission))`, deduped with `dict.fromkeys` as the validators do. **The composer gate too:** each report function raises on its own issue set (cp2a `downside_report :1586-1592` calls `validate_downside`, not `_validate_step`), so the pin issues are added to that gate as well (one private `_issues(pack, submission, upstream)` per module used by both); RED asserts the composer raises `ValueError` on a differing pin; a
`ContextRefused` becomes the single issue `Context refused: <message>` (the `context_facts` text, as Phase 4 `context_mismatch`). The composer
(function names below) takes `pinned: bool` from `pins_of(...) is not None` and, where it states its assumption line, appends `pinned_line` (appended last; text from `pinned_line(module, hedge_pinned=…)`; where the limitation is a table row it is a new last row and fact, ids in `expected.json`). `downside_report`, `liquidity_bridge`, `macro_fx`, `refinancing_risk`, `market_implied`, `restructuring`
(`restructuring_report` if that is the name at the tip) all rebuild from `pack`, so the verifier's replay reproduces the line.

- [ ] **RED, from Task 0 `expected.json` (all fail today; each also asserts the no-context and no-pin cases stay equal to the base oracle):**

| Task | Module, entry | Concrete RED (pin -> submission -> expected) |
|---|---|---|
| 3 | CP-2A `validate_downside` call site `cp2a.py:1577`, `_validate_step :1638`; limitation beside `ANALYST_SHOCKS :773` and the `limits` list `:1353` | pins as Task 0 (four scenarios) -> first decline `0.21` -> `assumptions.cp2a.scenarios[0].ebitda_decline_pct: pinned 0.2 (20%); submitted 0.21`; one scenario only -> `assumptions.cp2a.scenarios: pinned 4 scenarios; submitted 1`; scenarios 1-2 swapped -> two index lines; base spelled `0.2000` accepted; the base-period issue alone still carries the pin line (Decision 1); limitations gain `pinned_line("CP-2A")` |
| 4 | CP-2D `validate_liquidity_bridge :2226`, `_validate_step :2635`; limitation beside `MINIMUM_CASH_ASSUMED :849` (T2E.7 row, ledger `:1666`) | pins 24, <positive minimum cash> -> horizon 12 -> `assumptions.cp2d.horizon_months: pinned 24; submitted 12`; a different `minimum_cash` -> `...minimum_cash_m: pinned <pin>; submitted <value>`; `minimum_cash_absence` -> `... submitted absence`; the positive minimum cash spelled `"10.0"` accepted (the horizon stays `24`: `Contract` is strict, contracts.py:76, so JSON `24.0` for an int is a shape refusal); T2E.7 gains the pinned row last (fact ids in `expected.json`) |
| 5 | CP-2E `validate_macro_fx :826`, `_validate_step :1895`; limitation with the shock sentence | pins rate 100,200 / fx 10 -> rate `100,300` -> `assumptions.cp2e.rate_shocks_bps: pinned 100, 200; submitted 100, 300`; fx `["10","20"]` -> count line; junk `["abc"]` -> as typed, no exception; in the `hedge60` context hedge `61` -> hedge line, `hedge_absence` -> absence line; hedge pin `""` leaves hedge free |
| 6 | CP-3C `validate_refinancing :2513`, `_validate_step :2773`; limitation beside `_MINIMUM_CASH`/`_STEP_UP :1568-1592` and T3D.7 `:1823` | pin 400 -> `repricing.bps` 401 -> `assumptions.cp3c.repricing_bps: pinned 400; submitted 401`; `repricing_absence` -> absence line; 400 accepted, T3D.7 step-up row (`:1823`) reads `400 (analyst assumption)` unchanged, T3D.8 gains the pinned row last |
| 7 | CP-3D `validate_market_implied`, `_validate_step :2150`; limitation in `own_limitations :1672` beside `:1691` | pin 70 -> `recovery.percent_text` `71` -> `assumptions.cp3d.recovery_pct: pinned 70; submitted 71`; `recovery_absence` -> absence line; junk `x` -> as typed; `70.00` accepted; T3D recovery row label (`:1470`) unchanged |
| 8 | CP-4C `validate_restructuring`, `_validate_step :2943`; limitation beside `VAL_LIMIT :2270` and `:1489` | pin 4 -> the base positive (`4.0`, `3.0`, `2.0`) -> `assumptions.cp4c.ev_multiple (valuation[1].multiple): pinned 4; submitted 3.0` and `(valuation[2].multiple)` ... `2.0`; base `gap` -> `not assessed` line; `one_multiple` at `4.00` accepted. **Precedence (controller ruling, Phase 7 Q4):** when the pin is set it wins over any CP-1C-selected multiple; the pin check runs on the submitted multiples whatever the prompt or view offered, and a code comment states it; the RED with an offered multiple (refused even when an offered multiple equals the submission) belongs to Phase 7, since nothing offers a multiple before it. Phase 7 records the selection in CP-4C's limitation |

- [ ] Implement; run the module's new test, the module's existing `tests/test_owner_<m>.py` and `tests/test_connect_<m>.py` (where one exists), and `tests/test_pins.py`;
  gates. Commit one per task: `feat(<m>): refuse a submission that differs from the context pin; label it user-supplied`.
- Ordering inside the phase: Task 4 (CP-2D) before Task 6 (CP-3C) in review only (CP-3C reads CP-2D's minimum cash, `cp3c.py:1429`); no code dependency.
  Task 3 reuses `owners/blank.py` helpers already imported (`cp2a.py:70`); no new import cycle (`pins.py` imports `deploy_workflow.context`, `deploy_vii.preparation` and `clipped` from `deploy_vii.execution`, `cp2a.py:60`, only).

## Task 9: switch the prompt block on, module by module [sensitive: security, mx-adversary]

**Depends on** O6 Task 2 (`PINS_ENABLED: frozenset[str]` and the `pinned-assumptions` `data_block`, `part-b-o6.md:116`) being in the tree. Until then Tasks 0-8 and 10 stand alone; if O6 is not built, this task waits and Phase 6 reports "built, prompt switch pending".

**Files:** modify `src/deploy_workflow/prompts/compose.py` (the pin-block builder calls `pins.submission_form`; `PINS_ENABLED` gains ids);
tests `tests/prompts/test_pinned_block.py`.

**The switch.** `PINS_ENABLED` (O6, keyed by module id) gains one id per commit, **after that module's Task 3-8 gate is green**: one commit per module, never a batch. There is no
hand-kept second list. The guard test (`tests/prompts/test_pinned_block.py::test_enabled_modules_check_their_pin`) runs, for every id in `PINS_ENABLED`, that module's `ENTRY_VALIDATOR` on the Task 0 `differs` case and
asserts the output holds an `assumptions.<module>.` line, so no prompt invites a pin the owner does not check; at the end of Phase 6 it also asserts `PINS_ENABLED` equals all six ids.

- [ ] **RED**: (1) with `PINS_ENABLED = {"CP-3C"}` and the `context-covenant_refinancing.json` pack, the CP-3C prompt holds exactly one fenced block `<<<CONTEXT id=pinned-assumptions sha256=...>>>` whose JSON body is `{"repricing.bps": "400"}` and the exact-value rule; the CP-3D and CP-2A prompts hold none. (2) With the module enabled and the pin `null` (or no context) no block. (3) The block holds no rationale (`context.json` rationales contain a sentinel, absent from every message), no other module's pin, and the CP-2A body is `{"scenarios": [{"ebitda_decline": "0.2", "interest_increase": "0"}, ...]}` (submission paths and fractions). (4) Values are `Decimal` strings, so no pin can forge a delimiter: `submission_form` leaves match `^[0-9]+(\.[0-9]+)?$`. (5) An id in `PINS_ENABLED` whose owner does not emit the line -> the guard fails (test with a stub owner id added in the test only). (6) A module not enabled: its prompt hash equals O6's un-pinned prompt hash. (7) Sentinel `rationale` text and `os.environ` untouched (O6's no-leak test still green).
- [ ] Commits: `feat(prompts): pinned-assumptions block reads owners.pins` then `feat(prompts): enable the pinned-assumptions block for CP-2A` ... six, in the order of Tasks 3-8.

## Task 10: leases, regression and Done-when [docs + gates; mx-feature review]

**Files:** `docs/CP2A-OWNER-LEASE.md`, `docs/CP2D-OWNER-LEASE.md`, `docs/CP2E-OWNER-LEASE.md`, `docs/CP3C-OWNER-LEASE.md`, `docs/CP3D-OWNER-LEASE.md`, `docs/CP4C-OWNER-LEASE.md`
(each a new section "Pinned assumptions (Phase 6)"; the leases are referenced by tests only as docstring text, `tests/test_owner_cp3c.py:1`, not hashed). This is the B9 alternative: it records, per module:
1. the pin and the unit conversion (the table above); 2. fail-closed comparison and its issue wording; 3. "analyst assumption" in `src/deploy_vii/methods/<m>.md` and in `value_class="analyst_judgment"` means *uncited and not a source figure*; a pinned value is such a
   value the user supplied, labelled by the added limitation; 4. the count/order rule (CP-2A, CP-2E) and CP-4C's every-case rule; 5. the blank hedge pin; 6. the prompt switch.
No frozen-lease text is edited; the section is appended below the freeze note, dated, with the user-ruling reference.
- [ ] Run the regression and Done-when set (below), `python3 -I cases/pins.py --check` (exit 0), and the full suite once. Commit `docs: record pinned-assumption semantics in the six leases (Phase 6)`.
- **Review assignment.** Task 0 oracle: independent `mx-precise` (+ `mx-adversary`: figures). Tasks 1 and 10: `mx-feature`. Tasks 2-8: `mx-precise` per task and `mx-adversary` (figures); Task 9: `mx-adversary` (prompt boundary). Whole-phase: `mx-architect`.

## Done when (restated as tests)

| Phase row text | Test |
|---|---|
| Each module refuses a differing submission | `tests/test_owner_<m>_pins.py::test_differs_refused`, `::test_absence_refused` for the six modules (Task 0 `differs`, `absence`, `not_assessed`, `count_order`, `multi_case`) |
| ... and labels a pinned value | `::test_match_adds_user_supplied_limitation`; limitation text equals `pinned_line(<module>)`; value class still `analyst_judgment` |
| D4: Decimal after unit conversion | `tests/test_pins.py` (2), (6); CP-2A `0.2000` equals pin 20 |
| An absence variant counts as differing | `absence` cases (CP-2D `cp2d.py:112-113`, CP-3C `:143-144`, CP-3D, CP-2E `:1774`), `not_assessed` (CP-4C `:102`) |
| A pack without a pin behaves as today | `no_context`, `no_pin` cases; all `cases/*-owner` oracles and the existing module tests green; `python3 -I cases/pins.py --check` exit 0 |
| Pin limited to submission precision | Task 1 RED (a)-(e); every Task 0 pin is satisfiable by a valid submission |
| Prompt carries the pin per module | Task 9 RED (1)-(6); the guard test, `PINS_ENABLED` == all six ids after the last switch commit |

Regression set: `tests/product/test_context*.py`, `tests/test_pins.py`, the six `tests/test_owner_<m>*.py`/`tests/test_connect_<m>.py`, `tests/prompts`, then the full suite.

## Left for Phases 7 and 8 (shared files)

- **`cp4c.py` (Phase 7):** a pinned `ev_multiple` is authoritative and **wins over CP-1C's selected multiple** (ruling): the owner refuses a differing submitted multiple whatever Phase 7's basis selection (CP-1C range, `user_multiple`, `auto`) offers; Phase 7 decides what the prompt/view offers only when there is no pin, and records the selection (and that a pin overrode it) in CP-4C's limitation. Phase 6 does not read `Valuation` (`context.py:160`) and adds nothing to the CP-4C view. Left: `_issues`/`pin_issues` is one function; Phase 7 does not edit it. Phase 7 changes `methodology.json` and the distressed preset (B8), which re-pins `PINS.json` and may change CP-4C's upstream chain: Phase 7 re-pins this phase's `cases/pins-context-owner/` CP-4C and CP-2A files and rebuilds them (the new case is in the `cases/*-owner/*` glob).
- **`cp4c.py` (Phase 8):** Phase 6's limitation text avoids any period or currency word, so the replacement of `_PINNED_COLUMN` (`cp4c.py:1391`) and the period constants (`cp4c.py:414-417`; there is no `BASE_YEAR` in `cp4c.py`) does not touch it. The multiple is dimensionless; no currency conversion.
- **`cp2d.py` (Phase 8):** `minimum_cash_m` is compared as US$ m (`CURRENCY = "USD"`, `cp2d.py:70`, bounds `:2603`). Phase 8 replaces the constant with the context's `reporting_currency`; its currency-equality refusal must run before `pin_issues`, and `pinned_line` must not say "US$". Left: the unit label in the `minimum_cash` issue is `m` (millions of the reporting currency).
- **`cp3c.py`, `cp3d.py` (Phase 8; `cp3d` also Phase 3 market evidence):** Phase 6 touches only `_validate_step` (`cp3c.py:2773`, `cp3d.py:2150`), one limitation helper each, and nothing in the period or quote paths. Phase 3's market-evidence change to `cp3d_upstream` and Phase 8's period changes do not overlap those functions; if either rewrites `_validate_step`, it keeps the `pin_issues` call (guarded by Task 3-8 tests).
- **`context.py`/form (Phases 2, 3):** Phase 6 leaves the `Valuation`, `quotes`, `ratings` and period sections untouched; its `places` parameter is available to them.
- **`pins.py` (all):** other phases may add module ids only through `pins_of`; a new pinned module also needs a Task 9-style switch and a `differs` case for the guard test.

## Decisions (ruled in `work/context-plan/reviews/phase-6-plan-review.md`; no open questions)

1. **Ruled: pin issues are appended even where a validator returns alone** (CP-2A base period, `cp2a.py:679`; CP-3C staleness/provenance, `cp3c.py:2519-2527`), so one repair round fixes both.
2. **Ruled: CP-2D `minimum_cash_m` has no decimal limit** (`amount: Decimal`, `cp2d.py:69-72`); Task 2 (6) covers it.
3. **Ruled: `PINS_ENABLED` is keyed by module id** (`MODULE_ID`, e.g. `CP-3C`).

## Not verified (plan level)

No code or tests were run; line numbers are from `git show HEAD:`, and the working tree carries uncommitted edits to `owner_workflow.py` and an untracked `owners/cp6.py`. Not read: the Task 0 values `minimum_cash` (CP-2D) and CP-3C `repricing.bps` 400 / CP-3D 70 were taken from the review's probes, not re-run; the oracle builders' hash chain (so the claim that only hash fields change in the extra-source pack is an assumption); the exact composer function names for CP-3D and CP-4C limitations; `methods/*.md` prompt use by O6; the form's behaviour in a browser; whether `value_class` should instead become `source` for a pinned field (Q-X would label context figures that way; this plan keeps `analyst_judgment` because the owner's output cites no context line).
