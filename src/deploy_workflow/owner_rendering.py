"""Generic delivery of an authenticated G1 owner run through the unchanged core renderer.

`render_owner_slice` re-authenticates the run with the producer's own verifier, renders the one
verified view with `deploy_vii.render` (the core builds the Front Page from `SHIPPED_MAPS`
itself), proves what each assigned block and rail shows, and publishes a new directory by a
staged rename. `verify_owner_rendered_slice` re-derives every byte of that directory in memory
and writes nothing. Mechanisms generalise the financial slice delivery
(`financial_rendering.py`) without its relabelling catch-all: every refusal is a `ValueError`
whose message starts with an `owner_render_*` code.

Typed relabels (`WorkflowError`, `OSError`, pydantic and JSON errors into `owner_render_*`) keep
the original as `__cause__`. The one swallowed error is a failed removal of the call's own
stage, which is logged while the original failure propagates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Self

from pydantic import ValidationError, model_validator

from deploy_vii import charts
from deploy_vii import render as core_render
from deploy_vii.bindings import SHOWN_STATUSES
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Contract,
    Fact,
    Hash,
    Identifier,
    Module,
    PathwayId,
    Run,
    Text,
    View,
)
from deploy_vii.execution import Execution, Head, Qualification
from deploy_vii.registry import idle_statuses, modules
from deploy_vii.report_view import Block, build, pathways
from deploy_workflow.financial_workflow import FILES, ModelPublication
from deploy_workflow.owner_workflow import (
    BLOCKED_EDGE,
    OwnerRunReceipt,
    verify_owner_run_receipt,
)
from deploy_workflow.workflow import WorkflowError

_LOG = logging.getLogger(__name__)

SCHEMA_VERSION = "owner-slice-render/1"
RECEIPT_NAME = "render-receipt.json"
OWNER_RECEIPT_NAME = "owner-run.json"
_ANCHOR = '<div id="call-root"></div>'
_PAYLOAD_OPEN = '<script id="report-data" type="application/json">'
Rail = Literal["evidence", "limitations"]
_RAILS: tuple[Rail, ...] = ("evidence", "limitations")
# `core_render._report_payload` maps these block states for the DOM; nothing else changes.
_DOM_BLOCK_STATE = {"not_in_pathway": "outside", "outside_pathway": "outside"}
_SETTLED = frozenset({"accepted", "restricted"})
_ASSIGNED_SHOWN = frozenset({"populated", "collapsed"})
Outcome = Literal["complete", "refused"]


@dataclass(frozen=True)
class DeliveryScope:
    """One delivered module run: matched by (pathway, requested_modules, case_kind) alone."""

    scope_id: str
    pathway: PathwayId
    requested_modules: tuple[str, ...]
    case_kind: str
    sections: tuple[str, ...]
    rails: tuple[Rail, ...]
    banner: Mapping[str, str]


def _scope(
    scope_id: str,
    pathway: PathwayId,
    requested: tuple[str, ...],
    sections: tuple[str, ...],
    banner: Mapping[str, str],
) -> DeliveryScope:
    return DeliveryScope(
        scope_id, pathway, requested, "synthetic", sections, _RAILS, MappingProxyType(dict(banner))
    )


_DELIVERY_ROWS: tuple[DeliveryScope, ...] = (
    # Lease rev 0/1 (Q6 texts); sections per rev 3 R3.1: the three credit_snapshot blocks whose
    # producers are CP-1 alone (the chart strip included).
    _scope(
        "cp1-model",
        "credit_snapshot",
        ("CP-1", "CP-MODEL"),
        ("model-chart-strip", "capital-structure", "financials-credit-metrics"),
        {
            "complete": (
                "Historical financial analysis and Model publication only. "
                "Remaining analytical owners and forward projections remain unqualified."
            ),
            "refused": (
                "Financial source missing. CP1 financial analysis and Model publication "
                "did not run."
            ),
        },
    ),
    _scope(
        "s1a-credit-snapshot",
        "credit_snapshot",
        ("CP-1", "CP-MODEL", "CP-1A", "CP-2"),
        (
            "key-findings",
            "company-operating-model",
            "strengths-weaknesses",
            "company-profile",
            "transaction-summary",
        ),
        {
            "complete": (
                "Credit snapshot: source readiness, historical financials, Model, business "
                "context and credit synthesis only. Integrity review and remaining analytical "
                "owners remain unqualified."
            )
        },
    ),
    _scope(
        "cp3-fp01-relative-value",
        "credit_snapshot",
        ("CP-1", "CP-MODEL", "CP-1A", "CP-2", "CP-3"),
        ("relative-value",),
        {
            "complete": (
                "Relative value only: the instrument preference set against the observed market "
                "evidence. Every other block on this page, including committee challenge, "
                "integrity review and the remaining analytical owners, remains unqualified."
            )
        },
    ),
    # Gated, no row until its prerequisite lands (lease R2.2, rulings item 4 Q-S2):
    # "cp6-fp01-committee": no CP-6 core and no `cp6_closed` driver.
    _scope(
        "cp1c-fp03-peers",
        "relative_value",
        ("CP-1C",),
        ("peer-positioning",),
        {
            "complete": (
                "Peer positioning only. Every other block on this page remains unqualified."
            ),
            "refused": (
                "Peer positioning did not run: an earlier owner was not authorized, so this "
                "owner never started. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "cp3d-fp03-market",
        "relative_value",
        ("CP-3D",),
        ("market-against-fundamentals",),
        {
            "complete": (
                "Market against fundamentals only: observed levels, price metrics and spread. "
                "Instrument levels, yield against maturity and the remaining blocks on this "
                "page remain unqualified."
            )
        },
    ),
    _scope(
        "cp1d-fp02-quality",
        "earnings_update",
        ("CP-1D",),
        ("earnings-quality", "restated-leverage"),
        {
            "complete": (
                "Earnings quality and restated leverage only: the add-back assessment and "
                "leverage restated on supported earnings. Every other block on this page, "
                "including the headline results and the Model, remains unqualified."
            )
        },
    ),
    _scope(
        "cp2a-fp05-downside",
        "distressed_restructuring",
        ("CP-2A",),
        ("downside-stress", "break-points"),
        {
            "complete": (
                "Downside stress and break points only. Every other block on this page, "
                "including the forward, recovery and rating blocks, remains unqualified."
            ),
            "refused": (
                "Downside stress did not run: an earlier owner was not authorized, so this "
                "owner never started. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "cp2g-fp05-forward",
        "distressed_restructuring",
        ("CP-2G", "CP-1D"),
        ("forward-credit-path", "forward-breakpoints"),
        {
            "complete": (
                "Forward credit path and forward break points only, built on the downside "
                "stress and the supported earnings. Every other block on this page remains "
                "unqualified."
            )
        },
    ),
    _scope(
        "cp2g-fp05-forward-gap",
        "distressed_restructuring",
        ("CP-2G",),
        ("forward-credit-path", "forward-breakpoints"),
        {
            "complete": (
                "Forward credit path and forward break points only, built on the downside "
                "stress; supported earnings were not requested. Every other block on this page "
                "remains unqualified."
            ),
            "refused": (
                "Forward credit path did not run: an earlier owner was not authorized, so this "
                "owner never started. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "cp2h-fp05-ratings",
        "distressed_restructuring",
        ("CP-2H",),
        ("rating-triggers",),
        {
            "complete": (
                "Rating triggers only: headroom against a synthetic agency source, drawn from "
                "the forward credit path. Every other block on this page remains unqualified."
            ),
            "refused": (
                "Rating triggers did not run: an earlier owner was not authorized, so this "
                "owner never started. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "cp4c-fp05-recovery",
        "distressed_restructuring",
        ("CP-4C",),
        ("recovery-by-class", "value-allocation-claims"),
        {
            "complete": (
                "Recovery by class and value allocation only: the recovery waterfall under the "
                "stated scenarios. Every other block on this page remains unqualified."
            ),
            "refused": (
                "Recovery analysis did not run: an earlier owner was not authorized, so this "
                "owner never started. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "cp2d-fp04-liquidity",
        "covenant_refinancing",
        ("CP-1", "CP-1A", "CP-2", "CP-2D"),
        ("liquidity-runway", "funding-gap"),
        {
            "complete": (
                "Liquidity runway and funding gap only. The maturity wall, covenant analysis, "
                "refinancing and the remaining blocks on this page remain unqualified."
            )
        },
    ),
    # Gated, no row until the Q-C2 wiring and the oracle re-pin land (lease D2, rulings item 6):
    # "cp3c-fp04-refinancing" with funding-gap, refinancing-paths, lme-creditor-exposure.
    _scope(
        "cp4-fp04-covenants",
        "covenant_refinancing",
        ("CP-4",),
        (
            "covenant-tests-headroom",
            "red-flags",
            "lender-protection-score",
            "capacity",
            "ebitda-definition",
            "documents-structure",
        ),
        {
            "complete": (
                "Covenant analysis only: tests and headroom, capacity, red flags, lender "
                "protection, the EBITDA definition and the document register. Liquidity, "
                "refinancing and the remaining blocks on this page remain unqualified."
            )
        },
    ),
    _scope(
        "cp8-fp01-what-changed",
        "credit_snapshot",
        ("CP-8",),
        ("what-changed",),
        {
            "refused": (
                "What changed since the last Report did not run: the readiness review refused "
                "this owner itself because no prior case was supplied. Every other block on "
                "this page remains unqualified."
            ),
            "complete": (
                "What changed since the last Report only: a comparison with the recorded prior "
                "case. Every other block on this page remains unqualified."
            ),
        },
    ),
    _scope(
        "slice-cp2e-sensitivity",
        "credit_snapshot",
        ("CP-2E",),
        (),
        {
            "complete": (
                "Macro and FX sensitivity only, on its module page with its evidence and "
                "limitations. No Front Page block on this page is qualified."
            )
        },
    ),
    _scope(
        "slice-cpdr-research",
        "credit_snapshot",
        ("CP-DR",),
        (),
        {
            "complete": (
                "Local research agenda coverage only, shown as evidence and limitations. "
                "No Front Page block on this page is qualified."
            )
        },
    ),
    _scope(
        "slice-cpl10-screen",
        "credit_snapshot",
        ("CP-L10",),
        (),
        {
            "complete": (
                "Screening only, shown as evidence and limitations. No Front Page block on "
                "this page is qualified."
            )
        },
    ),
)
DELIVERY_SCOPES: Mapping[str, DeliveryScope] = MappingProxyType(
    {row.scope_id: row for row in _DELIVERY_ROWS}
)


# ---------------------------------------------------------------------------- proof contracts


class OwnerHeadResult(Contract):
    module_id: Identifier
    result_sha256: Hash
    status: Literal["accepted", "restricted"]
    qualification: Qualification | None


class OwnerBoundFact(Contract):
    module_id: Identifier
    result_sha256: Hash
    table_id: Identifier
    row_id: Identifier
    fact_id: Identifier
    fact_sha256: Hash


class OwnerSectionProof(Contract):
    block_id: Identifier
    state: str
    block_sha256: Hash
    facts: tuple[OwnerBoundFact, ...]


class OwnerModuleLimitations(Contract):
    module_id: Identifier
    limitations: tuple[Text, ...]


class OwnerRailProof(Contract):
    destination: Literal["evidence", "limitations"]
    facts: tuple[OwnerBoundFact, ...]
    limitations: tuple[OwnerModuleLimitations, ...]


def _refusal(code: str) -> ValueError:
    return ValueError(code)


def _strict_load(raw: bytes, *, typed: bool, code: str) -> Any:
    """Parse JSON refusing duplicate keys, non-finite numbers, bad UTF-8 and runaway nesting.
    `typed` keeps key order and number spelling (type-tagged text) for canonical comparison."""

    def pairs(items: list[tuple[str, Any]]) -> Any:
        if len({key for key, _ in items}) != len(items):
            raise _refusal(code)
        return ("object", tuple(items)) if typed else dict(items)

    def constant(_: str) -> Any:
        raise _refusal(code)

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=constant,
            parse_float=(lambda text: ("float", text)) if typed else float,
            parse_int=(lambda text: ("int", text)) if typed else int,
        )
    except (ValueError, RecursionError) as error:
        raise _refusal(code) from error


def _canonical(value: Contract) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class OwnerRenderReceipt(Contract):
    schema_version: Literal["owner-slice-render/1"] = "owner-slice-render/1"
    scope_id: Identifier
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    outcome: Literal["complete", "refused"]
    owner_receipt_file: Literal["owner-run.json"] = "owner-run.json"
    owner_receipt_file_sha256: Hash
    owner_receipt_content_sha256: Hash
    head_results: tuple[OwnerHeadResult, ...]
    model: ModelPublication | None
    sections: tuple[OwnerSectionProof, ...]
    rails: tuple[OwnerRailProof, ...]
    files: dict[str, Hash]

    @model_validator(mode="after")
    def exact_file_map(self) -> Self:
        expected = {"report.html", OWNER_RECEIPT_NAME}
        if self.model is not None:
            expected |= {f"model/{name}" for name in FILES} | {"calculation.json"}
        if set(self.files) != expected:
            raise _refusal("owner_render_receipt_files")
        if tuple(rail.destination for rail in self.rails) != _RAILS:
            raise _refusal("owner_render_receipt_rails")
        ids = [section.block_id for section in self.sections]
        if len(set(ids)) != len(ids):
            raise _refusal("owner_render_receipt_sections")
        return self

    @classmethod
    def from_wire(cls, raw: bytes) -> Self:
        """Strict parse of canonical bytes: exact keys, no duplicate or non-finite values."""
        _strict_load(raw, typed=False, code="owner_render_wire")
        try:
            value = cls.model_validate_json(raw)
        except ValidationError as error:
            raise _refusal("owner_render_wire") from error
        if _canonical(value) != raw:
            raise _refusal("owner_render_wire_spelling")
        return value


# ---------------------------------------------------------------------------- capture


@dataclass(frozen=True)
class _Capture:
    wire: OwnerRenderReceipt
    files: Mapping[str, bytes]

    @property
    def receipt_bytes(self) -> bytes:
        return _canonical(self.wire)

    @property
    def tree(self) -> dict[str, bytes]:
        return {**self.files, RECEIPT_NAME: self.receipt_bytes}


def _read_tree(directory: Path) -> dict[str, bytes]:
    """Every regular file below `directory` by relative path; a symlink, device or other
    non-regular entry refuses. Reads use O_NOFOLLOW relative to the open directory (D1 F5)."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    out: dict[str, bytes] = {}

    def walk(fd: int, prefix: str) -> None:
        for name in sorted(os.listdir(fd)):
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, flags, dir_fd=fd)
                try:
                    walk(child, f"{prefix}{name}/")
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    if not stat.S_ISREG(os.fstat(handle).st_mode):
                        raise _refusal("owner_render_delivery")
                    with os.fdopen(handle, "rb", closefd=False) as stream:
                        out[prefix + name] = stream.read()
                finally:
                    os.close(handle)
            else:
                raise _refusal("owner_render_delivery")

    try:
        root = os.open(directory, flags)
    except OSError as error:
        raise _refusal("owner_render_delivery") from error
    try:
        walk(root, "")
    except OSError as error:
        raise _refusal("owner_render_delivery") from error
    finally:
        os.close(root)
    return out


