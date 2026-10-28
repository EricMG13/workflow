"""A3 synthetic component previews, never owner/receipt/CP5/native acceptance."""

import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii import report_view
from deploy_vii.bindings import Binding, BindingMap, validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Citation,
    Fact,
    ModuleView,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
)
from deploy_vii.render import empty_view, render
from deploy_vii.report_view import FactCoord, build, pathways

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "cases/earnings/render-expected.json").read_text())
MANIFEST = json.loads((ROOT / "cases/financial/manifest.json").read_text())
FIXTURE_HASH = hashlib.sha256(b"A3 seeded CP1B component preview; no execution").hexdigest()
UPSTREAM_FIXTURE_HASH = hashlib.sha256(
    b"A3 named CP1 fixture reference, not a settled head"
).hexdigest()
LAYOUTS = {item["table_id"]: item for item in ORACLE["layout"]["tables"]}
LIMITATIONS = tuple(ORACLE["limitations_surface"]["required_semantics"])


def _citation(measure):
    prefixes = {
        "revenue": ("page:2", "Revenue  "),
        "ebitda": ("page:2", "Reported EBITDA  "),
        "adjusted_ebitda": ("page:2", "Adjusted EBITDA  "),
        "ebitda_margin": ("page:2", "Reported EBITDA  "),
        "cfo_reported": ("page:3", "Operating cash flow  "),
        "capex": ("page:3", "Total capital expenditure  "),
        "fcf": ("page:3", "Levered free cash flow  "),
        "cash_closing": ("page:4", "Cash and cash equivalents  "),
        "total_debt": ("page:4", "Total debt  "),
        "net_debt": ("page:4", "Total debt  "),
    }
    locator, prefix = prefixes.get(measure, ("page:1", "This source reports four"))
    source = next(s for s in MANIFEST["sources"] if s["source_id"] == "financial")
    page = next(p for p in source["pages"] if p["locator"] == locator)
    quote = next(line for line in page["text"].splitlines() if line.startswith(prefix))
    return Citation(
        source_id="financial", source_sha256=source["sha256"], locator=locator, quote=quote
    )


def _fixture_input_evidence(case_name):
    """Opaque supplied text: synthetic handles, not a production operand schema."""
    expected = ORACLE[case_name]
    measures = {row["row_id"]: row for table in expected["tables"] for row in table["rows"]}
    points = []
    for measure in (*measures, "total_leverage_reported", "net_leverage_reported"):
        roles = {}
        for role in ("prior", "current"):
            period = expected[f"{role}_period_id"]
            absent = case_name == "gap" and role == "prior"
            leverage = measure.endswith("leverage_reported")
            if leverage:
                value = (
                    (
                        "1.6666666666666666666666666666666666667"
                        if measure == "total_leverage_reported"
                        else "1"
                    )
                    if role == "current"
                    else None
                )
                status = "known" if role == "current" else "missing"
                unit, currency, scale = "MULTIPLE", None, "1"
                reason = (
                    None
                    if role == "current"
                    else (
                        "COMPARATIVE_NOT_SUPPLIED"
                        if absent
                        else "Four complete quarters not supplied"
                    )
                )
            else:
                cell = next(c for c in measures[measure]["cells"] if c["field"] == role)
                value, status = cell["value"], cell["status"]
                unit, currency, scale = cell["unit"], cell["currency"], cell["scale"]
                reason = cell["reason_contains"]
            roles[role] = {
                "requested_period_id": period,
                "trailing_denominator": (
                    {
                        "fact_id": f"fixture-primary:{period}:trailing-ebitda",
                        "value": "30",
                        "basis_id": f"fixture-trailing-basis:{period}",
                        "citations": [_citation("ebitda").model_dump(mode="json")],
                    }
                    if leverage and role == "current"
                    else None
                ),
                "input_operand_fact_ids": (
                    [
                        f"fixture-primary:{period}:{name}"
                        for name in (
                            ("total_debt", "trailing-ebitda")
                            if measure == "total_leverage_reported"
                            else ("total_debt", "cash_closing", "trailing-ebitda")
                        )
                    ]
                    if leverage and role == "current"
                    else []
                ),
                "primary_fact_id": None if absent else f"fixture-primary:{period}:{measure}",
                "companion_fact_ids": []
                if absent
                else [f"fixture-companion:{period}:{measure}:period_id"],
                "basis_id": None if absent else f"fixture-basis:{period}",
                "status": status,
                "value": value,
                "unit": unit,
                "currency": currency,
                "scale": scale,
                "reason": reason,
                "citations": [] if absent else [_citation(measure).model_dump(mode="json")],
            }
        points.append({"measure": measure, "roles": roles})
    return {
        "scope": "component fixture; synthetic handles only; no actual owner/settlement/grant authentication",
        "selected_cp1_artifact_sha256": UPSTREAM_FIXTURE_HASH,
        "requested_pair": [expected["prior_period_id"], expected["current_period_id"]],
        "points": points,
    }


