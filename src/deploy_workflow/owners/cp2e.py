"""CP-2E (macro, FX and hedging sensitivity): the module's pure calculation (Stage 1).

Lease: docs/CP2E-OWNER-LEASE.md. Python computes, from quoted FY 2025 facts of the financial
source, a static upward parallel rate shock and a foreign-currency strengthening move; the
analyst supplies only the shock sizes, an optional hedge ratio, the assessments and a summary.
Missing is never 0: every derived value is known, missing (with its reason) or not applicable.

Nothing here does I/O or touches a store, host, session or renderer. Connection, tool-use and
orchestration seams (G1-X protocol section 2) are added to this file in later stages.
"""

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any, Literal

from deploy_vii.contracts import Fact
from deploy_vii.quotes import hyphen_wrapped, normalise, quoted, reading
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-2E"
SOURCE_ID = "financial"  # the only source the CP-2E step may cite (fixed host scope)

Cite = tuple[str, str]  # (source_id, locator)
State = Literal["known", "missing", "not_applicable"]
RateType = Literal["FLOATING", "FIXED"]

# --- Decimal conventions (lease "Decimal composer") ------------------------------------------
_PRECISION = 38  # 38 significant digits, ROUND_HALF_EVEN; stored exactly, trailing zeros dropped


def _exact(x: Decimal) -> Decimal:
    """The stored form of a Decimal: same value, trailing zeros dropped, no exponent."""
    with localcontext() as ctx:
        ctx.prec = 80  # normalize() rounds to the context: keep every digit the value has
        text = format(x.normalize(), "f")
    return Decimal(0) if text in ("-0", "") else Decimal(text)


@dataclass(frozen=True)
class Value:
    """A derived value: known (with an exact amount), missing or not applicable (with a reason)."""

    state: State
    amount: Decimal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if (self.state == "known") != (self.amount is not None):
            raise ValueError("a known value carries an amount and only a known value does")
        if (self.state == "known") == (self.reason is not None):
            raise ValueError("an unknown value carries a reason and only an unknown value does")


def _known(x: Decimal) -> Value:
    return Value("known", amount=_exact(x))


def _missing(reason: str) -> Value:
    return Value("missing", reason=reason)


def _not_applicable(reason: str) -> Value:
    return Value("not_applicable", reason=reason)


def _maybe(x: Decimal | None, reason: str) -> Value:
    return _missing(reason) if x is None else _known(x)


def _ratio(num: Value, den: Value, divisor: str) -> Value:
    """num / den: a missing operand propagates (numerator first); a divisor <= 0 is n.m. with the
    reason '<divisor> is zero' or '<divisor> is negative' (ruling A3)."""
    for v in (num, den):
        if v.state == "missing":
            return v
    if num.amount is None or den.amount is None:
        return _not_applicable("an input is not applicable")
    if den.amount <= 0:
        return _not_applicable(f"{divisor} is {'zero' if den.amount == 0 else 'negative'}")
    return _known(num.amount / den.amount)


def _combine(a: Value, b: Value, fn: Callable[[Decimal, Decimal], Decimal]) -> Value:
    """fn(a, b) when both are known; otherwise the first value that is not known propagates."""
    if a.amount is None:
        return a
    if b.amount is None:
        return b
    return _known(fn(a.amount, b.amount))


# --- the pure sensitivity arithmetic -----------------------------------------------------------
@dataclass(frozen=True)
class Operands:
    """Sourced operands in millions (or basis points for the floor); None is missing, never 0."""

    total_debt: Decimal | None
    ebitda: Decimal | None
    interest: Decimal | None
    fcf: Decimal | None
    facility_balance: Decimal | None = None
    rate_type: RateType | None = None
    floor_bp: Decimal | None = None
    debt_foreign: bool | None = None  # quoted debt currency differs from the reporting currency
    foreign_ebitda_share: Decimal | None = None  # fraction of EBITDA earned in other currencies


@dataclass(frozen=True)
class RateShock:
    shock_bp: Value
    gross: Value
    net: Value
    interest_after: Value
    cov_after: Value
    cov_change: Value
    fcf_after: Value
    share_of_ebitda: Value


@dataclass(frozen=True)
class FxShock:
    shock: Value
    debt_change: Value
    debt_after: Value
    ebitda_change: Value
    ebitda_after: Value
    lev_after: Value


@dataclass(frozen=True)
class Sensitivity:
    floating: Value
    floating_share: Value
    cov_base: Value
    lev_base: Value
    hedge: Value
    floating_after_hedge: Value
    rate: tuple[RateShock, ...]
    foreign_debt: Value
    foreign_debt_share: Value
    fx: tuple[FxShock, ...]


_NO_HEDGE = "no hedge ratio is stated"
_NO_SHARE = "the share of EBITDA earned in other currencies is not stated"
_NO_TERMS = "the facility rate terms are not stated"
_NO_FLOOR = "the floor of the facility is not stated"
_FLOOR_MAY_BIND = "the reference rate level is not stated, so a floor above zero may bind"
_NO_DEBT_CURRENCY = "the currency of the debt is not stated"
_NO_BALANCE = "the facility balance is not stated"  # ruling E4a


def _gross(floating: Value, floor_bp: Decimal | None, shock_bp: Decimal) -> Value:
    """Added annual interest before hedges for an upward shock of shock_bp basis points."""
    if floating.amount is None:
        return floating
    if floating.amount == 0:
        return _known(Decimal(0))  # nothing floats: a known zero, whatever the floor
    if floor_bp is None:
        return _missing(_NO_FLOOR)
    if floor_bp != 0:
        return _missing(_FLOOR_MAY_BIND)
    return _known(floating.amount * shock_bp / 10000)


def _rate_shock(
    shock_bp: Decimal,
    *,
    floating: Value,
    floor_bp: Decimal | None,
    hedge: Value,
    interest: Value,
    ebitda: Value,
    fcf: Value,
    cov_base: Value,
) -> RateShock:
    gross = _gross(floating, floor_bp, shock_bp)
    interest_after = _combine(gross, interest, lambda g, i: i + g)
    cov_after = _ratio(ebitda, interest_after, "interest after the shock")
    return RateShock(
        shock_bp=_known(shock_bp),
        gross=gross,
        net=_combine(gross, hedge, lambda g, h: g * (1 - h)),
        interest_after=interest_after,
        cov_after=cov_after,
        cov_change=_combine(cov_after, cov_base, lambda a, b: a - b),
        fcf_after=_combine(gross, fcf, lambda g, f: f - g),
        share_of_ebitda=_ratio(gross, ebitda, "EBITDA"),
    )


def _fx_shock(
    move: Decimal, *, foreign_debt: Value, debt: Value, ebitda: Value, share: Decimal | None
) -> FxShock:
    m = _known(move)
    debt_change = _combine(foreign_debt, m, lambda f, x: f * x)
    debt_after = _combine(debt_change, debt, lambda c, d: d + c)
    if share is None:
        ebitda_change = _missing(_NO_SHARE)
    else:
        ebitda_change = _combine(ebitda, m, lambda e, x: e * share * x)
    ebitda_after = _combine(ebitda_change, ebitda, lambda c, e: e + c)
    return FxShock(
        shock=m,
        debt_change=debt_change,
        debt_after=debt_after,
        ebitda_change=ebitda_change,
        ebitda_after=ebitda_after,
        lev_after=_ratio(debt_after, ebitda_after, "EBITDA after the shock"),
    )


