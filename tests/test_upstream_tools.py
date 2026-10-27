"""Task2 component cases pinned before implementation; never owner completion evidence."""

import copy
import hashlib
import importlib
import json
from datetime import date
from decimal import Decimal

import pytest

from deploy_vii.contracts import Claim, Fact, Module, Run, Source, Span
from deploy_vii.execution import Execution, head_of
from deploy_vii.preparation import PreparedPack

CONTRACT_COMMIT = "d9411401e4797e04a2e030d3741e937d2d210e32"
PRODUCER_SHA = "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046"
SOURCE_SHA = "d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf"
ARTIFACT_JSON = '{"schema_version":"module/5","run_id":"task0-upstream-run","issuer_id":"synthetic-issuer","as_of":"2025-12-31","method_version":"deploy-v-r14","module_id":"CP-1","status":"accepted","inputs":[],"facts":[{"fact_id":"revenue","label":"Revenue","table_id":"income","row_id":"revenue","field":"value","amount":"120","text":null,"status":"known","unit":"MILLIONS","currency":"USD","scale":"1000000","decimals":null,"period":"FY2025","basis":null,"denominator":null,"citations":[{"source_id":"upstream-note","source_sha256":"d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf","locator":"line:1","quote":"Revenue was USD 120 million in FY2025."}],"calculation_id":null,"value_class":null,"source_amount":null,"stated_amount":null,"calculation_status":null,"formula":null,"limitation":null},{"fact_id":"operating_profit","label":"Operating profit","table_id":"income","row_id":"operating_profit","field":"value","amount":"0","text":null,"status":"known","unit":"MILLIONS","currency":"USD","scale":"1000000","decimals":null,"period":"FY2025","basis":null,"denominator":null,"citations":[{"source_id":"upstream-note","source_sha256":"d0c13ba47b0c6703c40aa521def7b28a834f99ac3f810c80103e49406c0d30cf","locator":"line:1","quote":"Operating profit was USD 0 million in FY2025."}],"calculation_id":null,"value_class":null,"source_amount":null,"stated_amount":null,"calculation_status":null,"formula":null,"limitation":null},{"fact_id":"impairment","label":"Impairment","table_id":"income","row_id":"impairment","field":"value","amount":null,"text":null,"status":"missing","unit":"MILLIONS","currency":"USD","scale":"1000000","decimals":null,"period":"FY2025","basis":null,"denominator":null,"citations":[],"calculation_id":null,"value_class":null,"source_amount":null,"stated_amount":null,"calculation_status":null,"formula":null,"limitation":"Synthetic upstream fact not disclosed"}],"tables":[],"claims":[],"limitations":[],"inherited_limitations":[],"attempt":0}'
SOURCE_TEXT = "Revenue was USD 120 million in FY2025.\nOperating profit was USD 0 million in FY2025.\nUPSTREAM_RAW_ONLY"
GRANTS = {
    "producer_ids": ["CP-1"],
    "table_ids": ["income"],
    "row_ids": ["revenue", "operating_profit", "impairment"],
    "fields": [
        "fact_id",
        "label",
        "table_id",
        "row_id",
        "field",
        "amount",
        "text",
        "status",
        "unit",
        "currency",
        "scale",
        "period",
        "limitation",
        "citation_handles",
    ],
    "raw_source_ids": [],
    "fact_fields": ["value"],
    "integrity_internal_inspection": "all metadata/citations of the single bound CP-1 artifact; no raw/quote disclosure",
}
LOOKUP = {
    "producer_module_id": "CP-1",
    "producer_sha256": "f0ac5658a87f2acb971d1b94a2f64638b40c500adc76759f09a1235f31c3b046",
    "table_id": "income",
    "row_ids": ["revenue", "operating_profit", "impairment"],
    "fields": [
        "fact_id",
        "table_id",
        "row_id",
        "field",
        "status",
        "label",
        "amount",
        "scale",
        "unit",
        "currency",
        "period",
        "limitation",
        "citation_handles",
    ],
}


def _tools():
    try:
        return importlib.import_module("deploy_workflow.tools.upstream").UpstreamTools
    except ModuleNotFoundError:
        pytest.fail("Task2 UpstreamTools implementation is absent")


def _execution(tmp_path, *, producer=None, consumer="CP-5", extras=()):
    """Seed reviewed component heads, then use genuine Execution.begin/current_inputs.

    These synthetic heads are not settled analytical owners. Factory authorization
    and real hash-checked reads still execute without mocking current_inputs.
    """
    producer = producer or Module.model_validate_json(ARTIFACT_JSON)
    selected = ("CP-1", consumer, *(head.module_id for head in extras))
    run = Run(
        run_id="task0-upstream-run",
        issuer_id="synthetic-issuer",
        issuer_name="Synthetic Issuer",
        as_of=date(2025, 12, 31),
        case_kind="synthetic",
        requested_modules=selected,
    )
    pack = PreparedPack(
        run=run,
        sources=(
            Source(
                source_id="upstream-note",
                name="Fixed note",
                status="ready",
                sha256=SOURCE_SHA,
                spans=(Span(locator="line:1", text=SOURCE_TEXT),),
            ),
        ),
    )
    store = Execution.create(tmp_path / "execution", pack)
    cp0 = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id="CP-0",
        status="accepted",
        facts=(
            Fact(
                fact_id="run-consumer",
                table_id="T8",
                row_id=consumer,
                field="exact_command",
                label="Run consumer",
                text=f"Run {consumer}",
            ),
        ),
    )
    heads = [cp0, producer, *extras]
    if consumer == "CP-2":
        heads.append(
            Module(
                run_id=run.run_id,
                issuer_id=run.issuer_id,
                as_of=run.as_of,
                module_id="CP-1A",
                status="accepted",
            )
        )
    for head in heads:
        store._store(head.model_dump_json())
    store._write(store.read().model_copy(update={"heads": tuple(map(head_of, heads))}))
    attempt = store.begin(consumer)
    step = "integrity_review" if consumer == "CP-5" else "credit_synthesis"
    return store, attempt, step, producer


def _session(store, attempt, step, grants=None):
    return _tools().from_execution(
        store,
        attempt.ticket_id,
        step,
        grants=copy.deepcopy(GRANTS if grants is None else grants),
    )


def _arguments(producer, **changes):
    return {**copy.deepcopy(LOOKUP), "producer_sha256": producer.content_hash(), **changes}


def _verify(producer, kind="citations", fact_ids=None):
    return {
        "producer_module_id": "CP-1",
        "producer_sha256": producer.content_hash(),
        "kind": kind,
        "fact_ids": fact_ids or ["revenue", "operating_profit", "impairment"],
    }


