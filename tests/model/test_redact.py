"""R3 key redaction: synthetic values only, no environment read."""

import io

from hypothesis import given
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
    assert KEY_PATTERN.pattern.startswith(r"\b(sk-(or|ant|proj)-")


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
    assert buf.getvalue() == "key [redacted] tail"


@given(t=st.text(), v=st.text(min_size=4))
def test_property_value_never_survives(t: str, v: str) -> None:
    if "[" in v or "]" in v or v in "[redacted]":
        return
    assert v not in Redactor([v]).text(t)
    assert v not in Redactor([v]).text(t + v + t)
