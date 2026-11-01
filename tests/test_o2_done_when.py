"""O2 done-when, part 1: the synthetic case through ``_run_pathway`` offline (O2 Task 5). No network.

Recordings are authored from the frozen ``cases/o2-synthetic/submissions.json`` by a test-only
``ScriptAdapter`` (``tests/o2_case.py``) and replayed through a plain ``recorded_adapter`` over a
fresh run directory with the same ``run_id``. The prompt composer is a labelled TEST composer: it
proves orchestration, not the prompts (O6), and recordings made now stop matching once O6 changes
the prompt (the digest includes the prompt hash).

``test_stopped_run_fast`` and the other tests run always. ``test_walk_through_cp1_quality_offline``
(about 4 minutes, no promotion) settles CP-0 and CP-1 and stops at CP-1A on a missing recording.
The full walk to the end state is behind ``RUN_PROMOTION`` (``test_end_to_end_offline`` and
``test_receipt_rejects_model_in_cp5_inputs``): measured by a direct drive, CP-1 takes 105 s,
publish 72 s, the receipt 107 s and its verify 110 s, so authoring plus replay is over 5 minutes
(B16). Its end state, read from the walk, is ``stopped`` with ``render: owner_render_scope``: the
renderer has no delivery scope for this pathway, so no delivery is written.
"""

import http.client
import json
import os
import socket
import time
from collections.abc import Iterator, Mapping
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn, cast

import o2_case
import pytest

from deploy_vii.contracts import Input
from deploy_vii.execution import Execution
from deploy_vii.preparation import load_pack
from deploy_workflow import financial_workflow
from deploy_workflow.financial_workflow import STATEMENT_HEADING
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.model.record import arguments_sha256
from deploy_workflow.model.turn import load_arguments
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow, verify_owner_run_receipt
from deploy_workflow.run_inputs import RunOutcome
from deploy_workflow.workflow import WorkflowError

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


UNITS = ("line:22-46", "line:47-81", "line:82-131")  # the three statement units of financial.txt


def at_financials(root: Path) -> tuple[OwnerWorkflow, Path]:
    """CP-1 ``financials`` on the prepared text pack: the frozen CP-0 and source-context payloads
    submitted, the searches the context step needs recorded."""
    empty = root / "check-recordings"
    empty.mkdir(parents=True)
    _, run_dir = o2_case._prepare(root, recorded_adapter(o2_case.MODEL, empty))
    pack = load_pack(run_dir / "pack")
    workflow = OwnerWorkflow.create(
        run_dir / "execution", pack, publication_directory=run_dir / "publication"
    )
    assert workflow.submit_review(o2_case.payload_for("source_readiness"))["status"] == "valid"
    for source_id, query in o2_case.SEARCHES:
        workflow.invoke("search_pack", {"query": query, "source_id": source_id})
    assert workflow.submit_review(o2_case.payload_for("source_context"))["status"] == "valid"
    assert workflow.binding.step_id == "financials"
    return workflow, run_dir


def test_a_text_pack_extracts_its_statement_units(tmp_path: Path) -> None:
    """B22: CP-1 ``financials`` requires every statement-heading unit of a line source to be
    extracted, a unit being ``line:K-E`` from a heading to the line before the next one. This
    replaces the Task 5 pin that ``page:N`` was the only locator ``extract_statements`` took."""
    heading = sorted(
        span.locator
        for source in load_pack(at_financials(tmp_path / "walk")[1] / "pack").sources
        if source.source_id == "financial"
        for span in source.spans
        if STATEMENT_HEADING.search(span.text)
    )
    assert heading == ["line:22", "line:47", "line:82"]
    workflow, _ = at_financials(tmp_path / "all")
    for unit in UNITS:
        done = workflow.invoke("extract_statements", {"source_id": "financial", "locators": [unit]})
        assert done["status"] == "ok", done
    # one unit short: the step names the missing coverage
    short, _ = at_financials(tmp_path / "short")
    for unit in UNITS[:2]:
        assert (
            short.invoke("extract_statements", {"source_id": "financial", "locators": [unit]})[
                "status"
            ]
            == "ok"
        )
    refused = short.submit_review("{}")
    assert refused["status"] == "refused"
    assert "Financials must extract every located statement page in this epoch" in refused["issues"]
    complete = workflow.submit_review("{}")
    assert (
        "Financials must extract every located statement page in this epoch"
        not in complete["issues"]
    )


