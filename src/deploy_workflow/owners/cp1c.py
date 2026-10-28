"""CP-1C (Peer benchmark): the Stage 1 calculation, pure Python over typed inputs.

Lease: docs/CP1C-OWNER-LEASE.md (frozen revision 4 with amendment 1: the universe totals are
table T1C.8), as extended by docs/rulings/2026-10-28-stage1.md (CP-1C 1C1-1C6, round 2 C1-C3;
a ruling wins over the lease). Oracle: cases/cp1c-owner/expected.json. Python owns every number: peer ratios,
medians, differences, positions, deviations, outlier flags and counts, all in an exact 38-digit
half-even decimal context. The analyst supplies only comparability judgments, rationale text,
the overall view and the gaps. No I/O, store, host, session or render call happens here; the
connection (pack, CP-1 head, tool use) and orchestration concerns join this file in later stages.
"""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal
from itertools import pairwise
from typing import Literal

from deploy_vii import prose
from deploy_vii.business_context import Category, Severity, prohibited_issues
from deploy_vii.contracts import Citation, Claim, Contract, Fact, Source, TableRow
from deploy_vii.readiness import citation_issues
from deploy_vii.report_view import fact_spelling

MODULE_ID = "CP-1C"

# One context for every operation: 38 significant digits, half-even (lease "peer metric").
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)

# Policy constants (lease open questions 2 and 3, expected.json policy_constants).
MIN_INCLUDED_PEERS = 3
OUTLIER_FRACTION = Decimal("0.5")
# Below this many included peers a limitation says medians move with one peer (oracle wording).
THIN_UNIVERSE = 5

PEERS_SOURCE_ID = "peers"
P1_HEADER = "Peer  Period end  Revenue  Adjusted EBITDA  Total debt  Interest expense  FFO"
P2_HEADER = "Peer  Reporting basis  Operating segments  Fiscal year end"
NOT_STATED = "Not stated"
# ASCII digits only. str.isdigit() and \d accept other Unicode digits: Decimal() reads some of
# them (Arabic-Indic) and rejects others (superscripts); neither belongs in a source amount.
AMOUNT = re.compile(r"-?[0-9]+(?:\.([0-9]+))?")
PERIOD_END = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")  # and a real calendar date (1C4)
TABLE_NOT_FOUND = "Peer table not found"
NO_PEER_SOURCE = "No peer source is in the pack"
# Round 4 (b): a peers source that is not ready composes the no-peers design with this reason.
NO_READY_PEER_SOURCE = "No ready peer source is in the pack"
NOT_STATED_IN_SOURCE = "Not stated in the peer source"
MIXED_PERIOD = "Mixed: issuer LTM Q4 25, each peer's own twelve months"
PROHIBITED_KINDS = ("instrument recommendation", "recovery conclusion")
EXCLUDED = "Not meaningful: the peer is excluded from the universe"
NO_MEDIAN = "Not calculable: no peer median (fewer than three included peers have a value)"
OWN_NOT_MEANINGFUL = "Not meaningful: the peer's own ratio is not meaningful"  # ruling 1C1
ZERO_MEDIAN = "Not meaningful: the peer median is zero"
NOT_COMPARED = "Not compared: one side is not available"  # ruling 1C2
# Round 2 C3: page:1 must carry this clause in its Basis line; the clause is what gives a source
# amount its currency, unit and scale. Any other basis is outside the table rule.
BASIS_PREFIX = "Basis:"
SUPPORTED_BASIS: Mapping[tuple[str, str], tuple[str, str, Decimal]] = {
    ("USD", "amounts in millions"): ("USD", "MILLIONS", Decimal(1_000_000)),
}
# The unit a settled source amount carries under the supported clause; the no-source gap twins
# carry it too (a missing fact carries its settled twin's unit).
NO_SOURCE_AMOUNT_UNIT = "MILLIONS"
# The oracle shows every source amount at one decimal place (decimals 1). An amount stated more
# precisely would be shown rounded, so it breaches the table rule (round 3 ruling 1C-x).
SHEET_DECIMALS = 1
PERCENT = "PERCENT"
MULTIPLE = "MULTIPLE"

TABLES: Mapping[str, str] = {
    "T1C.1": "Peer universe",
    "T1C.2": "Peer source figures",
    "T1C.3": "Normalised metrics",
    "T1C.4": "Peer statistics",
    "T1C.5": "Outlier register",
    "T1C.6": "Definition alignment and tie-out",
    "T1C.7": "Gaps ledger",
    # Amendment 1 ruling (LEAD 2026-10-28): the totals row moves out of T1C.1, one fact per column.
    "T1C.8": "Peer universe totals",
}
TOTALS = "T1C.8"

OPERANDS: tuple[tuple[str, str], ...] = (
    ("revenue", "Revenue"),
    ("ebitda", "Adjusted EBITDA"),
    ("debt", "Total debt"),
    ("interest", "Interest expense"),
    ("ffo", "FFO"),
)
OPERAND_LABEL: Mapping[str, str] = dict(OPERANDS)

Comparability = Literal["Comparable", "Partly comparable", "Not comparable"]


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    unit: str
    percent: bool
    higher_is_better: bool
    numerator: str
    denominator: str

    @property
    def direction(self) -> str:
        return "Higher is better" if self.higher_is_better else "Lower is better"

    @property
    def token(self) -> str:
        return "%" if self.percent else "x"

    @property
    def difference_unit(self) -> str:
        # The room between two percentages is percentage points (cp4_legal.py:970-972).
        return "pp" if self.percent else self.unit


METRICS: tuple[Metric, ...] = (
    Metric(
        "adjusted_ebitda_margin", "Adjusted EBITDA margin", PERCENT, True, True, "ebitda", "revenue"
    ),
    Metric(
        "total_leverage_adjusted",
        "Total leverage (adjusted)",
        MULTIPLE,
        False,
        False,
        "debt",
        "ebitda",
    ),
    Metric(
        "interest_coverage_adjusted",
        "Interest coverage (adjusted)",
        MULTIPLE,
        False,
        True,
        "ebitda",
        "interest",
    ),
    Metric("ffo_to_debt", "FFO to total debt", PERCENT, True, True, "ffo", "debt"),
)
STAT_FIELDS = ("direction", "n", "median", "difference", "position", "of", "outlier_count")
FLAG_FIELDS = tuple(f"{m.key}_{part}" for m in METRICS for part in ("deviation", "flag"))
UNIVERSE_FIELDS = (
    ("period_end", "Period end"),
    ("reporting_basis", "Reporting basis"),
    ("segments", "Operating segments"),
    ("fiscal_year_end", "Fiscal year end"),
    ("comparability", "Comparability"),
    ("included", "Universe"),
    ("evidence", "Evidence"),
)
TOTAL_FIELDS = (
    ("sheet", "Peers in the source"),
    ("included", "Peers included"),
    ("excluded", "Peers excluded"),
)


