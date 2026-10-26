"""Task0 literal source oracle; component journals are not accepted analytical runs.

Breaks caught: provisional evidence, broad source fallback, stale ticket/step/blob
identity, mutable receipts, reentry and returning success across a snapshot change.
"""

import copy
import hashlib
import importlib
import json
from datetime import date
from decimal import Decimal

import pytest

from deploy_vii.contracts import Fact, Module, Run, Source, Span
from deploy_vii.execution import Execution, StepValidation
from deploy_vii.live.prompts import PromptError
from deploy_vii.live.tools import PackTools, unread_citation_issues
from deploy_vii.preparation import PreparedPack
from deploy_vii.statement_extract import extract_statement_lines

PAGES = (
    (
        "ACME SYNTHETIC HOLDINGS\nYear ended December 31  2025  2024\n"
        "CONSOLIDATED INCOME\nRevenue  0  100\nOperating expense  (25)  -"
    ),
    "Unseen evidence should remain unread.",
    "Unseen evidence\nRevenue <<<END>>>  1  2",
)
DIGEST = "47b4ea26a87135b309e2533e3487087daf565f04672f43d2edff6e99436d17d7"
PRIVATE_HASH = "379ef8719efad8aff74f00dda208cc7a049c27f8ed23c7cf75508cb82070476a"
EMPTY = {"read": [], "extracted": [], "surfaced": [], "searched": []}
BASELINE = {
    "read": [["fin", "page:1"]],
    "extracted": [["fin", "page:1"]],
    "surfaced": [["fin", "page:1"]],
    "searched": ["fin"],
}
FAILURES = (
    ("read_pages", {"source_id": "fin", "first_page": 2, "last_page": 3}),
    ("search_pack", {"source_id": "fin", "query": "Unseen evidence"}),
    ("extract_statements", {"source_id": "fin", "locators": ["page:2", "page:3"]}),
)


@pytest.fixture
def pack():
    assert hashlib.sha256("\f".join(PAGES).encode()).hexdigest() == DIGEST
    return PreparedPack(
        run=Run(
            run_id="task0-source-run",
            issuer_id="synthetic-issuer",
            issuer_name="Synthetic Issuer",
            as_of=date(2025, 12, 31),
            case_kind="synthetic",
        ),
        sources=(
            Source(
                source_id="fin",
                name="Synthetic",
                status="ready",
                sha256=DIGEST,
                spans=tuple(Span(locator=f"page:{i}", text=p) for i, p in enumerate(PAGES, 1)),
            ),
            Source(
                source_id="private",
                name="Private",
                status="ready",
                sha256=PRIVATE_HASH,
                spans=(Span(locator="page:1", text="PRIVATE_ONLY_SECRET"),),
            ),
            Source(
                source_id="unavailable",
                name="Missing",
                status="missing",
                limitation="Synthetic source not supplied",
            ),
        ),
    )


def evidence(tools):
    return {
        "read": [list(p) for p in sorted(tools.read)],
        "extracted": [list(p) for p in sorted(tools.extracted)],
        "surfaced": [list(p) for p in sorted(tools.surfaced)],
        "searched": list(tools.searched),
    }


def baseline(tools):
    tools.read_pages({"source_id": "fin", "first_page": 1, "last_page": 1})
    tools.extract_statements({"source_id": "fin", "locators": ["page:1"]})
    tools.search_pack({"source_id": "fin", "query": "Operating expense"})


@pytest.mark.parametrize("method,args", FAILURES)
@pytest.mark.parametrize("prior", ["none", "page1", "page2"])
def test_failed_render_preserves_only_successful_evidence(pack, method, args, prior):
    tools = PackTools(pack, sources=("fin", "unavailable"))
    if prior == "page1":
        baseline(tools)
    elif prior == "page2":
        tools.read_pages({"source_id": "fin", "first_page": 2, "last_page": 2})
        tools.search_pack({"source_id": "fin", "query": "should remain unread"})
    before = evidence(tools)
    with pytest.raises(PromptError):
        getattr(tools, method)(args)
    assert evidence(tools) == before
    cited = json.dumps({"citations": [{"source_id": "fin", "locator": "page:2"}]})
    assert bool(unread_citation_issues(cited, tools.seen())) == (prior != "page2")


