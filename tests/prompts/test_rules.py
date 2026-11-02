"""O6 Task 3: the rule lists and the coverage oracle (pure; no store, no model).

Every validator refusal has a rule (tests 1, 2) and every composed prompt names every rule it
owes (tests 3, 5). The ids, checks and statements are a golden file (test 4), so removing or
rewording a rule is an explicit edit the review sees.

The 14 new steps' lists were drafted from their oracles and cores and their statements written by
M5's separate writer. Their prompt test is strict xfail per step: each marker comes off with the
work that makes it pass (Task 4).
"""

import ast
import importlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from prompt_support import CONTRACT_STEPS, EXISTING, request_for

from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack
from deploy_workflow.prompts import NoPrompt, compose, inventory, rules
from deploy_workflow.prompts.compose import PromptRequest
from deploy_workflow.prompts.g8 import G8_RULE_ID
from deploy_workflow.prompts.p5 import P5_RULE_ID

compose_module = importlib.import_module("deploy_workflow.prompts.compose")
GOLDEN = Path(__file__).with_name("rule_lists.golden.json")
STEPS = inventory()
NEW = tuple(s for s in STEPS if s not in EXISTING)

# Issue sites and oracle ids that no rule covers yet, with the task that covers each. The test
# fails for a step if a site listed here is already covered, so this list only shrinks.
CP3_CONTEXT_READER = "CP-3 context-reader sites, UNREADABLE or PENDING (owner list)"
PENDING: dict[str, dict[str, str]] = {
    "relative_value": {
        **{
            f"fn:deploy_vii.cp3_relative_value:{name}": CP3_CONTEXT_READER
            for name in (
                "_array_rows",
                "_row_problems",
                "_strings",
                "_identity_problems",
                "_date_problems",
                "_figure_problems",
            )
        },
    },
}

# O6-P19: content checks of an existing step that no STEP_CONTRACTS line states. Each is an owner
# item, because the statement needs a vii edit. The list may only shrink.
OWNER = "owner item: no contract line states this check (a statement needs a vii edit)"
OWNER_GAPS: dict[str, dict[str, str]] = {
    "legal_covenants": {"fn:deploy_vii.cp4_legal:_shape_issues": OWNER},
    "source_context": {"fn:deploy_vii.source_context:_blank_limitations": OWNER},
    "financials": {"fn:deploy_vii.cp1_workflow:_validate_stage": OWNER},
}


def xfail_new(step_id: str, *, reason: str, raises: type[BaseException] | None = None) -> Any:
    """The parameter for a step: plain for the 12 with a text, strict xfail for the 14 new ones.
    ``{step}`` in ``reason`` is the step id."""
    if step_id in EXISTING:
        return step_id
    mark = pytest.mark.xfail(strict=True, raises=raises, reason=reason.format(step=step_id))
    return pytest.param(step_id, marks=mark)


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
    known = {**PENDING.get(step_id, {}), **OWNER_GAPS.get(step_id, {})}
    uncovered, stale = gaps(step_id, covered_by(step_id), needed, known)
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


@pytest.mark.parametrize("step_id", CONTRACT_STEPS)
def test_an_existing_step_carries_its_contract_rules_whole(step_id: str) -> None:
    expected = rules.contract_rules(STEP_CONTRACTS[step_id], step_id)
    # source_readiness.g8 and .p5 are the composer's CP-0 blocks, not contract lines
    # (tests/prompts/test_g8.py, p5_strip.py)
    composer_owned = {G8_RULE_ID, P5_RULE_ID}
    got = [(r.id, r.statement) for r in rules.load_rules(step_id) if r.id not in composer_owned]
    assert got == list(expected)
    letters = re.findall(r"^([a-z])\. ", STEP_CONTRACTS[step_id], re.MULTILINE)
    assert [i for i, _ in expected] == [f"{step_id}.{c}" for c in letters]
    for _, statement in expected:
        assert statement in STEP_CONTRACTS[step_id]


@pytest.mark.parametrize("step_id", STEPS)
def test_every_rule_has_a_check(step_id: str) -> None:
    for rule in rules.load_rules(step_id):
        assert rule.checks or rule.from_code, f"{rule.id} enforces nothing"


@pytest.mark.parametrize("step_id", STEPS)
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
    composer = {c for r in rules.load_rules(rules.COMPOSE) for c in r.checks}
    assert drafted <= committed | composer
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
        if rule.when == "pins" and compose_module.request_pin_form(request) is None:
            continue
        out.append(rule)
    return out


