"""R3 key redaction: synthetic values only, no environment read."""

import gc
import io
import logging
import re

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from deploy_workflow.model.redact import KEY_PATTERN, Redactor


def test_exact_value_redacted() -> None:
    assert (
        Redactor(["abc123XYZ"]).text("401 bad key abc123XYZ here") == "401 bad key [redacted] here"
    )


def test_empty_exact_value_is_ignored() -> None:
    assert Redactor([""]).text("anything") == "anything"


def test_longest_exact_value_first() -> None:
    out = Redactor(["abcd", "abcdefgh"]).text("k=abcdefgh")
    assert out == "k=[redacted]"


def test_regex_only_redactor_catches_known_shapes() -> None:
    r = Redactor()
    assert r.text("x sk-or-v1-abcdef123 y") == "x [redacted] y"
    assert r.text("sk-ant-api03-ABCDEF") == "[redacted]"
    assert r.text("sk-proj-ABCDEF") == "[redacted]"
    assert r.text("sk-" + "a" * 20) == "[redacted]"
    assert r.text("sk-" + "a" * 19) == "sk-" + "a" * 19
    assert r.text("risk-or-x") == "risk-or-x"


def test_chain_cause_redacted() -> None:
    try:
        raise RuntimeError("outer") from ValueError("inner sk-ant-SECRETVAL1")
    except RuntimeError as exc:
        out = Redactor().exception(exc)
    assert "SECRETVAL1" not in out
    assert "inner" in out and "outer" in out


def test_chain_context_redacted() -> None:
    try:
        try:
            raise ValueError("inner sk-ant-SECRETVAL1")
        except ValueError:
            raise RuntimeError("outer")  # implicit __context__
    except RuntimeError as exc:
        out = Redactor().exception(exc)
    assert "SECRETVAL1" not in out
    assert "inner" in out


def test_cause_cycle_terminates() -> None:
    a = ValueError("a sk-ant-SECRETVAL1")
    b = RuntimeError("b")
    a.__cause__ = b
    b.__cause__ = a
    out = Redactor().exception(a)
    assert "SECRETVAL1" not in out


def test_exact_value_in_exception_redacted() -> None:
    out = Redactor(["abc123XYZ"]).exception(KeyError("abc123XYZ"))
    assert "abc123XYZ" not in out


def test_json_value_keys_and_values() -> None:
    out = Redactor(["abc123XYZ"]).json_value({"a": ["k=abc123XYZ"], "abc123XYZ": 1})
    assert out == {"a": ["k=[redacted]"], "[redacted]": 1}


def test_json_value_keeps_non_strings_and_colliding_keys() -> None:
    r = Redactor(["abc123XYZ", "def456UVW"])
    out = r.json_value({"abc123XYZ": 1, "def456UVW": 2, "n": None, "t": True, "f": 1.5})
    assert len(out) == 5
    assert out["n"] is None and out["t"] is True and out["f"] == 1.5
    assert sorted(v for k, v in out.items() if k.startswith("[redacted]")) == [1, 2]


def test_bytes_redacted() -> None:
    r = Redactor(["abc123XYZ"])
    assert r.bytes_(b"key abc123XYZ and sk-or-v1-abcdef123") == b"key [redacted] and [redacted]"


def test_from_environ_uses_only_given_mapping() -> None:
    env = {
        "OPENAI_API_KEY": "synthetic-openai-VALUE",
        "ANTHROPIC_API_KEY": "",
        "OPENROUTER_API_KEY": "synthetic-router-VALUE",
        "OTHER": "synthetic-other-VALUE",
    }
    r = Redactor.from_environ(env)
    assert r.text("synthetic-openai-VALUE synthetic-router-VALUE synthetic-other-VALUE") == (
        "[redacted] [redacted] synthetic-other-VALUE"
    )
    assert Redactor.from_environ({}).text("x") == "x"


def test_stream_redacts_line() -> None:
    buf = io.StringIO()
    stream = Redactor(["abc123XYZ"]).redact_stream(buf)
    stream.write("key abc123XYZ\n")
    assert "abc123XYZ" not in buf.getvalue()
    assert buf.getvalue() == "key [redacted]\n"