def _parse_receipt(raw: bytes) -> OwnerRunReceipt:
    typed_raw = _strict_load(raw, typed=True, code="owner_render_receipt_wire")
    try:
        receipt = OwnerRunReceipt.model_validate_json(raw)
    except ValidationError as error:
        raise _refusal("owner_render_receipt_wire") from error
    typed_canonical = _strict_load(
        receipt.model_dump_json().encode("utf-8"), typed=True, code="owner_render_receipt_wire"
    )
    if typed_raw != typed_canonical:
        raise _refusal("owner_render_receipt_spelling")
    return receipt


def _scope_of(run: Run) -> DeliveryScope:
    hits = [
        scope
        for scope in DELIVERY_SCOPES.values()
        if (scope.pathway, scope.requested_modules, scope.case_kind)
        == (run.pathway, tuple(run.requested_modules), run.case_kind)
    ]
    if len(hits) != 1:
        raise _refusal("owner_render_scope")
    return hits[0]


def _payload_of(page: str) -> dict[str, Any]:
    if page.count(_PAYLOAD_OPEN) != 1:
        raise _refusal("owner_render_payload")
    body = page.split(_PAYLOAD_OPEN, 1)[1].split("</script>", 1)[0]
    value = _strict_load(body.encode("utf-8"), typed=False, code="owner_render_payload")
    if not isinstance(value, dict):
        raise _refusal("owner_render_payload")
    return value


