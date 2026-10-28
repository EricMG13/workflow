"""Stage 1 proof for CP-5 (integrity review): the reused engine `deploy_vii.cp5_integrity`,
called through `deploy_workflow.owners.cp5`, equals the frozen oracle
`cases/cp5-owner/expected.json` on the positive and gap literals and the twelve validator
refusals, and the owner view body meets the lease's construction and view assertions.

Every expected value is read from the oracle. The evaluated heads come from the oracles the CP-5
oracle names (`manifest.reuse.heads`): CP-1A and CP-2 from the S1 oracle
(`cases/snapshot/expected.json#positive`; CP-1A with the R6 table deltas of
`cases/cp3-cp6-owner/expected.json`), CP-3 from the CP-3 oracle. The oracles record citations as
(source_id, locator) only, so each quote comes from the pinned literal submissions: a claim keeps
its own literal citations, and a fact citation takes the first literal quote at the same source
and locator.

The CP-1 head is a genuine promotion in the run (`run_time_bindings`). This fixture stands in for
it: the four T4.10 LTM figures of `cases/financial/manifest.json`, two facility facts no claim
names, and the seven narrative claims (the oracle's ids and limitation; label-only text; one
citation each at the RT-3 source and locator, quoting one line of that page). The fixture's
binding replaces every run-time marker of the oracle.
"""

import copy
import dataclasses
import hashlib
import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii.contracts import (
    Citation,
    Claim,
    Fact,
    Input,
    Module,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
)
from deploy_vii.cp5_integrity import (
    KIND_LABEL,
    NOT_EVALUATED,
    IntegritySubmission,
    ReviewScope,
    python_checks,
)
from deploy_vii.live.context import integrity_projection
from deploy_vii.preparation import PreparedPack
from deploy_vii.quotes import prefix
from deploy_vii.readiness import shape_issues
from deploy_workflow.owners.cp5 import CP5Inputs, CP5Result, candidate, compute, view_body
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).parents[1]


def _load(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


EXPECTED: dict[str, Any] = _load("cases/cp5-owner/expected.json")
SUBMISSIONS: dict[str, Any] = _load("cases/cp5-owner/submissions.json")
MANIFEST: dict[str, Any] = _load("cases/cp5-owner/manifest.json")
S1_EXPECTED: dict[str, Any] = _load("cases/snapshot/expected.json")
S1_SUBMISSIONS: dict[str, Any] = _load("cases/snapshot/submissions.json")
SNAPSHOT: dict[str, Any] = _load("cases/snapshot/manifest.json")
C3_EXPECTED: dict[str, Any] = _load("cases/cp3-cp6-owner/expected.json")
C3_SUBMISSIONS: dict[str, Any] = _load("cases/cp3-cp6-owner/submissions.json")
C3_MANIFEST: dict[str, Any] = _load("cases/cp3-cp6-owner/manifest.json")
FINANCIAL: dict[str, Any] = _load("cases/financial/manifest.json")

CASES = ("positive", "gap")
CASE_IDS = {"positive": "cp5-positive", "gap": "cp5-gap"}
VIEW: dict[str, Any] = EXPECTED["view"]
S1P: dict[str, Any] = S1_EXPECTED["positive"]
FIG_RE = re.compile(r"\{\{FIG:([a-z_]+)\}\}")
LABEL_RE = re.compile(r"<label and period of FIG:([a-z_]+)>")
MARKER_RE = re.compile(r"\{\{[^{}]+\}\}")

# The LEAD freeze (docs/CP5-OWNER-LEASE.md, header): the oracle and its builder.
PINNED = {
    "cases/cp5-owner/manifest.json": "605a5baed84ff9e1fb5731f56de798af5812b4e6796622735339af64441acd91",
    "cases/cp5-owner/submissions.json": "9effec68a97a450ae87ee7d203b36e80ee9b315e052dce9db66b2d17c6a2b8a4",
    "cases/cp5-owner/expected.json": "48fcd8991b858b9b08fc12e965abfcde42d467dfce2aba04a98e9edba07e92d2",
    "cases/cp5-owner/builder/build.py": "60805bcf42e26b09598a36571fbee2ff8015f067b22bca559bacc665a02394d2",
}


def _sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def test_oracle_files_are_the_pinned_revision() -> None:
    for rel, digest in PINNED.items():
        assert _sha(rel) == digest, rel


def test_upstream_oracles_are_the_manifest_pins() -> None:
    """The S1 and CP-3 oracles the heads are read from are the revision the CP-5 oracle pins."""
    for rel, digest in MANIFEST["pins"].items():
        assert _sha(rel) == digest, rel


# --- the prepared pack ---------------------------------------------------------------------------


def _source_pages(source_id: str) -> tuple[list[dict[str, str]], str]:
    if source_id == "market":
        item = C3_MANIFEST["market_source"]
    elif source_id == "business":
        item = SNAPSHOT["business_source"]["positive"]
    else:
        item = next(s for s in FINANCIAL["sources"] if s["source_id"] == source_id)
    return item["pages"], item["sha256"]


def _case_entry(case: str) -> dict[str, Any]:
    return next(c for c in MANIFEST["cases"] if c["case_id"] == CASE_IDS[case])


@cache
def make_pack(case: str) -> PreparedPack:
    sources = []
    for item in _case_entry(case)["pack_sources"]:
        pages, sha = _source_pages(item["source_id"])
        spans = tuple(Span(locator=p["locator"], text=p["text"]) for p in pages)
        assert hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest() == sha
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status=item["status"],
                sha256=sha,
                spans=spans,
                extraction_status="complete",
                limitation=item["limitation"],
            )
        )
    run = Run.model_validate_json(json.dumps(_case_entry(case)["run"]))
    return PreparedPack(run=run, sources=tuple(sources))


