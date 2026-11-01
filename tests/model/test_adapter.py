"""Recorded and live adapters. Fake transports only; no network, no real key."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import pytest

from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    AdapterReply,
    LiveAdapter,
    LivePauseInForce,
    RecordedAdapter,
    RecordingConflict,
    RecordingError,
    RecordingMissing,
    live_adapter,
    recorded_adapter,
)
from deploy_workflow.model.transport import InsecureUrl, Request, Response, TransportError
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ToolCall,
    Turn,
    TurnRequest,
    Usage,
    turn_to_json,
)

SPEC = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
DIGEST = "a" * 64
FAKE_KEY = "sk-test-fake-value-0123456789"
RULING_TEXT = "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: sol-medium\n"


def request() -> TurnRequest:
    return TurnRequest((Message("user", "hi"),), (), 100, "medium")


def one_call_turn() -> Turn:
    return Turn(
        "",
        (ToolCall("c1", "read_file", {"path": "a.txt", "n": Decimal("1.50")}),),
        Usage(input_tokens=5, output_tokens=3),
        "tool_use",
        "gpt-6.1-sol",
        "r1",
        200,
    )


def line(digest: str, index: int, response: object) -> str:
    return json.dumps(
        {"invocation_digest": digest, "call_index": index, "response": response}, default=str
    )


def write(path: Path, *lines: str) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def complete(
    adapter: RecordedAdapter | LiveAdapter, digest: str = DIGEST, index: int = 0
) -> AdapterReply:
    return adapter.complete(
        request(), invocation_digest=digest, call_index=index, reservation_id="r"
    )


# ------------------------------------------------------------------ recorded


def test_recorded_returns_the_turn(tmp_path: Path) -> None:
    turn = one_call_turn()
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(turn)))
    adapter = recorded_adapter(SPEC, tmp_path)
    assert adapter.ruling is None and adapter.config_id == "sol-medium"
    reply = complete(adapter)
    assert reply.kind == "ok" and reply.turn == turn
    assert reply.http_status == 200 and reply.usage == turn.usage
    assert reply.billed_usd is None


def test_recorded_missing_key_is_never_defaulted(tmp_path: Path) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())))
    adapter = recorded_adapter(SPEC, tmp_path)
    with pytest.raises(RecordingMissing):
        complete(adapter, index=1)
    with pytest.raises(RecordingMissing):
        complete(adapter, digest="b" * 64)


def test_recorded_reads_every_jsonl_under_the_directory(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    write(tmp_path / "one.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())))
    write(tmp_path / "sub" / "two.jsonl", line(DIGEST, 1, turn_to_json(one_call_turn())))
    adapter = recorded_adapter(SPEC, tmp_path)
    assert complete(adapter, index=1).kind == "ok"


def test_recorded_conflicting_duplicates(tmp_path: Path) -> None:
    other = turn_to_json(Turn("x", (), Usage(), "end", None, None, 200))
    write(
        tmp_path / "rec.jsonl",
        line(DIGEST, 0, turn_to_json(one_call_turn())),
        line(DIGEST, 0, other),
    )
    with pytest.raises(RecordingConflict):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_identical_duplicates_are_fine(tmp_path: Path) -> None:
    same = line(DIGEST, 0, turn_to_json(one_call_turn()))
    write(tmp_path / "a.jsonl", same)
    write(tmp_path / "b.jsonl", same)
    assert complete(recorded_adapter(SPEC, tmp_path)).kind == "ok"


def test_recorded_bad_json_line_names_the_line(tmp_path: Path) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())), "{not json")
    with pytest.raises(RecordingError, match="line 2"):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_response_without_http_status(tmp_path: Path) -> None:
    body = turn_to_json(one_call_turn())
    del body["http_status"]
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, body))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_old_format_arguments_refused(tmp_path: Path) -> None:
    body = turn_to_json(one_call_turn())
    body["tool_calls"][0]["arguments"] = {"path": "a.txt"}
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, body))
    with pytest.raises(RecordingError):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_bad_envelope(tmp_path: Path) -> None:
    write(tmp_path / "rec.jsonl", json.dumps({"invocation_digest": DIGEST, "call_index": 0}))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)
    write(tmp_path / "rec.jsonl", line(DIGEST, True, turn_to_json(one_call_turn())))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(RecordingError):
        recorded_adapter(SPEC, tmp_path / "nope")


def test_recorded_sent_usage_round_trips(tmp_path: Path) -> None:
    usage = {
        "input_tokens": 7,
        "cached_read_tokens": None,
        "cache_write_tokens": None,
        "cache_write_5m_tokens": None,
        "cache_write_1h_tokens": None,
        "output_tokens": 9,
        "reasoning_tokens": 2,
    }
    response = {
        "kind": "sent_usage",
        "error_class": "MalformedToolArguments",
        "http_status": 200,
        "usage": usage,
        "billed_usd": "0.0123",
    }
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, response))
    reply = complete(recorded_adapter(SPEC, tmp_path))
    assert reply.kind == "sent_usage" and reply.turn is None
    assert reply.usage == Usage(input_tokens=7, output_tokens=9, reasoning_tokens=2)
    assert reply.billed_usd == Decimal("0.0123")
    assert reply.error_class == "MalformedToolArguments" and reply.http_status == 200


def test_recorded_error_shapes_are_validated(tmp_path: Path) -> None:
    good = {"kind": "sent_known", "error_class": "ProviderRejected", "http_status": 400}
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, good))
    reply = complete(recorded_adapter(SPEC, tmp_path))
    assert reply.kind == "sent_known" and reply.usage is None
    bad_cases = [
        {"kind": "sent_known", "error_class": "X"},  # no http_status
        {**good, "extra": 1},
        {**good, "kind": "ok"},
        {**good, "kind": "sent_usage"},  # sent_usage needs usage
        {**good, "usage": {"input_tokens": 1}},  # usage on a non-usage kind
        {**good, "error_class": 3},
        {**good, "http_status": True},
    ]
    for bad in bad_cases:
        write(tmp_path / "rec.jsonl", line(DIGEST, 0, bad))
        with pytest.raises(RecordingError):
            recorded_adapter(SPEC, tmp_path)


def test_recorded_adapter_reads_no_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    class Trap(dict[str, str]):
        touched: ClassVar[list[str]] = []

        def __getitem__(self, key: str) -> str:
            self.touched.append(key)
            raise AssertionError("environment touched")

        def get(self, key: str, default: object = None) -> str:
            self.touched.append(key)
            raise AssertionError("environment touched")

    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())))
    trap = Trap()
    with monkeypatch.context() as scoped:
        scoped.setattr(os, "environ", trap)
        complete(recorded_adapter(SPEC, tmp_path))
    assert trap.touched == []


# ------------------------------------------------------------------ live


@pytest.fixture
def live_ruling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "rulings"
    root.mkdir()
    path = root / "lift.md"
    path.write_text(RULING_TEXT, encoding="utf-8")
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", root)
    return path


class FakeTransport:
    def __init__(self, response: Response | None = None, error: TransportError | None = None):
        self.response, self.error = response, error
        self.requests: list[Request] = []

    def __call__(self, req: Request) -> Response:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def test_live_empty_key_is_not_sent_and_names_the_variable(live_ruling: Path) -> None:
    fake = FakeTransport(Response(200, b"{}"))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": ""})
    reply = complete(adapter)
    assert reply.kind == "not_sent" and reply.error_class == "KeyMissing"
    assert reply.message is not None and "OPENAI_API_KEY" in reply.message
    assert "sk-" not in repr(reply)
    assert fake.requests == []


def test_live_redacts_every_provider_key_by_exact_value(live_ruling: Path) -> None:
    other = "plainvalue-anthropic-key-9876"  # no key shape: only an exact-value match can catch it
    env = {"OPENAI_API_KEY": FAKE_KEY, "ANTHROPIC_API_KEY": other}
    fake = FakeTransport(Response(500, f"oops {other}".encode()))
    reply = complete(live_adapter(SPEC, live_ruling, transport=fake, environ=env))
    assert reply.raw is not None and other.encode() not in reply.raw
    assert other not in repr(reply) and FAKE_KEY not in repr(reply)


def test_live_absent_key_is_not_sent(live_ruling: Path) -> None:
    reply = complete(live_adapter(SPEC, live_ruling, transport=FakeTransport(), environ={}))
    assert reply.kind == "not_sent" and reply.error_class == "KeyMissing"


def test_live_502_is_one_call_and_sent_unknown(live_ruling: Path) -> None:
    fake = FakeTransport(Response(502, b"<html>bad gateway</html>"))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert len(fake.requests) == 1
    assert reply.kind == "sent_unknown" and reply.http_status == 502
    assert reply.error_class == "ProviderServerError"
    assert reply.retry_after is None and reply.turn is None


def test_live_402_carries_retry_after(live_ruling: Path) -> None:
    body = b'{"error":{"message":"no credit","type":"billing"}}'
    fake = FakeTransport(Response(402, body, {"retry-after": "30"}))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert len(fake.requests) == 1
    assert reply.kind == "sent_known" and reply.error_class == "CreditExhausted402"
    assert reply.retry_after == 30 and reply.http_status == 402


def test_live_key_is_sent_only_in_the_header(live_ruling: Path) -> None:
    ok = (
        b'{"id":"r1","model":"gpt-6.1-sol","status":"completed","output":[{"type":"message",'
        b'"content":[{"type":"output_text","text":"hi"}]}],"usage":{"input_tokens":5,"output_tokens":3}}'
    )
    fake = FakeTransport(Response(200, ok))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert reply.kind == "ok" and reply.turn is not None and reply.turn.text == "hi"
    assert reply.usage == Usage(input_tokens=5, output_tokens=3)
    assert fake.requests[0].headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert FAKE_KEY.encode() not in fake.requests[0].body
    assert reply.started_at is not None and reply.finished_at is not None
    assert reply.started_at <= reply.finished_at


def test_live_transport_error_is_classified_and_redacted(live_ruling: Path) -> None:
    fake = FakeTransport(error=TransportError("boom", FAKE_KEY.encode()))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert len(fake.requests) == 1
    assert reply.kind == "sent_unknown" and reply.error_class == "TransportError"
    assert reply.raw is not None and FAKE_KEY.encode() not in reply.raw


def test_live_reflected_key_is_redacted_in_raw(live_ruling: Path) -> None:
    fake = FakeTransport(Response(500, f"oops {FAKE_KEY}".encode()))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert reply.raw is not None and FAKE_KEY.encode() not in reply.raw
    assert reply.message is not None and FAKE_KEY not in reply.message


def test_live_refused_request_is_not_sent(live_ruling: Path) -> None:
    fake = FakeTransport(Response(200, b"{}"))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    too_big = TurnRequest((Message("user", "hi"),), (), 10**9, "medium")
    reply = adapter.complete(too_big, invocation_digest=DIGEST, call_index=0, reservation_id="r")
    assert reply.kind == "not_sent" and reply.error_class == "MaxOutputTooLarge"
    assert fake.requests == []


def test_adapter_reply_ok_needs_a_turn() -> None:
    with pytest.raises(ValueError):
        AdapterReply("ok", None, None, 200, None, None, None, None)


# ------------------------------------------------------------------ fix round 1


def test_live_adapter_runs_the_gate_in_its_constructor(live_ruling: Path, tmp_path: Path) -> None:
    fake = FakeTransport(Response(200, b"{}"))
    with pytest.raises(LivePauseInForce):
        LiveAdapter(SPEC, tmp_path / "missing.md", fake, {"OPENAI_API_KEY": FAKE_KEY})
    bad = live_ruling.parent / "bad.md"
    bad.write_text(RULING_TEXT.replace("by: user", "by: codex"), encoding="utf-8")
    with pytest.raises(LivePauseInForce):
        LiveAdapter(SPEC, bad, fake, {"OPENAI_API_KEY": FAKE_KEY})
    assert fake.requests == []


def test_live_adapter_ruling_and_gate_are_read_only(live_ruling: Path) -> None:
    adapter = LiveAdapter(SPEC, live_ruling, FakeTransport(), {})
    assert adapter.ruling == live_ruling and adapter.gate.path == live_ruling.resolve()
    with pytest.raises(AttributeError):
        adapter.ruling = None  # type: ignore[misc]
    with pytest.raises(AttributeError):
        adapter.gate = adapter.gate  # type: ignore[misc]


def test_live_json_escaped_key_never_reaches_raw(live_ruling: Path) -> None:
    escaped = FAKE_KEY.replace("-", "\\u002d", 1)
    body = (
        '{"id":"r","model":"m","status":"completed","output":[{"type":"message","content":'
        '[{"type":"output_text","text":"' + escaped + '"}]}],'
        '"usage":{"input_tokens":1,"output_tokens":1}}'
    ).encode()
    adapter = live_adapter(
        SPEC,
        live_ruling,
        transport=FakeTransport(Response(200, body)),
        environ={"OPENAI_API_KEY": FAKE_KEY},
    )
    reply = complete(adapter)
    assert reply.error_class == "KeyReflected"
    assert reply.raw == b'"[redacted]"'


def test_live_sse_split_key_never_reaches_raw(live_ruling: Path) -> None:
    key = "sk-ant-" + "W" * 40
    spec = ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
    live_ruling.write_text(RULING_TEXT.replace("sol-medium", "opus-medium"), encoding="utf-8")
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {"id": "m1", "model": "x", "usage": {"input_tokens": 1}},
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": key[:5]},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": key[5:]},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 2},
        },
        {"type": "message_stop"},
    ]
    sse = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
    adapter = live_adapter(
        spec,
        live_ruling,
        transport=FakeTransport(Response(200, sse)),
        environ={"ANTHROPIC_API_KEY": key},
    )
    reply = complete(adapter)
    assert reply.error_class == "KeyReflected" and reply.raw == b'"[redacted]"'


def test_live_bad_tool_arguments_is_sent_usage_with_its_usage(live_ruling: Path) -> None:
    body = (
        b'{"id":"r","model":"gpt-6.1-sol","status":"completed","output":[{"type":"function_call",'
        b'"call_id":"c1","name":"t","arguments":"[1]"}],'
        b'"usage":{"input_tokens":5,"output_tokens":3}}'
    )
    adapter = live_adapter(
        SPEC,
        live_ruling,
        transport=FakeTransport(Response(200, body)),
        environ={"OPENAI_API_KEY": FAKE_KEY},
    )
    reply = complete(adapter)
    assert reply.kind == "sent_usage" and reply.error_class == "MalformedToolArguments"
    assert reply.usage == Usage(input_tokens=5, output_tokens=3) and reply.turn is None


def test_live_insecure_url_is_not_sent(live_ruling: Path) -> None:
    fake = FakeTransport(error=InsecureUrl("only https endpoints are permitted"))
    adapter = live_adapter(SPEC, live_ruling, transport=fake, environ={"OPENAI_API_KEY": FAKE_KEY})
    reply = complete(adapter)
    assert reply.kind == "not_sent" and reply.error_class == "InsecureUrl"


def _error(**over: object) -> dict[str, object]:
    return {"kind": "sent_unknown", "error_class": "X", "http_status": 502, **over}


@pytest.mark.parametrize(
    "response",
    [
        _error(kind="sent_known", http_status=502),
        _error(kind="sent_known", http_status=None),
        _error(kind="sent_known", http_status=200),
        _error(http_status="502"),
        {
            **_error(kind="sent_usage", http_status=None),
            "usage": {f: None for f in Usage.__dataclass_fields__},
        },
    ],
)
def test_recorded_error_status_rules(tmp_path: Path, response: object) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, response))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


@pytest.mark.parametrize("kind", ["not_sent", "sent_unknown"])
def test_recorded_null_status_allowed_for_unsent_or_unknown(tmp_path: Path, kind: str) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, _error(kind=kind, http_status=None)))
    reply = complete(recorded_adapter(SPEC, tmp_path))
    assert reply.kind == kind and reply.http_status is None


@pytest.mark.parametrize("status", [502, 500, 199, 300, 0, -1])
def test_recorded_ok_needs_a_2xx_status(tmp_path: Path, status: int) -> None:
    body = turn_to_json(one_call_turn())
    body["http_status"] = status
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, body))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_duplicate_object_keys_refused(tmp_path: Path) -> None:
    text = (
        '{"invocation_digest":"' + DIGEST + '","call_index":0,"response":'
        '{"kind":"sent_unknown","error_class":"X","http_status":502,"kind":"sent_known"}}'
    )
    write(tmp_path / "rec.jsonl", text)
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_conflict_distinguishes_true_from_one(tmp_path: Path) -> None:
    base = turn_to_json(one_call_turn())
    as_one = line(
        DIGEST, 0, {**base, "provider_blocks": [{"provider": "anthropic", "data": {"n": 1}}]}
    )
    as_true = as_one.replace('"n": 1', '"n": true')
    assert as_one != as_true
    write(tmp_path / "rec.jsonl", as_one, as_true)
    with pytest.raises(RecordingConflict):
        recorded_adapter(SPEC, tmp_path)


def test_recorded_refuses_bad_envelope_values(tmp_path: Path) -> None:
    good = turn_to_json(one_call_turn())
    for digest, index in ((DIGEST, -1), ("", 0)):
        write(tmp_path / "rec.jsonl", line(digest, index, good))
        with pytest.raises(RecordingError, match="line 1"):
            recorded_adapter(SPEC, tmp_path)
    bad = {"kind": "sent_known", "error_class": "X", "http_status": 400, "billed_usd": "-0.01"}
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, bad))
    with pytest.raises(RecordingError, match="line 1"):
        recorded_adapter(SPEC, tmp_path)


def test_recording_missing_carries_its_key(tmp_path: Path) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())))
    with pytest.raises(RecordingMissing) as caught:
        complete(recorded_adapter(SPEC, tmp_path), digest="b" * 64, index=3)
    assert caught.value.digest == "b" * 64 and caught.value.call_index == 3


def test_recorded_deeply_nested_line_is_a_recording_error(tmp_path: Path) -> None:
    write(tmp_path / "rec.jsonl", line(DIGEST, 0, turn_to_json(one_call_turn())), "[" * 100_000)
    with pytest.raises(RecordingError, match="line 2"):
        recorded_adapter(SPEC, tmp_path)
