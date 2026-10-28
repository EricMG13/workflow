"""CP-1D (Earnings quality): the Stage 1 calculation, pure over typed inputs.

`docs/CP1D-OWNER-LEASE.md` (frozen revision 3) fixes the Method: Python reads the management
bridge table, applies the analyst's achievability, recurrence and accepted basis or fraction,
and restates the bridge, the add-back shares, cash conversion and leverage on three bases
(statements, management financing case, supported). The oracle is
`cases/cp1d-owner/expected.json`.

Arithmetic is exact `Decimal`: sums, differences and products trap any rounding; every
quotient is one division correctly rounded to 38 significant digits, half-even. Display
spelling is `deploy_vii.display.format_value`. A missing amount stays `None` and never becomes
0; a 0 that the rules produce is a known 0.

No I/O, store, host, session or render call happens here (Stage 2 adds those).
"""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, InvalidOperation, Rounded
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from deploy_vii.business_context import (
    CP1_REFERENCES,
    Category,
    Confidence,
    Severity,
    spelled,
)
from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Input,
    Module,
    ReportTable,
    RunText,
    Source,
    TableColumn,
    Text,
)
from deploy_vii.contracts import Run as PackRun
from deploy_vii.contracts import TableRow as ReportRow
from deploy_vii.display import UnitClass, format_value
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Qualification,
    StepValidation,
    clipped,
    current_inputs,
    inherited_limitations,
    listed_issues,
    settle,
)
from deploy_vii.financial_contracts import Number
from deploy_vii.live.submission import Submitted
from deploy_vii.live.tools import Seen, unread_citation_issues
from deploy_vii.preparation import PreparedPack
from deploy_vii.prose import Run as ProseRun
from deploy_vii.prose import bind, tokenize
from deploy_vii.prose import issues as prose_issues
from deploy_vii.quotes import hyphen_wrapped, normalise, reading
from deploy_vii.readiness import citation_issues, shape_issues
from deploy_vii.report_view import figure_unit, scale_label
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-1D"
BRIDGE_SOURCE_ID = "bridge"

Achievability = Literal["Supported", "Partly supported", "Not supported", "Insufficient evidence"]
Recurrence = Literal["Non-recurring", "Recurring", "Not applicable", "Not assessable"]
Cp1bState = Literal["unbound", "settled", "blocked"]
FactStatus = Literal["known", "missing", "not_applicable"]
ValueClass = Literal["source", "calculated", "analyst_judgment"]
CellState = Literal["known", "gap", "not_meaningful"]

# --- submission schema (reference and judgment only; no computed number) ----------------------


class Assessment(Contract):
    addback: Text
    achievability: Achievability
    recurrence: Recurrence
    accepted_fraction: str | None
    accepted_basis: Citation | None
    category: Category
    rationale: Text
    evidence: tuple[Citation, ...]
    limitation: str | None


class Overall(Contract):
    rationale: Text
    category: Category
    confidence: Confidence
    limitation: str | None
    evidence: tuple[Citation, ...]


class Gap(Contract):
    gap: Text
    why_it_matters: Text
    affected_analysis: Text
    severity: Severity
    action: Text


class EarningsQualitySubmission(Contract):
    assessments: tuple[Assessment, ...]
    overall: Overall
    gaps: tuple[Gap, ...]


# --- inputs ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cp1Figure:
    """One CP-1 T4.10 fact (manifest `cp1_fact_selection_rule`), referenced as `cp1:<figure>`;
    `fact_id` is that CP-1 fact's own id."""

    fact_id: str
    figure: str
    label: str
    unit: str
    period: str
    amount: Decimal | None
    value_class: ValueClass
    currency: str | None = None
    status: FactStatus = "known"
    limitation: str | None = None

    def __post_init__(self) -> None:
        if (self.status == "known") != (self.amount is not None):
            raise ValueError(f"CP-1 figure {self.figure}: a known figure has an amount")
        if self.status != "known" and not self.limitation:
            raise ValueError(f"CP-1 figure {self.figure}: an unsettled figure needs a limitation")
        if self.amount is None:
            return
        if self.unit == "MULTIPLE" and not _is_cp1_ratio(self.amount):
            raise ValueError(f"CP-1 figure {self.figure}: not a CP-1 quotient of product Numbers")
        if self.unit != "MULTIPLE" and not _is_number(self.amount):  # round 5b Y1: an invariant
            raise ValueError(
                f"CP-1 fact {self.fact_id} ({self.figure}) is outside financial_contracts.Number; "
                "CP-1D cannot hold it exactly"
            )

    @property
    def value(self) -> Decimal:
        """The amount of an operand `Cp1Operands` requires to be known."""
        if self.amount is None:
            raise ValueError(f"CP-1 figure {self.figure} is not known")
        return self.amount

    @property
    def reason(self) -> str:
        """CP-1's own limitation of an unsettled figure."""
        if not self.limitation:
            raise ValueError(f"CP-1 figure {self.figure} has no limitation")
        return self.limitation


_CP1_FIGURES = (
    ("adjusted_ebitda", "adjusted_ebitda_ltm", "MILLIONS"),
    ("ebitda", "ebitda_ltm", "MILLIONS"),
    ("cfo", "cfo_ltm", "MILLIONS"),
    ("total_debt", "total_debt_ltm", "MILLIONS"),
    ("net_debt", "net_debt_ltm", "MILLIONS"),
    ("total_leverage", "total_leverage_adjusted", "MULTIPLE"),
    ("net_leverage", "net_leverage_adjusted", "MULTIPLE"),
)


@dataclass(frozen=True)
class Cp1Operands:
    """The seven CP-1 operands, LTM Q4 25 column (lease: Operands)."""

    adjusted_ebitda: Cp1Figure
    ebitda: Cp1Figure
    cfo: Cp1Figure
    total_debt: Cp1Figure
    net_debt: Cp1Figure
    total_leverage: Cp1Figure
    net_leverage: Cp1Figure

    def __post_init__(self) -> None:
        figures = self.ordered()
        for (attribute, name, unit), figure in zip(_CP1_FIGURES, figures, strict=True):
            if figure.figure != name or figure.unit != unit:
                raise ValueError(f"CP-1 operand {attribute} must be {name} in {unit}")
        if len({f.period for f in figures}) != 1:
            raise ValueError("CP-1 operands must share one period")
        if any(f.status != "known" for f in figures if f.unit == "MILLIONS"):
            raise ValueError("CP-1 amount operands must be known")
        currencies = {f.currency for f in figures if f.unit == "MILLIONS"}
        if len(currencies) != 1 or None in currencies:
            raise ValueError("CP-1 amount operands must share one stated currency")

    def ordered(self) -> tuple[Cp1Figure, ...]:
        return tuple(getattr(self, attribute) for attribute, _, _ in _CP1_FIGURES)


@dataclass(frozen=True)
class EarningsQualityInputs:
    """Everything the Method reads.

    `sources` are the pack sources in the host scope (the bridge, when present, has source id
    `bridge`); `cp1b` is CP-1B's binding state, which only selects the own limitation line.
    """

    sources: tuple[Source, ...]
    cp1: Cp1Operands
    submission: EarningsQualitySubmission
    cp1b: Cp1bState = "unbound"


# --- outputs --------------------------------------------------------------------------------


@dataclass(frozen=True)
class CellFact:
    """One table cell as a fact (`expected.json cell_notation`)."""

    fact_id: str
    table_id: str
    row_id: str
    field: str
    label: str
    status: FactStatus
    unit: str | None = None
    period: str | None = None
    amount: Decimal | None = None
    text: str | None = None
    shown: str | None = None
    currency: str | None = None
    scale: Decimal | None = None
    decimals: int | None = None
    value_class: ValueClass | None = None
    formula: str | None = None
    calculation_id: str | None = None
    derives_from: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()
    limitation: str | None = None

    @property
    def amount_exact(self) -> str | None:
        return None if self.amount is None else exact_text(self.amount)

    @property
    def cell_state(self) -> CellState:
        """`report_view.fact_spelling` state: missing -> gap, not_applicable -> not_meaningful."""
        if self.status == "known":
            return "known"
        return "not_meaningful" if self.status == "not_applicable" else "gap"

    def record(self) -> dict[str, object]:
        """Every field with exact decimals as canonical text (`amount_exact`, `scale`)."""
        return {
            "fact_id": self.fact_id,
            "table_id": self.table_id,
            "row_id": self.row_id,
            "field": self.field,
            "label": self.label,
            "status": self.status,
            "unit": self.unit,
            "period": self.period,
            "amount_exact": self.amount_exact,
            "text": self.text,
            "shown": self.shown,
            "currency": self.currency,
            "scale": None if self.scale is None else exact_text(self.scale),
            "decimals": self.decimals,
            "value_class": self.value_class,
            "formula": self.formula,
            "calculation_id": self.calculation_id,
            "derives_from": self.derives_from,
            "citations": self.citations,
            "limitation": self.limitation,
        }

    def to_fact(self) -> Fact:
        """The product `Fact` (used to bind run-text references)."""
        return Fact(
            fact_id=self.fact_id,
            label=self.label,
            table_id=self.table_id,
            row_id=self.row_id,
            field=self.field,
            amount=self.amount,
            text=self.text,
            status=self.status,
            unit=self.unit,
            currency=self.currency,
            scale=Decimal(1) if self.scale is None else self.scale,
            decimals=self.decimals,
            period=self.period,
            citations=self.citations,
            calculation_id=self.calculation_id,
            value_class=self.value_class,
            formula=self.formula,
            limitation=self.limitation,
        )


@dataclass(frozen=True)
class TableRow:
    row_id: str
    label: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class Cp1Reference:
    """A `cp1_references` row: a CP-1 figure the module's facts or prose name."""

    row_id: str
    figure: str
    label: str
    unit: str
    period: str
    amount: Decimal | None
    shown: str | None
    value_class: ValueClass
    status: FactStatus = "known"

    @property
    def amount_exact(self) -> str | None:
        return None if self.amount is None else exact_text(self.amount)


@dataclass(frozen=True)
class ClaimDraft:
    """A claim: analyst rationale (with its evidence) or a Python template (evidence None)."""

    claim_id: str
    text: str
    limitation: str | None
    evidence: tuple[Citation, ...] | None = None


@dataclass(frozen=True)
class BridgeSourceRef:
    source_id: str
    sha256: str
    pages: int


@dataclass(frozen=True)
class EarningsQualityResult:
    bridge_source: BridgeSourceRef | None
    operands: tuple[tuple[str, Decimal], ...]
    operands_unavailable: tuple[str, ...]
    facts: tuple[CellFact, ...]
    tables: tuple[Table, ...]
    cp1_references: tuple[Cp1Reference, ...]
    claims: tuple[ClaimDraft, ...]
    limitations: tuple[str, ...]


# --- bridge table (lease: Bridge parsing) ---------------------------------------------------

