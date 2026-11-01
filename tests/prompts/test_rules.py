"""O6 Task 3: the rule lists and the coverage oracle (pure; no store, no model).

Every validator refusal has a rule (tests 1, 2) and every composed prompt names every rule it
owes (tests 3, 5). The ids, checks and statements are a golden file (test 4), so removing or
rewording a rule is an explicit edit the review sees.

The 14 new steps have draft lists: ``checks`` filled from their oracles and cores, ``statement``
empty until M5's separate writer completes them. Their statement test and their prompt test are
strict xfail per step: each marker comes off with the work that makes it pass (M5; Task 4).
"""

import ast
import importlib
import json
import re
from pathlib import Path

import pytest
from prompt_support import EXISTING, request_for

from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import NoPrompt, compose, inventory, rules
from deploy_workflow.prompts.compose import PromptRequest

compose_module = importlib.import_module("deploy_workflow.prompts.compose")
GOLDEN = Path(__file__).with_name("rule_lists.golden.json")
STEPS = inventory()
NEW = tuple(s for s in STEPS if s not in EXISTING)

# Issue sites and oracle ids that no rule covers yet, with the task that covers each. The test
# fails for a step if a site listed here is already covered, so this list only shrinks.
CP3_T4 = "Phase 3 T4 regenerates the 12 lists from STEP_CONTRACTS (its context rule, 072e0590)"
# No contract rule states the stale-or-blocked upstream check of CP-2, CP-3, CP-4 and CP-6; it is
# Python's binding of the inputs, not something the model writes. No task covers it yet: the owner
# rules whether the model needs a statement of it (flagged in the Task 3 report).
UPSTREAM = "no contract rule states the upstream binding check; owner to rule (no task yet)"
PENDING: dict[str, dict[str, str]] = {
    "credit_synthesis": {"fn:deploy_vii.cp2_synthesis:_provenance_issues": UPSTREAM},
    "committee_challenge": {"fn:deploy_vii.cp6_committee:_provenance_issues": UPSTREAM},
    "legal_covenants": {"fn:deploy_vii.cp4_legal:stale_issues": UPSTREAM},
    "relative_value": {
        "fn:deploy_vii.cp3_relative_value:_provenance_issues": UPSTREAM,
        "fn:deploy_vii.cp3_relative_value:_array_rows": CP3_T4,
        "fn:deploy_vii.cp3_relative_value:_row_problems": CP3_T4,
        "fn:deploy_vii.cp3_relative_value:_strings": CP3_T4,
        "fn:deploy_vii.cp3_relative_value:_identity_problems": CP3_T4,
        **{
            f"oracle:cp3-context:{i}": CP3_T4
            for i in (
                "ctx-observed-and-talk-high",
                "ctx-talk-only-high",
                "ctx-deal-talk-high",
                "ctx-stale-high",
                "context-row-submitted",
                "context-quote-cited",
                "unknown-context-row",
                "talk-level-wording",
            )
        },
    },
}


def covered_by(step_id: str) -> set[str]:
    """What the step's own rules and the composer's rules (tool, pin and citation checks) carry."""
    return {
        c for name in (step_id, rules.COMPOSE) for r in rules.load_rules(name) for c in r.checks
    }


def gaps(
    step_id: str, covered: set[str], needed: frozenset[str], pending: dict[str, str]
) -> tuple[list[str], list[str]]:
    """``(uncovered, pending_but_covered)``: a need no rule carries and is not pending, and a
    pending entry some rule already carries (the list must shrink)."""
    return (
        sorted(needed - covered - set(pending)),
        sorted(set(pending) & covered),
    )


# --- test 1: every content refusal has a rule -------------------------------------------------


@pytest.mark.parametrize("step_id", STEPS)
def test_every_content_refusal_is_covered(step_id: str) -> None:
    assert step_id in rules.ENTRIES, f"{step_id} has no check source"
    needed = rules.needed_checks(step_id)
    assert needed, f"{step_id}: the validator and oracle give no check"
    assert step_id in rules.step_ids(), f"{step_id} has no rule list"
    uncovered, stale = gaps(step_id, covered_by(step_id), needed, PENDING.get(step_id, {}))
    assert not uncovered, f"{step_id}: no rule covers {uncovered}"
    assert not stale, f"{step_id}: PENDING entries are already covered, remove them: {stale}"


