"""Reader for the context form's ``context.json`` (schema ``context/1``).

``docs/templates/context-form.html`` (its ``build()``) is the normative rule set; each bound
below is copied from it. Numbers stay strings in the model; ``amount`` turns one into a
``Decimal``. An empty string means "not supplied", never zero.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Literal

from pydantic import ValidationError

from deploy_vii.contracts import Contract, PathwayId

SCHEMA = "context/1"
NUM = r"^\d+(\.\d+)?$"
SNUM = r"^-?\d+(\.\d+)?$"
PERIOD = r"^(q[1-4]|h[12]|fy)-(\d{4})$"
SLUG = r"^[a-z0-9][a-z0-9-]*$"
_DATE = r"^\d{4}-\d{2}-\d{2}$"
_CURRENCY = r"^[A-Z]{3}$"
_INT = r"^-?\d+$"
# JSON.stringify writes these raw, and str.splitlines() splits on them (R-P1b).
_LINE_BREAKS = ("\u0085", " ", " ")

RunType = Literal["primary", "secondary", "research", "earnings"]
CaseKind = Literal["public", "private", "synthetic"]
PeerSource = Literal["cp_dr_public", "user_list", "user_comps", "none"]
Basis = Literal["auto", "public_comps", "precedents", "blend", "issuer_trading", "user_multiple"]
EbitdaBasis = Literal["LTM", "NTM"]
LegalDocuments = Literal["executed", "draft", "none"]
QuoteKind = Literal["observed", "indicative_talk"]
RatingScope = Literal["issuer", "facility"]

# Row maxima: ROWS[...].max in the form.
_MAX_DEAL, _MAX_QUOTE, _MAX_RATING, _MAX_PEER = 20, 40, 20, 30
_MAX_PREC, _MAX_SCEN, _MAX_Q = 30, 4, 10


class ContextRefused(ValueError):
    """The file breaks a rule; ``problems`` lists each as ``"<json.path>: <message>"``."""

    def __init__(self, problems: tuple[str, ...] | list[str]) -> None:
        self.problems: tuple[str, ...] = tuple(problems)
        super().__init__("; ".join(self.problems))


class RunSettings(Contract):
    run_type: RunType
    pathway: PathwayId
    case_kind: CaseKind
    as_of: str
    current_period: str
    prior_period: str
    reporting_currency: str


class Identity(Contract):
    issuer_name: str
    issuer_id: str
    borrower_name: str
    parent_name: str
    guarantors: tuple[str, ...]
    aliases: tuple[str, ...]
    listed_equity: bool
    ticker: str
    sector: str
    country: str
    sponsor: str


class DealTerm(Contract):
    facility_id: str
    instrument: str
    currency: str
    size_m: str
    tenor_years: str
    talk_spread_bps_low: str
    talk_spread_bps_high: str
    talk_oid_low: str
    talk_oid_high: str
    floor_pct: str
    call_protection: str
    use_of_proceeds: str
    as_of: str
    provider: str


class Quote(Contract):
    facility_id: str
    kind: QuoteKind
    bid: str
    ask: str
    price: str
    yield_pct: str
    spread_bps: str
    as_of: str
    provider: str


class Rating(Contract):
    agency: str
    scope: RatingScope
    rating: str
    outlook: str
    as_of: str


class IssuerMarket(Contract):
    market_cap_m: str
    net_debt_m: str
    ev_m: str
    ebitda_basis: EbitdaBasis
    as_of: str
    source: str


class PeerRow(Contract):
    name: str
    ticker: str
    ev_m: str
    ebitda_m: str
    as_of: str
    source: str


class Precedent(Contract):
    target: str
    acquirer: str
    date: str
    ev_m: str
    ebitda_m: str
    source: str


class UserMultiple(Contract):
    value: str
    basis: EbitdaBasis
    rationale: str


class Valuation(Contract):
    peer_source: PeerSource
    basis: Basis
    issuer_market: IssuerMarket
    peers: tuple[PeerRow, ...]
    precedents: tuple[Precedent, ...]
    user_multiple: UserMultiple


class Cp2aScenario(Contract):
    ebitda_decline_pct: str
    interest_increase_pct: str


class Cp2aPins(Contract):
    scenarios: tuple[Cp2aScenario, ...]
    rationale: str


class Cp2dPins(Contract):
    horizon_months: str
    minimum_cash_m: str
    rationale: str


class Cp2ePins(Contract):
    rate_shocks_bps: tuple[str, ...]
    fx_shocks_pct: tuple[str, ...]
    hedge_ratio_pct: str
    rationale: str


class Cp3cPins(Contract):
    repricing_bps: str
    rationale: str


class Cp3dPins(Contract):
    recovery_pct: str
    rationale: str


class Cp4cPins(Contract):
    ev_multiple: str
    rationale: str


class Assumptions(Contract):
    cp2a: Cp2aPins | None
    cp2d: Cp2dPins | None
    cp2e: Cp2ePins | None
    cp3c: Cp3cPins | None
    cp3d: Cp3dPins | None
    cp4c: Cp4cPins | None


class Attachments(Contract):
    portfolio_workbook: bool
    prior_case: bool
    management_bridge: bool
    legal_documents: LegalDocuments


class ResearchQuestion(Contract):
    text: str
    focus_module: str


class RunContext(Contract):
    run: RunSettings
    identity: Identity
    deal_terms: tuple[DealTerm, ...]
    quotes: tuple[Quote, ...]
    ratings: tuple[Rating, ...]
    valuation: Valuation
    assumptions: Assumptions
    attachments: Attachments
    research_questions: tuple[ResearchQuestion, ...]


def amount(text: str) -> Decimal | None:
    """Parse a form number; the empty string is "not supplied", not zero."""
    return None if text == "" else Decimal(text)


# ---------------------------------------------------------------------------------- parsing


def _match(pattern: str, value: str) -> bool:
    """R-P1a: ASCII-only, whole-string match (the form's JS does neither \\d widening nor
    the trailing-newline allowance of ``$``)."""
    return re.fullmatch(pattern, value, re.ASCII) is not None


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContextRefused([f"$: duplicate key {key!r}"])
        out[key] = value
    return out


def _refuse_constant(name: str) -> Any:
    raise ContextRefused([f"$: {name} is not valid JSON"])


def _path(loc: tuple[int | str, ...]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def _join(base: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{base}[{key}]"
    return f"{base}.{key}" if base else key


def _line_break_problems(node: Any, path: str, out: list[str]) -> None:
    if isinstance(node, str):
        if any(c in node for c in _LINE_BREAKS):
            out.append(f"{path}: contains a line separator (U+0085, U+2028 or U+2029).")
    elif isinstance(node, dict):
        for key, value in node.items():
            _line_break_problems(value, _join(path, key), out)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _line_break_problems(value, _join(path, index), out)


def load_context(raw: bytes) -> RunContext:
    """Parse and validate ``context.json``; raise ``ContextRefused`` listing every problem.

    Shape problems (unknown keys, wrong types, bad enum values) and the form's value rules
    are reported in two passes: the value rules need a well-shaped file to run on.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContextRefused([f"$: not valid UTF-8 ({exc.reason})"]) from exc
    try:
        obj = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_refuse_constant)
    except json.JSONDecodeError as exc:
        raise ContextRefused([f"$: not valid JSON ({exc.msg} at line {exc.lineno})"]) from exc
    if not isinstance(obj, dict):
        raise ContextRefused(["$: the top level must be an object."])

    problems: list[str] = []
    if obj.pop("schema", None) != SCHEMA:
        problems.append(f"schema: must be {SCHEMA!r}.")
    _line_break_problems(obj, "", problems)
    try:
        ctx = RunContext.model_validate_json(json.dumps(obj))
    except ValidationError as exc:
        problems.extend(f"{_path(e['loc'])}: {e['msg']}" for e in exc.errors())
        raise ContextRefused(problems) from exc
    problems.extend(_Rules(ctx).run())
    if problems:
        raise ContextRefused(problems)
    return ctx