def _citation(pack: PreparedPack, source_id: str, locator: str, quote: str) -> Citation:
    source = next(s for s in pack.sources if s.source_id == source_id)
    assert source.sha256 is not None
    return Citation(source_id=source_id, source_sha256=source.sha256, locator=locator, quote=quote)


def _literal_quotes(node: Any) -> Iterator[tuple[str, str, str]]:
    """Every (source_id, locator, quote) of a literal submission, in document order."""
    if isinstance(node, dict):
        if {"source_id", "locator", "quote"} <= node.keys() and isinstance(node["quote"], str):
            yield node["source_id"], node["locator"], node["quote"]
        for value in node.values():
            yield from _literal_quotes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _literal_quotes(value)


@cache
def _quote_index(case: str) -> Mapping[tuple[str, str], str]:
    """The first literal quote at each (source, locator): the CP-3 case literal, then the S1
    positive literal it builds on (`cases/cp3-cp6-owner/submissions.json` `business_context.base`)."""
    index: dict[tuple[str, str], str] = {}
    for literal in (C3_SUBMISSIONS[case], S1_SUBMISSIONS["positive"]):
        for source_id, locator, quote in _literal_quotes(literal):
            index.setdefault((source_id, locator), quote)
    return index


def _fact_citations(pack: PreparedPack, case: str, cites: Any) -> tuple[Citation, ...]:
    if not isinstance(cites, list):  # a cp1_references placeholder: bound below from CP-1
        return ()
    return tuple(
        _citation(pack, s, loc, _quote_index(case)[(s, loc)])
        for s, loc in (tuple(c) for c in cites)
    )


# --- the CP-1 stand-in -----------------------------------------------------------------------------

SYNTH = EXPECTED["positive"]["settled_limitations"][-1]
CP1_OWN = (
    "Fixture stand-in for the CP-1 head's own limitation, bound from the promotion at run time"
)
_T52 = next(t for t in EXPECTED["positive"]["tables"] if t["table_id"] == "T5.2")
# The limitation every CP-1 narrative claim carries (the T5.2 cell of the first CP-1 claim).
CP1_LIMITATION = next(r for r in _T52["rows"] if r["label"].startswith("CP-1 "))["facts"][2]["text"]
CP1_C1: dict[str, list[str]] = MANIFEST["run_time_bindings"]["RT-3"]["c1_source_locator"]
# One line of each RT-3 page, chosen by its opening words; the claim text is label-only.
CP1_CLAIMS: dict[str, tuple[str, str, str, str, str]] = {
    "leverage": (
        "Total debt",
        "Debt remains material",
        "Total leverage is {T4.10.total_leverage_reported.ltm_q4_2025|x} on reported EBITDA",
        "Debt obligations constrain financial flexibility",
        "Review earnings resilience alongside scheduled debt",
    ),
    "coverage": (
        "Net interest expense",
        "Cash interest consumes earnings",
        "Interest cover is {T4.10.interest_coverage_reported.ltm_q4_2025|x} on reported EBITDA",
        "Interest service competes with other cash uses",
        "Monitor available earnings for debt service",
    ),
    "cash_flow_quality": (
        "Levered free cash flow",
        "Operating cash supports maintenance spending",
        "Levered free cash flow is positive after maintenance capital expenditure",
        "Capital requirements reduce cash available to creditors",
        "Retain focus on cash conversion and distributions",
    ),
    "liquidity": (
        "Cash and cash equivalents",
        "Cash balances support flexibility",
        "Cash balances rise through the year",
        "Cash is available alongside contractual debt obligations",
        "Assess liquidity within the disclosed consolidated scope",
    ),
    "data_quality": (
        "Unaudited quarterly and reported",
        "Historical source remains unaudited",
        "The statements are unaudited",
        "Lack of assurance limits reliance on reported amounts",
        "Seek audited corroboration before stronger conclusions",
    ),
    "definition_risks": (
        "Reported EBITDA equals",
        "Historical EBITDA has a stated definition",
        "The source states how reported EBITDA is built",
        "Covenant definitions may differ from the reported measure",
        "Obtain executed covenant definitions for legal analysis",
    ),
    "key_gaps": (
        "No borrower, guarantor",
        "Perimeter evidence remains limited",
        "No borrower, guarantor or restricted perimeter is established",
        "Consolidated resources may differ from creditor-accessible resources",
        "Obtain borrower and guarantor scope evidence",
    ),
}


