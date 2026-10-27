# Task3-B financial rendering — component and bounded actual-case proof

Status: C2's three-file implementation is integrated at common d4fb848, and the
separately admitted actual positive/gap portable renders and native browser proof
are complete. The final update changes this owned handoff document only.
All22 focused component cases and renderer mypy pass. The initial Ruff I/F run
found one mechanical test import-order issue; that exact fix is AST-equivalent
apart from the three cached imports' order, and scoped I/F plus format now pass.
The actual evidence below is bounded to the historical synthetic CP1/Model slice;
it does not grant blanket analytical, native, chart-series or production qualification.
Paid/provider tests remain paused. No product/test/source bytes changed for proof.

## Exact lease, dependency and frozen inputs

Branch `codex/cp1-rendered`; original8d578801e2285194f98062b2d022ec94f33bb34f.
LEAD-authorized ff-only progression:904ab863 → b9b855c7 →4cc75da0 → exact reviewed
C1 integration base **2946639147e340ff34be749a589b2c886eb4cbbd**. Prior completed
branches and owned untracked work were preserved. No mutable C1 WIP was copied.
Selected coding/sensitive-review route: Sol/high, per explicit LEAD dispatch;
this records requested/selected route, not hidden provider telemetry.

Exactly three tracked files belong to this commit:

- `src/deploy_workflow/financial_rendering.py`
- `tests/test_financial_render.py`
- `docs/handoffs/financial-rendered-slice.md`

C1 alone owns all Execution transitions and actual core Model publication before
its final receipt seal. C2 only authenticates, exports/reads the real promoted
canonical envelope, renders the actual selected view and copies files. No source/
host/workflow/core/assets/bindings, old first-slice interface, shared registry/
contract/case/matrix/queue or provider/model setting was edited by C2.

C1 reviewed commit07ede0f7c92380b61452dc536cee635dbfcf8610 integrated as
e474e314e53d50770b452f16ece91290f68f5c2f; product/test bytes independently matched:

| Input | SHA-256 |
| --- | --- |
| C1 financial_workflow.py | 4f513165d4229c853dd7723cb3b9bbdb838b614cbb11a9ae5f818635a947da56 |
| C1 test_financial_workflow.py | 771af9a706f0883008b327e12e3e47ed17e90a8b6a8544ca7d18b784acd4621b |
| Final docs/CP1-MODEL-SLICE.md | 0bd7d5d9e5fdffb4f8b3016fb913105dbd1f2d19b8b263827de9120f0bf08250 |
| Final cases/financial/manifest.json | 6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432 |
| Final financial source | 82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429 |

Earlier source-layout/quarter-only preparations were superseded before C2 functional
runtime. Final V4 explicitly reports FY2025 plus its four quarters and opening
PERIOD_END2024, with by-function COGS/gross profit. NoFY2024/YoY qualification.
Independent source/financial expectations belong to LEAD's frozen cases; no parser,
anchor selection, financial engine or policy gate was rewritten to make them pass.

## Public seam and output

`render_financial_slice(execution_directory: Path, receipt_path: Path, model_directory: Path | None, destination: Path) -> Path`
returns destination/report.html. The actual C1 `FinancialSliceReceipt` and
`verify_financial_slice_receipt(store, receipt, *, model_directory=None)` are imported
lazily from the reviewed leaf; no substitute schema or private candidate is used.
Strict receipt consumer fields/signature matched integration without an API change.

Producer verification owns complete real audit, five-stage recomputation, promotion,
publication and currentness. Local guards check exact run/pack/snapshot, finite
selected CP1+CP-MODEL scope, genuine promoted/Model heads or actual gap, real View
status/identity, and raw publication hashes. The wrapper authenticates before view,
after rendering and after full staging, compares typed receipt and raw receipt/
publication bytes, then compares every staged byte before one destination rename.
C1 mutations or changed original/copy bytes fail closed with sanitized ValueError.

Positive destination contains:

- `report.html`: actual selected-run verified CP1/core view/build/maps, report-only
  historical scope banner; ordinary shipped routes/default preserved.
- `financial-slice.json`: byte-exact final producer receipt.
- `render-receipt.json`: actual raw file hashes, scope/run/pack/final snapshot,
  producer receipt hash, selected CP1/Model result identities and refusal state.