def test_extraction_preserves_literal_zero_negative_and_missing(pack):
    table = extract_statement_lines(PAGES[0], "page:1", source_id="fin")
    assert table.headers == ("Year ended December 31  2025  2024",)
    assert [
        (r.line_no, r.label, r.raw_values, r.values, r.caption, r.flags) for r in table.lines
    ] == [
        (4, "Revenue", ("0", "100"), (Decimal(0), Decimal(100)), "CONSOLIDATED INCOME", ()),
        (5, "Operating expense", ("(25)", "-"), (Decimal(-25), None), "CONSOLIDATED INCOME", ()),
    ]


def source_api():
    assert importlib.util.find_spec("deploy_workflow.host") is not None, "Task1 host is absent"
    return importlib.import_module("deploy_workflow.host")


def make_store(tmp_path, pack, module="CP-0", step=None):
    step = step or ("source_readiness" if module == "CP-0" else "source_context")
    store = Execution.create(tmp_path / "execution", pack)
    if module == "CP-1":
        ready = store.begin("CP-0")
        candidate = Module(
            run_id=pack.run.run_id,
            issuer_id=pack.run.issuer_id,
            as_of=pack.run.as_of,
            module_id="CP-0",
            inputs=ready.inputs,
            facts=(
                Fact(
                    fact_id="run-cp1",
                    label="CP1 command",
                    table_id="T8",
                    row_id="CP-1",
                    field="exact_command",
                    text="Run CP-1",
                ),
            ),
        )
        # Trusted synthetic validator: journal mechanics only, not CP0 owner qualification.
        store.finish(ready.ticket_id, candidate.model_dump_json(), lambda _: ())
    attempt = store.begin(module)
    if step != ("source_readiness" if module == "CP-0" else "source_context"):
        # Trusted synthetic prior step; actual source-context validator is Task3 evidence.
        store.submit_step(
            attempt.ticket_id,
            "CP-1",
            ("source_context", "financials", "narrative", "readiness", "quality"),
            "source_context",
            "{}",
            lambda *_: StepValidation(output="{}"),
        )
    return store, attempt.ticket_id


def session(tmp_path, pack, step="source_readiness"):
    api = source_api()
    store, ticket = make_store(
        tmp_path, pack, "CP-0" if step == "source_readiness" else "CP-1", step
    )
    return api.SourceSession.from_execution(store, ticket, step), store, ticket


