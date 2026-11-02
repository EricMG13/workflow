"""CP-1C (Peer benchmark): the Stage 1 calculation, pure Python over typed inputs.

Lease: docs/CP1C-OWNER-LEASE.md (frozen revision 4 with amendment 1: the universe totals are
table T1C.8), as extended by docs/rulings/2026-10-28-stage1.md (CP-1C 1C1-1C6, round 2 C1-C3;
a ruling wins over the lease). Oracle: cases/cp1c-owner/expected.json. Python owns every number: peer ratios,
medians, differences, positions, deviations, outlier flags and counts, all in an exact 38-digit
half-even decimal context. The analyst supplies only comparability judgments, rationale text,
the overall view and the gaps. No I/O, store, host, session or render call happens here; the
connection (pack, CP-1 head, tool use) and orchestration concerns join this file in later stages.
"""

import hashlib
import importlib
import json
import re
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal
from itertools import pairwise
from types import ModuleType
from typing import TYPE_CHECKING, Any, Literal

from pydantic import TypeAdapter, ValidationError

from deploy_vii import prose
from deploy_vii.business_context import Category, Severity, prohibited_issues
from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Input,
    InputStatus,
    Module,
    ReportTable,
    RunText,
    Source,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.contracts import Run as PackRun
from deploy_vii.display import format_value
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepValidation,
    clipped,
    current_inputs,
    inherited_limitations,
    listed_issues,
)
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import Submitted
from deploy_vii.live.tools import Seen
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import citation_issues, shape_issues
from deploy_vii.report_view import fact_spelling
from deploy_workflow.context import ContextRefused, RunContext, Valuation, context_facts
from deploy_workflow.context_cites import context_text
from deploy_workflow.owners.blank import is_blank, one_per_page
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.owners.cp2g import select_cp1
from deploy_workflow.owners.period_basis import (
    DEFAULT_BASIS,
    DEFAULT_CURRENCY,
    PeriodBasis,
    PeriodRefused,
    run_basis,
)
from deploy_workflow.research.contracts import RESERVED_PREFIX
from deploy_workflow.research.steps import unread_issues

if TYPE_CHECKING:
    from deploy_workflow.owners.valuation_basis import (
        Admission,
        AdmittedRecord,
        Selection,
        SetStats,
    )

MODULE_ID = "CP-1C"

# One context for every operation: 38 significant digits, half-even (lease "peer metric").
CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)

# Policy constants (lease open questions 2 and 3, expected.json policy_constants).
MIN_INCLUDED_PEERS = 3
OUTLIER_FRACTION = Decimal("0.5")
# Below this many included peers a limitation says medians move with one peer (oracle wording).
THIN_UNIVERSE = 5
THIN_LINE = "Medians over fewer than five peers move with a single peer."

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


def mixed_period(basis: PeriodBasis) -> str:
    """The period of a fact derived from the issuer's CP-1 column and the peers' own twelve months."""
    return f"Mixed: issuer {basis.ltm_tag}, each peer's own twelve months"


MIXED_PERIOD = mixed_period(DEFAULT_BASIS)  # the default basis; a run's basis builds its own
PROHIBITED_KINDS = ("instrument recommendation", "recovery conclusion")
EXCLUDED = "Not meaningful: the peer is excluded from the universe"
NO_MEDIAN = "Not calculable: no peer median (fewer than three included peers have a value)"
OWN_NOT_MEANINGFUL = "Not meaningful: the peer's own ratio is not meaningful"  # ruling 1C1
ZERO_MEDIAN = "Not meaningful: the peer median is zero"
NOT_COMPARED = "Not compared: one side is not available"  # ruling 1C2
# Round 6 B1: the issuer's own outlier cells when its CP-1 ratio is not known.
ISSUER_NOT_STATED = "Not calculable: the issuer's CP-1 value is missing"
ISSUER_NOT_MEANINGFUL = "Not meaningful: the issuer's CP-1 ratio is not meaningful"
ISSUER_CONFLICTING = "Not calculable: the issuer's CP-1 value is conflicting"  # round 6h (a)
# Round 2 C3: page:1 must carry this clause in its Basis line; the clause is what gives a source
# amount its currency, unit and scale. Any other basis is outside the table rule.
BASIS_PREFIX = "Basis:"
# The one supported clause pair is the run's currency and this unit (Phase 8: the currency is the
# run's, so a peers page stating another currency is outside the table rule).
BASIS_UNIT_CLAUSE = "amounts in millions"
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


def _basis(lines: Sequence[str], currency: str) -> tuple[str, str, Decimal]:
    """Currency, unit and scale from the supported clause of a page:1 Basis line (C3): the run's
    `currency` and the millions clause."""
    for line in lines:
        if not line.startswith(BASIS_PREFIX):
            continue
        parts = [part.strip().rstrip(".") for part in line[len(BASIS_PREFIX) :].split(";")]
        for pair in pairwise(parts):
            if pair == (currency, BASIS_UNIT_CLAUSE):
                return currency, "MILLIONS", Decimal(1_000_000)
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
        if parts[0] in basis:  # round 4 (a): a repeated page:2 label
            raise PeerTableError(TABLE_NOT_FOUND)
        basis[parts[0]] = BasisLine(parts[1], parts[2], parts[3], line)
    return basis


def _row(line: str, basis: Mapping[str, BasisLine]) -> PeerRow:
    parts = _split(line)
    if len(parts) != 7:
        raise PeerTableError(TABLE_NOT_FOUND)
    amounts = {key: _amount(token) for (key, _), token in zip(OPERANDS, parts[2:], strict=True)}
    return PeerRow(parts[0], _period_end(parts[1]), amounts, line, basis.get(parts[0]))


def parse_peer_source(
    source: Source | None, *, issuer_name: str, currency: str = DEFAULT_CURRENCY.currency
) -> PeerSheet | None:
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
    currency, unit, scale = _basis(lines[:start], currency)
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


Status = Literal["missing", "not_applicable", "conflicting"]  # conflicting: CP-1's only (6g)


@dataclass(frozen=True)
class Unsettled:
    status: Status
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
    # Phase 7: the run's context file, its source (the lines it cites) and CP-1's LTM adjusted
    # EBITDA fact. All three stay None without a context, and then T1C.9-T1C.11 are not composed.
    context: RunContext | None = None
    context_source: Source | None = None
    cp1_ebitda: Fact | None = None
    # Phase 8: the run's period and currency (the default is the pre-Phase 8 run); the issuer
    # column, the mixed period and the peers page's Basis clause follow it.
    basis: PeriodBasis = DEFAULT_BASIS


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
    def __init__(self, sheet: PeerSheet | None, absent: str, basis: PeriodBasis) -> None:
        self.mixed = mixed_period(basis)
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
            period=self.mixed,
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
        status: Status = "missing",
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
        """The CP-1 fact verbatim under this module's id: status, limitation, unit, amount,
        decimals, currency, scale, period, value class, citations and CP-1's own calculation
        id (round 6 B1: status and limitation too, for every copy)."""
        table, row, name = ref
        self._add(
            Fact(
                fact_id=_fid(ref),
                label=label,
                table_id=table,
                row_id=row,
                field=name,
                status=cp1.status,
                limitation=cp1.limitation,
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
    value: tuple[Decimal, str] | Unsettled  # the known amount and its period, or why not


def _cp1_facts(inputs: PeerBenchmarkInputs) -> dict[str, _Cp1Cell]:
    return _cp1_cells(inputs.cp1_metrics)


def _cp1_cells(metrics: Mapping[str, Fact]) -> dict[str, _Cp1Cell]:
    """The CP-1 T4.10 fact per metric. A known one is numeric, in the metric's unit, with a
    period. A missing, not_applicable or conflicting one is carried with CP-1's limitation and
    takes the metric's unit, currency and scale (round 6 B1, round 6g). An absent fact, or a
    known one breaking those rules, is an invariant."""
    found: dict[str, _Cp1Cell] = {}
    for metric in METRICS:
        fact = metrics.get(metric.key)
        if fact is None:
            raise ValueError(f"CP-1 fact unavailable for {metric.key}")
        if fact.status != "known" and fact.limitation:
            # a ratio has no currency and scale 1, as T1C.3's own ratios
            metric_basis = {"unit": metric.unit, "currency": None, "scale": Decimal(1)}
            unsettled = fact.model_copy(update=metric_basis)
            found[metric.key] = _Cp1Cell(unsettled, Unsettled(fact.status, fact.limitation))
            continue
        if fact.status != "known" or fact.unit != metric.unit:
            raise ValueError(f"CP-1 fact unavailable for {metric.key}")
        if fact.amount is None or fact.period is None:
            raise ValueError(f"CP-1 fact unavailable for {metric.key}")
        found[metric.key] = _Cp1Cell(fact, (fact.amount, fact.period))
    return found


Values = dict[tuple[str, str], Ratio]


def _normalised(
    c: _Composer, cp1: Mapping[str, _Cp1Cell], issuer: str, peers: Sequence[_Peer], present: bool
) -> Values:
    values: Values = {}
    for m in METRICS:
        cell = cp1[m.key]
        c.copy(("T1C.3", "issuer", m.key), m.label, cell.fact)
        own = cell.value
        values[("issuer", m.key)] = own if isinstance(own, Unsettled) else Known(own[0])
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
    c: _Composer, m: Metric, issuer: Ratio, known: Sequence[tuple[str, Decimal]], med: Decimal
) -> None:
    k = m.key
    ders = tuple(f"T1C.3.{r}.{k}" for r, _ in known)
    own = f"T1C.3.issuer.{k}"
    c.amount(
        ("T1C.4", k, "median"),
        STAT_LABELS["median"],
        med,
        unit=m.unit,
        period=c.mixed,
        formula="median of included peers' values; even count: (a + b) / 2",
        derives=ders,
    )
    if isinstance(issuer, Unsettled):  # round 6 B1: the issuer side is not available
        units = _gap_units(m)
        for name in ("difference", "position", "of"):
            c.unsettled(
                ("T1C.4", k, name),
                STAT_LABELS[name],
                NOT_COMPARED,
                unit=units[name],
                period=c.mixed,
            )
        return
    formula = (
        "(issuer value minus peer median) x 100, percentage points"
        if m.percent
        else "issuer value minus peer median"
    )
    c.amount(
        ("T1C.4", k, "difference"),
        STAT_LABELS["difference"],
        difference(issuer.value, med, percent=m.percent),
        unit=m.difference_unit,
        period=c.mixed,
        formula=formula,
        derives=(own, f"T1C.4.{k}.median"),
    )
    rank, of = position(issuer.value, [v for _, v in known], higher_is_better=m.higher_is_better)
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
    c: _Composer, peers: Sequence[_Peer], values: Values, present: bool
) -> dict[str, _Stat | None]:
    """T1C.4 per metric; the issuer's value is its copied CP-1 value."""
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
                    period=c.mixed,
                )
            continue
        _settled_stats(c, m, values[("issuer", k)], known, med)
    return stats


