"""CP-1D earnings quality -> the two FP 02 blocks it owns and the evidence and limitations rails.

``earnings-quality`` shows the add-back assessment (T1D.2), the adjusted EBITDA bridge (T1D.3)
and the add-back share (T1D.5) as tabs; ``restated-leverage`` shows cash conversion and restated
leverage (T1D.6). The add-back register (T1D.1), the tie-out (T1D.4) and the CP-1 references go to
Evidence; the gaps ledger (T1D.7) to Limitations. Data only: identities and labels, no arithmetic.
Slots carry a ``cp1d-`` prefix: a slot is unique across all shipped maps.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-1D"
BLOCKS = ("earnings-quality", "restated-leverage")


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp1d-" + table.lower().replace(".", "-"),
        unit_class=unit,
        label=label,
    )


CP1D = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The two FP 02 blocks.
        _bind("T1D.2", "earnings-quality", "Add-back assessment"),
        _bind("T1D.3", "earnings-quality", "Adjusted EBITDA bridge", "amount"),
        _bind("T1D.5", "earnings-quality", "Add-back share", "percent"),
        _bind("T1D.6", "restated-leverage", "Cash conversion and restated leverage", "multiple"),
        # Evidence.
        _bind("T1D.1", "evidence", "Add-back register"),
        _bind("T1D.4", "evidence", "Source tie-out and CP-1 reconciliation"),
        _bind("cp1_references", "evidence", "CP-1 figures referenced in CP-1D", "amount"),
        # Limitations.
        _bind("T1D.7", "limitations", "CP-1D gaps ledger"),
    ),
)
