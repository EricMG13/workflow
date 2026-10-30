"""CP-8 Stage 2: the connection of the owner core (lease ``docs/CP8-OWNER-LEASE.md``).

Fast parts only (each file under about 60 s). The store runs (``tests/test_owner_cp8.py``), the
D3 run assertions, receipts, tamper, promotion and the render runs are deferred (the driver is
``tests/cp8_runs.py``). Every expected value is read from ``cases/cp8-owner`` or the lease; a fake
store appears only here, never in ``src``.
"""

import copy
import importlib
import json
import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest
from defect_classes import BLANK_VALUES
from test_method_cp8 import upstream as stage1_upstream

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.cp8 import CP8
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Input, Module, ModuleView, Run, View
from deploy_vii.cp6_committee import ACTION_BIAS_FACT, CONFIDENCE_FACT
from deploy_vii.execution import Attempt, Execution, Head, Qualification, StepValidation
from deploy_vii.live.tools import UNBACKED_ABSENCE, Seen
from deploy_vii.registry import plan, step_chain
from deploy_vii.report_view import _spec_of, build, build_index, gap_refs, pathways
from deploy_workflow import host
from deploy_workflow.owners import cp8
from deploy_workflow.owners.cp8 import (
    DecisionLedgerSubmission,
    Upstream,
    source_authority,
    validate_ledger,
)

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp8-owner"
EXPECTED = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text())
METHODS = ROOT / "src/deploy_vii/methods/cp8.md"
PREFIX = "Cited page not read through read_pages"


# --- inputs from the oracle (the Stage 1 test's own helpers, restated for this file) ----------------


def _upstream() -> Upstream:
    facts = []
    for item in EXPECTED["cp0"]["positive"]["facts"]:
        table, rest = item["fact_id"].split(".", 1)
        row, field = rest.rsplit(".", 1)
        facts.append(
            Fact(
                fact_id=item["fact_id"],
                label=field,
                table_id=table,
                row_id=row,
                field=field,
                text=item["text"],
            )
        )
    return Upstream(
        as_of=date.fromisoformat(EXPECTED["cases"]["positive"]["run"]["as_of"]),
        authority=source_authority(facts),
    )


def _pack() -> tuple[Any, ...]:
    from test_method_cp8 import pack

    return pack("positive")


def _issues(payload: dict[str, Any]) -> tuple[str, ...]:
    return validate_ledger(
        submission=DecisionLedgerSubmission.model_validate_json(json.dumps(payload)),
        upstream=_upstream(),
        pack=_pack(),
    )


def _quote_sites(node: Any, path: str = "") -> Iterator[str]:
    """The JSON path of every quote object (source_id, locator, quote) of a submission; the
    validator's path for a quote object is its JSON path."""
    if isinstance(node, dict):
        if {"source_id", "locator", "quote"} <= set(node):
            yield path
        for key, value in node.items():
            yield from _quote_sites(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _quote_sites(value, f"{path}[{i}]")


def _at(document: Any, path: str) -> dict[str, Any]:
    for part in re.findall(r"[^.\[\]]+", path):
        document = document[int(part)] if part.isdigit() else document[part]
    result: dict[str, Any] = document
    return result


# --- backlog: guard-limit notes (methods/cp8.md) -----------------------------------------------------

NOTES = {
    "rule W": ("rule W", "spaced range", "dash bullet"),
    "round 10 sign rule": ("round 10", "minus", "accounting parentheses"),
    "unsigned grammar": ("unsigned", "negative net leverage", "does not occur"),
    "item 2 date guard": ("item 2", "ISO", "day-first"),
    "item 8 comma costs": (
        "item 8",
        "grouped figure",
        "decimal comma",
        "comma-space list",
        "figure after a year",
        "day of a",
    ),
    "_labelled narrow join": ("_labelled", ",<digit>", "comma-space"),
}


@pytest.mark.parametrize("note", sorted(NOTES))
def test_methods_file_records_each_guard_limit(note: str) -> None:
    text = METHODS.read_text(encoding="utf-8")
    missing = [phrase for phrase in NOTES[note] if phrase not in text]
    assert not missing, f"{note}: methods/cp8.md lacks {missing}"


def test_methods_file_keeps_the_adaptation_record() -> None:
    """The freeze moves docs/methods-drafts/cp8.md to methods/cp8.md: its tables stay."""
    text = METHODS.read_text(encoding="utf-8")
    draft = (ROOT / "docs/methods-drafts/cp8.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| ([A-C][0-9]+) \|", draft, flags=re.MULTILINE)
    assert len(rows) == 28
    for row in rows:
        assert f"| {row} |" in text, row


# The notes describe what the readers do; these pin it (characterization: they pass as Stage 1
# stands, so a note can never say more or less than the code).


def test_rule_w_refuses_a_spaced_range_and_a_dash_bullet() -> None:
    assert cp8._token_once("1.80", "Total leverage 1.80x")
    assert not cp8._token_once("1.80", "Range 2.00 - 1.80x")
    assert not cp8._token_once("1.80", "- 1.80x was reported")


def test_sign_rule_reads_a_minus_or_accounting_parentheses_as_another_figure() -> None:
    assert not cp8._token_once("1.80", "Total leverage -1.80x")
    assert not cp8._token_once("1.80", "Total leverage (1.80)x")


def test_unsigned_grammar_cannot_record_a_negative_figure() -> None:
    assert not cp8._labelled("total_leverage", "1.25", "Total leverage was -1.25x")
    assert not cp8._token_once("1.25", "Net total leverage was -1.25x")


def test_item_2_date_guard_sees_month_day_year_only() -> None:
    at = "January 9, 2026"
    assert cp8._only_date(at, f"as of {at}")
    assert not cp8._only_date(at, f"as of {at} and March 31, 2026")
    assert cp8._only_date(at, f"as of {at} and 2026-03-31 and 31 March 2026")


@pytest.mark.parametrize(
    ("value", "quote"),
    [
        ("250.00", "Fees of 1,250.00 apply"),  # a grouped figure of 1,000 or more
        ("2.50", "Rates of 1, 2.50 and 3.00"),  # a comma-space list
        ("2.50", "In 2025, 2.50x"),  # a figure after a year
        ("2.50", "As of March 31, 2.50x"),  # a figure after the day of a Month D, YYYY date
        ("2.50", "Rate 1,2.50x"),  # a decimal comma
    ],
)
def test_item_8_comma_costs_are_refused(value: str, quote: str) -> None:
    assert not cp8._token_once(value, quote)


def test_labelled_joins_only_a_comma_directly_before_a_digit() -> None:
    assert not cp8._labelled("total_leverage", "1.80", "Total leverage 1,250 and 1.80x")
    assert cp8._labelled("total_leverage", "1.80", "Total leverage as of March 31, 2026 is 1.80x")
    assert cp8._labelled("total_leverage", "1.80", "Total leverage 1, 2 and 1.80x")


# --- backlog: a blank citation quote (round 13 addendum 3) -------------------------------------------

POSITIVE = SUBMISSIONS["positive"]
SITES = list(_quote_sites(POSITIVE))
BLANKS = [v for v in BLANK_VALUES if v != ""]  # "" stays the schema's Text min_length refusal


def test_the_positive_literal_is_the_accepted_twin() -> None:
    assert _issues(POSITIVE) == ()


def test_every_quote_site_is_inventoried() -> None:
    """The inventory: where the submission takes a citation (a quote that is not a site is not
    refused as blank, so a new site must be listed here and routed through ``_cite``)."""
    assert {"decision.action_bias.quote", "thesis.downside_paths.quote"} <= set(SITES)
    assert any(site.startswith("observations[") for site in SITES)
    assert "default_restructuring.quote" in SITES
    assert any(site.startswith("thesis.downside_sizes[") for site in SITES)
    assert any(".absence.quote" in site for site in SITES)


@pytest.mark.parametrize("blank", BLANKS, ids=lambda b: repr(b))
@pytest.mark.parametrize("site", SITES)
def test_a_blank_citation_quote_is_refused_before_the_page_check(site: str, blank: str) -> None:
    payload = copy.deepcopy(POSITIVE)
    _at(payload, site)["quote"] = blank
    found = _issues(payload)
    assert f"{site}.quote: empty text" in found
    assert not [i for i in found if i.startswith("Quote/locator mismatch")]


# --- plug-in parts (protocol §2) ---------------------------------------------------------------------

ENTRIES = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}


