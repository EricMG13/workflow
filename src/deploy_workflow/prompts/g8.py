"""G8 (O6 Task 5): the CP-0 prompt states the run's exact planned module set.

The set is ``live_consumers(pack)``, never a literal. Python writes each consumer's
``exact_command`` (``readiness._exact_command``); a lower readiness is a valid outcome that
execution refuses (``NotAuthorized``) and O3 journals as ``RefusedBegin.missing_commands``, so
this block adds no fault type: it only tells the model what its judgments will do.
"""

from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import live_consumers

__all__ = ["G8_RULE_ID", "G8_STATEMENT", "module_set_statement"]

G8_RULE_ID = "source_readiness.g8"
# The text of rule source_readiness.g8: it follows the module list in every composed message.
G8_STATEMENT = (
    'Write one consumer judgment for each. Python writes "Run <id>" for READY or '
    "READY_WITH_LIMITATIONS; any lower readiness refuses that module in this run, and every "
    "planned module that depends on it."
)


def module_set_statement(pack: PreparedPack) -> str:
    """The exact sentence block for ``source_readiness``: the planned modules, then the rule."""
    planned = ", ".join(live_consumers(pack)) or "none"
    return f"The planned modules are exactly {planned}. {G8_STATEMENT}"
