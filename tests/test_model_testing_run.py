"""Run driver (Task 11). Offline: no network, no key, no environment read.

The cases are built under ``tmp_path`` (CI has no corpus): one tiny HTML source per case, a golden
whose single fact the checker accepts, the real ``context.json`` of each public golden, and a
mapping written here. Runs come from the real ``run_pathway`` over a ``recorded_adapter`` whose
recordings directory is empty, so each stops at its first model call (``RecordingMissing``) and
is still scored. Where a test needs a *settled* run, ``run_pathway`` is replaced by a double that
writes a test-authored ``run.json``; those tests are about the driver's decisions, not the walk.
Receipt-bearing run directories come from the Task 8 G1 owner run (``test_model_testing_pathway``).
"""

from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import http.client
import json
import runpy
import shutil
import socket
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import pytest
import test_model_testing_budget as budget_tests
import test_model_testing_pathway as pathway_tests

from deploy_vii.contracts import PATHWAY_MODULES, PathwayId
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import LivePauseInForce
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing import pathway as pathway_module
from deploy_workflow.model_testing import run as run_module
from deploy_workflow.model_testing.cases import GoldenCase
from deploy_workflow.model_testing.configs import CASES, CONFIGS, OPUS_PATHWAYS, PILOT_PATHWAY
from deploy_workflow.model_testing.mapping import Mapping
from deploy_workflow.model_testing.records import RunMeta
from deploy_workflow.model_testing.run import (
    CaseInputs,
    DriverError,
    Settings,
    distressed_opus_estimate,
    load_inputs,
    load_runs,
    main,
    needed_usd,
    plan_runs,
    run_stage,
)
from deploy_workflow.run_inputs import RunOutcome

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = ROOT / "cases" / "goldens"
SOURCE_ID = "FIX_2025-06-30_10-Q_fixture"
PAGE = b"<html><body><table><tr><td>Revenue</td><td>1,234</td></tr></table></body></html>"
FACT_ID = "CP-1.revenue.total"
PILOT_CASE = CASES[PILOT_PATHWAY]
TDG = CASES["credit_snapshot"]

# the Task 8 G1 owner run (CP-0 repaired, CP-1 refused, nothing else ran) built by its own fixture
gap_run = pathway_tests.gap_run


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


# ------------------------------------------------------------------ case tree


def _golden(case_id: str, pathway: str, gold: Path, source: Path) -> dict[str, Any]:
    return {
        "schema_version": "module-golden/1",
        "case_id": case_id,
        "issuer_id": "fix",
        "pathway": pathway,
        "cutoff": "2025-08-08",
        "context_file": "context.json",
        "financial_gold": {
            "path": str(gold),
            "sha256": hashlib.sha256(gold.read_bytes()).hexdigest(),
        },
        "sources": [
            {
                "source_id": SOURCE_ID,
                "file": f"FIX/{source.name}",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "url": "https://example.invalid/fixture",
                "form": "10-Q",
                "period_end": "2025-06-30",
                "filed": "2025-08-08",
            }
        ],
        "facts": [
            {
                "fact_id": FACT_ID,
                "module": "CP-1",
                "topic": "revenue",
                "subject": "total",
                "field": "total",
                "period_end": None,
                "status": "missing",
                "value": None,
                "value_type": "decimal",
                "unit": None,
                "scale": None,
                "evidence": [],
                "derivation": None,
                "gap_reason": "not in the fixture",
            }
        ],
        "not_golden": [],
        "needs_user_input": [],
        "limitations": [],
        "preparer": "test",
    }


def _mapping(case_id: str) -> dict[str, Any]:
    return {
        "schema_version": "golden-mapping/1",
        "case_id": case_id,
        "preparer": "alice",
        "reviewer": "bob",
        "module_commits": {"CP-1": "a" * 40},
        "entries": [
            {
                "fact_id": FACT_ID,
                "module": "CP-1",
                "locator": {
                    "table_id": "T1",
                    "row_id": "revenue",
                    "field": "total",
                    "period": None,
                },
            }
        ],
        "unmapped": [],
    }


@dataclass(frozen=True)
class World:
    cases: Path
    corpus: Path
    recordings: Path
    out: Path

    @property
    def root(self) -> Path:
        """The runs root: the folder holding ``out`` and any sibling out folders."""
        return self.out.parent

    def settings(self, **changes: Any) -> Settings:
        base = Settings(
            self.out, self.cases, self.corpus, recordings=self.recordings, runs_root=self.root
        )
        return dataclasses.replace(base, **changes)

    def argv(self, command: str, *extra: str) -> list[str]:
        return [
            command,
            "--out",
            str(self.out),
            "--cases",
            str(self.cases),
            "--corpus",
            str(self.corpus),
            "--runs-root",
            str(self.root),
            *extra,
        ]


