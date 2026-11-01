"""R3 key redaction for text, JSON, exception chains, bytes and stderr.

A Redactor never reads the environment on its own. ``from_environ`` takes the
mapping it is given; an offline run builds ``Redactor()`` (regex only).
"""

from __future__ import annotations

import io
import re
import traceback
from collections.abc import Iterable, Mapping
from typing import Any, TextIO, cast

REPLACEMENT = "[redacted]"
KEY_ENV_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")
KEY_PATTERN = re.compile(r"\b(sk-(or|ant|proj)-[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9_-]{20,})")
_KEY_PATTERN_BYTES = re.compile(KEY_PATTERN.pattern.encode("ascii"))


class Redactor:
    def __init__(self, exact_values: Iterable[str] = ()) -> None:
        values = sorted({v for v in exact_values if v}, key=lambda v: (-len(v), v))
        self._exact = re.compile("|".join(re.escape(v) for v in values)) if values else None
        self._exact_bytes = (
            re.compile(b"|".join(re.escape(v.encode("utf-8")) for v in values)) if values else None
        )

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> Redactor:
        return cls(environ[name] for name in KEY_ENV_NAMES if environ.get(name))

    def text(self, value: str) -> str:
        if self._exact is not None:
            value = self._exact.sub(REPLACEMENT, value)
        return KEY_PATTERN.sub(REPLACEMENT, value)

    def bytes_(self, value: bytes) -> bytes:
        if self._exact_bytes is not None:
            value = self._exact_bytes.sub(REPLACEMENT.encode("ascii"), value)
        return _KEY_PATTERN_BYTES.sub(REPLACEMENT.encode("ascii"), value)

    def json_value(self, value: Any) -> Any:
        """Redact keys and string values, nested. Keys that collide once redacted get a suffix."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            out: dict[Any, Any] = {}
            for key, item in value.items():
                new_key = self.text(key) if isinstance(key, str) else key
                base, n = new_key, 1
                while new_key in out:
                    n += 1
                    new_key = f"{base}#{n}"
                out[new_key] = self.json_value(item)
            return out
        if isinstance(value, list | tuple):
            return [self.json_value(item) for item in value]
        return value

    def exception(self, exc: BaseException) -> str:
        """Format the full chain (cause and context; cycle-safe in the stdlib) then redact."""
        return self.text("".join(traceback.format_exception(exc)))

    def redact_stream(self, stream: TextIO) -> TextIO:
        return cast(TextIO, _RedactingStream(self, stream))


class _RedactingStream(io.TextIOBase):
    """Line-buffered writer: a partial line is held until a newline or flush, so a key
    split across writes is still seen whole."""

    def __init__(self, redactor: Redactor, target: TextIO) -> None:
        self._redactor = redactor
        self._target = target
        self._pending = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        self._pending += s
        head, sep, tail = self._pending.rpartition("\n")
        if sep:
            self._target.write(self._redactor.text(head + sep))
            self._pending = tail
        return len(s)

    def flush(self) -> None:
        if self._pending:
            self._target.write(self._redactor.text(self._pending))
            self._pending = ""
        self._target.flush()

    def close(self) -> None:
        if not self.closed:
            self.flush()
        super().close()