def derive_sensitivity(
    *,
    operands: Operands,
    rate_shocks_bp: Sequence[Decimal],
    fx_shocks: Sequence[Decimal],
    hedge_ratio: Decimal | None,
) -> Sensitivity:
    """Exact 38-digit derivation of every sensitivity value (lease Decimal composer table).

    ``fx_shocks`` and ``hedge_ratio`` are fractions (10 percent is 0.1); shocks are upward only.
    """
    op = operands
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        debt = _maybe(op.total_debt, "total debt not stated")
        ebitda = _maybe(op.ebitda, "EBITDA not stated")
        interest = _maybe(op.interest, "cash interest not stated")
        fcf = _maybe(op.fcf, "free cash flow not stated")
        balance = op.facility_balance
        if balance is None or op.rate_type is None:
            floating = _missing(_NO_TERMS)
        else:
            floating = _known(balance if op.rate_type == "FLOATING" else Decimal(0))
        hedge = _maybe(hedge_ratio, _NO_HEDGE)
        cov_base = _ratio(ebitda, interest, "cash interest")
        if op.debt_foreign is None:
            foreign_debt = _missing(_NO_DEBT_CURRENCY)
        elif balance is None:
            foreign_debt = _missing(_NO_BALANCE)
        else:
            foreign_debt = _known(balance if op.debt_foreign else Decimal(0))
        rate = tuple(
            _rate_shock(
                k,
                floating=floating,
                floor_bp=op.floor_bp,
                hedge=hedge,
                interest=interest,
                ebitda=ebitda,
                fcf=fcf,
                cov_base=cov_base,
            )
            for k in rate_shocks_bp
        )
        fx = tuple(
            _fx_shock(
                m,
                foreign_debt=foreign_debt,
                debt=debt,
                ebitda=ebitda,
                share=op.foreign_ebitda_share,
            )
            for m in fx_shocks
        )
        return Sensitivity(
            floating=floating,
            floating_share=_ratio(floating, debt, "total debt"),
            cov_base=cov_base,
            lev_base=_ratio(debt, ebitda, "EBITDA"),
            hedge=hedge,
            floating_after_hedge=_combine(floating, hedge, lambda f, h: f * (1 - h)),
            rate=rate,
            foreign_debt=foreign_debt,
            foreign_debt_share=_ratio(foreign_debt, debt, "total debt"),
            fx=fx,
        )


# --- the typed input object --------------------------------------------------------------------
@dataclass(frozen=True)
class Sourced:
    """A quoted numeric operand and the page it was quoted from."""

    value: Decimal
    cite: Cite


@dataclass(frozen=True)
class SourcedCode:
    code: str
    cite: Cite


@dataclass(frozen=True)
class RateBasis:
    rate_type: RateType
    reference_rate: str
    cite: Cite


@dataclass(frozen=True)
class FacilityTerms:
    balance: Sourced
    basis: RateBasis
    spread_bp: Sourced
    floor_bp: Sourced


@dataclass(frozen=True)
class Absence:
    reason: str
    follow_up: str


@dataclass(frozen=True)
class Assessment:
    section: Literal["interest_rate", "fx", "hedging"]
    category: Literal["Documentary Fact", "Analyst Interpretation", "Insufficient Information"]
    text: str
    basis: tuple[Cite, ...]
    limitation: str | None


@dataclass(frozen=True)
class MacroFxInputs:
    """Every operand the CP-2E method reads, plus the analyst judgment fields.

    Exactly one of each sourced/absence pair is set. ``hedge_ratio``, ``foreign_ebitda_share``
    and ``fx_shocks`` are fractions; ``rate_shocks_bp`` are whole basis points.
    """

    reporting_currency: SourcedCode
    total_debt: Sourced
    ebitda: Sourced
    interest: Sourced
    fcf: Sourced
    fx_cash_effect: Sourced
    facility: FacilityTerms | None
    rate_absence: Absence | None
    debt_currency: SourcedCode | None
    debt_currency_absence: Absence | None
    foreign_ebitda_share: Sourced | None
    operating_fx_absence: Absence | None
    hedge_ratio: Decimal | None
    hedge_absence: Absence | None
    rate_shocks_bp: tuple[Decimal, ...]
    fx_shocks: tuple[Decimal, ...]
    shock_rationale: str
    assessments: tuple[Assessment, ...]
    summary: str
    source_names: Mapping[str, str]

    def __post_init__(self) -> None:
        pairs = (
            ("facility", self.facility, self.rate_absence),
            ("debt_currency", self.debt_currency, self.debt_currency_absence),
            ("foreign_ebitda_share", self.foreign_ebitda_share, self.operating_fx_absence),
            ("hedge_ratio", self.hedge_ratio, self.hedge_absence),
        )
        for name, value, absence in pairs:
            if (value is None) == (absence is None):
                raise ValueError(f"{name}: exactly one of the value and its absence is required")
        if not self.rate_shocks_bp or not self.fx_shocks:
            raise ValueError("at least one rate shock and one currency move are required")
        if len(self.rate_shocks_bp) > len(_ORD) or len(self.fx_shocks) > len(_ORD):
            raise ValueError(f"at most {len(_ORD)} shocks of each kind are supported")


# --- parsing a validated submission ----------------------------------------------------------
def _row_decimal(token: str) -> Decimal:
    """A statement-row value; parentheses mean negative."""
    if token.startswith("(") and token.endswith(")"):
        return -Decimal(token[1:-1])
    return Decimal(token)


def _cite(ref: Mapping[str, Any]) -> Cite:
    return (str(ref["source_id"]), str(ref["locator"]))


def _absence(raw: Mapping[str, Any] | None) -> Absence | None:
    return None if raw is None else Absence(reason=raw["reason"], follow_up=raw["follow_up"])


def inputs_from_submission(
    submission: Mapping[str, Any], *, source_names: Mapping[str, str]
) -> MacroFxInputs:
    """The input object of a submission that ``validate_macro_fx`` accepted."""
    sub = submission
    ex, fx = sub["earnings"], sub["fx"]

    def row(ref: Mapping[str, Any]) -> Sourced:
        return Sourced(value=_row_decimal(ref["value_text"]), cite=_cite(ref))

    def code(ref: Mapping[str, Any]) -> SourcedCode:
        return SourcedCode(code=ref["code_text"], cite=_cite(ref))

    facility = None
    if sub.get("rate_exposure"):
        r = sub["rate_exposure"]
        basis = r["rate_basis"]
        facility = FacilityTerms(
            balance=Sourced(
                Decimal(r["facility_balance"]["value_text"]), _cite(r["facility_balance"])
            ),
            basis=RateBasis(basis["rate_type"], basis["reference_rate"], _cite(basis)),
            spread_bp=Sourced(Decimal(r["spread"]["bps_text"]), _cite(r["spread"])),
            floor_bp=Sourced(Decimal(r["floor"]["bps_text"]), _cite(r["floor"])),
        )
    share = fx.get("foreign_ebitda_share")
    hedge = sub.get("hedge_ratio")
    return MacroFxInputs(
        reporting_currency=code(sub["reporting_currency"]),
        total_debt=row(ex["total_debt"]),
        ebitda=row(ex["ebitda"]),
        interest=row(ex["interest"]),
        fcf=row(ex["fcf"]),
        fx_cash_effect=row(fx["fx_cash_effect"]),
        facility=facility,
        rate_absence=_absence(sub.get("rate_absence")),
        debt_currency=code(fx["debt_currency"]) if fx.get("debt_currency") else None,
        debt_currency_absence=_absence(fx.get("debt_currency_absence")),
        foreign_ebitda_share=(
            Sourced(_exact(Decimal(share["percent_text"]) / 100), _cite(share)) if share else None
        ),
        operating_fx_absence=_absence(fx.get("operating_fx_absence")),
        hedge_ratio=_exact(Decimal(hedge["percent_text"]) / 100) if hedge else None,
        hedge_absence=_absence(sub.get("hedge_absence")),
        rate_shocks_bp=tuple(Decimal(t) for t in sub["rate_shocks_bp"]),
        fx_shocks=tuple(_exact(Decimal(t) / 100) for t in sub["fx_shocks_percent"]),
        shock_rationale=sub["shock_rationale"],
        assessments=tuple(
            Assessment(
                section=a["section"],
                category=a["category"],
                text=a["text"],
                basis=tuple(_cite(b) for b in a["basis"]),
                limitation=a.get("limitation"),
            )
            for a in sub["assessments"]
        ),
        summary=sub["summary"]["text"],
        source_names=dict(source_names),
    )


