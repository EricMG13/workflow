"""CP-2G (forward credit model): the module's pure calculation (Stage 1).

Lease: docs/CP2G-OWNER-LEASE.md. From the CP-1 twelve-month base, seven analyst driver paths,
the CP-2A scenario that defines the downside and CP-2A's break register, Python computes a
three-year annual path for a base and a downside case (revenue, EBITDA, cash interest, free cash
flow, debt and cash roll-forward, accessible liquidity, leverage, coverage, FCF to debt), the
first year each break test is met and the leverage trajectory, and composes tables T2H.1-T2H.9,
the three reference tables, the claims and the own limitations.

Missing is never 0: every value is known, missing (with its root reason) or not applicable. All
sums and products run in the 38-digit half-even context with the Inexact trap (exact), each ratio
is one division in that context (the correctly rounded rational). Wording the lease and the
oracle leave open is LEAD's round 5 rulings G-1 to G-9 (docs/rulings/2026-10-28-stage1.md).

The Stage 1 core does no I/O and touches no store, host, session or renderer. The Stage 2
section at the end connects it (G1-X protocol section 2): one store adapter (`_inputs`) for
submit, probe and view, the step validator, the exact `read_inputs` view and the readers.
"""

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, fields, replace
from decimal import Decimal, Inexact, localcontext
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError

from deploy_vii import prose
from deploy_vii.business_context import (
    Category,
    Confidence,
    Severity,
    prohibited_issues,
    referencable,
    spelled,
)
from deploy_vii.contracts import (
    Citation,
    Contract,
    Fact,
    Hash,
    Input,
    InputStatus,
    Module,
    ReportTable,
    Run,
    RunText,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.contracts import Claim as ModuleClaim
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepValidation,
    bounded_issues,
    clipped,
    current_inputs,
    inherited_limitations,
)
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import Submitted
from deploy_vii.model._cells import CONTEXT
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners.blank import is_blank, one_per_page
from deploy_workflow.owners.cp1a import probe_one_step

MODULE_ID = "CP-2G"
SCHEMA_VERSION = "forward-credit-model/1"

# --- arithmetic contexts (lease "Decimal composer"; L7) --------------------------------------
_RATIO = CONTEXT.copy()  # 38 digits, ROUND_HALF_EVEN: one division of exact decimals
_EXACT = CONTEXT.copy()  # the same context with the Inexact trap: a rounded sum or product raises
_EXACT.traps[Inexact] = True

# --- periods (fixed by the lease: the CP-1 LTM column and the three fiscal years after it) ----
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
BASE_YEAR = 2025
YEARS = (BASE_YEAR + 1, BASE_YEAR + 2, BASE_YEAR + 3)
FY = tuple(f"FY{y}" for y in YEARS)
FY_PERIOD = tuple(f"FY{y}: {y}-01-01 to {y}-12-31" for y in YEARS)
FY_SPAN_PERIOD = f"{FY[0]}-{FY[-1]}: {YEARS[0]}-01-01 to {YEARS[-1]}-12-31"
NOT_REACHED = f"Not reached by {FY[-1]}"
NOT_CALCULABLE = "Not calculable"

# --- the submission schema (lease "Submission schema"; every field required) -----------------
GROWTH_PATTERN = r"^-?(0|1|0\.\d{1,4}|1\.0{1,4})$"
FRACTION_PATTERN = r"^(0|1|0\.\d{1,4}|1\.0{1,4})$"
AMOUNT_PATTERN = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
NOT_ASSESSED = "not assessed"
LIQUIDITY_PATTERN = r"^([0-9]{1,6}(\.[0-9]{1,4})?|not assessed)$"
SCENARIO_PATTERN = r"^s[0-9]{2}$"
BREAK_PATTERN = r"^b[0-9]{2}$"

Growth = Annotated[str, Field(pattern=GROWTH_PATTERN)]
Share = Annotated[str, Field(pattern=FRACTION_PATTERN)]
Amount = Annotated[str, Field(pattern=AMOUNT_PATTERN)]
Metric = Literal["total_leverage", "net_leverage", "interest_coverage"]


class GrowthDriver(Contract):
    values: tuple[Growth, Growth, Growth]  # FY2026, FY2027, FY2028
    category: Category
    rationale: str
    limitation: str | None


class FractionDriver(Contract):
    values: tuple[Share, Share, Share]
    category: Category
    rationale: str
    limitation: str | None


class AmountDriver(Contract):
    values: tuple[Amount, Amount, Amount]
    category: Category
    rationale: str
    limitation: str | None


class BaseDrivers(Contract):
    revenue_growth: GrowthDriver
    ebitda_margin: FractionDriver
    capex_pct_revenue: FractionDriver
    tax_wc_pct_revenue: FractionDriver
    interest_rate: FractionDriver
    dividends: AmountDriver
    debt_repayment: AmountDriver


class Downside(Contract):
    scenario: Annotated[str, Field(pattern=SCENARIO_PATTERN)]  # a CP-2A T2B.1 row id
    rationale: str
    limitation: str | None


class BreakMetric(Contract):
    break_id: Annotated[str, Field(pattern=BREAK_PATTERN)]
    metric: Metric


class MinimumLiquidity(Contract):
    amount: Annotated[str, Field(pattern=LIQUIDITY_PATTERN)]
    rationale: str


class Assessment(Contract):
    rationale: str
    category: Category
    confidence: Confidence
    limitation: str | None


class SynthesisGap(Contract):
    """CP-2G's own gap row: `cp2_synthesis.SynthesisGap` without `cp1a_refs` (lease)."""

    gap: str
    why_it_matters: str
    affected_analysis: str
    severity: Severity
    action: str


class ForwardSubmission(Contract):
    base_drivers: BaseDrivers
    downside: Downside
    break_metrics: tuple[BreakMetric, ...] = Field(max_length=8)  # no default: still required
    minimum_liquidity: MinimumLiquidity
    assessment: Assessment
    gaps: tuple[SynthesisGap, ...]


DRIVERS = (
    "revenue_growth",
    "ebitda_margin",
    "capex_pct_revenue",
    "tax_wc_pct_revenue",
    "interest_rate",
    "dividends",
    "debt_repayment",
)
DRIVER_LABEL = {
    "revenue_growth": "Revenue growth",
    "ebitda_margin": "EBITDA margin",
    "capex_pct_revenue": "Capital expenditure, share of revenue",
    "tax_wc_pct_revenue": "Cash taxes and working capital outflow, share of revenue",
    "interest_rate": "Cash interest rate on opening debt",
    "dividends": "Distributions to shareholders (outflow)",
    "debt_repayment": "Debt repayment (outflow)",
}
UnitKind = Literal["amount", "percent", "multiple"]
DRIVER_UNIT: Mapping[str, UnitKind] = {
    "revenue_growth": "percent",
    "ebitda_margin": "percent",
    "capex_pct_revenue": "percent",
    "tax_wc_pct_revenue": "percent",
    "interest_rate": "percent",
    "dividends": "amount",
    "debt_repayment": "amount",
}


def _driver(base: BaseDrivers, name: str) -> GrowthDriver | FractionDriver | AmountDriver:
    drivers: dict[str, GrowthDriver | FractionDriver | AmountDriver] = {
        "revenue_growth": base.revenue_growth,
        "ebitda_margin": base.ebitda_margin,
        "capex_pct_revenue": base.capex_pct_revenue,
        "tax_wc_pct_revenue": base.tax_wc_pct_revenue,
        "interest_rate": base.interest_rate,
        "dividends": base.dividends,
        "debt_repayment": base.debt_repayment,
    }
    return drivers[name]


# --- values ----------------------------------------------------------------------------------
NC_EBITDA = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_INTEREST = "Not calculable: cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_DEBT = "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_LIQUIDITY = "Not calculable: minimum liquidity was not assessed"
NC_REVENUE = "Not calculable: revenue is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"  # G-4


def _exact(x: Decimal) -> Decimal:
    """The canonical stored form: the same value, trailing zeros dropped, no exponent and no
    negative zero (so equal inputs always give byte-equal facts)."""
    if x == 0:
        return Decimal(0)
    with localcontext() as ctx:
        ctx.prec = 80  # normalize() rounds to the context: keep every digit the value has
        return Decimal(format(x.normalize(), "f"))


@dataclass(frozen=True)
class Val:
    """A computed value: an exact amount, or None with the root reason it is missing."""

    amount: Decimal | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if (self.amount is None) == (self.reason is None):
            raise ValueError("a value carries an amount or a reason, never both or neither")


def _known(x: Decimal) -> Val:
    return Val(_exact(x))


def _apply(fn: Callable[..., Decimal], *args: Val) -> Val:
    """fn over the amounts in the exact context; the first missing operand (formula order) wins."""
    for a in args:
        if a.amount is None:
            return a
    with localcontext(_EXACT):
        return _known(fn(*(a.amount for a in args)))


@contextmanager
def _exact_digits(operation: str) -> Iterator[None]:
    """Round 9 Info: a sum or product of an operation that needs more than 38 significant
    digits (the `_EXACT` Inexact trap) fails closed with a ValueError naming the operation.
    Only decimal.Inexact is caught."""
    try:
        yield
    except Inexact as error:
        raise ValueError(f"CP-2G: {operation} needs more than 38 significant digits") from error


def _ratio(num: Val, den: Val, non_positive: str) -> Val:
    """num / den: one division; a missing operand propagates (numerator first), den <= 0 is
    missing with `non_positive`."""
    if num.amount is None:
        return num
    if den.amount is None:
        return den
    if den.amount <= 0:
        return Val(None, non_positive)
    with localcontext(_RATIO):
        return _known(num.amount / den.amount)


# --- the CP-1 base (manifest.json fact_selection_rule) ---------------------------------------
CP1_METRICS = (
    "revenue",
    "ebitda",
    "cash_interest",
    "cash_taxes",
    "working_capital_change",
    "capex",
    "fcf",
    "total_debt",
    "cash_closing",
    "undrawn_rcf",
    "ebitda_margin",
    "capex_to_revenue",
    "total_leverage_reported",
    "net_leverage_reported",
    "interest_coverage_reported",
    "fcf_to_debt",
)
OPERAND_METRIC = {
    "revenue": "revenue",
    "ebitda": "ebitda",
    "interest": "cash_interest",
    "taxes": "cash_taxes",
    "wc": "working_capital_change",
    "capex": "capex",
    "fcf": "fcf",
    "debt": "total_debt",
    "cash": "cash_closing",
    "undrawn": "undrawn_rcf",
}
_OUTFLOWS = frozenset({"interest", "taxes", "wc", "capex"})  # CP-1 stores them negative
# The name of each base operand in the missing-operand frames (cash pinned by
# fixture_cash_missing, the rest LEAD ruling G-1).
_OPERAND_WORDS = {
    "revenue": "revenue",
    "ebitda": "EBITDA",
    "interest": "cash interest",
    "taxes": "cash taxes",
    "wc": "working capital change",
    "capex": "capital expenditure",
    "fcf": "free cash flow",
    "debt": "total debt",
    "undrawn": "undrawn revolver",
    "cash": "cash and cash equivalents",
}


def select_cp1(facts: Iterable[Fact]) -> dict[str, Fact]:
    """metric -> the unique T4.10 fact labelled `<LTM column> · <metric>`; zero or several fail."""
    facts = tuple(facts)
    out: dict[str, Fact] = {}
    for metric in CP1_METRICS:
        label = f"{LTM_COLUMN} · {metric}"
        found = [f for f in facts if f.table_id == "T4.10" and f.label == label]
        if len(found) != 1:
            raise ValueError(
                f"CP-1 needs exactly one T4.10 fact labelled {label}, found {len(found)}"
            )
        out[metric] = found[0]
    return out


def _usd_millions(name: str, fact: Fact) -> None:
    """Lease "All amounts USD, unit MILLIONS": another upstream book fails closed (an invariant;
    carrying the book's unit through would be a lease change). `name` is `CP-1 <metric>` (M2) or
    `CP-1D <label>` (round 11 Q12)."""
    if (fact.currency, fact.unit, fact.scale) != ("USD", "MILLIONS", Decimal(1000000)):
        raise ValueError(  # round 9 wording
            f"CP-2G: {name} must be USD MILLIONS at scale 1000000, not "
            f"{fact.currency} {fact.unit} at scale {fact.scale}"
        )


def _operand_reason(key: str) -> str:
    return f"Not calculable: base {_OPERAND_WORDS[key]} is missing in CP-1 ({LTM_PERIOD})"


@dataclass(frozen=True)
class Operands:
    """The CP-1 base in millions; outflows as positive magnitudes (lease "Base operands")."""

    revenue: Val
    ebitda: Val
    interest: Val
    taxes: Val
    wc: Val
    capex: Val
    fcf: Val
    debt: Val
    cash: Val
    undrawn: Val

    @classmethod
    def from_cp1(cls, cp1_facts: Iterable[Fact]) -> "Operands":
        cp1 = select_cp1(cp1_facts)
        vals: dict[str, Val] = {}
        for key, metric in OPERAND_METRIC.items():
            fact = cp1[metric]
            if fact.status != "known" or fact.amount is None:
                vals[key] = Val(None, _operand_reason(key))
            else:
                _usd_millions(f"CP-1 {metric}", fact)
                vals[key] = _known(-fact.amount if key in _OUTFLOWS else fact.amount)
        return cls(**vals)

    def items(self) -> tuple[tuple[str, Val], ...]:
        return tuple((key, getattr(self, key)) for key in OPERAND_METRIC)


# --- the forward engine (lease "Engine") -----------------------------------------------------
Triple = tuple[Decimal, Decimal, Decimal]


@dataclass(frozen=True)
class Drivers:
    """The analyst's base-case driver values per forecast year (FY2026, FY2027, FY2028)."""

    revenue_growth: Triple
    ebitda_margin: Triple
    capex_pct_revenue: Triple
    tax_wc_pct_revenue: Triple
    interest_rate: Triple
    dividends: Triple
    debt_repayment: Triple

    @classmethod
    def from_submission(cls, base: BaseDrivers) -> "Drivers":
        def triple(name: str) -> Triple:
            a, b, c = _driver(base, name).values
            return Decimal(a), Decimal(b), Decimal(c)

        return cls(**{name: triple(name) for name in DRIVERS})


@dataclass(frozen=True)
class Year:
    revenue: Val
    ebitda: Val
    interest: Val
    tax_wc: Val
    capex: Val
    cfo: Val  # cash flow after interest, taxes and working capital
    fcf: Val
    opening_debt: Val
    repayment: Val
    closing_debt: Val
    opening_cash: Val
    dividends: Val
    closing_cash: Val
    undrawn: Val
    liquidity: Val
    total_leverage: Val
    net_debt: Val
    net_leverage: Val
    coverage: Val
    fcf_to_debt: Val