# --- the analyst submission (references and judgment only; no computed number) ------------------


class PeerAssessment(Contract):
    peer: str
    comparability: Comparability
    category: Category
    rationale: str
    evidence: tuple[Citation, ...]
    limitation: str | None = None


class Overall(Contract):
    rationale: str
    category: Category
    confidence: Literal["High", "Medium", "Low"]
    limitation: str
    evidence: tuple[Citation, ...]


class Gap(Contract):
    gap: str
    why_it_matters: str
    affected_analysis: str
    severity: Severity
    action: str


class PeerBenchmarkSubmission(Contract):
    assessments: tuple[PeerAssessment, ...]
    overall: Overall
    gaps: tuple[Gap, ...]


# --- the peer source --------------------------------------------------------------------------------


class PeerTableError(ValueError):
    """The peers source cannot be read by the peer table rule; its text is the issue."""


@dataclass(frozen=True)
class BasisLine:
    basis: str
    segments: str
    fiscal_year_end: str
    line: str


@dataclass(frozen=True)
class PeerRow:
    label: str
    period_end: str
    amounts: Mapping[str, Decimal | None]  # operand -> amount; None is "Not stated" (missing)
    line: str  # the verbatim page:1 line, quoted by every fact read from it
    basis: BasisLine | None  # the page:2 line, None when the row is absent there

    @property
    def period(self) -> str:
        return f"Twelve months to {self.period_end}"


@dataclass(frozen=True)
class PeerSheet:
    source_sha256: str
    currency: str  # read from the page:1 Basis line clause
    unit: str
    scale: Decimal
    issuer: PeerRow
    peers: tuple[PeerRow, ...]


def _split(line: str) -> list[str]:
    # Fields are separated by two or more spaces (lease "Peer table rule").
    return re.split(r" {2,}", line)


def _amount(token: str) -> Decimal | None:
    if token == NOT_STATED:
        return None
    match = AMOUNT.fullmatch(token)
    if match is None:
        raise PeerTableError(TABLE_NOT_FOUND)
    if len(match.group(1) or "") > SHEET_DECIMALS:  # ruling 1C-x: a table rule breach
        raise PeerTableError(TABLE_NOT_FOUND)
    return Decimal(token)


def _period_end(token: str) -> str:
    if not PERIOD_END.fullmatch(token):
        raise PeerTableError(TABLE_NOT_FOUND)
    try:
        date.fromisoformat(token)
    except ValueError:
        raise PeerTableError(TABLE_NOT_FOUND) from None
    return token


def _span(source: Source, locator: str) -> str | None:
    return next((span.text for span in source.spans if span.locator == locator), None)


def _basis(lines: Sequence[str]) -> tuple[str, str, Decimal]:
    """Currency, unit and scale from the supported clause of a page:1 Basis line (C3)."""
    for line in lines:
        if not line.startswith(BASIS_PREFIX):
            continue
        parts = [part.strip().rstrip(".") for part in line[len(BASIS_PREFIX) :].split(";")]
        for pair in pairwise(parts):
            if pair in SUPPORTED_BASIS:
                return SUPPORTED_BASIS[pair]
    raise PeerTableError(TABLE_NOT_FOUND)


def _basis_lines(source: Source) -> dict[str, BasisLine]:
    """The page:2 table: it ends at the first line that is not 4 fields (1C4); without its
    header every peer's basis cells read Not stated (1C3)."""
    text = _span(source, "page:2")
    lines = [] if text is None else text.split("\n")
    if P2_HEADER not in lines:
        return {}
    basis: dict[str, BasisLine] = {}
    for line in lines[lines.index(P2_HEADER) + 1 :]:
        parts = _split(line)
        if len(parts) != 4:
            break  # free-text notes follow the table
        if parts[0] in basis:  # provisional (not ruled): a repeated page:2 label
            raise PeerTableError(TABLE_NOT_FOUND)
        basis[parts[0]] = BasisLine(parts[1], parts[2], parts[3], line)
    return basis


def _row(line: str, basis: Mapping[str, BasisLine]) -> PeerRow:
    parts = _split(line)
    if len(parts) != 7:
        raise PeerTableError(TABLE_NOT_FOUND)
    amounts = {key: _amount(token) for (key, _), token in zip(OPERANDS, parts[2:], strict=True)}
    return PeerRow(parts[0], _period_end(parts[1]), amounts, line, basis.get(parts[0]))


def parse_peer_source(source: Source | None, *, issuer_name: str) -> PeerSheet | None:
    """The peer table rule: None when the pack holds no peers source or one that is not ready
    (round 4 (b): the no-peers design). Every breach (no page:1, no header, no supported Basis clause, a line that is not 7 fields, a bad
    date, a non-decimal amount, an amount with more than one decimal place, a repeated label,
    an issuer line count other than 1) raises PeerTableError('Peer table not found'), which is
    returned alone (rulings 1C4, C3, 1C-x)."""
    if source is None or source.status != "ready":
        return None
    text = _span(source, "page:1")
    lines = [] if text is None else text.split("\n")
    if source.sha256 is None or P1_HEADER not in lines:
        raise PeerTableError(TABLE_NOT_FOUND)
    start = lines.index(P1_HEADER)
    currency, unit, scale = _basis(lines[:start])
    basis = _basis_lines(source)
    rows = [_row(line, basis) for line in lines[start + 1 :]]
    labels = Counter(row.label for row in rows)
    if any(count > 1 for count in labels.values()) or labels[issuer_name] != 1:
        raise PeerTableError(TABLE_NOT_FOUND)
    issuer = next(row for row in rows if row.label == issuer_name)
    peers = tuple(row for row in rows if row.label != issuer_name)
    return PeerSheet(source.sha256, currency, unit, scale, issuer, peers)


