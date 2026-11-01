"""O3 Task 4 (G4): a rerun after repair replays the retained upstream submissions.

The earlier runs are authored from the frozen ``cases/o2-synthetic`` payloads through ``o2_case``'s
``ScriptAdapter`` (CP-0 settled, then the script ends and CP-1 stops the run on a missing recording:
the fast world, P19). The rerun repairs ``CP-1``: CP-0 is replayed, CP-1 runs live. Tests that need
the walk past CP-1 are gated by ``RUN_PROMOTION`` and written, never run here (B16, T4-R1).
Part A is the plan and the refusals, part B the replay of a module, part C the rerun through
``run_pathway``.
"""

import dataclasses
import http.client
import shutil
import socket
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import o2_case
import pytest

from deploy_vii.preparation import load_pack
from deploy_workflow import replay
from deploy_workflow import run_pathway as rp
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.owner_workflow import (
    AUDIT,
)
from deploy_workflow.replay import (
    ReplayPackChanged,
    ReplayRefused,
)
from deploy_workflow.run_inputs import CaseSource, RunInputError, check_arguments, stage_sources

EARLIER_ID = o2_case.RUN_ID  # the frozen payloads bind the pack of this run id
RERUN_ID = "o2-synthetic-rerun"
PLANNED = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3", "CP-5", "CP-6", "CP-8")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


# ================================================================================== part A
# the worlds, the plan and the refusals