def _seed(case_name="positive", *, status="candidate"):
    """Seed independent oracle literals directly; no producer/registry/tool monkeypatch."""
    expected = ORACLE[case_name]
    facts, tables = [], []
    pair = f"{expected['prior_period_id']}->{expected['current_period_id']}"
    for table in expected["tables"]:
        layout = LAYOUTS[table["table_id"]]
        rows = []
        for row, row_layout in zip(table["rows"], layout["rows"], strict=True):
            for cell in row["cells"]:
                field = cell["field"]
                derived = field in {"delta", "growth"}
                amount = None if cell["value"] is None else Decimal(cell["value"])
                facts.append(
                    Fact(
                        fact_id=cell["fact_id"],
                        label=f"{row_layout['label']} · {field}",
                        table_id=table["table_id"],
                        row_id=row["row_id"],
                        field=field,
                        amount=amount,
                        status=cell["status"],
                        unit=cell["unit"],
                        currency=cell["currency"],
                        scale=Decimal(cell["scale"]),
                        decimals=cell["decimals"],
                        period=cell["period"],
                        basis=(
                            None
                            if case_name == "gap" and field == "prior"
                            else f"IFRS · consolidated group · component descriptor {cell['period']}"
                        ),
                        value_class="calculated" if derived else "source",
                        calculation_id=f"fixture-calculation:{cell['fact_id']}"
                        if derived
                        else None,
                        formula=(
                            f"fixture current[cp1b:{table['table_id']}:{row['row_id']}:current] "
                            f"minus prior[cp1b:{table['table_id']}:{row['row_id']}:prior]"
                            + (
                                f"; divided by prior[cp1b:{table['table_id']}:{row['row_id']}:prior]"
                                if field == "growth"
                                else ""
                            )
                            if derived
                            else None
                        ),
                        source_amount=amount if not derived else None,
                        stated_amount=amount if not derived else None,
                        calculation_status="Calculated"
                        if cell["status"] == "known"
                        else "Not Calculable",
                        limitation=cell["reason_contains"],
                        citations=(_citation(row["row_id"]),),
                    )
                )
            rows.append(
                TableRow(
                    row_id=row["row_id"],
                    label=row_layout["label"],
                    fact_ids=tuple(c["fact_id"] for c in row["cells"]),
                )
            )
        tables.append(
            ReportTable(
                table_id=table["table_id"],
                title=layout["title"],
                columns=tuple(
                    TableColumn(field=f, label=expected["column_labels"][f])
                    for f in layout["fields"]
                ),
                rows=tuple(rows),
                row_header=layout["row_header"],
                limitation="; ".join(expected["table_limitation_required_semantics"]),
            )
        )
    assessment_rows = []
    for item, row_layout in zip(expected["assessments"], LAYOUTS["T1B.3"]["rows"], strict=True):
        words = "; ".join(item["required_semantics"])
        if item["row_id"] == "evidence.inputs":
            words = json.dumps(_fixture_input_evidence(case_name), sort_keys=True)
        facts.append(
            Fact(
                fact_id=item["fact_id"],
                label=row_layout["label"],
                table_id="T1B.3",
                row_id=item["row_id"],
                field="assessment",
                status=item["status"],
                text=words if item["status"] == "known" else None,
                limitation=(item["reason_contains"] + "; " + words)
                if item["status"] != "known"
                else None,
                period=pair,
                citations=(_citation("assessment"),),
            )
        )
        assessment_rows.append(
            TableRow(row_id=item["row_id"], label=row_layout["label"], fact_ids=(item["fact_id"],))
        )
    tables.append(
        ReportTable(
            table_id="T1B.3",
            title=LAYOUTS["T1B.3"]["title"],
            row_header="Assessment",
            columns=(
                TableColumn(field="assessment", label=expected["column_labels"]["assessment"]),
            ),
            rows=tuple(assessment_rows),
        )
    )
    module = ModuleView(
        module_id="CP-1B",
        title="Seeded CP1B component preview; no owner execution",
        aliases=(),
        status=status,
        artifact_sha256=FIXTURE_HASH,
        facts=tuple(facts),
        tables=tuple(tables),
        limitations=LIMITATIONS,
    )
    run = Run(
        run_id=f"component-preview-{expected['case_id']}",
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="earnings_update",
        requested_modules=("CP-1B",),
    )
    view = empty_view(run, candidate=True)
    sources = tuple(
        Source(
            source_id=s["source_id"],
            name="Component fixture copy: " + s["name"],
            status="ready",
            sha256=s["sha256"],
            spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in s["pages"]),
        )
        for s in MANIFEST["sources"]
    )
    return view.model_copy(
        update={
            "modules": tuple(module if m.module_id == "CP-1B" else m for m in view.modules),
            "sources": sources,
        }
    )


