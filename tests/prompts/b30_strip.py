"""Undo the B30 wording change in CP-3's composed message (ruling B30): the market-observation and
preference rules, the method text and the `Basis` schema text name the context-row basis
`basis.context_rows` beside the market quote; shared by test_g8.py, test_context_evidence.py and
test_texts_loader.py. Wording only: removing exactly these spans gives the message the digest
pinned after B29. Undo B30 before B29: B29's spans overlap the text B30 extends."""

# docs/rulings/2026-10-31-context-plan.md B30: src/deploy_vii/methods/cp3.md, the words added after
# "(copy that row's quote into `basis.quotes`)".
METHOD_SPAN = " or, in a run\nwith a context file, names a context row in `basis.context_rows`"
# B30: CP3_BASIS_RULE (rule d), the words added to its market_observation clause.
RULE_D_SPAN = (
    "a `market_observation` other than none cites a market quote or a context row named in "
    "`basis.context_rows`."
)
RULE_D_OLD = "a `market_observation` other than none cites a market quote."
# B30: CP3_PREFERENCE_RULE (rule e), the words added to its citation clause.
RULE_E_SPAN = "it cites a market quote or a context row named in `basis.context_rows`;"
RULE_E_OLD = "it cites a market quote;"
# B30: the `Basis` docstring and the `context_rows` description in the JSON schema the message
# carries (a JSON string, so the line breaks are the two characters backslash and n).
BASIS_DOC_SPAN = (
    ", market-evidence quotes (copied from `market_evidence` rows)\\nand, in a run with a context "
    "file, Python's context market-evidence rows (`context_rows`);\\nits CP-1 basis is the "
    "figure references in its text."
)
BASIS_DOC_OLD = (
    " and market-evidence quotes (copied from `market_evidence`\\nrows); its CP-1 basis is the "
    "figure references in its text."
)
CONTEXT_ROWS_SPAN = (
    '"description":"Python\'s context market-evidence row ids, cited by id; figures never copied.",'
)
B30_SPANS: dict[str, tuple[tuple[str, int, str], ...]] = {
    "relative_value": (
        (METHOD_SPAN, 1, ""),
        (RULE_D_SPAN, 1, RULE_D_OLD),
        (RULE_E_SPAN, 1, RULE_E_OLD),
        (BASIS_DOC_SPAN, 1, BASIS_DOC_OLD),
        (CONTEXT_ROWS_SPAN, 1, ""),
    ),
}


def undo_b30(step_id: str, text: str) -> str:
    """Remove the B30 wording from a composed message (relative_value only)."""
    for span, count, replacement in B30_SPANS.get(step_id, ()):
        assert text.count(span) == count, (step_id, span)
        text = text.replace(span, replacement)
    return text
