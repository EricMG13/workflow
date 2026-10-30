"""CP-L10 Stage 2: the plug-in parts, the store adapter, the registrations, the rails bindings and
the D3 reader (`docs/CPL10-OWNER-LEASE.md` Public API, D3 and D7; `docs/G1X-OWNER-CORE-PROTOCOL.md`).

Expectations come from the frozen oracle (`cases/cpl10-owner`) and the lease, never from the code
under test. The upstream heads are hand-made CP-0 and CP-1 modules settled through the real
`Execution` journal (the frozen CP-1 oracle facts, with citations that hold in the financial pack),
so `submit`, `probe` and the step replay run on the product's own store. No CP-1 promotion, no
`OwnerWorkflow` run: those are the deferred store runs (`tests/test_owner_cpl10.py`).
"""

import hashlib
import importlib
import json
import shutil
from collections.abc import Iterator
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from test_connect_cp8 import _payload_facts, _what_changed_view
from test_method_cpl10 import (
    EXPECTED,
    MANIFEST,
    SUBMISSIONS,
    UPSTREAM,
    _cp1_facts,
)
from test_method_cpl10 import _payload as _stage1_payload

from deploy_vii import registry, report_view
from deploy_vii.bindings import RAIL_DESTINATIONS, validate_bindings
from deploy_vii.bindings.cpl10 import CPL10
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Citation, Fact, Input, Module, ModuleView, Run, View
from deploy_vii.execution import Attempt, Execution, Head, StepValidation, current_inputs
from deploy_vii.live.schema import normalise
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host, owner_workflow
from deploy_workflow.owners import cpl10
from deploy_workflow.workflow import WorkflowError

financial: Any = importlib.import_module("test_financial_workflow")
STEP = "change_screen"
RUN = Run.model_validate_json(json.dumps(MANIFEST["run"]))
POSITIVE: dict[str, Any] = EXPECTED["cases"]["positive"]
CP0_LIMIT = "CP-0 head limitation of the synthetic upstream"
CP1_LIMIT = "CP-1 head limitation of the synthetic upstream"
BOUND_SHAPE = "(root): not a JSON object within the payload bounds"


# --- a store with settled CP-0 and CP-1 heads ------------------------------------------------


def _pack() -> PreparedPack:
    return PreparedPack(run=RUN, sources=financial.make_pack().sources)


def _cp1_with_real_citations(pack: PreparedPack) -> list[Fact]:
    financial = next(s for s in pack.sources if s.source_id == "financial")
    span = financial.spans[1]
    quote = span.text.strip().splitlines()[0]
    assert financial.sha256 is not None
    cite = Citation(
        source_id="financial", source_sha256=financial.sha256, locator=span.locator, quote=quote
    )
    return [
        f.model_copy(update={"citations": (cite,), "amount": _padded(f.amount)})
        for f in _cp1_facts()
    ]


def _padded(amount: Decimal | None) -> Decimal | None:
    """A genuine CP-1 stores `17.50` where the oracle spells `17.5` (M1): pad to two places
    whenever that is lossless, so the view must write the canonical text, not the stored one."""
    if amount is None:
        return None
    padded = amount.quantize(Decimal("0.01"))
    return padded if padded == amount else amount


def _settle(store: Execution, module_id: str, facts: list[Fact], limitation: str | None) -> None:
    attempt = store.begin(module_id)
    run = store.read().run
    candidate = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=attempt.inputs,
        facts=tuple(facts),
        limitations=() if limitation is None else (limitation,),
        attempt=attempt.number,
    )
    store.finish(
        attempt.ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("differs",),
    )


def _t8(consumer: str) -> Fact:
    return Fact(
        fact_id=f"T8.{consumer}.exact_command",
        label=f"Command for {consumer}",
        table_id="T8",
        row_id=consumer,
        field="exact_command",
        text=f"Run {consumer}",
    )