def operands_of(inputs: MacroFxInputs) -> Operands:
    f = inputs.facility
    return Operands(
        total_debt=inputs.total_debt.value,
        ebitda=inputs.ebitda.value,
        interest=inputs.interest.value,
        fcf=inputs.fcf.value,
        facility_balance=f.balance.value if f else None,
        rate_type=f.basis.rate_type if f else None,
        floor_bp=f.floor_bp.value if f else None,
        debt_foreign=(
            inputs.debt_currency.code != inputs.reporting_currency.code
            if inputs.debt_currency
            else None
        ),
        foreign_ebitda_share=inputs.foreign_ebitda_share.value
        if inputs.foreign_ebitda_share
        else None,
    )


# --- the validator (journaled issues, wording frozen in expected.json#refusals) ----------------
_SECTIONS = ("interest_rate", "fx", "hedging")
_CATEGORIES = ("Documentary Fact", "Analyst Interpretation", "Insufficient Information")
_PROHIBITED = re.compile(
    r"\b(?:recommend|buy|sell|overweight|underweight|downgrade|upgrade|covenant breach)\b",
    re.IGNORECASE,
)
_ROW_LABELS = {
    "ebitda": "Reported EBITDA",
    "interest": "Cash interest paid",
    "fcf": "Levered free cash flow",
    "total_debt": "Total debt",
    "fx_cash_effect": "FX effect on cash",
}
_SENTENCE_NUM = re.compile(r"[0-9]{1,3}(?:\.[0-9]{1,4})?")  # operand bound: at most 999.9999
_ROW_NUM = re.compile(r"[0-9]+(?:\.[0-9]+)?|\([0-9]+(?:\.[0-9]+)?\)")  # parentheses balanced
_HEDGE_NUM = re.compile(r"[0-9]{1,3}(?:\.[0-9]{1,2})?")
_RATE_PHRASE = re.compile(r"\b(floating|fixed)[\s-]+rate\b", re.IGNORECASE)
_FY_HEADER = re.compile(r"FY 2025(?:-12-31)?$")
_MAX_SHOCKS = 3
_RATE_BP = (1, 1000)
_FX_PERCENT = (1, 50)


def _unsigned(token: str, text: str) -> set[tuple[int, int]]:
    """The spans where ``token`` is a whole, unsigned number in ``text`` (a normalised reading).

    Round 10: a figure is the signed numeral the text prints. A ``-`` before the first digit is a
    minus when it starts the text or follows a character that is neither a letter nor a digit,
    and a numeral in accounting parentheses reads as negative; such a printed figure is not an
    occurrence of the unsigned token. A ``+`` is ignored. Round 12 rule W: whitespace never
    separates a sign from its figure, so the minus may stand one space before the first digit
    (``normalise`` makes any whitespace run, a line break included, one space), and each
    accounting parenthesis may hold one space inside it."""
    minus = r"(?<![A-Za-z0-9])-"
    pattern = rf"(?<![0-9.])(?<!{minus})(?<!{minus} )" + re.escape(token) + r"(?![0-9]|\.[0-9])"
    return {
        m.span()
        for m in re.finditer(pattern, text)
        if not (text.endswith(("(", "( "), 0, m.start()) and text.startswith((")", " )"), m.end()))
    }


def _readings(raw: str) -> tuple[str, ...]:
    """``normalise(raw)``, plus the same with its hyphen wraps joined if ``raw`` holds one."""
    plain = normalise(raw)  # maps U+2212 and the dashes to "-"
    return (plain, reading(raw, join_wraps=True).text) if hyphen_wrapped(raw) else (plain,)


def _starts(needle: str, text: str) -> Iterator[int]:
    """Every index at which ``needle`` occurs in ``text``, overlapping occurrences included."""
    at = text.find(needle)
    while at >= 0:
        yield at
        at = text.find(needle, at + 1)


def _once(token: str, quote: str, page: str) -> bool:
    """token occurs exactly once in the normalised quote as a whole, unsigned number (round 10),
    and the page prints it there as the same unsigned whole figure (round 11 B1).

    B1: a figure at an edge of the quote occurs only if, at every occurrence of the quote (as
    normalised, and with its wraps joined if wrapped) in every reading of the page, the page does
    not continue it: no digit, ``.`` or minus sign before it, no digit or ``.`` plus a digit
    after it, and no accounting parentheses around it. Every occurrence is checked, not only the
    edge ones: away from an edge the characters around the figure are the quote's own, which the
    quote reading has already passed, so the result is the same."""
    if len(_unsigned(token, normalise(quote))) != 1:
        return False
    for text in _readings(page):
        on_page = _unsigned(token, text)
        for needle in _readings(quote):
            for at in _starts(needle, text):
                if any((at + s, at + e) not in on_page for s, e in _unsigned(token, needle)):
                    return False
    return True


class _Check:
    """Accumulates the validator's issues in rule order over one pack's financial pages."""

    def __init__(self, pages: Mapping[str, str]) -> None:
        self.pages = pages
        self.issues: list[str] = []

    def add(self, issue: str) -> None:
        self.issues.append(issue)

    def empty(self, path: str, text: str | None) -> None:
        """Round 11: analyst text that is present but blank is refused; round 12 B10: blank is
        ``blank.is_blank`` (whitespace and Unicode format characters only, or "")."""
        if text is not None and is_blank(text):
            self.add(f"{path}: empty text")

    def digit_free(self, path: str, text: str | None) -> None:
        if text is not None and any(ch.isnumeric() for ch in text):
            self.add(f"{path}: digits are not allowed")

    def prose(self, path: str, text: str) -> None:
        """An analyst text field: not blank, and digit-free."""
        self.empty(path, text)
        self.digit_free(path, text)

    def on_page(self, ref: Mapping[str, Any], path: str) -> bool:
        sid, loc = ref["source_id"], ref["locator"]
        if sid != SOURCE_ID:
            self.add(f"{path}: source {sid} is outside the CP-2E scope ({SOURCE_ID})")
            return False
        if loc not in self.pages or not quoted(ref["quote"], self.pages[loc]):
            self.add(f"{path}: quote not found on {sid} {loc}")
            return False
        return True

    def code(self, ref: Mapping[str, Any], path: str) -> None:
        if not self.on_page(ref, path):
            return
        c = ref["code_text"]
        quote = normalise(ref["quote"])  # the text the on_page match read
        in_quote = re.search(rf"(?<![A-Za-z]){re.escape(c)}(?![A-Za-z])", quote)
        if not re.fullmatch(r"[A-Z]{3}", c) or not in_quote:
            self.add(f"{path}: code_text {c} does not occur in the quote")

    def labelled(self, ref: Mapping[str, Any], key: str, label: str, path: str) -> Decimal | None:
        """A sentence operand: ``ref[key]`` occurs once in the quote, right after ``label``."""
        if not self.on_page(ref, path):
            return None
        v = ref[key]
        if not _SENTENCE_NUM.fullmatch(v) or not _once(v, ref["quote"], self.pages[ref["locator"]]):
            self.add(f"{path}: {key} {v} does not occur in the quote")
            return None
        if not re.search(rf"{label}\s+{re.escape(v)}(?![0-9])", normalise(ref["quote"])):
            self.add(f"{path}: {key} {v} is not labelled {label} in the quote")
            return None
        return Decimal(v)

    def row(self, ref: Mapping[str, Any], key: str, path: str) -> Decimal | None:
        """A statement row: a whole page line with its label, FY column last, value_text last."""
        if not self.on_page(ref, path):
            return None
        lines = [ln.strip() for ln in self.pages[ref["locator"]].split("\n")]
        quote = ref["quote"]
        if quote.strip() not in lines:
            self.add(f"{path}: quote is not a whole page line")
            return None
        if not quote.startswith(_ROW_LABELS[key] + "  "):
            self.add(f"{path}: the row is not {_ROW_LABELS[key]}")
            return None
        header = next((ln for ln in lines if ln.startswith("Period")), "")
        if not _FY_HEADER.search(header):
            self.add(f"{path}: the page header does not end in the FY column")
            return None
        v = ref["value_text"]
        if not _ROW_NUM.fullmatch(v) or v != quote.split()[-1]:
            self.add(f"{path}: value_text {v} is not the last value of the row")
            return None
        return _row_decimal(v)

    def exactly_one(self, a: object, b: object, path: str, names: tuple[str, str]) -> bool:
        if bool(a) == bool(b):
            self.add(f"{path}: exactly one of {names[0]} and {names[1]} is required")
            return False
        return True

    def shocks(
        self, values: Sequence[str], path: str, unit: str, digits: int, bounds: tuple[int, int]
    ) -> None:
        """1 to 3 whole-number shocks of at most ``digits`` digits, in bounds, strictly rising."""
        if not 1 <= len(values) <= _MAX_SHOCKS:
            self.add(f"{path}: between 1 and {_MAX_SHOCKS} shocks are required")
        parsed: list[int] = []
        for i, t in enumerate(values):
            if re.fullmatch(rf"[0-9]{{1,{digits}}}", t) and bounds[0] <= int(t) <= bounds[1]:
                parsed.append(int(t))
            else:
                self.add(f"{path}[{i}]: shock must be {unit} from {bounds[0]} to {bounds[1]}")
        if len(parsed) == len(values) and parsed != sorted(set(parsed)):
            self.add(f"{path}: shocks must be strictly increasing")


