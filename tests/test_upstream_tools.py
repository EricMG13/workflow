"""Task2 component cases pinned before implementation; never owner completion evidence."""

import copy
import hashlib
import importlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

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


# A2P additive projection components; no actual B1 participation is implied.
P_FIELDS = sorted([*A2_FIELDS, "denominator", "value_class", "calculation_status"])


def _projection_session(tmp_path, *, producer=None):
    producer = producer or _projection_producer15()
    producer = producer.model_copy(update={"facts": tuple(f.model_copy(update={
        "citations": (*f.citations, *f.citations) if len(f.citations) == 1 else f.citations})
        for f in producer.facts)})
    store, attempt, _, _ = _execution(tmp_path, producer=producer, consumer="CP-1B")
    grants = _a2_grants(producer)
    grants["producers"][0]["projected_fields"] = P_FIELDS.copy()
    session = _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)
    return store, attempt, producer, grants, session


def _projection_args(session, **changes):
    h = session.access_manifest
    return {"producer_module_id": "CP-1", "producer_sha256": h["producer"]["sha256"],
            "manifest_sha256": h["manifest_sha256"], "cursor": None, "limit": 20, **changes}


def _expected_projection_catalog(producer):
    facts = sorted(producer.facts, key=lambda f: (f.table_id, f.row_id, f.field, f.fact_id))
    return [{k: ([{"source_id": c.source_id, "source_sha256": c.source_sha256,
                  "locator": c.locator} for c in f.citations] if k == "citation_handles"
                 else f.model_dump(mode="json")[k]) for k in P_FIELDS} for f in facts]


def test_projection_complete_catalog_all19_order_status_and_duplicate_handles(tmp_path):
    _, _, producer, _, session = _projection_session(tmp_path, producer=_a2_producer())
    expected = _expected_projection_catalog(producer)
    seen, cursor = [], None
    while True:
        result = session.invoke("read_access_projection", _projection_args(session, cursor=cursor))
        assert result["status"] == "ok"
        body = result["body"]
        assert set(body) == {"producer", "projection", "grant_sha256", "manifest_sha256",
                             "coordinate_count", "offset", "entries", "next_cursor", "complete"}
        assert body["offset"] == len(seen) and body["coordinate_count"] == len(expected)
        assert body["projection"] == "granted_fact_projection"
        assert len(_a2_canonical(body)) <= 8192 and 1 <= len(body["entries"]) <= 20
        assert all(list(f) == P_FIELDS for f in body["entries"])
        seen.extend(body["entries"])
        assert result["source_evidence"] == dict(read=[], extracted=[], surfaced=[], searched=[])
        if body["complete"]:
            assert body["next_cursor"] is None
            break
        cursor = body["next_cursor"]
        assert cursor.startswith("projection-cursor:")
    assert seen == expected
    assert any(f["status"] == "missing" and f["amount"] is None and f["limitation"] for f in seen)
    assert any(f["status"] == "known" and f["amount"] == "0" for f in seen)
    assert all(len(f["citation_handles"]) == 2 and f["citation_handles"][0] == f["citation_handles"][1] for f in seen)
    assert "quote\"" not in json.dumps(seen)


def test_projection_maximal_utf8_escaped_prefix_includes_own_terminal_wrapper(tmp_path):
    producer = _a2_producer(page25=True)
    producer = producer.model_copy(update={"facts": tuple(f.model_copy(update={
        "label": '€"\\\n' * 80}) for f in producer.facts)})
    _, _, producer, _, session = _projection_session(tmp_path, producer=producer)
    catalog = _expected_projection_catalog(producer)
    cursor, offset = None, 0
    while offset < len(catalog):
        response = session.invoke("read_access_projection", _projection_args(session, cursor=cursor))
        assert response["status"] == "ok"
        body = response["body"]
        fitting = []
        for count in range(1, min(20, len(catalog) - offset) + 1):
            candidate = {**body, "entries": catalog[offset:offset + count],
                         "complete": offset + count == len(catalog),
                         "next_cursor": None if offset + count == len(catalog) else "projection-cursor:" + "0" * 64}
            if len(_a2_canonical(candidate)) <= 8192: fitting.append(count)
        assert len(body["entries"]) == max(fitting) < 20
        assert body["entries"] == catalog[offset:offset + max(fitting)]
        offset += len(body["entries"])
        cursor = body["next_cursor"]
        assert body["complete"] is (offset == len(catalog))


def test_projection_replay_cross_namespace_and_detached_authority(tmp_path):
    store, attempt, producer, grants, session = _projection_session(tmp_path)
    manifest_token = _a2_page(session, limit=1)["body"]["next_cursor"]
    _assert_refused(session.invoke("read_access_projection", _projection_args(session, cursor=manifest_token)), "stale_binding")
    first = session.invoke("read_access_projection", _projection_args(session, limit=1))
    token = first["body"]["next_cursor"]
    _assert_refused(_a2_page(session, cursor=token), "bad_arguments")
    args = _projection_args(session, cursor=token, limit=2)
    second = session.invoke("read_access_projection", args)
    replay = session.invoke("read_access_projection", args)
    assert _a2_canonical(second["body"]) == _a2_canonical(replay["body"])
    assert second["call_id"] != replay["call_id"] and second["sequence"] < replay["sequence"]
    other = _tools().from_execution(store, attempt.ticket_id, "earnings_delta", grants=grants)
    _assert_refused(other.invoke("read_access_projection", _projection_args(other, cursor=token)), "stale_binding")
    grants["producers"][0]["coordinates"].clear()
    first["body"]["entries"].clear()
    assert session.invoke("read_access_projection", _projection_args(session, limit=1))["body"]["entries"] == _expected_projection_catalog(producer)[:1]
    assert second["body"]["offset"] == 1 and len(second["body"]["entries"]) == 2
    assert session._cursors and session._projection_cursors
    assert not set(session._cursors) & set(session._projection_cursors)


@pytest.mark.parametrize("changes,code", [
    ({"limit": True}, "bad_arguments"), ({"limit": 0}, "bad_arguments"),
    ({"limit": 21}, "bad_arguments"), ({"fields": ["amount"]}, "bad_arguments"),
    ({"coordinates": []}, "bad_arguments"), ({"manifest_sha256": "bad"}, "bad_arguments"),
    ({"manifest_sha256": "f" * 64}, "identity_mismatch"),
    ({"producer_sha256": "f" * 64}, "identity_mismatch"),
    ({"cursor": "projection-cursor:" + "a" * 64}, "stale_binding"),
    ({"cursor": "projection-cursor:no"}, "bad_arguments"),
])
def test_projection_exact_arguments_refuse_atomically(tmp_path, changes, code):
    session = _projection_session(tmp_path)[4]
    _assert_refused(session.invoke("read_access_projection", _projection_args(session, **changes)), code)


def test_projection_v1_and_cp5_never_gain_new_capability(tmp_path):
    for consumer in ("CP-2", "CP-5"):
        store, attempt, step, producer = _execution(tmp_path / consumer, consumer=consumer)
        grants = copy.deepcopy(GRANTS)
        if consumer == "CP-2": grants["row_ids"] = ["revenue", "operating_profit"]
        session = _session(store, attempt, step, grants)
        _assert_refused(session.invoke("read_access_projection", dict(producer_module_id="CP-1", producer_sha256=producer.content_hash(), manifest_sha256="0" * 64, cursor=None, limit=20)), "not_permitted")


def test_projection_indivisible_record_refuses_without_cursor_or_lock_loss(tmp_path):
    producer = _a2_producer(page25=True)
    producer = producer.model_copy(update={"facts": tuple(f.model_copy(update={"label": "€" * 4000}) for f in producer.facts)})
    session = _projection_session(tmp_path, producer=producer)[4]
    earlier = _a2_page(session, limit=1)
    _assert_refused(session.invoke("read_access_projection", _projection_args(session)), "bad_arguments")
    assert session._projection_cursors == {} and session.receipts[0] == earlier
    assert _a2_page(session)["status"] == "ok"