def _module(view):
    return next(m for m in view.modules if m.module_id == "CP-1B")


def _replace(view, module):
    # Deliberate model_copy permits adversarial invalid objects at the build boundary.
    return view.model_copy(
        update={"modules": tuple(module if m.module_id == "CP-1B" else m for m in view.modules)}
    )


def _change_fact(view, fact_id, **updates):
    module = _module(view)
    return _replace(
        view,
        module.model_copy(
            update={
                "facts": tuple(
                    f.model_copy(update=updates) if f.fact_id == fact_id else f
                    for f in module.facts
                )
            }
        ),
    )


def _report(view, maps=SHIPPED_MAPS):
    return build(view, next(p for p in pathways() if p.id == view.run.pathway), maps)


def _blocks(report):
    return {b.block_id: b for b in report.blocks}


def _payload(html):
    return json.loads(
        html.split('<script id="report-data" type="application/json">', 1)[1].split("</script>", 1)[
            0
        ]
    )


def test_fp02_four_blocks_use_canonical_cp1b_preview():
    view = _seed()
    report = _report(view)
    blocks = _blocks(report)
    for spec in ORACLE["specifications"]:
        block = blocks[spec["block_id"]]
        assert (
            block.title,
            block.owner,
            block.kind,
            block.full_analysis_route,
            block.route_label,
        ) == (spec["title"], "CP-1B", spec["kind"], "CP-1B", "Full analysis")
        assert block.state == "populated" and block.tags == ("Synthetic",)
        actual_spec = report_view._spec_of(spec["block_id"])
        for name in ("producers", "collapsed", "width", "numbered", "pinned", "dated"):
            expected = tuple(spec[name]) if name == "producers" else spec[name]
            assert getattr(actual_spec, name) == expected
    assert "flat" in blocks["variance-drivers"].lines[0].runs[0].text
    assert _module(view).artifact_sha256 == FIXTURE_HASH


