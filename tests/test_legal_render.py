"""Seeded FP04 component checks; no actual legal owner/CP5/native acceptance."""

import copy
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
from deploy_vii.report_view import FactCoord, build, build_index, pathways

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "cases/legal/render-expected.json").read_text())

LEGAL = json.loads((ROOT / "cases/legal/manifest.json").read_text())
FINANCIAL = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SCHEMAS = {s["table_id"]: s for s in ORACLE["schemas"]}


def _seed(case=0, *, status="candidate"):
    """Materialize supplied literal rows, never a composer/owner or numerical oracle."""
    expected = ORACLE["cases"][case]
    rows = copy.deepcopy(ORACLE["fixture"]["shared_rows"])
    for change in expected["overrides"]:
        row = next(r for r in rows if r["table_id"] == change["table_id"])
        next(c for c in row["cells"] if c["field"] == change["field"]).update(change["replace"])
    if case:
        extra = expected["append_gap_row"]
        rows.append(
            {
                **extra,
                "row_kind": "row",
                "cells": [{"field": f, "text": t} for f, t in extra["cells"].items()],
            }
        )
    groups = ORACLE["fixture"]["citation_groups"][expected["case_id"]]
    facts, tables = [], []
    for schema in ORACLE["schemas"]:
        table_rows = []
        for row in (r for r in rows if r["table_id"] == schema["table_id"]):
            ids = []
            for cell in row["cells"]:
                values = {**ORACLE["fixture"]["fact_defaults"], **cell}
                field = values.pop("field")
                cites = values.pop("citation_group", "default")
                fact_id = values.pop("fact_id", f"{schema['table_id']}.{row['row_id']}.{field}")
                label = values.pop(
                    "label", next(c["label"] for c in schema["columns"] if c["field"] == field)
                )
                for name in ("amount", "scale", "source_amount", "stated_amount"):
                    if values.get(name) is not None:
                        values[name] = Decimal(values[name])
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        label=label,
                        table_id=schema["table_id"],
                        row_id=row["row_id"],
                        field=field,
                        citations=tuple(Citation(**c) for c in groups[cites]),
                        **values,
                    )
                )
                ids.append(fact_id)
            table_rows.append(
                TableRow(
                    row_id=row["row_id"],
                    label=row["label"],
                    row_kind=row["row_kind"],
                    fact_ids=tuple(ids),
                )
            )
        tables.append(
            ReportTable(
                table_id=schema["table_id"],
                title=schema["title"],
                columns=tuple(TableColumn(**c) for c in schema["columns"]),
                rows=tuple(table_rows),
                row_header="CP-1 figure" if schema["table_id"] == "T4F.2" else schema["row_header"],
            )
        )
    limits = [*ORACLE["fixture"]["module_limitations"]]
    if case:
        limits.append(expected["additional_module_limitation"])
    module = ModuleView(
        module_id="CP-4",
        title="Seeded CP4 component preview; no owner execution",
        aliases=(),
        status=status,
        artifact_sha256=expected["fixture_artifact"]["sha256"],
        facts=tuple(facts),
        tables=tuple(tables),
        limitations=tuple(limits),
    )
    run = Run(
        run_id=expected["fixture_run_id"],
        issuer_id="northbridge-synthetic",
        issuer_name="Northbridge Synthetic Group",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="covenant_refinancing",
        requested_modules=("CP-4", "CP-5"),
    )
    view = empty_view(run)
    legal = LEGAL["cases"][case]["legal_source"]
    sources = [*FINANCIAL["sources"], legal]
    return view.model_copy(
        update={
            "modules": tuple(module if m.module_id == "CP-4" else m for m in view.modules),
            "sources": tuple(
                Source(
                    source_id=s["source_id"],
                    name="Component fixture copy: " + s["name"],
                    status="ready",
                    sha256=s["sha256"],
                    spans=tuple(Span(**p) for p in s["pages"]),
                )
                for s in sources
            ),
        }
    )


def _module(view):
    return next(m for m in view.modules if m.module_id == "CP-4")


def _replace(view, module):
    # model_copy intentionally bypasses validation for adversarial build-boundary checks.
    return view.model_copy(
        update={"modules": tuple(module if m.module_id == "CP-4" else m for m in view.modules)}
    )


def _fact(view, fact_id, **updates):
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


