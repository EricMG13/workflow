# Task3-A rendered source slice — implementation and actual DOM proof

Status: C2's leased renderer is verified locally against both genuine C1 participant
stores. Integration and the assembled focused check remain LEAD/PR MANAGER work.
This is finite source-readiness delivery, not financial analysis or Model completion.

## Exact lease, dependency and immutable inputs

C2 branch `codex/rendered-slice`; original start
`a5b240c41561d7b73544dc3039d73304a22c8928`. LEAD authorized the ff-only update to
reviewed integration base `959e652c4d104b7aab05870ca41520473ba02a30`. C1 producer
`61187e75fa272a724ae00b5dbef1ff6206ea5209` landed there as
`de6ac31e02ac3ea02b31c2836a794ce7ba7706dd`; exact producer bytes matched.
No mutable C1 product files were copied. Prior branches/history were preserved.
Selected coding/review route: GPT-6.1 Sol/high; no hidden telemetry asserted.

Exactly three tracked paths belong to this lease:

- `src/deploy_workflow/rendering.py`
- `tests/test_connected_render.py`
- `docs/handoffs/rendered-slice.md`

No shared contract, workflow/host/tools, imported renderer/assets/bindings, registry,
manifest/matrix/queue or provider/model setting was changed by this commit.

| Immutable input | SHA-256 |
| --- | --- |
| docs/SLICE-CONTRACT.md | c1970233fd69aa5c7cf5b0a73156a7323eddcc894bd97a4cd558765c023dfb77 |
| cases/connected/manifest.json | 30b383bd397ecf1c99f3f49d02674605d8ad9c6868da4b4f205124942d731df1 |
| docs/SOURCE-SLICE-API.md, LEAD fbdda49e8288a17e20298ba352fba119ad40845a | 15201bd0e66868f5cf058b1f92ee217b4f18974b8504fb4c3ec9c9356e8c20d4 |
| src/deploy_workflow/rendering.py | 682eeb973428fba5f69d4274d1210f60e09de144bfa407cfa7bfaae7ba917fca |
| tests/test_connected_render.py | aa84b987c49ed0ff7fb56e67da22a70be10d5a85e88bcba831ee3410c386a30f |
| Ordered source/test set | 9d8f82b80f31d3978ab54dfdd2d96723e50f7c76401628fd323dccb0d3942d92 |

Source-set hash is SHA-256 of relative path UTF-8 + NUL + exact file bytes + NUL,
in rendering.py then test_connected_render.py order. It remained frozen throughout
GREEN, both actual render calls and native DOM proof. Later edits are this handoff only.

## Behavior and publication scope

`render_source_slice(execution_directory, receipt_path, destination) -> Path` uses
C1's actual strict `SourceSliceReceipt` and public `verify_source_slice_receipt`.
It checks current snapshot/pack/run/CP0 lineage; positive pending valid source_context
or actual gap refusal; then real `Execution.view()` and the shipped renderer/build/maps.
It never submits, settles or promotes a module. Delivered CP1 is `Not run`, and
CP-MODEL is `Not in this Pathway`. Exact persistent banner:
`Source readiness only. Financial analysis and Model publication remain unrun.`
Bare HTML URLs select Evidence through a fixed navigation-only script before app
bootstrap; explicit fragments are preserved. Existing renderer assets are reused.
The bundle contains exactly `report.html`, `render-receipt.json`, and byte-exact
`source-slice.json`. Metadata binds actual HTML bytes to source receipt, run, pack,
snapshot, CP0 result/step and CP1 ticket/output or refusal. Authentication is repeated
after rendering and after full staging; changed typed data or raw receipt bytes refuse.

LEAD's adopted publication precondition: trusted setup exclusively owns a unique new
destination. Existing destinations refuse at initial/final checks. Concurrent outside
creators are outside v1. Staged `os.rename` is not claimed to provide cross-process
atomic no-replace. No extra concurrency machinery or general guarantee is introduced.

## Focused tests and exact runtime admissions