# ---------------------------------------------------------------------------- value rules


class _Rules:
    """The form's ``build()`` rules over a well-shaped context; collects every problem."""

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.problems: list[str] = []
        self.as_of = ctx.run.as_of

    def bad(self, path: str, message: str) -> None:
        self.problems.append(f"{path}: {message}")

    # -- field readers (the form's fld) ------------------------------------------------

    def text(self, path: str, value: str, req: bool = False) -> None:
        if req and not value.strip():
            self.bad(path, "required.")

    def number(
        self,
        path: str,
        value: str,
        *,
        req: bool = False,
        signed: bool = False,
        whole: bool = False,
        low: str | None = None,
        low_excl: str | None = None,
        high: str | None = None,
        high_excl: str | None = None,
    ) -> None:
        if value == "":
            if req:
                self.bad(path, "required.")
            return
        message = _num_message(value, signed, whole, low, low_excl, high, high_excl)
        if message:
            self.bad(path, message)

    def date(self, path: str, value: str, req: bool = False, after: bool = False) -> None:
        if value == "":
            if req:
                self.bad(path, "required.")
            return
        if not _valid_date(value):
            self.bad(path, "enter a date as YYYY-MM-DD.")
        elif after and _valid_date(self.as_of) and value > self.as_of:
            self.bad(
                path,
                f"is after the run as-of date ({self.as_of}); sources dated after it are refused.",
            )

    def currency(self, path: str, value: str, req: bool = False) -> None:
        if value == "":
            if req:
                self.bad(path, "required.")
        elif not _match(_CURRENCY, value):
            self.bad(path, "use three uppercase letters, such as USD.")

    def shocks(self, path: str, items: tuple[str, ...], high: str, whole: bool) -> None:
        if not items:
            self.bad(path, "required.")
        if len(items) > 3:
            self.bad(path, "give at most 3 values.")
        for item in items:
            message = _num_message(item, False, whole, "1", None, high, None)
            if message:
                self.bad(path, f'"{item}": {message}')

    def not_above(self, path: str, low: str, high: str, message: str) -> None:
        if _match(NUM, low) and _match(NUM, high) and Decimal(low) > Decimal(high):
            self.bad(path, message)

    # -- sections ----------------------------------------------------------------------

    def run(self) -> list[str]:
        self.run_section()
        self.identity_section()
        self.deal_section()
        self.quote_and_rating_section()
        self.valuation_section()
        self.assumptions_section()
        self.attachments_and_questions()
        return self.problems

    def run_section(self) -> None:
        run = self.ctx.run
        self.date("run.as_of", run.as_of, req=True)
        earnings = run.run_type == "earnings"
        for name in ("current_period", "prior_period"):
            value = getattr(run, name)
            if value == "":
                if earnings:
                    self.bad(f"run.{name}", "required.")
            elif not _match(PERIOD, value):
                self.bad(f"run.{name}", "use q1-2026, h2-2026 or fy-2025 (lowercase).")
        a, b = _period_key(run.current_period), _period_key(run.prior_period)
        if a and b and a[0] == b[0] and (b[2] > a[2] or (b[2] == a[2] and b[1] >= a[1])):
            self.bad("run.prior_period", "must be earlier than the current period.")
        self.currency("run.reporting_currency", run.reporting_currency, req=True)

    def identity_section(self) -> None:
        ident = self.ctx.identity
        self.text("identity.issuer_name", ident.issuer_name, req=True)
        if ident.issuer_id == "":
            self.bad("identity.issuer_id", "required.")
        elif not _match(SLUG, ident.issuer_id):
            self.bad(
                "identity.issuer_id",
                "use lowercase letters, digits and hyphens only, not starting with a hyphen.",
            )
        if ident.ticker and not ident.listed_equity:
            self.bad("identity.ticker", "must be empty for an unlisted issuer.")

    def deal_section(self) -> None:
        deals = self.ctx.deal_terms
        if self.ctx.run.run_type != "primary":
            if deals:
                self.bad("deal_terms", "deal rows belong to a primary run only.")
            return
        if not deals:
            self.bad("deal_terms", "add at least one facility row.")
        self.too_many("deal_terms", len(deals), _MAX_DEAL)
        for i, d in enumerate(deals):
            p = f"deal_terms[{i}]"
            self.currency(f"{p}.currency", d.currency)
            for name in (
                "size_m",
                "tenor_years",
                "talk_spread_bps_low",
                "talk_spread_bps_high",
                "talk_oid_low",
                "talk_oid_high",
                "floor_pct",
            ):
                self.number(f"{p}.{name}", getattr(d, name), low="0")
            self.date(f"{p}.as_of", d.as_of, after=True)
            self.not_above(
                f"{p}.talk_spread_bps_low",
                d.talk_spread_bps_low,
                d.talk_spread_bps_high,
                "low must not exceed high.",
            )
            self.not_above(
                f"{p}.talk_oid_low", d.talk_oid_low, d.talk_oid_high, "low must not exceed high."
            )

    def too_many(self, path: str, count: int, limit: int) -> None:
        if count > limit:
            self.bad(path, f"give at most {limit} rows.")

    def quote_and_rating_section(self) -> None:
        self.too_many("quotes", len(self.ctx.quotes), _MAX_QUOTE)
        for i, q in enumerate(self.ctx.quotes):
            p = f"quotes[{i}]"
            for name in ("bid", "ask", "price", "yield_pct", "spread_bps"):
                self.number(f"{p}.{name}", getattr(q, name), low="0")
            self.date(f"{p}.as_of", q.as_of, req=True, after=True)
            self.text(f"{p}.provider", q.provider, req=True)
            self.not_above(f"{p}.bid", q.bid, q.ask, "bid must not exceed ask.")
        self.too_many("ratings", len(self.ctx.ratings), _MAX_RATING)
        for i, r in enumerate(self.ctx.ratings):
            p = f"ratings[{i}]"
            self.text(f"{p}.agency", r.agency, req=True)
            self.text(f"{p}.rating", r.rating, req=True)
            self.date(f"{p}.as_of", r.as_of, after=True)

    def valuation_section(self) -> None:
        val = self.ctx.valuation
        self.peers(val)
        self.too_many("valuation.precedents", len(val.precedents), _MAX_PREC)
        if val.basis in ("precedents", "blend"):
            for i, pr in enumerate(val.precedents):
                p = f"valuation.precedents[{i}]"
                self.text(f"{p}.target", pr.target, req=True)
                self.date(f"{p}.date", pr.date, after=True)
                self.number(f"{p}.ev_m", pr.ev_m, req=True, low="0")
                self.number(f"{p}.ebitda_m", pr.ebitda_m, req=True, low_excl="0")
                self.text(f"{p}.source", pr.source, req=True)
        if val.basis == "issuer_trading":
            self.issuer_market(val.issuer_market)
        if val.basis == "user_multiple":
            um = val.user_multiple
            self.number(
                "valuation.user_multiple.value", um.value, req=True, low_excl="0", high="99.99"
            )
            self.text("valuation.user_multiple.rationale", um.rationale, req=True)

    def peers(self, val: Valuation) -> None:
        self.too_many("valuation.peers", len(val.peers), _MAX_PEER)
        if val.peer_source in ("none", "cp_dr_public"):
            if val.peers:
                self.bad("valuation.peers", f"must be empty when peer_source is {val.peer_source}.")
            return
        for i, peer in enumerate(val.peers):
            p = f"valuation.peers[{i}]"
            self.text(f"{p}.name", peer.name, req=True)
            if val.peer_source == "user_comps":
                self.number(f"{p}.ev_m", peer.ev_m, req=True, low="0")
                self.number(f"{p}.ebitda_m", peer.ebitda_m, req=True, low_excl="0")
                self.date(f"{p}.as_of", peer.as_of, req=True, after=True)
                self.text(f"{p}.source", peer.source, req=True)

    def issuer_market(self, im: IssuerMarket) -> None:
        p = "valuation.issuer_market"
        if not self.ctx.identity.listed_equity:
            self.bad("valuation.basis", "issuer_trading needs a listed issuer.")
        self.number(f"{p}.market_cap_m", im.market_cap_m, low="0")
        self.number(f"{p}.net_debt_m", im.net_debt_m, signed=True)
        self.number(f"{p}.ev_m", im.ev_m, low_excl="0")
        self.date(f"{p}.as_of", im.as_of, req=True, after=True)
        self.text(f"{p}.source", im.source, req=True)
        if not im.ev_m and not (im.market_cap_m and im.net_debt_m):
            self.bad(f"{p}.ev_m", "give EV, or both market cap and net debt.")

    def assumptions_section(self) -> None:
        a = self.ctx.assumptions
        if a.cp2a is not None:
            n = len(a.cp2a.scenarios)
            if not 1 <= n <= _MAX_SCEN:
                self.bad("assumptions.cp2a.scenarios", "add 1 to 4 scenarios.")
            for i, s in enumerate(a.cp2a.scenarios):
                p = f"assumptions.cp2a.scenarios[{i}]"
                self.number(
                    f"{p}.ebitda_decline_pct", s.ebitda_decline_pct, req=True, low="0", high="100"
                )
                self.number(
                    f"{p}.interest_increase_pct",
                    s.interest_increase_pct,
                    req=True,
                    low="0",
                    high="100",
                )
            self.text("assumptions.cp2a.rationale", a.cp2a.rationale, req=True)
        if a.cp2d is not None:
            p = "assumptions.cp2d"
            self.number(
                f"{p}.horizon_months",
                a.cp2d.horizon_months,
                req=True,
                whole=True,
                low="1",
                high="60",
            )
            self.number(f"{p}.minimum_cash_m", a.cp2d.minimum_cash_m, req=True, low="0")
            self.text(f"{p}.rationale", a.cp2d.rationale, req=True)
        if a.cp2e is not None:
            p = "assumptions.cp2e"
            self.shocks(f"{p}.rate_shocks_bps", a.cp2e.rate_shocks_bps, "1000", True)
            self.shocks(f"{p}.fx_shocks_pct", a.cp2e.fx_shocks_pct, "50", False)
            self.number(f"{p}.hedge_ratio_pct", a.cp2e.hedge_ratio_pct, low="0", high="100")
            self.text(f"{p}.rationale", a.cp2e.rationale, req=True)
        if a.cp3c is not None:
            p = "assumptions.cp3c"
            self.number(f"{p}.repricing_bps", a.cp3c.repricing_bps, req=True, low="0", high="1000")
            self.text(f"{p}.rationale", a.cp3c.rationale, req=True)
        if a.cp3d is not None:
            p = "assumptions.cp3d"
            self.number(
                f"{p}.recovery_pct", a.cp3d.recovery_pct, req=True, low="0", high_excl="100"
            )
            self.text(f"{p}.rationale", a.cp3d.rationale, req=True)
        if a.cp4c is not None:
            p = "assumptions.cp4c"
            self.number(
                f"{p}.ev_multiple", a.cp4c.ev_multiple, req=True, low_excl="0", high="99.99"
            )
            self.text(f"{p}.rationale", a.cp4c.rationale, req=True)

    def attachments_and_questions(self) -> None:
        questions = self.ctx.research_questions
        self.too_many("research_questions", len(questions), _MAX_Q)
        for i, q in enumerate(questions):
            self.text(f"research_questions[{i}].text", q.text, req=True)


