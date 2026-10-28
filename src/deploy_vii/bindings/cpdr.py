"""CP-DR deep research -> the Evidence and Limitations rails only (lease D-C, D7, D8).

No Front Page block shows CP-DR and no pathway lists it: the research agenda with its gap status
(TDR.1) and the questions with their cited answers (TDR.2) go to Evidence, the coverage totals
(TDR.3) to Limitations. Slots carry a ``cpdr-`` prefix: a slot is unique across all shipped maps.
Data only; it reads facts by table id and never imports ``deploy_workflow``.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-DR"


def _bind(table: str, block: str, label: str) -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cpdr-" + table.lower().replace(".", "-"),
        unit_class="text",
        label=label,
    )


CPDR = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("TDR.1", "evidence", "Research agenda and gap status"),
        _bind("TDR.2", "evidence", "Research questions and cited answers"),
        _bind("TDR.3", "limitations", "Research coverage totals"),
    ),
)
