"""CP-2H rating triggers -> the Distressed & Restructuring ``rating-triggers`` block and the rails.

FP 05 already lists ``rating-triggers`` (lease D7); CP-2H fills it with six tabs: T2R.9 trigger
summary, T2R.4 current headroom, T2R.5 forward headroom, T2R.6 trigger timing, T2R.7 migration
view and T2R.8 agency divergence. T2R.1-T2R.3 and the two reference tables go to Evidence, T2R.10
to Limitations. Slots carry a ``cp2h-`` prefix: a slot is unique across all shipped maps. Data
only: no arithmetic, and ``deploy_workflow`` is never imported.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-2H"
BLOCK = "rating-triggers"


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp2h-" + table.lower().replace(".", "-").replace("_", "-"),
        unit_class=unit,
        label=label,
    )


CP2H = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The FP 05 block, tab order as the lease decides it.
        _bind("T2R.9", BLOCK, "Summary"),
        _bind("T2R.4", BLOCK, "Current headroom", "multiple"),
        _bind("T2R.5", BLOCK, "Forward headroom", "multiple"),
        _bind("T2R.6", BLOCK, "Trigger timing"),
        _bind("T2R.7", BLOCK, "Migration view"),
        _bind("T2R.8", BLOCK, "Agency divergence"),
        # Evidence.
        _bind("T2R.1", "evidence", "Upstream register"),
        _bind("T2R.2", "evidence", "Agency rating register"),
        _bind("T2R.3", "evidence", "Published trigger terms", "multiple"),
        _bind(CP1_REFERENCES, "evidence", "CP-1 facts referenced in CP-2H text", "multiple"),
        _bind("cp2g_references", "evidence", "CP-2G facts copied into CP-2H", "multiple"),
        # Limitations.
        _bind("T2R.10", "limitations", "CP-2H gaps ledger"),
    ),
)