@pytest.mark.parametrize("variant,code", [("snapshot", "stale_binding"), ("blob", "identity_mismatch")])
def test_projection_final_currentness_prevents_provisional_cursor(tmp_path, monkeypatch, variant, code):
    store, _, producer, _, session = _projection_session(tmp_path)
    args = _projection_args(session)
    original = session._projection_page
    def project_then_change(supplied, current):
        result = original(supplied, current)
        if variant == "blob": (store.directory / "blobs" / producer.content_hash()).write_text("private tamper")
        else:
            snapshot = store.read()
            store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return result
    monkeypatch.setattr(session, "_projection_page", project_then_change)
    _assert_refused(session.invoke("read_access_projection", args), code)
    assert session._projection_cursors == {}


@pytest.mark.parametrize("seam", ["serialize", "append"])
def test_projection_one_shot_retention_failure_retains_only_safe_error(tmp_path, monkeypatch, seam):
    from deploy_workflow.tools import upstream
    session = _projection_session(tmp_path)[4]
    earlier = session.invoke("read_access_projection", _projection_args(session, limit=1))
    previous_tokens = session._projection_cursors.copy()
    if seam == "serialize":
        original = upstream.json.dumps
        failed = False
        def fail_once(value, *args, **kwargs):
            nonlocal failed
            if isinstance(value, dict) and value.get("tool") == "read_access_projection" and not failed:
                failed = True
                raise RuntimeError("PRIVATE_RETENTION_SENTINEL")
            return original(value, *args, **kwargs)
        monkeypatch.setattr(upstream.json, "dumps", fail_once)
    else:
        class FailOnce(list):
            failed = False
            def append(self, value):
                if not self.failed:
                    self.failed = True
                    raise RuntimeError("PRIVATE_RETENTION_SENTINEL")
                super().append(value)
        monkeypatch.setattr(session, "_receipts", FailOnce(session._receipts))
    failed = session.invoke("read_access_projection", _projection_args(session, limit=2))
    assert failed["status"] == "error" and failed["error_code"] == "internal_error" and failed["body"] is None
    assert "PRIVATE_RETENTION" not in json.dumps(failed)
    assert session._projection_cursors == previous_tokens and session.receipts[0] == earlier
    assert session.receipts[-1] == failed
    assert session.invoke("read_access_projection", _projection_args(session, limit=2))["status"] == "ok"


def test_projection_permanent_retention_failure_is_visible_and_no_cursor(tmp_path, monkeypatch):
    session = _projection_session(tmp_path)[4]
    args = _projection_args(session)
    class NeverRetain(list):
        def append(self, value): raise RuntimeError("PRIVATE_RETENTION_SENTINEL")
    with monkeypatch.context() as patch:
        patch.setattr(session, "_receipts", NeverRetain())
        with pytest.raises(ValueError, match="^internal_error$"):
            session.invoke("read_access_projection", args)
        assert session._projection_cursors == {} and session.receipts == ()
    assert session.invoke("read_access_projection", args)["status"] == "ok"


def _projection_producer15():
    """Literal permission fixture: two15-field period rows, not actual issuer evidence."""
    producer = _a2_producer(page25=True)
    facts = [f for f in producer.facts if f.field != "basis_note"]
    for pid in ("q3-2025", "q4-2025"):
        sample = next(f for f in facts if f.table_id == "T4.14" and f.row_id == pid)
        for key, text in dict(day_count="92", audit_status="UNAUDITED", source_id="upstream-note",
                              source_locator="line:1", component_period_ids=None).items():
            facts.append(sample.model_copy(update=dict(fact_id=f"period-{pid}-{key}", field=key,
                label=key, text=text, status="not_applicable" if text is None else "known",
                limitation="No component periods" if text is None else None)))
    return producer.model_copy(update={"facts": tuple(facts)})


def test_projection_literal15_fact_rows_preserve_distinct_and_duplicate_handles(tmp_path):
    producer = _projection_producer15()
    target = producer.facts[0]
    distinct = target.citations[0].model_copy(update={"locator": "line:2"})
    producer = producer.model_copy(update={"facts": (target.model_copy(update={
        "citations": (*target.citations, distinct)}), *producer.facts[1:])})
    _, _, producer, _, session = _projection_session(tmp_path, producer=producer)
    expected = _expected_projection_catalog(producer)
    seen, cursor = [], None
    while True:
        result = session.invoke("read_access_projection", _projection_args(session, cursor=cursor))
        assert result["status"] == "ok"
        seen.extend(result["body"]["entries"])
        if result["body"]["complete"]: break
        cursor = result["body"]["next_cursor"]
    assert seen == expected
    for pid in ("q3-2025", "q4-2025"):
        assert sum(f["table_id"] == "T4.14" and f["row_id"] == pid for f in seen) == 15
    handles = next(f["citation_handles"] for f in seen if f["fact_id"] == target.fact_id)
    assert len(handles) == 2 and handles[0] != handles[1]


def test_projection_snapshot_change_during_receipt_encoding_cannot_publish_success(tmp_path, monkeypatch):
    from deploy_workflow.tools import upstream
    store, _, _, _, session = _projection_session(tmp_path)
    args = _projection_args(session)
    original = upstream.json.dumps
    changed = False
    def encode_then_change(value, *positional, **kwargs):
        nonlocal changed
        encoded = original(value, *positional, **kwargs)
        if isinstance(value, dict) and value.get("tool") == "read_access_projection" and not changed:
            changed = True
            snapshot = store.read()
            store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return encoded
    monkeypatch.setattr(upstream.json, "dumps", encode_then_change)
    failed = session.invoke("read_access_projection", args)
    _assert_refused(failed, "stale_binding")
    assert session._projection_cursors == {} and session.receipts[-1] == failed


@pytest.mark.parametrize("seam", ["projection", "retention"])
def test_projection_control_interrupt_releases_writer_without_usable_cursor(tmp_path, monkeypatch, seam):
    session = _projection_session(tmp_path)[4]
    args = _projection_args(session)
    with monkeypatch.context() as patch:
        if seam == "projection":
            def interrupt(*args): raise KeyboardInterrupt()
            patch.setattr(session, "_projection_page", interrupt)
        else:
            class Interrupt(list):
                def append(self, value): raise KeyboardInterrupt()
            patch.setattr(session, "_receipts", Interrupt())
        with pytest.raises(KeyboardInterrupt):
            session.invoke("read_access_projection", args)
        assert session._projection_cursors == {}
    assert session.invoke("read_access_projection", args)["status"] == "ok"


def test_projection_postappend_failure_hides_provisional_receipt_before_unlock(tmp_path, monkeypatch):
    """Observe immediately on unlock; retain an unrelated reentrant refusal too."""
    session = _projection_session(tmp_path)[4]
    args = _projection_args(session, limit=2)
    earlier = session.invoke("read_access_projection", _projection_args(session, limit=1))
    before_tokens = session._projection_cursors.copy()
    observed, unrelated = [], []
    lock = session._receipt_lock
    class FailOnceAfterAppend(list):
        failed = False
        def append(self, value):
            super().append(value)
            if not self.failed:
                self.failed = True
                raise RuntimeError("PRIVATE_RETENTION_SENTINEL")
    class ObserveUnlock:
        def __enter__(self):
            lock.acquire()
            return self
        def __exit__(self, kind, value, traceback):
            lock.release()
            if kind is RuntimeError:
                observed.extend(session.receipts)
                unrelated.append(session.invoke("read_access_projection", args))
            return False
    monkeypatch.setattr(session, "_receipts", FailOnceAfterAppend(session._receipts))
    monkeypatch.setattr(session, "_receipt_lock", ObserveUnlock())
    failed = session.invoke("read_access_projection", args)
    assert failed["status"] == "error" and failed["body"] is None
    assert observed == [earlier]  # No provisional success was visible when the lock released.
    _assert_refused(unrelated[0], "not_permitted")
    assert session.receipts == (earlier, failed, unrelated[0])
    assert session._projection_cursors == before_tokens