def _seen(read: list[list[str]], searched: bool) -> Seen:
    return Seen(
        read=frozenset((source, locator) for source, locator in read),
        searched=(None,) if searched else (),
    )


def test_core_attributes() -> None:
    assert (cp8.MODULE_ID, cp8.STEP_ID) == ("CP-8", "decision_ledger")
    assert cp8.STEP_IDS == ("decision_ledger",)
    assert type(cp8.STEP_IDS) is tuple and all(type(i) is str for i in cp8.STEP_IDS)
    assert cp8.SCHEMAS == {"decision_ledger": DecisionLedgerSubmission}
    assert cp8.QUALIFICATION == Qualification(implementation="implemented")
    assert cp8.ENTRY_VALIDATOR is cp8._validate_step
    for name in ("probe", "submit", "RULES", "cp8_upstream", "cp8_module", "cp8_reader"):
        assert callable(getattr(cp8, name)), name
    assert not hasattr(cp8, "view")  # inputs="none": the step has no read view
    assert not hasattr(cp8, "precheck")


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_schema_round_trips_and_gives_the_tail_digest(case: str) -> None:
    schema = cp8.SCHEMAS[cp8.STEP_ID]
    payload = json.dumps(SUBMISSIONS[case])
    model = schema.model_validate_json(payload)
    assert schema.model_validate_json(model.model_dump_json()) == model
    digest = model.content_hash()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    other = "no_outcome" if case == "positive" else "positive"
    assert schema.model_validate_json(json.dumps(SUBMISSIONS[other])).content_hash() != digest
    # the tail input of the settled head is this digest (host._submission_producer_inputs)
    assert cp8.SUBMISSION_INPUT == "decision-ledger-submission"
    assert cp8.SUBMISSION_INPUT == cp8.STEP_ID.replace("_", "-") + "-submission"


@pytest.mark.parametrize("rid", sorted(ENTRIES))
def test_rules_reproduce_the_oracle_tool_rule_issues(rid: str) -> None:
    entry = ENTRIES[rid]
    read = EXPECTED["cases"][entry["base"]]["tool_use_required"]["read_pages_cover"]
    got = cp8.RULES(json.dumps(entry["literal"]), _seen(read, True))
    assert got == tuple(entry["rules_issues"])


def test_rules_on_the_shape_literal_and_on_text_that_is_not_an_object() -> None:
    read = EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"]
    shape = SUBMISSIONS["shape_refusal"]["literal"]
    assert cp8.RULES(json.dumps(shape), _seen(read, True)) == ()
    for text in ("", "[]", "null", "not json", '{"decision": 3}'):
        assert cp8.RULES(text, _seen([], False)) == ()


@pytest.mark.parametrize("item", SUBMISSIONS["tool_use_refusals"], ids=lambda i: i["id"])
def test_rules_reproduce_the_tool_use_refusals(item: dict[str, Any]) -> None:
    got = cp8.RULES(json.dumps(SUBMISSIONS[item["literal"]]), _seen(item["read"], item["searched"]))
    pinned = next(t for t in EXPECTED["tool_use_refusals"] if t["id"] == item["id"])
    assert got == tuple(item["issues"]) == tuple(pinned["issues"])