@dataclass(frozen=True)
class CaseForecast:
    years: tuple[Year, Year, Year]


def _year(
    opening: tuple[Val, Val, Val],
    drivers: Drivers,
    t: int,
    shock: tuple[Decimal, Decimal] | None,
    undrawn: Val,
) -> Year:
    """One forecast year from the prior revenue, closing debt and closing cash."""
    revenue, debt, cash = opening
    g, m = drivers.revenue_growth[t], drivers.ebitda_margin[t]
    c, w = drivers.capex_pct_revenue[t], drivers.tax_wc_pct_revenue[t]
    rate, div, rep = drivers.interest_rate[t], drivers.dividends[t], drivers.debt_repayment[t]
    s, k = (Decimal(0), Decimal(0)) if shock is None else shock  # the base case: no shock (exact)
    rev = _apply(lambda r: r * (1 + g), revenue)
    ebitda = _apply(lambda r: r * m * (1 - s), rev)
    interest = _apply(lambda d: d * (rate * (1 + k)), debt)
    tax_wc = _apply(lambda r: r * w, rev)
    capex = _apply(lambda r: r * c, rev)
    cfo = _apply(lambda e, i, x: e - i - x, ebitda, interest, tax_wc)
    fcf = _apply(lambda a, b: a - b, cfo, capex)
    closing_debt = _apply(lambda d: d - rep, debt)
    closing_cash = _apply(lambda o, f: o + f - div - rep, cash, fcf)
    net_debt = _apply(lambda d, cc: d - cc, closing_debt, closing_cash)
    return Year(
        revenue=rev,
        ebitda=ebitda,
        interest=interest,
        tax_wc=tax_wc,
        capex=capex,
        cfo=cfo,
        fcf=fcf,
        opening_debt=debt,
        repayment=_known(rep),
        closing_debt=closing_debt,
        opening_cash=cash,
        dividends=_known(div),
        closing_cash=closing_cash,
        undrawn=undrawn,
        liquidity=_apply(lambda cc, u: cc + u, closing_cash, undrawn),
        total_leverage=_ratio(closing_debt, ebitda, NC_EBITDA),
        net_debt=net_debt,
        net_leverage=_ratio(net_debt, ebitda, NC_EBITDA),
        coverage=_ratio(ebitda, interest, NC_INTEREST),
        fcf_to_debt=_ratio(fcf, closing_debt, NC_DEBT),
    )


def forecast(
    *, operands: Operands, drivers: Drivers, shock: tuple[Decimal, Decimal] | None
) -> CaseForecast:
    """One case's three years. `shock` is None (base) or CP-2A's (decline, increase), applied
    to every year: EBITDA x (1 - decline), rate x (1 + increase), everything else held."""
    opening = (operands.revenue, operands.debt, operands.cash)
    years: list[Year] = []
    with _exact_digits("the base case forecast" if shock is None else "the downside case forecast"):
        for t in range(3):
            y = _year(opening, drivers, t, shock, operands.undrawn)
            years.append(y)
            opening = (y.revenue, y.closing_debt, y.closing_cash)
    return CaseForecast(years=(years[0], years[1], years[2]))


# --- break tests (lease "CP-2A consumption" and "First-break result") -------------------------
BreakKind = Literal["fcf", "coverage", "total_leverage", "net_leverage", "liquidity"]
DEF_FCF = "Free cash flow at or below zero"
DEF_COVERAGE = "EBITDA no longer covers cash interest"
_DEFINITION_KIND: Mapping[str, BreakKind] = {DEF_FCF: "fcf", DEF_COVERAGE: "coverage"}
_METRIC_KIND: Mapping[str, BreakKind] = {
    "total_leverage": "total_leverage",
    "net_leverage": "net_leverage",
    "interest_coverage": "coverage",
}
KIND_METRIC: Mapping[BreakKind, str] = {
    "fcf": "Free cash flow",
    "coverage": "Interest coverage",
    "total_leverage": "Total leverage",
    "net_leverage": "Net leverage",
    "liquidity": "Accessible liquidity",
}
LIQUIDITY_TEST = "Accessible liquidity below the minimum liquidity"


def _tested(kind: BreakKind, year: Year) -> Val:
    return {
        "fcf": year.fcf,
        "coverage": year.coverage,
        "total_leverage": year.total_leverage,
        "net_leverage": year.net_leverage,
        "liquidity": year.liquidity,
    }[kind]


@dataclass(frozen=True)
class BreakTest:
    row: str
    kind: BreakKind | None  # None: CP-2G maps no metric to CP-2A's wording (ruling G-7)
    test: str
    level: Decimal | None
    level_reason: str | None  # why the level is unknown (the root reason of every result)


@dataclass(frozen=True)
class BreakResult:
    row: str
    values: tuple[Decimal | None, ...]
    hits: tuple[bool | None, ...]  # None: not calculable that year
    first: str  # FY20xx, "Not reached by FY2028" or "Not calculable"
    reason: str | None  # the root reason when first is "Not calculable"


def first_result(hits: Sequence[bool | None]) -> str:
    """The first year met; a year not calculable before it, or no year met while one is not
    calculable, makes the answer Not calculable; none met and all calculable is Not reached."""
    unknown = False
    for t, hit in enumerate(hits):
        if hit is None:
            unknown = True
        elif hit:
            return NOT_CALCULABLE if unknown else FY[t]
    return NOT_CALCULABLE if unknown else NOT_REACHED


def _hit(kind: BreakKind, value: Decimal, level: Decimal) -> bool:
    if kind in ("fcf", "coverage"):
        return value <= level
    if kind == "liquidity":
        return value < level
    return value >= level


def test_breaks(*, tests: Sequence[BreakTest], forecast: CaseForecast) -> tuple[BreakResult, ...]:
    out: list[BreakResult] = []
    for test in tests:
        kind = test.kind
        vals = [
            Val(None, test.level_reason) if kind is None else _tested(kind, y)
            for y in forecast.years
        ]
        hits: list[bool | None] = []
        for v in vals:
            if kind is None or v.amount is None or test.level is None:
                hits.append(None)
            else:
                hits.append(_hit(kind, v.amount, test.level))
        first = first_result(hits)
        reason = None
        if first == NOT_CALCULABLE:
            t0 = hits.index(None)
            reason = test.level_reason or vals[t0].reason
            if reason is None:  # a level of None must come with its reason
                raise ValueError(f"CP-2G: break {test.row} is not calculable without a reason")
        out.append(BreakResult(test.row, tuple(v.amount for v in vals), tuple(hits), first, reason))
    return tuple(out)


def break_decline(*, kind: BreakKind, level: Decimal, operands: Operands) -> Fraction | None:
    """The EBITDA decline that reaches `level` on the CP-1 base (the CP-2A recipe), exact; None
    when an operand is missing or the denominator (E, or L x E for leverage) is not positive."""
    e, i, d, c = (
        None if v.amount is None else Fraction(v.amount)
        for v in (operands.ebitda, operands.interest, operands.debt, operands.cash)
    )
    lvl = Fraction(level)
    if kind == "coverage":
        return None if e is None or e <= 0 or i is None else (e - lvl * i) / e
    if kind not in ("total_leverage", "net_leverage"):
        raise ValueError(f"CP-2G: break_decline has no recipe for {kind}")
    debt = d if kind == "total_leverage" else None if d is None or c is None else d - c
    if e is None or e <= 0 or lvl <= 0 or debt is None:
        return None
    return (lvl * e - debt) / (lvl * e)


def _round38(x: Fraction) -> Decimal:
    with localcontext(_RATIO):
        return _exact(Decimal(x.numerator) / Decimal(x.denominator))


# --- the inputs (Stage 2 binds them from the settled heads) ----------------------------------
@dataclass(frozen=True)
class Cp2aScenario:
    row: str
    name: str
    decline: Fact  # T2B.1.<row>.ebitda_decline
    increase: Fact  # T2B.1.<row>.interest_increase


@dataclass(frozen=True)
class Cp2aBreak:
    row: str
    origin: str
    test: str
    level: Fact  # T2B.6.<row>.level
    required_decline: Fact  # T2B.6.<row>.required_decline
    outcome: str


@dataclass(frozen=True)
class Cp2aHead:
    base_period: str
    scenarios: tuple[Cp2aScenario, ...]
    breaks: tuple[Cp2aBreak, ...]


Cp1dState = Literal["bound", "unbound", "blocked"]
CP1D_IDS = (
    "T1D.3.supported.value",
    "T1D.6.supported.total_leverage",
    "T1D.6.supported.net_leverage",
)


@dataclass(frozen=True)
class Cp1dHead:
    """The optional CP-1D input: `status` None when CP-1D is not requested."""

    status: InputStatus | None
    supported: Fact | None = None  # T1D.3.supported.value
    total_leverage: Fact | None = None  # T1D.6.supported.total_leverage
    net_leverage: Fact | None = None  # T1D.6.supported.net_leverage

    @property
    def state(self) -> Cp1dState:
        if self.status is None:
            return "unbound"
        return "blocked" if self.status == "blocked" else "bound"

    def facts(self) -> tuple[Fact, Fact, Fact] | None:
        if self.state != "bound":
            return None
        if self.supported is None or self.total_leverage is None or self.net_leverage is None:
            raise ValueError("CP-2G: a bound CP-1D head supplies its three supported facts")
        return self.supported, self.total_leverage, self.net_leverage


@dataclass(frozen=True)
class ForwardContext:
    """Everything the step reads besides the submission (lease D3 pins)."""

    cp1_facts: tuple[Fact, ...]  # CP-1 facts; the T4.10 LTM column is selected from them
    cp2a: Cp2aHead
    cp1d: Cp1dHead
    cp1_status: InputStatus
    cp2a_status: InputStatus
    names: tuple[str, ...] = ()  # supplied names whose digits are not figures (issuer name)
    cp2d_status: InputStatus | None = None  # a declared optional edge this version never reads

    def prose_facts(self) -> tuple[Fact, ...]:
        """The upstream facts prose may reference: CP-1 and, when bound, CP-1D facts that carry
        a citation or a calculation."""
        cp1d = self.cp1d.facts() or ()
        return referencable((*select_cp1(self.cp1_facts).values(), *cp1d))


@dataclass(frozen=True)
class ForwardInputs:
    context: ForwardContext
    submission: ForwardSubmission


# --- validation (lease "Refusals") -----------------------------------------------------------
HIGH_ISSUE = (
    "assessment.confidence: High is not allowed: driver values are uncited analyst assumptions"
)
PROBABILITY_PHRASES = (
    "probability-weighted",
    "probability weighted",
    "probability of",
    "weighted by probability",
    "expected value",
    "likelihood-weighted",
)
UNVERIFIED_PERIOD = (
    "CP-2A stressed a different base period from the twelve-month base, "
    "so its required decline is not comparable"
)
UNVERIFIED_CP2A = "CP-2A has no known level or required decline for it (missing or not applicable)"
UNVERIFIED_EBITDA = (  # ruling G-8
    f"base EBITDA is zero or negative in CP-1 for {LTM_PERIOD} (ZERO_OR_NEGATIVE_DENOMINATOR)"
)
_OPERAND_ORDER: Mapping[BreakKind, tuple[str, ...]] = {
    "total_leverage": ("ebitda", "debt"),
    "net_leverage": ("ebitda", "debt", "cash"),
    "coverage": ("ebitda", "interest"),
}


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def _run_text_issues(path: str, text: str) -> list[str]:
    """Stage 2 round 3 item 2: text built as `Claim.text` is checked with that very type
    (`RunText`, one `TypeAdapter` built once), so a malformed reference is a journaled issue and
    composition never raises after the binding write. The message never echoes the input."""
    try:
        _RUN_TEXT.validate_python(text)
    except ValidationError as error:
        found = error.errors(include_input=False, include_url=False, include_context=False)
        return [clipped((path, ": ", item["msg"])) for item in found]
    return []


def _text_issues(
    path: str, text: str, bound: Mapping[str, Fact], names: Sequence[str], *, claim: bool = False
) -> list[str]:
    """Issues of one prose field; a `prose.issues` line can quote the analyst's text, so it is
    clipped (protocol section 6). `claim`: the text becomes `Claim.text`, so when `prose.issues`
    finds nothing it is also checked as `RunText`."""
    if is_blank(text):
        return [f"{path}: empty text"]
    found = prose.issues(text, bound, names=names)
    issues = [clipped((path, ": ", issue)) for issue in found]
    if claim and not found:
        issues += _run_text_issues(path, text)
    issues.extend(prohibited_issues(path, text))
    low = text.lower()  # this core's phrase guard (ruling L11), not a semantic check
    issues.extend(
        f'{path}: prohibited conclusion (probability weighting): "{phrase}"'
        for phrase in PROBABILITY_PHRASES
        if phrase in low
    )
    return issues


def _limitation_issues(path: str, text: str | None) -> list[str]:
    """Round 11 blank text: a stated limitation of whitespace alone (round 12 B10: and `Cf`
    characters), or `""`, is empty text, in the pinned frame (V08). A limitation is optional, so None is not refused."""
    return [f"{path}: empty text"] if text is not None and is_blank(text) else []


def _is_definition(b: Cp2aBreak) -> bool:
    return b.origin == "Definition"


def _metric_check(
    b: Cp2aBreak, kind: BreakKind, operands: Operands, base_period: str
) -> tuple[bool, str | None]:
    """(reproduces, unverified cause): the analyst's metric against CP-2A's required decline.
    Causes in order: base period, CP-2A unknown, first missing operand, then (ruling G-8) the
    non-positive denominator, base EBITDA before the CP-2A level."""
    if base_period != LTM_PERIOD:
        return True, UNVERIFIED_PERIOD
    lvl, rd = b.level, b.required_decline
    if lvl.status != "known" or rd.status != "known" or lvl.amount is None or rd.amount is None:
        return True, UNVERIFIED_CP2A
    s_star = break_decline(kind=kind, level=lvl.amount, operands=operands)
    if s_star is None:
        missing = [k for k in _OPERAND_ORDER[kind] if getattr(operands, k).amount is None]
        if missing:  # the first operand in formula order names the cause
            return True, f"base {_OPERAND_WORDS[missing[0]]} is missing in CP-1 for {LTM_PERIOD}"
        e = operands.ebitda.amount
        if e is not None and e <= 0:
            return True, UNVERIFIED_EBITDA
        return (
            True,
            f"the CP-2A level of {b.row} is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)",
        )
    return _round38(s_star) == rd.amount, None