def _assert_refused(receipt, code):
    assert receipt["status"] == "refused"
    assert receipt["error_code"] == code
    assert receipt["body"] is None
    assert receipt["source_evidence"] == {
        "read": [],
        "extracted": [],
        "surfaced": [],
        "searched": [],
    }
    assert "UPSTREAM_RAW_ONLY" not in json.dumps(receipt)
    assert SOURCE_TEXT.splitlines()[0] not in json.dumps(receipt)


def test_factory_lookup_preserves_fixed_facts(tmp_path):
    assert hashlib.sha256(ARTIFACT_JSON.encode()).hexdigest() == PRODUCER_SHA
    assert hashlib.sha256(SOURCE_TEXT.encode()).hexdigest() == SOURCE_SHA
    store, attempt, step, producer = _execution(tmp_path)
    before = store.read().content_hash()
    session = _session(store, attempt, step)
    result = session.invoke("lookup_upstream", copy.deepcopy(LOOKUP))
    assert result["status"] == "ok", result
    assert set(result) == {
        "schema_version",
        "call_id",
        "sequence",
        "binding",
        "tool",
        "arguments",
        "status",
        "body",
        "error_code",
        "source_evidence",
    }
    assert result["binding"] == {
        "run_id": "task0-upstream-run",
        "issuer_id": "synthetic-issuer",
        "as_of": "2025-12-31",
        "method_version": "deploy-v-r14",
        "pack_sha256": store.pack().content_hash(),
        "snapshot_sha256": before,
        "module_id": "CP-5",
        "step_id": "integrity_review",
        "ticket_id": attempt.ticket_id,
        "attempt": 0,
        "inputs": [item.model_dump(mode="json") for item in attempt.inputs],
    }
    assert result["body"]["producer"] == {
        "module_id": "CP-1",
        "sha256": PRODUCER_SHA,
        "status": "accepted",
    }
    rows = result["body"]["rows"]
    revenue, zero, missing = [row["facts"][0] for row in rows]
    assert [row["row_id"] for row in rows] == ["revenue", "operating_profit", "impairment"]
    assert list(revenue) == LOOKUP["fields"]
    assert (
        revenue["amount"],
        revenue["scale"],
        revenue["unit"],
        revenue["currency"],
        revenue["period"],
        revenue["status"],
    ) == (
        "120",
        "1000000",
        "MILLIONS",
        "USD",
        "FY2025",
        "known",
    )
    assert revenue["citation_handles"] == [
        {
            "source_id": "upstream-note",
            "source_sha256": SOURCE_SHA,
            "locator": "line:1",
        }
    ]
    assert zero["amount"] == "0" and zero["status"] == "known"
    assert missing["amount"] is None and missing["status"] == "missing"
    assert missing["limitation"] == "Synthetic upstream fact not disclosed"
    assert missing["citation_handles"] == []
    assert "quote" not in json.dumps(result["body"])
    assert "UPSTREAM_RAW_ONLY" not in json.dumps(result)
    assert result["source_evidence"] == {
        "read": [],
        "extracted": [],
        "surfaced": [],
        "searched": [],
    }
    assert store.read().content_hash() == before
    assert store.result(PRODUCER_SHA) == producer
    (tmp_path / "factory-lookup-receipt.json").write_text(json.dumps(result, indent=2))


@pytest.mark.parametrize("kind", ["citations", "integrity"])
def test_verification_reuses_checks_without_disclosure_or_writes(tmp_path, kind):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    before = store.read().model_dump_json()
    result = session.invoke("verify_upstream", _verify(producer, kind))
    assert result["status"] == "ok", result
    assert result["body"] == {
        "producer": {"module_id": "CP-1", "sha256": PRODUCER_SHA, "status": "accepted"},
        "kind": kind,
        "verdict": "valid",
        "issue_count": 0,
        "issues": [],
    }
    assert store.read().model_dump_json() == before
    (tmp_path / f"factory-{kind}-receipt.json").write_text(json.dumps(result, indent=2))


def test_bad_quote_is_invalid_verification_not_permission_or_raw_text(tmp_path):
    raw = json.loads(ARTIFACT_JSON)
    raw["facts"][0]["citations"][0]["quote"] = "Revenue was USD 999 million in FY2025."
    producer = Module.model_validate_json(json.dumps(raw))
    store, attempt, step, producer = _execution(tmp_path, producer=producer)
    result = _session(store, attempt, step).invoke("verify_upstream", _verify(producer))
    assert result["status"] == "ok"
    assert result["body"]["verdict"] == "invalid"
    assert result["body"]["issue_count"] == 1
    assert result["body"]["issues"] == [{"code": "fact_citation", "fact_ids": ["revenue"]}]
    assert "999" not in json.dumps(result) and "quote" not in json.dumps(result["body"])


@pytest.mark.parametrize(
    "change,code",
    [
        ({"producer_module_id": "CP-4"}, "not_permitted"),
        ({"producer_sha256": "a" * 64}, "identity_mismatch"),
        ({"table_id": "hidden"}, "not_permitted"),
        ({"row_ids": ["hidden"]}, "not_permitted"),
        (
            {"fields": ["fact_id", "table_id", "row_id", "field", "status", "citations"]},
            "not_permitted",
        ),
        (
            {"fields": ["fact_id", "table_id", "row_id", "field", "status", "quote"]},
            "not_permitted",
        ),
        ({"unexpected": "key"}, "bad_arguments"),
        ({"row_ids": []}, "bad_arguments"),
        ({"row_ids": [str(i) for i in range(21)]}, "bad_arguments"),
        ({"fields": [str(i) for i in range(17)]}, "bad_arguments"),
        ({"row_ids": True}, "bad_arguments"),
        ({"row_ids": [True]}, "bad_arguments"),
        ({"row_ids": ["revenue", "revenue"]}, "bad_arguments"),
        ({"fields": ["amount"]}, "bad_arguments"),
        ({"producer_sha256": "bad"}, "bad_arguments"),
    ],
)
def test_lookup_refuses_whole_request(tmp_path, change, code):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    before = store.read().content_hash()
    _assert_refused(session.invoke("lookup_upstream", _arguments(producer, **change)), code)
    assert store.read().content_hash() == before


