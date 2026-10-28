r"""Shared defect-class cases (AGENTS.md rules 3 and 4; LEAD rounds 11 and 12): data and assertions.

A helper module, not a test module (pytest collects only `test_*.py`). It imports no owner: each
module's own test file runs these cases through its own reader with its own `Adapter`, a callable
from (page text, quote, analyst value) to the module's validator issues for a submission that is
valid except for where the adapter places those three strings.

Rules encoded (`docs/rulings/2026-10-28-stage1.md`):
- `R10_SIGN`: round 10 §1. A figure read from a quote is the signed numeral that
  `quotes.normalise(quote)` prints; `(?<![A-Za-z0-9])-` before the first digit is a minus, `+` is
  ignored. An unsigned analyst figure does not occur in a quote that prints it signed.
- `R10_PARENS`: round 10 "Parentheses". `(` directly before the first digit and `)` directly after
  the last reads as negative; a parenthesis enclosing a unit or words is unaffected.
- `R12_W`: round 12 rule W, amending both: whitespace never separates a sign from its figure. In
  the four quote readers, on `normalise(text)` and the joined reading, of the quote and the page,
  the minus is `(?<![A-Za-z0-9])- ?` (directly or one space before the first digit), and the
  accounting negative is `(` or `( ` before the first digit with `)` or ` )` after the last.
  `normalise` makes any whitespace run one space, so `- `, `-\n`, U+2212 then NBSP and `(\n` all
  read signed, and an edge figure after a page `- ` is cut (B1). After a letter or digit `-\n`
  stays a hyphen wrap (`A-\n25`, `2024-\n2025`), not a sign. The accepted cost: a spaced range
  (`95 - 96`) or a dash bullet before a figure reads signed (no library case before round 12
  held one, so no expected outcome changed).
- `R11_B1`: round 11 Quote readers B1. A figure at an edge of `normalise(quote)` occurs only if it
  is the same unsigned whole figure on the page (start edge: not a digit, `.`, minus or closed
  accounting `(` before it; end edge: not a digit, `.` plus a digit, or closing `)` after it).
- `R11_B3`: round 11 Quote readers B3. When `quotes.hyphen_wrapped(quote)` holds and `"- "` occurs
  in `normalise(value)`, a name or text value does not occur in the quote.
  Round 13 addendum: a `"- "` that is rule W's minus (`(?<![A-Za-z0-9])- (?=[0-9])`) is no wrap
  split, so `is -\n1.25` occurs (the figure readers then read it signed), while `A-\n25` and
  `a - b` stay refused.
- `R9_M1`: round 9 CP-8 heading ("M1's normalised quote applies to every new check") with round 11
  "Shared class test": a figure, label or name is read on the text `quotes.quoted` matched, so a
  soft hyphen, mapped dash or NBSP reads as the page shows it.
- `R11_BLANK`: round 11 "Blank text is one defect class". Every analyst text field refuses
  whitespace-only text with the module's pinned empty-text frame, or `<path>: empty text`.
  Controller decision (library fix 1): for `""` an existing refusal stands, such as a `Text`
  field's pydantic `min_length=1` (raised, or reported as an issue); the frame is required only
  for blank text that is not `""` (`whitespace_only`).
- `R12_B10`: round 12 B10. Blank is every character whitespace (`str.isspace`) or of Unicode
  category `Cf` (`deploy_workflow.owners.blank.is_blank`), so U+200B, U+FEFF, U+00AD and
  `" \u200b\n"`, which `str.strip()` keeps, get the same frame at the same position.

Outcomes. A refused case expects the field's pinned refusal (passed in by the module, usually its
"does not occur in the quote" frame) among the issues. An accepted case expects that refusal to be
absent; other issues the field's own bounds or shape raise for the value are outside these classes.
Every refused case names an accepted twin, its nearest accepted counterpart: the same value
(except `wrap-split`, whose twin holds the joined spelling) on a page that prints the figure or
name plainly. An edge cut's twin is the accepted edge case with the same or nearest quote
(`edge-start-<f>` or `edge-end-<f>`), so the pair differs mainly in the page. A rule W case's twin
is the case with its sign deleted: `genuine-<f>` for `- <f>` and U+2212 then NBSP, `w-break-<f>`
(the same line break, no sign) for `-\n<f>` and `(\n<f>)`, and `edge-start-<f>` for the edge.
The self-check proves only that a refused case is not a normalisation-equal spelling of its twin
(page, quote and value are not all equal under `quotes.quoted`), and that a W case is signed only
one space away; it does not prove the expected outcome, which rests on the rulings.

Two classes of hostile text (`docs/rulings/2026-10-28-stage2.md`):
- `HOSTILE_JSON` (round 1 Q5): stored text that `schema.model_validate_json` must refuse only with a
  `ValueError` subclass, because `host._execution_state` maps nothing else. `assert_hostile_refused`.
- `MODEL_TEXT_HOSTILE` (round 3 item 2): model text a step validator may pass although the type the
  step builds from it refuses it after the binding audit write (protocol section 6). The module's
  `test_connect_<cp>` calls `model_text_failures` over a fresh real run per case.

Cases the rulings do not pin are not here (listed in the inventory report), for example a value
carrying its own soft hyphen, or a joined value against a wrapped quote.
"""