def test_a_line_citation_naming_the_range_key_is_not_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A payload line covers an extracted row only by citing the row's own ``line:K``; the unit's
    ``line:N-M`` key is the extraction request, not a located span. The payload is a stand-in
    for a ``FinancialSubmission`` (its real shape is some 36 KB of schema): only the fields
    ``_evidence_issues`` reads, over the real extraction of the real pack."""
    workflow, run_dir = at_financials(tmp_path)
    for unit in UNITS:
        assert (
            workflow.invoke("extract_statements", {"source_id": "financial", "locators": [unit]})[
                "status"
            ]
            == "ok"
        )
    periods = [
        SimpleNamespace(
            period_id=f"p-{name}",
            end_date="2025-12-31",
            fiscal_year="FY2025",
            period_type="QUARTER" if name != "fy" else "FY",
            fiscal_quarter=int(name[1]) if name != "fy" else None,
        )
        for name in ("q1", "q2", "q3", "q4", "fy")
    ]

    submissions: dict[str, Any] = {}
    for locator in ("line:22-46", "line:24"):
        cite = SimpleNamespace(source_id="financial", locator=locator, quote="Revenue  30")
        submissions[locator] = SimpleNamespace(
            financial=SimpleNamespace(
                books=[
                    SimpleNamespace(
                        periods=periods,
                        statement_lines=[
                            SimpleNamespace(
                                period_id=period.period_id,
                                statement="IS",
                                label="Revenue",
                                value=SimpleNamespace(amount=Decimal(amount), citations=[cite]),
                            )
                            for period, amount in zip(periods, (30, 30, 30, 30, 120), strict=True)
                        ],
                    )
                ]
            )
        )
    monkeypatch.setattr(
        financial_workflow,
        "FinancialSubmission",
        SimpleNamespace(model_validate_json=lambda text: submissions[text]),
    )
    store = Execution(run_dir / "execution")
    evidence = workflow._epoch_calls[-1].source_evidence

    def uncovered(locator: str) -> list[str]:
        found = financial_workflow._evidence_issues(
            store, cast(Any, workflow.binding), locator, evidence
        )
        return [i for i in found if i.startswith("Uncovered extracted statement line")]

    row = "Uncovered extracted statement line: financial line:22-46 line 24"
    assert row in uncovered("line:22-46")  # the range key names no row
    assert row not in uncovered("line:24")  # the row's own locator covers it


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


def assert_replay_equals_authoring(authored: o2_case.Authored, replayed: RunOutcome) -> None:
    """The replay's calls.jsonl equals the authoring run's, field for field, apart from timing
    (and a traceback's frames: adapter code differs; its final line is equal), and the two
    run.json files agree apart from each run's own staged source paths."""
    records, expected = records_of(replayed.run_dir), records_of(authored.run_dir)
    for group in (records, expected):
        for record in group:
            for key in TIMESTAMPS:
                record.pop(key)
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
    for body in bodies:
        for entry in body["sources"]:
            entry.pop("path")
    assert bodies[0] == bodies[1]  # same case, run_id, sources, outcome and reason
    assert set(bodies[1]) == OFFLINE_KEYS and bodies[1]["mode"] == "offline"


def test_the_default_token_bound_stops_the_walk_at_narrative(tmp_path: Path) -> None:
    """Pins today's behaviour on sol-medium (the opus-medium walk has no listed input limit): ``run_pathway`` builds its ToolLoop with ``bytes_per_token`` 1, which
    sizes the narrative step's second request (the read body is about 669 KB) above the model's
    listed context, so a run stops there with ``ContextTooLong``. A product gap, reported."""
    authored = o2_case.author(tmp_path, answers=o2_case.ALL_STEPS[:4], model=o2_case.SOL_MODEL)
    assert authored.outcome.stopped_reason is not None
    assert authored.outcome.stopped_reason.startswith("ContextTooLong: ")
    last = records_of(authored.run_dir)[-1]
    assert (last["step_id"], last["call_index"], last["error_class"]) == (
        "narrative",
        1,
        "ContextTooLong",
    )


def test_the_frozen_business_context_assesses_every_prepared_source(tmp_path: Path) -> None:
    """CP-1A requires every prepared source assessed once, ``context`` included. The Task 4c
    freeze added the ``context`` row to the frozen ``business_context``."""
    _, run_dir = o2_case.stage(tmp_path)
    pack_ids = {s.source_id for s in load_pack(run_dir / "pack").sources}
    sources = json.loads(o2_case.payload_for("business_context"))["sources"]
    assessed = [s["source_id"] for s in sources]
    assert "context" in pack_ids and "context" in assessed
    assert sorted(assessed) == sorted(pack_ids)  # each prepared source exactly once


def test_walk_through_cp1_quality_offline(tmp_path: Path) -> None:
    """CP-0 and CP-1 through its quality step (CP-1 settles offline), authored from the frozen payloads, the frozen
    CP-1 financials and the narrative/readiness the frozen drivers compute from the read inputs
    (``s1a_runs.drive_cp1``); replayed by a plain recorded adapter. The next step (CP-1A
    business_context) is not answered here (the full walk is the gated test), so both runs stop
    there with the same reason."""
    steps = o2_case.ALL_STEPS[:6]
    authored = o2_case.author(tmp_path / "authoring", answers=steps)
    replayed = o2_case.replay(tmp_path / "replay", authored.recordings)
    for outcome in (authored.outcome, replayed):
        assert outcome.outcome == "stopped"
        assert outcome.stopped_reason is not None
        assert outcome.stopped_reason.startswith("RecordingMissing: no recording for digest ")
        assert outcome.run_id == o2_case.RUN_ID
    assert replayed.stopped_reason == authored.outcome.stopped_reason
    for run_dir in (authored.run_dir, replayed.run_dir):
        assert {p.name for p in run_dir.iterdir()} == STOPPED_SET
    records = records_of(replayed.run_dir)
    assert [(r["module_id"], r["step_id"]) for r in records] == [
        ("CP-0", "source_readiness"),
        ("CP-1", "source_context"),
        ("CP-1", "financials"),
        ("CP-1", "narrative"),
        ("CP-1", "narrative"),
        ("CP-1", "readiness"),
        ("CP-1", "readiness"),
        ("CP-1", "quality"),
        ("CP-1", "quality"),
        ("CP-1A", "business_context"),
    ]
    assert [r["cost_status"] for r in records] == ["computed"] * 9 + ["unknown"]
    assert all(r["schema_version"] == "model-call/1" for r in records)
    assert [c["name"] for c in records[1]["tool_calls"]] == [
        "search_pack",
        "search_pack",
        "submit_source_context",
    ]
    searches = [  # the frozen drivers' searches (tests/s1a_runs.py:305-307)
        {"query": "subsequent", "source_id": "financial"},
        {"query": "acquisition", "source_id": "business"},
    ]
    assert [c["arguments_sha256"] for c in records[1]["tool_calls"][:2]] == [
        arguments_sha256(item) for item in searches
    ]
    frozen = load_arguments(o2_case.payload_for("source_context"))
    assert records[1]["tool_calls"][2]["arguments_sha256"] == arguments_sha256(frozen)
    financials = o2_case.frozen_financials()
    assert [c["name"] for c in records[2]["tool_calls"]] == [
        *(item["tool"] for item in financials["tool_calls"]),
        "submit_financials",
    ]
    assert records[2]["tool_calls"][-1]["arguments_sha256"] == arguments_sha256(
        financials["submission"]
    )
    heads = {h.module_id: h.status for h in Execution(replayed.run_dir / "execution").read().heads}
    assert heads["CP-0"] == "restricted" and "CP-1" in heads  # CP-1 settled; CP-1A is open
    assert_replay_equals_authoring(authored, replayed)


promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1",
    reason="full o2 walk: CP-1 105 s, publish 72 s, receipt 107 s, verify 110 s per run, "
    "authoring plus replay over 5 minutes (B16); deferred to CI",
)
END_REASON = "render: owner_render_scope"  # read from the walk: no delivery scope for this pathway