def _bound_facts(
    block_id: str,
    shown: Mapping[str, Any],
    heads: Mapping[str, Head],
    head_modules: Mapping[str, Module],
) -> tuple[tuple[OwnerBoundFact, Fact], ...]:
    """The facts the shipped maps place in `block_id`, in placement order, each a member of
    its receipt head's facts (the bound record and the fact itself)."""
    out: list[tuple[OwnerBoundFact, Fact]] = []
    members: dict[str, dict[tuple[str, str, str], list[Fact]]] = {}
    for module_map in SHIPPED_MAPS:
        module = shown.get(module_map.module_id)
        if module is None:
            continue
        for entry in module_map.entries:
            if entry.block_id != block_id:
                continue
            if module_map.module_id not in members:
                index: dict[tuple[str, str, str], list[Fact]] = {}
                for fact in head_modules[module_map.module_id].facts:
                    index.setdefault((fact.table_id, fact.row_id, fact.fact_id), []).append(fact)
                members[module_map.module_id] = index
            for fact in module.facts:
                if not entry.matches(module_map.module_id, fact):
                    continue
                key = (fact.table_id, fact.row_id, fact.fact_id)
                if fact not in members[module_map.module_id].get(key, ()):
                    raise _refusal("owner_render_proof")
                out.append((_bound(module_map.module_id, heads, fact), fact))
    return tuple(out)


