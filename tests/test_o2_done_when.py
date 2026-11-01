"""O2 done-when, part 1: the synthetic case through ``_run_pathway`` offline (O2 Task 5). No network.

Recordings are authored from the frozen ``cases/o2-synthetic/submissions.json`` by a test-only
``ScriptAdapter`` (``tests/o2_case.py``) and replayed through a plain ``recorded_adapter`` over a
fresh run directory with the same ``run_id``. The prompt composer is a labelled TEST composer: it
proves orchestration, not the prompts (O6), and recordings made now stop matching once O6 changes
the prompt (the digest includes the prompt hash).

``test_stopped_run_fast`` runs always. The full walk is not here: the prepared text pack cannot
pass CP-1 ``financials`` (see ``test_a_text_pack_cannot_extract_a_statement_page``), so no frozen
payload sequence reaches CP-8. That gap is reported, not worked around.
"""

import http.client
import json
import socket
import time
from pathlib import Path
from typing import Any, NoReturn

import o2_case
import pytest

from deploy_vii.execution import Execution
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.record import arguments_sha256
from deploy_workflow.model.turn import load_arguments

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
TIMESTAMPS = ("started_at", "first_byte_at", "finished_at")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


def records_of(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]


def test_every_scripted_payload_is_the_frozen_payload() -> None:
    frozen = o2_case.frozen_submissions()["positive"]
    for step_id, name in o2_case.FROZEN_STEP.items():
        assert o2_case.payload_for(step_id) == json.dumps(frozen[name])
    with pytest.raises(KeyError):
        o2_case.payload_for("financials")  # the frozen oracle holds no payload for it


def test_the_oracle_files_are_the_pinned_ones() -> None:
    o2_case.check_pins()  # raises on drift; reads cases/PINS.json


def test_a_text_pack_cannot_extract_a_statement_page(tmp_path: Path) -> None:
    """Why no full walk exists: CP-1 ``financials`` requires ``extract_statements`` on every
    statement-heading span, and that tool accepts ``page:N`` locators only, while a prepared text
    pack has ``line:N`` spans. This pins the blocker so a fix elsewhere turns this test red."""
    found = o2_case.blocker(tmp_path)
    assert found["extract_error"] == "bad_arguments"
    assert found["heading_locators"]  # the step requires spans...
    assert all(
        item.startswith("line:") for item in found["heading_locators"]
    )  # ...it cannot extract


def test_stopped_run_fast(tmp_path: Path) -> None:
    started = time.monotonic()
    authored = o2_case.author(tmp_path / "authoring", answers=("source_readiness",))
    assert authored.outcome.outcome == "stopped"  # the script ends where the recordings end
    replayed = o2_case.replay(tmp_path / "replay", authored.recordings)
    run_dir = replayed.run_dir
    # the second request has no recording: the missing recording stops the run
    assert replayed.outcome == "stopped"
    assert replayed.run_id == o2_case.RUN_ID
    assert replayed.stopped_reason is not None
    assert replayed.stopped_reason.startswith("RecordingMissing: no recording for digest ")
    assert {p.name for p in run_dir.iterdir()} == STOPPED_SET  # no raw/: a recorded run keeps none
    body = json.loads((run_dir / "run.json").read_text())
    assert set(body) == OFFLINE_KEYS
    assert body["outcome"] == "stopped" and body["stopped_reason"] == replayed.stopped_reason
    assert body["mode"] == "offline" and body["pathway"] == "portfolio_decision"
    assert body["run_id"] == o2_case.RUN_ID and body["config_id"] == o2_case.MODEL.config_id
    assert [s["source_id"] for s in body["sources"]] == [
        "identity",
        "financial",
        "business",
        "market",
        "context",
    ]
    # calls.jsonl in order: the recorded CP-0 submit, then the unrecorded CP-1 request (O5 records
    # a missing recording as AdapterError with the charge unknown; ruled C4, parked)
    records = records_of(run_dir)
    assert [(r["module_id"], r["step_id"], r["call_index"]) for r in records] == [
        ("CP-0", "source_readiness", 0),
        ("CP-1", "source_context", 0),
    ]
    first, second = records
    assert first["schema_version"] == "model-call/1" and first["cost_status"] == "computed"
    assert first["error_class"] is None and first["settled_usd"] is not None
    assert first["input_tokens"] == o2_case.USAGE.input_tokens
    assert first["output_tokens"] == o2_case.USAGE.output_tokens
    assert [c["name"] for c in first["tool_calls"]] == ["submit_source_readiness"]
    frozen = load_arguments(o2_case.payload_for("source_readiness"))
    assert first["tool_calls"][0]["arguments_sha256"] == arguments_sha256(frozen)
    assert first["submit_sha256"] is not None
    assert second["error_class"] == "AdapterError" and "RecordingMissing" in second["error"]
    assert second["cost_status"] == "unknown" and second["settled_usd"] is None
    # CP-0 is in the store from the frozen payload ("restricted": its review carries limitations);
    # the walk went no further
    heads = {h.module_id: h.status for h in Execution(run_dir / "execution").read().heads}
    assert heads == {"CP-0": "restricted"}
    # the replay's first record equals the authoring run's, apart from timestamps
    authored_first = records_of(authored.run_dir)[0]
    for key in TIMESTAMPS:
        authored_first.pop(key), first.pop(key)
    assert first == authored_first
    assert time.monotonic() - started < 300  # B16: under five minutes, no CP-1 promotion