def test_raw_source_tools_are_never_admitted(tmp_path):
    store, attempt, step, _ = _execution(tmp_path)
    session = _session(store, attempt, step)
    for name in ("read_pages", "search_pack", "extract_statements", "unknown"):
        _assert_refused(session.invoke(name, {}), "not_permitted")


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("run_id", "other-run"),
        ("issuer_id", "other-issuer"),
        ("as_of", date(2024, 12, 31)),
        ("method_version", "unknown-method"),
    ],
)
def test_foreign_valid_hash_is_rejected_by_factory(tmp_path, attribute, value):
    raw = json.loads(ARTIFACT_JSON)
    raw[attribute] = value.isoformat() if isinstance(value, date) else value
    # A foreign method cannot form a Module in the adopted contract: tampered bytes
    # still exercise the real result reader, rather than unsafe model_copy output.
    if attribute == "method_version":
        store, attempt, step, _ = _execution(tmp_path)
        digest = hashlib.sha256(json.dumps(raw).encode()).hexdigest()
        (store.directory / "blobs" / digest).write_text(json.dumps(raw))
        snapshot = store.read()
        heads = tuple(
            h.model_copy(update={"result_sha256": digest}) if h.module_id == "CP-1" else h
            for h in snapshot.heads
        )
        store._write(snapshot.model_copy(update={"heads": heads, "attempts": ()}))
        attempt = store.begin("CP-5")
    else:
        store, attempt, step, _ = _execution(
            tmp_path,
            producer=Module.model_validate_json(json.dumps(raw)),
        )
    with pytest.raises(ValueError, match="identity_mismatch"):
        _session(store, attempt, step)


def test_tampered_blob_refuses_without_emitting_old_partial_body(tmp_path):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    (store.directory / "blobs" / PRODUCER_SHA).write_text("tampered private blob")
    _assert_refused(session.invoke("lookup_upstream", _arguments(producer)), "identity_mismatch")


@pytest.mark.parametrize("change", ["head", "inputs", "ticket", "selection"])
def test_session_does_not_follow_mutable_journal(tmp_path, change):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    snapshot = store.read()
    if change == "head":
        heads = tuple(
            h.model_copy(update={"status": "stale"}) if h.module_id == "CP-1" else h
            for h in snapshot.heads
        )
        changed = snapshot.model_copy(update={"heads": heads})
    elif change == "inputs":
        changed_attempt = attempt.model_copy(update={"inputs": attempt.inputs[:-1]})
        changed = snapshot.model_copy(update={"attempts": (changed_attempt,)})
    elif change == "ticket":
        changed = snapshot.model_copy(update={"attempts": ()})
    else:
        changed = snapshot.model_copy(
            update={
                "run": snapshot.run.model_copy(
                    update={"requested_modules": ("CP-0",)},
                )
            }
        )
    store._write(changed)
    _assert_refused(session.invoke("lookup_upstream", _arguments(producer)), "stale_binding")


def test_cp2_view_does_not_offer_missing_fact(tmp_path):
    store, attempt, step, producer = _execution(tmp_path, consumer="CP-2")
    grants = copy.deepcopy(GRANTS)
    grants["row_ids"] = ["revenue", "operating_profit"]
    session = _session(store, attempt, step, grants)
    _assert_refused(session.invoke("lookup_upstream", _arguments(producer)), "not_permitted")
    result = session.invoke(
        "lookup_upstream",
        _arguments(
            producer,
            row_ids=["operating_profit", "revenue"],
        ),
    )
    assert result["status"] == "ok"
    assert [row["row_id"] for row in result["body"]["rows"]] == ["operating_profit", "revenue"]


@pytest.mark.parametrize("variant", ["subset", "partial", "claims", "multi"])
def test_integrity_cannot_hide_unfavorable_scope(tmp_path, variant):
    producer = Module.model_validate_json(ARTIFACT_JSON)
    if variant == "claims":
        producer = producer.model_copy(
            update={
                "claims": (
                    Claim(
                        claim_id="claim1",
                        text="Revenue is recorded.",
                        citations=(),
                    ),
                )
            }
        )
    extras = ()
    if variant == "multi":
        extras = (
            Module(
                run_id=producer.run_id,
                issuer_id=producer.issuer_id,
                as_of=producer.as_of,
                module_id="CP-1A",
                status="accepted",
            ),
        )
    store, attempt, step, producer = _execution(tmp_path, producer=producer, extras=extras)
    grants = copy.deepcopy(GRANTS)
    if variant == "partial":
        grants["row_ids"] = ["revenue", "operating_profit"]
    session = _session(store, attempt, step, grants)
    args = _verify(producer, "integrity")
    if variant == "subset":
        args["fact_ids"] = ["revenue"]
    _assert_refused(session.invoke("verify_upstream", args), "not_permitted")


def test_oversized_lookup_refuses_bytes_not_just_characters(tmp_path):
    producer = Module.model_validate_json(ARTIFACT_JSON)
    facts = (producer.facts[0].model_copy(update={"label": "€" * 3000}), *producer.facts[1:])
    store, attempt, step, producer = _execution(
        tmp_path, producer=producer.model_copy(update={"facts": facts})
    )
    _assert_refused(
        _session(store, attempt, step).invoke(
            "lookup_upstream",
            _arguments(producer),
        ),
        "bad_arguments",
    )


def test_snapshot_change_during_result_build_refuses(tmp_path, monkeypatch):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    original = store.result

    def result_and_change(sha256):
        result = original(sha256)
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return result

    monkeypatch.setattr(store, "result", result_and_change)
    _assert_refused(session.invoke("lookup_upstream", _arguments(producer)), "stale_binding")


def test_receipts_are_independent_and_success_survives_refusal(tmp_path):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    args = _arguments(producer)
    first = session.invoke("lookup_upstream", args)
    retained = copy.deepcopy(first)
    args["row_ids"].append("hidden")
    second = session.invoke("lookup_upstream", args)
    _assert_refused(second, "not_permitted")
    assert first == retained and first["sequence"] == 1 and second["sequence"] == 2
    assert first["call_id"] != second["call_id"]
    assert first["arguments"]["row_ids"] == ["revenue", "operating_profit", "impairment"]


@pytest.mark.parametrize(
    "variant", ["absent", "finished", "wrong-step", "pending-step", "unauthorized"]
)
def test_factory_rejects_nonexecutable_ticket(tmp_path, variant):
    from deploy_vii.execution import StepSubmission

    store, attempt, step, _ = _execution(tmp_path)
    snapshot = store.read()
    if variant == "absent":
        ticket_id = "missing-ticket"
    else:
        ticket_id = attempt.ticket_id
    if variant == "finished":
        store._write(
            snapshot.model_copy(
                update={"attempts": (attempt.model_copy(update={"status": "finished"}),)}
            )
        )
    elif variant == "wrong-step":
        step = "credit_synthesis"
    elif variant == "pending-step":
        pending = StepSubmission(step_id=step, inputs=attempt.inputs, payload_sha256="a" * 64)
        store._write(
            snapshot.model_copy(
                update={"attempts": (attempt.model_copy(update={"steps": (pending,)}),)}
            )
        )
    elif variant == "unauthorized":
        heads = tuple(
            h.model_copy(update={"commands": ()}) if h.module_id == "CP-0" else h
            for h in snapshot.heads
        )
        store._write(snapshot.model_copy(update={"heads": heads}))
    with pytest.raises(ValueError):
        _tools().from_execution(store, ticket_id, step, grants=copy.deepcopy(GRANTS))