def missing_rules(step_id: str, request: PromptRequest, system: str) -> list[str]:
    """Rule ids whose token or statement is not in the system message."""
    lost = []
    for rule in rules.load_rules(step_id):
        if f"[{rule.id}]" not in system or rule.statement not in system:
            lost.append(rule.id)
    # O6-P21: a composer rule is named by its token too
    lost.extend(
        r.id for r in applicable(request) if f"[{r.id}]" not in system or r.statement not in system
    )
    return lost


@pytest.mark.parametrize(
    "step_id",
    [xfail_new(s, raises=NoPrompt, reason="O6 Task 4: no text for {step} yet") for s in STEPS],
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
    assert "compose.O6" not in ids and "CP-0" not in compose_module.PINS_ENABLED


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
    assert list(golden) == list(current), (
        "the set of rule lists changed: a list was added or removed, which is an explicit edit "
        "of tests/prompts/rule_lists.golden.json (a rule-list change goes to the O6 rule-list process)"
    )
    for name, expected in golden.items():
        assert [r["id"] for r in current[name]] == [r["id"] for r in expected], name
        assert current[name] == expected, f"{name} differs from the golden: edit the golden"


def test_the_golden_file_pins_the_sha256_of_each_core_and_oracle() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["sha256"]
    current = rules.golden_document()["sha256"]
    assert golden["oracles"] == current["oracles"], "an oracle changed: see the cores message below"
    assert golden["cores"] == current["cores"], (
        "a validator core or oracle changed: run the coverage tests (test 1); if only this test "
        "fails, refresh the sha256 section with rules.refresh_sha256 in its own commit (O6-P20); "
        "any other failure goes to the O6 rule-list process"
    )


def test_compose_rules_are_the_composers_own_text(pack: PreparedPack) -> None:
    """The statements of ``compose.*`` are the composer's text, so a reworded rule fails here."""
    system = compose(request_for("narrative", pack))[0].text
    for rule in rules.load_rules(rules.COMPOSE):
        if rule.when in (None, "inputs"):
            assert rule.statement in system, rule.id


# --- fix round 1 -----------------------------------------------------------------------------------


def _mutated(module: str, new_source: str, call: str, into: str) -> str:
    """The module's text with ``new_source`` appended and ``call`` inserted into ``into``."""
    tree = ast.parse(rules.module_path(module).read_text(encoding="utf-8"))
    target = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == into)
    target.body.insert(0, ast.parse(call).body[0])
    tree.body.append(ast.parse(new_source).body[0])
    return ast.unparse(ast.fix_missing_locations(tree))


RETURNED = {
    "list comprehension": (
        "def _probe_issues(xs):\n    return [f'documents: {x} twice' for x in xs]",
        "list(_probe_issues(()))",
    ),
    "yield": (
        "def _probe_issues(xs):\n    for x in xs:\n        yield f'Financial scope lacks {x}'",
        "list(_probe_issues(()))",
    ),
    "tuple": (
        "def _probe_problems(x):\n    return ('a new refusal for the row',)",
        "_probe_problems(0)",
    ),
    "annotated": (
        "def _probe_rows(x) -> tuple[str, ...]:\n    return (f'a new refusal for {x}',)",
        "_probe_rows(0)",
    ),
}


@pytest.mark.parametrize("shape", sorted(RETURNED))
def test_a_returned_or_yielded_issue_in_a_new_function_has_no_rule(shape: str) -> None:
    new, call = RETURNED[shape]
    module, step_id = "deploy_vii.cp4_legal", "legal_covenants"
    mutated = _mutated(module, new, call, "validate_covenant_interpretation")
    needed = rules.needed_checks(step_id, {module: mutated})
    uncovered, _ = gaps(step_id, covered_by(step_id), needed, OWNER_GAPS[step_id])
    name = new.split("(")[0].removeprefix("def ")
    assert uncovered == [f"fn:{module}:{name}"]


def test_a_function_that_returns_text_without_an_issue_name_or_annotation_is_not_a_site() -> None:
    module, step_id = "deploy_vii.cp4_legal", "legal_covenants"
    new, call = "def _helper(x):\n    return [f'label {x}']", "_helper(0)"
    mutated = _mutated(module, new, call, "validate_covenant_interpretation")
    assert rules.needed_checks(step_id, {module: mutated}) == rules.needed_checks(step_id)


