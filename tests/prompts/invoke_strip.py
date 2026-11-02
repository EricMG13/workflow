"""Undo the invoke budget in a composed message: the pack-tools sentence of the ``Limits:`` line
says ``share 32 calls in one step`` (or ``at most 32 calls in one step`` for a single pack tool)
where it said 16 before the separate ``MAX_INVOKES`` budget. Removing exactly this span (putting
back ``MAX_CALLS`` there) gives the message as it was before the invoke budget."""

from prompt_support import spec_of

from deploy_vii.live.tools import EXTRACT, READ, SEARCH
from deploy_workflow.financial_workflow import MAX_CALLS, MAX_INVOKES
from deploy_workflow.prompts.tools import tool_names

_SHARE = (f"share {MAX_INVOKES} calls in one step", f"share {MAX_CALLS} calls in one step")
_AT_MOST = (f"at most {MAX_INVOKES} calls in one step", f"at most {MAX_CALLS} calls in one step")


def undo_invoke(step_id: str, text: str) -> str:
    """Put the 16-call wording back in the pack-tools sentence (steps that offer pack tools)."""
    offers = any(n in (SEARCH, READ, EXTRACT) for n in tool_names(spec_of(step_id)))
    spans = text.count(_SHARE[0]) + text.count(_AT_MOST[0])
    assert spans == (1 if offers else 0), step_id
    return text.replace(_SHARE[0], _SHARE[1]).replace(_AT_MOST[0], _AT_MOST[1])