def test_wrong_bound_status_refuses_as_identity_mismatch(tmp_path):
    store, attempt, step, _ = _execution(tmp_path)
    snapshot = store.read()
    inputs = tuple(
        item.model_copy(update={"status": "restricted"}) if item.input_id == "CP-1" else item
        for item in attempt.inputs
    )
    store._write(
        snapshot.model_copy(update={"attempts": (attempt.model_copy(update={"inputs": inputs}),)})
    )
    with pytest.raises(ValueError, match="identity_mismatch"):
        _session(store, attempt, step)


def test_integrity_reports_scale_without_new_arithmetic_or_unsafe_detail(tmp_path):
    producer = Module.model_validate_json(ARTIFACT_JSON)
    facts = (producer.facts[0].model_copy(update={"scale": Decimal(1)}), *producer.facts[1:])
    store, attempt, step, producer = _execution(
        tmp_path, producer=producer.model_copy(update={"facts": facts})
    )
    result = _session(store, attempt, step).invoke(
        "verify_upstream", _verify(producer, "integrity")
    )
    assert result["status"] == "ok"
    assert result["body"]["verdict"] == "invalid"
    assert result["body"]["issues"] == [{"code": "scale_unit", "fact_ids": ["revenue"]}]


def test_frozen_grants_and_returned_receipts_cannot_mutate_session(tmp_path):
    store, attempt, step, producer = _execution(tmp_path)
    grants = copy.deepcopy(GRANTS)
    session = _tools().from_execution(store, attempt.ticket_id, step, grants=grants)
    grants["fields"].append("citations")
    first = session.invoke("lookup_upstream", _arguments(producer))
    first["binding"]["run_id"] = "tampered-return"
    first["body"]["rows"].clear()
    retained = session.receipts
    assert retained[0]["binding"]["run_id"] == "task0-upstream-run"
    assert len(retained[0]["body"]["rows"]) == 3
    retained[0]["arguments"]["row_ids"].clear()
    assert len(session.receipts[0]["arguments"]["row_ids"]) == 3
    hidden = _arguments(producer, fields=[*LOOKUP["fields"], "citations"])
    _assert_refused(session.invoke("lookup_upstream", hidden), "not_permitted")


def test_reentrant_invocation_is_refused_and_retained_in_call_order(tmp_path, monkeypatch):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    original = store.result
    nested = []

    def reenter(sha256):
        if not nested:
            nested.append(session.invoke("lookup_upstream", _arguments(producer)))
        return original(sha256)

    monkeypatch.setattr(store, "result", reenter)
    outer = session.invoke("lookup_upstream", _arguments(producer))
    assert outer["status"] == "ok"
    _assert_refused(nested[0], "not_permitted")
    assert [r["sequence"] for r in session.receipts] == [1, 2]


@pytest.mark.parametrize("variant", ["unexpected", "control"])
def test_exception_categories_never_turn_failure_into_clean_success(tmp_path, monkeypatch, variant):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)

    # This is an exceptional local dependency seam; regular tests use real checks.
    def fails(*args, **kwargs):
        if variant == "control":
            raise KeyboardInterrupt()
        raise RuntimeError("UPSTREAM_RAW_ONLY")

    monkeypatch.setattr(
        importlib.import_module("deploy_workflow.tools.upstream"), "citation_issues", fails
    )
    if variant == "control":
        with pytest.raises(KeyboardInterrupt):
            session.invoke("verify_upstream", _verify(producer))
        interrupted = session.receipts[-1]
        assert interrupted["status"] == "error"
        assert interrupted["error_code"] == "internal_error"
        assert interrupted["body"] is None
        # An interrupted operation must not leave the single-writer lock held.
        recovered = session.invoke("lookup_upstream", _arguments(producer))
        assert recovered["status"] == "ok"
    else:
        result = session.invoke("verify_upstream", _verify(producer))
        assert result["status"] == "error" and result["error_code"] == "internal_error"
        assert result["body"] is None and "UPSTREAM_RAW_ONLY" not in json.dumps(result)


def test_cp2_factory_rejects_grants_beyond_referencable_view(tmp_path):
    store, attempt, step, _ = _execution(tmp_path, consumer="CP-2")
    # Original grants include the missing-only impairment row. Without the
    # typed referencable upper bound this factory would wrongly admit them.
    with pytest.raises(ValueError, match="not_permitted"):
        _session(store, attempt, step)


def test_snapshot_change_after_verification_refuses_staged_result(tmp_path, monkeypatch):
    from deploy_workflow.tools import upstream

    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    original = upstream.citation_issues

    def check_then_change(citations, sources):
        issues = original(citations, sources)
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return issues

    monkeypatch.setattr(upstream, "citation_issues", check_then_change)
    result = session.invoke("verify_upstream", _verify(producer))
    _assert_refused(result, "stale_binding")
    assert session.receipts[-1]["body"] is None


@pytest.mark.parametrize("seam", ["receipt-initialization", "receipt-retention"])
def test_interrupted_receipt_bookkeeping_never_strands_writer_lock(tmp_path, monkeypatch, seam):
    from deploy_workflow.tools import upstream

    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)

    def interrupted_id():
        raise KeyboardInterrupt()

    class InterruptedReceipts(list):
        def append(self, value):
            raise KeyboardInterrupt()

    with monkeypatch.context() as probe:
        if seam == "receipt-initialization":
            probe.setattr(upstream, "uuid4", interrupted_id)
        else:
            probe.setattr(session, "_receipts", InterruptedReceipts())
        with pytest.raises(KeyboardInterrupt):
            session.invoke("lookup_upstream", _arguments(producer))
    recovered = session.invoke("lookup_upstream", _arguments(producer))
    assert recovered["status"] == "ok"
    assert recovered["body"]["rows"][0]["facts"][0]["amount"] == "120"