@pytest.fixture
def world(tmp_path: Path) -> World:
    corpus = tmp_path / "corpus"
    (corpus / "FIX").mkdir(parents=True)
    page = corpus / "FIX" / "fixture.htm"
    page.write_bytes(PAGE)
    gold = tmp_path / "financial_gold.json"
    gold.write_text(json.dumps({"periods": [], "facts": []}), encoding="utf-8")
    cases = tmp_path / "cases"
    for pathway, case_id in CASES.items():
        case_dir = cases / case_id
        case_dir.mkdir(parents=True)
        shutil.copyfile(GOLDENS / case_id / "context.json", case_dir / "context.json")
        golden = _golden(case_id, pathway, gold, page)
        (case_dir / "module_golden.json").write_text(json.dumps(golden), encoding="utf-8")
        (case_dir / "mapping.json").write_text(json.dumps(_mapping(case_id)), encoding="utf-8")
    recordings = tmp_path / "recordings"
    for config_id in CONFIGS:
        (recordings / config_id).mkdir(parents=True)  # empty: a run stops at its first call
    return World(cases, corpus, recordings, tmp_path / "out")


def _run_dirs(out: Path) -> list[str]:
    return sorted(p.name for p in out.iterdir() if p.is_dir()) if out.is_dir() else []


# ------------------------------------------------------------------ plan


def test_plan_counts() -> None:
    assert len(plan_runs("pilot")) == 4
    assert len(plan_runs("repair")) == 12
    assert len(plan_runs("comparison")) == 11


def test_plan_contents() -> None:
    assert plan_runs("pilot") == tuple((PILOT_CASE, PILOT_PATHWAY, config) for config in CONFIGS)
    repair = plan_runs("repair")
    assert {config for _, _, config in repair} == {"sol-medium", "deepseek-max"}
    for config in ("sol-medium", "deepseek-max"):
        assert [p for _, p, c in repair if c == config] == list(CASES)
    comparison = plan_runs("comparison")
    assert [p for _, p, c in comparison if c == "sol-high"] == list(CASES)
    assert [p for _, p, c in comparison if c == "opus-medium"] == list(OPUS_PATHWAYS)
    for case_id, pathway, _ in (*repair, *comparison):
        assert CASES[pathway] == case_id
    assert "distressed_restructuring" not in OPUS_PATHWAYS  # the sixth Opus run is conditional


# ------------------------------------------------------------------ inputs


def test_inputs_come_from_the_golden_and_the_corpus(world: World) -> None:
    found = load_inputs(PILOT_CASE, world.cases, world.corpus)
    assert found.case.context_path == world.cases / PILOT_CASE / "context.json"
    assert [(s.source_id, s.media_type) for s in found.sources] == [(SOURCE_ID, "text/html")]
    assert found.sources[0].path == (world.corpus / "FIX" / "fixture.htm").resolve()
    assert found.case.pathway == PILOT_PATHWAY


def test_a_source_that_differs_from_the_golden_is_refused_before_any_run(world: World) -> None:
    (world.corpus / "FIX" / "fixture.htm").write_bytes(PAGE + b"<!-- changed -->")
    with pytest.raises(DriverError, match=SOURCE_ID):
        run_stage("pilot", world.settings())
    assert not world.out.exists()
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2


def test_a_missing_source_is_refused(world: World) -> None:
    (world.corpus / "FIX" / "fixture.htm").unlink()
    with pytest.raises(DriverError, match=f"{SOURCE_ID}.*missing"):
        load_inputs(PILOT_CASE, world.cases, world.corpus)


# ------------------------------------------------------------------ arguments