# --- the pure composer rules --------------------------------------------------------------------------


@dataclass(frozen=True)
class Known:
    value: Decimal
    status: Literal["known"] = "known"


@dataclass(frozen=True)
class Unsettled:
    status: Literal["missing", "not_applicable"]
    reason: str


Ratio = Known | Unsettled


def ratio(
    metric: Metric, amounts: Mapping[str, Decimal | None], *, where: str = "in the peer source"
) -> Ratio:
    """One division of exact decimals; a Not stated operand is missing, a denominator not
    positive is not_applicable (lease "peer metric"; `where` names the issuer line, 1C2)."""
    numerator, denominator = amounts[metric.numerator], amounts[metric.denominator]
    if numerator is None or denominator is None:
        absent = metric.numerator if numerator is None else metric.denominator
        return Unsettled(
            "missing", f"Not calculable: {OPERAND_LABEL[absent].lower()} is not stated {where}"
        )
    if denominator <= 0:
        reason = f"Not meaningful: {OPERAND_LABEL[metric.denominator].lower()} is not positive"
        return Unsettled("not_applicable", reason)
    return Known(CTX.divide(numerator, denominator))


def peer_metrics(row: PeerRow) -> dict[str, Ratio]:
    return {metric.key: ratio(metric, row.amounts) for metric in METRICS}


def median(values: Sequence[Decimal]) -> Decimal:
    """Odd count: the middle value; even count: (a + b) / 2 in the context on the stored values."""
    if not values:
        raise ValueError("A median needs at least one value")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return CTX.divide(CTX.add(ordered[middle - 1], ordered[middle]), Decimal(2))


def peer_median(values: Sequence[Decimal]) -> Decimal | None:
    """The peer median, or None (missing) below the minimum universe."""
    return median(values) if len(values) >= MIN_INCLUDED_PEERS else None


def position(
    issuer: Decimal, peers: Sequence[Decimal], *, higher_is_better: bool
) -> tuple[int, int]:
    """(1 + entities strictly better than the issuer, entities compared); ties share."""
    better = sum(1 for v in peers if (v > issuer if higher_is_better else v < issuer))
    return 1 + better, len(peers) + 1


def outlier(value: Decimal, peer_median_value: Decimal) -> tuple[Decimal, str] | None:
    """(deviation, flag); None when the median is zero (not_applicable). Outlier iff the
    absolute deviation is strictly above one half."""
    return None if peer_median_value == 0 else _deviation(value, peer_median_value)


def _deviation(value: Decimal, peer_median_value: Decimal) -> tuple[Decimal, str]:
    deviation = CTX.divide(CTX.subtract(value, peer_median_value), peer_median_value)
    flag = "Outlier" if deviation.copy_abs() > OUTLIER_FRACTION else "Within range"
    return deviation, flag


def difference(value: Decimal, reference: Decimal, *, percent: bool) -> Decimal:
    """value - reference in the context; percent metrics in percentage points (.scaleb(2))."""
    delta = CTX.subtract(value, reference)
    return delta.scaleb(2, context=CTX) if percent else delta


# --- inputs and result ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class PeerBenchmarkInputs:
    issuer_name: str
    sources: tuple[Source, ...]  # host-scoped pack sources; the peer table is read from "peers"
    cp1_metrics: Mapping[str, Fact]  # CP-1 T4.10 LTM facts by metric key
    submission: PeerBenchmarkSubmission


@dataclass(frozen=True)
class PeerFact:
    fact: Fact
    derives_from: tuple[str, ...] = ()
    copied_from_cp1: str | None = None  # the CP-1 fact label this cell copies verbatim


@dataclass(frozen=True)
class PeerTable:
    table_id: str
    title: str
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class PeerBenchmarkResult:
    facts: tuple[PeerFact, ...]
    tables: tuple[PeerTable, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]


def shown(fact: Fact) -> str | None:
    """The display text of a known fact (report_view.fact_spelling); None when unsettled, whose
    spelling needs the report-wide G# reference."""
    return fact_spelling(fact, None)[2] if fact.status == "known" else None


# --- composition ----------------------------------------------------------------------------------------


Ref = tuple[str, str, str]


def _fid(ref: Ref) -> str:
    return ".".join(ref)


