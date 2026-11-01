"""The tool loop drives the real OwnerWorkflow: order, money, retry, repair, redaction. No network."""

import json
import traceback
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from _pack import (
    SECRET,
    SPEC,
    ScriptedAdapter,
    Sent,
    failed,
    fw,
    gap_submit,
    make_rig,
    ok,
    owner_start,
    prompt_for,
    read_financial,
    read_identity,
    ready_submit,
    submit,
    tool_call,
)

from deploy_vii.execution import Execution
from deploy_workflow.model import loop as loop_module
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.model.budget import RunStopped
from deploy_workflow.model.loop import (
    StepStopped,
    contract_prompt_for,
    contract_tools_for,
    read_inputs_tool,
    repair_prompt,
)
from deploy_workflow.model.record import arguments_sha256
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec, Usage

CONFIG = SPEC.config_id


def _stop(rig: Any) -> StepStopped:
    with pytest.raises(StepStopped) as caught:
        rig.loop.run()
    return caught.value


def _markers(root: Path) -> list[str]:
    folder = root / "store" / "owner-run-audit" / "reservations"
    return sorted(p.name for p in folder.iterdir() if not p.name.endswith(".settled"))


# ---------------------------------------------------------------- order


def test_first_turn_runs_in_the_ordered_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit())], taped=True)
    real_turn, real_request = loop_module.redacted_turn, loop_module.redacted_request

    def turn(redactor: Redactor, value: Any) -> Any:
        rig.tape.append("redact_turn")
        return real_turn(redactor, value)

    def request(redactor: Redactor, value: Any) -> Any:
        rig.tape.append("redact_request")
        return real_request(redactor, value)

    monkeypatch.setattr(loop_module, "redacted_turn", turn)
    monkeypatch.setattr(loop_module, "redacted_request", request)
    outcomes = rig.loop.run()
    assert outcomes[-1]["status"] == "valid" and outcomes[-1]["next_step"] is None
    # The request is redacted first only because the reservation is sized from what is sent.
    assert rig.tape == [
        "redact_request",
        "reserve",
        "complete",
        "write_raw",
        "redact_turn",
        "workflow.invoke",
        "workflow.submit_review",
        "settle",
        "append",
    ]
    (record,) = rig.records()
    assert (record["call_index"], record["attempt"], record["cost_status"]) == (0, 0, "computed")
    assert record["schema_version"] == "model-call/1" and record["error_class"] is None


def test_the_adapter_must_name_the_specs_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="different configurations"):
        make_rig(tmp_path, [], adapter=ScriptedAdapter([], config_id="opus-medium"))


# ---------------------------------------------------------------- budget stop


def test_a_reservation_over_the_cap_sends_nothing(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit())], cap="0.001")
    stopped = _stop(rig)
    assert stopped.reason == "BudgetExhausted" and rig.adapter.sent == []
    (record,) = rig.records()
    assert record["error_class"] == "BudgetExhausted"
    assert (record["reserved_usd"], record["settled_usd"]) == ("0", "0")
    assert record["cost_status"] == "computed" and record["input_tokens"] is None
    assert rig.budget.spent == 0 and _markers(tmp_path) == []


# ---------------------------------------------------------------- unknown charge, retry (F1)


def _bad_gateway() -> Any:
    return failed("sent_unknown", "ProviderServerError", 502)


def test_a_502_then_a_200_is_one_retry_with_two_reservations(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [_bad_gateway(), ok(read_identity(), gap_submit())])
    assert rig.loop.run()[-1]["status"] == "valid"
    first, second = rig.records()
    assert (first["call_index"], second["call_index"]) == (0, 1)
    assert first["invocation_digest"] == second["invocation_digest"]
    assert first["cost_status"] == "unknown" and first["settled_usd"] is None
    assert first["error_class"] == "ProviderServerError" and second["error_class"] is None
    assert len(_markers(tmp_path)) == 2
    # the held reservation still counts, beside the retry's actual charge
    assert rig.budget.spent == Decimal(first["reserved_usd"]) + Decimal(second["settled_usd"])
    assert [s.call_index for s in rig.adapter.sent] == [0, 1]