def _flag_operands(
    peer: _Peer | None, value: Ratio, stat: _Stat
) -> Unsettled | tuple[Decimal, Decimal]:
    """Why the deviation and flag are unsettled, in the ruled order (1C1): excluded, median
    missing, value conflicting, missing or not_applicable, median zero; else (value, median)."""
    if peer is not None and not peer.included:
        return Unsettled("not_applicable", EXCLUDED)
    if stat.median is None:
        return Unsettled("missing", NO_MEDIAN)
    if isinstance(value, Unsettled):  # the issuer (peer None) has its own wording (round 6 B1)
        if value.status == "conflicting":  # only the issuer's CP-1 value (rounds 6g, 6h (a))
            return Unsettled("missing", ISSUER_CONFLICTING)
        if value.status == "missing":
            why = (
                ISSUER_NOT_STATED
                if peer is None
                else "Not calculable: the peer's value is not stated"
            )
            return Unsettled("missing", why)
        return Unsettled(
            "not_applicable", ISSUER_NOT_MEANINGFUL if peer is None else OWN_NOT_MEANINGFUL
        )
    if stat.median == 0:
        return Unsettled("not_applicable", ZERO_MEDIAN)
    return value.value, stat.median


def _flag_labels(m: Metric) -> tuple[str, str]:
    return f"{m.label} · Deviation from median", f"{m.label} · Flag"


def _flag_cells(
    c: _Composer, row_id: str, peer: _Peer | None, m: Metric, value: Ratio, stat: _Stat
) -> None:
    dev = ("T1C.5", row_id, f"{m.key}_deviation")
    flag = ("T1C.5", row_id, f"{m.key}_flag")
    dev_label, flag_label = _flag_labels(m)
    operands = _flag_operands(peer, value, stat)
    if isinstance(operands, Unsettled):
        gap = operands
        c.unsettled(dev, dev_label, gap.reason, unit=PERCENT, period=c.mixed, status=gap.status)
        c.unsettled(flag, flag_label, gap.reason, unit=None, period=c.mixed, status=gap.status)
        return
    deviation, verdict = _deviation(*operands)
    c.amount(
        dev,
        dev_label,
        deviation,
        unit=PERCENT,
        period=c.mixed,
        formula="(value - peer median) / peer median",
        derives=(f"T1C.3.{row_id}.{m.key}", f"T1C.4.{m.key}.median"),
    )
    c.text(
        flag,
        flag_label,
        verdict,
        value_class="calculated",
        period=c.mixed,
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
                period=c.mixed,
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
        else:
            c.amount(
                ("T1C.6", k, "sheet"),
                label,
                line[0],
                unit=m.unit,
                period=line[1],
                formula=f"{OPERAND_LABEL[m.numerator]} / {OPERAND_LABEL[m.denominator]} "
                "from the issuer line",
                derives=(f"T1C.2.issuer.{m.numerator}", f"T1C.2.issuer.{m.denominator}"),
            )
        c.copy(("T1C.6", k, "cp1"), "CP-1", cell.fact)
        if isinstance(line, Unsettled) or isinstance(cell.value, Unsettled):
            # ruling 1C2 / round 4 (d) / round 6 B1: one side is not available, so nothing is
            # compared; the absent-source reason comes first
            reason = c.absent if sheet is None else NOT_COMPARED
            unit = m.difference_unit
            c.unsettled(("T1C.6", k, "difference"), "Difference", reason, unit=unit, period=None)
            c.text(("T1C.6", k, "result"), "Result", "Not compared")
        else:
            _tie_out_settled(c, m, line[0], *cell.value)
        c.row("T1C.6", k, m.label, ("sheet", "cp1", "difference", "result"))


def _tie_out_settled(
    c: _Composer, m: Metric, sheet_value: Decimal, cp1_value: Decimal, cp1_period: str
) -> None:
    k = m.key
    delta = difference(sheet_value, cp1_value, percent=m.percent)
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
        period=cp1_period,
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
    absent: str,
    cp1: Mapping[str, _Cp1Cell],
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
        out.append(  # round 5 P1: the reason names a missing or a not-ready source
            f"{absent}: no peer universe, median, position or outlier flag can be formed."
        )
    out += [  # round 6 B1
        f"The issuer's {m.label[0].lower()}{m.label[1:]} is not available in CP-1 "
        f"({own.reason}), so its difference from the peer median, its position and its "
        "outlier flag are not compared."
        for m in METRICS
        if isinstance(own := cp1[m.key].value, Unsettled)
    ]
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
    """A calculated fact's citations: one Citation per (source, page), the first quote on that
    page among the citations of the facts it derives from, in derives_from order, transitively
    through calculated facts (rulings stage2 round 3 item 3). A copied CP-1 cell is a leaf
    carrying CP-1's own citations, so they appear at that cell's place in derives_from order."""
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
                    found += cites(parent)
                memo[fact_id] = one_per_page(found)
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


# --- the context's EV/EBITDA tables T1C.9-T1C.11 (Phase 7, Design 3-10) ------------------------------
# Composed only when the pack holds a `context` source with a valuation to show; the eight tables
# above are the default and are not touched. The arithmetic is `owners/valuation_basis.py`, which
# imports this module, so it is imported on first use (`_vbasis`). Oracle:
# cases/valuation-context-owner/expected.json (`cases.<case>.cp1c`).

JsonPath = tuple[str | int, ...]
EvStatus = Literal["known", "missing", "not_applicable"]

EV_TABLES: Mapping[str, str] = {
    "T1C.9": "EV/EBITDA records",
    "T1C.10": "EV/EBITDA statistics",
    "T1C.11": "Valuation basis selection",
}
EV_COLUMNS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "T1C.9": (
        ("kind", "Kind"),
        ("name", "Name"),
        ("figures_date", "Figures dated"),
        ("source", "Source"),
        ("currency", "Currency"),
        ("ebitda_period", "EBITDA period"),
        ("ev", "Enterprise value"),
        ("ebitda", "EBITDA"),
        ("multiple", "EV/EBITDA"),
        ("flag", "Outlier flag"),
        ("result", "Result"),
    ),
    "T1C.10": (
        ("n_total", "Records"),
        ("n_admitted", "Admitted"),
        ("min", "Minimum"),
        ("median", "Median"),
        ("max", "Maximum"),
        ("outliers", "Outliers"),
    ),
    "T1C.11": (
        ("requested_basis", "Requested basis"),
        ("selected_basis", "Selected basis"),
        ("reason", "Reason"),
        ("ebitda_basis", "EBITDA basis"),
        ("selected_multiple", "Selected multiple"),
        ("issuer_ebitda", "Issuer EBITDA"),
        ("implied_ev", "Implied enterprise value"),
    ),
}
EV_ROW_HEADERS: Mapping[str, str] = {"T1C.9": "Record", "T1C.10": "Set", "T1C.11": "Selection"}
# What a consumer reads from a head that holds T1C.11 (Design 10); a frozen head has none of them.
EV_READER_FACTS: tuple[str, ...] = (
    "T1C.11.selection.selected_multiple",
    "T1C.11.selection.selected_basis",
    "T1C.11.selection.ebitda_basis",
    "T1C.11.selection.implied_ev",
)
SELECTION_TABLE = "T1C.11"

NOT_STATED_BY_USER = "Not stated by the user"
NO_DATE_PERIOD = "Date not stated by the user"
NO_RECORDS = "No peer or precedent records are in the context"
EXCLUDED_FROM_STATS = "Not meaningful: the record is excluded from the statistics"
NO_FIGURES = "Excluded: no peer figures in the context"
SINGLE_VALUE = " (a single value: min, median and max are the value)"
RESULT_FORMULA = (
    "Included when EV and EBITDA are above zero and the record is dated within the window"
)
FLAG_FORMULA = "Outlier when the absolute deviation from the set median is above one half"
ISSUER_EBITDA_FORMULA = "CP-1 LTM adjusted EBITDA (T4.10)"
CP1_REF = (
    "cp1:ebitda"  # derives_from entry naming the CP-1 fact, which is not a fact of this module
)
# Design 8: until O7d's TDR.6 pack exists, these peer sources give no figures and no fallback.
PUBLIC_GAPS: Mapping[str, str] = {
    "cp_dr_public": "No peer figures: cp_dr_public peers come from the CP-DR peer pack (Part B O7d)",
    "user_list": "No peer figures: user_list peers need the peer lookup (O7d)",
}
USER_FIGURES_LINE = (
    "The EV and EBITDA figures of the peers and precedents are the user's own entries in the "
    "context file; CP-1C does not verify them against a source."
)


def currency_period_line(basis: PeriodBasis) -> str:
    return (
        "The peers' and precedents' currency and EBITDA period are not stated by the user; each "
        "multiple assumes its EV and EBITDA share both, and the selected multiple is applied to the "
        f"issuer's {basis.ltm_tag} EBITDA."
    )


CURRENCY_PERIOD_LINE = currency_period_line(DEFAULT_BASIS)
# The formula of a selected multiple, by the basis that was selected.
SELECTED_FORMULAS: Mapping[str, str] = {
    "public_comps": "median of the admitted public comps' multiples, rounded half-even to 2 dp",
    "precedents": "median of the admitted precedents' multiples, rounded half-even to 2 dp",
    "blend": "(public comps median + precedents median) / 2, rounded half-even to 2 dp",
    "issuer_trading": "issuer enterprise value / CP-1 LTM adjusted EBITDA, rounded half-even to 2 dp",
    "user_multiple": "user-supplied multiple",
}