def _break_issues(metrics: Sequence[BreakMetric], cp2a: Cp2aHead, operands: Operands) -> list[str]:
    rows = {b.row: b for b in cp2a.breaks}
    issues: list[str] = []
    seen: set[str] = set()
    for i, bm in enumerate(metrics):
        b = rows.get(bm.break_id)
        where = f"break_metrics[{i}]"
        if b is None:
            issues.append(f"{where}.break_id: not a CP-2A break: {bm.break_id}")
        elif _is_definition(b):
            issues.append(
                f"{where}.break_id: {bm.break_id} is a definition break with a fixed metric"
                if b.test in _DEFINITION_KIND
                else f"{where}.break_id: {bm.break_id} is a definition break whose test CP-2G does "
                "not map; no metric can be named for it"  # round 6d (G-7)
            )
        elif bm.break_id in seen:
            issues.append(f"{where}.break_id: duplicate break {bm.break_id}")
        else:
            seen.add(bm.break_id)
            ok, _cause = _metric_check(b, _METRIC_KIND[bm.metric], operands, cp2a.base_period)
            if not ok:
                issues.append(
                    f"{where}: metric {bm.metric} does not reproduce the CP-2A required decline "
                    f"of {bm.break_id}"
                )
    issues.extend(
        f"break_metrics: no metric for CP-2A break {b.row}"
        for b in cp2a.breaks
        if not _is_definition(b) and b.row not in seen
    )
    return issues


def content_issues(inputs: ForwardInputs) -> tuple[str, ...]:
    """Content issues of a parsed submission, in the pinned order: base_drivers (canonical
    driver order), downside, break_metrics, minimum_liquidity, assessment, gaps."""
    sub, ctx = inputs.submission, inputs.context
    operands = Operands.from_cp1(ctx.cp1_facts)
    bound = prose.bind(ctx.prose_facts())
    names = ctx.names
    issues: list[str] = []
    for name in DRIVERS:
        driver = _driver(sub.base_drivers, name)
        if name == "debt_repayment" and operands.debt.amount is not None:
            cumulative = Decimal(0)
            for t, value in enumerate(driver.values):
                cumulative += Decimal(value)
                if cumulative > operands.debt.amount:
                    issues.append(
                        f"base_drivers.debt_repayment.values[{t}]: repayment exceeds the opening "
                        "debt balance"
                    )
                    break
        path = f"base_drivers.{name}.rationale"
        issues += _text_issues(path, driver.rationale, bound, names, claim=True)
        issues += _limitation_issues(f"base_drivers.{name}.limitation", driver.limitation)
    if sub.downside.scenario not in {s.row for s in ctx.cp2a.scenarios}:
        issues.append(f"downside.scenario: not a CP-2A scenario: {sub.downside.scenario}")
    issues += _text_issues("downside.rationale", sub.downside.rationale, bound, names, claim=True)
    issues += _limitation_issues("downside.limitation", sub.downside.limitation)
    issues += _break_issues(sub.break_metrics, ctx.cp2a, operands)
    issues += _text_issues(
        "minimum_liquidity.rationale", sub.minimum_liquidity.rationale, bound, names, claim=True
    )
    rationale = sub.assessment.rationale
    issues += _text_issues("assessment.rationale", rationale, bound, names, claim=True)
    issues += _limitation_issues("assessment.limitation", sub.assessment.limitation)
    if sub.assessment.confidence == "High":
        issues.append(HIGH_ISSUE)
    for i, gap in enumerate(sub.gaps):
        for key in ("gap", "why_it_matters", "affected_analysis", "action"):
            issues += _text_issues(f"gaps[{i}].{key}", getattr(gap, key), bound, names)
    return tuple(dict.fromkeys(issues))


