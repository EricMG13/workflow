# Generic owner rendering (G2) lease — rev 1, FROZEN by LEAD 2026-10-28

Read-only draft, 2026-10-27. It is pre-code: implementation starts only after independent review, LEAD freeze and PM integration.

## Why

`financial_rendering.py` and D1's `earnings_rendering.py` each authenticate one bespoke receipt and fix their scope by hand. G2 renders any verified G1 `OwnerRunReceipt` through the unchanged core: `store.view()` (`execution.py:884`), `render` (`render.py:141`), `build` and `SHIPPED_MAPS`. Its first scope is S1a FP01.

## Prerequisites (G2 code waits for these; drafting does not)

1. **G1 integrated.** This gives the public `OwnerRunReceipt` and `verify_owner_run_receipt`.
2. **S1a extends G1.** Today G1 supports only CP-0 and CP-1 (`owner_workflow.py:75`). Its probes are keyed on CP-0 and CP-1 (`:79-82`) and the verifier indexes them with `_PROBES[head.module_id]` (`:1172`), so a CP-1A head fails verification. The S1a lease must add the CP-1A and CP-2 specs and their probes.
3. **The S1 oracle is adopted.** `cases/snapshot/` is untracked, and `manifest.json` still says "DRAFT … not adopted".
4. **A G1 fix is needed before S1b.** `plan(... + CP-5)` gives `CP-0, CP-1, CP-1A, CP-2, CP-MODEL, CP-5` (I checked this). G1's `_check_specs` refuses an analytical module that comes after a deterministic one (`owner_workflow.py:310-325`). G2 itself needs only a scope row for S1b.

## Files

- New only: `src/deploy_workflow/owner_rendering.py` and `tests/test_owner_rendering.py`.
- Import and never edit: `owner_workflow.py`, `financial_workflow.py`, `financial_rendering.py`, `src/deploy_vii`.
- No new rendering code is needed. The FP01 composition (`report_view.py:1066-1100`) and the CP-1A and CP-2 binding maps (`bindings/shipped.py:15`) already exist.
- D1 is held unintegrated, so G2 re-implements its mechanisms and does not import it.

## Consumes

- The store directory and the exact G1 receipt bytes. G1 writes `model_dump_json()` bytes (`owner_workflow.py:785`).
- The publication directory, if and only if `receipt.model` is set.
- Authentication is only the producer's own work: `OwnerRunReceipt.model_validate_json` followed by `verify_owner_run_receipt(store, receipt, publication_directory=…)`. That checks the seal, audit, begins, walk, probes and publication. There is no local replay and no substitute schema.

## Public API

```python
DeliveryScope(scope_id, pathway, requested_modules, case_kind, sections, rails, banner)
DELIVERY_SCOPES: Mapping[str, DeliveryScope]   # "s1a-credit-snapshot" (+ "cp1-model", Q2)
OwnerHeadResult(module_id, result_sha256, status, qualification)
OwnerBoundFact(module_id, result_sha256, table_id, row_id, fact_id, fact_sha256)
OwnerSectionProof(block_id, state, block_sha256, facts: tuple[OwnerBoundFact, ...])
OwnerRailProof(destination: Literal["evidence","limitations"], facts, limitations)
OwnerRenderReceipt(schema_version="owner-slice-render/1", scope_id, run, pack_sha256,
    snapshot_sha256, outcome: Literal["complete","refused"], owner_receipt_file="owner-run.json",
    owner_receipt_file_sha256, owner_receipt_content_sha256, head_results, model,
    sections, rails, files).from_wire(raw)
render_owner_slice(execution_directory, receipt_path, publication_directory, destination) -> Path
verify_owner_rendered_slice(execution_directory, receipt_path, publication_directory,
    delivery_directory) -> None
```

The scope is derived from the receipt and is never a caller argument. Exactly one scope must equal the run's `(pathway, requested_modules, case_kind)`; otherwise G2 refuses.

## Behaviour

**Capture.** This step runs at entry, after rendering, after staging, before the rename and after the rename.

- Strict-parse the raw bytes. Then require canonical spelling: number text is compared type-tagged (D1 F3 + N1) and only whitespace or escape spelling may differ.
- Run the G1 verifier.
- Require that the snapshot hash, pack, run and ordered heads (with their qualification) equal the receipt, and that no attempt is pending.
- Require `view.mode == "accepted"`, `view.sources == pack.sources`, and module order equal to `modules()`.
- For each shown module that has a head, its artifact, facts, tables, claims and limitations must equal `store.head_module(head)` (the D1 check). A module without a head must show its idle status and carry no output.
- Outcome:
  - `complete` requires every planned analytical head to be accepted or restricted, and the model published.
  - `refused` requires exactly one G1 `RefusedBegin`, no model, and no publication directory.
  - Anything else is refused.

**What proves each assigned section.** The rendered page and the proof both come from one verified view. `render` calls `build(view, pathway, SHIPPED_MAPS)` itself (`render.py:141-142`).

- G2 calls `build` once with those same arguments.
- For each `scope.sections` block it records:
  - its state;
  - `block_sha256` = T(Block);
  - its bound facts, in placement order. These come from the `SHIPPED_MAPS` entries placed in that block (rail destinations excluded), matched with the public `Binding.matches` over modules in `SHOWN_STATUSES`.
- A `complete` outcome requires:
  - every assigned block is `populated` or `collapsed`;
  - its bound facts are non-empty;
  - every bound fact is a member of `head_module(head).facts` for a receipt head (accepted or restricted) whose `result_sha256` it carries.
- A `refused` outcome requires that blocks whose producers never began have no bound facts and are not in the `populated` state.
- The `report-data` JSON parsed from the HTML must contain, for each assigned block, exactly `block.model_dump(mode="json")`. In G2, assigned sections are non-chart blocks, so `_report_payload` changes only the `not_in_pathway` state.
- **Rails** (see Q4 for what the proof covers):
  - the facts bound to `evidence` and to `limitations`, with their head hashes, must appear unchanged in the payload's `modules[*].facts`;
  - the per-module limitations must equal the view's.

**HTML.** G2 renders `core_render.render(view)` with no injected ReportView and no envelope view. The envelope adds nothing to the display: `envelope_view` re-draws the same head module (`cp1_render.py:38-50`). There must be exactly one `<div id="call-root"></div>`. Immediately after it G2 inserts `<section id="delivery-scope-banner" class="banner" role="note" data-delivery-scope="<scope_id>">`, then `html.escape(scope.banner[outcome])`, then `</section>`. The banner text is fixed per scope and outcome (Q6).

**Outputs.**

- `report.html`
- `owner-run.json`: the exact receipt bytes
- `render-receipt.json`: canonical bytes, with no trailing LF
- With a published model (Q3): `model/{model.html,calculation.json,receipt.json}` byte-equal to the G1 publication, plus a top-level `calculation.json`. The Model panel links that basename (`app.js:601-603`).
- `files` maps every delivered file except `render-receipt.json` to its B hash.
- No envelope, no symlinks, no extra files.