def _vbasis() -> ModuleType:
    """`valuation_basis` (it imports this module for its constants), imported on first use."""
    return importlib.import_module("deploy_workflow.owners.valuation_basis")


def shows_valuation(valuation: Valuation) -> bool:
    """Design 9: the context has a valuation to show. A peer source that gives no figures shows
    only for a basis that needs peers; a basis that needs no peers (`precedents`, `issuer_trading`,
    `user_multiple`) shows without any."""
    peer_basis = valuation.basis in ("auto", "public_comps", "blend")
    return (
        valuation.peer_source == "user_comps"
        or (valuation.peer_source in PUBLIC_GAPS and peer_basis)
        or bool(valuation.precedents)
        or valuation.basis in ("auto", "issuer_trading", "user_multiple")
    )


# --- citing the context file by line ---


class _LineWalk:
    """The 1-based line of every value of a JSON text, by path (member names and list indexes)."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0
        self.lines: dict[JsonPath, int] = {}
        self.breaks = [i for i, char in enumerate(text) if char == "\n"]

    def peek(self) -> str:
        return self.text[self.at : self.at + 1]

    def skip(self) -> None:
        while self.peek() in (" ", "\t", "\r", "\n"):
            self.at += 1

    def scalar(self) -> object:
        value, self.at = json.JSONDecoder().raw_decode(self.text, self.at)
        return value

    def node(self, path: JsonPath) -> None:
        self.skip()
        self.lines[path] = bisect_left(self.breaks, self.at) + 1
        opener = self.peek()
        if opener == "{":
            self.members(path)
        elif opener == "[":
            self.elements(path)
        else:
            self.scalar()

    def members(self, path: JsonPath) -> None:
        self.at += 1
        self.skip()
        while self.peek() != "}":
            name = str(self.scalar())
            self.skip()
            self.at += 1  # the colon
            self.node((*path, name))
            self.next_item()
        self.at += 1

    def elements(self, path: JsonPath) -> None:
        self.at += 1
        self.skip()
        index = 0
        while self.peek() != "]":
            self.node((*path, index))
            self.next_item()
            index += 1
        self.at += 1

    def next_item(self) -> None:
        self.skip()
        if self.peek() == ",":
            self.at += 1
            self.skip()


@dataclass(frozen=True)
class _ContextCites:
    """A citation of one value of the context file: its `line:<n>` span, the line as written."""

    source: Source
    lines: Mapping[JsonPath, int]

    def __call__(self, *paths: JsonPath) -> tuple[Citation, ...]:
        return tuple(self.one(path) for path in paths)

    def one(self, path: JsonPath) -> Citation:
        if path not in self.lines or self.source.sha256 is None:
            raise ValueError(f"The context file has no citable value at {path}")
        number = self.lines[path]
        span = self.source.spans[number - 1]
        if span.locator != f"line:{number}":
            raise ValueError(
                f"The context source span {number} is {span.locator}, not line:{number}"
            )
        return Citation(
            source_id=self.source.source_id,
            source_sha256=self.source.sha256,
            locator=span.locator,
            quote=span.text.strip(),
        )


def context_cites(source: Source) -> _ContextCites:
    """The citer of `source`; ValueError when the source cannot be read by line."""
    try:
        walk = _LineWalk(context_text(source))
        walk.node(())
    except ValueError as error:  # context_text, the JSON decoder
        raise ValueError(f"the context source cannot be cited by line: {error}") from error
    return _ContextCites(source, walk.lines)


# --- admission, statistics and selection over the context (the arithmetic is valuation_basis) ---


@dataclass(frozen=True)
class _EvRow:
    row_id: str
    kind: str  # "peer" or "precedent"
    name: str
    paths: Mapping[str, JsonPath]  # field -> the value's path in the context file
    record: "AdmittedRecord | None"  # None: a user_list name, which has no figures
    admission: "Admission | None" = None


@dataclass(frozen=True)
class _EvSet:
    set_id: str  # "public_comps" or "precedents"
    label: str
    start: date
    rows: tuple[_EvRow, ...]
    stats: "SetStats"

    def admitted(self) -> tuple[_EvRow, ...]:
        return tuple(r for r in self.rows if r.admission is not None and r.admission.included)


@dataclass(frozen=True)
class _EvPlan:
    valuation: Valuation
    as_of: date
    public: _EvSet
    precedents: _EvSet
    selection: "Selection"
    ebitda: Fact  # CP-1's LTM adjusted EBITDA, as CP-4C reads it
    ebitda_amount: Decimal | None  # its amount when it is a known positive MILLIONS amount

    @property
    def sets(self) -> tuple[_EvSet, ...]:
        return (self.public, self.precedents)


_PEER_KEYS = {"name": "name", "figures_date": "as_of"}
_PRECEDENT_KEYS = {"name": "target", "figures_date": "date"}


def _figure_row(
    kind: str,
    row_id: str,
    path: JsonPath,
    keys: Mapping[str, str],
    values: tuple[
        str, str, str, str, str
    ],  # name, date, source, EV, EBITDA as the file writes them
) -> _EvRow:
    name, when, source, ev, ebitda = values
    record = _vbasis().AdmittedRecord(
        "user_comps",
        kind,
        name,
        date.fromisoformat(when) if when else None,
        source,
        Decimal(ev),
        Decimal(ebitda),
    )
    named = {**keys, "source": "source", "ev": "ev_m", "ebitda": "ebitda_m"}
    return _EvRow(row_id, kind, name, {f: (*path, key) for f, key in named.items()}, record)


def _precedent_rows(valuation: Valuation) -> list[_EvRow]:
    return [
        _figure_row(
            "precedent",
            f"x{n:02d}",
            ("valuation", "precedents", n - 1),
            _PRECEDENT_KEYS,
            (p.target, p.date, p.source, p.ev_m, p.ebitda_m),
        )
        for n, p in enumerate(valuation.precedents, 1)
    ]


def _peer_rows(valuation: Valuation) -> list[_EvRow]:
    if valuation.peer_source == "user_comps":
        return [
            _figure_row(
                "peer",
                f"e{n:02d}",
                ("valuation", "peers", n - 1),
                _PEER_KEYS,
                (p.name, p.as_of, p.source, p.ev_m, p.ebitda_m),
            )
            for n, p in enumerate(valuation.peers, 1)
        ]
    if valuation.peer_source == "user_list":  # names only; the figures need the peer lookup (O7d)
        return [
            _EvRow(
                f"e{n:02d}", "peer", p.name, {"name": ("valuation", "peers", n - 1, "name")}, None
            )
            for n, p in enumerate(valuation.peers, 1)
        ]
    return []


def _ev_set(set_id: str, label: str, months: int, rows: list[_EvRow], as_of: date) -> _EvSet:
    vb = _vbasis()
    figures = [r.record for r in rows if r.record is not None]
    admissions = iter(vb.admit(figures, as_of, months))
    done = tuple(
        replace(r, admission=next(admissions)) if r.record is not None else r for r in rows
    )
    held = [r.admission for r in done if r.admission is not None]
    stats = (
        vb.stats(held)
        if len(held) == len(done)
        else vb.SetStats(len(done), 0, None, None, None, None)
    )
    return _EvSet(set_id, label, vb.window_start(as_of, months), done, stats)


def _selection(
    valuation: Valuation, public: _EvSet, precedents: _EvSet, ebitda: Decimal | None
) -> "Selection":
    """`select_basis`, with the Design 8 gaps for the peer sources that give no figures."""
    vb = _vbasis()
    chosen: Selection = vb.select_basis(
        valuation.basis,
        tuple(r.admission for r in public.rows if r.admission),
        tuple(r.admission for r in precedents.rows if r.admission),
        valuation.issuer_market,
        valuation.user_multiple,
        ebitda,
    )
    gap = PUBLIC_GAPS.get(valuation.peer_source)
    if gap is None:
        return chosen
    if valuation.basis == "public_comps":
        return replace(chosen, selected_basis=None, multiple=None, reason=gap, implied_ev=None)
    if valuation.basis == "auto" and chosen.selected_basis == vb.INSUFFICIENT:
        if valuation.peer_source == "user_list":
            return replace(chosen, selected_basis=None, reason=gap)
        thin = f"precedents {precedents.stats.n_admitted} admitted of {vb.MIN_ADMITTED} required"
        return replace(chosen, reason=f"{gap}; {thin}")
    return chosen


def _ev_plan(inputs: PeerBenchmarkInputs) -> _EvPlan:
    context, ebitda = inputs.context, inputs.cp1_ebitda
    if context is None or ebitda is None:
        raise ValueError("The EV/EBITDA tables need the context and CP-1's LTM adjusted EBITDA")
    vb, valuation = _vbasis(), context.valuation
    as_of = date.fromisoformat(context.run.as_of)
    public = _ev_set("public_comps", "Public comps", vb.PEER_MONTHS, _peer_rows(valuation), as_of)
    precedents = _ev_set(
        "precedents", "Precedents", vb.PRECEDENT_MONTHS, _precedent_rows(valuation), as_of
    )
    usable = (
        ebitda.status == "known"
        and ebitda.unit == "MILLIONS"
        and ebitda.period is not None
        and ebitda.amount is not None
        and ebitda.amount > 0
    )
    amount = ebitda.amount if usable else None
    selection = _selection(valuation, public, precedents, amount)
    return _EvPlan(valuation, as_of, public, precedents, selection, ebitda, amount)


# --- the facts of T1C.9-T1C.11 ---


class _EvEmitter:
    """The facts and rows of the three tables. Citations are written here, one per user figure
    (`value_class` source) and the same lines on every fact derived from it; nothing is inherited
    afterwards, so a fact that mixes the context with CP-1 (the implied EV) carries none."""

    def __init__(self, cite: _ContextCites) -> None:
        self.cite = cite
        self.items: list[PeerFact] = []
        self.rows: dict[str, list[TableRow]] = {table: [] for table in EV_TABLES}

    def put(
        self,
        ref: Ref,
        *,
        status: EvStatus = "known",
        text: str | None = None,
        amount: Decimal | None = None,
        unit: str | None = None,
        period: str | None = None,
        decimals: int | None = None,
        currency: str | None = None,
        value_class: Literal["source", "normalized", "calculated"] | None = None,
        formula: str | None = None,
        derives: Sequence[str] = (),
        citations: tuple[Citation, ...] = (),
        limitation: str | None = None,
    ) -> str:
        table, row, name = ref
        known = status == "known"
        fact = Fact(
            fact_id=_fid(ref),
            label=dict(EV_COLUMNS[table])[name],
            table_id=table,
            row_id=row,
            field=name,
            status=status,
            text=text,
            amount=amount,
            unit=unit,
            currency=currency,
            scale=Decimal(1_000_000) if unit == "MILLIONS" else Decimal(1),
            decimals=decimals,
            period=period,
            citations=citations,
            calculation_id=f"calc:{_fid(ref)}" if known and value_class == "calculated" else None,
            value_class=value_class if known else None,
            formula=formula if known else None,
            limitation=limitation,
        )
        self.items.append(PeerFact(fact, tuple(derives)))
        return fact.fact_id

    def text(
        self,
        ref: Ref,
        value: str,
        value_class: Literal["source", "normalized", "calculated"],
        **kw: Any,
    ) -> str:
        return self.put(ref, text=value, value_class=value_class, **kw)

    def gap(self, ref: Ref, reason: str, status: EvStatus = "missing", **kw: Any) -> str:
        return self.put(ref, status=status, limitation=reason, **kw)

    def line(self, table: str, row_id: str, label: str, fact_ids: Sequence[str]) -> None:
        self.rows[table].append(TableRow(row_id=row_id, label=label, fact_ids=tuple(fact_ids)))


def _not_calculable(admitted: int) -> str:
    return f"Not calculable: {admitted} admitted of {MIN_INCLUDED_PEERS} required"


def _date_fact(e: _EvEmitter, row: _EvRow, record: "AdmittedRecord") -> str:
    ref = ("T1C.9", row.row_id, "figures_date")
    if record.figures_date is None:
        return e.gap(ref, NOT_STATED_BY_USER)
    return e.text(
        ref, record.figures_date.isoformat(), "source", citations=e.cite(row.paths["figures_date"])
    )


def _multiple_fact(e: _EvEmitter, row: _EvRow, admission: "Admission", period: str) -> str:
    ref = ("T1C.9", row.row_id, "multiple")
    if admission.multiple is None:  # EV or EBITDA is not a positive finite amount
        reason = "Not meaningful: " + admission.reason.removeprefix("Excluded: ")
        return e.gap(ref, reason, status="not_applicable", unit=MULTIPLE, period=period)
    return e.put(
        ref,
        amount=admission.multiple,
        unit=MULTIPLE,
        period=period,
        decimals=2,
        value_class="calculated",
        formula="EV / EBITDA",
        derives=(f"T1C.9.{row.row_id}.ev", f"T1C.9.{row.row_id}.ebitda"),
        citations=e.cite(row.paths["ev"], row.paths["ebitda"]),
    )


def _flag_fact(e: _EvEmitter, row: _EvRow, admission: "Admission", ev_set: _EvSet) -> str:
    ref = ("T1C.9", row.row_id, "flag")
    if not admission.included:
        return e.gap(ref, EXCLUDED_FROM_STATS, status="not_applicable")
    median = ev_set.stats.median
    if median is None:
        return e.gap(ref, _not_calculable(ev_set.stats.n_admitted))
    found = outlier(admission.multiple, median) if admission.multiple is not None else None
    if found is None:  # a zero median cannot arise from admitted (positive) multiples
        return e.gap(ref, "Not meaningful: the set median is zero", status="not_applicable")
    derives = (f"T1C.9.{row.row_id}.multiple", f"T1C.10.{ev_set.set_id}.median")
    return e.text(ref, found[1], "normalized", formula=FLAG_FORMULA, derives=derives)


def _figure_facts(e: _EvEmitter, row: _EvRow, ev_set: _EvSet, admission: "Admission") -> list[str]:
    t, r, record = "T1C.9", row.row_id, admission.record
    period = f"As of {record.figures_date}" if record.figures_date else NO_DATE_PERIOD
    kind = "Public comp" if row.kind == "peer" else "Precedent"

    def money(name: str, amount: Decimal) -> str:
        return e.put(
            (t, r, name),
            amount=amount,
            unit="MILLIONS",
            period=period,
            decimals=SHEET_DECIMALS,
            value_class="source",
            citations=e.cite(row.paths[name]),
        )

    ids = [
        e.text((t, r, "kind"), kind, "normalized"),
        e.text((t, r, "name"), row.name, "source", citations=e.cite(row.paths["name"])),
        _date_fact(e, row, record),
        e.text((t, r, "source"), record.source, "source", citations=e.cite(row.paths["source"])),
        e.text((t, r, "currency"), NOT_STATED_BY_USER, "normalized"),
        e.text((t, r, "ebitda_period"), NOT_STATED_BY_USER, "normalized"),
        money("ev", record.ev),
        money("ebitda", record.ebitda),
        _multiple_fact(e, row, admission, period),
        _flag_fact(e, row, admission, ev_set),
        e.text(
            (t, r, "result"),
            admission.reason,
            "normalized",
            formula=RESULT_FORMULA,
            derives=(f"{t}.{r}.figures_date", f"{t}.{r}.ev", f"{t}.{r}.ebitda"),
        ),
    ]
    return ids


def _name_facts(e: _EvEmitter, row: _EvRow, gap: str) -> list[str]:
    """A user_list name: its figures need the peer lookup, so every figure cell is a named gap."""
    t, r = "T1C.9", row.row_id
    ids = [
        e.text((t, r, "kind"), "Public comp", "normalized"),
        e.text((t, r, "name"), row.name, "source", citations=e.cite(row.paths["name"])),
    ]
    for name, _label in EV_COLUMNS[t][2:]:
        ref = (t, r, name)
        if name == "flag":
            ids.append(e.gap(ref, EXCLUDED_FROM_STATS, status="not_applicable"))
        elif name == "result":
            ids.append(e.text(ref, NO_FIGURES, "normalized", formula=RESULT_FORMULA))
        else:
            unit = {"ev": "MILLIONS", "ebitda": "MILLIONS", "multiple": MULTIPLE}.get(name)
            period = NO_DATE_PERIOD if unit else None
            ids.append(e.gap(ref, gap, unit=unit, period=period))
    return ids


def _emit_none_row(e: _EvEmitter, plan: _EvPlan) -> None:
    """No record at all: a named gap when the peer source should have supplied them (Design 8)."""
    valuation = plan.valuation
    gap = PUBLIC_GAPS.get(valuation.peer_source)
    status: EvStatus
    if gap is not None and valuation.basis in ("auto", "public_comps"):
        status, reason = "missing", gap
    else:
        status, reason = "not_applicable", NO_RECORDS
    ids = [e.gap(("T1C.9", "none", name), reason, status=status) for name, _ in EV_COLUMNS["T1C.9"]]
    e.line("T1C.9", "none", "No records", ids)


def _emit_records(e: _EvEmitter, plan: _EvPlan) -> None:
    rows = [(row, ev_set) for ev_set in plan.sets for row in ev_set.rows]
    if not rows:
        _emit_none_row(e, plan)
    gap = PUBLIC_GAPS.get(plan.valuation.peer_source, "")
    for row, ev_set in rows:
        if row.admission is None:
            ids = _name_facts(e, row, gap)
        else:
            ids = _figure_facts(e, row, ev_set, row.admission)
        e.line("T1C.9", row.row_id, row.name, ids)


def _stat_gap(e: _EvEmitter, ref: Ref, reason: str, unit: str, period: str) -> str:
    return e.gap(ref, reason, unit=unit, period=period)


def _emit_set(e: _EvEmitter, ev_set: _EvSet, as_of: date) -> None:
    t, r, stats = "T1C.10", ev_set.set_id, ev_set.stats
    period = f"Window {ev_set.start} to {as_of}"
    results = tuple(f"T1C.9.{x.row_id}.result" for x in ev_set.rows)
    admitted = ev_set.admitted()
    multiples = tuple(f"T1C.9.{x.row_id}.multiple" for x in admitted)
    cites = tuple(c for x in admitted for c in e.cite(x.paths["ev"], x.paths["ebitda"]))
    thin = _not_calculable(stats.n_admitted)

    def count(name: str, value: int, formula: str, derives: Sequence[str]) -> str:
        return e.put(
            (t, r, name),
            amount=Decimal(value),
            unit="records",
            period=period,
            value_class="calculated",
            formula=formula,
            derives=derives,
        )

    def multiple(name: str, value: Decimal | None, formula: str, missing: str) -> str:
        ref = (t, r, name)
        if value is None:
            return _stat_gap(e, ref, missing, MULTIPLE, period)
        return e.put(
            ref,
            amount=value,
            unit=MULTIPLE,
            period=period,
            decimals=2,
            value_class="calculated",
            formula=formula,
            derives=multiples,
            citations=cites,
        )

    none_admitted = "Not calculable: no admitted records"

    def outliers() -> str:
        if stats.outliers is None:
            return _stat_gap(e, (t, r, "outliers"), thin, "records", period)
        return count(
            "outliers",
            stats.outliers,
            "count of admitted records whose absolute deviation from the median is above one half",
            tuple(f"T1C.9.{x.row_id}.flag" for x in admitted),
        )

    ids = [
        count("n_total", stats.n_total, "count of records in the set", results),
        count(
            "n_admitted",
            stats.n_admitted,
            "count of records admitted (EV and EBITDA above zero, dated within the window)",
            results,
        ),
        multiple(
            "min", stats.minimum, "smallest multiple among the admitted records", none_admitted
        ),
        multiple(
            "median",
            stats.median,
            "median of the admitted records' multiples; even count: (a + b) / 2; "
            "fewer than 3 admitted: not calculated",
            thin,
        ),
        multiple(
            "max", stats.maximum, "largest multiple among the admitted records", none_admitted
        ),
        outliers(),
    ]
    e.line(t, r, ev_set.label, ids)


def _issuer_multiple(plan: _EvPlan) -> Decimal | None:
    """The issuer's own EV / CP-1 EBITDA, exact, when the selection computed it."""
    market, amount = plan.valuation.issuer_market, plan.ebitda_amount
    if plan.selection.multiple is None or amount is None:
        return None
    ev = (
        Decimal(market.ev_m)
        if market.ev_m
        else CTX.add(Decimal(market.market_cap_m), Decimal(market.net_debt_m))
    )
    return CTX.divide(ev, amount)