def test_a_cap_that_admits_one_reservation_refuses_the_retry(tmp_path: Path) -> None:
    probe = make_rig(tmp_path / "probe", [_bad_gateway()])
    _stop(probe)
    held = Decimal(probe.records()[0]["reserved_usd"])
    rig = make_rig(tmp_path / "run", [_bad_gateway()], cap=str(held * Decimal("1.5")))
    assert _stop(rig).reason == "BudgetExhausted"
    first, refused = rig.records()
    assert first["cost_status"] == "unknown" and refused["error_class"] == "BudgetExhausted"
    assert (refused["reserved_usd"], refused["settled_usd"]) == ("0", "0")
    assert len(rig.adapter.sent) == 1


def test_a_failed_retry_stops_the_run_with_no_third_send(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [_bad_gateway(), _bad_gateway(), ok(read_identity(), gap_submit())])
    assert _stop(rig).reason == "ProviderServerError"
    assert len(rig.adapter.sent) == 2 and len(rig.records()) == 2


def test_a_retry_that_fails_with_a_known_charge_still_stops_the_run(tmp_path: Path) -> None:
    rig = make_rig(
        tmp_path,
        [_bad_gateway(), failed("sent_known", "ProviderRejected", 400), ok(gap_submit())],
    )
    assert _stop(rig).reason == "ProviderRejected"
    first, second = rig.records()
    assert (first["cost_status"], second["settled_usd"]) == ("unknown", "0")
    assert len(rig.adapter.sent) == 2


def test_a_402_on_the_retry_is_a_failed_retry_not_a_second_wait(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [_bad_gateway(), _credit(), ok(gap_submit())])
    assert _stop(rig).reason == "CreditExhausted402"
    assert rig.sleeps == [] and len(rig.adapter.sent) == 2 and len(rig.records()) == 2


def test_a_timeout_is_never_retried_and_leaves_the_run_stopped(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [failed("sent_unknown", "OverallTimeout", None), ok(gap_submit())])
    assert _stop(rig).reason == "OverallTimeout"
    (record,) = rig.records()
    assert (record["settled_usd"], record["cost_status"]) == (None, "unknown")
    assert record["http_status"] is None and len(rig.adapter.sent) == 1
    assert rig.budget.spent == Decimal(record["reserved_usd"])  # held and counted
    with pytest.raises(RunStopped):
        rig.budget.reserve("next-call", Decimal("0.001"), config_id=CONFIG)


@pytest.mark.parametrize("error_class", ["StreamCut", "IdleTimeout"])
def test_a_cut_stream_or_idle_timeout_with_no_usage_gets_the_one_retry(
    tmp_path: Path, error_class: str
) -> None:
    rig = make_rig(
        tmp_path,
        [failed("sent_unknown", error_class, None), ok(read_identity(), gap_submit())],
    )
    assert rig.loop.run()[-1]["status"] == "valid"
    assert len(rig.records()) == 2


def test_a_key_reflecting_reply_is_never_retried(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [failed("sent_unknown", "KeyReflected", 502), ok(gap_submit())])
    assert _stop(rig).reason == "KeyReflected" and len(rig.adapter.sent) == 1


def test_a_second_unknown_charge_in_the_run_is_not_retried(tmp_path: Path) -> None:
    """The run has one retry: the 502 after a retried 502 that then succeeded is final."""
    rig = make_rig(
        tmp_path,
        [
            _bad_gateway(),
            ok(tool_call("search_pack", query="identity")),
            _bad_gateway(),
            ok(read_identity(), gap_submit()),
        ],
    )
    assert _stop(rig).reason in {"ProviderServerError", "RunStopped"}
    assert len(rig.adapter.sent) == 3


def test_an_exception_out_of_complete_keeps_the_hold_and_stops(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [RuntimeError("the socket is gone")])
    assert _stop(rig).reason == "RuntimeError"
    (record,) = rig.records()
    assert (record["cost_status"], record["settled_usd"]) == ("unknown", None)
    assert record["error_class"] == "RuntimeError" and record["http_status"] is None
    assert rig.budget.spent == Decimal(record["reserved_usd"])
    with pytest.raises(RunStopped):
        rig.budget.reserve("next-call", Decimal("0.001"), config_id=CONFIG)


def test_recording_missing_is_a_recorded_call_and_a_stop(tmp_path: Path) -> None:
    empty = tmp_path / "recordings"
    empty.mkdir()
    rig = make_rig(tmp_path / "run", [], adapter=recorded_adapter(SPEC, empty))
    stopped = _stop(rig)
    assert stopped.reason == "RecordingMissing"
    (record,) = rig.records()
    assert record["error_class"] == "RecordingMissing" and record["cost_status"] == "unknown"
    digest = record["invocation_digest"]
    assert digest in stopped.detail  # a recording author reads the digest to write against
    assert (tmp_path / "run" / "store" / "owner-run-audit" / "invocations" / digest).is_file()