def test_rules_run_the_absence_rule_before_the_unread_rule() -> None:
    got = cp8.RULES(json.dumps(POSITIVE), _seen([], False))
    assert got[0] == UNBACKED_ABSENCE
    assert [i.split(": ")[0] for i in got[1:]] == [PREFIX] * 4
    assert list(got[1:]) == sorted(got[1:])


def test_rules_absence_lines_name_no_caller_text() -> None:
    payload = copy.deepcopy(POSITIVE)
    payload["outcome_absence"] = {"reason": "x" * 5000, "follow_up": "y"}
    got = cp8.RULES(json.dumps(payload), _seen([], False))
    assert got[0] == UNBACKED_ABSENCE and all(len(line) <= 600 for line in got)


# --- the store adapter (settled heads -> the Stage 1 input object) -----------------------------------


def _facts(case: str) -> tuple[Fact, ...]:
    out = []
    for item in EXPECTED["cp0"][case]["facts"]:
        table, rest = item["fact_id"].split(".", 1)
        row, field = rest.rsplit(".", 1)
        out.append(
            Fact(
                fact_id=item["fact_id"],
                label=field,
                table_id=table,
                row_id=row,
                field=field,
                text=item["text"],
            )
        )
    return tuple(out)


def _module(module_id: str, facts: tuple[Fact, ...], case: str = "positive") -> Module:
    run = EXPECTED["cases"][case]["run"]
    return Module(
        run_id=run["run_id"],
        issuer_id=run["issuer_id"],
        as_of=date.fromisoformat(run["as_of"]),
        module_id=module_id,
        status="accepted",
        facts=facts,
    )


def _cp6(bias: str, confidence: str) -> Module:
    def cell(fact_id: str, text: str) -> Fact:
        table, row, field = fact_id.split(".")
        return Fact(
            fact_id=fact_id, label=field, table_id=table, row_id=row, field=field, text=text
        )

    return _module("CP-6", (cell(ACTION_BIAS_FACT, bias), cell(CONFIDENCE_FACT, confidence)))


class FakeStore:
    """Test-only: the two reads the adapter makes of an Execution."""

    def __init__(self, case: str, modules: list[Module]) -> None:
        self.run = SimpleNamespace(
            as_of=date.fromisoformat(EXPECTED["cases"][case]["run"]["as_of"])
        )
        self.by_hash = {m.content_hash(): m for m in modules}

    def read(self) -> Any:
        return SimpleNamespace(run=self.run)

    def result(self, sha256: str) -> Module:
        return self.by_hash[sha256]


def _attempt(*modules: Module) -> Attempt:
    return Attempt(
        ticket_id="t1",
        module_id="CP-8",
        inputs=(
            Input(input_id="prepared-pack", sha256="0" * 64),
            *(Input(input_id=m.module_id, sha256=m.content_hash()) for m in modules),
        ),
        number=0,
    )


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_adapter_returns_the_stage_1_input_object(case: str) -> None:
    cp0 = _module("CP-0", _facts(case), case)
    got = cp8.cp8_upstream(store=cast(Any, FakeStore(case, [cp0])), attempt=_attempt(cp0))
    assert got == stage1_upstream(case)
    assert got.cp6 is None


def test_adapter_reads_the_settled_cp6_call_when_bound() -> None:
    cp0, cp6 = _module("CP-0", _facts("positive")), _cp6("Overweight", "High")
    store = cast(Any, FakeStore("positive", [cp0, cp6]))
    got = cp8.cp8_upstream(store=store, attempt=_attempt(cp0, cp6))
    assert got == stage1_upstream("positive", ("Overweight", "High"))
    # a CP-6 in the store but not bound to the attempt is not read
    assert cp8.cp8_upstream(store=store, attempt=_attempt(cp0)).cp6 is None


def test_adapter_fails_closed_without_cp0_or_a_settled_cp6_call() -> None:
    cp0 = _module("CP-0", _facts("positive"))
    store = cast(Any, FakeStore("positive", [cp0, _module("CP-6", ())]))
    with pytest.raises(ValueError, match="binds no CP-0"):
        cp8.cp8_upstream(store=store, attempt=_attempt())
    with pytest.raises(ValueError, match="no settled action bias"):
        cp8.cp8_upstream(store=store, attempt=_attempt(cp0, _module("CP-6", ())))


def test_cp8_module_binds_the_attempt_inputs_then_the_submission_digest() -> None:
    out = cp8.LedgerOutput(
        run=_run("positive"),
        submission_sha256="a" * 64,
        facts=(),
        tables=(),
        claims=(),
        limitations=("x",),
    )
    attempt = _attempt()
    module = cp8.cp8_module(report=out, inputs=attempt.inputs, attempt=1)
    assert [i.input_id for i in module.inputs] == ["prepared-pack", "decision-ledger-submission"]
    assert module.inputs[-1].sha256 == "a" * 64
    assert (module.module_id, module.attempt, module.limitations) == ("CP-8", 1, ("x",))
    assert (module.run_id, module.as_of) == ("slice-cp8-positive", date(2026, 4, 30))


def _run(case: str) -> Run:
    return Run.model_validate_json(json.dumps(EXPECTED["cases"][case]["run"]))


# --- registrations in owner_workflow (the lease's Files section) -------------------------------------


