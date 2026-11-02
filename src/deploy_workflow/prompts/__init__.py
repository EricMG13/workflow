"""The owner-path prompt set (O6): which steps need a prompt, and the composer.

``compose`` is pure (``prompts.compose``). The package is a leaf: it imports no workflow, host
or loop module, so ``prompts.fence`` can be imported at module level from anywhere. The loop's
``PromptFor`` factory lives in ``prompts.factory``, which reads the journal for what a request
needs. A step with no prompt stops the run with a named ``NoPrompt`` and is never sent a
placeholder.
"""

from deploy_workflow.owner_workflow import OWNER_SPECS
from deploy_workflow.prompts.compose import (
    NoPrompt,
    PromptRequest,
    RunContextRefused,
    compose,
)
from deploy_workflow.prompts.fence import FenceError

__all__ = [
    "FenceError",
    "NoPrompt",
    "PromptRequest",
    "RunContextRefused",
    "compose",
    "inventory",
]


def inventory() -> tuple[str, ...]:
    """The sorted step ids of ``OWNER_SPECS``: every step that needs a prompt."""
    return tuple(sorted({s.step_id for spec in OWNER_SPECS.values() for s in spec.steps}))