**Publication staging (generalised from D1).**

- Refuse with `lexists` before resolving: an existing file, directory, symlink or dangling symlink.
- Resolve the parent. Refuse by file identity (`os.path.samefile` on the path and every ancestor, D1 F1) any parent that is, or lies inside, the store or the publication directory.
- Make a sibling stage with `mkdtemp`, write it, read back its exact inventory, and run the read-only verifier on the stage.
- Re-capture, check `lexists` again, rename, then verify the delivered directory before returning `destination/report.html` in the caller's own spelling (D1 F4).
- Failure before the rename removes only the call's own stage. Failure after the rename keeps the output as forensic evidence and raises.
- Refusals are `ValueError` with `owner_render_*` codes. There is no relabelling catch-all; `financial_rendering.py:213` has one and G2 does not copy it.

**Read-only verifier.** It checks that the delivery is a real directory of regular files with the exact inventory. It repeats the capture, re-derives the HTML, proofs and canonical metadata in memory, and compares every byte. It then re-captures and re-reads the delivery. It writes nothing.

## Acceptance (expectations from `cases/snapshot/expected.json`, never from G2)

Genuine G1 runs are built once per module by a fixture; tests work on copies. The file is heavy and runs under the lock.

1. **S1a positive.**
   - A test-local normaliser, written from `cell_notation`, maps payload cells and lines to the oracle: `shown` = text; `cites` = the Source and Locator from the passports of the fact's index refs; `synthetic_ref` = S provenance; G# numbers sequential (Q7 ruling).
   - Assert that the title, owner, kind, state, numbered, summary, tabs and rows/lines of `key-findings`, `company-operating-model`, `company-profile`, `strengths-weaknesses` and `transaction-summary` equal `positive.FP01`.
   - `strengths-weaknesses` has bound facts from CP-2 only, per the oracle note.
   - The render-receipt sections are exactly those five ids, in pathway order, and their bound-fact hashes equal the receipt's CP-1A and CP-2 heads.
   - Every table in `rails.evidence` and `rails.limitations` is present on its module's payload.
   - Module limitations equal `rails.limitations.module_limitations`, with the inherited CP-1 entries bound to the CP-1 head as the oracle says.
2. **S1a gap.** The same checks against `gap_business_without_ownership_transaction`, plus `must_not_appear`: no 0, N/A, TBD or empty cell for the ownership, shareholder or transaction rows, and no CP-2 confidence of "High".
3. **Equivalence and refusal (Q2).**
   - Positive G1 financial case: `report.html` with the one banner section removed equals `render_financial_slice`'s report with its banner removed, and the model files are byte-equal.
   - Gap case: outcome `refused`; CP-1 and CP-MODEL show "Not run" with no facts; there are no model files. These are the values of `test_financial_render.py:108-122`.
4. **Refusals.**
   - Receipt: a typed tamper; the non-canonical spellings `1.50`/`1.5`, reordered keys and a duplicate key.
   - Store: a foreign store; an extra attempt; tampered current pointer, blob and pack (D1 F8).
   - Publication: wrong publication directory; a changed model file.
   - Scope: an outside `requested_modules`.
   - Destination: the four existing-destination kinds; a parent inside the store or the publication directory under a case-variant alias on darwin.
   - Timing: a store change during staging and after the rename (output preserved, error raised).
   - Forgery: forged HTML with its hashes rehashed.
   - Every case raises `ValueError`.
5. **Read-only.** The relative paths and bytes of the store, the publication directory, the receipt and the delivery are identical before and after a passing verify and after a refused verify.
6. **Determinism.** `verify_owner_rendered_slice` run in a subprocess with a different `PYTHONHASHSEED` exits 0.
7. **Gates.** `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.

No stub or fake value stands in for real behaviour. No catch-all hides a failure.

## D1 mechanisms: generalise, do not copy

- **Generalise:** strict `from_wire` with exact keys, a `mode="after"` file-map validator, duplicate-key, non-finite and recursion refusals (F2, F6); canonical raw spelling with type-tagged numbers (F3, N1); the samefile overlap guard, extended to every input directory (F1); the caller-spelling return (F4); the capture/recheck/stage/rename/verify state machine; head results with qualification.
- **Do not copy:** case pins (`_RUNS`, `_frozen_run`); outcome text keyed by case; the earnings-specific selected tuple.

## Open questions for LEAD

- **Q1. Run binding.**
  - (a) Pin the full frozen Run per case in product code (D1 F7).
  - (b) Bind the scope by pathway, requested_modules and case_kind; the G1 verifier binds run to store, and tests pin the oracle Runs.
  - **Recommend (b).** The architecture study (§1) flags case pins in product code.
- **Q2. Ship a `cp1-model` scope** so G2 can be tested on G1 alone (test 3) before S1a's specs exist?
  - **Recommend yes.** It is the only refused-outcome case available today.
- **Q3. Model files in the delivery.**
  - (a) Follow the financial precedent: `model/` plus a top-level `calculation.json`.
  - (b) A flat D1-style bundle, which leaves the Model panel link dangling.
  - **Recommend (a).**
- **Q4. What "Evidence rendered" means.** The `#evidence` route draws only the source inventory (`app.js:636-649`, `:803`). Tables bound to `evidence` or `limitations` show only on module pages (`app.js:546-590`).
  - (a) G2 proves rail facts are on the module payloads and that the Limitations page shows the module limitations.
  - (b) Require an `app.js` change (a separate C2 renderer lease).
  - **Recommend (a) for G2**, and record (b) as a PLAN gap.
- **Q5. D1 F5** (`O_NOFOLLOW`/`dir_fd` reads in the verifier).
  - **Recommend adopting it now.** The verifier runs outside the publisher lease, and the fix is about 15 lines.
- **Q6. Banner texts and outcomes.** LEAD freezes the literal text per scope and outcome.
  - **Recommend refusing receipts with blocked heads** until a slice oracle covers them.

Not verified: no code was run apart from `registry.plan` for the S1a and S1b selections. Unchecked: that the G1 receipt and verifier shape survives fix round 1 and integration; that S1a's G1 extension exists; that the S1 oracle is adopted; that the render is byte-deterministic for S1a views across processes; that the payload's assigned blocks exactly equal the `build()` dumps; that `Binding.matches` placement reproduces `build`'s placement for keyvalue tabs; that the oracle's line and cell notation maps one-to-one onto the payload (for example, the "pen" line kind for key-findings sentences containing figures); and the size of the heavy-test budget.

## LEAD rulings on rev 0 (2026-10-28)

- Prerequisite 3 is met: the S1 oracle is adopted (a4f966f, 49801d7).
- Prerequisite 4 (G1 refuses an analytical module after a deterministic one, needed for S1b's
  plan order) goes to the S1a/S1b G1-extension lease, not to G2.
