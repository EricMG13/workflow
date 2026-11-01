"""Citing the context file's figures by line: the shared cite interface (Phase 3, ruling P3-P19).

Python cites each figure of the context file by its own JSON text inside one span of the frozen
`context` source; the model never writes a context quote. CP-3D (Phase 3) and the rating rows
(Phase 4) build on this module. The vii engine may not import `deploy_workflow`, so
`deploy_vii.cp3_relative_value` carries its own copy of the offset walk; a parity test
(`tests/test_context_cites.py`) holds the two to the same offsets, locators and quotes.

The rule for one figure (rulings B20, B20a):

* a context source that is not `text/plain`, or that has a span holding a line break, is refused
  (`ContextTextError`) before any span is indexed: a line of the joined text must be one span;
* a figure whose raw text is not exactly `"<value>"` (a JSON escape, say) is not cited, because
  the file's bytes would not hold the figure shown;
* the figure alone on its line is cited by `"key": "value"` as the file writes it; otherwise by
  the text from the row object's `{` through the figure when that is one line and occurs exactly
  once in the span; otherwise it is not cited (`None`), never a guessed span.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from deploy_vii.contracts import Citation, Source
from deploy_vii.readiness import citation_issues

CITED_ARRAYS: tuple[str, ...] = ("quotes", "deal_terms")  # Phase 4 appends "ratings"
STALE_DAYS = 30  # a quote more than this many whole days before the run as-of is stale
UNREADABLE = "context source unreadable: "

_BOM = "not valid JSON (Unexpected UTF-8 BOM (decode using utf-8-sig) at line 1)"
_SPACE = " \t\n\r"
_DECODER = json.JSONDecoder()


class ContextTextError(ValueError):
    """The context source cannot be read as one line per span; the message says why."""


@dataclass(frozen=True)
class _Member:
    """Where one string member of a row sits in the text: the key's and the value's opening quote,
    the offset after the value's closing quote, and the row object's `{`."""

    key_start: int
    value_start: int
    value_end: int
    object_start: int


def context_text(source: Source) -> str:
    """The file's text, rebuilt as `"\\n".join(span.text ...)`. Raises `ContextTextError` for a
    source that is not `text/plain` or has a span holding more than one line."""
    if source.media_type != "text/plain":
        raise ContextTextError(f"media type is {source.media_type}, not text/plain")
    if any("\n" in span.text for span in source.spans):
        raise ContextTextError("a span holds more than one line")
    text = "\n".join(span.text for span in source.spans)
    if text.startswith("\ufeff"):  # the json module's own refusal, worded as the engine words it
        raise ContextTextError(_BOM)
    return text


class _Walk:
    """A cursor over the JSON text that records the string members of the cited arrays' rows."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0
        self.found: dict[str, _Member] = {}
        self.arrays: set[str] = set()

    def peek(self) -> str:
        return self.text[self.at : self.at + 1]

    def skip(self) -> None:
        while self.at < len(self.text) and self.text[self.at] in _SPACE:
            self.at += 1

    def expect(self, char: str) -> None:
        if self.peek() != char:
            raise ContextTextError(f"expected {char!r} at offset {self.at}")
        self.at += 1
        self.skip()

    def value(self) -> object:
        try:
            decoded, self.at = _DECODER.raw_decode(self.text, self.at)
        except json.JSONDecodeError as error:
            raise ContextTextError(
                f"not valid JSON ({error.msg} at line {error.lineno})"
            ) from error
        return decoded

    def key(self) -> str:
        if self.peek() != '"':
            raise ContextTextError(f"member name at offset {self.at} is not text")
        name: str
        name, self.at = _DECODER.raw_decode(self.text, self.at)
        return name

    def after(self, close: str) -> None:
        """After one member or element: past a ',', or at the closing `close`."""
        self.skip()
        if self.peek() == ",":
            self.at += 1
            self.skip()
            if self.peek() == close:
                raise ContextTextError(f"trailing comma before {close!r} at offset {self.at}")
        elif self.peek() != close:
            raise ContextTextError(f"expected ',' or {close!r} at offset {self.at}")

    def row(self, prefix: str) -> None:
        start = self.at
        self.expect("{")
        while self.peek() != "}":
            key_start = self.at
            name = self.key()
            self.skip()
            self.expect(":")
            value_start = self.at
            if isinstance(self.value(), str):
                path = f"{prefix}.{name}"
                if path in self.found:
                    raise ContextTextError(f"duplicate member {path}")
                self.found[path] = _Member(key_start, value_start, self.at, start)
            self.after("}")
        self.at += 1

    def array(self, name: str) -> None:
        if name in self.arrays:
            raise ContextTextError(f"{name} appears more than once")
        self.arrays.add(name)
        self.expect("[")
        index = 0
        while self.peek() != "]":
            if self.peek() == "{":
                self.row(f"{name}[{index}]")
            else:
                self.value()
            self.after("]")
            index += 1
        self.at += 1
        self.skip()

    def top(self) -> dict[str, _Member]:
        self.skip()
        self.expect("{")
        while self.peek() != "}":
            name = self.key()
            self.skip()
            self.expect(":")
            if name in CITED_ARRAYS and self.peek() == "[":
                self.array(name)
            else:
                self.value()
            self.after("}")
        self.at += 1
        self.skip()
        if self.at != len(self.text):
            raise ContextTextError(f"text after the top-level object at offset {self.at}")
        return self.found


def _members(text: str) -> dict[str, _Member]:
    """Every string member of the rows of the cited arrays, by `<array>[i].<field>`. Raises
    `ContextTextError` on text that is not a JSON object."""
    return _Walk(text).top()


def value_offsets(text: str) -> dict[str, int]:
    """The offset of each row string value's opening `"` in `text`, by `<array>[i].<field>`.
    Raises `ContextTextError` on text that is not a JSON object."""
    return {path: member.value_start for path, member in _members(text).items()}


def _cite_member(source: Source, text: str, member: _Member) -> Citation | None:
    """One figure's citation, or None when no single span of the file holds it uniquely."""
    if "\\" in text[member.value_start : member.value_end] or source.sha256 is None:
        return None
    line = text.count("\n", 0, member.value_start) + 1
    span = source.spans[line - 1]
    own = text[member.key_start : member.value_end]
    quote = (
        own
        if span.text.strip() in (own, own + ",")
        else text[member.object_start : member.value_end]
    )
    if "\n" in quote or span.text.count(quote) != 1:
        return None
    citation = Citation(
        source_id=source.source_id,
        source_sha256=source.sha256,
        locator=span.locator,
        quote=quote,
    )
    return None if citation_issues((citation,), (source,)) else citation


def cite(source: Source, path: str) -> Citation | None:
    """The citation of the figure at `path` (`quotes[0].bid`): locator `line:<n>`, the quote as
    the file writes it. None when the figure cannot be cited as one unique span. Raises
    `ContextTextError` for a source that cannot be read by line or text that is not a JSON object
    and `KeyError` for a path that is not a string member of a cited row."""
    text = context_text(source)
    return _cite_member(source, text, _members(text)[path])


def cite_all(source: Source, paths: Sequence[str]) -> tuple[Citation, ...] | None:
    """The citations of the figures at `paths`, in order; None unless every one cites. The text is
    walked once. Errors as `cite`."""
    text = context_text(source)
    found = _members(text)
    cited: list[Citation] = []
    for path in paths:
        citation = _cite_member(source, text, found[path])
        if citation is None:
            return None
        cited.append(citation)
    return tuple(cited)