def _split(rb: Mapping[str, Any]) -> bool:
    """Round 11 B3: a wrapped quote's name spelled with the wrap's ``- `` is not on the page."""
    return hyphen_wrapped(rb["quote"]) and "- " in normalise(rb["reference_rate"])


def _check_rate_exposure(chk: _Check, r: Mapping[str, Any]) -> Decimal | None:
    balance = chk.labelled(
        r["facility_balance"], "value_text", "balance of", "rate_exposure.facility_balance"
    )
    rb, path = r["rate_basis"], "rate_exposure.rate_basis"
    if chk.on_page(rb, path):
        quote = normalise(rb["quote"])  # the text the on_page match read
        stems = {m.lower() for m in _RATE_PHRASE.findall(quote)}  # rulings E5 and E8
        said = stems.pop().upper() if len(stems) == 1 else None
        if said is None:
            chk.add(f"{path}: the quote states neither a floating nor a fixed rate")
        elif rb["rate_type"] != said:
            chk.add(f"{path}: rate_type {rb['rate_type']} contradicts the quote")
        elif said == "FLOATING" and (rb["reference_rate"] not in quote or _split(rb)):
            chk.add(f"{path}: reference_rate does not occur in the quote")
    chk.empty(f"{path}.reference_rate", rb["reference_rate"])
    chk.labelled(r["spread"], "bps_text", "spread", "rate_exposure.spread")
    chk.labelled(r["floor"], "bps_text", "floor", "rate_exposure.floor")
    return balance


def _check_fx(chk: _Check, fx: Mapping[str, Any]) -> None:
    chk.row(fx["fx_cash_effect"], "fx_cash_effect", "fx.fx_cash_effect")
    dc = fx.get("debt_currency")
    names = ("debt_currency", "debt_currency_absence")
    if chk.exactly_one(dc, fx.get("debt_currency_absence"), "fx.debt_currency", names) and dc:
        chk.code(dc, "fx.debt_currency")  # a code other than the reporting currency is valid
    fe, path = fx.get("foreign_ebitda_share"), "fx.foreign_ebitda_share"
    names = ("foreign_ebitda_share", "operating_fx_absence")
    pair_ok = chk.exactly_one(fe, fx.get("operating_fx_absence"), path, names)
    if pair_ok and fe and chk.on_page(fe, path):
        pt = fe["percent_text"]
        page = chk.pages[fe["locator"]]
        ok = _SENTENCE_NUM.fullmatch(pt) and _once(pt, fe["quote"], page) and Decimal(pt) <= 100
        if not ok:
            chk.add(f"{path}: percent_text {pt} does not occur in the quote")


def _check_hedge(chk: _Check, sub: Mapping[str, Any]) -> None:
    hr = sub.get("hedge_ratio")
    names = ("hedge_ratio", "hedge_absence")
    if chk.exactly_one(hr, sub.get("hedge_absence"), "hedge_ratio", names) and hr:
        chk.prose("hedge_ratio.rationale", hr["rationale"])
        pt = hr["percent_text"]
        if not _HEDGE_NUM.fullmatch(pt) or not Decimal(pt) <= 100:
            chk.add("hedge_ratio: percent must be at least 0 and at most 100")


def _check_text(chk: _Check, sub: Mapping[str, Any]) -> None:
    chk.prose("shock_rationale", sub["shock_rationale"])
    sections = [a["section"] for a in sub["assessments"]]
    for i, a in enumerate(sub["assessments"]):
        p = f"assessments[{i}]"
        if a["section"] not in _SECTIONS:
            chk.add(f"{p}: section {a['section']} is not one of {', '.join(_SECTIONS)}")
        elif sections.count(a["section"]) > 1:
            chk.add(f"{p}: section {a['section']} appears more than once")
        if a["category"] not in _CATEGORIES:
            chk.add(f"{p}: category {a['category']} is not allowed")
        chk.prose(f"{p}.text", a["text"])
        if _PROHIBITED.search(a["text"]):
            chk.add(f"{p}.text: text carries a prohibited conclusion")
        limitation = a.get("limitation")
        chk.empty(f"{p}.limitation", limitation)
        stated = limitation is not None and not is_blank(limitation)  # blank states none
        if (a["category"] == "Insufficient Information") != stated:
            chk.add(f"{p}: limitation is required for Insufficient Information and only for it")
        if a["category"] == "Documentary Fact" and not a["basis"]:
            chk.add(f"{p}: a Documentary Fact needs at least one basis quote")
        for j, b in enumerate(a["basis"]):
            chk.on_page(b, f"{p}.basis[{j}]")
    for s in _SECTIONS:
        if s not in sections:
            chk.add(f"assessments: section {s} is missing")
    chk.prose("summary.text", sub["summary"]["text"])
    if _PROHIBITED.search(sub["summary"]["text"]):
        chk.add("summary.text: text carries a prohibited conclusion")


def validate_macro_fx(
    *, submission: Mapping[str, Any], pages: Mapping[str, str]
) -> tuple[str, ...]:
    """Issues of a macro_fx submission against the pack's financial pages (locator -> text)."""
    sub, chk = submission, _Check(pages)
    chk.code(sub["reporting_currency"], "reporting_currency")
    r = sub.get("rate_exposure")
    chk.exactly_one(r, sub.get("rate_absence"), "rate_exposure", ("rate_exposure", "rate_absence"))
    balance = _check_rate_exposure(chk, r) if r else None
    total_debt = None
    for key in ("ebitda", "interest", "fcf", "total_debt"):
        value = chk.row(sub["earnings"][key], key, f"earnings.{key}")
        if key == "total_debt":
            total_debt = value
    if r and balance is not None and total_debt is not None and balance > total_debt:
        chk.add(
            f"rate_exposure.facility_balance: value_text {r['facility_balance']['value_text']} "
            f"exceeds total debt {sub['earnings']['total_debt']['value_text']}"
        )
    fx = sub["fx"]
    _check_fx(chk, fx)
    _check_hedge(chk, sub)
    for key in ("rate_absence", "debt_currency_absence", "operating_fx_absence", "hedge_absence"):
        absence = sub.get(key) or fx.get(key)
        if absence:
            at = key if sub.get(key) else f"fx.{key}"  # the field's place in the submission
            for part in ("reason", "follow_up"):
                chk.empty(f"{at}.{part}", absence[part])
                chk.digit_free(f"{key}.{part}", absence[part])
    chk.shocks(
        sub["rate_shocks_bp"], "rate_shocks_bp", "a whole number of basis points", 4, _RATE_BP
    )
    chk.shocks(sub["fx_shocks_percent"], "fx_shocks_percent", "a whole percent", 2, _FX_PERCENT)
    _check_text(chk, sub)
    return tuple(chk.issues)


# --- cells, tables and claims ----------------------------------------------------------------
PER_FLOW = "FY 2025: 2025-01-01 to 2025-12-31"
PER_BAL = "Balance at 2025-12-31"
PER_RUN = "Run as of 2026-01-10"
PER_SHOCK = "FY 2025 base with a shock"
MILLIONS_SCALE = Decimal(1000000)
# An unsettled cell's G# is bound at render time (expected.json#cell_notation.gap).
GAP_SHOWN = {"missing": "∅ G#", "not_applicable": "∅ G# n.m."}
ValueClass = Literal["source", "calculated", "analyst_judgment"]


