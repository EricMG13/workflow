"""Undo the Phase 5 Task 1 rule line in CP-0's composed message (ruling P5T1-R6): the line
``[source_readiness.p5] <statement>`` that follows the G8 line in every composed source_readiness
message, and the JSON-schema text of `SourceAssessment.authority`, which the Task 1 code commit
widened from the `Authority` enum to that enum or `"draft"` (B7). Removing exactly these two spans
gives the message the digest pinned after B30."""

from deploy_workflow.prompts.p5 import P5_RULE_ID, P5_STATEMENT

P5_LINE = f"[{P5_RULE_ID}] {P5_STATEMENT}\n"
_ENUM = '"enum":["filed","executed","issuer","management","sponsor","third_party","unknown"]'
# The `authority` property of `SourceAssessment` in the schema the message carries.
SCHEMA_NEW = f'"authority":{{"anyOf":[{{{_ENUM},"type":"string"}},{{"enum":["draft"],"type":"string"}}],"title":"Authority"}}'
SCHEMA_OLD = f'"authority":{{{_ENUM},"title":"Authority","type":"string"}}'


def undo_p5(step_id: str, text: str) -> str:
    """Remove the P5 line from a composed message (source_readiness only)."""
    if step_id != "source_readiness":
        return text
    assert text.count(P5_LINE) == 1 and text.count(SCHEMA_NEW) == 1, step_id
    return text.replace(P5_LINE, "").replace(SCHEMA_NEW, SCHEMA_OLD)