def fig_fact(name: str) -> Fact:
    """The CP-1 T4.10 LTM Q4 2025 fact of a figure: amount from the financial oracle; id, label,
    period and calculation id are this fixture's run-time binding (as the CP-3 Stage 1 test)."""
    ratio = FINANCIAL["q4_ltm_metric_oracle"][name]
    coordinate = S1_SUBMISSIONS["figures"][name]["cp1_coordinate"]
    basis, start_end = coordinate.split(", ", 1)[1].rsplit(", ", 1)
    start, end = start_end.split(" to ")
    return Fact(
        fact_id=f"T4.10.{name}.ltm_q4_2025",
        label=name,
        table_id="T4.10",
        row_id=name,
        field="ltm_q4_2025",
        amount=Decimal(ratio["numerator"]) / Decimal(ratio["denominator"]),
        unit=ratio["unit"],
        period=f"{basis}: {start} to {end}",
        calculation_id=f"calc.{name}.ltm_q4_2025",
        value_class="calculated",
    )


FIGS = {name: fig_fact(name) for name in S1_SUBMISSIONS["figures"]}


def _page_line(pack: PreparedPack, source_id: str, locator: str, opening: str) -> str:
    source = next(s for s in pack.sources if s.source_id == source_id)
    text = next(s.text for s in source.spans if s.locator == locator)
    (line,) = [x for x in text.splitlines() if x.startswith(opening)]
    return line


def _module(pack: PreparedPack, module_id: str, **fields: Any) -> Module:
    run = pack.run
    fields.setdefault("status", "restricted")
    return Module(
        run_id=run.run_id, issuer_id=run.issuer_id, as_of=run.as_of, module_id=module_id, **fields
    )


def make_cp1(pack: PreparedPack, case: str, cp0: Module) -> Module:
    facility = tuple(
        Fact(
            fact_id=f"T4.18.term-loan.fy2025.{field}",
            label=field,
            table_id="T4.18",
            row_id="term-loan.fy2025",
            field=field,
            text=text,
            citations=_fact_citations(pack, case, [["financial", "page:5"]]),
        )
        for field, text in (
            ("facility_id", "term-loan"),
            ("facility_name", "Northbridge Term Loan"),
        )
    )
    claims = []
    for claim_id, (opening, title, evidence, risk, credit) in CP1_CLAIMS.items():
        source_id, locator = CP1_C1[claim_id]
        quote = _page_line(pack, source_id, locator, opening)
        text = (
            f"{claim_id.replace('_', ' ').capitalize()} · {title}\n\nEvidence\n{evidence}"
            f"\n\nRisk mechanic\n{risk}\n\nCredit implication\n{credit}"
        )
        claims.append(
            Claim(
                claim_id=claim_id,
                text=text,
                citations=(_citation(pack, source_id, locator, quote),),
                limitation=CP1_LIMITATION,
            )
        )
    own = (CP1_OWN, SYNTH)
    return _module(
        pack,
        "CP-1",
        facts=(*FIGS.values(), *facility),
        claims=tuple(claims),
        limitations=own,
        inherited_limitations=tuple(t for t in cp0.limitations if t not in own),
    )


# --- the oracle heads ------------------------------------------------------------------------------


def _bound_text(text: str | None) -> str | None:
    if text is None:
        return None
    return LABEL_RE.sub(lambda m: f"{FIGS[m[1]].label} · {FIGS[m[1]].period}", text)


def _references(title: str, names: Sequence[str]) -> tuple[list[Fact], ReportTable]:
    """A `cp1_references` table: verbatim copies of the CP-1 facts (own fact_id, value class and
    citations; only table, row and field move)."""
    facts, rows = [], []
    for index, name in enumerate(names, 1):
        row_id = f"ref{index:02d}"
        source = FIGS[name]
        facts.append(
            source.model_copy(
                update={"table_id": "cp1_references", "row_id": row_id, "field": "value"}
            )
        )
        rows.append(
            TableRow(
                row_id=row_id, label=f"{source.label} · {source.period}", fact_ids=(source.fact_id,)
            )
        )
    table = ReportTable(
        table_id="cp1_references",
        title=title,
        columns=(TableColumn(field="value", label="Value"),),
        rows=tuple(rows),
        row_header="CP-1 fact",
    )
    return facts, table


def _tables(
    pack: PreparedPack, case: str, oracle: list[dict[str, Any]], references: Sequence[str]
) -> tuple[tuple[Fact, ...], tuple[ReportTable, ...]]:
    facts: list[Fact] = []
    tables: list[ReportTable] = []
    for table in oracle:
        if table["table_id"] == "cp1_references":
            copies, ref_table = _references(table["title"], references)
            assert [r["row_id"] for r in table["rows"]] == [r.row_id for r in ref_table.rows]
            facts += copies
            tables.append(ref_table)
            continue
        rows = []
        for row in table["rows"]:
            for cell, column in zip(row["facts"], table["columns"], strict=True):
                known = cell["status"] == "known"
                facts.append(
                    Fact(
                        fact_id=cell["fact_id"],
                        label=cell["column"],
                        table_id=table["table_id"],
                        row_id=row["row_id"],
                        field=column["field"],
                        text=_bound_text(cell["text"]) if known else None,
                        status=cell["status"],
                        value_class=cell["value_class"],
                        limitation=cell["limitation"],
                        citations=_fact_citations(pack, case, cell["cites"]),
                    )
                )
            rows.append(
                TableRow(
                    row_id=row["row_id"],
                    label=_bound_text(row["label"]) or row["label"],
                    fact_ids=tuple(c["fact_id"] for c in row["facts"]),
                )
            )
        tables.append(
            ReportTable(
                table_id=table["table_id"],
                title=table["title"],
                columns=tuple(TableColumn(**c) for c in table["columns"]),
                rows=tuple(rows),
                row_header=table["row_header"],
            )
        )
    return tuple(facts), tuple(tables)