def test_live_refused_without_ruling(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(DriverError, match="--ruling"):
        run_stage("pilot", dataclasses.replace(world.settings(recordings=None), live=True))
    assert main(world.argv("pilot", "--live")) == 2
    err = capsys.readouterr().err
    assert "--ruling" in err and "Traceback" not in err
    assert not world.out.exists()


def test_offline_needs_recordings(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(world.argv("pilot")) == 2
    assert "--recordings" in capsys.readouterr().err
    assert not world.out.exists()


def test_ruling_without_live_and_recordings_with_live_are_refused(world: World) -> None:
    with pytest.raises(DriverError, match="--live"):
        run_stage("pilot", world.settings(ruling=Path("r.md")))
    with pytest.raises(DriverError, match="--recordings"):
        run_stage("pilot", world.settings(live=True, ruling=Path("r.md")))


def test_ruling_outside_docs_rulings_is_refused_by_the_precheck(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text("lifts: live-provider-pause\n", encoding="utf-8")
    live = dataclasses.replace(world.settings(recordings=None), live=True)
    with pytest.raises(DriverError, match="docs/rulings"):
        run_stage("pilot", dataclasses.replace(live, ruling=elsewhere))
    with pytest.raises(DriverError, match="does not exist"):
        run_stage("pilot", dataclasses.replace(live, ruling=rulings / "absent.md"))
    assert not world.out.exists()


def test_live_ruling_reaches_live_adapter(
    world: World,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The ruling passes the driver's pre-check (a file under the rulings root) but lacks R2's
    lines: the refusal is O5's ``LivePauseInForce``, raised before any run directory exists."""
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)
    ruling = rulings / "2026-11-02-not-a-lift.md"
    ruling.write_text("A note that lifts nothing.\n", encoding="utf-8")
    live = dataclasses.replace(world.settings(recordings=None), live=True, ruling=ruling)
    with pytest.raises(LivePauseInForce):
        run_stage("pilot", live)
    assert not world.out.exists()
    argv = world.argv("pilot", "--live", "--ruling", str(ruling))
    assert main(argv) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "lifts:" in err and "Traceback" not in err
    assert not world.out.exists()


def test_bad_command_line_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bogus"]) == 2
    assert main([]) == 2
    capsys.readouterr()


def test_score_and_report_take_no_run_arguments(world: World) -> None:
    assert main(world.argv("score", "--recordings", str(world.recordings))) == 2
    assert main(world.argv("report", "--live")) == 2


# ------------------------------------------------------------------ the offline pilot


def test_offline_pilot_scores(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    names = [f"pilot-{config}-{PILOT_PATHWAY}-1" for config in CONFIGS]
    assert _run_dirs(world.out) == sorted(names)
    for name in names:
        body = json.loads((world.out / name / "run.json").read_text())
        assert (body["mode"], body["outcome"]) == ("offline", "stopped")
        assert body["case_id"] == PILOT_CASE
        assert body["stopped_reason"].startswith("RecordingMissing")
    scores = json.loads((world.out / "scores.json").read_text())["scores"]
    assert sorted(s["run_id"] for s in scores) == sorted(names)
    assert {s["config_id"] for s in scores} == set(CONFIGS)
    for score in scores:
        assert score["outcome"] == "stopped" and score["passed"] is False
        assert [m["module_id"] for m in score["modules"]] == list(PATHWAY_MODULES[PILOT_PATHWAY])
        assert {m["head_status"] for m in score["modules"]} == {"absent"}
    report = (world.out / "report.md").read_text()
    assert report.startswith("Offline runs are included")
    assert "# Model comparison report" in report and f"## {PILOT_PATHWAY}" in report
    assert "Stopped configurations" not in report
    assert capsys.readouterr().err == ""
    assert (world.out / "settlements.json").exists() is False  # the framework never writes it


def test_score_and_report_commands_rebuild_the_outputs(world: World) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    (world.out / "scores.json").unlink()
    (world.out / "report.md").unlink()
    assert main(world.argv("report")) == 2  # no scores yet
    assert main(world.argv("score")) == 0
    assert main(world.argv("report")) == 0
    assert (world.out / "scores.json").is_file() and (world.out / "report.md").is_file()


def test_driver_never_writes_run_json(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only ``run_pathway`` creates ``run.json``. With a double that makes the run directory but
    no ``run.json``, the driver does not supply one: the folder stays a crashed run."""
    made: list[Path] = []

    def hollow(**kwargs: Any) -> RunOutcome:
        run_dir: Path = kwargs["run_dir"]
        run_dir.mkdir()
        (run_dir / "sources").mkdir()  # what run_pathway stages first
        made.append(run_dir)
        return RunOutcome(kwargs["run_id"], run_dir, "stopped", "x", Decimal(0))

    monkeypatch.setattr(run_module, "run_pathway", hollow)
    with pytest.raises(DriverError, match="no run.json"):
        run_stage("pilot", world.settings())
    assert len(made) == 1 and not (made[0] / "run.json").exists()
    assert not list(world.out.rglob("run.json"))


def test_the_real_run_pathway_writes_run_json_and_scoring_leaves_it_alone(world: World) -> None:
    run_stage("pilot", world.settings())
    before = {p: p.read_bytes() for p in sorted(world.out.rglob("run.json"))}
    assert len(before) == 4  # written by the real run_pathway
    assert main(world.argv("score")) == 0
    assert {p: p.read_bytes() for p in sorted(world.out.rglob("run.json"))} == before


def test_a_crashed_run_folder_stops_the_command(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    (world.out / "crashed-run" / "sources").mkdir(parents=True)  # staged, never finished
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
    err = capsys.readouterr().err
    assert "crashed-run" in err and "run.json" in err
    assert _run_dirs(world.out) == ["crashed-run"]  # nothing new started


# ------------------------------------------------------------------ budget


def _prior_live(
    out: Path,
    config_id: str,
    records: Sequence[CallRecord],
    *,
    run_id: str = "prior-live",
    pathway: PathwayId = PILOT_PATHWAY,
    outcome: str = "settled",
) -> None:
    """A live run folder written by the test, as an earlier session would have left it."""
    meta = budget_tests.meta("live", config_id, run_id).model_copy(
        update={
            "case_id": CASES[pathway],
            "pathway": pathway,
            "outcome": outcome,
            "stopped_reason": None if outcome == "settled" else "x",
        }
    )
    folder = out / run_id
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(meta.model_dump_json(), encoding="utf-8")
    lines = [
        r.model_copy(
            update={"run_id": run_id, "case_id": CASES[pathway], "pathway": pathway}
        ).model_dump_json()
        for r in records
    ]
    (folder / "calls.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_budget_exhausted_skips_config(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """A live call of sol-medium whose charge is unknown stops sol-medium and only sol-medium;
    the report says so."""
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    result = run_stage("pilot", world.settings())
    assert [o.run_id for o in result.outcomes] == [
        f"pilot-{config}-{PILOT_PATHWAY}-1" for config in CONFIGS if config != "sol-medium"
    ]
    assert list(result.stopped) == ["sol-medium"]
    why = result.stopped["sol-medium"]
    assert "unknown charge" in why and "prior-live" in why
    assert f"pilot-sol-medium-{PILOT_PATHWAY}-1" not in _run_dirs(world.out)
    assert json.loads((world.out / "exhausted.json").read_text())["stopped"] == dict(result.stopped)
    assert main(world.argv("score")) == 0 and main(world.argv("report")) == 0
    report = (world.out / "report.md").read_text()
    assert "## Stopped configurations" in report and "- sol-medium: " in report
    capsys.readouterr()


def test_a_spent_account_stops_every_config_on_it(world: World) -> None:
    spent = budget_tests.call("sol-medium", "117.00", reserved="1")
    _prior_live(world.out, "sol-medium", [spent])
    result = run_stage("pilot", world.settings())
    assert set(result.stopped) == {"sol-medium", "sol-high"}  # both on the openai account
    assert [o.run_id for o in result.outcomes] == [
        f"pilot-{config}-{PILOT_PATHWAY}-1" for config in ("opus-medium", "deepseek-max")
    ]


def test_a_settlement_releases_the_stopped_config(world: World) -> None:
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    (world.out / "settlements.json").write_text(
        json.dumps(
            {
                "schema_version": "charge-settlement/1",
                "entries": [
                    {
                        "run_id": "prior-live",
                        "module_id": "CP-1",
                        "step_id": "step-1",
                        "attempt": 0,
                        "call_index": 0,
                        "settled_usd": "1.00",
                        "by": "eric",
                        "date": "2026-11-02",
                        "source": "provider invoice",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_stage("pilot", world.settings())
    assert not result.stopped and len(result.outcomes) == 4


def test_a_settlement_matching_nothing_stops_the_command(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    entry = {
        "run_id": "elsewhere",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "settled_usd": "1.00",
        "by": "eric",
        "date": "2026-11-02",
        "source": "provider invoice",
    }
    body = {"schema_version": "charge-settlement/1", "entries": [entry]}
    (world.out / "settlements.json").write_text(json.dumps(body), encoding="utf-8")
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
    assert "matches no record" in capsys.readouterr().err
    assert _run_dirs(world.out) == ["prior-live"]


def test_report_counts_settlements(world: World) -> None:
    # a different pathway from the pilot's, so the report holds one score per (pathway, config)
    unknown = budget_tests.call("deepseek-max", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "deepseek-max", [unknown], pathway="credit_snapshot")
    entry = {
        "run_id": "prior-live",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "settled_usd": "1.00",
        "by": "eric",
        "date": "2026-11-02",
        "source": "provider | invoice",
    }
    body = {"schema_version": "charge-settlement/1", "entries": [entry]}
    (world.out / "settlements.json").write_text(json.dumps(body), encoding="utf-8")
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    report = (world.out / "report.md").read_text()
    assert "## Settled charges" in report
    row = "| prior-live | CP-1 | step-1 | 0 | 0 | $1.00 | eric | 2026-11-02 | "
    assert row + "provider \\| invoice |" in report
    assert "| openrouter | $1.00 |" in report  # the reservation of 3.25 no longer counts


def _live_runs(
    config_id: str, costs: Sequence[str], pathways: Sequence[PathwayId] | None = None
) -> list[tuple[RunMeta, tuple[CallRecord, ...]]]:
    out: list[tuple[RunMeta, tuple[CallRecord, ...]]] = []
    for index, cost in enumerate(costs):
        run_id = f"r{index}"
        meta = budget_tests.meta("live", config_id, run_id)
        if pathways is not None:
            meta = meta.model_copy(update={"pathway": pathways[index]})
        out.append((meta, (budget_tests.call(config_id, cost, run_id=run_id),)))
    return out


def test_needed_is_the_spec_estimate_until_a_run_is_measured() -> None:
    assert needed_usd("sol-medium", []) == Decimal("5.64")
    assert needed_usd("sol-high", []) == Decimal("8.15")
    assert needed_usd("opus-medium", []) == Decimal("25.15")
    assert needed_usd("deepseek-max", []) == Decimal("1.67")
    # the highest measured spend of a settled live run of the configuration replaces it
    measured = _live_runs("sol-medium", ["3.00", "7.50"])
    assert needed_usd("sol-medium", measured) == Decimal("7.50")
    assert needed_usd("sol-high", measured) == Decimal("8.15")  # another configuration
    stopped = measured[1][0].model_copy(update={"outcome": "stopped", "stopped_reason": "x"})
    assert needed_usd("sol-medium", [measured[0], (stopped, measured[1][1])]) == Decimal("3.00")
    offline = (measured[0][0].model_copy(update={"mode": "offline"}), measured[0][1])
    assert needed_usd("sol-medium", [offline]) == Decimal("5.64")  # offline is not money


def test_distressed_on_opus_estimate_scales_with_the_measured_five() -> None:
    five: list[PathwayId] = list(OPUS_PATHWAYS)
    assert distressed_opus_estimate([]) is None
    partial = _live_runs("opus-medium", ["25.144"] * 4, five[:4])
    assert distressed_opus_estimate(partial) is None  # needs all five
    exact = _live_runs("opus-medium", ["25.144"] * 5, five)
    assert distressed_opus_estimate(exact) == Decimal("28.93")  # 154.65 - 125.72
    cheaper = _live_runs("opus-medium", ["12.572"] * 5, five)
    assert distressed_opus_estimate(cheaper) == Decimal("14.47")  # half, rounded up


def _settled_double(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Replace ``run_pathway`` with a double that writes a settled offline ``run.json``."""
    calls: list[tuple[str, str]] = []

    def settled(**kwargs: Any) -> RunOutcome:
        run_dir: Path = kwargs["run_dir"]
        run_dir.mkdir()
        meta = budget_tests.meta("offline", kwargs["model"].config_id, kwargs["run_id"])
        meta = meta.model_copy(update={"case_id": kwargs["case_id"], "pathway": kwargs["pathway"]})
        (run_dir / "run.json").write_text(meta.model_dump_json(), encoding="utf-8")
        calls.append((kwargs["pathway"], kwargs["model"].config_id))
        return RunOutcome(kwargs["run_id"], run_dir, "settled", None, Decimal(0))

    monkeypatch.setattr(run_module, "run_pathway", settled)
    return calls


def test_distressed_runs_on_opus_after_the_five_when_the_cap_allows(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _settled_double(monkeypatch)
    result = run_stage("comparison", world.settings())
    assert len(calls) == 12 and not result.stopped
    assert calls[-1] == ("distressed_restructuring", "opus-medium")
    assert [p for p, c in calls[6:11] if c == "opus-medium"] == list(OPUS_PATHWAYS)


def test_distressed_is_skipped_when_the_cap_is_short(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Five earlier live Opus runs cost 110 of the 135 usable: the sixth is estimated at 25.32
    (28.93 scaled by 110 / 125.72, rounded up), and 25 remains."""
    for index, pathway in enumerate(OPUS_PATHWAYS):
        record = budget_tests.call("opus-medium", "22.00", run_id=f"earlier-{index}")
        _prior_live(world.out, "opus-medium", [record], run_id=f"earlier-{index}", pathway=pathway)
    calls = _settled_double(monkeypatch)
    result = run_stage("comparison", world.settings())
    key = "opus-medium (distressed_restructuring)"
    assert list(result.stopped) == [key]
    assert "anthropic" in result.stopped[key]
    assert ("distressed_restructuring", "opus-medium") not in calls
    assert len(calls) == 11


# ------------------------------------------------------------------ refusals reach the scorer


def _tdg_case() -> tuple[GoldenCase, Mapping]:
    case, mapping = pathway_tests._gap_case()
    return dataclasses.replace(case, case_id=TDG), mapping.model_copy(update={"case_id": TDG})


@pytest.fixture
def gap_out(gap_run: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An ``--out`` holding a copy of the G1 owner run, relabelled as the credit_snapshot golden's
    case, with scoring pointed at the Task 8 gap case instead of the corpus."""
    out = tmp_path / "gap-out"
    folder = out / "slice-cp1-model-gap"
    shutil.copytree(gap_run, folder)
    body = json.loads((folder / "run.json").read_text())
    body["case_id"] = TDG
    (folder / "run.json").write_text(json.dumps(body))
    case, mapping = _tdg_case()

    def fixed(case_id: str, cases: Path, corpus: Path) -> CaseInputs:
        assert case_id == TDG
        return CaseInputs(case, mapping, ())

    monkeypatch.setattr(run_module, "load_inputs", fixed)
    return out


def _name_refusals(folder: Path, modules: Sequence[str]) -> None:
    """Rewrite the receipt's refusal records so each listed module names CP-0 as its missing
    input: the O3 ``RefusedBegin.missing_inputs`` field the driver reads."""
    path = folder / "owner-run.json"
    body = json.loads(path.read_text())
    template = next(r for r in body["refusals"] if r["module_id"] == "CP-1")
    body["refusals"] = [{**template, "module_id": m, "missing_inputs": ["CP-0"]} for m in modules]
    path.write_text(json.dumps(body))


def _scores(out: Path) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = json.loads((out / "scores.json").read_text())["scores"]
    return scores


def _score(gap_out: Path) -> None:
    settings = Settings(gap_out, Path("unused"), Path("unused"), runs_root=gap_out)
    assert run_module.score_out(settings) == gap_out / "scores.json"


def test_refusal_names_reach_scorer(gap_out: Path) -> None:
    folder = gap_out / "slice-cp1-model-gap"
    _name_refusals(folder, ["CP-1"])
    assert pathway_module.receipt_refusals(folder) == {"CP-1": ("CP-0",)}
    _score(gap_out)
    cp1 = _scores(gap_out)[0]["modules"][1]
    assert (cp1["module_id"], cp1["head_status"]) == ("CP-1", "refused")
    assert [(f["fact_id"], f["outcome"]) for f in cp1["facts"]] == [
        (pathway_tests.CP1_FACT, "gap_ok")
    ]
    assert cp1["facts"][0]["observed"] == "refused: CP-0"
    assert cp1["passed"] is True


def test_a_refusal_naming_nothing_is_not_excused(gap_out: Path) -> None:
    folder = gap_out / "slice-cp1-model-gap"
    body = json.loads((folder / "owner-run.json").read_text())
    for refusal in body["refusals"]:
        refusal.pop("missing_inputs", None)
    (folder / "owner-run.json").write_text(json.dumps(body))
    assert pathway_module.receipt_refusals(folder) == {}
    _score(gap_out)
    cp1 = _scores(gap_out)[0]["modules"][1]
    assert cp1["head_status"] == "refused" and cp1["passed"] is False


def test_a_receipt_naming_a_module_outside_the_preset_is_refused(gap_out: Path) -> None:
    folder = gap_out / "slice-cp1-model-gap"
    path = folder / "owner-run.json"
    body = json.loads(path.read_text())
    next(r for r in body["refusals"] if r["module_id"] == "CP-1")["missing_inputs"] = ["CP-8"]
    path.write_text(json.dumps(body))
    with pytest.raises(DriverError, match="CP-8"):
        _score(gap_out)


def test_the_real_module_scorer_passes_a_run(
    gap_out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling 8: ``score_run`` returns ``passed=True`` from the real module scorer. No fast
    fixture settles a whole pathway (the O2 and G1 walks end before it, and the render walk is
    RUN_PROMOTION-gated), so every module the run never reached is given an honest O3 refusal
    naming its missing input in the test-written receipt. That edit invalidates the receipt's
    seal, so the render check alone is replaced here; it has its own tests in
    ``test_model_testing_pathway`` (tamper, missing delivery) and the real scorer runs unforced."""
    folder = gap_out / "slice-cp1-model-gap"
    _name_refusals(folder, [m for m in PATHWAY_MODULES["credit_snapshot"] if m != "CP-0"])
    monkeypatch.setattr(pathway_module, "_rendered", lambda run_dir, receipt: (True, None))
    _score(gap_out)
    score = _scores(gap_out)[0]
    assert [m["head_status"] for m in score["modules"]] == ["restricted", *8 * ["refused"]]
    assert all(m["passed"] is True for m in score["modules"])
    assert score["outcome"] == "settled" and score["rendered"] is True
    assert score["passed"] is True


def test_score_refuses_a_case_that_is_not_a_golden(gap_out: Path) -> None:
    folder = gap_out / "slice-cp1-model-gap"
    body = json.loads((folder / "run.json").read_text())
    body["case_id"] = "some-other-case"
    (folder / "run.json").write_text(json.dumps(body))
    with pytest.raises(DriverError, match="some-other-case"):
        _score(gap_out)


# ------------------------------------------------------------------ the entry point


def test_module_entry_point_exits_with_the_return_code_of_main(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["model_testing", *world.argv("score")])
    with pytest.raises(SystemExit) as refused:
        runpy.run_module("deploy_workflow.model_testing", run_name="__main__")
    assert refused.value.code == 2  # no run folders under --out: refused
    assert "no run folders" in capsys.readouterr().err


# ------------------------------------------------------------------ runs root (review round 1)


def _sibling(world: World) -> Path:
    return world.root / "earlier-out"


def test_spend_in_a_sibling_out_counts(world: World) -> None:
    """The account caps are global: an unknown charge or spent credit in another out folder under
    the same runs root stops the configuration here too."""
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(_sibling(world), "sol-medium", [unknown])
    spent = budget_tests.call("sol-high", "117.00", run_id="spent")
    _prior_live(_sibling(world), "sol-high", [spent], run_id="spent")
    result = run_stage("pilot", world.settings())
    assert set(result.stopped) == {"sol-medium", "sol-high"}
    assert [o.run_id for o in result.outcomes] == [
        f"pilot-{config}-{PILOT_PATHWAY}-1" for config in ("opus-medium", "deepseek-max")
    ]


def test_a_crashed_run_in_a_sibling_out_stops_the_command(world: World) -> None:
    (_sibling(world) / "crashed" / "sources").mkdir(parents=True)
    with pytest.raises(DriverError, match="crashed.*no run.json"):
        run_stage("pilot", world.settings())
    assert not world.out.exists()


def test_a_folder_without_sources_or_run_json_is_not_a_run(world: World) -> None:
    (_sibling(world) / "notes").mkdir(parents=True)
    assert len(run_stage("pilot", world.settings()).outcomes) == 4


def test_out_outside_the_runs_root_is_refused(
    world: World, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "elsewhere-root"
    root.mkdir()
    argv = world.argv("pilot", "--recordings", str(world.recordings))
    argv[argv.index("--runs-root") + 1] = str(root)
    assert main(argv) == 2
    err = capsys.readouterr().err
    assert "--runs-root" in err and "not counted" in err
    assert not world.out.exists()
    with pytest.raises(DriverError, match="--runs-root"):
        run_stage("pilot", world.settings(runs_root=root))


def test_a_stage_rerun_into_the_same_out_gets_new_run_ids(world: World) -> None:
    pilot = ["pilot", *("--recordings", str(world.recordings))]
    assert main(world.argv(*pilot)) == 0
    assert main(world.argv(*pilot)) == 0
    first = [f"pilot-{config}-{PILOT_PATHWAY}-1" for config in CONFIGS]
    second = [f"pilot-{config}-{PILOT_PATHWAY}-2" for config in CONFIGS]
    assert _run_dirs(world.out) == sorted(first + second)
    scores = json.loads((world.out / "scores.json").read_text())["scores"]
    assert len(scores) == 8
    report = (world.out / "report.md").read_text()  # one column per config: the latest run
    assert "# Model comparison report" in report


def test_run_numbers_are_free_across_every_run_directory(world: World) -> None:
    other = _sibling(world) / f"pilot-sol-medium-{PILOT_PATHWAY}-7"
    other.mkdir(parents=True)
    (other / "sources").mkdir()  # a run elsewhere under the root, number 7
    with pytest.raises(DriverError, match="pilot-sol-medium-earnings_update-7"):
        run_stage("pilot", world.settings())  # that folder is a crashed run
    shutil.rmtree(other)
    _prior_live(
        _sibling(world),
        "sol-medium",
        [budget_tests.call("sol-medium", "1.00")],
        run_id=f"pilot-sol-medium-{PILOT_PATHWAY}-7",
    )
    result = run_stage("pilot", world.settings())
    assert f"pilot-sol-medium-{PILOT_PATHWAY}-8" in [o.run_id for o in result.outcomes]


def test_stops_are_not_kept_after_a_settlement(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    assert set(run_stage("pilot", world.settings()).stopped) == {"sol-medium"}
    assert (world.out / "exhausted.json").is_file()
    entry = {
        "run_id": "prior-live",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "settled_usd": "1.00",
        "by": "eric",
        "date": "2026-11-02",
        "source": "provider invoice",
    }
    body = {"schema_version": "charge-settlement/1", "entries": [entry]}
    (world.out / "settlements.json").write_text(json.dumps(body), encoding="utf-8")
    assert main(world.argv("score")) == 0 and main(world.argv("report")) == 0
    assert "Stopped configurations" not in (world.out / "report.md").read_text()
    # a later stage that stops nothing rewrites the record
    _settled_double(monkeypatch)
    assert run_stage("repair", world.settings()).stopped == {}
    assert not (world.out / "exhausted.json").exists()


def test_a_skipped_distressed_run_is_recorded_for_any_cause(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    unknown = budget_tests.call("opus-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "opus-medium", [unknown], pathway="credit_snapshot")
    calls = _settled_double(monkeypatch)
    result = run_stage("comparison", world.settings())
    key = "opus-medium (distressed_restructuring)"
    assert "unknown charge" in result.stopped["opus-medium"]
    assert key in result.stopped and result.stopped[key].startswith("skipped")
    assert ("distressed_restructuring", "opus-medium") not in calls


def test_main_lets_a_defect_propagate(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(stage: str, settings: Settings) -> None:
        raise RuntimeError("a defect")

    monkeypatch.setattr(run_module, "run_stage", broken)
    with pytest.raises(RuntimeError, match="a defect"):
        main(world.argv("pilot", "--recordings", str(world.recordings)))

    def bare(stage: str, settings: Settings) -> None:
        raise ValueError("not a named refusal")

    monkeypatch.setattr(run_module, "run_stage", bare)
    with pytest.raises(ValueError, match="not a named refusal"):
        main(world.argv("pilot", "--recordings", str(world.recordings)))


def test_a_settlement_amount_beyond_the_exact_context_exits_2(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    entry = {
        "run_id": "prior-live",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "settled_usd": "1E-1000000",
        "by": "eric",
        "date": "2026-11-02",
        "source": "provider invoice",
    }
    body = {"schema_version": "charge-settlement/1", "entries": [entry]}
    (world.out / "settlements.json").write_text(json.dumps(body), encoding="utf-8")
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
    assert "held exactly" in capsys.readouterr().err


def test_key_shaped_settlement_text_never_reaches_the_report(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = "sk-proj-" + "Q" * 24  # fabricated, not a key
    unknown = budget_tests.call("sol-medium", None, reserved="3.25", status="unknown")
    _prior_live(world.out, "sol-medium", [unknown])
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    entry = {
        "run_id": "prior-live",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "settled_usd": "2.00",
        "by": "eric",
        "date": "2026-11-02",
        "source": f"billing page, key {fake}",
    }
    body = {"schema_version": "charge-settlement/1", "entries": [entry]}
    (world.out / "settlements.json").write_text(json.dumps(body), encoding="utf-8")
    capsys.readouterr()
    assert main(world.argv("report")) == 2
    assert fake not in capsys.readouterr().err
    assert fake not in (world.out / "report.md").read_text()


# ------------------------------------------------------------------ review round 2


def test_a_stage_command_holds_the_runs_root_lock_until_its_last_run(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A second stage command under the same root fails at once, while the first is mid-run."""
    refused: list[bool] = []
    real = _settled_double(monkeypatch)
    inner: Callable[..., RunOutcome] = vars(run_module)["run_pathway"]

    def nested(**kwargs: Any) -> RunOutcome:
        other = world.root / "other-out"
        with pytest.raises(DriverError, match="another stage command"):
            run_stage("pilot", world.settings(out=other))
        assert main(world.argv("pilot", "--recordings", str(world.recordings))) in (0, 2)
        refused.append(not other.exists())
        return inner(**kwargs)

    monkeypatch.setattr(run_module, "run_pathway", nested)
    run_stage("pilot", world.settings())
    assert refused and all(refused) and len(real) == 4
    capsys.readouterr()


def test_the_lock_is_released_when_the_command_ends_and_score_report_take_none(
    world: World,
) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    lock = world.root / ".driver.lock"
    assert lock.is_file()
    with lock.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)  # another command is running
        with pytest.raises(DriverError, match="another stage command"):
            run_stage("pilot", world.settings(out=world.root / "second"))
        assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
        assert main(world.argv("score")) == 0 and main(world.argv("report")) == 0
    out2 = world.root / "second"
    assert len(run_stage("pilot", world.settings(out=out2)).outcomes) == 4  # lock was free again


def test_a_symlinked_run_directory_is_refused(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    elsewhere = world.root.parent / "external-runs"
    unknown = budget_tests.call("sol-high", None, reserved="40", status="unknown")
    _prior_live(elsewhere, "sol-high", [unknown], run_id="linked-run")
    world.root.mkdir(exist_ok=True)
    (world.root / "linked-run").symlink_to(elsewhere / "linked-run", target_is_directory=True)
    with pytest.raises(DriverError, match="linked-run.*symbolic link"):
        run_stage("pilot", world.settings())
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
    assert "linked-run" in capsys.readouterr().err
    assert not world.out.exists()


def test_live_needs_an_explicit_absolute_runs_root(
    world: World, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruling = tmp_path / "r.md"
    ruling.write_text("x\n", encoding="utf-8")
    relative = dataclasses.replace(
        world.settings(recordings=None),
        live=True,
        ruling=ruling,
        runs_root=run_module.DEFAULT_RUNS_ROOT,
    )
    with pytest.raises(DriverError, match="absolute --runs-root"):
        run_stage("pilot", relative)
    argv = ["pilot", "--out", str(world.out), "--cases", str(world.cases)]
    argv += ["--corpus", str(world.corpus), "--live", "--ruling", str(ruling)]
    assert main(argv) == 2  # no --runs-root: the relative default
    err = capsys.readouterr().err
    assert "--runs-root" in err and "worktree" in err
    # offline commands may keep the relative default
    offline = world.settings(runs_root=run_module.DEFAULT_RUNS_ROOT)
    run_module.check_settings(dataclasses.replace(offline, out=run_module.DEFAULT_RUNS_ROOT / "x"))


def test_the_report_states_the_resolved_runs_root(world: World) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    assert f"Runs root: {world.root.resolve()}" in (world.out / "report.md").read_text()


def test_score_out_lets_a_defect_in_the_scorer_propagate(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0

    def defect(*args: Any, **kwargs: Any) -> None:
        raise ValueError("a defect")

    monkeypatch.setattr(run_module, "score_run", defect)
    with pytest.raises(ValueError, match="a defect") as caught:
        run_module.score_out(world.settings())
    assert type(caught.value) is ValueError  # not turned into a named refusal
    monkeypatch.undo()
    monkeypatch.setattr(run_module, "render_report", defect)
    with pytest.raises(ValueError, match="a defect") as again:
        run_module.report_out(world.settings())
    assert type(again.value) is ValueError


def test_scores_that_no_longer_match_the_runs_are_a_named_refusal(world: World) -> None:
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 0
    shutil.rmtree(world.out / f"pilot-sol-high-{PILOT_PATHWAY}-1")
    with pytest.raises(DriverError, match="pilot-sol-high.*score command"):
        run_module.report_out(world.settings())


def test_a_dangling_symlinked_run_directory_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "pilot-x").symlink_to(tmp_path / "unmounted" / "pilot", target_is_directory=True)
    with pytest.raises(DriverError, match="symbolic link"):
        load_runs(root)


def test_an_unopenable_lock_file_is_a_driver_error_exit_2(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    (world.root / ".driver.lock").mkdir(parents=True)  # open("a") on a directory fails
    assert main(world.argv("pilot", "--recordings", str(world.recordings))) == 2
    err = capsys.readouterr().err
    assert ".driver.lock" in err and "Traceback" not in err
