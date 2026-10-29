"""Support for the CR.2 and CR.3 chart tests (Stage 3 chart wiring W2, group c).

Every expected value is read from the frozen oracles ``cases/charts/cr2-expected.json`` and
``cases/charts/cr3-expected.json``; nothing here derives one. The views are real ones: the CP-2D
head is settled by the real CP-2D core over its frozen literal, the CP-3C head by the real CP-3C
core (``test_connect_cp2d`` / ``test_connect_cp3c`` drivers, no CP-1 promotion). The composer
fixtures of CR.3 carry no tables, so their T3D.1 register is laid out here from the composer's own
maturity rows (``cp3c.compose_refinancing``), the way the CP-3C table builder lays it out.
"""

import json
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import test_connect_cp2d as tc2d
import test_connect_cp3c as tc3
import test_method_cp3c as tm3

from deploy_vii import report_view
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, ModuleView, View
from deploy_vii.report_view import Block, Figure, ReportView
from deploy_workflow.owners import cp3c

ROOT = Path(__file__).resolve().parents[1]
CR2: dict[str, Any] = json.loads((ROOT / "cases/charts/cr2-expected.json").read_text("utf-8"))
CR3: dict[str, Any] = json.loads((ROOT / "cases/charts/cr3-expected.json").read_text("utf-8"))
CR2_FIG = CR2["chart_series"]["CR.2"]
CR3_FIG = CR3["chart_series"]["CR.3"]
CR2_CASES = ("positive", "long_horizon", "gap_minimum_cash")
CR3_PACK_CASES = ("positive", "gap_minimum_cash", "gap_no_repricing")
CR3_FIXTURES = (
    "fixture_two_facilities",
    "fixture_burn",
    "fixture_amortisation_missing",
    "fixture_long_horizon",
)
SETTLED = ("accepted", "restricted")


def module_of(view: View, module_id: str) -> ModuleView:
    return next(m for m in view.modules if m.module_id == module_id)


def cp2d_view(case: str, root: Path | None = None) -> View:
    """The covenant_refinancing view whose CP-2D head is the real core's over ``case``."""
    store, attempt = tc2d.make_upstream(root or Path(tempfile.mkdtemp()), case)
    tc2d._submit(store, attempt, tc2d._literal(case))
    return store.view()


def cp3c_view(case: str, root: Path | None = None) -> View:
    """The covenant_refinancing view with the real CP-2D and CP-3C heads settled for ``case``."""
    store, _, _, _ = tc3.settled(root or Path(tempfile.mkdtemp()), case)
    return store.view()


def report_of(view: View, pathway_id: str | None = None) -> ReportView:
    """``report_view.build`` over the shipped maps; ``pathway_id`` re-targets the same view."""
    if pathway_id is not None and pathway_id != view.run.pathway:
        run = view.run.model_copy(update={"pathway": pathway_id})
        view = view.model_copy(update={"run": run})
    pathway = next(p for p in report_view.pathways() if p.id == view.run.pathway)
    return report_view.build(view, pathway, SHIPPED_MAPS)


def block_of(report: ReportView, block_id: str) -> Block:
    return next(b for b in report.blocks if b.block_id == block_id)


def figure_of(block: Block, fig_id: str) -> Figure:
    return next(f for f in block.figures if f.fig_id == fig_id)


def tab_labels(block: Block) -> list[str | None]:
    """The block's register labels in order: the primary register, then its tabs."""
    return [block.tab_label, *(tab.label for tab in block.tabs)]


def labels_of(*table_ids: str) -> list[str | None]:
    """The binding labels of the oracle's table ids (the oracle names tabs by table id)."""
    by_table = {
        entry.fact_coord.table_id: entry.label for m in SHIPPED_MAPS for entry in m.entries
    }
    return [by_table[table_id] for table_id in table_ids]