def test_fp04_six_sections_use_canonical_component_tables():
    view = _seed()
    blocks = _blocks(_report(view))
    assert tuple(blocks) == tuple(ORACLE["pathway"]["block_order"])
    for expected in ORACLE["specifications"]:
        block = blocks[expected["block_id"]]
        assert (
            block.title,
            block.owner,
            block.kind,
            block.full_analysis_route,
            block.route_label,
        ) == (expected["title"], "CP-4", "dense", "CP-4", "Full analysis")
        assert block.state == "populated" and block.tags == ("Synthetic",)
        spec = report_view._spec_of(block.block_id)
        for field in ("collapsed", "width", "numbered", "pinned", "dated", "producers"):
            assert getattr(spec, field) == (
                tuple(expected[field]) if field == "producers" else expected[field]
            )
        table = next(t for t in _module(view).tables if t.table_id == expected["tables"][0])
        assert block.columns == tuple(c.label for c in table.columns)
        assert block.row_header == table.row_header
        assert [(r.row_id, r.label) for r in block.rows] == [
            (r.row_id, r.label) for r in table.rows
        ]
    documents = blocks["documents-structure"]
    assert documents.tab_label == "Document register"
    assert len(documents.tabs) == 1 and documents.tabs[0].label == "Facility coverage"
    assert documents.tabs[0].columns == tuple(c["label"] for c in SCHEMAS["T4C.12"]["columns"])


def test_all_31_existing_maps_are_exact_unique_and_shipped_once():
    view = _seed()
    maps = [m for m in SHIPPED_MAPS if m.module_id == "CP-4"]
    assert len(maps) == 1 and len(maps[0].entries) == 31
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
    assert len({e.cell_slot for e in maps[0].entries}) == 31
    assert {t.table_id for t in _module(view).tables} == set(SCHEMAS)
    assert validate_bindings(view, SHIPPED_MAPS) == ()


@pytest.mark.parametrize("case", [0, 1])
def test_adopted_values_gaps_capacity_and_all_front_columns(case):
    view = _seed(case)
    before = _module(view).model_dump_json()
    report = _report(view)
    row = _blocks(report)["covenant-tests-headroom"].rows[0]
    expected = ORACLE["cases"][case]
    assert row.cells[4].text == "1.00x"
    assert row.cells[1].text == "4.00x"
    for index, key in ((5, "headroom"), (6, "headroom_share")):
        wanted = expected["display_expectations"][key]
        assert (
            re.fullmatch(wanted, row.cells[index].text) if case else row.cells[index].text == wanted
        )
        fact = next(f for f in _module(view).facts if f.fact_id == f"T4.9.r01.{key}")
        assert fact.amount == (
            None if case else Decimal(expected["canonical_expectations"][key + "_amount"])
        )
        if case:
            passport = report.passport(row.cells[index].gap_ref)
            assert passport.kind == "gap" and expected["canonical_expectations"]["reason"] in next(
                f.value for f in passport.fields if f.name == "Reason"
            )
        else:
            assert fact.calculation_id is None and fact.formula and fact.value_class == "calculated"
            assert report.passport(row.cells[index].ref_id).kind == "synthetic"
    assert row.cells[7].text == expected["canonical_expectations"]["verdict"]
    capacity = _blocks(report)["capacity"].rows[0].cells[2]
    assert re.fullmatch(expected["display_expectations"]["capacity"], capacity.text)
    assert capacity.gap_ref and capacity.state == "gap"
    assert (
        _blocks(report)["lender-protection-score"].rows[0].cells[0].text
        == "Insufficient Information"
    )
    assert _module(view).model_dump_json() == before
    assert not any(f.amount == Decimal(90) for f in _module(view).facts)
    assert not any(f.field == "unused_commitment" for f in _module(view).facts)


