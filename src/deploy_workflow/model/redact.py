"""R3 key redaction for text, JSON, exception chains, bytes and stderr.

A Redactor never reads the environment on its own. ``from_environ`` takes the
mapping it is given; an offline run builds ``Redactor()`` (regex only).
"""

from __future__ import annotations

import io
import logging
import re
import traceback
from collections.abc import Iterable, Mapping
from typing import Any, TextIO, cast

_LOG = logging.getLogger(__name__)
REPLACEMENT = "[redacted]"
KEY_ENV_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")
# A key may follow "_" or any other non-key character, or a %XX escape (URL-encoded text); only a
# preceding letter, digit or "-" marks the "sk-" as the tail of a longer word such as "risk-".
KEY_PATTERN = re.compile(
    r"(?:(?<![A-Za-z0-9-])|(?<=%[0-9A-Fa-f]{2}))(sk-(or|ant|proj)-[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9_-]{20,})"
)
_KEY_PATTERN_BYTES = re.compile(KEY_PATTERN.pattern.encode("ascii"))
_KEY_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"


def _suffixed(key: Any, n: int) -> Any:
    if isinstance(key, str):
        return f"{key}#{n}"
    if isinstance(key, bytes):
        return key + f"#{n}".encode("ascii")
    if isinstance(key, tuple):
        return (*key, f"#{n}")
    return (key, f"#{n}")


def _replace_spans[T: (str, bytes)](value: T, spans: list[tuple[int, int]], marker: T) -> T:
    """Replace the union of ``spans`` (overlaps merged) in ``value`` once each."""
    out: list[T] = []
    pos = 0
    cur_start = cur_end = -1
    for start, end in sorted(spans):
        if start < cur_end:
            cur_end = max(cur_end, end)
            continue
        if cur_end >= 0:
            out.append(value[pos:cur_start])
            out.append(marker)
            pos = cur_end
        cur_start, cur_end = start, end
    if cur_end >= 0:
        out.append(value[pos:cur_start])
        out.append(marker)
        pos = cur_end
    out.append(value[pos:])
    return value[:0].join(out)


class Redactor:
    def __init__(self, exact_values: Iterable[str] = ()) -> None:
        self._values = sorted({v for v in exact_values if v}, key=lambda v: (-len(v), v))
        # A lookahead finds every occurrence, including ones that overlap an earlier match.
        self._exact = (
            re.compile("(?=(" + "|".join(re.escape(v) for v in self._values) + "))")
            if self._values
            else None
        )
        self._exact_bytes = (
            re.compile(
                b"(?=(" + b"|".join(re.escape(v.encode("utf-8")) for v in self._values) + b"))"
            )
            if self._values
            else None
        )

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> Redactor:
        return cls(environ[name] for name in KEY_ENV_NAMES if environ.get(name))

    def _spans(self, value: str) -> list[tuple[int, int]]:
        spans = [m.span() for m in KEY_PATTERN.finditer(value)]
        if self._exact is not None:
            spans += [m.span(1) for m in self._exact.finditer(value)]
        return spans

    def text(self, value: str) -> str:
        return _replace_spans(value, self._spans(value), REPLACEMENT)

    def bytes_(self, value: bytes) -> bytes:
        spans = [m.span() for m in _KEY_PATTERN_BYTES.finditer(value)]
        if self._exact_bytes is not None:
            spans += [m.span(1) for m in self._exact_bytes.finditer(value)]
        return _replace_spans(bytes(value), spans, REPLACEMENT.encode("ascii"))

    def _hold_from(self, text: str) -> int:
        """Index from which ``text`` might still be the start of a key: the trailing run of
        key characters, or a tail that is a prefix of an exact value. A complete match that
        crosses the cut pulls the cut back to the match start, so no match is split."""
        hold = len(text.rstrip(_KEY_CHARS))
        for value in self._values:
            for n in range(min(len(value), len(text)), 0, -1):
                if text.endswith(value[:n]):
                    hold = min(hold, len(text) - n)
                    break
        # One pass in descending start order reaches the fixed point: a move to ``start``
        # can only be crossed by a span that starts earlier, and those come later.
        for start, end in sorted(self._spans(text), reverse=True):
            if start < hold < end:
                hold = start
        return hold

    def _key(self, key: Any) -> Any:
        if isinstance(key, str):
            return self.text(key)
        if isinstance(key, bytes):
            return self.bytes_(key)
        if isinstance(key, tuple):
            return tuple(self._key(k) for k in key)
        if isinstance(key, frozenset):
            return frozenset(self._key(k) for k in key)
        return key

    def json_value(self, value: Any) -> Any:
        """Redact keys and values, nested, including bytes, tuples and sets. Keys that
        collide once redacted get a suffix, so no dict entry is dropped. Set entries that redact
        to the same text collapse into one; no secret is lost by that."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, bytes):
            return self.bytes_(value)
        if isinstance(value, bytearray):
            return bytearray(self.bytes_(bytes(value)))
        if isinstance(value, Mapping):
            out: dict[Any, Any] = {}
            for key, item in value.items():
                new_key = self._key(key)
                base, n = new_key, 1
                while new_key in out:
                    n += 1
                    new_key = _suffixed(base, n)
                out[new_key] = self.json_value(item)
            return out
        if isinstance(value, set | frozenset):
            return type(value)(self._key(item) for item in value)
        if isinstance(value, list | tuple):
            return [self.json_value(item) for item in value]
        return value

    def exception(self, exc: BaseException) -> str:
        """Format the full chain (cause and context; cycle-safe in the stdlib) then redact."""
        return self.text("".join(traceback.format_exception(exc)))

    def redact_stream(self, stream: TextIO) -> TextIO:
        return cast(TextIO, _RedactingStream(self, stream))


class _RedactingStream(io.TextIOBase):
    """Line-buffered writer. A partial line is held until a newline; flush() writes only the
    part that cannot be the start of a key (the trailing key-character run and any tail that
    is a prefix of an exact value stay held), so a key split by a flush is still seen whole.
    close() writes everything. If the stream is garbage-collected unclosed (CPython flushes but
    never closes std streams at exit) the redacted tail is written; if the target is already
    closed the drop is logged with a char count, never the text."""

    def __init__(self, redactor: Redactor, target: TextIO) -> None:
        self._redactor = redactor
        self._target = target
        self._pending = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        self._pending += s
        head, sep, tail = self._pending.rpartition("\n")
        if sep:
            self._target.write(self._redactor.text(head + sep))
            self._pending = tail
        return len(s)

    def flush(self) -> None:
        cut = self._redactor._hold_from(self._pending)
        if cut:
            self._target.write(self._redactor.text(self._pending[:cut]))
            self._pending = self._pending[cut:]
        self._target.flush()

    def __del__(self) -> None:
        pending = getattr(self, "_pending", "")
        if self.closed or not pending:
            return
        if self._target.closed:
            _LOG.warning(
                "dropped %d chars of held stream text: target already closed", len(pending)
            )
            return
        # Garbage collection is final, so the whole tail is redacted and written.
        self._target.write(self._redactor.text(pending))
        self._target.flush()
        self._pending = ""

    def close(self) -> None:
        if not self.closed:
            if self._pending:
                self._target.write(self._redactor.text(self._pending))
                self._pending = ""
            self._target.flush()
        super().close()
