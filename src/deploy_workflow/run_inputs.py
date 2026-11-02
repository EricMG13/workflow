"""Input checks and the single pack root for ``run_pathway`` (O2 Task 2).

``check_arguments`` performs every check of the ``run_pathway`` call shape before anything is
written; ``stage_sources`` then writes the bytes that were read and hashed into ``run_dir/sources``
and builds the pack from that one root. Nothing here reads the environment or the network, and no
check is skipped on failure: each refusal is a named ``RunInputError`` subclass with a stable
``code``. A crashed run leaves a run directory without ``run.json``.
"""

import hashlib
import json
import os
import stat
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Literal, get_args

from pydantic import TypeAdapter, ValidationError

from deploy_vii.contracts import Identifier, PathwayId, Run
from deploy_vii.preparation import (
    MAX_BYTES,
    PreparationRequest,
    PreparedPack,
    SourceRequest,
    prepare,
    prepare_source,
)
from deploy_workflow.context import CONTEXT_SOURCE_ID, RunContext, load_context, preparation_request
from deploy_workflow.html_text import convert_html
from deploy_workflow.model.adapter import (
    GateResult,
    LiveAdapter,
    ModelAdapter,
    RecordedAdapter,
    check_ruling,
)
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.research import evidence, webfetch
from deploy_workflow.research.contracts import ReservedSourceId, refuse_reserved
from deploy_workflow.research.intake import (
    MAX_ITEM_BYTES,
    AcceptedItem,
    Fetcher,
    ManifestRow,
    RefusedItem,
    effective_cutoff,
    intake,
    parse_rows,
    write_rejected,
)

HTML_MEDIA = "text/html"
_PACK_MEDIA: tuple[str, ...] = get_args(SourceRequest.model_fields["media_type"].annotation)
_SUFFIX = {
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}
_IDENTIFIER = TypeAdapter(Identifier)


class RunInputError(ValueError):
    """A refused argument; ``code`` is stable, the message names the argument."""

    code: ClassVar[str] = "run_input"


class RunDirExists(RunInputError):
    code = "run_dir_exists"


class RunDirInvalid(RunInputError):
    code = "run_dir_invalid"


class AdapterRefused(RunInputError):
    code = "adapter_refused"


class ConfigMismatch(RunInputError):
    code = "config_mismatch"


class PathwayMismatch(RunInputError):
    code = "pathway_mismatch"


class BadIdentifier(RunInputError):
    code = "bad_identifier"


class BadSourceId(RunInputError):
    code = "bad_source_id"


class DuplicateSource(RunInputError):
    code = "duplicate_source"


class SourceTooLarge(RunInputError):
    code = "source_too_large"


class SourceUnreadable(RunInputError):
    code = "source_unreadable"


class UnsupportedMedia(RunInputError):
    code = "unsupported_media"


class ResearchManifestRequired(RunInputError):
    code = "research_manifest_required"


class ResearchManifestUnused(RunInputError):
    code = "research_manifest_unused"


class ResearchManifestInvalid(RunInputError):
    code = "research_manifest_invalid"


class ResearchRulingUnused(RunInputError):
    code = "research_ruling_unused"


class BadCap(RunInputError):
    code = "bad_cap"


class StagedSourceChanged(RuntimeError):
    """A staged file no longer matches the bytes that were read: a fault, never a pack."""


@dataclass(frozen=True)
class CaseSource:
    source_id: str
    path: Path
    media_type: str  # "text/html" (converted) or a SourceRequest media type


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    run_dir: Path
    outcome: Literal["settled", "stopped"]
    stopped_reason: str | None
    spent_usd: Decimal


@dataclass(frozen=True)
class StagedFile:
    """One file to stage: the bytes that were read (or converted) and their sha256.
    ``original_sha256`` is the hash of the bytes read before any conversion (equal to ``sha256``
    unless the source was HTML). ``media_type`` is the caller's (``text/html`` for a converted
    source), so a label never has to be inferred from the hashes."""

    source_id: str
    filename: str
    data: bytes
    sha256: str
    original_sha256: str
    media_type: str