@pytest.mark.parametrize("seam", ["uuid", "binding-copy"])
def test_projection_receipt_initialization_failure_is_sanitized_without_fake_id(tmp_path, monkeypatch, seam):
    from deploy_workflow.tools import upstream
    session = _projection_session(tmp_path)[4]
    args = _projection_args(session)
    fired = False
    if seam == "uuid":
        original = upstream.uuid4
        def fail_once():
            nonlocal fired
            if not fired:
                fired = True
                raise OSError("PRIVATE_INIT_SENTINEL")
            return original()
        monkeypatch.setattr(upstream, "uuid4", fail_once)
    else:
        original = upstream.copy.deepcopy
        def fail_once(value, *positional, **kwargs):
            nonlocal fired
            if value is session._binding and not fired:
                fired = True
                raise OSError("PRIVATE_INIT_SENTINEL")
            return original(value, *positional, **kwargs)
        monkeypatch.setattr(upstream.copy, "deepcopy", fail_once)
    with pytest.raises(ValueError, match="^internal_error$"):
        session.invoke("read_access_projection", args)
    assert fired and session.receipts == () and session._projection_cursors == {}
    assert session.invoke("read_access_projection", args)["status"] == "ok"


# A4 CP5-v2 causal component expectations originate in the independently frozen
# integrity oracle. These seeded heads prove transport/core mechanics only.
def _integrity_execution(tmp_path, mutation=None, extras=(), transform=None):
    from pathlib import Path

    oracle = json.loads((Path(__file__).parents[1] / 'cases/integrity/expected.json').read_text())
    fixture = copy.deepcopy(oracle['literal_component_fixture'])
    data = fixture['producers']
    if mutation == 'bad_fact_quote':
        data[0]['facts'][0]['citations'][0]['quote'] = 'PRIVATE_QUOTE_SENTINEL'
    elif mutation == 'bad_claim_quote':
        data[0]['claims'][0]['citations'][0]['quote'] = 'PRIVATE_QUOTE_SENTINEL'
    elif mutation == 'bad_scale':
        data[0]['facts'][0]['scale'] = '1'
    elif mutation == 'unresolved_claim':
        data[0]['claims'][0]['text'] = 'Revenue observation [unknown.fact].'
    elif mutation in {'unsettled_unlimited', 'unsettled_limited'}:
        data[0]['facts'][0].update(amount=None, status='missing', limitation='Not supplied')
        data[0]['claims'][0]['text'] = 'Revenue observation [fin.rev].'
        if mutation == 'unsettled_limited':
            data[0]['claims'][0]['limitation'] = 'Observation is unavailable within this scope.'
    elif mutation == 'identity_twice':
        fact = copy.deepcopy(data[0]['facts'][0])
        fact['amount'] = '1'
        data[1]['facts'].append(fact)
    elif mutation == 'blocked':
        data[1]['status'] = 'blocked'
        data[1]['limitations'] = ['PRIVATE_BLOCKED_LIMITATION']
    if transform is not None:
        transform(data)
    run = Run(run_id='integrity-component', issuer_id='component', issuer_name='Component',
              as_of=date(2025, 12, 31), case_kind='synthetic',
              requested_modules=('CP-1B', 'CP-5', *(h.module_id for h in extras)))
    source = fixture['source']
    assert hashlib.sha256(source['text'].encode()).hexdigest() == source['sha256']
    pack = PreparedPack(run=run, sources=(Source(
        source_id=source['source_id'], name='Component note', status='ready',
        sha256=source['sha256'], spans=(Span(locator=source['locator'], text=source['text']),)),))
    store = Execution.create(tmp_path / 'integrity', pack)
    heads = [Module(run_id=run.run_id, issuer_id=run.issuer_id, as_of=run.as_of,
                    module_id='CP-0', status='accepted', facts=(Fact(
                        fact_id='run-cp5', label='Run integrity', table_id='T8', row_id='CP-5',
                        field='exact_command', text='Run CP-5'),))]
    for datum in data:
        heads.append(Module.model_validate_json(json.dumps({
            'run_id': run.run_id, 'issuer_id': run.issuer_id, 'as_of': run.as_of.isoformat(),
            **datum})))
    heads.extend(extras)
    for head in heads:
        store._store(head.model_dump_json())
    store._write(store.read().model_copy(update={'heads': tuple(map(head_of, heads))}))
    attempt = store.begin('CP-5')
    return store, attempt, heads[1:], fixture


def _integrity_grant(store, attempt):
    from pathlib import Path

    from deploy_vii import cp5_integrity

    wire = json.loads((Path(__file__).parents[1] / 'cases/integrity/expected.json').read_text())['wire_types']
    projected_fields = wire['FactAttribute'].split('|')
    scope = cp5_integrity.review_scope(store, attempt)
    return {
        'schema_version': 'cp5-upstream-grant/2', 'consumer_module_id': 'CP-5',
        'step_id': 'integrity_review',
        'bound_inputs': [item.model_dump(mode='json') for item in attempt.inputs],
        'producers': [{
            'module_id': item.input_id, 'sha256': item.sha256, 'status': item.status,
            'role': 'blocked' if item.status == 'blocked' else 'evaluated',
            'fact_coordinates': [] if item.status == 'blocked' else [{
                key: getattr(fact, key) for key in ('fact_id', 'table_id', 'row_id', 'field')
            } for fact in head.facts],
            'claim_ids': [] if item.status == 'blocked' else [c.claim_id for c in head.claims],
            'claim_citation_refs': [] if item.status == 'blocked' else [
                cp5_integrity.citation_ref(c.claim_id, n)
                for c in head.claims for n in range(1, len(c.citations) + 1)],
            'projected_fact_fields': sorted(projected_fields),
        } for item, head in scope.heads],
        'raw_source_ids': [],
        'internal_scope_inspection': 'complete_bound_scope_for_existing_python_checks_only',
    }


def _integrity_session(store, attempt, grants=None):
    return _tools().from_execution(store, attempt.ticket_id, 'integrity_review',
                                   grants=_integrity_grant(store, attempt) if grants is None else grants)


def _integrity_pages(session, section, limit=20):
    manifest = session.integrity_manifest
    cursor, entries, pages = None, [], []
    while True:
        receipt = session.invoke('read_integrity_scope', {
            'scope_sha256': manifest['scope_sha256'], 'section': section,
            'cursor': cursor, 'limit': limit})
        assert receipt['status'] == 'ok', receipt
        body = receipt['body']
        assert len(json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()) <= 8192
        assert body['offset'] == len(entries)
        assert body['grant_sha256'] == manifest['grant_sha256']
        assert body['manifest_sha256'] == manifest['manifest_sha256']
        entries.extend(body['entries'])
        pages.append(receipt)
        if body['complete']:
            assert body['next_cursor'] is None
            assert len(entries) == body['total']
            return entries, pages
        assert body['entries']
        cursor = body['next_cursor']


def test_integrity_v2_complete_two_producers_zero_and_qualified_claims(tmp_path):
    store, attempt, heads, fixture = _integrity_execution(tmp_path)
    before = store.read().content_hash()
    session = _integrity_session(store, attempt)
    manifest = session.integrity_manifest
    assert manifest['producer_count'] == manifest['evaluated_count'] == 2
    assert manifest['fact_count'] == manifest['claim_count'] == manifest['claim_citation_count'] == 2
    assert len(manifest['sections']) == 16
    evidence, _ = _integrity_pages(session, 'required_evidence')
    assert len(evidence) == 2
    assert [x['fact']['amount'] for x in evidence] == ['0', '0']
    assert all(x['fact']['citation_handles']['count'] == 1 for x in evidence)
    assert all(x['fact']['fact_sha256'] == heads[n].facts[0].content_hash()
               for n, x in enumerate(evidence))
    claims, _ = _integrity_pages(session, 'claims')
    assert [x['claim_id'] for x in claims] == ['summary', 'summary']
    assert [x['producer']['module_id'] for x in claims] == ['CP-1', 'CP-1B']
    for section in (x['section'] for x in manifest['sections']):
        _integrity_pages(session, section)
    verify = session.invoke('verify_integrity_scope', {'scope_sha256': manifest['scope_sha256']})
    assert verify['status'] == 'ok'
    assert verify['body']['category_counts'] == fixture['expected']['mechanical_counts']
    assert verify['body']['mechanical_verdict'] == 'clean'
    assert store.read().content_hash() == before
    serialized = json.dumps(session.receipts)
    assert 'Component revenue zero.' not in serialized
    assert 'quote' not in serialized
    assert all(r['source_evidence'] == {'read': [], 'extracted': [], 'surfaced': [], 'searched': []}
               for r in session.receipts)