@dataclass(frozen=True)
class Cell:
    """One table cell: a fact's coordinates, value, display spelling and page-level cites."""

    fact_id: str
    column: str
    status: Literal["known", "missing", "not_applicable"]
    shown: str
    period: str | None = None
    amount: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    scale: Decimal = Decimal(1)
    decimals: int | None = None
    text: str | None = None
    cites: tuple[Cite, ...] = ()
    value_class: ValueClass | None = None
    calculation_id: str | None = None
    formula: str | None = None
    limitation: str | None = None

    def fact(self) -> Fact:
        """The product Fact of this cell, without citations (bound to quotes in Stage 2)."""
        table_id, row_id, fld = self.fact_id.rsplit(".", 2)
        return Fact(
            fact_id=self.fact_id,
            label=self.column,
            table_id=table_id,
            row_id=row_id,
            field=fld,
            amount=self.amount,
            text=self.text,
            status=self.status,
            unit=self.unit,
            currency=self.currency,
            scale=self.scale,
            decimals=self.decimals,
            period=self.period,
            calculation_id=self.calculation_id,
            value_class=self.value_class,
            formula=self.formula,
            limitation=self.limitation,
        )


@dataclass(frozen=True)
class Row:
    row_id: str
    label: str
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    row_header: str
    columns: tuple[tuple[str, str], ...]  # (field, label)
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class ClaimText:
    claim_id: str
    text: str
    refs: tuple[str, ...]
    cites: tuple[Cite, ...]


@dataclass(frozen=True)
class MacroFxResult:
    sensitivity: Sensitivity
    tables: tuple[Table, ...]
    claims: tuple[ClaimText, ...]
    limitations: tuple[str, ...]


def _dedupe(cites: Sequence[Cite]) -> tuple[Cite, ...]:
    return tuple(dict.fromkeys(cites))


@dataclass(frozen=True)
class _Spec:
    """A cell before it gets its coordinates: number, text or gap."""

    kind: Literal["num", "text", "gap"]
    amount: Decimal | None = None
    text: str | None = None
    unit: str | None = None
    decimals: int | None = None
    period: str | None = None
    cites: tuple[Cite, ...] = ()
    value_class: ValueClass | None = None
    calc: str | None = None
    formula: str | None = None
    status: State = "known"


def _num(
    amount: Decimal,
    unit: str,
    decimals: int | None,
    cites: Sequence[Cite],
    value_class: ValueClass,
    period: str,
    calc: str | None = None,
    formula: str | None = None,
) -> _Spec:
    return _Spec(
        "num",
        amount=_exact(amount),
        unit=unit,
        decimals=decimals,
        period=period,
        cites=_dedupe(cites),
        value_class=value_class,
        calc=calc,
        formula=formula,
    )


def _txt(text: str, cites: Sequence[Cite] = (), value_class: ValueClass | None = None) -> _Spec:
    return _Spec("text", text=text, cites=_dedupe(cites), value_class=value_class)


def _gap(reason: str, unit: str | None = None, status: State = "missing") -> _Spec:
    return _Spec("gap", text=reason, unit=unit, status=status)


def _derived(
    v: Value,
    unit: str,
    decimals: int,
    cites: Sequence[Cite],
    calc: str,
    formula: str,
    period: str,
) -> _Spec:
    """A derived value as a cell: known is a calculated number, otherwise a gap."""
    if v.amount is not None:
        return _num(v.amount, unit, decimals, cites, "calculated", period, calc, formula)
    prefix = "Not calculable: " if v.state == "missing" else "Not meaningful: "
    return _gap(prefix + str(v.reason), unit, v.state)


def _materialise(spec: _Spec, fact_id: str, column: str, currency: str) -> Cell:
    millions = spec.unit == "MILLIONS"  # a MILLIONS fact carries the currency and its scale
    cell = Cell(
        fact_id=fact_id,
        column=column,
        status=spec.status,
        shown=GAP_SHOWN.get(spec.status, ""),
        unit=spec.unit,
        currency=currency if millions else None,
        scale=MILLIONS_SCALE if millions else Decimal(1),
    )
    if spec.kind == "gap":
        return replace(cell, limitation=spec.text)
    cell = replace(
        cell,
        period=spec.period,
        amount=spec.amount,
        decimals=spec.decimals,
        text=spec.text,
        cites=spec.cites,
        value_class=spec.value_class,
        calculation_id=spec.calc,
        formula=spec.formula,
    )
    _, _, shown = fact_spelling(cell.fact(), None)
    return replace(cell, shown=shown)


def _table(
    table_id: str,
    title: str,
    row_header: str,
    columns: Sequence[tuple[str, str]],
    rows: Sequence[tuple[str, str, Sequence[_Spec]]],
    currency: str,
) -> Table:
    out = []
    for row_id, label, specs in rows:
        if len(specs) != len(columns):
            raise ValueError(f"{table_id}.{row_id}: {len(specs)} cells for {len(columns)} columns")
        cells = tuple(
            _materialise(s, f"{table_id}.{row_id}.{fld}", col, currency)
            for (fld, col), s in zip(columns, specs, strict=True)
        )
        out.append(Row(row_id, label, cells))
    return Table(table_id, title, row_header, tuple(columns), tuple(out))


_ORD = ("first", "second", "third")
_NO_RATE = "Not stated: the pack holds no facility rate terms"
_NO_DEBT_CCY = "Not stated: the pack holds no statement of the currency of the debt"
_NO_SPLIT = "Not stated: no source gives the split of earnings by currency"


@dataclass(frozen=True)
class _Cites:
    """The page cites each formula reads, in formula order."""

    ccy: tuple[Cite, ...]
    debt: tuple[Cite, ...]
    ebitda: tuple[Cite, ...]
    interest: tuple[Cite, ...]
    fcf: tuple[Cite, ...]
    rate: tuple[Cite, ...]  # balance, rate basis, floor
    balance: tuple[Cite, ...]
    debt_ccy: tuple[Cite, ...]
    share: tuple[Cite, ...]


def _cites_of(i: MacroFxInputs) -> _Cites:
    f = i.facility
    return _Cites(
        ccy=(i.reporting_currency.cite,),
        debt=(i.total_debt.cite,),
        ebitda=(i.ebitda.cite,),
        interest=(i.interest.cite,),
        fcf=(i.fcf.cite,),
        rate=(f.balance.cite, f.basis.cite, f.floor_bp.cite) if f else (),
        balance=(f.balance.cite,) if f else (),
        debt_ccy=(i.debt_currency.cite,) if i.debt_currency else (),
        share=(i.foreign_ebitda_share.cite,) if i.foreign_ebitda_share else (),
    )


def _src(i: Sourced, unit: str, decimals: int | None, period: str) -> _Spec:
    return _num(i.value, unit, decimals, (i.cite,), "source", period)


def _t2f1_facility(i: MacroFxInputs) -> list[tuple[str, str, Sequence[_Spec]]]:
    f = i.facility
    if f is None:
        return [
            ("r03", "Term loan balance", [_gap(_NO_RATE, "MILLIONS"), _gap(_NO_RATE)]),
            ("r04", "Rate basis", [_gap(_NO_RATE), _gap(_NO_RATE)]),
            ("r05", "Spread", [_gap(_NO_RATE, "basis_points"), _gap(_NO_RATE)]),
            ("r06", "Floor", [_gap(_NO_RATE, "basis_points"), _gap(_NO_RATE)]),
        ]
    kind = "Floating" if f.basis.rate_type == "FLOATING" else "Fixed"
    basis = (f.basis.cite,)
    return [
        (
            "r03",
            "Term loan balance",
            [
                _src(f.balance, "MILLIONS", 2, PER_BAL),
                _txt("Facility schedule, closing balance", (f.balance.cite,)),
            ],
        ),
        (
            "r04",
            "Rate basis",
            [
                _txt(f"{kind} rate, {f.basis.reference_rate} reference rate", basis),
                _txt("Facility schedule", basis),
            ],
        ),
        (
            "r05",
            "Spread",
            [
                _src(f.spread_bp, "basis_points", None, PER_BAL),
                _txt("Facility schedule", (f.spread_bp.cite,)),
            ],
        ),
        (
            "r06",
            "Floor",
            [
                _src(f.floor_bp, "basis_points", None, PER_BAL),
                _txt("Facility schedule", (f.floor_bp.cite,)),
            ],
        ),
    ]