- `cp1/envelope.md`, `cp1/envelope.json`, `cp1/complete.json`: real core export/read.
- `model/model.html`, `model/calculation.json`, `model/receipt.json`: byte-exact
  canonical publication. No banner/default-route script is injected into Model HTML.
- `calculation.json`: exact duplicate beside primary report for its relative link.

Genuine missing-source negative: actual CP0 restricted, CP1/Model unrun, explicit
missing-source scope/limitation, no `model/`, `cp1/` or calculation.json. Forged,
stale, foreign or tampered positive inputs refuse entirely, never become an accepted
gap report. No new financial arithmetic, source permission or qualification write.
Existing destination is preserved. Publication precondition remains trusted setup's
exclusive writer to a unique new destination; no general cross-process atomic
no-replace claim is made for os.rename.

## Tests-first and actual focused verification

C2-FIN-RED-1 ran at904ab863 before the product module existed:
`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_financial_render.py::test_financial_rendering_entrypoint_is_available`.
Initial testfb323e6fe5cbda9b1880d00d459d6912f973fa6e6be94a53e223a11dfac951e2,
PID32584,2026-10-26T23:12:25.908980Z–23:12:26.105710Z,exit1,
1failed0.08s from explicit absent-entrypoint assertion, before producer setup.
Full log/record: `artifacts/financial-render-red-1{.log,-record.json}`. Slot released.

C1 agreed test-only `completed_financial_case(root, *, gap=False) -> (Executiondir,
receiptpath, Modeldir|None)` drives genuine bounded stages/core publication. C2 uses
it only after reviewed integration. Module fixture builds lazily once per positive/
gap key; each test receives isolated portable copies. No success mock or injected
final Module. These component builders are not actual participant acceptance.

Exact22-case GREEN-1 pytest command:
`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_financial_render.py`
— **22 passed in2673.07s (44m33s)**, originalPID41246,2026-10-27T00:25:50.345973Z
through01:10:23.725120Z,exit0. No restart, source edit or repeated positive pipeline.

Tests cover positive/gap real delivery, read-only selected state, exact receipt and
canonical Model bytes, real CP1 envelope, source-unit millions, FY/display-LTM versus
rolling-Q4 bases, signed outflow, actual RCF0, known gross profit, six early ratio
nulls, absentYoY, exact numerator/denominator/38-digit arithmetic and located quotes;
forged receipt/snapshot/pack/CP1/Model/publication and newline-only byte changes;
cross-case/unexpected-gap publication; existing destination; late render mutation
of journal/receipt bytes/publication; corrupted staged calculation/Model/envelope/
metadata; and journal mutation during staging.

Sequential admitted static commands:

1. Same Python/environment, `-m mypy --follow-imports=silent src/deploy_workflow/financial_rendering.py`
   — PID43865,exit0, no issues in1sourcefile.
2. `'/Users/ericguei/Documents/Deploy Workflow/.venv/bin/ruff' check --no-cache --select I,F src/deploy_workflow/financial_rendering.py tests/test_financial_render.py`
   — PID43868,exit1, exactly one test-local I001; closure below.
3. Same Ruff, `format --check src/deploy_workflow/financial_rendering.py tests/test_financial_render.py`
   — PID43869,exit0,2files already formatted.

Whole4command batch ended2026-10-27T01:10:23.976266Z, outer session71310 exit0.
Before/after hashes of every tracked src/tests/cases file, contract, pyproject and
owned source/test were IDENTICAL. No paid/provider call, new installation, source
permission, unrelated process kill, actual render/browser proof or broad suite.
Compute release reported immediately before handoff work; LEAD admitted C1's
actual financial runtime independently. No C2 runtime job remains held.

Full logs and complete command/PID/UTC/exit/before-after inventory:
`artifacts/financial-render-green-1-record.json`,
`artifacts/financial-render-green-1-{pytest,mypy,ruff,format}.log`.
Pytest log SHA6f74761d8e8d1beee6d5070b9e98c4f80ef5ba68d97fde69faf66e0a4f3c082c.

## Scoped lint closure and exact tested/final bytes