@pytest.mark.parametrize('mutation', [
    'bad_fact_quote', 'bad_claim_quote', 'bad_scale', 'unresolved_claim',
    'unsettled_unlimited', 'unsettled_limited', 'identity_twice', 'blocked',
])
def test_integrity_v2_causal_mechanical_categories(tmp_path, mutation):
    store, attempt, _, fixture = _integrity_execution(tmp_path, mutation)
    session = _integrity_session(store, attempt)
    expected = next(x for x in fixture['causal_mutations'] if x['id'] == mutation)
    response = session.invoke('verify_integrity_scope', {
        'scope_sha256': session.integrity_manifest['scope_sha256']})
    assert response['status'] == 'ok', response
    assert response['body']['category_counts'] == expected['expected_counts']
    findings, _ = _integrity_pages(session, 'findings')
    assert len(findings) == sum(expected['expected_counts'].values())
    nonzero = {code: count for code, count in expected['expected_counts'].items() if count}
    assert {code: sum(x['code'] == code for x in findings) for code in {x['code'] for x in findings}} == nonzero
    evidence, _ = _integrity_pages(session, 'required_evidence')
    if mutation.startswith('unsettled'):
        assert evidence[0]['fact']['amount'] is None
        unsettled, _ = _integrity_pages(session, 'unsettled')
        assert unsettled[0]['limited'] is expected['limited']
    if mutation == 'identity_twice':
        groups, _ = _integrity_pages(session, 'identity_groups')
        assert len(groups) == 2
        assert all(g['differing'] == ['value'] for g in groups)
        assert all(len(g['members']) == 2 for g in groups)
    assert 'PRIVATE_QUOTE_SENTINEL' not in json.dumps(session.receipts)
    assert 'PRIVATE_BLOCKED_LIMITATION' not in json.dumps(session.receipts)
    assert 'detail' not in json.dumps(findings)


@pytest.mark.parametrize('part', ['producers', 'fact_coordinates', 'claim_ids', 'claim_citation_refs'])
def test_integrity_v2_incomplete_grant_never_discloses(tmp_path, part):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    grant = _integrity_grant(store, attempt)
    if part == 'producers':
        grant[part].pop()
    else:
        grant['producers'][0][part].pop()
    with pytest.raises(ValueError, match='^not_permitted$'):
        _integrity_session(store, attempt, grant)


@pytest.mark.parametrize('part', ['fact_coordinates', 'claim_ids', 'claim_citation_refs', 'projected_fact_fields'])
def test_integrity_v2_duplicate_grant_is_bad_arguments(tmp_path, part):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    grant = _integrity_grant(store, attempt)
    grant['producers'][0][part].append(copy.deepcopy(grant['producers'][0][part][0]))
    with pytest.raises(ValueError, match='^bad_arguments$'):
        _integrity_session(store, attempt, grant)


@pytest.mark.parametrize('tool,args', [
    ('read_access_projection', {}), ('read_access_manifest', {}), ('read_source', {}),
    ('verify_upstream', {'kind': 'integrity'}),
])
def test_integrity_v2_denies_other_surfaces(tmp_path, tool, args):
    store, attempt, heads, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    if tool == 'verify_upstream':
        args = {'producer_module_id': 'CP-1', 'producer_sha256': heads[0].content_hash(),
                'kind': 'integrity', 'fact_ids': ['fin.rev']}
    _assert_refused(session.invoke(tool, args), 'not_permitted')


def test_integrity_v2_foreign_cursor_empty_section_and_replay(tmp_path):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    claims, pages = _integrity_pages(session, 'claims', 1)
    first = pages[0]['body']
    args = {'scope_sha256': session.integrity_manifest['scope_sha256'],
            'section': 'claims', 'cursor': first['next_cursor'], 'limit': 1}
    assert session.invoke('read_integrity_scope', args)['body'] == pages[1]['body']
    args['section'] = 'producers'
    _assert_refused(session.invoke('read_integrity_scope', args), 'stale_binding')
    args['cursor'] = 'integrity-cursor:' + 'a' * 64
    _assert_refused(session.invoke('read_integrity_scope', args), 'stale_binding')
    args['cursor'] = 'bad'
    _assert_refused(session.invoke('read_integrity_scope', args), 'bad_arguments')
    empty, empty_pages = _integrity_pages(session, 'findings')
    assert empty == [] and len(empty_pages) == 1
    assert empty_pages[0]['body']['offset'] == 0
    assert empty_pages[0]['body']['complete'] is True
    assert len(claims) == 2


def test_integrity_v2_final_recheck_discards_body_and_cursor(tmp_path, monkeypatch):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    manifest = session.integrity_manifest
    original = session._scope_page
    def race(args):
        result = original(args)
        store._write(store.read().model_copy(update={'heads': ()}))
        return result
    monkeypatch.setattr(session, '_scope_page', race)
    _assert_refused(session.invoke('read_integrity_scope', {
        'scope_sha256': manifest['scope_sha256'], 'section': 'claims',
        'cursor': None, 'limit': 1}), 'stale_binding')
    assert session._integrity_cursors == {}
    assert session.receipts[-1]['body'] is None


def test_integrity_v2_dynamic_model_is_mandatory_and_not_pooled(tmp_path):
    extra = Module(run_id='integrity-component', issuer_id='component', as_of=date(2025, 12, 31),
                   module_id='CP-MODEL', status='accepted', facts=(Fact(
                       fact_id='fin.rev', label='Model observation', amount=Decimal(0),
                       unit='MILLIONS', scale=Decimal(1000000), period='Q4 2025'),))
    store, attempt, _, _ = _integrity_execution(tmp_path, extras=(extra,))
    session = _integrity_session(store, attempt)
    assert session.integrity_manifest['evaluated_count'] == 3
    producers, _ = _integrity_pages(session, 'producers')
    assert {p['producer']['module_id'] for p in producers} == {'CP-1', 'CP-1B', 'CP-MODEL'}
    groups, _ = _integrity_pages(session, 'identity_groups')
    assert len(groups) == 1
    assert {r['producer_module_id'] for r in groups[0]['members']} == {'CP-1', 'CP-MODEL'}
    grant = _integrity_grant(store, attempt)
    grant['producers'] = [p for p in grant['producers'] if p['module_id'] != 'CP-MODEL']
    with pytest.raises(ValueError, match='^not_permitted$'):
        _integrity_session(store, attempt, grant)


def test_integrity_v2_unicode_maximal_prefix_and_oversize_atomic(tmp_path):
    def transform(data):
        data[0]['claims'] = [{'claim_id': f'claim{n:02}', 'text': 'Observation ' + '界' * 330 + '.',
                             'citations': [], 'limitation': None} for n in range(25)]
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=transform)
    session = _integrity_session(store, attempt)
    claims, pages = _integrity_pages(session, 'claims')
    assert len(claims) == 26 and len(pages) > 2
    for page in pages[:-1]:
        body = copy.deepcopy(page['body'])
        end = body['offset'] + len(body['entries'])
        body['entries'].append(claims[end])
        body['complete'] = end + 1 == len(claims)
        body['next_cursor'] = None if body['complete'] else 'integrity-cursor:' + '0' * 64
        assert len(json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()) > 8192
    def huge(data):
        data[0]['claims'][0]['text'] = 'Observation ' + '界' * 4000 + '.'
    other, ticket, _, _ = _integrity_execution(tmp_path / 'huge', transform=huge)
    large = _integrity_session(other, ticket)
    _assert_refused(large.invoke('read_integrity_scope', {
        'scope_sha256': large.integrity_manifest['scope_sha256'], 'section': 'claims',
        'cursor': None, 'limit': 20}), 'bad_arguments')
    assert large._integrity_cursors == {}


