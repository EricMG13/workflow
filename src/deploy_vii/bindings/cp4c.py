"""CP-4C restructuring fulcrum -> the two Distressed & Restructuring blocks and the rails.

CP-4C fills two FP 05 blocks that already exist in the ``distressed_restructuring`` preset
(lease D7, ``BLOCKS``): ``recovery-by-class`` (T4E.5 recovery, T4E.7 fulcrum, T4E.8 plan
treatment) and ``value-allocation-claims`` (T4E.2 claims, T4E.3 valuation, T4E.4 waterfall, T4E.6
attachment). T4E.1, T4E.9 and the four reference tables go to Evidence, T4E.10 to Limitations.
Slots carry a ``cp4c-`` prefix: a slot is unique across all shipped maps. Data only: no
arithmetic, and ``deploy_workflow`` is never imported.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-4C"
BLOCKS = ("recovery-by-class", "value-allocation-claims")


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp4c-" + table.lower().replace(".", "-").replace("_", "-"),
        unit_class=unit,
        label=label,
    )


CP4C = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The two FP 05 blocks, tabs in the oracle's order.
        _bind("T4E.5", "recovery-by-class", "Recovery", "percent"),
        _bind("T4E.7", "recovery-by-class", "Fulcrum"),
        _bind("T4E.8", "recovery-by-class", "Plan treatment"),
        _bind("T4E.2", "value-allocation-claims", "Claims", "amount"),
        _bind("T4E.3", "value-allocation-claims", "Valuation", "amount"),
        _bind("T4E.4", "value-allocation-claims", "Waterfall", "amount"),
        _bind("T4E.6", "value-allocation-claims", "Attachment", "multiple"),
        # Evidence.
        _bind("T4E.1", "evidence", "Upstream register"),
        _bind("T4E.9", "evidence", "Waterfall totals", "amount"),
        _bind(CP1_REFERENCES, "evidence", "CP-1 facts referenced in CP-4C"),
        _bind("cp2a_references", "evidence", "CP-2A facts copied into CP-4C"),
        _bind("cp2g_references", "evidence", "CP-2G facts copied into CP-4C"),
        _bind("cp4_references", "evidence", "CP-4 facts copied into CP-4C"),
        # Limitations.
        _bind("T4E.10", "limitations", "CP-4C gaps ledger"),
    ),
)
