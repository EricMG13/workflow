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
