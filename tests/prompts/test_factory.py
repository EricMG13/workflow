"""O6 Task 2: ``prompt_factory`` over a real o2-synthetic store (CP-0, then CP-1A with CP-1
CONDITIONAL, the walk of ``tests/test_owner_refusals.py``). Fast: no model, no network."""

import importlib
import json
from pathlib import Path
from typing import Any

import o2_case
import pytest
import test_method_cp3 as stage1
from prompt_support import EXISTING, spec_of

from deploy_vii.business_context import cp1_context_facts
from deploy_vii.contracts import Fact
from deploy_vii.execution import Execution, head_of
from deploy_vii.live.context import declared_sources, module_context, readable_sources
from deploy_vii.live.prompts import STEP_CONTRACTS, PromptError
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow.owner_workflow import OwnerBinding, OwnerWorkflow, StepSpec
from deploy_workflow.prompts import inventory
from deploy_workflow.prompts.compose import NoPrompt, RunContextRefused
from deploy_workflow.prompts.factory import prompt_factory
from deploy_workflow.prompts.tools import tools_for
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
    assert '- "fix the quote"' in messages[1].text


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


STEPS_WITHOUT_TEXT = [s for s in inventory() if s not in EXISTING]


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


def test_the_run_context_block_is_in_the_factory_prompt(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow
) -> None:
    user = prompt_factory(pack, store)(walk.binding, walk.spec, ())[1].text
    assert "<<<CONTEXT id=run-context sha256=" in user  # context_facts(pack) reached compose
    assert '"run_type"' in user


def cited(node: Any, out: set[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("source_id"), str) and isinstance(node.get("locator"), str):
            out.add((node["source_id"], node["locator"]))
        for value in node.values():
            cited(value, out)
    elif isinstance(node, list):
        for value in node:
            cited(value, out)


def test_p5a_a_cp0_payload_that_fits_the_offered_schema_is_accepted_by_the_validator(
    pack: PreparedPack, store: Execution, walk: OwnerWorkflow, tmp_path: Path
) -> None:
    """The adversary's H1: the schema offered for submit_source_readiness must be one a valid CP-0
    payload fits. Real OwnerWorkflow, the frozen o2 payload cut down to the offered properties."""
    tools = tools_for(walk.binding, walk.spec)
    offered = next(t for t in tools if t.name == "submit_source_readiness").parameters
    payload = json.loads(o2_case.payload_for("source_readiness"))
    # the strict schema requires every field; schema_version, which the frozen payload leaves to
    # its default, is pinned to its literal there (F1), which the model copies
    for key in set(offered["required"]) - set(payload):
        (literal,) = offered["properties"][key]["enum"]
        payload[key] = literal
    assert set(offered["required"]) <= set(payload)
    assert set(payload) <= set(offered["properties"])  # nothing the schema forbids
    assert payload["pack_sha256"] == pack.content_hash()  # what the prompt tells the model to copy
    pairs: set[tuple[str, str]] = set()
    cited(payload, pairs)
    for source_id, locator in sorted(pairs):
        line = int(locator.split(":")[1].split("-")[0])
        walk.invoke("read_pages", {"source_id": source_id, "first_page": line, "last_page": line})
    result = walk.submit_review(json.dumps(payload))
    assert result["status"] == "valid", result.get("issues")
    # and a payload without the field the offered schema requires is not one the model may send
    short = {k: v for k, v in payload.items() if k != "pack_sha256"}
    assert not set(offered["required"]) <= set(short)


def seeded_store(root: Path, module: str, command_row: str) -> tuple[Execution, PreparedPack, Any]:
    """Stage 1 fixture heads (hand-seeded, as tests/test_connect_cp3.py does), ``module`` begun."""
    pack = stage1.make_pack("positive")
    cp0 = stage1.make_cp0(pack, "positive")
    command = Fact(
        fact_id="run-consumer",
        table_id="T8",
        row_id=command_row,
        field="exact_command",
        label="Run consumer",
        text=f"Run {command_row}",
    )
    heads = [cp0.model_copy(update={"facts": (*cp0.facts, command)}), stage1.make_cp1(pack)]
    if module == "CP-3":
        heads += [stage1.make_cp1a(pack, "positive", blocked=False), stage1.make_cp2(pack)]
    store = Execution.create(root / "store", pack)
    for head in heads:
        store._store(head.model_dump_json())
    store._write(store.read().model_copy(update={"heads": tuple(head_of(h) for h in heads)}))
    return store, pack, store.begin(module)


@pytest.fixture
def listed_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hand-seeded heads are not verifiable producers, so ``session_sources`` would refuse them
    (identity_mismatch). Return the step's real scope instead, as ``host._execution_state``
    computes it: the declared sources that are also readable (CP-3: its market sources)."""

    def scope(store: Execution, ticket_id: str, step_id: str) -> tuple[str, ...]:
        attempt = next(a for a in store.read().attempts if a.ticket_id == ticket_id)
        ids = tuple(s.source_id for s in store.pack().sources)
        declared = set(declared_sources(store, attempt, step_id, ids))
        readable = set(readable_sources(store, attempt, step_id))
        return tuple(i for i in ids if i in declared and i in readable)

    monkeypatch.setattr(host, "session_sources", scope)


def block_body(user: str, block_id: str) -> dict[str, Any]:
    start = user.index(f"<<<CONTEXT id={block_id} ")
    text = user[start:].split(">>>\n", 1)[1].split("\n<<<END>>>", 1)[0]
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def test_h2_cp3_embeds_exactly_the_module_context_of_the_store(
    tmp_path: Path, listed_sources: None
) -> None:
    store, pack, attempt = seeded_store(tmp_path, "CP-3", "CP-3")
    binding = OwnerBinding.model_construct(
        step_id="relative_value", ticket_id=attempt.ticket_id, module_id="CP-3"
    )
    user = prompt_factory(pack, store)(binding, spec_of("relative_value"), ())[1].text
    expected = module_context(store, attempt, "relative_value")
    assert expected
    body = block_body(user, "prepared-pack")
    for key, value in expected.items():
        assert body[key] == json.loads(json.dumps(value)), key


def test_h2_cp1a_lists_the_facts_of_an_accepted_cp1(tmp_path: Path, listed_sources: None) -> None:
    store, pack, attempt = seeded_store(tmp_path, "CP-1A", "CP-1A")
    binding = OwnerBinding.model_construct(
        step_id="business_context", ticket_id=attempt.ticket_id, module_id="CP-1A"
    )
    user = prompt_factory(pack, store)(binding, spec_of("business_context"), ())[1].text
    facts = cp1_context_facts(store, attempt)
    assert facts
    listed = block_body(user, "prepared-pack")["cp1_facts"]
    assert [row["ref"] for row in listed] == [f.fact_id for f in facts]
    assert "CP-1 is not accepted in this journal" not in user


def test_h2_cp3_rule_5_names_only_the_market_scope(tmp_path: Path, listed_sources: None) -> None:
    store, pack, attempt = seeded_store(tmp_path, "CP-3", "CP-3")
    binding = OwnerBinding.model_construct(
        step_id="relative_value", ticket_id=attempt.ticket_id, module_id="CP-3"
    )
    system = prompt_factory(pack, store)(binding, spec_of("relative_value"), ())[0].text
    assert "declared sources: market." in system