import copy
import json
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

Defect = Literal["genuine", "soft_hyphen", "dashes", "nbsp", "signs", "edge_cut", "wrap"]
# figure: an unlabelled figure read from the quote; label: a figure read after a label the module
# names (bind with `label_cases`); text: a name or text value that must occur in the quote.
Kind = Literal["figure", "label", "text"]
Adapter = Callable[[str, str, str], Sequence[str]]
"""(page, quote, value) -> the module's issues, the value placed in one analyst field."""

SOFT_HYPHEN = "­"
NBSP = " "
MINUS = "−"
EN_DASH = "–"
EM_DASH = "—"
ZWSP = "\u200b"  # ZERO WIDTH SPACE (Cf)
BOM = "\ufeff"  # ZERO WIDTH NO-BREAK SPACE, the byte order mark (Cf)

R10_SIGN = "Round 10 §1 (read the sign)"
R10_PARENS = "Round 10 For LEAD: Parentheses"
R11_B1 = "Round 11 Quote readers B1 (edge cut)"
R11_B3 = "Round 11 Quote readers B3 (wrap refusal)"
R9_M1 = "Round 9 CP-8 M1 normalised quote; round 11 shared class test"
R11_BLANK = "Round 11 LEAD rulings: Blank text is one defect class"
R12_W = "Round 12 rule W (whitespace never separates a sign from its figure)"
R12_B10 = "Round 12 B10 (Unicode format characters count as blank)"

EMPTY_TEXT = "{path}: empty text"
"""The fallback frame where a module pins none (round 11 blank text)."""


@dataclass(frozen=True)
class QuoteCase:
    case_id: str
    defect: Defect
    kind: Kind
    page: str
    quote: str
    value: str
    accepted: bool
    ruling: str
    twin: str | None = None  # the nearest accepted counterpart (refused cases only)


@dataclass(frozen=True)
class BlankCase:
    case_id: str
    value: str
    page: str  # a genuine page and quote, for a field whose text must sit beside a quote
    quote: str
    # False for "": an existing refusal stands, the frame is not required. True for every other
    # blank value, whitespace or `Cf` (B10), which needs the frame.
    whitespace_only: bool
    ruling: str = R11_BLANK


def _level(figure: str) -> str:
    return f"The level is {figure} percent over the reference rate."


def _figure(
    case_id: str,
    defect: Defect,
    page: str,
    value: str,
    ruling: str,
    *,
    quote: str | None = None,
    twin: str | None = None,
) -> QuoteCase:
    return QuoteCase(
        case_id,
        defect,
        "figure",
        page,
        page if quote is None else quote,
        value,
        accepted=twin is None,
        ruling=ruling,
        twin=twin,
    )


def _genuine(value: str) -> QuoteCase:
    return _figure(f"genuine-{value}", "genuine", _level(value), value, R10_SIGN)


# Two figure spellings: a whole number and an N.NN decimal (CP-8 sizes and levels hold only N.NN).
FIGURES = ("25", "1.25")