@pytest.mark.parametrize("case", [0, 1])
def test_core_html_full_fact_fields_sources_passports_and_honest_states(case):
    view = _seed(case)
    report = _report(view)
    data = _payload(render(view))
    module = next(m for m in data["modules"] if m["module_id"] == "CP-4")
    assert (module["status_glyph"], module["status_word"]) == (
        "candidate",
        "Candidate",
    ) and "status" not in module
    assert module["artifact_sha256"] == ORACLE["cases"][case]["fixture_artifact"]["sha256"]
    assert (
        hashlib.sha256(ORACLE["cases"][case]["fixture_artifact"]["seed"].encode()).hexdigest()
        == module["artifact_sha256"]
    )
    assert module["limitations"] == list(_module(view).limitations)
    assert [t["table_id"] for t in module["tables"]] == list(SCHEMAS)
    serialized = {f["fact_id"]: f for f in module["facts"]}
    assert len(serialized) == (106 if case else 102)  # fixture count only, never guard invariant
    for fact in _module(view).facts:
        canonical = fact.model_dump(mode="json")
        assert {key: serialized[fact.fact_id][key] for key in canonical} == canonical
        coord = FactCoord(
            module_id="CP-4", table_id=fact.table_id, row_id=fact.row_id, fact_id=fact.fact_id
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
        assert actual == expected
    for ident, state in ORACLE["fixture"]["other_modules"].items():
        other = next(m for m in data["modules"] if m["module_id"] == ident)
        expected = ("unrun", "Not run") if state == "unrun" else ("na", "Not in this Pathway")
        assert (other["status_glyph"], other["status_word"]) == expected
        assert not other["facts"] and not other["tables"] and other["artifact_sha256"] is None
    assert data["analytical_qualification"] == data["native_host_qualification"] == "unrun"
    for source in view.sources:
        actual = next(s for s in data["sources"] if s["source_id"] == source.source_id)
        assert actual["sha256"] == source.sha256
        assert actual["spans"] == [s.model_dump(mode="json") for s in source.spans]
    # Stage 2 close release (rulings round 4 and round 5 item 18): the five blocks are the
    # CP-2D and CP-3C D7 `_Spec` rows; in a run that did not request the owner each renders the
    # empty state of a spec'd block, not the Unbound fallback.
    sections = ORACLE["other_front_sections"]
    assert set(sections["blocks"]) == set(sections["ids"])
    for block_id, want in sections["blocks"].items():
        block = _blocks(report)[block_id]
        assert report_view._spec_of(block_id).producers == tuple(want["producers"])
        assert (block.owner, block.kind, block.state, block.full_analysis_route) == (
            want["owner"],
            want["kind"],
            want["state"],
            want["full_analysis_route"],
        )
        assert block.note == want["note"]
        assert not block.rows and not block.lines  # no owner cell, no claim that the owner ran


@pytest.mark.parametrize("amount,display", [("0", "0.00x"), ("0.000", "0.00x")])
def test_known_zero_is_not_an_unknown_capacity_or_actual_unused_commitment(amount, display):
    view = _fact(_seed(), "T4.9.r01.headroom", amount=Decimal(amount))
    cell = _blocks(_report(view))["covenant-tests-headroom"].rows[0].cells[5]
    assert cell.text == display and cell.state == "known" and cell.gap_ref is None
    assert _blocks(_report(view))["capacity"].rows[0].cells[2].state == "gap"


def test_variable_rows_repeated_labels_and_source_precision_are_preserved():
    view = _seed()
    module = _module(view)
    table = next(t for t in module.tables if t.table_id == "T4.9")
    original = [f for f in module.facts if f.table_id == "T4.9"]
    copied = tuple(
        f.model_copy(update={"fact_id": f"T4.9.r02.{f.field}", "row_id": "r02"}) for f in original
    )
    row = table.rows[0].model_copy(
        update={"row_id": "r02", "fact_ids": tuple(f.fact_id for f in copied)}
    )
    view = _replace(
        view,
        module.model_copy(
            update={
                "facts": (*module.facts, *copied),
                "tables": tuple(
                    t.model_copy(update={"rows": (*t.rows, row)}) if t.table_id == "T4.9" else t
                    for t in module.tables
                ),
            }
        ),
    )
    view = _fact(view, "T4.9.r01.current", label="Original supplied source label", decimals=4)
    block = _blocks(_report(view))["covenant-tests-headroom"]
    assert len(block.rows) == 2 and block.rows[0].label == block.rows[1].label
    assert block.rows[0].cells[4].text == "1.0000x"
    assert (
        next(f for f in _module(view).facts if f.fact_id == "T4.9.r01.current").label
        == "Original supplied source label"
    )


def _empty_copy(view):
    module = _module(view)
    p = ORACLE["guard_contract"]["T4F.2_empty_policy"]
    fact = Fact(
        fact_id=p["fact_id"],
        label=p["label"],
        table_id="T4F.2",
        row_id=p["row_id"],
        field=p["field"],
        status=p["status"],
        limitation=p["limitation"],
    )
    table = next(t for t in module.tables if t.table_id == "T4F.2").model_copy(
        update={
            "row_header": None,
            "rows": (TableRow(row_id=p["row_id"], label=p["row_label"], fact_ids=(fact.fact_id,)),),
        }
    )
    return _replace(
        view,
        module.model_copy(
            update={
                "facts": (*tuple(f for f in module.facts if f.table_id != "T4F.2"), fact),
                "tables": tuple(table if t.table_id == "T4F.2" else t for t in module.tables),
            }
        ),
    )


def test_canonical_empty_reference_variant_is_not_missing_layout():
    view = _empty_copy(_seed())
    assert len(_module(view).tables) == 31
    _report(view)
    fact = next(f for f in _module(view).facts if f.table_id == "T4F.2")
    assert fact.status == "not_applicable" and fact.amount is None


def test_copy_id_is_producer_qualified_and_all_source_fields_may_survive():
    view = _seed()
    module = _module(view)
    original = next(f for f in module.facts if f.table_id == "T4F.2")
    view = _fact(
        view,
        original.fact_id,
        decimals=3,
        calculation_id="fixture-source-calculation",
        calculation_status="Fixture supplied calculation",
        formula="Fixture supplied formula",
    )
    _report(view)
    copy_fact = next(f for f in _module(view).facts if f.table_id == "T4F.2")
    original = copy_fact.model_copy(
        update={"table_id": "T4.10", "row_id": "fixture-row", "field": "value"}
    )
    cp1 = ModuleView(
        module_id="CP-1",
        title="Isolated candidate fixture; no execution",
        artifact_sha256=ORACLE["fixture"]["fixture_cp1_sha256"],
        aliases=(),
        status="candidate",
        facts=(original,),
        tables=(
            ReportTable(
                table_id="T4.10",
                title="Fixture original",
                columns=(TableColumn(field="value", label="Value"),),
                rows=(
                    TableRow(
                        row_id="fixture-row", label="Fixture original", fact_ids=(original.fact_id,)
                    ),
                ),
            ),
        ),
    )
    isolated = view.model_copy(
        update={"modules": tuple(cp1 if m.module_id == "CP-1" else m for m in view.modules)}
    )
    passports, index = build_index(isolated)
    entries = [e for e in index.facts if e.coord.fact_id == original.fact_id]
    assert {e.coord.module_id for e in entries} == {"CP-1", "CP-4"}
    assert any(p.kind == "calculated" for p in passports)
    assert {
        k: v for k, v in original.model_dump().items() if k not in {"table_id", "row_id", "field"}
    } == {
        k: v for k, v in copy_fact.model_dump().items() if k not in {"table_id", "row_id", "field"}
    }


def test_fact_permutation_changes_only_allocated_tokens_not_canonical_projection():
    view = _seed(1)
    reversed_view = _replace(
        view, _module(view).model_copy(update={"facts": tuple(reversed(_module(view).facts))})
    )

    def resolved(report):
        rows = []
        for block in report.blocks:
            for row in block.rows:
                rows.append(
                    (
                        block.block_id,
                        row.row_id,
                        row.label,
                        tuple(
                            (
                                c.state,
                                c.unit_class,
                                tuple(
                                    (report.passport(ref).kind, report.passport(ref).fields)
                                    for ref in (c.gap_ref or c.ref_id,)
                                    if ref
                                ),
                            )
                            for c in row.cells
                        ),
                    )
                )
        return rows

    assert resolved(_report(view)) == resolved(_report(reversed_view))


@pytest.mark.parametrize("status", ["accepted", "restricted"])
def test_existing_shown_states_are_presentation_only(status):
    assert _blocks(_report(_seed(status=status)))["capacity"].state == "populated"


@pytest.mark.parametrize("status", ["unrun", "not_in_pathway", "blocked", "stale"])
def test_empty_nonshown_modules_do_not_inherit_rows_or_routes(status):
    view = _seed()
    view = _replace(
        view,
        _module(view).model_copy(
            update={
                "status": status,
                "facts": (),
                "tables": (),
                "claims": (),
                "artifact_sha256": None,
            }
        ),
    )
    for spec in ORACLE["specifications"]:
        block = _blocks(_report(view))[spec["block_id"]]
        assert (
            block.state != "populated"
            and not block.rows
            and not block.lines
            and block.full_analysis_route is None
        )


@pytest.mark.parametrize("status", ["unrun", "not_in_pathway", "blocked", "stale", "rejected"])
def test_nonshown_output_refuses_before_full_analysis_carryover(status):
    with pytest.raises(ValueError):
        _report(_replace(_seed(), _module(_seed()).model_copy(update={"status": status})))


def _break(view, variant):
    module = _module(view)
    tables, facts = list(module.tables), list(module.facts)
    index = next(i for i, t in enumerate(tables) if t.table_id == "T4.9")
    table = tables[index]
    if variant.startswith("table-"):
        if variant == "table-missing":
            tables.pop(index)
        elif variant == "table-duplicate":
            tables.append(table)
        elif variant == "table-extra":
            tables.append(table.model_copy(update={"table_id": "T4.extra"}))
        else:
            tables.reverse()
    elif variant in {"title", "row-header", "interface"}:
        tables[index] = table.model_copy(
            update={
                "title": {"title": "Wrong"},
                "row-header": {"row_header": "Wrong"},
                "interface": {"interface_id": "borrowed"},
            }[variant]
        )
    elif variant.startswith("column-"):
        columns = list(table.columns)
        if variant == "column-missing":
            columns.pop()
        elif variant == "column-extra":
            columns.append(TableColumn(field="foreign", label="Foreign"))
        elif variant == "column-duplicate":
            columns.append(columns[0])
        elif variant == "column-order":
            columns.reverse()
        else:
            columns[0] = columns[0].model_copy(update={"label": "Wrong"})
        tables[index] = table.model_copy(update={"columns": tuple(columns)})
    elif variant in {
        "row-duplicate",
        "row-kind",
        "row-pointer",
        "pointer-unknown",
        "pointer-double",
        "row-empty",
        "row-label",
    }:
        row = table.rows[0]
        ids = list(row.fact_ids)
        if variant == "row-pointer":
            ids.reverse()
        elif variant == "pointer-unknown":
            ids[0] = "foreign"
        elif variant == "pointer-double":
            ids[0] = ids[1]
        changes = {"fact_ids": tuple(ids)}
        if variant == "row-kind":
            changes["row_kind"] = "total"
        if variant == "row-label":
            changes["label"] = " "
        rows = (
            ()
            if variant == "row-empty"
            else (row, row)
            if variant == "row-duplicate"
            else (row.model_copy(update=changes),)
        )
        tables[index] = table.model_copy(update={"rows": rows})
    elif variant.startswith("fact-"):
        if variant == "fact-missing":
            facts.pop()
        elif variant == "fact-duplicate":
            facts.append(facts[0])
        elif variant == "fact-extra":
            facts.append(facts[0].model_copy(update={"fact_id": "foreign", "table_id": "foreign"}))
        else:
            old_id = facts[0].fact_id
            facts[0] = facts[0].model_copy(
                update={"field": "foreign"}
                if variant == "fact-coordinate"
                else {"fact_id": "foreign"}
            )
            if variant == "fact-normal-identity":
                tables = [
                    t.model_copy(
                        update={
                            "rows": tuple(
                                r.model_copy(
                                    update={
                                        "fact_ids": tuple(
                                            "foreign" if i == old_id else i for i in r.fact_ids
                                        )
                                    }
                                )
                                for r in t.rows
                            )
                        }
                    )
                    for t in tables
                ]
    elif variant == "shown-empty":
        facts, tables = [], []
    return _replace(
        view, module.model_copy(update={"facts": tuple(facts), "tables": tuple(tables)})
    )


@pytest.mark.parametrize(
    "variant",
    [
        c["variant"]
        for c in ORACLE["refusal_checks"]
        if c["variant"]
        not in {
            "numeric-nonfinite",
            "numeric-shape",
            "gap-shape",
            "gap-reason",
            "native-dimension",
            "binding-missing",
            "binding-duplicate",
            "binding-double",
            "nonshown-output-carry",
        }
    ]
    + ["row-empty", "row-label"],
)
def test_structural_layout_mutations_refuse(variant):
    with pytest.raises(ValueError):
        _report(_break(_seed(), variant))


@pytest.mark.parametrize(
    "target,updates",
    [
        ("T4.9.r01.headroom", {"amount": Decimal("NaN")}),
        ("T4.9.r01.headroom", {"amount": Decimal("Infinity")}),
        ("T4.9.r01.headroom", {"amount": None}),
        ("T4.9.r01.headroom", {"text": "3"}),
        ("T4.9.r01.headroom", {"period": " "}),
        ("T4.9.r01.headroom", {"unit": "MILLIONS"}),
        ("T4.9.r01.headroom", {"scale": Decimal(100)}),
        ("T4.9.r01.headroom", {"currency": "USD"}),
        ("T4.9.r01.headroom_share", {"unit": "MULTIPLE"}),
        ("T4.9.r01.headroom_share", {"scale": Decimal(100)}),
        ("T4.9.r01.current", {"decimals": 7}),
        ("T4.9.r01.current", {"scale": Decimal("NaN")}),
        ("T4.9.r01.current", {"scale": Decimal("Infinity")}),
        ("T4.9.r01.current", {"scale": Decimal(0)}),
        ("T4.9.r01.test_formula", {"text": " "}),
        ("T4.10.r01.capacity_amount", {"amount": Decimal(0)}),
        ("T4.10.r01.capacity_amount", {"text": "Unknown"}),
        ("T4.10.r01.capacity_amount", {"limitation": " "}),
    ],
)
def test_known_nonknown_native_shape_mutations_refuse(target, updates):
    with pytest.raises(ValueError):
        _report(_fact(_seed(), target, **updates))


@pytest.mark.parametrize("variant", ["binding-missing", "binding-duplicate", "binding-double"])
def test_binding_mutations_refuse(variant):
    cp4 = next(m for m in SHIPPED_MAPS if m.module_id == "CP-4")
    entries = cp4.entries[1:] if variant == "binding-missing" else cp4.entries
    replacement = BindingMap(module_id="CP-4", entries=entries)
    maps = tuple(replacement if m.module_id == "CP-4" else m for m in SHIPPED_MAPS)
    if variant == "binding-duplicate":
        maps = (*maps, cp4)
    if variant == "binding-double":
        duplicate = Binding(
            fact_coord=FactCoord(module_id="CP-4", table_id="T4.9"),
            block_id="evidence",
            cell_slot="fixture-double",
            label="Fixture duplicate",
            unit_class="text",
        )
        maps = tuple(
            BindingMap(module_id="CP-4", entries=(*m.entries, duplicate))
            if m.module_id == "CP-4"
            else m
            for m in maps
        )
    with pytest.raises(ValueError):
        _report(_seed(), maps)


@pytest.mark.parametrize("variant", ["row-id", "text-copy", "empty-status", "empty-header"])
def test_copy_specific_malformed_shapes_refuse(variant):
    view = _empty_copy(_seed()) if variant.startswith("empty-") else _seed()
    module = _module(view)
    table = next(t for t in module.tables if t.table_id == "T4F.2")
    if variant == "empty-header":
        module = module.model_copy(
            update={
                "tables": tuple(
                    t.model_copy(update={"row_header": "CP-1 figure"})
                    if t.table_id == "T4F.2"
                    else t
                    for t in module.tables
                )
            }
        )
    elif variant == "row-id":
        module = module.model_copy(
            update={
                "facts": tuple(
                    f.model_copy(update={"row_id": "foreign"}) if f.table_id == "T4F.2" else f
                    for f in module.facts
                ),
                "tables": tuple(
                    t.model_copy(
                        update={"rows": (table.rows[0].model_copy(update={"row_id": "foreign"}),)}
                    )
                    if t.table_id == "T4F.2"
                    else t
                    for t in module.tables
                ),
            }
        )
    else:
        updates = (
            {"amount": None, "text": "Fixture nonnumeric copy"}
            if variant == "text-copy"
            else {"status": "missing"}
        )
        module = _module(_fact(view, table.rows[0].fact_ids[0], **updates))
    with pytest.raises(ValueError):
        _report(_replace(view, module))


def test_native_pp_and_other_current_dimensions_preserve_supplied_values():
    view = _fact(_seed(), "T4.9.r01.headroom", amount=Decimal("5.00"), unit="pp")
    view = _fact(
        view,
        "T4.9.r01.current",
        amount=Decimal("1.25"),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        decimals=2,
    )
    block = _blocks(_report(view))["covenant-tests-headroom"]
    assert block.rows[0].cells[5].text == "5.00 pp"
    current = next(f for f in _module(view).facts if f.fact_id == "T4.9.r01.current")
    assert (current.amount, current.unit, current.currency, current.scale, current.decimals) == (
        Decimal("1.25"),
        "MILLIONS",
        "USD",
        Decimal(1000000),
        2,
    )


@pytest.mark.parametrize("status", ["blocked", "stale"])
def test_nonshown_empty_actual_view_shape_may_retain_artifact_identity(status):
    view = _seed()
    module = _module(view).model_copy(
        update={"status": status, "facts": (), "tables": (), "claims": ()}
    )
    assert module.artifact_sha256 is not None
    assert _blocks(_report(_replace(view, module)))["capacity"].state != "populated"