def test_stream_redacts_value_split_across_writes_and_flush() -> None:
    buf = io.StringIO()
    stream = Redactor(["abc123XYZ"]).redact_stream(buf)
    stream.write("key abc1")
    stream.write("23XYZ tail")
    stream.flush()
    assert buf.getvalue() == "key [redacted] "
    stream.close()
    assert buf.getvalue() == "key [redacted] tail"


@given(t=st.text(), v=st.text(min_size=4))
def test_property_value_never_survives(t: str, v: str) -> None:
    if "[" in v or "]" in v or v in "[redacted]":
        return
    assert v not in Redactor([v]).text(t)
    assert v not in Redactor([v]).text(t + v + t)


def test_stream_flush_holds_regex_key_split_by_flush() -> None:
    buf = io.StringIO()
    stream = Redactor().redact_stream(buf)
    for chunk in ["The key is ", "sk-or-v1-", "TESTONLY", "abcdef0123", "456789", "\n"]:
        print(chunk, end="", file=stream, flush=True)
    assert buf.getvalue() == "The key is [redacted]\n"


def test_stream_flush_holds_exact_value_prefix() -> None:
    buf = io.StringIO()
    stream = Redactor(["abc 123 XYZ"]).redact_stream(buf)
    stream.write("key abc 12")
    stream.flush()
    assert "abc" not in buf.getvalue()
    stream.write("3 XYZ\n")
    assert buf.getvalue() == "key [redacted]\n"


def test_stream_flush_emits_safe_text_and_close_emits_held() -> None:
    buf = io.StringIO()
    stream = Redactor().redact_stream(buf)
    stream.write("hello world, sk-or")
    stream.flush()
    assert buf.getvalue() == "hello world, "
    stream.write("-v1-TESTONLYabcdef")
    stream.close()
    assert buf.getvalue() == "hello world, [redacted]"


def test_overlapping_exact_values_leave_no_fragment() -> None:
    out = Redactor(["TESTONLYaaaa", "aaaaSECRETTAILzzzzzzzz"]).text(
        "x TESTONLYaaaaSECRETTAILzzzzzzzz y"
    )
    assert out == "x [redacted] y"


def test_exact_inside_regex_key_redacts_whole_key() -> None:
    out = Redactor(["TESTONLYmid0"]).text("auth sk-or-v1-TESTONLYmid0KEYSUFFIXabc123 z")
    assert out == "auth [redacted] z"
    assert (
        Redactor(["TESTONLYmid0"]).bytes_(b"sk-or-v1-TESTONLYmid0KEYSUFFIXabc123") == b"[redacted]"
    )


def test_json_value_non_json_types_are_redacted() -> None:
    r = Redactor(["abc123XYZ"])
    assert r.json_value({"b": b"k abc123XYZ"}) == {"b": b"k [redacted]"}
    assert r.json_value({b"abc123XYZ": 1}) == {b"[redacted]": 1}
    assert r.json_value({("abc123XYZ", "q"): 1}) == {("[redacted]", "q"): 1}
    assert r.json_value({"s": {"abc123XYZ", "ok"}}) == {"s": {"[redacted]", "ok"}}
    assert r.json_value(("abc123XYZ", b"abc123XYZ")) == ["[redacted]", b"[redacted]"]


def test_flush_never_splits_exact_value_with_non_key_char() -> None:
    buf = io.StringIO()
    stream = Redactor(["TESTONLY.dot"]).redact_stream(buf)
    stream.write("a TESTONLY.dotmore")
    stream.flush()
    stream.write("\n")
    assert "TESTONLY" not in buf.getvalue()
    assert buf.getvalue() == "a [redacted]more\n"


def test_flush_never_splits_exact_value_starting_with_non_key_char() -> None:
    buf = io.StringIO()
    stream = Redactor(["x.TESTONLYval"]).redact_stream(buf)
    stream.write("k x.TESTONLYvalmore")
    stream.flush()
    stream.write("\n")
    assert "TESTONLY" not in buf.getvalue()


