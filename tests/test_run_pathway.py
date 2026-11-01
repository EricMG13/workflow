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
import traceback
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import pytest

from deploy_vii.live.prompts import PromptError
from deploy_vii.preparation import prepare
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
    CheckedRun,
    RunDirExists,
    check_arguments,
    stage_sources,
)
from deploy_workflow.run_pathway import run_pathway
from deploy_workflow.workflow import WorkflowError

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
STOPPED_SET = {"sources", "pack", "execution", "calls.jsonl", "run.json", "cap.json"}


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
    assert context["sha256"] == hashlib.sha256(args["context"].read_bytes()).hexdigest()
    assert (
        html["converted_sha256"]
        == hashlib.sha256((args["run_dir"] / "sources" / "s1.txt").read_bytes()).hexdigest()
    )


def test_the_harness_path_keeps_the_original_hash_and_the_html_media_type(
    args: dict[str, Any],
) -> None:
    """``_run_pathway`` without the caller's entries: an HTML source stays ``text/html`` with its
    original hash, and its staged (converted) hash is ``converted_sha256``."""
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    rp._run_pathway(checked, args["run_dir"], args["adapter"])
    html, text, context = run_json(args["run_dir"])["sources"]
    staged = (args["run_dir"] / "sources" / "s1.txt").read_bytes()
    assert html["media_type"] == "text/html"
    assert html["sha256"] == hashlib.sha256(HTML).hexdigest()
    assert html["converted_sha256"] == hashlib.sha256(staged).hexdigest()
    assert text["media_type"] == "text/plain" and text["converted_sha256"] is None
    assert text["sha256"] == hashlib.sha256(b"plain text\n").hexdigest()
    assert context["media_type"] == "text/plain"


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