def test_a_pending_site_that_is_already_covered_fails() -> None:
    site = "fn:x:covered"
    uncovered, stale = gaps("s", {site}, frozenset({site}), {site: "task"})
    assert uncovered == [] and stale == [site]


def test_a_site_with_no_rule_fails_unless_it_is_pending() -> None:
    site = "fn:x:new"
    assert gaps("s", set(), frozenset({site}), {})[0] == [site]
    assert gaps("s", set(), frozenset({site}), {site: "task"}) == ([], [])


def test_the_pending_entries_name_real_sites() -> None:
    """A pending key that is not a need at all (a typo, or a removed site) would hide nothing but
    rot; keep the list to real needs of the working tree or of the committed tree."""
    for step_id, entries in PENDING.items():
        needed = rules.needed_checks(step_id)
        absent = sorted(set(entries) - needed)
        assert not absent, f"{step_id}: PENDING names no current need: {absent}"


def test_a_new_inline_issue_in_a_copied_core_has_no_rule() -> None:
    """Mutation probe: a check added to a validator the lists know nothing about is flagged."""
    step_id = "downside_pathway"
    module = "deploy_workflow.owners.cp2a"
    tree = ast.parse(rules.module_path(module).read_text(encoding="utf-8"))
    new = ast.parse(
        'def _brand_new_check(issues: list[str]) -> None:\n    issues.append("a new inline issue")'
    ).body[0]
    entry = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_validate_step"
    )
    entry.body.insert(0, ast.parse("_brand_new_check([])").body[0])
    tree.body.append(new)
    mutated = ast.unparse(ast.fix_missing_locations(tree))
    needed = rules.needed_checks(step_id, {module: mutated})
    uncovered, _ = gaps(step_id, covered_by(step_id), needed, {})
    assert uncovered == [f"fn:{module}:_brand_new_check"]


def test_the_unmutated_core_has_no_uncovered_site() -> None:
    step_id = "downside_pathway"
    assert gaps(step_id, covered_by(step_id), rules.needed_checks(step_id), {})[0] == []


def test_a_removed_oracle_check_is_flagged() -> None:
    step_id = "change_screen"
    some = next(iter(sorted(rules.needed_checks(step_id))))
    covered = covered_by(step_id) - {some}
    assert gaps(step_id, covered, rules.needed_checks(step_id), {})[0] == [some]


def test_cp1b_has_no_oracle_so_its_source_is_the_code_list() -> None:
    assert rules.oracle_ids("earnings_delta") == {}
    sites = rules.cp1b_sites()
    assert "code:cp1b:shape" in sites and "code:cp1b:owner_error" in sites
    assert any(s.startswith("code:cp1b:period:") for s in sites)
    assert set(sites) <= rules.needed_checks("earnings_delta")


def test_a_pin_lines_helper_is_covered_by_the_pin_rule() -> None:
    """O6-P12: each owner's ``_pin_lines`` maps to ``compose.O6``; a later Phase 6 task that adds
    one must add it to that rule's checks."""
    owners = rules.ROOT / "src" / "deploy_workflow" / "owners"
    found = sorted(
        f"fn:deploy_workflow.owners.{p.stem}:_pin_lines"
        for p in owners.glob("*.py")
        if any(
            isinstance(n, ast.FunctionDef) and n.name == "_pin_lines"
            for n in ast.parse(p.read_text(encoding="utf-8")).body
        )
    )
    assert found, "no owner defines _pin_lines"
    o6 = next(r for r in rules.load_rules(rules.COMPOSE) if r.id == "compose.O6")
    assert "fn:deploy_workflow.owners.pins:pin_issues" in o6.checks
    assert set(found) <= set(o6.checks)


# --- test 2: every check exists -----------------------------------------------------------------


@pytest.mark.parametrize("name", (rules.COMPOSE, *STEPS))
def test_every_check_exists(name: str) -> None:
    for rule in rules.load_rules(name):
        for check in rule.checks:
            assert rules.check_exists(check), f"{rule.id}: {check} does not resolve"


def test_a_renamed_function_or_oracle_id_does_not_resolve() -> None:
    assert rules.check_exists("fn:deploy_workflow.owners.cp2a:_validate_step")
    assert not rules.check_exists("fn:deploy_workflow.owners.cp2a:_validate_step_gone")
    assert not rules.check_exists("fn:deploy_workflow.owners.no_such_module:f")
    assert rules.check_exists("oracle:cp2a:r01")
    assert not rules.check_exists("oracle:cp2a:r999")
    assert not rules.check_exists("oracle:no-such-case:r01")
    assert not rules.check_exists("code:cp1b:nope")
    assert not rules.check_exists("mystery:thing")