def test_nine_unique_bindings_are_shipped_once_immediately_after_cp1():
    maps = [m for m in SHIPPED_MAPS if m.module_id == "CP-1B"]
    assert len(maps) == 1
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.index("CP-1B") == ids.index("CP-1") + 1
    actual = [
        dict(
            module_id=e.fact_coord.module_id,
            table_id=e.fact_coord.table_id,
            row_id=e.fact_coord.row_id,
            fact_id=e.fact_coord.fact_id,
            block_id=e.block_id,
            cell_slot=e.cell_slot,
            label=e.label,
            unit_class=e.unit_class,
        )
        for e in maps[0].entries
    ]
    assert actual == ORACLE["bindings"]
    assert len({e.cell_slot for e in maps[0].entries}) == 9
    assert validate_bindings(_seed(), SHIPPED_MAPS) == ()


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_oracle_columns_values_statuses_and_existing_passports_are_preserved(case):
    view = _seed(case)
    module = _module(view)
    before = module.model_dump_json()
    report = _report(view)
    blocks = _blocks(report)
    for expected in ORACLE[case]["tables"]:
        target = "headline-results" if expected["table_id"] == "T1B.1" else "kpi-changes"
        block = blocks[target]
        layout = LAYOUTS[expected["table_id"]]
        assert block.columns == tuple(ORACLE[case]["column_labels"][f] for f in layout["fields"])
        assert [r.row_id for r in block.rows] == [r["row_id"] for r in expected["rows"]]
        assert [r.label for r in block.rows] == [r["label"] for r in layout["rows"]]
        for row, wanted in zip(block.rows, expected["rows"], strict=True):
            for cell, source in zip(row.cells, wanted["cells"], strict=True):
                fact = next(f for f in module.facts if f.fact_id == source["fact_id"])
                assert fact.amount == (
                    None if source["value"] is None else Decimal(source["value"])
                )
                assert (
                    fact.status,
                    fact.unit,
                    fact.currency,
                    fact.scale,
                    fact.period,
                    fact.decimals,
                ) == (
                    source["status"],
                    source["unit"],
                    source["currency"],
                    Decimal(source["scale"]),
                    source["period"],
                    None,
                )
                if source["display"] is not None:
                    assert cell.text == source["display"]
                else:
                    assert re.fullmatch(source["display_pattern"], cell.text)
                    assert source["reason_contains"] in fact.limitation
                assert report.passport(cell.gap_ref or cell.ref_id)
    assert module.model_dump_json() == before
    if case == "gap":
        assert [r.cells[1].text for r in blocks["kpi-changes"].rows] == ["20", "50", "30"]
        assert all(r.cells[0].gap_ref and r.cells[2].gap_ref for r in blocks["kpi-changes"].rows)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_core_html_preserves_full_analysis_source_context_and_limits(case):
    view = _seed(case)
    payload = _payload(render(view))
    module = next(m for m in payload["modules"] if m["module_id"] == "CP-1B")
    assert module["artifact_sha256"] == FIXTURE_HASH
    assert (module["status_glyph"], module["status_word"]) == ("candidate", "Candidate")
    assert "status" not in module
    assert len(module["facts"]) == 44 and [t["table_id"] for t in module["tables"]] == [
        "T1B.1",
        "T1B.2",
        "T1B.3",
    ]
    assert module["limitations"] == list(LIMITATIONS)
    assert payload["analytical_qualification"] == payload["native_host_qualification"] == "unrun"
    for other in payload["modules"]:
        if other["module_id"] in {"CP-MODEL", "CP-5", "CP-1"}:
            # The run requests only CP-1B: CP-1, CP-MODEL and CP-5 are earnings_update preset
            # modules the override left out, so all three were not requested (not foreign).
            assert (other["status_glyph"], other["status_word"]) == ("unrun", "Not run")
            assert not other["facts"] and not other["tables"]
            assert other["artifact_sha256"] is None
    record = next(f for f in module["facts"] if f["row_id"] == "evidence.inputs")
    assert UPSTREAM_FIXTURE_HASH in record["text"] and "component fixture" in record["text"]
    assert (
        "No FY2024 annual income statement"
        in next(s for s in payload["sources"] if s["source_id"] == "financial")["spans"][0]["text"]
    )
    if case == "positive":
        fact = next(f for f in module["facts"] if f["fact_id"] == "cp1b:T1B.2:cash_closing:delta")
        assert (
            fact["amount"] == "1.25" and fact["display"] == "1.25" and fact["table_display"] == "1"
        )
        assert "current[" in fact["formula"] and "prior[" in fact["formula"]
        assert fact["citations"][0]["source_sha256"] == ORACLE["financial_source_sha256"]
    # No native rail visibility/authentication claim: the real assets consume these fields later.


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_fixture_evidence_and_all_canonical_passport_fields_survive_round_trip(case):
    view = _seed(case)
    report = _report(view)
    rendered = next(m for m in _payload(render(view))["modules"] if m["module_id"] == "CP-1B")
    serialized = {f["fact_id"]: f for f in rendered["facts"]}
    evidence = json.loads(serialized["cp1b:T1B.3:evidence.inputs:assessment"]["text"])
    assert evidence == _fixture_input_evidence(case)
    assert evidence["selected_cp1_artifact_sha256"] == UPSTREAM_FIXTURE_HASH
    assert evidence["requested_pair"] == [
        ORACLE[case]["prior_period_id"],
        ORACLE[case]["current_period_id"],
    ]
    points = {p["measure"]: p["roles"] for p in evidence["points"]}
    assert set(points) == {
        "revenue",
        "ebitda",
        "adjusted_ebitda",
        "ebitda_margin",
        "cfo_reported",
        "capex",
        "fcf",
        "cash_closing",
        "total_debt",
        "net_debt",
        "total_leverage_reported",
        "net_leverage_reported",
    }
    for measure, roles in points.items():
        for role, operand in roles.items():
            period = ORACLE[case][f"{role}_period_id"]
            assert operand["requested_period_id"] == period
            if case == "gap" and role == "prior":
                assert operand["primary_fact_id"] is operand["basis_id"] is None
                assert operand["companion_fact_ids"] == operand["citations"] == []
                assert operand["value"] is None and operand["status"] == "missing"
                assert "COMPARATIVE_NOT_SUPPLIED" in operand["reason"]
            else:
                assert operand["primary_fact_id"] == f"fixture-primary:{period}:{measure}"
                assert operand["basis_id"] == f"fixture-basis:{period}"
                assert operand["companion_fact_ids"] == [
                    f"fixture-companion:{period}:{measure}:period_id"
                ]
                assert operand["citations"] == [_citation(measure).model_dump(mode="json")]
    for measure, value in (
        ("total_leverage_reported", "1.6666666666666666666666666666666666667"),
        ("net_leverage_reported", "1"),
    ):
        assert points[measure]["current"]["value"] == value
        assert points[measure]["current"]["status"] == "known"
        assert points[measure]["current"]["trailing_denominator"] == {
            "fact_id": f"fixture-primary:{ORACLE[case]['current_period_id']}:trailing-ebitda",
            "value": "30",
            "basis_id": f"fixture-trailing-basis:{ORACLE[case]['current_period_id']}",
            "citations": [_citation("ebitda").model_dump(mode="json")],
        }
        operands = (
            ("total_debt", "trailing-ebitda")
            if measure == "total_leverage_reported"
            else ("total_debt", "cash_closing", "trailing-ebitda")
        )
        assert points[measure]["current"]["input_operand_fact_ids"] == [
            f"fixture-primary:{ORACLE[case]['current_period_id']}:{name}" for name in operands
        ]
        if case == "positive":
            prior = points[measure]["prior"]
            assert prior["status"] == "missing" and prior["value"] is None
            assert prior["primary_fact_id"] is not None
            assert "Four complete quarters" in prior["reason"]
    for fact in _module(view).facts:
        canonical = fact.model_dump(mode="json")
        assert {key: serialized[fact.fact_id][key] for key in canonical} == canonical
        coord = FactCoord(
            module_id="CP-1B", table_id=fact.table_id, row_id=fact.row_id, fact_id=fact.fact_id
        )
        entry = next(e for e in report.index.facts if e.coord == coord)
        actual = [
            (report.passport(ref).kind, {f.name: f.value for f in report.passport(ref).fields})
            for ref in entry.ref_ids
        ]
        expected = []
        if fact.status != "known":
            expected.append(
                (
                    "gap",
                    {
                        "Item": fact.label,
                        "Status": fact.status.replace("_", " "),
                        "Reason": fact.limitation,
                    },
                )
            )
        expected.extend(
            (
                "synthetic",
                {
                    "Source": c.source_id,
                    "Locator": c.locator,
                    "Quote": c.quote,
                    "SHA-256": c.source_sha256,
                    "Data": "Synthetic test data",
                },
            )
            for c in fact.citations
        )
        if fact.calculation_id:
            expected.append(
                (
                    "calculated",
                    {
                        key: value
                        for key, value in {
                            "Calculation": fact.calculation_id,
                            "Formula": fact.formula,
                            "Status": fact.calculation_status,
                            "Period": fact.period,
                            "Basis": fact.basis,
                        }.items()
                        if value
                    },
                )
            )
        assert actual == expected