def test_a_staged_file_changed_before_prepare_ends_is_a_stop_with_run_json(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:

    def tampering(request: Any, sources: Path, out: Path) -> Any:
        (sources / "s1.txt").write_bytes(b"changed\n")
        return prepare(request, sources, out)

    monkeypatch.setattr(run_inputs_module, "prepare", tampering)
    outcome = run_pathway(**args)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "prepare: source s1 changed"
    assert run_json(args["run_dir"])["stopped_reason"] == "prepare: source s1 changed"


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


SPENT = Decimal("0.3")


def seed_spend(budget: Budget) -> None:
    """One settled charge (0.2) and one held unknown (0.1): spent is their sum, 0.3."""
    first, second = "call-" + "a" * 8, "call-" + "b" * 8
    budget.reserve(first, Decimal("0.25"), config_id="sol-medium")
    budget.settle(first, Decimal("0.2"))
    budget.reserve(second, Decimal("0.1"), config_id="sol-medium")
    budget.settle(second, None)


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
    budget = Budget(Decimal(1), run_dir / "execution")
    seed_spend(budget)
    return meta, workflow, budget, run_dir


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
    assert outcome.spent_usd == SPENT
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
    assert outcome.spent_usd == SPENT
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
    assert outcome.spent_usd == SPENT
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


# ---------------------------------------------------------------- the walk to a publication


@pytest.fixture
def walked(args: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> CheckedRun:
    """The real ``_walk``, ``_drive``, ``publish`` and ``_finish_run`` over the gap pack (CP-0, then
    a refused publication). Only ``ToolLoop.run`` is replaced: it does the fixture's reads and the
    CP-0 submit on the real workflow, and books a settled charge and a held unknown on the real
    budget. No recording is used."""
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    pack = fw.make_pack(True)
    monkeypatch.setattr(rp, "load_pack", lambda path: pack)

    def run(self: ToolLoop) -> tuple[dict[str, Any], ...]:
        fw.read_sources(self._workflow, gap=True)
        result = self._workflow.submit_review(fw.readiness(pack, gap=True))
        seed_spend(self._budget)
        return (result,)

    monkeypatch.setattr(ToolLoop, "run", run)
    return checked


def test_a_walk_with_a_publication_settles_through_the_public_seams(
    args: dict[str, Any], walked: CheckedRun
) -> None:
    outcome = rp._run_pathway(walked, args["run_dir"], args["adapter"])
    run_dir = args["run_dir"]
    assert outcome.outcome == "settled" and outcome.stopped_reason is None
    assert outcome.spent_usd == SPENT
    receipt = json.loads((run_dir / "owner-run.json").read_text())
    assert [p["status"] for p in receipt["publications"]] == ["refused"]  # publish() ran
    assert (run_dir / "delivery" / "report.html").is_file()
    assert run_json(run_dir)["outcome"] == "settled"


def test_a_receipt_that_fails_verification_stops_the_run_and_keeps_the_spend(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    def tampered(*a: object, **k: object) -> NoReturn:
        raise WorkflowError("identity_mismatch")

    monkeypatch.setattr(rp, "verify_owner_run_receipt", tampered)
    outcome = rp._run_pathway(walked, args["run_dir"], args["adapter"])
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == "WorkflowError: identity_mismatch"
    assert outcome.spent_usd == SPENT
    assert not (args["run_dir"] / "delivery").exists()
    assert (args["run_dir"] / "owner-run.json").is_file()


def test_a_non_terminal_refused_publication_stops_with_its_code_and_no_receipt(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    real_publish = OwnerWorkflow.publish

    def publish(self: OwnerWorkflow) -> dict[str, Any]:
        seen["result"] = real_publish(self)
        return seen["result"]  # type: ignore[no-any-return]

    monkeypatch.setattr(OwnerWorkflow, "_refused", property(lambda self: False))
    monkeypatch.setattr(OwnerWorkflow, "publish", publish)
    outcome = rp._run_pathway(walked, args["run_dir"], args["adapter"])
    code = seen["result"]["error_code"]
    assert seen["result"]["status"] == "refused" and code
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == f"publish: {code}"
    assert outcome.spent_usd == SPENT  # the budget's spend so far, not zero
    assert not (args["run_dir"] / "owner-run.json").exists()
    assert run_json(args["run_dir"])["stopped_reason"] == f"publish: {code}"


class CountingWorkflow:
    def __init__(self, result: dict[str, Any] | None) -> None:
        self.result, self.published = result, 0

    def publish(self) -> dict[str, Any]:
        self.published += 1
        if self.result is None:
            raise AssertionError("publish was called")
        return self.result


class CountingLoop:
    def __init__(self) -> None:
        self.runs = 0

    def run(self) -> tuple[()]:
        self.runs += 1
        return ()


def test_the_walk_resumes_after_a_publication_that_returns_a_next_step() -> None:
    workflow = CountingWorkflow({"status": "ok", "error_code": None, "next_step": "step"})
    loop = CountingLoop()
    assert rp._drive(workflow, loop, fw.make_pack(False)) is None  # type: ignore[arg-type]
    assert (workflow.published, loop.runs) == (1, 2)


def test_a_plan_with_no_publisher_never_calls_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow, loop = CountingWorkflow(None), CountingLoop()
    monkeypatch.setattr(rp, "plan", lambda requested: ("CP-0",))
    assert rp._drive(workflow, loop, fw.make_pack(False)) is None  # type: ignore[arg-type]
    assert (workflow.published, loop.runs) == (0, 1)


# ---------------------------------------------------------------- unnamed faults propagate


def test_a_value_error_outside_the_named_seams_propagates(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(requested: object) -> NoReturn:
        raise ValueError("not a named seam")

    monkeypatch.setattr(rp, "plan", broken)
    with pytest.raises(ValueError, match="not a named seam"):
        rp._run_pathway(walked, args["run_dir"], args["adapter"])
    assert not (args["run_dir"] / "run.json").exists()


def test_run_dir_exists_from_staging_propagates_and_the_other_run_is_untouched(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir: Path = args["run_dir"]

    def raced(checked: object, directory: Path) -> NoReturn:
        directory.mkdir()
        (directory / "theirs.txt").write_text("another run")
        raise RunDirExists(f"{directory} already exists")

    monkeypatch.setattr(rp, "stage_sources", raced)
    with pytest.raises(RunDirExists):
        run_pathway(**args)
    assert files_under(run_dir) == {"theirs.txt": hashlib.sha256(b"another run").hexdigest()}


@pytest.mark.parametrize("seam", ["load_pack", "create", "render"])
def test_an_unnamed_exception_at_a_seam_propagates(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch, seam: str
) -> None:
    def broken(*a: object, **k: object) -> NoReturn:
        raise RuntimeError("a programming error")

    if seam == "load_pack":
        monkeypatch.setattr(rp, "load_pack", broken)
    elif seam == "create":
        monkeypatch.setattr(OwnerWorkflow, "create", staticmethod(broken))
    else:
        monkeypatch.setattr(rp, "render_owner_slice", broken)
    with pytest.raises(RuntimeError, match="programming error"):
        rp._run_pathway(walked, args["run_dir"], args["adapter"])
    assert not (args["run_dir"] / "run.json").exists()


# ---------------------------------------------------------------- the named seams stop the run


def test_a_workflow_that_cannot_be_created_stops_with_its_code(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*a: object, **k: object) -> NoReturn:
        raise WorkflowError("not_permitted")

    monkeypatch.setattr(OwnerWorkflow, "create", staticmethod(refuse))
    outcome = rp._run_pathway(walked, args["run_dir"], args["adapter"])
    assert outcome.stopped_reason == "workflow: not_permitted"
    assert outcome.spent_usd == Decimal(0)
    assert run_json(args["run_dir"])["stopped_reason"] == "workflow: not_permitted"


def test_a_pack_that_fails_to_load_stops_as_prepare(
    args: dict[str, Any], walked: CheckedRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(path: Path) -> NoReturn:
        raise ValueError("Prepared pack hash mismatch")

    monkeypatch.setattr(rp, "load_pack", refuse)
    outcome = rp._run_pathway(walked, args["run_dir"], args["adapter"])
    assert outcome.stopped_reason == "prepare: Prepared pack hash mismatch"
    assert run_json(args["run_dir"])["outcome"] == "stopped"


def test_run_json_is_synced_as_a_file_then_moved_then_its_directory_is_synced(
    finished: tuple[Any, OwnerWorkflow, Budget, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    meta, workflow, budget, run_dir = finished
    events: list[tuple[str, int]] = []
    real_fsync, real_replace = os.fsync, os.replace
    directory = run_dir.stat().st_ino

    def fsync(fd: int) -> None:
        events.append(("dir" if os.fstat(fd).st_ino == directory else "file", os.fstat(fd).st_ino))
        real_fsync(fd)

    def replace(src: Any, dst: Any) -> None:
        events.append(("replace", os.stat(src).st_ino))
        real_replace(src, dst)

    monkeypatch.setattr("deploy_workflow.run_pathway.os.fsync", fsync)
    monkeypatch.setattr("deploy_workflow.run_pathway.os.replace", replace)
    rp._finish_run(workflow, run_dir, meta, budget)
    moved = next(i for i, (kind, _) in enumerate(events) if kind == "replace")
    inode = events[moved][1]
    assert ("file", inode) in events[:moved]  # the temp file's data is synced before the move
    assert events[moved + 1] == ("dir", directory)  # then the directory entry


# ---------------------------------------------------------------- stderr and run.json redaction


def test_a_partial_stderr_line_with_a_key_is_redacted_when_the_run_ends(
    args: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    def factory(pack: Any) -> PromptFor:
        inner = rp._default_prompt_for(pack)

        def prompt_for(binding: Any, spec: Any, issues: tuple[str, ...]) -> Any:
            print(f"tail {SECRET}", end="", file=sys.stderr)  # no newline
            return inner(binding, spec, issues)

        return prompt_for

    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    rp._run_pathway(checked, args["run_dir"], args["adapter"], factory)
    err = capsys.readouterr().err
    assert SECRET not in err and "tail [redacted]" in err


def test_stderr_written_while_staging_is_redacted(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real = prepare

    def noisy(request: Any, sources: Path, out: Path) -> Any:
        print(f"library warning {SECRET}", file=sys.stderr)
        print(f"partial {SECRET}", end="", file=sys.stderr)
        return real(request, sources, out)

    monkeypatch.setattr(run_inputs_module, "prepare", noisy)
    run_pathway(**args)
    err = capsys.readouterr().err
    assert SECRET not in err
    assert "library warning [redacted]" in err and "partial [redacted]" in err


def test_a_key_shaped_source_path_is_redacted_in_run_json(args: dict[str, Any]) -> None:
    odd = args["sources"][1].path.with_name(f"{SECRET}.txt")
    args["sources"][1].path.rename(odd)
    args["sources"][1] = CaseSource("s2", odd, "text/plain")
    run_pathway(**args)
    text = (args["run_dir"] / "run.json").read_text()
    assert SECRET not in text and "[redacted]" in text
    assert_clean(args["run_dir"], SECRET)


def test_a_double_fault_does_not_chain_the_raw_fault_into_the_escaping_error(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mapped fault carries a key; writing ``run.json`` then fails (a leftover temp file).
    The error that escapes must not hold the raw fault as its context."""

    def prepare(request: object, sources: object, out: object) -> NoReturn:
        (args["run_dir"] / "run.json.tmp").write_bytes(b"")
        raise ValueError(f"cannot prepare with {SECRET}")

    monkeypatch.setattr(run_inputs_module, "prepare", prepare)
    with pytest.raises(FileExistsError) as escaped:
        run_pathway(**args)
    text = "".join(traceback.format_exception(escaped.value))
    assert SECRET not in text
    assert escaped.value.__context__ is None and escaped.value.__cause__ is None
    assert_clean(args["run_dir"], SECRET)


def test_the_redacting_stream_is_closed_when_the_run_ends(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    streams: list[Any] = []
    real = Redactor.redact_stream

    def keep(self: Redactor, stream: Any) -> Any:
        streams.append(real(self, stream))
        return streams[-1]

    monkeypatch.setattr(Redactor, "redact_stream", keep)
    run_pathway(**args)
    assert len(streams) == 2 and all(stream.closed for stream in streams)  # outer and inner


def test_the_harness_path_labels_an_unchanged_html_conversion_text_html(
    args: dict[str, Any],
) -> None:
    """The label is the caller's media type, not ``sha256 != original_sha256``: HTML whose
    conversion changes nothing keeps ``text/html`` and a non-null ``converted_sha256``."""
    args["sources"][0].path.write_bytes(b"plain\n")
    checked = check_arguments(**args)
    assert checked.files[0].sha256 == checked.files[0].original_sha256
    stage_sources(checked, args["run_dir"])
    rp._run_pathway(checked, args["run_dir"], args["adapter"])
    html = run_json(args["run_dir"])["sources"][0]
    assert html["media_type"] == "text/html"
    assert html["converted_sha256"] == hashlib.sha256(b"plain\n").hexdigest()


def test_the_phase_accessor_mirrors_the_private_phase_across_a_walk(args: dict[str, Any]) -> None:
    """O5 Q6: ``phase`` is a read-only view of the walk's phase (here: create, a valid submit,
    then a refused publication that ends the walk)."""
    checked = check_arguments(**args)
    run_dir: Path = args["run_dir"]
    run_dir.mkdir()
    pack = fw.make_pack(True)
    workflow = OwnerWorkflow.create(
        run_dir / "execution", pack, publication_directory=run_dir / "publication"
    )
    assert checked.files  # the arguments are real; the walk below uses the gap pack
    seen = [workflow.phase]
    assert workflow.phase == workflow._phase == "analytical"
    fw.read_sources(workflow, gap=True)
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    seen.append(workflow.phase)
    assert workflow.publish()["status"] == "refused"
    seen.append(workflow.phase)
    assert seen[-1] == workflow._phase
    assert len(set(seen)) > 1  # the accessor moved with the walk
    with pytest.raises(AttributeError):
        workflow.phase = "complete"  # type: ignore[misc]


# ---------------------------------------------------------------- resume (O3 Task 3b: G5, N1, R9a)

pack_helpers: Any = importlib.import_module("tests.model._pack")


class Kill(BaseException):
    """A process killed: not an Exception, so nothing in the run catches it."""


def scripted_complete(
    monkeypatch: pytest.MonkeyPatch, replies: list[Any]
) -> list[tuple[str, int, str]]:
    """The provider double: each request takes the next reply (or raises it). What was sent."""
    sent: list[tuple[str, int, str]] = []
    queue = list(replies)

    def complete(
        self: object,
        request: object,
        *,
        invocation_digest: str,
        call_index: int,
        reservation_id: str,
    ) -> Any:
        sent.append((invocation_digest, call_index, reservation_id))
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(RecordedAdapter, "complete", complete)
    return sent


def kill_at_reserve(monkeypatch: pytest.MonkeyPatch, nth: int) -> None:
    """The process dies as the nth reservation of the run is about to be made."""
    real = Budget.reserve
    seen = [0]

    def reserve(self: Budget, *a: Any, **k: Any) -> None:
        seen[0] += 1
        if seen[0] == nth:
            raise Kill()
        real(self, *a, **k)

    monkeypatch.setattr(Budget, "reserve", reserve)


def read_s1() -> Any:
    return pack_helpers.ok(
        pack_helpers.tool_call("read_pages", source_id="s1", first_page=1, last_page=1)
    )


@pytest.fixture
def killed(args: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A fresh run killed between two model calls: the first call is settled and recorded, the
    second reservation is never made. The run directory holds no ``run.json``."""
    scripted_complete(monkeypatch, [read_s1()])
    real = Budget.reserve
    kill_at_reserve(monkeypatch, 2)
    with pytest.raises(Kill):
        run_pathway(**args)
    monkeypatch.setattr(Budget, "reserve", real)
    assert not (args["run_dir"] / "run.json").exists()
    return args


def calls_of(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]


def test_a_fresh_run_creates_cap_json_once(killed: dict[str, Any]) -> None:
    run_dir = killed["run_dir"]
    assert json.loads((run_dir / "cap.json").read_text()) == {"cap_usd": "1", "mode": "offline"}
    with pytest.raises(rp.CapExists):
        rp._create_cap(run_dir, Decimal(2), "offline")
    assert json.loads((run_dir / "cap.json").read_text()) == {"cap_usd": "1", "mode": "offline"}


def test_resume_continues_call_index_and_digest_and_counts_the_spend_once(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir: Path = killed["run_dir"]
    (first,) = calls_of(run_dir)
    assert (first["call_index"], first["cost_status"]) == (0, "computed")

    def not_called(*a: object, **k: object) -> NoReturn:
        raise AssertionError("a resume stages nothing")

    monkeypatch.setattr(rp, "stage_sources", not_called)
    monkeypatch.setattr(run_inputs_module, "_check_run_dir", not_called)
    sent = scripted_complete(
        monkeypatch, [pack_helpers.failed("sent_known", "ProviderRejected", 400)]
    )
    outcome = run_pathway(**killed, resume=True)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("ProviderRejected")
    assert [(s[0], s[1]) for s in sent] == [(first["invocation_digest"], 1)]
    records = calls_of(run_dir)
    assert [r["call_index"] for r in records] == [0, 1]  # appended, never rewritten
    assert records[0] == first
    assert outcome.spent_usd == Decimal(first["settled_usd"])  # the first call, counted once
    markers = [
        p
        for p in (run_dir / "execution/owner-run-audit/reservations").iterdir()
        if not p.name.endswith(".settled")
    ]
    assert len(markers) == 2
    assert run_json(run_dir)["stopped_reason"] == outcome.stopped_reason


def test_a_reservation_left_by_a_crash_stops_the_resume_and_sends_nothing(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    scripted_complete(monkeypatch, [Kill()])  # dies inside complete: the hold may have been sent
    with pytest.raises(Kill):
        run_pathway(**args)
    run_dir: Path = args["run_dir"]
    (marker,) = (run_dir / "execution/owner-run-audit/reservations").iterdir()
    held = Decimal(json.loads(marker.read_text())["usd"])
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert sent == []
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None and "unsettled by a crash" in outcome.stopped_reason
    assert outcome.spent_usd == held  # counted once
    assert run_json(run_dir)["outcome"] == "stopped"


def test_a_held_unknown_charge_stops_the_resume_and_sends_nothing(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    scripted_complete(
        monkeypatch, [pack_helpers.failed("sent_unknown", "ProviderServerError", 502)]
    )
    kill_at_reserve(monkeypatch, 2)  # the retry is never reserved
    real = Budget.reserve
    with pytest.raises(Kill):
        run_pathway(**args)
    monkeypatch.setattr(Budget, "reserve", real)
    run_dir: Path = args["run_dir"]
    (first,) = calls_of(run_dir)
    assert first["cost_status"] == "unknown"
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert sent == []
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("UnknownCharge")  # the loop's name for it (R15)
    assert outcome.spent_usd == Decimal(first["reserved_usd"])  # the hold, counted once


def test_a_torn_audit_ends_the_resume_as_torn_audit_not_as_a_workflow_code(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir: Path = killed["run_dir"]
    (first,) = calls_of(run_dir)
    (run_dir / "execution/owner-run-audit/calls" / ("0" * 64)).write_text("{}")
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**killed, resume=True)
    assert outcome.outcome == "stopped" and outcome.stopped_reason == "TornAudit"
    assert run_json(run_dir)["stopped_reason"] == "TornAudit"
    assert outcome.spent_usd == Decimal(first["settled_usd"])
    assert sent == []


def test_a_resume_without_a_run_dir_or_over_a_finished_run_is_refused_untouched(
    args: dict[str, Any],
) -> None:
    with pytest.raises(run_inputs_module.RunDirInvalid):
        run_pathway(**args, resume=True)
    assert not os.path.lexists(args["run_dir"])
    assert run_pathway(**args).outcome == "stopped"  # RecordingMissing: run.json is written
    before = files_under(args["run_dir"])
    with pytest.raises(rp.ResumeRefused):
        run_pathway(**args, resume=True)
    assert files_under(args["run_dir"]) == before


HIGH = ModelSpec("sol-high", "openai", "gpt-6.1-sol", "high")


@pytest.mark.parametrize(
    "change",
    [
        {"cap_usd": Decimal(2)},
        {"cap_usd": Decimal("0.5")},
        {"run_id": "run-2"},
        {"case_id": "case-2"},
        {"model": HIGH},
    ],
    ids=["cap-raised", "cap-lowered", "run_id", "case_id", "config_id"],
)
def test_a_resume_with_other_arguments_is_refused_before_anything_changes(
    killed: dict[str, Any], tmp_path: Path, change: dict[str, Any]
) -> None:
    run_dir: Path = killed["run_dir"]
    before = files_under(run_dir)
    other = {**killed, **change}
    if "model" in change:
        other["adapter"] = recorded_adapter(HIGH, tmp_path / "recordings")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**other, resume=True)
    assert files_under(run_dir) == before


def test_a_resume_with_another_pathway_is_refused_before_anything_changes(
    killed: dict[str, Any], tmp_path: Path
) -> None:
    context = json.loads((ROOT / "cases/context/research-minimal.json").read_text())
    context["run"]["pathway"] = "earnings_update"
    other_context = tmp_path / "other-context.json"
    other_context.write_text(json.dumps(context))
    run_dir: Path = killed["run_dir"]
    before = files_under(run_dir)
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(
            **{**killed, "context": other_context, "pathway": "earnings_update"}, resume=True
        )
    assert files_under(run_dir) == before


def test_a_second_run_pathway_on_a_held_run_dir_is_refused_before_it_writes(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir: Path = killed["run_dir"]
    seen: list[BaseException] = []

    def second(self: object, *a: object, **k: object) -> Any:
        before = files_under(run_dir)
        try:
            run_pathway(**killed, resume=True)
        except rp.RunDirBusy as error:
            seen.append(error)
        assert files_under(run_dir) == before
        return pack_helpers.failed("sent_known", "ProviderRejected", 400)

    monkeypatch.setattr(RecordedAdapter, "complete", second)
    outcome = run_pathway(**killed, resume=True)
    assert outcome.outcome == "stopped" and len(seen) == 1
    again = scripted_complete(monkeypatch, [])
    with pytest.raises(rp.ResumeRefused):  # the lock is released with the run; run.json now exists
        run_pathway(**killed, resume=True)
    assert again == []


def test_a_fresh_run_holds_the_lock_too(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[BaseException] = []

    def second(self: object, *a: object, **k: object) -> Any:
        try:
            run_pathway(**args, resume=True)
        except rp.RunDirBusy as error:
            seen.append(error)
        return pack_helpers.failed("sent_known", "ProviderRejected", 400)

    monkeypatch.setattr(RecordedAdapter, "complete", second)
    assert run_pathway(**args).outcome == "stopped" and len(seen) == 1


def test_a_resume_reads_state_once_and_never_polls_it_while_it_drives(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A poller on `state()` makes the mutators fail `not_permitted` (Task 2, I1): the one read is
    the loop's seed, before the first request."""
    reads: list[str] = []
    real = OwnerWorkflow.state

    def counting(self: OwnerWorkflow) -> Any:
        reads.append("state")
        return real(self)

    monkeypatch.setattr(OwnerWorkflow, "state", counting)
    scripted_complete(monkeypatch, [pack_helpers.failed("sent_known", "ProviderRejected", 400)])
    assert run_pathway(**killed, resume=True).outcome == "stopped"
    assert reads == ["state"]


def test_a_resume_of_a_run_killed_before_any_call_still_checks_run_id_and_sources(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No `calls.jsonl` and no marker to compare with: the staged pack alone refuses."""
    scripted_complete(monkeypatch, [])
    kill_at_reserve(monkeypatch, 1)
    with pytest.raises(Kill):
        run_pathway(**args)
    run_dir: Path = args["run_dir"]
    assert not (run_dir / "calls.jsonl").exists()
    before = files_under(run_dir)
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**{**args, "run_id": "run-2"}, resume=True)
    (args["sources"][1].path).write_bytes(b"other text\n")  # the caller's file changed since
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)
    assert files_under(run_dir) == before


class PhaseWorkflow:
    def __init__(self, phase: str, publications: tuple[str, ...] = ()) -> None:
        self.phase, self.published = phase, 0
        self._publications = list(publications)

    def publish(self) -> dict[str, Any]:
        self.published += 1
        self.phase = "complete"
        return {"status": "ok", "error_code": None, "next_step": None}


@pytest.mark.parametrize(
    ("phase", "runs", "published", "reason"),
    [
        ("analytical", 1, 0, None),
        ("walked", 0, 1, None),
        ("complete", 0, 0, None),
        ("failed", 0, 0, "resume: the publication left the walk failed"),
    ],
)
def test_a_resumed_walk_continues_by_the_phase_open_reports(
    phase: str, runs: int, published: int, reason: str | None
) -> None:
    workflow, loop = PhaseWorkflow(phase), CountingLoop()
    assert rp._drive_resumed(workflow, loop) == reason  # type: ignore[arg-type]
    assert (loop.runs, workflow.published) == (runs, published)


# ---------------------------------------------------------------- fix round 1 (R13 to R19)


def fresh_reason_dies_before_run_json(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """The run decides its stop, then the process dies as it writes run.json: the reasons the
    fresh run was about to write."""
    wrote: list[Any] = []

    def die(run_dir: Path, meta: object, outcome: str, reason: str | None) -> NoReturn:
        wrote.append((outcome, reason))
        raise Kill("run.json")

    monkeypatch.setattr(rp, "_write_run_json", die)
    return wrote


def gap_world(args: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Path, Any]:
    """The staged run over the gap pack (CP-0, then a refused publication), as `walked` does."""
    checked = check_arguments(**args)
    run_dir: Path = args["run_dir"]
    stage_sources(checked, run_dir)
    pack = fw.make_pack(True)
    monkeypatch.setattr(rp, "load_pack", lambda path: pack)
    return checked, run_dir, lambda p: pack_helpers.prompt_for


def test_a_settled_call_with_no_record_stops_the_resume_as_unrecorded_call(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """R13: killed after `settle`, before the record: the next call would reuse the lost call's
    call_index. The resume sends nothing and counts the charge."""
    import dataclasses

    run_dir: Path = args["run_dir"]
    reply = dataclasses.replace(read_s1(), raw=None)  # a recorded reply: no raw archive to collide
    with monkeypatch.context() as m:
        scripted_complete(m, [reply])
        real = Budget.settle

        def settle_then_die(self: Budget, *a: Any, **k: Any) -> NoReturn:
            real(self, *a, **k)
            raise Kill("after settle")

        m.setattr(Budget, "settle", settle_then_die)
        with pytest.raises(Kill):
            run_pathway(**args)
    assert not (run_dir / "calls.jsonl").exists()
    (marker,) = (run_dir / "execution/owner-run-audit/reservations").glob("call-*.settled")
    charged = Decimal(json.loads(marker.read_text())["usd"])
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert sent == [] and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("UnrecordedCall")
    assert outcome.spent_usd == charged and charged > 0
    assert run_json(run_dir)["outcome"] == "stopped"


@pytest.mark.parametrize(
    ("usage", "name"),
    [
        (pack_helpers.Usage(input_tokens=300_000, output_tokens=10), "UnknownCharge"),
        (pack_helpers.Usage(input_tokens=100, output_tokens=10_000_000), "OverrunStop"),
    ],
    ids=["unknown", "overrun"],
)
def test_a_money_stop_on_the_call_that_ends_the_walk_stops_the_resume(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch, usage: Any, name: str
) -> None:
    """R15: the call whose submit ends the analytical walk is settled after the walk moved on; a
    kill before run.json leaves nothing to ask the model, yet the stop stands."""
    checked, run_dir, factory = gap_world(args, monkeypatch)
    with monkeypatch.context() as m:
        scripted_complete(
            m,
            [
                pack_helpers.ok(pack_helpers.read_identity()),
                pack_helpers.ok(pack_helpers.gap_submit(), usage=usage),
            ],
        )
        wrote = fresh_reason_dies_before_run_json(m)
        with pytest.raises(Kill):
            rp._run_pathway(checked, run_dir, args["adapter"], factory)
    assert wrote[0][0] == "stopped" and wrote[0][1].startswith(name)
    sent = scripted_complete(monkeypatch, [])
    outcome = rp._run_pathway(checked, run_dir, args["adapter"], factory, resume=True)
    assert sent == [] and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None and outcome.stopped_reason.startswith(name)


STOPS = {
    "sent_usage": lambda: pack_helpers.failed(
        "sent_usage",
        "MalformedReply",
        200,
        usage=pack_helpers.Usage(input_tokens=10, output_tokens=5),
    ),
    "4xx": lambda: pack_helpers.failed("sent_known", "ProviderRejected", 400),
    "KeyReflected": lambda: pack_helpers.failed("sent_known", "KeyReflected", 400),
    "NoSubmit": lambda: pack_helpers.ok(),
}


@pytest.mark.parametrize("kind", list(STOPS))
def test_a_recorded_stop_survives_a_kill_and_the_resume_sends_nothing(
    kind: str, args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """R16: the loop wrote the stop into the call's record, then the process died before run.json;
    the resume ends with the very stop the fresh run was writing and sends nothing (R9: a
    key-reflecting reply is never resent)."""
    with monkeypatch.context() as m:
        scripted_complete(m, [STOPS[kind]()])
        wrote = fresh_reason_dies_before_run_json(m)
        with pytest.raises(Kill):
            run_pathway(**args)
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert sent == [] and outcome.outcome == "stopped"
    assert outcome.stopped_reason == wrote[0][1]


def test_a_first_402_record_is_not_a_stop_the_resume_waits_and_resends(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def credit() -> Any:
        return pack_helpers.failed("sent_known", "CreditExhausted402", 402)

    with monkeypatch.context() as m:
        scripted_complete(m, [credit()])
        kill_at_reserve(m, 2)  # killed while it waits out the 402
        with pytest.raises(Kill):
            run_pathway(**args)
    sent = scripted_complete(monkeypatch, [credit(), credit()])
    outcome = run_pathway(**args, resume=True)  # a new logical request: waits out one 402, resends
    assert len(sent) == 2 and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None and outcome.stopped_reason.startswith(
        "CreditExhausted"
    )


def test_a_source_dropped_from_the_resume_is_refused(killed: dict[str, Any]) -> None:
    """R17: the same ids and the same files, not a subset."""
    run_dir: Path = killed["run_dir"]
    before = files_under(run_dir)
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**{**killed, "sources": killed["sources"][:1]}, resume=True)
    assert files_under(run_dir) == before


def test_a_live_run_resumed_offline_is_refused(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R18: the mode is part of the identity cap.json records."""
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    ruling = rulings / "lift.md"
    ruling.write_text(RULING)
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)

    def transport(request: object) -> NoReturn:
        raise AssertionError("the transport was called")

    live = adapter_module.live_adapter(MODEL, ruling, transport=transport, environ={})
    with monkeypatch.context() as m:
        m.setattr(LiveAdapter, "complete", lambda self, request, **k: read_s1())
        kill_at_reserve(m, 2)
        with pytest.raises(Kill):
            run_pathway(**{**args, "adapter": live})
    run_dir: Path = args["run_dir"]
    assert json.loads((run_dir / "cap.json").read_text())["mode"] == "live"
    before = files_under(run_dir)
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)
    assert files_under(run_dir) == before


@pytest.mark.parametrize(
    "text",
    [
        '{"cap_usd": "sNaN", "mode": "offline"}',
        '{"cap_usd": "NaN", "mode": "offline"}',
        '{"cap_usd": "1"}',
        '{"cap_usd": "1", "mode": "x"}',
        "[]",
        "not json",
    ],
)
def test_a_bad_cap_json_is_a_named_refusal(killed: dict[str, Any], text: str) -> None:
    run_dir: Path = killed["run_dir"]
    (run_dir / "cap.json").write_text(text)
    before = files_under(run_dir)
    with pytest.raises(rp.ResumeRefused):
        run_pathway(**killed, resume=True)
    assert files_under(run_dir) == before


def test_a_sealed_run_without_run_json_has_its_own_named_stop(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """R19: finishing it is an owner follow-up; the stop is named, nothing is sent."""
    checked, run_dir, factory = gap_world(args, monkeypatch)
    with monkeypatch.context() as m:
        scripted_complete(
            m,
            [
                pack_helpers.ok(pack_helpers.read_identity()),
                pack_helpers.ok(pack_helpers.gap_submit()),
            ],
        )

        def die(*a: object, **k: object) -> NoReturn:
            raise Kill("after the seal")

        m.setattr(rp, "verify_owner_run_receipt", die)
        with pytest.raises(Kill):
            rp._run_pathway(checked, run_dir, args["adapter"], factory)
    assert (run_dir / "owner-run.json").exists() and not (run_dir / "run.json").exists()
    sent = scripted_complete(monkeypatch, [])
    outcome = rp._run_pathway(checked, run_dir, args["adapter"], factory, resume=True)
    assert sent == [] and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("SealedWithoutRunRecord")
    assert "not_permitted" not in outcome.stopped_reason


def test_a_torn_audit_counts_the_crash_left_hold(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """L1: the hold a kill inside `complete` left is counted once on a TornAudit stop too."""
    scripted_complete(monkeypatch, [Kill()])
    with pytest.raises(Kill):
        run_pathway(**args)
    run_dir: Path = args["run_dir"]
    (marker,) = (run_dir / "execution/owner-run-audit/reservations").iterdir()
    held = Decimal(json.loads(marker.read_text())["usd"])
    calls = run_dir / "execution/owner-run-audit/calls"
    calls.mkdir(exist_ok=True)
    (calls / ("0" * 64)).write_text("{}")
    scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert outcome.stopped_reason == "TornAudit" and outcome.spent_usd == held


def test_a_resume_does_not_publish_again_after_a_refused_publication() -> None:
    workflow, loop = PhaseWorkflow("walked", ("refused",)), CountingLoop()
    reason = rp._drive_resumed(workflow, loop)  # type: ignore[arg-type]
    assert workflow.published == 0 and reason is not None and reason.startswith("publish:")


def test_a_reservation_marker_the_budget_cannot_load_is_a_named_stop(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """L5: a BudgetError on a resume ends `stopped` with run.json, not as an exception."""
    run_dir: Path = killed["run_dir"]
    (marker,) = (run_dir / "execution/owner-run-audit/reservations").glob("*.settled")
    marker.write_text(json.dumps(json.loads(marker.read_text()) | {"usd": "abc"}))
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**killed, resume=True)
    assert sent == [] and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None and outcome.stopped_reason.startswith("BudgetError")
    assert run_json(run_dir)["outcome"] == "stopped"


# ---------------------------------------------------------------- kills adopted from the 3b review


def test_a_crash_left_marker_alone_pins_the_config(
    args: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """config_id is checked against a reservation marker even when calls.jsonl holds nothing."""
    scripted_complete(monkeypatch, [Kill()])
    with pytest.raises(Kill):
        run_pathway(**args)
    run_dir: Path = args["run_dir"]
    assert not (run_dir / "calls.jsonl").exists()
    before = files_under(run_dir)
    other = {**args, "model": HIGH, "adapter": recorded_adapter(HIGH, tmp_path / "recordings")}
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**other, resume=True)
    assert files_under(run_dir) == before


def test_the_crash_stop_counts_the_settled_charges_and_the_held_one(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    scripted_complete(monkeypatch, [read_s1(), Kill()])
    with pytest.raises(Kill):
        run_pathway(**args)
    audit = args["run_dir"] / "execution/owner-run-audit/reservations"
    settled = sum(
        (Decimal(json.loads(p.read_text())["usd"]) for p in audit.glob("*.settled")), Decimal(0)
    )
    held = sum(
        (
            Decimal(json.loads(p.read_text())["usd"])
            for p in audit.iterdir()
            if not p.name.endswith(".settled") and not (audit / (p.name + ".settled")).exists()
        ),
        Decimal(0),
    )
    assert settled > 0 and held > 0
    sent = scripted_complete(monkeypatch, [])
    outcome = run_pathway(**args, resume=True)
    assert sent == [] and outcome.spent_usd == settled + held


def test_a_resumed_walk_reaching_the_stop_publishes_then_settles(
    args: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked, run_dir, factory = gap_world(args, monkeypatch)
    with monkeypatch.context() as m:
        scripted_complete(m, [pack_helpers.ok(pack_helpers.read_identity())])
        kill_at_reserve(m, 2)
        with pytest.raises(Kill):
            rp._run_pathway(checked, run_dir, args["adapter"], factory)
    sent = scripted_complete(monkeypatch, [pack_helpers.ok(pack_helpers.gap_submit())])
    outcome = rp._run_pathway(checked, run_dir, args["adapter"], factory, resume=True)
    assert len(sent) == 1 and outcome.outcome == "settled", outcome.stopped_reason
    receipt = json.loads((run_dir / "owner-run.json").read_text())
    assert [p["status"] for p in receipt["publications"]] == ["refused"]


def test_the_identity_is_checked_under_the_lock(
    killed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second resume that runs to its end between the first one's identity check and its lock
    cannot be followed by a second run.json."""
    real_check = rp._check_identity
    inner: list[str] = []

    def racing(checked: Any, rd: Path, redactor: Any) -> None:
        real_check(checked, rd, redactor)
        if not inner:
            inner.append("ran")
            try:
                inner.append(run_pathway(**killed, resume=True).outcome)
            except rp.RunDirBusy:
                inner.append("busy")

    monkeypatch.setattr(rp, "_check_identity", racing)
    scripted_complete(monkeypatch, [pack_helpers.failed("sent_known", "ProviderRejected", 400)] * 2)
    replaced: list[str] = []
    real_replace = os.replace

    def spy(src: Any, dst: Any) -> None:
        replaced.append(Path(dst).name)
        real_replace(src, dst)

    monkeypatch.setattr("deploy_workflow.run_pathway.os.replace", spy)
    try:
        run_pathway(**killed, resume=True)
    except rp.ResumeRefused:
        pass
    assert replaced.count("run.json") == 1, (inner, replaced)