Integrated producer presence changed Ruff's import classification. The sole I001
required sorting exactly three test-local imports. No production or assertion/
fixture/oracle logic changed. All three modules are already loaded by the genuine
workflow/publisher fixture before this test body, so cached imports' ordering has
no new side effects. Reconstructed tested file hashes exactly3177aecd…; ASTs match
when only these three named local imports' order is normalized. Exact diff inspected
and retained. No additional45-minute pytest run for import sorting, per LEAD.

Static followup I/F and format both PASS; no broader Ruff pass is claimed. Records:
`artifacts/financial-render-static-fix-record.json`, `*-ruff.log`, `*-format.log`,
`artifacts/financial-render-import-order.diff`,
`artifacts/financial-render-import-order-proof.json`,
`artifacts/financial-render-tested-test.py` (exact tested-byte reconstruction).
This distinguishes original22-case tested bytes from the final mechanical test fix.

| Version | SHA-256 |
| --- | --- |
| Renderer, tested and final | d511935ca9724de3ed734da87498f786742f2e63ca4a62a68408f9d136b089a8 |
| Pytest-tested test file | 3177aecd779a3a12c5c507a60feaf18499129f7991cc79ff55410ac100019289 |
| Pytest source/test set | af110de1fb13595507f80098d4f0a89c8c56efb3ff78ab2a433add440eb1e4c5 |
| Final test after import sorting | 99059144b35d4c8d8cccee1ba4c4b6761ab06f9c45eb566c156ac063a4085b13 |
| Final source/test set | 239e353b6c3c17d0ef0857cdd114cf2b6327539252fdf200629acacfb87aa54a |

Set hash concatenates relative path UTF8+NUL+bytes+NUL, renderer then test.

## Separately admitted actual portable renders and native proof

These are genuine C1 bounded participant runs, independent of the component helper.
C1 alone performed source access, all six valid stage submissions, actual promotion,
Model publication and final producer receipt seal. C2 consumed the LEAD-created
portable copies read-only. Only corrected **positive-2** was consumed: the earlier
positive selector failure remains retained and was never presented as acceptance.
The corrected run selected the four source-linked QUARTER constructions, reached
actual Model readiness before QA, passed all94 mandatory input checks, and matched
the fresh independent QA expectation **58 / Restricted / Low**. Its CLI PID45650
closed on EOF with exit0 at2026-10-27T01:47:22.308Z before C2 admission.

Portable package root:
`/Users/ericguei/Documents/Codex/2026-10-26/deploy-workflow-lead/outputs/cp1-model-slice`.
Positive inputs are `evidence/positive/{store,receipt.json,model}`; gap inputs are
`evidence/gap/{store,receipt.json}` with no Model directory. LEAD verified all156
positive and40 gap input files byte-for-byte, without symlinks. C2 recorded its own
complete before/after inventories. Outputs are exclusive new `positive/` and `gap/`
leaves. No Execution, producer receipt, source, or canonical publication was edited.

| Actual identity | Positive-2 | Missing-source gap |
| --- | --- | --- |
| Producer receipt raw SHA-256 | bbbee0075581797e9cb916fe79b939b6c9ef03d521405da1afc3d0946cf8ce61 | 929fd192bdd933e6fe1fdbcf11dcd06e0e194f8e7046ee7905df89acb4963896 |
| Pack SHA-256 | 75a96bc2109cc1e8e2ada38fbc064bf32b0e13cd6367c51536b103bed6fce9cb | ccc256569d1d644eea7d1982ae6cc09140275bcb3bc734048e07a4673dca2a8d |
| Final snapshot SHA-256 | 17a4027d4a5c45143ae14b04a5966d12b533f1c512fb738eeca243de39b319ef | 4696cdafc9c31f34f723849955891ff61cdb789a61046397a9731d4e44d6b441 |
| Selected CP0 result | f08dbf0d771244aabea370c829523141bd790c4854657d21979cc42334cba30b | f5385793cd243ae5e9e1b8ab132ad06654848ce7f98610456798ff980347495c |
| Selected CP1 result | 87af2b93ae1e2a30df57fe0997c1e89f75bee07932501c7074d51155e59f846f | unrun; actual begin refused |
| Selected Model result | c6a8d3d0f909342fe4de15ffae183ca9dd9852f94ab21788c12f91f9274e5bbe | unrun; actual publisher refused |