@dataclass(frozen=True)
class ResearchStaging:
    """What intake decided, held until ``stage_sources`` writes it: the manifest file's sha256, the
    accepted items (each yields its ``EvidenceItem``) with the one retrieval time they share (O7-R13)
    except the items a rerun keeps the earlier instant for (``kept``, by ``item_id``; O7-R67), and
    the refused items. A run that fetched (O7b-2) also holds the record of each attempted fetch
    and the ``research_ruling`` that lifted the web pause (``ruling`` is set exactly then)."""

    manifest_sha256: str
    retrieved: str
    accepted: tuple[AcceptedItem, ...]
    refused: tuple[RefusedItem, ...]
    fetches: tuple[webfetch.FetchRecord, ...] = ()
    ruling: GateResult | None = None
    kept: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckedRun:
    case_id: str
    run_id: str
    pathway: PathwayId
    model: ModelSpec
    adapter: ModelAdapter
    gate: GateResult | None  # the live gate result read once from the adapter; None if recorded
    cap_usd: Decimal
    cp_dr: bool
    context: RunContext
    files: tuple[StagedFile, ...]  # sources in call order, ev-* items, then context.json
    request: PreparationRequest
    research: ResearchStaging | None = None


def read_capped(path: Path) -> bytes:
    """Read a regular file through one descriptor: open without blocking, ``fstat`` that
    descriptor (FIFO, directory, device refused), then read at most ``MAX_BYTES + 1`` from it."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    except (OSError, ValueError) as error:
        raise SourceUnreadable(
            f"{path}: cannot open ({getattr(error, 'strerror', None) or error})"
        ) from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise SourceUnreadable(f"{path}: not a regular file")
    except OSError as error:
        os.close(fd)
        raise SourceUnreadable(f"{path}: cannot stat ({error.strerror})") from None
    try:
        with os.fdopen(fd, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise SourceUnreadable(f"{path}: cannot read ({error.strerror})") from None
    if len(raw) > MAX_BYTES:
        raise SourceTooLarge(f"{path}: larger than {MAX_BYTES} bytes")
    return raw


def _identifier(value: object, error: type[RunInputError], what: str) -> str:
    try:
        return _IDENTIFIER.validate_python(value, strict=True)
    except ValidationError:
        raise error(f"{what} {value!r} is not a valid identifier") from None


def _check_run_dir(run_dir: Path) -> None:
    if os.path.lexists(run_dir):
        raise RunDirExists(f"{run_dir} already exists")
    if not run_dir.parent.is_dir():
        raise RunDirInvalid(f"{run_dir.parent} is not an existing directory")


def _check_adapter(adapter: ModelAdapter, model: ModelSpec) -> GateResult | None:
    if type(adapter) not in (RecordedAdapter, LiveAdapter):
        raise AdapterRefused(f"adapter type {type(adapter).__name__} is not one of O5's two")
    if adapter.config_id != model.config_id:
        raise ConfigMismatch(f"adapter {adapter.config_id!r} runs a different config")
    return adapter.gate if isinstance(adapter, LiveAdapter) else None


def _check_cap(cap_usd: Decimal) -> None:
    if not (isinstance(cap_usd, Decimal) and cap_usd.is_finite() and cap_usd > 0):
        raise BadCap(f"cap_usd {cap_usd!r} is not a finite Decimal above zero")


def _require_ready(request: SourceRequest, data: bytes) -> None:
    """``prepare_source`` does no I/O: refuse a source the pack would call unusable now."""
    prepared = prepare_source(request, data)
    if prepared.status != "ready":
        raise SourceUnreadable(f"source {request.source_id!r}: {prepared.limitation}")


def _case_files(
    sources: Sequence[CaseSource], source_raw: Sequence[bytes]
) -> tuple[list[StagedFile], list[SourceRequest]]:
    """The caller's sources as staged files and pack requests."""
    files: list[StagedFile] = []
    requests: list[SourceRequest] = []
    seen: set[str] = {CONTEXT_SOURCE_ID}
    for item, raw in zip(sources, source_raw, strict=True):
        source_id = _identifier(item.source_id, BadSourceId, "source_id")
        try:
            refuse_reserved(source_id)  # ev-*, cp-dr-dossier and peers belong to CP-DR
        except ReservedSourceId as error:
            raise BadSourceId(str(error)) from None
        if source_id == CONTEXT_SOURCE_ID:
            raise BadSourceId(f"source_id {source_id!r} is reserved for the context file")
        if source_id.casefold() in seen:
            raise DuplicateSource(f"source_id {source_id!r} repeats (compared case-folded)")
        seen.add(source_id.casefold())
        if item.media_type == HTML_MEDIA:
            data = convert_html(raw).text.encode("utf-8")
            if len(data) > MAX_BYTES:
                raise SourceTooLarge(f"{item.path}: converted text larger than {MAX_BYTES} bytes")
            media = "text/plain"
        elif item.media_type in _PACK_MEDIA:
            data, media = raw, item.media_type
        else:
            raise UnsupportedMedia(f"source {source_id!r}: media type {item.media_type!r}")
        filename = source_id + _SUFFIX[media]
        files.append(
            StagedFile(
                source_id,
                filename,
                data,
                hashlib.sha256(data).hexdigest(),
                hashlib.sha256(raw).hexdigest(),
                item.media_type,
            )
        )
        pack_request = SourceRequest.model_validate(
            {"source_id": source_id, "path": filename, "media_type": media}
        )
        _require_ready(pack_request, data)
        requests.append(pack_request)
    return files, requests