def _family(f: str) -> tuple[QuoteCase, ...]:
    """The cases built the same way for figure `f`; ids end in `-<f>`; twins are `genuine-<f>`,
    `edge-start-<f>` or `edge-end-<f>` for an edge cut, and `w-break-<f>` for a wrapped sign."""
    twin, start, end = f"genuine-{f}", f"edge-start-{f}", f"edge-end-{f}"
    w_break = f"w-break-{f}"
    rest = " percent over the reference rate."
    return (
        _genuine(f),
        # Soft hyphen inside a figure: deleted by normalisation, so the figure is the page's.
        _figure(f"shy-inside-{f}", "soft_hyphen", _level(f[0] + SOFT_HYPHEN + f[1:]), f, R9_M1),
        _figure(
            f"shy-prefix-{f}", "soft_hyphen", _level(f"1{SOFT_HYPHEN}{f}"), f, R9_M1, twin=twin
        ),
        # Dashes and the minus sign: before a figure after a space it is a minus; after a digit
        # (a range, `95-96`) it is not a sign.
        _figure(f"em-before-{f}", "dashes", _level(EM_DASH + f), f, R10_SIGN, twin=twin),
        _figure(f"en-inside-{f}", "dashes", _level(f"9{EN_DASH}{f}"), f, R10_SIGN),
        _figure(f"em-inside-{f}", "dashes", _level(f"9{EM_DASH}{f}"), f, R10_SIGN),
        _figure(f"minus-inside-{f}", "dashes", _level(f"9{MINUS}{f}"), f, R10_SIGN),
        # NBSP beside a figure is whitespace.
        _figure(f"nbsp-before-{f}", "nbsp", f"The level is{NBSP}{f} percent.", f, R9_M1),
        _figure(f"nbsp-after-{f}", "nbsp", f"The level is {f}{NBSP}percent.", f, R9_M1),
        # Signs and parentheses (round 10).
        _figure(f"sign-minus-{f}", "signs", _level(MINUS + f), f, R10_SIGN, twin=twin),
        _figure(f"sign-ascii-{f}", "signs", _level(f"-{f}"), f, R10_SIGN, twin=twin),
        _figure(f"sign-en-{f}", "signs", _level(EN_DASH + f), f, R10_SIGN, twin=twin),
        _figure(f"sign-parens-{f}", "signs", _level(f"({f})"), f, R10_PARENS, twin=twin),
        _figure(f"sign-plus-{f}", "signs", _level(f"+{f}"), f, R10_SIGN),
        _figure(
            f"sign-mid-{f}", "signs", f"The level is in the mid-{f} percent range.", f, R10_SIGN
        ),
        _figure(
            f"sign-parens-words-{f}",
            "signs",
            f"The level ({f} percent) is above it.",
            f,
            R10_PARENS,
        ),
        # Rule W (round 12): a sign one whitespace character from the figure. The quote is the
        # page, so it spans the break.
        _figure(f"w-minus-space-{f}", "signs", _level(f"- {f}"), f, R12_W, twin=twin),
        _figure(f"w-minus-wrap-{f}", "signs", _level(f"-\n{f}"), f, R12_W, twin=w_break),
        _figure(f"w-minus-nbsp-{f}", "signs", _level(MINUS + NBSP + f), f, R12_W, twin=twin),
        _figure(f"w-parens-wrap-{f}", "signs", _level(f"(\n{f})"), f, R12_W, twin=w_break),
        # Its accepted controls: a line break with no sign, and a hyphen wrap after a letter.
        _figure(w_break, "signs", _level(f"\n{f}"), f, R12_W),
        _figure(f"w-letter-wrap-{f}", "signs", _level(f"A-\n{f}"), f, R12_W),
        # Edge cut (round 11 B1): the figure touches an edge of the normalised quote.
        _figure(
            f"edge-prefix-{f}", "edge_cut", _level(f"4{f}"), f, R11_B1, quote=f + rest, twin=start
        ),
        _figure(
            f"edge-minus-{f}", "edge_cut", _level(f"-{f}"), f, R11_B1, quote=f + rest, twin=start
        ),
        _figure(
            f"w-edge-minus-space-{f}",
            "edge_cut",
            _level(f"- {f}"),
            f,
            R12_W,
            quote=f + rest,
            twin=start,
        ),
        _figure(
            f"edge-close-paren-{f}",
            "edge_cut",
            _level(f"({f})"),
            f,
            R11_B1,
            quote=f"{f}){rest}",
            twin=start,
        ),
        _figure(
            f"edge-open-paren-{f}",
            "edge_cut",
            _level(f"({f})"),
            f,
            R11_B1,
            quote=f"The level is ({f}",
            twin=end,
        ),
        _figure(
            f"edge-end-digit-{f}",
            "edge_cut",
            _level(f"{f}0"),
            f,
            R11_B1,
            quote=f"The level is {f}",
            twin=end,
        ),
        _figure(f"edge-start-{f}", "edge_cut", _level(f), f, R11_B1, quote=f + rest),
        _figure(f"edge-end-{f}", "edge_cut", _level(f), f, R11_B1, quote=f"The level is {f}"),
        _figure(
            f"edge-stop-{f}",
            "edge_cut",
            f"The level is {f}.",
            f,
            R11_B1,
            quote=f"The level is {f}.",
        ),
        _figure(
            f"edge-mid-{f}",
            "edge_cut",
            f"The level is in the mid-{f} percent range.",
            f,
            R11_B1,
            quote=f"{f} percent range.",
        ),
    )


