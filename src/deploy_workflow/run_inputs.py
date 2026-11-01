"""Input checks and the single pack root for ``run_pathway`` (O2 Task 2).

``check_arguments`` performs every check of the ``run_pathway`` call shape before anything is
written; ``stage_sources`` then writes the bytes that were read and hashed into ``run_dir/sources``
and builds the pack from that one root. Nothing here reads the environment or the network, and no
check is skipped on failure: each refusal is a named ``RunInputError`` subclass with a stable
``code``. A crashed run leaves a run directory without ``run.json``.
"""

import hashlib
import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import ClassVar, Literal, get_args

from pydantic import TypeAdapter, ValidationError

from deploy_vii.contracts import Identifier, PathwayId
from deploy_vii.preparation import (
    MAX_BYTES,
    PreparationRequest,
    PreparedPack,
    SourceRequest,
    prepare,
)
from deploy_workflow.context import CONTEXT_SOURCE_ID, RunContext, load_context, preparation_request
from deploy_workflow.html_text import convert_html
from deploy_workflow.model.adapter import GateResult, LiveAdapter, ModelAdapter, RecordedAdapter
from deploy_workflow.model.turn import ModelSpec

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


class CpDrNotBuilt(RunInputError):
    code = "cp_dr_not_built"


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
    """One file to stage: the bytes that were read (or converted) and their sha256."""

    source_id: str
    filename: str
    data: bytes
    sha256: str


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
    files: tuple[StagedFile, ...]  # sources in call order, then context.json
    request: PreparationRequest


def read_capped(path: Path) -> bytes:
    """Read a regular file through one descriptor: open without blocking, ``fstat`` that
    descriptor (FIFO, directory, device refused), then read at most ``MAX_BYTES + 1`` from it."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as error:
        raise SourceUnreadable(f"{path}: cannot open ({error.strerror})") from None
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
) -> CheckedRun:
    """Every call-shape check, in order, before any write. Raises a ``RunInputError``
    subclass, ``ContextRefused`` or ``UndecodableHtml``; never writes."""
    _check_run_dir(run_dir)
    gate = _check_adapter(adapter, model)
    if not (isinstance(cap_usd, Decimal) and cap_usd.is_finite() and cap_usd > 0):
        raise BadCap(f"cap_usd {cap_usd!r} is not a finite Decimal above zero")
    _identifier(case_id, BadIdentifier, "case_id")
    _identifier(run_id, BadIdentifier, "run_id")
    context_raw = read_capped(context)
    source_raw = [read_capped(item.path) for item in sources]
    run_context = load_context(context_raw)
    if run_context.run.pathway != pathway:
        raise PathwayMismatch(f"context pathway {run_context.run.pathway!r} is not {pathway!r}")
    files: list[StagedFile] = []
    requests: list[SourceRequest] = []
    seen: set[str] = set()
    for item, raw in zip(sources, source_raw, strict=True):
        source_id = _identifier(item.source_id, BadSourceId, "source_id")
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
        files.append(StagedFile(source_id, filename, data, hashlib.sha256(data).hexdigest()))
        requests.append(
            SourceRequest.model_validate(
                {"source_id": source_id, "path": filename, "media_type": media}
            )
        )
    if cp_dr:
        raise CpDrNotBuilt("cp_dr=True is refused until O7b")
    request = preparation_request(
        run_context, run_id=run_id, context_path="context.json", sources=requests
    )
    files.append(
        StagedFile(
            CONTEXT_SOURCE_ID, "context.json", context_raw, hashlib.sha256(context_raw).hexdigest()
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
    )


def _write_new(directory: Path, filename: str, data: bytes) -> None:
    target = (directory / filename).resolve()
    if target.parent != directory.resolve():
        raise RunInputError(f"staging path {filename!r} leaves the sources directory")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def stage_sources(checked: CheckedRun, run_dir: Path) -> None:
    """Create ``run_dir``, stage the bytes that were hashed (never a second read) under
    ``sources/`` and build the pack at ``run_dir/pack`` from that single root."""
    try:
        os.mkdir(run_dir)
    except FileExistsError:
        raise RunDirExists(f"{run_dir} already exists") from None
    sources = run_dir / "sources"
    os.mkdir(sources)
    for staged in checked.files:
        _write_new(sources, staged.filename, staged.data)
    pack: PreparedPack = prepare(checked.request, sources, run_dir / "pack")
    by_id = {source.source_id: source for source in pack.sources}
    for staged in checked.files:
        found = by_id.get(staged.source_id)
        if found is None or found.status != "ready" or found.sha256 != staged.sha256:
            raise StagedSourceChanged(f"prepare: source {staged.source_id} changed")


__all__ = [
    "AdapterRefused",
    "BadCap",
    "BadIdentifier",
    "BadSourceId",
    "CaseSource",
    "CheckedRun",
    "ConfigMismatch",
    "CpDrNotBuilt",
    "DuplicateSource",
    "PathwayMismatch",
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