_BASIS_LINE = "Basis: FY2025 (January 1-December 31, 2025)"
_HEADER = "Item  Type  Status  Amount"
_PROPOSED_TOTAL = "Total proposed adjustments"
_MANAGEMENT_EBITDA = "Management financing-case EBITDA"
_NOT_STATED = "Not stated"
_AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]+)?")
# Round 10 (LEAD), amended by round 12 rule W: a basis amount is the signed numeral the
# normalised quote prints. A "-" directly before the first digit, or one space before it (any
# whitespace, a line break included, since `normalise` makes a whitespace run one space), is a
# minus when it starts the quote or follows a character that is neither a letter nor a digit (so
# `1-December`, `2024-2025`, `2024-\n2025`, `S-350` are unsigned); "+" is ignored; a numeral in
# accounting parentheses, "(" or "( " before the first digit and ")" or " )" after the last,
# reads as negative. The amount string stays `-<digits>`. The bridge table keeps `_AMOUNT`.
# Round 13 items 7 and 8: a figure is a whole numeral run. None starts after a digit, a point, or
# a digit and a comma (with at most one space), and none ends before a digit, a point and a
# digit, or a comma (with at most one space) and a digit; so `.25`, `-.25`, `(.25)`, `1.2.5`,
# `1,250`, `1, 250` and `1,\n250` hold no figure. The grammar takes no separators in Stage 1.
_SIGNED_AMOUNT = re.compile(
    r"\( ?(?P<parenthesised>[0-9]+(?:\.[0-9]+)?) ?\)"
    r"|(?P<sign>(?<![A-Za-z0-9])- ?)?(?<![0-9.])(?<![0-9],)(?<![0-9], )"
    r"(?P<digits>[0-9]+(?:\.[0-9]+)?)(?![0-9]|[.,][0-9]|, [0-9])"
)
# Round 13 addendum 4 (fail closed): a numeral run is a maximal run of digits joined by ".", ","
# or ", ", with a leading point. Step 5 needs exactly one run in each reading of the quote and
# that run whole, so a figure hidden inside a longer run (`1,250`, `1.2.5`, `.25`) or a second
# run beside the one read (a date, a section number) never lets exactly-one vouch for the rest.
_NUMERAL_RUN = re.compile(r"\.?[0-9]+(?:(?:\.|, ?)[0-9]+)*")
_WHOLE_RUN = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_TYPES = ("Saving", "Cost")
# Round 4 (k): an amount is the product `financial_contracts.Number` (-1e18 < x < 1e18, 28
# digits, 10 places). Bridge amounts, quoted basis amounts and CP-1 amount operands hold it, so
# every sum and product here is exact and every value spells exactly (`display.format_value`).
_NUMBER: TypeAdapter[Decimal] = TypeAdapter(Number)
_NUMBER_LIMIT = Decimal("1e18")  # financial_contracts.Number: -1e18 < x < 1e18
# A CP-1 ratio is CP-1's own 38-digit quotient of two such Numbers, so its magnitude lies
# between 1e-29 and 1e29 (or it is 0); the T1D.4 difference against it stays exact.
_RATIO_DIGITS = 38
_RATIO_ADJUSTED = 29


def _line(prefix: str, quoted: str) -> str:
    """An issue line that quotes caller or pack text: cut to `MAX_ISSUE_CHARS` before it is
    built whole (protocol section 6; identical to the plain line when it is short)."""
    return clipped((prefix, quoted))


def _bounded(found: Iterable[str]) -> tuple[str, ...]:
    """At most `MAX_ISSUES` lines, the last counting the rest (`execution.listed_issues`)."""
    return listed_issues(found, lambda line: (line,), lambda n: f"{n} further issues not listed")


def _is_number(value: Decimal) -> bool:
    try:
        _NUMBER.validate_python(value)
    except ValidationError:
        return False
    return True


def _is_cp1_ratio(value: Decimal) -> bool:
    return (
        value.is_finite()
        and len(value.as_tuple().digits) <= _RATIO_DIGITS
        and (value == 0 or -_RATIO_ADJUSTED <= value.adjusted() < _RATIO_ADJUSTED)
    )


_FIELDS = re.compile(r" {2,}")


@dataclass(frozen=True)
class BridgeItem:
    row_id: str
    label: str
    type: str
    status: str
    amount: Decimal | None
    line: str


@dataclass(frozen=True)
class Bridge:
    items: tuple[BridgeItem, ...]
    proposed_total: Decimal | None
    management_ebitda: Decimal | None
    proposed_total_line: str | None = None
    management_ebitda_line: str | None = None


class _Unparseable(ValueError):
    pass


def _bridge_amount(token: str) -> Decimal | None:
    if token == _NOT_STATED:
        return None
    if not _AMOUNT.fullmatch(token) or not _is_number(amount := Decimal(token)):
        raise _Unparseable(token)
    return amount


def parse_bridge(pages: Sequence[str]) -> Bridge | None:
    """The bridge table on page:1, or None when it cannot be read (`Bridge table not found`).

    Page:1 must have a line starting with the FY2025 basis and the exact header line; every
    later line splits on two or more spaces into an item (4 fields, type Saving or Cost) or one
    of the two stated totals (2 fields). An amount is a decimal of at most 38 digits or
    `Not stated` (missing, never 0). Rulings 1D4, 1D5, 1D9: anything else, a duplicate label or
    total, or no item row at all, is not a bridge table.
    """
    lines = pages[0].split("\n") if pages else []
    if not any(line.startswith(_BASIS_LINE) for line in lines) or _HEADER not in lines:
        return None
    items: list[BridgeItem] = []
    totals: dict[str, Decimal | None] = {}
    total_lines: dict[str, str] = {}
    try:
        for line in lines[lines.index(_HEADER) + 1 :]:
            parts = _FIELDS.split(line)
            if len(parts) == 4:
                label, kind, status, amount = parts
                if kind not in _TYPES:
                    return None
                row_id = f"a{len(items) + 1:02d}"
                items.append(BridgeItem(row_id, label, kind, status, _bridge_amount(amount), line))
            elif len(parts) == 2 and parts[0] in (_PROPOSED_TOTAL, _MANAGEMENT_EBITDA):
                if parts[0] in totals:
                    return None
                totals[parts[0]] = _bridge_amount(parts[1])
                total_lines[parts[0]] = line
            else:
                return None
    except _Unparseable:
        return None
    if not items or len({item.label for item in items}) != len(items):
        return None
    return Bridge(
        tuple(items),
        totals.get(_PROPOSED_TOTAL),
        totals.get(_MANAGEMENT_EBITDA),
        total_lines.get(_PROPOSED_TOTAL),
        total_lines.get(_MANAGEMENT_EBITDA),
    )


# --- arithmetic and spelling ----------------------------------------------------------------

_QUOTIENT = Context(prec=38, rounding=ROUND_HALF_EVEN)
_EXACT = Context(prec=200, traps=[Inexact, Rounded, InvalidOperation])
_UNIT_CLASS: dict[str, UnitClass] = {
    "MILLIONS": "amount",
    "PERCENT": "percent",
    "MULTIPLE": "multiple",
}
_SCALE = {"MILLIONS": Decimal(1000000)}