class CallingScript(o2_case.ScriptAdapter):
    """CP-0 reads a page and searches the pack before it submits: retained calls to replay."""

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        plan = super()._plan(step_id, reads)
        if step_id != "source_readiness":
            return plan
        return [
            ("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
            ("search_pack", {"query": "subsequent", "source_id": "financial"}),
            *plan,
        ]


def checked_run(
    root: Path, run_id: str, sources: list[CaseSource] | None = None
) -> tuple[Any, Path]:
    """``check_arguments`` over the o2 case under ``root`` (nothing is written): the checked run
    and the run directory it would stage."""
    empty = root / "check-recordings"
    empty.mkdir(parents=True, exist_ok=True)
    run_dir = root / "run"
    checked = check_arguments(
        case_id=o2_case.CASE_ID,
        sources=o2_case.case_sources() if sources is None else sources,
        context=o2_case.CASE / "context.json",
        pathway=o2_case.PATHWAY,
        model=o2_case.MODEL,
        adapter=recorded_adapter(o2_case.MODEL, empty),
        cap_usd=o2_case.CAP,
        run_dir=run_dir,
        run_id=run_id,
    )
    return checked, run_dir


def author_earlier(
    root: Path,
    *,
    run_id: str = EARLIER_ID,
    script: type[o2_case.ScriptAdapter] = CallingScript,
    cap: Decimal | None = None,
) -> Path:
    """An earlier run: the script answers CP-0 and the run stops at the next request."""
    checked, run_dir = checked_run(root, run_id)
    if cap is not None:
        checked = dataclasses.replace(checked, cap_usd=cap)
    stage_sources(checked, run_dir)
    recordings = root / "recordings"
    recordings.mkdir()
    adapter = script(recordings, ("source_readiness",), run_dir / "execution", o2_case.MODEL)
    outcome = rp._run_pathway(checked, run_dir, adapter, o2_case.test_prompt_for)
    assert outcome.outcome == "stopped"
    return run_dir


def audit(run_dir: Path, kind: str) -> list[Path]:
    folder = run_dir / "execution" / AUDIT / kind
    return sorted(folder.iterdir()) if folder.is_dir() else []


def copy_of(earlier: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "copy"
    shutil.copytree(earlier, copy)
    return copy


@pytest.fixture
def earlier_run(tmp_path: Path) -> Path:
    return author_earlier(tmp_path / "earlier")


@pytest.mark.parametrize(
    ("repaired", "replayed", "live"),
    [
        ("CP-3", ("CP-0", "CP-1", "CP-1A", "CP-2"), ("CP-3", "CP-5", "CP-6", "CP-8")),
        ("CP-2", ("CP-0", "CP-1", "CP-1A"), ("CP-2", "CP-3", "CP-5", "CP-6", "CP-8")),
        # CP-1A cites CP-1 figures though its registry edge is CP-0 only: it follows CP-1
        ("CP-1", ("CP-0",), ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8")),
        ("CP-6", ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5"), ("CP-6", "CP-8")),
    ],
)
def test_live_is_the_repaired_modules_and_their_downstream(
    repaired: str,
    replayed: tuple[str, ...],
    live: tuple[str, ...],
    earlier_run: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The graph is the registry's (plus the context producer edge). The earlier run is made to
    hold every module, so only the graph decides; CP-MODEL is never replayed or listed."""
    monkeypatch.setattr(replay._Earlier, "unusable", lambda self, module: None)
    found = replay.plan_replay(earlier_run, PLANNED, frozenset({repaired}))
    assert (found.replayed, found.live, found.unreplayable) == (replayed, live, ())
    assert "CP-MODEL" not in found.replayed + found.live


def test_plan_goes_live_for_a_module_the_earlier_run_never_settled(earlier_run: Path) -> None:
    found = replay.plan_replay(earlier_run, PLANNED, frozenset({"CP-3"}))
    assert found.replayed == ("CP-0",)  # CP-1 was never settled in the earlier run
    reasons = dict(found.unreplayable)
    assert "CP-1" in reasons and "no settled, valid attempt" in reasons["CP-1"]
    assert found.live == ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8")
    assert found.earlier_run_id == EARLIER_ID
    with pytest.raises(ReplayRefused):
        replay.plan_replay(earlier_run, PLANNED, frozenset())
    with pytest.raises(ReplayRefused):
        replay.plan_replay(earlier_run, PLANNED, frozenset({"CP-MODEL"}))


@pytest.mark.parametrize(
    "case",
    [
        "no-repaired",
        "no-replay-from",
        "missing-replay-from",
        "replay-from-is-run-dir",
        "same-run-id",
        "unplanned-module",
        "publisher-module",
        "no-execution",
    ],
)
def test_check_replay_refuses_and_writes_nothing(
    case: str, tmp_path: Path, earlier_run: Path
) -> None:
    run_id = EARLIER_ID if case == "same-run-id" else RERUN_ID
    checked, run_dir = checked_run(tmp_path / "rerun", run_id)
    repaired = frozenset({"CP-1"})
    earlier: Path | None = earlier_run
    if case == "no-repaired":
        repaired = frozenset()
    elif case == "no-replay-from":
        earlier = None
    elif case == "missing-replay-from":
        earlier = tmp_path / "no-such-run"
    elif case == "replay-from-is-run-dir":
        run_dir = earlier_run
    elif case == "unplanned-module":
        repaired = frozenset({"CP-6A"})
    elif case == "publisher-module":
        repaired = frozenset({"CP-MODEL"})
    elif case == "no-execution":
        earlier = tmp_path / "bare"
        earlier.mkdir()
        (earlier / "run.json").write_text("{}")
    with pytest.raises(RunInputError):
        replay.check_replay(checked, run_dir, earlier, repaired)
    assert not (tmp_path / "rerun" / "run").exists()


def test_a_torn_call_record_refuses_the_rerun(tmp_path: Path, earlier_run: Path) -> None:
    copy = copy_of(earlier_run, tmp_path)
    path = audit(copy, "calls")[0]
    path.write_text(path.read_text() + " ")
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID)
    with pytest.raises(ReplayRefused, match="torn"):
        replay.check_replay(checked, run_dir, copy, frozenset({"CP-1"}))


def test_a_changed_source_set_is_refused_and_nothing_is_left_behind(
    tmp_path: Path, earlier_run: Path
) -> None:
    sources = o2_case.case_sources()
    extra = tmp_path / "extra.txt"
    extra.write_text("Another source.\n")
    changed = tmp_path / "business-changed.txt"
    changed.write_text(sources[2].path.read_text() + "One more sentence.\n")
    variants = {
        "added": [*sources, CaseSource("extra", extra, "text/plain")],
        "dropped": sources[:-1],
        "changed": [*sources[:2], CaseSource("business", changed, "text/plain"), sources[3]],
    }
    for name, edited in variants.items():
        checked, run_dir = checked_run(tmp_path / name, RERUN_ID, edited)
        with pytest.raises(ReplayPackChanged):
            replay.check_replay(checked, run_dir, earlier_run, frozenset({"CP-1"}))
        assert [p.name for p in (tmp_path / name).iterdir()] == ["check-recordings"], name
    checked, run_dir = checked_run(tmp_path / "same", RERUN_ID)
    assert replay.check_replay(checked, run_dir, earlier_run, frozenset({"CP-1"})).replayed == (
        "CP-0",
    )


PACK_FIELDS = {
    "spans": lambda s: s.model_copy(update={"spans": s.spans[:-1]}),
    "extraction_status": lambda s: s.model_copy(
        update={
            "extraction_status": "degraded" if s.extraction_status == "complete" else "complete"
        }
    ),
    "extractor": lambda s: s.model_copy(update={"extractor": "another-extractor"}),
    "limitation": lambda s: s.model_copy(update={"limitation": "a limitation"}),
    "name": lambda s: s.model_copy(update={"name": "another name"}),
    "media_type": lambda s: s.model_copy(update={"media_type": "application/pdf"}),
    "sha256": lambda s: s.model_copy(update={"sha256": "2" * 64}),
    "status": lambda s: s.model_copy(update={"status": "unreadable"}),
}


@pytest.mark.parametrize("field", list(PACK_FIELDS))
def test_every_source_field_counts_in_the_pack_comparison(field: str, earlier_run: Path) -> None:
    earlier = load_pack(earlier_run / "pack")
    renamed = earlier.model_copy(update={"run": earlier.run.model_copy(update={"run_id": "other"})})
    replay.check_same_pack(earlier, renamed)  # the run id alone is masked
    edited = PACK_FIELDS[field](earlier.sources[0])
    assert edited != earlier.sources[0]
    changed = earlier.model_copy(update={"sources": (edited, *earlier.sources[1:])})
    with pytest.raises(ReplayPackChanged):
        replay.check_same_pack(earlier, changed)