_WEB_CONFIG = "web-retrieval"
_RULING_UNUSED = "a research_ruling is only read when the research manifest has a url row"


def _web_fetcher() -> Fetcher:
    """The production fetcher: the system resolver, the pinned TLS connection, the item byte cap and
    ``time.monotonic`` as both the connection's clock and the fetch's (O7-R51, O7-R53). The module
    attributes are read at call time, so a test replaces them."""

    def fetcher(
        url: str, hosts: frozenset[str]
    ) -> tuple[webfetch.FetchRecord, bytes | None, str | None]:
        return webfetch.fetch(
            url,
            manifest_hosts=hosts,
            resolver=webfetch.system_resolver,
            connect=webfetch.pinned_connection,
            cap=MAX_ITEM_BYTES,
            clock=time.monotonic,
        )

    return fetcher


def _web_access(
    rows: Sequence[ManifestRow], research_ruling: Path | None
) -> tuple[GateResult | None, Fetcher | None]:
    """The web gate (O7b-2 D1, D2), before anything resolves. No ruling: no fetcher, so a url row
    is refused by ``intake`` naming the ruling it needs. A ruling with no url row is unused; a ruling
    that does not lift the pause for ``web-retrieval`` raises ``LivePauseInForce``."""
    if research_ruling is None:
        return None, None
    if not any(row.url is not None for row in rows):
        raise ResearchRulingUnused(_RULING_UNUSED)
    return check_ruling(_WEB_CONFIG, research_ruling), _web_fetcher()


def _research_staging(
    manifest: Path,
    context: RunContext,
    research_ruling: Path | None = None,
    earlier: Mapping[str, str] | None = None,
) -> ResearchStaging:
    """Read the research manifest and assess every row; writes nothing. Item refusals are listed on
    the result; a malformed manifest or a wrong row raises (``IntakeError`` and its kin).
    ``earlier`` maps a sha256 to the ``retrieved`` of an earlier run's evidence record (a rerun,
    O7-R67): an accepted item with such a sha256 keeps that instant, any other takes the clock."""
    raw = read_capped(manifest)
    try:
        rows = json.loads(raw)
    except (ValueError, RecursionError):  # not JSON, or nested past the parser's depth
        raise ResearchManifestInvalid(f"{manifest}: not valid JSON") from None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ResearchManifestInvalid(f"{manifest}: not a JSON list of rows")
    parsed = parse_rows(rows)
    ruling, fetcher = _web_access(parsed, research_ruling)
    as_of = date.fromisoformat(context.run.as_of)
    held = earlier or {}
    moment = evidence.research_clock()  # read once: the retrieval time and 'today' agree
    retrieved = evidence.retrieved_text(moment)
    result = intake(
        parsed,
        base_dir=manifest.parent,
        dest_dir=None,
        as_of=as_of,
        cutoff=effective_cutoff(as_of, context.run.cutoff),  # O7b-2 D9: min(as_of, run.cutoff)
        today=moment.date(),
        max_bytes=MAX_ITEM_BYTES,
        fetch=fetcher,
        retrieved=retrieved,
    )
    return ResearchStaging(
        hashlib.sha256(raw).hexdigest(),
        retrieved,
        result.accepted,
        result.refused,
        result.fetches if ruling is not None else (),
        ruling,
        {i.item_id: held[i.sha256] for i in result.accepted if i.sha256 in held},
    )


