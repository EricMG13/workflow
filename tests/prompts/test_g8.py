"""O6 Task 5: the CP-0 prompt states the planned module set (G8); the composer's own rules carry
``[compose.<id>]`` tokens (O6-P21), and the tokens change nothing else (T5-D)."""

import hashlib
import json
import re
import subprocess

import pytest
from b29_strip import undo_b29
from b30_strip import undo_b30
from b34_strip import undo_b34
from merge_strip import MERGE_REV, MERGE_SPANS, PRE_MERGE_REV, SPAN_TOKENS, undo_merged_contract
from p5_strip import undo_p5
from p5t6_strip import undo_p5t6_context, undo_p5t6_wording
from prompt_support import OLD_EVIDENCE_RULE, request_for

from deploy_vii.contracts import PATHWAY_MODULES, PathwayId
from deploy_vii.live.prompts import CP3_EVIDENCE_RULE, STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import live_consumers
from deploy_workflow.prompts import rules
from deploy_workflow.prompts.compose import compose
from deploy_workflow.prompts.g8 import G8_RULE_ID, G8_STATEMENT, module_set_statement

TOKEN = re.compile(r"^\[compose\.[A-Za-z0-9]+\] ", re.MULTILINE)
PLANNED = re.compile(
    r"^\[source_readiness\.g8\] The planned modules are exactly (.*)\. Write one consumer",
    re.MULTILINE,
)

# The answer key (ruling T5-D): the sha256 of the JSON of each STEP_CONTRACTS step's composed
# messages on the o2 pack, frozen before the tokens and the G8 block existed. Never edited.
OLD_FROZEN: dict[str, str] = {
    "business_context": "77e144292b8b64791e6a326a9dbfd68de8dd776282549ce823c334c7780f2f93",
    "committee_challenge": "20af64f31e55a976174c1f953a6787769b94137307030ef6cadd04fda50e0716",
    "credit_synthesis": "ce0a50087423ab9e674d178f243fd0eb54de655ed447651a9b56cc00a14d6702",
    "financials": "f42748bd79792c3a1e6e703b36fa2384456eec66ec25f8fe87c95612d9a57022",
    "integrity_review": "3bbd8f39400a1ca508f00150c52e3437b55bf9e32a4eead1f839cdfa96925038",
    "legal_covenants": "dc57675b1e42b1810ed1a3da99ba2dc70d0698e15aa41af1261c1e108ae6b14f",
    "narrative": "2e13063723b8fde9a990002de88f2857155c070c80a4649500d5183e226372fc",
    "quality": "007209478b2ffe287277ff755b9d497d101552cf0451eff4bfb854e4b921c058",
    "readiness": "8f92e8a5bfe7ea33a91d6112fb28925050b2d3885670fdfbcb968d08e7805fcd",
    "relative_value": "e3483e176ff80b2f302311904cdba37d6bfce3e75c2914caf33031d3f1541e22",
    "source_context": "1b40c9c60bd152592cf691414ea459416706b842d9e407e166024d382d8d11d8",
    "source_readiness": "ea4e4966aee75b656e67c6c07ac46e3cf68b6c8c8d9063ac8316cf111e1d5db6",
}


def g8_line(system: str) -> str:
    return next(line for line in system.splitlines() if line.startswith(f"[{G8_RULE_ID}] "))


def planned_system(pack: PreparedPack, preset: PathwayId) -> tuple[PreparedPack, str]:
    run = pack.run.model_copy(
        update={"pathway": preset, "requested_modules": PATHWAY_MODULES[preset]}
    )
    planned = pack.model_copy(update={"run": run})
    return planned, compose(request_for("source_readiness", planned, context=None))[0].text


@pytest.mark.parametrize("preset", sorted(PATHWAY_MODULES))
def test_the_cp0_prompt_states_exactly_the_planned_modules_in_plan_order(
    pack: PreparedPack, preset: PathwayId
) -> None:
    planned, system = planned_system(pack, preset)
    expected = live_consumers(planned)
    assert expected, preset
    match = PLANNED.search(system)
    assert match is not None
    assert tuple(match.group(1).split(", ")) == expected
    assert module_set_statement(planned) in system
    assert "CP-MODEL" not in expected and "CP-MODEL" not in match.group(1)
    assert "CP-0" not in match.group(1).split(", ")


def test_the_statement_is_the_ruled_sentence(pack: PreparedPack) -> None:
    planned, _ = planned_system(pack, "credit_snapshot")
    listed = ", ".join(live_consumers(planned))
    assert module_set_statement(planned) == (
        f"The planned modules are exactly {listed}. Write one consumer judgment for each. "
        'Python writes "Run <id>" for READY or READY_WITH_LIMITATIONS; any lower readiness '
        "refuses that module in this run, and every planned module that depends on it."
    )


def test_no_other_step_states_the_module_set(pack: PreparedPack) -> None:
    for step in sorted(STEP_CONTRACTS):
        if step != "source_readiness":
            assert "The planned modules are exactly" not in compose(request_for(step, pack))[0].text