def _inherited(spec: dict[str, Any], cp1: Module, own: Sequence[str]) -> tuple[str, ...]:
    """An oracle inherited-limitations spec (literal head, the bound CP-1 entries, literal tail),
    de-duplicated at first position, minus the head's own entries (execution.py:345-366)."""
    items = [
        *spec["literal_head"],
        *cp1.limitations,
        *cp1.inherited_limitations,
        *spec.get("literal_tail_after_CP-1", ()),
    ]
    return tuple(t for t in dict.fromkeys(items) if t not in own)


def _claim_citations(
    pack: PreparedPack, literal: Sequence[dict[str, str]], cites: Sequence[Sequence[str]]
) -> tuple[Citation, ...]:
    assert [[c["source_id"], c["locator"]] for c in literal] == [list(c) for c in cites]
    return tuple(_citation(pack, c["source_id"], c["locator"], c["quote"]) for c in literal)


def make_cp1a(pack: PreparedPack, case: str, cp1: Module, quote: str | None) -> Module:
    """The S1 positive CP-1A head with the CP-3 oracle's R6 table deltas (claims unchanged).
    `quote` replaces the first citation quote of claim r01 (a probe of the view only)."""
    delta = C3_EXPECTED[case]["upstream"]["CP-1A"]["R6"]
    assert delta["claims_unchanged"] is True
    oracle = []
    for table in copy.deepcopy(S1P["CP-1A"]["tables"]):
        ops = delta["tables"].get(table["table_id"], {})
        assert set(ops) <= {"replace_table", "append_row"}, ops
        if "replace_table" in ops:
            table = copy.deepcopy(ops["replace_table"])
        if "append_row" in ops:
            table["rows"].append(copy.deepcopy(ops["append_row"]))
        oracle.append(table)
    assert set(delta["tables"]) <= {t["table_id"] for t in oracle}
    facts, tables = _tables(pack, case, oracle, ())
    literal = S1_SUBMISSIONS["positive"]["business_context"]["credit_translations"]
    claims = []
    for index, (claim, row) in enumerate(zip(S1P["CP-1A"]["claims"], literal, strict=True), 1):
        assert claim["claim_id"] == f"credit_translation.r{index:02d}"
        citations = _claim_citations(pack, row["citations"], claim["cites"])
        if quote is not None and index == 1:
            citations = (citations[0].model_copy(update={"quote": quote}), *citations[1:])
        claims.append(
            Claim(
                claim_id=claim["claim_id"],
                text=claim["text"],
                citations=citations,
                limitation=claim["limitation"],
            )
        )
    own = tuple(S1P["CP-1A"]["settled_limitations"])
    spec = C3_EXPECTED[case]["upstream"]["CP-1A_inherited"]
    return _module(
        pack,
        "CP-1A",
        facts=facts,
        tables=tables,
        claims=tuple(claims),
        limitations=own,
        inherited_limitations=_inherited(spec, cp1, own),
    )


def _figure_refs(text: str) -> str:
    """`{{FIG:name}}` in head text: the run text reference `{<fact_id>|<unit_token>}`."""
    return FIG_RE.sub(
        lambda m: (
            "{" + FIGS[m[1]].fact_id + "|" + S1_SUBMISSIONS["figures"][m[1]]["unit_token"] + "}"
        ),
        text,
    )


def make_cp2(pack: PreparedPack, case: str, cp1: Module) -> Module:
    names = [f["name"] for f in S1P["CP-2"]["figures_referenced"]]
    facts, tables = _tables(pack, case, S1P["CP-2"]["tables"], names)
    claims = tuple(
        Claim(
            claim_id=c["claim_id"],
            text=_figure_refs(c["text"]),
            citations=(),
            limitation=c.get("limitation"),
        )
        for c in S1P["CP-2"]["claims"]
    )
    own = tuple(S1P["CP-2"]["settled_limitations_own"])
    spec = C3_EXPECTED[case]["upstream"]["CP-2"]["inherited"]
    return _module(
        pack,
        "CP-2",
        facts=facts,
        tables=tables,
        claims=claims,
        limitations=own,
        inherited_limitations=_inherited(spec, cp1, own),
    )


def _cp3_literal_citations(case: str, claim_id: str) -> list[dict[str, str]]:
    literal = C3_SUBMISSIONS[case]["relative_value"]
    if claim_id == "T3.4.preference":
        quotes: list[dict[str, str]] = literal["preference"]["basis"]["quotes"]
        return quotes
    (instrument,) = literal["instruments"]
    assert claim_id == "T3.1.i01" and instrument["facility_id"] == "term-loan"
    instrument_quotes: list[dict[str, str]] = instrument["basis"]["quotes"]
    return instrument_quotes


