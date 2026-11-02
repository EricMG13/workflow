"""Call-shape checks and source staging for run_pathway (O2 Task 2). Offline; no key read."""

import json
import os
import signal
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Self

import cpdr_consumers as cc
import cpdr_runs as runs
import pytest
from cpdr_s1_support import ResearchCase, WebCase, key_file, web_file

from deploy_vii.preparation import MAX_BYTES, load_pack, prepare
from deploy_workflow import run_inputs
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
from deploy_workflow.research import evidence, webfetch
from deploy_workflow.research.contracts import EvidenceFetchRefused
from deploy_workflow.research.intake import MAX_ITEM_BYTES, intake
from deploy_workflow.run_inputs import (
    AdapterRefused,
    BadCap,
    BadIdentifier,
    BadSourceId,
    CaseSource,
    ConfigMismatch,
    DuplicateSource,
    PathwayMismatch,
    ResearchManifestRequired,
    ResearchManifestUnused,
    ResearchRulingUnused,
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
from deploy_workflow.workflow import WorkflowError

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


def test_reserved_source_id_case_variant_refused(args: dict[str, Any]) -> None:
    args["sources"][0] = CaseSource("CONTEXT", args["sources"][0].path, "text/html")
    refused(args, DuplicateSource)


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


def test_cp_dr_without_a_manifest_refused(args: dict[str, Any]) -> None:
    refused(args, ResearchManifestRequired, cp_dr=True)


def test_a_manifest_without_cp_dr_refused(args: dict[str, Any], tmp_path: Path) -> None:
    case = ResearchCase(tmp_path / "case")
    refused(args, ResearchManifestUnused, research_manifest=case.manifest_path)
    refused(args, ResearchManifestUnused, cp_dr=False, research_manifest=case.manifest_path)


@pytest.mark.parametrize("source_id", ["ev-1", "EV-7", "peers", "cp-dr-dossier"])
def test_reserved_research_ids(args: dict[str, Any], source_id: str) -> None:
    """Plan 4 row 2: a case source named like a research id is BadSourceId with the key's text."""
    texts = key_file("expected.json")["intake"]["refusal_texts"]["reserved_id"]
    args["sources"][1] = CaseSource(source_id, args["sources"][1].path, "text/plain")
    with pytest.raises(BadSourceId) as caught:
        check_arguments(**args)
    if source_id in texts:
        assert str(caught.value) == texts[source_id]
    assert not os.path.lexists(args["run_dir"])


def test_cp_dr_checks_the_manifest_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    moment = datetime(2026, 11, 2, 5, 40, 0, 999999, tzinfo=UTC)
    monkeypatch.setattr(evidence, "research_clock", lambda: moment)
    case = ResearchCase(tmp_path)
    arguments = {**case.arguments(tmp_path), "adapter": RecordedAdapter(MODEL, {})}
    before = sorted(tmp_path.rglob("*"))
    checked = check_arguments(**arguments)
    assert sorted(tmp_path.rglob("*")) == before
    assert [f.filename for f in checked.files] == [
        "identity.txt",
        "financial.txt",
        "ev-1.txt",
        "ev-2.txt",
        "ev-3.txt",
        "context.json",
    ]
    assert {f.media_type for f in checked.files if f.source_id.startswith("ev-")} == {"text/plain"}
    assert "CP-DR" in checked.request.run.requested_modules
    assert checked.research is not None
    key = key_file("expected.json")["intake"]
    assert [a.item_id for a in checked.research.accepted] == [x["item_id"] for x in key["accepted"]]
    assert [r.locator for r in checked.research.refused] == sorted(
        r["locator"] for r in key["rejected_json"]["entries"]
    )
    assert checked.research.retrieved == "2026-11-02T05:40:00Z"  # to the second, UTC (O7-R13)
    assert (
        checked.research.manifest_sha256
        == key_file("manifest.json")["research_manifest"]["file_sha256"]
    )


def test_presets_are_untouched_by_cp_dr(args: dict[str, Any]) -> None:
    preset = check_arguments(**args).request.run.requested_modules
    assert "CP-DR" not in preset


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
    previous = signal.signal(signal.SIGALRM, lambda *_: pytest.fail("blocked on a FIFO"))
    signal.alarm(5)
    try:
        refused(args, SourceUnreadable)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


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
    assert not (args["run_dir"] / "pack").exists()


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
    assert not (args["run_dir"] / "pack").exists()


def test_non_ready_status_with_matching_sha_is_a_fault(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked = check_arguments(**args)
    real = prepare

    def downgrading(request: Any, root: Path, destination: Path) -> Any:
        pack = real(request, root, destination)
        first = pack.sources[0].model_copy(update={"status": "unreadable", "limitation": "x"})
        return pack.model_copy(update={"sources": (first, *pack.sources[1:])})

    monkeypatch.setattr("deploy_workflow.run_inputs.prepare", downgrading)
    with pytest.raises(StagedSourceChanged, match="source s1 changed"):
        stage_sources(checked, args["run_dir"])
    assert not (args["run_dir"] / "pack").exists()


@pytest.mark.parametrize(
    ("data", "media"),
    [
        (b"", "text/plain"),
        (b"  \n\n", "text/plain"),
        (b"not a pdf", "application/pdf"),
        (b"not a zip", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        (b"<html><body></body></html>", "text/html"),
    ],
)
def test_unready_source_refused_before_any_write(
    args: dict[str, Any], tmp_path: Path, data: bytes, media: str
) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(data)
    args["sources"][1] = CaseSource("s2", bad, media)
    refused(args, SourceUnreadable)


def test_nul_in_a_path_is_unreadable(args: dict[str, Any], tmp_path: Path) -> None:
    nul = Path(str(tmp_path) + "/a\x00b")
    refused(args, SourceUnreadable, context=nul)
    args["sources"][1] = CaseSource("s2", nul, "text/plain")
    refused(args, SourceUnreadable)


def test_staged_files_are_private(args: dict[str, Any]) -> None:
    stage_sources(check_arguments(**args), args["run_dir"])
    for path in (args["run_dir"] / "sources").iterdir():
        assert path.stat().st_mode & 0o777 == 0o600


def test_converted_html_over_cap_refused(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    big = tmp_path / "big.html"
    big.write_bytes(b"<meta charset=windows-1252><p>" + b"\xe9" * 1900 + b"</p>")
    monkeypatch.setattr("deploy_workflow.run_inputs.MAX_BYTES", 2500)
    args["sources"][0] = CaseSource("s1", big, "text/html")
    refused(args, SourceTooLarge)


def test_read_capped_refuses_a_device() -> None:
    with pytest.raises(SourceUnreadable):
        read_capped(Path("/dev/null"))


def test_every_staged_file_carries_the_hash_of_the_bytes_read(args: dict[str, Any]) -> None:
    """HTML is staged converted: ``sha256`` is the converted bytes', ``original_sha256`` the file's."""
    import hashlib

    checked = check_arguments(**args)
    html, text, context = checked.files
    assert html.original_sha256 == hashlib.sha256(HTML).hexdigest()
    assert html.sha256 == hashlib.sha256(html.data).hexdigest() != html.original_sha256
    assert text.original_sha256 == text.sha256 == hashlib.sha256(b"plain text\n").hexdigest()
    raw = (ROOT / "cases/context/research-minimal.json").read_bytes()
    assert context.original_sha256 == context.sha256 == hashlib.sha256(raw).hexdigest()


def test_a_hard_link_planted_at_a_staging_path_is_refused_and_the_victim_survives(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A racer links a victim at ``sources/s1.txt`` between the mkdir and the write: ``resolve``
    cannot see a hard link, so ``O_EXCL`` is the only defence (kills the no-``O_EXCL`` mutant)."""
    checked = check_arguments(**args)
    victim = tmp_path / "victim.txt"
    victim.write_bytes(b"keep\n")
    real_mkdir = os.mkdir

    def planting(path: Any, *a: Any, **k: Any) -> None:
        real_mkdir(path, *a, **k)
        if str(path).endswith("sources"):
            os.link(victim, os.path.join(path, "s1.txt"))

    monkeypatch.setattr(os, "mkdir", planting)
    with pytest.raises(FileExistsError):
        stage_sources(checked, args["run_dir"])
    assert victim.read_bytes() == b"keep\n"


def test_the_run_dir_is_private(args: dict[str, Any]) -> None:
    old = os.umask(0o022)
    try:
        stage_sources(check_arguments(**args), args["run_dir"])
    finally:
        os.umask(old)
    assert args["run_dir"].stat().st_mode & 0o777 == 0o700


def test_a_staged_file_carries_the_callers_media_type(args: dict[str, Any]) -> None:
    checked = check_arguments(**args)
    assert [f.media_type for f in checked.files] == ["text/html", "text/plain", "text/plain"]


# ---- the research_ruling argument (O7b-2 S4) against cases/cpdr-web-retrieval ----


def web_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, with_urls: bool = True
) -> tuple[WebCase, dict[str, Any]]:
    case = WebCase(tmp_path, with_urls=with_urls)
    case.install(monkeypatch)
    return case, {**case.arguments(tmp_path), "adapter": RecordedAdapter(MODEL, {})}


def test_url_rows_without_ruling_are_refused_before_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`#gate/no_ruling/{exception,text}`, `#gate/resolver_calls_before_gate`: nothing resolved,
    nothing written."""
    case, arguments = web_arguments(tmp_path, monkeypatch)
    key = web_file("expected.json")["gate"]
    with pytest.raises(EvidenceFetchRefused) as raised:
        check_arguments(**{**arguments, "research_ruling": None})
    assert type(raised.value).__name__ == key["no_ruling"]["exception"]
    assert str(raised.value) == key["no_ruling"]["text"]
    assert len(case.resolved) == key["resolver_calls_before_gate"] and case.requests == []
    assert not os.path.lexists(arguments["run_dir"])


def test_ruling_without_url_rows_is_unused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`#gate/unused_ruling/{exception,text}`: a ruling is read only when a row has a url."""
    case, arguments = web_arguments(tmp_path, monkeypatch, with_urls=False)
    key = web_file("expected.json")["gate"]["unused_ruling"]
    with pytest.raises(ResearchRulingUnused) as raised:
        check_arguments(**arguments)
    assert type(raised.value).__name__ == key["exception"]
    assert str(raised.value) == key["text"]
    assert case.resolved == [] and not os.path.lexists(arguments["run_dir"])


@pytest.mark.parametrize("name", ["configs_missing", "lifts_missing"])
def test_bad_ruling_is_refused_before_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """`#gate/{configs_missing,lifts_missing}/{exception,text}` and
    `#gate/resolver_calls_before_gate`: the gate runs before the first resolver call."""
    case, arguments = web_arguments(tmp_path, monkeypatch)
    key = web_file("expected.json")["gate"][name]
    arguments["research_ruling"] = case.write_ruling(name)
    with pytest.raises(LivePauseInForce) as raised:
        check_arguments(**arguments)
    assert type(raised.value).__name__ == key["exception"]
    assert str(raised.value) == key["text"]
    assert len(case.resolved) == web_file("expected.json")["gate"]["resolver_calls_before_gate"]
    assert case.requests == [] and not os.path.lexists(arguments["run_dir"])


def test_a_ruling_without_a_manifest_is_unused(tmp_path: Path) -> None:
    ruling = tmp_path / "r.md"
    ruling.write_text("x", encoding="utf-8")
    case = ResearchCase(tmp_path)
    arguments = {**case.arguments(tmp_path), "adapter": RecordedAdapter(MODEL, {})}
    arguments.update(cp_dr=False, research_manifest=None, research_ruling=ruling)
    with pytest.raises(ResearchRulingUnused):
        check_arguments(**arguments)


def test_the_production_fetcher_uses_the_monotonic_clock_and_the_real_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O7b-2 S4 review L-2: `_web_fetcher()` hands `webfetch.fetch` `time.monotonic` as the clock
    (a mutant to `time.time` survived), the system resolver, the pinned connection and the item
    byte cap, all read at call time."""
    seen: dict[str, Any] = {}

    def spy(url: str, **kwargs: Any) -> tuple[None, None, None]:
        seen.update(kwargs, url=url)
        return None, None, None

    monkeypatch.setattr(webfetch, "fetch", spy)
    run_inputs._web_fetcher()("https://sector-desk.example/x", frozenset({"sector-desk.example"}))
    assert seen["clock"] is time.monotonic
    assert seen["resolver"] is webfetch.system_resolver
    assert seen["connect"] is webfetch.pinned_connection
    assert seen["cap"] == MAX_ITEM_BYTES
    assert seen["manifest_hosts"] == frozenset({"sector-desk.example"})


def test_intake_is_given_the_research_clocks_retrieval_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7b-2 S4 review L-2: `intake`'s `retrieved` is the instant the research clock gave, the one
    every `#records/evidence_json/rows/*/retrieved` records (a mutant that dropped it survived)."""
    seen: list[str] = []
    real = intake

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen.append(kwargs["retrieved"])
        return real(*args, **kwargs)

    monkeypatch.setattr("deploy_workflow.run_inputs.intake", spy)
    _case, arguments = web_arguments(tmp_path, monkeypatch)
    check_arguments(**arguments)
    rows = web_file("expected.json")["records"]["evidence_json"]["rows"]
    assert seen == [rows[0]["retrieved"]]
    assert {row["retrieved"] for row in rows} == set(seen)


LATER_CLOCK = datetime(2026, 11, 2, 6, 40, 0, tzinfo=UTC)
LATER_TEXT = "2026-11-02T06:40:00Z"


def rerun_arguments(base: Path, earlier: Path, **change: Any) -> dict[str, Any]:
    return ResearchCase(base).arguments(base, run_id="rerun-1", replay_from=earlier, **change)


def test_a_rerun_keeps_the_earlier_retrieved_for_unchanged_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7-R67: staging a rerun that names a run with a settled CP-DR head keeps that run's
    `retrieved` for each item whose sha256 is a row of its `research/evidence.json`; an item whose
    bytes changed takes the clock."""
    earlier = cc.settled_through_cpdr(tmp_path / "earlier", ("CP-1", "CP-DR"), name="execution")
    monkeypatch.setattr(evidence, "research_clock", lambda: LATER_CLOCK)
    base = tmp_path / "second"
    case = ResearchCase(base)
    rows = json.loads(case.manifest_path.read_text("utf-8"))
    changed = case.inputs / rows[0]["path"]
    changed.write_text(changed.read_text("utf-8") + "\nA new sentence.\n", encoding="utf-8")
    (case.inputs / "extra.txt").write_text("A fresh note on input costs.\n", encoding="utf-8")
    extra = {**rows[0], "path": "extra.txt", "locator": "line:1"}
    case.manifest_path.write_text(json.dumps([*rows, extra]), encoding="utf-8")
    arguments = case.arguments(base, run_id="rerun-1", replay_from=earlier.directory.parent)
    stage_sources(check_arguments(**arguments), base / "run")
    staged = evidence.read_evidence(base / "run" / "research" / "evidence.json")
    by_item = {row["item_id"]: row["retrieved"] for row in staged}
    changed_id = next(r["item_id"] for r in staged if r["path"] == rows[0]["path"])
    new_id = next(r["item_id"] for r in staged if r["path"] == "extra.txt")
    unchanged = set(by_item) - {changed_id, new_id}
    assert len(unchanged) == 2 and changed_id != new_id
    assert by_item[changed_id] == LATER_TEXT  # changed bytes: the clock
    assert by_item[new_id] == LATER_TEXT  # a new item: the clock
    assert {by_item[i] for i in unchanged} == {runs.RETRIEVED}  # unchanged bytes: kept


def test_a_rerun_of_a_run_without_a_settled_cp_dr_head_keeps_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: an earlier run staged but never settled through CP-DR authenticates nothing, so every
    item takes the clock."""
    monkeypatch.setattr(
        evidence, "research_clock", lambda: datetime(2026, 11, 2, 5, 40, tzinfo=UTC)
    )
    first = tmp_path / "first"
    stage_sources(check_arguments(**ResearchCase(first).arguments(first)), first / "run")
    monkeypatch.setattr(evidence, "research_clock", lambda: LATER_CLOCK)
    second = tmp_path / "second"
    checked = check_arguments(**rerun_arguments(second, first / "run"))
    assert checked.research is not None and checked.research.kept == {}


def test_an_edited_earlier_evidence_record_is_refused_before_anything_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: the earlier run's `evidence.json` must be the bytes its settled CP-DR head bound
    (`cpdr.check_records`); an edited `retrieved` is `identity_mismatch`, never kept."""
    earlier = cc.settled_through_cpdr(tmp_path / "earlier", ("CP-1", "CP-DR"), name="execution")
    record = earlier.directory.parent / "research" / "evidence.json"
    rows = json.loads(record.read_text(encoding="utf-8"))
    rows[0]["retrieved"] = "2000-01-01T00:00:00Z"
    record.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(evidence, "research_clock", lambda: LATER_CLOCK)
    second = tmp_path / "second"
    with pytest.raises(WorkflowError) as refused:
        check_arguments(**rerun_arguments(second, earlier.directory.parent))
    assert refused.value.code == "identity_mismatch"
    assert not (second / "run").exists()


def _unsettled_earlier(root: Path, block: bool) -> Path:
    """An earlier run directory whose execution/ has no settled CP-DR head: CP-0 and CP-1 settled
    and no CP-DR head, or (``block``) CP-DR settled and then written `blocked`; its
    `evidence.json` `retrieved` is then edited."""
    requested = ("CP-1", "CP-DR", "CP-1C")
    if block:
        store = cc.settled_through_cpdr(root, requested, name="execution")
        runs.edit_head(store, "CP-DR", status="blocked")
        assert cc.head(store, "CP-DR").status == "blocked"
    else:
        store = cc.store_with(root, requested, name="execution")
        for module_id in ("CP-0", "CP-1"):
            cc.hand_settle(store, module_id)
        assert all(h.module_id != "CP-DR" for h in store.read().heads)
    record = root / "research" / "evidence.json"
    rows = json.loads(record.read_text(encoding="utf-8"))
    rows[0]["retrieved"] = "2000-01-01T00:00:00Z"
    record.write_text(json.dumps(rows), encoding="utf-8")
    return root


@pytest.mark.parametrize("block", [False, True], ids=["no_cp_dr_head", "blocked_cp_dr_head"])
def test_an_earlier_run_without_a_settled_cp_dr_head_keeps_nothing_even_if_edited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, block: bool
) -> None:
    """L2 head gate: with no settled CP-DR head there is nothing to authenticate the earlier
    record against, so an edited `retrieved` is not kept and every item takes the clock."""
    earlier = _unsettled_earlier(tmp_path / "earlier", block)
    monkeypatch.setattr(evidence, "research_clock", lambda: LATER_CLOCK)
    checked = check_arguments(**rerun_arguments(tmp_path / "second", earlier))
    assert checked.research is not None and checked.research.kept == {}