@pytest.mark.parametrize("step_id", [s for s in STEPS if s in rules.OWNER_MODULE])
def test_the_declared_entry_is_the_entry_validator(step_id: str) -> None:
    """The extractor starts from the step's ``ENTRY_VALIDATOR``; a retargeted one must fail."""
    entry = importlib.import_module(rules.OWNER_MODULE[step_id]).ENTRY_VALIDATOR
    assert f"{entry.__module__}:{entry.__qualname__}" in rules.ENTRIES[step_id]


# --- the lists themselves -----------------------------------------------------------------------


def test_there_is_one_list_per_inventory_step_and_one_for_the_composer() -> None:
    assert rules.step_ids() == STEPS
    assert len(STEPS) == 26
    assert [r.id for r in rules.load_rules(rules.COMPOSE)][:4] == [
        "compose.O1",
        "compose.O2",
        "compose.O3",
        "compose.O4",
    ]


@pytest.mark.parametrize("step_id", EXISTING)
def test_an_existing_step_carries_its_contract_rules_whole(step_id: str) -> None:
    expected = rules.contract_rules(STEP_CONTRACTS[step_id], step_id)
    got = [(r.id, r.statement) for r in rules.load_rules(step_id)]
    assert got == list(expected)
    letters = re.findall(r"^([a-z])\. ", STEP_CONTRACTS[step_id], re.MULTILINE)
    assert [i for i, _ in expected] == [f"{step_id}.{c}" for c in letters]
    for _, statement in expected:
        assert statement in STEP_CONTRACTS[step_id]


@pytest.mark.parametrize("step_id", STEPS)
def test_every_rule_has_a_check(step_id: str) -> None:
    for rule in rules.load_rules(step_id):
        assert rule.checks or rule.from_code, f"{rule.id} enforces nothing"


@pytest.mark.parametrize(
    "step_id",
    [
        s
        if s in EXISTING
        else pytest.param(
            s,
            marks=pytest.mark.xfail(
                strict=True, reason=f"M5: the statements of {s} wait for their separate writer"
            ),
        )
        for s in STEPS
    ],
)
def test_every_rule_has_a_statement(step_id: str) -> None:
    empty = [r.id for r in rules.load_rules(step_id) if not r.statement.strip()]
    assert not empty, f"{step_id}: no statement for {empty}"


@pytest.mark.parametrize("step_id", NEW)
def test_the_draft_is_the_extractor_output_before_the_statements_are_written(
    step_id: str,
) -> None:
    """Whatever M5 does to the statements, the draft's checks are a subset of the extractor's."""
    draft = rules.extract_checks(step_id)
    drafted = {c for r in draft["rules"] for c in r["checks"]}
    committed = {c for r in rules.load_rules(step_id) for c in r.checks}
    assert drafted <= committed
    assert all(r["statement"] == "" for r in draft["rules"])


def test_prose_rules_in_a_core_are_carried_as_from_code() -> None:
    screen = rules.extract_checks("change_screen")["rules"]
    assert any("Python rates each of the seven topics" in str(r.get("from_code")) for r in screen)
    peers = rules.extract_checks("peer_benchmark")["rules"]
    assert any("minimum_included_peers" in str(r.get("from_code")) for r in peers)
    assert not any("from_code" in r for r in rules.extract_checks("macro_fx")["rules"])


# --- test 3: the composed prompt names every rule ----------------------------------------------


def applicable(request: PromptRequest) -> list[rules.Rule]:
    """The composer's rules that bind this request: a conditional rule only where it holds."""
    out = []
    for rule in rules.load_rules(rules.COMPOSE):
        if rule.when == "inputs" and request.spec.inputs == "none":
            continue
        if rule.when == "line_source" and not (
            request.spec.sources and compose_module._is_line_source(request.pack)
        ):
            continue
        if rule.when == "pins" and request.module_id not in compose_module.PINS_ENABLED:
            continue
        out.append(rule)
    return out


def missing_rules(step_id: str, request: PromptRequest, system: str) -> list[str]:
    """Rule ids whose token or statement is not in the system message."""
    lost = []
    for rule in rules.load_rules(step_id):
        if f"[{rule.id}]" not in system or rule.statement not in system:
            lost.append(rule.id)
    lost.extend(r.id for r in applicable(request) if r.statement not in system)
    return lost