# ---------------------------------------------------------------- 402


def _credit() -> Any:
    return failed("sent_known", "CreditExhausted402", 402, retry_after=7)


def test_an_in_flight_402_waits_once_and_resends_on_a_new_reservation(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [_credit(), ok(read_identity(), gap_submit())])
    assert rig.loop.run()[-1]["status"] == "valid"
    assert rig.sleeps == [7]
    first, second = rig.records()
    assert (first["call_index"], second["call_index"]) == (0, 1)
    assert (first["settled_usd"], first["cost_status"]) == ("0", "computed")
    assert first["error_class"] == "CreditExhausted402" and first["http_status"] == 402
    assert len(_markers(tmp_path)) == 2
    assert rig.budget.spent == Decimal(second["settled_usd"])


def test_a_402_twice_is_credit_exhausted(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [_credit(), _credit(), ok(gap_submit())])
    assert _stop(rig).reason == "CreditExhausted"
    assert rig.sleeps == [7] and len(rig.records()) == 2 and len(rig.adapter.sent) == 2


# ---------------------------------------------------------------- the other failure kinds


def test_a_prompt_over_the_listed_context_is_refused_before_any_send(tmp_path: Path) -> None:
    def huge(binding: Any, spec: Any, issues: Any) -> Any:
        return prompt_for(binding, spec, ("x" * 300_000,))

    rig = make_rig(tmp_path, [ok(gap_submit())], prompts=huge)
    assert _stop(rig).reason == "ContextTooLong" and rig.adapter.sent == []
    (record,) = rig.records()
    assert record["error_class"] == "ContextTooLong" and record["settled_usd"] == "0"


@pytest.mark.parametrize("bound", [Decimal(0), Decimal(-1), Decimal("NaN")])
def test_a_bytes_per_token_bound_must_be_positive_and_finite(
    tmp_path: Path, bound: Decimal
) -> None:
    with pytest.raises(ValueError, match="bytes_per_token"):
        make_rig(tmp_path, [], bytes_per_token=bound)


def test_not_sent_releases_the_reservation(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [failed("not_sent", "KeyMissing", None, message="no key")])
    assert _stop(rig).reason == "KeyMissing"
    (record,) = rig.records()
    assert (record["reserved_usd"], record["settled_usd"]) == ("0", "0")
    assert (record["cost_status"], record["error_class"]) == ("computed", "KeyMissing")
    assert rig.budget.spent == 0 and rig.budget.reserved == 0 and rig.budget.unsettled == ()


def test_a_4xx_with_no_usage_settles_zero_and_stops(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [failed("sent_known", "ProviderRejected", 400)])
    assert _stop(rig).reason == "ProviderRejected"
    (record,) = rig.records()
    assert (record["settled_usd"], record["cost_status"]) == ("0", "computed")
    assert Decimal(record["reserved_usd"]) > 0 and record["http_status"] == 400
    assert rig.budget.spent == 0


def test_sent_usage_settles_from_the_usage_then_stops(tmp_path: Path) -> None:
    usage = Usage(input_tokens=1000, output_tokens=90000)
    rig = make_rig(
        tmp_path,
        [failed("sent_usage", "MalformedToolArguments", 200, usage=usage), ok(gap_submit())],
        cap="5",
        max_output=100_000,
    )
    assert _stop(rig).reason == "MalformedToolArguments"
    (record,) = rig.records()
    charge = Decimal("0.902")  # (1000 * 2.00 + 90000 * 10.00) per million, sol
    assert Decimal(record["settled_usd"]) == charge and record["cost_status"] == "computed"
    assert Decimal(record["reserved_usd"]) > charge
    assert (record["input_tokens"], record["output_tokens"]) == (1000, 90000)
    assert record["error_class"] == "MalformedToolArguments"
    assert rig.budget.spent == charge and rig.budget.reserved == 0  # released down to the actual
    assert len(rig.adapter.sent) == 1


def test_an_ok_reply_with_an_unknowable_charge_keeps_the_hold_and_stops(tmp_path: Path) -> None:
    spec = ModelSpec("deepseek-max", "openrouter", "deepseek/deepseek-v4.1-flash-1017", "max")
    live = ScriptedAdapter(
        [ok(read_identity(), gap_submit())],
        config_id=spec.config_id,
        ruling=Path("docs/rulings/live.md"),  # a live adapter: no usage.cost, no charge
    )
    rig = make_rig(tmp_path, [], adapter=live, spec=spec)
    assert _stop(rig).reason == "UnknownCharge"
    (record,) = rig.records()
    assert (record["cost_status"], record["settled_usd"]) == ("unknown", None)
    assert rig.budget.spent == Decimal(record["reserved_usd"])


