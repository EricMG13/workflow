"""run_pathway: the stopped-run file set, run.json and its ordering (O2 Task 3). Offline; no network.

No test reads a key or the environment. Faults are produced by the real loop over a real pack and a
real recorded adapter with no recordings (``RecordingMissing``) or by patching one named seam.
"""

import hashlib
import http.client
import importlib
import json
import os
import socket
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import pytest

from deploy_vii.live.prompts import PromptError
from deploy_workflow import run_inputs as run_inputs_module
from deploy_workflow import run_pathway as rp
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import (
    LiveAdapter,
    RecordedAdapter,
    RecordingError,
    recorded_adapter,
)
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.loop import PromptFor, ToolLoop
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.run_inputs import (
    BadCap,
    CaseSource,
    RunDirExists,
    check_arguments,
    stage_sources,
)
from deploy_workflow.run_pathway import run_pathway

fw: Any = importlib.import_module("tests.test_financial_workflow")

ROOT = Path(__file__).resolve().parents[1]
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
HTML = b"<html><body><table><tr><td>Revenue</td><td>1,234</td></tr></table></body></html>"
SECRET = "sk-or-v1-TESTONLY123456"
RULING = "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: sol-medium\n"
TINY = Decimal("0.0000001")
OFFLINE_KEYS = {
    "case_id",
    "pathway",
    "config_id",
    "run_id",
    "mode",
    "cap_usd",
    "sources",
    "cp_dr_invoked",
    "replayed_from_run",
    "outcome",
    "stopped_reason",
}
STOPPED_SET = {"sources", "pack", "execution", "calls.jsonl", "run.json"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


@pytest.fixture
def args(tmp_path: Path) -> dict[str, Any]:
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.html").write_bytes(HTML)
    (src / "b.txt").write_bytes(b"plain text\n")
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    return {
        "case_id": "case-1",
        "sources": [
            CaseSource("s1", src / "a.html", "text/html"),
            CaseSource("s2", src / "b.txt", "text/plain"),
        ],
        "context": ROOT / "cases/context/research-minimal.json",
        "pathway": "credit_snapshot",
        "model": MODEL,
        "adapter": recorded_adapter(MODEL, recordings),
        "cap_usd": Decimal(1),
        "run_dir": tmp_path / "run",
        "run_id": "run-1",
    }


def files_under(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def assert_clean(root: Path, text: str) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            assert text.encode() not in path.read_bytes(), path


def run_json(run_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((run_dir / "run.json").read_text())
    return loaded


# ---------------------------------------------------------------- refusals


def test_a_refusal_through_run_pathway_leaves_no_directory(args: dict[str, Any]) -> None:
    with pytest.raises(BadCap):
        run_pathway(**{**args, "cap_usd": Decimal(0)})
    assert not os.path.lexists(args["run_dir"])


def test_the_second_call_on_one_run_dir_is_refused_and_changes_nothing(
    args: dict[str, Any],
) -> None:
    first = run_pathway(**args)
    assert first.outcome == "stopped"
    before = files_under(args["run_dir"])
    with pytest.raises(RunDirExists):
        run_pathway(**args)
    assert files_under(args["run_dir"]) == before


# ---------------------------------------------------------------- stopped runs


def test_a_missing_recording_stops_the_run_with_the_stopped_file_set(args: dict[str, Any]) -> None:
    outcome = run_pathway(**args)
    run_dir = args["run_dir"]
    assert outcome.outcome == "stopped" and outcome.run_id == "run-1"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("RecordingMissing: no recording for digest ")
    assert {p.name for p in run_dir.iterdir()} == STOPPED_SET
    records = [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]
    assert len(records) == 1
    # O5 records an exception out of complete as the fixed class AdapterError with an unknown
    # charge held (the exception type is in the error text), not as a computed zero.
    assert records[0]["error_class"] == "AdapterError"
    assert "RecordingMissing" in records[0]["error"]
    assert records[0]["cost_status"] == "unknown" and records[0]["settled_usd"] is None
    body = run_json(run_dir)
    assert body["outcome"] == "stopped" and body["stopped_reason"] == outcome.stopped_reason
    assert outcome.spent_usd == Decimal(records[0]["reserved_usd"])  # the held unknown counts
    assert outcome.spent_usd > 0


def test_a_step_with_no_composer_stops_as_no_prompt(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rp, "STEP_CONTRACTS", {})
    outcome = run_pathway(**args)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "NoPrompt: source_readiness"
    assert outcome.spent_usd == Decimal(0)
    assert not (args["run_dir"] / "calls.jsonl").exists()  # nothing was sent or reserved
    assert run_json(args["run_dir"])["stopped_reason"] == "NoPrompt: source_readiness"


def test_the_default_composer_is_the_contract_composer_for_a_contract_step(
    args: dict[str, Any],
) -> None:
    seen: list[str] = []

    def factory(pack: Any) -> PromptFor:
        inner = rp._default_prompt_for(pack)

        def prompt_for(binding: Any, spec: Any, issues: tuple[str, ...]) -> Any:
            seen.append(binding.step_id)
            return inner(binding, spec, issues)

        return prompt_for

    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    outcome = rp._run_pathway(checked, args["run_dir"], args["adapter"], factory)
    assert seen == ["source_readiness"]
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("RecordingMissing")  # NoPrompt was not hit


def test_a_prompt_error_stops_the_run_and_sends_nothing(args: dict[str, Any]) -> None:
    def factory(pack: Any) -> PromptFor:
        def prompt_for(binding: Any, spec: Any, issues: tuple[str, ...]) -> Any:
            raise PromptError(f"cannot build {binding.step_id}")

        return prompt_for

    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    outcome = rp._run_pathway(checked, args["run_dir"], args["adapter"], factory)
    assert outcome.stopped_reason == "PromptError: cannot build source_readiness"
    assert not (args["run_dir"] / "calls.jsonl").exists()


def test_a_cap_below_the_first_reservation_sends_nothing(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(*a: object, **k: object) -> NoReturn:
        raise AssertionError("the adapter was called")

    monkeypatch.setattr(RecordedAdapter, "complete", never)
    outcome = run_pathway(**{**args, "cap_usd": TINY})
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("BudgetExhausted")
    assert outcome.spent_usd == Decimal(0)
    records = [
        json.loads(line) for line in (args["run_dir"] / "calls.jsonl").read_text().splitlines()
    ]
    assert [r["error_class"] for r in records] == ["BudgetExhausted"]
    assert run_json(args["run_dir"])["cap_usd"] == "0.0000001"


def test_a_live_run_records_the_ruling_the_adapter_passed(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    ruling = rulings / "lift.md"
    ruling.write_text(RULING)
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)

    def transport(request: object) -> NoReturn:
        raise AssertionError("the transport was called")

    live = adapter_module.live_adapter(MODEL, ruling, transport=transport, environ={})
    assert type(live) is LiveAdapter
    outcome = run_pathway(**{**args, "adapter": live, "cap_usd": TINY})
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("BudgetExhausted")
    body = run_json(args["run_dir"])
    assert body["mode"] == "live"
    assert body["ruling_path"] == str(live.gate.path)
    assert body["ruling_sha256"] == live.gate.sha256
    assert body["ruling_date"] == live.gate.date.isoformat()


def test_the_offline_run_json_key_set_and_sources(args: dict[str, Any]) -> None:
    run_pathway(**args)
    body = run_json(args["run_dir"])
    assert set(body) == OFFLINE_KEYS
    assert body["mode"] == "offline" and body["cp_dr_invoked"] is False
    assert body["replayed_from_run"] is None and body["cap_usd"] == "1"
    assert body["config_id"] == "sol-medium" and body["pathway"] == "credit_snapshot"
    html, text, context = body["sources"]
    assert html["sha256"] == hashlib.sha256(HTML).hexdigest()  # the original bytes
    assert html["media_type"] == "text/html" and html["converted_sha256"] is not None
    assert html["path"] == str(args["sources"][0].path)
    assert text["sha256"] == hashlib.sha256(b"plain text\n").hexdigest()
    assert text["converted_sha256"] is None
    assert context["source_id"] == "context" and context["media_type"] == "text/plain"
    assert context["converted_sha256"] is None


def test_a_changed_html_source_is_a_fault_before_anything_is_written(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    real = run_inputs_module.read_capped

    def changed(path: Path) -> bytes:
        return real(path).replace(b"1,234", b"9,999")

    monkeypatch.setattr(rp, "read_capped", changed)
    with pytest.raises(run_inputs_module.StagedSourceChanged):
        run_pathway(**args)
    assert not os.path.lexists(args["run_dir"])


# ---------------------------------------------------------------- redaction


def test_a_key_in_a_prepare_error_reaches_no_file(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*a: object, **k: object) -> NoReturn:
        raise ValueError(f"cannot prepare with {SECRET}")

    monkeypatch.setattr(run_inputs_module, "prepare", broken)
    outcome = run_pathway(**args)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "prepare: cannot prepare with [redacted]"
    assert SECRET not in repr(outcome)
    assert_clean(args["run_dir"], SECRET)


def test_a_key_in_a_recording_error_reaches_no_file(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*a: object, **k: object) -> NoReturn:
        raise RecordingError(f"bad recording {SECRET}")

    monkeypatch.setattr(RecordedAdapter, "complete", broken)
    outcome = run_pathway(**args)
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("RecordingError: bad recording [redacted]")
    assert SECRET not in repr(outcome)
    assert_clean(args["run_dir"], SECRET)


def test_a_key_written_to_stderr_inside_the_loop_is_redacted(
    args: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    def factory(pack: Any) -> PromptFor:
        inner = rp._default_prompt_for(pack)

        def prompt_for(binding: Any, spec: Any, issues: tuple[str, ...]) -> Any:
            print(f"debug {SECRET}", file=sys.stderr)
            return inner(binding, spec, issues)

        return prompt_for

    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    rp._run_pathway(checked, args["run_dir"], args["adapter"], factory)
    err = capsys.readouterr().err
    assert SECRET not in err and "debug [redacted]" in err


# ---------------------------------------------------------------- crashes


def test_an_unexpected_exception_propagates_and_leaves_no_run_json(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*a: object, **k: object) -> NoReturn:
        raise RuntimeError("a programming error")

    monkeypatch.setattr(run_inputs_module, "prepare", crash)
    with pytest.raises(RuntimeError, match="programming error"):
        run_pathway(**args)
    assert args["run_dir"].exists() and not (args["run_dir"] / "run.json").exists()


def test_an_unexpected_exception_in_the_walk_propagates(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*a: object, **k: object) -> NoReturn:
        raise KeyError("a programming error")

    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    monkeypatch.setattr(ToolLoop, "run", crash)
    with pytest.raises(KeyError):
        rp._run_pathway(checked, args["run_dir"], args["adapter"])
    assert not (args["run_dir"] / "run.json").exists()


# ---------------------------------------------------------------- _finish_run


@pytest.fixture
def finished(args: dict[str, Any]) -> tuple[Any, OwnerWorkflow, Budget, Path]:
    """A one-module walk (the gap pack: CP-0, then a refused publication): ``Run.requested_modules``
    defaults to the full preset, so no one-module walk exists through ``run_pathway``."""
    checked = check_arguments(**args)
    run_dir: Path = args["run_dir"]
    run_dir.mkdir()
    pack = fw.make_pack(True)
    workflow = OwnerWorkflow.create(
        run_dir / "execution", pack, publication_directory=run_dir / "publication"
    )
    fw.read_sources(workflow, gap=True)
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert workflow.publish()["status"] == "refused"
    meta = rp._Meta(checked, rp._staged_entries(checked, run_dir), False, Redactor())
    return meta, workflow, Budget(Decimal(1), run_dir / "execution"), run_dir


def test_finish_run_writes_the_receipt_the_delivery_and_run_json_last(
    finished: tuple[Any, OwnerWorkflow, Budget, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    meta, workflow, budget, run_dir = finished
    replaced: list[set[str]] = []
    real_replace = os.replace

    def spy(src: Any, dst: Any) -> None:
        replaced.append({str(p.relative_to(run_dir)) for p in run_dir.rglob("*")})
        real_replace(src, dst)

    monkeypatch.setattr("deploy_workflow.run_pathway.os.replace", spy)
    outcome = rp._finish_run(workflow, run_dir, meta, budget)
    assert outcome.outcome == "settled" and outcome.stopped_reason is None
    assert (run_dir / "owner-run.json").is_file()
    assert (run_dir / "delivery" / "report.html").is_file()
    assert len(replaced) == 1  # run.json is the only file moved into place by this module
    before = replaced[0]
    assert {"owner-run.json", "delivery/report.html", "run.json.tmp"} <= before
    assert "run.json" not in before  # nothing but the temp file existed when run.json landed
    assert not (run_dir / "run.json.tmp").exists()
    stamps = {p: p.stat().st_mtime_ns for p in run_dir.rglob("*") if p.is_file()}
    assert stamps[run_dir / "run.json"] == max(stamps.values())
    body = run_json(run_dir)
    assert set(body) == OFFLINE_KEYS
    assert body["outcome"] == "settled" and body["stopped_reason"] is None


def test_a_blocked_render_stops_the_run_and_keeps_the_receipt(
    finished: tuple[Any, OwnerWorkflow, Budget, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    meta, workflow, budget, run_dir = finished

    def blocked(*a: object, **k: object) -> NoReturn:
        raise ValueError("owner_render_blocked")

    monkeypatch.setattr(rp, "render_owner_slice", blocked)
    outcome = rp._finish_run(workflow, run_dir, meta, budget)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "render: owner_render_blocked"
    assert (run_dir / "owner-run.json").is_file()
    assert run_json(run_dir)["stopped_reason"] == "render: owner_render_blocked"


def test_a_verify_failure_after_the_rename_keeps_the_delivery(
    finished: tuple[Any, OwnerWorkflow, Budget, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    meta, workflow, budget, run_dir = finished

    def tampered(*a: object, **k: object) -> NoReturn:
        raise ValueError("owner_render_delivery")

    monkeypatch.setattr(rp, "verify_owner_rendered_slice", tampered)
    outcome = rp._finish_run(workflow, run_dir, meta, budget)
    assert outcome.stopped_reason == "render: owner_render_delivery"
    assert (run_dir / "delivery" / "report.html").is_file()


def test_sealing_an_unfinished_walk_is_a_named_fault(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The loop returns with the walk still open and no publisher is planned: the receipt cannot
    be written, and that ``WorkflowError`` ends the run as ``stopped`` with a ``run.json``."""
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    monkeypatch.setattr(ToolLoop, "run", lambda self: ())
    monkeypatch.setattr(rp, "plan", lambda requested: ("CP-0",))
    outcome = rp._run_pathway(checked, args["run_dir"], args["adapter"])
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "WorkflowError: not_permitted"
    assert not (args["run_dir"] / "owner-run.json").exists()
    assert run_json(args["run_dir"])["stopped_reason"] == "WorkflowError: not_permitted"
