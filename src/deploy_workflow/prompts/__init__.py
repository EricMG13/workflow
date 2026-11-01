"""The owner-path prompt set (O6): which steps need a prompt, and the contract of the composer.

Task 1 fixes the names only. ``compose`` refuses with ``NoPrompt`` for every step until Tasks 2-4
give that step a prompt, so a step with no prompt stops the run with a named refusal and is never
sent a placeholder.
"""

from dataclasses import dataclass

from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.model.loop import PromptFor
from deploy_workflow.model.turn import Message
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerBinding, StepSpec

__all__ = ["NoPrompt", "PromptRequest", "compose", "inventory", "prompt_factory"]


class NoPrompt(Exception):
    """No prompt exists for this step; the run stops. ``str()`` is the step id (O6-P2)."""

    def __init__(self, step: str) -> None:
        super().__init__(step)
        self.step = step

    @property
    def step_id(self) -> str:
        return self.step


@dataclass(frozen=True)
class PromptRequest:
    """What ``compose`` reads. Task 2 adds the attempt, module context and CP-1 facts."""

    step_id: str
    issues: tuple[str, ...] = ()


def inventory() -> tuple[str, ...]:
    """The sorted step ids of ``OWNER_SPECS``: every step that needs a prompt."""
    return tuple(sorted({s.step_id for spec in OWNER_SPECS.values() for s in spec.steps}))


def compose(request: PromptRequest) -> tuple[Message, ...]:
    """The messages for one request. Pure. No step has a prompt before Task 2."""
    raise NoPrompt(request.step_id)


def prompt_factory(pack: PreparedPack, store: Execution) -> PromptFor:
    """The ``PromptFor`` of a run (O6-P1); ``store`` supplies the attempt Task 2 reads."""
    del pack, store

    def prompt_for(
        binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
    ) -> tuple[Message, ...]:
        del spec
        return compose(PromptRequest(binding.step_id, issues))

    return prompt_for