def test_factory_receipt_and_submission_are_real_immutable_snapshots(tmp_path, pack):
    host, store, ticket = session(tmp_path, pack)
    frozen = store.read().content_hash()
    args = {"source_id": "fin", "first_page": 1, "last_page": 1}
    receipt = host.invoke("read_pages", args)
    assert set(receipt) == {
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
    assert receipt["status"] == "ok" and receipt["error_code"] is None
    assert (
        receipt["body"]
        == f"<<<SOURCE id=fin sha256={DIGEST}>>>\nlocator=page:1 | {PAGES[0]}\n<<<END>>>"
    )
    assert receipt["source_evidence"] == dict(EMPTY, read=[["fin", "page:1"]])
    assert receipt["binding"] == {
        "run_id": "task0-source-run",
        "issuer_id": "synthetic-issuer",
        "as_of": "2025-12-31",
        "method_version": "deploy-v-r14",
        "pack_sha256": pack.content_hash(),
        "snapshot_sha256": frozen,
        "module_id": "CP-0",
        "step_id": "source_readiness",
        "ticket_id": ticket,
        "attempt": 0,
        "inputs": [i.model_dump(mode="json") for i in store.read().attempts[-1].inputs],
    }
    payload = '{"exact":"£ bytes"}'
    binding = host.bind_submission(payload)
    assert set(binding) == {
        "schema_version",
        "binding",
        "payload_sha256",
        "successful_call_ids",
        "call_ids",
        "source_evidence",
    }
    assert binding["schema_version"] == "submission-binding/1"
    assert binding["payload_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
    assert binding["successful_call_ids"] == binding["call_ids"] == [receipt["call_id"]]
    (tmp_path / "source-host-receipts.json").write_text(
        json.dumps(
            {"tool_receipt": receipt, "submission_binding": binding}, ensure_ascii=False, indent=2
        )
    )
    saved = copy.deepcopy(binding)
    args["first_page"] = 3
    receipt["binding"]["inputs"].clear()
    host.invoke("search_pack", {"query": "Operating expense", "source_id": "fin"})
    assert binding == saved
    assert store.read().content_hash() == frozen  # binding never submits/settles


@pytest.mark.parametrize(
    "tool,args,code",
    [
        ("shell", {}, "not_permitted"),
        ("extract_statements", {"source_id": "fin", "locators": ["page:1"]}, "not_permitted"),
        ("read_pages", {"source_id": "unknown", "first_page": 1, "last_page": 1}, "not_permitted"),
        (
            "read_pages",
            {"source_id": "unavailable", "first_page": 1, "last_page": 1},
            "unavailable",
        ),
        ("read_pages", {"source_id": "fin", "first_page": True, "last_page": 1}, "bad_arguments"),
        ("read_pages", {"source_id": "fin", "first_page": 3, "last_page": 2}, "bad_arguments"),
        ("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 6}, "bad_arguments"),
        (
            "read_pages",
            {"source_id": "fin", "first_page": 1, "last_page": 1, "quote": "secret"},
            "bad_arguments",
        ),
        ("search_pack", {"query": "", "source_id": "fin"}, "bad_arguments"),
        ("search_pack", {"query": "x", "max_hits": True}, "bad_arguments"),
        ("search_pack", {"query": "x", "max_hits": 16}, "bad_arguments"),
    ],
)
def test_host_refuses_malformed_or_disallowed_calls_without_state(tmp_path, pack, tool, args, code):
    host, _, _ = session(tmp_path, pack)
    result = host.invoke(tool, args)
    assert (result["status"], result["error_code"], result["body"]) == ("refused", code, None)
    assert result["source_evidence"] == EMPTY
    assert "PRIVATE_ONLY_SECRET" not in json.dumps(result)


@pytest.mark.parametrize("tool,args", FAILURES)
def test_host_stages_source_evidence_and_records_failed_calls(tmp_path, pack, tool, args):
    host, _, _ = session(tmp_path, pack, "financials")
    successes = []
    for name, arguments in [
        ("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1}),
        ("extract_statements", {"source_id": "fin", "locators": ["page:1"]}),
        ("search_pack", {"query": "Operating expense", "source_id": "fin"}),
    ]:
        successes.append(host.invoke(name, arguments))
    result = host.invoke(tool, args)
    assert result["status"] == "refused" and result["error_code"] == "render_refused"
    assert result["body"] is None and result["source_evidence"] == BASELINE
    binding = host.bind_submission("{}")
    assert binding["successful_call_ids"] == [r["call_id"] for r in successes]
    assert binding["call_ids"] == [r["call_id"] for r in successes] + [result["call_id"]]
    assert [r["sequence"] for r in successes] + [result["sequence"]] == [1, 2, 3, 4]


@pytest.mark.parametrize("step", ["financials", "narrative", "readiness", "quality", "unknown"])
def test_factory_rejects_future_wrong_or_source_free_steps(tmp_path, pack, step):
    api = source_api()
    store, ticket = make_store(tmp_path, pack, "CP-1")
    with pytest.raises(api.SourceError):
        api.SourceSession.from_execution(store, ticket, step)


def test_factory_accepts_current_source_context(tmp_path, pack):
    host, _, _ = session(tmp_path, pack, "source_context")
    assert (
        host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})["status"]
        == "ok"
    )


def test_stale_binding_refuses_invocation_and_submission(tmp_path, pack):
    api = source_api()
    host, store, ticket = session(tmp_path, pack)
    store.interrupt(ticket, "Controlled stale case")
    result = host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})
    assert (result["status"], result["error_code"], result["body"]) == (
        "refused",
        "stale_binding",
        None,
    )
    assert result["source_evidence"] == EMPTY
    with pytest.raises(api.SourceError, match="stale_binding"):
        host.bind_submission("{}")
    with pytest.raises(api.SourceError):
        api.SourceSession.from_execution(store, ticket, "source_readiness")


