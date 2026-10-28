"""Stage 1 proof for CP-3 (relative value): the reused engine, called through
`deploy_workflow.owners.cp3.compute`, equals the frozen oracle `cases/cp3-cp6-owner/expected.json`
on the positive and gap literals, the blocked-CP-1A variant and the CP-3 validator refusals.

Every expected value is read from the oracle. Inputs come from the oracle's own sources:
the pack from the source manifests, CP-0 authority from `upstream.CP-0.R3.facts`, CP-2 rows from
the S1 oracle (`cases/snapshot/expected.json#positive.CP-2`, which the CP-3 oracle names as
unchanged) and CP-1 figures from `cases/financial/manifest.json` `q4_ltm_metric_oracle`. CP-1
fact ids, labels and periods are run-time bindings in the oracle (`run_time_bindings`); this
Stage 1 fixture fixes them once and substitutes them into the oracle's placeholders.
"""

import copy
import dataclasses
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import (
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
from deploy_vii.cp3_relative_value import RelativeValueSubmission
from deploy_vii.cp6_committee import cp3_catalogue
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners.cp3 import CP3Inputs, CP3Result, candidate, compute, context

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp3-cp6-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
FINANCIAL: dict[str, Any] = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAPSHOT: dict[str, Any] = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
S1_EXPECTED: dict[str, Any] = json.loads((ROOT / "cases/snapshot/expected.json").read_text())

CASE_IDS = {"positive": "cp3-cp6-positive", "gap": "cp3-cp6-gap"}
CP2_REGISTERS = ("T2.1", "T2.7", "T2.10", "T2.11", "T2.12")
FIG_RE = re.compile(r"\{\{FIG:([a-z_]+)\}\}")
PLACEHOLDER_RE = re.compile(r"<label and period of FIG:([a-z_]+)>")


# Oracle pins: cases/PINS.json, the shared manifest LEAD regenerates (python3 -I cases/pins.py).
PINS: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
PINNED = ("manifest.json", "submissions.json", "expected.json", "builder/build.py")


def test_oracle_files_are_the_pinned_revision() -> None:
    for name in PINNED:
        digest = hashlib.sha256((CASE / name).read_bytes()).hexdigest()
        assert digest == PINS[f"cases/cp3-cp6-owner/{name}"], name


# --- inputs from the oracle's sources ------------------------------------------------------------


def _pages(source_id: str) -> tuple[list[dict[str, str]], str]:
    if source_id == "market":
        market = MANIFEST["market_source"]
        return market["pages"], market["sha256"]
    if source_id == "business":
        business = SNAPSHOT["business_source"]["positive"]
        return business["pages"], business["sha256"]
    item = next(s for s in FINANCIAL["sources"] if s["source_id"] == source_id)
    return item["pages"], item["sha256"]


def make_pack(case: str) -> PreparedPack:
    entry = next(c for c in MANIFEST["cases"] if c["case_id"] == CASE_IDS[case])
    sources = []
    for item in entry["pack_sources"]:
        pages, sha = _pages(item["source_id"])
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
    run = Run.model_validate_json(json.dumps(entry["runs"]["R3"]["run"]))
    return PreparedPack(run=run, sources=tuple(sources))


def _module(pack: PreparedPack, module_id: str, **fields: Any) -> Module:
    run = pack.run
    fields.setdefault("status", "restricted")
    fields.setdefault("limitations", ("Synthetic case; not real issuer qualification",))
    return Module(
        run_id=run.run_id, issuer_id=run.issuer_id, as_of=run.as_of, module_id=module_id, **fields
    )


def make_cp0(pack: PreparedPack, case: str) -> Module:
    """CP-0's T3 authority cells, from `upstream.CP-0.R3.facts` (the cells CP-3 reads)."""
    facts = []
    for item in EXPECTED[case]["upstream"]["CP-0"]["R3"]["facts"]:
        table_id, row_id, field = item["fact_id"].split(".")
        if table_id == "T3" and field == "authority":
            facts.append(
                Fact(
                    fact_id=item["fact_id"],
                    label="Authority",
                    table_id=table_id,
                    row_id=row_id,
                    field=field,
                    text=item["text"],
                )
            )
    return _module(pack, "CP-0", facts=tuple(facts))


def fig_fact(name: str) -> Fact:
    """The CP-1 T4.10 LTM Q4 2025 fact for a figure: amount from the financial oracle; id, label,
    period and calculation id are this fixture's run-time binding."""
    ratio = FINANCIAL["q4_ltm_metric_oracle"][name]
    coordinate = SUBMISSIONS["figures"][name]["cp1_coordinate"]
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


FIGS = {name: fig_fact(name) for name in SUBMISSIONS["figures"]}


def make_cp1(pack: PreparedPack) -> Module:
    """CP-1's referencable figures and the T4.18 facility cells (`run_time_bindings.facility`)."""
    facility = tuple(
        Fact(
            fact_id=f"T4.18.term-loan.fy2025.{field}",
            label=field,
            table_id="T4.18",
            row_id="term-loan.fy2025",
            field=field,
            text=text,
        )
        for field, text in (
            ("facility_id", "term-loan"),
            ("facility_name", "Northbridge Term Loan"),
        )
    )
    return _module(pack, "CP-1", facts=(*FIGS.values(), *facility))


def make_cp2(pack: PreparedPack) -> Module:
    """The CP-2 register tables of the S1 positive oracle (unchanged for CP-3)."""
    tables, facts = [], []
    for table in S1_EXPECTED["positive"]["CP-2"]["tables"]:
        if table["table_id"] not in CP2_REGISTERS:
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
                        text=cell["text"] if known else None,
                        status=cell["status"],
                        value_class=cell["value_class"],
                        limitation=cell["limitation"],
                    )
                )
            rows.append(
                TableRow(
                    row_id=row["row_id"],
                    label=row["label"],
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
    return _module(pack, "CP-2", facts=tuple(facts), tables=tuple(tables))


def make_cp1a(pack: PreparedPack, case: str, *, blocked: bool) -> Module:
    """What CP-3 reads of CP-1A: status and limitations (CONTEXT `optional_upstream`). A blocked
    head's limitations are bound at run time; the fixture marks that."""
    if blocked:
        return _module(
            pack,
            "CP-1A",
            status="blocked",
            limitations=("Stage 1 fixture: the blocked CP-1A head's issue texts bind at run time",),
        )
    optional = EXPECTED[case]["CP-3"]["context_block_checks"]["optional_upstream"]
    limits = next(o["limitations"] for o in optional if o["module_id"] == "CP-1A")
    return _module(pack, "CP-1A", limitations=tuple(limits))


def _instantiate(value: Any) -> str:
    """The literal as JSON, each `{{FIG:name}}` replaced by `{<fact_id>|<unit_token>}`
    (submissions.json note)."""

    def ref(match: re.Match[str]) -> str:
        name = match[1]
        unit = str(SUBMISSIONS["figures"][name]["unit_token"])
        return "{" + FIGS[name].fact_id + "|" + unit + "}"

    return FIG_RE.sub(ref, json.dumps(value))


def make_inputs(case: str, literal: Any = None, *, blocked_cp1a: bool = False) -> CP3Inputs:
    pack = make_pack(case)
    heads = {
        "CP-0": make_cp0(pack, case),
        "CP-1": make_cp1(pack),
        "CP-1A": make_cp1a(pack, case, blocked=blocked_cp1a),
        "CP-2": make_cp2(pack),
    }
    bound = (
        Input(input_id="prepared-pack", sha256=pack.content_hash(), status="accepted"),
        *(
            Input(
                input_id=module_id,
                sha256=head.content_hash(),
                status="blocked" if module_id == "CP-1A" and blocked_cp1a else "restricted",
            )
            for module_id, head in heads.items()
        ),
    )
    if literal is None:
        literal = SUBMISSIONS[case]["relative_value"]
    return CP3Inputs(
        pack=pack,
        submission=RelativeValueSubmission.model_validate_json(_instantiate(literal)),
        bound=bound,
        current=bound,
        cp0=heads["CP-0"],
        cp1=heads["CP-1"],
        cp2=heads["CP-2"],
        optional={"CP-1A": heads["CP-1A"]},
        inherited=(),
    )


# --- oracle comparison ---------------------------------------------------------------------------


def _bound_text(text: str | None) -> str | None:
    """Substitute the oracle's CP-1 label placeholders with the fixture binding."""
    if text is None:
        return None

    def label(match: re.Match[str]) -> str:
        fact = FIGS[match[1]]
        return f"{fact.label} · {fact.period}"

    return PLACEHOLDER_RE.sub(label, text)


def _cell(fact: Fact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "column": fact.label,
        "text": fact.text,
        "status": fact.status,
        "cites": [[c.source_id, c.locator] for c in fact.citations],
        "value_class": fact.value_class,
        "limitation": fact.limitation,
    }


def _actual_tables(result: CP3Result) -> list[dict[str, Any]]:
    assert result.report is not None
    facts = {fact.fact_id: fact for fact in result.report.facts}
    out = []
    for table in result.report.tables:
        rows: list[dict[str, Any]] = []
        for row in table.rows:
            item: dict[str, Any] = {"row_id": row.row_id, "label": row.label}
            if table.table_id != "cp1_references":  # the oracle binds these facts at run time
                item["facts"] = [_cell(facts[i]) for i in row.fact_ids]
            rows.append(item)
        out.append(
            {
                "table_id": table.table_id,
                "title": table.title,
                "row_header": table.row_header,
                "columns": [c.model_dump() for c in table.columns],
                "rows": rows,
            }
        )
    return out


def _expected_tables(case: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = copy.deepcopy(EXPECTED[case]["CP-3"]["tables"])
    for table in tables:
        for row in table["rows"]:
            row["label"] = _bound_text(row["label"])
            row.pop("fact_binding", None)
            for fact in row.get("facts", []):
                fact["text"] = _bound_text(fact["text"])
    return tables


@pytest.fixture(scope="module", params=["positive", "gap"])
def settled(request: pytest.FixtureRequest) -> tuple[str, CP3Inputs, CP3Result]:
    inputs = make_inputs(request.param)
    return request.param, inputs, compute(inputs)


def test_composes_without_issues(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    _, _, result = settled
    assert result.issues == ()
    assert result.report is not None


def test_tables_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert _actual_tables(result) == _expected_tables(case)


def test_cp1_references_bind_cp1_facts(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    order = EXPECTED[case]["CP-3"]["cp1_references_order"]
    table = next(t for t in result.report.tables if t.table_id == "cp1_references")
    facts = {fact.fact_id: fact for fact in result.report.facts}
    assert [r.row_id for r in table.rows] == [f"ref{i:02d}" for i in range(1, len(order) + 1)]
    for row, name in zip(table.rows, order, strict=True):
        (fact_id,) = row.fact_ids
        fact, source = facts[fact_id], FIGS[name]
        assert fact.fact_id == source.fact_id
        assert fact.value_class == "calculated"
        assert fact.citations == source.citations
        assert (fact.table_id, fact.row_id, fact.field) == ("cp1_references", row.row_id, "value")
        moved = {"table_id", "row_id", "field"}
        assert fact.model_dump(exclude=moved) == source.model_dump(exclude=moved)


def test_figures_spelled_as_pinned(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    _, _, result = settled
    assert result.report is not None
    view = next(f for f in result.report.facts if f.fact_id == "T3.1.i01.fundamental_view")
    for name in ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported"):
        assert SUBMISSIONS["figures"][name]["spelled"] in (view.text or "")


def test_claims_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    actual = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in result.report.claims
    ]
    assert actual == EXPECTED[case]["CP-3"]["claims"]


def test_own_limitations_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    assert list(result.report.limitations) == EXPECTED[case]["CP-3"]["own_limitations"]


def test_catalogue_for_cp6(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    """The CP-3 rows CP-6 may cite (`cp6_committee.cp3_catalogue` over the candidate), by ref
    and row label, equal the oracle's catalogue in order."""
    case, inputs, result = settled
    catalogue = cp3_catalogue(candidate(result, inputs, attempt=0))
    actual = [(ref, row.label) for ref, row in catalogue.items()]
    assert actual == list(EXPECTED[case]["CP-3"]["catalogue_for_CP-6"].items())


def test_module_inputs(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, inputs, result = settled
    module = candidate(result, inputs, attempt=0)
    assert [i.input_id for i in module.inputs] == EXPECTED[case]["CP-3"]["module_inputs"]
    assert module.module_id == "CP-3"


def _rows(block: dict[str, object], key: str) -> list[dict[str, Any]]:
    """A list-valued CONTEXT entry, typed for the comparisons below."""
    value = block[key]
    assert isinstance(value, list)
    return value


def _upstream_statuses(block: dict[str, object]) -> dict[str, str]:
    return {u["module_id"]: u["status"] for u in _rows(block, "upstream")}


def test_context_block_checks(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, inputs, _ = settled
    checks = EXPECTED[case]["CP-3"]["context_block_checks"]
    block = context(inputs)
    assert _upstream_statuses(block) == checks["upstream_statuses"]
    assert [(f["facility_id"], f["name"]) for f in _rows(block, "cp1_facilities")] == [
        (f["facility_id"], f["name"]) for f in checks["cp1_facilities"]
    ]
    assert [r["ref"] for r in _rows(block, "cp2_rows")] == checks["cp2_rows"]
    assert block["optional_upstream"] == checks["optional_upstream"]
    assert block["market_evidence_sources"] == checks["market_evidence_sources"]
    assert block["market_evidence_note"] == checks["market_evidence_note"]
    assert block["confidence_caps"] == checks["confidence_caps"]
    authority = {s["source_id"]: s["authority"] for s in _rows(block, "pack_sources")}
    assert authority == checks["pack_source_authority"]


# --- blocked CP-1A variant (oracle positive.CP-3.blocked_cp1a_variant) ---------------------------


def test_blocked_cp1a_variant() -> None:
    variant = EXPECTED["positive"]["CP-3"]["blocked_cp1a_variant"]
    inputs = make_inputs("positive", blocked_cp1a=True)
    result = compute(inputs)
    assert result.issues == ()
    assert result.report is not None
    assert list(result.report.limitations) == variant["own_limitations"]
    assert _actual_tables(result) == _expected_tables("positive")
    module = candidate(result, inputs, attempt=0)
    assert [i.input_id for i in module.inputs] == variant["module_inputs"]
    statuses = {i.input_id: i.status for i in inputs.bound if i.input_id.startswith("CP-")}
    assert statuses == variant["input_statuses"]
    checks = variant["context_block_checks"]
    block = context(inputs)
    assert _upstream_statuses(block) == checks["upstream_statuses"]
    assert [(o["module_id"], o["status"]) for o in _rows(block, "optional_upstream")] == [
        (o["module_id"], o["status"]) for o in checks["optional_upstream"]
    ]
    assert block["confidence_caps"] == checks["confidence_caps"]


# --- validator refusals (oracle refusals.validator_refusals, CP-3 entries) -----------------------

CP3_REFUSALS = [e for e in EXPECTED["refusals"]["validator_refusals"] if e["owner"] == "CP-3"]
MUTATIONS = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}
PATH_RE = re.compile(r"([a-z0-9_]+)(?:\[(\d+)\])?")


def _walk(root: Any, path: str) -> tuple[Any, str | int]:
    parts: list[str | int] = []
    for segment in path.split("."):
        match = PATH_RE.fullmatch(segment)
        assert match is not None, segment
        parts.append(match[1])
        if match[2] is not None:
            parts.append(int(match[2]))
    node = root
    for part in parts[:-1]:
        node = node[part]
    return node, parts[-1]


def mutate(literal: Any, edits: list[list[Any]]) -> Any:
    out = copy.deepcopy(literal)
    for op, path, value in edits:
        node, key = _walk(out, path)
        if op == "set":
            node[key] = [node[key][1]] if value == "ROW1_ONLY" else copy.deepcopy(value)
        elif op == "append_text":
            node[key] = node[key] + value
        else:
            raise AssertionError(f"unknown edit {op}")
    return out


def test_every_cp3_refusal_has_a_mutation() -> None:
    assert len(CP3_REFUSALS) == 10
    owned = {m["id"] for m in MUTATIONS.values() if m["owner"] == "CP-3"}
    assert {e["id"] for e in CP3_REFUSALS} == owned


@pytest.mark.parametrize("entry", CP3_REFUSALS, ids=[e["id"] for e in CP3_REFUSALS])
def test_validator_refusal(entry: dict[str, Any]) -> None:
    mutation = MUTATIONS[entry["id"]]
    assert mutation["case"] == entry["case"]
    literal = mutate(SUBMISSIONS[entry["case"]]["relative_value"], mutation["edits"])
    result = compute(make_inputs(entry["case"], literal))
    assert result.report is None
    assert any(entry["issue_contains"] in issue for issue in result.issues), result.issues


def test_current_inputs_reach_the_engine() -> None:
    """`current` is an operand, not decoration: a current input set that differs from the bound
    one refuses the submission (wording is the engine's; not an oracle value, so not pinned)."""
    inputs = make_inputs("positive")
    stale = dataclasses.replace(inputs, current=inputs.bound[:-1])
    result = compute(stale)
    assert result.report is None
    assert result.issues