def _research_files(staging: ResearchStaging) -> tuple[list[StagedFile], list[SourceRequest]]:
    """Each accepted item as a staged ``ev-<n>.txt`` (text/plain) and a pack request, checked ready."""
    files: list[StagedFile] = []
    requests: list[SourceRequest] = []
    for item in staging.accepted:
        filename = f"{item.item_id}.txt"
        data = item.text.encode("utf-8")
        files.append(
            StagedFile(item.item_id, filename, data, item.sha256, item.sha256, "text/plain")
        )
        pack_request = SourceRequest.model_validate(
            {"source_id": item.item_id, "path": filename, "media_type": "text/plain"}
        )
        _require_ready(pack_request, data)
        requests.append(pack_request)
    return files, requests


def _with_cp_dr(request: PreparationRequest) -> PreparationRequest:
    """The request with ``CP-DR`` after the pathway's preset modules; presets are untouched."""
    run = request.run
    modules = (*run.requested_modules, "CP-DR")
    widened = Run.model_validate({**dict(run), "requested_modules": modules})
    return request.model_copy(update={"run": widened})


def _research_arguments(cp_dr: bool, manifest: Path | None, ruling: Path | None) -> None:
    if cp_dr and manifest is None:
        raise ResearchManifestRequired("cp_dr=True needs a research_manifest")
    if manifest is not None and not cp_dr:
        raise ResearchManifestUnused("a research_manifest is only read when cp_dr=True")
    if ruling is not None and manifest is None:
        raise ResearchRulingUnused(_RULING_UNUSED)


def check_arguments(
    *,
    case_id: str,
    sources: Sequence[CaseSource],
    context: Path,
    pathway: PathwayId,
    model: ModelSpec,
    adapter: ModelAdapter,
    cap_usd: Decimal,
    run_dir: Path,
    run_id: str,
    cp_dr: bool = False,
    research_manifest: Path | None = None,
    research_ruling: Path | None = None,
    resume: bool = False,
    replay_from: Path | None = None,
) -> CheckedRun:
    """Every call-shape check, in order, before any write. Raises a ``RunInputError``
    subclass, ``ContextRefused``, ``UndecodableHtml`` or a CP-DR ``ResearchError``; never writes.
    A ``research_ruling`` is read only when the research manifest has a url row.
    ``resume`` skips the check that ``run_dir`` is new: ``run_pathway`` checks a run directory it
    resumes itself. ``replay_from`` (the earlier run of a rerun) lets the research staging keep that
    run's ``retrieved`` for unchanged evidence (O7-R67); ``check_replay`` still decides whether the
    rerun is accepted, and a refused rerun writes nothing."""
    _research_arguments(cp_dr, research_manifest, research_ruling)
    if not resume:
        _check_run_dir(run_dir)
    gate = _check_adapter(adapter, model)
    _check_cap(cap_usd)
    _identifier(case_id, BadIdentifier, "case_id")
    _identifier(run_id, BadIdentifier, "run_id")
    context_raw = read_capped(context)
    source_raw = [read_capped(item.path) for item in sources]
    run_context = load_context(context_raw)
    if run_context.run.pathway != pathway:
        raise PathwayMismatch(f"context pathway {run_context.run.pathway!r} is not {pathway!r}")
    files, requests = _case_files(sources, source_raw)
    staging = None
    if research_manifest is not None:
        earlier = None if replay_from is None else evidence.earlier_retrieved(replay_from)
        staging = _research_staging(research_manifest, run_context, research_ruling, earlier)
        research_files, research_requests = _research_files(staging)
        files.extend(research_files)
        requests.extend(research_requests)
    request = preparation_request(
        run_context, run_id=run_id, context_path="context.json", sources=requests
    )
    if cp_dr:
        request = _with_cp_dr(request)
    files.append(
        StagedFile(
            CONTEXT_SOURCE_ID,
            "context.json",
            context_raw,
            hashlib.sha256(context_raw).hexdigest(),
            hashlib.sha256(context_raw).hexdigest(),
            "text/plain",
        )
    )
    return CheckedRun(
        case_id=case_id,
        run_id=run_id,
        pathway=pathway,
        model=model,
        adapter=adapter,
        gate=gate,
        cap_usd=cap_usd,
        cp_dr=cp_dr,
        context=run_context,
        files=tuple(files),
        request=request,
        research=staging,
    )


