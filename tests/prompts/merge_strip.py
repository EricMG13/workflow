"""Undo the restricted-cash change that the base merge cfe37c23 (merged as 8869ef55) brought into two
steps' composed messages (ruling M-R1 and M-R2); shared by test_g8.py and test_texts_loader.py."""

PRE_MERGE_REV = "0fc6eb35"  # the first parent of cfe37c23: src/deploy_vii before the change
MERGE_REV = "cfe37c23"
# Every stripped span contains one of these tokens, which cfe37c23 added to src/deploy_vii.
SPAN_TOKENS = ("restricted_cash_noncurrent", "cash_scope", "CashScope")

# Ruling M-R1 and M-R2: the base merge 8869ef55 added the restricted-cash balance-sheet ids and the cash-scope
# contract (src/deploy_vii/financial_contracts.py). They reach two steps' messages: the narrative
# contract line lists the new id, and the financials message lists it in its contract line and
# carries the output schema, which gained the id in two enums, the CashMovementBridge docstring
# sentence, its `cash_scope` property and `required` entry, and the CashScope definition. Undoing
# exactly those spans, for these two steps only, gives the message the old digest pins.
NARRATIVE_ID = ", `restricted_cash_noncurrent`"
FINANCIALS_ID = ", restricted_cash_noncurrent"
SCHEMA_ID = ',"restricted_cash_noncurrent"'
BRIDGE_DOC = (
    "\\n`cash_scope` is null unless the CFS cash line includes restricted cash; then it lists the"
    "\\nbalance-sheet restricted cash items (`restricted_cash`, `restricted_cash_noncurrent`) that"
    "\\nline adds to cash and equivalents, and the check sums every listed item's change."
)
CASH_SCOPE_PROPERTY = '"cash_scope":{"anyOf":[{"$ref":"#/$defs/CashScope"},{"type":"null"}]},'
CASH_SCOPE_REQUIRED = ',"cash_scope"]'
CASH_SCOPE_DEFINITION = (
    '"CashScope":{"additionalProperties":false,"description":"The balance-sheet lines, besides cash'
    " and equivalents, that the cash flow statement's cash\\nline includes. Cite the CFS cash line"
    ' and the source span that names restricted cash.","properties":{"citations":{"items":{"$ref":'
    '"#/$defs/Citation"},"minItems":1,"title":"Citations","type":"array"},"items":{"items":{"enum"'
    ':["restricted_cash","restricted_cash_noncurrent"],"type":"string"},"maxItems":2,"minItems":1,'
    '"title":"Items","type":"array"}},"required":["items","citations"],"title":"CashScope",'
    '"type":"object"},'
)
# (text, how many times the merged contract put it in the message, what it is replaced by)
MERGE_SPANS: dict[str, tuple[tuple[str, int, str], ...]] = {
    "narrative": ((NARRATIVE_ID, 1, ""),),
    "financials": (
        (FINANCIALS_ID, 1, ""),
        (CASH_SCOPE_DEFINITION, 1, ""),
        (SCHEMA_ID, 2, ""),
        (BRIDGE_DOC, 1, ""),
        (CASH_SCOPE_PROPERTY, 1, ""),
        (CASH_SCOPE_REQUIRED, 1, "]"),
    ),
}


def undo_merged_contract(step_id: str, text: str) -> str:
    """Remove the merged restricted-cash change from a composed message (financials, narrative)."""
    for span, count, replacement in MERGE_SPANS.get(step_id, ()):
        assert text.count(span) == count, (step_id, span)
        text = text.replace(span, replacement)
    return text
