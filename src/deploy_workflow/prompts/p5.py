"""Phase 5 Task 1: the CP-0 prompt states the draft and context authority rule.

``readiness.context_authority_issues`` refuses a ``draft`` assessment unless the run's context
declares draft legal documents, and refuses ``executed``, ``filed`` or ``draft`` on the ``context``
source. The statement follows the G8 line in every composed ``source_readiness`` message.
"""

__all__ = ["P5_RULE_ID", "P5_STATEMENT"]

P5_RULE_ID = "source_readiness.p5"
P5_STATEMENT = (
    "Assess a source as draft only when the run's context declares draft legal documents "
    "(`legal_documents: draft`). The `context` source is never assessed as executed, filed or draft."
)