@pytest.mark.parametrize(
    "step_id",
    [
        s
        if s in EXISTING
        else pytest.param(
            s,
            marks=pytest.mark.xfail(
                strict=True, raises=NoPrompt, reason=f"O6 Task 4: no text for {s} yet"
            ),
        )
        for s in STEPS
    ],
)
def test_prompt_names_every_rule(step_id: str, pack: PreparedPack) -> None:
    request = request_for(step_id, pack)
    system = compose(request)[0].text  # NoPrompt names the step with no text
    assert missing_rules(step_id, request, system) == []


def test_the_conditional_composer_rules_bind_only_where_their_condition_holds(
    pack: PreparedPack,
) -> None:
    by_id = {r.id: r for r in rules.load_rules(rules.COMPOSE)}
    assert by_id["compose.O4"].when == "inputs"
    assert by_id["compose.O5"].when == "line_source"
    assert by_id["compose.O6"].when == "pins"
    narrative = request_for("narrative", pack)  # reads inputs, has no source
    assert {"compose.O4"} <= {r.id for r in applicable(narrative)}
    assert "compose.O5" not in {r.id for r in applicable(narrative)}
    readiness = request_for("source_readiness", pack)  # a source step on a line pack
    ids = {r.id for r in applicable(readiness)}
    assert "compose.O5" in ids and "compose.O4" not in ids
    assert "compose.O6" not in ids and compose_module.PINS_ENABLED == frozenset()


def test_o6_binds_when_the_module_is_enabled(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compose_module, "PINS_ENABLED", frozenset({"CP-1A"}))
    request = request_for("business_context", pack, pins={"hedge_ratio.percent_text": "60"})
    system = compose(request)[0].text
    assert "compose.O6" in {r.id for r in applicable(request)}
    assert missing_rules("business_context", request, system) == []


# --- test 5: deleting a rule's text is caught ----------------------------------------------------


@pytest.mark.parametrize("step_id", ["source_readiness", "financials", "quality"])
def test_deleting_one_rules_text_from_the_contract_fails_the_prompt_check(
    step_id: str, pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = request_for(step_id, pack)
    assert missing_rules(step_id, request, compose(request)[0].text) == []
    contract = STEP_CONTRACTS[step_id]
    victim_id, victim = rules.contract_rules(contract, step_id)[1]
    monkeypatch.setitem(STEP_CONTRACTS, step_id, contract.replace(victim, ""))
    system = compose(request)[0].text
    assert missing_rules(step_id, request, system) == [victim_id]


def test_deleting_a_composer_rules_text_fails_the_prompt_check(
    pack: PreparedPack, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = request_for("source_readiness", pack)
    monkeypatch.setattr(compose_module, "O3", "O3. gone.")
    system = compose(request)[0].text
    assert missing_rules("source_readiness", request, system) == ["compose.O3"]


# --- test 4: ids are unique and stable (golden) ------------------------------------------------


@pytest.mark.parametrize("name", (rules.COMPOSE, *STEPS))
def test_rule_ids_are_unique_and_belong_to_their_list(name: str) -> None:
    ids = [r.id for r in rules.load_rules(name)]
    assert len(ids) == len(set(ids))
    assert ids
    assert all(i.startswith(f"{name}.") for i in ids)


def test_the_golden_file_pins_every_rule_id_check_and_statement() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["rules"]
    current = rules.golden_document()["rules"]
    assert list(golden) == list(current)
    for name, expected in golden.items():
        assert [r["id"] for r in current[name]] == [r["id"] for r in expected], name
        assert current[name] == expected, f"{name} differs from the golden: edit the golden"


def test_the_golden_file_pins_the_sha256_of_each_core_and_oracle() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["sha256"]
    current = rules.golden_document()["sha256"]
    assert golden["oracles"] == current["oracles"]
    assert golden["cores"] == current["cores"], (
        "a validator core changed: re-run the coverage tests and refresh the golden"
    )


def test_compose_rules_are_the_composers_own_text(pack: PreparedPack) -> None:
    """The statements of ``compose.*`` are the composer's text, so a reworded rule fails here."""
    system = compose(request_for("narrative", pack))[0].text
    for rule in rules.load_rules(rules.COMPOSE):
        if rule.when in (None, "inputs"):
            assert rule.statement in system, rule.id