def test_integrity_v2_preserves_unreferenced_flagged_fact_and_calculation_alias(tmp_path):
    def transform(data):
        data[0]['facts'][0]['calculation_id'] = 'calc.rev'
        data[0]['claims'][0]['text'] = 'Revenue observation {calc.rev|MILLIONS}.'
        unreferenced = copy.deepcopy(data[0]['facts'][0])
        unreferenced.update(fact_id='unreferenced', row_id='unreferenced', calculation_id=None, scale='1')
        data[0]['facts'].append(unreferenced)
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=transform)
    session = _integrity_session(store, attempt)
    evidence, _ = _integrity_pages(session, 'required_evidence')
    by_id = {e['fact']['fact_id']: e for e in evidence}
    assert by_id['fin.rev']['reasons'] == ['claim_reference']
    assert by_id['fin.rev']['claim_ids'] == ['summary']
    assert by_id['unreferenced']['reasons'] == ['flagged_fact']
    assert by_id['unreferenced']['claim_ids'] == []


def test_integrity_v2_lookup_safe_citation_verification_and_hash_refusal(tmp_path):
    store, attempt, heads, _ = _integrity_execution(tmp_path, 'bad_fact_quote')
    session = _integrity_session(store, attempt)
    args = {'producer_module_id': 'CP-1', 'producer_sha256': heads[0].content_hash(),
            'table_id': 'T4.10', 'row_ids': ['revenue'],
            'fields': ['fact_id', 'table_id', 'row_id', 'field', 'status', 'amount', 'citation_handles']}
    receipt = session.invoke('lookup_upstream', args)
    assert receipt['status'] == 'ok', receipt
    assert receipt['body']['projection'] == 'safe_scope_fact_projection'
    assert receipt['body']['rows'][0]['facts'][0]['amount'] == '0'
    assert receipt['body']['rows'][0]['facts'][0]['fact_sha256'] == heads[0].facts[0].content_hash()
    args['fields'].append('quote')
    _assert_refused(session.invoke('lookup_upstream', args), 'not_permitted')
    args['producer_sha256'] = '0' * 64
    _assert_refused(session.invoke('lookup_upstream', args), 'identity_mismatch')
    result = session.invoke('verify_upstream', {'producer_module_id': 'CP-1',
        'producer_sha256': heads[0].content_hash(), 'kind': 'citations', 'fact_ids': ['fin.rev']})
    assert result['body']['verdict'] == 'invalid' and result['body']['issue_count'] == 1
    assert 'PRIVATE_QUOTE_SENTINEL' not in json.dumps(session.receipts)


_PERIOD_FIELDS = ['period_id', 'period_type', 'fiscal_year', 'fiscal_quarter', 'start_date',
                  'end_date', 'currency', 'unit', 'accounting_basis', 'entity_perimeter']
_PERIOD_VALUES = {
    'q3-2025': ['q3-2025', 'QUARTER', '2025', 'Q3', '2025-07-01', '2025-09-30', 'USD',
                'MILLIONS', 'GAAP', 'consolidated'],
    'q4-2025': ['q4-2025', 'QUARTER', '2025', 'Q4', '2025-10-01', '2025-12-31', 'USD',
                'MILLIONS', 'GAAP', 'consolidated'],
}


def _model_basis(pid):
    """The frozen reference derivation (cp5-fixture-reference-contract.md, basis(pid))."""
    raw = ''.join(f'{len(x)}:{x}' for x in ['historical', 'Q:' + pid])
    return 'model-basis:' + hashlib.sha256(raw.encode()).hexdigest()


def _canonical_text(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _protected_component(data, prior=True, drop=()):
    """Handwritten structural envelopes; no financial engine or actual B1 claim.

    12 lineages x (2 primary refs + 21 ordered companions) derived from the canonical
    CP1 join (T4.14 period rows, T4.10 metric rows keyed by model-basis ids), duplicate
    primary citations, 44 owner identities. Large original basis and bundle stay internal.
    Generic labels/units/layout test typed transport stress only; they do not qualify
    actual B1 measure selection, dimensions or frozen A3 layouts. With prior=False the
    CP1 genuinely lacks the prior period row and every prior-basis fact.
    """
    from pathlib import Path

    measure_order = json.loads((Path(__file__).parents[1] / 'cases/earnings/owner-expected.json').read_text())['lineage']['measure_order']
    cp1 = data[0]
    source_citation = copy.deepcopy(cp1['facts'][0]['citations'][0])
    source_basis = 'Component basis ' + 'scope ' * 180
    pids = ['q3-2025', 'q4-2025'] if prior else ['q4-2025']
    for pid in pids:
        for field, value in zip(_PERIOD_FIELDS, _PERIOD_VALUES[pid], strict=True):
            cp1['facts'].append({'fact_id': f'{pid}.{field}', 'label': 'Component period',
                                 'table_id': 'T4.14', 'row_id': pid, 'field': field,
                                 'text': value, 'status': 'known', 'period': pid})
    # First pin the complete full CP1 before any qualified lineage is constructed.
    for n, measure in enumerate(measure_order):
        cp1['facts'].append({'fact_id': f'metric{n:02}', 'label': 'Metric identity', 'table_id': 'T4.10',
                            'row_id': measure, 'field': 'field_1', 'text': measure})
        for role, pid in (('prior', 'q3-2025'), ('current', 'q4-2025')):
            if pid not in pids:
                continue
            cp1['facts'].append({'fact_id': f'{measure}.{role}', 'label': 'Component operand',
                'table_id': 'T4.10', 'row_id': measure, 'field': _model_basis(pid), 'amount': '0',
                'status': 'known', 'unit': 'MILLIONS', 'scale': '1000000', 'currency': 'USD',
                'period': pid, 'basis': source_basis,
                'citations': [copy.deepcopy(source_citation), copy.deepcopy(source_citation)]})
    cp1['facts'] = [f for f in cp1['facts'] if f['fact_id'] not in drop]
    source = Module.model_validate_json(json.dumps({
        'run_id': 'integrity-component', 'issuer_id': 'component', 'as_of': '2025-12-31', **cp1}))
    by_id = {f.fact_id: f for f in source.facts}
    def reference(fact):
        return {'producer_module_id': 'CP-1', 'producer_sha256': source.content_hash(),
                **{k: getattr(fact, k) for k in ('fact_id', 'table_id', 'row_id', 'field')}}
    points = []
    for n, measure in enumerate(measure_order):
        companions = [by_id[f'metric{n:02}']] + [
            by_id[f'{pid}.{field}'] for pid in pids for field in _PERIOD_FIELDS
            if f'{pid}.{field}' in by_id]
        point = {'measure_id': measure, 'prior': None,
                 'companions': [reference(f) for f in companions]}
        for role, pid in (('prior', 'q3-2025'), ('current', 'q4-2025')):
            if pid not in pids or f'{measure}.{role}' not in by_id:
                continue
            fact = by_id[f'{measure}.{role}']
            point[role] = {'fact': reference(fact), 'period_id': pid,
                           'basis_id': _model_basis(pid), 'source_period': fact.period,
                           'source_basis': fact.basis, 'fact_sha256': fact.content_hash(),
                           'citation_handles': [{k: getattr(c, k) for k in
                               ('source_id', 'source_sha256', 'locator')} for c in fact.citations]}
        points.append(point)
    bundle = {'producer_module_id': 'CP-1', 'producer_sha256': source.content_hash(),
              'prior_period_id': 'q3-2025', 'current_period_id': 'q4-2025',
              'prior_basis_id': _model_basis('q3-2025') if prior else None,
              'current_basis_id': _model_basis('q4-2025'), 'operands': points}
    _write_bundle(data, bundle)
    data[1]['claims'][0]['text'] = 'Delta observation {owner00|MILLIONS}.'


def _write_bundle(data, bundle):
    """Rewrite the CP1B evidence bundle and keep every owner basis a genuine lineage."""
    source_citation = copy.deepcopy(data[0]['facts'][0]['citations'][0])
    points = bundle['operands']
    data[1]['facts'] = [{
        'fact_id': f'owner{n:02}', 'label': 'Component owner', 'table_id': 'T1B.1',
        'row_id': f'owner{n:02}', 'field': 'delta', 'amount': '0', 'unit': 'MILLIONS',
        'scale': '1000000', 'currency': 'USD', 'period': 'current_period',
        'basis': _canonical_text(points[n % 12]),
        'citations': [copy.deepcopy(source_citation), copy.deepcopy(source_citation)],
    } for n in range(43)]
    data[1]['facts'].append({
        'fact_id': 'cp1b:T1B.3:evidence.inputs:assessment', 'label': 'Evidence inputs',
        'table_id': 'T1B.3', 'row_id': 'evidence.inputs', 'field': 'assessment',
        'text': _canonical_text(bundle)})


def test_integrity_v2_protected_large_lineage_is_complete_bounded_and_ordinal(tmp_path):
    store, attempt, heads, _ = _integrity_execution(tmp_path, transform=_protected_component)
    session = _integrity_session(store, attempt)
    bundle, _ = _integrity_pages(session, 'lineage_bundles')
    headers, _ = _integrity_pages(session, 'lineage_headers')
    operands, _ = _integrity_pages(session, 'lineage_operands')
    companions, _ = _integrity_pages(session, 'lineage_companions')
    citations, _ = _integrity_pages(session, 'lineage_citations')
    owner, _ = _integrity_pages(session, 'lineage_owner_facts')
    fact_cites, _ = _integrity_pages(session, 'fact_citations')
    evidence, _ = _integrity_pages(session, 'required_evidence')
    assert (len(bundle), len(headers), len(operands), len(companions), len(citations), len(owner)) == (1, 12, 24, 252, 48, 44)
    # 24 primaries + 12 metric identities + 20 distinct period fields (companions of the canonical
    # join) + original named CP1 + one named owner. (Was 47 when companions were shared stand-ins.)
    assert len(evidence) == 58
    assert bundle[0]['raw_bytes'] > 8192
    assert [r['ordinal'] for r in companions[:21]] == list(range(21))
    assert citations[0]['citation'] == citations[1]['citation']
    assert citations[0]['ordinal'] == 0 and citations[1]['ordinal'] == 1
    assert len([c for c in fact_cites if c['owner_fact']['ref'] == 'owner00']) == 2
    args = {'producer_module_id': 'CP-1B', 'producer_sha256': heads[1].content_hash(),
            'table_id': 'T1B.3', 'row_ids': ['evidence.inputs'],
            'fields': ['fact_id', 'table_id', 'row_id', 'field', 'status', 'text']}
    result = session.invoke('lookup_upstream', args)
    text = result['body']['rows'][0]['facts'][0]['text']
    assert text['kind'] == 'cp1b_evidence_bundle' and text['handle'] == bundle[0]['bundle_id']
    assert text['raw_sha256'] == hashlib.sha256(heads[1].facts[-1].text.encode()).hexdigest()
    assert '"operands"' not in json.dumps(result)


@pytest.mark.parametrize('mutation', ['extra', 'hash', 'coordinate', 'citation', 'missing', 'reordered'])
def test_integrity_v2_protected_payload_never_accepts_partial_or_nested_authority(tmp_path, mutation):
    def transform(data):
        _protected_component(data)
        bundle = json.loads(data[1]['facts'][-1]['text'])
        point = bundle['operands'][0]
        if mutation == 'extra':
            point['current']['fact']['quote'] = 'PRIVATE_NESTED_QUOTE'
        elif mutation == 'hash':
            point['current']['fact_sha256'] = '0' * 64
        elif mutation == 'coordinate':
            point['current']['fact']['row_id'] = 'other'
        elif mutation == 'citation':
            point['current']['citation_handles'].pop()
        elif mutation == 'missing':
            bundle['operands'].pop()
        else:
            bundle['operands'].reverse()
        data[1]['facts'][-1]['text'] = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=transform)
    with pytest.raises(ValueError, match='^not_permitted$'):
        _integrity_session(store, attempt)


