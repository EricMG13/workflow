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
from typing import Any, cast

import pytest
from defect_classes import BLANK_VALUES
from test_method_cp8 import upstream as stage1_upstream

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.cp8 import CP8
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Input, Module, ModuleView, Run, View
from deploy_vii.cp6_committee import ACTION_BIAS_FACT, CONFIDENCE_FACT
from deploy_vii.execution import Attempt, Head, Qualification
from deploy_vii.live.tools import UNBACKED_ABSENCE, Seen
from deploy_vii.registry import plan, step_chain
from deploy_vii.report_view import _spec_of
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
    assert SHIPPED_MAPS[-1] is CP8
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