@pytest.mark.parametrize("measure", ["revenue", "ebitda", "adjusted_ebitda"])
def test_zero_prior_keeps_known_delta_and_missing_growth(measure):
    view = _seed()
    for field, updates in {
        "prior": {"amount": Decimal(0)},
        "current": {"amount": Decimal(30)},
        "delta": {"amount": Decimal(30)},
        "growth": {"amount": None, "status": "missing", "limitation": "ZERO_DENOMINATOR"},
    }.items():
        view = _change_fact(view, f"cp1b:T1B.1:{measure}:{field}", **updates)
    row = next(r for r in _blocks(_report(view))["headline-results"].rows if r.row_id == measure)
    assert row.cells[0].text == "0" and row.cells[2].text == "30"
    assert re.fullmatch(r"∅ G[1-9][0-9]*", row.cells[3].text)


@pytest.mark.parametrize("amount,text", [("5", "5 pp"), ("5.00", "5.00 pp"), ("0.00", "0.00 pp")])
def test_pp_is_exact_without_display_arithmetic_or_quantization(amount, text):
    view = _change_fact(_seed(), "cp1b:T1B.1:ebitda_margin:delta", amount=Decimal(amount))
    row = next(
        r for r in _blocks(_report(view))["headline-results"].rows if r.row_id == "ebitda_margin"
    )
    assert row.cells[2].text == text
    assert (
        next(
            f for f in _module(view).facts if f.fact_id == "cp1b:T1B.1:ebitda_margin:delta"
        ).amount.as_tuple()
        == Decimal(amount).as_tuple()
    )


