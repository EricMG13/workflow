"""CP-1C peer benchmark -> the one FP 03 block it owns and the evidence and limitations rails.

FP 03 ("Relative Value") gives CP-1C ``peer-positioning`` (``docs/CP1C-OWNER-LEASE.md``, D7): the
peer universe (T1C.1), the universe totals (T1C.8), the normalised metrics (T1C.3), the peer
statistics (T1C.4) and the outlier register (T1C.5) are its tabs in that order. The source figures
(T1C.2) and the definition alignment and tie-out (T1C.6) go to Evidence; the gaps ledger (T1C.7)
to Limitations. A table that mixes units (percent, multiple, pp, counts, text) is bound as
``text``; every cell is still spelled from its own fact. The reference's range strip (Fig. RV.3) is a chart and is not bound. Data only: no
arithmetic, and no import of ``deploy_workflow``. Slots carry a ``cp1c-`` prefix: a slot is unique
across all shipped maps.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-1C"
BLOCKS = ("peer-positioning",)


def _bind(table: str, block: str, label: str, unit: UnitClass = "text") -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp1c-" + table.lower().replace(".", "-"),
        unit_class=unit,
        label=label,
    )


CP1C = BindingMap(
    module_id=MODULE_ID,
    entries=(
        # The five tabs of peer-positioning (expected.json cases.<case>.FP03).
        _bind("T1C.1", "peer-positioning", "Peer universe"),
        _bind("T1C.8", "peer-positioning", "Peer universe totals"),
        _bind("T1C.3", "peer-positioning", "Normalised metrics"),
        _bind("T1C.4", "peer-positioning", "Peer statistics"),
        _bind("T1C.5", "peer-positioning", "Outlier register"),
        # Evidence.
        _bind("T1C.2", "evidence", "Peer source figures", "amount"),
        _bind("T1C.6", "evidence", "Definition alignment and tie-out"),
        # Limitations.
        _bind("T1C.7", "limitations", "CP-1C gaps ledger"),
    ),
)