def make_cp3(pack: PreparedPack, case: str, cp1: Module) -> Module:
    head = C3_EXPECTED[case]["CP-3"]
    facts, tables = _tables(pack, case, head["tables"], head["cp1_references_order"])
    claims = tuple(
        Claim(
            claim_id=c["claim_id"],
            text=c["text"],
            citations=_claim_citations(
                pack, _cp3_literal_citations(case, c["claim_id"]), c["cites"]
            ),
            limitation=c["limitation"],
        )
        for c in head["claims"]
    )
    own = tuple(head["settled_limitations"])
    return _module(
        pack,
        "CP-3",
        facts=facts,
        tables=tables,
        claims=claims,
        limitations=own,
        inherited_limitations=_inherited(head["inherited_limitations"], cp1, own),
    )


# --- the review scope and the literal --------------------------------------------------------------


def _flatten(sequence: Sequence[dict[str, Any]], bound: Sequence[str]) -> tuple[str, ...]:
    """`inherited_limitations.sequence`: literal entries and the CP-1 bind marker, in order,
    de-duplicated at first position."""
    items: list[str] = []
    for segment in sequence:
        items += segment["literal"] if "literal" in segment else list(bound)
    return tuple(dict.fromkeys(items))


@dataclass(frozen=True)
class Fixture:
    case: str
    pack: PreparedPack
    heads: Mapping[str, Module]
    scope: ReviewScope

    @property
    def markers(self) -> dict[str, str]:
        """Every run-time marker of the oracle, bound to this fixture."""
        out = {"{{PACK_SHA256}}": self.pack.content_hash()}
        for item in self.scope.inputs:
            out["{{SHA256:" + item.input_id + "}}"] = item.sha256
            out["{{STATUS:" + item.input_id + "}}"] = item.status
        for name, fact in FIGS.items():
            out["{{FIG:" + name + "}}"] = fact.fact_id
        for claim in self.heads["CP-1"].claims:
            out["{{TRACE:CP-1 " + claim.claim_id + "}}"] = "; ".join(
                f"{claim.claim_id}#c{n} {c.source_id} {c.locator}"
                for n, c in enumerate(claim.citations, 1)
            )
        return out


@cache
def make_fixture(case: str, cp1a_quote: str | None = None) -> Fixture:
    pack = make_pack(case)
    cp0 = _module(
        pack, "CP-0", limitations=tuple(C3_EXPECTED[case]["upstream"]["CP-0"]["R6"]["limitations"])
    )
    cp1 = make_cp1(pack, case, cp0)
    heads = {
        "CP-0": cp0,
        "CP-1": cp1,
        "CP-1A": make_cp1a(pack, case, cp1, cp1a_quote),
        "CP-2": make_cp2(pack, case, cp1),
        "CP-3": make_cp3(pack, case, cp1),
    }
    bound = (
        Input(input_id="prepared-pack", sha256=pack.content_hash(), status="accepted"),
        *(Input(input_id=m, sha256=h.content_hash(), status=h.status) for m, h in heads.items()),
    )
    sequence = EXPECTED[case]["inherited_limitations"]["sequence"]
    scope = ReviewScope(
        pack=pack,
        inputs=bound,
        heads=tuple(
            (i, heads[i.input_id]) for i in bound if i.input_id in EXPECTED[case]["evaluated"]
        ),
        inherited=_flatten(sequence, (*cp1.limitations, *cp1.inherited_limitations)),
    )
    return Fixture(case=case, pack=pack, heads=heads, scope=scope)


def _instantiate(literal: Any) -> str:
    """The literal as JSON, each `{{FIG:name}}` replaced by the bound CP-1 fact_id (the fact_id of
    its verbatim CP-2 copy; submissions.json note)."""
    return FIG_RE.sub(lambda m: FIGS[m[1]].fact_id, json.dumps(literal))


def make_inputs(case: str, literal: Any = None) -> CP5Inputs:
    if literal is None:
        literal = SUBMISSIONS[case]
    return CP5Inputs(
        scope=make_fixture(case).scope,
        submission=IntegritySubmission.model_validate_json(_instantiate(literal)),
    )


def test_fixture_follows_the_oracle_sequence() -> None:
    """The inherited sequence without its CP-1 entries is the oracle's flattened list, and the
    fixture binds the CP-1 entries at the oracle's bind marker."""
    for case in CASES:
        spec = EXPECTED[case]["inherited_limitations"]
        assert list(_flatten(spec["sequence"], ())) == spec["flattened_without_bound_CP-1"]
        fixture = make_fixture(case)
        assert CP1_OWN in fixture.scope.inherited
        assert [m for m, _ in EXPECTED[case]["claims_to_review"]].count("CP-1") == len(CP1_CLAIMS)


# --- oracle comparison -----------------------------------------------------------------------------