def test_deep_json_arguments_return_and_retain_complete_refusal(tmp_path):
    store, attempt, step, producer = _execution(tmp_path)
    session = _session(store, attempt, step)
    nested = "caller-owned"
    for _ in range(600):
        nested = [nested]
    arguments = _arguments(producer, unexpected=nested)
    result = session.invoke("lookup_upstream", arguments)
    _assert_refused(result, "bad_arguments")
    # JSON roundtrips at this protocol-valid depth; deepcopy's lower effective
    # recursion ceiling must not prevent a detached complete refusal receipt.
    assert json.dumps(result["arguments"]) == json.dumps(arguments)
    assert json.dumps(session.receipts[0]["arguments"]) == json.dumps(arguments)
    assert session.invoke("lookup_upstream", _arguments(producer))["status"] == "ok"


# A2 fixtures are handwritten permission components, not settled analytical evidence.
A2_FIELDS = ["fact_id", "label", "table_id", "row_id", "field", "amount", "text", "status",
             "unit", "currency", "scale", "period", "basis", "limitation", "calculation_id",
             "citation_handles"]


def _a2_basis(period_id, kind="Q"):
    parts = ("historical", f"{kind}:{period_id}")
    return "model-basis:" + hashlib.sha256("".join(f"{len(p)}:{p}" for p in parts).encode()).hexdigest()


def _a2_producer(*, page25=False, long_ids=False):
    producer = Module.model_validate_json(ARTIFACT_JSON)
    facts = []
    periods = ("q3-2025", "q4-2025") if page25 else (
        "q1-2025", "q2-2025", "q3-2025", "q4-2025", "fy-2025", "opening-2024")
    suffix = "x" * 153 if long_ids else ""

    def add(table, row, field, value, period):
        numeric = isinstance(value, Decimal)
        facts.append(Fact(
            fact_id=f"f{len(facts):03}" + suffix, label=field, table_id=table,
            row_id=row + suffix, field=field, amount=value if numeric else None,
            text=None if numeric or value is None else value,
            status="missing" if value is None else "known", period=period,
            limitation="Four complete contiguous quarters required" if value is None else None,
            unit="MULTIPLE" if row == "total_leverage_reported" else "MILLIONS" if numeric else None,
            currency="USD" if numeric and row != "total_leverage_reported" else None,
            scale=Decimal(1000000) if numeric and row != "total_leverage_reported" else Decimal(1),
            citations=producer.facts[0].citations,
        ))
    for pid in periods:
        kind = "QUARTER" if pid.startswith("q") else "FY" if pid.startswith("fy") else "PERIOD_END"
        values = dict(period_id=pid, period_type=kind, fiscal_year="2025",
                      fiscal_quarter="3" if pid.startswith("q3") else "4", start_date="2025-07-01",
                      end_date="2025-09-30", currency="USD", unit="MILLIONS",
                      accounting_basis="IFRS", entity_perimeter="consolidated group")
        for key, value in values.items():
            add("T4.14", pid, key, value, pid)
    if page25:
        add("T4.14", periods[0], "basis_note", "Reported", periods[0])
    for row in (("revenue",) if page25 else ("revenue", "total_leverage_reported")):
        add("T4.10", row, "field_0", "Earnings", "dashboard")
        add("T4.10", row, "field_1", row, "dashboard")
        for pid in ("q3-2025", "q4-2025"):
            value = (Decimal(0) if pid.startswith("q3") else Decimal(30)) if row == "revenue" else (
                None if pid.startswith("q3") else Decimal("1.6666666666666666666666666666666666667"))
            add("T4.10", row, _a2_basis(pid), value, pid)
    return producer.model_copy(update={"facts": tuple(facts)})


def _a2_grants(producer, *, diagonal=False):
    coords = [dict(fact_id=f.fact_id, table_id=f.table_id, row_id=f.row_id, field=f.field)
              for f in producer.facts if not diagonal or f.table_id == "T4.14"
              or f.field in {"field_0", "field_1"}
              or (f.row_id == "revenue" and f.field == _a2_basis("q3-2025"))
              or (f.row_id == "total_leverage_reported" and f.field == _a2_basis("q4-2025"))]
    return dict(schema_version="cp1b-upstream-grant/2", consumer_module_id="CP-1B",
                step_id="earnings_delta", raw_source_ids=[], producers=[dict(
                    module_id="CP-1", sha256=producer.content_hash(), coordinates=coords,
                    projected_fields=A2_FIELDS.copy())])


def _a2_session(tmp_path, *, producer=None, diagonal=False):
    producer = producer or _a2_producer()
    store, attempt, _, producer = _execution(tmp_path, producer=producer, consumer="CP-1B")
    grants = _a2_grants(producer, diagonal=diagonal)
    session = _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)
    return store, attempt, producer, grants, session


def _a2_lookup(producer, row="revenue", **changes):
    return dict(producer_module_id="CP-1", producer_sha256=producer.content_hash(),
                table_id="T4.10", row_ids=[row], fields=A2_FIELDS.copy(), **changes)


def _a2_page(session, *, cursor=None, limit=20, **changes):
    header = session.access_manifest
    args = dict(producer_module_id="CP-1", producer_sha256=header["producer"]["sha256"],
                manifest_sha256=header["manifest_sha256"], cursor=cursor, limit=limit)
    args.update(changes)
    return session.invoke("read_access_manifest", args)


def _a2_canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def test_a2_status_projection_tuple_grants_and_citation_handles(tmp_path):
    _, _, producer, grants, session = _a2_session(tmp_path, diagonal=True)
    first = session.invoke("lookup_upstream", _a2_lookup(producer))
    assert first["status"] == "ok"
    body = first["body"]
    assert body["projection"] == "granted_fact_projection"
    values = [f for f in body["rows"][0]["facts"] if f["amount"] is not None]
    assert [(f["amount"], f["status"]) for f in values] == [("0", "known")]
    assert [f["field"] for f in body["rows"][0]["facts"]] == sorted(f["field"] for f in body["rows"][0]["facts"])
    assert set(values[0]["citation_handles"][0]) == {"source_id", "source_sha256", "locator"}
    hidden = next(f.fact_id for f in producer.facts if f.row_id == "revenue" and f.field == _a2_basis("q4-2025"))
    _assert_refused(session.invoke("verify_upstream", _verify(producer, "citations", [hidden])), "not_permitted")
    allowed = {c["fact_id"] for c in grants["producers"][0]["coordinates"]}
    assert hidden not in allowed
    assert all(not any(v in json.dumps(receipt) for v in ("UPSTREAM_RAW_ONLY", "quote\"")) for receipt in session.receipts)
    other = _a2_session(tmp_path / "all")[4]
    missing = other.invoke("lookup_upstream", _a2_lookup(producer, "total_leverage_reported"))
    gap = next(f for f in missing["body"]["rows"][0]["facts"] if f["status"] == "missing")
    assert gap["amount"] is None and "Four complete" in gap["limitation"]
    metadata = other.invoke("lookup_upstream", dict(producer_module_id="CP-1", producer_sha256=producer.content_hash(),
        table_id="T4.14", row_ids=["opening-2024"], fields=A2_FIELDS.copy()))
    assert any(f["text"] == "PERIOD_END" for f in metadata["body"]["rows"][0]["facts"])


