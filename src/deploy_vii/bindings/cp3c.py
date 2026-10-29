"""CP-3C refinancing and liability-management risk -> the Refinancing paths and LME capacity
and creditor exposure blocks, rails.

FP 04 ("Covenant & Refinancing") composes ``refinancing-paths`` and ``lme-creditor-exposure``;
CP-3C fills them (docs/CP3C-OWNER-LEASE.md, Rendered sections). The path judgments (T3D.6) lead
the paths block, with the burden and the cost sensitivity as its tabs; the
LME capacity (T3D.5) leads the collapsed exposure block, with the creditor position as its tab.
The analyst judgments and the upstream trace go to Evidence, the gaps ledger to Limitations.
CP-3C binds the need by maturity (T3D.1) into CP-2D's ``funding-gap`` and registers no
``maturity-wall`` (CP-2D's; lease open question 2).
Data only: no arithmetic, and nothing from ``deploy_workflow`` is imported. Slots carry a
``cp3c-`` prefix: a slot is unique across all shipped maps.
"""

from deploy_vii.bindings import Binding, BindingMap
from deploy_vii.report_view import FactCoord

MODULE_ID = "CP-3C"
BLOCKS = ("refinancing-paths", "lme-creditor-exposure", "funding-gap")


def _bind(table: str, block: str, label: str) -> Binding:
    return Binding(
        fact_coord=FactCoord(module_id=MODULE_ID, table_id=table),
        block_id=block,
        cell_slot="cp3c-" + table.lower().replace(".", "-"),
        unit_class="text",
        label=label,
    )


CP3C = BindingMap(
    module_id=MODULE_ID,
    entries=(
        _bind("T3D.6", "refinancing-paths", "Refinancing paths"),
        _bind("T3D.2", "refinancing-paths", "Refinancing burden"),
        _bind("T3D.3", "refinancing-paths", "Refinancing cost sensitivity"),
        _bind("T3D.5", "lme-creditor-exposure", "LME capacity"),
        _bind("T3D.4", "lme-creditor-exposure", "Creditor position"),
        # Funding gap (CP-2D's block): the need by maturity is its tab and CR.3 draws from it. It
        # moved here from refinancing-paths (Stage 3 ruling item 6.1): one fact is never bound to
        # two blocks of a Pathway.
        _bind("T3D.1", "funding-gap", "Refinancing need by maturity"),
        # Evidence.
        _bind("T3D.7", "evidence", "Analyst judgments"),
        _bind("T3D.9", "evidence", "Upstream trace"),
        # Limitations.
        _bind("T3D.8", "limitations", "Gaps ledger"),
    ),
)
