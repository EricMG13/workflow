"""CP-2G forward credit model -> the two Distressed & Restructuring blocks and the rails.

CP-2G has no Front Page block of its own in the design (lease D7); it fills two new FP 05 blocks
(``BLOCKS``): ``forward-credit-path`` (T2H.4 operating forecast, T2H.5 debt and cash, T2H.6
credit metrics) and ``forward-breakpoints`` (T2H.7 break-point timing, T2H.8 deleveraging path).
T2H.1-T2H.3 and the three reference tables go to Evidence, T2H.9 to Limitations. Slots carry a
``cp2g-`` prefix: a slot is unique across all shipped maps. Data only: no arithmetic, and
``deploy_workflow`` is never imported.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-2G"
BLOCKS = ("forward-credit-path", "forward-breakpoints")


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp2g-" + table.lower().replace(".", "-").replace("_", "-"),
        unit_class=unit,
        label=label,
    )


CP2G = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The two FP 05 blocks.
        _bind("T2H.4", "forward-credit-path", "Operating forecast", "amount"),
        _bind("T2H.5", "forward-credit-path", "Debt and cash", "amount"),
        _bind("T2H.6", "forward-credit-path", "Credit metrics", "multiple"),
        _bind("T2H.7", "forward-breakpoints", "Break-point timing"),
        _bind("T2H.8", "forward-breakpoints", "Deleveraging path", "multiple"),
        # Evidence.
        _bind("T2H.1", "evidence", "Upstream register"),
        _bind("T2H.2", "evidence", "Historical-to-base bridge", "amount"),
        _bind("T2H.3", "evidence", "Assumption register", "percent"),
        _bind(CP1_REFERENCES, "evidence", "CP-1 facts referenced in CP-2G text"),
        _bind("cp2a_references", "evidence", "CP-2A facts copied into CP-2G"),
        _bind("cp1d_references", "evidence", "CP-1D facts copied into CP-2G"),
        # Limitations.
        _bind("T2H.9", "limitations", "CP-2G gaps ledger"),
    ),
)