def _bound(module_id: str, heads: Mapping[str, Head], fact: Fact) -> OwnerBoundFact:
    return OwnerBoundFact(
        module_id=module_id,
        result_sha256=heads[module_id].result_sha256,
        table_id=fact.table_id,
        row_id=fact.row_id,
        fact_id=fact.fact_id,
        fact_sha256=fact.content_hash(),
    )


def _store_failure(error: Exception) -> ValueError:
    return ValueError("owner_render_store")


def _publication(receipt: OwnerRunReceipt, directory: Path | None) -> dict[str, bytes]:
    if receipt.model is None:
        if directory is not None:
            raise _refusal("owner_render_model")
        return {}
    if directory is None:
        raise _refusal("owner_render_model")
    tree = _read_tree(directory)
    if set(tree) != set(FILES) or set(receipt.model.files) != set(FILES):
        raise _refusal("owner_render_model")
    if any(_sha(tree[name]) != receipt.model.files[name] for name in FILES):
        raise _refusal("owner_render_model")
    return tree


def _outcome_rules(
    receipt: OwnerRunReceipt, scope: DeliveryScope, snapshot_heads: tuple[Head, ...]
) -> Outcome:
    outcome: Outcome = "refused" if receipt.refusals else "complete"
    if outcome not in scope.banner:
        raise _refusal("owner_render_outcome")
    if any(r.reason == BLOCKED_EDGE for r in receipt.refusals):
        raise _refusal("owner_render_blocked")
    if any(head.status not in _SETTLED for head in snapshot_heads):
        raise _refusal("owner_render_blocked")  # blocked and stale heads are not scope outcomes
    if outcome == "refused":
        if len(receipt.refusals) != 1 or receipt.model is not None:
            raise _refusal("owner_render_outcome")
    elif {head.module_id for head in snapshot_heads} != set(receipt.plan):
        raise _refusal("owner_render_outcome")
    if (receipt.model is not None) != (
        outcome == "complete" and "CP-MODEL" in scope.requested_modules
    ):
        raise _refusal("owner_render_model")
    return outcome