def test_step_validation_with_a_literal_issue_is_a_site() -> None:
    module, step_id = "deploy_vii.cp4_legal", "legal_covenants"
    new = "def _probe_issues(x):\n    return StepValidation(issues=(f'refused {x}',))"
    mutated = _mutated(module, new, "_probe_issues(0)", "validate_covenant_interpretation")
    needed = rules.needed_checks(step_id, {module: mutated})
    assert f"fn:{module}:_probe_issues" in needed


def test_non_content_checks_are_subtracted_and_never_in_a_list() -> None:
    assert rules.NON_CONTENT
    for step_id in STEPS:
        assert not set(rules.NON_CONTENT) & rules.needed_checks(step_id), step_id
        listed = {c for r in rules.load_rules(step_id) for c in r.checks}
        assert not listed & set(rules.NON_CONTENT), f"{step_id} lists a non-content check"
    assert "fn:deploy_vii.cp4_legal:stale_issues" in rules.NON_CONTENT
    assert "fn:deploy_workflow.owners.cp1c:_provenance_issues" in rules.NON_CONTENT


def test_a_non_content_function_takes_no_submission() -> None:
    allowed = {"upstream", "pack", "inputs", "bound", "current"}
    for check in rules.NON_CONTENT:
        if not check.startswith("fn:"):
            continue
        module, _, qualname = check.removeprefix("fn:").rpartition(":")
        function = rules.function_node(module, qualname)
        for arg in function.args.args + function.args.kwonlyargs:
            if arg.arg in ("self", "cls"):
                continue
            notes = ast.unparse(arg.annotation) if arg.annotation else ""
            assert arg.arg in allowed, f"{check}: parameter {arg.arg} may hold a submission"
            assert not re.search(r"Submission|Review|Report", notes), f"{check}: {notes}"


def _oracle_item(case: str, ident: str) -> dict[str, Any]:
    """The oracle entry with this id or, for a dict-keyed container, this name."""
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("id") == ident:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(rules.oracle_path(case).read_text(encoding="utf-8")))
    assert found, f"{case}:{ident} is in no oracle entry"
    return found[0]


def test_a_non_content_oracle_id_arises_with_no_step_submission() -> None:
    """O6-P18a: a stale-input refusal is a bound-input mismatch; a source-unreadable one comes from
    the pack (or the context file) alone."""
    seen = 0
    for check, why in rules.NON_CONTENT.items():
        if not check.startswith("oracle:"):
            continue
        _, case, ident = check.split(":")
        item = _oracle_item(case, ident)
        seen += 1
        if why == rules.UPSTREAM:
            issues = item["expected_issues"]
            assert issues and all(i.startswith("Stale input ") for i in issues), check
        else:
            assert why == rules.UNREADABLE, check
            assert (
                item.get("pack") == "unparseable"
                or "source_fixture" in item
                or "context" in item
                and item["id"] == "context-unreadable"
            ), check
    assert seen == 15


def test_owner_gaps_may_only_shrink() -> None:
    for step_id, entries in OWNER_GAPS.items():
        assert set(entries) <= rules.needed_checks(step_id), f"{step_id}: stale owner gap"
        assert not set(entries) & covered_by(step_id), f"{step_id}: covered, remove it"


def test_golden_pins_every_module_named_by_an_fn_check() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["sha256"]["cores"]
    modules = {
        rules.module_path(c.split(":")[1]).relative_to(rules.ROOT).as_posix()
        for name in (rules.COMPOSE, *STEPS)
        for r in rules.load_rules(name)
        for c in r.checks
        if c.startswith("fn:")
    }
    assert modules <= set(golden), sorted(modules - set(golden))


def test_the_sha_refresh_rewrites_only_the_sha256_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        rules, "dirty_paths", lambda paths, root=rules.ROOT: []
    )  # no git in an archive
    stale = json.loads(GOLDEN.read_text(encoding="utf-8"))
    stale["sha256"]["cores"] = {k: "0" * 64 for k in stale["sha256"]["cores"]}
    target = tmp_path / "golden.json"
    target.write_text(json.dumps(stale), encoding="utf-8")
    rules.refresh_sha256(target)
    refreshed = json.loads(target.read_text(encoding="utf-8"))
    assert refreshed["rules"] == stale["rules"]
    assert refreshed["sha256"] == rules.golden_document()["sha256"]