FIGURE_CASES: tuple[QuoteCase, ...] = (
    *(c for f in FIGURES for c in _family(f)),
    _genuine("0"),
    _genuine("0.25"),
    # The round 10 examples that are not signs, each with its own figure.
    _figure("sign-1-december", "signs", "The level resets on 1-December each year.", "1", R10_SIGN),
    _figure("sign-2024-2025", "signs", "The level is fixed for 2024-2025.", "2025", R10_SIGN),
    _figure("sign-95-96", "signs", _level("95-96"), "96", R10_SIGN),
    _figure("sign-s-350", "signs", "The level is S-350 over the reference rate.", "350", R10_SIGN),
    # Rule W's control: a hyphen wrap after a digit is not a sign.
    _figure("w-2024-2025-wrap", "signs", "The level is fixed for 2024-\n2025.", "2025", R12_W),
    # The round 11 B1 examples with their own figures, and their accepted edge twins.
    *(
        _figure(
            f"edge-start-{v}",
            "edge_cut",
            _level(v),
            v,
            R11_B1,
            quote=f"{v} percent over the reference rate.",
        )
        for v in ("0", "0.25")
    ),
    _figure(
        "edge-10",
        "edge_cut",
        _level("10"),
        "0",
        R11_B1,
        quote="0 percent over the reference rate.",
        twin="edge-start-0",
    ),
    _figure(
        "edge-minus-0.25",
        "edge_cut",
        _level("-0.25"),
        "0.25",
        R11_B1,
        quote="0.25 percent over the reference rate.",
        twin="edge-start-0.25",
    ),
    _figure(
        "edge-end-decimal",
        "edge_cut",
        _level("25.5"),
        "25",
        R11_B1,
        quote="The level is 25",
        twin="edge-end-25",
    ),
)


NAME = "Northbridge Term Loan"
_WRAP_PAGE = "The Northbridge first-\npriority Term Loan is quoted by dealers."
_W_MINUS_PAGE = "The level is -\n1.25 percent over the reference rate."
_LETTER_WRAP_PAGE = "The Term Loan A-\n25 notes are quoted."
_NO_DIGIT_WRAP_PAGE = "The rate a -\nb applies."
_INDEX0_LETTER_PAGE = "The Term Loan A-\n1.25 notes are quoted."
_INDEX0_DIGIT_PAGE = "In 2024-\n2025 notes held."