def test_a_charge_above_the_reservation_is_recorded_in_full_and_stops(tmp_path: Path) -> None:
    usage = Usage(input_tokens=1000, output_tokens=5000)
    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit(), usage=usage)], max_output=10)
    assert _stop(rig).reason == "OverrunStop"
    (record,) = rig.records()
    assert Decimal(record["settled_usd"]) == Decimal("0.052")  # (1000 * 2 + 5000 * 10) per million
    assert Decimal(record["settled_usd"]) > Decimal(record["reserved_usd"])
    assert rig.budget.spent == Decimal("0.052")


def test_a_turn_with_no_tool_call_is_no_submit(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [ok(text="I will answer in prose.")])
    assert _stop(rig).reason == "NoSubmit"
    (record,) = rig.records()
    assert record["error_class"] == "NoSubmit" and record["tool_calls"] == []
    assert Decimal(record["settled_usd"]) == Decimal("0.004")  # it was sent and billed


# ---------------------------------------------------------------- raw before validation


def test_raw_is_archived_before_the_workflow_validates(tmp_path: Path) -> None:
    rig = make_rig(
        tmp_path,
        [ok(read_identity(), gap_submit())],
        fail_submit=RuntimeError("the workflow broke"),
    )
    assert _stop(rig).reason == "RuntimeError"
    (record,) = rig.records()
    digest = rig.adapter.sent[0].digest
    assert (rig.run_dir / "raw" / f"{digest}-0.json").is_file()
    assert record["error_class"] == "RuntimeError" and record["cost_status"] == "computed"
    assert record["settled_usd"] is not None  # the reply was received: its charge is settled
    assert [c["name"] for c in record["tool_calls"]] == ["read_pages", "submit_source_readiness"]


def test_a_failing_turn_redaction_dispatches_nothing_and_still_settles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(redactor: Redactor, value: Any) -> Any:
        raise ValueError("the redactor broke")

    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit())], taped=True)
    monkeypatch.setattr(loop_module, "redacted_turn", broken)
    assert _stop(rig).reason == "ValueError"
    assert "workflow.invoke" not in rig.tape and "workflow.submit_review" not in rig.tape
    assert rig.tape[-2:] == ["settle", "append"]
    (record,) = rig.records()
    assert record["error_class"] == "ValueError" and record["cost_status"] == "computed"
    assert Decimal(record["settled_usd"]) == Decimal("0.004") and record["tool_calls"] == []


# ---------------------------------------------------------------- repair (F2)


def _repair_rig(root: Path, tail: list[Any]) -> Any:
    script = [ok(read_identity(), read_financial(), ready_submit()), *tail]
    return make_rig(root, script, gap=False)


def _shape(rig: Any) -> list[tuple[str, int, int]]:
    return [(r["step_id"], r["attempt"], r["call_index"]) for r in rig.records()]


def test_an_invalid_submit_on_a_pending_attempt_repairs_the_same_step(tmp_path: Path) -> None:
    rig = _repair_rig(
        tmp_path,
        [ok(submit("source_context", "{}")), ok(submit("source_context", "{}")), ok(text="done")],
    )
    assert _stop(rig).reason == "NoSubmit"
    assert _shape(rig) == [
        ("source_readiness", 0, 0),
        ("source_context", 0, 0),
        ("source_context", 0, 1),  # same attempt, the next index
        ("source_context", 1, 0),  # attempt 0 finished invalid: attempt 1 starts over
    ]
    digests = [r["invocation_digest"] for r in rig.records()]
    assert digests[1] == digests[2] and len({digests[0], digests[1], digests[3]}) == 3
    sent: list[Sent] = rig.adapter.sent
    assert "REPAIR" not in sent[1].request.messages[-1].text
    assert "entities: Field required" in sent[2].request.messages[-1].text  # the issues
    assert "Step source_context, attempt 1" in sent[3].request.messages[-1].text
    assert (sent[2].call_index, sent[3].call_index) == (1, 0)