Tests were authored first. C2-RENDER-RED-1 ran the entrypoint test while rendering.py
was absent: PID22194, 2026-10-26T22:00:51.093650Z–22:00:51.447639Z, exit1,
1 failed/0.20s from the explicit missing-entrypoint assertion before producer setup.
Initial test SHA e2bd9532ab68857d5b67bf34f81adb9b5ba438e0a5dc09fec787ae144ff2cfb0;
log `artifacts/render-red-1.log`. The slot was released immediately.

C2-RENDER-GREEN-1 used exact base/source-set above and these sequential commands:

1. `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' -m pytest -q tests/test_connected_render.py`
   — PID26337, 22:35:08.676235Z–22:35:10.607292Z, exit0, **14 passed in 1.71s**.
2. Same environment/python, `-m mypy --follow-imports=silent src/deploy_workflow/rendering.py`
   — PID26338, exit0, no issues in 1 source file.
3. `'/Users/ericguei/Documents/Deploy Workflow/.venv/bin/ruff' check --no-cache src/deploy_workflow/rendering.py tests/test_connected_render.py`
   — PID26342, exit0, all checks passed.
4. Same Ruff, `format --check src/deploy_workflow/rendering.py tests/test_connected_render.py`
   — PID26343, exit0, 2 files already formatted; batch ended22:35:11.781893Z.

Records/logs: `artifacts/render-green-1-record.json` and
`artifacts/render-green-1-{pytest,mypy,ruff,format}.log`. Slot released.
Cases cover real SourceWorkflow positive/gap stores, metadata/source status,
forged receipt/snapshot/pack/CP0/CP1 bytes, foreign cross-case receipt, state mutation
during rendering and staging, raw receipt byte changes, destination preservation,
and forged recorded tool body while journal/heads remain unchanged. The last case
requires the public producer verifier; local hashes alone cannot authenticate it.
Component review payload builders reuse C1 test shapes over the frozen manifest.
They do not stand in for actual participant evidence; the separate runs below do.
No mock View/final Module/accepted injection, provider call, install or broad suite.

## Genuine C1 stores and actual rendering

C1 ACTUAL-SOURCE-1 used bounded JSON-lines sessions: the participant inspected returned
bodies before authoring raw reviews. Positive: four CP0 and four CP1 source-context
successful tool calls. Gap: three CP0 successful calls; CP1 admission actually refused,
with no CP1 ticket, tool call, submission or output. These are separate from pytest.

C1 root: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1`.

### Positive identities

- Execution: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/runs/task3-source-positive`
- Producer receipt: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-positive/receipt.json`
- Raw receipt SHA: `90925e534fc895fac5bb2d9dd28e4e2d7c7d23e94dcc49378ae949a594b47e02`
- Snapshot SHA: `3fda7b283bef6cb6ff753b65cebc9abf2c3f8fac1ad2372d562ccc1e2f1501a4`
- Pack SHA: `bc15096a011a4f8d431b36489fb63e6ff1d2b6e2e607b907c12bd20d8f2ecd85`
- Restricted CP0 result: `c6e7f209aabe1dd6054e3c989a524220a29e63f5e18836992ed8885c1c97c9bc`
- Pending CP1 ticket: `45dedb96-2443-4dda-a83d-a7a2beceeffd`
- Valid restricted source_context output: `e3374cae828bf077c62cb29789296cbbb65c0788cadca073d0c91364327917f4`
- Actual HTML: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2/artifacts/source-slice-delivery-1/positive/report.html`
- HTML SHA: `371bbc18c8ee68fb7fc9b5151c67a90f37511e5829ad99f14be5444887180a9d`

### Gap identities

- Execution: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/runs/task3-source-gap`
- Producer receipt: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-1/artifacts/source-slice-gap/receipt.json`
- Raw receipt SHA: `cf07e26d18ae733b60bee6c6dad389edbdec8fc7a2cf13e828729cc6be19d76a`
- Snapshot SHA: `45bb2376b6bc3b3dae72a6674f0ba375311d4a34c367e471a9f48abb788a04ca`
- Pack SHA: `f5b1192fcfb401681b648ee2d3a4b83e738ba9c2fca8df821283e4b9eb4b0c61`
- Restricted CP0 result: `9a14f88e74247a9fa388cb20a47495c248da2244cf9032b7993c21b7b3819668`
- Actual CP1 refusal: `not_authorized`; no consumer output.
- Actual HTML: `/Users/ericguei/Documents/Deploy Workflow Sessions/coordinator-2/artifacts/source-slice-delivery-1/gap/report.html`
- HTML SHA: `3ca8219afc608e30e405747d033397df33b1acd69610beec460b587d407e967d`

