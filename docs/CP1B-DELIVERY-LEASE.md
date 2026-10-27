# Authenticated FP02 earnings delivery — pre-code lease

This contract freezes C2's bounded read-only delivery of the actual A4 final
earnings slice. It is not code/job admission, an actual run or FP02 acceptance.
C2 proposal311f6d6a is resolved here. The exact pins, wire order, literal reused
financial expectations, cases and causal failures are in
`cases/earnings/delivery-expected.json`; that oracle is normative with this lease.
No financial source or earlier contract/oracle bytes change.

## Authority, boundary and prerequisites

LEAD explicitly assigned Sol/high source/state contract authoring and the existing
independent review chain. C2 later owns ONLY NEW
`src/deploy_workflow/earnings_rendering.py` and NEW
`tests/test_earnings_rendering.py`. Handoffs/logs/reviews stay in assigned work.
No shared renderer, assets, bindings, chart producer, registry, Execution, B1/A4,
old delivery, sourcehost, source/oracle or session/status file edits. Do not import
old mutable WIP, invent a receipt class matching a future producer, or substitute
a fake verifier. Name a concrete missing seam to LEAD if two files cannot consume
the public supported interfaces. No additional approval/review chain.

Adopt original B1 leasee66aa2df plus CURRENT owner oraclea37dc25f and exact
claim-reference override3341de53; raw4a6ddd6d/7fba44bc and
sessionedc60f4e/7c2e0312 stay unchanged. Adopt A4 leasecf562507 plus CURRENT
oracle90871a00/reference addendum92c2851b and original independent reviewba27cc9d.
A3b0de1be5/7b45f939, A1b32b91f8/041e2e05, descriptor60ed9578 and unchanged
financial/chart sources remain adopted. Full SHA256 strings, same-review
reference corrections and accepted source referencebcf6aef835b68869f84be09d65f9b746a2af3c88
are recorded in the oracle. These are reference/pre-code authorities, not a
license to inspect mutable implementation work or a substitute for exact later
PM-integrated implementation and runtime admission. B1/A4 authors continue their
disjoint work; drafting does not wait for them, runtime does.

Original B1 oraclec8af02d3, A4 oraclea23517e8 and intermediateef5e0e17 are archived
historical evidence, not active expectations. The same-ID monetary figure/gap-chip
correction preserves all numbers, units, citations, lineages, limitations, counts,
wire/API/caps and source permissions. Its independently checked A4 proof still
fits65tools/70messages and maxBODY8088. Correct grammar does not approve semantic
support, an old candidate's settlement or a clean CP5 report. Exact corrected
producer integration remains required; no new financial audit or policy follows.

First actual selection: synthetic Northbridge `earnings_update`, explicitly
requested `(CP-1B,CP-5)`, ordered closure `(CP-0,CP-1,CP-1B,CP-5)`, and A4
`publication_files={}`. Accept only the three frozen owner case identities/runs
through their actual producer verifier. Do not let the generic earnings preset
silently add Model/specialists. This is a bounded FP02 slice, not all26 owners,
full earnings-specialist coverage, other pathways or production qualification.

## Exact public API and producer authority

New module `deploy_workflow.earnings_rendering` exports:

```python
render_earnings_slice(execution_directory: Path, receipt_path: Path,
                      destination: Path) -> Path
verify_earnings_rendered_slice(execution_directory: Path, receipt_path: Path,
                               delivery_directory: Path) -> None
```

Render returns `destination/report.html` only after final delivered verification.
Verify returns None only, is read-only, and requires the genuine execution
journal/pack/blobs/owner+integrity audits/ancestor/seals. Three output files alone
are not portable producer authentication; a portable input must include the
complete genuine store and final supplied receipt. This is a trusted downstream
source-authorized delivery, not an expansion of the upstream-only CP5 actor
channel: never send the final composite receipt/raw foundation evidence through
CP5 tools. Neither function begins,
submits, settles, repairs, publishes or seals a producer workflow or mutates any
qualification field. Missing producer code is an integration dependency, never a
source gap or permission to stub.