def _capture(
    execution_directory: Path, receipt_path: Path, publication_directory: Path | None
) -> _Capture:
    try:
        raw = receipt_path.read_bytes()
    except OSError as error:
        raise _refusal("owner_render_io") from error
    receipt = _parse_receipt(raw)
    scope = _scope_of(receipt.run)
    outcome: Outcome = "refused" if receipt.refusals else "complete"
    if outcome not in scope.banner:
        raise _refusal("owner_render_outcome")
    if (receipt.model is None) != (publication_directory is None):
        raise _refusal("owner_render_model")
    store = Execution(execution_directory)
    try:
        verify_owner_run_receipt(store, receipt, publication_directory=publication_directory)
    except WorkflowError as error:
        raise _refusal("owner_render_unauthenticated") from error
    try:
        snapshot = store.read()
        pack = store.pack(snapshot)
        view = store.view()
        head_modules = {head.module_id: store.head_module(head) for head in snapshot.heads}
    except (ValueError, OSError) as error:
        raise _store_failure(error) from error
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or pack.content_hash() != receipt.pack_sha256
        or snapshot.run != receipt.run
        or any(attempt.status != "finished" for attempt in snapshot.attempts)
        or [(h.module_id, h.result_sha256, h.status) for h in snapshot.heads]
        != [(h.module_id, h.result_sha256, h.status) for h in receipt.heads]
    ):
        raise _refusal("owner_render_stale")
    outcome = _outcome_rules(receipt, scope, snapshot.heads)
    heads = {head.module_id: head for head in snapshot.heads}
    if (
        view.mode != "accepted"
        or view.run != receipt.run
        or view.sources != pack.sources
        or [m.module_id for m in view.modules] != [r.module_id for r in modules()]
    ):
        raise _refusal("owner_render_view")
    idle = idle_statuses(receipt.run)
    for shown in view.modules:
        head = heads.get(shown.module_id)
        if head is None:
            if (
                shown.status != idle[shown.module_id]
                or shown.artifact_sha256 is not None
                or shown.facts
                or shown.tables
                or shown.claims
                or shown.limitations
            ):
                raise _refusal("owner_render_view")
            continue
        module = head_modules[shown.module_id]
        visible = module.status in SHOWN_STATUSES
        if (
            shown.status != module.status
            or shown.artifact_sha256 != module.content_hash()
            or shown.facts != (module.facts if visible else ())
            or shown.tables != (module.tables if visible else ())
            or shown.claims != (module.claims if visible else ())
            or shown.limitations
            != tuple(dict.fromkeys((*module.limitations, *module.inherited_limitations)))
        ):
            raise _refusal("owner_render_view")
    publication = _publication(receipt, publication_directory)
    pathway = next(item for item in pathways() if item.id == view.run.pathway)
    try:
        report = build(view, pathway, SHIPPED_MAPS)
        page = core_render.render(view)
    except ValueError as error:
        raise _refusal("owner_render_build") from error
    if page.count(_ANCHOR) != 1:
        raise _refusal("owner_render_html")
    banner = (
        '<section id="delivery-scope-banner" class="banner" role="note" '
        f'data-delivery-scope="{scope.scope_id}">{escape(scope.banner[outcome])}</section>'
    )
    html_bytes = page.replace(_ANCHOR, _ANCHOR + banner, 1).encode("utf-8")
    payload = _payload_of(page)
    shown_modules = {m.module_id: m for m in view.modules if m.status in SHOWN_STATUSES}
    blocks: dict[str, Block] = {b.block_id: b for b in report.blocks}
    payload_blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
    sections = _sections(scope, outcome, blocks, payload_blocks, shown_modules, heads, head_modules)
    rails = _rails(scope, view, payload, shown_modules, heads, head_modules)
    files: dict[str, bytes] = {"report.html": html_bytes, OWNER_RECEIPT_NAME: raw}
    if receipt.model is not None:
        files |= {f"model/{name}": publication[name] for name in FILES}
        files["calculation.json"] = publication["calculation.json"]
    wire = OwnerRenderReceipt(
        scope_id=scope.scope_id,
        run=receipt.run,
        pack_sha256=receipt.pack_sha256,
        snapshot_sha256=receipt.snapshot_sha256,
        outcome=outcome,
        owner_receipt_file_sha256=_sha(raw),
        owner_receipt_content_sha256=receipt.content_hash(),
        head_results=tuple(
            OwnerHeadResult(
                module_id=head.module_id,
                result_sha256=head.result_sha256,
                status="accepted" if head.status == "accepted" else "restricted",
                qualification=head.qualification,
            )
            for head in snapshot.heads
        ),
        model=receipt.model,
        sections=sections,
        rails=rails,
        files={name: _sha(body) for name, body in sorted(files.items())},
    )
    return _Capture(wire, MappingProxyType(files))


