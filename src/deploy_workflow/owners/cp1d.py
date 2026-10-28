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

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, InvalidOperation, Rounded
from typing import Literal

from deploy_vii.contracts import Citation, Contract, Fact, Source, Text
from deploy_vii.display import UnitClass, format_value
from deploy_vii.prose import bind
from deploy_vii.prose import issues as prose_issues
from deploy_vii.readiness import citation_issues

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
    category: Text
    rationale: Text
    evidence: tuple[Citation, ...]
    limitation: str | None


class Overall(Contract):
    rationale: Text
    category: Text
    confidence: Text
    limitation: str | None
    evidence: tuple[Citation, ...]


class Gap(Contract):
    gap: Text
    why_it_matters: Text
    affected_analysis: Text
    severity: Text
    action: Text


class EarningsQualitySubmission(Contract):
    assessments: tuple[Assessment, ...]
    overall: Overall
    gaps: tuple[Gap, ...]


# --- inputs ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cp1Figure:
    """One CP-1 T4.10 fact (manifest `cp1_fact_selection_rule`), referenced as `cp1:<figure>`."""

    figure: str
    label: str
    unit: str
    period: str
    amount: Decimal
    value_class: ValueClass
    currency: str | None = None


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
    amount: Decimal
    shown: str
    value_class: ValueClass
    status: Literal["known"] = "known"

    @property
    def amount_exact(self) -> str:
        return exact_text(self.amount)


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


class _Unparseable(ValueError):
    pass


def _bridge_amount(token: str) -> Decimal | None:
    if token == _NOT_STATED:
        return None
    if not _AMOUNT.fullmatch(token):
        raise _Unparseable(token)
    return Decimal(token)


def parse_bridge(pages: Sequence[str]) -> Bridge | None:
    """The bridge table on page:1, or None when it cannot be read (`Bridge table not found`).

    Page:1 must have a line starting with the FY2025 basis and the exact header line; every
    later line splits on two or more spaces into an item (4 fields) or one of the two stated
    totals (2 fields). An amount is a decimal or `Not stated` (missing, never 0).
    """
    lines = pages[0].split("\n") if pages else []
    if not any(line.startswith(_BASIS_LINE) for line in lines) or _HEADER not in lines:
        return None
    items: list[BridgeItem] = []
    totals: dict[str, Decimal | None] = {}
    try:
        for line in lines[lines.index(_HEADER) + 1 :]:
            parts = _FIELDS.split(line)
            if len(parts) == 4:
                label, kind, status, amount = parts
                row_id = f"a{len(items) + 1:02d}"
                items.append(BridgeItem(row_id, label, kind, status, _bridge_amount(amount), line))
            elif len(parts) == 2 and parts[0] in (_PROPOSED_TOTAL, _MANAGEMENT_EBITDA):
                if parts[0] in totals:
                    return None
                totals[parts[0]] = _bridge_amount(parts[1])
            else:
                return None
    except _Unparseable:
        return None
    if len({item.label for item in items}) != len(items):
        return None
    return Bridge(tuple(items), totals.get(_PROPOSED_TOTAL), totals.get(_MANAGEMENT_EBITDA))


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


def _basis_amounts(citation: Citation) -> list[str]:
    return _AMOUNT.findall(citation.quote)


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


def _outcome(item: BridgeItem, assessment: Assessment) -> _Outcome:
    """Applied fraction and accepted amount of a shape-valid assessment (lease recipe table)."""
    if assessment.achievability == "Partly supported" and assessment.recurrence == "Recurring":
        raise ValueError(
            f"Partly supported with Recurring is not specified by the lease: {item.label}"
        )
    if not _accepts(assessment):
        return _Outcome(item, assessment, "rule", Decimal(0), None, Decimal(0))
    claimed = item.amount
    if claimed is None:
        raise ValueError(f"Cannot accept an unstated amount: {item.label}")
    if assessment.achievability == "Supported":
        return _Outcome(item, assessment, "rule", Decimal(1), None, _EXACT.multiply(claimed, 1))
    if assessment.accepted_basis is not None:
        basis = Decimal(_basis_amounts(assessment.accepted_basis)[0])
        return _Outcome(item, assessment, "source", _quotient(basis, claimed), basis, basis)
    if assessment.accepted_fraction is None:
        raise ValueError(f"Partly supported without basis or fraction: {item.label}")
    fraction = Decimal(assessment.accepted_fraction)
    accepted = _EXACT.multiply(claimed, fraction)
    return _Outcome(item, assessment, "judgment", fraction, None, accepted)