def exact_text(value: Decimal) -> str:
    """Canonical exact decimal: plain notation, no trailing zeros, unsigned zero."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _quotient(numerator: Decimal, denominator: Decimal) -> Decimal:
    """One division of exact decimals, correctly rounded to 38 digits half-even."""
    return _QUOTIENT.divide(numerator, denominator)


def _sum(values: Iterable[Decimal]) -> Decimal:
    total = Decimal(0)
    for value in values:
        total = _EXACT.add(total, value)
    return total


def _spell(amount: Decimal, unit: str, decimals: int | None) -> str:
    return format_value(amount, _UNIT_CLASS[unit], "known", decimals=decimals)


# --- per-assessment outcome -----------------------------------------------------------------

_ACCEPTING = ("Supported", "Partly supported")
_FRACTION = re.compile(r"0\.[0-9]{1,2}")
_TREATMENT = {
    "Supported": "Accepted in full",
    "Partly supported": "Accepted in part",
    "Not supported": "Excluded: not supported",
    "Insufficient evidence": "Excluded: insufficient evidence",
}


def _accepts(assessment: Assessment) -> bool:
    """The rules give a share above 0 (Recurring forces 0)."""
    return assessment.achievability in _ACCEPTING and assessment.recurrence != "Recurring"


def _basis_amounts(citation: Citation, sources: Sequence[Source]) -> list[str]:
    """The signed amounts in the quote as `citation_issues` matched it (`quotes.normalise`:
    U+00AD removed, so a soft hyphen inside a figure does not split it; U+2212 and the dashes
    read as "-"), each as a decimal string (round 10 with round 12 rule W, `_SIGNED_AMOUNT`).

    Round 11 B1: an amount at an edge of the normalised quote (nothing or only "-" before its
    digits, nothing or only "." after them) is not counted when an occurrence of the quote on its
    cited page shows it cut from a longer or signed figure (`_edge_cut`); step 5's exactly-one
    rule then refuses the quote. A quote that is not on its page has no occurrence to show a cut:
    the citation check refuses it."""
    needle = normalise(citation.quote)
    page = _cited_text(citation, sources)
    amounts: list[str] = []
    for match in _SIGNED_AMOUNT.finditer(needle):
        if match["parenthesised"] is not None:
            amounts.append(f"-{match['parenthesised']}")
            continue
        start, end = match.span("digits")
        at_start = needle[:start] in ("", "-", ",", ", ")
        at_end = needle[end:] in ("", ".", ",")
        edge = at_start or at_end
        if (
            edge
            and page is not None
            and _edge_cut(citation.quote, page, (start, end), at_start=at_start, at_end=at_end)
        ):
            continue  # round 11 B1: cut from a longer or signed page figure, so not counted
        amounts.append(f"{'-' if match['sign'] else ''}{match['digits']}")
    return amounts


def _one_whole_run(quote: str) -> bool:
    """Addendum 4 and 5: each reading of the quote (`_readings`) holds exactly one numeral run
    and it is whole and readable. Fail closed: a numeric character (`isnumeric`) outside ASCII
    0-9 fails; a run a letter or a Cf/Mn/Me character touches on its left is an identifier
    (`Q2`, `FY25`); a run directly followed by an ordinal suffix is an ordinal (`2nd`). Other
    letters after a run leave it readable (`2.5m`, `25bps`)."""
    for reading_text in _readings(quote):
        if any(not ("0" <= char <= "9") and char.isnumeric() for char in reading_text):
            return False
        runs = list(_NUMERAL_RUN.finditer(reading_text))
        if len(runs) != 1 or _WHOLE_RUN.fullmatch(runs[0].group()) is None:
            return False
        before = reading_text[: runs[0].start()][-1:]
        if _touches_before(before):  # the one seam for the before-rule
            return False
        if _ordinal_after(reading_text, runs[0].end()):
            return False
    return True


# Addendum 5: a run directly followed by st, nd, rd or th (any case) and then no letter is an
# ordinal; it counts toward exactly-one but cannot be read.
_ORDINAL_AFTER = re.compile(r"(?:st|nd|rd|th)(?![^\W\d_])", re.IGNORECASE)


_SKIPPED = ("Cf", "Mn", "Me")
_SUFFIX_WINDOW = 32


def _ordinal_after(text: str, end: int) -> bool:
    """Stage 2 L3 (LEAD): after the run, Cf/Mn/Me characters are skipped and the suffix window
    is NFKC-folded, so `2ⁿᵈ`, `2ｎｄ`, `2<ZWSP>nd` and `2<Mn>nd` are ordinals like `2nd`; a letter
    after the folded suffix (`2nds`, `2ndly`) still leaves the run readable."""
    window = "".join(
        c for c in text[end : end + _SUFFIX_WINDOW] if unicodedata.category(c) not in _SKIPPED
    )
    return _ORDINAL_AFTER.match(unicodedata.normalize("NFKC", window)) is not None


def _touches_before(char: str) -> bool:
    """A letter, a Mn/Mc/Me/Cf character, or a character whose NFKC fold holds a letter (a
    circled letter), directly before a run touches it (`Q2`, `FY25`; Stage 2 I2)."""
    if not char:
        return False
    category = unicodedata.category(char)
    return (
        category[0] == "L"
        or category in ("Mn", "Mc", "Me", "Cf")
        or any(c.isalpha() for c in unicodedata.normalize("NFKC", char))
    )


def _cited_text(citation: Citation, sources: Sequence[Source]) -> str | None:
    """The raw text of the span the citation names, found as `citation_issues` finds it (the
    last source with that id, its first span with that locator); None when the pack has none."""
    source = {item.source_id: item for item in sources}.get(citation.source_id)
    if source is None:
        return None
    return next((span.text for span in source.spans if span.locator == citation.locator), None)


def _readings(raw: str) -> tuple[str, ...]:
    """The readings `quotes.quoted` compares: `normalise(raw)` and, when `raw` holds a hyphen
    wrap, the reading with its wraps joined (round 11 B1)."""
    plain = normalise(raw)
    return (plain, reading(raw, join_wraps=True).text) if hyphen_wrapped(raw) else (plain,)


# Round 12 rule W, matched as ending where the digits start: the round 10 minus directly before
# them or one space before them, and an accounting "(" with at most one space inside.
_W_MINUS = re.compile(r"(?<![A-Za-z0-9])- ?\Z")
_OPEN_PAREN = re.compile(r"\( ?\Z")
_CLOSE_PAREN = re.compile(r" ?\)")
_DIGIT_OR_POINT = re.compile(r"[0-9.]")
_CONTINUES = re.compile(r"[0-9]|[.,][0-9]|, [0-9]")
_COMMA_BEFORE = re.compile(r"[0-9],(?: )?\Z")


def _edge_cut(
    quote: str, page: str, digits: tuple[int, int], *, at_start: bool, at_end: bool
) -> bool:
    """Round 11 B1: whether, at some occurrence of the quote (as written, and with its wraps
    joined) in some reading of its page, the edge figure at `digits` of `normalise(quote)` is
    not the same unsigned whole figure on the page.

    Start edge: the page character before the digits is a digit or ".", or the page's characters
    before them are a digit and "," (round 13 item 8; one space may follow the comma), or the
    page holds a minus by rule W (round 12: directly or one space before them), or an accounting
    "(" or "( " that a ")" or " )" right after the digits closes. End edge: the page text after
    the digits is a digit, "." or "," plus a digit, ", " plus a digit, or a ")" or " )" closing a
    "(" or "( " right before them. A start-edge figure keeps its offsets in the joined quote and an end-edge one its offsets from
    the end, since a join only removes the spaces after a wrapped hyphen."""
    plain = normalise(quote)
    for needle in _readings(quote):
        shift = 0 if at_start else len(needle) - len(plain)
        start, end = digits[0] + shift, digits[1] + shift
        for text in _readings(page):
            at = text.find(needle)
            while at >= 0:
                if _cut(text, at + start, at + end, at_start=at_start, at_end=at_end):
                    return True
                at = text.find(needle, at + 1)
    return False


def _cut(text: str, start: int, end: int, *, at_start: bool, at_end: bool) -> bool:
    """B1's page test at one occurrence of the edge figure whose digits are `text[start:end]`
    (rule W: a sign or parenthesis may sit one space from them)."""
    lead = max(0, start - 2)  # the "- " or "( " ending at the digits; the lookbehind sees past it
    if _OPEN_PAREN.search(text, lead, start) and _CLOSE_PAREN.match(text, end):
        return True
    if at_start and (
        _DIGIT_OR_POINT.fullmatch(text[start - 1 : start]) is not None
        or _COMMA_BEFORE.search(text, max(0, start - 3), start) is not None
        or _W_MINUS.search(text, lead, start) is not None
    ):
        return True
    return at_end and _CONTINUES.match(text, end) is not None


@dataclass(frozen=True)
class _Outcome:
    item: BridgeItem
    assessment: Assessment
    path: Literal["source", "judgment", "rule"]
    fraction: Decimal
    basis: Decimal | None
    accepted: Decimal

    @property
    def treatment(self) -> str:
        if self.assessment.recurrence == "Recurring":
            return "Excluded: recurring"
        return _TREATMENT[self.assessment.achievability]


def _outcome(item: BridgeItem, assessment: Assessment, sources: Sequence[Source]) -> _Outcome:
    """Applied fraction and accepted amount of a shape-valid assessment (lease recipe table).

    Recurring forces f = 0 on any achievability (ruling 1D2); a cited basis amount is kept as
    evidence on that path, and an analyst fraction is not applied.
    """
    cited = assessment.accepted_basis
    if not _accepts(assessment):
        kept = None if cited is None else Decimal(_basis_amounts(cited, sources)[0])
        return _Outcome(item, assessment, "rule", Decimal(0), kept, Decimal(0))
    claimed = item.amount
    if claimed is None:
        raise ValueError(_line("Cannot accept an unstated amount: ", item.label))
    if assessment.achievability == "Supported":
        return _Outcome(item, assessment, "rule", Decimal(1), None, _EXACT.multiply(claimed, 1))
    if cited is not None:
        basis = Decimal(_basis_amounts(cited, sources)[0])
        return _Outcome(item, assessment, "source", _quotient(basis, claimed), basis, basis)
    if assessment.accepted_fraction is None:
        raise ValueError(_line("Partly supported without basis or fraction: ", item.label))
    fraction = Decimal(assessment.accepted_fraction)
    accepted = _EXACT.multiply(claimed, fraction)
    return _Outcome(item, assessment, "judgment", fraction, None, accepted)


def _shape_issue(item: BridgeItem, assessment: Assessment, sources: Sequence[Source]) -> str | None:
    """The first failing basis/fraction shape rule (`refusal_rules.basis_fraction_order`)."""
    label = item.label
    basis, fraction = assessment.accepted_basis, assessment.accepted_fraction
    if assessment.achievability != "Partly supported":
        if basis is not None:
            return _line("Accepted basis only applies to Partly supported: ", label)
        if fraction is not None:
            return _line("Accepted fraction only applies to Partly supported: ", label)
        return None
    if basis is not None and fraction is not None:
        return _line("Give either an accepted basis or an accepted fraction, not both: ", label)
    if basis is None and fraction is None:
        return _line("Accepted basis or accepted fraction required for Partly supported: ", label)
    if fraction is not None and not (_FRACTION.fullmatch(fraction) and Decimal(fraction) > 0):
        return _line(
            "Accepted fraction must be a decimal above 0 and below 1 with at most two places: ",
            label,
        )
    if basis is not None:
        amounts = _basis_amounts(basis, sources)
        if len(amounts) != 1 or not _one_whole_run(basis.quote):
            return _line("Accepted basis quote must contain exactly one amount: ", label)
        amount = Decimal(amounts[0])
        if item.amount is None and _accepts(assessment):
            return None  # ruling 1D7: the content rule `Cannot accept an unstated amount`
        # Fix round 2 N1 / round 5b Y4: an amount outside the product bound never composes. At
        # or above 1e18 against a stated proposed amount the bounds text is true; otherwise
        # (precision, or no stated proposed amount) the exactness text is. Round 10: "above 0"
        # applies on its own, so a signed amount at or below 0 gets the bounds text first, also
        # on an unstated proposed amount (the Recurring path).
        bounds = _line("Accepted basis must be above 0 and below the proposed amount: ", label)
        if amount <= 0:
            return bounds
        if not _is_number(amount):
            if item.amount is not None and amount >= _NUMBER_LIMIT:
                return bounds
            return _line(
                "Accepted basis amount cannot be held exactly as a product amount: ", label
            )
        if item.amount is not None and not amount < item.amount:
            return bounds
    return None


_FITS = {"Saving": ("Not applicable",), "Cost": ("Non-recurring", "Recurring", "Not assessable")}


def _rule_issues(item: BridgeItem, assessment: Assessment) -> list[str]:
    """Content rules of one shape-valid assessment in ruling 1D10's order: evidence,
    recurrence, unstated amount (citations and prose follow)."""
    label, recurrence = item.label, assessment.recurrence
    found: list[str] = []
    if _accepts(assessment) and not assessment.evidence:
        found.append(_line("Evidence required for an accepted add-back: ", label))
    if recurrence not in _FITS[item.type]:
        found.append(_line("Recurrence does not fit the add-back type: ", label))
    if recurrence == "Not assessable" and assessment.achievability != "Insufficient evidence":
        found.append(
            _line("Recurrence can be not assessable only with insufficient evidence: ", label)
        )
    if _accepts(assessment) and item.amount is None:
        found.append(_line("Cannot accept an unstated amount: ", label))
    return found


# --- composition ----------------------------------------------------------------------------

_TABLES = (
    ("T1D.1", "Add-back register"),
    ("T1D.2", "Add-back assessment"),
    ("T1D.3", "Adjusted EBITDA bridge"),
    ("T1D.4", "Source tie-out and CP-1 reconciliation"),
    ("T1D.5", "Add-back share"),
    ("T1D.6", "Cash conversion and restated leverage"),
    ("T1D.7", "Gaps ledger"),
)
_ASSESSMENT_FIELDS = (
    "achievability",
    "recurrence",
    "basis",
    "applied_fraction",
    "treatment",
    "accepted",
    "unsupported",
    "evidence",
)
_GAP_FIELDS = ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action")
_REGISTER_FIELDS = ("type", "status", "claimed")
_VALUE_FIELDS = ("value",)
_TIE_FIELDS = ("reported", "recomputed", "difference", "result")
_CONVERSION_FIELDS = ("ebitda", "cfo", "cfo_to_ebitda", "total_leverage", "net_leverage")
_BRIDGE_ROW_IDS = ("start", "claimed", "mgmt", "accepted", "supported", "unsupported")
_TIE_ROW_IDS = ("proposed_total", "mgmt_ebitda", "cp1_total_leverage", "cp1_net_leverage")
_SHARE_ROW_IDS = ("management", "supported", "acceptance")
_CONVERSION_ROW_IDS = ("statements", "management", "supported")
_NO_BRIDGE = "No management bridge is in the pack"
_UNSTATED_ITEM = "Not calculable: the proposed amount is not stated"
_UNSTATED_ANY = "Not calculable: a proposed amount is not stated"
_NOT_STATED_SOURCE = "Not stated in the bridge source"
_NO_BASIS = (
    "No source amount is cited: the share follows the achievability rule or the analyst fraction"
)


@dataclass
class _Facts:
    period: str
    currency: str | None
    facts: list[CellFact] = field(default_factory=list)
    rows: dict[str, list[TableRow]] = field(default_factory=lambda: {t: [] for t, _ in _TABLES})

    def _add(self, fact: CellFact) -> None:
        self.facts.append(fact)

    def number(
        self,
        at: tuple[str, str, str, str],
        value: Decimal,
        unit: str,
        formula: str,
        derives: Sequence[str] = (),
        value_class: ValueClass = "calculated",
        citations: tuple[Citation, ...] = (),
    ) -> None:
        table, row, name, label = at
        money = unit == "MILLIONS"
        self._add(
            CellFact(
                fact_id=f"{table}.{row}.{name}",
                table_id=table,
                row_id=row,
                field=name,
                label=label,
                status="known",
                unit=unit,
                period=self.period,
                amount=value,
                shown=_spell(value, unit, 2 if money else None),
                currency=self.currency if money else None,
                scale=_SCALE[unit] if money else None,
                decimals=2 if money else None,
                value_class=value_class,
                formula=formula,
                calculation_id=f"calc:{table}.{row}.{name}"
                if value_class == "calculated"
                else None,
                derives_from=tuple(derives),
                citations=citations,
            )
        )

    def gap(
        self,
        at: tuple[str, str, str, str],
        unit: str,
        reason: str,
        status: FactStatus = "missing",
    ) -> None:
        table, row, name, label = at
        self._add(
            CellFact(
                fact_id=f"{table}.{row}.{name}",
                table_id=table,
                row_id=row,
                field=name,
                label=label,
                status=status,
                unit=unit,
                period=self.period,
                limitation=reason,
            )
        )

    def text(
        self,
        at: tuple[str, str, str, str],
        value: str,
        value_class: ValueClass | None = None,
        citations: tuple[Citation, ...] = (),
    ) -> None:
        table, row, name, label = at
        self._add(
            CellFact(
                fact_id=f"{table}.{row}.{name}",
                table_id=table,
                row_id=row,
                field=name,
                label=label,
                status="known",
                text=value,
                shown=value,
                value_class=value_class,
                citations=citations,
            )
        )

    def none_row(self, table: str, names: Sequence[str], reason: str) -> None:
        """A `none` row: one not_applicable fact per column, labelled by the column name."""
        for name in names:
            unit = "PERCENT" if name == "applied_fraction" else None
            self._add(
                CellFact(
                    fact_id=f"{table}.none.{name}",
                    table_id=table,
                    row_id="none",
                    field=name,
                    label=name,
                    status="not_applicable",
                    unit=unit,
                    limitation=reason,
                )
            )
        self.row(table, "none", "None", names)

    def row(self, table: str, row_id: str, label: str, names: Sequence[str]) -> None:
        ids = tuple(f"{table}.{row_id}.{name}" for name in names)
        self.rows[table].append(TableRow(row_id, label, ids))

    def tables(self) -> tuple[Table, ...]:
        return tuple(Table(t, title, tuple(self.rows[t])) for t, title in _TABLES)


def _cite(source: Source, locator: str, quote: str) -> Citation:
    if source.sha256 is None:
        raise ValueError(_line("Source without a hash: ", source.source_id))
    return Citation(
        source_id=source.source_id, source_sha256=source.sha256, locator=locator, quote=quote
    )


def _register(out: _Facts, bridge: Bridge | None, source: Source | None, cp1: Cp1Operands) -> None:
    """T1D.1: the bridge rows as stated, then the statement row from CP-1."""
    if bridge is not None and source is not None:
        for item in bridge.items:
            row = item.row_id
            line = (_cite(source, "page:1", item.line),)
            out.text(("T1D.1", row, "type", "Type"), item.type, "source", line)
            out.text(("T1D.1", row, "status", "Status"), item.status, "source", line)
            at = ("T1D.1", row, "claimed", "Proposed amount")
            if item.amount is None:
                out.gap(at, "MILLIONS", _NOT_STATED_SOURCE)
            else:
                out.number(at, item.amount, "MILLIONS", "Bridge source amount", (), "source", line)
            out.row("T1D.1", row, item.label, _REGISTER_FIELDS)
    recorded = _EXACT.subtract(cp1.adjusted_ebitda.value, cp1.ebitda.value)
    out.text(("T1D.1", "stmt", "type", "Type"), "Statement adjustment")
    out.text(("T1D.1", "stmt", "status", "Status"), "Recorded")
    out.number(
        ("T1D.1", "stmt", "claimed", "Recorded amount"),
        recorded,
        "MILLIONS",
        "CP-1 adjusted_ebitda minus ebitda",
        ("cp1:adjusted_ebitda_ltm", "cp1:ebitda_ltm"),
    )
    out.row("T1D.1", "stmt", "Recorded in the statements (CP-1)", _REGISTER_FIELDS)


def _assessment_rows(out: _Facts, outcomes: Sequence[_Outcome]) -> None:
    """T1D.2: one row per bridge item with its applied share and accepted amount."""
    for o in outcomes:
        row, a = o.item.row_id, o.assessment
        out.text(
            ("T1D.2", row, "achievability", "Achievability"), a.achievability, "analyst_judgment"
        )
        out.text(("T1D.2", row, "recurrence", "Recurrence"), a.recurrence, "analyst_judgment")
        basis_at = ("T1D.2", row, "basis", "Source-supported amount")
        share_at = ("T1D.2", row, "applied_fraction", "Share accepted")
        accepted_at = ("T1D.2", row, "accepted", "Accepted amount")
        basis_id, claimed_id, share_id = (
            f"T1D.2.{row}.basis",
            f"T1D.1.{row}.claimed",
            f"T1D.2.{row}.applied_fraction",
        )
        if o.basis is not None and a.accepted_basis is not None:
            basis_citation = (a.accepted_basis,)  # as given; citation_issues located it
            out.number(
                basis_at,
                o.basis,
                "MILLIONS",
                "Amount in the cited quote",
                (),
                "source",
                basis_citation,
            )
        else:
            out.gap(basis_at, "MILLIONS", _NO_BASIS, "not_applicable")
        if o.path == "source":
            out.number(
                share_at,
                o.fraction,
                "PERCENT",
                "Source-supported amount / proposed amount",
                (basis_id, claimed_id),
            )
            out.number(accepted_at, o.accepted, "MILLIONS", "Source-supported amount", (basis_id,))
        else:
            if o.path == "judgment":
                out.number(
                    share_at,
                    o.fraction,
                    "PERCENT",
                    "Analyst accepted fraction",
                    (),
                    "analyst_judgment",
                )
            else:
                out.number(
                    share_at,
                    o.fraction,
                    "PERCENT",
                    "Rule: Supported 100%; otherwise 0; Recurring 0",
                )
            if o.fraction == 0:
                out.number(
                    accepted_at,
                    o.accepted,
                    "MILLIONS",
                    "Zero by rule (share accepted is 0)",
                    (share_id,),
                )
            else:
                out.number(
                    accepted_at,
                    o.accepted,
                    "MILLIONS",
                    "Proposed amount x share accepted",
                    (claimed_id, share_id),
                )
        out.text(("T1D.2", row, "treatment", "Treatment"), o.treatment)
        unsupported_at = ("T1D.2", row, "unsupported", "Not accepted")
        if o.item.amount is None:
            out.gap(unsupported_at, "MILLIONS", _UNSTATED_ITEM)
        else:
            out.number(
                unsupported_at,
                _EXACT.subtract(o.item.amount, o.accepted),
                "MILLIONS",
                "Proposed amount minus accepted amount",
                (claimed_id, f"T1D.2.{row}.accepted"),
            )
        located = "; ".join(f"{c.source_id} {c.locator}" for c in a.evidence) or "None located"
        out.text(("T1D.2", row, "evidence", "Evidence"), located)
        out.row("T1D.2", row, o.item.label, _ASSESSMENT_FIELDS)
    if not outcomes:
        out.none_row(
            "T1D.2", _ASSESSMENT_FIELDS, f"{_NO_BRIDGE}, so there is no add-back to assess"
        )


@dataclass(frozen=True)
class _Totals:
    start: Decimal
    claimed: Decimal | None  # None: not stated, or no bridge
    management: Decimal | None
    accepted: Decimal
    supported: Decimal
    unsupported: Decimal | None


def _totals(bridge: Bridge | None, outcomes: Sequence[_Outcome], cp1: Cp1Operands) -> _Totals:
    start = cp1.adjusted_ebitda.value
    amounts = [o.item.amount for o in outcomes]
    claimed = None
    if bridge is not None and all(a is not None for a in amounts):
        claimed = _sum(a for a in amounts if a is not None)
    accepted = _sum(o.accepted for o in outcomes)
    management = None if claimed is None else _EXACT.add(start, claimed)
    unsupported = None if claimed is None else _EXACT.subtract(claimed, accepted)
    supported = _EXACT.add(start, accepted)
    return _Totals(start, claimed, management, accepted, supported, unsupported)


def _bridge_rows(out: _Facts, bridge: Bridge | None, totals: _Totals, items: int) -> None:
    """T1D.3: statements, proposed, management, accepted, supported, not accepted."""
    out.number(
        ("T1D.3", "start", "value", "Adjusted EBITDA, statements (CP-1)"),
        totals.start,
        "MILLIONS",
        "CP-1 adjusted_ebitda",
        ("cp1:adjusted_ebitda_ltm",),
    )
    for row, label, value, formula, derives in (
        (
            "claimed",
            "Proposed add-backs (management)",
            totals.claimed,
            "Sum of proposed amounts",
            ("T1D.1.<each>.claimed",),
        ),
        (
            "mgmt",
            "Management financing-case EBITDA",
            totals.management,
            "Statement adjusted EBITDA plus proposed add-backs",
            ("T1D.3.start.value", "T1D.3.claimed.value"),
        ),
    ):
        _optional(out, ("T1D.3", row, "value", label), bridge, value, formula, derives)
    out.number(
        ("T1D.3", "accepted", "value", "Accepted add-backs"),
        totals.accepted,
        "MILLIONS",
        "Sum of accepted amounts",
        ("T1D.2.<each>.accepted",) if items else (),
    )
    out.number(
        ("T1D.3", "supported", "value", "Supported adjusted EBITDA"),
        totals.supported,
        "MILLIONS",
        "Statement adjusted EBITDA plus accepted add-backs",
        ("T1D.3.start.value", "T1D.3.accepted.value"),
    )
    _optional(
        out,
        ("T1D.3", "unsupported", "value", "Add-backs not accepted"),
        bridge,
        totals.unsupported,
        "Proposed add-backs minus accepted add-backs",
        ("T1D.3.claimed.value", "T1D.3.accepted.value"),
    )
    for row, label in (
        ("start", "Adjusted EBITDA, statements (CP-1)"),
        ("claimed", "Proposed add-backs (management)"),
        ("mgmt", "Management financing-case EBITDA"),
        ("accepted", "Accepted add-backs"),
        ("supported", "Supported adjusted EBITDA"),
        ("unsupported", "Add-backs not accepted"),
    ):
        out.row("T1D.3", row, label, _VALUE_FIELDS)


def _optional(
    out: _Facts,
    at: tuple[str, str, str, str],
    bridge: Bridge | None,
    value: Decimal | None,
    formula: str,
    derives: Sequence[str],
) -> None:
    """An amount that needs the bridge: not_applicable without one, missing when unstated."""
    if bridge is None:
        out.gap(at, "MILLIONS", _NO_BRIDGE, "not_applicable")
    elif value is None:
        out.gap(at, "MILLIONS", _UNSTATED_ANY)
    else:
        out.number(at, value, "MILLIONS", formula, derives)


def _tie(
    out: _Facts,
    row: tuple[str, str],
    bridge: Bridge | None,
    reported: tuple[Decimal | None, tuple[Citation, ...]],
    recomputed: tuple[Decimal | None, str],
) -> None:
    """A T1D.4 tie-out of a stated bridge total (citing its line, ruling 1D1) against the
    recomputed rows."""
    row_id, label = row
    stated, line = reported
    value, source_fact = recomputed

    def at(name: str, title: str) -> tuple[str, str, str, str]:
        return ("T1D.4", row_id, name, title)

    if bridge is None:
        for name, title in (
            ("reported", "Stated"),
            ("recomputed", "Recomputed"),
            ("difference", "Difference"),
        ):
            out.gap(at(name, title), "MILLIONS", _NO_BRIDGE, "not_applicable")
        result = "Not compared"
    else:
        if stated is None:
            out.gap(at("reported", "Stated"), "MILLIONS", _NOT_STATED_SOURCE)
        else:
            out.number(
                at("reported", "Stated"),
                stated,
                "MILLIONS",
                "Bridge source amount",
                (),
                "source",
                line,
            )
        if value is None:
            out.gap(at("recomputed", "Recomputed"), "MILLIONS", _UNSTATED_ANY)
        else:
            out.number(
                at("recomputed", "Recomputed"),
                value,
                "MILLIONS",
                "Recomputed from the rows",
                (source_fact,),
            )
        if stated is None or value is None:
            out.gap(
                at("difference", "Difference"),
                "MILLIONS",
                "Not compared: one side is not available",
            )
            result = "Not compared"
        else:
            out.number(
                at("difference", "Difference"),
                _EXACT.subtract(value, stated),
                "MILLIONS",
                "Recomputed minus stated",
                (f"T1D.4.{row_id}.recomputed", f"T1D.4.{row_id}.reported"),
            )
            result = "Reconciled" if value == stated else "Differs"
    out.text(at("result", "Result"), result)
    out.row("T1D.4", row_id, label, _TIE_FIELDS)


_BASIS_LABEL = {
    "start": "Adjusted EBITDA, statements (CP-1)",
    "mgmt": "Management financing-case EBITDA",
    "supported": "Supported adjusted EBITDA",
}


def _not_meaningful(bridge_row: str) -> str:
    """Ruling 1D3: a ratio over a basis EBITDA that is zero or negative."""
    return (
        f"Not meaningful: {_BASIS_LABEL[bridge_row]} is zero or negative "
        "(ZERO_OR_NEGATIVE_DENOMINATOR)"
    )


def _ratio(
    out: _Facts,
    at: tuple[str, str, str, str],
    numerator: Decimal,
    denominator: tuple[Decimal, str],
    unit: str,
    formula: str,
    derives: Sequence[str],
) -> None:
    """One quotient over a T1D.3 EBITDA basis: not_applicable when that basis is not above 0."""
    value, bridge_row = denominator
    if value <= 0:
        out.gap(at, unit, _not_meaningful(bridge_row), "not_applicable")
    else:
        out.number(at, _quotient(numerator, value), unit, formula, derives)


def _total_line(source: Source | None, line: str | None) -> tuple[Citation, ...]:
    return () if source is None or line is None else (_cite(source, "page:1", line),)


def _tie_outs(
    out: _Facts, pack: tuple[Bridge | None, Source | None], totals: _Totals, cp1: Cp1Operands
) -> None:
    """T1D.4: stated bridge totals against the rows, then CP-1's leverage recomputed."""
    bridge, source = pack
    _tie(
        out,
        ("proposed_total", "Proposed add-backs: stated total against rows"),
        bridge,
        (
            bridge.proposed_total if bridge else None,
            _total_line(source, bridge.proposed_total_line if bridge else None),
        ),
        (totals.claimed, "T1D.3.claimed.value"),
    )
    _tie(
        out,
        ("mgmt_ebitda", "Management EBITDA: stated against statement EBITDA plus rows"),
        bridge,
        (
            bridge.management_ebitda if bridge else None,
            _total_line(source, bridge.management_ebitda_line if bridge else None),
        ),
        (totals.management, "T1D.3.mgmt.value"),
    )
    for row, label, reported, debt in (
        (
            "cp1_total_leverage",
            "Statement total leverage against CP-1",
            cp1.total_leverage,
            cp1.total_debt,
        ),
        ("cp1_net_leverage", "Statement net leverage against CP-1", cp1.net_leverage, cp1.net_debt),
    ):
        reported_at = ("T1D.4", row, "reported", "CP-1 reported")
        if reported.amount is None:  # ruling 1D3: the reported side keeps CP-1's status
            out.gap(reported_at, "MULTIPLE", reported.reason, reported.status)
        else:
            out.number(
                reported_at,
                reported.amount,
                "MULTIPLE",
                f"CP-1 {reported.figure}",
                (f"cp1:{reported.figure}",),
            )
        recomputed_at = ("T1D.4", row, "recomputed", "Recomputed")
        recomputed = None
        if totals.start <= 0:
            out.gap(recomputed_at, "MULTIPLE", _not_meaningful("start"), "not_applicable")
        else:
            recomputed = _quotient(debt.value, totals.start)
            out.number(
                recomputed_at,
                recomputed,
                "MULTIPLE",
                "Debt / statement adjusted EBITDA",
                (f"cp1:{debt.figure}", "T1D.3.start.value"),
            )
        difference_at = ("T1D.4", row, "difference", "Difference")
        if recomputed is None or reported.amount is None:
            out.gap(difference_at, "MULTIPLE", "Not compared: one side is not available")
            result = "Not compared"
        else:
            out.number(
                difference_at,
                _EXACT.subtract(recomputed, reported.amount),
                "MULTIPLE",
                "Recomputed minus CP-1",
                (f"T1D.4.{row}.recomputed", f"T1D.4.{row}.reported"),
            )
            result = "Reconciled" if recomputed == reported.amount else "Differs"
        out.text(("T1D.4", row, "result", "Result"), result)
        out.row("T1D.4", row, label, _TIE_FIELDS)


