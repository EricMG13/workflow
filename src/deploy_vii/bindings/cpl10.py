"""CP-L10 financial change screen -> the Evidence and Limitations rails (lease D7, rails only).

CP-L10 owns no Front Page block (no Pathway lists it). TL10.1 scope and sources, TL10.2 topic
screen, TL10.5 screen totals (the same block as TL10.2) and TL10.3 screen items go to Evidence;
TL10.4 upgrade triggers goes to Limitations. Slots carry a ``cpl10-`` prefix: a slot is unique
across all shipped maps. Data only: no arithmetic, no ``deploy_workflow`` import.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-L10"


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cpl10-" + table.lower().replace(".", "-"),
        unit_class=unit,
        label=label,
    )


CPL10 = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("TL10.1", "evidence", "Change screen scope and sources"),
        _bind("TL10.2", "evidence", "Change screen by topic"),
        _bind("TL10.5", "evidence", "Change screen totals", "amount"),
        _bind("TL10.3", "evidence", "Change screen items"),
        _bind("TL10.4", "limitations", "Change screen upgrade triggers"),
    ),
)