@pytest.mark.parametrize("status", ["restricted", "accepted"])
def test_existing_shown_states_do_not_change_fixture_authority(status):
    view = _seed(status=status)
    assert _blocks(_report(view))["headline-results"].state == "populated"
    assert _module(view).status == status and "component preview" in _module(view).limitations[-1]


@pytest.mark.parametrize("status", ["unrun", "blocked", "stale"])
def test_nonshown_state_never_inherits_populated_earnings(status):
    view = _seed()
    changes = {"status": status}
    if status == "unrun":
        changes.update(facts=(), tables=(), artifact_sha256=None)
    view = _replace(view, _module(view).model_copy(update=changes))
    for block in _report(view).blocks:
        if block.block_id in {s["block_id"] for s in ORACLE["specifications"]}:
            assert block.state != "populated" and not block.rows and not block.lines


def _broken_layout(view, variant):
    module = _module(view)
    tables = list(module.tables)
    table = tables[0]
    if variant.startswith("table-"):
        tables = {
            "table-missing": tables[1:],
            "table-duplicate": [*tables, table],
            "table-extra": [*tables, table.model_copy(update={"table_id": "T1B.foreign"})],
            "table-order": list(reversed(tables)),
        }[variant]
    elif variant.startswith("column-"):
        cols = list(table.columns)
        cols = {
            "column-missing": cols[:-1],
            "column-duplicate": [*cols, cols[0]],
            "column-extra": [*cols, TableColumn(field="foreign", label="Foreign")],
            "column-order": list(reversed(cols)),
            "column-label": [
                cols[0].model_copy(update={"label": "Wrong prior heading"}),
                *cols[1:],
            ],
        }[variant]
        tables[0] = table.model_copy(update={"columns": tuple(cols)})
    elif variant.startswith("row-"):
        rows = list(table.rows)
        rows = {
            "row-missing": rows[:-1],
            "row-duplicate": [*rows, rows[0]],
            "row-extra": [*rows, rows[0].model_copy(update={"row_id": "foreign"})],
            "row-order": list(reversed(rows)),
            "row-label": [rows[0].model_copy(update={"label": "Wrong row"}), *rows[1:]],
            "row-kind": [rows[0].model_copy(update={"row_kind": "total"}), *rows[1:]],
            "row-pointer": [
                rows[0].model_copy(update={"fact_ids": tuple(reversed(rows[0].fact_ids))}),
                *rows[1:],
            ],
        }[variant]
        tables[0] = table.model_copy(update={"rows": tuple(rows)})
    else:
        tables[0] = table.model_copy(
            update={
                "interface": {"interface_id": "T4.borrowed"},
                "title": {"title": "Wrong title"},
                "header": {"row_header": "Wrong header"},
            }[variant]
        )
    return _replace(view, module.model_copy(update={"tables": tuple(tables)}))


@pytest.mark.parametrize(
    "variant",
    [
        "table-missing",
        "table-duplicate",
        "table-extra",
        "table-order",
        "column-missing",
        "column-duplicate",
        "column-extra",
        "column-order",
        "column-label",
        "row-missing",
        "row-duplicate",
        "row-extra",
        "row-order",
        "row-label",
        "row-kind",
        "row-pointer",
        "interface",
        "title",
        "header",
    ],
)
def test_malformed_layout_refuses_before_fallback_or_partial_projection(variant):
    with pytest.raises(ValueError):
        _report(_broken_layout(_seed(), variant))