**C2-ACTUAL-POSITIVE-RENDER-1**: one unchanged `render_financial_slice` call with
all three real public authentications; PID46685,2026-10-27T01:50:08.990672Z through
01:55:18.253842Z, actual exit0. All156 inputs and the source/test/case inventory
were unchanged. Exactly10 output files; canonical three-file publication copied
byte-for-byte, and the co-located calculation equals its canonical counterpart.
The full command, script hash, PID/UTC, input inventories, metadata and output hashes
are `artifacts/actual-positive-render-1/{run.py,run.log,record.json}` in C2's clone.
No extra verifier, pytest, helper, Model builder or provider job ran.

**C2-ACTUAL-GAP-RENDER-1**: one unchanged call with `model_directory=None`;
PID45823,2026-10-27T01:33:24.812629Z through01:33:24.913871Z, exit0. All40 inputs
unchanged. Exactly `report.html`, `financial-slice.json`, `render-receipt.json`;
no `model/`, `cp1/` or calculation JSON. Evidence is
`artifacts/actual-gap-render-1/{run.py,run.log,record.json}`.

| Actual output | SHA-256 |
| --- | --- |
| Positive report.html | 4dbdfc091d02174d12ea9d0941b43d0294d6a4ab53d58bd3b441ec36981daf95 |
| Positive render-receipt.json | 2b10f68d6287d118ca7e816e753409837eb1ad7e1716f6a3f70c2d1f493f1bd2 |
| Canonical model/model.html | 6be1d2ec79ccb1b6bdbf233c2334bcb10c9c82d289581e491d2cfff9616a8dfc |
| Both calculation.json copies | 89b1bf3b48d214ab2b600d7f3ead534f6f2aaa2d8ab44f2cf36214ca99a13d8c |
| Canonical model/receipt.json | 265e6c2dc70f060ca5209564a4fe6aca78ad37a8cfd48ba3b6ac01413a8cc8d4 |
| Gap report.html | 51a0f1fbe6b47574b5ef04992647b72775079167bb432b88f37fd12b7523eb3e |
| Gap render-receipt.json | 510633ff962bb2963859e0711b522e52a4e7ced1dff53038a97dcca1cf13ab0a |

**C2-ACTUAL-POSITIVE-DOM-1 / C2-ACTUAL-POSITIVE-NATIVE-RECOVERY-1** used the
unchanged positive leaf on owned127.0.0.1:54227 serverPID47199 and only owned
native IAB tab5. The ~63MB HTML exceeds the full-page AX bridge frame limit.
Codex native-app computer-use access was safety-denied; that route was closed.
Purpose-built navigation moved the same owned tab to the small calculation JSON,
allowing a normal browser handle to bind. All subsequent work used supported
native browser screenshots, actual UI clicks, public role locators and bounded
read-only DOM. No OS automation, private API, page injection, alternate report,
or replacement screenshot was used. Full-page AX success is not claimed.

Actual positive observations:

- Bare report shows the Front Page, issuer/as-of/synthetic/method identity and
  historical-financial-only scope. Actual financial/capital tables and chart
  destination/KPI table fallback come from CP1 maps. Chart plots remain `n/a`:
  the shipped core says no S.1-S.4 producer series exists yet. No plotted-series
  qualification or new chart code is claimed.
- CP1 QA shows Restricted, confidence58(Low). Model readiness shows `ready` for
  the retained historical quarter scope. All77 displayed reconciliation rows
  show PASS; this UI count is distinct from C1's94 mandatory gate checks.
- Period register shows opening PERIOD_END, four dated QUARTERs and FY2025 in
  USD/MILLIONS. Separate reported FY, constructed display-LTM and rolling-Q4
  bases remain inspectable. Native clicked JSON retains the four rolling quarter
  construction IDs/365days, calculated EBITDA30 and FCF9, plus computation refs.
- Clicked Q4 Revenue passport shows source30, currencyUSD, scale1000000,
  2025-10-01..2025-12-31, full financial source SHA
  `82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429`,
  `page:2`, exact quote `Revenue  30  30  30  30  120`, and full current CP1
  artifact `87af2b93ae1e2a30df57fe0997c1e89f75bee07932501c7074d51155e59f846f`.