Import the ACTUAL `EarningsSliceReceipt` and
`verify_earnings_slice_receipt(store: Execution, receipt: EarningsSliceReceipt)
-> None` from `deploy_workflow.integrity_workflow`. Strict-parse the supplied
bytes as that type and call that public verifier. It alone authenticates the
B1 prefix, selected session/call credits, CP5 full scope/participation, historical
rederivation, journal transitions, final current state and seals. Do not implement
a competing replay, shadow store, alternate producer schema or provenance check
that accepts something the public verifier refuses. Fixed delivery-scope checks,
View consistency, file hashes and deterministic HTML checks remain C2's work.

Complete input requires the authentic A4 complete receipt: actual promoted
accepted/restricted CP5, unchanged verified owner ancestor, exact final heads and
no pending/unaccounted records. A valid no-YoY comparison can meet this while its
missing prior remains disclosed. Source-negative input is ONLY the genuine B1
`cp1_not_authorized` plus actual A4 CP5 begin refusal, no CP5 ticket/result and
unchanged final state. Invalid/pending/partial CP5, absent implementation or an
owner-only checkpoint cannot become a source-negative delivery.

## Exact output and hash domains

Every supported outcome publishes exactly three regular files, with no output
symlinks, hidden extras or subdirectories:

- `report.html`: ordinary actual View rendering plus the one fixed scope banner.
- `earnings-slice.json`: EXACT supplied final receipt bytes, without reserialization.
- `render-receipt.json`: strict immutable `EarningsRenderReceipt`, canonical UTF-8
  `model_dump_json()` bytes with no terminal LF.

No Model directory/model.html/calculation.json/publication receipt, envelope,
calculation download or copied historical output. All assets remain embedded by
the existing renderer. Output paths/staging must not alias or be inside the
execution store or overwrite any existing input/artifact.

`B(x)` is SHA256 of exact raw bytes; `T(x)` is existing
`Contract.content_hash()` over canonical model_dump_json UTF-8 bytes. Never
conflate an input file's whitespace spelling with its typed producer identity.
If actual A4 parsing/verification accepts a different raw whitespace spelling of
the same genuine typed receipt, copy it exactly and bind its distinct B while
retaining the same T. Rechecks require that supplied raw spelling stays unchanged.

`EarningsHeadResult` fields, in order: module_id:Identifier, result_sha256:Hash,
status:accepted|restricted|blocked, qualification:existing Qualification|null.
Copy the ordered actual A4 heads; complete has exactly CP0/CP1/CP1B/CP5, negative
CP0 only. Qualification is the actual object or null, not a string, renderer
judgment or omission; serialize all four current object fields unchanged.

`EarningsRenderReceipt` fields, in exact order:

1. schema_version: literal `earnings-slice-render/1`.
2. scope: literal `earnings-update-slice`.
3. run: existing Run from actual A4 receipt.
4. pack_sha256:Hash; snapshot_sha256:Hash — actual A4 final values.
5. outcome:complete|cp1_not_authorized — actual A4 outcome.
6. earnings_receipt_file: literal `earnings-slice.json`.
7. earnings_receipt_file_sha256:Hash=B(exact supplied/exported receipt bytes).
8. earnings_receipt_content_sha256:Hash=T(actual final EarningsSliceReceipt).
9. owner_receipt_sha256:Hash=T(embedded owner), equal A4's actual field.
10. integrity_receipt_sha256:Hash=T(embedded integrity), equal A4's actual field.
11. head_results:ordered tuple[EarningsHeadResult,...].
12. files:exact mapping, ordered report.html then earnings-slice.json, values B(file).

Existing strict frozen Contract policy applies. Every key required, no extras or
duplicate JSON keys, no coercion/default substitution, null only where declared.
The files map deliberately excludes the render receipt itself; externally retain
its raw hash for the handoff. Self-consistent metadata is not authentication.
The verifier rederives exact canonical metadata and HTML, so changing HTML and
updating all hashes still refuses. Render metadata never promotes a source head's
implementation/analytical/render/native qualification or replaces actual status.