def _valid_date(value: str) -> bool:
    if not _match(_DATE, value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _period_key(value: str) -> tuple[str, int, int] | None:
    m = re.fullmatch(PERIOD, value, re.ASCII)
    if m is None:
        return None
    return m[1][0], 0 if m[1] == "fy" else int(m[1][1]), int(m[2])


def _num_message(
    value: str,
    signed: bool,
    whole: bool,
    low: str | None,
    low_excl: str | None,
    high: str | None,
    high_excl: str | None,
) -> str:
    """The form's ``numMsg``, comparing as ``Decimal``."""
    if "," in value:
        return "no thousands separators; write 1250, not 1,250."
    if not _match(SNUM if signed else NUM, value):
        return "enter a plain number such as 1250 or 99.5."
    if whole and not _match(_INT, value):
        return "enter a whole number."
    x = Decimal(value)
    checks: tuple[tuple[str | None, Callable[[Decimal, Decimal], bool], str], ...] = (
        (low, lambda a, b: a < b, "must be {} or more."),
        (low_excl, lambda a, b: a <= b, "must be above {}."),
        (high, lambda a, b: a > b, "must be {} or less."),
        (high_excl, lambda a, b: a >= b, "must be below {}."),
    )
    for bound, failed, template in checks:
        if bound is not None and failed(x, Decimal(bound)):
            return template.format(bound)
    return ""