def test_registration_rows_equal_the_lease() -> None:
    spec = owner.OWNER_SPECS["CP-8"]
    assert spec == owner.OwnerSpec(
        "CP-8",
        (
            owner.StepSpec(
                "decision_ledger",
                DecisionLedgerSubmission,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="none",
                rules="journaled",
            ),
        ),
        "owner_core",
        "analytical",
        None,
    )
    owner._check_steps("CP-8", spec)
    assert "CP-8" in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES["CP-8"] is cp8
    assert owner._QUALIFICATION["CP-8"] is cp8.QUALIFICATION
    assert owner._PROBES["CP-8"] is cp8.probe
    assert owner._ENTRY_VALIDATORS["CP-8"] is cp8.ENTRY_VALIDATOR
    assert "CP-8" not in owner._PRECHECKS
    assert "decision_ledger" not in owner._VIEWS
    assert ("CP-8", "decision_ledger") in host._OWNER_SCOPES
    assert host._SOURCE_STEPS["CP-8"] == ("decision_ledger",)


def test_registrations_are_append_only() -> None:
    assert list(owner.OWNER_SPECS)[:5] == ["CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL"]
    assert list(owner._QUALIFICATION)[:4] == ["CP-1", "CP-1A", "CP-2", "CP-MODEL"]
    assert list(owner._PROBES)[:4] == ["CP-0", "CP-1", "CP-1A", "CP-2"]
    assert list(owner._ENTRY_VALIDATORS)[:2] == ["CP-1A", "CP-2"]
    assert list(owner._VIEWS)[:1] == ["credit_synthesis"]


def test_plan_is_cp0_then_cp8() -> None:
    assert plan(("CP-8",)) == ("CP-0", "CP-8")
    with pytest.raises(ValueError, match="has no live step contract"):
        step_chain("CP-8")


# --- bindings (data only; the what-changed block) ----------------------------------------------------

BLOCKS = {
    "cp8.what_changed": "what-changed",
    **{f"T7.{n}": "evidence" for n in range(1, 8)},
    "T7.8": "limitations",
}


def test_binding_map_equals_the_lease() -> None:
    assert CP8.module_id == "CP-8"
    assert {e.fact_coord.table_id: e.block_id for e in CP8.entries} == BLOCKS
    assert len(CP8.entries) == len(BLOCKS)
    assert all(e.cell_slot.startswith("cp8-") for e in CP8.entries)
    assert all(e.fact_coord.module_id == "CP-8" for e in CP8.entries)
    assert cp8.WHAT_CHANGED == "cp8.what_changed"


def test_binding_map_is_shipped_last_and_slots_are_unique() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert CP8 in SHIPPED_MAPS
    assert ids.index("CP-8") > ids.index("CP-6")
    assert len(SHIPPED_MAPS) == len({m.module_id for m in SHIPPED_MAPS})
    slots = [e.slot for m in SHIPPED_MAPS for e in m.entries]
    assert len(slots) == len(set(slots))


def test_binding_module_does_not_import_the_workflow() -> None:
    source = (ROOT / "src/deploy_vii/bindings/cp8.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from|import) deploy_workflow", source, flags=re.MULTILINE)


def _view_facts(case: str) -> tuple[Fact, ...]:
    out = []
    for table in EXPECTED["cases"][case]["tables"]:
        for row in table["rows"]:
            for item in row["facts"]:
                out.append(
                    Fact(
                        fact_id=item["fact_id"],
                        label=item["column"],
                        table_id=table["table_id"],
                        row_id=row["row_id"],
                        field=item["fact_id"].rsplit(".", 1)[1],
                        text="x",
                    )
                )
    return tuple(out)


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_expected_tables_bind_exactly_once(case: str) -> None:
    facts = _view_facts(case)
    assert len(facts) == (181 if case == "positive" else 153)
    view = View(
        run=_run(case),
        mode="accepted",
        modules=(
            ModuleView(
                module_id="CP-8",
                title="CP-8",
                aliases=(),
                status="restricted",
                artifact_sha256="b" * 64,
                facts=facts,
            ),
        ),
    )
    assert validate_bindings(view, SHIPPED_MAPS) == ()


def test_the_what_changed_block_is_cp8s() -> None:
    spec = _spec_of("what-changed")
    assert (spec.owner, spec.kind, spec.producers) == ("CP-8", "prose", ("CP-8",))
    assert spec.title == "What changed since the last Report"
    assert spec.collapsed is False  # the oracle pins the as-is state (lease question 5)


def _what_changed_view(case: str, edit: dict[str, str] | None = None) -> View:
    """The oracle's CP-8 module as an accepted view; ``edit`` swaps fact texts by fact id."""
    module = _head_module(case)
    facts = tuple(
        f.model_copy(update={"text": edit[f.fact_id]}) if edit and f.fact_id in edit else f
        for f in module.facts
    )
    facts = tuple(  # a figure needs a calculation behind it (the oracle's own id)
        f.model_copy(update={"calculation_id": f"calc:{f.fact_id}"})
        if f.fact_id == "T7.3.window.realized_value"
        else f
        for f in facts
    )
    return View(
        run=_run(case),
        mode="accepted",
        modules=(
            ModuleView(
                module_id="CP-8",
                title="CP-8",
                aliases=(),
                status="restricted",
                artifact_sha256="b" * 64,
                facts=facts,
                limitations=module.limitations,
            ),
        ),
    )


def _what_changed_lines(view: View) -> list[list[tuple[str, str, str | None]]]:
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    block = next(
        b for b in build(view, pathway, SHIPPED_MAPS).blocks if b.block_id == "what-changed"
    )
    return [[(r.kind, r.text, r.ref_id) for r in line.runs] for line in block.lines]


def test_the_outcome_cell_shows_the_gap_the_page_gives_the_window_figure() -> None:
    view = _what_changed_view("no_outcome")
    _, index = build_index(view)
    gap = gap_refs(index)[("CP-8", "T7.3.window.realized_value")]
    lines = _what_changed_lines(view)
    line = next(r for r in lines if r[0][1].startswith("No realized outcome is recorded"))
    assert line == [
        ("text", "No realized outcome is recorded, so the window since the decision ", None),
        ("gap", f"\u2205 {gap}", gap),
        ("text", " and every variance are missing.", None),
    ]
    assert not any("[T7.3" in run[1] for r in lines for run in r)