@pytest.fixture(scope="module")
def full_walk(tmp_path_factory: pytest.TempPathFactory) -> tuple[o2_case.Authored, RunOutcome]:
    """The whole walk, authored and replayed once, shared by the gated tests."""
    root = tmp_path_factory.mktemp("o2-full")
    authored = o2_case.author(root / "authoring", answers=o2_case.ALL_STEPS)
    return authored, o2_case.replay(root / "replay", authored.recordings)


def receipt_of(run_dir: Path) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())


@promotion
def test_end_to_end_offline(full_walk: tuple[o2_case.Authored, RunOutcome]) -> None:
    """Every step with a frozen payload is authored and replayed through CP-6, publish inside the
    walk; CP-8 is refused at its begin (CP-0 did not authorise it), the receipt is sealed and
    verifies, and the renderer stops the run: it has no delivery scope for this pathway. The end
    state is read from the walk, not chosen: the Task 4 ruling expected ``owner_render_blocked``."""
    authored, replayed = full_walk
    for outcome in (authored.outcome, replayed):
        assert outcome.outcome == "stopped" and outcome.stopped_reason == END_REASON
        assert outcome.run_id == o2_case.RUN_ID
    expected_files = STOPPED_SET | {"publication", "owner-run.json"}  # no delivery, no raw/
    for run_dir in (authored.run_dir, replayed.run_dir):
        assert {p.name for p in run_dir.iterdir()} == expected_files
        receipt = receipt_of(run_dir)
        verify_owner_run_receipt(
            Execution(run_dir / "execution"), receipt, publication_directory=run_dir / "publication"
        )
        assert receipt.plan == (
            "CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3", "CP-5", "CP-6", "CP-8"
        )  # fmt: skip
        assert [(r.module_id, r.reason) for r in receipt.refusals] == [
            ("CP-8", "CP-0 has not authorized this consumer's source readiness")
        ]
        assert {h.module_id for h in receipt.heads} == set(receipt.plan) - {"CP-8"}
        assert receipt.model is not None and len(receipt.publications) == 1
    records = records_of(replayed.run_dir)
    assert all(r["schema_version"] == "model-call/1" for r in records)
    assert all(r["cost_status"] == "computed" for r in records)  # a run-ending error would not be
    steps = [(r["step_id"]) for r in records]
    expected_steps = [
        step for step in o2_case.ALL_STEPS for _ in range(2 if step in o2_case.READ_FIRST else 1)
    ]
    assert steps == expected_steps
    body = json.loads((replayed.run_dir / "run.json").read_text())
    assert body["outcome"] == "stopped" and body["stopped_reason"] == END_REASON
    assert_replay_equals_authoring(authored, replayed)