def _basis_paths(valuation: Valuation) -> tuple[JsonPath, ...]:
    """The context values the issuer or user multiple stands on."""
    if valuation.basis == "issuer_trading":
        market = ("valuation", "issuer_market")
        if valuation.issuer_market.ev_m:
            return ((*market, "ev_m"),)
        return ((*market, "market_cap_m"), (*market, "net_debt_m"))
    if valuation.basis == "user_multiple":
        return (
            ("valuation", "user_multiple", "value"),
            ("valuation", "user_multiple", "rationale"),
        )
    return ()


def _emit_single(
    e: _EvEmitter,
    row_id: str,
    label: str,
    period: str,
    value: Decimal | None,
    formula: str,
    value_class: Literal["source", "calculated"],
    cites: tuple[Citation, ...],
) -> None:
    """issuer_trading and user_multiple: one value, so min, median and max are that value."""
    t = "T1C.10"

    def count(name: str, amount: int, text: str) -> str:
        return e.put(
            (t, row_id, name),
            amount=Decimal(amount),
            unit="records",
            period=period,
            value_class="calculated",
            formula=text,
        )

    def cell(name: str) -> str:
        ref = (t, row_id, name)
        if value is None:
            return _stat_gap(e, ref, "Not calculable: no multiple", MULTIPLE, period)
        return e.put(
            ref,
            amount=value,
            unit=MULTIPLE,
            period=period,
            decimals=2,
            value_class=value_class,
            formula=formula + SINGLE_VALUE,
            citations=cites,
        )

    ids = [
        count("n_total", 1, "count of records in the set"),
        count("n_admitted", 0 if value is None else 1, "count of records with a multiple"),
        cell("min"),
        cell("median"),
        cell("max"),
        e.gap(
            (t, row_id, "outliers"),
            "Not meaningful: a single value has no outlier test",
            status="not_applicable",
            unit="records",
            period=period,
        ),
    ]
    e.line(t, row_id, label, ids)


