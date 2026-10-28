"""CP-2A downside pathway -> the two Distressed & Restructuring blocks and the rails.

FP 05 ("Distressed & Restructuring") has no downside block (lease D7); CP-2A fills two new ones
(``BLOCKS``), each with two tabs: ``downside-stress`` (T2B.3 earnings and cash flow, T2B.4 credit
metrics) and ``break-points`` (T2B.6 break-point register, T2B.7 first-break ranking). Every other
CP-2A table goes to Evidence or Limitations. Slots carry a ``cp2a-`` prefix: a slot is unique
across all shipped maps. Data only: no arithmetic, and ``deploy_workflow`` is never imported.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-2A"
BLOCKS = ("downside-stress", "break-points")


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp2a-" + table.lower().replace(".", "-").replace("_", "-"),
        unit_class=unit,
        label=label,
    )


CP2A = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The two FP 05 blocks.
        _bind("T2B.3", "downside-stress", "Earnings and cash flow", "amount"),
        _bind("T2B.4", "downside-stress", "Credit metrics", "multiple"),
        _bind("T2B.6", "break-points", "Break-point register", "percent"),
        _bind("T2B.7", "break-points", "First-break ranking"),
        # Evidence.
        _bind("T2B.1", "evidence", "Scenario register"),
        _bind("T2B.2", "evidence", "Base operands", "amount"),
        _bind("T2B.5", "evidence", "Base reconciliation", "multiple"),
        _bind("T2B.8", "evidence", "Scenario against break"),
        _bind(CP1_REFERENCES, "evidence", "CP-1 facts referenced in CP-2A text"),
        # Limitations.
        _bind("T2B.9", "limitations", "CP-2A gaps ledger"),
    ),
)