@pytest.mark.parametrize(
    "variant",
    ["missing", "duplicate", "extra", "undeclared-table", "coordinate", "identity", "field"],
)
def test_fact_inventory_and_coordinates_refuse(variant):
    view = _seed()
    module = _module(view)
    facts = list(module.facts)
    if variant == "missing":
        facts.pop()
    elif variant == "duplicate":
        facts.append(facts[0])
    elif variant == "extra":
        facts.append(facts[0].model_copy(update={"fact_id": "foreign.fact"}))
    else:
        changes = {
            "undeclared-table": {"table_id": "foreign"},
            "coordinate": {"row_id": "ebitda"},
            "identity": {"fact_id": "foreign.fact"},
            "field": {"field": "current"},
        }[variant]
        facts[0] = facts[0].model_copy(update=changes)
    with pytest.raises(ValueError):
        _report(_replace(view, module.model_copy(update={"facts": tuple(facts)})))


@pytest.mark.parametrize(
    "target,updates",
    [
        ("T1B.1:revenue:prior", {"unit": "THOUSANDS"}),
        ("T1B.1:revenue:prior", {"currency": "EUR"}),
        ("T1B.2:cash_closing:delta", {"scale": Decimal(1)}),
        ("T1B.1:ebitda_margin:delta", {"unit": "PERCENT"}),
        ("T1B.1:ebitda_margin:current", {"currency": "USD"}),
        ("T1B.1:revenue:growth", {"unit": "MULTIPLE"}),
        ("T1B.1:revenue:growth", {"scale": Decimal(100)}),
        ("T1B.1:revenue:current", {"decimals": 2}),
        ("T1B.3:drivers:assessment", {"scale": Decimal(1000000)}),
        ("T1B.3:evidence.inputs:assessment", {"currency": "USD"}),
    ],
)
def test_role_dimensions_and_precision_refuse(target, updates):
    with pytest.raises(ValueError):
        _report(_change_fact(_seed(), "cp1b:" + target, **updates))


@pytest.mark.parametrize(
    "target,updates",
    [
        ("T1B.1:revenue:current", {"amount": Decimal("NaN")}),
        ("T1B.1:revenue:current", {"amount": Decimal("Infinity")}),
        ("T1B.1:revenue:current", {"amount": None}),
        ("T1B.1:revenue:current", {"text": "30"}),
        ("T1B.1:revenue:current", {"status": "missing", "limitation": "missing"}),
        ("T1B.1:capex:growth", {"limitation": None}),
        ("T1B.1:capex:growth", {"limitation": " "}),
        ("T1B.3:evidence.inputs:assessment", {"text": ""}),
        ("T1B.3:evidence.inputs:assessment", {"text": " "}),
        (
            "T1B.3:evidence.inputs:assessment",
            {"text": None, "amount": Decimal(1), "unit": "MILLIONS"},
        ),
        ("T1B.3:guidance:assessment", {"text": "Invented guidance"}),
    ],
)
def test_numeric_and_assessment_shapes_refuse(target, updates):
    with pytest.raises(ValueError):
        _report(_change_fact(_seed(), "cp1b:" + target, **updates))


@pytest.mark.parametrize("measure", ["ebitda_margin", "cfo_reported", "capex", "fcf"])
@pytest.mark.parametrize("status", ["known", "missing"])
def test_nongrowth_rows_require_reasoned_not_applicable(measure, status):
    updates = {
        "status": status,
        "amount": Decimal(0) if status == "known" else None,
        "limitation": "wrong applicability",
    }
    with pytest.raises(ValueError):
        _report(_change_fact(_seed(), f"cp1b:T1B.1:{measure}:growth", **updates))


@pytest.mark.parametrize("measure", ["revenue", "ebitda", "adjusted_ebitda"])
@pytest.mark.parametrize(
    "status,amount,reason",
    [
        ("not_applicable", None, "ZERO_DENOMINATOR"),
        ("known", Decimal(0), None),
        ("missing", None, "wrong reason"),
    ],
)
def test_zero_prior_growth_cannot_be_na_known_zero_or_unreasoned(measure, status, amount, reason):
    view = _change_fact(_seed(), f"cp1b:T1B.1:{measure}:prior", amount=Decimal(0))
    view = _change_fact(
        view, f"cp1b:T1B.1:{measure}:growth", status=status, amount=amount, limitation=reason
    )
    with pytest.raises(ValueError):
        _report(view)