def test_a2_manifest_exact_hashes_pagination_replay_and_detachment(tmp_path):
    _, _, producer, grants, session = _a2_session(tmp_path, producer=_a2_producer(page25=True))
    header = session.access_manifest
    assert header["coordinate_count"] == 25 and header["period_index"]["authorized_complete"] is True
    normalized = copy.deepcopy(grants)
    pg = normalized["producers"][0]
    pg["projected_fields"].sort()
    pg["coordinates"].sort(key=lambda c: tuple(c[k] for k in ("table_id", "row_id", "field", "fact_id")))
    assert header["grant_sha256"] == hashlib.sha256(_a2_canonical(normalized)).hexdigest()
    without_m = {k: v for k, v in header.items() if k != "manifest_sha256"}
    assert header["manifest_sha256"] == hashlib.sha256(_a2_canonical(dict(header=without_m, coordinates=pg["coordinates"]))).hexdigest()
    page1 = _a2_page(session)["body"]
    assert page1["offset"] == 0 and len(page1["entries"]) == 20 and not page1["complete"]
    token = page1["next_cursor"]
    page2 = _a2_page(session, cursor=token)["body"]
    assert page2["offset"] == 20 and len(page2["entries"]) == 5 and page2["complete"]
    assert page2["next_cursor"] is None
    assert page1["entries"] + page2["entries"] == pg["coordinates"]
    assert _a2_page(session, cursor=token)["body"] == page2
    assert len(_a2_page(session, cursor=token, limit=1)["body"]["entries"]) == 1
    header["projected_fields"].append("quote")
    grants["producers"][0]["coordinates"].clear()
    page1["entries"].clear()
    assert len(_a2_page(session)["body"]["entries"]) == 20
    assert "quote" not in session.access_manifest["projected_fields"]
    assert producer.content_hash() == session.access_manifest["producer"]["sha256"]


@pytest.mark.parametrize("variant,code", [
    ("omit-index", "not_permitted"), ("missing-index", "not_permitted"),
    ("omit-field", "not_permitted"), ("extra-table", "not_permitted"),
    ("wrong-tuple", "not_permitted"), ("rolling", "not_permitted"),
    ("duplicate", "bad_arguments"), ("duplicate-id", "bad_arguments"),
    ("duplicate-placement", "bad_arguments"),
    ("extra-key", "bad_arguments"), ("quote-field", "not_permitted"),
    ("extra-producer", "not_permitted"), ("wrong-digest", "identity_mismatch"),
])
def test_a2_factory_grant_guards(tmp_path, variant, code):
    producer = _a2_producer()
    if variant == "missing-index":
        producer = producer.model_copy(update={"facts": tuple(f for f in producer.facts if f.table_id != "T4.14")})
    store, attempt, _, _ = _execution(tmp_path, producer=producer, consumer="CP-1B")
    grants = _a2_grants(producer)
    pg = grants["producers"][0]
    if variant == "omit-index": pg["coordinates"].pop(1)
    elif variant == "omit-field": pg["projected_fields"].remove("text")
    elif variant == "extra-table": pg["coordinates"][0]["table_id"] = "T4.1"
    elif variant == "wrong-tuple": pg["coordinates"][0]["row_id"] = "ungranted-row"
    elif variant == "rolling": pg["coordinates"][-1]["field"] = "rolling:value"
    elif variant == "duplicate": pg["coordinates"].append(pg["coordinates"][0].copy())
    elif variant == "duplicate-id": pg["coordinates"][1]["fact_id"] = pg["coordinates"][0]["fact_id"]
    elif variant == "duplicate-placement": pg["coordinates"][0]["row_id"] = "q4-2025"
    elif variant == "extra-key": grants["unexpected"] = True
    elif variant == "quote-field": pg["projected_fields"].append("quote")
    elif variant == "extra-producer": grants["producers"].append(dict(pg, module_id="CP-1B"))
    elif variant == "wrong-digest": pg["sha256"] = "e" * 64
    with pytest.raises(ValueError, match=f"^{code}$"):
        _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)


@pytest.mark.parametrize("change,code", [
    ({"cursor": "bad"}, "bad_arguments"), ({"cursor": "access-cursor:" + "a" * 64}, "stale_binding"),
    ({"limit": True}, "bad_arguments"), ({"limit": 0}, "bad_arguments"),
    ({"limit": 21}, "bad_arguments"), ({"manifest_sha256": "e" * 64}, "identity_mismatch"),
    ({"manifest_sha256": "bad"}, "bad_arguments"), ({"producer_module_id": "CP-0"}, "not_permitted"),
    ({"extra": 1}, "bad_arguments"),
])
def test_a2_manifest_refusals(tmp_path, change, code):
    session = _a2_session(tmp_path)[4]
    _assert_refused(_a2_page(session, **change), code)
    assert _a2_page(session)["status"] == "ok"


def test_a2_versions_are_exclusive_and_no_integrity_or_source_tools(tmp_path):
    store, attempt, _, producer = _execution(tmp_path, producer=_a2_producer(), consumer="CP-1B")
    with pytest.raises(ValueError, match="not_permitted"):
        _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=GRANTS)
    _, _, producer, _, session = _a2_session(tmp_path / "v2")
    _assert_refused(session.invoke("verify_upstream", _verify(producer, "integrity")), "not_permitted")
    for name in ("read_integrity_scope", "verify_integrity_scope", "read_pages", "search_pack"):
        _assert_refused(session.invoke(name, {}), "not_permitted")
    for consumer in ("CP-2", "CP-5"):
        st, at, step, pr = _execution(tmp_path / consumer, consumer=consumer)
        with pytest.raises(ValueError, match="not_permitted"):
            _tools().from_execution(st, at.ticket_id, step, grants=_a2_grants(pr))
    st, at, step, _ = _execution(tmp_path / "v1")
    v1 = _session(st, at, step)
    with pytest.raises(ValueError, match="not_permitted"):
        _ = v1.access_manifest
    _assert_refused(v1.invoke("read_access_manifest", {}), "not_permitted")


