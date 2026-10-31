"""Python statement-line extraction from whitespace-aligned page text (task 8.10).

User decision "A" (24 Oct 2026): Python extracts the printed statement lines and the model maps,
corrects and cites them instead of retyping them. One call reads one page's text and reports
only what is printed: each data line's label, its raw numeric cells and their exact `Decimal`
values, the label's indent, the caption above it and the raw header lines above the first data
line. It never rounds and never guesses a unit, period, item, statement or sign convention (the
model maps `period_id` and `item_id`). A line the rules cannot parse is never stubbed as
data; a candidate such line (two or more tokens ending in a numeric cell) is recorded in
`ExtractedTable.omitted` as printed, and prose yields an empty table.

Rules (docs/development/live-runner.md, "Statement extraction"):

- A line's cells are separated by two or more spaces, or by a ` | ` pipe (a table row printed
  as `Label | 1,759 | 1,668`: the line is read as if each pipe were two spaces; a row of only
  `-` runs and pipes gives no line, and a line holding a pipe is never a caption or a label
  continuation). A data line is a label (with a letter)
  followed, to the end of the line, by two or more numeric cells: `10,441`, `2.42`, `(1,234)`
  (negative) or a lone em dash, en dash or hyphen (nil: value `None`, raw token kept). A `$`
  before a number, alone or attached, is folded into it and not kept in the raw value.
- A single cell of text with no digit and a lowercase letter, not ending in `:`, directly above
  a data line (no blank line between) continues its label; such lines join the label with one
  space and the indent is the first line's. A line ending in `:` is a sub-heading, not joined.
- A line with a letter, no lowercase letter and no digit is a caption; it applies to the data
  lines that follow until the next caption.
- `headers` are the raw lines nearest above the first data line holding two or more four-digit
  years or a month name, with the adjacent such lines above them (blank lines between allowed).
- A line whose numeric cells are all bare four-digit years from 1900 to 2099 with no `$` is a
  header line, not data, only when its label is empty, wholly parenthesised (`(In millions)`),
  or made only of month names, period words (`Year ended December 31`) and unit or scale words
  (`in millions, except per share data`). Any other label makes it a data line, read like any
  other (`Net revenues  2025  1998`), so `headers` never holds a returned data line.
- `omitted` lists, in page order, each candidate line the rules did not return as data: a
  non-blank line of two or more whitespace-separated tokens (after the pipe rewrite) whose
  last token is a numeric cell, that is neither a returned data line, a returned header line
  nor a header-shaped line ending in a bare four-digit year (a second table's period row). A
  lone token (a page number) is never a candidate.

Flags (task 8.10b, review risks 1-2) inform the model and never drop a line:

- `more_values_than_header_years`: the line has more numeric cells than the table's header
  lines hold four-digit years (counted over all header lines; none counted when the headers
  name no year). A footnote marker `(1)` two spaces before the values reads as a value of -1.
- `label_ends_numeric`: the label's last token is a numeric cell (`1,234`, `$5`, `(12)`, a nil
  dash). Two numbers one space apart are one text cell, so the scan stops there and they stay
  in the label; a label ending in a year (`Balance, January 1, 2023`) is flagged too.
- `footnote_marker`: the header lines hold N > 0 four-digit years and the line has N + 1 raw
  values whose first is `(n)` (one or two digits, no `$`): that first cell is a footnote
  marker, dropped from `raw_values` and `values` (the label is unchanged), and the line does
  not also get `more_values_than_header_years`. With no year in the headers the marker still
  reads as -1 and is flagged as above.

`ExtractedTable.source_id` names the table's source: `extract_pack_statements` sets it and
binds locators per source, so two sources may share a locator; `extract_statement_lines` sets
it only when given one.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_NIL_TOKENS = ("\u2014", "\u2013", "-")  # em dash, en dash, hyphen
_NILS = frozenset(_NIL_TOKENS)
_NIL = "|".join(_NIL_TOKENS)
_NUMERIC_CELL = re.compile(rf"(?P<dollar>\$ ?)?(?P<raw>\((?:{_NUMBER})\)|(?:{_NUMBER})|{_NIL})")
_CELL = re.compile(r"\S+(?: \S+)*")
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_BARE_YEAR = re.compile(r"(?:19|20)\d{2}")
_WORD = re.compile(r"[A-Za-z]+")
_PIPE = re.compile(r"[ \t]*\|[ \t]*")
_MONTH_NAMES = (
    *("January", "February", "March", "April", "May", "June", "July", "August"),
    *("September", "October", "November", "December"),
)
_MONTHS = frozenset((*_MONTH_NAMES, *(name.upper() for name in _MONTH_NAMES)))
_FOOTNOTE = re.compile(r"\(\d{1,2}\)")
_HEADER_WORDS = frozenset(
    (
        *(name.lower() for name in _MONTH_NAMES),
        *"year years ended ending fiscal month months week weeks quarter quarters".split(),
        *"period periods three six nine twelve for the as of at and".split(),
        *"in millions thousands billions dollars usd except per share data par value".split(),
        *("amounts", "unaudited"),
    )
)
LineFlag = Literal["more_values_than_header_years", "label_ends_numeric", "footnote_marker"]
MORE_VALUES_THAN_HEADER_YEARS: LineFlag = "more_values_than_header_years"
LABEL_ENDS_NUMERIC: LineFlag = "label_ends_numeric"
FOOTNOTE_MARKER: LineFlag = "footnote_marker"


@dataclass(frozen=True)
class ExtractedLine:
    """One printed data line. `line_no` is the 1-based line of the page text holding the values;
    `raw_values[i]` is printed on that line and `values[i]` is its exact Decimal (None for a nil).
    `flags` (module docstring) are computed, in a fixed order; they never drop the line.
    """

    locator: str
    line_no: int
    label: str
    raw_values: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    indent: int
    caption: str | None
    flags: tuple[LineFlag, ...] = ()


@dataclass(frozen=True)
class OmittedLine:
    """A candidate line (module docstring) not returned as data: `line_no` is 1-based and `text`
    the page line as printed."""

    line_no: int
    text: str


@dataclass(frozen=True)
class ExtractedTable:
    """The data lines of one page's text, in page order, with the raw header lines and the
    candidate lines omitted. `source_id` names the source the page belongs to (None: the text
    was given without one)."""

    locator: str
    headers: tuple[str, ...]
    lines: tuple[ExtractedLine, ...]
    source_id: str | None = None
    omitted: tuple[OmittedLine, ...] = ()


@dataclass(frozen=True)
class _Cells:
    label: str
    raw_values: tuple[str, ...]
    values: tuple[Decimal | None, ...]
    first_dollar: bool  # a `$` is folded into the first cell


def _value(raw: str) -> Decimal | None:
    if raw in _NILS:
        return None
    if raw.startswith("("):
        # Built from the string, never by negation: `-Decimal` would round to the context.
        return Decimal("-" + raw[1:-1].replace(",", ""))
    return Decimal(raw.replace(",", ""))


def _cells(line: str) -> _Cells | None:
    """The label and trailing numeric cells of a data line, or None for any other line."""
    if "|" in line:
        line = _PIPE.sub("  ", line)
    found: list[tuple[str, bool]] = []  # (raw, a `$` is folded in), right to left
    start = len(line)
    for cell in reversed(list(_CELL.finditer(line))):
        text = cell.group()
        if text == "$" and found and not found[-1][1]:
            found[-1] = (found[-1][0], True)
        elif match := _NUMERIC_CELL.fullmatch(text):
            found.append((match["raw"], match["dollar"] is not None))
        else:
            break
        start = cell.start()
    label = line[:start].strip()
    if len(found) < 2 or not _WORD.search(label):
        return None
    if _is_period_label(label) and all(
        _BARE_YEAR.fullmatch(raw) and not dollar for raw, dollar in found
    ):
        return None
    raws = tuple(raw for raw, _ in reversed(found))
    return _Cells(
        label=label,
        raw_values=raws,
        values=tuple(_value(raw) for raw in raws),
        first_dollar=found[-1][1],
    )


def _is_period_label(label: str) -> bool:
    """A label that makes a line of only bare years a header line (module docstring)."""
    return (
        not label
        or (label.startswith("(") and label.endswith(")"))
        or all(word.lower() in _HEADER_WORDS for word in _WORD.findall(label))
    )


def _is_header(line: str) -> bool:
    return len(_YEAR.findall(line)) >= 2 or bool(_MONTHS.intersection(_WORD.findall(line)))


def _is_caption(stripped: str) -> bool:
    return (
        "|" not in stripped
        and bool(_WORD.search(stripped))
        and not any(c.islower() for c in stripped)
        and not any(c.isdigit() for c in stripped)
    )


def _is_continuation(stripped: str) -> bool:
    return (
        "|" not in stripped
        and _CELL.fullmatch(stripped) is not None
        and any(c.islower() for c in stripped)
        and not any(c.isdigit() for c in stripped)
        and not stripped.endswith(":")
        and not _is_header(stripped)
    )


def _header_indexes(lines: Sequence[str], first: int) -> tuple[int, ...]:
    """The 0-based indexes of the header block nearest above the 0-based line `first` (the first
    data line), in page order."""
    index = first - 1
    while index >= 0 and not _is_header(lines[index]):
        index -= 1
    block: list[int] = []
    while index >= 0 and (_is_header(lines[index]) or not lines[index].strip()):
        if lines[index].strip():
            block.append(index)
        index -= 1
    return tuple(reversed(block))


def _is_omitted_candidate(line: str) -> bool:
    tokens = (_PIPE.sub("  ", line) if "|" in line else line).split()
    if len(tokens) < 2 or not _NUMERIC_CELL.fullmatch(tokens[-1]):
        return False
    # A second table's period row (`June 30, 2026 | December 31, 2025`) is not a lost value.
    return not (_is_header(line) and _BARE_YEAR.fullmatch(tokens[-1]))


def _label_ends_numeric(label: str) -> bool:
    tokens = label.split()
    return bool(tokens) and _NUMERIC_CELL.fullmatch(tokens[-1]) is not None


def _flags(line: ExtractedLine, years: int, footnote: bool) -> tuple[LineFlag, ...]:
    flags: list[LineFlag] = []
    if years and len(line.raw_values) > years:
        flags.append(MORE_VALUES_THAN_HEADER_YEARS)
    if _label_ends_numeric(line.label):
        flags.append(LABEL_ENDS_NUMERIC)
    if footnote:
        flags.append(FOOTNOTE_MARKER)
    return tuple(flags)


def _footnote_marker(line: ExtractedLine, first_dollar: bool, years: int) -> bool:
    return (
        years > 0
        and len(line.raw_values) == years + 1
        and not first_dollar
        and _FOOTNOTE.fullmatch(line.raw_values[0]) is not None
    )


def extract_statement_lines(
    text: str, locator: str, source_id: str | None = None
) -> ExtractedTable:
    """The printed data lines of one page's text (module docstring rules); prose yields none."""
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    found: list[ExtractedLine] = []
    first_dollars: list[bool] = []
    first: int | None = None
    caption: str | None = None
    pending: list[str] = []  # continuation lines directly above the current line
    for index, line in enumerate(lines):
        stripped = line.strip()
        cells = _cells(line)
        if cells is not None:
            first = index if first is None else first
            head = pending[0] if pending else line
            found.append(
                ExtractedLine(
                    locator=locator,
                    line_no=index + 1,
                    label=" ".join((*(part.strip() for part in pending), cells.label)),
                    raw_values=cells.raw_values,
                    values=cells.values,
                    indent=len(head) - len(head.lstrip()),
                    caption=caption,
                )
            )
            first_dollars.append(cells.first_dollar)
            pending = []
        elif _is_caption(stripped):
            caption = stripped
            pending = []
        elif _is_continuation(stripped):
            pending.append(line)
        else:
            pending = []
    header_at = () if first is None else _header_indexes(lines, first)
    headers = tuple(lines[index] for index in header_at)
    years = sum(len(_YEAR.findall(header)) for header in headers)
    flagged: list[ExtractedLine] = []
    for printed, first_dollar in zip(found, first_dollars, strict=True):
        footnote = _footnote_marker(printed, first_dollar, years)
        line = (
            replace(printed, raw_values=printed.raw_values[1:], values=printed.values[1:])
            if footnote
            else printed
        )
        flagged.append(replace(line, flags=_flags(line, years, footnote)))
    kept = {line.line_no - 1 for line in found}.union(header_at)
    omitted = tuple(
        OmittedLine(line_no=index + 1, text=text)
        for index, text in enumerate(lines)
        if index not in kept and _is_omitted_candidate(text)
    )
    return ExtractedTable(
        locator=locator,
        headers=headers,
        lines=tuple(flagged),
        source_id=source_id,
        omitted=omitted,
    )


