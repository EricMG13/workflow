"""CP-3 relative value and security selection (task 8.3): one live step, `relative_value`.

Decision 0008 MC-1, as for CP-1A and CP-2: the model returns a `RelativeValueSubmission`,
judgments and verbatim quotes only. It judges which of the issuer's own instruments (the bound
CP-1 Debt Facility Register, T4.18) looks best compensated against CP-2's fundamental view, and
orders them. Python owns every figure, id, hash, status, limitation and all pricing arithmetic:
the model computes no spread, yield, price, rating or ranking number.

Evidence (coordinator rulings 1, 2 and 5): market evidence enters only as quoted spans of a pack
source the bound CP-0 head classes `third_party` (no new source kind, no ingest). Pack quotes
appear only in `market_evidence`; an instrument's or the preference's basis quotes one of those
rows. Every other basis is a CP-2 row id (`cp2_refs`, catalogue `<table_id>.<row_id>` over the
bound CP-2 head's T2.1, T2.7, T2.10, T2.11 and T2.12, built from its rows: cited, never
restated) or a `{ref|unit}` reference to a referencable fact of the bound CP-1 head.
`validate_relative_value` holds the submission, in Python only, to:

- facility, CP-2 row and figure existence (`prose.issues`: no bare figure, no chip);
- provenance and staleness against `execution.current_inputs`, as CP-2;
- the market-evidence rules: a quote binds to its span (`readiness.citation_issues`) of a
  `third_party` source; an `observed` row never quotes indicative talk; indicative talk is never
  worded as a market level; a market observation cites a market-evidence quote;
- the ordering: each instrument exactly once, nothing else;
- gap propagation (decision 0007, ruling 4): no observed or indicative evidence makes the
  preference Insufficient Information; a CP-2 that is not `accepted`, any blocked bound input
  (a blocked optional CP-1A or CP-4 included) or talk-only evidence caps its confidence below
  High; an optional upstream the run does not select is silent;
- the prohibited conclusions (ruling 3, `business_context.prohibited_issues` with the CP-3
  kinds): no buy, sell or other action phrase, no final recommendation, no recovery conclusion
  and no external peer ranking; an intra-issuer ordering is CP-3's own output.

`relative_value` then composes, in Python, minimal tables under r14 CP-3 ids (`methods/cp3.md`
records the decision 0005 adaptation: the r14 SKILL.md and its columns are not in the
repository), the FP 01 `relative-value` table (`cp3.relative_value`), the CP-1 facts the text
references (verbatim, `cp1_references`), claims and own limitations. The status is the
journal's (`execution.settle`). `submit_cp3_step` settles CP-3 as `submit_cp2_step` does and
needs no registry entry.
"""

import dataclasses
import json
import re
from collections import Counter
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    ValidationError,
    model_serializer,
)