def test_a2_bytes_and_invalid_citations_are_sanitized(tmp_path):
    producer = _a2_producer()
    target = next(f for f in producer.facts if f.row_id == "revenue" and f.amount is not None)
    bad = target.model_copy(update={"citations": (target.citations[0].model_copy(update={"quote": "UPSTREAM_PRIVATE_QUOTE_SENTINEL"}),)})
    producer = producer.model_copy(update={"facts": tuple(bad if f == target else f for f in producer.facts)})
    _, _, producer, _, session = _a2_session(tmp_path, producer=producer)
    result = session.invoke("verify_upstream", _verify(producer, "citations", [bad.fact_id]))
    assert result["status"] == "ok" and result["body"]["verdict"] == "invalid"
    assert result["body"]["issues"] == [{"code": "fact_citation", "fact_ids": [bad.fact_id]}]
    assert "UPSTREAM_PRIVATE" not in json.dumps(result)
    giant = bad.model_copy(update={"label": "€" * 3000})
    producer = producer.model_copy(update={"facts": tuple(giant if f == bad else f for f in producer.facts)})
    s2 = _a2_session(tmp_path / "giant", producer=producer)[4]
    _assert_refused(s2.invoke("lookup_upstream", _a2_lookup(producer)), "bad_arguments")


def test_a2_long_coordinate_pages_obey_bytes_and_traverse_every_entry(tmp_path):
    _, _, _, _, session = _a2_session(tmp_path, producer=_a2_producer(page25=True, long_ids=True))
    offset, cursor, entries = 0, None, []
    while True:
        result = _a2_page(session, cursor=cursor)
        assert result["status"] == "ok"
        body = result["body"]
        assert len(_a2_canonical(body)) <= 8192
        if offset == 0:
            assert len(body["entries"]) < 20  # Twenty legal long-ID entries exceed8192 bytes.
        assert body["offset"] == offset and 1 <= len(body["entries"]) <= 20
        entries.extend(body["entries"])
        offset += len(body["entries"])
        cursor = body["next_cursor"]
        if body["complete"]:
            assert cursor is None
            break
    assert offset == session.access_manifest["coordinate_count"] == len(entries)


@pytest.mark.parametrize("operation", ["lookup", "page", "property", "verify"])
def test_a2_changed_snapshot_revokes_all_access(tmp_path, operation):
    store, _, producer, _, session = _a2_session(tmp_path)
    header = session.access_manifest
    store._write(store.read().model_copy(update={"parent": store.read().content_hash()}))
    if operation == "property":
        with pytest.raises(ValueError, match="stale_binding"):
            _ = session.access_manifest
    elif operation == "lookup":
        _assert_refused(session.invoke("lookup_upstream", _a2_lookup(producer)), "stale_binding")
    elif operation == "verify":
        _assert_refused(session.invoke("verify_upstream", _verify(producer, "citations", [producer.facts[0].fact_id])), "stale_binding")
    else:
        _assert_refused(session.invoke("read_access_manifest", dict(producer_module_id="CP-1", producer_sha256=producer.content_hash(),
            manifest_sha256=header["manifest_sha256"], cursor=None, limit=20)), "stale_binding")


def test_a2_fresh_executable_repair_uses_actual_attempt_number(tmp_path):
    store, attempt, producer, grants, old = _a2_session(tmp_path)
    store.interrupt(attempt.ticket_id, "Retained deliberate component interruption")
    repaired = store.begin("CP-1B")
    assert repaired.number == 1
    session = _tools().from_execution(store, repaired.ticket_id, "earnings_delta", grants=grants)
    assert session.access_manifest["attempt"] == 1
    assert session.invoke("lookup_upstream", _a2_lookup(producer))["binding"]["attempt"] == 1
    with pytest.raises(ValueError, match="stale_binding"):
        _ = old.access_manifest


@pytest.mark.parametrize("variant", ["absent", "blocked", "unauthorized"])
def test_a2_real_begin_keeps_required_edges_and_cp0_gate(tmp_path, variant):
    store, _, _, _, _ = _a2_session(tmp_path)
    snapshot = store.read()
    heads = list(snapshot.heads)
    if variant == "absent": heads = [h for h in heads if h.module_id != "CP-1"]
    elif variant == "blocked": heads = [h.model_copy(update={"status": "blocked"}) if h.module_id == "CP-1" else h for h in heads]
    else: heads = [h.model_copy(update={"commands": ()}) if h.module_id == "CP-0" else h for h in heads]
    store._write(snapshot.model_copy(update={"attempts": (), "heads": tuple(heads)}))
    with pytest.raises(ValueError):
        store.begin("CP-1B")


@pytest.mark.parametrize("attribute,value", [("run_id", "other-run"), ("issuer_id", "other-issuer"), ("as_of", date(2024, 12, 31))])
def test_a2_foreign_bound_module_cannot_disclose(tmp_path, attribute, value):
    producer = _a2_producer().model_copy(update={attribute: value})
    store, attempt, _, _ = _execution(tmp_path, producer=producer, consumer="CP-1B")
    with pytest.raises(ValueError, match="identity_mismatch"):
        _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=_a2_grants(producer))


def test_a2_tampered_current_blob_and_duplicate_current_identity_refuse(tmp_path):
    store, _, producer, _, session = _a2_session(tmp_path)
    (store.directory / "blobs" / producer.content_hash()).write_text("UPSTREAM_PRIVATE_QUOTE_SENTINEL")
    _assert_refused(session.invoke("lookup_upstream", _a2_lookup(producer)), "identity_mismatch")
    producer = _a2_producer()
    grants = _a2_grants(producer)
    producer = producer.model_copy(update={"facts": (*producer.facts, producer.facts[0])})
    grants["producers"][0]["sha256"] = producer.content_hash()
    store, attempt, _, _ = _execution(tmp_path / "duplicate", producer=producer, consumer="CP-1B")
    with pytest.raises(ValueError, match="identity_mismatch"):
        _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)


def test_a2_cursor_is_session_bound_and_commit_is_staged(tmp_path, monkeypatch):
    store, attempt, _, grants, session = _a2_session(tmp_path)
    token = _a2_page(session)["body"]["next_cursor"]
    other = _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)
    _assert_refused(_a2_page(other, cursor=token), "stale_binding")
    header = other.access_manifest
    args = dict(producer_module_id="CP-1", producer_sha256=header["producer"]["sha256"],
                manifest_sha256=header["manifest_sha256"], cursor=None, limit=20)
    original = other._manifest_page
    def page_then_change(supplied):
        page = original(supplied)
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return page
    monkeypatch.setattr(other, "_manifest_page", page_then_change)
    _assert_refused(other.invoke("read_access_manifest", args), "stale_binding")
    assert other._cursors == {} and other.receipts[-1]["body"] is None