def _shares(out: _Facts, bridge: Bridge | None, totals: _Totals) -> None:
    """T1D.5: proposed / management, accepted / supported, accepted / proposed."""
    management_at = ("T1D.5", "management", "value", "Proposed add-backs / management EBITDA")
    if bridge is None:
        out.gap(management_at, "PERCENT", _NO_BRIDGE, "not_applicable")
    elif totals.claimed is None or totals.management is None:
        out.gap(management_at, "PERCENT", _UNSTATED_ANY)
    else:
        _ratio(
            out,
            management_at,
            totals.claimed,
            (totals.management, "mgmt"),
            "PERCENT",
            "Proposed add-backs / management financing-case EBITDA",
            ("T1D.3.claimed.value", "T1D.3.mgmt.value"),
        )
    _ratio(
        out,
        ("T1D.5", "supported", "value", "Accepted add-backs / supported EBITDA"),
        totals.accepted,
        (totals.supported, "supported"),
        "PERCENT",
        "Accepted add-backs / supported adjusted EBITDA",
        ("T1D.3.accepted.value", "T1D.3.supported.value"),
    )
    acceptance_at = ("T1D.5", "acceptance", "value", "Accepted / proposed add-backs")
    if bridge is None:
        out.gap(acceptance_at, "PERCENT", _NO_BRIDGE, "not_applicable")
    elif totals.claimed is None:
        out.gap(acceptance_at, "PERCENT", _UNSTATED_ANY)
    elif totals.claimed == 0:
        out.gap(acceptance_at, "PERCENT", "No add-backs claimed", "not_applicable")
    else:
        out.number(
            acceptance_at,
            _quotient(totals.accepted, totals.claimed),
            "PERCENT",
            "Accepted add-backs / proposed add-backs",
            ("T1D.3.accepted.value", "T1D.3.claimed.value"),
        )
    for row, label in (
        ("management", "Proposed add-backs / management EBITDA"),
        ("supported", "Accepted add-backs / supported EBITDA"),
        ("acceptance", "Accepted / proposed add-backs"),
    ):
        out.row("T1D.5", row, label, _VALUE_FIELDS)