# --- Fix round 1: canonical lineage authentication, parity, detachment, categories ----------
def _upstream_module():
    return importlib.import_module('deploy_workflow.tools.upstream')


def _lineage_transform(prior=True, drop=(), edit=None):
    def transform(data):
        _protected_component(data, prior, drop)
        if edit is not None:
            bundle = json.loads(data[1]['facts'][-1]['text'])
            edit(bundle)
            _write_bundle(data, bundle)
    return transform


def _null_prior(bundle):
    bundle['prior_basis_id'] = None
    for point in bundle['operands']:
        point['prior'] = None


def _null_prior_and_companions(bundle):
    _null_prior(bundle)
    for point in bundle['operands']:
        point['companions'] = point['companions'][:1] + point['companions'][11:]


def _swap_periods(bundle):
    bundle['prior_period_id'], bundle['current_period_id'] = (
        bundle['current_period_id'], bundle['prior_period_id'])
    for point in bundle['operands']:
        point['prior']['period_id'], point['current']['period_id'] = (
            point['current']['period_id'], point['prior']['period_id'])


def _prior_equals_current(bundle):
    bundle['prior_period_id'], bundle['prior_basis_id'] = (
        bundle['current_period_id'], bundle['current_basis_id'])
    for point in bundle['operands']:
        point['prior'] = copy.deepcopy(point['current'])


def _drop_companion(bundle):
    bundle['operands'][0]['companions'].pop()


def _dup_companion(bundle):
    companions = bundle['operands'][0]['companions']
    companions[1] = copy.deepcopy(companions[0])


def _empty_companions(bundle):
    bundle['operands'][0]['companions'].clear()


def _reorder_companions(bundle):
    bundle['operands'][0]['companions'].reverse()


def _garbage_basis(bundle):
    bundle['prior_basis_id'] = 'prior_basis'
    for point in bundle['operands']:
        point['prior']['basis_id'] = 'prior_basis'


def _swap_operand_facts(bundle):
    point = bundle['operands'][0]
    point['prior']['fact'], point['current']['fact'] = point['current']['fact'], point['prior']['fact']


def _consistent_swap(bundle):
    bundle['prior_period_id'], bundle['current_period_id'] = (
        bundle['current_period_id'], bundle['prior_period_id'])
    bundle['prior_basis_id'], bundle['current_basis_id'] = (
        bundle['current_basis_id'], bundle['prior_basis_id'])
    for point in bundle['operands']:
        point['prior'], point['current'] = point['current'], point['prior']
        c = point['companions']
        point['companions'] = [c[0], *c[11:], *c[1:11]]


_Q3_PERIOD_FACTS = {f'q3-2025.{field}' for field in _PERIOD_FIELDS}
_PRIOR_FACTS = {f'{m}.prior' for m in json.loads((Path(__file__).parents[1] / 'cases/earnings/owner-expected.json').read_text())['lineage']['measure_order']}


@pytest.mark.parametrize('name,kwargs', [
    ('p1_false_absence', {'edit': _null_prior}),
    ('p1_false_absence_consistent_companions', {'edit': _null_prior_and_companions}),
    ('p1b_swapped_periods', {'edit': _swap_periods}),
    ('p7_prior_equals_current', {'edit': _prior_equals_current}),
    ('consistent_swap_prior_after_current', {'edit': _consistent_swap}),
    ('p8_drop_companion', {'edit': _drop_companion}),
    ('p8_duplicate_companion', {'edit': _dup_companion}),
    ('p8_empty_companions', {'edit': _empty_companions}),
    ('p8_reordered_companions', {'edit': _reorder_companions}),
    ('bundle_basis_not_derived', {'edit': _garbage_basis}),
    ('operand_fact_swapped', {'edit': _swap_operand_facts}),
    # Open semantic questions: partial absence shapes are refused, not interpreted.
    ('partial_row_present_measure_fact_missing', {'drop': {'revenue.prior'}}),
    ('partial_period_field_missing', {'drop': {'q3-2025.end_date'}}),
    ('partial_row_present_all_prior_facts_missing', {'drop': _PRIOR_FACTS, 'edit': _null_prior}),
    ('partial_row_absent_prior_facts_present', {'drop': _Q3_PERIOD_FACTS, 'edit': _null_prior}),
])
def test_integrity_v2_lineage_is_authenticated_against_canonical_cp1(tmp_path, name, kwargs):
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=_lineage_transform(**kwargs))
    with pytest.raises(ValueError, match='^not_permitted$'):
        _integrity_session(store, attempt)


