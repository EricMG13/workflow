"""Call-shape checks and source staging for run_pathway (O2 Task 2). Offline; no key read."""

import os
import signal
from decimal import Decimal
from pathlib import Path
from typing import Any, Self

import pytest

from deploy_vii.preparation import MAX_BYTES, load_pack, prepare
from deploy_workflow.context import ContextRefused
from deploy_workflow.html_text import UndecodableHtml, convert_html
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    LiveAdapter,
    LivePauseInForce,
    RecordedAdapter,
    live_adapter,
)
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.run_inputs import (
    AdapterRefused,
    BadCap,
    BadIdentifier,
    BadSourceId,
    CaseSource,
    ConfigMismatch,
    CpDrNotBuilt,
    DuplicateSource,
    PathwayMismatch,
    RunDirExists,
    RunDirInvalid,
    SourceTooLarge,
    SourceUnreadable,
    StagedSourceChanged,
    UnsupportedMedia,
    check_arguments,
    read_capped,
    stage_sources,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
HTML = b"<html><body><table><tr><td>Revenue</td><td>1,234</td></tr></table></body></html>"
RULING = "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: sol-medium\n"


class ScriptAdapter:
    """A live-calling duck type that reports no ruling: must be refused by exact type."""

    config_id = "sol-medium"
    ruling = None

    def complete(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("never called")


class SubRecorded(RecordedAdapter):
    pass


@pytest.fixture
def args(tmp_path: Path) -> dict[str, Any]:
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.html").write_bytes(HTML)
    (src / "b.txt").write_bytes(b"plain text\n")
    return {
        "case_id": "case-1",
        "sources": [
            CaseSource("s1", src / "a.html", "text/html"),
            CaseSource("s2", src / "b.txt", "text/plain"),
        ],
        "context": ROOT / "cases/context/research-minimal.json",
        "pathway": "credit_snapshot",
        "model": MODEL,
        "adapter": RecordedAdapter(MODEL, {}),
        "cap_usd": Decimal(1),
        "run_dir": tmp_path / "run",
        "run_id": "run-1",
    }


def refused(args: dict[str, Any], error: type[Exception], **change: Any) -> None:
    args = {**args, **change}
    with pytest.raises(error):
        check_arguments(**args)
    assert not os.path.lexists(args["run_dir"])


def test_valid_arguments_check_and_do_not_write(args: dict[str, Any]) -> None:
    checked = check_arguments(**args)
    assert [f.filename for f in checked.files] == ["s1.txt", "s2.txt", "context.json"]
    assert checked.gate is None
    assert not args["run_dir"].exists()


def test_existing_run_dir_refused(args: dict[str, Any]) -> None:
    args["run_dir"].mkdir()
    with pytest.raises(RunDirExists):
        check_arguments(**args)
    assert list(args["run_dir"].iterdir()) == []


def test_dangling_symlink_run_dir_refused(args: dict[str, Any], tmp_path: Path) -> None:
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "nowhere")
    with pytest.raises(RunDirExists):
        check_arguments(**{**args, "run_dir": link})
    assert not (tmp_path / "nowhere").exists()


def test_missing_parent_refused(args: dict[str, Any], tmp_path: Path) -> None:
    refused(args, RunDirInvalid, run_dir=tmp_path / "no" / "run")


def test_duck_typed_adapter_with_no_ruling_refused(args: dict[str, Any]) -> None:
    refused(args, AdapterRefused, adapter=ScriptAdapter())


def test_subclass_of_recorded_adapter_refused(args: dict[str, Any]) -> None:
    refused(args, AdapterRefused, adapter=SubRecorded(MODEL, {}))


def test_config_mismatch_refused(args: dict[str, Any]) -> None:
    other = ModelSpec("sol-high", "openai", "gpt-6.1-sol", "high")
    refused(args, ConfigMismatch, adapter=RecordedAdapter(other, {}))


@pytest.mark.parametrize("cap", [Decimal(0), Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_bad_cap_refused(args: dict[str, Any], cap: Decimal) -> None:
    refused(args, BadCap, cap_usd=cap)


def test_float_cap_refused(args: dict[str, Any]) -> None:
    refused(args, BadCap, cap_usd=1.0)


@pytest.mark.parametrize("field", ["case_id", "run_id"])
def test_bad_case_or_run_id_refused(args: dict[str, Any], field: str) -> None:
    refused(args, BadIdentifier, **{field: "bad id"})


def test_pathway_mismatch_refused(args: dict[str, Any]) -> None:
    refused(args, PathwayMismatch, pathway="covenant_refinancing")


def test_bad_context_refused(args: dict[str, Any], tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"{}")
    refused(args, ContextRefused, context=bad)


@pytest.mark.parametrize("bad", ["bad id", "a/b", "../x", ""])
def test_bad_source_id_refused(args: dict[str, Any], bad: str) -> None:
    args["sources"][0] = CaseSource(bad, args["sources"][0].path, "text/html")
    refused(args, BadSourceId)


def test_reserved_source_id_refused(args: dict[str, Any]) -> None:
    args["sources"][0] = CaseSource("context", args["sources"][0].path, "text/html")
    refused(args, BadSourceId)


@pytest.mark.parametrize("second", ["s1", "S1"])
def test_duplicate_source_id_refused_after_casefold(args: dict[str, Any], second: str) -> None:
    args["sources"][1] = CaseSource(second, args["sources"][1].path, "text/plain")
    refused(args, DuplicateSource)


def test_unsupported_media_refused(args: dict[str, Any]) -> None:
    args["sources"][1] = CaseSource("s2", args["sources"][1].path, "text/csv")
    refused(args, UnsupportedMedia)


def test_undecodable_html_refused(args: dict[str, Any], tmp_path: Path) -> None:
    bad = tmp_path / "bad.html"
    bad.write_bytes(b"<p>caf\xe9</p>")
    args["sources"][0] = CaseSource("s1", bad, "text/html")
    refused(args, UndecodableHtml)


def test_cp_dr_refused(args: dict[str, Any]) -> None:
    refused(args, CpDrNotBuilt, cp_dr=True)


def test_over_cap_source_refused_and_read_is_bounded(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    big = tmp_path / "big.txt"
    with big.open("wb") as handle:
        handle.truncate(MAX_BYTES + 1)
    sizes: list[int] = []
    real = os.fdopen

    class Spy:
        def __init__(self, inner: Any) -> None:
            self.inner = inner

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *exc: object) -> None:
            self.inner.close()

        def fileno(self) -> int:
            return int(self.inner.fileno())

        def read(self, size: int = -1) -> bytes:
            sizes.append(size)
            return bytes(self.inner.read(size))

    monkeypatch.setattr(os, "fdopen", lambda fd, mode: Spy(real(fd, mode)))
    args["sources"][1] = CaseSource("s2", big, "text/plain")
    refused(args, SourceTooLarge)
    assert sizes and max(sizes) == MAX_BYTES + 1 and -1 not in sizes


def test_directory_source_refused(args: dict[str, Any], tmp_path: Path) -> None:
    args["sources"][1] = CaseSource("s2", tmp_path, "text/plain")
    refused(args, SourceUnreadable)


def test_fifo_source_refused_without_blocking(args: dict[str, Any], tmp_path: Path) -> None:
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    args["sources"][1] = CaseSource("s2", fifo, "text/plain")
    signal.signal(signal.SIGALRM, lambda *_: pytest.fail("blocked on a FIFO"))
    signal.alarm(5)
    try:
        refused(args, SourceUnreadable)
    finally:
        signal.alarm(0)


def test_missing_source_refused(args: dict[str, Any], tmp_path: Path) -> None:
    args["sources"][1] = CaseSource("s2", tmp_path / "gone.txt", "text/plain")
    refused(args, SourceUnreadable)


def test_read_capped_returns_bytes(tmp_path: Path) -> None:
    path = tmp_path / "f"
    path.write_bytes(b"abc")
    assert read_capped(path) == b"abc"


def test_real_ruling_makes_live_adapter_raise() -> None:
    with pytest.raises(LivePauseInForce):
        live_adapter(MODEL, ROOT / "docs/rulings/2026-10-31-context-plan.md")


def test_live_adapter_gate_is_read_once_from_the_adapter(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "rulings"
    root.mkdir()
    ruling = root / "lift.md"
    ruling.write_text(RULING, encoding="utf-8")
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", root)
    adapter = live_adapter(MODEL, ruling, environ={})
    assert type(adapter) is LiveAdapter
    # a later check against a different default root must not matter: the gate is the adapter's
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", tmp_path / "elsewhere")
    checked = check_arguments(**{**args, "adapter": adapter})
    assert checked.gate == adapter.gate
    assert not args["run_dir"].exists()


def test_stage_positive(args: dict[str, Any]) -> None:
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    sources = args["run_dir"] / "sources"
    assert sorted(p.name for p in sources.iterdir()) == ["context.json", "s1.txt", "s2.txt"]
    assert (sources / "s1.txt").read_bytes() == convert_html(HTML).text.encode()
    assert (sources / "s2.txt").read_bytes() == b"plain text\n"
    pack = load_pack(args["run_dir"] / "pack")
    assert [s.source_id for s in pack.sources] == ["s1", "s2", "context"]
    assert next(s for s in pack.sources if s.source_id == "context").media_type == "text/plain"
    assert all(s.status == "ready" for s in pack.sources)


def test_stage_uses_the_bytes_read_not_a_second_read(args: dict[str, Any]) -> None:
    checked = check_arguments(**args)
    args["sources"][1].path.write_bytes(b"changed after the check\n")
    stage_sources(checked, args["run_dir"])
    assert (args["run_dir"] / "sources" / "s2.txt").read_bytes() == b"plain text\n"


def test_lost_mkdir_race_writes_nothing(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked = check_arguments(**args)
    other = args["run_dir"]
    other.mkdir()

    def lost(path: Any, *a: Any, **k: Any) -> None:
        raise FileExistsError(path)

    monkeypatch.setattr(os, "mkdir", lost)
    with pytest.raises(RunDirExists):
        stage_sources(checked, other)
    assert list(other.iterdir()) == []


def test_file_replaced_before_prepare_is_a_fault(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked = check_arguments(**args)
    real = prepare

    def swapping(request: Any, root: Path, destination: Path) -> Any:
        (root / "s1.txt").write_bytes(b"tampered\n")
        return real(request, root, destination)

    monkeypatch.setattr("deploy_workflow.run_inputs.prepare", swapping)
    with pytest.raises(StagedSourceChanged, match="prepare: source s1 changed"):
        stage_sources(checked, args["run_dir"])


def test_file_vanished_before_prepare_is_a_fault(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked = check_arguments(**args)
    real = prepare

    def vanishing(request: Any, root: Path, destination: Path) -> Any:
        (root / "s2.txt").unlink()
        return real(request, root, destination)

    monkeypatch.setattr("deploy_workflow.run_inputs.prepare", vanishing)
    with pytest.raises(StagedSourceChanged, match="source s2 changed"):
        stage_sources(checked, args["run_dir"])