def _shape_issue(item: BridgeItem, assessment: Assessment) -> str | None:
    """The first failing basis/fraction shape rule (`refusal_rules.basis_fraction_order`)."""
    label = item.label
    basis, fraction = assessment.accepted_basis, assessment.accepted_fraction
    if assessment.achievability != "Partly supported":
        if basis is not None:
            return f"Accepted basis only applies to Partly supported: {label}"
        if fraction is not None:
            return f"Accepted fraction only applies to Partly supported: {label}"
        return None
    if basis is not None and fraction is not None:
        return f"Give either an accepted basis or an accepted fraction, not both: {label}"
    if basis is None and fraction is None:
        return f"Accepted basis or accepted fraction required for Partly supported: {label}"
    if fraction is not None and not (_FRACTION.fullmatch(fraction) and Decimal(fraction) > 0):
        return (
            "Accepted fraction must be a decimal above 0 and below 1 with at most two places: "
            f"{label}"
        )
    if basis is not None:
        amounts = _basis_amounts(basis)
        if len(amounts) != 1:
            return f"Accepted basis quote must contain exactly one amount: {label}"
        # An unstated proposed amount is the content rule `Cannot accept an unstated amount`.
        if item.amount is not None and not 0 < Decimal(amounts[0]) < item.amount:
            return f"Accepted basis must be above 0 and below the proposed amount: {label}"
    return None


def _rule_issues(item: BridgeItem, assessment: Assessment) -> list[str]:
    """Content rules of one shape-valid assessment, before its citations and prose."""
    label, recurrence = item.label, assessment.recurrence
    found: list[str] = []
    if _accepts(assessment) and item.amount is None:
        found.append(f"Cannot accept an unstated amount: {label}")
    if _accepts(assessment) and not assessment.evidence:
        found.append(f"Evidence required for an accepted add-back: {label}")
    fits = {"Saving": ("Not applicable",), "Cost": ("Non-recurring", "Recurring", "Not assessable")}
    if recurrence not in fits.get(item.type, ()):
        found.append(f"Recurrence does not fit the add-back type: {label}")
    if recurrence == "Not assessable" and assessment.achievability != "Insufficient evidence":
        found.append(f"Recurrence can be not assessable only with insufficient evidence: {label}")
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
        raise ValueError(f"Source without a hash: {source.source_id}")
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
            out.row("T1D.1", row, item.label, ("type", "status", "claimed"))
    recorded = _EXACT.subtract(cp1.adjusted_ebitda.amount, cp1.ebitda.amount)
    out.text(("T1D.1", "stmt", "type", "Type"), "Statement adjustment")
    out.text(("T1D.1", "stmt", "status", "Status"), "Recorded")
    out.number(
        ("T1D.1", "stmt", "claimed", "Recorded amount"),
        recorded,
        "MILLIONS",
        "CP-1 adjusted_ebitda minus ebitda",
        ("cp1:adjusted_ebitda_ltm", "cp1:ebitda_ltm"),
    )
    out.row("T1D.1", "stmt", "Recorded in the statements (CP-1)", ("type", "status", "claimed"))


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
        if o.path == "source" and o.basis is not None and a.accepted_basis is not None:
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
            out.number(
                share_at,
                o.fraction,
                "PERCENT",
                "Source-supported amount / proposed amount",
                (basis_id, claimed_id),
            )
            out.number(accepted_at, o.accepted, "MILLIONS", "Source-supported amount", (basis_id,))
        else:
            out.gap(basis_at, "MILLIONS", _NO_BASIS, "not_applicable")
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
    start = cp1.adjusted_ebitda.amount
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
        out.row("T1D.3", row, label, ("value",))


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
    stated: Decimal | None,
    recomputed: tuple[Decimal | None, str],
) -> None:
    """A T1D.4 tie-out of a stated bridge total against the recomputed rows."""
    row_id, label = row
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
                at("reported", "Stated"), stated, "MILLIONS", "Bridge source amount", (), "source"
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
    out.row("T1D.4", row_id, label, ("reported", "recomputed", "difference", "result"))