TEXT_CASES: tuple[QuoteCase, ...] = (
    QuoteCase(
        "text-genuine",
        "genuine",
        "text",
        f"The {NAME} is quoted by dealers.",
        NAME,
        NAME,
        accepted=True,
        ruling=R9_M1,
    ),
    QuoteCase(
        "shy-name",
        "soft_hyphen",
        "text",
        f"The Northbridge Term Lo{SOFT_HYPHEN}an is quoted by dealers.",
        f"Northbridge Term Lo{SOFT_HYPHEN}an",
        NAME,
        accepted=True,
        ruling=R9_M1,
    ),
    QuoteCase(
        "nbsp-name",
        "nbsp",
        "text",
        f"The Northbridge{NBSP}Term Loan is quoted by dealers.",
        f"Northbridge{NBSP}Term Loan",
        NAME,
        accepted=True,
        ruling=R9_M1,
    ),
    QuoteCase(
        "wrap-joined",
        "wrap",
        "text",
        _WRAP_PAGE,
        "Northbridge first-priority Term Loan",
        "Northbridge first-priority Term Loan",
        accepted=True,
        ruling=R11_B3,
    ),
    QuoteCase(
        "wrap-split",
        "wrap",
        "text",
        _WRAP_PAGE,
        "Northbridge first-\npriority Term Loan",
        "Northbridge first- priority Term Loan",
        accepted=False,
        ruling=R11_B3,
        twin="wrap-joined",
    ),
    # Round 13 addendum: W's minus (`- ` not after a letter or digit, a digit next) is no wrap
    # split, so B3 does not refuse it; every other `- ` still does.
    QuoteCase(
        "w-minus-wrap-text",
        "wrap",
        "text",
        _W_MINUS_PAGE,
        "The level is -\n1.25 percent over the reference rate.",
        "is - 1.25",
        accepted=True,
        ruling=R12_W,
    ),
    QuoteCase(
        "b3-letter-wrap-text",
        "wrap",
        "text",
        _LETTER_WRAP_PAGE,
        "The Term Loan A-\n25 notes",
        "A- 25",
        accepted=False,
        ruling=R11_B3,
        twin="b3-letter-joined-text",
    ),
    QuoteCase(
        "b3-letter-joined-text",
        "wrap",
        "text",
        _LETTER_WRAP_PAGE,
        "The Term Loan A-25 notes",
        "A-25",
        accepted=True,
        ruling=R11_B3,
    ),
    QuoteCase(
        "b3-no-digit-wrap-text",
        "wrap",
        "text",
        _NO_DIGIT_WRAP_PAGE,
        "The rate a -\nb applies",
        "a - b",
        accepted=False,
        ruling=R11_B3,
        twin="b3-no-digit-joined-text",
    ),
    QuoteCase(
        "b3-no-digit-joined-text",
        "wrap",
        "text",
        _NO_DIGIT_WRAP_PAGE,
        "The rate a -b applies",
        "a -b",
        accepted=True,
        ruling=R11_B3,
    ),
    QuoteCase(
        "b3-index-0-letter-wrap-text",
        "wrap",
        "text",
        _INDEX0_LETTER_PAGE,
        "The Term Loan A-\n1.25 notes",
        "- 1.25 notes",
        accepted=False,
        ruling=R11_B3,
        twin="b3-index-0-letter-joined-text",
    ),
    QuoteCase(
        "b3-index-0-letter-joined-text",
        "wrap",
        "text",
        _INDEX0_LETTER_PAGE,
        "The Term Loan A-1.25 notes",
        "-1.25 notes",
        accepted=True,
        ruling=R11_B3,
    ),
    QuoteCase(
        "b3-index-0-digit-wrap-text",
        "wrap",
        "text",
        _INDEX0_DIGIT_PAGE,
        "In 2024-\n2025 notes",
        "- 2025 notes",
        accepted=False,
        ruling=R11_B3,
        twin="b3-index-0-digit-joined-text",
    ),
    QuoteCase(
        "b3-index-0-digit-joined-text",
        "wrap",
        "text",
        _INDEX0_DIGIT_PAGE,
        "In 2024-2025 notes",
        "-2025 notes",
        accepted=True,
        ruling=R11_B3,
    ),
)

_LABEL = "{label}"
_SHY_LABEL = "{shy_label}"
_FIG = "{figure}"