def _emit_stats(e: _EvEmitter, plan: _EvPlan) -> None:
    valuation = plan.valuation
    if valuation.basis in ("auto", "public_comps", "blend") or plan.public.stats.n_total:
        _emit_set(e, plan.public, plan.as_of)
    if valuation.basis in ("precedents", "blend") or plan.precedents.stats.n_total:
        _emit_set(e, plan.precedents, plan.as_of)
    if valuation.basis == "issuer_trading":
        multiple, paths = _issuer_multiple(plan), _basis_paths(valuation)
        _emit_single(
            e,
            "issuer_trading",
            "Issuer trading",
            f"As of {valuation.issuer_market.as_of}",
            multiple,
            "issuer enterprise value / CP-1 LTM adjusted EBITDA",
            "calculated",
            e.cite(*paths) if multiple is not None else (),
        )
    if valuation.basis == "user_multiple":
        value = plan.selection.multiple
        _emit_single(
            e,
            "user_multiple",
            "User multiple",
            NOT_STATED_BY_USER,
            value,
            "user-supplied multiple",
            "source",
            e.cite(*_basis_paths(valuation)[:1]) if value is not None else (),
        )


def _selected_cites(e: _EvEmitter, plan: _EvPlan) -> tuple[Citation, ...]:
    """The lines the selected multiple stands on: each set's admitted records, then the
    issuer's or the user's own values."""
    chosen = {
        "public_comps": (plan.public,),
        "precedents": (plan.precedents,),
        "blend": (plan.public, plan.precedents),
    }.get(plan.selection.selected_basis or "", ())
    found = [
        c for s in chosen for r in s.admitted() for c in e.cite(r.paths["ev"], r.paths["ebitda"])
    ]
    return (*found, *e.cite(*_basis_paths(plan.valuation)))


def _selected_multiple(e: _EvEmitter, plan: _EvPlan) -> str:
    sel, ref = plan.selection, (SELECTION_TABLE, "selection", "selected_multiple")
    period = f"EBITDA basis: {sel.ebitda_basis}"
    if sel.multiple is None:
        return e.gap(ref, sel.reason, unit=MULTIPLE, period=period)
    basis = sel.selected_basis or ""
    medians = tuple(
        f"T1C.10.{s}.median"
        for s in ("public_comps", "precedents")
        if basis == s or basis == "blend"
    )
    return e.put(
        ref,
        amount=sel.multiple,
        unit=MULTIPLE,
        period=period,
        decimals=2,
        value_class="source" if basis == "user_multiple" else "calculated",
        formula=SELECTED_FORMULAS[basis],
        derives=medians,
        citations=_selected_cites(e, plan),
    )


def _implied_gap(plan: _EvPlan) -> str:
    sel = plan.selection
    if sel.multiple is None:
        return "Not calculable: no selected multiple"
    if sel.ebitda_basis == "NTM":
        return f"Not calculable: {_vbasis().NTM_NOT_APPLIED}"
    return f"Not calculable: {_vbasis().EBITDA_GAP}"


def _emit_ebitda_facts(e: _EvEmitter, plan: _EvPlan) -> tuple[str, str]:
    """(issuer_ebitda, implied_ev): CP-1's LTM adjusted EBITDA and the selected multiple on it."""
    sel, cp1 = plan.selection, plan.ebitda
    t, r, period = SELECTION_TABLE, "selection", cp1.period
    ebitda_ref, implied_ref = (t, r, "issuer_ebitda"), (t, r, "implied_ev")
    if plan.ebitda_amount is None:
        gap = _vbasis().EBITDA_GAP
        ebitda_id = e.gap(ebitda_ref, gap, unit="MILLIONS", period=period)
    else:
        ebitda_id = e.put(
            ebitda_ref,
            amount=plan.ebitda_amount,
            unit="MILLIONS",
            period=period,
            decimals=SHEET_DECIMALS,
            currency=cp1.currency,
            value_class="calculated",
            formula=ISSUER_EBITDA_FORMULA,
            derives=(CP1_REF,),
        )
    if sel.implied_ev is None:
        return ebitda_id, e.gap(implied_ref, _implied_gap(plan), unit="MILLIONS", period=period)
    implied_id = e.put(
        implied_ref,
        amount=sel.implied_ev,
        unit="MILLIONS",
        period=period,
        decimals=SHEET_DECIMALS,
        currency=cp1.currency,
        value_class="calculated",
        formula="selected multiple x CP-1 LTM adjusted EBITDA",
        derives=(f"{t}.{r}.selected_multiple", ebitda_id),
    )
    return ebitda_id, implied_id


def _ebitda_basis_fact(e: _EvEmitter, plan: _EvPlan) -> str:
    """The EBITDA basis the multiple is on: the user's own label (cited) for the issuer's trading
    multiple and the user's multiple, else the text that none is stated."""
    sel, valuation = plan.selection, plan.valuation
    ref = (SELECTION_TABLE, "selection", "ebitda_basis")
    if valuation.basis == "issuer_trading" and sel.ebitda_basis in ("LTM", "NTM"):
        return e.text(
            ref,
            sel.ebitda_basis,
            "source",
            citations=e.cite(("valuation", "issuer_market", "ebitda_basis")),
        )
    if valuation.basis == "user_multiple" and sel.ebitda_basis in ("LTM", "NTM"):
        return e.text(
            ref,
            sel.ebitda_basis,
            "source",
            citations=e.cite(("valuation", "user_multiple", "basis")),
        )
    return e.text(ref, sel.ebitda_basis, "normalized")


def _emit_selection(e: _EvEmitter, plan: _EvPlan) -> None:
    sel, t, r = plan.selection, SELECTION_TABLE, "selection"
    ids = [
        e.text(
            (t, r, "requested_basis"),
            sel.requested,
            "source",
            citations=e.cite(("valuation", "basis")),
        )
    ]
    if sel.selected_basis is not None:
        ids.append(e.text((t, r, "selected_basis"), sel.selected_basis, "normalized"))
    else:
        ids.append(e.gap((t, r, "selected_basis"), sel.reason))
    ids.append(e.text((t, r, "reason"), sel.reason, "normalized"))
    ids.append(_ebitda_basis_fact(e, plan))
    ids.append(_selected_multiple(e, plan))
    ids += _emit_ebitda_facts(e, plan)
    e.line(t, r, "Selection", ids)


@dataclass(frozen=True)
class _EvComposed:
    facts: tuple[PeerFact, ...]
    tables: tuple[PeerTable, ...]
    limitations: tuple[str, ...]


def _ev_limitations(plan: _EvPlan, basis: PeriodBasis) -> tuple[str, ...]:
    """The limitations of the context's valuation, in the oracle's order."""
    valuation, sel = plan.valuation, plan.selection
    lines: list[str] = []
    if any(row.record is not None for s in plan.sets for row in s.rows):
        lines += [USER_FIGURES_LINE, currency_period_line(basis)]
    if any(MIN_INCLUDED_PEERS <= s.stats.n_admitted < THIN_UNIVERSE for s in plan.sets):
        lines.append(THIN_LINE)
    market, user = valuation.issuer_market, valuation.user_multiple
    if valuation.basis == "issuer_trading":
        lines.append(
            f"The issuer's trading figures are the user's own entries (source: {market.source}, "
            f"dated {market.as_of}); CP-1C does not verify them against a market source."
        )
    if valuation.basis == "user_multiple":
        lines.append(
            f"The selected multiple is user-supplied ({user.basis} basis; rationale: "
            f"{user.rationale}); CP-1C does not verify it."
        )
    if sel.multiple is None:
        lines.append(f"Valuation basis not selected: {sel.reason}.")
    return tuple(lines)