def _parsed(payload: str) -> tuple[ForwardSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`). The schema validates the bounded document's exact re-serialisation, never the
    raw text; text `json_object` refuses keeps Pydantic's own shape issue (the frozen r14 frame),
    and is refused even if Pydantic would parse it."""
    document = json_object(payload)
    try:
        if document is None:
            ForwardSubmission.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return ForwardSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def payload_issues(payload: str, context: ForwardContext) -> tuple[str, ...]:
    """Shape issues alone (a payload that does not parse gets no content check), else the
    content issues."""
    submission, shape = _parsed(payload)
    if submission is None:
        return shape
    return content_issues(ForwardInputs(context=context, submission=submission))


def stale_issues(*, bound: Sequence[Input], current: Sequence[Input] | str) -> tuple[str, ...]:
    """Every bound upstream that changed (ruling 10), in the `cp2_synthesis._stale_issues` form.
    Returned alone, like shape issues (G-decisions): Stage 2 runs no content check on a stale
    upstream."""
    if isinstance(current, str):
        return (clipped(("Stale inputs: ", current)),)
    was = {item.input_id: item for item in bound}
    now = {item.input_id: item for item in current}

    def state(item: Input | None) -> str:
        return "absent" if item is None else f"{item.status} {item.sha256[:12]}"

    return tuple(
        f"Stale input {key}: bound {state(was.get(key))}, current {state(now.get(key))}"
        for key in dict.fromkeys((*was, *now))
        if was.get(key) != now.get(key)
    )


# --- cells, tables, references, claims -------------------------------------------------------
_UNIT: Mapping[UnitKind, str] = {"amount": "MILLIONS", "multiple": "MULTIPLE", "percent": "PERCENT"}
_UNIT_KIND: Mapping[str, UnitKind] = {unit: kind for kind, unit in _UNIT.items()}
_MILLIONS = Decimal(1000000)
ValueClass = Literal["source", "normalized", "calculated", "analyst_judgment"]
CellStatus = Literal["known", "missing", "not_applicable"]


@dataclass(frozen=True)
class Cell:
    """One table cell: the product Fact it settles as, its lineage and its display spelling."""

    fact: Fact
    derives_from: tuple[str, ...]
    shown: str | None  # report_view.fact_spelling of a known fact; None while unsettled


@dataclass(frozen=True)
class Row:
    row_id: str
    label: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Reference:
    row_id: str
    label: str
    fact: Fact  # the upstream fact, verbatim


@dataclass(frozen=True)
class RefTable:
    table_id: str
    title: str
    row_header: str
    rows: tuple[Reference, ...]
    note: str | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str  # run text: {fact_id|unit} figures and [fact_id] chips
    limitation: str | None
    references: tuple[str, ...]  # upstream fact ids the analyst's text names as figures


@dataclass(frozen=True)
class BreakRow:
    row: str
    kind: BreakKind | None
    test: str
    base: BreakResult
    down: BreakResult


@dataclass(frozen=True)
class Trajectory:
    change: Decimal | None
    peak: Decimal | None
    peak_year: str | None


@dataclass(frozen=True)
class ForwardResult:
    operands: Operands
    forecast: Mapping[str, CaseForecast]  # "base", "down"
    cells: tuple[Cell, ...]
    tables: tuple[Table, ...]
    references: tuple[RefTable, RefTable, RefTable]  # cp1, cp2a, cp1d
    claims: tuple[Claim, ...]
    own_limitations: tuple[str, ...]
    break_tests: tuple[BreakRow, ...]
    trajectory: Mapping[str, Trajectory]


TABLES = {
    "T2H.1": "Upstream register",
    "T2H.2": "Historical-to-base bridge",
    "T2H.3": "Assumption register",
    "T2H.4": "Operating forecast",
    "T2H.5": "Debt and cash roll-forward",
    "T2H.6": "Credit metrics",
    "T2H.7": "Break-point timing",
    "T2H.8": "Deleveraging path",
    "T2H.9": "Gaps ledger",
}
CASES = ("base", "down")
CASE_LABEL = {"base": "Base", "down": "Downside"}
ROW_PREFIX = {"base": "b", "down": "d"}
A25 = "a25"
FORECAST_LIMITATION = "Forecast on analyst-assumed drivers"
LIQ_HEADROOM_FY25 = (
    "Minimum liquidity is a forecast-year assumption and is not applied to the FY2025 actual"
)
CP1D_WHY = {
    "unbound": "CP-1D (earnings quality) is not part of this run",
    "blocked": "CP-1D is blocked, so no supported earnings were settled",
}


class _Book:
    """The module's cells in table, row and field order, and each table's rows."""

    def __init__(self) -> None:
        self.cells: list[Cell] = []
        self.by_id: dict[str, Cell] = {}
        self.rows: dict[str, list[Row]] = {t: [] for t in TABLES}

    def _add(self, fact: Fact, derives: Sequence[str]) -> None:
        if fact.fact_id in self.by_id:
            raise ValueError(f"CP-2G: duplicate fact {fact.fact_id}")
        shown = fact_spelling(fact, None)[2] if fact.status == "known" else None
        cell = Cell(fact=fact, derives_from=tuple(derives), shown=shown)
        self.cells.append(cell)
        self.by_id[fact.fact_id] = cell

    @staticmethod
    def _id(table: str, row: str, field: str) -> str:
        return f"{table}.{row}.{field}"

    def num(
        self,
        at: tuple[str, str, str],
        label: str,
        value: Decimal,
        unit: UnitKind,
        formula: str,
        *,
        value_class: ValueClass | None = "calculated",
        period: str = LTM_PERIOD,
        derives: Sequence[str] = (),
        keep_lineage: bool = False,
    ) -> None:
        table, row, field = at
        fid = self._id(table, row, field)
        calculated = value_class == "calculated"
        amount_unit = unit == "amount"
        fact = Fact(
            fact_id=fid,
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            amount=_exact(value),
            unit=_UNIT[unit],
            currency="USD" if amount_unit else None,
            scale=_MILLIONS if amount_unit else Decimal(1),
            decimals=2 if amount_unit else None,
            period=period,
            calculation_id=f"calc:{fid}" if calculated else None,
            value_class=value_class,
            formula=formula,
        )
        self._add(fact, derives if calculated or keep_lineage else ())

    def gap(
        self,
        at: tuple[str, str, str],
        label: str,
        unit: UnitKind,
        reason: str,
        *,
        status: CellStatus = "missing",
        period: str = LTM_PERIOD,
    ) -> None:
        table, row, field = at
        fact = Fact(
            fact_id=self._id(table, row, field),
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            status=status,
            unit=_UNIT[unit],
            period=period,
            limitation=reason,
        )
        self._add(fact, ())

    def value(
        self,
        at: tuple[str, str, str],
        label: str,
        v: Val,
        unit: UnitKind,
        formula: str,
        derives: Sequence[str],
        *,
        period: str = LTM_PERIOD,
    ) -> None:
        if v.amount is None:
            assert v.reason is not None
            self.gap(at, label, unit, v.reason, period=period)
        else:
            self.num(at, label, v.amount, unit, formula, period=period, derives=derives)

    def text(
        self,
        at: tuple[str, str, str],
        label: str,
        value: str,
        *,
        value_class: ValueClass | None = None,
        derives: Sequence[str] = (),
    ) -> None:
        table, row, field = at
        fact = Fact(
            fact_id=self._id(table, row, field),
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            text=value,
            value_class=value_class,
        )
        self._add(fact, derives)

    def missing_text(self, at: tuple[str, str, str], label: str, reason: str) -> None:
        """A text cell that cannot be settled: missing with its root reason, never a known text."""
        table, row, field = at
        fact = Fact(
            fact_id=self._id(table, row, field),
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            status="missing",
            limitation=reason,
        )
        self._add(fact, ())

    def row(self, table: str, row_id: str, label: str, fields: Sequence[str]) -> None:
        ids = tuple(self._id(table, row_id, f) for f in fields)
        for fid in ids:
            if fid not in self.by_id:
                raise ValueError(f"CP-2G: row {table}.{row_id} names no fact {fid}")
        self.rows[table].append(Row(row_id=row_id, label=label, fact_ids=ids))

    def status(self, fact_id: str) -> str:
        return self.by_id[fact_id].fact.status


@dataclass(frozen=True)
class _Run:
    """What the composer reads, resolved once."""

    sub: ForwardSubmission
    ctx: ForwardContext
    cp1: Mapping[str, Fact]
    ops: Operands
    drivers: Drivers
    scenario: Cp2aScenario
    shock_reason: str | None  # why the downside is not calculated (ruling G-5)
    path: Mapping[str, CaseForecast]
    min_liq: Decimal | None
    cp1d: tuple[Fact, Fact, Fact] | None
    cp1d_why: str | None
    supported: Val  # CP-1D supported EBITDA as an operand of the comparisons (ruling G-9)
    tl0: Val
    a25_fcf: Val
    bound: Mapping[str, Fact]  # the validator's reference map (prose.bind of the prose facts)


def _a25(ops: Operands) -> tuple[Val, Val]:
    """FY2025 cash flow after interest, taxes and working capital, and free cash flow."""
    with _exact_digits("the FY2025 cash flow"):
        cfo = _apply(lambda e, i, x, w: e - i - x - w, ops.ebitda, ops.interest, ops.taxes, ops.wc)
        return cfo, _apply(lambda a, k: a - k, cfo, ops.capex)


def _known_fact(f: Fact) -> bool:
    return f.status == "known" and f.amount is not None


def _shock_reason(scenario: Cp2aScenario) -> str | None:
    """Ruling G-5: the first CP-2A shock that is not known (decline, then increase)."""
    for fact, words in (
        (scenario.decline, "EBITDA decline"),
        (scenario.increase, "interest increase"),
    ):
        if not _known_fact(fact):
            return f"Not calculable: CP-2A scenario {scenario.row} states no known {words}"
    return None


def _not_calculated(reason: str) -> CaseForecast:
    """A case that cannot be forecast: every value of every year missing with `reason`."""
    gap = Val(None, reason)
    year = Year(**{f.name: gap for f in fields(Year)})
    return CaseForecast(years=(year, year, year))


def _t1d_label(f: Fact) -> str:
    """A CP-1D row label in running text: its first letter lower-cased (round 6d, G-9)."""
    return f.label[:1].lower() + f.label[1:]


def _supported(cp1d: tuple[Fact, Fact, Fact] | None, why: str | None) -> Val:
    """CP-1D supported EBITDA for the adjustment and the FY2026 comparison (ruling G-9)."""
    if cp1d is None:
        return Val(None, why)
    f = cp1d[0]
    if not _known_fact(f):
        return Val(None, f"Not calculable: CP-1D {_t1d_label(f)} is not available")
    _usd_millions(f"CP-1D {_t1d_label(f)}", f)  # round 11 Q12: an explicit raise, not an assert
    if f.period != LTM_PERIOD:
        return Val(None, f"Not compared: CP-1D {_t1d_label(f)} is for {f.period}, not {LTM_PERIOD}")
    return _known(_amount(f))


def _resolve(inputs: ForwardInputs) -> _Run:
    sub, ctx = inputs.submission, inputs.context
    found = content_issues(inputs)
    if found:
        raise ValueError("CP-2G submission has issues: " + "; ".join(bounded_issues(found)))
    ops = Operands.from_cp1(ctx.cp1_facts)
    drivers = Drivers.from_submission(sub.base_drivers)
    scenario = next(s for s in ctx.cp2a.scenarios if s.row == sub.downside.scenario)
    shock_reason = _shock_reason(scenario)
    path = {
        "base": forecast(operands=ops, drivers=drivers, shock=None),
        "down": _not_calculated(shock_reason)
        if shock_reason is not None
        else forecast(
            operands=ops,
            drivers=drivers,
            shock=(_amount(scenario.decline), _amount(scenario.increase)),
        ),
    }
    amount = sub.minimum_liquidity.amount
    cp1d = ctx.cp1d.facts()
    state = ctx.cp1d.state
    why = None if state == "bound" else CP1D_WHY[state]
    return _Run(
        sub=sub,
        ctx=ctx,
        cp1=select_cp1(ctx.cp1_facts),
        ops=ops,
        drivers=drivers,
        scenario=scenario,
        shock_reason=shock_reason,
        path=path,
        min_liq=None if amount == NOT_ASSESSED else Decimal(amount),
        cp1d=cp1d,
        cp1d_why=why,
        supported=_supported(cp1d, why),
        tl0=_ratio(ops.debt, ops.ebitda, NC_EBITDA),
        a25_fcf=_a25(ops)[1],
        bound=prose.bind(ctx.prose_facts()),
    )


def _t2h1(b: _Book, run: _Run) -> None:
    state = run.ctx.cp1d.state
    if state == "bound":
        # round 9: the period of the first known CP-1D fact (supported, total, net); the row's
        # "Not applicable" when none is known
        period = next((f.period for f in run.cp1d or () if _known_fact(f)), None)
        cp1d_row = (
            str(run.ctx.cp1d.status),
            "Not applicable" if period is None else f"Base period {period}",
            "T1D.3 supported EBITDA and T1D.6 supported leverage",
            "Supported EBITDA includes accepted savings not yet realised.",
        )
    else:
        cp1d_row = (
            "not part of this run" if state == "unbound" else "blocked",
            "Not applicable",
            "Nothing read",
            f"{run.cp1d_why}.",
        )
    rows = (
        (
            "u_cp1",
            "CP-1",
            run.ctx.cp1_status,
            f"Base period {LTM_PERIOD}",
            "T4.10 twelve-month operands and reported ratios",
            "Inherits CP-1's own limitations.",
        ),
        (
            "u_cp2a",
            "CP-2A",
            run.ctx.cp2a_status,
            f"Base period {run.ctx.cp2a.base_period}",
            "T2B.1 scenario shocks and T2B.6 break register",
            "Shock sizes and watch levels are analyst assumptions.",
        ),
        ("u_cp1d", "CP-1D", *cp1d_row),
        (
            "u_cp2d",
            "CP-2D",
            run.ctx.cp2d_status or "not part of this run",  # bound: recorded, never read (G-6)
            "Not applicable",
            "Nothing read",
            "CP-2D (liquidity bridge) is an optional input that this version never reads.",
        ),
    )
    fields = ("module", "status", "basis", "read", "limitation")
    for row, *values in rows:
        for field, value in zip(fields, values, strict=True):
            b.text(("T2H.1", row, field), field.capitalize(), value)
        b.row("T2H.1", row, values[0], fields)


def _t2h2_row(
    b: _Book,
    row: str,
    label: str,
    v: Val,
    unit: UnitKind,
    formula: str,
    derives: Sequence[str],
    basis: str,
    check: str,
) -> None:
    b.value(("T2H.2", row, "value"), label, v, unit, formula, derives)
    b.text(("T2H.2", row, "basis"), "Basis", basis)
    b.text(("T2H.2", row, "check"), "Check", check)
    b.row("T2H.2", row, label, ("value", "basis", "check"))


def _compared(v: Val, reported: Fact) -> str:
    if v.amount is None or reported.status != "known" or reported.amount is None:
        return "Not compared"
    return "Reconciled to CP-1" if v.amount == reported.amount else "Differs from CP-1"


def _t2h2(b: _Book, run: _Run) -> None:
    ops, cp1 = run.ops, run.cp1
    copies = (
        ("revenue", "Revenue"),
        ("ebitda", "EBITDA"),
        ("interest", "Cash interest paid (outflow)"),
        ("taxes", "Cash taxes paid (outflow)"),
        ("wc", "Working capital movement (outflow)"),
        ("capex", "Capital expenditure (outflow)"),
    )

    def copy(key: str, label: str) -> None:
        metric = OPERAND_METRIC[key]
        formula = f"CP-1 {metric}" + (", sign reversed" if key in _OUTFLOWS else "")
        _t2h2_row(
            b,
            key,
            label,
            getattr(ops, key),
            "amount",
            formula,
            [f"cp1:{metric}"],
            f"CP-1 T4.10 {metric} · {LTM_PERIOD}",
            "Copied from CP-1",
        )

    for key, label in copies:
        copy(key, label)
    _t2h2_row(
        b,
        "fcf",
        "Free cash flow recomputed",
        run.a25_fcf,
        "amount",
        "EBITDA - cash interest - cash taxes - working capital outflow - capital expenditure",
        [
            "cp1:ebitda",
            "cp1:cash_interest",
            "cp1:cash_taxes",
            "cp1:working_capital_change",
            "cp1:capex",
        ],
        "Statement identity against CP-1 fcf (cp1_references)",
        _compared(run.a25_fcf, cp1["fcf"]),
    )
    for key, label in (
        ("debt", "Total debt"),
        ("cash", "Cash and cash equivalents"),
        ("undrawn", "Undrawn revolver"),
    ):
        copy(key, label)

    def cp1d_copy(row: str, label: str, idx: int, unit: UnitKind, basis: str) -> None:
        """A CP-1D copy keeps CP-1D's status, limitation and period (ruling G-9)."""
        at = ("T2H.2", row, "value")
        f = None if run.cp1d is None else run.cp1d[idx]
        if f is None:
            assert run.cp1d_why is not None
            b.gap(at, label, unit, run.cp1d_why)
        elif not _known_fact(f):
            b.gap(at, label, unit, _reason(f), status=_copy_status(f))
        else:
            assert f.period is not None  # a numeric Fact has a period (contracts.Fact)
            src = CP1D_IDS[idx]
            formula = f"Copy of CP-1D {src}"
            b.num(at, label, _amount(f), unit, formula, period=f.period, derives=[f"cp1d:{src}"])
        known = f is not None and _known_fact(f)
        b.text(("T2H.2", row, "basis"), "Basis", basis)
        b.text(("T2H.2", row, "check"), "Check", "Copied from CP-1D" if known else "Not compared")
        b.row("T2H.2", row, label, ("value", "basis", "check"))

    cp1d_copy(
        "ebitda_supported",
        "EBITDA supported by CP-1D evidence",
        0,
        "amount",
        "CP-1D T1D.3 supported adjusted EBITDA",
    )
    adj = _apply(lambda s, e: s - e, run.supported, ops.ebitda)
    _t2h2_row(
        b,
        "ebitda_adjustment",
        "Earnings-quality adjustment",
        adj,
        "amount",
        "Supported EBITDA - CP-1 EBITDA",
        ["cp1d:T1D.3.supported.value", "cp1:ebitda"],
        "Supported EBITDA less CP-1 EBITDA",
        "Computed" if adj.amount is not None else "Not compared",
    )
    nl0 = _ratio(_apply(lambda d, c: d - c, ops.debt, ops.cash), ops.ebitda, NC_EBITDA)
    _t2h2_row(
        b,
        "total_leverage",
        "Total leverage on CP-1 EBITDA",
        run.tl0,
        "multiple",
        "Total debt / EBITDA",
        ["cp1:total_debt", "cp1:ebitda"],
        "Recomputed against CP-1 total_leverage_reported (cp1_references)",
        _compared(run.tl0, cp1["total_leverage_reported"]),
    )
    _t2h2_row(
        b,
        "net_leverage",
        "Net leverage on CP-1 EBITDA",
        nl0,
        "multiple",
        "(Total debt - cash) / EBITDA",
        ["cp1:total_debt", "cp1:cash_closing", "cp1:ebitda"],
        "Recomputed against CP-1 net_leverage_reported (cp1_references)",
        _compared(nl0, cp1["net_leverage_reported"]),
    )
    for row, label, idx in (
        ("total_leverage_supported", "Total leverage on CP-1D supported EBITDA", 1),
        ("net_leverage_supported", "Net leverage on CP-1D supported EBITDA", 2),
    ):
        cp1d_copy(row, label, idx, "multiple", "CP-1D T1D.6 supported leverage")


def _amount(f: Fact) -> Decimal:
    if f.amount is None:
        raise ValueError(f"CP-2G: upstream fact {f.fact_id} has no amount")
    return f.amount


_T2H3_FIELDS = ("case", "driver", "fy1", "fy2", "fy3", "class", "source")


def _t2h3(b: _Book, run: _Run) -> None:
    for n, name in enumerate(DRIVERS, 1):
        row = f"a{n:02d}"
        b.text(("T2H.3", row, "case"), "Case", "Base")
        b.text(("T2H.3", row, "driver"), "Driver", DRIVER_LABEL[name])
        for t, value in enumerate(getattr(run.drivers, name)):
            b.num(
                ("T2H.3", row, f"fy{t + 1}"),
                FY[t],
                value,
                DRIVER_UNIT[name],
                "analyst input",
                value_class="analyst_judgment",
                period=FY_PERIOD[t],
            )
        b.text(("T2H.3", row, "class"), "Class", "analyst_judgment")
        b.text(("T2H.3", row, "source"), "Source", "Analyst assumption")
        b.row("T2H.3", row, DRIVER_LABEL[name], _T2H3_FIELDS)
    for row, label, fact in (
        ("d01", "EBITDA decline against the base case", run.scenario.decline),
        ("d02", "Increase in the cash interest rate", run.scenario.increase),
    ):
        b.text(("T2H.3", row, "case"), "Case", "Downside")
        b.text(("T2H.3", row, "driver"), "Driver", label)
        for t in range(3):  # a copy keeps CP-2A's class; only a calculated copy has lineage
            _cp2a_copy(b, ("T2H.3", row, f"fy{t + 1}"), FY[t], fact, "percent", period=FY_PERIOD[t])
        b.text(("T2H.3", row, "class"), "Class", fact.value_class or "analyst_judgment")
        b.text(("T2H.3", row, "source"), "Source", f"CP-2A {fact.fact_id}")
        b.row("T2H.3", row, label, _T2H3_FIELDS)
    b.text(("T2H.3", "m01", "case"), "Case", "Both")
    b.text(("T2H.3", "m01", "driver"), "Driver", "Minimum liquidity")
    for t in range(3):
        at = ("T2H.3", "m01", f"fy{t + 1}")
        if run.min_liq is None:
            b.gap(at, FY[t], "amount", "Minimum liquidity was not assessed", period=FY_PERIOD[t])
        else:
            b.num(
                at,
                FY[t],
                run.min_liq,
                "amount",
                "analyst input",
                value_class="analyst_judgment",
                period=FY_PERIOD[t],
            )
    b.text(("T2H.3", "m01", "class"), "Class", "analyst_judgment")
    b.text(
        ("T2H.3", "m01", "source"),
        "Source",
        "Analyst assumption" if run.min_liq is not None else "Not assessed",
    )
    b.row("T2H.3", "m01", "Minimum liquidity", _T2H3_FIELDS)


def _cp2a_copy(
    b: _Book,
    at: tuple[str, str, str],
    label: str,
    f: Fact,
    unit: UnitKind,
    *,
    period: str = LTM_PERIOD,
    keep_lineage: bool = False,
) -> None:
    """A copy of a CP-2A cell: its value and class, or its status and limitation (G-decisions)."""
    if not _known_fact(f):
        b.gap(at, label, unit, _reason(f), status=_copy_status(f), period=period)
        return
    b.num(
        at,
        label,
        _amount(f),
        unit,
        f"Copy of CP-2A {f.fact_id}",
        value_class=f.value_class,
        period=period,
        derives=[f"cp2a:{f.fact_id}"],
        keep_lineage=keep_lineage,
    )


def _rows(case: str) -> tuple[str, str, str]:
    p = ROW_PREFIX[case]
    return f"{p}26", f"{p}27", f"{p}28"


_T2H4_FIELDS = ("revenue", "ebitda", "margin", "cfo", "capex", "fcf")
_T2H4_LABEL = {
    "revenue": "Revenue",
    "ebitda": "EBITDA",
    "margin": "EBITDA margin",
    "cfo": "Cash flow after interest, taxes and working capital",
    "capex": "Capital expenditure (outflow)",
    "fcf": "Free cash flow",
}
_FCF_FORMULA = "Cash flow after interest, taxes and working capital - capital expenditure"


def _t2h4(b: _Book, run: _Run) -> None:
    ops = run.ops
    cfo0, fcf0 = _a25(ops)

    def put(
        row: str,
        field: str,
        v: Val,
        unit: UnitKind,
        formula: str,
        derives: Sequence[str],
        period: str,
    ) -> None:
        b.value(("T2H.4", row, field), _T2H4_LABEL[field], v, unit, formula, derives, period=period)

    put(A25, "revenue", ops.revenue, "amount", "CP-1 revenue", ["cp1:revenue"], LTM_PERIOD)
    put(A25, "ebitda", ops.ebitda, "amount", "CP-1 EBITDA", ["cp1:ebitda"], LTM_PERIOD)
    put(
        A25,
        "margin",
        _ratio(ops.ebitda, ops.revenue, NC_REVENUE),
        "percent",
        "EBITDA / revenue",
        ["cp1:ebitda", "cp1:revenue"],
        LTM_PERIOD,
    )
    put(
        A25,
        "cfo",
        cfo0,
        "amount",
        "EBITDA - cash interest - cash taxes - working capital outflow",
        ["cp1:ebitda", "cp1:cash_interest", "cp1:cash_taxes", "cp1:working_capital_change"],
        LTM_PERIOD,
    )
    put(
        A25,
        "capex",
        ops.capex,
        "amount",
        "CP-1 capital expenditure, sign reversed",
        ["cp1:capex"],
        LTM_PERIOD,
    )
    put(
        A25,
        "fcf",
        fcf0,
        "amount",
        _FCF_FORMULA,
        [f"T2H.4.{A25}.cfo", f"T2H.4.{A25}.capex"],
        LTM_PERIOD,
    )
    b.row("T2H.4", A25, f"FY{BASE_YEAR} actual", _T2H4_FIELDS)
    decline_id = f"cp2a:{run.scenario.decline.fact_id}"
    for case in CASES:
        rows = _rows(case)
        for t, y in enumerate(run.path[case].years):
            r, fy, pr = rows[t], f"fy{t + 1}", FY_PERIOD[t]
            prev = A25 if t == 0 else rows[t - 1]
            put(
                r,
                "revenue",
                y.revenue,
                "amount",
                "Prior revenue x (1 + growth)",
                [f"T2H.4.{prev}.revenue", f"T2H.3.a01.{fy}"],
                pr,
            )
            if case == "base":
                put(
                    r,
                    "ebitda",
                    y.ebitda,
                    "amount",
                    "Revenue x margin",
                    [f"T2H.4.{r}.revenue", f"T2H.3.a02.{fy}"],
                    pr,
                )
            else:
                put(
                    r,
                    "ebitda",
                    y.ebitda,
                    "amount",
                    "Revenue x margin x (1 - CP-2A EBITDA decline)",
                    [f"T2H.4.{r}.revenue", f"T2H.3.a02.{fy}", f"T2H.3.d01.{fy}", decline_id],
                    pr,
                )
            put(
                r,
                "margin",
                _ratio(y.ebitda, y.revenue, NC_REVENUE),
                "percent",
                "EBITDA / revenue",
                [f"T2H.4.{r}.ebitda", f"T2H.4.{r}.revenue"],
                pr,
            )
            put(
                r,
                "cfo",
                y.cfo,
                "amount",
                "EBITDA - cash interest - revenue x (taxes and working capital share)",
                [
                    f"T2H.4.{r}.ebitda",
                    f"T2H.5.{r}.interest",
                    f"T2H.3.a04.{fy}",
                    f"T2H.4.{r}.revenue",
                ],
                pr,
            )
            put(
                r,
                "capex",
                y.capex,
                "amount",
                "Revenue x capital expenditure share",
                [f"T2H.4.{r}.revenue", f"T2H.3.a03.{fy}"],
                pr,
            )
            put(r, "fcf", y.fcf, "amount", _FCF_FORMULA, [f"T2H.4.{r}.cfo", f"T2H.4.{r}.capex"], pr)
            b.row("T2H.4", r, f"{CASE_LABEL[case]} case {FY[t]}", _T2H4_FIELDS)


_T2H5_FIELDS = (
    "opening_debt",
    "repayment",
    "closing_debt",
    "interest",
    "opening_cash",
    "fcf",
    "dividends",
    "closing_cash",
    "undrawn_revolver",
    "accessible_liquidity",
)
_T2H5_LABEL = {
    "opening_debt": "Opening debt",
    "repayment": "Debt repayment (outflow)",
    "closing_debt": "Closing debt",
    "interest": "Cash interest (outflow)",
    "opening_cash": "Opening cash",
    "fcf": "Free cash flow",
    "dividends": "Distributions (outflow)",
    "closing_cash": "Closing cash",
    "undrawn_revolver": "Undrawn revolver",
    "accessible_liquidity": "Accessible liquidity",
}


def _t2h5_row(b: _Book, run: _Run, case: str, t: int, y: Year) -> None:
    rows = _rows(case)
    r, fy, pr = rows[t], f"fy{t + 1}", FY_PERIOD[t]

    def put(field: str, v: Val, formula: str, derives: Sequence[str]) -> None:
        at = ("T2H.5", r, field)
        b.value(at, _T2H5_LABEL[field], v, "amount", formula, derives, period=pr)

    def analyst(field: str, v: Val) -> None:
        at = ("T2H.5", r, field)
        if v.amount is None:  # a downside that is not calculated (ruling G-5)
            assert v.reason is not None
            b.gap(at, _T2H5_LABEL[field], "amount", v.reason, period=pr)
            return
        b.num(
            at,
            _T2H5_LABEL[field],
            v.amount,
            "amount",
            "analyst input",
            value_class="analyst_judgment",
            period=pr,
        )

    prev = None if t == 0 else rows[t - 1]
    if prev is None:
        put("opening_debt", y.opening_debt, "CP-1 total debt", ["cp1:total_debt"])
    else:
        put("opening_debt", y.opening_debt, "Prior closing debt", [f"T2H.5.{prev}.closing_debt"])
    analyst("repayment", y.repayment)
    put(
        "closing_debt",
        y.closing_debt,
        "Opening debt - repayment",
        [f"T2H.5.{r}.opening_debt", f"T2H.3.a07.{fy}"],
    )
    interest_from = [f"T2H.5.{r}.opening_debt", f"T2H.3.a05.{fy}"]
    if case == "base":
        put("interest", y.interest, "Opening debt x rate", interest_from)
    else:
        increase = [f"T2H.3.d02.{fy}", f"cp2a:{run.scenario.increase.fact_id}"]
        put(
            "interest",
            y.interest,
            "Opening debt x rate x (1 + CP-2A interest increase)",
            interest_from + increase,
        )
    if prev is None:
        put("opening_cash", y.opening_cash, "CP-1 cash and cash equivalents", ["cp1:cash_closing"])
    else:
        put("opening_cash", y.opening_cash, "Prior closing cash", [f"T2H.5.{prev}.closing_cash"])
    put("fcf", y.fcf, "From T2H.4", [f"T2H.4.{r}.fcf"])
    analyst("dividends", y.dividends)
    put(
        "closing_cash",
        y.closing_cash,
        "Opening cash + free cash flow - distributions - repayment",
        [f"T2H.5.{r}.opening_cash", f"T2H.5.{r}.fcf", f"T2H.3.a06.{fy}", f"T2H.5.{r}.repayment"],
    )
    put("undrawn_revolver", y.undrawn, "CP-1 undrawn revolver, held", ["cp1:undrawn_rcf"])
    put(
        "accessible_liquidity",
        y.liquidity,
        "Closing cash + undrawn revolver",
        [f"T2H.5.{r}.closing_cash", f"T2H.5.{r}.undrawn_revolver"],
    )
    b.row("T2H.5", r, f"{CASE_LABEL[case]} case {FY[t]}", _T2H5_FIELDS)


def _t2h5(b: _Book, run: _Run) -> None:
    for case in CASES:
        for t, y in enumerate(run.path[case].years):
            _t2h5_row(b, run, case, t, y)


_T2H6_FIELDS = (
    "total_leverage",
    "net_leverage",
    "interest_coverage",
    "fcf_to_debt",
    "liquidity_headroom",
)
_T2H6_SPEC: Mapping[str, tuple[str, UnitKind, str]] = {
    "total_leverage": ("Total leverage", "multiple", "Closing debt / EBITDA"),
    "net_leverage": ("Net leverage", "multiple", "(Closing debt - closing cash) / EBITDA"),
    "interest_coverage": ("Interest coverage", "multiple", "EBITDA / cash interest"),
    "fcf_to_debt": ("Free cash flow to debt", "percent", "Free cash flow / closing debt"),
}
_HEADROOM = (
    "Accessible liquidity less minimum liquidity",
    "Accessible liquidity - minimum liquidity",
)


def _t2h6(b: _Book, run: _Run) -> None:
    ops = run.ops

    def ratios(
        row: str, vals: Mapping[str, Val], derives: Mapping[str, list[str]], period: str
    ) -> None:
        for field, (label, unit, formula) in _T2H6_SPEC.items():
            b.value(
                ("T2H.6", row, field),
                label,
                vals[field],
                unit,
                formula,
                derives[field],
                period=period,
            )

    nd0 = _apply(lambda d, c: d - c, ops.debt, ops.cash)
    ratios(
        A25,
        {
            "total_leverage": run.tl0,
            "net_leverage": _ratio(nd0, ops.ebitda, NC_EBITDA),
            "interest_coverage": _ratio(ops.ebitda, ops.interest, NC_INTEREST),
            "fcf_to_debt": _ratio(run.a25_fcf, ops.debt, NC_DEBT),
        },
        {
            "total_leverage": ["cp1:total_debt", "cp1:ebitda"],
            "net_leverage": ["cp1:total_debt", "cp1:cash_closing", "cp1:ebitda"],
            "interest_coverage": ["cp1:ebitda", "cp1:cash_interest"],
            "fcf_to_debt": [f"T2H.4.{A25}.fcf", "cp1:total_debt"],
        },
        LTM_PERIOD,
    )
    # ruling L2: the minimum liquidity is a forecast-year assumption, not applied to FY2025
    b.gap(
        ("T2H.6", A25, "liquidity_headroom"),
        _HEADROOM[0],
        "amount",
        LIQ_HEADROOM_FY25,
        status="not_applicable",
    )
    b.row("T2H.6", A25, f"FY{BASE_YEAR} actual", _T2H6_FIELDS)
    for case in CASES:
        rows = _rows(case)
        for t, y in enumerate(run.path[case].years):
            r, pr = rows[t], FY_PERIOD[t]
            ratios(
                r,
                {
                    "total_leverage": y.total_leverage,
                    "net_leverage": y.net_leverage,
                    "interest_coverage": y.coverage,
                    "fcf_to_debt": y.fcf_to_debt,
                },
                {
                    "total_leverage": [f"T2H.5.{r}.closing_debt", f"T2H.4.{r}.ebitda"],
                    "net_leverage": [
                        f"T2H.5.{r}.closing_debt",
                        f"T2H.5.{r}.closing_cash",
                        f"T2H.4.{r}.ebitda",
                    ],
                    "interest_coverage": [f"T2H.4.{r}.ebitda", f"T2H.5.{r}.interest"],
                    "fcf_to_debt": [f"T2H.5.{r}.fcf", f"T2H.5.{r}.closing_debt"],
                },
                pr,
            )
            if run.min_liq is None:
                headroom = Val(None, NC_LIQUIDITY)
            else:
                headroom = _apply(lambda liq, floor: liq - floor, y.liquidity, _known(run.min_liq))
            b.value(
                ("T2H.6", r, "liquidity_headroom"),
                _HEADROOM[0],
                headroom,
                "amount",
                _HEADROOM[1],
                [f"T2H.5.{r}.accessible_liquidity", f"T2H.3.m01.fy{t + 1}"],
                period=pr,
            )
            b.row("T2H.6", r, f"{CASE_LABEL[case]} case {FY[t]}", _T2H6_FIELDS)


def _unmapped_reason(b: Cp2aBreak) -> str:
    return (
        f"Not calculable: CP-2A definition break {b.row} has a test CP-2G does not map ({b.test})"
    )


def _tests(run: _Run) -> tuple[list[BreakTest], list[tuple[str, str]]]:
    """The CP-2A break rows then m01, and the (row, cause) of each unverified metric."""
    metric_of = {m.break_id: m.metric for m in run.sub.break_metrics}
    tests: list[BreakTest] = []
    unverified: list[tuple[str, str]] = []
    for b in run.ctx.cp2a.breaks:
        level, reason = (
            (b.level.amount, None) if _known_fact(b.level) else (None, b.level.limitation)
        )
        kind: BreakKind | None
        if _is_definition(b):
            kind = _DEFINITION_KIND.get(b.test)
            if kind is None:  # ruling G-7: settles, not a validator error
                level, reason = None, _unmapped_reason(b)
        else:
            kind = _METRIC_KIND[metric_of[b.row]]
            _ok, cause = _metric_check(b, kind, run.ops, run.ctx.cp2a.base_period)
            if cause is not None:
                unverified.append((b.row, cause))
        tests.append(BreakTest(b.row, kind, b.test, level, reason))
    tests.append(
        BreakTest(
            "m01",
            "liquidity",
            LIQUIDITY_TEST,
            run.min_liq,
            NC_LIQUIDITY if run.min_liq is None else None,
        )
    )
    return tests, unverified


_T2H7_FIELDS = ("test", "metric", "level", "static_decline", "base_first", "down_first")
_STATIC = "CP-2A required EBITDA decline"


def _t2h7(
    b: _Book, run: _Run, tests: Sequence[BreakTest], results: Mapping[str, Sequence[BreakResult]]
) -> None:
    breaks = {x.row: x for x in run.ctx.cp2a.breaks}
    for n, test in enumerate(tests):
        r = test.row
        b.text(("T2H.7", r, "test"), "Test", test.test)
        unit: UnitKind = "amount" if test.kind in ("fcf", "liquidity") else "multiple"
        if test.kind is None:  # ruling G-7: the copies stay, the metric is missing
            assert test.level_reason is not None
            b.missing_text(("T2H.7", r, "metric"), "Metric", test.level_reason)
            if breaks[r].level.unit not in _UNIT_KIND:  # the copy's unit comes from CP-2A
                raise ValueError(
                    f"CP-2G: CP-2A level {breaks[r].level.fact_id} states no unit CP-2G maps "
                    f"({breaks[r].level.unit})"
                )
            unit = _UNIT_KIND[str(breaks[r].level.unit)]
        else:
            b.text(("T2H.7", r, "metric"), "Metric", KIND_METRIC[test.kind])
        lineage: list[str] = []
        if r in breaks:
            src = breaks[r]
            lineage = [f"cp2a:{src.level.fact_id}"]
            _cp2a_copy(b, ("T2H.7", r, "level"), "Level", src.level, unit, keep_lineage=True)
            _cp2a_copy(
                b,
                ("T2H.7", r, "static_decline"),
                _STATIC,
                src.required_decline,
                "percent",
                keep_lineage=True,
            )
        else:  # m01, the analyst's minimum liquidity
            if test.level is None:
                b.gap(
                    ("T2H.7", r, "level"), "Level", "amount", "Minimum liquidity was not assessed"
                )
            else:
                b.num(
                    ("T2H.7", r, "level"),
                    "Level",
                    test.level,
                    "amount",
                    "analyst input",
                    value_class="analyst_judgment",
                )
            b.gap(
                ("T2H.7", r, "static_decline"),
                _STATIC,
                "percent",
                "CP-2A has no liquidity test",
                status="not_applicable",
            )
        for case in CASES:
            res = results[case][n]
            label = f"First year reached, {CASE_LABEL[case].lower()} case"
            if res.first == NOT_CALCULABLE:  # ruling L5: missing with the root reason
                assert res.reason is not None
                b.missing_text(("T2H.7", r, f"{case}_first"), label, res.reason)
            else:
                b.text(("T2H.7", r, f"{case}_first"), label, res.first, derives=lineage)
        b.row("T2H.7", r, test.test, _T2H7_FIELDS)


def _reason(f: Fact) -> str:
    if not f.limitation:
        raise ValueError(f"CP-2G: unsettled upstream fact {f.fact_id} states no limitation")
    return f.limitation


def _copy_status(f: Fact) -> CellStatus:
    if f.status not in ("missing", "not_applicable"):
        raise ValueError(f"CP-2G: upstream fact {f.fact_id} has status {f.status}")
    return "not_applicable" if f.status == "not_applicable" else "missing"


_T2H8_FIELDS = (
    "trajectory",
    "total_leverage_fy28",
    "change_vs_fy25",
    "peak_total_leverage",
    "peak_period",
    "ebitda_fy26_vs_supported",
    "downstream",
)


def _trajectory(run: _Run, case: str) -> tuple[Trajectory, Val, Val, Val, str | None]:
    """(trajectory, FY2028 leverage, change, peak, peak reason)."""
    years = run.path[case].years
    tls = [y.total_leverage for y in years]
    last = tls[-1]
    if last.amount is None:
        change = last
    elif run.tl0.amount is None:
        change = run.tl0
    else:
        with localcontext(_RATIO):  # one subtraction of two 38-digit values
            change = _known(last.amount - run.tl0.amount)
    peak_reason = next((v.reason for v in tls if v.amount is None), None)
    amounts = [v.amount for v in tls]
    if peak_reason is None:
        known = [a for a in amounts if a is not None]
        top = max(known)
        peak, year = _known(top), FY[known.index(top)]
    else:
        peak, year = Val(None, peak_reason), None
    return Trajectory(change.amount, peak.amount, year), last, change, peak, peak_reason


def _t2h8(b: _Book, run: _Run) -> dict[str, Trajectory]:
    out: dict[str, Trajectory] = {}
    for case in CASES:
        r, rows = case, _rows(case)
        traj, last, change, peak, peak_reason = _trajectory(run, case)
        out[case] = traj
        if change.amount is None:  # ruling L5 applied to the trajectory
            assert change.reason is not None
            b.missing_text(("T2H.8", r, "trajectory"), "Trajectory", change.reason)
        else:
            word = (
                "Deleveraging"
                if change.amount < 0
                else "Releveraging"
                if change.amount > 0
                else "Flat"
            )
            b.text(("T2H.8", r, "trajectory"), "Trajectory", word)
        p28 = FY_PERIOD[-1]
        b.value(
            ("T2H.8", r, "total_leverage_fy28"),
            f"Total leverage {FY[-1]}",
            last,
            "multiple",
            "From T2H.6",
            [f"T2H.6.{rows[2]}.total_leverage"],
            period=p28,
        )
        b.value(
            ("T2H.8", r, "change_vs_fy25"),
            f"Change from FY{BASE_YEAR}",
            change,
            "multiple",
            f"Total leverage {FY[-1]} - total leverage FY{BASE_YEAR}",
            [f"T2H.8.{r}.total_leverage_fy28", "T2H.2.total_leverage.value"],
            period=p28,
        )
        peak_period = (
            FY_SPAN_PERIOD if traj.peak_year is None else FY_PERIOD[FY.index(traj.peak_year)]
        )
        b.value(
            ("T2H.8", r, "peak_total_leverage"),
            "Peak total leverage in the forecast",
            peak,
            "multiple",
            "Highest total leverage of the three forecast years",
            [f"T2H.6.{x}.total_leverage" for x in rows],
            period=peak_period,
        )
        if traj.peak_year is None:
            assert peak_reason is not None
            b.missing_text(("T2H.8", r, "peak_period"), "Peak year", peak_reason)
        else:
            b.text(("T2H.8", r, "peak_period"), "Peak year", traj.peak_year)
        b.value(
            ("T2H.8", r, "ebitda_fy26_vs_supported"),
            f"{FY[0]} EBITDA less CP-1D supported EBITDA",
            _apply(lambda e, s: e - s, run.path[case].years[0].ebitda, run.supported),
            "amount",
            "Forecast EBITDA - CP-1D supported EBITDA",
            [f"T2H.4.{rows[0]}.ebitda", "cp1d:T1D.3.supported.value"],
            period=FY_PERIOD[0],
        )
        b.text(("T2H.8", r, "downstream"), "Downstream modules", "CP-2H, CP-4C")
        b.row("T2H.8", r, f"{CASE_LABEL[case]} case", _T2H8_FIELDS)
    return out


def _spelled(text: str, bound: Mapping[str, Fact]) -> str:
    """Round 9 (CP-2A Choice 5 extended to CP-2G): stored gap text spells each `{ref|unit}` as
    rendered (`business_context.spelled`), never as raw braces. Validated text holds only figure
    references to known upstream figures, so the raise is an invariant."""
    parts = []
    for run in prose.tokenize(text):
        if run.kind == "text":
            parts.append(run.text)
        elif run.figure and run.text in bound and bound[run.text].status == "known":
            parts.append(spelled(bound[run.text]))
        else:
            raise ValueError(
                f"CP-2G: stored text reference {run.text} does not name a known upstream figure"
            )
    return "".join(parts)


def _t2h9(b: _Book, run: _Run) -> None:
    for n, gap in enumerate(run.sub.gaps, 1):
        r = f"g{n:02d}"
        b.text(("T2H.9", r, "id"), "Gap id", f"CP-2G-GAP-{n:03d}")
        for field, label in (
            ("gap", "Gap"),
            ("why_it_matters", "Why it matters"),
            ("affected_analysis", "Affected analysis"),
        ):
            text = _spelled(getattr(gap, field), run.bound)
            b.text(("T2H.9", r, field), label, text, value_class="analyst_judgment")
        b.text(("T2H.9", r, "severity"), "Severity", gap.severity)
        action = _spelled(gap.action, run.bound)
        b.text(("T2H.9", r, "action"), "Action", action, value_class="analyst_judgment")
        b.row(
            "T2H.9",
            r,
            f"Gap {n}",
            ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action"),
        )


def _prose_texts(sub: ForwardSubmission) -> list[str]:
    texts = [_driver(sub.base_drivers, name).rationale for name in DRIVERS]
    texts += [sub.downside.rationale, sub.minimum_liquidity.rationale, sub.assessment.rationale]
    for g in sub.gaps:
        texts += [g.gap, g.why_it_matters, g.affected_analysis, g.action]
    return texts


def _named(text: str, bound: Mapping[str, Fact]) -> list[Fact]:
    """The upstream facts a valid prose text names by figure reference, in reading order,
    resolved through `prose.bind` as the validator resolves them (a fact id, or a calculation id
    one fact alone carries; the CP-2A `_figure_refs` pattern)."""
    return [bound[run.text] for run in prose.tokenize(text) if run.figure and run.text in bound]


def _references(run: _Run) -> tuple[RefTable, RefTable, RefTable]:
    metric_of = {f.fact_id: m for m, f in run.cp1.items()}
    named = [
        metric_of[f.fact_id]
        for text in _prose_texts(run.sub)
        for f in _named(text, run.bound)
        if f.fact_id in metric_of
    ]
    metrics = dict.fromkeys([*named, "fcf", "total_leverage_reported", "net_leverage_reported"])
    cp1_rows = tuple(
        Reference(f"ref{n:02d}", f"{run.cp1[m].label} · {run.cp1[m].period}", run.cp1[m])
        for n, m in enumerate(metrics, 1)
    )
    cp2a_facts = [run.scenario.decline, run.scenario.increase]
    for x in run.ctx.cp2a.breaks:
        cp2a_facts += [x.level, x.required_decline]
    cp2a_rows = tuple(Reference(f"ref{n:02d}", f.label, f) for n, f in enumerate(cp2a_facts, 1))
    cp1d_rows = tuple(Reference(f"ref{n:02d}", f.label, f) for n, f in enumerate(run.cp1d or (), 1))
    return (
        RefTable(
            "cp1_references",
            "CP-1 facts referenced in CP-2G text and compared in T2H.2",
            "CP-1 fact",
            cp1_rows,
        ),
        RefTable(
            "cp2a_references",
            "CP-2A facts copied into CP-2G (T2B.1 scenario, T2B.6 breaks)",
            "CP-2A fact",
            cp2a_rows,
        ),
        RefTable(
            "cp1d_references",
            "CP-1D facts copied into CP-2G (T1D.3 and T1D.6)",
            "CP-1D fact",
            cp1d_rows,
            run.cp1d_why,
        ),
    )


def _joined(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _first_claim(case: str, tests: Sequence[BreakTest], results: Sequence[BreakResult]) -> str:
    lab = CASE_LABEL[case].lower()
    reached = [(t, r.first) for t, r in zip(tests, results, strict=True) if r.first in FY]
    if reached:
        first = min(FY.index(y) for _t, y in reached)
        names = [t.test for t, y in reached if FY.index(y) == first]
        if len(names) == 1:  # ruling G-2
            return f"The first test reached in the {lab} case is {names[0]} in {FY[first]}."
        return f"The first tests reached in the {lab} case are {_joined(names)} in {FY[first]}."
    if all(r.first == NOT_REACHED for r in results):
        return f"No tested break point is reached in the {lab} case through {FY[-1]}."
    if all(r.first == NOT_CALCULABLE for r in results):  # round 9 L3: the first test's chip
        return (
            f"In the {lab} case no tested break point is calculable through {FY[-1]}: "
            f"[T2H.7.{tests[0].row}.{case}_first]."
        )
    return f"In the {lab} case no tested break point is reached, but not every test is calculable."


def _leverage_claim(
    lab: str, peak: str, fy28: str, settled: tuple[bool, bool], year: str | None
) -> str:
    """The T2H.8 claim; `peak` and `fy28` are rendered references (a figure, else a chip) and
    `settled` says which is known (ruling G-3 for the mixed pairs)."""
    if settled == (True, True):
        return f"In the {lab} case, total leverage peaks at {peak} in {year} and ends {FY[2]} at {fy28}."
    if settled == (True, False):
        return (
            f"In the {lab} case, total leverage peaks at {peak} in {year}; {FY[2]} leverage is not "
            f"calculated: {fy28}."
        )
    if settled == (False, True):
        return (
            f"In the {lab} case, total leverage ends {FY[2]} at {fy28}; the peak is not "
            f"calculated: {peak}."
        )
    return f"In the {lab} case, the leverage path is not fully calculable: peak {peak}, {FY[2]} {fy28}."


def _claims(
    b: _Book,
    run: _Run,
    tests: Sequence[BreakTest],
    results: Mapping[str, Sequence[BreakResult]],
    traj: Mapping[str, Trajectory],
) -> tuple[Claim, ...]:
    def ref(fid: str, token: str) -> str:
        return "{" + fid + "|" + token + "}" if b.status(fid) == "known" else f"[{fid}]"

    def analyst(cid: str, text: str, limitation: str | None) -> Claim:
        return Claim(cid, text, limitation, tuple(f.fact_id for f in _named(text, run.bound)))

    def forecast_claim(cid: str, text: str) -> Claim:  # ruling L12
        return Claim(cid, text, FORECAST_LIMITATION, ())

    sub = run.sub
    out = [
        analyst(
            f"T2H.3.{name}",
            _driver(sub.base_drivers, name).rationale,
            _driver(sub.base_drivers, name).limitation,
        )
        for name in DRIVERS
    ]
    out.append(analyst("T2H.3.downside", sub.downside.rationale, sub.downside.limitation))
    out.append(
        analyst(
            "T2H.3.minimum_liquidity",
            sub.minimum_liquidity.rationale,
            None if run.min_liq is not None else "Minimum liquidity was not assessed.",
        )
    )
    for case in CASES:
        r28, lab = _rows(case)[2], CASE_LABEL[case].lower()
        out.append(
            forecast_claim(
                f"T2H.4.{case}",
                f"In the {lab} case, EBITDA reaches {ref(f'T2H.4.{r28}.ebitda', 'US$ m')} in {FY[2]} "
                f"against {ref(f'T2H.4.{A25}.ebitda', 'US$ m')} in FY{BASE_YEAR} and free cash flow "
                f"reaches {ref(f'T2H.4.{r28}.fcf', 'US$ m')}.",
            )
        )
    b28 = _rows("base")[2]
    d26, d27, d28 = _rows("down")
    out.append(
        forecast_claim(
            "T2H.6.base",
            f"In the base case, total leverage moves from {ref(f'T2H.6.{A25}.total_leverage', 'x')} in "
            f"FY{BASE_YEAR} to {ref(f'T2H.6.{b28}.total_leverage', 'x')} in {FY[2]} and interest "
            f"coverage from {ref(f'T2H.6.{A25}.interest_coverage', 'x')} to "
            f"{ref(f'T2H.6.{b28}.interest_coverage', 'x')}.",
        )
    )
    out.append(
        forecast_claim(
            "T2H.6.down",
            f"In the downside case, total leverage is {ref(f'T2H.6.{d26}.total_leverage', 'x')} in "
            f"{FY[0]} and {ref(f'T2H.6.{d28}.total_leverage', 'x')} in {FY[2]}, and interest coverage "
            f"in {FY[0]} is {ref(f'T2H.6.{d26}.interest_coverage', 'x')}.",
        )
    )
    out.append(
        forecast_claim(
            "T2H.5.down",
            f"In the downside case, closing cash is {ref(f'T2H.5.{d26}.closing_cash', 'US$ m')} in "
            f"{FY[0]} and {ref(f'T2H.5.{d27}.closing_cash', 'US$ m')} in {FY[1]}.",
        )
    )
    for case in CASES:
        out.append(forecast_claim(f"T2H.7.{case}", _first_claim(case, tests, results[case])))
    for case in CASES:
        peak, fy28 = f"T2H.8.{case}.peak_total_leverage", f"T2H.8.{case}.total_leverage_fy28"
        settled = (b.status(peak) == "known", b.status(fy28) == "known")
        text = _leverage_claim(
            CASE_LABEL[case].lower(),
            ref(peak, "x"),
            ref(fy28, "x"),
            settled,
            traj[case].peak_year,
        )
        out.append(forecast_claim(f"T2H.8.{case}", text))
    if run.ctx.cp1d.state == "bound":
        supported = b.by_id["T2H.2.total_leverage_supported.value"].fact
        if supported.status == "known" and supported.period != LTM_PERIOD:  # round 9 L2
            text = (
                "CP-1D's total leverage on the earnings it supports, "
                f"{ref('T2H.2.total_leverage_supported.value', 'x')}, is for another period than "
                "the base, so opening total leverage is not restated on it; on reported earnings "
                f"it is {ref('T2H.2.total_leverage.value', 'x')}."
            )
        else:
            text = (
                "On the earnings CP-1D supports, opening total leverage is "
                f"{ref('T2H.2.total_leverage_supported.value', 'x')} against "
                f"{ref('T2H.2.total_leverage.value', 'x')} on reported earnings."
            )
        out.append(Claim("T2H.2.cp1d", text, None, ()))
    a = sub.assessment
    out.append(analyst("T2H.3.assessment", a.rationale, a.limitation))
    return tuple(out)


_FIXED_LIMITATIONS = (
    (
        "Driver values are analyst assumptions without a source citation; no management guidance or "
        "consensus is an input."
    ),
    (
        "The forecast is annual over three years from the CP-1 twelve-month base; no quarterly path "
        "is modelled."
    ),
    (
        "Cash interest is the analyst's rate applied to the opening debt balance; no hedging, floor or "
        "reference-rate curve is modelled."
    ),
    (
        "Cash taxes and working capital are modelled together as a share of revenue; no tax shield or "
        "working-capital cycle is modelled."
    ),
    (
        "No new borrowing, refinancing or covenant waiver is modelled: debt moves only by the "
        "analyst's repayments, and cash is not floored, so a negative cash balance is an unfunded "
        "requirement, not a forecast of events."
    ),
    (
        "The downside applies CP-2A's settled scenario shocks to every forecast year and holds "
        "revenue, capital expenditure, distributions and repayments at the base case; no mitigating "
        "action is modelled."
    ),
    (
        "The break tests reuse CP-2A's levels, which are watch levels and definitions, not covenant "
        "tests; covenant compliance belongs to CP-4."
    ),
    (
        "Accessible liquidity is closing cash plus CP-1's undrawn revolver; restricted, trapped or "
        "operationally required cash is not separated."
    ),
    (
        "Debt maturities and refinancing feasibility are not modelled; the maturity wall and funding "
        "gap belong to CP-2D and CP-3C."
    ),
)
_CP1D_LIMITATION = {
    "bound": "CP-1D's supported EBITDA includes accepted savings not yet realised; it is shown "
    "for starting leverage and comparison only and is not a forecast base.",
    "unbound": "CP-1D (earnings quality) is not part of this run, so starting leverage is not "
    "restated on evidence-supported EBITDA and no comparison with it is made.",
    "blocked": "CP-1D (earnings quality) is bound but blocked, so starting leverage is not "
    "restated on evidence-supported EBITDA and no comparison with it is made.",
}


def _own_limitations(
    run: _Run,
    unverified: Sequence[tuple[str, str]],
    results: Mapping[str, Sequence[BreakResult]],
    traj: Mapping[str, Trajectory],
) -> tuple[str, ...]:
    out = list(_FIXED_LIMITATIONS)
    out.append(_CP1D_LIMITATION[run.ctx.cp1d.state])
    out.extend(  # ruling G-9, wording round 6d
        f"CP-1D is bound but its {_t1d_label(f)} is not a known {LTM_PERIOD} figure, so starting "
        "leverage is not restated on it."
        for f in run.cp1d or ()
        if not _known_fact(f) or f.period != LTM_PERIOD
    )
    if run.ctx.cp2d_status is not None:  # ruling G-6
        out.append(
            "CP-2D (liquidity cash flow bridge) is bound but its liquidity bridge is not read in "
            "this version."
        )
    out.append(
        "Minimum liquidity was not assessed, so the liquidity break test and liquidity headroom "
        "are not calculated."
        if run.min_liq is None
        else "Minimum liquidity is an analyst assumption, not a source figure."
    )
    for key, v in run.ops.items():
        if v.amount is None:
            out.append(
                f"Base {_OPERAND_WORDS[key]} is not available in CP-1 for {LTM_PERIOD}: every "
                "figure that needs it is Not calculable."
            )
    base_period = run.ctx.cp2a.base_period
    if base_period != LTM_PERIOD:
        out.append(
            f"CP-2A stressed the base period {base_period}; its required declines are shown for "
            "reference and are not comparable with the twelve-month forward path."
        )
    if run.shock_reason is not None:  # ruling G-5
        out.append(
            f"CP-2A scenario {run.scenario.row} has no known shock, so the downside case is not "
            "calculated."
        )
    out.extend(
        f"The metric named for CP-2A break {row} could not be checked against its CP-2A required "
        f"decline: {cause}."
        for row, cause in unverified
    )
    out.extend(  # ruling G-7
        f"CP-2A definition break {b.row} has the test {b.test}, which CP-2G does not map; its "
        "first years are not calculated."
        for b in run.ctx.cp2a.breaks
        if _is_definition(b) and b.test not in _DEFINITION_KIND
    )
    for case in CASES:
        negative = [
            FY[t]
            for t, y in enumerate(run.path[case].years)
            if y.closing_cash.amount is not None and y.closing_cash.amount < 0
        ]
        if negative:
            out.append(
                f"In the {CASE_LABEL[case].lower()} case closing cash is negative from "
                f"{negative[0]}: an unfunded requirement, not a forecast of events."
            )
    if any(r.first == NOT_CALCULABLE for case in CASES for r in results[case]):
        out.append(
            "A break test whose metric is not calculable in a forecast year is missing, with the "
            "reason, when no earlier year has met it."
        )
    if any(t.change is None for t in traj.values()):
        out.append(
            "A leverage trajectory that cannot be calculated is missing, with the reason, "
            "not a known text."
        )
    out.extend(f"Gap ({g.severity}): {_spelled(g.gap, run.bound)}" for g in run.sub.gaps)
    return tuple(out)


def _cite(b: _Book, run: _Run) -> None:
    """Lease :132 (lineage_rule; rulings stage2 round 3 item 3): a calculated fact gets one
    Citation per (source, page), the first quote on that page among the citations of the facts
    in its derives_from list, in that order; an own fact contributes its own (transitively CP-1)
    citations; analyst inputs and CP-2A watch levels carry none. A lineage entry the rule cannot
    resolve fails closed."""
    upstream = {f"cp1:{metric}": f for metric, f in run.cp1.items()}
    cp2a = [run.scenario.decline, run.scenario.increase]
    for x in run.ctx.cp2a.breaks:
        cp2a += [x.level, x.required_decline]
    upstream |= {f"cp2a:{f.fact_id}": f for f in cp2a}
    upstream |= {f"cp1d:{f.fact_id}": f for f in run.cp1d or ()}
    done: dict[str, tuple[Citation, ...]] = {}

    def of(ref: str, path: tuple[str, ...]) -> tuple[Citation, ...]:
        if ref in upstream:
            return upstream[ref].citations
        if ref not in b.by_id or ref in path:
            raise ValueError(f"CP-2G: lineage {' -> '.join((*path, ref))} names no settled fact")
        if ref not in done:
            cell = b.by_id[ref]
            fact = cell.fact
            calculated = fact.status == "known" and fact.value_class == "calculated"
            done[ref] = (
                one_per_page(tuple(c for d in cell.derives_from for c in of(d, (*path, ref))))
                if calculated
                else fact.citations
            )
        return done[ref]

    cited = [of(cell.fact.fact_id, ()) for cell in b.cells]
    b.cells = [
        replace(cell, fact=cell.fact.model_copy(update={"citations": cites}))
        if cites != cell.fact.citations
        else cell
        for cell, cites in zip(b.cells, cited, strict=True)
    ]
    b.by_id = {cell.fact.fact_id: cell for cell in b.cells}


def compute(inputs: ForwardInputs) -> ForwardResult:
    """The forward model of one valid submission; raises ValueError on any issue."""
    run = _resolve(inputs)
    tests, unverified = _tests(run)
    results = {case: test_breaks(tests=tests, forecast=run.path[case]) for case in CASES}
    b = _Book()
    _t2h1(b, run)
    with _exact_digits("the historical-to-base bridge"):
        _t2h2(b, run)
    _t2h3(b, run)
    _t2h4(b, run)
    _t2h5(b, run)
    with _exact_digits("the credit metrics"):
        _t2h6(b, run)
    _t2h7(b, run, tests, results)
    with _exact_digits("the deleveraging path"):
        traj = _t2h8(b, run)
    _t2h9(b, run)
    _cite(b, run)
    claims = _claims(b, run, tests, results, traj)
    tables = tuple(Table(t, title, tuple(b.rows[t])) for t, title in TABLES.items())
    break_rows = tuple(
        BreakRow(t.row, t.kind, t.test, base, down)
        for t, base, down in zip(tests, results["base"], results["down"], strict=True)
    )
    return ForwardResult(
        operands=run.ops,
        forecast=run.path,
        cells=tuple(b.cells),
        tables=tables,
        references=_references(run),
        claims=claims,
        own_limitations=_own_limitations(run, unverified, results, traj),
        break_tests=break_rows,
        trajectory=traj,
    )


# --- Stage 2: the connection to the store (lease Public API, G1-X protocol section 2) ---------

STEP_ID = "forward_credit_model"
STEP_IDS = (STEP_ID,)
QUALIFICATION = Qualification(implementation="implemented")
SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: ForwardSubmission}
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
CP1, CP1D, CP2A, CP2D = "CP-1", "CP-1D", "CP-2A", "CP-2D"
_SETTLED: Mapping[str, InputStatus] = {
    "accepted": "accepted",
    "restricted": "restricted",
    "blocked": "blocked",
}


def _fact_of(facts: Mapping[str, Fact], fact_id: str, module_id: str) -> Fact:
    fact = facts.get(fact_id)
    if fact is None:
        raise ValueError(f"CP-2G: the {module_id} head has no fact {fact_id}")
    return fact


def _text_of(facts: Mapping[str, Fact], fact_id: str, module_id: str) -> str:
    fact = _fact_of(facts, fact_id, module_id)
    if fact.status != "known" or fact.text is None:
        raise ValueError(f"CP-2G: {module_id} {fact_id} is not a known text")
    return fact.text


def cp2a_of(module: Module) -> Cp2aHead:
    """A settled CP-2A module as the core reads it: every T2B.1 scenario (name, decline,
    increase) and T2B.6 break (origin, test, level, required decline, outcome), in register
    order (`manifest.json upstream_fact_selection`). The scenario name is the known text fact
    `T2B.1.<row>.name`. The base period is the one period the T2B.1 shocks state (round 13 R1 L2;
    round 5 item 6): a shock with no period is not a conflict (round 5 item 5), two periods are,
    and none at all leaves no base period. Each refusal raises (fail closed)."""
    if module.module_id != CP2A:
        raise ValueError(f"CP-2G: not a CP-2A head: {module.module_id}")
    facts = {f.fact_id: f for f in module.facts}

    def rows(table_id: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(f.row_id for f in module.facts if f.table_id == table_id))

    scenarios = tuple(
        Cp2aScenario(
            row=row,
            name=_text_of(facts, f"T2B.1.{row}.name", CP2A),
            decline=_fact_of(facts, f"T2B.1.{row}.ebitda_decline", CP2A),
            increase=_fact_of(facts, f"T2B.1.{row}.interest_increase", CP2A),
        )
        for row in rows("T2B.1")
    )
    breaks = tuple(
        Cp2aBreak(
            row=row,
            origin=_text_of(facts, f"T2B.6.{row}.origin", CP2A),
            test=_text_of(facts, f"T2B.6.{row}.test", CP2A),
            level=_fact_of(facts, f"T2B.6.{row}.level", CP2A),
            required_decline=_fact_of(facts, f"T2B.6.{row}.required_decline", CP2A),
            outcome=_text_of(facts, f"T2B.6.{row}.outcome", CP2A),
        )
        for row in rows("T2B.6")
    )
    shocks = (f for s in scenarios for f in (s.decline, s.increase))
    periods = tuple(dict.fromkeys(f.period for f in shocks if f.period is not None))
    if len(periods) > 1:
        raise ValueError("CP-2G: CP-2A T2B.1 facts differ in period")
    if not periods:
        raise ValueError("CP-2G: CP-2A T2B.1 facts state no period")
    return Cp2aHead(base_period=periods[0], scenarios=scenarios, breaks=breaks)


def cp1d_of(module: Module, status: InputStatus) -> Cp1dHead:
    """A settled CP-1D module under its bound `status`: a blocked head is the state alone (it
    settled no supported earnings); otherwise the three supported facts (`CP1D_IDS`)."""
    if module.module_id != CP1D:
        raise ValueError(f"CP-2G: not a CP-1D head: {module.module_id}")
    if status == "blocked":
        return Cp1dHead(status="blocked")
    facts = {f.fact_id: f for f in module.facts}
    supported, total, net = (_fact_of(facts, fid, CP1D) for fid in CP1D_IDS)
    return Cp1dHead(status=status, supported=supported, total_leverage=total, net_leverage=net)


def _settled_module(store: Execution, head: Head, module_id: str) -> tuple[Module, InputStatus]:
    if head.module_id != module_id:
        raise ValueError(f"CP-2G: not a {module_id} head: {head.module_id}")
    status = _SETTLED.get(head.status)
    if status is None:
        raise ValueError(f"CP-2G: the {module_id} head is {head.status}")
    return store.head_module(head), status


def cp2a_reader(store: Execution, head: Head) -> Cp2aHead:
    """D3: the T2B.1 scenarios and T2B.6 breaks of a settled CP-2A head (`cp2a_of`). CP-2A is a
    required edge, so a blocked head is never bound and is refused here."""
    module, status = _settled_module(store, head, CP2A)
    if status == "blocked":
        raise ValueError("CP-2G: the CP-2A head is blocked")
    return cp2a_of(module)


def cp1d_reader(store: Execution, head: Head) -> Cp1dHead:
    """D3: T1D.3.supported.value and T1D.6.supported.total_leverage / net_leverage of a settled
    CP-1D head, or its blocked state (`cp1d_of`)."""
    module, status = _settled_module(store, head, CP1D)
    return cp1d_of(module, status)


@dataclass(frozen=True)
class Upstream:
    """What one CP-2G attempt binds, read once from the journal (`cp2g_upstream`).

    `bound` is the attempt's input set; `current` is `execution.current_inputs` now, or its
    refusal text; `cp1` the facts of the bound CP-1 head; `cp2a` and `cp1d` the bound heads as
    the core reads them (`Cp1dHead(status=None)` when CP-1D is not bound); `inherited` what
    settlement will carry from the bound heads (`execution.inherited_limitations`)."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp1: tuple[Fact, ...]
    cp2a: Cp2aHead
    cp1d: Cp1dHead
    inherited: tuple[str, ...] = ()

    def status(self, input_id: str) -> InputStatus | None:
        return next((item.status for item in self.bound if item.input_id == input_id), None)


def cp2g_upstream(*, store: Execution, attempt: Attempt) -> Upstream:
    """The bound CP-1, CP-2A and (when bound) CP-1D heads, the current input set and the
    inherited limitations. A refusal of `current_inputs` (an upstream gone stale, unrun or
    blocked, or CP-0 no longer authorizing CP-2G) is kept as text: the validator reports it as a
    staleness issue. A bound input whose blob is another module's raises."""
    snapshot = store.read()
    current: tuple[Input, ...] | str
    try:
        current = current_inputs(snapshot, MODULE_ID)
    except ValueError as error:  # NotAuthorized included: reported, never passed as current
        current = str(error)

    def bound(module_id: str) -> tuple[Module, InputStatus] | None:
        item = next((i for i in attempt.inputs if i.input_id == module_id), None)
        if item is None:
            return None
        module = store.result(item.sha256)
        if module.module_id != module_id:
            raise ValueError(
                f"The CP-2G attempt's {module_id} input is a {module.module_id} module"
            )
        return module, item.status

    cp1, cp2a, cp1d = bound(CP1), bound(CP2A), bound(CP1D)
    if cp1 is None or cp2a is None:
        raise ValueError("The CP-2G attempt binds no CP-1 or no CP-2A input")
    return Upstream(
        bound=attempt.inputs,
        current=current,
        cp1=cp1[0].facts,
        cp2a=cp2a_of(cp2a[0]),
        cp1d=Cp1dHead(status=None) if cp1d is None else cp1d_of(*cp1d),
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


def _required_status(upstream: Upstream, input_id: str) -> InputStatus:
    status = upstream.status(input_id)
    if status is None:
        raise ValueError(f"The CP-2G attempt binds no {input_id} input")
    return status


def _inputs(pack: PreparedPack, submission: ForwardSubmission, upstream: Upstream) -> ForwardInputs:
    """The store adapter: the CP-1 head's selected T4.10 LTM facts (`select_cp1`, in the head's
    order), the bound CP-2A and CP-1D heads, the bound statuses and the issuer name, as the
    Stage 1 `ForwardInputs` the core reads. Submit, probe and view reach the core only
    through this."""
    chosen = {f.fact_id for f in select_cp1(upstream.cp1).values()}
    context = ForwardContext(
        cp1_facts=tuple(f for f in upstream.cp1 if f.fact_id in chosen),
        cp2a=upstream.cp2a,
        cp1d=upstream.cp1d,
        cp1_status=_required_status(upstream, CP1),
        cp2a_status=_required_status(upstream, CP2A),
        names=(pack.run.issuer_name,),
        cp2d_status=upstream.status(CP2D),
    )
    return ForwardInputs(context=context, submission=submission)


def validate_forward(
    *, pack: PreparedPack, submission: ForwardSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Every issue of `submission` over the bound `upstream`: staleness alone when a bound
    upstream changed (ruling 10; no content check runs on a stale upstream), else the core's
    content issues in their pinned order; empty when it composes."""
    stale = stale_issues(bound=upstream.bound, current=upstream.current)
    if stale:
        return stale
    return content_issues(_inputs(pack, submission, upstream))


class ForwardReport(Contract):
    """The retained step output: the composed content bound to the pack and the submission."""

    schema_version: Literal["forward-credit-model/1"] = "forward-credit-model/1"
    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[ModuleClaim, ...]
    limitations: tuple[Text, ...]


# A table whose row labels are per row (T2H.2) or that can be empty (T2H.9) has fixed columns;
# every other T2H table takes its columns from its first row's facts (one field sequence a table).
_FIXED_COLUMNS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "T2H.2": (("value", "Value"), ("basis", "Basis"), ("check", "Check")),
    "T2H.9": (
        ("id", "Gap id"),
        ("gap", "Gap"),
        ("why_it_matters", "Why it matters"),
        ("affected_analysis", "Affected analysis"),
        ("severity", "Severity"),
        ("action", "Action"),
    ),
}
_VALUE_COLUMN = (TableColumn(field="value", label="Value"),)


def _report_table(table: Table, facts: Mapping[str, Fact]) -> ReportTable:
    fixed = _FIXED_COLUMNS.get(table.table_id)
    if fixed is not None:
        columns = tuple(TableColumn(field=f, label=label) for f, label in fixed)
    else:
        first = (facts[fid] for fid in table.rows[0].fact_ids)
        columns = tuple(TableColumn(field=f.field, label=f.label) for f in first)
    rows = tuple(TableRow(row_id=r.row_id, label=r.label, fact_ids=r.fact_ids) for r in table.rows)
    return ReportTable(table_id=table.table_id, title=table.title, columns=columns, rows=rows)


def _reference_facts(ref: RefTable) -> tuple[Fact, ...]:
    """The upstream facts verbatim under their own ids, placed in the reference table's cells
    (`references_rule`): only the table, row and field coordinates change."""
    return tuple(
        r.fact.model_copy(update={"table_id": ref.table_id, "row_id": r.row_id, "field": "value"})
        for r in ref.rows
    )


def _reference_table(ref: RefTable) -> ReportTable:
    return ReportTable(
        table_id=ref.table_id,
        title=ref.title,
        columns=_VALUE_COLUMN,
        rows=tuple(
            TableRow(row_id=r.row_id, label=r.label, fact_ids=(r.fact.fact_id,)) for r in ref.rows
        ),
        row_header=ref.row_header,
        limitation=ref.note,
    )


def forward_model(
    *, pack: PreparedPack, submission: ForwardSubmission, upstream: Upstream
) -> ForwardReport:
    """The composed report of a valid submission; raises ValueError on any issue."""
    issues = validate_forward(pack=pack, submission=submission, upstream=upstream)
    if issues:
        raise ValueError("; ".join(bounded_issues(issues)))
    result = compute(_inputs(pack, submission, upstream))
    cells = {c.fact.fact_id: c.fact for c in result.cells}
    return ForwardReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=(
            *(_report_table(t, cells) for t in result.tables),
            *(_reference_table(r) for r in result.references),
        ),
        facts=(*cells.values(), *(f for r in result.references for f in _reference_facts(r))),
        claims=tuple(
            ModuleClaim(claim_id=c.claim_id, text=c.text, citations=(), limitation=c.limitation)
            for c in result.claims
        ),
        limitations=result.own_limitations,
    )


def cp2g_module(report: ForwardReport, *, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-2G candidate: the report's tables and claims bound to `inputs`, then the
    submission's content hash (the owner-only settled tail, protocol section 2 `SCHEMAS`)."""
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


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands the journal and the verifier replays (its last step is
    the one under validation)."""
    submission, shape = _parsed(store.payload(attempt.steps[-1].payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    upstream = cp2g_upstream(store=store, attempt=attempt)
    issues = validate_forward(pack=pack, submission=submission, upstream=upstream)
    if issues:
        return StepValidation(issues=issues)
    report = forward_model(pack=pack, submission=submission, upstream=upstream)
    return StepValidation(output=report.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _submit_step(store: Execution, ticket_id: str, payload: str) -> Attempt:
    """Retain the one `forward_credit_model` response, validate it, then settle CP-2G with the
    Python candidate (as `cp2a._submit_step`). An invalid step finishes the attempt rejected
    (blocked on the repair): there is no within-attempt repair. A crash after the step resumes
    from the retained step."""
    attempt = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if attempt is None or attempt.module_id != MODULE_ID or attempt.status != "pending":
        raise ValueError("Ticket is absent, finished or belongs to another module")
    if (
        attempt.steps
        and attempt.steps[0].payload_sha256 != hashlib.sha256(payload.encode()).hexdigest()
    ):
        raise ValueError("Ticket already retains a different response; resume or interrupt")
    if not attempt.steps or attempt.steps[0].status == "pending":
        attempt = store.submit_step(
            ticket_id,
            MODULE_ID,
            STEP_IDS,
            STEP_ID,
            payload,
            lambda pack, current: _validate_step(store, pack, current),
        )
    if attempt.status == "finished":
        return attempt
    outcome = _validate_step(store, store.pack(), attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise ValueError("Retained CP-2G output differs from trusted validation")
    candidate = _candidate(outcome.output or "", attempt)
    return store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP-2G candidate differs",),
        qualification=QUALIFICATION,
    )


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal one `forward_credit_model` payload: null resolution against the model-facing
    schema, then the validated step and, when valid, the settlement. CP-2G has no tool-loop
    rules."""
    if rules is not None:
        raise ValueError("CP-2G has no tool-loop rules (rule mode none)")
    if step_id != STEP_ID:
        raise ValueError(f"CP-2G has one step, {STEP_ID}")
    normalised, resolved = normalise(ForwardSubmission, payload)
    journal = _submit_step(store, ticket_id, normalised)
    return Submitted(journal, normalised, resolved, (), (), None)


def _candidate(output: str, attempt: Attempt) -> Module:
    return cp2g_module(
        ForwardReport.model_validate_json(output), inputs=attempt.inputs, attempt=attempt.number
    )


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


# --- the exact `read_inputs` view (lease Tool use; manifest.json tool_use.view_tree_draft) -----

_BOUNDS: Mapping[object, dict[str, object]] = {
    GrowthDriver: {"min": "-1", "max": "1", "places": 4},
    FractionDriver: {"min": "0", "max": "1", "places": 4},
    AmountDriver: {"min": "0", "max": "999999.9999", "places": 4},
}
BREAK_METRICS_OFFERED = ("total_leverage", "net_leverage", "interest_coverage")


def _cell(fact: Fact, referencable_ids: frozenset[str]) -> dict[str, object]:
    return {
        "ref": fact.fact_id if fact.fact_id in referencable_ids else None,
        "shown": spelled(fact) if fact.status == "known" else None,
        "status": fact.status,
        "limitation": fact.limitation,
    }


def _shown(fact: Fact) -> dict[str, object]:
    return {"shown": spelled(fact) if fact.status == "known" else None, "status": fact.status}


def _figure(fact: Fact) -> dict[str, object]:
    return {
        "ref": fact.fact_id,
        "label": fact.label,
        "period": fact.period,
        "unit": figure_unit(fact) or fact.unit,
        "shown": spelled(fact),
    }


def context_block(*, pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """What `read_inputs` returns, all Python's (lease Tool use): the upstream statuses, the
    CP-1 twelve-month base with each operand and reported ratio, the driver bounds, the CP-2A
    scenarios and breaks, the CP-1D supported figures when bound, the break metrics offered, the
    figures a reference may name and the limitations settlement will inherit. Missing facts are
    offered with their status. No quote, citation or record. `pack` is part of the lease
    signature; the view reads none of it."""
    del pack
    base = select_cp1(upstream.cp1)
    cp1d = upstream.cp1d.facts()
    allowed = frozenset(f.fact_id for f in referencable(base.values()))
    operands = CP1_METRICS[: len(OPERAND_METRIC)]
    supported = dict(
        zip(("supported_ebitda", "supported_total_leverage", "supported_net_leverage"), cp1d or ())
    )
    return {
        "upstream": [
            {"module_id": item.input_id, "status": item.status}
            for item in upstream.bound
            if item.input_id.startswith("CP-")
        ],
        "base": {
            "period": LTM_PERIOD,
            "forecast_periods": list(FY),
            "operands": {m: _cell(base[m], allowed) for m in operands},
            "ratios": {m: _cell(base[m], allowed) for m in CP1_METRICS[len(operands) :]},
        },
        "drivers": [
            *(
                {
                    "name": name,
                    "label": DRIVER_LABEL[name],
                    "unit_class": DRIVER_UNIT[name],
                    "bounds": _BOUNDS[BaseDrivers.model_fields[name].annotation],
                }
                for name in DRIVERS
            ),
            {
                "name": "minimum_liquidity",
                "label": "Minimum liquidity",
                "unit_class": "amount",
                "bounds": _BOUNDS[AmountDriver],
                "may_be_not_assessed": True,
            },
        ],
        "cp2a": {
            "base_period": upstream.cp2a.base_period,
            "scenarios": [
                {
                    "row": s.row,
                    "name": s.name,
                    "ebitda_decline": _shown(s.decline),
                    "interest_increase": _shown(s.increase),
                }
                for s in upstream.cp2a.scenarios
            ],
            "breaks": [
                {
                    "row": b.row,
                    "origin": b.origin,
                    "test": b.test,
                    "level": _shown(b.level),
                    "required_decline": {
                        **_shown(b.required_decline),
                        "limitation": b.required_decline.limitation,
                    },
                    "outcome": b.outcome,
                }
                for b in upstream.cp2a.breaks
            ],
        },
        "cp1d": {
            "state": upstream.cp1d.state,
            **{
                key: None
                if key not in supported
                else {"ref": supported[key].fact_id, "shown": _shown(supported[key])["shown"]}
                for key in (
                    "supported_ebitda",
                    "supported_total_leverage",
                    "supported_net_leverage",
                )
            },
        },
        "break_metrics_offered": list(BREAK_METRICS_OFFERED),
        "cp1_facts": [_figure(f) for f in base.values() if f.fact_id in allowed],
        "cp1d_facts": [_figure(f) for f in referencable(cp1d or ())],
        "inherited_limitations": list(upstream.inherited),
    }


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the one `read_inputs` record, as compact JSON (S1a lease rev 2, M4)."""
    upstream = cp2g_upstream(store=historical, attempt=attempt)
    context = context_block(pack=historical.pack(), upstream=upstream)
    body = json.dumps(context, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


# --- the consumer reader pinned for CP-2H and CP-4C (lease Consumption; round 13 item 2) ------


@dataclass(frozen=True)
class Cp2gHead:
    """What a consumer reads from a settled CP-2G head: its status and hash, the pinned facts
    verbatim (`_reader_ids`), the T2H.7 break rows, and the settled own limitations (with the
    synthetic line on a synthetic case). A blocked head gives its status and hash only (round 5
    item 9 L2)."""

    status: InputStatus
    head_sha256: str
    facts: tuple[Fact, ...] = ()
    break_rows: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def fact(self, fact_id: str) -> Fact:
        found = next((f for f in self.facts if f.fact_id == fact_id), None)
        if found is None:
            raise ValueError(f"CP-2G: {fact_id} is not exposed by the reader")
        return found


def _reader_ids(break_rows: Sequence[str]) -> tuple[str, ...]:
    """Per case and year revenue, EBITDA and free cash flow (T2H.4, with the FY2025 actual),
    cash interest, closing debt and cash and accessible liquidity (T2H.5), the four ratios
    (T2H.6, with the actual), each T2H.7 first year, the T2H.8 trajectory, and the two T2H.3
    source texts that name the CP-2A row (lease amendment, round 13 item 2)."""
    years = (*_rows("base"), *_rows("down"))
    return (
        *(f"T2H.4.{r}.{f}" for r in (A25, *years) for f in ("revenue", "ebitda", "fcf")),
        *(
            f"T2H.5.{r}.{f}"
            for r in years
            for f in ("interest", "closing_debt", "closing_cash", "accessible_liquidity")
        ),
        *(
            f"T2H.6.{r}.{f}"
            for r in (A25, *years)
            for f in ("total_leverage", "net_leverage", "interest_coverage", "fcf_to_debt")
        ),
        *(f"T2H.7.{r}.{case}_first" for r in break_rows for case in CASES),
        *(
            f"T2H.8.{case}.{f}"
            for case in CASES
            for f in (
                "trajectory",
                "total_leverage_fy28",
                "change_vs_fy25",
                "peak_total_leverage",
                "peak_period",
            )
        ),
        "T2H.3.d01.source",
        "T2H.3.d02.source",
    )


def cp2g_reader(store: Execution, head: Head) -> Cp2gHead:
    """The consumer reader of a settled CP-2G head (lease Public API). A stale head or another
    module's head raises."""
    module, status = _settled_module(store, head, MODULE_ID)
    if status == "blocked":
        return Cp2gHead(status=status, head_sha256=head.result_sha256)
    t2h7 = next((t for t in module.tables if t.table_id == "T2H.7"), None)
    if t2h7 is None:
        raise ValueError("CP-2G: the settled head has no table T2H.7")
    rows = tuple(r.row_id for r in t2h7.rows)
    facts = {f.fact_id: f for f in module.facts}
    return Cp2gHead(
        status=status,
        head_sha256=head.result_sha256,
        facts=tuple(_fact_of(facts, fid, MODULE_ID) for fid in _reader_ids(rows)),
        break_rows=rows,
        limitations=module.limitations,
    )