def _t2f1(i: MacroFxInputs, c: _Cites) -> list[tuple[str, str, Sequence[_Spec]]]:
    def flow(s: Sourced, basis: str) -> list[_Spec]:
        return [_src(s, "MILLIONS", 2, PER_FLOW), _txt(basis, (s.cite,))]

    debt_ccy = (
        [_txt(i.debt_currency.code, c.debt_ccy), _txt("Facility schedule header", c.debt_ccy)]
        if i.debt_currency
        else [_gap(_NO_DEBT_CCY), _gap(_NO_DEBT_CCY)]
    )
    share = (
        [
            _src(i.foreign_ebitda_share, "PERCENT", 1, PER_FLOW),
            _txt("Source statement", c.share),
        ]
        if i.foreign_ebitda_share
        else [_gap(_NO_SPLIT, "PERCENT"), _gap(_NO_SPLIT)]
    )
    return [
        (
            "r01",
            "Reporting currency",
            [_txt(i.reporting_currency.code, c.ccy), _txt("Financial statements header", c.ccy)],
        ),
        (
            "r02",
            "Total debt",
            [_src(i.total_debt, "MILLIONS", 2, PER_BAL), _txt("Balance sheet, FY column", c.debt)],
        ),
        *_t2f1_facility(i),
        ("r07", "Reported EBITDA", flow(i.ebitda, "Income statement, FY column")),
        ("r08", "Cash interest paid", flow(i.interest, "Cash flow statement, FY column")),
        ("r09", "Levered free cash flow", flow(i.fcf, "Cash flow statement, FY column")),
        ("r10", "FX effect on cash", flow(i.fx_cash_effect, "Cash flow statement, FY column")),
        ("r11", "Currency of the debt", debt_ccy),
        ("r12", "Share of EBITDA earned in other currencies", share),
    ]


def _t2f2(s: Sensitivity, c: _Cites) -> list[tuple[str, str, Sequence[_Spec]]]:
    rate2 = c.rate[:2]  # balance and rate basis
    return [
        (
            "r01",
            "Floating-rate debt",
            [
                _derived(s.floating, "MILLIONS", 2, rate2, "cp2e.floating",
                         "facility balance if the rate is floating, else zero", PER_BAL),
                _txt("Closing balance of a floating-rate facility"),
            ],
        ),
        (
            "r02",
            "Floating-rate debt share of total debt",
            [
                _derived(s.floating_share, "PERCENT", 1, rate2 + c.debt, "cp2e.floating_share",
                         "floating-rate debt / total debt", PER_BAL),
                _txt("Share of total debt"),
            ],
        ),
        (
            "r03",
            "Interest coverage",
            [
                _derived(s.cov_base, "MULTIPLE", 2, c.ebitda + c.interest, "cp2e.cov_base",
                         "EBITDA / cash interest paid", PER_FLOW),
                _txt("Reported EBITDA over cash interest, FY 2025"),
            ],
        ),
        (
            "r04",
            "Total leverage",
            [
                _derived(s.lev_base, "MULTIPLE", 2, c.debt + c.ebitda, "cp2e.lev_base",
                         "total debt / EBITDA", PER_FLOW),
                _txt("Total debt over reported EBITDA, FY 2025"),
            ],
        ),
        (
            "r05",
            "Foreign-currency debt",
            [
                _derived(s.foreign_debt, "MILLIONS", 2, c.balance + c.debt_ccy + c.ccy,
                         "cp2e.foreign_debt",
                         "term loan balance if its currency differs from the reporting currency,"
                         " else zero", PER_BAL),
                _txt("Debt denominated in a currency other than the reporting currency"),
            ],
        ),
        (
            "r06",
            "Foreign-currency debt share of total debt",
            [
                _derived(s.foreign_debt_share, "PERCENT", 1, c.debt_ccy + c.ccy + c.debt,
                         "cp2e.foreign_debt_share", "foreign-currency debt / total debt", PER_BAL),
                _txt("Share of total debt"),
            ],
        ),
    ]  # fmt: skip


_T2F3_COLUMNS = (
    ("shock", "Rate shock"),
    ("gross", "Added annual interest before hedges"),
    ("net", "Added annual interest after hedges"),
    ("interest_after", "Cash interest after the shock"),
    ("cov_after", "Interest coverage after the shock"),
    ("cov_change", "Change in interest coverage"),
    ("fcf_after", "Free cash flow after the shock"),
    ("share", "Added interest as share of EBITDA"),
)


def _t2f3(s: Sensitivity, c: _Cites) -> list[tuple[str, str, Sequence[_Spec]]]:
    rows: list[tuple[str, str, Sequence[_Spec]]] = []
    cov = c.rate + c.interest + c.ebitda
    for n, r in enumerate(s.rate, 1):
        calc = f"cp2e.rate{n}"
        assert r.shock_bp.amount is not None
        rows.append((f"r{n:02d}", f"Reference rate up, {_ORD[n - 1]} shock", [
            _num(r.shock_bp.amount, "basis_points", None, (), "analyst_judgment", PER_RUN),
            _derived(r.gross, "MILLIONS", 2, c.rate, f"{calc}.gross",
                     "floating-rate debt x shock / 10000", PER_SHOCK),
            _derived(r.net, "MILLIONS", 2, c.rate, f"{calc}.net",
                     "added interest before hedges x (1 - hedge ratio)", PER_SHOCK),
            _derived(r.interest_after, "MILLIONS", 2, c.rate + c.interest,
                     f"{calc}.interest_after", "cash interest + added interest before hedges",
                     PER_SHOCK),
            _derived(r.cov_after, "MULTIPLE", 2, cov, f"{calc}.cov_after",
                     "EBITDA / cash interest after the shock", PER_SHOCK),
            _derived(r.cov_change, "MULTIPLE", 2, cov, f"{calc}.cov_change",
                     "coverage after the shock - coverage before", PER_SHOCK),
            _derived(r.fcf_after, "MILLIONS", 2, c.rate + c.fcf, f"{calc}.fcf_after",
                     "free cash flow - added interest before hedges", PER_SHOCK),
            _derived(r.share_of_ebitda, "PERCENT", 1, c.rate + c.ebitda, f"{calc}.share",
                     "added interest before hedges / EBITDA", PER_SHOCK),
        ]))  # fmt: skip
    return rows


_T2F4_COLUMNS = (
    ("shock", "Currency move"),
    ("debt_change", "Change in debt"),
    ("debt_after", "Total debt after the move"),
    ("ebitda_change", "Change in EBITDA"),
    ("lev_after", "Total leverage after the move"),
)


def _t2f4(s: Sensitivity, c: _Cites) -> list[tuple[str, str, Sequence[_Spec]]]:
    rows: list[tuple[str, str, Sequence[_Spec]]] = []
    fc = c.balance + c.debt_ccy
    for n, r in enumerate(s.fx, 1):
        calc = f"cp2e.fx{n}"
        assert r.shock.amount is not None
        rows.append((f"r{n:02d}", f"Foreign currency strengthens, {_ORD[n - 1]} move", [
            _num(r.shock.amount, "PERCENT", 0, (), "analyst_judgment", PER_RUN),
            _derived(r.debt_change, "MILLIONS", 2, fc, f"{calc}.debt_change",
                     "foreign-currency debt x move", PER_SHOCK),
            _derived(r.debt_after, "MILLIONS", 2, fc + c.debt, f"{calc}.debt_after",
                     "total debt + change in debt", PER_SHOCK),
            _derived(r.ebitda_change, "MILLIONS", 2, c.share + c.ebitda, f"{calc}.ebitda_change",
                     "EBITDA x share earned in other currencies x move", PER_SHOCK),
            _derived(r.lev_after, "MULTIPLE", 2, fc + c.debt + c.share + c.ebitda,
                     f"{calc}.lev_after", "total debt after the move / EBITDA after the move",
                     PER_SHOCK),
        ]))  # fmt: skip
    return rows