def test_a_known_window_figure_renders_as_the_figure_and_a_positive_line_is_unchanged() -> None:
    plain = _what_changed_lines(_what_changed_view("positive"))
    leverage = next(r for r in plain if r[0][1].startswith("Total leverage was recorded"))
    assert leverage[0] == ("text", leverage[0][1], None) and "[" not in leverage[0][1]
    token = "Window {T7.3.window.realized_value|days} after the decision."
    lines = _what_changed_lines(
        _what_changed_view("positive", {"cp8.what_changed.attribution.value": token})
    )
    line = next(r for r in lines if r[0][1] == "Window ")
    shown = next(
        f["shown"]
        for t in EXPECTED["cases"]["positive"]["tables"]
        for row in t["rows"]
        for f in row["facts"]
        if f["fact_id"] == "T7.3.window.realized_value"
    )
    assert shown == "109 days"
    assert line[1][:2] == ("fig", shown)
    assert line[-1][1] == " after the decision." and not any(run[0] == "gap" for run in line)


def _payload_facts(view: View) -> dict[str, dict[str, Any]]:
    from deploy_vii import render as core_render

    page = core_render.render(view)
    found = re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', page, flags=re.DOTALL)
    assert found
    return {f["fact_id"]: f for f in json.loads(found.group(1))["modules"][0]["facts"]}


def test_the_module_table_and_inspector_spell_the_outcome_as_the_block_does() -> None:
    view = _what_changed_view("no_outcome")
    _, index = build_index(view)
    gap = gap_refs(index)[("CP-8", "T7.3.window.realized_value")]
    fact = _payload_facts(view)["cp8.what_changed.outcome.value"]
    block = "".join(
        run[1]
        for line in _what_changed_lines(view)
        if line[0][1].startswith("No realized outcome is recorded")
        for run in line
    )
    for field in ("display", "table_display"):
        assert "[" not in fact[field] and "]" not in fact[field]
        assert fact[field] == block and f"\u2205 {gap}" in fact[field]


def test_a_known_window_figure_is_spelled_in_the_module_table_as_the_block_does() -> None:
    token = "Window {T7.3.window.realized_value|days} after the decision."
    view = _what_changed_view("positive", {"cp8.what_changed.attribution.value": token})
    fact = _payload_facts(view)["cp8.what_changed.attribution.value"]
    assert fact["display"] == fact["table_display"] == "Window 109 days after the decision."


def test_a_well_formed_token_beside_a_non_token_bracket_fails_closed() -> None:
    text = "Window {T7.3.window.realized_value|days} then [Not a token]."
    view = _what_changed_view("positive", {"cp8.what_changed.attribution.value": text})
    with pytest.raises(ValueError, match="does not resolve"):
        _what_changed_lines(view)


def test_a_token_naming_a_fact_outside_the_module_fails_closed() -> None:
    view = _what_changed_view(
        "no_outcome", {"cp8.what_changed.outcome.value": "Outside [T9.9.nope.value] here."}
    )
    with pytest.raises(ValueError, match="does not resolve"):
        _what_changed_lines(view)


# --- the reader (D3 is OPEN: pin what it exposes, claim nothing) -------------------------------------


def _head_module(case: str) -> Module:
    facts = []
    for table in EXPECTED["cases"][case]["tables"]:
        for row in table["rows"]:
            for item in row["facts"]:
                facts.append(
                    Fact.model_validate(
                        {
                            "fact_id": item["fact_id"],
                            "label": item["column"],
                            "table_id": table["table_id"],
                            "row_id": row["row_id"],
                            "field": item["fact_id"].rsplit(".", 1)[1],
                            "amount": None if item["amount"] is None else Decimal(item["amount"]),
                            "text": item["text"],
                            "status": item["status"],
                            "unit": item["unit"],
                            "period": item["period"],
                            "limitation": item["limitation"],
                        }
                    )
                )
    base = _module("CP-8", tuple(facts), case)
    return base.model_copy(
        update={
            "status": "restricted",
            "limitations": tuple(EXPECTED["cases"][case]["own_limitations"]),
        }
    )


def _read(case: str) -> cp8.Cp8Head:
    module = _head_module(case)
    head = Head(
        module_id="CP-8", status="restricted", result_sha256=module.content_hash(), inputs=()
    )
    store = SimpleNamespace(head_module=lambda h: module)
    return cp8.cp8_reader(cast(Any, store), head)


def test_reader_exposes_the_pinned_values_on_the_positive_case() -> None:
    pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
    got = _read("positive")
    assert got.head_sha256 == _head_module("positive").content_hash()
    assert got.status == "restricted"
    assert (got.overall_label, got.overall_process_sound) == (
        pinned["overall"],
        pinned["process_sound"],
    )
    assert got.window_days == Decimal(pinned["window_days"])
    assert got.hit_rate == Decimal(pinned["hit_rate"]) and got.hit_rate_absence is None
    assert dict(got.directions) == pinned["directions"]
    assert dict(got.magnitudes) == {
        "total_leverage": Decimal("0.13"),
        "interest_cover": Decimal("0.50"),
        "loan_mid": Decimal(50),
    }
    assert (got.decisions_recorded, got.decisions_required) == (1, 3)
    assert got.limitations == tuple(EXPECTED["cases"]["positive"]["own_limitations"])


