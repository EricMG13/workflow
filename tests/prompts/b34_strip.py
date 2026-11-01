"""Undo the B34 wording change in CP-3's composed message (ruling B34): the preference line under
"What to return" in the method text names the context-row basis `basis.context_rows` beside the
market evidence quote; shared by test_g8.py, test_context_evidence.py and test_texts_loader.py.
Wording only: removing exactly this span gives the message the digest pinned after B30. Undo B34
before B30 and B29."""

# docs/rulings/2026-10-31-context-plan.md B34: src/deploy_vii/methods/cp3.md, the words added after
# "(at least one market\n  evidence quote" in the `preference` line.
PREFERENCE_SPAN = " or a context row named in\n  `basis.context_rows`"
B34_SPANS: dict[str, tuple[tuple[str, int, str], ...]] = {
    "relative_value": ((PREFERENCE_SPAN, 1, ""),),
}


def undo_b34(step_id: str, text: str) -> str:
    """Remove the B34 wording from a composed message (relative_value only)."""
    for span, count, replacement in B34_SPANS.get(step_id, ()):
        assert text.count(span) == count, (step_id, span)
        text = text.replace(span, replacement)
    return text
