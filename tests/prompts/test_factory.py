"""O6 Task 2: ``prompt_factory`` over a real o2-synthetic store (CP-0, then CP-1A with CP-1
CONDITIONAL, the walk of ``tests/test_owner_refusals.py``). Fast: no model, no network."""

import importlib
import json
from pathlib import Path

import o2_case
import pytest
from prompt_support import spec_of

from deploy_vii.execution import Execution
from deploy_vii.live.prompts import STEP_CONTRACTS, PromptError
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow.owner_workflow import OwnerBinding, OwnerWorkflow, StepSpec
from deploy_workflow.prompts import NoPrompt, inventory, prompt_factory
from deploy_workflow.prompts.compose import RunContextRefused
from deploy_workflow.tools.source import SourceError

compose_module = importlib.import_module("deploy_workflow.prompts.compose")


@pytest.fixture
def walk(pack: PreparedPack, tmp_path: Path) -> OwnerWorkflow:
    return OwnerWorkflow.create(tmp_path / "store", pack, publication_directory=tmp_path / "model")


@pytest.fixture
def store(walk: OwnerWorkflow, tmp_path: Path) -> Execution:
    return Execution(tmp_path / "store")


def conditional_cp1() -> str:
    document = json.loads(o2_case.payload_for("source_readiness"))
    row = next(c for c in document["consumers"] if c["module_id"] == "CP-1")
    row["readiness"] = "CONDITIONAL"
    row["missing_source"] = "financial: restated statements"
    row["rationale"] = "Test input: the restated statements are not yet located."
    return json.dumps(document)


def test_cp0_binding_is_composed_into_a_system_and_a_user_message(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    prompt_for = prompt_factory(pack, store)
    binding, spec = walk.binding, walk.spec
    assert (binding.module_id, binding.step_id) == ("CP-0", "source_readiness")
    messages = prompt_for(binding, spec, ())
    assert [m.role for m in messages] == ["system", "user"]
    assert STEP_CONTRACTS["source_readiness"] in messages[0].text
    assert "search_pack and read_pages" in messages[0].text
    # the sources the session can read (O6-P14) are named in rule 5
    readable = host.session_sources(store, binding.ticket_id, binding.step_id)
    assert readable
    assert f"declared sources: {', '.join(readable)}" in messages[0].text


def test_session_sources_is_the_execution_states_source_list(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    binding = walk.binding
    found = host.session_sources(store, binding.ticket_id, binding.step_id)
    assert found == host._execution_state(store, binding.ticket_id, binding.step_id)[3]
    assert set(found) <= {s.source_id for s in pack.sources}


def test_session_sources_refuses_a_step_with_no_source_session(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    with pytest.raises(SourceError):
        host.session_sources(store, walk.binding.ticket_id, "narrative")


def test_the_repair_issues_reach_the_prompt(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    prompt_for = prompt_factory(pack, store)
    messages = prompt_for(walk.binding, walk.spec, ("fix the quote",))
    assert "<<<REPAIR id=prior-validation-issues" in messages[1].text
    assert "- fix the quote" in messages[1].text


def test_the_factory_prompt_equals_the_composer_of_the_same_request(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    again = prompt_factory(pack, store)(walk.binding, walk.spec, ())
    assert prompt_factory(pack, store)(walk.binding, walk.spec, ()) == again


def test_cp1a_after_a_conditional_cp1_is_told_no_figure_may_be_referenced(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    assert walk.submit_review(conditional_cp1())["status"] == "valid"
    assert walk.binding.module_id == "CP-1A"
    messages = prompt_factory(pack, store)(walk.binding, walk.spec, ())
    user = messages[1].text
    assert "CP-1 is not accepted in this journal" in user  # H2: the settled CP-1 facts, none
    assert '"cp1_facts": []' in user
    assert "consumers" in user


STEPS_WITHOUT_TEXT = [s for s in inventory() if s not in STEP_CONTRACTS]


@pytest.mark.parametrize("step_id", STEPS_WITHOUT_TEXT)
def test_every_other_step_is_a_named_no_prompt_before_the_store_is_read(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow, step_id: str
) -> None:
    binding: OwnerBinding = walk.binding.model_copy(update={"step_id": step_id})
    spec: StepSpec = spec_of(step_id)
    with pytest.raises(NoPrompt) as caught:
        prompt_factory(pack, store)(binding, spec, ())
    assert caught.value.step_id == step_id


def test_a_binding_for_no_attempt_is_a_prompt_error(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    binding = walk.binding.model_copy(update={"ticket_id": "no-such-ticket"})
    with pytest.raises(PromptError, match="no-such-ticket"):
        prompt_factory(pack, store)(binding, walk.spec, ())


def test_a_context_that_disagrees_with_the_run_is_a_named_prompt_error(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    other = pack.model_copy(update={"run": pack.run.model_copy(update={"issuer_name": "Other Co"})})
    with pytest.raises(RunContextRefused) as caught:
        prompt_factory(other, store)(walk.binding, walk.spec, ())
    assert isinstance(caught.value, PromptError)
    assert "issuer_name" in str(caught.value)


def test_the_pin_form_is_asked_only_for_an_enabled_module(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []

    def pin_form(module_id: str, _: PreparedPack) -> dict[str, str]:
        asked.append(module_id)
        return {"x": "13.37"}

    off = prompt_factory(pack, store, pin_form=pin_form)(walk.binding, walk.spec, ())
    assert asked == [] and "pinned-assumptions" not in off[1].text
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-0"}))
    on = prompt_factory(pack, store, pin_form=pin_form)(walk.binding, walk.spec, ())
    assert asked == ["CP-0"] and "13.37" in on[1].text