def test_snapshot_change_during_render_discards_result_and_evidence(tmp_path, pack, monkeypatch):
    host, store, ticket = session(tmp_path, pack)
    import deploy_vii.live.tools as imported

    block = imported.block

    def changed(*args, **kwargs):
        store.interrupt(ticket, "Changed while rendering")
        return block(*args, **kwargs)

    monkeypatch.setattr(imported, "block", changed)
    result = host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})
    assert (result["status"], result["error_code"], result["body"]) == (
        "refused",
        "stale_binding",
        None,
    )
    assert result["source_evidence"] == EMPTY


def test_reentrant_calls_are_refused_and_retained(tmp_path, pack, monkeypatch):
    host, _, _ = session(tmp_path, pack)
    import deploy_vii.live.tools as imported

    block = imported.block
    nested = []

    def reenter(*args, **kwargs):
        nested.append(host.invoke("search_pack", {"query": "Operating expense"}))
        return block(*args, **kwargs)

    monkeypatch.setattr(imported, "block", reenter)
    result = host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})
    assert result["status"] == "ok"
    assert nested[0]["status"] == "refused" and nested[0]["body"] is None
    assert nested[0]["source_evidence"] == EMPTY
    binding = host.bind_submission("{}")
    assert binding["call_ids"] == [result["call_id"], nested[0]["call_id"]]
    assert binding["successful_call_ids"] == [result["call_id"]]


def test_corrupt_pack_blob_does_not_disclose_or_return_success(tmp_path, pack):
    host, store, _ = session(tmp_path, pack)
    (store.directory / "blobs" / pack.content_hash()).write_text("PRIVATE_ONLY_SECRET")
    result = host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})
    assert result["status"] == "refused" and result["error_code"] == "identity_mismatch"
    assert result["body"] is None and result["source_evidence"] == EMPTY
    assert "PRIVATE_ONLY_SECRET" not in json.dumps(result)


@pytest.mark.parametrize(
    "tool,args",
    [
        ("search_pack", {"query": "PRIVATE", "source_id": "private"}),
        ("read_pages", {"source_id": "private", "first_page": 1, "last_page": 1}),
        ("extract_statements", {"source_id": "private", "locators": ["page:1"]}),
    ],
)
def test_explicit_scope_refuses_ready_private_source(pack, tool, args):
    from deploy_workflow.tools.source import SourceError, SourceTools

    tools = SourceTools(pack, ("fin", "unavailable"), extraction=True)
    with pytest.raises(SourceError, match="not_permitted"):
        tools.stage(tool, args)
    assert tools.evidence() == EMPTY


@pytest.mark.parametrize("scope", [{}, {"source_id": None}])
def test_unscoped_search_remains_inside_explicit_grant(pack, scope):
    from deploy_workflow.tools.source import SourceTools

    tools = SourceTools(pack, ("fin", "unavailable"), extraction=True)
    body, staged = tools.stage("search_pack", dict(query="PRIVATE", **scope))
    assert body == "0 spans match 'PRIVATE'; showing 0."
    assert PRIVATE_HASH not in body and "PRIVATE_ONLY_SECRET" not in body
    tools.commit(staged)
    assert tools.evidence() == dict(EMPTY, searched=[None])