ACTUAL-RENDER-DOM-1 admitted exactly two render calls on these immutable stores.
PID26426, 2026-10-26T22:39:23.410318Z–22:39:23.702599Z; both succeeded. Original
source snapshots remained byte-hash identical before/after rendering and at final
proof indexing. Every bundle file still matches the recorded SHA. Full metadata,
consumer identities and literal source/citation spans: `artifacts/source-slice-proof-1/render-record.json`.

## Native browser proof and cleanup

Current native IAB capability was established in separately admitted C2-BROWSER-CAP-1:
fixed JS probe hash a86e69d7bcd6748014539dccceaf5b144cd61a2a5ac77e4c2a4581767e237c92,
actual `native-dom-ready` heading. Probe PID23228/port50370 and tab1 were closed;
receipt `artifacts/browser-capability-receipt.json`. No Chrome fallback/harness needed.

Actual report proof used native IAB browser3, owned temporary tabs2/3, and one stdlib
loopback server serving only immutable delivery bundles. Actual AX observations and
native screenshots, without hidden report-data retrieval, established:

| Visible behavior | Positive | Gap |
| --- | --- | --- |
| Bare URL/default | Evidence | Evidence |
| Explicit #CP-0 + reload | preserved | preserved |
| Financial source inspector | ready/complete, exact source hash, page:1/2/3, Revenue 120 100 and USD/millions | missing, SHA Not supplied, extraction blocked, absent content and explicit gap |
| CP0 readiness passport | READY_WITH_LIMITATIONS | CONDITIONAL |
| Exact command passport | Run CP-1 | DO NOT RUN |
| Assertion scope | SOURCE_SUFFICIENCY_ONLY; CP_MODEL_INPUT_CONTRACT_NOT_EVALUATED | same |
| CP0 cited authority | financial/page:1, exact quote/hash and selected CP0 artifact | identity/page:1, exact quote/hash and selected CP0 artifact |
| Limitations | exact frozen source limit and synthetic qualification limit | Financial statements were not supplied. |
| CP1 / Model | Not run / Not in this Pathway | Not run / Not in this Pathway |
| Source-only banner | present outside replaced route root | present outside replaced route root |

Positive citation: financial, page:1,
fc03eecff2e157030c498a66e4de3eacb26f778fff7b449924ad8d18cb0e6a9e,
“Issuer-prepared unaudited annual financial statements”; artifact c6e7f209….
Gap citation: identity, page:1,
93735759484b756f5d6eb54f7b99c6c33c2414083257358daaa498087283bdb3,
“Northbridge Synthetic Group is the issuer and consolidated group.”; artifact9a14f88e….
Full citation captures and the proof index contain complete artifact hashes.

Evidence root: `artifacts/source-slice-proof-1`. `browser-proof.json` indexes31
retained files with hashes, all observed values, exact source/store/bundle identities,
server and tab cleanup. Some AX captures are documented diffs; full default/citation,
positive scope and gap-limitations captures are retained. Positive limitations/CP1
route diffs preserve the preceding banner; the positive limitations screenshot shows
the actual complete scoped limits. Default and CP0 full captures show the banner.
Screenshots: positive/gap source, citation and limitations PNGs. Screenshot content
is observed UI evidence, not an independent financial computation oracle.

Owned server PID26465, 127.0.0.1:50849, ran22:39:45.110328Z–22:45:57.763489Z;
closed via own exec session71594, exit0. Owned tabs2/3 closed22:45:54.487Z.
`server-record.json` and `tab-cleanup.json` retain cleanup. LEAD notified immediately
that ACTUAL-RENDER-DOM-1 was released. No server, browser lease or heavy job remains.

## Confidence review — final renderer and connected tests

Least confident about (ranked):