- Six exact Q4 operand passports show50/30 leverage,7.5/30 own EBITDA margin,
  and2.25/7.5 own FCF margin, all bound to that CP1 result. Source outflow is
  -2.5 with the located parenthesized capex quote. RCF commitment is known0;
  early leverage is missing/Not Calculable with its four-quarter reason, while
  prior-year growth is Not Available/not applicable, never fabricated zero.
- Actual report calculation link was clicked and opened the same-origin JSON
  in the same owned tab. Canonical `model/model.html#CP-1` and `#CP-MODEL`
  function; provenance exposes full CP1/pack/calculation hashes. Canonical Model
  HTML has no injected delivery banner. Its relative calculation link was also
  clicked. Twenty-two bounded DOM text reads reconstruct the exact2,108,966bytes
  with raw SHA89b1bf3b..., equal to both frozen canonical/report calculation files.
- Initial large AX JSON text adds two layout spaces at1MiB boundaries; an initial
  single DOM response hit the tool's200000-character string cap. Those failed
  comparisons remain retained. The successful bounded DOM witness is byte-exact;
  neither initial mismatch is misrepresented as a raw-body success.
- Evidence and Limitations show unaudited supplied pages, missing prior-year
  comparisons and the actual restrictions. Remaining analytical owners and
  forward projections stay unqualified. This is a bounded synthetic case.

Native positive proof index: C2
`artifacts/actual-positive-dom-1/browser-proof.json`, SHA
`95514c82a5b7d287d947f2b740578a36cf55cc8c5010918a643b59df54c391e8`:
22 checks true and54 indexed artifacts. Owned tab5 closed and inventory confirms
absence, no child tabs created. Server exited0 at2026-10-27T02:17:44.603743Z;
all10 served file hashes before/after identical. Compute/browser resources released.

**C2-ACTUAL-GAP-DOM-1** used only immutable gap leaf on owned serverPID45924/
127.0.0.1:53970 and native IAB tab4. Full native AX and screenshots show actual
default scope/identity, financial missing/Not supplied/blocked, CP0 CONDITIONAL /
DO NOT RUN, honest Limitations, CP1 and Model Not run, no calculation/publication
link or Model directory. Actual authority passport shows full identity source SHA
`74fe2ad422266bc01a43af025fed0aca5fdb5aa952c60c013efbbef0ba816ec4`, `page:1`,
quote `Northbridge Synthetic Group is the issuer and consolidated group.`, and
full actual CP0 result f5385793.... Explicit CP0 route survives reload.
Index `artifacts/actual-gap-dom-1/browser-proof.json`, SHA
`627904890c7be514f8a91eeb0f5a0ad509c521678010e01dc65f3a175f4f2c08`:
14 checks true/24 indexed artifacts. Owned tab4/server closed; server exit0 at
2026-10-27T01:39:22.585498Z and all3 leaf hashes unchanged.

Final proof confidence review investigated wrong-run/component substitution,
misleading byte equality, native recovery boundaries, qualification/count/precision
overclaims, input immutability and cleanup. Actual records close those points;
the full-page AX/chart-series/broader qualification limits remain explicit.
Evidence: `artifacts/actual-positive-render-1/confidence-review.md` and
`artifacts/actual-positive-dom-1/confidence-review.md`. No confirmed product issue.
No-argument rewrite tournament is skipped for this final doc/test-proof-only work;
no product function changed. Existing component tournament closure below remains valid.

## Confidence review — component consumer and tests

Least confident about (ranked), investigated to the real boundary:

1. Locally plausible receipt fields could bypass actual participation/promotion.
   Real strict C1 verifier is called three times; integrated schema/API was traced,
   actual component lineage is used, forged receipt/artifact cases all refuse.
   Verdict: verified fine within reviewed producer contract; no local fake schema.
2. Positive state could be mislabeled as a gap or foreign/stale heads mixed.
   Disjoint fixed-refusal/positive guards, real View identity and selected heads;
   genuine negative, cross-case, source/current blob and unexpected publication
   causals all passed. Verdict: verified fine; no inferred Model-readiness gate.
3. Raw-equivalent or late mutation could escape currentness checks.
   Typed/raw bytes/publication checks surround rendering/staging. Receipt reformat,
   original publication and snapshot changes, staged Model/calc/envelope/metadata
   corruption and staging journal change all passed causal refusal. Verdict: fine.
