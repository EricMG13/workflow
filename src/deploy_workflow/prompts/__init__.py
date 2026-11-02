"""The owner-path prompt set (O6): which steps need a prompt.

The package exports only leaf names (``FenceError``, ``inventory``). ``compose``, ``NoPrompt``,
``PromptRequest`` and ``RunContextRefused`` live in ``prompts.compose``, which reaches the
workflow modules, so they are not re-exported here. The package is a leaf: it imports no workflow, host
or loop module, so ``prompts.fence`` can be imported at module level from anywhere. The loop's
``PromptFor`` factory lives in ``prompts.factory``, which reads the journal for what a request
needs. A step with no prompt stops the run with a named ``NoPrompt`` and is never sent a
placeholder.
"""

from deploy_workflow.prompts.fence import FenceError

__all__ = [
    "FenceError",
    "inventory",
]


def inventory() -> tuple[str, ...]:
    """The sorted step ids of ``OWNER_SPECS``: every step that needs a prompt."""
    # Imported here, not at package import: owner_workflow reaches host, and host reaches
    # tools.source, which imports prompts.fence. A module-level import would close that cycle.
    from deploy_workflow.owner_workflow import OWNER_SPECS

    return tuple(sorted({s.step_id for spec in OWNER_SPECS.values() for s in spec.steps}))
