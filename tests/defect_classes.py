"""Shared defect-class cases (AGENTS.md rules 3 and 4; LEAD round 11): data and assertions.

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
- `R11_B1`: round 11 Quote readers B1. A figure at an edge of `normalise(quote)` occurs only if it
  is the same unsigned whole figure on the page (start edge: not a digit, `.`, minus or closed
  accounting `(` before it; end edge: not a digit, `.` plus a digit, or closing `)` after it).
- `R11_B3`: round 11 Quote readers B3. When `quotes.hyphen_wrapped(quote)` holds and `"- "` occurs
  in `normalise(value)`, a name or text value does not occur in the quote.
- `R9_M1`: round 9 CP-8 heading ("M1's normalised quote applies to every new check") with round 11
  "Shared class test": a figure, label or name is read on the text `quotes.quoted` matched, so a
  soft hyphen, mapped dash or NBSP reads as the page shows it.
- `R11_BLANK`: round 11 "Blank text is one defect class". Every analyst text field refuses
  whitespace-only text with the module's pinned empty-text frame, or `<path>: empty text`.

Outcomes. A refused case expects the field's pinned refusal (passed in by the module, usually its
"does not occur in the quote" frame) among the issues. An accepted case expects that refusal to be
absent; other issues the field's own bounds or shape raise for the value are outside these classes.
Every refused case names an accepted twin with the same value whose page prints it plainly.

Cases the rulings do not pin are not here (listed in the inventory report), for example a value
carrying its own soft hyphen, or a joined value against a wrapped quote.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Literal

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

R10_SIGN = "Round 10 §1 (read the sign)"
R10_PARENS = "Round 10 For LEAD: Parentheses"
R11_B1 = "Round 11 Quote readers B1 (edge cut)"
R11_B3 = "Round 11 Quote readers B3 (wrap refusal)"
R9_M1 = "Round 9 CP-8 M1 normalised quote; round 11 shared class test"
R11_BLANK = "Round 11 LEAD rulings: Blank text is one defect class"

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
    twin: str | None = None  # an accepted case with the same value (refused cases only)


@dataclass(frozen=True)
class BlankCase:
    case_id: str
    value: str
    page: str  # a genuine page and quote, for a field whose text must sit beside a quote
    quote: str
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
    """The cases built the same way for figure `f`; ids end in `-<f>`, twins are `genuine-<f>`."""
    twin = f"genuine-{f}"
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
        # Edge cut (round 11 B1): the figure touches an edge of the normalised quote.
        _figure(
            f"edge-prefix-{f}", "edge_cut", _level(f"4{f}"), f, R11_B1, quote=f + rest, twin=twin
        ),
        _figure(
            f"edge-minus-{f}", "edge_cut", _level(f"-{f}"), f, R11_B1, quote=f + rest, twin=twin
        ),
        _figure(
            f"edge-close-paren-{f}",
            "edge_cut",
            _level(f"({f})"),
            f,
            R11_B1,
            quote=f"{f}){rest}",
            twin=twin,
        ),
        _figure(
            f"edge-open-paren-{f}",
            "edge_cut",
            _level(f"({f})"),
            f,
            R11_B1,
            quote=f"The level is ({f}",
            twin=twin,
        ),
        _figure(
            f"edge-end-digit-{f}",
            "edge_cut",
            _level(f"{f}0"),
            f,
            R11_B1,
            quote=f"The level is {f}",
            twin=twin,
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
    # The round 11 B1 examples with their own figures.
    _figure(
        "edge-10",
        "edge_cut",
        _level("10"),
        "0",
        R11_B1,
        quote="0 percent over the reference rate.",
        twin="genuine-0",
    ),
    _figure(
        "edge-minus-0.25",
        "edge_cut",
        _level("-0.25"),
        "0.25",
        R11_B1,
        quote="0.25 percent over the reference rate.",
        twin="genuine-0.25",
    ),
    _figure(
        "edge-end-decimal",
        "edge_cut",
        _level("25.5"),
        "25",
        R11_B1,
        quote="The level is 25",
        twin="genuine-25",
    ),
)


NAME = "Northbridge Term Loan"
_WRAP_PAGE = "The Northbridge first-\npriority Term Loan is quoted by dealers."

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


BLANK_VALUES = ("", "   ", "\n", " ", "\t ")
BLANK_CASES: tuple[BlankCase, ...] = tuple(
    BlankCase(f"blank-{i}", value, f"The {NAME} is quoted by dealers.", NAME)
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


def blank_failure(c: BlankCase, adapter: Adapter, expected: str) -> str | None:
    """None when the module refuses the blank value with `expected` (its pinned empty-text frame
    filled for the field, or `EMPTY_TEXT`); else what it did."""
    issues = tuple(adapter(c.page, c.quote, c.value))
    if expected in issues:
        return None
    return f"{c.case_id} {c.value!r}: expected {expected!r}, got {list(issues)}"