@pytest.mark.parametrize("operation", ["lookup", "verify", "page", "property"])
def test_a2_mid_projection_changes_never_expose_provisional_data(tmp_path, monkeypatch, operation):
    from deploy_workflow.tools import upstream
    store, _, producer, _, session = _a2_session(tmp_path)
    header = session.access_manifest
    def change():
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
    if operation == "property":
        original = upstream._canonical
        def encode_then_change(value):
            encoded = original(value)
            if isinstance(value, dict) and value.get("schema_version") == "cp1b-access-manifest/1": change()
            return encoded
        monkeypatch.setattr(upstream, "_canonical", encode_then_change)
        with pytest.raises(ValueError, match="stale_binding"):
            _ = session.access_manifest
        return
    method = "_lookup" if operation == "lookup" else "_verify" if operation == "verify" else "_manifest_page"
    original = getattr(session, method)
    def build_then_change(*args):
        result = original(*args)
        change()
        return result
    monkeypatch.setattr(session, method, build_then_change)
    if operation == "lookup": tool, args = "lookup_upstream", _a2_lookup(producer)
    elif operation == "verify": tool, args = "verify_upstream", _verify(producer, "citations", [producer.facts[0].fact_id])
    else: tool, args = "read_access_manifest", dict(producer_module_id="CP-1", producer_sha256=producer.content_hash(), manifest_sha256=header["manifest_sha256"], cursor=None, limit=20)
    _assert_refused(session.invoke(tool, args), "stale_binding")
    assert session._cursors == {}


def test_a2_reentrant_property_and_invocation_are_atomic(tmp_path, monkeypatch):
    _, _, producer, _, session = _a2_session(tmp_path)
    original = session._lookup
    nested = []
    def reenter(*args):
        with pytest.raises(ValueError, match="not_permitted"):
            _ = session.access_manifest
        nested.append(session.invoke("lookup_upstream", _a2_lookup(producer)))
        return original(*args)
    monkeypatch.setattr(session, "_lookup", reenter)
    assert session.invoke("lookup_upstream", _a2_lookup(producer))["status"] == "ok"
    _assert_refused(nested[0], "not_permitted")
    assert [r["sequence"] for r in session.receipts] == [1, 2]


def test_a2_manifest_failure_recovers_without_cursor_or_private_diagnostics(tmp_path, monkeypatch):
    session = _a2_session(tmp_path)[4]
    with monkeypatch.context() as patch:
        def fails(args): raise RuntimeError("UPSTREAM_PRIVATE_QUOTE_SENTINEL")
        patch.setattr(session, "_manifest_page", fails)
        result = _a2_page(session)
        assert result["status"] == "error" and result["error_code"] == "internal_error"
        assert result["body"] is None and "UPSTREAM_PRIVATE" not in json.dumps(result)
        assert session._cursors == {}
    assert _a2_page(session)["status"] == "ok"


@pytest.mark.parametrize("operation", ["property", "constructor"])
def test_a2_final_authenticated_module_read_rechecks_live_snapshot(tmp_path, monkeypatch, operation):
    store, attempt, _, grants, session = _a2_session(tmp_path)
    original = store.head_module
    reads = 0
    def authenticate_then_change(head):
        nonlocal reads
        result = original(head)
        if head.module_id == "CP-1":
            reads += 1
            if reads == 2:
                snapshot = store.read()
                store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return result
    monkeypatch.setattr(store, "head_module", authenticate_then_change)
    with pytest.raises(ValueError, match="^stale_binding$"):
        if operation == "property":
            _ = session.access_manifest
        else:
            _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)
    assert reads == 2


@pytest.mark.parametrize("status", ["missing", "conflicting", "not_applicable"])
def test_a2_all_nonknown_statuses_remain_visible(tmp_path, status):
    producer = _a2_producer()
    producer = producer.model_copy(update={"facts": tuple(f.model_copy(update={"status": status})
        if f.status == "missing" else f for f in producer.facts)})
    session = _a2_session(tmp_path, producer=producer)[4]
    result = session.invoke("lookup_upstream", _a2_lookup(producer, "total_leverage_reported"))
    assert result["status"] == "ok"
    gaps = [f for f in result["body"]["rows"][0]["facts"] if f["status"] != "known"]
    assert len(gaps) == 1 and gaps[0]["status"] == status and gaps[0]["amount"] is None
    assert gaps[0]["limitation"]


@pytest.mark.parametrize("variant", ["other-table", "trend", "rolling", "unknown-basis", "unknown-metric", "missing-companion"])
def test_a2_existing_actual_facts_outside_universe_stay_hidden(tmp_path, variant):
    producer = _a2_producer()
    target = next(f for f in producer.facts if f.table_id == "T4.10" and f.amount is not None)
    if variant == "other-table":
        extra = target.model_copy(update={"fact_id": "extra", "table_id": "T4.1"})
    elif variant in {"trend", "rolling", "unknown-basis"}:
        field = "field_2" if variant == "trend" else "model-basis:" + "d" * 64 if variant == "unknown-basis" else "rolling:value"
        extra = target.model_copy(update={"fact_id": "extra", "field": field})
    elif variant == "unknown-metric":
        producer = producer.model_copy(update={"facts": tuple(f.model_copy(update={"text": "operating_profit"})
            if f.row_id == "revenue" and f.field == "field_1" else f for f in producer.facts)})
        extra = None
    else: extra = None
    if extra is not None: producer = producer.model_copy(update={"facts": (*producer.facts, extra)})
    grants = _a2_grants(producer)
    if variant == "missing-companion":
        grants["producers"][0]["coordinates"] = [c for c in grants["producers"][0]["coordinates"]
            if not (c["table_id"] == "T4.10" and c["row_id"] == "revenue" and c["field"] == "field_0")]
    store, attempt, _, _ = _execution(tmp_path, producer=producer, consumer="CP-1B")
    with pytest.raises(ValueError, match="^not_permitted$"):
        _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)


def test_a2_shared_live_offline_submit_refuses_before_callback_and_journal(tmp_path):
    from deploy_vii.live.submission import submit_model_payload
    store, attempt, _, _, _ = _a2_session(tmp_path)
    before = store.read().content_hash()
    called = []
    with pytest.raises(ValueError, match="offline-only"):
        submit_model_payload(store, attempt.ticket_id, "earnings_delta", "invalid private payload",
                             on_normalised=lambda value: called.append(value))
    assert not called and store.read().content_hash() == before