def _objects(value: object, missing: str, not_object: str) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(missing)
    objects: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(not_object)
        objects.append(item)
    return objects


def _pack_spans(pack_json: Mapping[str, object]) -> tuple[list[str], list[tuple[str, str, str]]]:
    """The source ids, and (source_id, locator, text) of every span, in pack order; a malformed
    pack raises."""
    ids: list[str] = []
    found: list[tuple[str, str, str]] = []
    sources = pack_json.get("sources")
    for source in _objects(sources, "pack has no sources list", "a source is not an object"):
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            raise ValueError("a source has no string source_id")
        ids.append(source_id)
        of = f"of source {source_id!r}"
        spans = source.get("spans")
        for span in _objects(
            spans, f"source {source_id!r} has no spans list", f"a span {of} is not an object"
        ):
            locator, text = span.get("locator"), span.get("text")
            if not isinstance(locator, str):
                raise ValueError(f"a span {of} has no string locator")
            if not isinstance(text, str):
                raise ValueError(f"span {locator!r} {of} has no string text")
            found.append((source_id, locator, text))
    return ids, found


def extract_pack_statements(
    pack_json: Mapping[str, object],
    locators: Iterable[str] | None = None,
    source_id: str | None = None,
) -> tuple[ExtractedTable, ...]:
    """One table per span of `sources[*].spans`, in pack order; read-only, no file I/O.

    With `source_id` given, only that source's spans (an id the pack lacks raises); with
    `locators` given, only those spans. Each table carries its `source_id`, so a locator two
    sources share yields one table per source (task 8.10b); a locator twice in one source in
    scope raises, as its table would be ambiguous. A requested locator that no span in scope
    has raises too. Every span in scope yields a table, an empty one for a page without data
    lines.
    """
    if isinstance(locators, str):
        # A str is an Iterable[str] of characters; reading it so would miss every page.
        raise TypeError("locators must be an iterable of locators, not one string")
    wanted = None if locators is None else frozenset(locators)
    ids, spans = _pack_spans(pack_json)
    if source_id is not None and source_id not in ids:
        raise ValueError(f"source {source_id!r} is not in the pack")
    bound: set[tuple[str, str]] = set()
    tables: list[ExtractedTable] = []
    for owner, locator, text in spans:
        if (source_id is not None and owner != source_id) or (
            wanted is not None and locator not in wanted
        ):
            continue
        if (owner, locator) in bound:
            raise ValueError(
                f"locator {locator!r} is twice in source {owner!r}; an extracted table names "
                "its span by source and locator"
            )
        bound.add((owner, locator))
        tables.append(extract_statement_lines(text, locator, source_id=owner))
    if wanted is not None and (missing := sorted(wanted - {loc for _, loc in bound})):
        where = "the pack" if source_id is None else f"source {source_id!r}"
        raise ValueError(f"locators not in {where}: {missing}")
    return tuple(tables)