def _write_new(directory: Path, filename: str, data: bytes) -> None:
    target = (directory / filename).resolve()
    if target.parent != directory.resolve():
        raise RunInputError(f"staging path {filename!r} leaves the sources directory")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def stage_sources(checked: CheckedRun, run_dir: Path) -> None:
    """Create ``run_dir``, stage the bytes that were hashed (never a second read) under
    ``sources/`` and build the pack from that single root into ``pack.unverified``, renamed to ``pack`` only after
    every pack hash equals the staged hash (a fault leaves no ``pack``)."""
    try:
        os.mkdir(run_dir, 0o700)  # private: pack/originals and pack.json are written under it
    except FileExistsError:
        raise RunDirExists(f"{run_dir} already exists") from None
    sources = run_dir / "sources"
    if checked.research is not None:
        research = run_dir / evidence.RESEARCH_DIR
        os.mkdir(research)
        evidence.write_evidence(
            research / evidence.EVIDENCE_FILE,
            checked.research.accepted,
            checked.research.retrieved,
            checked.research.kept,
        )
        write_rejected(research / evidence.REJECTED_FILE, checked.research.refused)
        evidence.write_manifest_sha(
            research / evidence.MANIFEST_SHA_FILE, checked.research.manifest_sha256
        )
        if checked.research.ruling is not None:  # a web run: its fetch records and its ruling
            evidence.write_fetches(research / evidence.FETCHES_FILE, checked.research.fetches)
            evidence.write_manifest_sha(
                research / evidence.RULING_SHA_FILE, checked.research.ruling.sha256
            )
    os.mkdir(sources)
    for staged in checked.files:
        _write_new(sources, staged.filename, staged.data)
    unverified = run_dir / "pack.unverified"
    pack: PreparedPack = prepare(checked.request, sources, unverified)
    by_id = {source.source_id: source for source in pack.sources}
    for staged in checked.files:
        found = by_id.get(staged.source_id)
        if found is None or found.status != "ready" or found.sha256 != staged.sha256:
            raise StagedSourceChanged(f"prepare: source {staged.source_id} changed")
    os.rename(unverified, run_dir / "pack")


__all__ = [
    "AdapterRefused",
    "BadCap",
    "BadIdentifier",
    "BadSourceId",
    "CaseSource",
    "CheckedRun",
    "ConfigMismatch",
    "DuplicateSource",
    "PathwayMismatch",
    "ResearchManifestInvalid",
    "ResearchManifestRequired",
    "ResearchManifestUnused",
    "ResearchRulingUnused",
    "ResearchStaging",
    "RunDirExists",
    "RunDirInvalid",
    "RunInputError",
    "RunOutcome",
    "SourceTooLarge",
    "SourceUnreadable",
    "StagedFile",
    "StagedSourceChanged",
    "UnsupportedMedia",
    "check_arguments",
    "read_capped",
    "stage_sources",
]