def test_the_g8_rule_is_in_the_list_and_its_statement_is_in_every_cp0_message(
    pack: PreparedPack,
) -> None:
    by_id = {r.id: r for r in rules.load_rules("source_readiness")}
    assert by_id[G8_RULE_ID].statement == G8_STATEMENT
    assert list(by_id)[-1] == G8_RULE_ID  # appended, nothing renumbered
    for preset in PATHWAY_MODULES:
        planned, system = planned_system(pack, preset)
        assert G8_STATEMENT in g8_line(system)
        assert g8_line(system) == f"[{G8_RULE_ID}] {module_set_statement(planned)}"


@pytest.mark.parametrize("step_id", sorted(STEP_CONTRACTS))
def test_every_composed_rule_carries_its_token(pack: PreparedPack, step_id: str) -> None:
    system = compose(request_for(step_id, pack))[0].text
    tokened = {line.split("]")[0][1:] for line in system.splitlines() if TOKEN.match(line)}
    assert {f"compose.{i}" for i in ("1", "2", "3", "4", "5", "6", "O1", "O2", "O3")} <= tokened
    assert next(line for line in system.splitlines() if "compose.5]" in line).startswith(
        "[compose.5] 5. "
    )


@pytest.mark.parametrize("step_id", sorted(STEP_CONTRACTS))
def test_every_token_is_followed_by_its_own_rules_statement(
    pack: PreparedPack, step_id: str
) -> None:
    """A swapped or stray token names a rule whose statement does not follow it (O6 T5 L1)."""
    system = compose(request_for(step_id, pack))[0].text
    own = {r.id: r.statement for r in rules.load_rules("compose")}
    tokened = [line for line in system.splitlines() if TOKEN.match(line)]
    assert len(tokened) >= 9
    for line in tokened:
        rule_id, rest = line[1:].split("] ", 1)
        assert rule_id in own, line
        assert own[rule_id] in rest, line


@pytest.mark.parametrize("step_id", sorted(STEP_CONTRACTS))
def test_the_tokens_and_the_g8_block_are_the_only_change_to_the_frozen_message(
    pack: PreparedPack, step_id: str
) -> None:
    """T5-D: remove the ``[compose.<id>] `` tokens and, for CP-0, the G8 line, and (Phase 3 Task 4)
    put back CP-3's old evidence rule, and (M-R1) undo the merged restricted-cash change, and the message is the one the old frozen digest pins."""
    messages = compose(request_for(step_id, pack))
    system = undo_p5t6_wording(step_id, messages[0].text)  # Phase 5 Task 6 (P5T6-R1): CP-4 wording
    if step_id == "source_readiness":
        system = undo_p5(step_id, system)  # Phase 5 Task 1 (P5T1-R6): the draft authority line
        system = system.replace(g8_line(system) + "\n", "")
    system = TOKEN.sub("", system)
    # Phase 3 Task 4 (B17 item 3): CP-3's evidence rule was reworded; put the old text back.
    system = system.replace(CP3_EVIDENCE_RULE, OLD_EVIDENCE_RULE)
    # M-R1: undo the merged restricted-cash ids, for financials and narrative only.
    system = undo_merged_contract(step_id, system)
    # B34, then B30, then B29: undo the context-row basis wording in CP-3's method text, rules d
    # and e and the Basis schema text.
    system = undo_b29(step_id, undo_b30(step_id, undo_b34(step_id, system)))
    body = json.dumps(
        [
            [messages[0].role, system],
            [messages[1].role, undo_p5t6_context(step_id, messages[1].text)],
        ]
    )
    assert hashlib.sha256(body.encode()).hexdigest() == OLD_FROZEN[step_id]


def git_grep(rev: str, token: str) -> bool:
    """Whether ``token`` appears anywhere under src/deploy_vii at ``rev``."""
    done = subprocess.run(
        ["git", "grep", "-q", "-F", token, rev, "--", "src/deploy_vii"], check=False
    )
    return done.returncode == 0


def test_every_stripped_span_comes_from_the_merge() -> None:
    """M-R2: each stripped span carries a token the merge cfe37c23 added to src/deploy_vii and
    the merge's first parent 0fc6eb35 lacks, and the composed message holds the span now."""
    for step_id, spans in MERGE_SPANS.items():
        for span, _count, _replacement in spans:
            tokens = [tok for tok in SPAN_TOKENS if tok in span]
            assert tokens, (step_id, span)
            for token in tokens:
                assert not git_grep(PRE_MERGE_REV, token), token
                assert git_grep(MERGE_REV, token), token


def test_the_strip_removes_only_spans_the_message_holds(pack: PreparedPack) -> None:
    for step_id in MERGE_SPANS:
        system = compose(request_for(step_id, pack))[0].text
        assert all(span in system for span, _, _ in MERGE_SPANS[step_id])