@pytest.mark.parametrize(
    "args",
    [
        {"source_id": "fin", "locators": []},
        {"source_id": "fin", "locators": ["page:1", "page:1"]},
        {"source_id": "fin", "locators": ["page:4"]},
        {"source_id": "fin", "locators": ["page:01"]},
        {"source_id": "fin", "locators": [f"page:{i}" for i in range(1, 10)]},
    ],
)
def test_bad_extraction_never_credits_evidence(tmp_path, pack, args):
    host, _, _ = session(tmp_path, pack, "financials")
    result = host.invoke("extract_statements", args)
    assert (result["status"], result["error_code"], result["body"]) == (
        "refused",
        "bad_arguments",
        None,
    )
    assert result["source_evidence"] == EMPTY


def test_missing_read_span_and_empty_extraction_stay_honest(tmp_path, pack):
    host, _, _ = session(tmp_path, pack, "financials")
    gap = host.invoke("read_pages", {"source_id": "fin", "first_page": 4, "last_page": 4})
    assert gap["status"] == "ok" and gap["body"] == "page:4 is not a located span of fin."
    assert gap["source_evidence"] == EMPTY
    empty = host.invoke("extract_statements", {"source_id": "fin", "locators": ["page:2"]})
    assert (
        empty["status"] == "ok" and "no statement lines extracted from this page" in empty["body"]
    )
    assert empty["source_evidence"] == dict(EMPTY, extracted=[["fin", "page:2"]])


def test_deep_json_arguments_cannot_escape_sanitized_refusal(tmp_path, pack):
    host, _, _ = session(tmp_path, pack)
    nested = None
    for _ in range(600):
        nested = {"x": nested}
    result = host.invoke("shell", {"nested": nested})
    assert (result["status"], result["error_code"], result["body"]) == (
        "refused",
        "not_permitted",
        None,
    )
    assert result["source_evidence"] == EMPTY
    assert json.dumps(result["arguments"]) == json.dumps({"nested": nested})


@pytest.mark.parametrize("step", ["narrative", "readiness", "quality"])
def test_current_source_free_cp1_steps_never_gain_source_tools(tmp_path, pack, step):
    api = source_api()
    store, ticket = make_store(tmp_path, pack, "CP-1")
    sequence = ("source_context", "financials", "narrative", "readiness", "quality")
    for prior in sequence[: sequence.index(step)]:
        store.submit_step(
            ticket, "CP-1", sequence, prior, "{}", lambda *_: StepValidation(output="{}")
        )
    assert (
        tuple(s.step_id for s in store.read().attempts[-1].steps)
        == sequence[: sequence.index(step)]
    )
    with pytest.raises(api.SourceError, match="not_permitted"):
        api.SourceSession.from_execution(store, ticket, step)


@pytest.mark.parametrize(
    "target,step", [("CP-2", "credit_synthesis"), ("CP-5", "integrity_review")]
)
def test_current_upstream_only_consumers_never_gain_source_tools(tmp_path, pack, target, step):
    from deploy_vii.registry import plan

    api = source_api()
    pack = pack.model_copy(
        update={"run": pack.run.model_copy(update={"requested_modules": (target,)})}
    )
    store = Execution.create(tmp_path / "upstream-only", pack)
    sequence = plan((target,))
    for module in sequence:
        attempt = store.begin(module)
        if module == target:
            break
        # All prerequisite Modules here are trusted component mechanics, not owner outputs.
        facts = tuple(
            Fact(
                fact_id="command:" + m,
                label="Command",
                table_id="T8",
                row_id=m,
                field="exact_command",
                text="Run " + m,
            )
            for m in sequence
            if m != "CP-0"
        )
        candidate = Module(
            run_id=pack.run.run_id,
            issuer_id=pack.run.issuer_id,
            as_of=pack.run.as_of,
            module_id=module,
            inputs=attempt.inputs,
            facts=facts if module == "CP-0" else (),
        )
        store.finish(attempt.ticket_id, candidate.model_dump_json(), lambda _: ())
    assert attempt.module_id == target and attempt.status == "pending"
    with pytest.raises(api.SourceError, match="not_permitted"):
        api.SourceSession.from_execution(store, attempt.ticket_id, step)


