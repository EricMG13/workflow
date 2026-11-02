"""CP1B paired earnings and analytical gaps -> FP02 and existing evidence rails.

Layout metadata contains identities and labels, never financial answers. Whole
paired tables preserve their columns; the assessment table is partitioned by row
so no fact is bound twice in one pathway. Rail bindings provide coverage; actual
source inventory and module limitations keep their existing rendering behavior.
"""

from dataclasses import dataclass, replace

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord


@dataclass(frozen=True)
class _Layout:
    table_id: str
    title: str
    row_header: str
    fields: tuple[str, ...]
    rows: tuple[tuple[str, str], ...]


_LAYOUT_TEMPLATES = (
    _Layout(
        "T1B.1",
        "Paired earnings results",
        "Measure",
        ("prior", "current", "delta", "growth"),
        (
            ("revenue", "Revenue ({unit})"),
            ("ebitda", "Reported EBITDA ({unit})"),
            ("adjusted_ebitda", "Adjusted EBITDA ({unit})"),
            ("ebitda_margin", "EBITDA margin (%; change pp)"),
            ("cfo_reported", "Reported CFO ({unit})"),
            ("capex", "Signed capex ({unit})"),
            ("fcf", "Levered FCF ({unit})"),
        ),
    ),
    _Layout(
        "T1B.2",
        "Balance changes",
        "Measure",
        ("prior", "current", "delta"),
        (
            ("cash_closing", "Closing cash ({unit})"),
            ("total_debt", "Total debt ({unit})"),
            ("net_debt", "Net debt ({unit})"),
        ),
    ),
    _Layout(
        "T1B.3",
        "Evidence and analytical gaps",
        "Assessment",
        ("assessment",),
        (
            ("variance.summary", "Numerical comparison"),
            ("drivers", "Driver evidence"),
            ("guidance", "Guidance evidence"),
            ("comparative.prior-year", "Prior-year comparison"),
            ("comparative.trailing-leverage", "Leverage comparison"),
            ("evidence.inputs", "Selected input evidence"),
            ("scope.limitations", "Scope limitations"),
        ),
    ),
)


def cp1b_layouts(unit: str = "US$ m") -> tuple[_Layout, ...]:
    """The three layouts with the nine money labels stated in ``unit`` (e.g. ``EUR m``)."""
    return tuple(
        replace(layout, rows=tuple((row, label.format(unit=unit)) for row, label in layout.rows))
        for layout in _LAYOUT_TEMPLATES
    )


_CP1B_LAYOUTS = cp1b_layouts()


def _bind(
    table: str, block: str, slot: str, label: str, unit: UnitClass = "text", row: str | None = None
) -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id="CP-1B", table_id=table, row_id=row),
        block_id=block,
        cell_slot=slot,
        label=label,
        unit_class=unit,
    )


CP1B = BindingMap(
    module_id="CP-1B",
    entries=(
        _bind("T1B.1", "headline-results", "cp1b-paired-earnings", "Paired earnings results"),
        _bind("T1B.2", "kpi-changes", "cp1b-balance-changes", "Balance changes", "amount"),
        _bind(
            "T1B.3",
            "variance-drivers",
            "cp1b-variance-summary",
            "Numerical comparison",
            row="variance.summary",
        ),
        _bind("T1B.3", "variance-drivers", "cp1b-drivers", "Driver evidence", row="drivers"),
        _bind("T1B.3", "guidance-signals", "cp1b-guidance", "Guidance evidence", row="guidance"),
        _bind(
            "T1B.3",
            "limitations",
            "cp1b-prior-year-gap",
            "Prior-year comparison",
            row="comparative.prior-year",
        ),
        _bind(
            "T1B.3",
            "limitations",
            "cp1b-trailing-leverage-gap",
            "Leverage comparison",
            row="comparative.trailing-leverage",
        ),
        _bind(
            "T1B.3",
            "evidence",
            "cp1b-input-evidence",
            "Selected input evidence",
            row="evidence.inputs",
        ),
        _bind(
            "T1B.3",
            "limitations",
            "cp1b-scope-limitations",
            "Scope limitations",
            row="scope.limitations",
        ),
    ),
)