def _label_template(
    case_id: str, defect: Defect, text: str, ruling: str, twin: str | None = None
) -> QuoteCase:
    return QuoteCase(
        case_id, defect, "label", text, text, _FIG, accepted=twin is None, ruling=ruling, twin=twin
    )


LABEL_TEMPLATES: tuple[QuoteCase, ...] = (
    _label_template(
        "label-genuine", "genuine", f"Dealers quote the loan at {_LABEL} {_FIG}.", R10_SIGN
    ),
    _label_template(
        "shy-label", "soft_hyphen", f"Dealers quote the loan at {_SHY_LABEL} {_FIG}.", R9_M1
    ),
    _label_template(
        "nbsp-label", "nbsp", f"Dealers quote the loan at {_LABEL}{NBSP}{_FIG}.", R9_M1
    ),
    # The labelled figure is signed; the unsigned value occurs once elsewhere in the quote.
    _label_template(
        "sign-label",
        "signs",
        f"Dealers quote the loan at {_LABEL} {MINUS}{_FIG}, against {_FIG} a year ago.",
        R10_SIGN,
        twin="label-genuine",
    ),
)


def label_cases(label: str, figure: str = FIGURES[0]) -> tuple[QuoteCase, ...]:
    """The label cases for a module's label (`bid`, `spread`, ...) and figure: `{label}` is the
    label, `{shy_label}` the label with U+00AD after its first character, `{figure}` the figure
    (one of `FIGURES`, so the edge and sign structure of the family holds)."""
    if len(label) < 2 or not label[:2].isalpha():
        raise ValueError(f"a label needs two leading letters to carry a soft hyphen: {label!r}")
    if figure not in FIGURES:
        raise ValueError(f"a label case figure is one of {FIGURES}: {figure!r}")
    shy = label[0] + SOFT_HYPHEN + label[1:]

    def bind(text: str) -> str:
        return text.replace(_LABEL, label).replace(_SHY_LABEL, shy).replace(_FIG, figure)

    return tuple(
        replace(c, page=bind(c.page), quote=bind(c.quote), value=figure) for c in LABEL_TEMPLATES
    )


BLANK_VALUES = ("", "   ", "\n", " ", "\t ", ZWSP, BOM, SOFT_HYPHEN, f" {ZWSP}\n")


def _blank_ruling(value: str) -> str:
    return R12_B10 if any(unicodedata.category(ch) == "Cf" for ch in value) else R11_BLANK


BLANK_CASES: tuple[BlankCase, ...] = tuple(
    BlankCase(
        f"blank-{i}",
        value,
        f"The {NAME} is quoted by dealers.",
        NAME,
        value != "",
        _blank_ruling(value),
    )
    for i, value in enumerate(BLANK_VALUES)
)


def case(case_id: str, cases: Sequence[QuoteCase]) -> QuoteCase:
    """The case with this id (each id once)."""
    found = [c for c in cases if c.case_id == case_id]
    if len(found) != 1:
        raise KeyError(f"{len(found)} cases named {case_id}")
    return found[0]


def quote_failure(c: QuoteCase, adapter: Adapter, refusal: str) -> str | None:
    """None when the module's outcome is the case's; else what it did. `refusal` is the field's
    pinned issue for this case's value (for example `margin: bps_text 25 does not occur in the
    quote`)."""
    issues = tuple(adapter(c.page, c.quote, c.value))
    refused = refusal in issues
    if c.accepted and refused:
        return f"{c.case_id}: expected accepted, got {list(issues)}"
    if not c.accepted and not refused:
        return f"{c.case_id}: expected {refusal!r}, got {list(issues)}"
    return None


def _min_length_refusal(error: ValidationError) -> bool:
    return all(item["type"] == "string_too_short" for item in error.errors())