def test_shown_empty_cp1b_refuses_instead_of_appearing_as_a_partial_report():
    view = _seed()
    module = _module(view).model_copy(update={"facts": (), "tables": ()})
    with pytest.raises(ValueError):
        _report(_replace(view, module))


def test_fact_tuple_order_does_not_replace_declared_table_order():
    view = _seed()
    before = _report(view)
    view = _replace(
        view, _module(view).model_copy(update={"facts": tuple(reversed(_module(view).facts))})
    )
    after = _report(view)

    def projected_rows(report):
        # G numbers are view-local. Resolve each one to its own fact and reason.
        gaps = {
            ref: (entry.coord.fact_id, report.passport(ref).kind, report.passport(ref).fields)
            for entry in report.index.facts
            for ref in entry.ref_ids
            if ref.startswith("G")
        }
        return [
            (
                row.row_id,
                row.label,
                [
                    (cell.state, cell.unit_class, gaps[cell.gap_ref])
                    if cell.gap_ref
                    else (cell.state, cell.unit_class, cell.text)
                    for cell in row.cells
                ],
            )
            for row in _blocks(report)["headline-results"].rows
        ]

    assert projected_rows(before) == projected_rows(after)


@pytest.mark.parametrize("mutation", ["map", "slot", "destination", "unbound"])
def test_existing_binding_rejections_are_retained(mutation):
    current = next(m for m in SHIPPED_MAPS if m.module_id == "CP-1B")
    entries = list(current.entries)
    maps = list(SHIPPED_MAPS)
    if mutation == "map":
        maps.append(current)
    else:
        if mutation == "slot":
            entries.append(entries[0])
        elif mutation == "destination":
            entries.append(
                Binding(
                    fact_coord=FactCoord(module_id="CP-1B", table_id="T1B.1"),
                    block_id="evidence",
                    cell_slot="cp1b-double",
                    unit_class="text",
                )
            )
        else:
            entries = entries[1:]
        maps = [
            BindingMap(module_id="CP-1B", entries=tuple(entries)) if m.module_id == "CP-1B" else m
            for m in maps
        ]
    with pytest.raises(ValueError):
        _report(_seed(), tuple(maps))


def test_cp1_candidate_metric_strip_and_other_owners_remain_separate():
    view = _seed()
    base = empty_view(view.run, candidate=True)
    fact = Fact(
        fact_id="fixture-cp1-revenue-name",
        label="Metric name",
        table_id="T4.10",
        row_id="revenue",
        field="field_1",
        text="revenue",
        citations=(_citation("revenue"),),
    )
    cp1 = next(m for m in base.modules if m.module_id == "CP-1").model_copy(
        update={
            "status": "candidate",
            "artifact_sha256": UPSTREAM_FIXTURE_HASH,
            "facts": (fact,),
            "tables": (
                ReportTable(
                    table_id="T4.10",
                    title="CP1 isolation fixture",
                    columns=(TableColumn(field="field_1", label="Metric name"),),
                    rows=(TableRow(row_id="revenue", label="Revenue", fact_ids=(fact.fact_id,)),),
                ),
            ),
            "limitations": ("Separate CP1 candidate isolation fixture; no owner execution",),
        }
    )
    base = base.model_copy(
        update={"modules": tuple(cp1 if m.module_id == "CP-1" else m for m in base.modules)}
    )
    combined = view.model_copy(
        update={"modules": tuple(cp1 if m.module_id == "CP-1" else m for m in view.modules)}
    )
    prior = _blocks(_report(base))["metric-strip"]
    current = _blocks(_report(combined))["metric-strip"]
    assert prior.model_dump() == current.model_dump()
    assert [f.fig_id for f in current.figures] == ["S.1", "S.2", "S.3"]
    assert all(not f.chart.marks for f in current.figures)
    assert not _blocks(_report(combined))["ebitda-adjustments"].rows
    assert next(m for m in combined.modules if m.module_id == "CP-1D").status == "not_in_pathway"
    # This proves candidate isolation, not drawn CP1-series or full FP02 acceptance.