def _expected_block_payload(block: Block) -> dict[str, Any]:
    """The block as `render._report_payload` puts it in `report-data`: the dumped block, the
    DOM spelling of its state and, for a chart or figure, the SVG and gaps note it adds."""
    expected: dict[str, Any] = block.model_dump(mode="json")
    expected["state"] = _DOM_BLOCK_STATE.get(block.state, block.state)
    if block.chart is not None:
        expected["chart"]["svg"] = charts.render_svg(
            block.chart, chart_id=block.block_id, title=block.title
        )
    for index, (item, figure) in enumerate(zip(expected["figures"], block.figures, strict=True)):
        item["gaps_note"] = figure.gaps_note
        item["chart"]["svg"] = charts.render_svg(
            figure.chart, chart_id=f"{block.block_id}-f{index}", title=figure.title
        )
    return expected


def _sections(
    scope: DeliveryScope,
    outcome: Outcome,
    blocks: Mapping[str, Block],
    payload_blocks: Mapping[str, Any],
    shown: Mapping[str, Any],
    heads: Mapping[str, Head],
    head_modules: Mapping[str, Module],
) -> tuple[OwnerSectionProof, ...]:
    proofs: list[OwnerSectionProof] = []
    for section_id in scope.sections:
        block = blocks.get(section_id)
        if block is None:
            raise _refusal("owner_render_proof")
        # Rev 3 R3.2: a shown block may hold figures. They are proved against the frozen chart
        # oracles by the acceptance tests and are covered here by the exact payload equality
        # below; a refused page draws no figure (blocks that never ran carry none).
        if outcome == "refused" and (block.figures or block.chart is not None):
            raise _refusal("owner_render_proof")
        facts = tuple(item for item, _ in _bound_facts(section_id, shown, heads, head_modules))
        if outcome == "complete":
            if block.state not in _ASSIGNED_SHOWN or not facts:
                raise _refusal("owner_render_proof")
        elif facts or block.state in _ASSIGNED_SHOWN:
            raise _refusal("owner_render_proof")
        if payload_blocks.get(section_id) != _expected_block_payload(block):
            raise _refusal("owner_render_payload")
        proofs.append(
            OwnerSectionProof(
                block_id=section_id,
                state=block.state,
                block_sha256=block.content_hash(),
                facts=facts,
            )
        )
    return tuple(proofs)


