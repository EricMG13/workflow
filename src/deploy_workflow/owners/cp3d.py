"""CP-3D (market implied risk) owner core: Stage 1, the calculation.

Pure functions only: no store, host, session or render call and no I/O. The analyst submits
references and judgment (`MarketImpliedSubmission`); Python parses each quoted numeral, derives
every figure with `Decimal` (`compose`) and composes the lease's tables T3E.1-T3E.9, claims and
own limitations (`market_implied_result`). `submission_issues` is the validator of the lease's
journaled refusals that are calculation outcomes. Conventions: `docs/CP3D-OWNER-LEASE.md`
(Method) and `cases/cp3d-owner/expected.json#arithmetic`.

The last section, "Stage 2 connections", binds the core to the owner workflow: the store
adapter (`cp3d_upstream`), the report and module builders, the plug-in parts of
`docs/G1X-OWNER-CORE-PROTOCOL.md` section 2 and the consumer reader. Everything above it stays
pure.
"""

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from functools import partial
from typing import Literal, Protocol, Self

from pydantic import TypeAdapter, ValidationError

from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Input,
    Module,
    ReportTable,
    Run,
    RunText,
    TableColumn,
    TableRow,
)
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepValidation,
    clipped,
)
from deploy_vii.live.schema import exact_json, json_object
from deploy_vii.live.schema import normalise as normalise_payload
from deploy_vii.live.submission import Submitted, _with_rules
from deploy_vii.live.tools import UNBACKED_ABSENCE, Seen, unread_citation_issues
from deploy_vii.preparation import PreparedPack
from deploy_vii.quotes import hyphen_wrapped, normalise, quoted, reading
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners.blank import is_blank
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.workflow import WorkflowError

MODULE_ID = "CP-3D"

# --- submission schema (reference and judgment only) -------------------------------------------


class QuoteRef(Contract):
    source_id: str
    locator: str
    quote: str


class Instrument(Contract):
    name: str
    quote: QuoteRef


class Observation(Contract):
    kind: str
    source_id: str
    locator: str
    quote: str
    level_text: str
    as_of_text: str | None = None


class Absence(Contract):
    reason: str
    follow_up: str


class MaturityTerm(Contract):
    quote: QuoteRef | None = None
    date_text: str | None = None
    absence: Absence | None = None


class MarginTerm(Contract):
    quote: QuoteRef | None = None
    bps_text: str | None = None
    absence: Absence | None = None


class AmortisationTerm(Contract):
    quote: QuoteRef | None = None
    value_text: str | None = None
    absence: Absence | None = None


class ReferenceLevel(Contract):
    quote: QuoteRef
    percent_text: str


class ReferenceRate(Contract):
    name: str
    quote: QuoteRef
    level: ReferenceLevel | None = None
    absence: Absence | None = None


class Terms(Contract):
    maturity: MaturityTerm
    margin: MarginTerm
    amortisation: AmortisationTerm
    reference_rate: ReferenceRate


class Recovery(Contract):
    percent_text: str
    rationale: str


class Technical(Contract):
    aspect: str
    category: str
    text: str
    basis: tuple[QuoteRef, ...] = ()
    limitation: str | None = None


class Summary(Contract):
    text: str


class MarketImpliedSubmission(Contract):
    instrument: Instrument
    observations: tuple[Observation, ...] = ()
    market_absence: Absence | None = None
    terms: Terms
    recovery: Recovery | None = None
    recovery_absence: Absence | None = None
    technicals: tuple[Technical, ...] = ()
    summary: Summary


@dataclass(frozen=True)
class MarketContext:
    """What the composer and validator read besides the submission (Stage 2 binds each)."""

    pages: Mapping[str, Mapping[str, str]]  # source_id -> locator -> page text (the pack)
    names: Mapping[str, str]  # source_id -> pack source name
    third_party: frozenset[str]  # CP-0 T3 sources whose authority is third_party
    # (source_id, locator) -> the `Published <date>` the page itself states
    published: Mapping[tuple[str, str], date]
    run_as_of: date


# --- dates and numerals ------------------------------------------------------------------------

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_ALT = "|".join(_MONTHS)
_DATE = re.compile(rf"^({_MONTH_ALT}) ([1-9]|[12][0-9]|3[01]), ((?:19|20)[0-9]{{2}})$")
_PUBLISHED = re.compile(rf"Published ((?:{_MONTH_ALT}) [0-9]{{1,2}}, [0-9]{{4}})\.")
_NUMERAL = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{1,4})?$")
_DECIMAL = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")  # any decimal numeral, before its shape
_SHAPE = "must have at most three integer digits and four decimal places"
_LEADING_ZERO = re.compile(r"^0[0-9]")  # an integer part longer than one digit, starting with 0
_NO_LEADING_ZERO = "must have no leading zero"  # ruling 6g
_RECOVERY = re.compile(r"^[0-9]{1,3}(?:\.[0-9]{1,2})?$")


def parse_date(text: str) -> date | None:
    """`Month D, YYYY` as a date; None when the text is not one."""
    m = _DATE.match(text)
    if m is None:
        return None
    try:
        return date(int(m.group(3)), _MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    except ValueError:
        return None


def _short_date(d: date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1][:3]} {d.year}"


_MINUS = r"(?<![A-Za-z0-9])-"  # round 10 item 1: a minus sign, not a hyphen after a letter or digit
# Round 12 rule W: the minus directly or one space before the figure (`normalise` prints any
# whitespace run, a line break included, as one space).
# Round 13 item 8: `<digit>,` and `<digit>, ` (one space) join the run, so no figure is read after
# them, nor before `,<digit>` or `, <digit>`.
_CUT_BEFORE = re.compile(
    rf"(?:[0-9.]|[0-9], ?|{_MINUS} ?)\Z"
)  # round 11 B1: the page figure starts earlier
_CUT_AFTER = re.compile(r"[0-9]|[.,][0-9]|, [0-9]")  # round 11 B1: the page figure goes on
# Round 13 addendum 4 (CP-1D H2 mirror): a quote that ends `<figure>,` ends at an edge, and one that
# starts `,<figure>` or `, <figure>` starts at one, so `_cut` sees the page's comma run.
_EDGE_AFTER = ("", ".", ",")  # nothing, a full stop or a comma after a figure at the quote end
_EDGE_BEFORE = ("", ",", ", ")  # nothing, a comma or a comma and a space before a figure


def _parenthesised(before: str, after: str) -> bool:
    """Round 10 item 1 with round 12 rule W: an accounting `(` or `( ` ends `before` and `)` or
    ` )` starts `after`."""
    return before.endswith(("(", "( ")) and after.startswith((")", " )"))


def _tokens(value_text: str, text: str) -> list[re.Match[str]]:
    """Where `value_text` is a whole unsigned numeric token of the normalised `text`.

    Round 10 item 1: the token is the signed numeral the text prints. A `-` directly before it
    that starts the text or follows a non-alphanumeric is a minus sign, and a token that starts
    with a digit with `(` directly before and `)` directly after reads as negative, so neither is
    an occurrence of the unsigned text. Round 11 B2: `(-425)` prints the signed `-425`, which
    occurs and gets its shape issue. A `-` after a letter or digit (`95-96`, `S-350`) and a `+`
    are not signs. Round 12 rule W: whitespace never separates a sign from its figure, so a minus
    one space before the token, and `( ` and ` )` around it, are signs too."""
    pattern = (
        rf"(?<![0-9.])(?<![0-9],)(?<![0-9], )(?<!{_MINUS})(?<!{_MINUS} )"
        + re.escape(value_text)
        + r"(?![0-9]|[.,][0-9]|, [0-9])"
    )
    accounting = re.match(r"[0-9]", value_text) is not None
    return [
        m
        for m in re.finditer(pattern, text)
        if not (accounting and _parenthesised(text[: m.start()], text[m.end() :]))
    ]


def _token_once(value_text: str, quote: str) -> bool:
    """`value_text` occurs exactly once as a whole numeric token (`_tokens`) in `quote`
    normalised, the text `quoted` matched (a soft hyphen never splits or ends a token)."""
    return len(_tokens(value_text, normalise(quote))) == 1


def _readings(raw: str) -> tuple[str, ...]:
    """`normalise(raw)`, and the reading with its hyphenated line wraps joined if it has one."""
    plain = normalise(raw)
    return (plain, reading(raw, join_wraps=True).text) if hyphen_wrapped(raw) else (plain,)


def _occurrences(needle: str, text: str) -> list[int]:
    """Every index at which `needle` starts in `text`, overlapping ones included."""
    found: list[int] = []
    at = text.find(needle)
    while at >= 0:
        found.append(at)
        at = text.find(needle, at + 1)
    return found


def _cut(page: str, start: int, end: int, *, at_start: bool, at_end: bool) -> bool:
    """Whether the page figure at [start, end) of a page reading is not the same unsigned whole
    figure: at a start edge a digit, `.` or minus sign (round 12 rule W: directly or one space)
    before it; at an end edge a digit or `.` and a digit after it; at either edge an accounting
    `(` and `)` around it, each with or without one space inside (rule W)."""
    before, after = page[:start], page[end:]
    if _parenthesised(before, after):
        return True
    return (at_start and _CUT_BEFORE.search(before) is not None) or (
        at_end and _CUT_AFTER.match(after) is not None
    )


def _whole_on_page(value_text: str, quote: str, page: str) -> bool:
    """Round 11 B1: a figure at an edge of the quote occurs only if the page holds the same
    unsigned whole figure there, at every occurrence of each needle (`normalise(quote)`, and its
    joined reading if the quote is wrapped) in each page reading.

    The start edge is nothing, a comma, or a comma and a space before the figure (`_EDGE_BEFORE`:
    round 13 item 8, a comma at the quote edge starts a run with the page's digits, so the figure
    is cut). The ruling's "or only a sign" changes no outcome here: such a sign is quoted, so the
    page prints it too; a minus is already no token (`_tokens`), and a `+` or an unclosed `(` is
    never a cut. The end edge is nothing, a full stop or a comma after it (`_EDGE_AFTER`); the
    page then cuts it by a digit, by `.` or `,` and a digit, or by `, ` and a digit
    (`_CUT_AFTER`)."""
    for needle in _readings(quote):
        for m in _tokens(value_text, needle):
            at_start = needle[: m.start()] in _EDGE_BEFORE
            at_end = needle[m.end() :] in _EDGE_AFTER
            if not (at_start or at_end):
                continue
            for text in _readings(page):
                for at in _occurrences(needle, text):
                    if _cut(text, at + m.start(), at + m.end(), at_start=at_start, at_end=at_end):
                        return False
    return True


