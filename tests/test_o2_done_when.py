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
import os
import socket
import time
from collections.abc import Iterator, Mapping
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


# (module, step) -> (the section of submissions.json `positive`, that section's top-level keys),
# written here independently of ``o2_case.FROZEN_STEP`` so that a wrong mapping fails.
FROZEN_SECTIONS = {
    ("CP-0", "source_readiness"): (
        "readiness_review",
        ("pack_sha256", "objective", "reporting_period", "issuer_confirmed", "sources")
        + ("consumers", "gaps", "analysis"),
    ),
    ("CP-1", "source_context"): (
        "cp1_source_context",
        ("pack_sha256", "entities", "sources", "limitations"),
    ),
    ("CP-1A", "business_context"): (
        "business_context",
        ("sources", "company", "business_lines", "owners", "operating_drivers", "transactions")
        + ("events", "governance_and_sponsor", "capital_allocation", "acquisitions")
        + ("disclosure_items", "credit_translations", "conflicts", "gaps", "consumers"),
    ),
    ("CP-3", "relative_value"): (
        "relative_value",
        ("instruments", "market_evidence", "preference", "risks", "gaps"),
    ),
    ("CP-5", "integrity_review"): (
        "integrity_review",
        ("claim_reviews", "contradictions", "gaps"),
    ),
    ("CP-6", "committee_challenge"): (
        "committee_challenge",
        ("recommendation", "thesis_challenges", "recovery_view", "risks", "gaps"),
    ),
}


def test_every_scripted_payload_is_the_frozen_payload() -> None:
    frozen = o2_case.frozen_submissions()["positive"]
    assert {step for _, step in FROZEN_SECTIONS} == set(o2_case.FROZEN_STEP)
    for (_, step), (section, keys) in FROZEN_SECTIONS.items():
        assert tuple(frozen[section]) == keys  # the oracle section is the one named here
        assert o2_case.payload_for(step) == json.dumps(frozen[section])
        assert tuple(json.loads(o2_case.payload_for(step))) == keys  # and that is what is scripted
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


def test_end_to_end_offline(tmp_path: Path) -> None:
    """The furthest honest walk: every step with a frozen payload (CP-0, CP-1 source_context) is
    authored and replayed; the next step, CP-1 financials, has no frozen payload and no
    recording, so both runs stop there. The settled walk with receipt and render waits on a user
    decision about ``line:N`` support in vii ``live/tools.py`` (see ``blocker``)."""
    authored = o2_case.author(
        tmp_path / "authoring", answers=("source_readiness", "source_context")
    )
    replayed = o2_case.replay(tmp_path / "replay", authored.recordings)
    for outcome in (authored.outcome, replayed):
        assert outcome.outcome == "stopped"
        assert outcome.stopped_reason is not None
        assert outcome.stopped_reason.startswith("RecordingMissing: no recording for digest ")
        assert outcome.run_id == o2_case.RUN_ID
    assert replayed.stopped_reason == authored.outcome.stopped_reason
    assert {p.name for p in replayed.run_dir.iterdir()} == STOPPED_SET
    assert {p.name for p in authored.run_dir.iterdir()} == STOPPED_SET
    records = records_of(replayed.run_dir)
    assert [(r["module_id"], r["step_id"]) for r in records] == [
        ("CP-0", "source_readiness"),
        ("CP-1", "source_context"),
        ("CP-1", "financials"),
    ]
    assert [c["name"] for c in records[1]["tool_calls"]] == [
        "search_pack",
        "search_pack",
        "submit_source_context",
    ]
    assert [r["cost_status"] for r in records] == ["computed", "computed", "unknown"]
    assert all(r["schema_version"] == "model-call/1" for r in records)
    searches = [  # the frozen drivers' searches (tests/s1a_runs.py:305-307)
        {"query": "subsequent", "source_id": "financial"},
        {"query": "acquisition", "source_id": "business"},
    ]
    assert [c["arguments_sha256"] for c in records[1]["tool_calls"][:2]] == [
        arguments_sha256(item) for item in searches
    ]
    frozen = load_arguments(o2_case.payload_for("source_context"))
    assert records[1]["tool_calls"][2]["arguments_sha256"] == arguments_sha256(frozen)
    # the replay's calls.jsonl equals the authoring run's, field for field, apart from timing
    expected = records_of(authored.run_dir)
    for group in (records, expected):
        for record in group:
            for key in TIMESTAMPS:
                record.pop(key)
    # the one field that differs is a traceback's frames (adapter code); its final line is equal
    assert [r["error"].splitlines()[-1] if r["error"] else None for r in records] == [
        r["error"].splitlines()[-1] if r["error"] else None for r in expected
    ]
    for group in (records, expected):
        for record in group:
            record.pop("error")
    assert records == expected
    bodies = [
        json.loads((d / "run.json").read_text()) for d in (authored.run_dir, replayed.run_dir)
    ]
    for body in bodies:  # the staged path of each source is under its own run directory
        for entry in body["sources"]:
            entry.pop("path")
    assert bodies[0] == bodies[1]  # same case, run_id, sources, outcome and reason
    assert set(bodies[1]) == OFFLINE_KEYS and bodies[1]["mode"] == "offline"
    heads = {h.module_id: h.status for h in Execution(replayed.run_dir / "execution").read().heads}
    assert heads == {"CP-0": "restricted"}  # CP-1 is open at financials: no head yet


