"""CP-2D liquidity bridge -> the Liquidity runway, Maturity wall and Funding gap blocks, rails.

FP 04 ("Covenant & Refinancing") composes ``liquidity-runway``, ``maturity-wall`` and
``funding-gap``; CP-2D fills them (docs/CP2D-OWNER-LEASE.md, Rendered sections). Sources and uses
(T2E.1) is the second tab of the runway, the liquidity position (T2E.2) the second tab of the
funding gap. The analyst judgments and the CP-1 source trace go to Evidence, the gaps ledger to
Limitations. Data only: no arithmetic, and nothing from ``deploy_workflow`` is imported. Slots
carry a ``cp2d-`` prefix: a slot is unique across all shipped maps.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-2D"
BLOCKS = ("liquidity-runway", "maturity-wall", "funding-gap")


def _bind(table: str, block: str, label: str) -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp2d-" + table.lower().replace(".", "-"),
        unit_class="text",
        label=label,
    )


CP2D = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("T2E.3", "liquidity-runway", "Cash runway"),
        _bind("T2E.1", "liquidity-runway", "Sources and uses"),
        _bind("T2E.4", "maturity-wall", "Maturity wall"),
        _bind("T2E.5", "funding-gap", "Funding gap"),
        _bind("T2E.2", "funding-gap", "Liquidity position"),
        # Evidence.
        _bind("T2E.6", "evidence", "Analyst judgments"),
        _bind("T2E.9", "evidence", "CP-1 source trace"),
        # Limitations.
        _bind("T2E.7", "limitations", "Gaps ledger"),
    ),
)
