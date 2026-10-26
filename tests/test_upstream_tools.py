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