4. Rendering/export might show a candidate or write Execution.
   Real write/read promoted envelope plus actual Execution.view/core render;
   supported signatures and strict mypy pass. Positive store snapshot unchanged,
   core copied publication and exported envelope verify. Verdict: fine.
5. Wrong scale or same-valued ratio could conceal wrong period/operands.
   Independent frozen source-unit literals, separate FY/display/rolling/Q4 bases,
   dates/units/operand references,5/3 at38digit half-even, own7.5/30margin,
   source citation hash/locator/quote, RCF0 and explicit early ratio/YoY nulls all
   passed. Lightweight read-only JSON spot-check corroborated. Verdict: fine.
6. Canonical Model might be changed or relative calculation link broken.
   All canonical3file bytes copied unchanged, root/nested calculation identical,
   report-only scope copy. Both source-only corruption and destination-copy-only
   corruption refuse. Verdict: component verified; the separately admitted actual
   native click/DOM closure is recorded above.
7. Failure cleanup could expose partial files/overwrite existing delivery.
   Complete adjacent staging/final byte equality; existing destination preservation
   and all late-failure cases pass. Verdict: fine within adopted exclusive setup
   writer; cross-process no-replace guarantee is explicitly outside scope.
8. Shared expensive fixture could leak mutation or rebuild per test.
   Lazy bool-keyed module cache builds each genuine baseline once, per-test copies
   isolate mutation, all22 pass. Negative-only smoke remains lazy. Verdict: fine.
9. Integration/lint cleanup might invalidate tested behavior.
   Exact dependency bytes/hashes, scoped compile, no API adjustment. One confirmed
   I001 fixed by exact cached import reorder; before/after normalized AST identical,
   diff inspected and scoped static checks pass. Verdict: fine; no product change.

Fixed: mechanical test import ordering only after integration. No confirmed product
renderer defect from sensitive/confidence reviews or full runtime cases.
Verified fine: authority/currentness/state/canonical copy/causal refusal/caller types
and raw identities with evidence above. By-design: unique trusted destination writer,
implementation-only qualification, no local arithmetic or analytical permission.
At the component baseline, actual actor/raw-QA/native proof remained open. Those
bounded actual cases are now closed by the separate evidence above, not inferred
from component tests. Broader qualification and populated chart series remain open.

Independent read-only Sol/high render_sensitive_review checked initial product
4260bdd1… and Memory-only delta57e3574…/test-oracle shapes at amended frozen base.
No concrete local defect or oracle misinterpretation. Later V4 changes were global
honest scope copy and test-only independent source expectations/lazy setup/import
sorting; no material production-function logic change. Integrated runtime/caller
uncertainties from static review are now closed by22cases+mypy, not assumed away.

## No-argument rewrite tournament — closed with runtime evidence

Targets: `src/deploy_workflow/financial_rendering.py` — `_verified_financial_view`
lines31–108 and `render_financial_slice` lines111–214 (the only two material product functions). Impact set via rg: helper's three wrapper calls,
focused test entrypoints and frozen public consumer API; no shared re-export.
Invariants: signatures/return/error/side effects, actual public producer verifier,
three auth passes, no Execution transition, real core envelope/view/render,
exact bytes/state/gap, canonical layout and complete staged refusal/publication.

Separate Incumbent/Speed/Memory/Readability roles plus blind Arbiter; at most two
roles active together. Anonymous A=Speed incumbent-preserving abstention,
B=Memory, C=Readability incumbent-preserving abstention, D=Incumbent.
B wins A/B, B/C, B/D; no semantic disqualification. Backup before apply:
`artifacts/financial-rendering-before-tournament.py`; anonymous candidates/bracket:
`artifacts/financial-render-tournament-anonymous.json`.

Winner: **Snippet B (Memory)** replaces the two scoped functions; helper unchanged.

- Releases envelope, rendered View and original HTML after their last use.
- Releases second verification's full receipt/View/publication before final auth.
- Preserves every authentication/filesystem call/byte/error behavior. Complexity
  unchanged; memory savings unmeasured, no performance benchmark claimed.

