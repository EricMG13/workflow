"""The owner-path prompt set (O6): which steps need a prompt, the composer and its factory.

``compose`` is pure (``prompts.compose``); ``prompt_factory`` reads the journal for what a request
needs and returns the loop's ``PromptFor``. A step with no prompt stops the run with a named
``NoPrompt`` and is never sent a placeholder.
"""

from collections.abc import Callable, Mapping

from deploy_vii.business_context import STEP_ID as BUSINESS_CONTEXT
from deploy_vii.business_context import cp1_context_facts
from deploy_vii.execution import Execution
from deploy_vii.live.context import MODULE_CONTEXTS, module_context
from deploy_vii.live.prompts import PromptError
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow.context import ContextRefused, context_facts
from deploy_workflow.model.loop import PromptFor
from deploy_workflow.model.turn import Message
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerBinding, StepSpec
from deploy_workflow.prompts.compose import (
    JsonValue,
    NoPrompt,
    PromptRequest,
    RunContextRefused,
    compose,
    has_prompt,
    pin_enabled,
)
from deploy_workflow.prompts.fence import FenceError
from deploy_workflow.tools.source import SourceError

__all__ = [
    "FenceError",
    "NoPrompt",
    "PromptRequest",
    "RunContextRefused",
    "compose",
    "inventory",
    "prompt_factory",
]

PinForm = Callable[[str, PreparedPack], Mapping[str, JsonValue] | None]


def inventory() -> tuple[str, ...]:
    """The sorted step ids of ``OWNER_SPECS``: every step that needs a prompt."""
    return tuple(sorted({s.step_id for spec in OWNER_SPECS.values() for s in spec.steps}))


def prompt_factory(
    pack: PreparedPack, store: Execution, *, pin_form: PinForm | None = None
) -> PromptFor:
    """The ``PromptFor`` of a run (O6-P1). ``store`` supplies the attempt, the module context of
    a step that embeds one, the settled CP-1 facts and the sources the step's tools read.
    With ``pin_form=None`` the pins come from the request's own context
    (``compose.request_pin_form``). ``pin_form(module_id, pack)``, Phase 6's
    ``pins.submission_form``, is an override: it is asked only for a module in
    ``compose.PINS_ENABLED``, and its form replaces the one derived from the context."""

    def prompt_for(
        binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
    ) -> tuple[Message, ...]:
        step_id = binding.step_id
        if not has_prompt(step_id):
            raise NoPrompt(step_id)
        attempt = next((a for a in store.read().attempts if a.ticket_id == binding.ticket_id), None)
        if attempt is None:
            raise PromptError(f"no attempt for ticket {binding.ticket_id}")
        try:
            context = context_facts(pack)
        except ContextRefused as error:
            raise RunContextRefused(str(error)) from error
        embeds = step_id in MODULE_CONTEXTS and spec.inputs == "none"
        readable = None
        if spec.sources:
            try:
                readable = host.session_sources(store, binding.ticket_id, step_id)
            except SourceError as error:
                raise PromptError(
                    f"the sources of step {step_id} cannot be listed: {error.code}"
                ) from error
        pins = None
        if pin_form is not None and pin_enabled(binding.module_id):
            pins = pin_form(binding.module_id, pack)
        return compose(
            PromptRequest(
                step_id=step_id,
                spec=spec,
                pack=pack,
                module_id=binding.module_id,
                context=context,
                module_context=module_context(store, attempt, step_id) if embeds else None,
                readable=readable,
                cp1_facts=cp1_context_facts(store, attempt) if step_id == BUSINESS_CONTEXT else (),
                pins=pins,
                issues=issues,
            )
        )

    return prompt_for