- Q1: (b). The scope binds by pathway, requested_modules and case_kind; no case pins in
  product code; tests pin the oracle Runs.
- Q2: yes, ship the `cp1-model` scope so G2 is tested on G1 alone first.
- Q3: (a), the financial precedent (`model/` plus top-level `calculation.json`).
- Q4: (a) for G2. PLAN gap recorded: the `#evidence` route draws only the source inventory,
  so rail tables show only on module pages; an `app.js` change needs its own C2 lease.
- Q5: adopt D1 F5 now (`O_NOFOLLOW`/`dir_fd` reads in the verifier).
- Q6: G2 refuses receipts with blocked heads until a slice oracle covers them. Banner texts:
  - `cp1-model` complete: "Historical financial analysis and Model publication only.
    Remaining analytical owners and forward projections remain unqualified."
  - `cp1-model` refused: "Financial source missing. CP1 financial analysis and Model
    publication did not run."
  - `s1a-credit-snapshot` complete: "Credit snapshot: source readiness, historical
    financials, Model, business context and credit synthesis only. Integrity review and
    remaining analytical owners remain unqualified."
  - `s1a-credit-snapshot` refused: "Credit snapshot incomplete: an owner was not
    authorized, so later owners did not run."

## Rev 1 amendments (LEAD, 2026-10-28) — override the body and rulings

From the independent review (`docs/reviews/s1a-g2-lease-review.md`).
- **Prerequisites:** G1 and S1a integrated, and the manifest adoption (49801d7) on
  `codex/checkpoint` ("prerequisite 3 met" held only on the LEAD branch).
- **M1 (outcomes):** `s1a-credit-snapshot` supports `complete` only; any S1a receipt with a
  refusal or blocked head is refused until a slice oracle covers it. The s1a refused banner is
  dropped. `cp1-model` keeps both outcomes.
- **M2:** acceptance imports `tests/s1a_runs.py` (owned by S1a) and G1's `promoted_case`; G2
  never re-implements them.
- **M3:** store heads equal the receipt on (module_id, result_sha256, status), and
  `OwnerHeadResult.qualification` is the store `Head.qualification`, which the G1 verifier
  already checks through `head_of` (`owner_workflow.py:1108`).
- **L1:** cite `render` at render.py:127 and `build` at :129-131; assigned blocks have no chart
  and `figures == ()`, asserted.
- **L2:** the scope matches the Run's exact `requested_modules` tuple.
- **L3:** model blocks rendered outside any scope section are an S1a scope limitation.
- **L4:** the "analytical after deterministic" G1 change belongs to the S1b lease.

## Rev 2 amendments (Modules, 2026-10-29) — override the body and rulings — FROZEN by Modules 2026-10-29 after mx-precise a6a7d04d (APPROVE)

Prepared for `docs/rulings/2026-10-29-stage3.md` item 2 on the release base `ab9777f`. It compiles one `DELIVERY_SCOPES` row per module run that has a frozen owner oracle, from the module leases, the oracles, the run drivers and the code. It needs an independent mx-precise approval before the G2 build starts; Modules freezes the banner texts on that approval. Rev 1 (M1-M3, L1-L4) stands except where this section says otherwise. Every line number below is on `ab9777f`.

### R2.1 What a row binds, and three small changes to the body