def _bind(value: Any, markers: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return MARKER_RE.sub(lambda m: markers[m[0]], value)
    if isinstance(value, list):
        return [_bind(v, markers) for v in value]
    if isinstance(value, dict):
        return {k: _bind(v, markers) for k, v in value.items()}
    return value


def _cell(table_id: str, row_id: str, column: dict[str, str], text: str) -> dict[str, Any]:
    return {
        "fact_id": f"{table_id}.{row_id}.{column['field']}",
        "column": column["label"],
        "text": text,
        "status": "known",
        "cites": [],
        "value_class": None,
        "limitation": None,
    }


def _row(table: dict[str, Any], row_id: str, label: str, texts: Sequence[str]) -> dict[str, Any]:
    cells = [
        _cell(table["table_id"], row_id, c, t) for c, t in zip(table["columns"], texts, strict=True)
    ]
    return {"row_id": row_id, "label": label, "facts": cells}


def _bound_rows(
    table: dict[str, Any], rule: dict[str, Any], fixture: Fixture
) -> list[dict[str, Any]]:
    """The rows a `bound_rows` rule describes, written from the rule and the fixture's binding."""
    inherited = fixture.scope.inherited
    if table["table_id"] == "T5.5":
        members = sorted(rule["members"], key=lambda m: FIGS[m["figure"]].fact_id)
        return [
            _row(table, f"r{i:03d}", FIGS[m["figure"]].fact_id, m["cells"])
            for i, m in enumerate(members, 1)
        ]
    if table["table_id"] == "T5.8":
        assert rule["cells"] == ["Bound inputs", "<the entry text>"]
        return [
            _row(table, f"r{i:03d}", "Inherited limitation", ("Bound inputs", text))
            for i, text in enumerate(inherited, 1)
        ]
    assert table["table_id"] == "T5B.7" and rule["cells"] == ["<the entry text>", "Inherited"]
    first = rule["first_index"]
    assert len(table["rows"]) == first - 1
    return [
        _row(table, f"r{i:03d}", f"L{i:03d}", (text, "Inherited"))
        for i, text in enumerate(inherited, first)
    ]


def _expected_tables(fixture: Fixture) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = copy.deepcopy(EXPECTED[fixture.case]["tables"])
    for table in tables:
        rule = table.pop("bound_rows", None)
        if rule is not None:
            table["rows"] += _bound_rows(table, rule, fixture)
    bound: list[dict[str, Any]] = _bind(tables, fixture.markers)
    return bound


def _actual_tables(result: CP5Result) -> list[dict[str, Any]]:
    assert result.report is not None
    facts = {fact.fact_id: fact for fact in result.report.facts}
    return [
        {
            "table_id": table.table_id,
            "title": table.title,
            "row_header": table.row_header,
            "columns": [c.model_dump() for c in table.columns],
            "rows": [
                {
                    "row_id": row.row_id,
                    "label": row.label,
                    "facts": [
                        {
                            "fact_id": f.fact_id,
                            "column": f.label,
                            "text": f.text,
                            "status": f.status,
                            "cites": [[c.source_id, c.locator] for c in f.citations],
                            "value_class": f.value_class,
                            "limitation": f.limitation,
                        }
                        for f in (facts[i] for i in row.fact_ids)
                    ],
                }
                for row in table.rows
            ],
        }
        for table in result.report.tables
    ]


@pytest.fixture(scope="module", params=CASES)
def settled(request: pytest.FixtureRequest) -> tuple[str, CP5Inputs, CP5Result]:
    inputs = make_inputs(request.param)
    return request.param, inputs, compute(inputs)


def test_composes_without_issues(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    _, _, result = settled
    assert result.issues == ()
    assert result.report is not None


def test_tables_equal_oracle(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    case, _, result = settled
    assert _actual_tables(result) == _expected_tables(make_fixture(case))


def test_table_ids_are_the_registers(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    _, _, result = settled
    assert result.report is not None
    assert [t.table_id for t in result.report.tables] == EXPECTED["table_id_check"]["CP-5"]


def test_python_checks_find_nothing(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    """Over the fixture heads no mechanical check fires (`python_checks.expected_findings`);
    over the genuine CP-1 head this is the run-time assertion RT-2."""
    _, inputs, _ = settled
    assert (
        list(python_checks(inputs.scope).findings) == EXPECTED["python_checks"]["expected_findings"]
    )


def test_findings_status_and_limitations(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    case, inputs, result = settled
    expected = EXPECTED[case]
    assert result.report is not None
    assert list(result.report.findings) == expected["findings"]
    assert result.report.status == expected["report_status"]
    assert list(result.report.limitations) == expected["own_limitations"]
    assert [i.input_id for i in result.report.evaluated] == expected["evaluated"]
    outside = [i.input_id for i in inputs.scope.inputs if i.input_id in NOT_EVALUATED]
    assert outside == expected["not_evaluated"]
    assert len(SUBMISSIONS[case]["claim_reviews"]) == expected["claim_count"]


def test_candidate_module(settled: tuple[str, CP5Inputs, CP5Result]) -> None:
    case, inputs, result = settled
    assert result.report is not None
    module = candidate(result, inputs, attempt=1)
    assert module.module_id == "CP-5"
    assert [i.input_id for i in module.inputs] == EXPECTED[case]["module_inputs"]
    assert module.inputs[:-1] == inputs.scope.inputs
    assert module.inputs[-1].sha256 == inputs.submission.content_hash()
    assert module.attempt == 1
    assert module.claims == ()  # the head has no claims (lease, Acceptance)
    assert module.tables == result.report.tables and module.facts == result.report.facts
    assert list(module.limitations) == EXPECTED[case]["own_limitations"]


def test_candidate_of_a_refused_submission_raises() -> None:
    literal = copy.deepcopy(SUBMISSIONS["positive"])
    literal["gaps"][0]["affected_modules"] = ["CP-4"]
    inputs = make_inputs("positive", literal)
    result = compute(inputs)
    assert result.report is None
    with pytest.raises(ValueError, match="A refused CP-5 submission has no candidate"):
        candidate(result, inputs, attempt=0)


def test_scope_issues_refuse_the_review() -> None:
    """A stale or unreadable scope (`review_scope` issues) refuses the submission with exactly
    those issues (the engine's rule; the wording here is a probe, not an oracle value)."""
    inputs = make_inputs("positive")
    stale = CP5Inputs(
        scope=dataclasses.replace(inputs.scope, issues=("Stale inputs: probe",)),
        submission=inputs.submission,
    )
    result = compute(stale)
    assert result == CP5Result(issues=("Stale inputs: probe",), report=None)


# --- the owner view (lease, Owner view; expected.json view) ----------------------------------------


def _body(case: str) -> tuple[str, str, dict[str, Any]]:
    digest, body = view_body(make_fixture(case).scope)
    parsed: dict[str, Any] = json.loads(body)
    return digest, body, parsed


def _keys(items: Sequence[dict[str, Any]]) -> list[str]:
    shapes = {tuple(item) for item in items}
    assert len(shapes) == 1, shapes
    return list(shapes.pop())


def _strings(node: Any, skip: Any = None) -> Iterator[str]:
    """Every string value of the parsed body; `skip(path)` drops a subtree."""

    def walk(value: Any, path: tuple[Any, ...]) -> Iterator[str]:
        if skip is not None and skip(path, value):
            return
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for k, v in value.items():
                yield from walk(v, (*path, k))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                yield from walk(v, (*path, i))

    yield from walk(node, ())


def _keys_anywhere(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys_anywhere(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys_anywhere(v)


@pytest.mark.parametrize("case", CASES)
def test_view_key_tree(case: str) -> None:
    _, _, block = _body(case)
    modules = block["modules"]
    facts = [f for m in modules for f in m["facts"]]
    claims = [c for m in modules for c in m["claims"]]
    citations = [x for c in claims for x in c["citations"]]
    tree = {
        "top": list(block),
        "sources[*]": _keys(block["sources"]),
        "modules[*]": _keys(modules),
        "modules[*].facts[*]": _keys(facts),
        "modules[*].claims[*]": _keys(claims),
        "modules[*].claims[*].citations[*]": _keys(citations),
    }
    assert tree == VIEW["key_tree"]


@pytest.mark.parametrize("case", CASES)
def test_view_counts(case: str) -> None:
    _, _, block = _body(case)
    counts = VIEW["counts"][case]
    assert len(block["sources"]) == counts["sources"]
    assert len(block["modules"]) == counts["modules"]
    assert [m["module_id"] for m in block["modules"]] == counts["module_order"]
    assert block["claims_to_review"] == counts["claims_to_review"]
    assert block["claims_to_review"] == EXPECTED[case]["claims_to_review"]
    assert block["python_findings"] == counts["python_findings"]
    assert block["blocked_upstream"] == counts["blocked_upstream"]
    assert all(c["python_findings"] == [] for m in block["modules"] for c in m["claims"])
    assert block["inherited_limitations"] == list(make_fixture(case).scope.inherited)


@pytest.mark.parametrize("case", CASES)
def test_view_digest_and_compact_body(case: str) -> None:
    digest, body, block = _body(case)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    assert body == json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert view_body(make_fixture(case).scope) == (digest, body)  # recomputed, not remembered


def _exempt(path: tuple[Any, ...], value: Any, block: dict[str, Any]) -> bool:
    """CP-3's own T3.3 `*.quote` facts (`shown`, `text`, `label`): settled market-evidence facts,
    not citations (view.binding.no_quote)."""
    if (
        len(path) != 5
        or path[0] != "modules"
        or path[2] != "facts"
        or path[4] not in ("shown", "text", "label")
    ):
        return False
    module = block["modules"][path[1]]
    ref = module["facts"][path[3]]["ref"]
    return module["module_id"] == "CP-3" and re.fullmatch(r"T3\.3\.[^.]+\.quote", ref) is not None


def _citation_quotes(scope: ReviewScope) -> set[str]:
    return {
        c.quote
        for _, head in scope.heads
        for record in (*head.claims, *head.facts)
        for c in record.citations
    }


@pytest.mark.parametrize("case", CASES)
def test_view_carries_no_quote(case: str) -> None:
    fixture = make_fixture(case)
    _, _, block = _body(case)
    assert "quote" not in set(_keys_anywhere(block))
    quotes = _citation_quotes(fixture.scope)
    assert quotes  # the heads do cite
    shown = list(_strings(block, lambda p, v: _exempt(p, v, block)))
    leaked = sorted(q for q in quotes if any(q in s for s in shown))
    assert leaked == []
    if case == "positive":  # the exempt facts equal the CP-3 claims' citation quotes (F1)
        cp3 = next(m for m in block["modules"] if m["module_id"] == "CP-3")
        exempt = {f["shown"] for f in cp3["facts"] if f["ref"].startswith("T3.3.")}
        claims = fixture.heads["CP-3"].claims
        assert {c.quote for claim in claims for c in claim.citations} <= exempt


@pytest.mark.parametrize("case", CASES)
def test_view_fact_projection(case: str) -> None:
    """CP-1 lists exactly what `integrity_projection` keeps; every other head lists every fact."""
    fixture = make_fixture(case)
    _, _, block = _body(case)
    listed = {m["module_id"]: [f["ref"] for f in m["facts"]] for m in block["modules"]}
    kept = integrity_projection(fixture.scope)
    for module_id, head in fixture.heads.items():
        if module_id not in listed:
            continue
        if module_id == "CP-1":
            assert listed[module_id] == [f.fact_id for f in kept(head)]
            assert sorted(listed[module_id]) == sorted(f.fact_id for f in FIGS.values())
            assert len(head.facts) > len(listed[module_id])  # the facility facts are left out
        else:
            assert listed[module_id] == [f.fact_id for f in head.facts]


@pytest.mark.parametrize("case", CASES)
def test_view_lists_every_literal_upstream_ref(case: str) -> None:
    _, _, block = _body(case)
    named: dict[str, set[str]] = {
        m["module_id"]: {f["ref"] for f in m["facts"]}
        | {x["ref"] for c in m["claims"] for x in c["citations"]}
        for m in block["modules"]
    }
    submission = json.loads(_instantiate(SUBMISSIONS[case]))
    for review in submission["claim_reviews"]:
        for ref in review["upstream_refs"]:
            assert ref in named[review["producer_module"]], (review["claim_ref"], ref)


def test_view_refuses_a_scope_with_issues() -> None:
    scope = dataclasses.replace(make_fixture("positive").scope, issues=("Stale inputs: probe",))
    with pytest.raises(WorkflowError, match="^identity_mismatch$"):
        view_body(scope)


def _failing_view(quote: str) -> tuple[ReviewScope, dict[str, Any], str]:
    scope = make_fixture("positive", cp1a_quote=quote).scope
    _, body = view_body(scope)
    return scope, json.loads(body), body


def test_view_withholds_finding_detail() -> None:
    """A citation finding's detail carries a quote prefix; the view keeps kind and where only
    (ruling 3). Not an oracle case: no mechanical finding fires on the frozen heads."""
    quote = "This sentence is not on the cited business page"
    scope, block, body = _failing_view(quote)
    findings = python_checks(scope).findings
    assert [f.kind for f in findings] == ["claim_citation"]
    assert prefix(quote) in findings[0].detail
    assert block["python_findings"] == [f"{KIND_LABEL[f.kind]}: {f.where}" for f in findings]
    cp1a = next(m for m in block["modules"] if m["module_id"] == "CP-1A")
    marks = {c["claim_id"]: c["python_findings"] for c in cp1a["claims"]}
    assert marks["credit_translation.r01"] == ["claim_citation"]
    assert all(
        ": " not in mark
        for m in block["modules"]
        for c in m["claims"]
        for mark in c["python_findings"]
    )
    assert prefix(quote) not in body and quote not in body


@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(alphabet="bcdfghjklmnpqrstvwxz", min_size=6, max_size=40))
def test_property_a_failing_quote_never_reaches_the_view(word: str) -> None:
    """For any quote that does not hold, the body holds neither the quote nor its prefix."""
    quote = f"Probe {word} quote"
    _, block, body = _failing_view(quote)
    assert len(block["python_findings"]) == 1
    assert quote not in body and prefix(quote) not in body


# --- validator refusals (expected.json refusals.validator_refusals) --------------------------------

REFUSALS = EXPECTED["refusals"]["validator_refusals"]
MUTATIONS = {m["id"]: m["op"] for m in SUBMISSIONS["refusal_mutations"]}


def apply_op(literal: Any, op: dict[str, Any]) -> Any:
    out = copy.deepcopy(literal)
    ((name, args),) = op.items()
    if name in ("remove_review", "duplicate_review"):
        key = tuple(args)
        match = [r for r in out["claim_reviews"] if (r["producer_module"], r["claim_ref"]) == key]
        assert len(match) == 1, key
        if name == "remove_review":
            out["claim_reviews"].remove(match[0])
        else:
            out["claim_reviews"].append(copy.deepcopy(match[0]))
        return out
    path, value = args
    target = out
    for part in path[:-1]:
        target = target[part]
    if name == "set":
        target[path[-1]] = copy.deepcopy(value)
    elif name == "append":
        target[path[-1]].append(value)
    else:
        raise AssertionError(f"unknown op {name}")
    return out


def test_every_refusal_has_a_mutation() -> None:
    assert len(REFUSALS) == 12
    assert [r["id"] for r in REFUSALS] == list(MUTATIONS)
    assert all(r["case"] == "positive" and r["owner"] == "CP-5" for r in REFUSALS)


@pytest.mark.parametrize("entry", REFUSALS, ids=[r["id"] for r in REFUSALS])
def test_validator_refusal(entry: dict[str, Any]) -> None:
    literal = apply_op(SUBMISSIONS[entry["case"]], MUTATIONS[entry["id"]])
    if "issues_contains" in entry:
        with pytest.raises(ValidationError) as error:
            IntegritySubmission.model_validate_json(_instantiate(literal))
        issues = shape_issues(error.value)
        for wanted in entry["issues_contains"]:
            assert any(issue.startswith(wanted) for issue in issues), issues
        return
    result = compute(make_inputs(entry["case"], literal))
    assert result.report is None
    assert list(result.issues) == entry["issues"]