def blank_failure(c: BlankCase, adapter: Adapter, expected: str) -> str | None:
    """None when the module refuses the blank value as round 11 and fix 1 require; else what it
    did. Whitespace-only text needs `expected` (the pinned empty-text frame filled for the field,
    or `EMPTY_TEXT`). `""` needs any refusal: an issue, or the schema's `min_length` refusal
    raised as a `ValidationError` (only that error type is taken as the refusal; any other
    error propagates)."""
    if c.whitespace_only:
        issues = tuple(adapter(c.page, c.quote, c.value))
        if expected in issues:
            return None
        return f"{c.case_id} {c.value!r}: expected {expected!r}, got {list(issues)}"
    try:
        issues = tuple(adapter(c.page, c.quote, c.value))
    except ValidationError as error:
        if _min_length_refusal(error):
            return None  # the existing schema refusal of "" stands (controller, library fix 1)
        raise
    return None if issues else f"{c.case_id} {c.value!r}: expected a refusal, got []"


# --- Stage 2 round 1 Q5: hostile stored text raises only ValueError --------------------------

HOSTILE_JSON: Mapping[str, str] = {
    "deep_array": "[" * 200_000,
    "deep_object": '{"a":' * 50_000 + "1" + "}" * 50_000,
    "huge_int": '{"x":1' + "0" * 200_000 + "}",
    "nan": '{"x":NaN}',
    "lone_surrogate": '{"x":"\\ud800"}',
    "not_object": '"text"',
    "dup_keys": '{"x":1,"x":2}',
    "empty": "",
}
"""The inputs of LEAD's Q5 probe, verbatim."""


def _str_fields(schema: type[BaseModel]) -> list[str]:
    return [
        name
        for name, field in schema.model_fields.items()
        if field.annotation is str or "str" in repr(field.annotation)
    ]


def _one_field(field: str, text: str) -> str:
    return json.dumps({field: text}, separators=(",", ":"))


def hostile_inputs(schema: type[BaseModel]) -> dict[str, str]:
    """`HOSTILE_JSON` plus, for the schema's first five string fields, a bracket flood and a
    `{a|b}` flood in that field (the probe's per-field inputs)."""
    texts = dict(HOSTILE_JSON)
    for field in _str_fields(schema)[:5]:
        texts[f"field_{field}_brackets"] = _one_field(field, "{" * 50_000 + "|" * 10)
        texts[f"field_{field}_refs"] = _one_field(field, "{a|b}" * 20_000)
    return texts


def assert_hostile_refused(schema: type[BaseModel]) -> None:
    """Run every hostile input through `schema.model_validate_json`. A `ValueError` subclass
    (pydantic's `ValidationError` is one) is the refusal and an acceptance is not a failure here;
    any other exception propagates with its own class and traceback."""
    for text in hostile_inputs(schema).values():
        try:
            schema.model_validate_json(text)
        except ValueError:
            continue


# --- Stage 2 round 3 item 2: model text that passes the validator then fails a build ---------

MODEL_TEXT_HOSTILE = ("Rates matter [a lot", "{low", "{}")
TextPath = tuple[str | int, ...]
_NOT_FREE = ("pattern", "enum", "const", "format")


def _resolve(node: Mapping[str, Any], defs: Mapping[str, Any]) -> Mapping[str, Any]:
    while "$ref" in node:
        node = defs[node["$ref"].rsplit("/", 1)[-1]]
    if "allOf" in node and len(node["allOf"]) == 1:
        return _resolve(node["allOf"][0], defs)
    return node


def _walk(
    node: Mapping[str, Any],
    value: Any,
    path: TextPath,
    defs: Mapping[str, Any],
    out: list[TextPath],
) -> None:
    node = _resolve(node, defs)
    for key in ("anyOf", "oneOf"):
        for branch in node.get(key, ()):
            _walk(branch, value, path, defs, out)
    if isinstance(value, str):
        free = node.get("type") == "string" and not any(k in node for k in _NOT_FREE)
        if free and path not in out:
            out.append(path)
    elif isinstance(value, dict):
        props = node.get("properties", {})
        extra = node.get("additionalProperties")
        for key, item in value.items():
            if key in props:
                _walk(props[key], item, (*path, key), defs, out)
            elif isinstance(extra, dict):
                _walk(extra, item, (*path, key), defs, out)
    elif isinstance(value, list):
        prefix = node.get("prefixItems", ())
        items = node.get("items")
        for i, item in enumerate(value):
            if i < len(prefix):
                _walk(prefix[i], item, (*path, i), defs, out)
            elif isinstance(items, dict):
                _walk(items, item, (*path, i), defs, out)


