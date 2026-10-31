"""H03: CP-L10 TL10.4 `decision_impact` is stored with the analyst's `{TL10.2...}` reference
tokens (it reuses TL10.3 `credit_transmission`, which `cpl10._text_issues` validates), so the
report view resolves it like TL10.3 and shows the figure, never the raw token."""

from test_connect_cpl10 import _tl10_3_facts, _tl10_3_page


def test_tl10_4_decision_impact_shows_the_figure_not_the_reference() -> None:
    _, topic, facts = _tl10_3_facts()
    page = _tl10_3_page(facts)
    transmission = page[f"TL10.3.{topic}.credit_transmission"]
    impact = page[f"TL10.4.{topic}.decision_impact"]
    for key in ("display", "table_display"):
        assert "{" not in impact[key]
        assert "3.75 US$ m" in impact[key]
        assert impact[key] == transmission[key]