class TrapMapping(Mapping[str, str]):
    """Any read raises and is recorded, except pydantic's own ``PYDANTIC_*`` plugin lookups, which
    pass through to the real environment (the library reads them whenever it builds a schema; no
    key is among them). Everything else, including iteration and length, trips."""

    def __init__(self, real: Mapping[str, str]) -> None:
        self.touched: list[str] = []
        self._real = real

    def _own(self, key: object) -> bool:
        return isinstance(key, str) and key.startswith("PYDANTIC_")

    def _trip(self, what: str) -> NoReturn:
        self.touched.append(what)
        raise AssertionError(f"environment touched: {what}")

    def __getitem__(self, key: str) -> str:
        if self._own(key):
            return self._real[key]
        self._trip(key)

    def __iter__(self) -> Iterator[str]:
        self._trip("<iter>")

    def __len__(self) -> int:
        self.touched.append("<len>")
        raise AssertionError("environment touched: <len>")

    def __contains__(self, key: object) -> bool:
        if self._own(key):
            return key in self._real
        self._trip(str(key))

    def get(self, key: str, default: object = None) -> Any:
        if self._own(key):
            return self._real.get(key, default)
        self._trip(key)


ANSWERS = ("source_readiness", "source_context")


def walk_under_trap(
    root: Path, monkeypatch: pytest.MonkeyPatch, plant: bool = False
) -> TrapMapping:
    """Author and replay with ``os.environ`` replaced by a trap. pydantic reads its own plugin
    variables lazily on first use, so a warm-up walk runs first, untrapped. ``plant`` makes the
    authoring adapter read a key variable inside the walk, to show the trap sees it."""
    warm = o2_case.author(root / "warm", answers=ANSWERS)
    o2_case.replay(root / "warm-replay", warm.recordings)
    trap = TrapMapping(os.environ)
    with monkeypatch.context() as scoped:  # pytest reads os.environ outside the test body
        scoped.setattr(os, "environ", trap)
        if plant:
            original = o2_case.ScriptAdapter.complete

            def planted(self: o2_case.ScriptAdapter, *args: Any, **kwargs: Any) -> Any:
                os.environ.get("OPENAI_API_KEY")
                return original(self, *args, **kwargs)

            scoped.setattr(o2_case.ScriptAdapter, "complete", planted)
        authored = o2_case.author(root / "a", answers=ANSWERS)
        o2_case.replay(root / "r", authored.recordings)
    return trap


def test_authoring_and_replay_read_no_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert walk_under_trap(tmp_path, monkeypatch).touched == []


def test_the_environment_trap_sees_a_read_planted_inside_the_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "OPENAI_API_KEY" in walk_under_trap(tmp_path, monkeypatch, plant=True).touched