_WRAP_SPLIT = re.compile(r"- ")
_W_SIGN = re.compile(r"(?<![A-Za-z0-9])- (?=[0-9])")  # rule W's minus, `_MINUS` plus a digit


def _name_occurs(name: str, quote: str) -> bool:
    """`name` is in the normalised quote. Round 11 B3: when the quote has a hyphenated line wrap,
    a name holding `- ` (the wrap as `normalise` prints it) does not occur. Round 13 addendum: a
    `- ` that is rule W's minus (not after a letter or digit, a digit next) is no wrap split. A
    `- ` at index 0 cannot see the page character before it, so it stays a wrap split."""
    if name not in normalise(quote):
        return False
    if not hyphen_wrapped(quote):
        return True
    plain = normalise(name)
    exempt = {m.start() for m in _W_SIGN.finditer(plain) if m.start() > 0}
    return all(m.start() in exempt for m in _WRAP_SPLIT.finditer(plain))


def publication_dates(pages: Mapping[str, Mapping[str, str]]) -> dict[tuple[str, str], date]:
    """Per page, the first `Published <Month D, YYYY>.` date the page itself states; a page that
    states none is absent (never defaulted). Ruling D1 (docs/rulings/2026-10-28-stage1.md)."""
    out: dict[tuple[str, str], date] = {}
    for source_id, by_locator in pages.items():
        for locator, text in by_locator.items():
            m = _PUBLISHED.search(text)
            parsed = parse_date(m.group(1)) if m else None
            if parsed is not None:
                out[(source_id, locator)] = parsed
    return out


# --- the calculation ---------------------------------------------------------------------------

PAR = Decimal(100)
BP = Decimal(10000)
POINTS = ("bid", "mid", "offer")
DefaultState = Literal["known", "missing", "not_applicable"]


@dataclass(frozen=True)
class MarketInputs:
    """Every operand of the Method. Levels in points of par (98.50); recovery and the reference
    rate level as fractions (0.7, 0.043); margin in basis points. None is missing, never 0."""

    bid: Decimal | None
    offer: Decimal | None
    talk: Decimal | None
    quotation_date: date | None
    maturity: date | None
    margin_bp: Decimal | None
    amortisation_zero: bool | None
    recovery: Decimal | None
    reference_rate_level: Decimal | None


@dataclass(frozen=True)
class PointMeasures:
    """Unrounded measures at one price (bid, mid or offer)."""

    discount_bp: Decimal | None
    margin_bp: Decimal | None
    intensity_bp: Decimal | None
    probability: Decimal | None
    default_state: DefaultState
    all_in_yield: Decimal | None