def _rails(
    scope: DeliveryScope,
    view: View,
    payload: Mapping[str, Any],
    shown: Mapping[str, Any],
    heads: Mapping[str, Head],
    head_modules: Mapping[str, Module],
) -> tuple[OwnerRailProof, ...]:
    payload_modules = {m["module_id"]: m for m in payload["modules"]}
    for module in view.modules:
        if module.status == "rejected":
            continue
        if list(module.limitations) != payload_modules[module.module_id]["limitations"]:
            raise _refusal("owner_render_payload")
    on_page: dict[str, dict[tuple[str, str, str], list[dict[str, Any]]]] = {}
    for module_id, entry in payload_modules.items():
        index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for item in entry["facts"]:
            index.setdefault((item["table_id"], item["row_id"], item["fact_id"]), []).append(item)
        on_page[module_id] = index
    proofs: list[OwnerRailProof] = []
    for destination in scope.rails:
        pairs = _bound_facts(destination, shown, heads, head_modules)
        for bound, fact in pairs:
            expected = fact.model_dump(mode="json")
            candidates = on_page[bound.module_id].get(
                (bound.table_id, bound.row_id, bound.fact_id), []
            )
            if not any(
                all(item[key] == value for key, value in expected.items()) for item in candidates
            ):
                raise _refusal("owner_render_payload")
        facts = tuple(bound for bound, _ in pairs)
        limits = tuple(
            OwnerModuleLimitations(module_id=m.module_id, limitations=m.limitations)
            for m in view.modules
            if destination == "limitations" and m.limitations
        )
        proofs.append(OwnerRailProof(destination=destination, facts=facts, limitations=limits))
    return tuple(proofs)


