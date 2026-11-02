"""Undo the B29 wording change in CP-3's composed message (ruling B29): the method text and rule d
name the context-row basis `basis.context_rows` beside `basis.quotes`; shared by test_g8.py and
test_texts_loader.py. Wording only: removing exactly these two spans gives the message the digest
pinned before B29."""

# docs/rulings/2026-10-31-context-plan.md B29: src/deploy_vii/methods/cp3.md, the sentence added after
# "(copy that row's quote into `basis.quotes`)."
METHOD_SPAN = (
    " A run with a\ncontext file also offers Python's context rows: a basis cites one by its row id in\n"
    "`basis.context_rows` and never copies its figures."
)
# B29: CP3_BASIS_RULE (rule d) in src/deploy_vii/live/prompts.py, the words added after
# "a `basis.quotes` market quote".
RULE_D_SPAN = " or a context row named in `basis.context_rows`"
B29_SPANS: dict[str, tuple[tuple[str, int, str], ...]] = {
    "relative_value": ((METHOD_SPAN, 1, ""), (RULE_D_SPAN, 1, "")),
}


def undo_b29(step_id: str, text: str) -> str:
    """Remove the B29 wording from a composed message (relative_value only)."""
    for span, count, replacement in B29_SPANS.get(step_id, ()):
        assert text.count(span) == count, (step_id, span)
        text = text.replace(span, replacement)
    return text