class _Composer:
    def __init__(self, sheet: PeerSheet | None, absent: str) -> None:
        self.items: list[PeerFact] = []
        self.rows: dict[str, list[TableRow]] = {table: [] for table in TABLES}
        self.sheet = sheet
        self.absent = absent  # the reason every peer-derived cell carries without a sheet

    def _peer_sheet(self) -> PeerSheet:
        if self.sheet is None:  # a peer citation or source amount exists only with a sheet
            raise ValueError("A peer source fact needs the peers source")
        return self.sheet

    def cite(self, locator: str, quote: str) -> Citation:
        sha = self._peer_sheet().source_sha256
        return Citation(source_id=PEERS_SOURCE_ID, source_sha256=sha, locator=locator, quote=quote)

    def _add(self, fact: Fact, derives: Sequence[str] = (), copied: str | None = None) -> None:
        self.items.append(PeerFact(fact, tuple(derives), copied))

    def amount(
        self,
        ref: Ref,
        label: str,
        value: Decimal,
        *,
        unit: str,
        period: str,
        formula: str,
        derives: Sequence[str] = (),
        source: tuple[Citation, ...] | None = None,
    ) -> None:
        """A known number: calculated unless `source` (its citations) marks a source amount."""
        table, row, name = ref
        sheet = self._peer_sheet() if source is not None else None
        self._add(
            Fact(
                fact_id=_fid(ref),
                label=label,
                table_id=table,
                row_id=row,
                field=name,
                amount=value,
                unit=unit,
                period=period,
                formula=formula,
                currency=sheet.currency if sheet else None,
                scale=sheet.scale if sheet else Decimal(1),
                decimals=SHEET_DECIMALS if sheet else None,
                value_class="source" if sheet else "calculated",
                calculation_id=None if sheet else f"calc:{_fid(ref)}",
                citations=source or (),
            ),
            derives,
        )

    def count(
        self, ref: Ref, label: str, value: int, unit: str, formula: str, derives: Sequence[str]
    ) -> None:
        self.amount(
            ref,
            label,
            Decimal(value),
            unit=unit,
            period=MIXED_PERIOD,
            formula=formula,
            derives=derives,
        )

    def text(
        self,
        ref: Ref,
        label: str,
        value: str,
        *,
        value_class: Literal["source", "calculated", "analyst_judgment"] | None = None,
        citations: tuple[Citation, ...] = (),
        formula: str | None = None,
        derives: Sequence[str] = (),
        period: str | None = None,
    ) -> None:
        table, row, name = ref
        calculated = value_class == "calculated"
        self._add(
            Fact(
                fact_id=_fid(ref),
                label=label,
                table_id=table,
                row_id=row,
                field=name,
                text=value,
                value_class=value_class,
                citations=citations,
                period=period,
                formula=formula if calculated else None,
                calculation_id=f"calc:{_fid(ref)}" if calculated else None,
            ),
            derives if calculated else (),
        )

    def unsettled(
        self,
        ref: Ref,
        label: str,
        reason: str,
        *,
        unit: str | None,
        period: str | None,
        status: Literal["missing", "not_applicable"] = "missing",
    ) -> None:
        table, row, name = ref
        self._add(
            Fact(
                fact_id=_fid(ref),
                label=label,
                table_id=table,
                row_id=row,
                field=name,
                status=status,
                unit=unit,
                period=period,
                limitation=reason,
            )
        )

    def copy(self, ref: Ref, label: str, cp1: Fact) -> None:
        """The CP-1 fact verbatim under this module's id: unit, amount, decimals, currency,
        scale, period, value class, citations and CP-1's own calculation id."""
        table, row, name = ref
        self._add(
            Fact(
                fact_id=_fid(ref),
                label=label,
                table_id=table,
                row_id=row,
                field=name,
                amount=cp1.amount,
                unit=cp1.unit,
                currency=cp1.currency,
                scale=cp1.scale,
                decimals=cp1.decimals,
                period=cp1.period,
                value_class=cp1.value_class,
                citations=cp1.citations,
                calculation_id=cp1.calculation_id,
            ),
            copied=cp1.label,
        )

    def row(self, table: str, row_id: str, label: str, fields: Sequence[str]) -> None:
        ids = tuple(f"{table}.{row_id}.{name}" for name in fields)
        self.rows[table].append(TableRow(row_id=row_id, label=label, fact_ids=ids))


@dataclass(frozen=True)
class _Peer:
    row_id: str
    data: PeerRow
    assessment: PeerAssessment

    @property
    def included(self) -> bool:
        return self.assessment.comparability != "Not comparable"


@dataclass
class _Stat:
    n: int
    median: Decimal | None
    flags: dict[str, bool] = field(default_factory=dict)


def _universe(c: _Composer, peers: Sequence[_Peer], present: bool) -> None:
    for p in peers:
        r, basis = p.row_id, p.data.basis
        c.text(
            ("T1C.1", r, "period_end"),
            "Period end",
            p.data.period_end,
            value_class="source",
            citations=(c.cite("page:1", p.data.line),),
        )
        for (name, label), attr in zip(
            UNIVERSE_FIELDS[1:4], ("basis", "segments", "fiscal_year_end")
        ):
            if basis is None:  # the row is absent from the page:2 table
                c.unsettled(("T1C.1", r, name), label, NOT_STATED_IN_SOURCE, unit=None, period=None)
            else:
                c.text(
                    ("T1C.1", r, name),
                    label,
                    getattr(basis, attr),
                    value_class="source",
                    citations=(c.cite("page:2", basis.line),),
                )
        c.text(
            ("T1C.1", r, "comparability"),
            "Comparability",
            p.assessment.comparability,
            value_class="analyst_judgment",
        )
        c.text(
            ("T1C.1", r, "included"),
            "Universe",
            "Included" if p.included else "Excluded",
            value_class="calculated",
            formula="Included unless Not comparable",
            derives=(f"T1C.1.{r}.comparability",),
        )
        evidence = "; ".join(f"{e.source_id} {e.locator}" for e in p.assessment.evidence)
        c.text(("T1C.1", r, "evidence"), "Evidence", evidence)
        c.row("T1C.1", r, p.data.label, [name for name, _ in UNIVERSE_FIELDS])
    if present:
        flags = [f"T1C.1.{p.row_id}.included" for p in peers]
        included = sum(1 for p in peers if p.included)
        counts = (len(peers), included, len(peers) - included)
        for (name, label), value in zip(TOTAL_FIELDS, counts):
            formula = "count of peer rows" if name == "sheet" else "count by universe flag"
            derives = () if name == "sheet" else flags
            c.count((TOTALS, "total", name), label, value, "peers", formula, derives)
    else:
        for name, label in UNIVERSE_FIELDS:
            c.unsettled(("T1C.1", "none", name), label, c.absent, unit=None, period=None)
        c.row("T1C.1", "none", "No peer source", [name for name, _ in UNIVERSE_FIELDS])
        for name, label in TOTAL_FIELDS:
            c.unsettled((TOTALS, "total", name), label, c.absent, unit="peers", period=None)
    c.row(TOTALS, "total", "Total", [name for name, _ in TOTAL_FIELDS])


def _source_figures(c: _Composer, sheet: PeerSheet | None, peers: Sequence[_Peer]) -> None:
    if sheet is None:
        for key, label in OPERANDS:
            c.unsettled(
                ("T1C.2", "none", key),
                label,
                c.absent,
                unit=NO_SOURCE_AMOUNT_UNIT,
                period=None,
            )
        c.row("T1C.2", "none", "No peer source", [key for key, _ in OPERANDS])
        return
    for row_id, data in [("issuer", sheet.issuer), *((p.row_id, p.data) for p in peers)]:
        for key, label in OPERANDS:
            value = data.amounts[key]
            if value is None:
                c.unsettled(
                    ("T1C.2", row_id, key),
                    label,
                    NOT_STATED_IN_SOURCE,
                    unit=sheet.unit,
                    period=data.period,
                )
            else:
                c.amount(
                    ("T1C.2", row_id, key),
                    label,
                    value,
                    unit=sheet.unit,
                    period=data.period,
                    formula="Peer source amount",
                    source=(c.cite("page:1", data.line),),
                )
        c.row("T1C.2", row_id, data.label, [key for key, _ in OPERANDS])


@dataclass(frozen=True)
class _Cp1Cell:
    fact: Fact
    amount: Decimal
    period: str