def _ev_compose(inputs: PeerBenchmarkInputs) -> _EvComposed | None:
    """T1C.9-T1C.11, their facts and limitations; None when the pack has no context or the
    context has no valuation to show (the eight tables are then the whole head)."""
    if inputs.context is None or not shows_valuation(inputs.context.valuation):
        return None
    if inputs.context_source is None:
        raise ValueError("The EV/EBITDA tables cite the context source, which is not supplied")
    plan = _ev_plan(inputs)
    e = _EvEmitter(context_cites(inputs.context_source))
    _emit_records(e, plan)
    _emit_stats(e, plan)
    _emit_selection(e, plan)
    tables = tuple(PeerTable(t, title, tuple(e.rows[t])) for t, title in EV_TABLES.items())
    return _EvComposed(tuple(e.items), tables, _ev_limitations(plan, inputs.basis))


def _compose(inputs: PeerBenchmarkInputs, sheet: PeerSheet | None) -> _Composed:
    """Facts, tables and limitations; needs one assessment per sheet peer."""
    cp1 = _cp1_facts(inputs)
    by_label = {a.peer: a for a in inputs.submission.assessments}
    rows = sheet.peers if sheet is not None else ()
    peers = tuple(_Peer(f"p{n:02d}", row, by_label[row.label]) for n, row in enumerate(rows, 1))
    present = sheet is not None
    c = _Composer(sheet, _absence(inputs.sources), inputs.basis)
    _universe(c, peers, present)
    _source_figures(c, sheet, peers)
    values = _normalised(c, cp1, inputs.issuer_name, peers, present)
    stats = _statistics(c, peers, values, present)
    _outliers(c, inputs.issuer_name, peers, values, stats, present)
    _tie_out(c, sheet, cp1)
    _gaps(c, inputs.submission.gaps)
    tables = tuple(PeerTable(t, title, tuple(c.rows[t])) for t, title in TABLES.items())
    ev = _ev_compose(inputs)  # Phase 7: T1C.9-T1C.11 after the eight, only over a context
    limitations = _limitations(present, c.absent, cp1, peers, stats, inputs.submission.gaps)
    if ev:  # Phase 7: the context's lines follow the frozen list, none repeated
        limitations += tuple(line for line in ev.limitations if line not in limitations)
    facts = _with_lineage(c.items) + (ev.facts if ev else ())
    return _Composed(facts, tables + (ev.tables if ev else ()), limitations, peers, stats, c.absent)


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
        elif (
            stat is not None and stat.median is not None and status[f"T1C.3.issuer.{k}"] != "known"
        ):
            text += (  # round 6 B1, ahead of C2 in the 1C1 order
                " The outlier test does not apply to the issuer on this metric because its CP-1 "
                "value is not available."
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
            clipped(("Assessment given without a peer source in the pack: ", a.peer))
            for a in submission.assessments
        ]
    labels = [row.label for row in sheet.peers]
    unknown = [a.peer for a in submission.assessments if a.peer not in labels]
    counts = Counter(a.peer for a in submission.assessments)
    issues = [clipped(("Unknown peer: ", peer)) for peer in dict.fromkeys(unknown)]
    issues += [
        clipped(("Assess each sheet peer exactly once: ", label))
        for label in labels
        if counts[label] != 1
    ]
    return issues


def _content_issues(submission: PeerBenchmarkSubmission, sheet: PeerSheet | None) -> list[str]:
    issues: list[str] = []
    if sheet is not None and submission.overall.confidence == "High":
        issues.append("Confidence cannot be High: the peer figures are desk-supplied and unaudited")
    for a in submission.assessments:
        if not a.evidence:
            issues.append(clipped(("Evidence required for a comparability assessment: ", a.peer)))
        if a.comparability == "Partly comparable" and is_blank(a.limitation or ""):
            issues.append(clipped(("Limitation required for Partly comparable: ", a.peer)))
    return issues


def _citation_issues(submission: PeerBenchmarkSubmission, sources: Sequence[Source]) -> list[str]:
    """Every citation in payload order. A quote that `is_blank` gets `<path>: empty text` and
    never reaches the page-occurrence check (round 13 addendum 3); any other quote must occur
    under its located page (`readiness.citation_issues`; Source quotes: CP-1C reads no figure
    from a quote)."""
    cited = [
        (f"assessments[{i}].evidence[{j}]", citation)
        for i, a in enumerate(submission.assessments)
        for j, citation in enumerate(a.evidence)
    ]
    cited += [(f"overall.evidence[{j}]", c) for j, c in enumerate(submission.overall.evidence)]
    found: list[str] = []
    for path, citation in cited:
        if is_blank(citation.quote):
            found.append(f"{path}.quote: empty text")
        else:
            found += citation_issues((citation,), tuple(sources))
    return found


def _bounded(found: Iterable[str]) -> tuple[str, ...]:
    """At most `MAX_ISSUES` lines of at most `MAX_ISSUE_CHARS`, the last counting the rest
    (`execution.listed_issues`, protocol section 6)."""
    return listed_issues(found, lambda line: (line,), lambda n: f"{n} further issues not listed")


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
    are no facts to bind them to, and the set issues already refuse the payload). A line that
    quotes the payload is cut by `clipped` before it is built whole, and the list is bounded
    (`_bounded`), so the issue text cannot outgrow the payload (protocol section 6)."""
    submission = inputs.submission
    try:
        sheet = parse_peer_source(
            _peer_source(inputs.sources),
            issuer_name=inputs.issuer_name,
            currency=inputs.basis.currency,
        )
    except PeerTableError as error:
        return (str(error),)
    set_issues = _assessment_set_issues(submission, sheet)
    issues = [*set_issues, *_content_issues(submission, sheet)]
    issues += _citation_issues(submission, inputs.sources)
    for path, text in _prohibited_fields(submission):
        if is_blank(text):  # round 11, round 12 B10: blank text is refused (no CP-1C frame)
            issues.append(f"{path}: empty text")
        issues += prohibited_issues(path, text, kinds=PROHIBITED_KINDS)
    if not set_issues:
        bound = prose.bind(item.fact for item in _compose(inputs, sheet).facts)
        names = (inputs.issuer_name,)
        for text in _prose_texts(submission):
            # a prose line can quote a payload word whole (`Bare figure: <token>`)
            issues += [clipped((line,)) for line in prose.issues(text, bound, names=names)]
    return _bounded(dict.fromkeys(issues))


def compute(inputs: PeerBenchmarkInputs) -> PeerBenchmarkResult:
    """The module's facts, tables, claims and own limitations; ValueError on any issue."""
    if issues := calculation_issues(inputs):
        raise ValueError("; ".join(issues))
    sheet = parse_peer_source(
        _peer_source(inputs.sources),
        issuer_name=inputs.issuer_name,
        currency=inputs.basis.currency,
    )
    composed = _compose(inputs, sheet)
    claims = _claims(composed, inputs.submission)
    return PeerBenchmarkResult(composed.facts, composed.tables, claims, composed.limitations)


# =============================================================================================
# Stage 2: the connection (docs/CP1C-OWNER-LEASE.md Public API; docs/G1X-OWNER-CORE-PROTOCOL.md).
# Everything above is the pure Stage 1 calculation; what follows binds it to the store.
# =============================================================================================

STEP_ID = "peer_benchmark"
STEP_IDS = (STEP_ID,)
QUALIFICATION = Qualification(implementation="implemented")
SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: PeerBenchmarkSubmission}
# The fixed H1 mapping (`host._OWNER_SCOPES[("CP-1C", "peer_benchmark")]`, lease :33): identity,
# financial, peers when the pack holds it, then every held research item (`ev-*`, O7c C1,
# O7-R47); a held source stays in scope in pack order.
SCOPE = frozenset({"identity", "financial", PEERS_SOURCE_ID})


def in_scope(source_id: str) -> bool:
    """The O7c scope predicate (`host._OWNER_SCOPES` row): the named `SCOPE` sources and every
    supplied research item (`ev-*`), which CP-1C may cite by `line:N` like a peers page."""
    return source_id in SCOPE or source_id.startswith(RESERVED_PREFIX)


CP0, CP1 = "CP-0", "CP-1"
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
# Rulings stage 2 round 5 item 9: the admitted shape issue of text `json_object` refuses.
BAD_PAYLOAD = "(root): not a JSON object within the payload bounds"
# manifest.json `cp1_fact_selection_rule`: the table of the four T4.10 facts; the column and the
# period are the run basis's `ltm_column` and `ltm_period`.
_CP1_TABLE = "T4.10"
_SETTLED: Mapping[str, InputStatus] = {
    "accepted": "accepted",
    "restricted": "restricted",
    "blocked": "blocked",
}