- A row is `DeliveryScope(scope_id, pathway, requested_modules, case_kind, sections, rails, banner)`. Matching is on `(pathway, requested_modules, case_kind)` with `requested_modules` the exact ordered tuple of the receipt's Run (Q1(b), L2). It never reads the preset, so the Q-C1 preset change (`covenant_refinancing` now lists `CP-MODEL`, `contracts.py:56-66`) does not touch any row: every owner run requests its modules explicitly (`Run`, `contracts.py:82-95`).
- `banner` is a mapping outcome to literal. A scope carries a banner only for an outcome it supports. A receipt whose outcome the scope does not support is refused with an `owner_render_*` code, exactly as an unmatched scope is.
- **Empty `sections` is valid.** Four rows are rails-only (`slice-cp2e-sensitivity`, `slice-cpdr-research`, `slice-cpl10-screen`, and CP-5's share of the gated R6 row). Their proof is the rail proof alone; `render-receipt.json` records `sections == []`. The "complete requires every assigned block populated" rule holds vacuously.
- **Blocked heads stay refused (Q6, M1).** Each oracle's `blocked`, `*_blocked` and `begin_refused_*` cases produce a blocked head or a refused begin on a blocked upstream. They are not scope outcomes. G2 raises `owner_render_*` on them, and each new scope's acceptance asserts that for every such case its driver offers.
- **Model rule (overrides body `:59`).** `complete` requires `receipt.model` set and published if and only if `"CP-MODEL" in requested_modules`. Otherwise it requires `receipt.model is None` and no publication directory. A model or directory where none is expected is refused with an `owner_render_*` code.
- **Refused outcome (M1 applied per scope).** A scope supports `refused` only where its oracle pins a refused run (the oracle's refused case, `cases.refused`, or `refused/no_record` for CP-8: one `RefusedBegin`, heads `["CP-0"]`, no model) **and** its run driver can produce it. The driver condition is new: acceptance imports the driver (M2) and G2 never builds a run. Where the oracle pins a refused run but `CASES` lacks it, the outcome is deferred and listed in R2.5.

### R2.2 Scope table (keyed by `scope_id`)

`rails` is `("evidence","limitations")` in every row. `case_kind` is `synthetic` in every row (each driver's pack, checked below). "Complete" runs are the driver cases that settle accepted or restricted heads. Status `ready` means the owner core, oracle and driver exist on `ab9777f`; `gated` names what is missing.

| scope_id | pathway | requested_modules | sections (pathway order) | complete cases | refused case | status |
|---|---|---|---|---|---|---|
| `cp1-model` | credit_snapshot | `("CP-1","CP-MODEL")` | unchanged from rev 0/1 | positive | gap (rev 0 test 3) | ready (rev 0) |
| `s1a-credit-snapshot` | credit_snapshot | `("CP-1","CP-MODEL","CP-1A","CP-2")` | unchanged: key-findings, company-operating-model, strengths-weaknesses, company-profile, transaction-summary | positive, gap | none (M1) | ready (rev 1) |
| `cp3-fp01-relative-value` | credit_snapshot | `("CP-1","CP-MODEL","CP-1A","CP-2","CP-3")` | `relative-value` | positive, gap | none | ready |
| `cp6-fp01-committee` | credit_snapshot | `("CP-1","CP-1A","CP-2","CP-3","CP-5","CP-6")` | `strengths-weaknesses`, `committee-challenge` | positive, gap | none | gated: no CP-6 core, no `cp6_closed` |
| `cp1c-fp03-peers` | relative_value | `("CP-1C",)` | `peer-positioning` | positive, gap, no_peers | refused | ready |
| `cp3d-fp03-market` | relative_value | `("CP-3D",)` | `market-against-fundamentals` | positive, gap_no_recovery, gap_no_market | none | ready |
| `cp1d-fp02-quality` | earnings_update | `("CP-1D",)` | `earnings-quality`, `restated-leverage` | positive, statements_only, gap | deferred (R2.5) | ready |
| `cp2a-fp05-downside` | distressed_restructuring | `("CP-2A",)` | `downside-stress`, `break-points` | positive, gap | refused | ready |
| `cp2g-fp05-forward` | distressed_restructuring | `("CP-2G","CP-1D")` | `forward-credit-path`, `forward-breakpoints` | positive | none | ready |
| `cp2g-fp05-forward-gap` | distressed_restructuring | `("CP-2G",)` | `forward-credit-path`, `forward-breakpoints` | gap | refused | ready |
| `cp2h-fp05-ratings` | distressed_restructuring | `("CP-2H",)` | `rating-triggers` | positive, gap | refused | ready |
| `cp4c-fp05-recovery` | distressed_restructuring | `("CP-4C",)` | `recovery-by-class`, `value-allocation-claims` | positive, gap | refused | ready |
| `cp2d-fp04-liquidity` | covenant_refinancing | `("CP-1","CP-1A","CP-2","CP-2D")` | `liquidity-runway`, `funding-gap` | positive, long_horizon, gap_minimum_cash | none | ready |
| `cp3c-fp04-refinancing` | covenant_refinancing | `("CP-1","CP-1A","CP-2","CP-2D","CP-3C")` | `funding-gap`, `refinancing-paths`, `lme-creditor-exposure` | positive, gap_minimum_cash, gap_no_repricing | none | gated: Q-C2 wiring and oracle re-pin (D2) |
| `cp4-fp04-covenants` | covenant_refinancing | `("CP-4",)` | `covenant-tests-headroom`, `red-flags`, `lender-protection-score`, `capacity`, `ebitda-definition`, `documents-structure` | positive, gap, gap_false_same_definition | none | ready |
| `cp8-fp01-what-changed` | credit_snapshot | `("CP-8",)` | `what-changed` | positive, no_outcome | no_record | ready |
| `slice-cp2e-sensitivity` | credit_snapshot | `("CP-2E",)` | none (rails and module page) | positive, gap_no_facility_schedule | none | ready |
| `slice-cpdr-research` | credit_snapshot | `("CP-DR",)` | none (rails) | partial, unresolved, empty_agenda | none | ready |
| `slice-cpl10-screen` | credit_snapshot | `("CP-L10",)` | none (rails) | positive, limited | deferred (R2.5) | ready |

Rows: 2 existing plus 17 new (15 ready, 2 gated). Scope ids keep the module leases' names where a lease names one (`cp1c-fp03-peers`, `cp1d-fp02-quality`, `cp2a-fp05-downside`, `cp2g-fp05-forward`, `cp2h-fp05-ratings`, `slice-cp2e-sensitivity`, `slice-cpl10-screen`); the others are assigned here. `strengths-weaknesses` on the gated CP-6 row is the block owned `CP-2 · CP-6` (`report_view.py:1109`); its CP-2 side belongs to `s1a-credit-snapshot`.

**Pathway order and ownership** are the `_PRESETS` block tuples (`report_view.py:485`: credit_snapshot `:487`, earnings_update `:506`, relative_value `:527`, covenant_refinancing `:544`, distressed_restructuring `:562`) and the `_Spec` rows (`report_view.py:1090-1250`). Order is the pathway's, not the oracle dict's: the CP-4 oracle lists `capacity` second (`cp4-owner/expected.json#/render/sections`), the pathway puts it fourth.

### R2.3 Matching: no two rows share a triple

All 19 triples are distinct (R2.7 says how this was checked). Positive and gap runs of one module share one triple and so one scope; the scope's outcome set is what separates them, and the receipt's outcome (not the case name) selects the banner. The only module whose runs differ in `requested_modules` is CP-2G (`positive` and `cp1d_blocked` request `("CP-2G","CP-1D")`, the other cases `("CP-2G",)`, `cases/cp2g-owner/manifest.json`, `tests/cp2g_runs.py:64`), so it has two rows. Within one pathway the ordered tuples differ in every pair; no row's tuple is a prefix-equal of another's (`("CP-4",)` against `("CP-2G",)` etc.). An acceptance test asserts triple uniqueness over `DELIVERY_SCOPES` statically, and asserts for each row that every driver case's Run (`make_pack(case).run`) matches exactly one row.

### R2.4 Banner texts (draft; Modules freezes on approval)

Style as rev 0: what the scope covers, then that the rest remains unqualified. No numbers, no module codes. The refused text names no cause beyond its oracle's pinned one. `html.escape` is applied as in the body.

| scope_id | outcome | literal |
|---|---|---|
| `cp3-fp01-relative-value` | complete | Relative value only: the instrument preference set against the observed market evidence. Every other block on this page, including committee challenge, integrity review and the remaining analytical owners, remains unqualified. |
| `cp6-fp01-committee` | complete | Committee challenge only: the action bias and the challenge to thesis, strengths and weaknesses, resting on the integrity review. Every other block on this page, including relative value and the remaining analytical owners, remains unqualified. |
| `cp1c-fp03-peers` | complete | Peer positioning only. Every other block on this page remains unqualified. |
| `cp1c-fp03-peers` | refused | Peer positioning did not run: an earlier owner was not authorized, so this owner never started. Every other block on this page remains unqualified. |
| `cp3d-fp03-market` | complete | Market against fundamentals only: observed levels, price metrics and spread. Instrument levels, yield against maturity and the remaining blocks on this page remain unqualified. |
| `cp1d-fp02-quality` | complete | Earnings quality and restated leverage only: the add-back assessment and leverage restated on supported earnings. Every other block on this page, including the headline results and the Model, remains unqualified. |
| `cp2a-fp05-downside` | complete | Downside stress and break points only. Every other block on this page, including the forward, recovery and rating blocks, remains unqualified. |
| `cp2a-fp05-downside` | refused | Downside stress did not run: an earlier owner was not authorized, so this owner never started. Every other block on this page remains unqualified. |
| `cp2g-fp05-forward` | complete | Forward credit path and forward break points only, built on the downside stress and the supported earnings. Every other block on this page remains unqualified. |
| `cp2g-fp05-forward-gap` | complete | Forward credit path and forward break points only, built on the downside stress; supported earnings were not requested. Every other block on this page remains unqualified. |
| `cp2g-fp05-forward-gap` | refused | Forward credit path did not run: an earlier owner was not authorized, so this owner never started. Every other block on this page remains unqualified. |
| `cp2h-fp05-ratings` | complete | Rating triggers only: headroom against a synthetic agency source, drawn from the forward credit path. Every other block on this page remains unqualified. |
| `cp2h-fp05-ratings` | refused | Rating triggers did not run: an earlier owner was not authorized, so this owner never started. Every other block on this page remains unqualified. |
| `cp4c-fp05-recovery` | complete | Recovery by class and value allocation only: the recovery waterfall under the stated scenarios. Every other block on this page remains unqualified. |
| `cp4c-fp05-recovery` | refused | Recovery analysis did not run: an earlier owner was not authorized, so this owner never started. Every other block on this page remains unqualified. |
| `cp2d-fp04-liquidity` | complete | Liquidity runway and funding gap only. The maturity wall, covenant analysis, refinancing and the remaining blocks on this page remain unqualified. |
| `cp3c-fp04-refinancing` | complete | Refinancing paths, the funding gap by maturity and creditor exposure under liability management only, built on the liquidity analysis. Covenant analysis and the remaining blocks on this page remain unqualified. |
| `cp4-fp04-covenants` | complete | Covenant analysis only: tests and headroom, capacity, red flags, lender protection, the EBITDA definition and the document register. Liquidity, refinancing and the remaining blocks on this page remain unqualified. |
| `cp8-fp01-what-changed` | refused | What changed since the last Report did not run: the readiness review refused this owner itself because no prior case was supplied. Every other block on this page remains unqualified. |
| `cp8-fp01-what-changed` | complete | What changed since the last Report only: a comparison with the recorded prior case. Every other block on this page remains unqualified. |
| `slice-cp2e-sensitivity` | complete | Macro and FX sensitivity only, on its module page with its evidence and limitations. No Front Page block on this page is qualified. |
| `slice-cpdr-research` | complete | Local research agenda coverage only, shown as evidence and limitations. No Front Page block on this page is qualified. |
| `slice-cpl10-screen` | complete | Screening only, shown as evidence and limitations. No Front Page block on this page is qualified. |

`cp1-model` and `s1a-credit-snapshot` keep their rev 0 texts (`:173-181`; the s1a refused text is dropped by M1).

### R2.5 Oracle pointers and run fixtures

`E` is `expected.json` of the cited case directory; pointers are JSON Pointers. A complete-outcome acceptance asserts the block tree and rails at the first pointer for the case run; a refused acceptance asserts the second. Gap cells are the pattern `∅ G#` / `∅ G# n.m.` (G numbers sequential in report order, oracle `cell_notation`). "Driver" is `tests/<cp>_runs.py` function and its return shape; `pack` is the line that builds the Run checked in R2.6.

| scope_id | complete pointer (per case `<c>`) | refused pointer | driver (pack line) |
|---|---|---|---|
| `cp3-fp01-relative-value` | `cp3-cp6-owner/E#/<c>/CP-3/render` (`FP01.relative-value`, `rails`) | none | `cp3_closed(case, root, *, requested=None) -> (store, receipt, publication)` `cp3_cp6_runs.py:235` (pack `:56`) |
| `cp6-fp01-committee` | `cp3-cp6-owner/E#/<c>/CP-6/render` (`FP01.committee-challenge`, `FP01.strengths-weaknesses.CP-6-side`, `rails`) and `cp5-owner/E#/render` (`rails`, `slots`) | none | none: `cp3_cp6_runs.py:6` says it exports no `cp6_closed` |
| `cp1c-fp03-peers` | `cp1c-owner/E#/cases/<c>/FP03` | `cp1c-owner/E#/cases/refused` | `cp1c_closed -> (store, receipt, None)` `cp1c_runs.py:273` (pack `:81`) |
| `cp3d-fp03-market` | `cp3d-owner/E#/render` with tables at `#/cases/<c>/tables` | none | `cp3d_closed -> (store, receipt)` `cp3d_runs.py:125` (pack `:41`) |
| `cp1d-fp02-quality` | `cp1d-owner/E#/cases/<c>/FP02` | oracle `#/cases/refused` exists, driver lacks it | `cp1d_closed -> (store, receipt)` `cp1d_runs.py:269` (pack `:48`) |
| `cp2a-fp05-downside` | `cp2a-owner/E#/cases/<c>/FP05` | `cp2a-owner/E#/cases/refused` | `cp2a_closed -> (store, receipt, None)` `cp2a_runs.py:261` (pack `:44`) |
| `cp2g-fp05-forward` | `cp2g-owner/E#/cases/positive/FP05` | none | `cp2g_closed("positive", root)` `cp2g_runs.py:339` (pack `:64`) |
| `cp2g-fp05-forward-gap` | `cp2g-owner/E#/cases/gap/FP05` | `cp2g-owner/E#/cases/refused` | `cp2g_closed("gap"/"refused", root)` |
| `cp2h-fp05-ratings` | `cp2h-owner/E#/cases/<c>/FP05` | `cp2h-owner/E#/cases/refused` | `cp2h_closed -> (store, receipt, None)` `cp2h_runs.py:287` (pack `:59`) |
| `cp4c-fp05-recovery` | `cp4c-owner/E#/cases/<c>/FP05` | `cp4c-owner/E#/cases/refused` | `cp4c_closed -> (store, receipt, None)` `cp4c_runs.py:317` (pack `:65`) |
| `cp2d-fp04-liquidity` | `cp2d-owner/E#/fp04_render` (`blocks`, `rails`) with cell text from `#/cases/<c>/tables` | none | `cp2d_closed(case, root, template=None) -> (store, receipt)` `cp2d_runs.py:119` (pack `:47`) |
| `cp3c-fp04-refinancing` | `cp3c-owner/E#/fp04_render` (to be re-pinned, D2) with `#/cases/<c>/tables` | none | `cp3c_closed(case, root, template) -> (store, receipt)` `cp3c_runs.py:178` (pack `:63`; `template` from `reach_cp2d`) |
| `cp4-fp04-covenants` | `cp4-owner/E#/render` (`sections`, `evidence_rail_tables`, `limitations_rail_tables`, `displayed_literals/<positive or gap>`, `limitations_rail_module_limitations`) with cases at `#/positive`, `#/gap`, `#/gap_false_same_definition` | none | `cp4_closed(case, root, *, template=None) -> (store, receipt, None)` `cp4_runs.py:149` (pack `test_method_cp4.py:89` via `cp4_runs.py:50`) |
| `cp8-fp01-what-changed` | `cp8-owner/E#/render` (`blocks`, `rails`, `lines_positive`) with `#/cases/<c>` | `cp8-owner/E#/refused/no_record` | complete: `cp8_closed -> (OwnerWorkflow, PreparedPack)` `cp8_runs.py:127` (pack `:42`) returns the settled workflow, so the test writes the receipt with `workflow.write_receipt` as `cpl10_closed` does (`cpl10_runs.py:175`). Refused: `cp8_runs.start("no_record", root)` (`cp8_runs.py:94`) then `workflow.write_receipt`, as `tests/test_owner_cp8.py:121-130` |
| `slice-cp2e-sensitivity` | `cp2e-owner/E#/render` (`module_page`, `evidence rail`, `limitations rail`) and `#/cases/<c>/module_tables` | none | `cp2e_closed -> (store, receipt)` `cp2e_runs.py:146` (pack `:44`) |
| `slice-cpdr-research` | `cpdr-owner/E#/evidence_rail`, `#/limitations_rail` (rails); `#/rendering` pins the surrounding page and is not asserted by G2 | none | `cpdr_closed -> (store, receipt)` `cpdr_runs.py:128` (pack `:43`) |
| `slice-cpl10-screen` | `cpl10-owner/E#/rendered/rails` | oracle `#/refused` exists, driver lacks it | `cpl10_closed -> (store, receipt)` `cpl10_runs.py:169` (pack `:40`) |

Deferred refused outcomes (oracle pins a refused run, driver cannot yet run it): `cp1d-fp02-quality` (`cp1d_runs.py:26` `CASES`) and `slice-cpl10-screen`. Each gets a banner and the outcome in one later amendment when its driver gains the case; until then a refused receipt for these triples raises `owner_render_*`. This is M1 applied: no outcome without a pinned run **and** a driver.

### R2.6 Disagreements between a lease, the oracle, the code and the rulings

| # | What disagrees | Choice |
|---|---|---|
| D1 | CP-2D lease `:141` assigns `maturity-wall` (T2E.4 tab) to the CP-2D scope. The CP-2D oracle pins only the owner (`#/fp04_render/blocks/maturity-wall`: owner `MODEL`, `stage3_pending`), and Q-C1 made the block Model-owned with producers `("CP-1",)` (`report_view.py:1171-1174`). | Oracle and ruling win: sections are `liquidity-runway`, `funding-gap`. `maturity-wall` joins the CP-2D row, between them, in the amendment that follows the Stage 3 S.4 wiring and the oracle's populated shape. |
| D2 | CP-3C lease `:205` and its oracle bind `T3D.1` to `refinancing-paths` (`bindings/cp3c.py:35`, `#/fp04_render/blocks/refinancing-paths/tabs` = T3D.1-T3D.3). Q-C2 and ruling item 2 draw the T3D.1 series in `funding-gap`. | The row follows the ruling: `funding-gap` is its first section (facts from the CP-2D and CP-3C heads, both receipt heads). It is `gated` until the Q-C2 wiring moves the binding and re-pins `cp3c-owner/E#/fp04_render` (and its builder pins); G2 ships no `cp3c-fp04-refinancing` entry before that, so a CP-3C receipt is refused as outside every scope. |
| D3 | CP-2E lease `:82` says the scope is "module page and rails". Rev 0 proves sections and rails only. | `sections == ()`. The module page is asserted in the scope's acceptance on the payload (`modules[CP-2E].tables` ids and layouts equal `#/cases/<c>/module_tables`, claims equal the oracle's). No API change. |
| D4 | CP-3 lease `:76` says the driver exports `cp6_closed`. `tests/cp3_cp6_runs.py:6` says it exports none, and `tests/test_connect_cp3.py:385` asserts that. No CP-6 core exists (`src/deploy_workflow/owners/` has no `cp6.py`). | The code wins: `cp6-fp01-committee` is `gated`. CP-5 (rails only, no block, `CP5-OWNER-LEASE.md:206`) has no run of its own: its oracle runs are the R6 run (`cases/cp5-owner/manifest.json`, `slice-cp6-*`), so CP-5 shares the R6 row and gets no standalone row. |
| D5 | CP-DR lease `:185`: "a new scope entry, sections Evidence and Limitations only", no id. The brief recorded CP-DR as "none per Q1"; no "Q1" text exists in `CPDR-OWNER-LEASE.md`, and the other leases' "Q1" are unrelated. | CP-DR gets a rails-only row `slice-cpdr-research` as its lease says. The oracle's full-page pin (`#/rendering`: every block `not_in_pathway` or `absent`, wording the lease calls false for an override slice) stays the CP-DR test's business; the banner says no Front Page block is qualified. **Question Q-S1 below.** |
| D6 | CP-4 lease `:200` and the oracle list the six sections in oracle order. | Pathway order (R2.2). |
| D7 | Drivers return different shapes (`cp1d_closed`, `cp2d_closed`, `cp3c_closed`, `cp2e_closed`, `cp3d_closed`, `cpdr_closed`, `cpl10_closed` return two paths; `cp8_closed` returns a workflow; `cp2d_closed` and `cp3c_closed` take a template). Leases quote `(store, receipt, None)` for several. | Drivers are unchanged (M2: G2 imports, never re-implements). The shape is recorded per row in R2.5 and the G2 test adapts it. |
| D8 | CP-1D and CP-L10 oracles pin refused runs but their `CASES` lack them (R2.5). CP-8's `no_record` is driven by `cp8_runs.start`, so CP-8 supports `refused`. Lease rows (`CP1D-OWNER-LEASE.md:47`) name no outcomes. | Outcome deferred, not guessed. |
| D9 | CP-2G lease `:166` and CP-1D lease `:47` omit `case_kind`; CP-3 and CP-4 leases name no scope. | `case_kind="synthetic"` for all rows, from each pack's Run (R2.7). |

### R2.7 Gate evidence (script run on `ab9777f`; rerun it, do not trust this table)

- **`requested_modules`, `pathway`, `case_kind`**: for every row, every driver case in R2.2 and R2.5 builds a `Run` (`make_pack(case).run`; `cp4` via `test_method_cp4.make_pack`) whose `(pathway, requested_modules, case_kind)` equals the row, and the Run's own `requested_modules` is the explicit tuple (`contracts.py:82-95`). The script covered the 16 rows with a driver; `cp6-fp01-committee` rests on `cases/cp3-cp6-owner/manifest.json#/runs/R6/requested_modules` and the two existing rows on their rev 0/1 drivers (`cases/financial/manifest.json`, `tests/s1a_runs.py:77`). Oracle manifests that hold a run agree where they hold one; the CP-4 manifest's `requested_modules` is prose, so CP-4 rests on the pack.
- **Sections**: each row's `sections` is the subsequence of the pathway's `_PRESETS` tuple (`report_view.py:485-`) and is a subset of the block keys of the oracle pointer in R2.5. The two exceptions are declared above: `funding-gap` on `cp3c-fp04-refinancing` (not yet in that oracle, D2) and the empty tuples.
- **Triples unique**: the script checked the 16 driver rows; the other three (`cp1-model`, `s1a-credit-snapshot`, `cp6-fp01-committee`) were compared by eye against them (the tuples differ from every other `credit_snapshot` row).
- **Not claimed by the script**: the oracle block trees against rendered output (nothing renders until G2 exists).

### R2.8 Acceptance G2 needs per new scope

Rev 1's list (1-7) applies to `cp1-model` and `s1a-credit-snapshot` unchanged. For every new scope, add (each reads expectations from the R2.5 oracle pointers, never from G2):

1. **Block check.** For each assigned section and each complete case: the five fields title, owner, kind, state and tabs (table id, label, rows and cells with `fact_id`, `field`, `shown`, `state`) equal the oracle block; `numbered`, `summary` and `lines` where the oracle has them (`cp3`, `cp6`, `cp8`). Gap cells match the `∅ G#` pattern and G numbers are sequential in report order. The render-receipt `sections` are exactly the row's ids in pathway order, and their bound-fact hashes equal the receipt heads.
2. **Rails.** Every table in the oracle's `evidence` and `limitations` rails is on its module's payload, and module limitations equal the oracle's (own, settled and inherited, as the oracle splits them).
3. **Outcomes.** Each complete case yields outcome `complete` with the row's banner; where the row supports `refused`, that case yields `refused` with its banner, blocks show their `not_run`-family state (`report_view.py:1304-`) with no bound facts, and there is no publication; every other outcome raises. The block state on the refused page comes from the core `report_view` honest-state code on purpose, since G2 does not own it; the test takes the producer ids from the oracle's `refused_begins` and `heads`, not from G2; for CP-8 it reads the oracle's `begin` and `rendered` fields, because `refused/no_record` has no `refused_begins` or `heads`.
4. **Blocked and unsupported.** Every `blocked`, `*_blocked` and `begin_refused_*` case the driver offers raises `owner_render_*`; so does a refused receipt on a row without `refused`.
5. **Scope refusal.** A Run with an outside `requested_modules` (one module added, dropped, or reordered) is refused. The triple-uniqueness test of R2.3.
6. **Banner.** Exactly one banner section carrying the row's literal for the outcome, `html.escape`d; the page minus the banner equals `render(view)`.
7. **Row extras.** `cp3-fp01-relative-value`: the Model is published and delivered as in the S1a row (the run requests `CP-MODEL`). Rows without `CP-MODEL` in the tuple deliver no `model/` and no top-level `calculation.json`. `cp4-fp04-covenants`: the three displayed-literal sets, including the corrected `gap_false_same_definition`. `cp2d-fp04-liquidity` and `cp3c-fp04-refinancing`: `funding-gap` bound facts come from the CP-2D head (and, for CP-3C, also the CP-3C head), each a member of its head's facts. `slice-cp2e-sensitivity`: the module-page check of D3.
8. **Gated rows** (`cp6-fp01-committee`, `cp3c-fp04-refinancing`) have no `DELIVERY_SCOPES` entry and no test until their prerequisite lands; a receipt for their triple is refused as outside every scope, and a test asserts that.
9. Determinism, read-only and the other rev 1 cross-cutting tests (5-7) run on one new scope per pathway, not on all.

### R2.9 Modules with no row, and why

`CP-OS` (independent of G2, rulings item 1 Q2); `CP-1B` (its delivery is the unintegrated D1 `earnings_rendering`, not a G1 run, and `cases/earnings` is the D1 oracle); `CP-5` (shares the R6 row, D4); the `legal`, `connected`, `source`, `upstream` and `integrity` case sets (not owner runs or not G1 receipts). S1b (`CP-5` after the S1a modules) needs the G1 change of prerequisite 4 first.

### R2.10 Questions

Settled by rulings item 4 (`docs/rulings/2026-10-29-stage3.md` on the lane); no open questions here.

Not verified: nothing was rendered or run through G2 (it does not exist); the banners are drafts; the oracle block trees were compared to the pathway order and key sets only, not to product output; for `cp3-fp01-relative-value` the CP-3 core was not run; the refused-run pins were read from oracle text, and the refused drivers (`cp1c`, `cp2a`, `cp2g`, `cp2h`, `cp4c`) were checked to list the case, not run.

## Rev 3 amendments (Modules, 2026-10-29) — override rev 2 where they differ

Prepared for `docs/rulings/2026-10-29-stage3.md` item 15 (with items 2, 4 and 7). Rev 2 is frozen at `b6730b7`; rev 3 settles two things and changes nothing else. Oracle paths are on `731059f` (the integrated Stage 3 chart tree); `E` is `cases/charts/`. Line numbers for `report_view.py`, `bindings/`, `financial_series.py`, `financial_rendering.py` and the tests are on `b6730b7`.

### R3.1 `cp1-model` sections (answers the G2 builder's question 1)

Sections, in pathway order (`_PRESETS` credit_snapshot, `report_view.py:493-495`): `model-chart-strip`, `capital-structure`, `financials-credit-metrics`. Rev 0/1's "unchanged" for this row means these three, not the builder's two.

Derivation. The `cp1-model` complete run is the `slice-cp1-model-positive` run (`requested_modules ["CP-1","CP-MODEL"]`, `cases/financial/manifest.json` `run`). `tests/test_financial_render.py` asserts CP-1 and CP-MODEL both read "With limitations" (`:127-128`), and "Not run" with no facts or claims on the gap (`:108-122`). The page is rendered by `core_render.render(view)` (`financial_rendering.py:158`), so the composed blocks are the ones the shipped bindings fill from CP-1:

| block | what fills it | file:line |
|---|---|---|
| `model-chart-strip` | T4.10 bound `text` (`kpi-dashboard`); figures S.1-S.4 from `cp1_chart_series` for a CP-1 head that is accepted or restricted | `bindings/cp1.py:52`; `report_view.py:1098-1100`, `:1645-1660`; `financial_series.py:53-55`, `:256` |
| `capital-structure` | T4.18, T4.17 and `pro-forma` | `bindings/cp1.py:54-58`; `report_view.py:1101` |
| `financials-credit-metrics` | T4.4, T4.5, T4.6, T4.8, T4.9, T4.15, T4.16, `segment-allocation`, `operating-kpis` | `bindings/cp1.py:42-51`; `report_view.py:1102-1108` |

`CP-MODEL` binds the Evidence rail only (`bindings/cp_model.py:5-20`), so it adds no section. These three are the only credit_snapshot blocks whose producers are `("CP-1",)` alone (`report_view.py:1098-1108`); every other block needs CP-1A, CP-2 or a later owner, which a `("CP-1","CP-MODEL")` run does not request.

`model-chart-strip` IS a section. The builder excluded it only because rev 1 L1 forced `figures == ()` and the strip is a chart block; R3.2 lifts that rule. The strip is bound (`bindings/cp1.py:52`) and drawn for a restricted CP-1 (`_cp1_strip`, `report_view.py:1645-1660`; its payload is asserted at `tests/test_cp1_chart_render.py:405-410` and `:439-441`), so the "complete requires every assigned block populated" rule holds for it. Leaving it out would leave a populated, bound Model block outside the proof of the one scope whose purpose is the Model. Rev 1 L3 (model blocks outside a scope section are an S1a limitation) is unchanged for `s1a-credit-snapshot` and does not apply to `cp1-model`.

Refused outcome: all three blocks have no bound facts, are not populated, and have `figures == ()` (the rev 1 refused rule, plus `E/expected.json` adversarial `missing_financial_source`: no chart zero-fill).

### R3.2 Figures in assigned blocks (replaces rev 1 L1)

Rev 1 L1's "assigned blocks have no chart and `figures == ()`, asserted" is withdrawn. Its `render`/`build` citations stand.

**Rule.** For an assigned block, the block's `figures` in `build`'s output and in the `report-data` JSON equal the frozen chart oracle's render expectation for that block, pathway and case. Where no chart oracle covers the block and pathway, or the oracle says the case draws nothing, `figures == ()`, asserted. A refused outcome keeps `figures == ()` (blocks not populated).

**Comparison.** Field by field against the oracle's literals, never recomputed. For each figure: `fig_id`, `placement`, chart `kind`, title, unit, series captions in order, and for each mark its category, series, text, value and report reference. Each mark's fact id is looked up at run time from the oracle's `fact_coordinate`/`companion_coordinates` (or `fact_id_rule`) and must resolve to exactly one fact of the receipt's head. The table twin's row labels and cell texts equal the oracle's twin in order. A gap mark equals the oracle's gap mark (`value` null, `∅ G#`), never 0. The test reads values from the oracle; it never derives a mark, ratio, sum or rounding from the payload or the facts. A figure the oracle names for the case but the payload lacks, or an extra figure the oracle does not name, fails.

**Rows with a chart expectation** (every rev 2 row's sections checked). `<c>` is the driver case.

| scope_id | block | figures | oracle path and pointers |
|---|---|---|---|
| `cp1-model` | `model-chart-strip` | S.1-S.4 | `E/expected.json` `#/chart_series` (S.1-S.4), `#/quarters`, `#/q4_trailing_basis`, `#/current_maturity_wall` (positive only) |
| `cp1-model` | `financials-credit-metrics` | S.5, beside | `E/s5-expected.json` `#/render` (credit_snapshot), `#/chart_series/0`, `#/table_twin/S.5` |
| `cp1c-fp03-peers` | `peer-positioning` | RV.3a and RV.3b, above | `E/rv3-expected.json` `#/render`, `#/cases/<c>/chart_series` for `positive`, `gap`; `no_peers` and `refused`: `()` (adversarial `no_peers_and_refused`) |
| `cp4-fp04-covenants` | `covenant-tests-headroom` | CR.1, beside | `E/cr1-expected.json` `#/render`, `#/cases/<c>/chart_series` for `positive`, `gap`; `gap_false_same_definition` settles the `gap` chart (`#/cases/gap_false_same_definition/corrected_resubmission_chart`) |
| `cp2d-fp04-liquidity` | `liquidity-runway` | CR.2, above | `E/cr2-expected.json` `#/render/covenant_refinancing`, `#/chart_series/CR.2/<c>`, `#/table_twins/<c>` for `positive`, `long_horizon`, `gap_minimum_cash` |
| `cp2d-fp04-liquidity` | `funding-gap` | `()` (no CR.3: no CP-3C in the run) | `E/cr3-expected.json` adversarial `cp3c_not_in_the_run` |
| `cp3c-fp04-refinancing` | `funding-gap` | CR.3, beside | `E/cr3-expected.json` `#/render/covenant_refinancing`, `#/chart_series/CR.3/<c>`, `#/table_twins/<c>` for `positive`, `gap_minimum_cash`, `gap_no_repricing` |
| `cp4c-fp05-recovery` | `recovery-by-class` | DR.2, above | `E/dr2-expected.json` `#/render/distressed_restructuring`, `#/chart_series/DR.2/<c>`, `#/table_twins/<c>` for `positive`, `gap` |
| `cp4c-fp05-recovery` | `value-allocation-claims` | DR.3, DR.4, DR.5 in that order, above | `E/dr345-expected.json` `#/render/distressed_restructuring`, `#/chart_series/DR.3-5/<c>/DR.3` (and `.../DR.4`, `.../DR.5`), `#/table_twins/<c>` for `positive`, `gap` |
| `cp2h-fp05-ratings` | `rating-triggers` | DR.6 (the n/a frame, 0 marks, chip "Not computable") | `E/dr6-expected.json` `#/render/distressed_restructuring`, `#/chart_series/DR.6`, `#/render/distressed_restructuring/frame_texts/per_case/<c>` for `positive`, `gap` |

Notes on the table.
- **S.5.** It sits on `financials-credit-metrics` for the credit_snapshot pathway (`s5#/render`). The only credit_snapshot row that assigns that block is `cp1-model`; `s1a-credit-snapshot` and `cp3-fp01-relative-value` assign other blocks, so S.5 is not asserted there (rev 1 L3).
- **`cp2d-fp04-liquidity`.** `funding-gap` is `()` because CR.3 needs a CP-3C head.
- **`cp3c-fp04-refinancing`.** CR.2 is not asserted: the row assigns no `liquidity-runway`.
- **CR.2 on distressed_restructuring** (`cr2#/render/distressed_restructuring`) applies to no row: no distressed row assigns `liquidity-runway`.
- **S.4 on FP-04** (`E/s4fp04-expected.json`, block `maturity-wall`) applies to no row, as rev 2 D1 holds.
- **Fixtures.** Oracle entries keyed `fixture_*` are derived-only unit fixtures, not driver cases; G2 acceptance does not assert them.

**Every other assigned block** in every rev 2 row has no chart oracle for its pathway: `figures == ()`, asserted. That covers `key-findings`, `company-operating-model`, `strengths-weaknesses`, `company-profile`, `transaction-summary`; `relative-value`; `market-against-fundamentals`; `earnings-quality`, `restated-leverage`; `downside-stress`, `break-points`; `forward-credit-path`, `forward-breakpoints`; `red-flags`, `lender-protection-score`, `capacity`, `ebitda-definition`, `documents-structure`; `refinancing-paths`, `lme-creditor-exposure`; `what-changed`; and `capital-structure` on `cp1-model`. Rows with `sections == []` assert nothing.

**Acceptance (adds to R2.8).**
1. Each row above: figures equal the oracle by the comparison rule, for every listed case, on the genuine driver run.
2. Each other assigned block: `figures == ()`.
3. A negative: for one row, perturb a payload mark's text, value or ref after rendering, and the comparison fails; a figure moved to another block or an extra figure fails.
4. Each listed oracle pointer must exist; a missing pointer fails the test and is never skipped.

`cp3c-fp04-refinancing` is `gated`, so its figure assertions land with its wiring, as rev 2 holds.

Not verified: nothing was rendered or run through G2; no `report_view.build` output was compared to these oracle pointers (keys were read from the JSON, not from product output); whether `build` already emits S.5, RV.3, CR.1-3 and DR.2-6 is the wiring builders' work; the claim that a restricted CP-1 run populates `model-chart-strip` rests on `tests/test_cp1_chart_render.py` (a typed-seam fixture, not the genuine G1 run); the `E/expected.json` pointers for S.1-S.4 were read as keys, not matched to marks.
