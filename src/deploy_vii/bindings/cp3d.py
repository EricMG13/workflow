"""CP-3D market-implied risk -> the one FP 03 block it owns and the rails.

FP 03 ("Relative Value") gives CP-3D ``market-against-fundamentals`` (``docs/CP3D-OWNER-LEASE.md``,
"Rendered sections"): the market-implied default panel is populated, the alignment half is an
honest partial (the T3E.9 limitation says so). The six tabs follow the ruling's order, T3E.5
primary. ``instrument-levels`` stays CP-3's and ``yield-against-maturity`` is deferred (it needs a
reference rate level the pack does not state), so neither is bound here. T3E.10 is registered in
the method and unused. Data only: no arithmetic, and no import of ``deploy_workflow``. Slots carry
a ``cp3d-`` prefix: a slot is unique across all shipped maps.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-3D"
BLOCKS = ("market-against-fundamentals",)


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp3d-" + table.lower().replace(".", "-"),
        unit_class=unit,
        label=label,
    )


CP3D = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The six tabs of market-against-fundamentals, T3E.5 primary.
        _bind("T3E.5", "market-against-fundamentals", "Market-implied default"),
        _bind("T3E.4", "market-against-fundamentals", "Assumptions and terms"),
        _bind("T3E.6", "market-against-fundamentals", "Technicals"),
        _bind("T3E.1", "market-against-fundamentals", "Market levels"),
        _bind("T3E.2", "market-against-fundamentals", "Price metrics"),
        _bind("T3E.3", "market-against-fundamentals", "Spread and yield"),
        # Evidence.
        _bind("T3E.8", "evidence", "Evidence"),
        # Limitations.
        _bind("T3E.9", "limitations", "Limitations"),
        _bind("T3E.7", "limitations", "Missing inputs"),
    ),
)