@dataclass(frozen=True)
class Upstream:
    """What one CP-1C attempt binds, read once from the journal (`cp1c_upstream`).

    `bound` is the attempt's input set; `current` is `execution.current_inputs` now, or its
    refusal text; `cp0` and `cp1` are the bound required heads; `inherited` is what settlement
    will carry from them (`execution.inherited_limitations`)."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp0: Module
    cp1: Module
    inherited: tuple[str, ...] = ()

    def status(self, module_id: str) -> InputStatus | None:
        return next((item.status for item in self.bound if item.input_id == module_id), None)


def _bound_module(store: Execution, attempt: Attempt, module_id: str) -> Module:
    item = next((i for i in attempt.inputs if i.input_id == module_id), None)
    if item is None:
        raise ValueError(f"The CP-1C attempt binds no {module_id} input")
    module = store.result(item.sha256)
    if module.module_id != module_id:
        raise ValueError(f"The CP-1C attempt's {module_id} input is a {module.module_id} module")
    return module


def cp1c_upstream(store: Execution, attempt: Attempt) -> Upstream:
    """The bound CP-0 and CP-1 heads of `attempt`, the current input set and the inherited
    limitations. A refusal of `current_inputs` (an upstream gone stale or blocked, or CP-0 no
    longer authorizing CP-1C) is kept as text: the validator reports it as a staleness issue.
    A required input that is absent, or whose blob is another module's, raises (store
    integrity; `begin` binds both)."""
    snapshot = store.read()
    current: tuple[Input, ...] | str
    try:
        current = current_inputs(snapshot, MODULE_ID)
    except ValueError as error:  # NotAuthorized included: reported, never passed as current
        current = str(error)
    return Upstream(
        bound=attempt.inputs,
        current=current,
        cp0=_bound_module(store, attempt, CP0),
        cp1=_bound_module(store, attempt, CP1),
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


def _cp1_metrics(cp1: Module, basis: PeriodBasis) -> dict[str, Fact]:
    """The four T4.10 facts of the basis's LTM column by metric key (manifest
    `cp1_fact_selection_rule`): exactly one match each, zero or several raise."""
    picked: dict[str, Fact] = {}
    for metric in METRICS:
        label = f"{basis.ltm_column} · {metric.key}"
        hits = [
            f
            for f in cp1.facts
            if f.table_id == _CP1_TABLE and f.period == basis.ltm_period and f.label == label
        ]
        if len(hits) != 1:
            raise ValueError(
                f"CP-1 {_CP1_TABLE} {metric.key}: {len(hits)} facts, expected exactly one"
            )
        picked[metric.key] = hits[0]
    return picked


def _inputs(
    pack: PreparedPack, submission: PeerBenchmarkSubmission, upstream: Upstream
) -> PeerBenchmarkInputs:
    """The one store adapter: the run's issuer name, the pack sources in the fixed H1 scope, the
    four selected CP-1 facts and the submission, as the Stage 1 input object. Used by `submit`
    (through the validator), `probe` and `view`. The run's basis is `run_basis` (P8-R3). Raises
    ValueError when the CP-1 head does not hold exactly one fact per metric, ContextRefused when
    the pack's context is refused and PeriodRefused when its period or currency is."""
    basis = run_basis(context_facts(pack), upstream.cp1.facts)
    base = PeerBenchmarkInputs(
        issuer_name=pack.run.issuer_name,
        sources=tuple(s for s in pack.sources if in_scope(s.source_id)),
        cp1_metrics=_cp1_metrics(upstream.cp1, basis),
        submission=submission,
        basis=basis,
    )
    return _with_context(base, pack, upstream.cp1.facts)


def _citable_context_source(pack: PreparedPack) -> Source:
    """The pack's context source; ContextRefused when it cannot be cited by line."""
    source = next(s for s in pack.sources if s.source_id == "context")
    try:
        context_cites(source)
    except ValueError as error:
        raise ContextRefused([f"sources.context: {error}"]) from error
    return source


def _with_context(
    inputs: PeerBenchmarkInputs, pack: PreparedPack, cp1_facts: Iterable[Fact]
) -> PeerBenchmarkInputs:
    """`inputs` with the pack's context, its source and CP-1's LTM adjusted EBITDA, selected as
    CP-4C selects it, when the context has a valuation to show. A pack without a context source
    is returned unchanged. ContextRefused when the context is refused or cannot be cited by line;
    ValueError when CP-1 does not hold exactly one EBITDA fact."""
    context = context_facts(pack)
    if context is None or not shows_valuation(context.valuation):
        return replace(inputs, context=context)
    source = _citable_context_source(pack)
    ebitda = select_cp1(cp1_facts, inputs.basis)["ebitda"]
    return replace(inputs, context=context, context_source=source, cp1_ebitda=ebitda)


def _basis_issue(error: ContextRefused | PeriodRefused) -> str:
    """The one issue line a refused context, period or currency becomes."""
    prefix = "Context refused: " if isinstance(error, ContextRefused) else "Period basis: "
    return clipped((prefix, str(error)))


def _stale_issues(upstream: Upstream) -> list[str]:
    if isinstance(upstream.current, str):
        return [clipped(("Stale inputs: ", upstream.current))]
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
    bound = {item.input_id: item for item in upstream.bound}
    found = [
        f"Upstream {module_id}: the supplied module is not the bound input"
        for module_id, module in ((CP0, upstream.cp0), (CP1, upstream.cp1))
        if (item := bound.get(module_id)) is None
        or module.module_id != module_id
        or module.content_hash() != item.sha256
    ]
    found += [
        f"Required upstream {item.input_id} is blocked"
        for item in upstream.bound
        if item.input_id in (CP0, CP1) and item.status == "blocked"
    ]
    return found


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def _model_text_issues(submission: PeerBenchmarkSubmission) -> list[str]:
    """Rulings stage 2 round 3 item 2: each rationale becomes `Claim.text`, so it is checked here
    with that type (`RunText`), and no composition can raise after the binding write. Lines are
    `<path>: <msg>` without the input value."""
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
                clipped((path, ": ", e["msg"]))
                for e in error.errors(include_input=False, include_url=False, include_context=False)
            ]
    return found


class PeerBenchmarkReport(Contract):
    """The composed CP-1C output retained as the step output: the module's tables, facts, claims
    and own limitations, bound to the pack and the retained submission."""

    schema_version: Literal["peer-benchmark/1"] = "peer-benchmark/1"
    run: PackRun
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[Text, ...]


# Each table's columns are fixed by the composer's own field lists (T1C.7 has no row without a
# gap), so a table's header never depends on which row comes first.
_COLUMNS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "T1C.1": UNIVERSE_FIELDS,
    "T1C.2": OPERANDS,
    "T1C.3": tuple((m.key, m.label) for m in METRICS),
    "T1C.4": (("direction", "Direction"), *((n, STAT_LABELS[n]) for n in STAT_FIELDS[1:])),
    "T1C.5": tuple(
        pair
        for m in METRICS
        for pair in zip((f"{m.key}_deviation", f"{m.key}_flag"), _flag_labels(m), strict=True)
    ),
    "T1C.6": (
        ("sheet", "Issuer line on the peer source"),
        ("cp1", "CP-1"),
        ("difference", "Difference"),
        ("result", "Result"),
    ),
    "T1C.7": (("id", "Gap id"), *GAP_FIELDS),
    TOTALS: TOTAL_FIELDS,
}
_ROW_HEADERS: Mapping[str, str] = {
    "T1C.1": "Peer",
    "T1C.2": "Entity",
    "T1C.3": "Entity",
    "T1C.4": "Metric",
    "T1C.5": "Entity",
    "T1C.6": "Metric",
    "T1C.7": "Gap",
    TOTALS: "Universe",
}


def _columns(table_id: str) -> tuple[tuple[str, str], ...]:
    """A table's columns: the eight tables' own, or T1C.9-T1C.11's when the head holds them."""
    return EV_COLUMNS[table_id] if table_id in EV_COLUMNS else _COLUMNS[table_id]


def _report(
    pack: PreparedPack, submission: PeerBenchmarkSubmission, result: PeerBenchmarkResult
) -> PeerBenchmarkReport:
    return PeerBenchmarkReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=tuple(
            ReportTable(
                table_id=table.table_id,
                title=table.title,
                columns=tuple(
                    TableColumn(field=f, label=label) for f, label in _columns(table.table_id)
                ),
                rows=table.rows,
                row_header=EV_ROW_HEADERS.get(table.table_id) or _ROW_HEADERS[table.table_id],
            )
            for table in result.tables
        ),
        facts=tuple(item.fact for item in result.facts),
        claims=result.claims,
        limitations=result.limitations,
    )


def _checked(
    pack: PreparedPack, submission: PeerBenchmarkSubmission, upstream: Upstream
) -> tuple[tuple[str, ...], PeerBenchmarkReport | None]:
    """(issues, None) for a refused submission, else ((), the composed report). Every check runs
    before any product record is built from model text: the bound inputs (returned alone), the
    CP-1 selection and the Stage 1 rules on it, the Stage 1 content rules, then the run-text type
    of each rationale. A record the product refuses (`ValidationError`, for example a sheet row
    whose label is empty) is reported as issue lines, never raised."""
    found = [*_provenance_issues(upstream), *_stale_issues(upstream)]
    if found:
        return _bounded(found), None
    try:
        inputs = _inputs(pack, submission, upstream)
        _cp1_facts(inputs)  # the Stage 1 rules on the selected facts (unit, amount, period)
    except (ContextRefused, PeriodRefused) as error:  # a named issue, never "none" (P8-R5)
        return (_basis_issue(error),), None
    except ValueError as error:
        return (clipped(("CP-1 facts unavailable: ", str(error))),), None
    issues = calculation_issues(inputs)
    if issues:
        return issues, None
    texts = _model_text_issues(submission)
    if texts:
        return _bounded(texts), None
    try:
        return (), _report(pack, submission, compute(inputs))
    except ValidationError as error:
        return _bounded(
            clipped((".".join(map(str, e["loc"])) or "(root)", ": ", e["msg"]))
            for e in error.errors(include_input=False, include_url=False, include_context=False)
        ), None