## Currentness, staging and failure boundary

Caller/setup PRECONDITION for this offline checkpoint: LEAD's later runtime
admission names the sole publisher, exact destination and resolved existing
parent, and single-writer lease lifetime through staging/reverification/rename.
No concurrent external destination/parent writer is covered. This is trusted
caller authority, not an actor-supplied boolean, detectable global guarantee or
new output field. Do not add generic locks or claim platform no-replace safety.

At entry reject any destination entry with lexists semantics, including empty
directory, file, symlink and dangling symlink. Resolve the parent for the trusted
lease; do not follow/resolve away a destination entry before its lexists check.
Retain supplied receipt raw bytes;
public-verify the genuine store/final receipt, supported case/selection and empty
publication set. Bind exact current snapshot/pack/run/heads. Obtain ONLY actual
accepted `store.view()` with no candidate ticket; its run/status/current module
artifact identities must match those verified heads. Render through
`core_render.render(view)` with no injected ReportView, envelope View, local
financial facts or standalone component constructor.

Use the unchanged actual renderer and exactly-one
`<div id="call-root"></div>` anchor. Immediately after that anchor insert one
section id=delivery-scope-banner, class=banner, role=note,
data-delivery-scope=earnings-update-slice. Exact opening bytes:
`<section id="delivery-scope-banner" class="banner" role="note" data-delivery-scope="earnings-update-slice">`;
then `html.escape(fixed_outcome_text)` and `</section>`, with no added separator
whitespace. Use the oracle's fixed text for the actual outcome. Missing/duplicate anchor refuses. No dynamic invented
status, external assets, JS rewrite, numerical substitutions or manual SVG.

After rendering repeat public verification, exact raw-receipt stability and
snapshot/pack/head/View identity checks. Create a unique exclusively owned sibling
stage outside the execution store. Write the exact three files, compare exact
bytes/inventory and run the same read-only delivered verifier against that stage.
Immediately before rename repeat public verification/raw/currentness and
lexists(destination); destination/parent identity stays stable under the trusted
lease. Rename the sibling stage while that lease holds. Then read-only verify
the delivered directory, including final public/raw/currentness checks, BEFORE
returning success. The checks bind observations to this final state; they promise
no perpetual currentness after return.

Before-rename failure: no destination published by this call, cleanup ONLY its
owned unpublished stage. After-rename failure: preserve published directory as
forensic output, raise visibly, never report successful delivery or rollback.
Any prior output/input/store is immutable. Retry refuses an existing destination;
use read-only verification on it or a newly admitted exclusive destination. Do
not silently repair, overwrite, reseal or delete. Cleanup/read/write/rename errors
must remain visible, including chained expected IO errors; unexpected errors
propagate rather than catch-all success. Invalid/unverifiable inputs raise
ValueError. An expected error is never relabelled missing-source.

The public read-only verifier repeats the same actual A4 authentication, scope
and currentness checks; requires copied receipt bytes equal the supplied receipt;
requires a nonsymlink directory containing exactly three regular nonsymlink files;
rederives actual accepted View,
core HTML/banner and canonical metadata in memory; compares all exact bytes,
hashes, head order/status/qualification; and repeats raw/public/currentness checks
before returning None. No temporary envelope/store, receipt seal, repair or any
journal/file write is allowed. It may read renderer's embedded assets normally.

## Financial, provenance and visible FP02 expectations

Reuse A1/A3/financial/chart oracles exactly; no new formulas, math audit, score
prediction, source literals or QA interpretation. The oracle copies the existing
positive/gap numeric cell literals and references their immutable authorities.
A3's seeded component fixture prose does NOT describe actual owner status:
B1's actual stage and truthful seven Module limitations govern the real chain.
Keep actual CP1 restrictions/unaudited consolidated IFRS/USD millions, owner
analytical/source gaps and actual CP5 findings/status visible with full source
context. Do not blindly carry 'component preview/no actual owner' into a completed
run or upgrade it to broad qualification.