def _cp1_facts(inputs: PeerBenchmarkInputs) -> dict[str, _Cp1Cell]:
    """The CP-1 T4.10 fact per metric: known, numeric, in the metric's unit, with a period."""
    found: dict[str, _Cp1Cell] = {}
    for metric in METRICS:
        fact = inputs.cp1_metrics.get(metric.key)
        if fact is None or fact.status != "known" or fact.unit != metric.unit:
            raise ValueError(f"CP-1 fact unavailable for {metric.key}")
        if fact.amount is None or fact.period is None:
            raise ValueError(f"CP-1 fact unavailable for {metric.key}")
        found[metric.key] = _Cp1Cell(fact, fact.amount, fact.period)
    return found


Values = dict[tuple[str, str], Ratio]


def _normalised(
    c: _Composer, cp1: Mapping[str, _Cp1Cell], issuer: str, peers: Sequence[_Peer], present: bool
) -> Values:
    values: Values = {}
    for m in METRICS:
        c.copy(("T1C.3", "issuer", m.key), m.label, cp1[m.key].fact)
        values[("issuer", m.key)] = Known(cp1[m.key].amount)
    c.row("T1C.3", "issuer", f"{issuer} (CP-1)", [m.key for m in METRICS])
    for p in peers:
        ratios = peer_metrics(p.data)
        for m in METRICS:
            got, ref = ratios[m.key], ("T1C.3", p.row_id, m.key)
            values[(p.row_id, m.key)] = got
            if isinstance(got, Known):
                formula = f"{OPERAND_LABEL[m.numerator]} / {OPERAND_LABEL[m.denominator]}"
                derives = (f"T1C.2.{p.row_id}.{m.numerator}", f"T1C.2.{p.row_id}.{m.denominator}")
                c.amount(
                    ref,
                    m.label,
                    got.value,
                    unit=m.unit,
                    period=p.data.period,
                    formula=formula,
                    derives=derives,
                )
            else:
                c.unsettled(
                    ref, m.label, got.reason, unit=m.unit, period=p.data.period, status=got.status
                )
        c.row("T1C.3", p.row_id, p.data.label, [m.key for m in METRICS])
    if not present:
        for m in METRICS:
            c.unsettled(("T1C.3", "none", m.key), m.label, c.absent, unit=m.unit, period=None)
        c.row("T1C.3", "none", "No peer source", [m.key for m in METRICS])
    return values


def _gap_units(m: Metric) -> dict[str, str]:
    """A missing or not-applicable fact carries the unit its settled twin carries."""
    return {
        "n": "peers",
        "median": m.unit,
        "difference": m.difference_unit,
        "position": "rank",
        "of": "entities",
        "outlier_count": "peers",
    }


STAT_LABELS = {
    "n": "Included peers with a value",
    "median": "Peer median",
    "difference": "Issuer minus median",
    "position": "Issuer position",
    "of": "Entities compared",
    "outlier_count": "Peers flagged as outliers",
}


def _settled_stats(
    c: _Composer, m: Metric, issuer: Decimal, known: Sequence[tuple[str, Decimal]], med: Decimal
) -> None:
    k = m.key
    ders = tuple(f"T1C.3.{r}.{k}" for r, _ in known)
    own = f"T1C.3.issuer.{k}"
    c.amount(
        ("T1C.4", k, "median"),
        STAT_LABELS["median"],
        med,
        unit=m.unit,
        period=MIXED_PERIOD,
        formula="median of included peers' values; even count: (a + b) / 2",
        derives=ders,
    )
    formula = (
        "(issuer value minus peer median) x 100, percentage points"
        if m.percent
        else "issuer value minus peer median"
    )
    c.amount(
        ("T1C.4", k, "difference"),
        STAT_LABELS["difference"],
        difference(issuer, med, percent=m.percent),
        unit=m.difference_unit,
        period=MIXED_PERIOD,
        formula=formula,
        derives=(own, f"T1C.4.{k}.median"),
    )
    rank, of = position(issuer, [v for _, v in known], higher_is_better=m.higher_is_better)
    c.count(
        ("T1C.4", k, "position"),
        STAT_LABELS["position"],
        rank,
        "rank",
        "1 + number of entities strictly better than the issuer; ties share a position",
        (own, *ders),
    )
    c.count(
        ("T1C.4", k, "of"),
        STAT_LABELS["of"],
        of,
        "entities",
        "included peers with a value + the issuer",
        (*ders, own),
    )


def _statistics(
    c: _Composer,
    peers: Sequence[_Peer],
    values: Values,
    present: bool,
    issuer: Mapping[str, Decimal],
) -> dict[str, _Stat | None]:
    """T1C.4 per metric; `issuer` is the copied CP-1 value per metric."""
    stats: dict[str, _Stat | None] = {}
    for m in METRICS:
        k, units = m.key, _gap_units(m)
        c.text(("T1C.4", k, "direction"), "Direction", m.direction)
        c.row("T1C.4", k, m.label, STAT_FIELDS)
        if not present:
            for name in STAT_FIELDS[1:]:
                c.unsettled(
                    ("T1C.4", k, name),
                    STAT_LABELS[name],
                    c.absent,
                    unit=units[name],
                    period=None,
                )
            stats[k] = None
            continue
        known = [
            (p.row_id, got.value)
            for p in peers
            if p.included and isinstance(got := values[(p.row_id, k)], Known)
        ]
        c.count(
            ("T1C.4", k, "n"),
            STAT_LABELS["n"],
            len(known),
            "peers",
            "count of included peers with a calculated value",
            [f"T1C.3.{r}.{k}" for r, _ in known],
        )
        med = peer_median([v for _, v in known])
        stats[k] = _Stat(len(known), med)
        if med is None:
            why = (
                f"Not calculable: {len(known)} included peers have a stated value, "
                f"at least {MIN_INCLUDED_PEERS} are required"
            )
            for name in STAT_FIELDS[2:]:
                c.unsettled(
                    ("T1C.4", k, name),
                    STAT_LABELS[name],
                    why,
                    unit=units[name],
                    period=MIXED_PERIOD,
                )
            continue
        _settled_stats(c, m, issuer[k], known, med)
    return stats