1. Receipt trust seam: a fabricated local receipt could satisfy surface hash checks.
   Investigated actual strict typed producer verifier and its retained audit lineage,
   then tested recorded-body forgery with matching journal/heads. Verdict: fine for
   reviewed producer contract; causal refusal passes, both actual receipts authenticate.
2. Currentness/cross-case mixing and late mutation: traced snapshot/pack/run/head,
   current inputs, exact pending step and three authentication passes. Adversarial
   foreign/forged/stale/render/staging/raw-byte mutation tests all pass. Actual cases
   remain distinct with unchanged source snapshots and hashes. Verdict: fine.
3. False analytical promotion/claim: traced real Execution.view and core build/maps,
   required empty/unrun CP1 and unselected Model, checked actual DOM for both.
   Verdict: fine; pending context is retained evidence, never a settled CP1 Module.
4. Partial publication/overwriting: traced complete adjacent staging and final auth;
   existing destination and late mutation tests pass. Independent review identified
   the possible outside-creator POSIX directory race; LEAD explicitly scoped it out
   through exclusive setup ownership. Verdict: by-design; no atomic no-replace claim.
5. Source/HTML byte identity and error paths: exact receipt bytes copied, metadata
   hashes actual HTML; parsed and raw bytes compared on rechecks. Byte-reformat,
   corrupt output and mutation refusal tests pass; final actual bundle hashes match.
   Verdict: fine; only sanctioned bundles published, sanitized ValueError failures.
6. Default route/script/banner: traced bootstrap ordering and conditional navigation,
   structural test checks placement, native bare URLs reach Evidence, explicit CP0
   reload survives, gap limitations reload also preserves its route. Actual banner
   remains outside route replacement. Verdict: fine; no imported asset edits needed.
7. Rewritten temporary lifetime/caller contract: bounded attempt generator and early
   object release retain three auth passes and signatures. Focused14-case suite,
   narrow mypy and Ruff pass; concrete real-source invariant below holds. Verdict: fine.
8. Browser capability/evidence quality: actual native IAB JS probe then both actual
   reports; recorded AX diffs labeled honestly, full citation records retained and
   exact anchor tuples asserted against source spans. Snapshot/bundle/source-set
   hashes unchanged, owned processes/tabs closed. Verdict: fine within finite scope.

Fixed: required default-Evidence navigation was implemented before the final frozen
checks. No additional renderer defect was confirmed by confidence/sensitive review.
Verified fine: authentication/currentness, refusal/byte identities, caller types,
real rendering, bounded source statuses/quotes, default/explicit routes and cleanup,
with causal tests plus actual participant-store/native DOM evidence above.
By-design: trusted unique-destination writer; pending context remains unpromoted;
historical25 canonical owners/16 aliases versus26 intended owners is not redesigned.
Still open: assembled main integration check and delivery packaging belong to LEAD/
PR MANAGER. Financial/narrative/readiness/quality CP1 steps and Model were not run;
all intended owners are not complete. Registry/aliases and later analytical owners
need their own explicit leases. No provider or financial qualification is inferred.

Independent read-only Sol/high `render_sensitive_review` checked initial and final
source/test versions, including final682eeb97…/aa84b987…. No local lineage bypass,
contract drift or state fabrication defect found; default script remains before
bootstrap, conditional fragment preservation and shipped CSP are compatible.
Publication question was resolved by LEAD's explicit scope; runtime/DOM dependencies
from that static review are now closed by the exact frozen evidence above.

## No-argument rewrite tournament — completed

Scope: `_verified_view` lines30–103 and `render_source_slice` lines106–174 in
`src/deploy_workflow/rendering.py`; no other material product function changed.
Impact set from targeted rg: helper's three wrapper calls, public entrypoint's focused
connected tests and frozen downstream source-slice interface; no shared re-export.
Invariants: strict producer authentication; three currentness passes; unchanged
signatures/return/error behavior; exact bytes/hashes; honest CP1/Model state; existing
destination refusal and complete staging within adopted single-writer scope.