def _conversion(out: _Facts, bridge: Bridge | None, totals: _Totals, cp1: Cp1Operands) -> None:
    """T1D.6: cash conversion and leverage on each EBITDA basis."""
    for row, label, ebitda, bridge_row in (
        ("statements", "Statements (CP-1)", totals.start, "start"),
        ("management", "Management financing case", totals.management, "mgmt"),
        ("supported", "Supported", totals.supported, "supported"),
    ):
        ratios = (
            (
                "cfo_to_ebitda",
                "Operating cash flow / EBITDA",
                cp1.cfo,
                "PERCENT",
                "Operating cash flow / EBITDA",
            ),
            ("total_leverage", "Total leverage", cp1.total_debt, "MULTIPLE", "Total debt / EBITDA"),
            ("net_leverage", "Net leverage", cp1.net_debt, "MULTIPLE", "Net debt / EBITDA"),
        )
        status: FactStatus = "not_applicable" if bridge is None else "missing"
        reason = _NO_BRIDGE if bridge is None else _UNSTATED_ANY
        ebitda_at = ("T1D.6", row, "ebitda", "EBITDA")
        if ebitda is None:
            out.gap(ebitda_at, "MILLIONS", reason, status)
        else:
            out.number(
                ebitda_at, ebitda, "MILLIONS", "T1D.3 basis value", (f"T1D.3.{bridge_row}.value",)
            )
        out.number(
            ("T1D.6", row, "cfo", "Operating cash flow"),
            cp1.cfo.value,
            "MILLIONS",
            "CP-1 cfo_adjusted",
            ("cp1:cfo_ltm",),
        )
        for name, title, numerator, unit, formula in ratios:
            if ebitda is None:
                out.gap(("T1D.6", row, name, title), unit, reason, status)
            else:
                _ratio(
                    out,
                    ("T1D.6", row, name, title),
                    numerator.value,
                    (ebitda, bridge_row),
                    unit,
                    formula,
                    (f"cp1:{numerator.figure}", f"T1D.6.{row}.ebitda"),
                )
        out.row("T1D.6", row, label, _CONVERSION_FIELDS)


def _gaps(out: _Facts, gaps: Sequence[Gap]) -> None:
    """T1D.7: the analyst's gaps ledger."""
    for n, g in enumerate(gaps, 1):
        row = f"g{n:02d}"
        out.text(("T1D.7", row, "id", "Gap id"), f"CP-1D-GAP-{n:03d}")
        out.text(("T1D.7", row, "gap", "Gap"), g.gap, "analyst_judgment")
        out.text(
            ("T1D.7", row, "why_it_matters", "Why it matters"), g.why_it_matters, "analyst_judgment"
        )
        out.text(
            ("T1D.7", row, "affected_analysis", "Affected analysis"),
            g.affected_analysis,
            "analyst_judgment",
        )
        out.text(("T1D.7", row, "severity", "Severity"), g.severity)
        out.text(("T1D.7", row, "action", "Action"), g.action, "analyst_judgment")
        out.row("T1D.7", row, f"Gap {n}", _GAP_FIELDS)
    if not gaps:
        out.none_row("T1D.7", _GAP_FIELDS, "None in the CP-1D submission (gaps ledger)")


_CP1B_LINE = {
    "unbound": "CP-1B (earnings update) is not part of this run, so its variance evidence is not read.",
    "settled": "CP-1B is bound but its variance evidence is not read in this version.",
    "blocked": "CP-1B is bound but its variance evidence is not read in this version.",
}


def _limitations(
    bridge: Bridge | None, outcomes: Sequence[_Outcome], gaps: Sequence[Gap], cp1b: Cp1bState
) -> tuple[str, ...]:
    """The module's own limitations, in the lease's fixed order."""
    lines = [
        "Add-back amounts are management's proposals from the bridge source; none is recorded in the statements."
        if bridge is not None
        else "No management bridge is in the pack: add-backs are tested only against the statements, which record none."
    ]
    lines += [
        clipped(
            (
                "Proposed amount is not stated for ",
                o.item.label,
                ": every figure that needs it is Not calculable.",
            )
        )
        for o in outcomes
        if o.item.amount is None
    ]
    lines += [
        clipped(
            ("Recurring add-back excluded although a source amount is cited: ", o.item.label, ".")
        )
        for o in outcomes
        if o.path == "rule" and o.basis is not None
    ]
    if any(o.path == "judgment" for o in outcomes):
        lines.append(
            "Accepted fractions given without a source amount are analyst assumptions without a source calculation."
        )
    if any(o.accepted > 0 and o.item.type == "Saving" for o in outcomes):
        lines.append(
            "One-time costs to achieve accepted savings are not deducted from supported adjusted EBITDA."
        )
    if any(o.accepted > 0 and o.item.status == "Unrealised" for o in outcomes):
        lines.append(
            "Supported adjusted EBITDA includes accepted savings that are not yet realised; the statements record no adjustment."
        )
    lines += [
        "Cash conversion divides CP-1 operating cash flow by EBITDA over the same twelve months; working capital and timing are not separated.",
        "Supported adjusted EBITDA is an analyst view and does not replace the covenant EBITDA definition tested by CP-4.",
        _CP1B_LINE[cp1b],
    ]
    lines += [f"Gap ({g.severity}): {g.gap}" for g in gaps]
    return tuple(lines)