def test_integrity_v2_factory_tampered_store_bytes_are_identity_mismatch(tmp_path):
    store, attempt, heads, _ = _integrity_execution(tmp_path, transform=_protected_component)
    grant = _integrity_grant(store, attempt)
    (store.directory / 'blobs' / heads[0].content_hash()).write_text('private tamper')
    with pytest.raises(ValueError, match='^identity_mismatch$') as caught:
        _integrity_session(store, attempt, grant)
    assert 'tamper' not in str(caught.value)


def test_integrity_v2_lineage_genuine_prior_absence_is_accepted(tmp_path):
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=_lineage_transform(prior=False))
    session = _integrity_session(store, attempt)
    headers, _ = _integrity_pages(session, 'lineage_headers')
    operands, _ = _integrity_pages(session, 'lineage_operands')
    companions, _ = _integrity_pages(session, 'lineage_companions')
    assert [h['prior_operand_id'] for h in headers] == [None] * 12
    assert {o['role'] for o in operands} == {'current'} and len(operands) == 12
    assert len(companions) == 12 * 11 and [h['companion_count'] for h in headers] == [11] * 12
    bundle, _ = _integrity_pages(session, 'lineage_bundles')
    assert bundle[0]['prior_basis_id'] is None


def test_integrity_v2_lineage_both_present_counts_are_stable(tmp_path):
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=_lineage_transform())
    session = _integrity_session(store, attempt)
    counts = {s: len(_integrity_pages(session, s)[0]) for s in
              ('lineage_bundles', 'lineage_headers', 'lineage_operands', 'lineage_companions',
               'lineage_citations', 'lineage_owner_facts')}
    assert counts == {'lineage_bundles': 1, 'lineage_headers': 12, 'lineage_operands': 24,
                      'lineage_companions': 252, 'lineage_citations': 48, 'lineage_owner_facts': 44}


def _contradictions():
    import typing
    from types import SimpleNamespace

    from deploy_vii import cp5_integrity as core

    severities = typing.get_args(core.Severity)
    refs = (core.ClaimRef(producer_module='CP-1', claim_ref='summary'),
            core.ClaimRef(producer_module='CP-1B', claim_ref='summary'))
    first = core.Contradiction(claim_refs=refs, nature='Opposed direction',
                               rationale='Labels only.', severity=severities[0])
    second = core.Contradiction(claim_refs=refs, nature='Opposed timing',
                                rationale='Labels only.', severity=severities[-1])
    return core, SimpleNamespace, first, second


@pytest.mark.parametrize('label,pick,expected', [
    ('distinct_same_pair', (0, 1), 2), ('exact_repeat', (0, 0), 1)])
def test_integrity_v2_final_findings_preserve_core_contradiction_multiplicity(tmp_path, label, pick, expected):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    core, namespace, first, second = _contradictions()
    items = [(first, second)[n] for n in pick]
    findings = core._ordered([core._contradiction_finding(c) for c in items])
    assert len(findings) == expected
    out = session._catalog.safe_findings(findings, final=True, submission=namespace(contradictions=items))
    assert [f['code'] for f in out] == ['contradiction'] * expected
    assert len({f['finding_id'] for f in out}) == expected
    assert all([r['producer_module_id'] for r in f['claim_refs']] == ['CP-1', 'CP-1B'] for f in out)


def test_integrity_v2_returned_receipts_are_detached_from_catalog(tmp_path):
    store, attempt, heads, _ = _integrity_execution(tmp_path, transform=_protected_component)
    session = _integrity_session(store, attempt)
    manifest = session.integrity_manifest
    args = {'scope_sha256': manifest['scope_sha256'], 'section': 'claims', 'cursor': None, 'limit': 20}
    first = session.invoke('read_integrity_scope', args)
    original = copy.deepcopy(first['body'])
    first['body']['entries'][0]['text'] = 'TAMPERED'
    first['body']['entries'][0]['touching_kinds'].append('fact_citation')
    again = session.invoke('read_integrity_scope', args)
    assert again['body']['entries'] == original['entries']
    assert session.integrity_manifest['manifest_sha256'] == manifest['manifest_sha256']
    assert session.receipts[0]['body'] == original
    lookup = {'producer_module_id': 'CP-1B', 'producer_sha256': heads[1].content_hash(),
              'table_id': 'T1B.3', 'row_ids': ['evidence.inputs'],
              'fields': ['fact_id', 'table_id', 'row_id', 'field', 'status', 'text', 'citation_handles']}
    receipt = session.invoke('lookup_upstream', lookup)
    pristine = copy.deepcopy(receipt['body'])
    receipt['body']['rows'][0]['facts'][0]['text']['raw_sha256'] = '0' * 64
    receipt['body']['rows'][0]['facts'][0]['citation_handles']['count'] = 999
    assert session.invoke('lookup_upstream', lookup)['body'] == pristine
    owner, _ = _integrity_pages(session, 'lineage_owner_facts')
    bundle = next(o for o in owner if o['coordinate']['fact_id'] == 'cp1b:T1B.3:evidence.inputs:assessment')
    assert bundle['text_commitment']['raw_sha256'] == pristine['rows'][0]['facts'][0]['text']['raw_sha256']
    assert bundle['citation_set']['count'] != 999
    findings = session.invoke('read_integrity_scope', {**args, 'section': 'findings'})
    findings['body']['entries'].append('TAMPERED')
    verify = session.invoke('verify_integrity_scope', {'scope_sha256': manifest['scope_sha256']})
    assert verify['status'] == 'ok'


def test_integrity_v2_touching_kinds_match_core_claim_marks(tmp_path):
    from deploy_vii import cp5_integrity as core

    def two_claims(data):
        data[0]['facts'][0].update(amount=None, status='missing', limitation='Not supplied')
        base = data[0]['claims'][0]
        base['text'] = 'Revenue observation [fin.rev].'
        other = copy.deepcopy(base)
        other.update(claim_id='limited', limitation='Observation is unavailable within this scope.')
        data[0]['claims'].append(other)
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=two_claims)
    session = _integrity_session(store, attempt)
    claims, _ = _integrity_pages(session, 'claims')
    kinds = {(c['producer']['module_id'], c['claim_id']): c['touching_kinds'] for c in claims}
    # Oracle: a properly limited claim is in the unsettled catalog but gets no forced own finding.
    assert kinds['CP-1', 'limited'] == []
    assert kinds['CP-1', 'summary'] == ['unsettled_fact']
    marks = core.python_checks(core.review_scope(store, attempt)).claim_marks
    for key, value in kinds.items():
        assert value == sorted({m.split(':')[0].split(' on ')[0] for m in marks.get(key, ())},
                               key=core.KINDS.index)


@pytest.mark.parametrize('error', [ValueError('secret'), KeyError('secret'), TypeError('secret'),
                                   RuntimeError('secret')])
def test_integrity_v2_factory_unexpected_error_is_internal_error(tmp_path, monkeypatch, error):
    from deploy_vii import cp5_integrity as core

    store, attempt, _, _ = _integrity_execution(tmp_path)
    def boom(_scope):
        raise error
    monkeypatch.setattr(core, 'python_checks', boom)
    with pytest.raises(ValueError, match='^internal_error$') as caught:
        _integrity_session(store, attempt)
    assert 'secret' not in str(caught.value) and caught.value.__cause__ is None