def _flag_operands(
    peer: _Peer | None, value: Ratio, stat: _Stat
) -> Unsettled | tuple[Decimal, Decimal]:
    """Why the deviation and flag are unsettled, in the ruled order (1C1): excluded, median
    missing, value missing, value not_applicable, median zero; else (value, median)."""
    if peer is not None and not peer.included:
        return Unsettled("not_applicable", EXCLUDED)
    if stat.median is None:
        return Unsettled("missing", NO_MEDIAN)
    if isinstance(value, Unsettled):
        if value.status == "missing":
            return Unsettled("missing", "Not calculable: the peer's value is not stated")
        return Unsettled("not_applicable", OWN_NOT_MEANINGFUL)
    if stat.median == 0:
        return Unsettled("not_applicable", ZERO_MEDIAN)
    return value.value, stat.median


def _flag_cells(
    c: _Composer, row_id: str, peer: _Peer | None, m: Metric, value: Ratio, stat: _Stat
) -> None:
    dev = ("T1C.5", row_id, f"{m.key}_deviation")
    flag = ("T1C.5", row_id, f"{m.key}_flag")
    dev_label, flag_label = f"{m.label} · Deviation from median", f"{m.label} · Flag"
    operands = _flag_operands(peer, value, stat)
    if isinstance(operands, Unsettled):
        gap = operands
        c.unsettled(
            dev, dev_label, gap.reason, unit=PERCENT, period=MIXED_PERIOD, status=gap.status
        )
        c.unsettled(flag, flag_label, gap.reason, unit=None, period=MIXED_PERIOD, status=gap.status)
        return
    deviation, verdict = _deviation(*operands)
    c.amount(
        dev,
        dev_label,
        deviation,
        unit=PERCENT,
        period=MIXED_PERIOD,
        formula="(value - peer median) / peer median",
        derives=(f"T1C.3.{row_id}.{m.key}", f"T1C.4.{m.key}.median"),
    )
    c.text(
        flag,
        flag_label,
        verdict,
        value_class="calculated",
        period=MIXED_PERIOD,
        formula="Outlier iff |deviation| is strictly above one half",
        derives=(_fid(dev),),
    )
    stat.flags[row_id] = verdict == "Outlier"


def _outliers(
    c: _Composer,
    issuer: str,
    peers: Sequence[_Peer],
    values: Values,
    stats: Mapping[str, _Stat | None],
    present: bool,
) -> None:
    if not present:
        for name in FLAG_FIELDS:
            unit = None if name.endswith("_flag") else PERCENT
            c.unsettled(("T1C.5", "none", name), name, c.absent, unit=unit, period=None)
        c.row("T1C.5", "none", "No peer source", FLAG_FIELDS)
        return
    entries: list[tuple[str, str, _Peer | None]] = [("issuer", issuer, None)]
    entries += [(p.row_id, p.data.label, p) for p in peers]
    for row_id, label, peer in entries:
        for m in METRICS:
            stat = stats[m.key]
            if stat is None:  # unreachable with a peer source
                raise ValueError(f"No statistics for {m.key}")
            _flag_cells(c, row_id, peer, m, values[(row_id, m.key)], stat)
        c.row("T1C.5", row_id, label, FLAG_FIELDS)
    for m in METRICS:
        stat = stats[m.key]
        if stat is None or stat.median is None:
            continue  # its outlier_count gap was written with the other statistics
        if stat.median == 0:  # round 2 C2: not a known 0
            count = ("T1C.4", m.key, "outlier_count")
            c.unsettled(
                count,
                STAT_LABELS["outlier_count"],
                ZERO_MEDIAN,
                unit="peers",
                period=MIXED_PERIOD,
                status="not_applicable",
            )
            continue
        tested = [p.row_id for p in peers if p.included and p.row_id in stat.flags]
        flagged = sum(1 for r in tested if stat.flags[r])
        c.count(
            ("T1C.4", m.key, "outlier_count"),
            STAT_LABELS["outlier_count"],
            flagged,
            "peers",
            "count of included peers flagged",
            [f"T1C.5.{r}.{m.key}_flag" for r in tested],
        )


def _issuer_line(
    m: Metric, sheet: PeerSheet | None, absent: str
) -> Unsettled | tuple[Decimal, str]:
    """The issuer line's own ratio and period, or why it cannot be recomputed (1C2)."""
    if sheet is None:
        return Unsettled("missing", absent)
    got = ratio(m, sheet.issuer.amounts, where="on the issuer line of the peer source")
    return got if isinstance(got, Unsettled) else (got.value, sheet.issuer.period)


def _tie_out(c: _Composer, sheet: PeerSheet | None, cp1: Mapping[str, _Cp1Cell]) -> None:
    """The issuer line on the peer source recomputed and set against the copied CP-1 value."""
    for m in METRICS:
        k, cell, label = m.key, cp1[m.key], "Issuer line on the peer source"
        line = _issuer_line(m, sheet, c.absent)
        if isinstance(line, Unsettled):
            period = None if sheet is None else sheet.issuer.period
            sheet_ref = ("T1C.6", k, "sheet")
            c.unsettled(
                sheet_ref, label, line.reason, unit=m.unit, period=period, status=line.status
            )
            c.copy(("T1C.6", k, "cp1"), "CP-1", cell.fact)
            # ruling 1C2 / round 4 (d): one side is not available, so nothing is compared
            reason = c.absent if sheet is None else NOT_COMPARED
            unit = m.difference_unit
            c.unsettled(("T1C.6", k, "difference"), "Difference", reason, unit=unit, period=None)
            c.text(("T1C.6", k, "result"), "Result", "Not compared")
        else:
            value, period = line
            c.amount(
                ("T1C.6", k, "sheet"),
                label,
                value,
                unit=m.unit,
                period=period,
                formula=f"{OPERAND_LABEL[m.numerator]} / {OPERAND_LABEL[m.denominator]} "
                "from the issuer line",
                derives=(f"T1C.2.issuer.{m.numerator}", f"T1C.2.issuer.{m.denominator}"),
            )
            c.copy(("T1C.6", k, "cp1"), "CP-1", cell.fact)
            _tie_out_settled(c, m, value, cell)
        c.row("T1C.6", k, m.label, ("sheet", "cp1", "difference", "result"))