def _positive(value: Decimal, what: str) -> Decimal:
    """A denominator the lease divides by only when above 0; any other value is not specified."""
    if value <= 0:
        raise ValueError(f"{what} is not above 0; the lease defines no result for it")
    return value


def _tie_outs(out: _Facts, bridge: Bridge | None, totals: _Totals, cp1: Cp1Operands) -> None:
    """T1D.4: stated bridge totals against the rows, then CP-1's leverage recomputed."""
    _tie(
        out,
        ("proposed_total", "Proposed add-backs: stated total against rows"),
        bridge,
        bridge.proposed_total if bridge else None,
        (totals.claimed, "T1D.3.claimed.value"),
    )
    _tie(
        out,
        ("mgmt_ebitda", "Management EBITDA: stated against statement EBITDA plus rows"),
        bridge,
        bridge.management_ebitda if bridge else None,
        (totals.management, "T1D.3.mgmt.value"),
    )
    start = _positive(totals.start, "Statement adjusted EBITDA")
    for row, label, reported, debt in (
        (
            "cp1_total_leverage",
            "Statement total leverage against CP-1",
            cp1.total_leverage,
            cp1.total_debt,
        ),
        ("cp1_net_leverage", "Statement net leverage against CP-1", cp1.net_leverage, cp1.net_debt),
    ):
        recomputed = _quotient(debt.amount, start)
        out.number(
            ("T1D.4", row, "reported", "CP-1 reported"),
            reported.amount,
            "MULTIPLE",
            f"CP-1 {reported.figure}",
            (f"cp1:{reported.figure}",),
        )
        out.number(
            ("T1D.4", row, "recomputed", "Recomputed"),
            recomputed,
            "MULTIPLE",
            "Debt / statement adjusted EBITDA",
            (f"cp1:{debt.figure}", "T1D.3.start.value"),
        )
        out.number(
            ("T1D.4", row, "difference", "Difference"),
            _EXACT.subtract(recomputed, reported.amount),
            "MULTIPLE",
            "Recomputed minus CP-1",
            (f"T1D.4.{row}.recomputed", f"T1D.4.{row}.reported"),
        )
        out.text(
            ("T1D.4", row, "result", "Result"),
            "Reconciled" if recomputed == reported.amount else "Differs",
        )
        out.row("T1D.4", row, label, ("reported", "recomputed", "difference", "result"))


def _shares(out: _Facts, bridge: Bridge | None, totals: _Totals) -> None:
    """T1D.5: proposed / management, accepted / supported, accepted / proposed."""
    management_at = ("T1D.5", "management", "value", "Proposed add-backs / management EBITDA")
    if bridge is None:
        out.gap(management_at, "PERCENT", _NO_BRIDGE, "not_applicable")
    elif totals.claimed is None or totals.management is None:
        out.gap(management_at, "PERCENT", _UNSTATED_ANY)
    else:
        out.number(
            management_at,
            _quotient(totals.claimed, _positive(totals.management, "Management EBITDA")),
            "PERCENT",
            "Proposed add-backs / management financing-case EBITDA",
            ("T1D.3.claimed.value", "T1D.3.mgmt.value"),
        )
    out.number(
        ("T1D.5", "supported", "value", "Accepted add-backs / supported EBITDA"),
        _quotient(totals.accepted, _positive(totals.supported, "Supported adjusted EBITDA")),
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
        out.row("T1D.5", row, label, ("value",))


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
            cp1.cfo.amount,
            "MILLIONS",
            "CP-1 cfo_adjusted",
            ("cp1:cfo_ltm",),
        )
        for name, title, numerator, unit, formula in ratios:
            if ebitda is None:
                out.gap(("T1D.6", row, name, title), unit, reason, status)
            else:
                out.number(
                    ("T1D.6", row, name, title),
                    _quotient(numerator.amount, _positive(ebitda, f"{label} EBITDA")),
                    unit,
                    formula,
                    (f"cp1:{numerator.figure}", f"T1D.6.{row}.ebitda"),
                )
        out.row(
            "T1D.6",
            row,
            label,
            ("ebitda", "cfo", "cfo_to_ebitda", "total_leverage", "net_leverage"),
        )


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
        f"Proposed amount is not stated for {o.item.label}: every figure that needs it is Not calculable."
        for o in outcomes
        if o.item.amount is None
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
            shown=_spell(f.amount, f.unit, None),
            value_class=f.value_class,
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
    found = [f"Unknown add-back: {a.addback}" for a in assessments if a.addback not in labels]
    pairs: list[tuple[BridgeItem, Assessment]] = []
    for item in bridge.items:
        if count[item.label] != 1:
            found.append(f"Assess each bridge add-back exactly once: {item.label}")
            continue
        pairs.append((item, next(a for a in assessments if a.addback == item.label)))
    return found, pairs