def test_reader_reads_missing_as_none_never_zero() -> None:
    got = _read("no_outcome")
    assert got.window_days is None and got.hit_rate is None
    assert got.hit_rate_absence is not None and got.hit_rate_absence.startswith("Not calculable")
    assert set(got.directions.values()) == {None} and set(got.magnitudes.values()) == {None}
    assert (got.overall_label, got.overall_process_sound) == (
        "Insufficient Information",
        "Not assessed",
    )


def test_reader_refuses_another_modules_head() -> None:
    head = Head(module_id="CP-0", status="accepted", result_sha256="c" * 64, inputs=())
    with pytest.raises(ValueError, match="not a CP-8 head"):
        cp8.cp8_reader(cast(Any, SimpleNamespace()), head)


@pytest.mark.parametrize(
    "path",
    [
        ("decision", "posture"),
        ("decision", "size"),
        ("thesis", "exit_trigger"),
        ("thesis", "expected_spread_return"),
        ("thesis", "expected_rating_path"),
        ("thesis", "expected_hold"),
        ("outcome_absence",),
    ],
    ids=".".join,
)
def test_rules_each_absence_site_alone_needs_a_search(path: tuple[str, ...]) -> None:
    payload = copy.deepcopy(POSITIVE)
    cited = {"quote": payload["thesis"]["thesis"]["quote"]}
    for name in ("posture", "size"):
        payload["decision"][name] = {"text": "x", "quote": cited["quote"]}
    for name in ("exit_trigger", "expected_spread_return", "expected_rating_path", "expected_hold"):
        payload["thesis"][name] = cited
    payload["outcome_absence"] = None
    read = EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"]
    assert cp8.RULES(json.dumps(payload), _seen(read, False)) == ()
    node: Any = payload
    for part in path[:-1]:
        node = node[part]
    absence = {"reason": "r", "follow_up": "f"}
    node[path[-1]] = absence if path == ("outcome_absence",) else {"absence": absence}
    assert cp8.RULES(json.dumps(payload), _seen(read, False)) == (UNBACKED_ABSENCE,)
    assert cp8.RULES(json.dumps(payload), _seen(read, True)) == ()


# --- model text and citations (Stage 2 round 3 rulings that bind every module) ------------------------

HOSTILE_TEXT = (
    "{",
    "}",
    "[",
    "]",
    "a {b|c} d",
    "see [T7.1.d01.action_bias]",
    "{T7.1.d01.action_bias|MULTIPLE}",
    "tab\there",
    "nul\x00here",
    "line\nbreak",
    "\u202ertl",
    "x" * 20000,
    "² squared",
    "Ⅻ numeral",
    "￾",
)


def _text_paths(node: Any, path: str = "") -> Iterator[str]:
    """The JSON path of every analyst-text string of a submission (not a quote object field and
    not a vocabulary or id field)."""
    names = {"basis", "lesson", "gap", "missing_item", "why_it_matters", "impact_on_output"}
    names |= {"follow_up", "reason", "text"}
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}" if path else key
            if key in names and isinstance(value, str) and not path.startswith("decision."):
                yield here
            else:
                yield from _text_paths(value, here)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _text_paths(value, f"{path}[{i}]")


TEXT_SITES = [p for p in _text_paths(POSITIVE) if not p.startswith("decision.")]


def _set(document: Any, path: str, value: str) -> None:
    parts = re.findall(r"[^.\[\]]+", path)
    for part in parts[:-1]:
        document = document[int(part)] if part.isdigit() else document[part]
    document[parts[-1]] = value


def test_text_sites_are_inventoried() -> None:
    assert "synthesis.text" in TEXT_SITES
    assert any(s.startswith("attributions[") and s.endswith(".basis") for s in TEXT_SITES)
    assert any(s.startswith("lessons[") for s in TEXT_SITES)
    assert any(s.endswith(".absence.reason") or s == "outcome_absence.reason" for s in TEXT_SITES)


@pytest.mark.parametrize("value", HOSTILE_TEXT, ids=lambda v: repr(v[:12]))
@pytest.mark.parametrize("site", TEXT_SITES)
def test_hostile_model_text_is_an_issue_or_composes_never_raises(site: str, value: str) -> None:
    """Nothing raises after the binding write: a text the step's RunText would refuse is a
    validator issue; one the validator admits composes into a Module."""
    payload = copy.deepcopy(POSITIVE)
    _set(payload, site, value)
    submission = DecisionLedgerSubmission.model_validate_json(json.dumps(payload))
    found = validate_ledger(submission=submission, upstream=_upstream(), pack=_pack())
    if not found:
        report = cp8.decision_ledger(pack=_pack(), submission=submission, upstream=_upstream())
        Module(
            run_id="r",
            issuer_id="i",
            as_of=date(2026, 4, 30),
            module_id="CP-8",
            facts=report.facts,
            tables=report.tables,
            claims=report.claims,
        )


def _positive_report() -> Any:
    from test_method_cp8 import report_of

    return report_of("positive")


def _all_quotes() -> set[tuple[str, str, str]]:
    return {
        (
            _at(POSITIVE, site)["source_id"],
            _at(POSITIVE, site)["locator"],
            _at(POSITIVE, site)["quote"],
        )
        for site in SITES
    }


def test_a_fact_carries_one_citation_per_page_and_never_invents_a_quote() -> None:
    quotes = _all_quotes()
    for fact in _positive_report().facts:
        pages = [(c.source_id, c.locator) for c in fact.citations]
        assert len(pages) == len(set(pages)), fact.fact_id
        for c in fact.citations:
            assert (c.source_id, c.locator, c.quote) in quotes, fact.fact_id