Positive q3-2025→q4-2025 flat earnings, cash/debt each+1.25 USDm and unchanged
net debt remain exact; display uses existing whole-million/percent/pp policy.
No-YoY fy-2024→fy-2025 keeps current FY2025 values while missing prior/deltas/
applicable growth remain missing. Opening-2024 balances are no annual comparison.
Drivers/guidance remain unsupported source gaps; a numeric variance is no causal
explanation. Prior trailing leverage remains missing while current is known.

All44 canonical CP1B facts, ordered three tables T1B.1/T1B.2/T1B.3, all12 genuine
lineages and the one cp1b-comparison own claim remain available through full
analysis/evidence/passports. Preserve actual primary/companion/source/period/
scale/basis/current artifact references and limitations; use no hardcoded report
C/K/S/G IDs. Four actual FP02 sections: Headline results, Variance drivers, KPI
changes and Guidance signals, with populated Full analysis routes to CP-1B.
Existing Evidence/Limitations and CP5/source routes remain reachable.

The existing CP1 chart projection already supports direct accepted/restricted
CP1 Facts; no financial envelope or Model publication is required. Use ordinary
`financial_series -> report_view -> ChartSpec/SVG` with FP02 S.1/S.2/S.3 only.
The unchanged chart oracle gives8/4/12 rows,24 points,nine genuine early-quarter
trailing gaps and four known undrawn-RCF zeros. Preserve exact quarter/source/
rolling-basis identities, chart/table twins and numeric/gap passports. Do not add
S.4 to FP02 or manufacture zero for missing ratios. The existing Model destination
may show CP1 detail and honest 'Model is not part of this Pathway' state; it must
have no fake publication/download. Missing-source case shows actual missing
source/refusal and no copied positive CP1/CP1B facts/charts.

## Checks, admission and bounded completion

Same existing independent sensitive contract review must pass this exact pair
before code admission; no new financial or governance chain. Root/PM names the
exact integrated B1/A4/delivery-contract/source revision and C2 exclusive files
before writing/running. C2's later code needs meaningful causal focused RED/GREEN,
confidence-review, changed-function no-argument rewrite-tournament and independent
sensitive review on exact final bytes. Missing public entrypoint/output behavior
is a causal RED; an unrelated import/collection failure is not.

Focused controls are frozen in the oracle: authenticated positive/no-YoY/genuine
source refusal; typed/raw/domain tampering; missing audits; stale source or View
around every publication phase; forged self-rehashed HTML; strict metadata and
inventory; existing/symlink destinations; IO/rename/post-publish recovery;
read-only verification; genuine zero/gap/unit/period/passport behavior. Seeded
component mocks can test presentation only, never qualify authentication or
actual analyst consumption. Do not run whole financial workflows merely for a
small pure formatting test.

Later LEAD admits each genuine fresh B1→A4 chain and sole-publisher destination
lease on exact frozen source, one heavy local job, with paid/provider/live paused.
Retain actual source-tool calls/five CP1 stages/QA/promotion/CP1B/CP5 participation,
consumer refs, final public receipts, source/runtime/input/output hashes and
argv/PID/UTC/exit. Reuse no old sealed workflow/output as a new analytical run.
Native proof on immutable authenticated packages covers all four FP02 sections,
CP1B+CP5 Full analysis, Evidence/Limitations/source context, exact numeric/gap and
source passports, S.1–S.3 Chart/Table and keyboard/mouse interactions, current
provenance and honest Model absence; negative covers genuine source/refusal.
Record browser errors and close only owned tabs/server. Preserve historical
financial/Model/chart deliveries unchanged. Only actual full chain, consumer and
render/native proof close this bounded checkpoint; broader PLAN remains open.

Not verified: B1/A4/delivery implementation or integration, actual fresh execution,
receipt authentication at runtime, delivered/native behavior, providers/production
or broader owner/pathway qualification.