def _composable(item: BridgeItem, assessment: Assessment) -> bool:
    return not (
        (_accepts(assessment) and item.amount is None)
        or (assessment.achievability == "Partly supported" and assessment.recurrence == "Recurring")
    )


def _bridge_issues(inputs: EarningsQualityInputs, source: Source, bridge: Bridge) -> list[str]:
    """Label rules, then each item's shape failure alone or its content rules, citations and
    prose (bound to every module fact when all items compose), then the confidence rule."""
    label_issues, pairs = _assessments_by_item(bridge, inputs.submission.assessments)
    shapes = {item.label: _shape_issue(item, a) for item, a in pairs}
    valid = [(item, a) for item, a in pairs if shapes[item.label] is None]
    composed = [_outcome(item, a) for item, a in valid if _composable(item, a)]
    if not label_issues and len(composed) == len(bridge.items):
        out = _compose(inputs, bridge, source, composed)
    else:
        out = _Facts(inputs.cp1.adjusted_ebitda.period, inputs.cp1.adjusted_ebitda.currency)
        _register(out, bridge, source, inputs.cp1)
        _assessment_rows(out, composed)
    bound = bind(f.to_fact() for f in out.facts)
    found = list(label_issues)
    for item, a in pairs:
        shape = shapes[item.label]
        if shape is not None:
            found.append(shape)
            continue
        cited = (*a.evidence, *filter(None, (a.accepted_basis,)))
        found += _rule_issues(item, a)
        found += citation_issues(cited, inputs.sources)
        found += prose_issues(a.rationale, bound)
    if inputs.submission.overall.confidence == "High":
        found.append("Confidence cannot be High: the add-back evidence is management-supplied")
    return found


def validation_issues(inputs: EarningsQualityInputs) -> tuple[str, ...]:
    """Every calculation-level issue of the submission against the pack and the bridge.

    Shape rules come first; a shape failure is returned alone for its item and that item's
    citations and prose are not checked (`expected.json refusal_rules`). Tool-use rules (cited
    page read) are Stage 2; the overall rationale's `{{FIG:...}}` references are bound to CP-1
    facts at run time, so its prose is checked there.
    """
    submission = inputs.submission
    source = _bridge_source(inputs.sources)
    if source is None:
        found = [
            f"Assessment given without a bridge in the pack: {a.addback}"
            for a in submission.assessments
        ]
        if not submission.overall.evidence:
            found.append(
                "Evidence required when no bridge is supplied: the statements' add-back disclosure"
            )
    else:
        bridge = parse_bridge(_pages(source))
        if bridge is None:
            return ("Bridge table not found",)
        found = _bridge_issues(inputs, source, bridge)
    found += citation_issues(submission.overall.evidence, inputs.sources)
    return tuple(dict.fromkeys(found))


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
    _tie_outs(out, bridge, totals, cp1)
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
    outcomes = [_outcome(item, by_label[item.label]) for item in bridge.items] if bridge else []
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