def test_the_oracle_exclusions_are_recorded_with_a_reason() -> None:
    assert set(rules.ORACLE_EXCLUSIONS) >= {
        "cp2h-context",
        "cp4",
        "context-attachments",
        "valuation-context",
        "pins-context",
    }
    for case, why in rules.ORACLE_EXCLUSIONS.items():
        assert why.strip()
        assert rules.oracle_path(case.split("#")[0]).exists(), case


def test_an_oracle_item_with_no_id_is_refused_not_dropped() -> None:
    with pytest.raises(ValueError, match="no id"):
        rules.groups_of({"refusals": [{"id": "r01"}, {"class": "x"}]})


def test_an_oracle_name_both_nested_and_top_level_is_refused() -> None:
    document = {
        "tool_use_refusals": [{"id": "dup"}],
        "refusals": {"tool_use_refusals": [{"id": "dup"}], "note": "x"},
    }
    with pytest.raises(ValueError, match="both"):
        rules.groups_of(document)


def test_a_rule_whose_checks_are_not_a_list_is_a_type_error() -> None:
    with pytest.raises(TypeError, match="checks"):
        rules.rule_from({"id": "x.1", "statement": "s", "checks": "fn:a:b"})


# --- fix round 2 ---------------------------------------------------------------------------------

LIMITS = {
    "fn:deploy_vii.cp3_relative_value:Upstream.limits",
    "fn:deploy_vii.cp3_relative_value:_evidence_limitations",
    "fn:deploy_workflow.owners.cp1c:_bounded",
    "fn:deploy_workflow.owners.cp1d:_bounded",
    "fn:deploy_workflow.owners.cp3c:_names",
    "fn:deploy_workflow.owners.cp3d:_single_dealer",
    "fn:deploy_workflow.owners.cp8:_Composer._limitations",
    "fn:deploy_workflow.owners.cp2g:_own_limitations",
    "fn:deploy_workflow.owners.cp2d:_limitations",
    "fn:deploy_workflow.owners.cp2d:_facility_limitations",
    "fn:deploy_workflow.owners.cp3d:own_limitations",
    "fn:deploy_workflow.owners.cp1c:_limitations",
    "fn:deploy_workflow.owners.cp2h:_own_limitations",
    "fn:deploy_workflow.owners.cp4c:_own_limitations",
    "fn:deploy_workflow.owners.cp4c:_selection_line",
    "fn:deploy_workflow.owners.cp4c:_fixed_limitations",
    "fn:deploy_workflow.owners.cp2e:own_limitations",
    "fn:deploy_workflow.owners.cp2d:_claims",
    "fn:deploy_workflow.owners.cp2e:_fx_claim",
    "fn:deploy_workflow.owners.cp2e:_hedge_claim",
    "fn:deploy_workflow.owners.cp2e:_rate_claims",
    "fn:deploy_workflow.owners.cp2g:_claims",
    "fn:deploy_workflow.owners.cp2h:_claims",
    "fn:deploy_workflow.owners.cp4c:_claims",
    "fn:deploy_workflow.owners.cpl10:_claims",
    "fn:deploy_workflow.owners.cpl10:_item_rows",
    "fn:deploy_workflow.owners.cp3d:_Composer.missing_inputs",
    "fn:deploy_workflow.owners.cp2h:_with_upstream_citations",
    "fn:deploy_workflow.owners.cp8:_Composer._resolved",
    "fn:deploy_workflow.owners.cp2d:check_cp1_totals",
    "fn:deploy_workflow.owners.cp4c:_Book.cells",
    "fn:deploy_vii.readiness:absent_page_ranges",
    "fn:deploy_workflow.owners.cp3d:_issues",
}


def test_not_issue_sites_hold_the_helpers_and_are_not_non_content() -> None:
    assert set(rules.NOT_ISSUE_SITES) == LIMITS
    assert not set(rules.NOT_ISSUE_SITES) & set(rules.NON_CONTENT)
    assert all(why.strip() for why in rules.NOT_ISSUE_SITES.values())
    for step_id in STEPS:
        assert not set(rules.NOT_ISSUE_SITES) & rules.needed_checks(step_id), step_id
        listed = {c for r in rules.load_rules(step_id) for c in r.checks}
        assert not listed & set(rules.NOT_ISSUE_SITES), step_id