def _q(value: Decimal | None, places: int) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _s(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


@dataclass(frozen=True)
class Derived:
    """Exact intermediates (28 significant digits) of one composition; `stored()` quantises."""

    bid: Decimal | None
    offer: Decimal | None
    talk: Decimal | None
    mid: Decimal | None
    width: Decimal | None
    discount_mid_pts: Decimal | None
    talk_less_mid_pts: Decimal | None
    days: int | None
    years: Decimal | None
    margin_bp: Decimal | None
    points: Mapping[str, PointMeasures]

    def fraction(self, name: str) -> Decimal | None:
        """A level or price metric in points of par, stored as a fraction of par."""
        value: Decimal | None = getattr(self, name)
        return None if value is None else value / PAR

    def years_shown(self) -> Decimal | None:
        return _q(self.years, 2)

    def stored(self) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        for name in (
            "bid",
            "offer",
            "talk",
            "mid",
            "width",
            "discount_mid_pts",
            "talk_less_mid_pts",
        ):
            out[name] = _s(self.fraction(name))
        out["days"] = None if self.days is None else str(self.days)
        out["years"] = _s(self.years_shown())
        out["margin_bp"] = _s(self.margin_bp)
        for n in POINTS:
            p = self.points[n]
            out[f"disc_{n}"] = _s(_q(p.discount_bp, 1))
            out[f"dm_{n}"] = _s(_q(p.margin_bp, 1))
            out[f"lam_{n}"] = _s(_q(p.intensity_bp, 1))
            out[f"pd_{n}"] = _s(_q(p.probability, 4))
            out[f"pd_state_{n}"] = p.default_state
            out[f"yield_{n}"] = _s(_q(p.all_in_yield, 4))
        return out


def _point(inputs: MarketInputs, price: Decimal | None, years: Decimal | None) -> PointMeasures:
    discount = (PAR - price) / years * PAR if price is not None and years is not None else None
    # The simple margin needs a cited margin and a cited zero amortisation.
    margin = inputs.margin_bp if inputs.amortisation_zero is True else None
    dm = margin + discount if margin is not None and discount is not None else None
    intensity: Decimal | None = None
    probability: Decimal | None = None
    state: DefaultState
    if dm is None or inputs.recovery is None or years is None:
        state = "missing"
    elif dm <= 0:
        state = "not_applicable"
    else:
        intensity = dm / (1 - inputs.recovery)
        probability = 1 - (-(intensity / BP) * years).exp()
        state = "known"
    level = inputs.reference_rate_level
    all_in = level + dm / BP if level is not None and dm is not None else None
    return PointMeasures(discount, dm, intensity, probability, state, all_in)


def compose(*, inputs: MarketInputs) -> Derived:
    """Pure Decimal derivation of every Method figure from validated operands."""
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        bid, offer, talk = inputs.bid, inputs.offer, inputs.talk
        mid = (bid + offer) / 2 if bid is not None and offer is not None else None
        width = offer - bid if bid is not None and offer is not None else None
        days = None
        if inputs.quotation_date is not None and inputs.maturity is not None:
            days = (inputs.maturity - inputs.quotation_date).days
        years = Decimal(days) / Decimal(365) if days is not None else None
        prices = {"bid": bid, "mid": mid, "offer": offer}
        return Derived(
            bid=bid,
            offer=offer,
            talk=talk,
            mid=mid,
            width=width,
            discount_mid_pts=PAR - mid if mid is not None else None,
            talk_less_mid_pts=talk - mid if talk is not None and mid is not None else None,
            days=days,
            years=years,
            margin_bp=inputs.margin_bp,
            points={n: _point(inputs, prices[n], years) for n in POINTS},
        )


def _quotation_date(submission: MarketImpliedSubmission) -> date | None:
    dates = {
        parse_date(o.as_of_text)
        for o in submission.observations
        if o.kind in ("bid", "offer") and o.as_of_text
    }
    if len(dates) > 1:
        raise ValueError("bid and offer have different dates")
    return next(iter(dates), None)


def inputs_from_submission(submission: MarketImpliedSubmission) -> MarketInputs:
    """Parse the quoted numerals of a validated submission (`submission_issues` returned ())."""
    obs = {o.kind: o for o in submission.observations}

    def level(kind: str) -> Decimal | None:
        return Decimal(obs[kind].level_text) if kind in obs else None

    terms = submission.terms
    maturity = parse_date(terms.maturity.date_text) if terms.maturity.date_text else None
    margin = Decimal(terms.margin.bps_text) if terms.margin.bps_text else None
    amort = terms.amortisation.value_text
    rec = submission.recovery
    lvl = terms.reference_rate.level
    return MarketInputs(
        bid=level("bid"),
        offer=level("offer"),
        talk=level("indicative_talk"),
        quotation_date=_quotation_date(submission),
        maturity=maturity,
        margin_bp=margin,
        amortisation_zero=(Decimal(amort) == 0) if amort else None,
        recovery=Decimal(rec.percent_text) / PAR if rec else None,
        reference_rate_level=Decimal(lvl.percent_text) / PAR if lvl else None,
    )


# --- the validator (journaled refusals) --------------------------------------------------------

KINDS = ("bid", "offer", "indicative_talk")
ASPECTS = ("quote_quality", "trading_activity", "talk_versus_quote", "rating")
CATEGORIES = ("Documentary Fact", "Analyst Interpretation", "Insufficient Information")
_PROHIBITED = re.compile(
    r"\b(?:buy|sell|overweight|underweight|recommend|cheap|undervalued|overvalued|outperform"
    r"|attractive)\b",
    re.IGNORECASE,
)


class _Issues:
    def __init__(self, context: MarketContext) -> None:
        self.context = context
        self.items: list[str] = []

    def add(self, issue: str) -> None:
        self.items.append(issue)

    def digit_free(self, path: str, text: str | None) -> None:
        if text is not None and any(ch.isnumeric() for ch in text):
            self.add(f"{path}: digits are not allowed")

    def conclusion_free(self, path: str, text: str | None) -> None:
        """Ruling 6b C3: the pinned frame on every analyst text field; quotes are never checked."""
        if text is not None and _PROHIBITED.search(text):
            self.add(f"{path}: text carries a prohibited conclusion")

    def analyst_text(self, path: str, text: str | None) -> None:
        if text is not None and is_blank(text):  # round 11, round 12 B10: blank text class
            self.add(f"{path}: empty text")
            return
        self.digit_free(path, text)
        self.conclusion_free(path, text)

    def on_page(self, source_id: str, locator: str, quote: str, path: str) -> bool:
        if is_blank(quote):  # round 13 addendum 3: before the page check, every citation quote
            self.add(f"{path}: empty text")
            return False
        pages = self.context.pages
        if source_id not in pages:
            self.add(f"{path}: source {source_id} is not in the pack")
            return False
        page = pages[source_id].get(locator)
        if page is None or not quoted(quote, page):
            self.add(f"{path}: quote not found on {source_id} {locator}")
            return False
        return True

    def ref_on_page(self, ref: QuoteRef, path: str) -> bool:
        return self.on_page(ref.source_id, ref.locator, ref.quote, path)

    def occurs(self, value_text: str, source_id: str, locator: str, quote: str) -> bool:
        """Ruling 6b C2 with rounds 10 and 11: `value_text` is the one whole unsigned token of
        the quote, and the page holds it whole at a quote edge (B1). Only after `on_page`."""
        page = self.context.pages[source_id][locator]
        return _token_once(value_text, quote) and _whole_on_page(value_text, quote, page)


def _labelled(kind: str, level_text: str, quote: str) -> bool:
    words = normalise(quote)  # the text `quoted` matched
    return (
        re.search(rf"\b{kind}\s+{re.escape(level_text)}(?![0-9])", words, re.IGNORECASE) is not None
    )


def _observation_level(o: Observation, path: str, out: _Issues) -> Decimal | None:
    """The level of one observation, or None after recording its first issue."""
    if o.kind not in KINDS:
        out.add(f"{path}: kind {o.kind} is not one of bid, offer, indicative_talk")
        return None
    if o.source_id in out.context.pages and o.source_id not in out.context.third_party:
        out.add(f"{path}: source {o.source_id} is not a third_party source (CP-0 T3)")
        return None
    if not out.on_page(o.source_id, o.locator, o.quote, path):
        return None
    lt = o.level_text
    if not _DECIMAL.match(lt):  # keeps pinned refusals[1] ("ninety")
        out.add(f"{path}: level_text {lt} is not a decimal number")
        return None
    if not out.occurs(lt, o.source_id, o.locator, o.quote):  # ruling 6b C2: occurrence first
        out.add(f"{path}: level_text {lt} does not occur in the quote")
        return None
    if _LEADING_ZERO.match(lt):  # ruling 6g: after occurrence, before decimals and bound
        out.add(f"{path}: level_text {lt} {_NO_LEADING_ZERO}")
        return None
    if o.kind == "indicative_talk":
        if _labelled("(?:bid|offer)", lt, o.quote):
            out.add(f"{path}: indicative_talk level_text {lt} is a bid or offer level in the quote")
            return None
    elif not _labelled(o.kind, lt, o.quote):
        out.add(f"{path}: {o.kind} level_text {lt} is not labelled {o.kind} in the quote")
        return None
    if "." in lt and len(lt.split(".")[1]) > 4:
        out.add(f"{path}: level_text {lt} must have at most four decimal places")
        return None
    value = Decimal(lt)
    if not 0 < value <= 200:  # also every level of more than three integer digits
        out.add(f"{path}: level must be above 0 and at most 200")
        return None
    return value


def _observation_date(o: Observation, path: str, out: _Issues) -> date | None:
    if o.as_of_text is None:
        if o.kind != "indicative_talk":
            out.add(f"{path}: {o.kind} needs as_of_text")
        return None
    parsed = parse_date(o.as_of_text)
    if o.as_of_text not in normalise(o.quote) or parsed is None:
        out.add(f"{path}: as_of_text {o.as_of_text} does not occur in the quote")
        return None
    return parsed


def _check_observations(sub: MarketImpliedSubmission, out: _Issues) -> date | None:
    """Observation rules; returns the quotation date (bid's, else offer's) when one is valid."""
    if bool(sub.observations) == bool(sub.market_absence):
        out.add("observations: exactly one of observations and market_absence is required")
    kinds = [o.kind for o in sub.observations]
    for k in dict.fromkeys(kinds):
        if kinds.count(k) > 1:
            out.add(f"observations: kind {k} appears more than once")
    levels: dict[str, Decimal] = {}
    dates: dict[str, date] = {}
    for i, o in enumerate(sub.observations):
        path = f"observations[{i}]"
        value = _observation_level(o, path, out)
        if value is None:
            continue
        levels[o.kind] = value
        parsed = _observation_date(o, path, out)
        if parsed is not None:
            dates[o.kind] = parsed
    if "bid" in levels and "offer" in levels:
        if levels["bid"] > levels["offer"]:
            out.add("observations: bid exceeds offer")
        if "bid" in dates and "offer" in dates and dates["bid"] != dates["offer"]:
            out.add("observations: bid and offer have different dates")
    return dates.get("bid") or dates.get("offer")


def _check_quoted_numeral(
    key: str, label: str, text: str | None, quote: QuoteRef | None, out: _Issues
) -> Decimal | None:
    """A `*_text` numeral that must occur once as a whole token in its own on-page quote."""
    if quote is None or text is None:
        out.add(f"{key}: {label} {text} does not occur in the quote")
        return None
    if not out.ref_on_page(quote, key):
        return None
    if not out.occurs(text, quote.source_id, quote.locator, quote.quote):  # ruling 6b C2
        out.add(f"{key}: {label} {text} does not occur in the quote")
        return None
    if _LEADING_ZERO.match(text):  # ruling 6g
        out.add(f"{key}: {label} {text} {_NO_LEADING_ZERO}")
        return None
    if not _NUMERAL.match(text):
        out.add(f"{key}: {label} {text} {_SHAPE}")
        return None
    return Decimal(text)


def _check_maturity(term: MaturityTerm, quotation: date | None, out: _Issues) -> None:
    if bool(term.date_text) == bool(term.absence):
        out.add("maturity: exactly one of date_text and absence is required")
        return
    if not term.date_text:
        return
    if term.quote is None:
        out.add(f"maturity: date_text {term.date_text} does not occur in the quote")
        return
    if not out.ref_on_page(term.quote, "maturity"):
        return
    parsed = parse_date(term.date_text)
    if parsed is None or term.date_text not in normalise(term.quote.quote):
        out.add(f"maturity: date_text {term.date_text} does not occur in the quote")
    elif quotation is not None and parsed <= quotation:
        out.add("maturity: date is not after the quotation date")


def _check_terms(terms: Terms, quotation: date | None, out: _Issues) -> None:
    _check_maturity(terms.maturity, quotation, out)
    for key, term_absence in (
        ("maturity", terms.maturity.absence),
        ("margin", terms.margin.absence),
        ("amortisation", terms.amortisation.absence),
    ):
        if term_absence is not None:
            out.analyst_text(f"{key}.absence.reason", term_absence.reason)
            out.analyst_text(f"{key}.absence.follow_up", term_absence.follow_up)
    margin = terms.margin
    if bool(margin.bps_text) == bool(margin.absence):
        out.add("margin: exactly one of bps_text and absence is required")
    elif margin.bps_text:
        _check_quoted_numeral("margin", "bps_text", margin.bps_text, margin.quote, out)
    amort = terms.amortisation
    if bool(amort.value_text) == bool(amort.absence):
        out.add("amortisation: exactly one of value_text and absence is required")
    elif amort.value_text:
        value = _check_quoted_numeral(
            "amortisation", "value_text", amort.value_text, amort.quote, out
        )
        if value is not None and value != 0:
            out.add("amortisation: the simple margin convention requires zero amortisation")
    rr = terms.reference_rate
    out.analyst_text("reference_rate.name", rr.name)  # ruling 6e item 3
    if out.ref_on_page(rr.quote, "reference_rate.quote") and not _name_occurs(
        rr.name, rr.quote.quote
    ):
        out.add("reference_rate: name does not occur in the quote")
    if bool(rr.level) == bool(rr.absence):
        out.add("reference_rate: exactly one of level and absence is required")
    elif rr.level is not None and out.ref_on_page(rr.level.quote, "reference_rate.level.quote"):
        pt = rr.level.percent_text
        q = rr.level.quote
        if not out.occurs(pt, q.source_id, q.locator, q.quote):  # ruling 6b C2
            out.add(f"reference_rate: level percent_text {pt} does not occur in the quote")
        elif _LEADING_ZERO.match(pt):  # ruling 6g
            out.add(f"reference_rate: level percent_text {pt} {_NO_LEADING_ZERO}")
        elif not _NUMERAL.match(pt):
            out.add(f"reference_rate: level percent_text {pt} {_SHAPE}")
    if rr.absence is not None:
        out.analyst_text("reference_rate.absence.reason", rr.absence.reason)
        out.analyst_text("reference_rate.absence.follow_up", rr.absence.follow_up)


def _check_recovery(sub: MarketImpliedSubmission, out: _Issues) -> None:
    rec = sub.recovery
    if bool(rec) == bool(sub.recovery_absence):
        out.add("recovery: exactly one of recovery and recovery_absence is required")
    elif rec is not None:
        out.analyst_text("recovery.rationale", rec.rationale)
        ok = _RECOVERY.match(rec.percent_text) is not None
        if _LEADING_ZERO.match(rec.percent_text):  # ruling 6h: before the shape and bound
            out.add(f"recovery: percent_text {rec.percent_text} {_NO_LEADING_ZERO}")
        elif not ok or not Decimal(0) <= Decimal(rec.percent_text) < PAR:
            out.add("recovery: percent must be at least 0 and below 100")


def _check_technicals(sub: MarketImpliedSubmission, out: _Issues) -> None:
    aspects = [x.aspect for x in sub.technicals]
    for i, x in enumerate(sub.technicals):
        path = f"technicals[{i}]"
        if x.aspect not in ASPECTS:
            out.add(f"{path}: aspect {x.aspect} is not one of {', '.join(ASPECTS)}")
        elif aspects.count(x.aspect) > 1:
            out.add(f"{path}: aspect {x.aspect} appears more than once")
        if x.category not in CATEGORIES:
            out.add(f"{path}: category {x.category} is not allowed")
        out.analyst_text(f"{path}.text", x.text)
        out.analyst_text(f"{path}.limitation", x.limitation)
        if (x.category == "Insufficient Information") != bool(x.limitation):
            out.add(f"{path}: limitation is required for Insufficient Information and only for it")
        if x.category == "Documentary Fact" and not x.basis:
            out.add(f"{path}: a Documentary Fact needs at least one basis quote")
        for j, b in enumerate(x.basis):
            out.ref_on_page(b, f"{path}.basis[{j}]")


def submission_issues(
    *, submission: MarketImpliedSubmission, context: MarketContext
) -> tuple[str, ...]:
    """Every validator issue of a submission, in rule order (empty: valid)."""
    out = _Issues(context)
    quotation = _check_observations(submission, out)
    for key, absence in (
        ("market_absence", submission.market_absence),
        ("recovery_absence", submission.recovery_absence),
    ):
        if absence is not None:
            out.analyst_text(f"{key}.reason", absence.reason)
            out.analyst_text(f"{key}.follow_up", absence.follow_up)
    inst = submission.instrument
    out.analyst_text("instrument.name", inst.name)
    if out.ref_on_page(inst.quote, "instrument.quote") and not _name_occurs(
        inst.name, inst.quote.quote
    ):
        out.add("instrument: name does not occur in the quote")
    _check_terms(submission.terms, quotation, out)
    _check_recovery(submission, out)
    _check_technicals(submission, out)
    out.analyst_text("summary.text", submission.summary.text)
    return tuple(out.items)


# --- tables ------------------------------------------------------------------------------------

Cite = tuple[str, str]
CellStatus = Literal["known", "missing", "not_applicable"]
ValueClass = Literal["source", "calculated", "analyst_judgment"]
GAP_SHOWN = "∅ G#"  # the gap spelling; G# is bound at run time (G2)
NOT_MEANINGFUL_SHOWN = "∅ G# n.m."


class _Located(Protocol):
    @property
    def source_id(self) -> str: ...

    @property
    def locator(self) -> str: ...

    @property
    def quote(self) -> str: ...


@dataclass(frozen=True)
class _Ref:
    source_id: str
    locator: str
    quote: str


class Cites(tuple[Cite, ...]):
    """The pages a cell rests on, as the (source_id, locator) pairs the oracle pins (it compares
    equal to the plain tuple), and for each page the distinct submitted quotes the cell rests on,
    in order (`quotes`). A derived cell rests on every input quote; none is invented."""

    quotes: Mapping[Cite, tuple[str, ...]]

    def __new__(cls, refs: Iterable[_Located] = ()) -> Self:
        pairs: list[Cite] = []
        found: dict[Cite, list[str]] = {}
        for r in refs:
            key = (r.source_id, r.locator)
            if key not in pairs:
                pairs.append(key)
            quotes = found.setdefault(key, [])
            if r.quote not in quotes:
                quotes.append(r.quote)
        self = super().__new__(cls, pairs)
        self.quotes = {k: tuple(v) for k, v in found.items()}
        return self

    @classmethod
    def merged(cls, parts: Iterable["Cites"]) -> "Cites":
        return cls(
            _Ref(source_id, locator, quote)
            for part in parts
            for (source_id, locator), quotes in part.quotes.items()
            for quote in quotes
        )


NO_CITES = Cites()


@dataclass(frozen=True)
class Cell:
    fact_id: str
    column: str
    period: str | None
    amount: Decimal | None
    unit: str | None
    decimals: int | None
    text: str | None
    shown: str
    status: CellStatus
    cites: Cites
    value_class: ValueClass | None
    calculation_id: str | None
    formula: str | None
    limitation: str | None


@dataclass(frozen=True)
class Row:
    row_id: str
    label: str
    facts: tuple[Cell, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    row_header: str
    columns: tuple[tuple[str, str], ...]
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class ClaimText:
    claim_id: str
    text: str
    refs: tuple[str, ...]
    cites: Cites


@dataclass(frozen=True)
class MarketImpliedResult:
    derived: Derived
    tables: tuple[Table, ...]
    claims: tuple[ClaimText, ...]
    own_limitations: tuple[str, ...]


def _trace(refs: Iterable[_Located]) -> Cites:
    return Cites(refs)


@dataclass(frozen=True)
class _Num:
    amount: Decimal
    unit: str
    decimals: int | None
    cites: Cites = NO_CITES
    value_class: ValueClass = "calculated"
    calculation_id: str | None = None
    formula: str | None = None
    period: str | None = None


@dataclass(frozen=True)
class _Text:
    text: str
    cites: Cites = NO_CITES
    value_class: ValueClass | None = None


@dataclass(frozen=True)
class _Gap:
    reason: str
    unit: str | None = None
    status: CellStatus = "missing"


_Content = _Num | _Text | _Gap
_RowSpec = tuple[str, str, Sequence[_Content]]


def _spell(fact_id: str, label: str, num: _Num, period: str) -> str:
    """The product spelling of a known numeric fact (report_view.fact_spelling)."""
    fact = Fact(
        fact_id=fact_id,
        label=label,
        amount=num.amount,
        unit=num.unit,
        decimals=num.decimals,
        period=period,
    )
    return fact_spelling(fact, None)[2]


def _cell(fact_id: str, column: str, content: _Content, default_period: str) -> Cell:
    if isinstance(content, _Num):
        period = content.period or default_period
        return Cell(
            fact_id,
            column,
            period,
            content.amount,
            content.unit,
            content.decimals,
            None,
            _spell(fact_id, column, content, period),
            "known",
            content.cites,
            content.value_class,
            content.calculation_id,
            content.formula,
            None,
        )
    if isinstance(content, _Text):
        return Cell(
            fact_id,
            column,
            None,
            None,
            None,
            None,
            content.text,
            content.text,
            "known",
            content.cites,
            content.value_class,
            None,
            None,
            None,
        )
    shown = GAP_SHOWN if content.status == "missing" else NOT_MEANINGFUL_SHOWN
    return Cell(
        fact_id,
        column,
        None,
        None,
        content.unit,
        None,
        None,
        shown,
        content.status,
        NO_CITES,
        None,
        None,
        None,
        content.reason,
    )


def _table(
    table_id: str,
    title: str,
    columns: Sequence[tuple[str, str]],
    rows: Sequence[_RowSpec],
    row_header: str,
    period: str,
) -> Table:
    built = []
    for row_id, label, contents in rows:
        if len(contents) != len(columns):
            raise ValueError(
                f"{table_id}.{row_id}: {len(contents)} cells for {len(columns)} columns"
            )
        facts = tuple(
            _cell(f"{table_id}.{row_id}.{fld}", col, c, period)
            for (fld, col), c in zip(columns, contents, strict=True)
        )
        built.append(Row(row_id, label, facts))
    return Table(table_id, title, row_header, tuple(columns), tuple(built))


NO_MARKET = "No market level: the pack holds no third-party market quotation source"
NEED_YEARS = "Not calculable: needs a quotation date and a final maturity date"
NEED_MID = "Not calculable: needs both an observed bid and an observed offer"
NEED_RATE = "Not calculable: no reference rate level in any source"
NEED_DM = "Not calculable: needs a stated contractual margin and a stated zero amortisation"
NEED_DEFAULT = "Not calculable: needs a simple discount margin and a recovery assumption"
NOT_MEANINGFUL = "Not meaningful: the simple discount margin is not positive"
NOT_STATED = "Not stated: no observation submitted"
_POINT_COLUMNS = (("bid", "At bid"), ("mid", "At mid"), ("offer", "At offer"))
_CONVENTION = ("convention", "Convention")


@dataclass
class _Composer:
    """Composes T3E.1-T3E.9 and the claims of one validated submission."""

    sub: MarketImpliedSubmission
    ctx: MarketContext
    derived: Derived
    obs: dict[str, Observation] = field(init=False)
    stored: dict[str, str | None] = field(init=False)
    market_absent: bool = field(init=False)

    def __post_init__(self) -> None:
        self.obs = {o.kind: o for o in self.sub.observations}
        self.stored = self.derived.stored()
        self.market_absent = self.sub.market_absence is not None

    # periods ----------------------------------------------------------------------------------
    @property
    def run_period(self) -> str:
        return f"Run as of {self.ctx.run_as_of.isoformat()}"

    @property
    def quotation_period(self) -> str:
        quotation = _quotation_date(self.sub)
        return f"Quotation of {quotation.isoformat()}" if quotation else self.run_period

    def _published(self, ref: _Located) -> str:
        """` published <iso date>` from the cited page's `Published` line, else the ruled
        `, publication date not stated` (ruling D1: never fail closed)."""
        stated = self.ctx.published.get((ref.source_id, ref.locator))
        return f" published {stated.isoformat()}" if stated else ", publication date not stated"

    def talk_period(self) -> str:
        return f"Commentary{self._published(self.obs['indicative_talk'])}"

    def terms_period(self, ref: QuoteRef) -> str:
        return f"Facility terms in the {ref.source_id} source{self._published(ref)}"

    # shared operands ---------------------------------------------------------------------------
    def why(self, reason: str) -> str:
        """A gap reason; with no market source in the pack the reason is that."""
        return NO_MARKET if self.market_absent else reason

    def cites_of(self, *kinds: str) -> tuple[_Located, ...]:
        return tuple(self.obs[k] for k in kinds if k in self.obs)

    @property
    def terms_refs(self) -> tuple[QuoteRef, ...]:
        """The margin, amortisation and maturity quotes every spread figure rests on."""
        t = self.sub.terms
        return tuple(r for r in (t.margin.quote, t.amortisation.quote, t.maturity.quote) if r)

    def point_refs(self, n: str) -> tuple[_Located, ...]:
        return self.cites_of("bid", "offer") if n == "mid" else self.cites_of(n)

    def point_need(self, n: str) -> str:
        if self.derived.days is None:
            return self.why(NEED_YEARS)
        return {
            "bid": self.why("Not calculable: no observed bid"),
            "mid": self.why(NEED_MID),
            "offer": self.why("Not calculable: no observed offer"),
        }[n]

    def dm_need(self, n: str) -> str:
        if self.derived.days is None or self.stored[f"disc_{n}"] is None:
            return self.point_need(n)
        return self.why(NEED_DM)

    def calc(
        self,
        value: str | None,
        unit: str,
        decimals: int | None,
        refs: Iterable[_Located],
        calculation_id: str,
        formula: str,
        need: str,
        period: str | None = None,
    ) -> _Content:
        if value is None:
            return _Gap(need, unit)
        return _Num(
            Decimal(value),
            unit,
            decimals,
            _trace(refs),
            calculation_id=calculation_id,
            formula=formula,
            period=period,
        )

    def table(
        self,
        table_id: str,
        title: str,
        columns: Sequence[tuple[str, str]],
        rows: Sequence[_RowSpec],
        row_header: str,
    ) -> Table:
        return _table(table_id, title, columns, rows, row_header, self.quotation_period)

    # T3E.1 ------------------------------------------------------------------------------------
    def _level_row(self, kind: str, label: str) -> list[_Content]:
        o = self.obs.get(kind)
        if o is None:
            missing = NO_MARKET if self.market_absent else NOT_STATED
            level_gap = (
                NO_MARKET if self.market_absent else f"Not calculable: no {label} was submitted"
            )
            return [
                _Gap(level_gap, "decimal_fraction"),
                _Gap(missing),
                _Gap(missing),
                _Gap(missing),
            ]
        talk = kind == "indicative_talk"
        cites = _trace([o])
        value = self.derived.fraction("talk" if talk else kind)
        if value is None:
            raise ValueError(f"Observed {kind} has no derived level")
        level = _Num(
            value,
            "decimal_fraction",
            2,
            cites,
            value_class="source",
            period=self.talk_period() if talk else None,
        )
        as_of = "None stated"
        if o.as_of_text:
            stated = parse_date(o.as_of_text)
            if stated is None:
                raise ValueError(f"as_of_text {o.as_of_text} is not a date: validate first")
            as_of = _short_date(stated)
        basis = (
            "Indicative talk; not a quotation or a trade" if talk else "Observed dealer quotation"
        )
        source = f"{self.ctx.names[o.source_id]}, {o.locator}"
        return [level, _Text(as_of, cites), _Text(basis, cites), _Text(source, cites)]

    def market_levels(self) -> Table:
        columns = (
            ("level", "Level (% of par)"),
            ("as_of", "As of"),
            ("basis", "Basis"),
            ("source", "Source"),
        )
        rows: list[_RowSpec] = [
            ("r01", "Dealer bid", self._level_row("bid", "bid")),
            ("r02", "Dealer offer", self._level_row("offer", "offer")),
            ("r03", "Indicative dealer talk", self._level_row("indicative_talk", "talk")),
        ]
        return self.table("T3E.1", "Market levels", columns, rows, "Level")

    # T3E.2 ------------------------------------------------------------------------------------
    def price_metrics(self) -> Table:
        s, bo = self.stored, self.cites_of("bid", "offer")
        days_refs = (*bo[:1], *self._maturity_refs())
        talk_less_period = None
        if s["talk_less_mid_pts"] is not None:
            q = self.quotation_period
            talk_less_period = f"{self.talk_period()} and {q[0].lower()}{q[1:]}"

        def frac(name: str) -> str | None:
            return _s(self.derived.fraction(name))

        rows: list[_RowSpec] = [
            (
                "r01",
                "Mid of bid and offer",
                [
                    self.calc(
                        frac("mid"),
                        "decimal_fraction",
                        3,
                        bo,
                        "cp3d.mid",
                        "(bid + offer) / 2",
                        self.why(NEED_MID),
                    ),
                    _Text("(bid + offer) / 2"),
                ],
            ),
            (
                "r02",
                "Bid-offer width",
                [
                    self.calc(
                        frac("width"),
                        "decimal_fraction",
                        2,
                        bo,
                        "cp3d.width",
                        "offer - bid",
                        self.why(NEED_MID),
                    ),
                    _Text("offer - bid"),
                ],
            ),
            (
                "r03",
                "Discount to par at mid",
                [
                    self.calc(
                        frac("discount_mid_pts"),
                        "decimal_fraction",
                        3,
                        bo,
                        "cp3d.discount_mid",
                        "par - mid",
                        self.why(NEED_MID),
                    ),
                    _Text("par - mid"),
                ],
            ),
            (
                "r04",
                "Indicative talk less mid (context only, not used in any calculation)",
                [
                    self.calc(
                        frac("talk_less_mid_pts"),
                        "decimal_fraction",
                        3,
                        (*bo, *self.cites_of("indicative_talk")),
                        "cp3d.talk_less_mid",
                        "talk - mid",
                        self.why("Not calculable: needs an indicative talk level and a mid"),
                        period=talk_less_period,
                    ),
                    _Text("talk - mid"),
                ],
            ),
            (
                "r05",
                "Days from quotation date to final maturity",
                [
                    self.calc(
                        s["days"],
                        "days",
                        None,
                        days_refs,
                        "cp3d.days",
                        "maturity date - quotation date",
                        self.why(NEED_YEARS),
                    ),
                    _Text("Calendar days"),
                ],
            ),
            (
                "r06",
                "Years to final maturity",
                [
                    self.calc(
                        s["years"],
                        "years",
                        None,
                        days_refs,
                        "cp3d.years",
                        "days / 365 (Act/365 Fixed, unrounded in later steps)",
                        self.why(NEED_YEARS),
                    ),
                    _Text(
                        "Act/365 Fixed; shown to two places, later steps use the unrounded value"
                    ),
                ],
            ),
        ]
        return self.table(
            "T3E.2",
            "Price metrics",
            (("value", "Value"), ("convention", "Convention")),
            rows,
            "Metric",
        )

    def _maturity_refs(self) -> tuple[QuoteRef, ...]:
        q = self.sub.terms.maturity.quote
        return (q,) if q else ()

    def _spread_refs(self, n: str) -> tuple[_Located, ...]:
        """Price, margin, amortisation and maturity quotes of a spread figure, in that order."""
        t = self.sub.terms
        terms = tuple(r for r in (t.margin.quote, t.amortisation.quote) if r)
        return (*self.point_refs(n), *terms, *self._maturity_refs())

    # T3E.3 ------------------------------------------------------------------------------------
    def spread_and_yield(self) -> Table:
        s, t = self.stored, self.sub.terms
        disc_row: list[_Content] = [
            self.calc(
                s[f"disc_{n}"],
                "basis_points",
                None,
                (*self.point_refs(n), *self._maturity_refs()),
                f"cp3d.disc_{n}",
                "(par - price) / years",
                self.point_need(n),
            )
            for n in POINTS
        ]
        margin: _Content = _Gap("Not stated: no contractual margin cited", "basis_points")
        if self.derived.margin_bp is not None and t.margin.quote is not None:
            margin = _Num(
                self.derived.margin_bp,
                "basis_points",
                None,
                _trace([t.margin.quote]),
                value_class="source",
                period=self.terms_period(t.margin.quote),
            )
        dm_row: list[_Content] = [
            self.calc(
                s[f"dm_{n}"],
                "basis_points",
                None,
                self._spread_refs(n),
                f"cp3d.dm_{n}",
                "contractual margin + annualised discount to par",
                self.dm_need(n),
            )
            for n in POINTS
        ]
        rr = t.reference_rate
        level: _Content = _Gap(NEED_RATE, "decimal_fraction")
        level_refs: tuple[QuoteRef, ...] = ()
        if rr.level is not None:
            level_refs = (rr.level.quote,)
            level = _Num(
                Decimal(rr.level.percent_text) / PAR,
                "decimal_fraction",
                2,
                _trace(level_refs),
                value_class="source",
                period=self.terms_period(rr.level.quote),
            )
        yield_row: list[_Content] = [
            self.calc(
                s[f"yield_{n}"],
                "decimal_fraction",
                2,
                (*self._spread_refs(n), *level_refs),
                f"cp3d.yield_{n}",
                "reference rate level + simple discount margin",
                NEED_RATE if rr.level is None else self.dm_need(n),
            )
            for n in POINTS
        ]
        rows: list[_RowSpec] = [
            (
                "r01",
                "Annualised discount to par",
                [*disc_row, _Text("Redemption at par at final maturity")],
            ),
            (
                "r02",
                "Contractual margin",
                [
                    margin,
                    margin,
                    margin,
                    _Text("Stated contractual spread over the reference rate"),
                ],
            ),
            (
                "r03",
                "Simple discount margin",
                [*dm_row, _Text("Simple margin; no amortisation; quotation date as settlement")],
            ),
            (
                "r04",
                "Reference rate level",
                [level, level, level, _Text("Dated reference rate level or curve required")],
            ),
            (
                "r05",
                "All-in yield (simple)",
                [*yield_row, _Text("Reference rate level + simple discount margin")],
            ),
        ]
        return self.table(
            "T3E.3", "Spread and yield", (*_POINT_COLUMNS, _CONVENTION), rows, "Measure"
        )

    # T3E.4 ------------------------------------------------------------------------------------
    def assumptions(self) -> Table:
        t, rec = self.sub.terms, self.sub.recovery
        recovery: _Content = _Gap(
            "Not calculable: recovery assumption not assessed", "decimal_fraction"
        )
        if rec is not None:
            recovery = _Num(
                Decimal(rec.percent_text) / PAR,
                "decimal_fraction",
                0,
                value_class="analyst_judgment",
                period=self.run_period,
            )
        mat = t.maturity
        maturity: _Content = _Gap("Not stated: no final maturity cited")
        mat_date = parse_date(mat.date_text) if mat.date_text else None
        if mat_date is not None and mat.quote is not None:
            maturity = _Text(_short_date(mat_date), _trace([mat.quote]))
        amort: _Content = _Gap("Not stated: amortisation not cited")
        if t.amortisation.value_text and t.amortisation.quote is not None:
            amort = _Text("Zero, as stated", _trace([t.amortisation.quote]))
        inst = self.sub.instrument
        rows: list[_RowSpec] = [
            ("r01", "Recovery rate (analyst assumption)", [recovery]),
            (
                "r02",
                "Reference rate",
                [_Text(t.reference_rate.name, _trace([t.reference_rate.quote]))],
            ),
            ("r03", "Final maturity", [maturity]),
            ("r04", "Mandatory amortisation", [amort]),
            ("r05", "Instrument", [_Text(inst.name, _trace([inst.quote]))]),
        ]
        return self.table("T3E.4", "Assumptions and terms", (("value", "Value"),), rows, "Input")

    # T3E.5 ------------------------------------------------------------------------------------
    def _default_cell(
        self, n: str, key: str, unit: str, decimals: int | None, calc: str, formula: str
    ) -> _Content:
        state = self.stored[f"pd_state_{n}"]
        value = self.stored[f"{key}_{n}"]
        if state == "known" and value is not None:
            return _Num(
                Decimal(value),
                unit,
                decimals,
                _trace(self._spread_refs(n)),
                calculation_id=f"{calc}_{n}",
                formula=formula,
            )
        if state == "not_applicable":
            return _Gap(NOT_MEANINGFUL, unit, "not_applicable")
        return _Gap(self.why(NEED_DEFAULT), unit)

    def market_implied_default(self) -> Table:
        lam = [
            self._default_cell(
                n,
                "lam",
                "basis_points",
                None,
                "cp3d.lambda",
                "simple discount margin / (1 - recovery)",
            )
            for n in POINTS
        ]
        pd = [
            self._default_cell(
                n, "pd", "decimal_fraction", 2, "cp3d.pd", "1 - exp(-(intensity) x years)"
            )
            for n in POINTS
        ]
        rows: list[_RowSpec] = [
            (
                "r01",
                "Annual default intensity",
                [*lam, _Text("Credit triangle: spread / (1 - recovery)")],
            ),
            (
                "r02",
                "Cumulative default probability to final maturity",
                [*pd, _Text("Constant intensity to final maturity; risk-neutral")],
            ),
        ]
        columns = (*_POINT_COLUMNS, _CONVENTION)
        return self.table("T3E.5", "Market-implied default", columns, rows, "Measure")

    # T3E.6 ------------------------------------------------------------------------------------
    def technicals(self) -> Table:
        rows: list[_RowSpec] = []
        for i, x in enumerate(self.sub.technicals, 1):
            cites = _trace(x.basis)
            rows.append(
                (
                    f"r{i:02d}",
                    x.aspect.replace("_", " ").capitalize(),
                    [
                        _Text(x.category, cites, "analyst_judgment"),
                        _Text(x.text, cites, "analyst_judgment"),
                    ],
                )
            )
        rows.append(
            (
                f"r{len(rows) + 1:02d}",
                "Summary",
                [
                    _Text("Analyst Interpretation", NO_CITES, "analyst_judgment"),
                    _Text(self.sub.summary.text, NO_CITES, "analyst_judgment"),
                ],
            )
        )
        columns = (("category", "Category"), ("assessment", "Assessment"))
        return self.table("T3E.6", "Technicals", columns, rows, "Aspect")

    # T3E.7-T3E.9 ------------------------------------------------------------------------------
    def _dm_ledger_reason(self) -> str:
        """The first missing cause of the mid margin, in formula order (ruling round 4 (h))."""
        if self.derived.years is None:
            return "Needs a quotation date and a final maturity date"
        if self.derived.mid is None:
            return "Needs both an observed bid and an observed offer"
        return "Needs a contractual margin and stated zero amortisation"

    def missing_inputs(self) -> Table:
        miss: list[tuple[str, str]] = []
        if self.market_absent:
            miss.append(
                (
                    "Dealer levels, price metrics, days and years, discount margin and default measures",
                    "Pack holds no third-party market quotation source",
                )
            )
        elif self.derived.days is None:
            miss.append(
                (
                    "Days and years to final maturity",
                    "Needs a quotation date and a final maturity date",
                )
            )
        rr_absence = self.sub.terms.reference_rate.absence
        if rr_absence is not None:
            miss.append(("Reference rate level and all-in yield", rr_absence.reason))
        if self.sub.recovery_absence is not None:
            miss.append(
                (
                    "Annual default intensity and cumulative default probability",
                    self.sub.recovery_absence.reason,
                )
            )
        if self.stored["dm_mid"] is None and not self.market_absent:
            miss.append(("Simple discount margin", self._dm_ledger_reason()))
        rows: list[_RowSpec] = [
            (f"r{i:02d}", affected, [_Text(affected), _Text(reason)])
            for i, (affected, reason) in enumerate(miss, 1)
        ]
        if not rows:
            rows = [("r01", "Missing inputs", [_Text("None"), _Text("No input is missing")])]
        columns = (("affected", "Not calculated"), ("reason", "Reason"))
        return self.table("T3E.7", "Missing inputs", columns, rows, "Input")

    def evidence(self) -> Table:
        rows: list[_RowSpec] = [
            (f"r{i:02d}", f"{self.ctx.names[sid]}, {loc}", [_Text(sid), _Text(loc)])
            for i, (sid, loc) in enumerate(cited_pages(self.sub), 1)
        ]
        columns = (("source", "Source"), ("locator", "Locator"))
        return self.table("T3E.8", "Evidence", columns, rows, "Page")

    def limitations(self, own: Sequence[str]) -> Table:
        rows: list[_RowSpec] = [
            (f"r{i:02d}", f"Limitation {i}", [_Text(text)]) for i, text in enumerate(own, 1)
        ]
        return self.table("T3E.9", "Limitations", (("text", "Limitation"),), rows, "Limitation")


def cited_refs(submission: MarketImpliedSubmission) -> tuple[QuoteRef | Observation, ...]:
    """Every quote the submission cites, in the order the lease lists them."""
    t = submission.terms
    refs: list[QuoteRef | Observation] = [*submission.observations, submission.instrument.quote]
    refs += [r for r in (t.maturity.quote, t.margin.quote, t.amortisation.quote) if r]
    refs.append(t.reference_rate.quote)
    if t.reference_rate.level is not None:
        refs.append(t.reference_rate.level.quote)
    for x in submission.technicals:
        refs += x.basis
    return tuple(refs)


def cited_pages(submission: MarketImpliedSubmission) -> tuple[Cite, ...]:
    """Every (source_id, locator) the submission cites, in order of first appearance."""
    return _trace(cited_refs(submission))


def absence_paths(submission: MarketImpliedSubmission) -> tuple[str, ...]:
    """Absence objects that claim a source lacks something (`recovery_absence` is not one)."""
    t = submission.terms
    out = ["market_absence"] if submission.market_absence is not None else []
    terms = (
        ("maturity", t.maturity.absence),
        ("margin", t.margin.absence),
        ("amortisation", t.amortisation.absence),
        ("reference_rate", t.reference_rate.absence),
    )
    out += [f"terms.{key}.absence" for key, absence in terms if absence is not None]
    return tuple(out)


def _single_dealer(sub: MarketImpliedSubmission) -> list[str]:
    """Ruling 6b C1: the single-dealer limitation, keyed on the observed sides only."""
    sides = [k for k in ("bid", "offer") if any(o.kind == k for o in sub.observations)]
    if len(sides) == 2:
        return [
            "Single dealer quotation; the sheet reports no trade in the period to the quotation date"
        ]
    if sides:
        return [
            (
                f"Single dealer quotation with only the {sides[0]} observed; trading activity in the "
                "period to the quotation date is not read"
            )
        ]
    return []  # talk only: LVL-01 and the talk limitation already say it


def own_limitations(submission: MarketImpliedSubmission) -> tuple[str, ...]:
    """The module's own limitations, in the lease's order, de-duplicated."""
    sub = submission
    out: list[str] = []
    if sub.market_absence is not None:
        out.append(
            "No third-party market quotation source is in the pack, so no market level is shown"
        )
    else:
        out += _single_dealer(sub)
    out += [x.limitation for x in sub.technicals if x.limitation]
    if any(o.kind == "indicative_talk" for o in sub.observations):
        out.append("Indicative dealer talk is shown but is not used in any calculation")
    if sub.terms.reference_rate.absence is not None:
        out.append(
            "The reference rate level is not in any source, so the all-in yield is not calculated"
        )
    if sub.recovery is not None:
        out.append(
            "The recovery rate is an analyst assumption following the first-lien loan CDS convention, "
            "not a source figure; the convention itself is not verified against a source"
        )
        out.append(
            "A higher recovery raises the implied default intensity and default probability for the same margin"
        )
    else:
        out.append("The recovery rate was not assessed, so the default measures are not calculated")
    out.append(
        "The simple discount margin assumes redemption at par at final maturity, no amortisation and the "
        "quotation date as settlement date; it is not a Z-spread; not divided by price; "
        "not the three-year-life convention"
    )
    out.append(
        "The whole spread is attributed to default risk and the intensity is constant, so the default "
        "measures are risk-neutral and overstate the default component if a liquidity premium is present"
    )
    out.append(
        "The contractual margin and the amortisation are read from the financial source page, "
        "not from a CP-1 fact"
    )
    out.append(
        "The alignment of the market-implied view with the fundamentals is not shown: no fundamental "
        "comparator is bound, so only the market-implied default half of the market-against-fundamentals "
        "block is populated"
    )
    if absence_paths(sub):
        out.append(
            "An absence is backed only by a recorded search over some source, not by a search for the "
            "specific item"
        )
    return tuple(dict.fromkeys(out))


def inherited_limitations(*, own: Sequence[str], upstream: Sequence[str]) -> tuple[str, ...]:
    """CP-0 head limitations then CP-0 inherited (in `upstream`), de-duplicated, own removed."""
    return tuple(x for x in dict.fromkeys(upstream) if x not in own)


# --- claims ------------------------------------------------------------------------------------


_BID, _OFFER, _TALK = "T3E.1.r01.level", "T3E.1.r02.level", "T3E.1.r03.level"
_MID, _YEARS = "T3E.2.r01.value", "T3E.2.r06.value"
_MARGIN, _DM, _YLD = "T3E.3.r02.mid", "T3E.3.r03.mid", "T3E.3.r05.mid"
_LAM, _PD = "T3E.5.r01.mid", "T3E.5.r02.mid"
_Claim = Callable[[str, str, Sequence[str]], ClaimText]


def _lvl_claim(c: _Composer, claim: _Claim) -> ClaimText:
    """CP-3D-LVL-01; partial quotations per ruling X1 (i)-(iii), the date per ruling D2."""
    cid = "CP-3D-LVL-01"
    if c.market_absent:
        return claim(
            cid,
            f"No market level is available: [{_BID}] and [{_OFFER}] are not stated because the pack "
            "holds no third-party market quotation source.",
            [_BID, _OFFER],
        )
    bid, offer = c.obs.get("bid"), c.obs.get("offer")
    if bid is not None and offer is not None:
        return claim(
            cid,
            f"On {bid.as_of_text} the dealer quotation was {{{_BID}|%}} bid and {{{_OFFER}|%}} "
            f"offer, a mid of {{{_MID}|%}} of par.",
            [_BID, _OFFER, _MID],
        )
    if bid is not None:
        return claim(
            cid,
            f"On {bid.as_of_text} the dealer quotation was {{{_BID}|%}} bid; no offer was submitted, "
            f"so the mid is not calculated: [{_MID}].",
            [_BID, _MID],
        )
    if offer is not None:
        return claim(
            cid,
            f"On {offer.as_of_text} the dealer quotation was {{{_OFFER}|%}} offer; no bid was "
            f"submitted, so the mid is not calculated: [{_MID}].",
            [_OFFER, _MID],
        )
    return claim(
        cid,
        f"No dealer quotation was submitted: [{_BID}] and [{_OFFER}] are not stated; indicative "
        f"talk of {{{_TALK}|%}} of par is shown as context only.",
        [_BID, _OFFER, _TALK],
    )


def _dm_claim(c: _Composer, claim: _Claim) -> ClaimText:
    """CP-3D-DM-01: known form whenever the mid margin is known, negative included (X1 (iv))."""
    maturity_text = c.sub.terms.maturity.date_text
    if c.stored["dm_mid"] is not None and maturity_text:
        return claim(
            "CP-3D-DM-01",
            f"At the mid the simple discount margin over the reference rate is {{{_DM}|bp}}, from a "
            f"contractual margin of {{{_MARGIN}|bp}} and {{{_YEARS}|years}} to final maturity on "
            f"{maturity_text}.",
            [_DM, _MARGIN, _YEARS],
        )
    return claim(
        "CP-3D-DM-01",
        f"The simple discount margin is not calculated: [{_DM}] is not available.",
        [_DM],
    )


def _yld_claim(c: _Composer, claim: _Claim) -> ClaimText:
    """CP-3D-YLD-01; a quoted level with no final maturity is ruling X1 (v), with a stated
    maturity but no mid margin ruling round 4 (g)."""
    cid = "CP-3D-YLD-01"
    if c.stored["yield_mid"] is not None:
        return claim(
            cid,
            f"At the mid the all-in yield is {{{_YLD}|%}}, the reference rate level plus the simple "
            f"discount margin of {{{_DM}|bp}}.",
            [_YLD, _DM],
        )
    if c.sub.terms.reference_rate.level is None:
        return claim(
            cid,
            f"The all-in yield is not calculated: [{_YLD}] needs a reference rate level that no "
            "source in the pack states.",
            [_YLD],
        )
    if c.sub.terms.maturity.date_text is None:
        return claim(
            cid,
            f"The all-in yield is not calculated: [{_YLD}] needs a final maturity date, which no "
            "source in the pack states.",
            [_YLD],
        )
    if c.stored["dm_mid"] is None:  # a stated maturity, the mid margin missing (round 4 (g))
        return claim(
            cid,
            f"The all-in yield is not calculated: [{_YLD}] needs the simple discount margin at the "
            f"mid, which is not calculated: [{_DM}].",
            [_YLD, _DM],
        )
    # Neither ruling applies. Unreachable today (a quoted level and a known mid margin give a
    # known yield); the DM-01 gap form's neutral wording rather than a raise.
    return claim(cid, f"The all-in yield is not calculated: [{_YLD}] is not available.", [_YLD])


def _pd_claim(c: _Composer, claim: _Claim) -> ClaimText:
    """CP-3D-PD-01; not meaningful at the mid per ruling X1 (iv)."""
    cid, state = "CP-3D-PD-01", c.stored["pd_state_mid"]
    if state == "known":
        return claim(
            cid,
            "At the analyst recovery assumption the mid spread implies an annual default intensity "
            f"of {{{_LAM}|bp}} and a cumulative default probability to final maturity of "
            f"{{{_PD}|%}}; both are risk-neutral measures.",
            [_LAM, _PD],
        )
    if state == "not_applicable":
        return claim(
            cid,
            f"The market-implied default probability is not meaningful: [{_LAM}] and [{_PD}] need a "
            f"positive simple discount margin, and at the mid the margin is {{{_DM}|bp}}.",
            [_LAM, _PD, _DM],
        )
    needs = (
        "simple discount margin"
        if c.sub.recovery is not None
        else "simple discount margin and a recovery assumption"
    )
    return claim(
        cid,
        f"The market-implied default probability is not calculated: [{_LAM}] and [{_PD}] need a "
        f"{needs}.",
        [_LAM, _PD],
    )


def _claims(c: _Composer, tables: Sequence[Table]) -> tuple[ClaimText, ...]:
    cells = {f.fact_id: f for t in tables for r in t.rows for f in r.facts}

    def claim(claim_id: str, text: str, refs: Sequence[str]) -> ClaimText:
        return ClaimText(claim_id, text, tuple(refs), Cites.merged(cells[r].cites for r in refs))

    composed = tuple(f(c, claim) for f in (_lvl_claim, _dm_claim, _yld_claim, _pd_claim))
    return (*composed, ClaimText("CP-3D-VIEW-01", c.sub.summary.text, (), Cites()))


def market_implied_result(
    *, submission: MarketImpliedSubmission, context: MarketContext
) -> MarketImpliedResult:
    """Tables T3E.1-T3E.9, claims and own limitations of a validated submission (pure)."""
    derived = compose(inputs=inputs_from_submission(submission))
    c = _Composer(submission, context, derived)
    own = own_limitations(submission)
    builders: tuple[Callable[[], Table], ...] = (
        c.market_levels,
        c.price_metrics,
        c.spread_and_yield,
        c.assumptions,
        c.market_implied_default,
        c.technicals,
        c.missing_inputs,
        c.evidence,
    )
    tables = (*(b() for b in builders), c.limitations(own))
    return MarketImpliedResult(derived, tables, _claims(c, tables), own)


# --- Stage 2 connections -----------------------------------------------------------------------
#
# The parts below bind the pure core to the owner workflow (`docs/G1X-OWNER-CORE-PROTOCOL.md`
# section 2, `docs/CP3D-OWNER-LEASE.md` Public API). CP-3D is owner-only: CP-0 is its one
# upstream (CP-2H is unbound), its one step `market_implied` has pack sources and journaled rules,
# and it reads no view and has no precheck.

STEP_ID = "market_implied"
STEP_IDS: tuple[str, ...] = (STEP_ID,)
SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: MarketImpliedSubmission}
QUALIFICATION = Qualification(implementation="implemented")
CP0_INPUT = "CP-0"
# The settled head's extra input: `<step id with hyphens>-submission` (protocol section 2).
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
_INCONSISTENT = "identity_mismatch"


@dataclass(frozen=True)
class Upstream:
    """What the validator and composer read of the bound CP-0 head: the Stage 1 `MarketContext`
    (pack pages and names, the CP-0 T3 `third_party` sources, page publication dates, the run
    as-of date) and the CP-0 limitations CP-3D inherits (head limitations, then its inherited)."""

    context: MarketContext
    inherited: tuple[str, ...]


def _third_party(cp0: Module) -> frozenset[str]:
    """The sources whose CP-0 T3 authority fact reads `third_party`."""
    out: set[str] = set()
    for fact in cp0.facts:
        parts = fact.fact_id.split(".")
        if (
            len(parts) == 3
            and (parts[0], parts[2]) == ("T3", "authority")
            and fact.text == "third_party"
        ):
            out.add(parts[1])
    return frozenset(out)


def upstream_of(*, pack: PreparedPack, cp0: Module) -> Upstream:
    """The pure adapter: the pack and the bound CP-0 module to the Stage 1 context object."""
    pages = {s.source_id: {span.locator: span.text for span in s.spans} for s in pack.sources}
    context = MarketContext(
        pages=pages,
        names={s.source_id: s.name for s in pack.sources},
        third_party=_third_party(cp0),
        published=publication_dates(pages),
        run_as_of=pack.run.as_of,
    )
    return Upstream(context, tuple(dict.fromkeys((*cp0.limitations, *cp0.inherited_limitations))))


def cp3d_upstream(
    *, store: Execution, attempt: Attempt, pack: PreparedPack | None = None
) -> Upstream:
    """Read the attempt's bound CP-0 head from the store (exactly one binding) and adapt it.
    `submit`, `probe` and the entry validator all come through here."""
    bound = [item for item in attempt.inputs if item.input_id == CP0_INPUT]
    if len(bound) != 1:
        raise WorkflowError(_INCONSISTENT)
    return upstream_of(
        pack=store.pack() if pack is None else pack, cp0=store.result(bound[0].sha256)
    )


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def validate_market_implied(
    *, submission: MarketImpliedSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """The validator issues of a submission against the bound upstream (empty: valid). The
    summary becomes `Claim.text` (`CP-3D-VIEW-01`), so it is also checked as `RunText` (the
    type's message, never the input) whatever the content rules found, as CP-2E does, and no
    composition can raise after the binding write."""
    issues = submission_issues(submission=submission, context=upstream.context)
    try:
        _RUN_TEXT.validate_python(submission.summary.text)
    except ValidationError as error:
        issues = (
            *issues,
            *(
                clipped(("summary.text: ", e["msg"]))
                for e in error.errors(include_input=False, include_url=False, include_context=False)
            ),
        )
    return tuple(dict.fromkeys(issues))


# --- the report and the module -----------------------------------------------------------------


class MarketImpliedReport(Contract):
    """The validated step output the journal retains: Python's facts, tables and claims."""

    schema_version: Literal["market-implied/1"] = "market-implied/1"
    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]
    inherited_limitations: tuple[str, ...]


def cite_of(pack: PreparedPack, cites: Cites, cite: Cite) -> Citation:
    """A page-level cite as a `Citation`: the pack source hash and the first submitted quote the
    cell rests on for that page (a derived cell rests on several; the first input quote on the
    page is cited, none is invented). A page the cell has no quote for is refused."""
    quotes = cites.quotes.get(cite)
    source = next((s for s in pack.sources if s.source_id == cite[0]), None)
    if not quotes or source is None or source.sha256 is None:
        raise ValueError(f"no quote or source hash for the cited page {cite[0]} {cite[1]}")
    return Citation(
        source_id=cite[0], source_sha256=source.sha256, locator=cite[1], quote=quotes[0]
    )


def _fact_of(
    cell: Cell, label: str, table_id: str, row_id: str, field: str, cites: tuple[Citation, ...]
) -> Fact:
    return Fact(
        fact_id=cell.fact_id,
        label=label,
        table_id=table_id,
        row_id=row_id,
        field=field,
        amount=cell.amount,
        text=cell.text,
        status=cell.status,
        unit=cell.unit,
        decimals=cell.decimals,
        period=cell.period,
        citations=cites,
        calculation_id=cell.calculation_id,
        value_class=cell.value_class,
        formula=cell.formula,
        limitation=cell.limitation,
    )


def _layout(table: Table, pack: PreparedPack) -> tuple[ReportTable, list[Fact]]:
    facts: list[Fact] = []
    rows: list[TableRow] = []
    for row in table.rows:
        if len(row.facts) != len(table.columns):
            raise ValueError(f"{table.table_id}.{row.row_id}: row and columns differ")
        for (key, column), cell in zip(table.columns, row.facts, strict=True):
            if cell.fact_id != f"{table.table_id}.{row.row_id}.{key}" or cell.column != column:
                raise ValueError(f"{cell.fact_id}: not the coordinate of its cell")
            cites = tuple(cite_of(pack, cell.cites, c) for c in cell.cites)
            facts.append(
                _fact_of(cell, f"{row.label} · {column}", table.table_id, row.row_id, key, cites)
            )
        rows.append(
            TableRow(
                row_id=row.row_id,
                label=row.label,
                fact_ids=tuple(c.fact_id for c in row.facts),
            )
        )
    layout = ReportTable(
        table_id=table.table_id,
        title=table.title,
        columns=tuple(TableColumn(field=f, label=label) for f, label in table.columns),
        rows=tuple(rows),
        row_header=table.row_header,
    )
    return layout, facts


def market_implied(
    *, pack: PreparedPack, submission: MarketImpliedSubmission, upstream: Upstream
) -> MarketImpliedReport:
    """The report of a submission the validator accepts (`ValueError` listing the issues if not)."""
    if issues := validate_market_implied(submission=submission, upstream=upstream):
        raise ValueError("; ".join(issues))
    result = market_implied_result(submission=submission, context=upstream.context)
    tables: list[ReportTable] = []
    facts: list[Fact] = []
    for table in result.tables:
        layout, table_facts = _layout(table, pack)
        tables.append(layout)
        facts += table_facts
    claims = tuple(
        Claim(
            claim_id=c.claim_id,
            text=c.text,
            citations=tuple(cite_of(pack, c.cites, x) for x in c.cites),
        )
        for c in result.claims
    )
    return MarketImpliedReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=tuple(tables),
        facts=tuple(facts),
        claims=claims,
        limitations=result.own_limitations,
        inherited_limitations=inherited_limitations(
            own=result.own_limitations, upstream=upstream.inherited
        ),
    )