def _tie_out_settled(c: _Composer, m: Metric, sheet_value: Decimal, cell: _Cp1Cell) -> None:
    k = m.key
    delta = difference(sheet_value, cell.amount, percent=m.percent)
    formula = (
        "(peer-source ratio minus CP-1 ratio) x 100, percentage points"
        if m.percent
        else "peer-source ratio minus CP-1 ratio"
    )
    c.amount(
        ("T1C.6", k, "difference"),
        "Difference",
        delta,
        unit=m.difference_unit,
        period=cell.period,
        formula=formula,
        derives=(f"T1C.6.{k}.sheet", f"T1C.6.{k}.cp1"),
    )
    c.text(
        ("T1C.6", k, "result"),
        "Result",
        "Reconciled" if delta == 0 else "Differs",
        value_class="calculated",
        formula="Reconciled iff the difference is zero",
        derives=(f"T1C.6.{k}.difference",),
    )


GAP_FIELDS = (
    ("gap", "Gap"),
    ("why_it_matters", "Why it matters"),
    ("affected_analysis", "Affected analysis"),
    ("severity", "Severity"),
    ("action", "Action"),
)


def _gaps(c: _Composer, gaps: Sequence[Gap]) -> None:
    for n, gap in enumerate(gaps, 1):
        r = f"g{n:02d}"
        c.text(("T1C.7", r, "id"), "Gap id", f"CP-1C-GAP-{n:03d}")
        for name, label in GAP_FIELDS:
            c.text(
                ("T1C.7", r, name),
                label,
                getattr(gap, name),
                value_class=None if name == "severity" else "analyst_judgment",
            )
        c.row("T1C.7", r, f"Gap {n}", ["id", *(name for name, _ in GAP_FIELDS)])


def _limitations(
    present: bool,
    peers: Sequence[_Peer],
    stats: Mapping[str, _Stat | None],
    gaps: Sequence[Gap],
) -> tuple[str, ...]:
    out: list[str] = []
    if present:
        out.append(
            "Peer figures come from the peer summary source, which is supplied by a data "
            "desk and unaudited; no peer is restated to the issuer's basis."
        )
        out.append(
            "Peer ratios use the definitions stated in the peer summary; the issuer line on "
            "the same summary is tied to CP-1 in the definition alignment table."
        )
    else:
        out.append(
            "No peer source is in the pack: no peer universe, median, position or outlier "
            "flag can be formed."
        )
    out += [
        f"Partly comparable peer included: {p.data.label}: {p.assessment.limitation}"
        for p in peers
        if p.assessment.comparability == "Partly comparable"
    ]
    if present and sum(1 for p in peers if p.included) < THIN_UNIVERSE:
        out.append("Medians over fewer than five peers move with a single peer.")
    out += [
        f"Peer amount not stated: {p.data.label} {label.lower()}: every figure that needs it is "
        "Not calculable."
        for p in peers
        for key, label in OPERANDS
        if p.data.amounts[key] is None
    ]
    if present:
        out += [
            f"Peer median not calculable for {m.label.lower()}: fewer than three included peers "
            "have a stated value."
            for m in METRICS
            if (stat := stats[m.key]) is not None and stat.median is None
        ]
        out.append(
            "Outlier flags use a fixed distance of half the peer median; they are screens, "
            "not credit judgments."
        )
        out.append(
            "Peer positioning is a description of the peer set and is not a valuation or a "
            "recommendation; relative value belongs to CP-3."
        )
    out += [f"Gap ({gap.severity}): {gap.gap}" for gap in gaps]
    return tuple(out)


def _with_lineage(items: Sequence[PeerFact]) -> tuple[PeerFact, ...]:
    """A calculated fact's citations: the ordered, de-duplicated citations of the facts it
    derives from, transitively through calculated facts. A copied CP-1 cell is a leaf carrying
    CP-1's own citations, so they appear at that cell's place in derives_from order."""
    by_id = {item.fact.fact_id: item for item in items}
    memo: dict[str, tuple[Citation, ...]] = {}

    def derived(item: PeerFact) -> bool:
        return bool(item.derives_from) and item.fact.value_class == "calculated"

    def cites(fact_id: str) -> tuple[Citation, ...]:
        if fact_id not in memo:
            item = by_id[fact_id]
            if derived(item):
                found: list[Citation] = []
                for parent in item.derives_from:
                    found += [cite for cite in cites(parent) if cite not in found]
                memo[fact_id] = tuple(found)
            else:
                memo[fact_id] = item.fact.citations
        return memo[fact_id]

    return tuple(
        replace(item, fact=item.fact.model_copy(update={"citations": cites(item.fact.fact_id)}))
        if derived(item)
        else item
        for item in items
    )


@dataclass(frozen=True)
class _Composed:
    facts: tuple[PeerFact, ...]
    tables: tuple[PeerTable, ...]
    limitations: tuple[str, ...]
    peers: tuple[_Peer, ...]
    stats: Mapping[str, _Stat | None]
    absent: str


def _absence(sources: Sequence[Source]) -> str:
    """The no-peers reason: no peers source at all, or one that is not ready (round 4 (b))."""
    source = _peer_source(sources)
    return NO_PEER_SOURCE if source is None or source.status == "ready" else NO_READY_PEER_SOURCE


def _compose(inputs: PeerBenchmarkInputs, sheet: PeerSheet | None) -> _Composed:
    """Facts, tables and limitations; needs one assessment per sheet peer."""
    cp1 = _cp1_facts(inputs)
    by_label = {a.peer: a for a in inputs.submission.assessments}
    rows = sheet.peers if sheet is not None else ()
    peers = tuple(_Peer(f"p{n:02d}", row, by_label[row.label]) for n, row in enumerate(rows, 1))
    present = sheet is not None
    c = _Composer(sheet, _absence(inputs.sources))
    _universe(c, peers, present)
    _source_figures(c, sheet, peers)
    values = _normalised(c, cp1, inputs.issuer_name, peers, present)
    stats = _statistics(c, peers, values, present, {k: cell.amount for k, cell in cp1.items()})
    _outliers(c, inputs.issuer_name, peers, values, stats, present)
    _tie_out(c, sheet, cp1)
    _gaps(c, inputs.submission.gaps)
    tables = tuple(PeerTable(t, title, tuple(c.rows[t])) for t, title in TABLES.items())
    limitations = _limitations(present, peers, stats, inputs.submission.gaps)
    return _Composed(_with_lineage(c.items), tables, limitations, peers, stats, c.absent)