Separate Incumbent/Speed/Memory/Readability roles and blind Arbiter were used.
Anonymous A=Speed, B=Memory, C=Readability incumbent-preserving abstention, D=Incumbent.
Bracket: B wins A/B, B/C and B/D; no disqualifications. After adding mandatory default
routing to every candidate, the refreshed bracket still selected B. Backup before
apply: `artifacts/rendering-before-tournament.py`; candidate/bracket evidence:
`artifacts/render-tournament-anonymous.md`, `artifacts/render-tournament-default-route.md`.

Winner: **Snippet B (Memory)** replaces the two scoped functions.

- Bounded generator matching retains O(1) match state instead of a match list.
- Releases large view/HTML/second-verification objects earlier; savings unmeasured.
- Preserves signatures, refusal ordering, exact byte identities and all three auth passes.

Verification: exact focused pytest command above,14 passed1.71s; same caller subset
and narrow mypy pass; Ruff/format pass. Concrete invariant spot-check: the positive
actual source inspector retains literal Revenue120/100 and USD/millions with exact
financial source hash/page locators, while delivered CP1 remains unrun and the gap
has no consumer output. Source/test hashes remained9d8f82… throughout actual proof.
Orchestrator reread the actual winning source and staged diff; no shared writes.

Final winning code (imports/constants included so this is self-contained):