@pytest.mark.parametrize("step_id", NEW)
def test_a_check_the_composer_carries_is_not_drafted_into_a_step(step_id: str) -> None:
    composer = {c for r in rules.load_rules(rules.COMPOSE) for c in r.checks}
    drafted = {c for r in rules.extract_checks(step_id)["rules"] for c in r["checks"]}
    assert not drafted & composer, sorted(drafted & composer)
    assert not {c for r in rules.load_rules(step_id) for c in r.checks} & {
        c for r in rules.load_rules(rules.COMPOSE) for c in r.checks if c.endswith(":_pin_lines")
    }


def test_a_returned_issue_without_prose_in_an_issue_named_function_is_a_site() -> None:
    module, step_id = "deploy_vii.cp4_legal", "legal_covenants"
    new = "def _probe_issues(x):\n    return [x.reason]"
    mutated = _mutated(module, new, "_probe_issues(0)", "validate_covenant_interpretation")
    needed = rules.needed_checks(step_id, {module: mutated})
    assert f"fn:{module}:_probe_issues" in needed
    empty = "def _probe_issues(x):\n    return []"
    mutated = _mutated(module, empty, "_probe_issues(0)", "validate_covenant_interpretation")
    assert f"fn:{module}:_probe_issues" not in rules.needed_checks(step_id, {module: mutated})


def test_the_run_text_issue_functions_are_covered() -> None:
    for step_id, module in (
        ("forward_credit_model", "cp2g"),
        ("rating_triggers", "cp2h"),
    ):
        check = f"fn:deploy_workflow.owners.{module}:_run_text_issues"
        assert check in rules.needed_checks(step_id)
        assert check in covered_by(step_id)


def _git(root: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_dirty_paths_names_only_uncommitted_pinned_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "c")
    assert rules.dirty_paths([tmp_path / "a.py", tmp_path / "b.py"], root=tmp_path) == []
    (tmp_path / "b.py").write_text("y = 2\n")
    assert rules.dirty_paths([tmp_path / "a.py", tmp_path / "b.py"], root=tmp_path) == ["b.py"]


def test_dirty_paths_names_an_untracked_pinned_file(tmp_path: Path) -> None:
    """O6 T3 I-b: a pinned file no commit holds yet is as dirty as an edited one."""
    (tmp_path / "a.py").write_text("x = 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "c")
    (tmp_path / "new.py").write_text("z = 1\n")
    (tmp_path / "other.py").write_text("not pinned\n")
    pinned = [tmp_path / "a.py", tmp_path / "new.py"]
    assert rules.dirty_paths(pinned, root=tmp_path) == ["new.py"]


def test_the_golden_is_not_refreshed_or_written_from_a_dirty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rules, "dirty_paths", lambda paths, root=rules.ROOT: ["src/x/dirty.py"])
    target = tmp_path / "golden.json"
    target.write_text(GOLDEN.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(rules.DirtyTree, match="src/x/dirty.py"):
        rules.refresh_sha256(target)
    with pytest.raises(rules.DirtyTree, match="src/x/dirty.py"):
        rules.write_golden(tmp_path / "new.json")
    assert target.read_text(encoding="utf-8") == GOLDEN.read_text(encoding="utf-8")
    assert not (tmp_path / "new.json").exists()


# --- fix round 1 (M4): a module-level string constant is text --------------------------------

CONSTANT_SITE = """
ERR = "bad thing"
FMT = ("x {i} "
       "y")
PATTERN = re.compile("a b")
NAMES = ("a b", "c d")

def entry(local):
    issues = []
    issues.append(ERR)
    issues.append(FMT.format(i=1))
    issues.append(PATTERN)
    issues.append(NAMES)
    issues.append(local)
    return issues
"""


def test_an_append_of_a_module_level_string_constant_is_a_site() -> None:
    """``issues.append(CONST)`` and ``issues.append(CONST.format(...))`` refuse like a literal;
    a compiled pattern, a tuple and a local name are not text."""
    assert rules.issue_functions("m", "entry", CONSTANT_SITE) == {"entry": 2}


def test_a_name_that_is_not_a_module_level_string_is_not_a_site() -> None:
    source = CONSTANT_SITE.replace('ERR = "bad thing"', "ERR = make()")
    assert rules.issue_functions("m", "entry", source) == {"entry": 1}
