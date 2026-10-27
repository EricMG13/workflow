# Owner harness architecture study

Read-only `mx-autonomous` (Opus 5.5) report to LEAD, 2026-10-27, saved by LEAD.
LEAD decisions on its questions are in `docs/OWNER-WORKFLOW-LEASE.md`.

## 1. Why the bespoke adapters are large

The per-owner bloat is not analytical code.

- Each re-drives the CP-0/CP-1 foundation: `earnings_workflow.py:803-1186` copies
  `financial_workflow.py:251-469` (`_binding`, `_historical`, `_projection`,
  `_filled`, `_evidence_issues`, `_column_periods`).
- Each writes its own receipt, verifier, transcript, inventory and JSON-lines
  server (earnings 2818-3279, 3808+; integrity 1110-1665, 1665+), crash-recovery
  intents (earnings 2096-2440), case pins in product code (earnings 576-586) and
  duplicated helpers (`_hash`, `_put`, `_audit`, `_snapshot`, `_FrozenExecution`).
- Owner composition sits inside the adapter (`_compose`, earnings 1665-1916).

## 2. What the core already makes uniform

- One-step cores share a shape: submission schema, `xx_upstream(store, attempt)`,
  validator, Python composer, `xx_module(report, inputs, number)`,
  `submit_xx_step(store, ticket, step, payload) -> Attempt` (`cp2_synthesis.py:923-956`).
- `submit_model_payload` dispatches CP-1A, CP-2, CP-3, CP-4, CP-5 and CP-6 with tool
  rules (`live/submission.py:265-283`, `:941-986`).
- `module_context` is the typed upstream view for CP-2/3/4/6 (`live/context.py:94-116`),
  `integrity_scope` for CP-5 (`:181`); source scope is `declared_sources`/
  `readable_sources` (`:127-151`).
- Rendering is generic: `store.view()` (`execution.py:884`), `render`
  (`render.py:127`), `SHIPPED_MAPS` (`bindings/shipped.py:15`).

## 3. Seams to fix before owners beyond CP-1

1. **Source host provenance (H1).** `host.py:33-37` accepts a non-CP-0 producer only
   if `producer.inputs == current_inputs(producer)`, but every one-step core appends a
   `*-submission` tail (CP-1A `business_context.py:1789`, CP-2 `cp2_synthesis.py:897-901`,
   CP-3 `:1162-1166`, CP-4 `:1492`, CP-5 `:1242`, CP-6 `:1347`) and CP-1 four promotion
   tails. Fix: require a unique finished issue-free attempt whose `result_sha256` equals
   the producer hash with `producer.inputs[:n] == attempt.inputs == current_inputs`,
   then re-run `settle` on the retained payload (`host.py:62-70`); add `_SOURCE_STEPS`
   entries (`host.py:18`) per pack-source owner.
2. **Offline-only steps and tool rules.** `ToolRules` reads `STEPS[step].schema`
   (`live/tools.py:1057`, `:1122`) and `STEPS` refuses offline-only steps
   (`submission.py:218-221`); new pack-source owners call `unread_citation_issues`
   (`tools.py:1101`) directly with declared absence markers.
3. **`UpstreamTools` is CP-1-producer-only** (`upstream.py:23`, `:114`, `:375`);
   multi-producer lookup needs an additive versioned grant after A4 releases the file.
   Optional under decision D2.

## 4. Owners with no core implementation

Registry run chains exist only for CP-0, CP-1, CP-1B (partial; pure core in
`deploy_workflow/earnings.py`), CP-1A, CP-2, CP-4, CP-3, CP-5 and CP-6
(`registry.py:282-378`). CP-3B/CP-6A are aliases only: `canonical()` maps them to
CP-3/CP-6 (`registry.py:45-49`).