```python
"""Authenticate and publish the bounded source-readiness slice using the shipped renderer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from deploy_vii import render as core_render
from deploy_vii.contracts import View
from deploy_vii.execution import Execution, NotAuthorized, current_inputs

if TYPE_CHECKING:
    from deploy_workflow.workflow import SourceSliceReceipt

SCOPE = "Source readiness only. Financial analysis and Model publication remain unrun."
_DEFAULT_ROUTE = (
    "<script>if (!window.location.hash) {"
    ' window.history.replaceState(null, "", "#evidence"); }</script>'
)
_BANNER = (
    '<section id="delivery-scope-banner" class="banner" role="note" '
    'data-delivery-scope="source-readiness">' + SCOPE + "</section>"
)


def _verified_view(store: Execution, receipt_path: Path) -> tuple[SourceSliceReceipt, bytes, View]:
    # Producer code can land independently of this module; importing this entry
    # point never substitutes a local receipt schema or a mock authorization path.
    from deploy_workflow.workflow import SourceSliceReceipt, verify_source_slice_receipt

    raw = receipt_path.read_bytes()
    receipt = SourceSliceReceipt.model_validate_json(raw)
    verify_source_slice_receipt(store, receipt)
    snapshot = store.read()
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or store.pack(snapshot).content_hash() != receipt.pack_sha256
    ):
        raise ValueError("stale_source_slice")
    if snapshot.run != receipt.run:
        raise ValueError("foreign_source_slice")
    # This entry point publishes only the finite readiness/context slice. A
    # broader selected run or settled analyst head needs its own delivery lease.
    if set(snapshot.run.requested_modules) != {"CP-1"} or {h.module_id for h in snapshot.heads} != {
        "CP-0"
    }:
        raise ValueError("outside_source_slice")
    cp0 = store.result(receipt.cp0.result_sha256)
    if cp0.module_id != "CP-0" or cp0.status != receipt.cp0.status:
        raise ValueError("invalid_source_slice")
    cp1_attempts = (attempt for attempt in snapshot.attempts if attempt.module_id == "CP-1")
    if receipt.cp1 is None:
        if receipt.cp1_refusal != "not_authorized" or next(cp1_attempts, None) is not None:
            raise ValueError("invalid_source_gap")
        try:
            current_inputs(snapshot, "CP-1")
        except NotAuthorized:
            pass
        else:
            raise ValueError("invalid_source_gap")
    else:
        consumer = receipt.cp1
        if (
            receipt.cp1_refusal is not None
            or consumer.status != "pending"
            or consumer.selected_cp0_sha256 != cp0.content_hash()
            or consumer.inputs != current_inputs(snapshot, "CP-1")
        ):
            raise ValueError("invalid_source_consumer")
        matches = (attempt for attempt in cp1_attempts if attempt.ticket_id == consumer.ticket_id)
        attempt = next(matches, None)
        if attempt is None or next(matches, None) is not None:
            raise ValueError("invalid_source_consumer")
        if (
            attempt.status != "pending"
            or attempt.inputs != consumer.inputs
            or len(attempt.steps) != 1
            or attempt.steps[0].step_id != "source_context"
            or attempt.steps[0].status != "valid"
            or attempt.steps[0].content_hash() != consumer.step_sha256
            or attempt.steps[0].output_sha256 != consumer.step_output_sha256
        ):
            raise ValueError("invalid_source_consumer")
        store.step_output(consumer.step_output_sha256)  # checked bytes, never a fake CP1 Module
    view = store.view()
    modules = {module.module_id: module for module in view.modules}
    if (
        view.run != receipt.run
        or modules["CP-0"].artifact_sha256 != receipt.cp0.result_sha256
        or modules["CP-1"].status != "unrun"
        or modules["CP-1"].facts
        or modules["CP-1"].claims
        or modules["CP-1"].artifact_sha256 is not None
        or modules["CP-MODEL"].status != "not_in_pathway"
    ):
        raise ValueError("invalid_source_view")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise ValueError("stale_source_slice")
    return receipt, raw, view


def render_source_slice(execution_directory: Path, receipt_path: Path, destination: Path) -> Path:
    """Publish report.html and identity metadata in a new, exclusive destination.

    All paths are trusted setup. The producer's strict typed verifier owns receipt
    and audit authentication. Publication rechecks that same selected state after
    actual rendering; existing outputs are never overwritten. No workflow is run,
    submitted or promoted by rendering, and no browser acceptance is implied.
    """
    execution_directory, receipt_path, destination = (
        Path(execution_directory),
        Path(receipt_path),
        Path(destination),
    )
    store = Execution(execution_directory)
    try:
        receipt, raw, view = _verified_view(store, receipt_path)
        if destination.exists():
            raise ValueError("destination_exists")
        html = core_render.render(view)
        del view
        anchor = '<div id="call-root"></div>'
        if html.count(anchor) != 1:
            raise ValueError("source_slice_banner_target_missing")
        data_anchor = '<script id="report-data"'
        if html.count(data_anchor) != 1:
            raise ValueError("source_slice_bootstrap_target_missing")
        html = html.replace(anchor, _BANNER + anchor, 1)
        html_bytes = html.replace(data_anchor, _DEFAULT_ROUTE + data_anchor, 1).encode("utf-8")
        del html
        metadata = {
            "schema_version": "source-slice-render/1",
            "scope": SCOPE,
            "run": receipt.run.model_dump(mode="json"),
            "pack_sha256": receipt.pack_sha256,
            "snapshot_sha256": receipt.snapshot_sha256,
            "source_receipt_file": "source-slice.json",
            "source_receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "html_file": "report.html",
            "html_sha256": hashlib.sha256(html_bytes).hexdigest(),
            "cp0_result_sha256": receipt.cp0.result_sha256,
            "cp0_step_output_sha256": receipt.cp0.step_output_sha256,
            "cp1_ticket_id": None if receipt.cp1 is None else receipt.cp1.ticket_id,
            "cp1_step_output_sha256": None
            if receipt.cp1 is None
            else receipt.cp1.step_output_sha256,
            "cp1_refusal": receipt.cp1_refusal,
        }
        checked, checked_raw, checked_view = _verified_view(store, receipt_path)
        if checked != receipt or checked_raw != raw:
            raise ValueError("stale_source_slice")
        del checked, checked_raw, checked_view
        destination.parent.mkdir(parents=True, exist_ok=True)
        # The setup-selected destination has one writer. Stage the complete
        # standalone bundle beside it; no partial report is exposed on refusal.
        with TemporaryDirectory(prefix=".source-slice-", dir=destination.parent) as temporary:
            stage = Path(temporary)
            (stage / "report.html").write_bytes(html_bytes)
            (stage / "source-slice.json").write_bytes(raw)
            (stage / "render-receipt.json").write_text(
                json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                encoding="utf-8",
            )
            final, final_raw, _ = _verified_view(store, receipt_path)
            if final != receipt or final_raw != raw or destination.exists():
                raise ValueError("stale_source_slice")
            os.rename(stage, destination)
        return destination / "report.html"
    except (ValueError, OSError):
        raise ValueError("source_slice_render_refused") from None
```