def test_a_refused_submit_keeps_the_digest_and_the_attempt(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [ok(gap_submit()), ok(read_identity(), gap_submit())])
    assert rig.loop.run()[-1]["status"] == "valid"
    assert _shape(rig) == [("source_readiness", 0, 0), ("source_readiness", 0, 1)]
    first, second = rig.records()
    assert first["invocation_digest"] == second["invocation_digest"]
    assert first["tool_calls"][0]["refusal_code"] == "refused"
    answer = rig.adapter.sent[1].request.messages[
        -1
    ]  # the refusal's issues go back as a tool result
    assert answer.role == "tool" and "Cited page not read" in answer.text


def test_the_repair_prompt_names_the_failing_step_within_an_attempt(tmp_path: Path) -> None:
    rig = _repair_rig(tmp_path, [ok(submit("source_context", "{}")), ok(text="done")])
    _stop(rig)
    snapshot = rig.execution.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-1")
    repair = repair_prompt(snapshot, attempt, "source_context")
    assert (repair.scope, repair.failing_step) == ("failing-step", "source_context")
    assert repair.issues == ("entities: Field required", "sources: Field required")
    assert repair.to_record() == {
        "scope": "failing-step",
        "failing_step": "source_context",
        "issue_count": 2,
    }


def test_the_repair_prompt_scopes_to_none_for_another_step(tmp_path: Path) -> None:
    rig = _repair_rig(
        tmp_path,
        [ok(submit("source_context", "{}")), ok(submit("source_context", "{}")), ok(text="done")],
    )
    _stop(rig)
    snapshot = rig.execution.read()
    second = [a for a in snapshot.attempts if a.module_id == "CP-1"][-1]
    assert second.number == 1 and second.repair_of is not None
    assert repair_prompt(snapshot, second, "source_context").scope == "failing-step"
    other = repair_prompt(snapshot, second, "financials")
    assert (other.scope, other.failing_step, other.issues) == ("none", "source_context", ())


def test_the_repair_prompt_carries_the_module_issues_when_no_step_failed(tmp_path: Path) -> None:
    workflow, pack = owner_start(tmp_path)
    store = Execution(tmp_path / "store")
    store.interrupt(store.read().attempts[0].ticket_id, "operator stop")
    store.begin("CP-0")
    snapshot = store.read()
    repair = repair_prompt(snapshot, snapshot.attempts[-1], "source_readiness")
    assert (repair.scope, repair.failing_step) == ("module", None)
    assert repair.issues == ("Interrupted: operator stop",)
    first = repair_prompt(snapshot, snapshot.attempts[0], "source_readiness")
    assert (first.scope, first.issues) == ("none", ())
    assert workflow is not None and pack is not None


# ---------------------------------------------------------------- call limit, tool results


def test_the_seventeenth_call_of_a_kind_in_a_step_is_the_call_limit(tmp_path: Path) -> None:
    searches = [tool_call("search_pack", query="identity") for _ in range(17)]
    rig = make_rig(tmp_path, [ok(*searches)])
    assert _stop(rig).reason == "CallLimit"
    (record,) = rig.records()
    assert record["error_class"] == "CallLimit" and len(record["tool_calls"]) == 17
    assert record["tool_calls"][15]["refusal_code"] is None
    assert record["tool_calls"][16]["refusal_code"] == "CallLimit"


def test_a_not_permitted_read_inputs_is_returned_to_the_model(tmp_path: Path) -> None:
    rig = make_rig(
        tmp_path, [ok(tool_call("read_inputs")), ok(read_identity(), gap_submit())]
    )  # source_readiness has no inputs to read
    assert rig.loop.run()[-1]["status"] == "valid"
    first, _ = rig.records()
    assert first["error_class"] is None
    assert first["tool_calls"][0]["refusal_code"] == "not_permitted"
    returned = rig.adapter.sent[1].request.messages[-1]
    assert returned.role == "tool" and "not_permitted" in returned.text


def test_tool_call_records_hash_the_arguments_the_workflow_received(tmp_path: Path) -> None:
    call = read_identity()
    rig = make_rig(tmp_path, [ok(call, gap_submit())])
    rig.loop.run()
    (record,) = rig.records()
    read, send = record["tool_calls"]
    assert read["arguments_sha256"] == arguments_sha256(call.arguments)
    assert read["result_bytes"] > 0 and read["refusal_code"] is None
    assert record["submit_sha256"] is not None and send["name"] == "submit_source_readiness"


