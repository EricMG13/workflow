"""Helpers the owner cores share.

`is_blank` is the one blank-text predicate for analyst text (LEAD round 12 B10); the predicate
itself is `deploy_vii.prose.is_blank`, and this module keeps its public name for the owner cores
(`from deploy_workflow.owners.blank import is_blank`). `one_per_page` is the derived-fact
citation rule of Stage 2 round 3, which cp1c, cp2g, cp2h and cp4c each held a copy of.
"""

from collections.abc import Sequence

from deploy_vii.contracts import Citation
from deploy_vii.prose import is_blank

__all__ = ["is_blank", "one_per_page"]


def one_per_page(citations: Sequence[Citation]) -> tuple[Citation, ...]:
    """One Citation per (source, page), quoting the first input quote on that page, in input
    order. No quote is invented."""
    first: dict[tuple[str, str], Citation] = {}
    for citation in citations:
        first.setdefault((citation.source_id, citation.locator), citation)
    return tuple(first.values())