from deploy_vii import prose
from deploy_vii.business_context import (
    CP1_REFERENCES,
    LABEL,
    NONE_STATED,
    Cell,
    Confidence,
    Gap,
    Quote,
    Register,
    Severity,
    prohibited_issues,
    referencable,
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
    Run,
    Source,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.cp2_synthesis import REQUIRED_TABLES as CP2_REGISTERS
from deploy_vii.cp2_synthesis import CatalogueRow, cp1a_catalogue
from deploy_vii.execution import (
    Attempt,
    Execution,
    Qualification,
    StepValidation,
    current_inputs,
    inherited_limitations,
    text_sha256,
)
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import citation_issues, shape_issues
from deploy_vii.report_view import figure_unit

MODULE_ID = "CP-3"
STEP_ID = "relative_value"
CP3_STEPS = (STEP_ID,)
SCHEMA_VERSION = "relative-value/1"
PROMOTED = Qualification(implementation="implemented")
CP0 = "CP-0"
CP1 = "CP-1"
CP2 = "CP-2"
REQUIRED = (CP0, CP1, CP2)
# Ruling 4: the optional upstreams CP-3 reads in M8 (statuses and limitations only); CP-3C,
# CP-3D, CP-4C and CP-2D are never read, whatever the run binds.
READ_OPTIONAL: Mapping[str, str] = {
    "CP-1A": "business and transaction context",
    "CP-4": "covenant and legal context",
}
NOT_IN_RUN = "not in this run"
FACILITY_TABLE = "T4.18"
# The T4.18 text cells the CONTEXT block shows per facility (labels, never figures).
TERMS = (
    "facility_name",
    "facility_type",
    "seniority",
    "secured_status",
    "currency",
    "maturity_date",
    "rate_type",
    "reference_rate",
)
THIRD_PARTY = "third_party"
NONE = "none"
# Ruling 3: action phrases, a final recommendation, a recovery conclusion and an external peer
# ranking stay prohibited; an ordering of the issuer's own instruments does not.
CP3_PROHIBITED_KINDS = ("peer ranking", "instrument action", "recovery conclusion")
# A text that cites indicative talk only may not word it as a market level: the verbs that
# assert where an instrument trades. Nouns ("market level") are not listed, so an honest
# negation ("talk, not a market level") passes (confidence review).
LEVEL_PHRASES = (
    "trades at",
    "traded at",
    "trading at",
    "quoted at",
    "is quoted",
    "are quoted",
    "priced at",
    "bid at",
    "offered at",
    "changed hands",
    "trading around",
    "trading near",
    "trades wide",
    "trades tight",
    "indicated at",
    "yields",
)
# Wording that marks a quote as indicative talk: an `observed` row never quotes it.
TALK_MARKERS = (
    "talk",
    "indicative",
    "guidance",
    "whisper",
    "initial price thoughts",
    "IPT",
    "IPTs",
    "proposed pricing",
    "expected pricing",
)


def _phrases(phrases: Sequence[str]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    return tuple(
        (p, re.compile(rf"(?<![A-Za-z]){re.escape(p)}(?![A-Za-z])", re.IGNORECASE)) for p in phrases
    )


_LEVELS = _phrases(LEVEL_PHRASES)
_TALK = _phrases(TALK_MARKERS)


def _found(patterns: Sequence[tuple[str, re.Pattern[str]]], text: str) -> list[str]:
    return [phrase for phrase, pattern in patterns if pattern.search(text)]


# --- the model-facing contract ---------------------------------------------------------------
# Plain `str` fields and `Literal` enums, as CP-2: the validator, not the sent schema, holds the
# references and the text.

MarketKind = Literal["observed", "indicative_talk", "none"]


class Basis(Contract):
    """A row's basis: CP-2 rows by id and market-evidence quotes (copied from `market_evidence`
    rows); its CP-1 basis is the figure references in its text."""

    cp2_refs: tuple[str, ...]
    quotes: tuple[Quote, ...]
    # Python's context market-evidence rows by id (`c01`, B6): a deliberate default, because every
    # submission made before the context file was read lacks it. An empty value is left out of the
    # dump, so a submission and a head without context evidence keep their content hash (N1).
    context_rows: tuple[str, ...] = ()

    @model_serializer(mode="wrap")
    def _omit_empty_context_rows(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if not self.context_rows:
            data.pop("context_rows", None)
        return data


class Instrument(Contract):
    facility_id: str
    fundamental_view: str
    market_observation: str  # run text, or "none"
    basis: Basis
    limitation: str | None


class MarketEvidence(Contract):
    source_id: str
    kind: MarketKind
    quote: Quote | None  # null exactly for a `none` row
    as_of: str
    limitation: str | None


class Preference(Contract):
    ordering: tuple[str, ...]  # facility ids, most preferred first
    rationale: str
    basis: Basis
    confidence: Confidence
    limitation: str | None


class Risk(Contract):
    risk: str
    mechanic: str
    implication: str
    severity: Severity
    cp2_refs: tuple[str, ...]


class RelativeValueSubmission(Contract):
    """What the model returns for `relative_value`; every field is required (no defaults)."""

    # `minItems: 1` in the sent schema only, as CP-2's `key_findings`; empty composes as a gap.
    instruments: tuple[Instrument, ...] = Field(json_schema_extra={"minItems": 1})
    market_evidence: tuple[MarketEvidence, ...]
    preference: Preference
    risks: tuple[Risk, ...]
    gaps: tuple[Gap, ...]


# --- the composed report ---------------------------------------------------------------------


class RelativeValueReport(Contract):
    schema_version: Literal["relative-value/1"] = "relative-value/1"
    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[Text, ...]


# --- the upstream heads a step binds ---------------------------------------------------------


@dataclass(frozen=True)
class Facility:
    """One facility of the bound CP-1 T4.18: its id, display name, text terms and the
    referencable figures of its rows."""

    facility_id: str
    name: str
    terms: tuple[tuple[str, str], ...]
    figures: tuple[Fact, ...]


def facilities(cp1: Module) -> dict[str, Facility]:
    """The facilities an instrument row may name: each known `facility_id` cell of T4.18, its
    rows (one per period) merged in fact order. A row without a known id is not a facility."""
    offered = {fact.fact_id for fact in referencable(cp1.facts)}
    rows: dict[str, list[Fact]] = {}
    for fact in cp1.facts:
        if fact.table_id == FACILITY_TABLE:
            rows.setdefault(fact.row_id, []).append(fact)
    found: dict[str, tuple[dict[str, str], list[Fact]]] = {}
    for cells in rows.values():
        by_field = {fact.field: fact for fact in cells}
        ident = by_field.get("facility_id")
        if ident is None or ident.status != "known" or not ident.text:
            continue
        terms, figures = found.setdefault(ident.text, ({}, []))
        for name in TERMS:
            cell = by_field.get(name)
            if cell is not None and cell.status == "known" and cell.text:
                terms.setdefault(name, cell.text)
        figures.extend(fact for fact in cells if fact.fact_id in offered)
    return {
        facility_id: Facility(
            facility_id=facility_id,
            name=terms.get("facility_name", facility_id),
            terms=tuple(terms.items()),
            figures=tuple(figures),
        )
        for facility_id, (terms, figures) in found.items()
    }


def cp2_catalogue(cp2: Module) -> dict[str, CatalogueRow]:
    """The CP-2 rows a `cp2_refs` id may name (ruling 2): `<table_id>.<row_id>` of every row of
    the bound head's T2.1, T2.7, T2.10, T2.11 and T2.12 that settles a cell, built from the
    head's rows by the CP-1A catalogue rule (`cp2_synthesis.cp1a_catalogue`). The Front Page
    copies (`cp2.*`), `cp1_references` and the explicit empty rows are not citable."""
    table_of = {f"{t.table_id}.{r.row_id}": t.table_id for t in cp2.tables for r in t.rows}
    return {ref: row for ref, row in cp1a_catalogue(cp2).items() if table_of[ref] in CP2_REGISTERS}


def third_party_sources(cp0: Module) -> frozenset[str]:
    """The pack sources the bound CP-0 head classes `third_party` (its T3 authority cells)."""
    return frozenset(
        fact.row_id
        for fact in cp0.facts
        if fact.table_id == "T3" and fact.field == "authority" and fact.text == THIRD_PARTY
    )


@dataclass(frozen=True)
class Upstream:
    """What one CP-3 attempt binds, read once from the journal (`cp3_upstream`).

    `bound` is the attempt's input set; `current` is `execution.current_inputs` now, or its
    refusal text; `cp0`, `cp1` and `cp2` are the bound required heads; `optional` holds the bound
    heads of `READ_OPTIONAL` (a blocked one is its limitations only); `inherited` is what
    settlement will carry from them (`execution.inherited_limitations`)."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp0: Module
    cp1: Module
    cp2: Module
    optional: Mapping[str, Module]
    inherited: tuple[str, ...]

    def status(self, module_id: str) -> str | None:
        return next((item.status for item in self.bound if item.input_id == module_id), None)

    @property
    def cp2_status(self) -> str | None:
        return self.status(CP2)

    @property
    def catalogue(self) -> dict[str, CatalogueRow]:
        return {} if self.cp2_status == "blocked" else cp2_catalogue(self.cp2)

    @property
    def facilities(self) -> dict[str, Facility]:
        return facilities(self.cp1)

    @property
    def market_sources(self) -> frozenset[str]:
        return third_party_sources(self.cp0)

    def optional_status(self, module_id: str) -> str:
        """A read optional upstream's bound status, or `NOT_IN_RUN`."""
        return self.status(module_id) or NOT_IN_RUN

    @property
    def caps(self) -> tuple[str, ...]:
        """Why the preference's confidence is below High whatever the evidence (decision 0007,
        ruling 4): a CP-2 that is not accepted and any blocked bound input. An optional upstream
        the run does not select is silent (fix round 1 ruling)."""
        reasons: list[str] = []
        if self.cp2_status != "accepted":
            reasons.append(f"CP-2 is {self.cp2_status or 'absent'}")
        reasons += [
            f"{item.input_id} is blocked"
            for item in self.bound
            if item.input_id.startswith("CP-") and item.status == "blocked"
        ]
        return tuple(dict.fromkeys(reasons))

    @property
    def limits(self) -> tuple[str, ...]:
        """The own limitation a bound blocked read optional upstream records (ruling 4,
        decision 0007 wording: never a halt). One the run does not select records none:
        `current_inputs` refuses a selected one that is unrun or stale, so blocked is the only
        missing state a bound attempt can show."""
        return tuple(
            f"Optional upstream {module_id} {self.optional_status(module_id)}: CP-3 reads no {what}"
            for module_id, what in READ_OPTIONAL.items()
            if self.optional_status(module_id) == "blocked"
        )


def _bound_module(store: Execution, attempt: Attempt, module_id: str) -> Module:
    item = next((i for i in attempt.inputs if i.input_id == module_id), None)
    if item is None:
        raise ValueError(f"The CP-3 attempt binds no {module_id} input")
    return store.result(item.sha256)


def cp3_upstream(store: Execution, attempt: Attempt) -> Upstream:
    """The bound CP-0, CP-1 and CP-2 heads of `attempt`, its bound CP-1A and CP-4 heads (when
    the run selects them), the current input set and the inherited limitations. A refusal of
    `current_inputs` is kept as text: the validator reports it as a staleness issue."""
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
        cp2=_bound_module(store, attempt, CP2),
        optional={
            module_id: _bound_module(store, attempt, module_id)
            for module_id in READ_OPTIONAL
            if module_id in bound
        },
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


# --- the context file's market evidence (B6, B6a) ----------------------------------------------
# A pack that holds a `context` source (the user's context file, `context/1`) carries quotes and
# deal-talk rows. Python reads them from the frozen spans, binds each to a CP-1 facility, cites
# each figure in the context's own text and offers the rows as T3.3 rows `c01...`; the model cites
# a row by id only (`Basis.context_rows`) and writes or copies no context figure. The engine may
# not import `deploy_workflow`, so it reads the bytes itself and re-checks only what it uses.

CONTEXT_SOURCE = "context"
CONTEXT_SCHEMA = "context/1"
CONTEXT_NUM = r"^\d+(\.\d+)?$"  # `deploy_workflow.context.NUM`; a parity test pins the two
STALE_DAYS = 30  # a quote more than this many whole days before the run as-of is stale
UNREADABLE = "context source unreadable: "
USER_SUPPLIED = "Market evidence rows from the context file are user-supplied figures"
NOT_STATED = "Not stated"
CONTEXT_CAP = f"a context quote is more than {STALE_DAYS} days old"
BY_ROW_ID = "cite it by row id in a basis"
CONTEXT_ONLY_NOTE = (
    "Market evidence is the rows in context_market_evidence; cite one only by its row id in "
    "basis.context_rows; copy no figure"
)
QUOTE_FIELDS = ("facility_id", "kind", "bid", "ask", "price", "yield_pct", "spread_bps")
QUOTE_STRINGS = (*QUOTE_FIELDS, "as_of", "provider")
QUOTE_FIGURES = (
    ("bid", "bid {}"),
    ("ask", "ask {}"),
    ("price", "price {}"),
    ("yield_pct", "yield {}%"),
    ("spread_bps", "spread {} bps"),
)
DEAL_STRINGS = (
    "facility_id",
    "talk_spread_bps_low",
    "talk_spread_bps_high",
    "talk_oid_low",
    "talk_oid_high",
    "as_of",
    "provider",
)
DEAL_RANGES = (
    ("spread talk", "talk_spread_bps_low", "talk_spread_bps_high", " bps"),
    ("OID talk", "talk_oid_low", "talk_oid_high", ""),
)
_ARRAYS = ("quotes", "deal_terms")
_WS = re.compile(r"[ \t\n\r]*")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_DECODER = json.JSONDecoder()


@dataclass(frozen=True)
class ContextRow:
    """One Python-built T3.3 row: its id (`c01`...), the quote's kind, the CP-1 facility, the
    provider and date as the context states them (`as_of` empty when a deal row has none), the
    Quote cell text, its citations, the Limitation cell text and the stale text (or None)."""

    row_id: str
    kind: str
    facility_id: str
    provider: str
    as_of: str
    figures: str
    citations: tuple[Citation, ...]
    limitation: str
    stale: str | None


@dataclass(frozen=True)
class ContextEvidence:
    """What the pack's context file offers: the rows (in context order, quotes then deal talk),
    the validator issues of an unreadable file (then no rows) and the own-limitation gaps for the
    rows that were not used."""

    rows: tuple[ContextRow, ...]
    issues: tuple[str, ...]
    gaps: tuple[str, ...]


NO_CONTEXT = ContextEvidence((), (), ())


@dataclass(frozen=True)
class _Parsed:
    text: str
    quotes: tuple[dict[str, str], ...]
    deals: tuple[dict[str, str], ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class _Member:
    """Where one string member of a row sits in the text: the key's and the value's opening
    quote, the value's end (after its closing quote) and the row object's `{`."""

    key_start: int
    value_start: int
    value_end: int
    object_start: int


@dataclass(frozen=True)
class _Reading:
    source: Source
    parsed: _Parsed
    members: Mapping[str, _Member]
    facilities: Collection[str]
    run_as_of: date


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    found: dict[str, object] = {}
    for key, value in pairs:
        if key in found:
            raise ValueError(f"duplicate key {key!r}")
        found[key] = value
    return found


def _valid_date(value: str) -> date | None:
    if _ISO.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _strings(path: str, item: object, names: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """The named members of one row as text; a missing or non-text member is a problem."""
    if not isinstance(item, dict):
        return {}, [f"{path} is not an object"]
    row: dict[str, str] = {}
    problems: list[str] = []
    for name in names:
        value = item.get(name)
        if isinstance(value, str):
            row[name] = value
        else:
            problems.append(f"{path}.{name} is {'missing' if name not in item else 'not text'}")
    return row, problems


def _figure_problems(path: str, row: Mapping[str, str], quote: bool) -> list[str]:
    """The figures of one row that are not a plain number (the context's `NUM`)."""
    figures = (
        [name for name, _ in QUOTE_FIGURES]
        if quote
        else [name for _, low, high, _ in DEAL_RANGES for name in (low, high)]
    )
    return [
        f"{path}.{name} is not a plain number"
        for name in figures
        if row.get(name) and not re.fullmatch(CONTEXT_NUM, row[name], re.ASCII)
    ]


def _date_problems(path: str, stated: str, run_as_of: date) -> list[str]:
    """A row's date: ISO, and not after the run as-of."""
    when = _valid_date(stated)
    if when is None:
        return [f"{path}.as_of is not an ISO date"]
    if when > run_as_of:
        return [f"{path}.as_of {stated} is after the run as-of {run_as_of.isoformat()}"]
    return []


def _row_problems(path: str, row: Mapping[str, str], run_as_of: date, quote: bool) -> list[str]:
    """The figures, date and kind of one row against the context's number and date rules."""
    problems = _figure_problems(path, row, quote)
    if quote and row.get("kind") not in ("observed", "indicative_talk"):
        problems.append(f"{path}.kind is not observed or indicative_talk")
    stated = row.get("as_of", "")
    if stated or quote:  # a deal row may state no date; a quote must
        problems += _date_problems(path, stated, run_as_of)
    return problems


def _identity_problems(loaded: Mapping[str, Any], run: Run) -> list[str]:
    """The schema tag and the issuer identity against the run."""
    problems: list[str] = []
    if loaded.get("schema") != CONTEXT_SCHEMA:
        problems.append(f"schema is not {CONTEXT_SCHEMA}")
    identity, found = _strings("identity", loaded.get("identity"), ("issuer_id", "issuer_name"))
    problems += found
    problems += [
        f"identity.{name} differs from the run"
        for name, ours in (("issuer_id", run.issuer_id), ("issuer_name", run.issuer_name))
        if name in identity and identity[name] != ours
    ]
    return problems


def _array_rows(
    loaded: Mapping[str, Any], array: str, names: Sequence[str], run: Run
) -> tuple[tuple[dict[str, str], ...], list[str]]:
    """One array's rows (the members CP-3 uses) and their problems."""
    items = loaded.get(array)
    if not isinstance(items, list):
        return (), [f"{array} is {'missing' if array not in loaded else 'not a list'}"]
    rows: list[dict[str, str]] = []
    problems: list[str] = []
    for index, item in enumerate(items):
        path = f"{array}[{index}]"
        row, found = _strings(path, item, names)
        problems += found or _row_problems(path, row, run.as_of, array == "quotes")
        rows.append(row)
    return tuple(rows), problems


def _read_context(source: Source, run: Run) -> _Parsed:
    """The context source's quotes and deal rows (only the members CP-3 uses), or the issues that
    make the file unreadable. `prepare` never calls `load_context`, so every figure, date and
    identity used is re-checked here; no other form rule is re-applied. The source must be
    `text/plain` with one line per span: citations map a line of the joined text to its span."""
    text = "\n".join(span.text for span in source.spans)

    def refused(*problems: str) -> _Parsed:
        return _Parsed(text, (), (), tuple(UNREADABLE + problem for problem in problems))

    if source.status != "ready":
        return refused(f"status is {source.status}: {source.limitation}")
    if source.media_type != "text/plain":
        return refused(f"media type is {source.media_type}, not text/plain")
    if any("\n" in span.text for span in source.spans):
        return refused("a span holds more than one line")
    try:
        loaded = json.loads(text, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as error:
        return refused(f"not valid JSON ({error.msg} at line {error.lineno})")
    except (ValueError, RecursionError) as error:
        return refused(f"not valid JSON ({error})")
    if not isinstance(loaded, dict):
        return refused("the top level is not an object")
    problems = _identity_problems(loaded, run)
    quotes, found = _array_rows(loaded, "quotes", QUOTE_STRINGS, run)
    problems += found
    deals, found = _array_rows(loaded, "deal_terms", DEAL_STRINGS, run)
    problems += found
    return refused(*problems) if problems else _Parsed(text, quotes, deals, ())


def _skip(text: str, at: int) -> int:
    found = _WS.match(text, at)  # `[ \t\n\r]*` matches at every offset
    return at if found is None else found.end()


def _expect(text: str, at: int, char: str) -> int:
    if text[at : at + 1] != char:
        raise ValueError(f"expected {char!r} at offset {at}")
    return _skip(text, at + 1)


def _after(text: str, at: int, close: str) -> int:
    """After one member or element ending at `at`: past a ',' , or at the closing `close`."""
    at = _skip(text, at)
    if text[at : at + 1] == ",":
        return _skip(text, at + 1)
    if text[at : at + 1] != close:
        raise ValueError(f"expected ',' or {close!r} at offset {at}")
    return at


def _object_members(text: str, at: int, prefix: str, found: dict[str, _Member]) -> int:
    """Read the object at `at`; record each string member as `<prefix>.<key>`; return its end."""
    start = at
    at = _expect(text, at, "{")
    while text[at : at + 1] != "}":
        key, end = _DECODER.raw_decode(text, at)
        if not isinstance(key, str):
            raise TypeError(f"member name at offset {at} is not text")
        key_start, at = at, _expect(text, _skip(text, end), ":")
        value, end = _DECODER.raw_decode(text, at)
        if isinstance(value, str):
            path = f"{prefix}.{key}"
            if path in found:
                raise ValueError(f"duplicate member {path}")
            found[path] = _Member(key_start, at, end, start)
        at = _after(text, end, "}")
    return at + 1


def _array_members(text: str, at: int, key: str, found: dict[str, _Member]) -> int:
    """Read the array at `at` (`quotes` or `deal_terms`); record the string members of each of
    its objects; return the offset after its `]`."""
    at = _expect(text, at, "[")
    index = 0
    while text[at : at + 1] != "]":
        if text[at : at + 1] == "{":
            end = _object_members(text, at, f"{key}[{index}]", found)
        else:
            _, end = _DECODER.raw_decode(text, at)
        at, index = _after(text, end, "]"), index + 1
    return _skip(text, at + 1)


def _members(text: str) -> dict[str, _Member]:
    """Every string member of `quotes[i]` and `deal_terms[i]`, by `<array>[i].<field>`. Raises
    ValueError on text that is not a JSON object."""
    found: dict[str, _Member] = {}
    at = _expect(text, _skip(text, 0), "{")
    while text[at : at + 1] != "}":
        key, end = _DECODER.raw_decode(text, at)
        at = _expect(text, _skip(text, end), ":")
        if key in _ARRAYS and text[at : at + 1] == "[":
            end = _array_members(text, at, key, found)
        else:
            _, end = _DECODER.raw_decode(text, at)
        at = _after(text, end, "}")
    return found


def _value_offsets(text: str) -> dict[str, int]:
    """The offset of each row string value's opening `"` in `text`, by `<array>[i].<field>`."""
    return {path: member.value_start for path, member in _members(text).items()}


def _cite(source: Source, text: str, member: _Member) -> Citation | None:
    """One figure cited in the context's own text (B20, B20a): the member alone on its line, else
    the text from the row object's `{` through the figure when that is on one line and occurs once
    in it, else None (never a guessed span)."""
    line = text.count("\n", 0, member.value_start) + 1
    span = source.spans[line - 1]
    own = text[member.key_start : member.value_end]
    quote = (
        own
        if span.text.strip() in (own, own + ",")
        else text[member.object_start : member.value_end]
    )
    if "\n" in quote or span.text.count(quote) != 1 or source.sha256 is None:
        return None
    citation = Citation(
        source_id=CONTEXT_SOURCE, source_sha256=source.sha256, locator=span.locator, quote=quote
    )
    return None if citation_issues((citation,), (source,)) else citation


def _cite_all(
    ctx: _Reading, array: str, index: int, row: Mapping[str, str], fields: Sequence[str]
) -> tuple[Citation, ...] | None:
    """The citations of the named figures of one row, in order; None unless every one cites. A
    figure whose raw text is not exactly `"<value>"` (a JSON escape, say) is not cited: the
    file's bytes would not hold the figure the Quote cell shows."""
    cited: list[Citation] = []
    for name in fields:
        member = ctx.members[f"{array}[{index}].{name}"]
        if ctx.parsed.text[member.value_start : member.value_end] != f'"{row[name]}"':
            return None
        citation = _cite(ctx.source, ctx.parsed.text, member)
        if citation is None:
            return None
        cited.append(citation)
    return tuple(cited)


def _stale_text(facility: str, stated: str, run_as_of: date) -> str | None:
    when = _valid_date(stated)
    days = 0 if when is None else (run_as_of - when).days
    if days <= STALE_DAYS:
        return None
    return (
        f"Stale quote: {facility} quote dated {stated} is {days} days before the run as-of "
        f"{run_as_of.isoformat()} (limit {STALE_DAYS})"
    )


def _limitation(provider: str, notes: Sequence[str], stated: str, stale: str | None) -> str:
    """The Limitation cell: the provider, the user-supplied label, any omitted bound and the
    date note (the stale text, or that a deal row states no date)."""
    parts = [f"Provider: {provider}" if provider else "Provider not stated", "user-supplied figure"]
    parts += notes
    if not stated:
        parts.append("date not stated")
    elif stale:
        parts.append(stale)
    return "; ".join(parts)


def _quote_row(ctx: _Reading, index: int, quote: Mapping[str, str]) -> ContextRow | str:
    """One quote as a row, or the gap text saying why it is not used."""
    facility = quote["facility_id"]
    if facility not in ctx.facilities:
        return f"context quote for facility {facility} matches no CP-1 facility (T4.18); not used"
    fields = [name for name, _ in QUOTE_FIGURES if quote[name]]
    if not fields:
        return f"context quote for facility {facility} carries no figure; not used"
    cites = _cite_all(ctx, "quotes", index, quote, fields)
    if cites is None:
        return (
            f"context quote row {index + 1} for facility {facility} cannot be cited as one "
            "unique span; not used"
        )
    shown = ", ".join(label.format(quote[name]) for name, label in QUOTE_FIGURES if quote[name])
    stale = _stale_text(facility, quote["as_of"], ctx.run_as_of)
    return ContextRow(
        "",
        quote["kind"],
        facility,
        quote["provider"],
        quote["as_of"],
        f"{facility}: {shown}",
        cites,
        _limitation(quote["provider"], (), quote["as_of"], stale),
        stale,
    )


def _deal_row(ctx: _Reading, index: int, deal: Mapping[str, str]) -> ContextRow | str | None:
    """One deal-terms row's talk as one `indicative_talk` range row (no midpoint), or the gap
    text saying why it is not used; None when the row states no talk at all."""
    facility = deal["facility_id"]
    if not any(deal[name] for _, low, high, _ in DEAL_RANGES for name in (low, high)):
        return None
    if facility not in ctx.facilities:
        return (
            f"context deal term for facility {facility} matches no CP-1 facility (T4.18); not used"
        )
    shown: list[str] = []
    fields: list[str] = []
    notes: list[str] = []
    for label, low, high, unit in DEAL_RANGES:
        if deal[low] and deal[high]:
            shown.append(f"{label} {deal[low]}-{deal[high]}{unit}")
            fields += [low, high]
        elif deal[low] or deal[high]:
            side, value, other = ("lower", deal[low], "an upper")
            if not deal[low]:
                side, value, other = "upper", deal[high], "a lower"
            notes.append(f"{label} {side} bound {value} given without {other} bound; not used")
    here = f"context deal terms row {index + 1} for facility {facility}"
    if not shown:
        return f"{here} carries no complete talk range; not used"
    cites = _cite_all(ctx, "deal_terms", index, deal, fields)
    if cites is None:
        return f"{here} cannot be cited as one unique span; not used"
    stale = _stale_text(facility, deal["as_of"], ctx.run_as_of)
    return ContextRow(
        "",
        "indicative_talk",
        facility,
        deal["provider"],
        deal["as_of"],
        f"{facility}: " + "; ".join(shown),
        cites,
        _limitation(deal["provider"], notes, deal["as_of"], stale),
        stale,
    )


def context_evidence(pack: PreparedPack, facilities: Collection[str]) -> ContextEvidence:
    """The market evidence the pack's `context` source offers, all Python's: each quote and each
    deal row's talk with a CP-1 facility (`facilities`, T4.18 ids) and a figure that cites as one
    unique span becomes a row `c01...` (quotes, then deal terms); one that does not is named in
    `gaps`; an unreadable file is `issues`, never a silent "no evidence". A pack without a
    `context` source offers `NO_CONTEXT`."""
    source = next((s for s in pack.sources if s.source_id == CONTEXT_SOURCE), None)
    if source is None:
        return NO_CONTEXT
    parsed = _read_context(source, pack.run)
    if parsed.issues:
        return ContextEvidence((), parsed.issues, ())
    try:
        members = _members(parsed.text)
    except (ValueError, TypeError) as error:
        return ContextEvidence((), (f"{UNREADABLE}cannot locate the figures ({error})",), ())
    ctx = _Reading(source, parsed, members, facilities, pack.run.as_of)
    built = [
        *(_quote_row(ctx, i, quote) for i, quote in enumerate(parsed.quotes)),
        *(_deal_row(ctx, i, deal) for i, deal in enumerate(parsed.deals)),
    ]
    rows: list[ContextRow] = []
    gaps: list[str] = []
    for item in built:
        if isinstance(item, str):
            gaps.append(f"Gap (Medium): {item}")
        elif item is not None:
            rows.append(dataclasses.replace(item, row_id=f"c{len(rows) + 1:02d}"))
    return ContextEvidence(tuple(rows), (), tuple(gaps))


# --- validation ------------------------------------------------------------------------------

_TEXT = (str, str | None)
_NOT_PROSE = frozenset({"facility_id", "source_id"})
SubmissionRow = Instrument | MarketEvidence | Preference | Risk | Gap
QuoteKey = tuple[str, str, str]


def _key(quote: Quote) -> QuoteKey:
    return (quote.source_id, quote.locator, quote.quote)


def _rows(submission: RelativeValueSubmission) -> Iterator[tuple[str, SubmissionRow]]:
    for name in ("instruments", "market_evidence"):
        for index, row in enumerate(getattr(submission, name)):
            yield f"{name}[{index}]", row
    yield "preference", submission.preference
    for name in ("risks", "gaps"):
        for index, row in enumerate(getattr(submission, name)):
            yield f"{name}[{index}]", row


def _texts(row: BaseModel) -> Iterator[tuple[str, str]]:
    """(field, value) of each prose field of one row; ids, enums, refs and quotes excluded."""
    for name, info in type(row).model_fields.items():
        value = getattr(row, name)
        if name not in _NOT_PROSE and info.annotation in _TEXT and value is not None:
            yield name, value


def _figures(row: BaseModel, bound: Mapping[str, Fact]) -> list[Fact]:
    """The CP-1 facts the row's text names by figure reference, in reading order. A malformed
    text names none here; `prose.issues` reports it."""
    found: list[Fact] = []
    for _, text in _texts(row):
        try:
            runs = prose.tokenize(text)
        except ValueError:
            continue
        found += [bound[r.text] for r in runs if r.kind == "ref" and r.figure and r.text in bound]
    return list({fact.fact_id: fact for fact in found}.values())


def _none(text: str) -> bool:
    return text.strip().casefold() == NONE


def _stale_issues(upstream: Upstream) -> list[str]:
    if isinstance(upstream.current, str):
        return [f"Stale inputs: {upstream.current}"]
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
    """The supplied modules are the bound heads (same module, same canonical hash); a bound
    read optional upstream is supplied, and none is supplied unbound."""
    supplied: dict[str, Module | None] = {CP0: upstream.cp0, CP1: upstream.cp1, CP2: upstream.cp2}
    bound = {item.input_id: item for item in upstream.bound}
    for module_id in READ_OPTIONAL:
        if module_id in bound or module_id in upstream.optional:
            supplied[module_id] = upstream.optional.get(module_id)
    issues: list[str] = []
    for module_id, module in supplied.items():
        item = bound.get(module_id)
        if (
            item is None
            or module is None
            or module.module_id != module_id
            or module.content_hash() != item.sha256
        ):
            issues.append(f"Upstream {module_id}: the supplied module is not the bound input")
    issues.extend(
        f"Required upstream {item.input_id} is blocked"
        for item in upstream.bound
        if item.input_id in REQUIRED and item.status == "blocked"
    )
    return issues


@dataclass(frozen=True)
class _Evidence:
    """The submission's market evidence bound to the pack: each quoted row's kind and
    `Citation` by its quote, and the issues of the rows that could not be bound."""

    kinds: Mapping[QuoteKey, str]
    citations: Mapping[QuoteKey, Citation]
    issues: tuple[str, ...]
    context: ContextEvidence = NO_CONTEXT

    def strength(self) -> frozenset[str]:
        return (frozenset(self.kinds.values()) | {row.kind for row in self.context.rows}) - {NONE}

    @property
    def context_kinds(self) -> Mapping[str, str]:
        return {row.row_id: row.kind for row in self.context.rows}

    @property
    def context_stale(self) -> bool:
        return any(row.stale for row in self.context.rows)


def _bind_evidence(
    pack: PreparedPack, submission: RelativeValueSubmission, upstream: Upstream
) -> _Evidence:
    """Each market-evidence quote as a `Citation` with the pack's source hash, held to the
    market rules: a `none` row quotes nothing, every other row quotes its own `third_party`
    source, the quote holds in its span (`citation_issues`) and an `observed` row never quotes
    indicative talk."""
    digests = {s.source_id: s.sha256 for s in pack.sources if s.status == "ready" and s.sha256}
    market = upstream.market_sources
    context = context_evidence(pack, upstream.facilities)
    kinds: dict[QuoteKey, str] = {}
    citations: dict[QuoteKey, Citation] = {}
    first: dict[QuoteKey, int] = {}
    issues: list[str] = list(context.issues)
    for index, row in enumerate(submission.market_evidence):
        path = f"market_evidence[{index}]"
        if row.source_id == CONTEXT_SOURCE:  # a model never writes a context row
            issues.append(f"{path}: context market evidence is built by Python; {BY_ROW_ID}")
            continue
        # One row per quoted span: a basis quote names its row, so a span quoted twice (under
        # two kinds, say) would leave the row it names to submission order.
        if row.quote is not None and (seen := first.setdefault(_key(row.quote), index)) != index:
            issues.append(
                f"{path}: quotes the same span as market_evidence[{seen}] "
                f"({row.quote.source_id} {row.quote.locator})"
            )
        found, citation = _market_row(path, row, market, digests, pack)
        issues += found
        if citation is not None and row.quote is not None:
            kinds[_key(row.quote)] = row.kind
            citations[_key(row.quote)] = citation
    return _Evidence(kinds, citations, tuple(dict.fromkeys(issues)), context)


def _market_row(
    path: str,
    row: MarketEvidence,
    market: frozenset[str],
    digests: Mapping[str, str],
    pack: PreparedPack,
) -> tuple[list[str], Citation | None]:
    """One model market-evidence row's issues and, when it binds, its `Citation`."""
    quote = row.quote
    if row.kind == NONE:
        extra = [f"{path}: a none row quotes nothing"] if quote is not None else []
        return extra + (
            [] if row.limitation else [f"{path}: a none row states its limitation"]
        ), None
    if quote is None:
        return [f"{path}: an {row.kind} row quotes its source"], None
    issues: list[str] = []
    if quote.source_id != row.source_id:
        issues.append(f"{path}.quote: quotes {quote.source_id}, not {row.source_id}")
    if row.source_id not in market:
        issues.append(f"{path}: {row.source_id} is not a third_party source (CP-0 T3)")
    digest = digests.get(quote.source_id)
    if digest is None:
        return [*issues, f"Unavailable or changed source: {quote.source_id}"], None
    try:
        citation = Citation(
            source_id=quote.source_id,
            source_sha256=digest,
            locator=quote.locator,
            quote=quote.quote,
        )
    except ValidationError:
        return [*issues, f"{path}: malformed citation (empty locator or quote)"], None
    issues.extend(f"{path}: {i}" for i in citation_issues((citation,), pack.sources))
    if row.kind == "observed":
        issues.extend(
            f'{path}: an observed row quotes indicative talk: "{marker}"'
            for marker in _found(_TALK, quote.quote)
        )
    return issues, citation


def _basis_issues(
    path: str, basis: Basis, catalogue: Mapping[str, CatalogueRow], evidence: _Evidence
) -> list[str]:
    issues = [
        f"{path}.basis.cp2_refs: unknown CP-2 row {ref}"
        for ref in basis.cp2_refs
        if ref not in catalogue
    ]
    issues += [
        f"{path}.basis.quotes[{j}]: quotes no market_evidence row ({q.source_id} {q.locator})"
        for j, q in enumerate(basis.quotes)
        if _key(q) not in evidence.kinds
    ]
    issues += [
        f"{path}.basis.context_rows[{j}]: no context row {row_id}"
        for j, row_id in enumerate(basis.context_rows)
        if row_id not in evidence.context_kinds
    ]
    return issues


def _cites_market(basis: Basis) -> bool:
    """The basis cites market evidence: a `market_evidence` quote or a context row."""
    return bool(basis.quotes or basis.context_rows)


def _talk_only(basis: Basis, evidence: _Evidence) -> bool:
    kinds = {evidence.kinds.get(_key(quote)) for quote in basis.quotes}
    kinds |= {evidence.context_kinds.get(row_id) for row_id in basis.context_rows}
    return _cites_market(basis) and kinds <= {"indicative_talk"}


def _level_issues(where: str, text: str) -> list[str]:
    return [
        f'{where}: indicative talk worded as a market level: "{phrase}"'
        for phrase in _found(_LEVELS, text)
    ]


def _instrument_issues(
    submission: RelativeValueSubmission,
    upstream: Upstream,
    evidence: _Evidence,
    bound: Mapping[str, Fact],
) -> list[str]:
    issues: list[str] = []
    offered = upstream.facilities
    catalogue = upstream.catalogue
    seen = [row.facility_id for row in submission.instruments]
    for facility_id in sorted(f for f, n in Counter(seen).items() if n > 1):
        issues.append(f"instruments: facility {facility_id} appears more than once")
    for index, row in enumerate(submission.instruments):
        path = f"instruments[{index}]"
        if row.facility_id not in offered:
            issues.append(f"{path}.facility_id: unknown CP-1 facility {row.facility_id}")
        issues += _basis_issues(path, row.basis, catalogue, evidence)
        market = not _none(row.market_observation)
        cites_market = _cites_market(row.basis)
        if market and not cites_market:
            issues.append(f"{path}: a market observation cites a market_evidence quote")
        if not (row.basis.cp2_refs or cites_market or _figures(row, bound)):
            issues.append(
                f"{path}: an instrument cites a CP-2 row, a market_evidence quote or a CP-1 figure"
            )
        if market and _talk_only(row.basis, evidence):
            issues += _level_issues(f"{path}.market_observation", row.market_observation)
    return issues


def _cap_reasons(upstream: Upstream, evidence: _Evidence) -> list[str]:
    """Why the preference is capped below High: the upstream caps, talk-only evidence and a stale
    context quote, in that order."""
    reasons = list(upstream.caps)
    if evidence.strength() == {"indicative_talk"}:
        reasons.append("the market evidence is indicative talk only")
    if evidence.context_stale:
        reasons.append(CONTEXT_CAP)
    return reasons


def _preference_issues(
    submission: RelativeValueSubmission, upstream: Upstream, evidence: _Evidence
) -> list[str]:
    """The ordering, the basis and gap propagation on the preference (decision 0007, rulings
    4 and 5)."""
    row = submission.preference
    issues = _basis_issues("preference", row.basis, upstream.catalogue, evidence)
    instruments = [item.facility_id for item in submission.instruments]
    known = set(instruments)
    ranked = Counter(row.ordering)
    for facility_id in dict.fromkeys(row.ordering):
        if facility_id not in known:
            issues.append(f"preference.ordering: {facility_id} is not an instruments row")
        elif ranked[facility_id] > 1:
            issues.append(f"preference.ordering: {facility_id} appears more than once")
    for facility_id in dict.fromkeys(instruments):
        if facility_id not in ranked:
            issues.append(f"preference.ordering: {facility_id} is missing")
    insufficient = row.confidence == "Insufficient Information"
    if insufficient and not row.limitation:
        issues.append("preference: an Insufficient Information preference states its limitation")
    strength = evidence.strength()
    if not strength and not insufficient:
        issues.append(
            "preference.confidence: Insufficient Information without observed or indicative "
            "market evidence"
        )
    if not insufficient and not _cites_market(row.basis):
        issues.append("preference: a relative value preference cites a market_evidence quote")
    reasons = _cap_reasons(upstream, evidence)
    if reasons and row.confidence == "High":
        issues.append(f"preference.confidence: capped below High because {'; '.join(reasons)}")
    if _talk_only(row.basis, evidence):
        issues += _level_issues("preference.rationale", row.rationale)
    return issues


def _risk_issues(
    submission: RelativeValueSubmission, upstream: Upstream, bound: Mapping[str, Fact]
) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(submission.risks):
        path = f"risks[{index}]"
        issues += [
            f"{path}.cp2_refs: unknown CP-2 row {ref}"
            for ref in row.cp2_refs
            if ref not in upstream.catalogue
        ]
        if not row.cp2_refs and not _figures(row, bound):
            issues.append(f"{path}: a risk cites a CP-2 row or a CP-1 figure")
    return issues


def _text_issues(
    submission: RelativeValueSubmission, bound: Mapping[str, Fact], names: tuple[str, ...]
) -> list[str]:
    issues: list[str] = []
    for path, row in _rows(submission):
        for name, text in _texts(row):
            where = f"{path}.{name}"
            if prose.is_blank(text):
                issues.append(f"{where}: empty text")
                continue
            issues.extend(f"{where}: {issue}" for issue in prose.issues(text, bound, names=names))
            # Quotes are source text, not CP-3's words: only the model's own text is guarded.
            issues.extend(prohibited_issues(where, text, kinds=CP3_PROHIBITED_KINDS))
            if isinstance(row, MarketEvidence) and row.kind == "indicative_talk":
                issues += _level_issues(where, text)
    return issues


def validate_relative_value(
    pack: PreparedPack, submission: RelativeValueSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Every issue of `submission` over the bound `upstream`, in a stable order; empty when it
    composes."""
    try:
        pack = PreparedPack.model_validate_json(pack.model_dump_json())
        submission = RelativeValueSubmission.model_validate_json(submission.model_dump_json())
    except ValidationError as error:
        return shape_issues(error)
    bound = prose.bind(referencable(upstream.cp1.facts))
    evidence = _bind_evidence(pack, submission, upstream)
    issues = [*_stale_issues(upstream), *_provenance_issues(upstream), *evidence.issues]
    issues += _instrument_issues(submission, upstream, evidence, bound)
    issues += _preference_issues(submission, upstream, evidence)
    issues += _risk_issues(submission, upstream, bound)
    issues += _text_issues(submission, bound, (pack.run.issuer_name,))
    return tuple(dict.fromkeys(issues))


# --- composition -----------------------------------------------------------------------------

NO_BASIS = "No CP-2 row, market evidence or CP-1 figure cited"
NO_MARKET = "No market evidence cited."
# Minimal tables under r14 CP-3 ids (ruling 7); the id-to-content mapping and every column are
# composed from the contract rows, not from r14 column definitions (`methods/cp3.md`).
REGISTERS: Mapping[str, Register] = {
    item.table_id: item
    for item in (
        Register(
            "T3.1",
            "Instrument relative value",
            (
                ("facility_id", "Facility ID"),
                ("fundamental_view", "Fundamental view"),
                ("market_observation", "Market observation"),
                ("basis", "Basis"),
                ("limitation", "Limitation"),
            ),
        ),
        Register(
            "T3.3",
            "Market evidence",
            (
                ("source", "Source"),
                ("kind", "Kind"),
                ("quote", "Quote"),
                ("as_of", "As of"),
                ("limitation", "Limitation"),
            ),
        ),
        Register(
            "T3.4",
            "Security selection preference",
            (
                ("ordering", "Ordering"),
                ("rationale", "Rationale"),
                ("confidence", "Confidence"),
                ("basis", "Basis"),
                ("limitation", "Limitation"),
            ),
        ),
        Register(
            "T3.9",
            "Relative value risks",
            (
                ("risk", "Risk"),
                ("mechanic", "Risk mechanic"),
                ("implication", "Credit implication"),
                ("severity", "Severity"),
                ("basis", "Basis"),
            ),
        ),
        Register(
            "T3.10",
            "Gaps ledger",
            (
                ("gap_id", "Gap ID"),
                ("gap", "Gap"),
                ("why_it_matters", "Why it matters"),
                ("affected_analysis", "Affected analysis"),
                ("severity", "Severity"),
                ("action", "Action"),
            ),
        ),
    )
}
REQUIRED_TABLES = tuple(REGISTERS)
# The FP 01 `relative-value` table: one model text per line (a prose block shows one line per
# bound fact, unlabelled): the preference first (the collapsed block's summary), then each
# instrument, its CP-1 facility name leading the text.
RELATIVE_VALUE = "cp3.relative_value"
KIND_LABEL: Mapping[str, str] = {
    "observed": "Observed",
    "indicative_talk": "Indicative talk",
    "none": "None",
}


@dataclass(frozen=True)
class _SourceCell(Cell):
    """A cell that is the context file's own text (Q-X): its fact carries `value_class` source."""


@dataclass(frozen=True)
class _Row:
    row_id: str
    label: str
    cells: Sequence[Cell]


class _Composer:
    """Writes the tables: cells from validated rows, figures spelled by Python."""

    def __init__(
        self,
        bound: Mapping[str, Fact],
        catalogue: Mapping[str, CatalogueRow],
        evidence: _Evidence,
    ) -> None:
        self.bound = bound
        self.catalogue = catalogue
        self.evidence = evidence
        self.tables: list[ReportTable] = []
        self.facts: list[Fact] = []
        self.limitations: list[str] = []
        self.referenced: dict[str, Fact] = {}

    def text(self, value: str) -> str:
        """Validated run text with each figure reference spelled by Python (`spelled`)."""
        out: list[str] = []
        for run in prose.tokenize(value):
            if run.kind == "text":
                out.append(run.text)
                continue
            fact = self.bound[run.text]
            self.referenced.setdefault(fact.fact_id, fact)
            out.append(spelled(fact))
        return "".join(out)

    def said(self, value: str) -> Cell:
        return Cell(self.text(value), judged=True)

    def limit(self, limitation: str | None) -> Cell:
        return Cell(self.text(limitation) if limitation else NONE_STATED)

    def basis(self, row: Instrument | Preference | Risk) -> Cell:
        """Python's basis cell: each cited CP-2 row with its label in catalogue (register)
        order, each quoted market evidence by source and locator in the model's order, then
        each CP-1 figure in reading order."""
        refs = row.cp2_refs if isinstance(row, Risk) else row.basis.cp2_refs
        quotes = () if isinstance(row, Risk) else row.basis.quotes
        context_rows = () if isinstance(row, Risk) else row.basis.context_rows
        cited = set(refs)
        parts = [
            f"CP-2 {ref} ({item.label})" for ref, item in self.catalogue.items() if ref in cited
        ]
        parts += [
            f"Market evidence {q.source_id} {q.locator} "
            f"({KIND_LABEL[self.evidence.kinds[_key(q)]].lower()})"
            for q in dict.fromkeys(quotes)
        ]
        parts += [
            f"Market evidence {CONTEXT_SOURCE} {row_id} "
            f"({KIND_LABEL[self.evidence.context_kinds[row_id]].lower()})"
            for row_id in dict.fromkeys(context_rows)
        ]
        parts += [
            f"CP-1 {fact.label} · {fact.period}" if fact.period else f"CP-1 {fact.label}"
            for fact in _figures(row, self.bound)
        ]
        return Cell("; ".join(parts) or NO_BASIS)

    def cited(self, basis: Basis) -> tuple[Citation, ...]:
        """The basis's citations: its market-evidence quotes, then its context rows' figures."""
        by_id = {row.row_id: row for row in self.evidence.context.rows}
        market = (self.evidence.citations[_key(q)] for q in basis.quotes)
        context = (c for row_id in basis.context_rows for c in by_id[row_id].citations)
        return tuple(dict.fromkeys((*market, *context)))

    def _fact(self, table_id: str, row_id: str, field: str, label: str, cell: Cell) -> str:
        fact_id = f"{table_id}.{row_id}.{field}"
        self.facts.append(
            Fact(
                fact_id=fact_id,
                label=label,
                table_id=table_id,
                row_id=row_id,
                field=field,
                text=cell.text,
                status="known" if cell.text is not None else cell.status,
                citations=cell.citations,
                value_class=(
                    "analyst_judgment"
                    if cell.judged
                    else "source"
                    if isinstance(cell, _SourceCell)
                    else None
                ),
                limitation=cell.reason if cell.text is None else None,
            )
        )
        return fact_id

    def _empty(self, title: str, required: bool) -> Cell:
        if required:
            reason = f"No {title.lower()} rows in the CP-3 submission"
            self.limitations.append(reason)
            return Cell(None, reason=reason, status="missing")
        return Cell(
            None, reason=f"None in the CP-3 submission ({title.lower()})", status="not_applicable"
        )

    def table(self, register: Register, rows: Sequence[_Row], *, required: bool) -> None:
        if not rows:
            cell = self._empty(register.title, required)
            rows = (_Row("none", "None", tuple(cell for _ in register.columns)),)
        self.tables.append(
            ReportTable(
                table_id=register.table_id,
                title=register.title,
                columns=tuple(TableColumn(field=f, label=label) for f, label in register.columns),
                rows=tuple(
                    TableRow(
                        row_id=row.row_id,
                        label=row.label,
                        fact_ids=tuple(
                            self._fact(register.table_id, row.row_id, field, label, cell)
                            for (field, label), cell in zip(
                                register.columns, row.cells, strict=True
                            )
                        ),
                    )
                    for row in rows
                ),
                row_header="Item",
            )
        )

    def front(self, lines: Sequence[tuple[str, str, Cell]]) -> None:
        """The FP 01 table: one `value` fact per line, labelled as the block shows it."""
        self.tables.append(
            ReportTable(
                table_id=RELATIVE_VALUE,
                title="Relative value",
                columns=(TableColumn(field="value", label="Value"),),
                rows=tuple(
                    TableRow(
                        row_id=row_id,
                        label=label,
                        fact_ids=(self._fact(RELATIVE_VALUE, row_id, "value", label, cell),),
                    )
                    for row_id, label, cell in lines
                ),
                row_header="Relative value",
            )
        )


def _instruments(
    submission: RelativeValueSubmission, offered: Mapping[str, Facility], out: _Composer
) -> list[tuple[str, str, Cell]]:
    """T3.1, one row per instrument in submission order, labelled with the CP-1 facility name;
    returns the FP 01 lines (the fundamental view, then the market observation)."""
    rows: list[_Row] = []
    lines: list[tuple[str, str, Cell]] = []
    for index, row in enumerate(submission.instruments, 1):
        row_id, name = f"i{index:02d}", offered[row.facility_id].name
        view = out.text(row.fundamental_view)
        market = NO_MARKET if _none(row.market_observation) else out.text(row.market_observation)
        rows.append(
            _Row(
                row_id,
                name,
                (
                    Cell(row.facility_id),
                    Cell(view, judged=True),
                    Cell(market, judged=not _none(row.market_observation)),
                    out.basis(row),
                    out.limit(row.limitation),
                ),
            )
        )
        # A prose block line carries no label, so the facility name leads the text.
        lines.append((row_id, name, Cell(f"{name}: {view} Market: {market}", judged=True)))
    out.table(REGISTERS["T3.1"], rows, required=True)
    return lines


def _market(submission: RelativeValueSubmission, out: _Composer) -> None:
    """T3.3: each market-evidence row with its quote carried as a cited cell."""
    rows: list[_Row] = []
    for index, row in enumerate(submission.market_evidence, 1):
        quote = row.quote
        rows.append(
            _Row(
                f"m{index:02d}",
                f"Market evidence {index}",
                (
                    Cell(row.source_id),
                    Cell(KIND_LABEL[row.kind]),
                    Cell(quote.quote, citations=(out.evidence.citations[_key(quote)],))
                    if quote is not None
                    else Cell(NONE_STATED),
                    out.said(row.as_of),
                    out.limit(row.limitation),
                ),
            )
        )
    rows += [
        _Row(
            row.row_id,
            f"Context market evidence {number}",
            (
                Cell(CONTEXT_SOURCE),
                Cell(KIND_LABEL[row.kind]),
                _SourceCell(row.figures, citations=row.citations),
                _SourceCell(row.as_of or NOT_STATED),
                Cell(row.limitation),
            ),
        )
        for number, row in enumerate(out.evidence.context.rows, 1)
    ]
    out.table(REGISTERS["T3.3"], rows, required=False)


def _preference(
    submission: RelativeValueSubmission, offered: Mapping[str, Facility], out: _Composer
) -> Cell:
    """T3.4 and the FP 01 preference line: the ordering spelled by Python from the CP-1
    facility names, then the model's rationale."""
    row = submission.preference
    ordering = " > ".join(offered[f].name for f in row.ordering) or "No ordering"
    rationale = out.text(row.rationale) + (
        LABEL["Insufficient Information"] if row.confidence == "Insufficient Information" else ""
    )
    out.table(
        REGISTERS["T3.4"],
        [
            _Row(
                "preference",
                "Preference",
                (
                    Cell(ordering, judged=True),
                    Cell(rationale, judged=True),
                    Cell(row.confidence),
                    out.basis(row),
                    out.limit(row.limitation),
                ),
            )
        ],
        required=True,
    )
    if row.confidence == "Insufficient Information":
        why = out.text(row.limitation or "")
        out.limitations.append(f"Relative value preference is Insufficient Information: {why}")
    return Cell(f"Preference: {ordering}. {rationale}", judged=True)


def _risks_and_gaps(submission: RelativeValueSubmission, out: _Composer) -> None:
    out.table(
        REGISTERS["T3.9"],
        [
            _Row(
                f"r{index:02d}",
                f"Risk {index}",
                (
                    out.said(risk.risk),
                    out.said(risk.mechanic),
                    out.said(risk.implication),
                    Cell(risk.severity),
                    out.basis(risk),
                ),
            )
            for index, risk in enumerate(submission.risks, 1)
        ],
        required=True,
    )
    out.table(
        REGISTERS["T3.10"],
        [
            _Row(
                f"g{index:02d}",
                f"Gap {index}",
                (
                    Cell(f"CP-3-GAP-{index:03d}"),
                    out.said(gap.gap),
                    out.said(gap.why_it_matters),
                    out.said(gap.affected_analysis),
                    Cell(gap.severity),
                    out.said(gap.action),
                ),
            )
            for index, gap in enumerate(submission.gaps, 1)
        ],
        required=False,
    )


def _evidence_limitations(evidence: _Evidence) -> list[str]:
    """Own limitations of the market evidence (decision 0007): none at all, or talk only."""
    strength = evidence.strength()
    if not strength:
        return ["No observed or indicative market evidence: relative value is not assessed"]
    if strength == {"indicative_talk"}:
        return ["Market evidence is indicative talk only, not an observed market level"]
    return []


def _context_limitations(evidence: _Evidence) -> list[str]:
    """Own limitations of the context file's rows: each row not used (named), each stale quote,
    and that the rows are user-supplied figures (whenever a Python row exists)."""
    context = evidence.context
    stale = [row.stale for row in context.rows if row.stale]
    return [*context.gaps, *stale, *([USER_SUPPLIED] if context.rows else [])]


def relative_value(
    pack: PreparedPack, submission: RelativeValueSubmission, upstream: Upstream
) -> RelativeValueReport:
    """The composed CP-3 tables of a valid submission; raises ValueError on any issue."""
    issues = validate_relative_value(pack, submission, upstream)
    if issues:
        raise ValueError("; ".join(issues))
    pack = PreparedPack.model_validate_json(pack.model_dump_json())
    submission = RelativeValueSubmission.model_validate_json(submission.model_dump_json())
    evidence = _bind_evidence(pack, submission, upstream)
    offered = upstream.facilities
    out = _Composer(prose.bind(referencable(upstream.cp1.facts)), upstream.catalogue, evidence)
    # Own limitations: the gaps rows, the market evidence, a blocked read optional upstream, an
    # empty required register and an Insufficient Information preference.
    # Inherited ones (a restricted CP-2's included) are settlement's (`execution.settle`).
    out.limitations.extend(f"Gap ({g.severity}): {out.text(g.gap)}" for g in submission.gaps)
    out.limitations.extend(_evidence_limitations(evidence))
    out.limitations.extend(_context_limitations(evidence))
    out.limitations.extend(upstream.limits)
    lines = _instruments(submission, offered, out)
    _market(submission, out)
    preference = _preference(submission, offered, out)
    _risks_and_gaps(submission, out)
    out.front([("preference", "Preference", preference), *lines])
    referenced = [
        fact.model_copy(
            update={"table_id": CP1_REFERENCES, "row_id": f"ref{index:02d}", "field": "value"}
        )
        for index, fact in enumerate(out.referenced.values(), 1)
    ]
    tables = list(out.tables)
    if referenced:
        tables.append(
            ReportTable(
                table_id=CP1_REFERENCES,
                title="CP-1 facts referenced in CP-3 text",
                columns=(TableColumn(field="value", label="Value"),),
                rows=tuple(
                    TableRow(
                        row_id=fact.row_id,
                        label=f"{fact.label} · {fact.period}" if fact.period else fact.label,
                        fact_ids=(fact.fact_id,),
                    )
                    for fact in referenced
                ),
                row_header="CP-1 fact",
            )
        )
    preference_row = submission.preference
    # Claims are the model's run text as written, each market claim with its bound citations;
    # references resolve against the carried CP-1 facts (`execution.candidate_issues`).
    claims = (
        Claim(
            claim_id="T3.4.preference",
            text=preference_row.rationale,
            citations=out.cited(preference_row.basis),
            limitation=preference_row.limitation,
        ),
        *(
            Claim(
                claim_id=f"T3.1.i{index:02d}",
                text=row.market_observation,
                citations=out.cited(row.basis),
                limitation=row.limitation,
            )
            for index, row in enumerate(submission.instruments, 1)
            if not _none(row.market_observation)
        ),
    )
    return RelativeValueReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=tuple(tables),
        facts=(*out.facts, *referenced),
        claims=claims,
        limitations=tuple(dict.fromkeys(out.limitations)),
    )


# --- the module and the journal ---------------------------------------------------------------


def cp3_module(report: RelativeValueReport, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-3 candidate: the report's tables and claims bound to `inputs`."""
    run = report.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=MODULE_ID,
        inputs=(
            *inputs,
            Input(input_id="relative-value-submission", sha256=report.submission_sha256),
        ),
        facts=report.facts,
        tables=report.tables,
        claims=report.claims,
        limitations=report.limitations,
        attempt=attempt,
    )


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    try:
        submission = RelativeValueSubmission.model_validate_json(
            store.payload(attempt.steps[0].payload_sha256)
        )
    except ValidationError as error:
        return StepValidation(issues=shape_issues(error))
    upstream = cp3_upstream(store, attempt)
    issues = validate_relative_value(pack, submission, upstream)
    if issues:
        return StepValidation(issues=issues)
    return StepValidation(output=relative_value(pack, submission, upstream).model_dump_json())


def submit_cp3_step(store: Execution, ticket_id: str, step_id: str, payload: str) -> Attempt:
    """Retain the one `relative_value` response, validate it, then settle CP-3 with the Python
    candidate (as `submit_cp2_step`): promotion is an accepted step and no validator issue. An
    invalid step finishes the attempt rejected (or blocked on the repair); there is no
    within-attempt repair. A crash after the step resumes from the retained step."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-3 has one step, {STEP_ID}")
    attempt = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if attempt is None or attempt.module_id != MODULE_ID or attempt.status != "pending":
        raise ValueError("Ticket is absent, finished or belongs to another module")
    if attempt.steps and attempt.steps[0].payload_sha256 != text_sha256(payload):
        raise ValueError("Ticket already retains a different response; resume or interrupt")
    if not attempt.steps or attempt.steps[0].status == "pending":
        attempt = store.submit_step(
            ticket_id,
            MODULE_ID,
            CP3_STEPS,
            STEP_ID,
            payload,
            lambda pack, current: _validate_step(store, pack, current),
        )
    if attempt.status == "finished":
        return attempt
    outcome = _validate_step(store, store.pack(), attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise ValueError("Retained CP-3 output differs from trusted validation")
    report = RelativeValueReport.model_validate_json(outcome.output or "")
    candidate = cp3_module(report, attempt.inputs, attempt.number)
    return store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP-3 candidate differs",),
        qualification=PROMOTED,
    )


def _market_note(third_party: bool, offered: ContextEvidence) -> str:
    """The CONTEXT block's note on where market evidence may come from."""
    if third_party:
        return (
            "Quote market evidence only from a source listed in market_evidence_sources; "
            "classify each quote observed or indicative_talk, never talk as a level."
        )
    if offered.rows:
        return CONTEXT_ONLY_NOTE
    return (
        "No third_party source: there is no market evidence, so the preference is "
        "Insufficient Information."
    )


def _context_caps(offered: ContextEvidence) -> list[str]:
    return [CONTEXT_CAP] if any(row.stale for row in offered.rows) else []


def _context_rows_block(pack: PreparedPack, offered: ContextEvidence) -> dict[str, object]:
    """`context_market_evidence` for a pack with a `context` source (none otherwise): the rows the
    model may cite by id (`basis.context_rows`); their figures are shown so it can choose, never
    to be copied. `provider` is the user's text."""
    if not any(source.source_id == CONTEXT_SOURCE for source in pack.sources):
        return {}
    rows = [
        {
            "row": row.row_id,
            "facility_id": row.facility_id,
            "kind": row.kind,
            "as_of": row.as_of or NOT_STATED,
            "provider": row.provider,
            "stale": row.stale is not None,
            "figures": row.figures,
        }
        for row in offered.rows
    ]
    return {"context_market_evidence": rows}


def context_block(pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """What the `relative_value` CONTEXT block adds to the pack facts, all Python's: the
    upstream statuses, the CP-1 facilities and the figures a reference may name, the CP-2 rows
    `cp2_refs` may cite, the read optional upstreams, the pack sources with CP-0's authority, the
    market-evidence catalogue (the `third_party` sources; empty without one), the confidence caps
    and the limitations settlement will inherit."""
    facts = referencable(upstream.cp1.facts)
    authority = {
        fact.row_id: fact.text
        for fact in upstream.cp0.facts
        if fact.table_id == "T3" and fact.field == "authority"
    }
    market = upstream.market_sources
    blocked = upstream.cp2_status == "blocked"
    offered = context_evidence(pack, upstream.facilities)
    block: dict[str, object] = {
        "upstream": [
            {"module_id": item.input_id, "status": item.status}
            for item in upstream.bound
            if item.input_id.startswith("CP-")
        ],
        "cp1_facilities": [
            {
                "facility_id": item.facility_id,
                "name": item.name,
                "terms": dict(item.terms),
                "figures": [fact.fact_id for fact in item.figures],
            }
            for item in upstream.facilities.values()
        ],
        "cp1_facilities_note": (
            "Name instruments only by a facility_id listed in cp1_facilities; order each exactly "
            "once in preference.ordering."
        ),
        "cp1_facts": [
            {
                "ref": fact.fact_id,
                "label": fact.label,
                "period": fact.period,
                "unit": figure_unit(fact) or fact.unit,
                "shown": spelled(fact),
            }
            for fact in facts
        ],
        "cp1_facts_note": (
            "Reference a figure only as {ref|unit} with a ref and unit listed in cp1_facts."
            if facts
            else "CP-1 offers no referencable figure: no figure may be referenced, so write no "
            "figure at all (labels only)."
        ),
        "cp2_rows": [
            {"ref": ref, "register": row.register, "row": row.label, "cells": dict(row.cells)}
            for ref, row in upstream.catalogue.items()
        ],
        "cp2_rows_note": (
            "CP-2 is blocked: no CP-2 row may be cited."
            if blocked
            else "Cite a CP-2 row only by listing its ref in cp2_refs; never restate it."
        ),
        "optional_upstream": [
            {
                "module_id": module_id,
                "status": upstream.optional_status(module_id),
                "limitations": list(
                    upstream.optional[module_id].limitations
                    if module_id in upstream.optional
                    else ()
                ),
            }
            for module_id in READ_OPTIONAL
        ],
        "pack_sources": [
            {
                "source_id": source.source_id,
                "name": source.name,
                "status": source.status,
                "authority": authority.get(source.source_id, "unassessed"),
            }
            for source in pack.sources
        ],
        "market_evidence_sources": [
            {"source_id": source.source_id, "name": source.name, "spans": len(source.spans)}
            for source in pack.sources
            if source.source_id in market and source.status == "ready"
        ],
        "market_evidence_note": _market_note(bool(market), offered),
        "confidence_caps": [*upstream.caps, *_context_caps(offered)],
        "inherited_limitations": list(upstream.inherited),
    }
    block.update(_context_rows_block(pack, offered))
    return block