@pytest.fixture(scope="module")
def settled(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    root = tmp_path_factory.mktemp("cpl10-connect")
    pack = _pack()
    store = Execution.create(root / "store", pack)
    _settle(store, "CP-0", [_t8("CP-1"), _t8("CP-L10")], CP0_LIMIT)
    _settle(store, "CP-1", _cp1_with_real_citations(pack), CP1_LIMIT)
    yield root / "store"


@pytest.fixture(scope="module")
def varied(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A public run of another issuer and as_of, CP-0 restricted and CP-1 accepted, so no
    constant equal to the oracle's run or statuses can pass (L1)."""
    root = tmp_path_factory.mktemp("cpl10-varied")
    run = RUN.model_copy(
        update={
            "case_kind": "public",
            "issuer_name": "Other Issuer plc",
            "as_of": date(2027, 3, 31),
        }
    )
    pack = PreparedPack(run=run, sources=financial.make_pack().sources)
    store = Execution.create(root / "store", pack)
    _settle(store, "CP-0", [_t8("CP-1"), _t8("CP-L10")], CP0_LIMIT)
    _settle(store, "CP-1", _cp1_with_real_citations(pack), None)
    yield root / "store"


@pytest.fixture(scope="module")
def mixed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A public (not synthetic) run: CP-0 settles accepted (no limitation, no synthetic note) and
    CP-1 restricted, so the two status words differ."""
    root = tmp_path_factory.mktemp("cpl10-mixed")
    pack = PreparedPack(
        run=RUN.model_copy(update={"case_kind": "public"}), sources=financial.make_pack().sources
    )
    store = Execution.create(root / "store", pack)
    _settle(store, "CP-0", [_t8("CP-1"), _t8("CP-L10")], None)
    _settle(store, "CP-1", _cp1_with_real_citations(pack), CP1_LIMIT)
    yield root / "store"


def _fork(settled: Path, tmp_path: Path) -> Execution:
    shutil.copytree(settled, tmp_path / "store")
    return Execution(tmp_path / "store")


def _positive() -> str:
    return json.dumps(SUBMISSIONS["positive"])


def _heads(store: Execution) -> dict[str, Head]:
    return {h.module_id: h for h in store.read().heads}


def _unbegun(settled: Path) -> Attempt:
    """An attempt bound as `Execution.begin` binds it, without touching the shared store."""
    return Attempt(
        ticket_id="adapter-ticket",
        module_id="CP-L10",
        inputs=current_inputs(Execution(settled).read(), "CP-L10"),
        number=0,
    )


def _without(attempt: Attempt, input_id: str) -> Attempt:
    return attempt.model_copy(
        update={"inputs": tuple(i for i in attempt.inputs if i.input_id != input_id)}
    )


def _submit(store: Execution, payload: str) -> tuple[Attempt, Any]:
    ticket = store.begin("CP-L10")
    return ticket, cpl10.submit(store, ticket.ticket_id, STEP, payload, None)


# --- parts: ids, schemas, registration rows ---------------------------------------------------


def test_step_ids_are_a_tuple_of_str_and_schemas_cover_them() -> None:
    assert cpl10.STEP_IDS == (STEP,)
    assert type(cpl10.STEP_IDS) is tuple and all(type(i) is str for i in cpl10.STEP_IDS)
    assert set(cpl10.SCHEMAS) == set(cpl10.STEP_IDS)
    assert cpl10.SCHEMAS[STEP] is cpl10.ChangeScreenSubmission
    with pytest.raises(ValueError, match="no live step contract"):
        registry.step_chain("CP-L10")


@pytest.mark.parametrize("name", ["positive", "limited"])
def test_schema_round_trips_and_gives_the_tail_digest(name: str) -> None:
    text = json.dumps(SUBMISSIONS[name])
    parsed = cpl10.SCHEMAS[STEP].model_validate_json(text)
    again = cpl10.SCHEMAS[STEP].model_validate_json(parsed.model_dump_json())
    assert again == parsed and again.content_hash() == parsed.content_hash()
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()
    assert normalise(cpl10.SCHEMAS[STEP], text) == (text, ())  # nothing to resolve: kept as sent


def test_registration_rows_equal_the_lease() -> None:
    spec = owner_workflow.OWNER_SPECS["CP-L10"]
    assert spec.module_id == "CP-L10" and spec.entry == "owner_core"
    assert spec.kind == "analytical" and spec.publish is None
    (step,) = spec.steps
    assert (step.step_id, step.schema) == (STEP, cpl10.ChangeScreenSubmission)
    assert (step.sources, step.extract, step.upstream_grant) == (False, False, None)
    assert (step.inputs, step.rules) == ("module_context", "none")
    assert "CP-L10" in owner_workflow.SUPPORTED_ANALYTICAL
    assert owner_workflow._CORES["CP-L10"] is cpl10
    assert owner_workflow._QUALIFICATION["CP-L10"] == cpl10.QUALIFICATION
    assert cpl10.QUALIFICATION.implementation == "implemented"
    assert owner_workflow._PROBES["CP-L10"] is cpl10.probe
    assert owner_workflow._VIEWS[STEP] is cpl10.view
    assert owner_workflow._ENTRY_VALIDATORS["CP-L10"] is cpl10.ENTRY_VALIDATOR
    # lease: no precheck ("every content rule is a journaled validator issue"), no pack sources
    assert "CP-L10" not in owner_workflow._PRECHECKS
    assert ("CP-L10", STEP) not in host._OWNER_SCOPES


def test_check_steps_accepts_the_registered_spec() -> None:
    owner_workflow._check_steps("CP-L10", owner_workflow.OWNER_SPECS["CP-L10"])


def test_registrations_are_appended_after_the_existing_rows() -> None:
    specs = list(owner_workflow.OWNER_SPECS)
    assert specs.index("CP-L10") > specs.index("CP-MODEL")
    for rows in (
        owner_workflow._CORES,
        owner_workflow._QUALIFICATION,
        owner_workflow._PROBES,
        owner_workflow._ENTRY_VALIDATORS,
    ):
        assert "CP-L10" in rows
    assert STEP in owner_workflow._VIEWS
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert CPL10 in SHIPPED_MAPS
    assert ids.index("CP-L10") > ids.index("CP-6")


# --- backlog: -0 / exponent form of the exact change -----------------------------------------


@pytest.mark.parametrize(
    ("start", "close", "text"),
    [
        ("0", "-0", "0"),
        ("-0", "0", "0"),
        ("1E+2", "1E+2", "0"),
        ("0.00", "0.000", "0"),
        ("1E+3", "2E+3", "1000"),
        ("0", "1E+5", "100000"),
        ("5E+1", "0", "-50"),
        ("20", "20.5", "0.5"),
    ],
)
def test_the_exact_change_is_stored_in_plain_form(start: str, close: str, text: str) -> None:
    change = cpl10.screen_topic(start=Decimal(start), close=Decimal(close)).change
    assert change is not None and str(change) == text


# --- protocol section 6: model text is parsed only through the bounded parse --------------------------


def test_payload_beyond_the_bounded_parse_fails_closed_as_a_shape_issue() -> None:
    deep = "[" * 70 + "]" * 70
    for text in (deep, "[1]", '"text"', '{"comparison": NaN}', '{"a": "\\ud800"}', "{"):
        assert cpl10._parse(text) == (BOUND_SHAPE,), text
    assert cpl10._parse(b"\xff\xfe") == (BOUND_SHAPE,)
    assert cpl10.validate_screen(submission=deep, upstream=UPSTREAM) == (BOUND_SHAPE,)


def test_parse_accepts_text_bytes_and_mapping_alike() -> None:
    want = cpl10.SCHEMAS[STEP].model_validate_json(_positive())
    assert cpl10._parse(_positive()) == want
    assert cpl10._parse(_positive().encode()) == want
    assert cpl10._parse(SUBMISSIONS["positive"]) == want


def test_a_wrongly_shaped_object_keeps_the_pydantic_shape_issues() -> None:
    sub = json.loads(_positive())
    del sub["comparison"]["from_period"]
    assert cpl10._parse(json.dumps(sub)) == ("comparison.from_period: Field required",)


# --- the store adapter -----------------------------------------------------------------------


def test_adapter_returns_the_stage_one_upstream(settled: Path) -> None:
    store = Execution(settled)
    heads = _heads(store)
    got = cpl10.cpl10_upstream(store, _unbegun(settled))
    want = replace(
        UPSTREAM,
        cp0_status_word="With limitations",
        cp0_result_sha256=heads["CP-0"].result_sha256,
        cp1_status_word="With limitations",
        cp1_result_sha256=heads["CP-1"].result_sha256,
        cp1_facts=cpl10.bind_operands(store.head_module(heads["CP-1"]).facts),
        inherited_limitations=(CP0_LIMIT, CP1_LIMIT),
    )
    assert got == want
    assert (got.issuer_name, got.as_of) == (RUN.issuer_name, RUN.as_of)
    assert [f.name for f in fields(got)] == [
        "issuer_name",
        "as_of",
        "cp0_status_word",
        "cp0_result_sha256",
        "cp1_status_word",
        "cp1_result_sha256",
        "cp1_facts",
        "inherited_limitations",
    ]


@pytest.mark.parametrize("missing", ["CP-0", "CP-1"])
def test_adapter_refuses_a_missing_upstream_input(settled: Path, missing: str) -> None:
    with pytest.raises(ValueError, match=f"binds no {missing} input"):
        cpl10.cpl10_upstream(Execution(settled), _without(_unbegun(settled), missing))


# --- the exact read_inputs view --------------------------------------------------------------


def test_view_is_the_oracle_tree(settled: Path) -> None:
    store = Execution(settled)
    digest, body = cpl10.view(store, _unbegun(settled))
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert list(tree) == EXPECTED["execution"]["view_keys"]
    assert tree["upstream"] == [
        {"module_id": "CP-0", "status": "With limitations"},
        {"module_id": "CP-1", "status": "With limitations"},
    ]
    assert tree["periods"] == [{"period": q.period, "column": q.column} for q in cpl10.QUARTERS]
    assert tree["topics"] == POSITIVE["view_topics"]
    assert tree["pair_screens"] == POSITIVE["view_pair_screens"]
    assert tree["inherited_limitations"] == [CP0_LIMIT, CP1_LIMIT]
    assert isinstance(tree["rules"], str) and "Material" in tree["rules"]
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    # no quote, citation or record in the view (lease D2)
    cp1 = store.head_module(_heads(store)["CP-1"])
    assert '"quote"' not in body and "record_json" not in body and "citation" not in body
    assert all(c.quote not in body for f in cp1.facts for c in f.citations)
    assert all(fact.fact_id not in body for fact in cp1.facts)


def test_view_refuses_an_unbound_upstream(settled: Path) -> None:
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpl10.view(Execution(settled), _without(_unbegun(settled), "CP-1"))


# --- submit, the step replay, settlement ------------------------------------------------------


def test_submit_settles_the_positive_screen(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    ticket, submitted = _submit(store, _positive())
    assert submitted.payload == _positive() and submitted.nulls_resolved == ()
    assert (submitted.prefilled, submitted.prefilled_kinds) == ((), ())
    assert submitted.composition is None
    assert submitted.journal.status == "finished" and submitted.journal.issues == ()
    heads = _heads(store)
    head = heads["CP-L10"]
    assert head.status == "restricted" and head.qualification == cpl10.QUALIFICATION
    module = store.head_module(head)
    # the tail input is the retained submission's content hash (G1-X section 2, SCHEMAS row)
    sub = cpl10.ChangeScreenSubmission.model_validate_json(_positive())
    assert module.inputs[-1] == Input(
        input_id="change-screen-submission", sha256=sub.content_hash()
    )
    assert module.inputs[:-1] == submitted.journal.inputs
    assert [i.input_id for i in module.inputs[:-1]] == ["prepared-pack", "CP-0", "CP-1"]
    got = [
        (t.table_id, [c.field for c in t.columns], [list(r.fact_ids) for r in t.rows])
        for t in module.tables
    ]
    want = [
        (t["table_id"], t["columns"], [r["fact_ids"] for r in t["rows"]])
        for t in POSITIVE["tables"]
    ]
    assert got == want
    assert [c.text for c in module.claims] == [c["text"] for c in POSITIVE["claims"]]
    assert list(module.limitations) == POSITIVE["settled_limitations"]
    assert module.inherited_limitations == (CP0_LIMIT, CP1_LIMIT)
    # the run-bound TL10.1 cells (F3) equal the heads they name
    cells = {f.fact_id: f for f in module.facts}
    for row, module_id in (("cp0", "CP-0"), ("cp1", "CP-1")):
        ref = cells[f"TL10.1.{row}.source_ref"].text
        assert ref == f"{module_id}:{heads[module_id].result_sha256}"
        assert cells[f"TL10.1.{row}.scope_status"].text == "With limitations"
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket.ticket_id)
    assert attempt.result_sha256 == head.result_sha256 and len(attempt.steps) == 1


def test_probe_rebuilds_the_settled_head_and_refuses_a_forged_one(
    settled: Path, tmp_path: Path
) -> None:
    store = _fork(settled, tmp_path)
    ticket, _ = _submit(store, _positive())
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.ticket_id == ticket.ticket_id)
    cpl10.probe(store, snapshot, attempt)

    class Forged(Execution):
        def head_module(self, head: Head) -> Module:
            module = super().head_module(head)
            if module.module_id != "CP-L10":
                return module
            facts = tuple(
                f.model_copy(update={"text": "Stable"})
                if f.fact_id == "TL10.2.cash.materiality"
                else f
                for f in module.facts
            )
            return module.model_copy(update={"facts": facts})

    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpl10.probe(Forged(store.directory), snapshot, attempt)


@pytest.mark.parametrize("refusal", SUBMISSIONS["refusals"], ids=lambda r: r["id"])
def test_every_refusal_is_a_retained_invalid_step(
    settled: Path, tmp_path: Path, refusal: dict[str, Any]
) -> None:
    expected = {r["id"]: r for r in EXPECTED["refusals"]}[refusal["id"]]["expected_issues"]
    store = _fork(settled, tmp_path)
    _, submitted = _submit(store, json.dumps(refusal["payload"]))
    journal = submitted.journal
    assert journal.status == "finished" and journal.number == 0
    assert list(journal.issues) == expected
    step = journal.steps[-1]
    assert step.status == "invalid" and list(step.issues) == expected
    assert "CP-L10" not in _heads(store)  # a rejected attempt 0 is not a head


def test_blocked_walk_repeats_the_second_refusal(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    by_id = {r["id"]: r for r in SUBMISSIONS["refusals"]}
    _, first = _submit(store, json.dumps(by_id["r01"]["payload"]))
    assert first.journal.number == 0
    _, second = _submit(store, json.dumps(by_id["r08"]["payload"]))
    assert second.journal.number == 1
    assert _heads(store)["CP-L10"].status == "blocked"
    with pytest.raises(ValueError):
        store.begin("CP-L10")


def test_submit_refuses_a_foreign_step_tool_rules_and_an_absent_ticket(
    settled: Path, tmp_path: Path
) -> None:
    store = _fork(settled, tmp_path)
    ticket = store.begin("CP-L10")
    with pytest.raises(ValueError, match="one step"):
        cpl10.submit(store, ticket.ticket_id, "other_step", _positive(), None)
    with pytest.raises(ValueError, match="no tool-loop rules"):
        cpl10.submit(store, ticket.ticket_id, STEP, _positive(), lambda _text: ())
    with pytest.raises(ValueError, match="absent, finished or belongs to another module"):
        cpl10.submit(store, "no-such-ticket", STEP, _positive(), None)


def test_an_unbound_upstream_settles_as_an_issue_not_a_hang(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    ticket = store.begin("CP-L10")
    pending = store.submit_step(
        ticket.ticket_id,
        "CP-L10",
        cpl10.STEP_IDS,
        STEP,
        _positive(),
        lambda _pack, _attempt: StepValidation(output="{}"),
    )
    outcome = cpl10._validate_step(store, store.pack(), _without(pending, "CP-1"))
    assert outcome.output is None
    assert outcome.issues == ("CP-L10: The CP-L10 attempt binds no CP-1 input",)


# --- rails bindings (D7/D8) -------------------------------------------------------------------


def test_bindings_place_every_table_on_a_rail() -> None:
    placed = [(e.fact_coord.table_id, e.block_id, e.cell_slot) for e in CPL10.entries]
    assert CPL10.module_id == "CP-L10"
    assert placed == [
        ("TL10.1", "evidence", "cpl10-tl10-1"),
        ("TL10.2", "evidence", "cpl10-tl10-2"),
        ("TL10.5", "evidence", "cpl10-tl10-5"),
        ("TL10.3", "evidence", "cpl10-tl10-3"),
        ("TL10.4", "limitations", "cpl10-tl10-4"),
    ]
    assert {e.block_id for e in CPL10.entries} <= RAIL_DESTINATIONS


def test_expected_tables_are_fully_bound_and_no_spec_row_names_the_module(
    settled: Path, tmp_path: Path
) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, _positive())
    head = _heads(store)["CP-L10"]
    module = store.head_module(head)
    view = View(
        run=RUN,
        mode="accepted",
        modules=(
            ModuleView(
                module_id="CP-L10",
                title="Financial change screen",
                aliases=(),
                status="restricted",
                artifact_sha256=head.result_sha256,
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )
    assert validate_bindings(view, SHIPPED_MAPS) == ()
    assert validate_bindings(view, tuple(m for m in SHIPPED_MAPS if m is not CPL10)) != ()
    # rails only (lease D7): the module owns no Front Page block, so `_spec_of` has no row for it
    composed = {
        b
        for c in (
            report_view._CREDIT_SNAPSHOT,
            report_view._EARNINGS_UPDATE,
            report_view._COVENANT_REFINANCING,
        )
        for b in c
    }
    assert not {e.block_id for e in CPL10.entries} & composed


# --- D3 (OPEN): the reader pins what a consumer reads; nothing claims consumption -------------


def test_reader_exposes_exactly_what_the_lease_pins(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, _positive())
    head = _heads(store)["CP-L10"]
    got = cpl10.cpl10_reader(store, head)
    assert [f.name for f in fields(got)] == ["status", "result_sha256", "topics", "counts"]
    assert [f.name for f in fields(cpl10.TopicRead)] == [
        "topic_id",
        "materiality",
        "evidence",
        "disposition",
        "rank",
        "change",
    ]
    assert got.status == "restricted" and got.result_sha256 == head.result_sha256
    want = {t["topic_id"]: t for t in POSITIVE["topics"]}
    assert [t.topic_id for t in got.topics] == list(cpl10.TOPIC_IDS)
    for topic in got.topics:
        row = want[topic.topic_id]
        assert (topic.materiality, topic.evidence, topic.disposition, topic.rank) == (
            row["materiality"],
            row["evidence"],
            row["disposition"],
            row["rank"],
        )
        exact = row["change_exact"]
        assert topic.change == (None if exact is None else Decimal(exact))
    assert dict(got.counts) == POSITIVE["counts"]


def test_reader_refuses_another_module_and_a_tampered_head(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, _positive())
    heads = _heads(store)
    with pytest.raises(ValueError, match="not a CP-L10 head"):
        cpl10.cpl10_reader(store, heads["CP-1"])
    forged = heads["CP-L10"].model_copy(update={"result_sha256": "0" * 64})
    with pytest.raises((ValueError, OSError)):
        cpl10.cpl10_reader(store, forged)


def test_consumption_stays_open() -> None:
    assert EXPECTED["consumption"].startswith("OPEN")
    owners = Path(cpl10.__file__).parent
    readers = [
        p.name
        for p in owners.glob("*.py")
        if "cpl10_reader" in p.read_text() and p.name != "cpl10.py"
    ]
    assert readers == []  # no consumer core reads CP-L10 yet (lease D3)


# --- the methods record ----------------------------------------------------------------------


def test_methods_record_names_the_substring_limit_of_l10_b() -> None:
    path = Path(cpl10.__file__).parents[2] / "deploy_vii" / "methods" / "cpl10.md"
    text = path.read_text()
    assert "substring" in text and "Recovery" in text and "TL10.5" in text
    assert "<!--" not in text  # the draft banner is gone


def test_each_head_status_word_is_its_own(mixed: Path) -> None:
    store = Execution(mixed)
    heads = _heads(store)
    assert (heads["CP-0"].status, heads["CP-1"].status) == ("accepted", "restricted")
    got = cpl10.cpl10_upstream(store, _unbegun(mixed))
    assert (got.cp0_status_word, got.cp1_status_word) == ("Pass", "With limitations")
    assert got.inherited_limitations == (CP1_LIMIT,)
    tree = json.loads(cpl10.view(store, _unbegun(mixed))[1])
    assert [u["status"] for u in tree["upstream"]] == ["Pass", "With limitations"]


def test_the_totals_binding_is_an_amount_slot() -> None:
    unit = {e.fact_coord.table_id: e.unit_class for e in CPL10.entries}
    assert unit == {
        "TL10.1": "text",
        "TL10.2": "text",
        "TL10.5": "amount",
        "TL10.3": "text",
        "TL10.4": "text",
    }


# --- M1: the view writes CP-1's canonical exact decimal ---------------------------------------


def _oracle_amounts() -> list[str]:
    return [
        v["amount_exact"]
        for case in ("positive", "limited")
        for t in EXPECTED["cases"][case]["view_topics"]
        for v in t["values"]
        if v["amount_exact"] is not None
    ]


@pytest.mark.parametrize("text", sorted(set(_oracle_amounts())))
def test_every_oracle_amount_exact_round_trips_whatever_the_stored_padding(text: str) -> None:
    value = Decimal(text)
    variants = {
        value,
        value.quantize(Decimal("0.01")) if value == value.quantize(Decimal("0.01")) else value,
    }
    variants.add(Decimal(f"{text}0") if "." in text else Decimal(f"{text}.00"))
    for variant in variants:
        assert cpl10._plain_text(variant) == text, variant


def test_the_fixture_really_stores_padded_amounts(settled: Path) -> None:
    store = Execution(settled)
    cp1 = store.head_module(_heads(store)["CP-1"])
    stored = {str(f.amount) for f in cp1.facts if f.amount is not None}
    assert {"17.50", "20.00", "47.50", "50.00", "30.00"} <= stored


# --- L1: the adapter, the view and the reader vary with the run ------------------------------


def test_adapter_reads_the_run_and_each_heads_own_status(varied: Path) -> None:
    store = Execution(varied)
    heads = _heads(store)
    assert (heads["CP-0"].status, heads["CP-1"].status) == ("restricted", "accepted")
    got = cpl10.cpl10_upstream(store, _unbegun(varied))
    assert got.issuer_name == "Other Issuer plc" and got.as_of == date(2027, 3, 31)
    assert (got.cp0_status_word, got.cp1_status_word) == ("With limitations", "Pass")
    assert got.inherited_limitations == (CP0_LIMIT,)
    assert (got.cp0_result_sha256, got.cp1_result_sha256) == (
        heads["CP-0"].result_sha256,
        heads["CP-1"].result_sha256,
    )


def test_a_screen_over_another_issuer_names_it_and_settles(varied: Path, tmp_path: Path) -> None:
    store = _fork(varied, tmp_path)
    _submit(store, _positive())
    module = store.head_module(_heads(store)["CP-L10"])
    cells = {f.fact_id: f for f in module.facts}
    assert cells["TL10.1.cp1.scope_status"].text == "Pass"
    assert cells["TL10.1.cp0.scope_status"].text == "With limitations"
    assert module.as_of == date(2027, 3, 31)
    assert module.inherited_limitations == (CP0_LIMIT,)
    assert "Synthetic case; not real issuer qualification" not in module.limitations


def test_reader_follows_the_head_it_is_given(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, json.dumps(SUBMISSIONS["limited"]))
    got = cpl10.cpl10_reader(store, _heads(store)["CP-L10"])
    want = EXPECTED["cases"]["limited"]
    assert dict(got.counts) == want["counts"] != POSITIVE["counts"]
    assert {t.topic_id: t.rank for t in got.topics} == {
        t["topic_id"]: t["rank"] for t in want["topics"]
    }
    assert {t.topic_id: t.materiality for t in got.topics} == {
        t["topic_id"]: t["materiality"] for t in want["topics"]
    }
    assert any(t.change is None for t in got.topics)  # a missing change stays a gap, not 0


def test_reader_on_a_blocked_head_returns_status_and_hash_only(
    settled: Path, tmp_path: Path
) -> None:
    store = _fork(settled, tmp_path)
    by_id = {r["id"]: r for r in SUBMISSIONS["refusals"]}
    _submit(store, json.dumps(by_id["r01"]["payload"]))
    _submit(store, json.dumps(by_id["r08"]["payload"]))
    head = _heads(store)["CP-L10"]
    got = cpl10.cpl10_reader(store, head)
    assert (got.status, got.result_sha256) == ("blocked", head.result_sha256)
    assert got.topics == () and dict(got.counts) == {}


# --- L3: only a bind failure is an analyst-visible issue --------------------------------------


def test_a_store_integrity_failure_propagates_from_the_validator(
    settled: Path, tmp_path: Path
) -> None:
    store = _fork(settled, tmp_path)
    ticket = store.begin("CP-L10")
    pending = store.submit_step(
        ticket.ticket_id,
        "CP-L10",
        cpl10.STEP_IDS,
        STEP,
        _positive(),
        lambda _pack, _attempt: StepValidation(output="{}"),
    )
    cp1 = next(i for i in pending.inputs if i.input_id == "CP-1")
    blob = store.directory / "blobs" / cp1.sha256
    blob.write_bytes(blob.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash"):
        cpl10._validate_step(store, store.pack(), pending)
    with pytest.raises(ValueError, match="hash"):
        cpl10.view(store, pending)


# --- model text: nothing raises after the binding write ---------------------------------------

HOSTILE = ("Rates matter [a lot", "{low", "{}", "x }")


def _free_text_paths() -> list[tuple[Any, ...]]:
    sub = json.loads(_positive())
    paths: list[tuple[Any, ...]] = []
    for i in range(len(sub["assessments"])):
        paths += [("assessments", i, "assessment"), ("assessments", i, "credit_transmission")]
    paths.append(("overall", "rationale"))
    for i in range(len(sub["gaps"])):
        paths += [("gaps", i, f) for f in ("gap", "why_it_matters", "action")]
    return paths


@pytest.mark.parametrize("bad", HOSTILE)
@pytest.mark.parametrize("path", _free_text_paths(), ids=lambda p: ".".join(map(str, p)))
def test_hostile_text_in_any_free_text_field_never_raises_after_the_write(
    settled: Path, tmp_path: Path, path: tuple[Any, ...], bad: str
) -> None:
    sub = json.loads(_positive())
    target: Any = sub
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    store = _fork(settled, tmp_path)
    _, submitted = _submit(store, json.dumps(sub))  # must not raise
    journal = submitted.journal
    assert journal.status == "finished"
    # a journaled issue, or plain data the settled module holds as sent
    assert journal.issues or "CP-L10" in _heads(store)


# --- M2: the run driver binds the readiness markers from the read's own spelling -------------


def _readiness_body(period: str = "Q{n} 25") -> str:
    lines = ['kind=kpi entries=20 columns=["evidence_id","key","period","amount"]']
    for n in range(1, 5):
        for k in ("ebitda", "fcf", "cash_closing", "total_debt", "net_debt"):
            lines.append(json.dumps([f"ev-{k}-{n}", k, period.format(n=n), "1"]))
            lines.append(json.dumps([f"late-{k}-{n}", k, "LTM Q4 25", "1"]))
    lines.append('kind=gap entries=2 columns=["evidence_id","gap_id","text"]')
    lines += ['["g-1","gap-a","x"]', '["g-2","gap-b","y"]']
    return "\n".join(lines)


def test_readiness_literal_binds_markers_from_the_short_period_spelling() -> None:
    runs: Any = importlib.import_module("cpl10_runs")
    document = json.loads(runs.readiness_literal(_readiness_body()))
    (consumer,) = document["consumers"]
    ids = consumer["requirements"][0]["evidence_ids"]
    assert ids[:5] == [
        f"ev-{k}-1" for k in ("ebitda", "fcf", "cash_closing", "total_debt", "net_debt")
    ]
    assert ids[-1] == "ev-net_debt-4" and len(ids) == 20
    assert consumer["gaps"][0]["gap_ids"] == ["gap-a", "gap-b"]
    assert "inputs_sha256" not in document


def test_readiness_literal_fails_loudly_on_an_unmatched_period() -> None:
    runs: Any = importlib.import_module("cpl10_runs")
    with pytest.raises(RuntimeError, match="no kpi evidence for ebitda, quarter 1"):
        runs.readiness_literal(_readiness_body("Quarter {n}"))


# --- acceptance 6: the navigator states (D4 is applied; the Front Page blocks need G2) --------

NAVIGATOR = EXPECTED["rendered"]["front_page_states"]["navigator"]["states"]


def _navigator_state(view: View) -> dict[str, Any]:
    rows = report_view.navigator(view)
    footer: dict[str, list[str]] = {}
    for row in rows:
        if row.number is None:
            footer.setdefault(row.word, []).append(row.module_id)
    return {
        "rows": [
            {"number": r.number, "module_id": r.module_id, "word": r.word, "glyph": r.glyph}
            for r in rows
            if r.number is not None
        ],
        "footer": footer,
        "row_count": len(rows),
    }


def test_navigator_with_cp1_unrun_equals_the_oracle_state(tmp_path: Path) -> None:
    store = Execution.create(tmp_path / "store", _pack())
    got = _navigator_state(store.view())
    want = NAVIGATOR["d4_cp1_unrun"]
    assert got == {"rows": want["rows"], "footer": want["footer"], "row_count": 25}


def test_navigator_with_cp1_settled_equals_the_oracle_state(settled: Path) -> None:
    got = _navigator_state(Execution(settled).view())
    want = NAVIGATOR["d4_cp1_settled"]
    assert got == {"rows": want["rows"], "footer": want["footer"], "row_count": 25}


def test_the_settled_screen_gets_its_own_navigator_row(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, _positive())
    rows = {r["module_id"]: r for r in _navigator_state(store.view())["rows"]}
    assert (rows["CP-L10"]["number"], rows["CP-L10"]["word"]) == (3, "With limitations")


@pytest.mark.skip(
    reason="blocked on G2 (Stage 3): Front Page blocks, call band and rail population"
)
def test_front_page_blocks_and_rails_render_from_the_delivery_scope() -> None:
    raise AssertionError("G2 owner_rendering does not exist yet")


def test_reader_reports_the_status_of_the_head_it_is_given(settled: Path, tmp_path: Path) -> None:
    store = _fork(settled, tmp_path)
    _submit(store, _positive())
    head = _heads(store)["CP-L10"]
    stale = head.model_copy(update={"status": "stale", "notes": ("Input changed: CP-1",)})
    got = cpl10.cpl10_reader(store, stale)
    assert got.status == "stale" and got.result_sha256 == head.result_sha256
    assert dict(got.counts) == POSITIVE["counts"]


# --- round 4: analyst run text in TL10.3 is resolved, free fields are shown as written ---------


def _tl10_3_facts(
    edit: dict[str, str] | None = None, *, token: str = "{TL10.2.%s.change|US$ m}"
) -> tuple[dict[str, Any], str, tuple[Fact, ...]]:
    sub = json.loads(_stage1_payload("positive"))
    first = sub["assessments"][0]
    topic = first["topic_id"]
    tok = token % topic if "%s" in token else token
    first = dict(
        first,
        assessment=f"The balance moved by {tok} in the quarter.",
        credit_transmission=f"A move of {tok} reaches the credit view.",
    )
    overall = dict(sub["overall"], rationale=f"Overall, the balance moved by {tok}.")
    sub = dict(sub, assessments=[first, *sub["assessments"][1:]], overall=overall)
    res = cpl10.change_screen(submission=sub, upstream=UPSTREAM)
    facts = tuple(c.fact for c in res.cells)
    facts = tuple(
        f.model_copy(update={"text": edit[f.fact_id]}) if edit and f.fact_id in edit else f
        for f in facts
    )
    return sub, topic, facts


def _tl10_3_page(facts: tuple[Fact, ...]) -> dict[str, dict[str, Any]]:
    base = _what_changed_view("positive")
    module = ModuleView(
        module_id="CP-L10",
        title="CP-L10",
        aliases=(),
        status="restricted",
        artifact_sha256="c" * 64,
        facts=facts,
        limitations=(),
    )
    return _payload_facts(base.model_copy(update={"modules": (module,)}))


@pytest.mark.parametrize("field", ["assessment", "credit_transmission", "overall"])
def test_tl10_3_analyst_run_text_shows_the_figure_not_the_reference(field: str) -> None:
    _, topic, facts = _tl10_3_facts()
    fact_id = "TL10.3.overall.assessment" if field == "overall" else f"TL10.3.{topic}.{field}"
    shown = _tl10_3_page(facts)[fact_id]
    token = "{TL10.2." + topic + ".change|US$ m}"
    for key in ("display", "table_display"):
        assert token not in shown[key]
        assert "3.75 US$ m" in shown[key]


@pytest.mark.parametrize("broken", ["{TL10.2.%s.chang|US$ m}", "{TL10.2.%s.change|US$ m"])
def test_tl10_3_malformed_reference_in_run_text_fails_closed(broken: str) -> None:
    _, topic, facts = _tl10_3_facts()
    bad = broken % topic
    edited = tuple(
        f.model_copy(update={"text": f"Moved by {bad}."})
        if f.fact_id == f"TL10.3.{topic}.assessment"
        else f
        for f in facts
    )
    with pytest.raises(ValueError, match="does not resolve"):
        _tl10_3_page(edited)


def test_tl10_3_free_source_refs_with_brackets_is_shown_as_written() -> None:
    _, topic, facts = _tl10_3_facts()
    fact_id = f"TL10.3.{topic}.source_refs"
    edited = tuple(
        f.model_copy(update={"text": "CP-1 Cash [sic]"}) if f.fact_id == fact_id else f
        for f in facts
    )
    assert _tl10_3_page(edited)[fact_id]["display"] == "CP-1 Cash [sic]"


def _fact(table_id: str, field: str, text: str) -> Fact:
    return Fact(
        fact_id=f"{table_id}.x.{field}",
        label=field,
        text=text,
        table_id=table_id,
        row_id="x",
        field=field,
        citations=(),
    )


@pytest.mark.parametrize(
    ("module_id", "table_id", "field"),
    [
        ("CP-8", "cp8.what_changed", "value"),
        ("CP-L10", "TL10.3", "assessment"),
        ("CP-L10", "TL10.3", "credit_transmission"),
        ("CP-2H", "T2R.10", "gap"),
        ("CP-2H", "T2R.10", "why_it_matters"),
        ("CP-2H", "T2R.10", "affected_analysis"),
        ("CP-2H", "T2R.10", "action"),
    ],
)
def test_carries_reference_is_true_for_every_registered_run_text_field(
    module_id: str, table_id: str, field: str
) -> None:
    assert report_view._carries_reference(module_id, _fact(table_id, field, "a {X.y|x} b"))
    assert not report_view._carries_reference(module_id, _fact(table_id, field, "no brackets"))


@pytest.mark.parametrize(
    ("module_id", "table_id", "field"),
    [
        ("CP-L10", "TL10.3", "source_refs"),
        ("CP-2A", "T2B.9", "gap"),
        ("CP-1C", "T1C.7", "gap"),
        ("CP-2H", "T2R.10", "id"),
    ],
)
def test_carries_reference_is_false_for_free_text_fields(
    module_id: str, table_id: str, field: str
) -> None:
    assert not report_view._carries_reference(module_id, _fact(table_id, field, "a [sic] b"))