def free_text_paths(payload: Any, schema: type[BaseModel]) -> list[TextPath]:
    """Every path in `payload` (parsed JSON, or its text) whose schema type is a free string: a
    JSON-schema `string` with no pattern, enum, const or format (so identifiers, hashes, dates and
    literals are not free text). Read from `schema.model_json_schema()`, so a new field is covered
    without a name here. Each path is a tuple of keys and list indices."""
    parsed = json.loads(payload) if isinstance(payload, str) else payload
    document = schema.model_json_schema()
    out: list[TextPath] = []
    _walk(document, parsed, (), document.get("$defs", {}), out)
    return out


def with_text(payload: Any, path: TextPath, value: str) -> Any:
    """A deep copy of `payload` (parsed JSON) with the string at `path` replaced by `value`."""
    changed = copy.deepcopy(payload)
    node = changed
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value
    return changed


class ReviewRun(Protocol):
    """A run at the step under test: `OwnerWorkflow` over a real store, or a module's `submit`
    seam wrapped to the same outcome (`status`, `issues`)."""

    def submit_review(self, payload: str) -> Mapping[str, Any]: ...


def _dotted(path: TextPath) -> str:
    return ".".join(str(step) for step in path)


def path_matches(pattern: tuple[str | int, ...], path: TextPath) -> bool:
    """`pattern` names `path`: the same length and keys, with `"*"` standing for any list index."""
    return len(pattern) == len(path) and all(
        p == q or (p == "*" and isinstance(q, int)) for p, q in zip(pattern, path, strict=True)
    )


def model_text_failures(
    schema: type[BaseModel],
    positive: str,
    fresh: Callable[[], ReviewRun],
    *,
    values: Sequence[str] = MODEL_TEXT_HOSTILE,
    verbatim: frozenset[tuple[str | int, ...]] = frozenset(),
) -> list[str]:
    """Round 3 item 2 and round 5 item 10: for each free-text path of the module's `positive`
    payload and each hostile value, on a `fresh()` run at the step: the outcome lists an issue and
    is not `valid`, and a following submission of `positive` is `valid`, so the run is not wedged
    on `stale_binding`.

    `verbatim` is the module's explicit set of path patterns (`"*"` for a list index) whose value
    is stored as plain text and is never built as `RunText` or `Claim.text` downstream; the module
    records each path's sink beside the set. Only on those paths is a `valid` outcome allowed (the
    step is then done, so no wedge check). Every other path must journal an issue. A pattern that
    names no path of the payload is a failure, so the set cannot rot.

    `fresh()` returns a run whose `submit_review` does whatever the module needs before a submit
    (reads), since a refused attempt re-activates the step. A raise, from the hostile submit or the
    follow-up, propagates as the failure. Returns the non-raising failures as
    `<path>=<value>: <what>` (accepted, no issue, wedged, unused verbatim); `[]` when none."""
    payload = json.loads(positive)
    failures: list[str] = []
    paths = free_text_paths(payload, schema)
    failures.extend(
        f"{'.'.join(map(str, pattern))}: verbatim pattern names no path of the payload"
        for pattern in sorted(verbatim, key=str)
        if not any(path_matches(pattern, path) for path in paths)
    )
    for path in paths:
        allowed = any(path_matches(pattern, path) for pattern in verbatim)
        for value in values:
            label = f"{_dotted(path)}={value!r}"
            run = fresh()
            text = json.dumps(with_text(payload, path, value), ensure_ascii=False)
            outcome = run.submit_review(text)  # a raise propagates: it is the failure
            if outcome["status"] == "valid":
                if not allowed:
                    failures.append(f"{label}: accepted")
                continue  # taken verbatim and the step is done: nothing to wedge
            if not outcome["issues"]:
                failures.append(f"{label}: {outcome['status']} with no issue")
            followed = run.submit_review(positive)["status"]  # a raise propagates
            if followed != "valid":
                failures.append(f"{label}: wedged, valid payload was {followed}")
    return failures