def cp3d_module(*, report: MarketImpliedReport, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-3D candidate: the report bound to `inputs` plus the submission input."""
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
        inherited_limitations=report.inherited_limitations,
        attempt=attempt,
    )


# --- the journal: validator, rules, submit and probe -------------------------------------------


def _parsed(payload: str) -> tuple[MarketImpliedSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`). The schema validates the bounded document's exact re-serialisation, never the
    raw text; text `json_object` refuses keeps Pydantic's own shape issue and is refused even if
    Pydantic would parse it."""
    document = json_object(payload)
    try:
        if document is None:
            MarketImpliedSubmission.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return MarketImpliedSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands `Execution.submit_step` and the verifier replays: the
    attempt's last step, against the bound CP-0 head."""
    submission, shape = _parsed(store.payload(attempt.steps[-1].payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    upstream = cp3d_upstream(store=store, attempt=attempt, pack=pack)
    if issues := validate_market_implied(submission=submission, upstream=upstream):
        return StepValidation(issues=issues)
    report = market_implied(pack=pack, submission=submission, upstream=upstream)
    return StepValidation(output=report.model_dump_json())


# The validator CP-3D's own `submit` hands `Execution.submit_step` (R4-2 invalid-step replay).
ENTRY_VALIDATOR = _validate_step

_ABSENCE_PATHS: tuple[tuple[str, ...], ...] = (
    ("market_absence",),
    ("terms", "maturity", "absence"),
    ("terms", "margin", "absence"),
    ("terms", "amortisation", "absence"),
    ("terms", "reference_rate", "absence"),
)


def _present(document: Mapping[str, object], path: tuple[str, ...]) -> bool:
    node: object = document
    for key in path:
        if not isinstance(node, Mapping):
            return False
        node = node.get(key)
    return node is not None


def _rules(text: str, seen: Seen) -> tuple[str, ...]:
    """The journaled tool-use rules (protocol section 2): `UNBACKED_ABSENCE` once when an absence
    object (`absence_paths`; `recovery_absence` is not one) is present and no search was recorded,
    then the unread cited pages, sorted. The payload is read only through `json_object`; text
    that is no object has no absence to back, and the validator refuses its shape."""
    document = json_object(text)
    backed = bool(seen.searched)
    unbacked = (
        document is not None and not backed and any(_present(document, p) for p in _ABSENCE_PATHS)
    )
    return (*((UNBACKED_ABSENCE,) if unbacked else ()), *unread_citation_issues(text, seen))


RULES = _rules


def _candidate(output: str, attempt: Attempt) -> Module:
    report = MarketImpliedReport.model_validate_json(output)
    return cp3d_module(report=report, inputs=attempt.inputs, attempt=attempt.number)


def _settle(store: Execution, ticket_id: str, attempt: Attempt) -> Attempt:
    """Settle CP-3D with the Python candidate after its one valid step (as `submit_cp1a_step`)."""
    outcome = _validate_step(store, store.pack(), attempt)
    if outcome.issues or outcome.output is None or not outcome.retained_as(attempt.steps[0]):
        raise ValueError("Retained CP-3D output differs from trusted validation")
    candidate = _candidate(outcome.output, attempt)
    return store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP-3D candidate differs",),
        qualification=QUALIFICATION,
    )


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `market_implied` response (null resolution through `SCHEMAS`, the rule
    issues appended as the product `_with_rules` appends them) and settle CP-3D after it."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-3D has one step, {STEP_ID}")
    normal, resolved = normalise_payload(MarketImpliedSubmission, payload)
    validate: Callable[[PreparedPack, Attempt], StepValidation] = partial(_validate_step, store)
    if rules is not None and rules(normal):
        validate = _with_rules(validate, rules, normal)
    attempt = store.submit_step(ticket_id, MODULE_ID, STEP_IDS, STEP_ID, normal, validate)
    if (
        attempt.status == "pending"
        and len(attempt.steps) == len(STEP_IDS)
        and all(s.status == "valid" for s in attempt.steps)
    ):
        attempt = _settle(store, ticket_id, attempt)
    return Submitted(attempt, normal, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun the validator and settlement over the settled snapshot (`identity_mismatch` unless
    the attempt and head rebuild exactly)."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


# --- the consumer reader (D3 stays OPEN) -------------------------------------------------------

READ_DM_MID, READ_LAMBDA_MID = "T3E.3.r03.mid", "T3E.5.r01.mid"
READ_PD_MID, READ_RECOVERY = "T3E.5.r02.mid", "T3E.4.r01.value"


@dataclass(frozen=True)
class Reading:
    """One fact as a consumer sees it: its id, its status and its exact amount (None when the
    fact is not known; a missing figure is never 0)."""

    fact_id: str
    status: str
    amount: Decimal | None


@dataclass(frozen=True)
class Cp3dHead:
    """What `expected.json#consumption.reader_pinned_for_cp3c` pins CP-3C to read."""

    head_sha256: str
    status: str
    discount_margin_mid: Reading
    intensity_mid: Reading
    probability_mid: Reading
    recovery: Reading
    own_limitations: tuple[str, ...]


def _reading(facts: Mapping[str, Fact], fact_id: str) -> Reading:
    fact = facts.get(fact_id)
    if fact is None:
        raise WorkflowError(_INCONSISTENT)
    return Reading(fact_id, fact.status, fact.amount)


def cp3d_reader(store: Execution, head: Head) -> Cp3dHead:
    """The consumer reader: the head's hash and status, the mid discount margin, default
    intensity and cumulative probability, the recovery assumption (or its absence) and the own
    limitations. No consumer core reads it yet, so no consumption is claimed (lease D3)."""
    if head.module_id != MODULE_ID:
        raise WorkflowError(_INCONSISTENT)
    module = store.head_module(head)
    facts = {f.fact_id: f for f in module.facts}
    return Cp3dHead(
        head_sha256=head.result_sha256,
        status=head.status,
        discount_margin_mid=_reading(facts, READ_DM_MID),
        intensity_mid=_reading(facts, READ_LAMBDA_MID),
        probability_mid=_reading(facts, READ_PD_MID),
        recovery=_reading(facts, READ_RECOVERY),
        own_limitations=module.limitations,
    )
