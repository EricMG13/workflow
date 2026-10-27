# C2 actual CP1 chart delivery and native proof

Actual read-only delivery and native interaction proof are complete for the new
positive CP1/Model chain and genuine missing-financial-source case. This is a
new doc-only C2 lease; prior handoffs, product code, sources, stores and canonical
publications were not edited. Integration remains PR MANAGER/LEAD's responsibility.

C2 proof branch: `codex/cp1-chart-proof`, base
`8f9ebe357a32f494bade6b128863a2fc88fbfa66`. The original product branch remains at
`3e5b537a22ae95638273503326a3ede7739f31fb`; no reset or forced fast-forward across
the cherry-pick ancestry was used. Untracked `work/` is preserved.

## Exact sealed inputs

Package root:
`/Users/ericguei/Documents/Codex/2026-10-26/deploy-workflow-lead/outputs/cp1-chart-slice`.
Input stores/receipts/publication are under `evidence/{positive,gap}`; new delivered
leaves are `positive/` and `gap/`. C1 alone performed actual analytical execution,
actual QA submission/promotion, publication, strict receipt seal and CLI EOF.
LEAD's independent reviewer froze/checked the QA expectation before submission.
C2 waited for seal/EOF and exact LEAD admission before consumption. Neither old QA58 nor old
calculation89b1 evidence was reused to qualify this chain.

| Identity | Positive | Gap |
| --- | --- | --- |
| Financial receipt SHA256 | `f4b17b0a092e770150ec4a806c74d3aff47b22804c9b22ae6b73e0c6aa4f1c51` | `abc42d9835f0ff7834674b80ab4aba8ad86b5bb5fceb25c6e9ac9bd5f81d0ed3` |
| Final snapshot | `8b0589817fc53cb0f14c89bff1b0bb5e0a39de085f1423b86d84e0d74123f2b8` | `3408c3601c1c66ca37c8d13aaae06e81792e45c4d640c5ab06aebb97c44f0004` |
| Pack | `75a96bc2109cc1e8e2ada38fbc064bf32b0e13cd6367c51536b103bed6fce9cb` | `ccc256569d1d644eea7d1982ae6cc09140275bcb3bc734048e07a4673dca2a8d` |
| Portable files / bytes | 203 / 305,595,205 | 73 / 126,426 |

Positive CP1 head:
`6d41c0a0b6782e4eace1f93d7b028f89041480b3d69721d6b69cfda4afcea8be`.
Positive Model head:
`d2420600276137c1810927f0ddd761c5e9a63420bd5452774721b1a911e5880f`.
The financial source remains
`82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429`.
The gap has `cp1_not_authorized`, null CP1/Model receipts and no Model publication.
Actual CP1/publisher refusals and source-attachment repair history remain in C1's
sealed audit; a rendered refusal alone is not the execution authority.

## Actual unchanged-wrapper deliveries

All calls used the public `render_financial_slice`, including its authentic
verification/rederivation passes. No direct composer, replacement verifier,
Execution mutation, old publication rewrite or financial recalculation was used.