@pytest.mark.parametrize('error', [KeyError('secret'), 'internal_error'])
def test_integrity_v2_lineage_internal_error_is_not_relabelled_not_permitted(tmp_path, monkeypatch, error):
    module = _upstream_module()
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=_protected_component)
    def boom(*_args, **_kwargs):
        raise module._Refusal(error) if isinstance(error, str) else error
    monkeypatch.setattr(module._IntegrityCatalog, '_citation_set', boom)
    with pytest.raises(ValueError, match='^internal_error$'):
        _integrity_session(store, attempt)


@pytest.mark.parametrize('kind,code', [
    (5, 'bad_arguments'), (['citations'], 'bad_arguments'), (None, 'bad_arguments'),
    ('bogus', 'bad_arguments'), ('integrity', 'not_permitted')])
def test_integrity_v2_verify_kind_is_checked_before_producer_hash(tmp_path, kind, code):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    receipt = session.invoke('verify_upstream', {
        'producer_module_id': 'CP-1', 'producer_sha256': '0' * 64, 'kind': kind,
        'fact_ids': ['fin.rev']})
    _assert_refused(receipt, code)


def test_integrity_v2_ordinary_brace_prose_passes_but_record_json_refuses(tmp_path):
    def prose(data):
        data[0]['facts'][0]['basis'] = '{fin.rev|MILLIONS} rose'
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=prose)
    session = _integrity_session(store, attempt)
    evidence, _ = _integrity_pages(session, 'required_evidence')
    assert evidence[0]['fact']['basis'] == '{fin.rev|MILLIONS} rose'
    def wrapper(data):
        data[0]['facts'][0]['basis'] = '{"record_json":"x"}'
    store, attempt, _, _ = _integrity_execution(tmp_path / 'wrapper', transform=wrapper)
    with pytest.raises(ValueError, match='^not_permitted$'):
        _integrity_session(store, attempt)


def test_integrity_v2_causal_findings_exact_and_blocked_limitation_never_disclosed(tmp_path):
    store, attempt, _, fixture = _integrity_execution(tmp_path, 'blocked')
    session = _integrity_session(store, attempt)
    expected = next(x for x in fixture['causal_mutations'] if x['id'] == 'blocked')['expected_counts']
    findings, _ = _integrity_pages(session, 'findings')
    assert {f['code'] for f in findings} == {k for k, v in expected.items() if v}
    for section in (x['section'] for x in session.integrity_manifest['sections']):
        _integrity_pages(session, section)
    limitations, _ = _integrity_pages(session, 'limitations')
    assert all(entry['label'] == 'Upstream restriction retained' for entry in limitations)
    assert 'PRIVATE_BLOCKED_LIMITATION' not in json.dumps(session.receipts)
    assert 'PRIVATE_BLOCKED_LIMITATION' not in json.dumps(session.integrity_manifest)


@pytest.mark.parametrize('mutation', ['bound_input_hash', 'producer_hash', 'producer_status'])
def test_integrity_v2_wrong_grant_identity_is_identity_mismatch(tmp_path, mutation):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    grant = _integrity_grant(store, attempt)
    if mutation == 'bound_input_hash':
        grant['bound_inputs'][0]['sha256'] = '0' * 64
    elif mutation == 'producer_hash':
        grant['producers'][0]['sha256'] = '0' * 64
    else:
        actual = grant['producers'][0]['status']
        grant['producers'][0]['status'] = 'restricted' if actual != 'restricted' else 'accepted'
    with pytest.raises(ValueError, match='^identity_mismatch$'):
        _integrity_session(store, attempt, grant)


def test_integrity_v2_empty_evaluated_set_is_one_mechanical_finding(tmp_path):
    from deploy_vii import cp5_integrity as core

    store, attempt, _, fixture = _integrity_execution(tmp_path)
    module = _upstream_module()
    pack = core.review_scope(store, attempt).pack
    scope = core.ReviewScope(pack=pack, inputs=(), heads=())
    grant = {'schema_version': 'cp5-upstream-grant/2', 'consumer_module_id': 'CP-5',
             'step_id': 'integrity_review', 'bound_inputs': [], 'producers': [],
             'raw_source_ids': [],
             'internal_scope_inspection': 'complete_bound_scope_for_existing_python_checks_only'}
    catalog = module._IntegrityCatalog(scope, {}, grant)
    expected = next(x for x in fixture['causal_mutations'] if x['id'] == 'empty')['expected_counts']
    findings = catalog.sections['findings']
    assert [f['code'] for f in findings] == ['empty_evaluated_set']
    assert expected['empty_evaluated_set'] == 1 and sum(expected.values()) == 1


def test_integrity_v2_same_cursor_with_different_limit_keeps_starting_offset(tmp_path):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    session = _integrity_session(store, attempt)
    manifest = session.integrity_manifest
    base = {'scope_sha256': manifest['scope_sha256'], 'section': 'required_evidence', 'limit': 1}
    first = session.invoke('read_integrity_scope', {**base, 'cursor': None})
    cursor = first['body']['next_cursor']
    one = session.invoke('read_integrity_scope', {**base, 'cursor': cursor})
    two = session.invoke('read_integrity_scope', {**base, 'cursor': cursor, 'limit': 2})
    assert one['body']['offset'] == two['body']['offset'] == 1
    assert one['body']['entries'] == two['body']['entries']  # only one entry remains
    assert one['body']['entries'][0] != first['body']['entries'][0]


def test_integrity_v2_same_cursor_with_different_limit_changes_prefix_length(tmp_path):
    # Lease L53: another valid limit can change prefix length from the same start.
    store, attempt, _, _ = _integrity_execution(tmp_path, transform=_protected_component)
    session = _integrity_session(store, attempt)
    manifest = session.integrity_manifest
    base = {'scope_sha256': manifest['scope_sha256'], 'section': 'lineage_companions'}
    first = session.invoke('read_integrity_scope', {**base, 'cursor': None, 'limit': 1})
    cursor = first['body']['next_cursor']
    one = session.invoke('read_integrity_scope', {**base, 'cursor': cursor, 'limit': 1})
    two = session.invoke('read_integrity_scope', {**base, 'cursor': cursor, 'limit': 2})
    assert one['status'] == two['status'] == 'ok'
    assert one['body']['offset'] == two['body']['offset'] == 1
    assert len(one['body']['entries']) == 1 and len(two['body']['entries']) == 2
    assert two['body']['entries'][0] == one['body']['entries'][0]
    assert first['body']['total'] - 1 >= 3


def test_integrity_v2_lineage_measures_are_the_one_vocabulary_in_owner_order():
    module = _upstream_module()
    owner = json.loads((Path(__file__).parents[1] / 'cases/earnings/owner-expected.json').read_text())
    assert list(module._LINEAGE_MEASURES) == owner['lineage']['measure_order']
    assert set(module._LINEAGE_MEASURES) == module._MEASURES


@pytest.mark.parametrize('where,key,value', [
    ('producers', 'role', []), ('producers', 'status', {}), ('bound_inputs', 'status', [])])
def test_integrity_v2_unhashable_grant_enum_is_bad_arguments(tmp_path, where, key, value):
    store, attempt, _, _ = _integrity_execution(tmp_path)
    grant = _integrity_grant(store, attempt)
    grant[where][0][key] = value
    with pytest.raises(ValueError, match='^bad_arguments$'):
        _integrity_session(store, attempt, grant)


def test_integrity_v2_verify_reread_swapped_cp1b_blob_is_identity_mismatch(tmp_path, monkeypatch):
    from deploy_vii import cp5_integrity

    store, attempt, heads, _ = _integrity_execution(tmp_path, transform=_protected_component)
    session = _integrity_session(store, attempt)
    scope_sha = session.integrity_manifest['scope_sha256']
    real = cp5_integrity.review_scope
    path = store.directory / 'blobs' / heads[1].content_hash()

    def swapping(store_, attempt_):
        raw = path.read_bytes()
        path.write_bytes(b'x')
        try:
            return real(store_, attempt_)
        finally:
            path.write_bytes(raw)

    monkeypatch.setattr(cp5_integrity, 'review_scope', swapping)
    receipt = session.invoke('verify_integrity_scope', {'scope_sha256': scope_sha})
    _assert_refused(receipt, 'identity_mismatch')