def _claims(composed: _Composed, submission: PeerBenchmarkSubmission) -> tuple[Claim, ...]:
    status = {item.fact.fact_id: item.fact.status for item in composed.facts}

    def ref(fact_id: str, token: str) -> str:
        return f"{{{fact_id}|{token}}}" if status[fact_id] == "known" else f"[{fact_id}]"

    claims = [
        Claim(
            claim_id=f"T1C.1.{p.row_id}",
            text=p.assessment.rationale,
            citations=p.assessment.evidence,
            limitation=p.assessment.limitation,
        )
        for p in composed.peers
    ]
    sheet, included = f"{TOTALS}.total.sheet", f"{TOTALS}.total.included"
    universe = (
        f"The peer source lists {ref(sheet, 'peers')} and {ref(included, 'peers')} are included "
        "in the universe."
        if status[sheet] == "known"
        else f"{composed.absent}, so no universe is formed {ref(sheet, 'peers')}."
    )
    claims.append(Claim(claim_id="T1C.1.universe", text=universe, citations=()))
    for m in METRICS:
        k = m.key
        text = (
            f"{m.label} of the issuer is {ref(f'T1C.3.issuer.{k}', m.token)} against a peer "
            f"median of {ref(f'T1C.4.{k}.median', m.token)} across {ref(f'T1C.4.{k}.n', 'peers')}."
        )
        stat = composed.stats[k]
        issuer_flag = None if stat is None else stat.flags.get("issuer")
        if issuer_flag is not None:  # the issuer's flag is known
            text += (
                " The issuer is flagged an outlier on this metric."
                if issuer_flag
                else " The issuer is not flagged an outlier on this metric."
            )
        elif stat is not None and stat.median == 0:  # round 2 C2
            text += (
                " The outlier test does not apply to this metric because the peer median is zero."
            )
        claims.append(Claim(claim_id=f"T1C.4.{k}", text=text, citations=()))
    overall = submission.overall
    claims.append(
        Claim(
            claim_id="T1C.1.assessment",
            text=overall.rationale,
            citations=overall.evidence,
            limitation=overall.limitation,
        )
    )
    return tuple(claims)


# --- validation (calculation-level content rules) and the entry point ---------------------------------


def _peer_source(sources: Sequence[Source]) -> Source | None:
    return next((s for s in sources if s.source_id == PEERS_SOURCE_ID), None)


def _assessment_set_issues(
    submission: PeerBenchmarkSubmission, sheet: PeerSheet | None
) -> list[str]:
    """Exactly one assessment per sheet peer by exact label; none without a peer source."""
    if sheet is None:
        return [
            f"Assessment given without a peer source in the pack: {a.peer}"
            for a in submission.assessments
        ]
    labels = [row.label for row in sheet.peers]
    unknown = [a.peer for a in submission.assessments if a.peer not in labels]
    counts = Counter(a.peer for a in submission.assessments)
    issues = [f"Unknown peer: {peer}" for peer in dict.fromkeys(unknown)]
    issues += [
        f"Assess each sheet peer exactly once: {label}" for label in labels if counts[label] != 1
    ]
    return issues


def _content_issues(submission: PeerBenchmarkSubmission, sheet: PeerSheet | None) -> list[str]:
    issues: list[str] = []
    if sheet is not None and submission.overall.confidence == "High":
        issues.append("Confidence cannot be High: the peer figures are desk-supplied and unaudited")
    for a in submission.assessments:
        if not a.evidence:
            issues.append(f"Evidence required for a comparability assessment: {a.peer}")
        if a.comparability == "Partly comparable" and not (a.limitation or "").strip():
            issues.append(f"Limitation required for Partly comparable: {a.peer}")
    return issues


def _prohibited_fields(submission: PeerBenchmarkSubmission) -> list[tuple[str, str]]:
    """Every analyst text field, in the order of round 2 ruling C1 (paths 0-based, 1C5)."""
    fields: list[tuple[str, str]] = []
    for n, a in enumerate(submission.assessments):
        fields.append((f"assessments[{n}].rationale", a.rationale))
        if a.limitation is not None:
            fields.append((f"assessments[{n}].limitation", a.limitation))
    fields.append(("overall.rationale", submission.overall.rationale))
    fields.append(("overall.limitation", submission.overall.limitation))
    for n, gap in enumerate(submission.gaps):
        for name in ("gap", "why_it_matters", "affected_analysis", "action"):
            fields.append((f"gaps[{n}].{name}", getattr(gap, name)))
    return fields


def _prose_texts(submission: PeerBenchmarkSubmission) -> list[str]:
    """The run texts the bare-figure and reference rules read: every rationale."""
    return [a.rationale for a in submission.assessments] + [submission.overall.rationale]


def calculation_issues(inputs: PeerBenchmarkInputs) -> tuple[str, ...]:
    """Every content issue of the analyst payload against the peer source and the module's own
    facts. An unreadable peer table returns alone (1C4). References in the analyst's text are checked
    against the composed facts only when the assessment set is consistent (before that there
    are no facts to bind them to, and the set issues already refuse the payload)."""
    submission = inputs.submission
    try:
        sheet = parse_peer_source(_peer_source(inputs.sources), issuer_name=inputs.issuer_name)
    except PeerTableError as error:
        return (str(error),)
    set_issues = _assessment_set_issues(submission, sheet)
    issues = [*set_issues, *_content_issues(submission, sheet)]
    citations = tuple(c for a in submission.assessments for c in a.evidence)
    issues += citation_issues((*citations, *submission.overall.evidence), inputs.sources)
    for path, text in _prohibited_fields(submission):
        issues += prohibited_issues(path, text, kinds=PROHIBITED_KINDS)
    if not set_issues:
        bound = prose.bind(item.fact for item in _compose(inputs, sheet).facts)
        for text in _prose_texts(submission):
            issues += prose.issues(text, bound, names=(inputs.issuer_name,))
    return tuple(dict.fromkeys(issues))


def compute(inputs: PeerBenchmarkInputs) -> PeerBenchmarkResult:
    """The module's facts, tables, claims and own limitations; ValueError on any issue."""
    if issues := calculation_issues(inputs):
        raise ValueError("; ".join(issues))
    sheet = parse_peer_source(_peer_source(inputs.sources), issuer_name=inputs.issuer_name)
    composed = _compose(inputs, sheet)
    claims = _claims(composed, inputs.submission)
    return PeerBenchmarkResult(composed.facts, composed.tables, claims, composed.limitations)