def _t2f5(i: MacroFxInputs, s: Sensitivity, c: _Cites) -> list[tuple[str, str, Sequence[_Spec]]]:
    hedge = (
        _num(i.hedge_ratio, "PERCENT", 0, (), "analyst_judgment", PER_RUN)
        if i.hedge_ratio is not None
        else _gap("Not stated: no hedge ratio is assumed or sourced", "PERCENT")
    )
    after = _derived(
        s.floating_after_hedge,
        "MILLIONS",
        2,
        c.rate[:2],
        "cp2e.floating_after_hedge",
        "floating-rate debt x (1 - hedge ratio)",
        PER_BAL,
    )
    return [
        (
            "r01",
            "Hedge ratio (analyst assumption)",
            [hedge, _txt("Share of floating-rate debt hedged")],
        ),
        ("r02", "Floating-rate debt after hedges", [after, _txt("Unhedged floating-rate debt")]),
        (
            "r03",
            "Hedging instruments",
            [
                _gap("Not stated: no source states a hedging instrument"),
                _txt("Located in the sources"),
            ],
        ),
    ]


def _t2f6(i: MacroFxInputs) -> list[tuple[str, str, Sequence[_Spec]]]:
    judged: list[tuple[str, str, str, tuple[Cite, ...]]] = [
        (a.section.replace("_", " ").capitalize(), a.category, a.text, a.basis)
        for a in i.assessments
    ]
    judged.append(("Shock basis", "Analyst Interpretation", i.shock_rationale, ()))
    judged.append(("Summary", "Analyst Interpretation", i.summary, ()))
    return [
        (
            f"r{n:02d}",
            label,
            [_txt(category, basis, "analyst_judgment"), _txt(text, basis, "analyst_judgment")],
        )
        for n, (label, category, text, basis) in enumerate(judged, 1)
    ]


def _t2f7(i: MacroFxInputs) -> list[tuple[str, str, Sequence[_Spec]]]:
    missing = [
        (absence, affected)
        for absence, affected in (
            (i.rate_absence, "Floating-rate debt, added interest and coverage after a rate shock"),
            (
                i.debt_currency_absence,
                "Foreign-currency debt and the debt effect of a currency shock",
            ),
            (i.operating_fx_absence, "Currency effect on EBITDA and on leverage"),
            (i.hedge_absence, "Added interest after hedges"),
        )
        if absence is not None
    ]
    if not missing:
        return [("r01", "Missing inputs", [_txt("None"), _txt("No input is missing")])]
    return [
        (f"r{n:02d}", affected, [_txt(affected), _txt(absence.reason)])
        for n, (absence, affected) in enumerate(missing, 1)
    ]


def cited_pages(i: MacroFxInputs) -> tuple[Cite, ...]:
    """Every page the submission cites, in order of first appearance (T2F.8, tool-use cover)."""
    f = i.facility
    refs: list[Cite] = [i.reporting_currency.cite]
    if f:
        refs += [f.balance.cite, f.basis.cite, f.spread_bp.cite, f.floor_bp.cite]
    refs += [i.ebitda.cite, i.interest.cite, i.fcf.cite, i.total_debt.cite, i.fx_cash_effect.cite]
    if i.debt_currency:
        refs.append(i.debt_currency.cite)
    if i.foreign_ebitda_share:
        refs.append(i.foreign_ebitda_share.cite)
    for a in i.assessments:
        refs += a.basis
    return _dedupe(refs)


def _t2f8(i: MacroFxInputs) -> list[tuple[str, str, Sequence[_Spec]]]:
    return [
        (f"r{n:02d}", f"{i.source_names[sid]}, {loc}", [_txt(sid), _txt(loc)])
        for n, (sid, loc) in enumerate(cited_pages(i), 1)
    ]


_LIM_STATIC = (
    "Each shock is a static, parallel move applied once to the closing balances and the FY 2025 "
    "flows; no repricing date, no change in debt and no tax shield are modelled"
)
_LIM_CASH = (
    "Interest income on the cash balance is not shocked, so the added interest is not offset by "
    "any higher income on cash"
)
_LIM_FLOOR = (
    "The reference rate level is not in any source, so a floor of zero is treated as not binding "
    "for the upward shocks and downward shocks are not tested"
)
LIM_REMAINDER = (
    "The quoted facility is only part of total debt and the rate type of the remainder is not "
    "stated, so the shock figures cover the quoted facility alone"
)
_LIM_NO_RATE = "The facility rate terms are not stated, so the rate sensitivity is not calculated"
_LIM_NO_HEDGE = "Hedging is not disclosed, so every shock effect is shown before any hedge"
_LIM_HEDGE_ASSUMED = "The hedge ratio is an analyst assumption, not a source figure"
_LIM_NO_SPLIT = (
    "The split of earnings by currency is not stated, so the currency effect on EBITDA and on "
    "leverage is not calculated"
)
_LIM_DEBT_CCY = (
    "The currency of the debt is read from the header of the facility schedule, which states the "
    "currency of its amounts; no denomination clause is cited"
)
_LIM_MACRO = (
    "Macro drivers other than the reference rate and currency, such as demand, input costs and "
    "inflation, are not sourced and not assessed; the figures are unaudited FY 2025 statements"
)


_LIM_FLOOR_ABOVE = (  # ruling A4
    "The reference rate level is not in any source and the facility floor is above zero, so the "
    "rate shocks are not calculated and downward shocks are not tested"
)


def _floor_limitation(facility: FacilityTerms) -> str | None:
    """Ruling A4 by floor state, for floating-rate debt only (round 6i): a floor does not bind a
    fixed coupon, so fixed-rate debt has no floor limitation. A4's not-stated text has no path
    here, because the input object requires a quoted floor."""
    if facility.basis.rate_type == "FIXED":
        return None
    floor = facility.floor_bp.value
    if floor == 0:
        return _LIM_FLOOR
    if floor > 0:
        return _LIM_FLOOR_ABOVE
    # A validated floor is digits only; a negative one needs directly built inputs.
    raise ValueError(f"Floor limitation: a floor of {floor} basis points is not a quoted floor")


def own_limitations(i: MacroFxInputs) -> tuple[str, ...]:
    out = [_LIM_STATIC, _LIM_CASH]
    if i.facility is not None:
        floor_line = _floor_limitation(i.facility)
        if floor_line is not None:
            out.append(floor_line)
        if i.facility.balance.value < i.total_debt.value:  # LEAD ruling 9: a remainder
            out.append(LIM_REMAINDER)
    else:
        out.append(_LIM_NO_RATE)
    out.append(_LIM_NO_HEDGE if i.hedge_absence is not None else _LIM_HEDGE_ASSUMED)
    if i.operating_fx_absence is not None:
        out.append(_LIM_NO_SPLIT)
    if i.debt_currency is not None:
        out.append(_LIM_DEBT_CCY)
    out.append(_LIM_MACRO)
    return tuple(out)


# Why a missing added-interest value is missing, as claim text (rulings E2 and E4b).
_GROSS_NEEDS = {
    _NO_TERMS: "needs the facility rate terms, which the pack does not state",
    _NO_FLOOR: "needs the floor of the facility, which the pack does not state",
    _FLOOR_MAY_BIND: (
        "needs the reference rate level, which no source states, because the floor of the "
        "facility is above zero"
    ),
}


def _gross_needs(gross: Value) -> str:
    if gross.state != "missing" or gross.reason not in _GROSS_NEEDS:
        raise ValueError(f"added interest is not missing for a known reason: {gross}")
    return _GROSS_NEEDS[gross.reason]


def rate_gap_claim(n: int, gross: Value) -> str:
    """CP-2E-RATE-nn text when the added interest of shock n (1-based) is missing (ruling E2)."""
    return (
        f"The effect of the {_ORD[n - 1]} rate shock is not calculated: "
        f"[T2F.3.r{n:02d}.gross] {_gross_needs(gross)}."
    )