def decimal_or_none(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def oracle_points(expected: dict[str, Any]) -> list[tuple[Any, ...]]:
    """(series, category, fact_id, companions, shown, value) of an oracle figure."""
    return [
        (
            p["series"],
            p["category"],
            p["fact_id"],
            tuple(p["companion_fact_ids"]),
            p["shown"],
            decimal_or_none(p["value"]),
        )
        for p in expected["points"]
    ]


def record_points(record: Any) -> list[tuple[Any, ...]]:
    return [
        (p.series, p.category, p.fact_id, tuple(p.companion_fact_ids), p.shown, p.value)
        for p in record.points
    ]


def record_meta(record: Any) -> dict[str, Any]:
    return {
        "fig_id": record.fig_id,
        "title": record.title,
        "kind": record.kind,
        "unit_class": record.unit_class,
        "unit": record.unit,
        "series": list(record.series),
        "reason": record.reason,
    }


def oracle_meta(expected: dict[str, Any]) -> dict[str, Any]:
    keys = ("fig_id", "title", "kind", "unit_class", "unit", "series", "reason")
    return {k: expected[k] for k in keys}


def twin_rows(figure: Figure) -> list[tuple[str, list[str]]]:
    return [(r.label, [c.text for c in r.cells]) for r in figure.chart.table_twin.rows]


def oracle_twin(twin: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return [(r["label"], r["cells"]) for r in twin["rows"]]


# --- the composer fixtures of CR.3 ------------------------------------------------------------


@dataclass(frozen=True)
class FixtureRegister:
    module: ModuleView
    facility_ids: tuple[str, ...]


def _fact(fact_id: str, label: str, value: cp3c.Num, *, balance: str) -> Fact:
    row, field = fact_id.split(".")[2:4]
    common: dict[str, Any] = {
        "fact_id": fact_id,
        "label": label,
        "table_id": "T3D.1",
        "row_id": row,
        "field": field,
        "value_class": "calculated",
    }
    if isinstance(value, cp3c.Gap):
        return Fact(
            **common,
            status="missing",
            unit="MILLIONS",
            currency="USD",
            scale=Decimal(1000000),
            limitation=value.reason,
        )
    return Fact(
        **common,
        amount=value,
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period=balance,
    )


def fixture_register(name: str) -> FixtureRegister:
    """The T3D.1 register of a composer fixture: one row per facility in the composer's order,
    holding the maturity date (c2), months (c3), principal payable (c6) and resources (c7)."""
    from deploy_vii.contracts import ReportTable, TableColumn, TableRow

    operands, step_up = tm3._fixture_operands(name)
    refinancing = cp3c.compose_refinancing(operands=operands, step_up_bps=step_up)
    balance = tm3.BALANCE_DATE.isoformat()
    facts: list[Fact] = []
    rows: list[TableRow] = []
    ids: list[str] = []
    for n, maturity in enumerate(refinancing.maturities, 1):
        row = f"r{n:02d}"
        facility = maturity.facility
        coords = (
            ("c2", "Maturity date", None, facility.maturity_date.isoformat()),
            ("c3", "Months", facility.months, None),
            ("c6", "Principal payable at maturity (US$ m)", maturity.principal_payable, None),
            ("c7", "Resources at maturity (US$ m)", maturity.resources, None),
        )
        for field, label, value, text in coords:
            fact_id = f"T3D.1.{row}.{field}"
            if text is not None:
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        label=label,
                        table_id="T3D.1",
                        row_id=row,
                        field=field,
                        text=text,
                        value_class="source",
                    )
                )
            elif field == "c3":
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        label=label,
                        table_id="T3D.1",
                        row_id=row,
                        field=field,
                        amount=Decimal(facility.months),
                        unit="months",
                        period=balance,
                        value_class="calculated",
                    )
                )
            else:
                assert value is not None
                facts.append(_fact(fact_id, label, value, balance=balance))
        ids.append(facility.facility_id)
        rows.append(
            TableRow(
                row_id=row,
                label=facility.facility_id,
                fact_ids=tuple(f"T3D.1.{row}.{f}" for f in ("c2", "c3", "c6", "c7")),
            )
        )
    table = ReportTable(
        table_id="T3D.1",
        title="Refinancing need by maturity",
        columns=tuple(TableColumn(field=f, label=f) for f in ("c2", "c3", "c6", "c7")),
        rows=tuple(rows),
        row_header="Facility",
    )
    module = ModuleView(
        module_id="CP-3C",
        title="Refinancing and liability-management risk",
        aliases=(),
        status="restricted",
        artifact_sha256="0" * 64,
        facts=tuple(facts),
        tables=(table,),
    )
    return FixtureRegister(module=module, facility_ids=tuple(ids))