def validate_peer_benchmark(
    *, pack: PreparedPack, submission: PeerBenchmarkSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Every issue of one submission: the bound-input checks, the CP-1 selection, the Stage 1
    content rules, the run-text type of each rationale and the product's own record checks.
    Bounded to `MAX_ISSUES` lines of at most `MAX_ISSUE_CHARS`."""
    return _checked(pack, submission, upstream)[0]


def peer_benchmark(
    *, pack: PreparedPack, submission: PeerBenchmarkSubmission, upstream: Upstream
) -> PeerBenchmarkReport:
    """The composed CP-1C report of a valid submission; raises ValueError on any issue."""
    issues, report = _checked(pack, submission, upstream)
    if issues or report is None:
        raise ValueError("; ".join(issues))
    return report


def cp1c_module(report: PeerBenchmarkReport, *, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-1C candidate: the report bound to `inputs` plus the one `*-submission` input (the
    owner-only settled tail, protocol section 2 `SCHEMAS`)."""
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


# --- the exact `read_inputs` view (lease Tool use, D2) ----------------------------------------

_RULES_VIEW = {
    "inclusion": "Comparable and Partly comparable peers are included; a Not comparable peer is "
    "shown but kept out of every statistic",
    "position": "1 + the number of entities strictly better than the issuer among the included "
    "peers with a value and the issuer; ties share a position",
}


def _view_row(row_id: str, row: PeerRow) -> dict[str, object]:
    """One sheet row as the table rule reads it; each amount spelled as its T1C.2 cell (one
    decimal place) or `Not stated`. The basis cells, not the page:2 line."""
    return {
        "row": row_id,
        "label": row.label,
        "period_end": row.period_end,
        "amounts": {
            key: NOT_STATED
            if value is None
            else format_value(value, "amount", "known", decimals=SHEET_DECIMALS)
            for key, value in row.amounts.items()
        },
        "basis": None
        if row.basis is None
        else {
            "reporting_basis": row.basis.basis,
            "segments": row.basis.segments,
            "fiscal_year_end": row.basis.fiscal_year_end,
        },
    }


def _view_default(upstream: Upstream) -> tuple[PeriodBasis | None, dict[str, Fact]]:
    """What `DEFAULT_BASIS` selects for a refused context (P8T4-R2, as cp2d): nothing when the
    CP-1 head holds no such column."""
    try:
        return DEFAULT_BASIS, _cp1_metrics(upstream.cp1, DEFAULT_BASIS)
    except ValueError:
        return None, {}


def _view_context_use(
    pack: PreparedPack, upstream: Upstream, basis: PeriodBasis, facts: Mapping[str, Fact]
) -> None:
    """The checks the validator makes of the selection after `_cp1_metrics`: a context with a
    valuation is citable by line and CP-1 holds one EBITDA fact in the column (`_with_context`),
    then the four facts meet the Stage 1 rules (`_cp1_facts`)."""
    context = context_facts(pack)
    if context is not None and shows_valuation(context.valuation):
        _citable_context_source(pack)
        select_cp1(upstream.cp1.facts, basis)
    _cp1_cells(facts)


def _view_selection(
    pack: PreparedPack, upstream: Upstream
) -> tuple[PeriodBasis | None, dict[str, Fact], str | None]:
    """(basis, facts, issue) the view offers. A refusal the validator states becomes the same
    issue line and the view never raises (P8-R5, P8T2-R3). A refused context still offers what
    the default basis selects (P8T2-R1, P8T2-R2); a refused period, currency or CP-1 selection
    offers nothing."""
    try:
        basis = run_basis(context_facts(pack), upstream.cp1.facts)
        facts = _cp1_metrics(upstream.cp1, basis)
        _view_context_use(pack, upstream, basis, facts)
    except ContextRefused as error:
        return *_view_default(upstream), _basis_issue(error)
    except PeriodRefused as error:
        return None, {}, _basis_issue(error)
    except ValueError as error:  # the validator's `CP-1 facts unavailable` line
        return None, {}, clipped(("CP-1 facts unavailable: ", str(error)))
    return basis, facts, None


def _view_sheet(
    pack: PreparedPack, source: Source | None, basis: PeriodBasis | None
) -> PeerSheet | None:
    """The peer sheet the view reads under the basis's currency: none without a basis, and none
    when the table rule cannot read a ready peers source."""
    if basis is None:
        return None
    try:
        return parse_peer_source(source, issuer_name=pack.run.issuer_name, currency=basis.currency)
    except PeerTableError:
        return None


def _peers_view(source: Source | None, sheet: PeerSheet | None) -> dict[str, object]:
    present = source is not None and source.status == "ready"
    return {
        "state": "present" if present else "absent",
        "source_id": None if source is None else source.source_id,
        "pages": [] if source is None else [span.locator for span in source.spans],
        "rows": []
        if sheet is None
        else [_view_row(f"p{n:02d}", row) for n, row in enumerate(sheet.peers, 1)],
        "issuer_line": None if sheet is None else _view_row("issuer", sheet.issuer),
    }


def context_block(*, pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """The exact `read_inputs` view (lease key tree): the upstream statuses, the peer sheet's rows
    as the table rule reads them, the four CP-1 facts a `{ref|unit}` names through the module's
    copied cells, the policy rules and the limitations settlement will inherit. No quote,
    citation or record is in it. A ready peers source the table rule cannot read shows no rows
    (the validator refuses every payload over it with `Peer table not found`)."""
    source = _peer_source(pack.sources)
    basis, facts, issue = _view_selection(pack, upstream)
    sheet = _view_sheet(pack, source, basis)
    block: dict[str, object] = {
        "upstream": [
            {"module_id": item.input_id, "status": item.status}
            for item in upstream.bound
            if item.input_id.startswith("CP-")
        ],
        "peers": _peers_view(source, sheet),
        "cp1_facts": [
            {
                "ref": f"T1C.3.issuer.{m.key}",
                "label": m.label,
                "period": facts[m.key].period,
                "unit": m.token,
                "shown": shown(facts[m.key]),
                "value_class": facts[m.key].value_class,
            }
            for m in METRICS
            if m.key in facts
        ],
        "rules": {
            "minimum_included_peers": MIN_INCLUDED_PEERS,
            "outlier_fraction": str(OUTLIER_FRACTION),
            **_RULES_VIEW,
            "direction": {m.key: m.direction for m in METRICS},
        },
        "inherited_limitations": list(upstream.inherited),
    }
    return block if issue is None else {**block, "context_issue": issue}


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the one `read_inputs` view over the bound heads, as compact JSON."""
    block = context_block(pack=historical.pack(), upstream=cp1c_upstream(historical, attempt))
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


# --- the tool-use rule, the validator, submit and the verifier probe ---------------------------


def RULES(text: str, seen: Seen) -> tuple[str, ...]:
    """The tool-use evidence rule (protocol section 2): every cited page was returned by
    `read_pages` in the step. The schema holds no `ABSENCE_MARKERS` value (lease open question 13),
    so the cited-page rule is the only one. O7-R54 M-1: `research.steps.unread_issues` is
    `live.tools.unread_citation_issues` for `page:N` (same text, bounded and sorted) and also
    judges a cited `line:N` of an `ev-*` item, which CP-1C may cite since O7c C1."""
    return unread_issues(text, seen)


def _parsed(payload: str) -> tuple[PeerBenchmarkSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues. Model text is read only through `json_object`
    (protocol section 6): the schema validates the bounded document's exact re-serialisation,
    never the raw text, and text `json_object` refuses is `BAD_PAYLOAD`."""
    document = json_object(payload)
    if document is None:
        return None, (BAD_PAYLOAD,)
    try:
        return PeerBenchmarkSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, _bounded(shape_issues(error))


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands `Execution.submit_step` and the verifier replays: the
    attempt's last step is the one under validation."""
    submission, shape = _parsed(store.payload(attempt.steps[-1].payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    issues, report = _checked(pack, submission, cp1c_upstream(store, attempt))
    if issues or report is None:
        return StepValidation(issues=issues)
    return StepValidation(output=report.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    report = PeerBenchmarkReport.model_validate_json(output)
    return cp1c_module(report, inputs=attempt.inputs, attempt=attempt.number)


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
    """Journal the one `peer_benchmark` step (null resolution through `SCHEMAS`, the rule issues
    appended) and, when it is valid, settle CP-1C with the Python candidate. An invalid step
    finishes the attempt; the repair is a new attempt."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-1C has one step, {STEP_ID}")
    normal, resolved = normalise(PeerBenchmarkSubmission, payload)
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
            raise ValueError("Retained CP-1C output differs from trusted validation")
        candidate = _candidate(outcome.output or "", attempt)
        attempt = store.finish(
            ticket_id,
            candidate.model_dump_json(),
            lambda supplied: () if supplied == candidate else ("CP-1C candidate differs",),
            qualification=QUALIFICATION,
        )
    return Submitted(attempt, normal, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun the step validator and settlement over the settled snapshot (nothing is written);
    `WorkflowError("identity_mismatch")` unless the head rebuilds exactly."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


# --- the consumer reader (lease Public API and D3: OPEN, no consumer exists yet) ---------------

# expected.json `execution.consumption.consumer_facts`, per metric in METRICS order, then the
# universe count: what a consumer reads as facts (it may read the position, never re-rank).
READER_FACTS: tuple[str, ...] = (
    *(
        f"T1C.4.{m.key}.{name}"
        for m in METRICS
        for name in ("median", "difference", "position", "outlier_count")
    ),
    f"{TOTALS}.total.included",
)


@dataclass(frozen=True)
class Cp1cHead:
    """What a consumer reads from a settled CP-1C head: its status and hash, the pinned facts
    verbatim (`READER_FACTS`) and the settled own limitations (on a synthetic case these include
    the run-level synthetic line). A blocked head gives its status and hash only (rulings stage 2
    round 5 item 9 L2)."""

    status: InputStatus
    head_sha256: str
    facts: tuple[Fact, ...] = ()
    limitations: tuple[str, ...] = ()

    def fact(self, fact_id: str) -> Fact:
        found = next((f for f in self.facts if f.fact_id == fact_id), None)
        if found is None:
            raise ValueError(f"CP-1C: {fact_id} is not exposed by the reader")
        return found


def cp1c_reader(store: Execution, head: Head) -> Cp1cHead:
    """The consumer reader of a settled CP-1C head (lease Public API). No consumer core calls it
    yet, so no consumption is claimed (D3 open). A stale head, another module's head, or a head
    without a pinned fact raises."""
    if head.module_id != MODULE_ID:
        raise ValueError(f"CP-1C: not a CP-1C head: {head.module_id}")
    status = _SETTLED.get(head.status)
    if status is None:
        raise ValueError(f"CP-1C: the CP-1C head is {head.status}")
    if status == "blocked":
        return Cp1cHead(status=status, head_sha256=head.result_sha256)
    module = store.head_module(head)
    return Cp1cHead(
        status=status,
        head_sha256=head.result_sha256,
        facts=reader_facts(module),
        limitations=module.limitations,
    )


def reader_facts(module: Module) -> tuple[Fact, ...]:
    """The pinned facts of a settled CP-1C module, verbatim: `READER_FACTS`, then `EV_READER_FACTS`
    when the module holds T1C.11 (a frozen head has none). A missing fact raises."""
    facts = {f.fact_id: f for f in module.facts}
    wanted = READER_FACTS
    if any(table.table_id == SELECTION_TABLE for table in module.tables):
        wanted = (*READER_FACTS, *EV_READER_FACTS)
    missing = [fact_id for fact_id in wanted if fact_id not in facts]
    if missing:
        raise ValueError(f"CP-1C: the head has no fact {missing[0]}")
    return tuple(facts[fact_id] for fact_id in wanted)