def test_explicit_within_attempt_repair_remains_current(tmp_path, pack):
    api = source_api()
    store, ticket = make_store(tmp_path, pack, "CP-1")
    sequence = ("source_context", "financials", "narrative", "readiness", "quality")
    store.submit_step(
        ticket,
        "CP-1",
        sequence,
        "source_context",
        "{}",
        lambda *_: StepValidation(issues=("Synthetic invalid first try",)),
    )
    host = api.SourceSession.from_execution(store, ticket, "source_context")
    assert (
        host.invoke("read_pages", {"source_id": "fin", "first_page": 1, "last_page": 1})["status"]
        == "ok"
    )


@pytest.mark.parametrize("coordinate", ["inputs", "issuer", "step_output"])
def test_factory_refuses_corrupt_bound_identities(tmp_path, pack, coordinate):
    from deploy_vii.contracts import Input

    api = source_api()
    store, ticket = make_store(tmp_path, pack, "CP-1", "financials")
    snapshot = store.read()
    attempt = snapshot.attempts[-1]
    if coordinate == "inputs":
        attempt = attempt.model_copy(
            update={"inputs": (Input(input_id="prepared-pack", sha256="0" * 64),)}
        )
        store._write(snapshot.model_copy(update={"attempts": (*snapshot.attempts[:-1], attempt)}))
    elif coordinate == "issuer":
        head = snapshot.heads[0]
        foreign = store.result(head.result_sha256).model_copy(
            update={"issuer_id": "foreign-issuer"}
        )
        digest = store._store(foreign.model_dump_json())
        head = head.model_copy(update={"result_sha256": digest})
        inputs = tuple(
            i.model_copy(update={"sha256": digest}) if i.input_id == "CP-0" else i
            for i in attempt.inputs
        )
        attempt = attempt.model_copy(update={"inputs": inputs})
        store._write(
            snapshot.model_copy(
                update={"heads": (head,), "attempts": (*snapshot.attempts[:-1], attempt)}
            )
        )
    else:
        (store.directory / "blobs" / attempt.steps[0].output_sha256).write_text("corrupt")
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, ticket, "financials")


def test_bind_submission_rechecks_after_hashing_and_rejects_reentry(tmp_path, pack, monkeypatch):
    api = source_api()
    host, store, ticket = session(tmp_path, pack)
    original = api.sha256

    def changed(raw):
        with pytest.raises(api.SourceError, match="not_permitted"):
            host.bind_submission("{}")
        store.interrupt(ticket, "Changed while hashing submission")
        return original(raw)

    monkeypatch.setattr(api, "sha256", changed)
    with pytest.raises(api.SourceError, match="stale_binding"):
        host.bind_submission("{}")


def test_json_envelope_near_recursion_limit_never_escapes(tmp_path, pack):
    import sys

    host, _, _ = session(tmp_path, pack)
    for depth in range(sys.getrecursionlimit() - 100, sys.getrecursionlimit() + 1, 2):
        nested = None
        for _ in range(depth):
            nested = {"x": nested}
        result = host.invoke("shell", {"nested": nested})
        assert result["status"] == "refused" and result["body"] is None
        assert result["error_code"] in ("bad_arguments", "not_permitted")
        assert result["source_evidence"] == EMPTY
