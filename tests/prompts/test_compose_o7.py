"""PF1: compose.O7, the bounded pack-reading rule. The statement is read from the pinned key."""

import json
from pathlib import Path
from typing import Any

from prompt_support import request_for

from deploy_vii.live.tools import READ, SEARCH
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import rules
from deploy_workflow.prompts.compose import compose
from deploy_workflow.prompts.tools import tool_names

KEY_FILE = Path(__file__).parents[2] / "cases" / "pilot-fixes" / "compose-o7.json"


def _key() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    return loaded


def test_source_readiness_system_prompt_carries_the_o7_token_and_statement(
    pack: PreparedPack,
) -> None:
    key = _key()
    request = request_for("source_readiness", pack)
    names = tool_names(request.spec)
    assert SEARCH in names and READ in names
    system = compose(request)[0].text
    assert key["token"] + key["statement"] in system


def test_a_step_without_both_pack_tools_has_no_o7(pack: PreparedPack) -> None:
    key = _key()
    request = request_for("narrative", pack)  # reads inputs, offers no pack tool
    names = tool_names(request.spec)
    assert not (SEARCH in names and READ in names)
    system = compose(request)[0].text
    assert key["token"] not in system and key["statement"] not in system


def test_the_rule_list_entry_is_the_keys_statement() -> None:
    key = _key()
    by_id = {r.id: r for r in rules.load_rules(rules.COMPOSE)}
    assert by_id[key["id"]].statement == key["statement"]
    assert by_id[key["id"]].when == "pack_tools"


def test_the_o7_checks_are_the_pack_cap_and_the_unread_citation_refusal() -> None:
    checks = {r.id: r.checks for r in rules.load_rules(rules.COMPOSE)}["compose.O7"]
    assert set(checks) == {
        "fn:deploy_workflow.financial_workflow:FinancialWorkflow.invoke",
        "fn:deploy_vii.live.tools:unread_citation_issues",
    }
    assert all(rules.check_exists(c) for c in checks)
