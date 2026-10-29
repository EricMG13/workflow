"""Stage 2 close release (round 13 addendum 3): `readiness.citation_issues` refuses a blank
quote, whatever the span holds. `quoted` already matches nothing for an empty reading, but a
quote of invisible characters (U+200B, U+2800, a control) is a substring of a span that holds
the same characters."""

import pytest

from deploy_vii.contracts import Citation, Source, Span
from deploy_vii.readiness import citation_issues

SHA = "a" * 64
TEXT = "Net debt was 100.​ ⠀ \x01 ͏ end"
SOURCE = Source(
    source_id="doc",
    name="Doc",
    status="ready",
    sha256=SHA,
    spans=(Span(locator="page:1", text=TEXT), Span(locator="page:2", text="Other text.")),
)


def _cite(quote: str, locator: str = "page:1") -> Citation:
    return Citation(source_id="doc", source_sha256=SHA, locator=locator, quote=quote)


@pytest.mark.parametrize("quote", [" ", "\n\t", "​", "⠀", "\x01", "͏", " ​ "])
def test_a_blank_quote_is_refused_whatever_the_span_holds(quote: str) -> None:
    (issue,) = citation_issues((_cite(quote),), (SOURCE,))
    assert issue == "Quote/locator mismatch: blank quote under doc page:1"


def test_a_blank_quote_under_a_missing_locator_keeps_the_locator_issue() -> None:
    (issue,) = citation_issues((_cite("⠀", "page:9"),), (SOURCE,))
    assert issue.startswith("Quote/locator mismatch: no locator page:9 in doc")


def test_a_visible_quote_still_holds() -> None:
    assert citation_issues((_cite("Net debt was 100."), _cite("​Net debt")), (SOURCE,)) == (
        "Quote/locator mismatch: quote not found under doc page:1 "
        '(normalised whitespace, quote marks and dashes): "​Net debt"',
    )