Orchestrator verified exact source diff, actual focused command22PASS, strict caller
mypy and scoped static checks. Concrete invariant in already-passed component output:
canonical root/nested calculation and raw producer receipt copies equal; Q4 rolling
revenue120M, FYgross60M, RCF0, leverage50/30=5/3 at38digits, ownmargin7.5/30 on a
different basis. This was read-only stdlib JSON over passed artifacts, no new core
execution/renderer or actor/browser acceptance. Evidence `artifacts/financial-render-invariant.json`.

Component spot-check identities: snapshot `816c99a052f5be275c903409256a8a76c789f43019a6bd04182798fc69b72d13`,
CP1 `ca43fceedfe01e138171a2be019b469071ea420864ebe5376037337a39c06c67`, Model `5f12c1fa795ebc9261c6fa080c88695f0aa80adbaa552e3403a2e70643d30bd7`,
calculation `1ee36aa854af7b22839c920c70ad25bf44f23fee890ab3ebcbbd3aac163a86e2`. These are component identities only.

Final winning code (imports/constants included):

```python
"""Read-only delivery of authenticated CP1 financials and a published historical Model."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from deploy_vii import render as core_render
from deploy_vii.contracts import View
from deploy_vii.cp1_render import envelope_view
from deploy_vii.cp1_workflow import read_cp1_envelope, write_cp1_envelope
from deploy_vii.execution import Execution

if TYPE_CHECKING:
    from deploy_workflow.financial_workflow import FinancialSliceReceipt

_MODEL_FILES = frozenset({"model.html", "calculation.json", "receipt.json"})
_POSITIVE_SCOPE = (
    "Historical financial analysis and Model publication only. "
    "Remaining analytical owners and forward projections remain unqualified."
)
_NEGATIVE_SCOPE = (
    "Financial source missing. CP1 financial analysis and Model publication did not run."
)


def _verified_financial_view(
    store: Execution, receipt_path: Path, model_directory: Path | None
) -> tuple[FinancialSliceReceipt, bytes, View, dict[str, bytes]]:
    # Only the producer's public strict schema/verifier authenticates the
    # participant audit, all five stages, promotion and publication. No local
    # replacement schema or private candidate constructor grants that authority.
    from deploy_workflow.financial_workflow import (
        FinancialSliceReceipt,
        verify_financial_slice_receipt,
    )

    raw = receipt_path.read_bytes()
    receipt = FinancialSliceReceipt.model_validate_json(raw)
    verify_financial_slice_receipt(store, receipt, model_directory=model_directory)
    snapshot = store.read()
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or store.pack(snapshot).content_hash() != receipt.pack_sha256
        or snapshot.run != receipt.run
    ):
        raise ValueError("stale_financial_slice")
    if set(snapshot.run.requested_modules) != {"CP-1", "CP-MODEL"}:
        raise ValueError("outside_financial_slice")
    heads = {head.module_id: head for head in snapshot.heads}
    publication: dict[str, bytes] = {}
    if receipt.refusal is not None:
        if (
            receipt.refusal != "cp1_not_authorized"
            or receipt.cp1 is not None
            or receipt.model is not None
            or model_directory is not None
            or set(heads) != {"CP-0"}
        ):
            raise ValueError("invalid_financial_gap")
    else:
        if (
            receipt.cp1 is None
            or receipt.model is None
            or model_directory is None
            or set(heads) != {"CP-0", "CP-1", "CP-MODEL"}
            or receipt.cp1.status not in {"accepted", "restricted"}
            or heads["CP-1"].status != receipt.cp1.status
            or heads["CP-1"].result_sha256 != receipt.cp1.result_sha256
            or heads["CP-MODEL"].status not in {"accepted", "restricted"}
            or heads["CP-MODEL"].result_sha256 != receipt.model.result_sha256
            or receipt.model.cp1_result_sha256 != receipt.cp1.result_sha256
            or set(receipt.model.files) != _MODEL_FILES
        ):
            raise ValueError("invalid_financial_publication")
        publication = {name: (model_directory / name).read_bytes() for name in _MODEL_FILES}
        if any(
            hashlib.sha256(raw_file).hexdigest() != receipt.model.files[name]
            for name, raw_file in publication.items()
        ):
            raise ValueError("changed_model_publication")
    view = store.view()
    modules = {module.module_id: module for module in view.modules}
    if view.run != receipt.run:
        raise ValueError("foreign_financial_view")
    for module_id in ("CP-1", "CP-MODEL"):
        shown = modules[module_id]
        if receipt.refusal is not None:
            if (
                shown.status != "unrun"
                or shown.artifact_sha256 is not None
                or shown.facts
                or shown.tables
                or shown.claims
            ):
                raise ValueError("invalid_financial_gap_view")
        elif (
            shown.status != heads[module_id].status
            or shown.artifact_sha256 != heads[module_id].result_sha256
        ):
            raise ValueError("invalid_financial_view")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise ValueError("stale_financial_slice")
    return receipt, raw, view, publication


def render_financial_slice(
    execution_directory: Path,
    receipt_path: Path,
    model_directory: Path | None,
    destination: Path,
) -> Path:
    """Render the selected run and copy its verified publication into a new destination.

    Trusted setup owns every path and exclusively owns the new destination.
    Authentication is repeated after rendering and before complete staged export;
    no Execution transition or analytical/rendering qualification is performed.
    """
    execution_directory, receipt_path, destination = (
        Path(execution_directory),
        Path(receipt_path),
        Path(destination),
    )
    model_directory = None if model_directory is None else Path(model_directory)
    store = Execution(execution_directory)
    try:
        receipt, raw, view, publication = _verified_financial_view(
            store, receipt_path, model_directory
        )
        if destination.exists():
            raise ValueError("destination_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".financial-slice-", dir=destination.parent) as temporary:
            stage = Path(temporary)
            files = {"financial-slice.json": raw}
            if receipt.refusal is None:
                # These APIs export/read the genuine promoted head. They only
                # write export files, never the Execution journal or its heads.
                envelope_directory = stage / "cp1"
                write_cp1_envelope(store, envelope_directory)
                envelope = read_cp1_envelope(store, envelope_directory)
                view = envelope_view(view, envelope)
                del envelope
                files.update(
                    ("cp1/" + name, (envelope_directory / name).read_bytes())
                    for name in ("envelope.md", "envelope.json", "complete.json")
                )
                files.update(("model/" + name, body) for name, body in publication.items())
                # The real Model panel links a basename relative to report.html.
                files["calculation.json"] = publication["calculation.json"]
                scope = _POSITIVE_SCOPE
            else:
                scope = _NEGATIVE_SCOPE
            html = core_render.render(view)
            del view
            anchor = '<div id="call-root"></div>'
            if html.count(anchor) != 1:
                raise ValueError("financial_scope_target_missing")
            banner = (
                '<section id="delivery-scope-banner" class="banner" role="note" '
                'data-delivery-scope="historical-financials">' + scope + "</section>"
            )
            files["report.html"] = html.replace(anchor, banner + anchor, 1).encode("utf-8")
            del html
            checked, checked_raw, checked_view, checked_publication = _verified_financial_view(
                store, receipt_path, model_directory
            )
            if checked != receipt or checked_raw != raw or checked_publication != publication:
                raise ValueError("stale_financial_slice")
            del checked, checked_raw, checked_view, checked_publication
            metadata = {
                "schema_version": "cp1-model-slice-render/1",
                "scope": scope,
                "run": receipt.run.model_dump(mode="json"),
                "pack_sha256": receipt.pack_sha256,
                "snapshot_sha256": receipt.snapshot_sha256,
                "financial_receipt_file": "financial-slice.json",
                "financial_receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "cp1_result_sha256": None if receipt.cp1 is None else receipt.cp1.result_sha256,
                "model_result_sha256": None
                if receipt.model is None
                else receipt.model.result_sha256,
                "refusal": receipt.refusal,
                "files": {
                    name: hashlib.sha256(body).hexdigest() for name, body in sorted(files.items())
                },
            }
            files["render-receipt.json"] = (
                json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            ).encode("utf-8")
            del metadata
            for name, body in files.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
            final, final_raw, _, final_publication = _verified_financial_view(
                store, receipt_path, model_directory
            )
            if (
                final != receipt
                or final_raw != raw
                or final_publication != publication
                or destination.exists()
                or any((stage / name).read_bytes() != body for name, body in files.items())
            ):
                raise ValueError("stale_financial_slice")
            os.rename(stage, destination)
        return destination / "report.html"
    except (ValueError, OSError):
        raise ValueError("financial_slice_render_refused") from None
```