@promotion
def test_receipt_rejects_model_in_cp5_inputs(
    full_walk: tuple[o2_case.Authored, RunOutcome],
) -> None:
    """B1/B21: CP-MODEL is no input of CP-5. A sealed receipt whose CP-5 submissions list it as an
    input is rejected by ``verify_owner_run_receipt`` (``identity_mismatch``)."""
    _, replayed = full_walk
    run_dir = replayed.run_dir
    receipt = receipt_of(run_dir)
    assert receipt.model is not None
    model_input = Input(input_id="CP-MODEL", sha256=receipt.model.result_sha256, status="accepted")
    submissions = []
    for item in receipt.submissions:
        if item.binding.binding.module_id == "CP-5":
            bound = item.binding.binding
            assert "CP-MODEL" not in [i.input_id for i in bound.inputs]
            wrapped = item.binding.model_copy(
                update={
                    "binding": bound.model_copy(update={"inputs": (*bound.inputs, model_input)})
                }
            )
            item = item.model_copy(update={"binding": wrapped})
        submissions.append(item)
    tampered = receipt.model_copy(update={"submissions": tuple(submissions)})
    assert tampered != receipt
    with pytest.raises(WorkflowError) as rejected:
        verify_owner_run_receipt(
            Execution(run_dir / "execution"),
            tampered,
            publication_directory=run_dir / "publication",
        )
    assert rejected.value.code == "identity_mismatch"


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