| Owner | Python (Decimal) | Analyst judgment | Edges (methodology) | Section |
|---|---|---|---|---|
| CP-1C peer | normalised peer metrics, medians, outliers | universe, comparability | req CP-0, CP-1 | FP03 peer-positioning |
| CP-1D quality | adjusted-EBITDA bridge, add-back share, CFO/EBITDA, restated leverage | add-back achievability/recurrence | req CP-0, CP-1; opt CP-1B | FP02 quality/full analysis |
| CP-2A downside | stressed EBITDA/FCF/leverage/coverage, break points | scenario, shock size | req CP-0, CP-1 | FP05 downside (no block yet) |
| CP-2D liquidity | sources/uses, runway, maturity wall (T4.18), RCF availability | horizon, minimum cash | req CP-0, CP-1, CP-2 | FP04/05 liquidity-runway, maturity-wall, funding-gap |
| CP-2E macro/FX | FX/rate shock arithmetic | exposures, hedging | req CP-0 | full analysis |
| CP-2G forward | EBITDA/FCF/net debt/leverage path | assumptions, guidance | req CP-0, CP-1, CP-2A; opt CP-1D, CP-2D | forward/scenario (no block yet) |
| CP-2H ratings | trigger headroom on CP-2G | ratings, thresholds, migration view | req CP-0, CP-1, CP-2G; opt CP-1D | FP05 rating-triggers |
| CP-3B fit | sizing against limits | mandate fit | alias only | FP01/05/06 portfolio-fit |
| CP-3C refi/LME | refinancing need/cost, LME capacity from CP-4 | path, LME likelihood | req CP-0, CP-1, CP-2D; opt CP-1A, CP-2A, CP-4, CP-3D | FP04 refinancing-paths, lme-creditor-exposure |
| CP-3D market | spread/yield, implied default probability | technicals | req CP-0; opt CP-2H | FP03 instrument-levels, market-against-fundamentals |
| CP-4C fulcrum | waterfall by class, recovery %, fulcrum | EV multiple, distressed EBITDA | req CP-0, CP-1, CP-2G, CP-4, CP-2A; opt CP-3C | FP05 recovery-by-class, value-allocation-claims |
| CP-6A recommendation | sizing | portfolio call | alias only | FP06 portfolio-recommendation, instrument-decision |
| CP-8 ledger | diff against prior decision record | post-mortem | req CP-0; opt CP-6 (block) | what-changed (`report_view.py:1099`) |
| CP-DR research | gap-status bookkeeping | cited answers from local sources | req CP-0 | evidence rail |
| CP-L10 screen | screening thresholds | flag synthesis | req CP-0 | screening (no block) |
| CP-OS nav | reuse `report_view.navigator` (`:840`) | none | exempt (`execution.py:259`, `registry.py:25`) | navigation |

Minimum new core per owner (~300-600 lines, `src/deploy_workflow/owners/<cp>.py`):
reference/judgment-only schema, upstream reader, validator, Decimal composer keeping
zero/missing/blocked distinct (reuse `model/debt.py`, `model/metrics.py`,
`facility_fx.py`, `cp4_legal.headroom` `:334`), `xx_module`, and a `submit` on a
shared helper copying the `cp2_synthesis.py:923-956` pattern.

Consumers: CP-5 consumes every selected analyst (`registry.py:67-69`;
`cp5_integrity.py:277-323`). Named consumers often do not read optional producers:
CP-3 never reads CP-3C/3D/4C/2D (`cp3_relative_value.py:99-104`); CP-2 reads only
CP-1 and CP-1A (`cp2_synthesis.py:339-359`).

## 5. Slice sequence

- Phase 0 (in flight): C3 B1, C1 A4, C1 L2, C2 D1.
- Phase 1: G1 `owner_workflow.py` (critical path; equivalence on CP-0/CP-1/CP-MODEL plus
  refusals), then H1 in `host.py` after L2; G2 `owner_rendering.py`; C3 CP-1D pure core
  after B1.
- Phase 2, S1 credit snapshot: S1a CP-0 → CP-1 → CP-MODEL → CP-1A → CP-2 rendering FP01
  key-findings, company-operating-model, company-profile, strengths-weaknesses,
  Evidence, Limitations; S1b adds CP-5 after A4. S2 adds CP-4 (after L2), CP-3 (after
  H1) and CP-6.
- Parallel lanes: C1 snapshot then CP-3D, CP-2E, CP-L10, later CP-3B/6A/8 (FP06); C2
  covenant FP04 (CP-4 spec, CP-2D → CP-3C), CP-OS, CP-DR and FP03/05/06 block specs
  (missing today, `report_view.py:1179-1184`); C3 FP02 (CP-1D) then CP-1C; a fourth
  lane for distressed FP05 (CP-2A → CP-2G → CP-2H → CP-4C), the longest pole.
- Critical path: G1 freeze → L2 integrated → G1 → H1 → S1a run → A4 integrated → S1b →
  G2 FP01 delivery. Shared one-line registrations are serialised by PM.

## 6. Questions for LEAD

D1 CP-3B/CP-6A distinct vs alias; D2 `read_inputs` as tool use; D3 what counts as
consumption; D4 CP-1 edges for CP-2E/CP-L10; D5 CP-8 prior report offline; D6 CP-OS
head or render proof; D7 unowned blocks; D8 table-id collisions (CP-1C T4.1-T4.11,
CP-2A T5.1-T5.7); D9 per-owner source grants (CP-1A reads all sources by fallback,
`context.py:85-87`); D10 paging and resume; D11 uncited assumptions; D12 code location
and registrations.

Not verified: no code was run; replay determinism per owner entry, reuse of CP5-v2
cursor verification outside `integrity_workflow.py`, and sufficiency of H1's settle
replay are unchecked; line estimates are guesses; WIP files were skimmed unintegrated.