# ---------------------------------------------------------------------------- delivery


def _check_destination(destination: Path, inputs: tuple[Path | None, ...]) -> Path:
    """Refuse an existing destination of any kind, then a parent that is, or lies inside, an
    input directory (by file identity, so a case-variant alias cannot hide it)."""
    if os.path.lexists(destination):
        raise _refusal("owner_render_destination_exists")
    try:
        parent = destination.parent.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise _refusal("owner_render_destination_parent") from error
    if not parent.is_dir():
        raise _refusal("owner_render_destination_parent")
    for ancestor in (parent, *parent.parents):
        for directory in inputs:
            if directory is None:
                continue
            try:
                same = os.path.samefile(ancestor, directory)
            except OSError:
                continue  # an input that does not exist cannot be the destination's ancestor
            if same:
                raise _refusal("owner_render_destination_overlap")
    return parent


def _verify_directory(
    delivery: Path,
    execution_directory: Path,
    receipt_path: Path,
    publication_directory: Path | None,
) -> None:
    expected = _capture(execution_directory, receipt_path, publication_directory)
    tree = _read_tree(delivery)
    if tree != expected.tree:
        raise _refusal("owner_render_delivery")
    if OwnerRenderReceipt.from_wire(tree[RECEIPT_NAME]) != expected.wire:
        raise _refusal("owner_render_delivery")
    if _capture(execution_directory, receipt_path, publication_directory) != expected:
        raise _refusal("owner_render_stale")
    if _read_tree(delivery) != tree:
        raise _refusal("owner_render_delivery")


def verify_owner_rendered_slice(
    execution_directory: Path,
    receipt_path: Path,
    publication_directory: Path | None,
    delivery_directory: Path,
) -> None:
    """Re-derive the delivery from the store in memory and compare every byte; write nothing."""
    _verify_directory(
        Path(delivery_directory),
        Path(execution_directory),
        Path(receipt_path),
        None if publication_directory is None else Path(publication_directory),
    )


def render_owner_slice(
    execution_directory: Path,
    receipt_path: Path,
    publication_directory: Path | None,
    destination: Path,
) -> Path:
    """Render a verified G1 owner run into a new `destination`; return `destination/report.html`
    in the caller's own spelling. Trusted setup owns every path. A failure before the rename
    removes only this call's stage; a failure after it keeps the delivery as evidence."""
    store, receipt = Path(execution_directory), Path(receipt_path)
    publication = None if publication_directory is None else Path(publication_directory)
    target = Path(destination)
    parent = _check_destination(target, (store, publication))
    first = _capture(store, receipt, publication)
    stage = Path(tempfile.mkdtemp(prefix=".owner-render-", dir=parent))
    renamed = False
    try:
        for name, body in first.tree.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        if _read_tree(stage) != first.tree:
            raise _refusal("owner_render_delivery")
        _verify_directory(stage, store, receipt, publication)
        if _capture(store, receipt, publication) != first:
            raise _refusal("owner_render_stale")
        if os.path.lexists(target):
            raise _refusal("owner_render_destination_exists")
        os.rename(stage, target)
        renamed = True
    except BaseException:
        if not renamed:
            try:
                shutil.rmtree(stage)
            except OSError:
                _LOG.warning("owner render: could not remove stage %s", stage, exc_info=True)
        raise
    _verify_directory(target, store, receipt, publication)
    return destination / "report.html"