def _claims(
    facts: Sequence[CellFact], outcomes: Sequence[_Outcome], overall: Overall
) -> tuple[ClaimDraft, ...]:
    """Analyst rationales per item, the three Python templates, then the overall assessment."""
    known = {f.fact_id for f in facts if f.status == "known"}

    def ref(fact_id: str, unit: str) -> str:
        return f"{{{fact_id}|{unit}}}" if fact_id in known else f"[{fact_id}]"

    claims = [
        ClaimDraft(
            f"T1D.2.{o.item.row_id}",
            o.assessment.rationale,
            o.assessment.limitation,
            o.assessment.evidence,
        )
        for o in outcomes
    ]
    claims += [
        ClaimDraft(
            "T1D.3.restated",
            f"Supported adjusted EBITDA is {ref('T1D.3.supported.value', 'US$ m')} against "
            f"{ref('T1D.3.mgmt.value', 'US$ m')} in the management financing case and "
            f"{ref('T1D.3.start.value', 'US$ m')} in the statements, so total leverage restates to "
            f"{ref('T1D.6.supported.total_leverage', 'x')} from "
            f"{ref('T1D.6.statements.total_leverage', 'x')} on the statements.",
            None,
        ),
        ClaimDraft(
            "T1D.5.share",
            f"Proposed add-backs are {ref('T1D.5.management.value', '%')} of management "
            "financing-case EBITDA and accepted add-backs are "
            f"{ref('T1D.5.supported.value', '%')} of supported adjusted EBITDA.",
            None,
        ),
        ClaimDraft(
            "T1D.6.conversion",
            f"Operating cash flow is {ref('T1D.6.statements.cfo_to_ebitda', '%')} of statement "
            f"EBITDA, {ref('T1D.6.management.cfo_to_ebitda', '%')} of management financing-case "
            f"EBITDA and {ref('T1D.6.supported.cfo_to_ebitda', '%')} of supported adjusted EBITDA.",
            None,
        ),
        ClaimDraft("T1D.1.assessment", overall.rationale, overall.limitation, overall.evidence),
    ]
    return tuple(claims)


def _cp1_references(cp1: Cp1Operands) -> tuple[Cp1Reference, ...]:
    return tuple(
        Cp1Reference(
            row_id=f.figure,
            figure=f.figure,
            label=f.label,
            unit=f.unit,
            period=f.period,
            amount=f.amount,
            shown=None if f.amount is None else _spell(f.amount, f.unit, None),
            value_class=f.value_class,
            status=f.status,
        )
        for f in cp1.ordered()
    )


# --- validation -----------------------------------------------------------------------------


def _bridge_source(sources: Sequence[Source]) -> Source | None:
    return next((s for s in sources if s.source_id == BRIDGE_SOURCE_ID), None)


def _pages(source: Source) -> list[str]:
    return [span.text for span in source.spans]


def _assessments_by_item(
    bridge: Bridge, assessments: Sequence[Assessment]
) -> tuple[list[str], list[tuple[BridgeItem, Assessment]]]:
    """Label issues, and each bridge item paired with its single assessment."""
    labels = {item.label for item in bridge.items}
    count = Counter(a.addback for a in assessments)
    found = [_line("Unknown add-back: ", a.addback) for a in assessments if a.addback not in labels]
    pairs: list[tuple[BridgeItem, Assessment]] = []
    for item in bridge.items:
        if count[item.label] != 1:
            found.append(_line("Assess each bridge add-back exactly once: ", item.label))
            continue
        pairs.append((item, next(a for a in assessments if a.addback == item.label)))
    return found, pairs


def _composable(item: BridgeItem, assessment: Assessment) -> bool:
    return not (_accepts(assessment) and item.amount is None)


_UNRESOLVED = "Unresolved reference: "


@dataclass(frozen=True)
class _Shape:
    """What the structure alone says about a fact: its unit (None for text), whether it is
    always a gap (`none` rows), and whether it may carry a calculation id."""

    unit: str | None
    always_gap: bool = False
    calculated: bool = True


_UNITS = {
    "claimed": "MILLIONS",
    "basis": "MILLIONS",
    "applied_fraction": "PERCENT",
    "accepted": "MILLIONS",
    "unsupported": "MILLIONS",
    "value": "MILLIONS",
    "ebitda": "MILLIONS",
    "cfo": "MILLIONS",
    "cfo_to_ebitda": "PERCENT",
    "total_leverage": "MULTIPLE",
    "net_leverage": "MULTIPLE",
}


def _shape(table: str, row: str, name: str) -> _Shape:
    if row == "none":
        return _Shape(None, always_gap=True, calculated=False)
    if table == "T1D.4" and name != "result":
        control = row.startswith("cp1_")  # the CP-1 controls; the other two tie bridge totals
        return _Shape(
            "MULTIPLE" if control else "MILLIONS", calculated=control or name != "reported"
        )
    unit = "PERCENT" if table == "T1D.5" else _UNITS.get(name)
    source = (table == "T1D.1" and row != "stmt") or name == "basis"
    return _Shape(unit, calculated=unit is not None and not source)


def _module_shapes(bridge: Bridge | None, gaps: int) -> dict[str, _Shape]:
    """Every fact a full composition carries, by id, from the structure alone (no values)."""
    items = bridge.items if bridge is not None else ()
    rows: list[tuple[str, str, tuple[str, ...]]] = [
        *(("T1D.1", i.row_id, _REGISTER_FIELDS) for i in items),
        ("T1D.1", "stmt", _REGISTER_FIELDS),
        *(("T1D.2", i.row_id, _ASSESSMENT_FIELDS) for i in items),
        *(("T1D.3", r, _VALUE_FIELDS) for r in _BRIDGE_ROW_IDS),
        *(("T1D.4", r, _TIE_FIELDS) for r in _TIE_ROW_IDS),
        *(("T1D.5", r, _VALUE_FIELDS) for r in _SHARE_ROW_IDS),
        *(("T1D.6", r, _CONVERSION_FIELDS) for r in _CONVERSION_ROW_IDS),
        *(("T1D.7", f"g{n:02d}", _GAP_FIELDS) for n in range(1, gaps + 1)),
    ]
    if not items:
        rows.append(("T1D.2", "none", _ASSESSMENT_FIELDS))
    if not gaps:
        rows.append(("T1D.7", "none", _GAP_FIELDS))
    return {
        f"{table}.{row}.{name}": _shape(table, row, name)
        for table, row, names in rows
        for name in names
    }


def module_fact_ids(bridge: Bridge | None, gaps: int) -> frozenset[str]:
    """Every fact id a full composition carries, from the structure alone (no values)."""
    return frozenset(_module_shapes(bridge, gaps))


def _structural_issues(run: ProseRun, shape: _Shape, currency: str | None) -> list[str]:
    """The product's reference checks (`prose._run_issues`, `prose._fact_issues`) that the
    structure decides; whether a numeric fact is known depends on values and is not checked."""
    if not run.figure:
        return []
    if shape.always_gap:
        return [f"Figure reference names a gap: {run.text}"]
    if shape.unit is None:
        return [f"Figure reference needs a known numeric fact: {run.text}"]
    shown = {"PERCENT": "%", "MULTIPLE": "x"}.get(shape.unit) or scale_label(shape.unit, currency)
    if run.unit is not None and run.unit not in {shape.unit, shown}:
        return [f"Unit {run.unit} differs from the fact's unit {shown or shape.unit}: {run.text}"]
    return []


def _rationale_issues(
    text: str, bound: Mapping[str, Fact], absent: Mapping[str, _Shape], currency: str | None
) -> list[str]:
    """`prose.issues` against the bound facts; a reference to a fact only a full composition
    carries (or its calculation id) gets the structural checks instead of `Unresolved`."""
    found: list[str] = []
    for issue in prose_issues(text, bound):
        ref = issue.removeprefix(_UNRESOLVED) if issue.startswith(_UNRESOLVED) else None
        target = None if ref is None else absent.get(ref.removeprefix("calc:"))
        if ref is None or target is None or (ref.startswith("calc:") and not target.calculated):
            found.append(issue)
            continue
        for run in tokenize(text):
            if run.kind != "text" and run.text == ref:
                found += _structural_issues(run, target, currency)
    return list(dict.fromkeys(found))


def _bridge_issues(inputs: EarningsQualityInputs, source: Source, bridge: Bridge) -> list[str]:
    """Ruling 1D10 from step 3: the assessment set, then each assessment in submission order
    (its basis/fraction shape failure alone, else evidence, recurrence, unstated amount,
    citations, prose), then the overall confidence rule."""
    submission, currency = inputs.submission, inputs.cp1.adjusted_ebitda.currency
    label_issues, pairs = _assessments_by_item(bridge, submission.assessments)
    shapes = {item.label: _shape_issue(item, a, inputs.sources) for item, a in pairs}
    composed = [
        _outcome(item, a, inputs.sources)
        for item, a in pairs
        if shapes[item.label] is None and _composable(item, a)
    ]
    if len(composed) == len(bridge.items):
        out = _compose(inputs, bridge, source, composed)
    else:  # T1D.1 and the composable T1D.2 rows; compute is never reached with these issues
        out = _Facts(inputs.cp1.adjusted_ebitda.period, currency)
        _register(out, bridge, source, inputs.cp1)
        _assessment_rows(out, composed)
    bound = bind(f.to_fact() for f in out.facts)
    absent = {
        fact_id: shape
        for fact_id, shape in _module_shapes(bridge, len(submission.gaps)).items()
        if fact_id not in bound
    }
    items = {item.label: item for item, _ in pairs}
    found = list(label_issues)
    for a in submission.assessments:
        item = items.get(a.addback)
        if item is None:  # unknown or assessed more than once: the set issues above
            continue
        shape = shapes[item.label]
        if shape is not None:
            found.append(shape)
            continue
        found += _rule_issues(item, a)
        found += citation_issues((*a.evidence, *filter(None, (a.accepted_basis,))), inputs.sources)
        found += _rationale_issues(a.rationale, bound, absent, currency)
    if submission.overall.confidence == "High":
        found.append("Confidence cannot be High: the add-back evidence is management-supplied")
    return found


_GAP_TEXTS = ("gap", "why_it_matters", "affected_analysis", "action")


def _blank_issues(submission: EarningsQualitySubmission) -> list[str]:
    """LEAD round 11 (blank text is one defect class): every analyst text field refuses blank
    text, which round 12 B10 defines as `blank.is_blank` (whitespace and Unicode `Cf` characters
    only). CP-1D pins no empty-text frame, so the issue is `<path>: empty text`.
    A `Text` field's "" is already the schema's `min_length` refusal (controller decision); a
    `limitation` of "" gets the frame. `addback` is a bridge label, not text: a blank one is
    `Unknown add-back`."""
    texts: list[tuple[str, str | None]] = []
    for index, a in enumerate(submission.assessments):
        texts += [
            (f"assessments[{index}].rationale", a.rationale),
            (f"assessments[{index}].limitation", a.limitation),
        ]
    texts += [
        ("overall.rationale", submission.overall.rationale),
        ("overall.limitation", submission.overall.limitation),
    ]
    for index, gap in enumerate(submission.gaps):
        texts += [(f"gaps[{index}].{name}", getattr(gap, name)) for name in _GAP_TEXTS]
    return [f"{path}: empty text" for path, text in texts if text is not None and is_blank(text)]