class _Claims:
    """Collects claims whose figures and chips name this module's own cells."""

    def __init__(self, tables: Sequence[Table]) -> None:
        self.cells = {c.fact_id: c for t in tables for r in t.rows for c in r.cells}
        self.claims: list[ClaimText] = []

    def add(self, claim_id: str, text: str, refs: Sequence[str]) -> None:
        cites = _dedupe([x for ref in refs for x in self.cells[ref].cites])
        self.claims.append(ClaimText(claim_id, text, tuple(refs), cites))

    def known(self, ref: str) -> bool:
        return self.cells[ref].status == "known"

    def fig(self, ref: str) -> str:
        """A figure reference; only a known number may be one."""
        unit = figure_unit(self.cells[ref].fact())
        if not self.known(ref) or unit is None:
            raise ValueError(f"Claim figure: {ref} is not a known number")
        return "{" + ref + "|" + unit + "}"

    def ref(self, ref: str) -> str:
        """A figure reference when the value is known, otherwise a gap chip."""
        return self.fig(ref) if self.known(ref) else f"[{ref}]"


def _rate_claims(out: _Claims, s: Sensitivity) -> None:
    floating, cov = "T2F.2.r01.value", "T2F.2.r03.value"
    for n, r in enumerate(s.rate, 1):
        nth, gross, cov_after = _ORD[n - 1], f"T2F.3.r{n:02d}.gross", f"T2F.3.r{n:02d}.cov_after"
        claim_id, adds = (
            f"CP-2E-RATE-{n:02d}",
            f"For the {nth} rate shock tested, the floating-rate",
        )
        if r.gross.state != "known":
            out.add(claim_id, rate_gap_claim(n, r.gross), [gross])
        elif out.known(cov) and r.cov_after.state == "not_applicable":  # ruling E7
            word = str(r.cov_after.reason).removeprefix("interest after the shock is ")
            if word not in ("zero", "negative"):
                raise ValueError(f"coverage after the shock is n.m. for {r.cov_after.reason!r}")
            out.add(
                claim_id,
                f"{adds} debt of {out.fig(floating)} adds {out.fig(gross)} of annual cash interest "
                "before any hedge; interest coverage after the shock is not meaningful because "
                f"cash interest after the shock is {word}: [{cov_after}].",
                [floating, gross, cov_after],
            )
        elif out.known(cov):
            out.add(
                claim_id,
                f"{adds} debt of {out.fig(floating)} adds {out.fig(gross)} of annual cash interest "
                f"before any hedge, which takes interest coverage from {out.fig(cov)} to "
                f"{out.fig(cov_after)}.",
                [floating, gross, cov, cov_after],
            )
        else:  # ruling E3: coverage at base is not meaningful
            out.add(
                claim_id,
                f"{adds} debt of {out.fig(floating)} adds {out.fig(gross)} of annual cash interest "
                f"before any hedge; interest coverage after the shock is {out.ref(cov_after)}, and "
                f"no change is stated because coverage at base is not meaningful: [{cov}].",
                [floating, gross, cov_after, cov],
            )


def _fx_claim(out: _Claims, i: MacroFxInputs, s: Sensitivity) -> None:
    foreign, debt_after = "T2F.2.r05.value", "T2F.4.r01.debt_after"
    ebitda_change, lev_after = "T2F.4.r01.ebitda_change", "T2F.4.r01.lev_after"
    share_stated = i.foreign_ebitda_share is not None
    if s.fx[0].debt_after.state == "known":
        if share_stated:  # ruling E1: foreign debt known, share known
            out.add(
                "CP-2E-FX-01",
                f"The debt in a foreign currency is {out.fig(foreign)}, so the first currency move "
                f"leaves total debt at {out.fig(debt_after)}, changes EBITDA by "
                f"{out.fig(ebitda_change)} and leaves total leverage at {out.ref(lev_after)}.",
                [foreign, debt_after, ebitda_change, lev_after],
            )
        else:
            out.add(
                "CP-2E-FX-01",
                f"The debt in a foreign currency is {out.fig(foreign)}, so the first currency move "
                f"leaves total debt at {out.fig(debt_after)}; the effect on EBITDA is not "
                f"calculated: [{ebitda_change}] needs the share of earnings in other currencies, "
                "which no source states.",
                [foreign, debt_after, ebitda_change],
            )
        return
    # ruling E4a: the currency stated without a facility balance needs the balance
    needs = "the currency of the debt" if i.debt_currency is None else "the facility balance"
    if share_stated:  # ruling E1: foreign debt missing, share known
        out.add(
            "CP-2E-FX-01",
            f"The first currency move changes EBITDA by {out.fig(ebitda_change)}; the currency "
            f"effect on the debt is not calculated: [{foreign}] needs {needs}, which the pack "
            "does not state.",
            [ebitda_change, foreign],
        )
    else:
        out.add(
            "CP-2E-FX-01",
            f"The currency effect on the debt is not calculated: [{foreign}] needs {needs}, which "
            "the pack does not state.",
            [foreign],
        )


def _hedge_claim(out: _Claims, i: MacroFxInputs, s: Sensitivity) -> None:
    net, first = "T2F.3.r01.net", s.rate[0]
    if first.net.state == "known":
        text = (
            f"After the analyst hedge assumption the first rate shock adds {out.fig(net)} of "
            "annual cash interest."
        )
    elif i.hedge_ratio is None:
        text = (
            f"The effect of the first rate shock after hedges is not calculated: [{net}] needs a "
            "hedge ratio that no source states."
        )
    else:  # ruling E4b: a hedge ratio is stated, the added interest before hedges is missing
        text = (
            f"The effect of the first rate shock after hedges is not calculated: [{net}] "
            f"{_gross_needs(first.gross)}."
        )
    out.add("CP-2E-HEDGE-01", text, [net])


def _claims(i: MacroFxInputs, s: Sensitivity, tables: Sequence[Table]) -> tuple[ClaimText, ...]:
    out = _Claims(tables)
    _rate_claims(out, s)
    _fx_claim(out, i, s)
    _hedge_claim(out, i, s)
    out.claims.append(ClaimText("CP-2E-VIEW-01", i.summary, (), ()))
    return tuple(out.claims)


def compute(inputs: MacroFxInputs) -> MacroFxResult:
    """Tables T2F.1 to T2F.9, claims and own limitations of one validated submission."""
    i = inputs
    s = derive_sensitivity(
        operands=operands_of(i),
        rate_shocks_bp=i.rate_shocks_bp,
        fx_shocks=i.fx_shocks,
        hedge_ratio=i.hedge_ratio,
    )
    c = _cites_of(i)
    ccy = i.reporting_currency.code  # every MILLIONS fact carries the quoted reporting currency
    own = own_limitations(i)
    two = (("value", "Value"), ("convention", "Convention"))
    tables = (
        _table("T2F.1", "Sourced operands", "Operand", (("value", "Value"), ("basis", "Basis")),
               _t2f1(i, c), ccy),
        _table("T2F.2", "Baseline exposure", "Measure", two, _t2f2(s, c), ccy),
        _table("T2F.3", "Interest rate shock", "Shock", _T2F3_COLUMNS, _t2f3(s, c), ccy),
        _table("T2F.4", "Currency shock", "Shock", _T2F4_COLUMNS, _t2f4(s, c), ccy),
        _table("T2F.5", "Hedging", "Item", two, _t2f5(i, s, c), ccy),
        _table("T2F.6", "Assessments", "Section",
               (("category", "Category"), ("assessment", "Assessment")), _t2f6(i), ccy),
        _table("T2F.7", "Missing inputs", "Input",
               (("affected", "Not calculated"), ("reason", "Reason")), _t2f7(i), ccy),
        _table("T2F.8", "Evidence", "Page", (("source", "Source"), ("locator", "Locator")),
               _t2f8(i), ccy),
        _table("T2F.9", "Limitations", "Limitation", (("text", "Limitation"),),
               [(f"r{n:02d}", f"Limitation {n}", [_txt(t)]) for n, t in enumerate(own, 1)], ccy),
    )  # fmt: skip
    return MacroFxResult(
        sensitivity=s, tables=tables, claims=_claims(i, s, tables), limitations=own
    )