def test_garbage_collected_stream_emits_redacted_tail() -> None:
    buf = io.StringIO()
    stream = Redactor().redact_stream(buf)
    stream.write("tail sk-or-v1-TESTONLYabcdef")
    stream.flush()
    del stream
    gc.collect()
    assert buf.getvalue() == "tail [redacted]"


def test_garbage_collected_stream_with_closed_target_logs_char_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    buf = io.StringIO()
    stream = Redactor().redact_stream(buf)
    stream.write("fatal: sk-or-v1-TESTONLYabcdef")
    buf.close()
    with caplog.at_level(logging.WARNING, logger="deploy_workflow.model.redact"):
        del stream
        gc.collect()
    assert "TESTONLY" not in caplog.text
    assert "30 chars" in caplog.text


def test_write_after_close_raises() -> None:
    buf = io.StringIO()
    stream = Redactor().redact_stream(buf)
    stream.close()
    with pytest.raises(ValueError):
        stream.write("late")


def test_json_value_redacts_bytearray() -> None:
    out = Redactor(["abc123XYZ"]).json_value({"b": bytearray(b"k abc123XYZ")})
    assert bytes(out["b"]) == b"k [redacted]"


def test_flush_cost_stays_linear_in_held_text() -> None:
    import time

    for values, text in ((["a.a"], "a." * 8000), ([], "a" * 40000 + ".")):
        stream = Redactor(values).redact_stream(io.StringIO())
        stream.write(text)
        started = time.perf_counter()
        stream.flush()
        assert time.perf_counter() - started < 1.0


GLUED = "sk-proj-QQQQQQFAKEKEY"


@pytest.mark.parametrize(
    "text",
    [
        "key_" + GLUED,
        "401 key_" + GLUED + " bad",
        "pre_" + GLUED + "_post",
        '{"error": "' + GLUED + '"}',
        '{"k":"x_' + GLUED + '"}',
        "q=%20" + GLUED,
        "a=" + GLUED,
        GLUED,
        "x-" + GLUED,
        "x\n" + GLUED,
        "q=%2F" + GLUED,
        "q=%3D" + GLUED,
    ],
)
def test_glued_embedded_quoted_encoded_and_leading_keys_redacted(text: str) -> None:
    assert "QQQQQQ" not in Redactor().text(text)
    assert b"QQQQQQ" not in Redactor().bytes_(text.encode())
    assert not KEY_PATTERN.search(Redactor().text(text))


def test_word_internal_sk_is_not_over_redacted() -> None:
    r = Redactor()
    assert r.text("risk-or-abcdefgh") == "risk-or-abcdefgh"
    assert r.text("task-proj-abcdefgh") == "task-proj-abcdefgh"
    assert r.bytes_(b"risk-or-abcdefgh") == b"risk-or-abcdefgh"


_OLD_PATTERN = re.compile(r"\b(sk-(or|ant|proj)-[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9_-]{20,})")


@example("x-sk-proj-abcdefg")
@given(st.text(alphabet='sk-orantpj_%2F0aB .="', max_size=40))
def test_every_old_pattern_match_still_matches(text: str) -> None:
    for m in _OLD_PATTERN.finditer(text):
        assert KEY_PATTERN.match(text, m.start()), (text, m.span())


def test_dash_preceded_key_is_redacted_with_str_and_bytes() -> None:
    r = Redactor()
    assert r.text("x-" + GLUED) == "x-[redacted]"
    assert r.bytes_(b"x-" + GLUED.encode()) == b"x-[redacted]"


@pytest.mark.parametrize("prefix", ["%2F", "%3D"])
def test_percent_encoded_key_survives_a_stream_split(prefix: str) -> None:
    out = io.StringIO()
    stream = Redactor().redact_stream(out)
    stream.write("q=" + prefix + GLUED[:10])
    stream.flush()
    stream.write(GLUED[10:] + "\n")
    stream.close()
    assert "QQQQQQ" not in out.getvalue()