def validation_issues(inputs: EarningsQualityInputs) -> tuple[str, ...]:
    """Every calculation-level issue of the submission against the pack and the bridge, in
    ruling 1D10's order: bridge, assessment set, each assessment, overall (gaps have no rule);
    then each blank analyst text field in submission order (round 11, `_blank_issues`).

    A bridge source CP-0 did not mark ready (ruling 1D-x) or an unreadable bridge table gives
    `Bridge table not found` alone. Tool-use rules (cited page read) are Stage 2; the overall
    rationale's `{{FIG:...}}` references are bound to CP-1 facts at run time, so its prose is
    checked there.
    """
    submission = inputs.submission
    source = _bridge_source(inputs.sources)
    if source is None:
        found = [
            _line("Assessment given without a bridge in the pack: ", a.addback)
            for a in submission.assessments
        ]
        if not submission.overall.evidence:
            found.append(
                "Evidence required when no bridge is supplied: the statements' add-back disclosure"
            )
    else:
        bridge = parse_bridge(_pages(source)) if source.status == "ready" else None
        if bridge is None:
            return ("Bridge table not found",)
        found = _bridge_issues(inputs, source, bridge)
    found += citation_issues(submission.overall.evidence, inputs.sources)
    found += _blank_issues(submission)
    return _bounded(dict.fromkeys(found))


# --- the calculation ------------------------------------------------------------------------


def _compose(
    inputs: EarningsQualityInputs,
    bridge: Bridge | None,
    source: Source | None,
    outcomes: Sequence[_Outcome],
) -> _Facts:
    """All seven tables' facts and rows, in the lease's table and row order."""
    cp1 = inputs.cp1
    totals = _totals(bridge, outcomes, cp1)
    out = _Facts(cp1.adjusted_ebitda.period, cp1.adjusted_ebitda.currency)
    _register(out, bridge, source, cp1)
    _assessment_rows(out, outcomes)
    _bridge_rows(out, bridge, totals, len(outcomes))
    _tie_outs(out, (bridge, source), totals, cp1)
    _shares(out, bridge, totals)
    _conversion(out, bridge, totals, cp1)
    _gaps(out, inputs.submission.gaps)
    return out


def compute(inputs: EarningsQualityInputs) -> EarningsQualityResult:
    """The lease's tables, claims and own limitations; raises ValueError on any issue."""
    issues = validation_issues(inputs)
    if issues:
        raise ValueError("; ".join(issues))
    cp1, submission = inputs.cp1, inputs.submission
    source = _bridge_source(inputs.sources)
    bridge = parse_bridge(_pages(source)) if source is not None else None
    by_label = {a.addback: a for a in submission.assessments}
    outcomes = (
        [_outcome(item, by_label[item.label], inputs.sources) for item in bridge.items]
        if bridge
        else []
    )
    out = _compose(inputs, bridge, source, outcomes)
    totals = _totals(bridge, outcomes, cp1)
    available = {
        "start": totals.start,
        "claimed": totals.claimed,
        "mgmt": totals.management,
        "accepted": totals.accepted,
        "supported": totals.supported,
        "unsupported": totals.unsupported,
    }
    return EarningsQualityResult(
        bridge_source=(
            None
            if source is None or source.sha256 is None
            else BridgeSourceRef(source.source_id, source.sha256, len(source.spans))
        ),
        operands=tuple((k, v) for k, v in available.items() if v is not None),
        operands_unavailable=tuple(k for k, v in available.items() if v is None),
        facts=tuple(out.facts),
        tables=out.tables(),
        cp1_references=_cp1_references(cp1),
        claims=_claims(out.facts, outcomes, submission.overall),
        limitations=_limitations(bridge, outcomes, submission.gaps, inputs.cp1b),
    )


# =============================================================================================
# Stage 2: the connection (docs/CP1D-OWNER-LEASE.md Public API; docs/G1X-OWNER-CORE-PROTOCOL.md).
# Everything above is the pure Stage 1 calculation and is not changed by what follows.
# =============================================================================================

STEP_ID = "earnings_quality"
STEP_IDS = (STEP_ID,)
QUALIFICATION = Qualification(implementation="implemented")
SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: EarningsQualitySubmission}
# The fixed H1 mapping (`host._OWNER_SCOPES[("CP-1D", "earnings_quality")]`): identity, financial
# and, when the pack holds it, the bridge; a held source stays in scope in pack order.
SCOPE = frozenset({"identity", "financial", BRIDGE_SOURCE_ID})
CP0, CP1, CP1B = "CP-0", "CP-1", "CP-1B"
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
_CP1_TABLE = "T4.10"
_CP1_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
_CP1_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
# Operand name -> CP-1 T4.10 metric (manifest `cp1_fact_selection_rule.metrics`), in
# `_CP1_FIGURES` order.
_CP1_METRICS = {
    "adjusted_ebitda_ltm": "adjusted_ebitda",
    "ebitda_ltm": "ebitda",
    "cfo_ltm": "cfo_adjusted",
    "total_debt_ltm": "total_debt",
    "net_debt_ltm": "net_debt",
    "total_leverage_adjusted": "total_leverage_adjusted",
    "net_leverage_adjusted": "net_leverage_adjusted",
}
_CP1B_BOUND = "CP-1B is bound but its variance evidence is not read in this version."


class EarningsQualityReport(Contract):
    """The composed CP-1D output retained as the step output: the module's tables, facts, claims
    and own limitations, bound to the pack and the retained submission."""

    schema_version: Literal["earnings-quality/1"] = "earnings-quality/1"
    run: PackRun
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[Text, ...]


@dataclass(frozen=True)
class Upstream:
    """What one CP-1D attempt binds, read once from the journal (`cp1d_upstream`).

    `bound` is the attempt's input set; `current` is `execution.current_inputs` now, or its
    refusal text; `cp0` and `cp1` are the bound required heads; `cp1b` is the bound optional
    CP-1B head (status and limitations only; v1 reads no CP-1B fact); `inherited` is what
    settlement will carry."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp0: Module
    cp1: Module
    cp1b: Module | None
    inherited: tuple[str, ...]

    def status(self, module_id: str) -> str | None:
        return next((item.status for item in self.bound if item.input_id == module_id), None)

    @property
    def cp1b_state(self) -> Cp1bState:
        status = self.status(CP1B)
        return "unbound" if status is None else "blocked" if status == "blocked" else "settled"


def _bound_module(store: Execution, attempt: Attempt, module_id: str) -> Module:
    item = next((i for i in attempt.inputs if i.input_id == module_id), None)
    if item is None:
        raise ValueError(f"The CP-1D attempt binds no {module_id} input")
    return store.result(item.sha256)


def cp1d_upstream(store: Execution, attempt: Attempt) -> Upstream:
    """The bound CP-0 and CP-1 heads of `attempt`, its bound CP-1B head when the run has one,
    the current input set and the inherited limitations. A refusal of `current_inputs` is kept
    as text: the validator reports it as a staleness issue."""
    snapshot = store.read()
    current: tuple[Input, ...] | str
    try:
        current = current_inputs(snapshot, MODULE_ID)
    except ValueError as error:  # NotAuthorized included: reported, never passed as current
        current = str(error)
    bound = {item.input_id for item in attempt.inputs}
    return Upstream(
        bound=attempt.inputs,
        current=current,
        cp0=_bound_module(store, attempt, CP0),
        cp1=_bound_module(store, attempt, CP1),
        cp1b=_bound_module(store, attempt, CP1B) if CP1B in bound else None,
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


def _stale_issues(upstream: Upstream) -> list[str]:
    if isinstance(upstream.current, str):
        return [_line("Stale inputs: ", upstream.current)]
    bound = {item.input_id: item for item in upstream.bound}
    current = {item.input_id: item for item in upstream.current}

    def state(item: Input | None) -> str:
        return "absent" if item is None else f"{item.status} {item.sha256[:12]}"

    return [
        f"Stale input {key}: bound {state(bound.get(key))}, current {state(current.get(key))}"
        for key in dict.fromkeys((*bound, *current))
        if bound.get(key) != current.get(key)
    ]


def _provenance_issues(upstream: Upstream) -> list[str]:
    """The supplied modules are the bound heads (same module, same canonical hash)."""
    supplied: dict[str, Module | None] = {CP0: upstream.cp0, CP1: upstream.cp1}
    if upstream.status(CP1B) is not None or upstream.cp1b is not None:
        supplied[CP1B] = upstream.cp1b
    bound = {item.input_id: item for item in upstream.bound}
    found: list[str] = []
    for module_id, module in supplied.items():
        item = bound.get(module_id)
        if (
            item is None
            or module is None
            or module.module_id != module_id
            or module.content_hash() != item.sha256
        ):
            found.append(f"Upstream {module_id}: the supplied module is not the bound input")
    found += [
        f"Required upstream {item.input_id} is blocked"
        for item in upstream.bound
        if item.input_id in (CP0, CP1) and item.status == "blocked"
    ]
    return found


def _cp1_facts(cp1: Module) -> dict[str, Fact]:
    """The seven T4.10 facts of the LTM Q4 25 column by operand name (manifest
    `cp1_fact_selection_rule`): exactly one match each, zero or several fail."""
    picked: dict[str, Fact] = {}
    for name, metric in _CP1_METRICS.items():
        label = f"{_CP1_COLUMN} · {metric}"
        hits = [
            f
            for f in cp1.facts
            if f.table_id == _CP1_TABLE and f.period == _CP1_PERIOD and f.label == label
        ]
        if len(hits) != 1:
            raise ValueError(f"CP-1 {_CP1_TABLE} {metric}: {len(hits)} facts, expected exactly one")
        picked[name] = hits[0]
    return picked


def _cp1_operands(cp1: Module) -> tuple[Cp1Operands, dict[str, Fact]]:
    """The Stage 1 `Cp1Operands` read from the CP-1 head, and the facts they came from."""
    facts = _cp1_facts(cp1)
    figures: dict[str, Cp1Figure] = {}
    for name, fact in facts.items():
        if fact.status not in ("known", "missing", "not_applicable"):
            raise ValueError(f"CP-1 figure {name} is {fact.status}")
        if fact.value_class not in ("source", "calculated", "analyst_judgment"):
            raise ValueError(f"CP-1 figure {name}: value class {fact.value_class} is not readable")
        figures[name] = Cp1Figure(
            fact_id=fact.fact_id,
            figure=name,
            label=fact.label,
            unit=fact.unit or "",
            period=fact.period or "",
            amount=fact.amount,
            value_class=fact.value_class,
            currency=fact.currency,
            status=fact.status,
            limitation=fact.limitation,
        )
    operands = Cp1Operands(
        adjusted_ebitda=figures["adjusted_ebitda_ltm"],
        ebitda=figures["ebitda_ltm"],
        cfo=figures["cfo_ltm"],
        total_debt=figures["total_debt_ltm"],
        net_debt=figures["net_debt_ltm"],
        total_leverage=figures["total_leverage_adjusted"],
        net_leverage=figures["net_leverage_adjusted"],
    )
    return operands, facts


def _inputs(
    pack: PreparedPack, submission: EarningsQualitySubmission, upstream: Upstream
) -> tuple[EarningsQualityInputs, dict[str, Fact]]:
    """The one store adapter: the settled heads and the pack as the Stage 1 input object. Used by
    `submit` (through the validator), `probe` and `view`. Raises ValueError when the CP-1 head
    does not hold the seven operands."""
    operands, facts = _cp1_operands(upstream.cp1)
    return (
        EarningsQualityInputs(
            sources=tuple(s for s in pack.sources if s.source_id in SCOPE),
            cp1=operands,
            submission=submission,
            cp1b=upstream.cp1b_state,
        ),
        facts,
    )


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def _model_text_issues(submission: EarningsQualitySubmission) -> list[str]:
    """Rulings Stage 2 round 3: each model-text field the step later builds as run text is
    checked here with that type (`RunText`), so no composition can raise after the binding write.
    Lines are `<path>: <msg>` without the input value."""
    texts = [
        (f"assessments[{i}].rationale", a.rationale) for i, a in enumerate(submission.assessments)
    ]
    texts.append(("overall.rationale", submission.overall.rationale))
    found: list[str] = []
    for path, text in texts:
        try:
            _RUN_TEXT.validate_python(text)
        except ValidationError as error:
            found += [
                _line(f"{path}: ", e["msg"])
                for e in error.errors(include_input=False, include_url=False, include_context=False)
            ]
    return found


def _one_per_page(citations: Sequence[Citation]) -> tuple[Citation, ...]:
    """A derived fact's citations (Stage 2 round 3 ruling): one per (source, page), quoting the
    first of its own input quotes on that page, in input order. No quote is invented."""
    first: dict[tuple[str, str], Citation] = {}
    for citation in citations:
        first.setdefault((citation.source_id, citation.locator), citation)
    return tuple(first.values())


def _module_fact(cell: CellFact) -> Fact:
    fact = cell.to_fact()
    if cell.value_class != "calculated":
        return fact  # a sourced fact quotes its own field
    return fact.model_copy(update={"citations": _one_per_page(fact.citations)})


def _checked(
    pack: PreparedPack, submission: EarningsQualitySubmission, upstream: Upstream
) -> tuple[tuple[str, ...], EarningsQualityReport | None]:
    """(issues, None) for a refused submission, else ((), the composed report). Every check runs
    before any product record is built from model text, and a record the product refuses
    (`ValidationError`) is reported as an issue line, never raised."""
    found = [*_provenance_issues(upstream), *_stale_issues(upstream)]
    if found:
        return _bounded(found), None
    try:
        inputs, cp1_facts = _inputs(pack, submission, upstream)
    except ValueError as error:
        return (_line("CP-1 operands unavailable: ", str(error)),), None
    issues = validation_issues(inputs)
    if issues:
        return issues, None
    texts = _model_text_issues(submission)
    if texts:
        return _bounded(texts), None
    try:
        result = compute(inputs)
        module_facts = tuple(_module_fact(f) for f in result.facts)
        prose = prose_issues(
            submission.overall.rationale, bind((*module_facts, *cp1_facts.values()))
        )
        if prose:
            return _bounded(prose), None
        return (), _report(pack, submission, result, module_facts, cp1_facts)
    except ValidationError as error:
        return _bounded(
            _line(f"{'.'.join(map(str, e['loc'])) or '(root)'}: ", e["msg"])
            for e in error.errors(include_input=False, include_url=False, include_context=False)
        ), None


def validate_earnings_quality(
    *, pack: PreparedPack, submission: EarningsQualitySubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Every issue of one submission: the bound-input checks, the Stage 1 calculation rules, the
    model-text types, the overall rationale's references against the module's facts and the
    seven CP-1 facts, and the product's own record checks. Bounded to `MAX_ISSUES` lines."""
    return _checked(pack, submission, upstream)[0]