Cwd: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2`.
Runtime: `/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python`, resolving to
CPython 3.13.15. Executable SHA256:
`7c72112b685250b1aec69081696d8fc04040ccefc34505ca56ac48ace7da8d5b`.
Environment: `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`; no dependency sync.
Wrapper SHA256:
`d511935ca9724de3ed734da87498f786742f2e63ca4a62a68408f9d136b089a8`.
Consumer SHA256:
`571ee44cbac0a39c3dd77871e13f7f9cc414c4e6700e9e887a70a64b74b7c4cc`.
Producer SHA256:
`9f4d0df14cb14e8dd3e8c3d0c7ed20afa9beadff2ced229a38047478e18caa8c`.

| Exact admission | PID | UTC on 2026-10-27 | Exit |
| --- | --- | --- | --- |
| C2-ACTUAL-CHART-POSITIVE-RENDER-1 | 65156 | 07:53:19.425732–07:58:50.284023 | 0 |
| C2-ACTUAL-CHART-GAP-RENDER-1 | 67409 | 08:01:00.349934–08:01:00.890244 | 0 |

Positive arguments: portable `positive/store`, `positive/receipt.json`,
`positive/model`, and the absent new delivered `positive/` destination. Gap uses
portable `gap/store`, `gap/receipt.json`, **actual Python None** for model_directory,
and the absent new delivered `gap/` destination. No `Path('None')` was passed.

The positive job preserved all 131 tracked source/test/case files, all 203 portable
inputs, preflight and runtime hashes. The gap job preserved all 131 source files,
73 gap inputs, runtime/preflight and all ten frozen positive output hashes.
Canonical HTML, calculation and publication receipt are byte-exact copies of the
new sealed publication. Report calculation JSON is byte-exact to canonical JSON.
Every render receipt file hash and current run/pack/snapshot/head identity matches.

| Delivered file | SHA256 |
| --- | --- |
| positive/report.html | `9d4cf37aae5c6295fd8ad0d2439cecd69f9b6b50924dec9cf52a39dd3397faf1` |
| positive/render-receipt.json | `5a9722879925642da9501146cdd6ac1e8fea2b6085c6f9402d626cea31c3b584` |
| positive/model/model.html | `af820b7ec0b342f39be07ea0660192da7b8fb88f8928f7b108fbcea4592fc4ce` |
| positive/model/calculation.json (and positive/calculation.json) | `739c32eeb0a4e5ed7c34a418e46633ae3f34b52fd6ff564730ce4b6fdb19938d` |
| positive/model/receipt.json | `e9209d38908451402607df6b45dad56ef78858c4bafe84af577e97b670c397ae` |
| gap/report.html | `dc27311a3aba43af9f9b569c75ecf741f9f9d7423e069a2cb945b315580329b6` |
| gap/render-receipt.json | `856d13628462fb6baa185e2ec3a11f1b0591ef359eef65013bbc31837c43e984` |

Gap output is exactly three files: report.html, render-receipt.json and the
byte-exact financial-slice.json receipt. There is no Model directory or calculation
file. Native checks below also verify no calculation link is offered.

Actual argv/env/cwd/PID/UTC/full logs and complete before/after inventories:
`artifacts/cp1-chart-actual-positive-render-1/{record.json,run.log}` and
`artifacts/cp1-chart-actual-gap-render-1/{record.json,run.log}` in the C2 checkout.

## Actual native browser proof

Admission `C2-ACTUAL-CHART-NATIVE-1` used one owned loopback server, exact pinned
`python -u -m http.server 0 --bind 127.0.0.1 --directory <package-root>`.
Server PID67570 bound port57026, starting 08:03:38.550681 UTC and ending
08:13:04.465067 UTC on 2026-10-27. It was deliberately terminated with SIGTERM:
child exit -15, recording parent exit0. No unrelated process was stopped.

Owned IAB tabs6,7,8 each bound a normal handle first on the tiny same-origin
root directory listing, then navigated to immutable report, canonical Model and
gap respectively. Supported CUA browser methods, bounded rendered DOM reads,
normal locators/keyboard input and screenshots were used. No full huge-page AX
export, native Codex-app route, app-state injection, protocol bypass, browser fetch,
engine, test, rerender or product edit was performed.

Both positive HTML destinations show four SVGs: line/line/line/grouped, with
8/4/12/1 focusable points (25 total), nine genuine gaps, four known-zero RCF points,
and one current principal50 at contractual2029-12-31. The maturity title names
principal at2025-12-31 and explicitly says not a forecast. All four actual
Chart/Table controls on each destination switch correctly and expose exact
8/4/12/1 twin rows. Each twin value text matches its corresponding mark.

Actual leverage, interest, zero-RCF and principal mark clicks open current
calculation/source passports. ArrowRight from K547 focuses G7125; Enter opens its
COMPONENT_MISSING/four-contiguous-quarters reason in both outputs. Full CP1 fact
controls expose exact total leverage
`1.6666666666666666666666666666666666667`, source cash16.25 USD MILLIONS/scale1000000,
current CP1 artifact, financial source hash and exact page quotes. The maturity
fact exposes2029-12-31, current q4-2025 identity, page5 terms, zero annual
amortisation and no forecast inference.

The actual clicked JSON retains Q4 metric values5/3,1,6; denominator EBITDA30 and
signed cash interest -5.00 with coefficient -1 use the365-day trailing-four-quarter
basis, with four actual quarter construction IDs. Own Q4 remains a distinct92-day
historical basis. Inspection only reads these retained Python results and operands;
C2 did not recalculate or substitute financial values.

Visible monetary labels follow adopted whole-million formatting: exact cash
16.25/17.50/18.75/20 appears as16/18/19/20. Exact amounts remain in numeric facts,
marks, JSON and full passports. Multiple labels are1.67x/1.00x/6.00x. No claim of
visible fractional cash labels is made.

### View-local companion references

Initial raw twin-label comparison differed: report period companion[S8] versus
canonical[S7]. Real search/result clicks on each token resolve identical current
financial source hash, page1 and exact quarter-date quote. Numeric mark DOM is
identical. All twin field/key/value data match after only that individually
verified companion alias; raw records/differences are retained. No blanket
reference renumbering or HTML mutation was used. This is resolved evidence
identity within each current view, not byte-identical presentation numbering.

### Calculation links, status and gap

Actual calculation.json anchor clicks in both outputs navigate respectively to
`/positive/calculation.json` and `/positive/model/calculation.json`. Each complete
clicked document was read in22 bounded DOM text chunks, reconstructed without
normalizing whitespace, and saved as2,128,882 bytes with exact canonical SHA256
`739c32eeb0a4e5ed7c34a418e46633ae3f34b52fd6ff564730ce4b6fdb19938d`.
This is actual link/DOM byte evidence; no truncated AX or direct filesystem copy
is presented as browser download proof.

Native CP1/Model routes show the new current head/pack references, QA59 Restricted/
Low, historical Model readiness and retained limitations. The visible T4.19 source
reconciliation register has77 rows. It is distinct from the actual producer's
technical/workbook readiness witness: four selected quarters and94 mandatory
checks, all94 PASS. That witness is in sealed positive evidence as
technical-readiness-summary.json, not inferred from the visible77 rows.

Gap front page states that financial analysis and Model publication did not run.
Its CP1 and CP-MODEL routes are Not run, with zero figures and no calculation link;
CP1 explicitly states that no calculation JSON has been emitted.

Tabs6/7/8 were closed and verified absent; the owned server PID is absent. Final
hashes match the initial131 source files,276 portable inputs,13 delivered files
and runtime binary exactly. All original and delivered publication bytes remain
unchanged. All resource admissions were released to LEAD before document closeout.

## Evidence and fact-review closure

Exact evidence root:
`/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2/artifacts/cp1-chart-native-1`.
Main files: browser-proof.json; server-record.json/http.log; report/canonical chart,
toggle, mark, full-fact, keyboard and status JSON; companion identity closure;
clicked JSON/byte proofs; gap front/CP1/Model DOM; owned-tab cleanup; screenshots;
confidence-review.md and sha256-index.json. Runtime render records are in the two
sibling directories named above. Evidence was written only to the admitted new
artifact directories; existing input/output leaves were not extended or edited.

Confidence review checks the handoff against primary execution records, actual
DOM/click captures, complete clicked JSON and final hash inventories. Confirmed
reporting hazards were closed: view-local passport numbers, whole-million display,
77 versus94 check scopes, controlled server exit -15, and exact JSON byte length.
An initial summary-inspection predicate used acct-prefixed keys and literal '-5'
where actual metric operands use unprefixed keys and raw '-5.00'. The final audit
requires four matching earnings operands and Decimal numeric equality while
retaining raw strings. Initial audit and corrected result are both preserved; no
financial result, product or browser source changed. An ambiguous Q1 cash locator
was inspected and restricted to the actual canonical-value identity before click.

The final native evidence audit passes21 explicit checks. No confirmed delivery
or native-proof defect remains. Rewrite tournament is skipped for this doc-only
lease; no non-trivial product code was written or modified during delivery/proof.
Paid/provider/live tests remain paused. Historical synthetic CP1/Model chart links
are the acceptance scope; other analytical owners, projections, legal perimeters,
real issuers and broader platform/provider qualification remain unqualified.