def test_a_derived_fact_quotes_the_first_of_its_input_quotes_on_each_page() -> None:
    facts = {f.fact_id: f for f in _positive_report().facts}
    thesis = POSITIVE["thesis"]
    evidence = {(c.source_id, c.locator): c.quote for c in facts["T7.2.t01.evidence_id"].citations}
    assert evidence == {
        ("prior_case", "page:1"): thesis["thesis"]["quote"]["quote"],
        ("prior_case", "page:2"): thesis["downside_paths"]["quote"]["quote"],
    }
    observed = {(o["side"], o["metric"]): o["quote"]["quote"] for o in POSITIVE["observations"]}
    window = {
        (c.source_id, c.locator): c.quote for c in facts["T7.3.window.realized_value"].citations
    }
    assert window == {
        ("prior_case", "page:1"): POSITIVE["decision"]["decision_date"]["quote"]["quote"],
        ("update", "page:1"): observed[("realized", "total_leverage")],
        ("market_update", "page:1"): observed[("realized", "loan_bid")],
    }
    as_of = {(c.source_id, c.locator): c.quote for c in facts["T7.3.window.as_of"].citations}
    assert as_of == {k: v for k, v in window.items() if k[0] != "prior_case"}


def test_a_sourced_fact_quotes_its_own_field() -> None:
    facts = {f.fact_id: f for f in _positive_report().facts}
    own = POSITIVE["decision"]["decision_date"]["quote"]
    (cite,) = facts["T7.1.d01.decision_date"].citations
    assert (cite.source_id, cite.locator, cite.quote) == (
        own["source_id"],
        own["locator"],
        own["quote"],
    )


# --- fix round 1 (review.md L1): pins for the mutants the first pass left alive -------------------


def _store_of(module: Module) -> Any:
    return SimpleNamespace(head_module=lambda head: module)


def test_reader_refuses_a_head_without_a_whole_count() -> None:
    """R2: a missing or fractional count is never read as 0."""
    for amount, status in ((None, "missing"), (Decimal("1.5"), "known")):
        module = _head_module("positive")
        facts = tuple(
            f.model_copy(
                update={
                    "amount": amount,
                    "status": status,
                    "limitation": None if status == "known" else "Not calculable",
                }
            )
            if f.fact_id == "T7.6.gate.decisions_recorded"
            else f
            for f in module.facts
        )
        head = Head(
            module_id="CP-8", status="restricted", result_sha256=module.content_hash(), inputs=()
        )
        store = _store_of(module.model_copy(update={"facts": facts}))
        with pytest.raises(ValueError, match="no whole count"):
            cp8.cp8_reader(cast(Any, store), head)


def test_reader_refuses_a_head_without_an_overall_attribution() -> None:
    """R3: the overall label and process are stated cells."""
    for fact_id in ("T7.5.overall.label", "T7.5.overall.process_sound"):
        module = _head_module("positive")
        facts = tuple(
            f.model_copy(update={"text": None, "status": "missing", "limitation": "gap"})
            if f.fact_id == fact_id
            else f
            for f in module.facts
        )
        head = Head(
            module_id="CP-8", status="restricted", result_sha256=module.content_hash(), inputs=()
        )
        store = _store_of(module.model_copy(update={"facts": facts}))
        with pytest.raises(ValueError, match="no overall attribution"):
            cp8.cp8_reader(cast(Any, store), head)


@pytest.mark.parametrize("status", ["accepted", "restricted", "stale"])
def test_reader_passes_the_heads_status_through(
    status: Literal["accepted", "restricted", "stale"],
) -> None:
    """R4: the status is the head's (a stale head reads stale)."""
    module = _head_module("positive")
    head = Head(
        module_id="CP-8",
        status=status,
        result_sha256=module.content_hash(),
        inputs=(),
    )
    got = cp8.cp8_reader(cast(Any, SimpleNamespace(head_module=lambda h: module)), head)
    assert got.status == status


def _only_absence_at(site: tuple[str, ...]) -> dict[str, Any]:
    """The positive payload with every absence replaced by a cited field and one absence at
    ``site`` (any field, including a required one)."""
    payload: dict[str, Any] = copy.deepcopy(POSITIVE)
    cited = {"quote": payload["thesis"]["thesis"]["quote"]}
    for name in ("posture", "size"):
        payload["decision"][name] = {"text": "x", "quote": cited["quote"]}
    for name in ("exit_trigger", "expected_spread_return", "expected_rating_path", "expected_hold"):
        payload["thesis"][name] = cited
    payload["outcome_absence"] = None
    node: Any = payload
    for part in site[:-1]:
        node = node[part]
    node[site[-1]] = {"absence": {"reason": "r", "follow_up": "f"}}
    return payload


@pytest.mark.parametrize(
    "site",
    [
        ("decision", "action_bias"),
        ("decision", "confidence"),
        ("decision", "instrument"),
        ("decision", "decision_date"),
        ("decision", "decision_maker_role"),
        ("thesis", "thesis"),
        ("thesis", "greatest_uncertainty"),
        ("thesis", "downside_paths"),
    ],
    ids=".".join,
)
def test_rules_count_an_absence_only_on_the_optional_fields(site: tuple[str, ...]) -> None:
    """U1/U2: a required field claiming absence is the validator's refusal, not a search rule."""
    read = EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"]
    got = cp8.RULES(json.dumps(_only_absence_at(site)), _seen(read, False))
    assert got == ()


@pytest.mark.parametrize(
    ("source_id", "locator", "expected"),
    [
        (
            "identity",
            "page:1",
            "decision.action_bias.quote: source identity is outside the CP-8 scope",
        ),
        ("board_minutes", "page:1", "Unavailable or changed source: board_minutes"),
        ("update", "page:1", "decision.action_bias.quote: must cite prior_case"),
    ],
)
def test_a_blank_quote_is_judged_after_the_pack_scope_and_source_rule(
    source_id: str, locator: str, expected: str
) -> None:
    """B1/B2: the blank check sits after the pack, scope and must-cite checks."""
    payload = copy.deepcopy(POSITIVE)
    payload["decision"]["action_bias"]["quote"] = {
        "source_id": source_id,
        "locator": locator,
        "quote": "   ",
    }
    found = _issues(payload)
    assert found == (expected,)