def test_read_inputs_is_offered_when_the_step_has_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fw, "start", owner_start)
    workflow, pack = fw.before_financials(tmp_path)
    fw.financial_reads(workflow)
    assert workflow.submit_review(json.dumps(fw.financials(pack)))["status"] == "valid"
    assert workflow.spec.step_id == "narrative" and workflow.spec.inputs == "projection"
    rig = make_rig(
        tmp_path,
        [ok(tool_call("read_inputs")), ok(text="done")],
        workflow=workflow,
        pack=pack,
        bytes_per_token=Decimal(3),  # a measured bound; the default of 1 refuses a 272 KB prompt
    )
    assert _stop(rig).reason == "NoSubmit"
    assert "read_inputs" in [t.name for t in rig.adapter.sent[0].request.tools]
    body = rig.adapter.sent[1].request.messages[-1]
    assert body.role == "tool" and len(body.text) > 100
    (record,) = [r for r in rig.records() if r["step_id"] == "narrative"][:1]
    assert record["tool_calls"][0]["refusal_code"] is None


def test_read_inputs_tool_takes_no_arguments() -> None:
    tool = read_inputs_tool()
    assert tool.name == "read_inputs" and tool.parameters["additionalProperties"] is False


def test_the_contract_prompt_and_tools_come_from_the_live_registry(tmp_path: Path) -> None:
    workflow, pack = owner_start(tmp_path, True)
    messages = contract_prompt_for(pack)(workflow.binding, workflow.spec, ("fix the date",))
    tools = contract_tools_for(workflow.binding, workflow.spec)
    assert [m.role for m in messages] == ["system", "user"]
    assert "prior-validation-issues" in messages[1].text and "fix the date" in messages[1].text
    assert [t.name for t in tools] == ["search_pack", "read_pages", "submit_source_readiness"]


# ---------------------------------------------------------------- redaction (F3, F4)


def test_a_key_in_a_tool_argument_reaches_no_audit_file(tmp_path: Path) -> None:
    body = b'{"arguments":"' + SECRET.encode() + b'"}'
    rig = make_rig(
        tmp_path,
        [ok(tool_call("search_pack", query=SECRET), read_identity(), gap_submit(), raw=body)],
    )
    assert rig.loop.run()[-1]["status"] == "valid"
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files and not [p for p in files if SECRET.encode() in p.read_bytes()]
    calls = list((tmp_path / "store" / "owner-run-audit" / "calls").iterdir())
    assert any(b"[redacted]" in p.read_bytes() for p in calls)  # the call was made, redacted
    assert (tmp_path / "run" / "raw").is_dir() and (tmp_path / "run" / "calls.jsonl").is_file()


def test_a_key_in_the_prompt_is_not_sent(tmp_path: Path) -> None:
    def prompt(binding: Any, spec: Any, issues: Any) -> Any:
        return prompt_for(binding, spec, (f"key {SECRET}",))

    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit())], prompts=prompt)
    rig.loop.run()
    sent = rig.adapter.sent[0].request
    assert SECRET not in "".join(m.text for m in sent.messages)
    assert "[redacted]" in sent.messages[-1].text


def test_a_stop_chains_no_raw_exception(tmp_path: Path) -> None:
    planted = "planted-opaque-value"

    class ProviderBoom(Exception):
        pass

    try:
        raise ProviderBoom("provider failed") from ValueError(planted)
    except ProviderBoom as error:
        boom = error
    rig = make_rig(tmp_path, [boom], redactor=Redactor([planted]))
    stopped = _stop(rig)
    assert stopped.reason == "ProviderBoom"
    assert stopped.__cause__ is None and stopped.__suppress_context__
    assert planted not in "".join(traceback.format_exception(stopped))
    assert planted not in (tmp_path / "run" / "calls.jsonl").read_text()


# ---------------------------------------------------------------- timing


def test_first_byte_at_comes_from_the_adapter_between_start_and_finish(tmp_path: Path) -> None:
    rig = make_rig(
        tmp_path,
        [ok(read_identity(), gap_submit(), started=100.0, first_byte=100.2, finished=101.0)],
    )
    rig.loop.run()
    (record,) = rig.records()
    started, first, finished = (
        datetime.fromisoformat(record[k]) for k in ("started_at", "first_byte_at", "finished_at")
    )
    assert started.timestamp() == 100.0 and first.timestamp() == pytest.approx(100.2)
    assert started <= first <= finished and finished.timestamp() == 101.0


def test_an_unreported_first_byte_stays_unreported(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, [ok(read_identity(), gap_submit(), first_byte=None)])
    rig.loop.run()
    assert rig.records()[0]["first_byte_at"] is None
