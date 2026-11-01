"""Phase 3 Task 4 (Part B): the CP-3D text and rule list carry the context-evidence rule.

The step rule ("rows from the context are Python's; refer to them by row id; never copy their
figures") is `market_implied.10`, a statement that appears verbatim in the text and the composed
system message. The oracle's context refusal ids (`cases/cp3-context-owner`) are carried by the
rule lists. `relative_value` has no loaded text: its rules are the `STEP_CONTRACTS` lines.
"""

import pytest
from prompt_support import request_for

from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import compose, rules
from deploy_workflow.prompts.compose import TEXTS_DIR

STEP_RULE = "Rows from the context are Python's; refer to them by row id; never copy their figures."
TEXT = (TEXTS_DIR / "market_implied.md").read_text(encoding="utf-8")


def rule(step: str, rule_id: str) -> rules.Rule:
    return next(r for r in rules.load_rules(step) if r.id == rule_id)


def test_the_text_describes_the_evidence_block_not_the_retired_one() -> None:
    assert "context-rows" not in TEXT
    assert '{"context_observations": [rows]}' in TEXT


def test_the_step_rule_is_a_new_id_with_its_statement_verbatim_in_the_text() -> None:
    statement = rule("market_implied", "market_implied.10").statement
    assert statement == STEP_RULE
    assert any(line.endswith(f"[market_implied.10] {STEP_RULE}") for line in TEXT.splitlines())


def test_the_ids_are_not_renumbered() -> None:
    ids = [r.id for r in rules.load_rules("market_implied")]
    assert ids == [f"market_implied.{n}" for n in range(1, 11)]


def test_the_composed_system_message_names_the_step_rule(pack: PreparedPack) -> None:
    system = compose(request_for("market_implied", pack))[0].text
    assert f"[market_implied.10] {STEP_RULE}" in system


def test_the_step_rule_enforces_the_filled_and_unknown_row_refusals() -> None:
    checks = set(rule("market_implied", "market_implied.10").checks)
    assert {
        "oracle:cp3-context:cp3d-filled-context-row",
        "oracle:cp3-context:cp3d-unknown-context-row",
    } <= checks


NEW_RELATIVE_VALUE_IDS = (
    "context-row-submitted",
    "context-quote-cited",
    "unknown-context-row",
    "ctx-observed-and-talk-high",
    "ctx-talk-only-high",
    "ctx-deal-talk-high",
    "ctx-stale-high",
    "talk-level-wording",
)


@pytest.mark.parametrize("case", NEW_RELATIVE_VALUE_IDS)
def test_relative_value_covers_each_context_refusal_id(case: str) -> None:
    covered = {c for r in rules.load_rules("relative_value") for c in r.checks}
    assert f"oracle:cp3-context:{case}" in covered
