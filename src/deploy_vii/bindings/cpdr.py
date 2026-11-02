"""CP-DR deep research -> the Evidence and Limitations rails only (lease D-C, D7, D8).

No Front Page block shows CP-DR and no pathway lists it: the locked questions and recipients
(TDR.1) and the claims with their located evidence (TDR.2) go to Evidence, the answers with their
contrary evidence, uncertainty and downstream use (TDR.3) to Limitations. The labels are the R7
table titles. Slots carry a ``cpdr-`` prefix: a slot is unique across all shipped maps.
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
        _bind("TDR.1", "evidence", "Locked questions and recipients"),
        _bind("TDR.2", "evidence", "Claims and located evidence"),
        _bind("TDR.3", "limitations", "Answers, contrary evidence, uncertainty and downstream use"),
        _bind("TDR.4", "evidence", "Candidate peers"),
        _bind("TDR.5", "evidence", "Provisional alignment observations"),
        _bind("TDR.6", "evidence", "Located peer/transaction figures"),
    ),
)