def test_a_blank_quote_is_judged_after_the_realized_source_rule() -> None:
    payload = copy.deepcopy(POSITIVE)
    realized = next(o for o in payload["observations"] if o["side"] == "realized")
    realized["quote"] = {"source_id": "prior_case", "locator": "page:1", "quote": "   "}
    found = _issues(payload)
    assert [i for i in found if "empty text" in i] == []
    assert any("cannot cite prior_case" in i for i in found)


def test_a_payload_that_is_not_an_object_is_one_shape_issue() -> None:
    """P1: ``_parse`` gives ``NOT_AN_OBJECT`` for text ``json_object`` refuses."""
    for text in ("[]", "null", "not json", "NaN", '{"a": NaN}', "[" * 1000):
        assert cp8._parse(text) == (cp8.NOT_AN_OBJECT,), text
    parsed = cp8._parse(json.dumps(POSITIVE))
    assert isinstance(parsed, DecisionLedgerSubmission)
    shape = cp8._parse(json.dumps({"decision": POSITIVE["decision"]}))
    assert isinstance(shape, tuple) and shape != (cp8.NOT_AN_OBJECT,)


def test_the_entry_validator_turns_a_non_object_payload_into_an_issue() -> None:
    step = SimpleNamespace(payload_sha256="p")
    store = SimpleNamespace(payload=lambda sha: "[]")
    outcome = cp8._validate_step(
        cast(Any, store), cast(Any, None), cast(Any, SimpleNamespace(steps=(step,)))
    )
    assert outcome.issues == (cp8.NOT_AN_OBJECT,) and outcome.output is None


# --- fix round 1: submit and the settled head, through the store (about a second each) ---------------


def test_the_reader_returns_the_own_limitations_settle_wrote(tmp_path: Path) -> None:
    """M1/R1: a head built by ``settle``; for a synthetic run the own list ends with the
    synthetic line, which the oracle's own list does not hold."""
    import cp8_runs as runs

    runs.cp8_closed("positive", tmp_path)
    store = Execution(tmp_path / "store")
    head = next(h for h in store.read().heads if h.module_id == "CP-8")
    module = store.head_module(head)
    oracle = EXPECTED["cases"]["positive"]
    synthetic = "Synthetic case; not real issuer qualification"
    want = (*oracle["own_limitations"], synthetic)
    assert module.limitations == want
    assert synthetic not in module.inherited_limitations
    assert cp8.cp8_reader(store, head).limitations == want


def test_submit_journals_validator_then_rules_issues_without_deduplicating(tmp_path: Path) -> None:
    """S1: r42 is journaled twice (rules wrap only when RULES adds an issue)."""
    import cp8_runs as runs

    workflow, _ = runs.start("positive", tmp_path)
    entry = next(e for e in SUBMISSIONS["refusal_mutations"]["entries"] if e["id"] == "r42")
    read = EXPECTED["cases"]["positive"]["tool_use_required"]["read_pages_cover"]
    outcome = runs.submit(workflow, json.dumps(entry["literal"]), read=read)
    assert outcome["issues"] == entry["issues"] and len(entry["issues"]) == 2


def test_submit_revalidates_the_retained_step_before_it_settles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S2: a trusted re-validation that differs from the retained output is refused."""
    import cp8_runs as runs
    import s1a_runs as base

    workflow, pack = runs.start("positive", tmp_path)
    real = cp8._validate_step
    calls: list[int] = []

    def drifting(store: Any, pk: Any, attempt: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            return real(store, pk, attempt)
        return StepValidation(output="{}")

    monkeypatch.setattr(cp8, "_validate_step", drifting)
    payload = runs.literal("positive", "submission", pack)
    base.read_cited(workflow, payload)
    base.search(workflow, "prior_case", runs.SEARCH_QUERY)
    with pytest.raises(ValueError, match="differs from trusted validation"):
        workflow.submit_review(payload)


# --- run-text tables: only a registered table's text is run text (rulings item 56) ----------------


def _thesis_fact_id(view: View) -> str:
    return next(
        f.fact_id
        for f in view.modules[0].facts
        if f.table_id == "T7.2" and f.status == "known" and f.text
    )


def test_a_verbatim_quote_holding_brackets_is_shown_as_written_in_block_and_payload() -> None:
    quote = "Section 7.11 [Reserved]; see [sic] and [1]."
    fact_id = _thesis_fact_id(_what_changed_view("positive"))
    view = _what_changed_view("positive", {fact_id: quote})
    fact = _payload_facts(view)[fact_id]
    assert fact["display"] == fact["table_display"] == quote
    assert _what_changed_lines(view)  # the block renders too


@pytest.mark.parametrize(
    "bad",
    [
        "No realized outcome is recorded [T7.3.window.realized_valu].",
        "No realized outcome is recorded [T7.3.window.realized_value",
    ],
)
def test_malformed_run_text_in_the_what_changed_table_fails_closed_on_both_paths(bad: str) -> None:
    view = _what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": bad})
    for step in (_what_changed_lines, _payload_facts):
        with pytest.raises(ValueError, match="does not resolve"):
            step(view)


def test_run_text_naming_an_issuer_with_digits_renders_on_both_paths() -> None:
    text = (
        "No realized outcome is recorded for 3M Company, "
        "so the window [T7.3.window.realized_value] is missing."
    )
    view = _what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": text})
    run = view.run.model_copy(update={"issuer_name": "3M Company"})
    view = view.model_copy(update={"run": run})
    assert _what_changed_lines(view)
    assert "3M Company" in _payload_facts(view)["cp8.what_changed.outcome.value"]["display"]