def _reference_fact(figure: str, fact: Fact) -> Fact:
    return fact.model_copy(update={"table_id": CP1_REFERENCES, "row_id": figure, "field": "value"})


_COLUMN_LABELS = {"cfo_to_ebitda": "CFO to EBITDA"}
_ROW_HEADERS = {
    "T1D.1": "Add-back",
    "T1D.2": "Add-back",
    "T1D.3": "Bridge line",
    "T1D.4": "Tie-out",
    "T1D.5": "Basis",
    "T1D.6": "Basis",
    "T1D.7": "Gap",
}


def _report_table(table: Table, facts: Mapping[str, Fact]) -> ReportTable:
    fields = [facts[fid].field for fid in table.rows[0].fact_ids]
    return ReportTable(
        table_id=table.table_id,
        title=table.title,
        columns=tuple(
            TableColumn(field=name, label=_COLUMN_LABELS.get(name, name.replace("_", " ").title()))
            for name in fields
        ),
        rows=tuple(
            ReportRow(row_id=row.row_id, label=row.label, fact_ids=row.fact_ids)
            for row in table.rows
        ),
        row_header=_ROW_HEADERS.get(table.table_id),
    )


def _report(
    pack: PreparedPack,
    submission: EarningsQualitySubmission,
    result: EarningsQualityResult,
    module_facts: tuple[Fact, ...],
    cp1_facts: Mapping[str, Fact],
) -> EarningsQualityReport:
    by_id = {f.fact_id: f for f in module_facts}
    referenced = tuple(_reference_fact(name, fact) for name, fact in cp1_facts.items())
    by_figure = {name: fact for name, fact in zip(cp1_facts, referenced, strict=True)}
    tables = [_report_table(t, by_id) for t in result.tables]
    tables.append(
        ReportTable(
            table_id=CP1_REFERENCES,
            title="CP-1 facts referenced in CP-1D",
            columns=(TableColumn(field="value", label="Value"),),
            rows=tuple(
                ReportRow(row_id=r.row_id, label=r.label, fact_ids=(by_figure[r.figure].fact_id,))
                for r in result.cp1_references
            ),
            row_header="CP-1 fact",
        )
    )
    claims = tuple(
        Claim(
            claim_id=c.claim_id,
            text=c.text,
            citations=tuple(c.evidence or ()),
            limitation=c.limitation,
        )
        for c in result.claims
    )
    return EarningsQualityReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=tuple(tables),
        facts=(*module_facts, *referenced),
        claims=claims,
        limitations=tuple(dict.fromkeys(result.limitations)),
    )


def earnings_quality(
    *, pack: PreparedPack, submission: EarningsQualitySubmission, upstream: Upstream
) -> EarningsQualityReport:
    """The composed CP-1D report of a valid submission; raises ValueError on any issue."""
    issues, report = _checked(pack, submission, upstream)
    if issues or report is None:
        raise ValueError("; ".join(issues))
    return report


def cp1d_module(report: EarningsQualityReport, *, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-1D candidate: the report bound to `inputs` plus the one `*-submission` input."""
    run = report.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=MODULE_ID,
        inputs=(*inputs, Input(input_id=SUBMISSION_INPUT, sha256=report.submission_sha256)),
        facts=report.facts,
        tables=report.tables,
        claims=report.claims,
        limitations=report.limitations,
        attempt=attempt,
    )


def context_block(*, pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """The exact `read_inputs` view (lease key tree): the upstream statuses, the bridge rows as
    the table rule reads them, the seven CP-1 facts a `{ref|unit}` may name, the CP-1 T4.17 row
    count and the limitations settlement will inherit. No quote or citation text is in it."""
    source = next((s for s in pack.sources if s.source_id == BRIDGE_SOURCE_ID), None)
    bridge = (
        parse_bridge(_pages(source)) if source is not None and source.status == "ready" else None
    )
    facts = _cp1_facts(upstream.cp1)
    rows = {f.row_id for f in upstream.cp1.facts if f.table_id == "T4.17"}
    return {
        "upstream": [
            {"module_id": item.input_id, "status": item.status}
            for item in upstream.bound
            if item.input_id.startswith("CP-")
        ],
        "bridge": {
            "state": "present" if source is not None else "absent",
            "source_id": None if source is None else source.source_id,
            "pages": [] if source is None else [span.locator for span in source.spans],
            "items": []
            if bridge is None
            else [
                {
                    "row": item.row_id,
                    "label": item.label,
                    "type": item.type,
                    "status": item.status,
                    "claimed_ref": None if item.amount is None else f"T1D.1.{item.row_id}.claimed",
                    "claimed_shown": None
                    if item.amount is None
                    else _spell(item.amount, "MILLIONS", None),
                }
                for item in bridge.items
            ],
            "totals": None
            if bridge is None
            else {
                "proposed_total": None
                if bridge.proposed_total is None
                else _spell(bridge.proposed_total, "MILLIONS", None),
                "management_ebitda": None
                if bridge.management_ebitda is None
                else _spell(bridge.management_ebitda, "MILLIONS", None),
            },
        },
        "cp1_facts": [
            {
                "ref": fact.fact_id,
                "label": fact.label,
                "period": fact.period,
                "unit": figure_unit(fact) or fact.unit,
                "shown": spelled(fact),
            }
            for fact in facts.values()
            if fact.status == "known"
        ],
        "cp1_t417_rows": len(rows),
        "cp1_facts_note": (
            "Reference a CP-1 figure only as {ref|unit} with a ref and unit listed in cp1_facts; "
            "reference a module figure as {T1D.x.y.z|unit}. Quote evidence only from read_pages."
        ),
        "inherited_limitations": list(upstream.inherited),
    }


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the one `read_inputs` view over the bound heads, as compact JSON."""
    block = context_block(pack=historical.pack(), upstream=cp1d_upstream(historical, attempt))
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


# --- the tool-use rule, the validator, submit and the verifier probe ---------------------------


def RULES(text: str, seen: Seen) -> tuple[str, ...]:
    """The tool-use evidence rule (protocol section 2): every cited page was returned by
    `read_pages` in the step. The schema holds no `ABSENCE_MARKERS` value, so the product's
    cited-page rule (`live.tools.unread_citation_issues`, bounded and sorted) is the only one."""
    return unread_citation_issues(text, seen)


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands `Execution.submit_step` and the verifier replays: the
    attempt's last step is the one under validation."""
    step = attempt.steps[-1]
    try:
        submission = EarningsQualitySubmission.model_validate_json(
            store.payload(step.payload_sha256)
        )
    except ValidationError as error:
        return StepValidation(issues=shape_issues(error))
    issues, report = _checked(pack, submission, cp1d_upstream(store, attempt))
    if issues or report is None:
        return StepValidation(issues=issues)
    return StepValidation(output=report.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    report = EarningsQualityReport.model_validate_json(output)
    return cp1d_module(report, inputs=attempt.inputs, attempt=attempt.number)


def _with_rules(
    validate: Callable[[PreparedPack, Attempt], StepValidation],
    rules: Callable[[str], tuple[str, ...]],
    payload: str,
) -> Callable[[PreparedPack, Attempt], StepValidation]:
    """`validate`, then the tool-use rule issues of the retained payload appended."""

    def run(pack: PreparedPack, attempt: Attempt) -> StepValidation:
        outcome = validate(pack, attempt)
        found = rules(payload)
        if not found:
            return outcome
        return StepValidation(
            output=outcome.output, issues=tuple(dict.fromkeys((*outcome.issues, *found)))
        )

    return run


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `earnings_quality` step (null resolution through `SCHEMAS`, the rule
    issues appended) and, when it is valid, settle CP-1D with the Python candidate."""
    from deploy_vii.live.schema import normalise as normalise_payload

    if step_id != STEP_ID:
        raise ValueError(f"CP-1D has one step, {STEP_ID}")
    normal, resolved = normalise_payload(EarningsQualitySubmission, payload)
    validate: Callable[[PreparedPack, Attempt], StepValidation] = lambda pack, current: (
        _validate_step(store, pack, current)
    )
    if rules is not None and rules(normal):
        validate = _with_rules(validate, rules, normal)
    attempt = store.submit_step(ticket_id, MODULE_ID, STEP_IDS, step_id, normal, validate)
    if (
        attempt.status == "pending"
        and len(attempt.steps) == 1
        and attempt.steps[0].status == "valid"
    ):
        outcome = _validate_step(store, store.pack(), attempt)
        if outcome.issues or not outcome.retained_as(attempt.steps[0]):
            raise ValueError("Retained CP-1D output differs from trusted validation")
        candidate = _candidate(outcome.output or "", attempt)
        attempt = store.finish(
            ticket_id,
            candidate.model_dump_json(),
            lambda supplied: () if supplied == candidate else ("CP-1D candidate differs",),
            qualification=QUALIFICATION,
        )
    return Submitted(attempt, normal, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun the step validator and settlement over the settled snapshot (nothing is written);
    `WorkflowError("identity_mismatch")` unless the head rebuilds exactly."""
    from deploy_workflow.owners.cp1a import probe_one_step

    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


_ = settle  # re-exported for tests that replay settlement
