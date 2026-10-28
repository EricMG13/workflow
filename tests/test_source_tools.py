"""Task0 literal source oracle; component journals are not accepted analytical runs.

Breaks caught: provisional evidence, broad source fallback, stale ticket/step/blob
identity, mutable receipts, reentry and returning success across a snapshot change.
"""

import copy
import hashlib
import importlib
import json
import re
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


@pytest.fixture(autouse=True)
def fresh_cp1_cache(monkeypatch):
    """The host's in-process CP-1 memo must never carry across tests (copied histories repeat)."""
    monkeypatch.setattr(source_api(), "_CP1_VERIFIED", {}, raising=False)


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


# CP4 independent expectations are frozen in cases/legal/source-host-expected.json.
# These fixtures create new public CP0/CP1 journals; they do not qualify a legal owner.
def legal_pack(variant=0, *, authority="executed", ready=True):
    from pathlib import Path

    import test_financial_workflow as financial_fixture

    manifest = json.loads((Path(__file__).parents[1] / "cases/legal/manifest.json").read_text())
    case = manifest["cases"][variant]
    baseline_pack = financial_fixture.make_pack()
    raw = case["legal_source"]
    pages = tuple(Span(**page) for page in raw["pages"])
    assert hashlib.sha256("\f".join(p.text for p in pages).encode()).hexdigest() == raw["sha256"]
    legal = Source(
        source_id=raw["source_id"],
        name=raw["name"],
        status="ready" if ready else "missing",
        sha256=raw["sha256"] if ready else None,
        spans=pages if ready else (),
        extraction_status="complete" if ready else "blocked",
        limitation=raw["limitation"],
    )
    run = baseline_pack.run.model_copy(
        update={
            "run_id": case["run_id"] + "-" + authority + ("" if ready else "-missing"),
            "pathway": "covenant_refinancing",
            "requested_modules": ("CP-4", "CP-5"),
        }
    )
    return PreparedPack(run=run, sources=(*baseline_pack.sources, legal))


def legal_cp0_review(pack, *, authority="executed", authorize=True):
    import test_financial_workflow as financial_fixture

    review = json.loads(financial_fixture.readiness(pack))
    legal = pack.sources[-1]
    citation = (
        {
            "source_id": legal.source_id,
            "source_sha256": legal.sha256,
            "locator": "page:1",
            "quote": "Execution attestation:",
        }
        if legal.status == "ready"
        else None
    )
    review["sources"].append(
        {
            "source_id": legal.source_id,
            "document_family": "Selected covenant terms",
            "authority": authority,
            "entity": pack.run.issuer_name,
            "period": "Current through January 10, 2026",
            "version_relationship": "Current restatement",
            "fidelity": "verified" if citation else "blocked",
            "citations": [citation] if citation else [],
            "limitations": [legal.limitation],
        }
    )
    for module in ("CP-4", "CP-5"):
        review["consumers"].append(
            {
                "module_id": module,
                "readiness": "READY_WITH_LIMITATIONS"
                if authorize or module != "CP-4"
                else "CONDITIONAL",
                "evidence_demand": "Selected executed legal terms for interpretation with scope gaps",
                "source_ids": ["identity", "financial", legal.source_id]
                if citation
                else ["identity", "financial"],
                "rationale": "Interpret selected terms; omitted protections remain explicit limitations.",
                "citations": [financial_fixture.IDENTITY, financial_fixture.FINANCIAL]
                + ([citation] if citation else []),
                "limitations": [legal.limitation],
                "missing_source": None
                if authorize or module != "CP-4"
                else "Legal authority withheld",
            }
        )
    return json.dumps(review)


def legal_history(
    root,
    variant=0,
    *,
    authority="executed",
    ready=True,
    blocked=False,
    invalid_context=False,
    authorize=True,
    blocked_quality=False,
):
    import test_financial_workflow as financial_fixture

    from deploy_vii.cp0_workflow import submit_cp0_review
    from deploy_vii.cp1_quality import cp1_quality_inputs
    from deploy_vii.cp1_workflow import FinancialStage, cp1_registers, promote_cp1, submit_cp1_step
    from deploy_vii.downstream_readiness import DownstreamInputs
    from deploy_vii.live.context import narrative_evidence
    from deploy_vii.live.submission import submit_model_payload

    pack = legal_pack(variant, authority=authority, ready=ready)
    store = Execution.create(root / "execution", pack)
    cp0 = store.begin("CP-0")
    cp0 = submit_cp0_review(
        store, cp0.ticket_id, legal_cp0_review(pack, authority=authority, authorize=authorize)
    )
    assert cp0.status == "finished" and not cp0.issues
    attempt = store.begin("CP-1")
    if blocked:
        for number in (0, 1):
            assert attempt.number == number
            for _ in range(2):
                attempt = submit_cp1_step(store, attempt.ticket_id, "source_context", "{}")
            assert attempt.status == "finished" and attempt.issues
            if number == 0:
                attempt = store.begin("CP-1")
        assert store.result(attempt.result_sha256).status == "blocked"
        return store

    def complete(attempt):
        if invalid_context:
            attempt = submit_cp1_step(store, attempt.ticket_id, "source_context", "{}")
            assert len(attempt.step_repairs) == 1
        context = json.loads(financial_fixture.context(pack))
        legal = pack.sources[-1]
        context["sources"].append(
            {
                "source_id": legal.source_id,
                "classification": "nonfinancial",
                "document_type": "Selected legal terms",
                "published_on": "2025-12-30",
                "evidence_class": "internal",
                "evidence_rationale": "Legal supplement only",
                "analytical_use": "Legal interpretation in CP-4",
                "citations": [
                    {
                        "source_id": legal.source_id,
                        "source_sha256": legal.sha256,
                        "locator": "page:1",
                        "quote": "Execution attestation:",
                    }
                ]
                if legal.status == "ready"
                else [],
                "event_scan": "unassessed",
                "event_scan_explanation": "Not a financial source",
            }
        )
        attempt = submit_cp1_step(store, attempt.ticket_id, "source_context", json.dumps(context))
        assert not attempt.issues and len(attempt.steps) == 1
        financial = financial_fixture.financials(pack)
        attempt = submit_model_payload(
            store, attempt.ticket_id, "financials", json.dumps(financial)
        ).journal
        assert len(attempt.steps) == 2 and not attempt.issues
        stage = FinancialStage.model_validate_json(
            store.step_output(attempt.steps[-1].output_sha256)
        )
        narrative = financial_fixture.narrative({"body": narrative_evidence(stage)})
        attempt = submit_model_payload(
            store, attempt.ticket_id, "narrative", json.dumps(narrative)
        ).journal
        assert len(attempt.steps) == 3 and not attempt.issues
        downstream = DownstreamInputs.model_validate_json(
            store.step_output(attempt.steps[-1].output_sha256)
        )
        attempt = submit_model_payload(
            store,
            attempt.ticket_id,
            "readiness",
            json.dumps(
                {
                    "inputs_sha256": downstream.content_hash(),
                    "consumers": [],
                }
            ),
        ).journal
        assert len(attempt.steps) == 4 and not attempt.issues
        inputs = cp1_quality_inputs(cp1_registers(store, attempt.ticket_id))
        kpis = {r.evidence_id for r in stage.narrative_inputs.catalogue if r.kind == "kpi"}
        review = {
            "inputs_sha256": inputs.content_hash(),
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "material": True,
                    "evidence": [
                        {
                            "evidence_id": e,
                            "lineage_class": "Calculated" if e in kpis else "Directly Sourced",
                            "rationale": "Python calculation"
                            if e in kpis
                            else "Located source evidence",
                        }
                        for e in c.evidence_ids
                    ],
                    "rationale": "Material historical credit consideration",
                }
                for c in inputs.claims
            ],
        }
        attempt = promote_cp1(
            store, attempt.ticket_id, "{}" if blocked_quality else json.dumps(review)
        )
        assert attempt.status == "finished"
        if blocked_quality:
            assert attempt.issues and store.result(attempt.result_sha256).status == (
                "rejected" if attempt.number == 0 else "blocked"
            )
        else:
            assert not attempt.issues and store.result(attempt.result_sha256).status == "restricted"
        return attempt

    attempt = complete(attempt)
    if blocked_quality:
        attempt = complete(store.begin("CP-1"))
        assert attempt.number == 1
    return store


@pytest.fixture(scope="module")
def legal_histories(tmp_path_factory):
    result = {}
    options = {
        "positive": {},
        "gap": {"variant": 1},
        "filed": {"authority": "filed"},
        "blocked": {"blocked": True},
        "retained-repair": {"invalid_context": True},
        "issuer": {"authority": "issuer"},
        "unknown": {"authority": "unknown", "blocked": True},
        "missing": {"ready": False, "blocked": True},
        "blocked-quality": {"blocked_quality": True},
    }

    def load(name):
        if name not in result:
            result[name] = legal_history(
                tmp_path_factory.mktemp("legal-" + name), **options[name]
            ).directory
        return result[name]

    return load


def cp4_store(tmp_path, legal_histories, name="positive"):
    import shutil

    directory = tmp_path / "execution"
    shutil.copytree(legal_histories(name), directory)
    store = Execution(directory)
    return store, store.begin("CP-4")


def tree_bytes(directory):
    return {
        str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "name,locators", [("positive", []), ("gap", ["page:2"]), ("filed", []), ("retained-repair", [])]
)
def test_cp4_genuine_promotion_legal_only_and_zero_writes(
    tmp_path, legal_histories, monkeypatch, name, locators
):
    from deploy_vii.cp1_workflow import PROMOTED
    from deploy_vii.execution import head_of

    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, name)
    snapshot = store.read()
    cp1 = next(
        a for a in snapshot.attempts if a.module_id == "CP-1" and a.result_sha256 is not None
    )
    producer = store.result(cp1.result_sha256)
    assert [i.input_id for i in producer.inputs[-4:]] == [
        "pack",
        "financial-review",
        "downstream-report",
        "statement-history",
    ]
    assert next(h for h in snapshot.heads if h.module_id == "CP-1") == head_of(producer, PROMOTED)
    before = tree_bytes(store.directory)

    def no_writer(*_args, **_kwargs):
        pytest.fail("Historical authentication entered a real writer path")

    for method in (
        "_locked",
        "_write",
        "_store",
        "begin",
        "finish",
        "submit_step",
        "interrupt",
        "replace_pack",
        "_save_finished",
    ):
        monkeypatch.setattr(Execution, method, no_writer)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    search = host.invoke("search_pack", {"query": "Schedule A", "source_id": None, "max_hits": 15})
    assert search["status"] == "ok", search
    assert search["source_evidence"]["read"] == []
    assert search["source_evidence"]["searched"] == [None]
    legal = store.pack().sources[-1]
    # Unchanged search ranks any-term matches; only the literal phrase is the oracle's "Schedule A" signal.
    any_term = [s.locator for s in legal.spans if re.search(r"schedule|a", s.text, re.IGNORECASE)]
    assert [p[1] for p in search["source_evidence"]["surfaced"]] == any_term
    assert all(p[0] == "legal-covenants" for p in search["source_evidence"]["surfaced"])
    assert [
        s.locator for s in legal.spans if re.search(r"schedule\s+a", s.text, re.IGNORECASE)
    ] == locators
    literal = re.findall(
        r"phrase_matches=([1-9]\d*)\n<<<SOURCE[^\n]*\n(?:locator=(page:\d+))", search["body"]
    )
    assert [loc for _, loc in literal] == locators
    read = host.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 3}
    )
    assert read["status"] == "ok", read
    assert read["body"] == "\n".join(
        f"<<<SOURCE id=legal-covenants sha256={legal.sha256}>>>\nlocator={span.locator} | {span.text}\n<<<END>>>"
        for span in legal.spans
    )
    assert read["source_evidence"]["read"] == [
        ["legal-covenants", f"page:{i}"] for i in range(1, 4)
    ]
    assert read["source_evidence"]["extracted"] == []
    for identifier in ("identity", "financial", "private", "nonexistent"):
        refused = host.invoke(
            "read_pages", {"source_id": identifier, "first_page": 1, "last_page": 1}
        )
        assert refused["error_code"] == "not_permitted" and refused["body"] is None
    assert (
        host.invoke("extract_statements", {"source_id": "legal-covenants", "locators": ["page:2"]})[
            "error_code"
        ]
        == "not_permitted"
    )
    raw = '{"exact":"£ legal bytes"}'
    binding = host.bind_submission(raw)
    assert binding["payload_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert len(binding["successful_call_ids"]) == 2
    assert tree_bytes(store.directory) == before


def test_cp4_cached_history_matches_freshly_built_history(tmp_path, legal_histories):
    """Faithfulness of the module cache: an uncached build behaves identically to the cached copy."""
    api = source_api()
    (tmp_path / "fresh").mkdir()
    (tmp_path / "cached").mkdir()
    fresh = legal_history(tmp_path / "fresh")
    attempt = fresh.begin("CP-4")
    cached, cached_attempt = cp4_store(tmp_path / "cached", legal_histories)
    args = {"query": "Schedule A", "source_id": None, "max_hits": 15}
    results = []
    for store, ticket in ((fresh, attempt), (cached, cached_attempt)):
        host = api.SourceSession.from_execution(store, ticket.ticket_id, "legal_covenants")
        found = host.invoke("search_pack", args)
        assert found["status"] == "ok", found
        results.append((found["body"], found["source_evidence"]))
    assert results[0] == results[1]
    assert fresh.read().heads == cached.read().heads


@pytest.mark.parametrize("history", ["blocked", "blocked-quality"])
def test_cp4_authentic_blocked_repair_degrades_without_financial_disclosure(
    tmp_path, legal_histories, history
):
    from deploy_vii.cp4_legal import upstream_of

    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, history)
    upstream = upstream_of(store, attempt)
    assert upstream.blocked and upstream.facts == () and upstream.facilities == {}
    assert upstream.cp1_gaps and upstream.legal_sources == ("legal-covenants",)
    before = tree_bytes(store.directory)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert (
        host.invoke(
            "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 3}
        )["status"]
        == "ok"
    )
    assert host.bind_submission("{}")["source_evidence"]["extracted"] == []
    assert tree_bytes(store.directory) == before


@pytest.mark.parametrize("history", ["issuer", "unknown", "missing"])
def test_cp4_empty_authenticated_legal_scope_refuses(tmp_path, legal_histories, history):
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, history)
    with pytest.raises(api.SourceError, match="not_permitted"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


def rewrite_cp1(store, change):
    from deploy_vii.execution import head_of

    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-1" and a.result_sha256)
    producer = store.result(attempt.result_sha256)
    changed = change(producer)
    digest = store._store(changed.model_dump_json())
    revised = attempt.model_copy(update={"result_sha256": digest})
    heads = tuple(
        head_of(changed, h.qualification) if h.module_id == "CP-1" else h for h in snapshot.heads
    )
    attempts = []
    for item in snapshot.attempts:
        if item.ticket_id == attempt.ticket_id:
            item = revised
        if item.module_id == "CP-4":
            item = item.model_copy(
                update={
                    "inputs": tuple(
                        i.model_copy(update={"sha256": digest, "status": changed.status})
                        if i.input_id == "CP-1"
                        else i
                        for i in item.inputs
                    )
                }
            )
        attempts.append(item)
    store._write(snapshot.model_copy(update={"heads": heads, "attempts": tuple(attempts)}))


@pytest.mark.parametrize(
    "coordinate",
    ["missing-tail", "extra-tail", "tail-order", "tail-hash", "fact", "limits", "fake-blocked"],
)
def test_cp4_refuses_consistently_rehashed_forged_cp1(tmp_path, legal_histories, coordinate):
    from deploy_vii.contracts import Input

    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories)

    def change(producer):
        if coordinate == "missing-tail":
            return producer.model_copy(update={"inputs": producer.inputs[:-1]})
        if coordinate == "extra-tail":
            return producer.model_copy(
                update={"inputs": (*producer.inputs, Input(input_id="forged", sha256="0" * 64))}
            )
        if coordinate == "tail-order":
            return producer.model_copy(
                update={"inputs": (*producer.inputs[:-2], *reversed(producer.inputs[-2:]))}
            )
        if coordinate == "tail-hash":
            return producer.model_copy(
                update={
                    "inputs": (
                        *producer.inputs[:-1],
                        producer.inputs[-1].model_copy(update={"sha256": "0" * 64}),
                    )
                }
            )
        if coordinate == "fact":
            fact = next(f for f in producer.facts if f.amount is not None)
            forged = fact.model_copy(update={"amount": Decimal(987654321)})
            return producer.model_copy(
                update={
                    "facts": tuple(
                        forged if f.fact_id == fact.fact_id else f for f in producer.facts
                    )
                }
            )
        if coordinate == "limits":
            return producer.model_copy(update={"limitations": ("Forged limitation",)})
        return producer.model_copy(
            update={
                "status": "blocked",
                "inputs": tuple(
                    i for i in producer.inputs if i.input_id in {"prepared-pack", "CP-0"}
                ),
            }
        )

    rewrite_cp1(store, change)
    before = tree_bytes(store.directory)
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert tree_bytes(store.directory) == before


@pytest.mark.parametrize(
    "coordinate",
    [
        "stage-input",
        "quality-input",
        "repair-input",
        "repair-issues",
        "envelope-hash",
        "candidate-hash",
        "head-qualification",
        "candidate-bytes",
    ],
)
def test_cp4_refuses_retained_chain_or_handoff_tamper(tmp_path, legal_histories, coordinate):
    from deploy_vii.contracts import Input

    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "retained-repair")
    snapshot = store.read()
    cp1 = next(a for a in snapshot.attempts if a.module_id == "CP-1")
    updates = {}
    heads = snapshot.heads
    if coordinate in ("stage-input", "quality-input"):
        index = 0 if coordinate == "stage-input" else 4
        steps = list(cp1.steps)
        steps[index] = steps[index].model_copy(
            update={"inputs": (Input(input_id="forged", sha256="0" * 64),)}
        )
        updates["steps"] = tuple(steps)
    elif coordinate.startswith("repair-"):
        repair = cp1.step_repairs[0]
        repair = repair.model_copy(
            update={"inputs": ()} if coordinate == "repair-input" else {"issues": ("Forged issue",)}
        )
        updates["step_repairs"] = (repair,)
    elif coordinate == "head-qualification":
        heads = tuple(
            h.model_copy(update={"qualification": None}) if h.module_id == "CP-1" else h
            for h in heads
        )
    elif coordinate == "candidate-bytes":
        candidate = Module.model_validate_json(store.payload(cp1.payload_sha256))
        updates["payload_sha256"] = store._store(
            candidate.model_copy(update={"limitations": ("Forged candidate",)}).model_dump_json()
        )
    else:
        step = cp1.steps[-1]
        handoff = json.loads(store.step_output(step.output_sha256))
        handoff["envelope_sha256" if coordinate == "envelope-hash" else "candidate_sha256"] = (
            "0" * 64
        )
        steps = (
            *cp1.steps[:-1],
            step.model_copy(update={"output_sha256": store._store(json.dumps(handoff))}),
        )
        updates["steps"] = steps
    cp1 = cp1.model_copy(update=updates)
    store._write(
        snapshot.model_copy(
            update={
                "heads": heads,
                "attempts": tuple(
                    cp1 if a.ticket_id == cp1.ticket_id else a for a in snapshot.attempts
                ),
            }
        )
    )
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


@pytest.mark.parametrize("blob", ["cp0-review", "cp1-stage", "cp1-output", "candidate", "result"])
def test_cp4_revalidates_named_bytes_after_prior_success(tmp_path, legal_histories, blob):
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    read = host.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1}
    )
    assert read["status"] == "ok"
    cp0 = next(a for a in store.read().attempts if a.module_id == "CP-0")
    cp1 = next(a for a in store.read().attempts if a.module_id == "CP-1")
    digest = {
        "cp0-review": cp0.steps[0].payload_sha256,
        "cp1-stage": cp1.steps[1].payload_sha256,
        "cp1-output": cp1.steps[1].output_sha256,
        "candidate": cp1.payload_sha256,
        "result": cp1.result_sha256,
    }[blob]
    (store.directory / "blobs" / digest).write_text("corrupt")
    refused = host.invoke("search_pack", {"query": "Covenant"})
    assert refused["error_code"] == "identity_mismatch" and refused["body"] is None
    assert refused["source_evidence"] == read["source_evidence"]
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        host.bind_submission("{}")


def count_cp1_replays(monkeypatch, api):
    """Count CP-1 replays against an empty cache so earlier tests cannot pre-warm it."""
    monkeypatch.setattr(api, "_CP1_VERIFIED", {})
    calls = []
    original = api._CP1Verification.replay

    def counted(self):
        calls.append(self._attempt.ticket_id)
        return original(self)

    monkeypatch.setattr(api._CP1Verification, "replay", counted)
    return calls


def test_cp4_cp1_authentication_is_memoised_per_snapshot_and_misses_on_a_new_one(
    tmp_path, legal_histories, monkeypatch
):
    api = source_api()
    replays = count_cp1_replays(monkeypatch, api)
    store, attempt = cp4_store(tmp_path, legal_histories)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    first = len(replays)
    assert first > 0
    again = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert host.invoke("search_pack", {"query": "Covenant"})["status"] == "ok"
    assert again.bind_submission("{}")["source_evidence"] == EMPTY
    assert len(replays) == first
    other, other_attempt = cp4_store(tmp_path / "other", legal_histories, "gap")
    api.SourceSession.from_execution(other, other_attempt.ticket_id, "legal_covenants")
    assert len(replays) > first


def count_cp1_attempt_verifications(monkeypatch, api):
    """Count entries into the real per-attempt CP-1 verifier (a memo hit never enters it)."""
    calls = []
    original = api._verify_cp1_attempt

    def counted(store, snapshot, attempt, producer):
        calls.append(attempt.ticket_id)
        return original(store, snapshot, attempt, producer)

    monkeypatch.setattr(api, "_verify_cp1_attempt", counted)
    return calls


@pytest.mark.parametrize("mode", ["corrupt", "missing"])
@pytest.mark.parametrize(
    "history,blob",
    [
        ("blocked", "cp1-stage-0"),
        ("blocked", "candidate-0"),
        ("blocked", "cp1-stage-1"),
        ("blocked", "candidate-1"),
        ("blocked", "result-before-memo"),
        ("retained-repair", "cp1-stage-last"),
        ("retained-repair", "cp1-output-last"),
        ("retained-repair", "candidate-last"),
        ("retained-repair", "result-before-memo"),
    ],
)
def test_cp4_cached_cp1_authentication_rereads_every_touched_blob(
    tmp_path, legal_histories, monkeypatch, history, blob, mode
):
    """SH-R16 / SH-R12 after a cached success: the hit still refuses without a new replay.

    The cp1-stage, cp1-output and candidate blobs are read only through the memo's re-read
    (the blocked history has a CP-1 attempt 0 and a repair attempt 1 with one step each, no
    step output; the retained-repair history has one attempt with five steps, so the output
    blob comes from there). Damage to them proves a hit re-reads what the first verification
    touched. The result blob is also read before the memo (store.head_module and the upstream
    check), so result-before-memo does not by itself prove the re-read.
    """
    api = source_api()
    replays = count_cp1_replays(monkeypatch, api)
    verifications = count_cp1_attempt_verifications(monkeypatch, api)
    store, attempt = cp4_store(tmp_path, legal_histories, history)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    warm, warm_verifications = len(replays), len(verifications)
    assert warm_verifications > 0
    chain = sorted(
        (a for a in store.read().attempts if a.module_id == "CP-1"), key=lambda a: a.number
    )
    last = chain[-1]
    step = last.steps[-1 if history == "blocked" else 1]
    if blob == "cp1-stage-0":
        digest = chain[0].steps[0].payload_sha256
    elif blob == "candidate-0":
        digest = chain[0].payload_sha256
    elif blob.startswith("cp1-stage"):
        digest = step.payload_sha256
    elif blob.startswith("cp1-output"):
        digest = step.output_sha256
    elif blob.startswith("candidate"):
        digest = last.payload_sha256
    else:
        assert blob == "result-before-memo"
        digest = last.result_sha256
    assert digest
    path = store.directory / "blobs" / digest
    if mode == "corrupt":
        path.write_text("corrupt")
    else:
        path.unlink()
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert host.invoke("search_pack", {"query": "Covenant"})["error_code"] == "identity_mismatch"
    assert len(replays) == warm and len(verifications) == warm_verifications


def test_cp4_warm_cache_does_not_admit_a_changed_cp1_snapshot(
    tmp_path, legal_histories, monkeypatch
):
    """The memo key's snapshot half: forged repair ancestry after a warm cache is re-verified.

    Same CP-1 producer, same result hash, so only the snapshot half of the key can miss. A key
    without the snapshot hash would hit and accept the forged ancestry.
    """
    api = source_api()
    verifications = count_cp1_attempt_verifications(monkeypatch, api)
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    warm = len(verifications)
    assert warm > 0
    snapshot = store.read()
    repair = next(a for a in snapshot.attempts if a.module_id == "CP-1" and a.number == 1)
    forged = repair.model_copy(update={"repair_issues": ("Forged ancestry",)})
    assert forged.result_sha256 == repair.result_sha256
    store._write(
        snapshot.model_copy(
            update={
                "attempts": tuple(
                    forged if a.ticket_id == repair.ticket_id else a for a in snapshot.attempts
                )
            }
        )
    )
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert len(verifications) > warm


def test_cp4_fresh_epoch_and_retained_step_end_old_capability(tmp_path, legal_histories):
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert (
        host.invoke(
            "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1}
        )["status"]
        == "ok"
    )
    fresh = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    assert fresh.bind_submission("{}")["source_evidence"] == EMPTY
    store.submit_step(
        attempt.ticket_id,
        "CP-4",
        ("legal_covenants",),
        "legal_covenants",
        "{}",
        lambda *_: StepValidation(output="{}"),
    )
    assert host.invoke("shell", {"x": float("nan")})["error_code"] == "bad_arguments"
    assert host.invoke("shell", {})["error_code"] == "stale_binding"
    with pytest.raises(api.SourceError, match="not_permitted"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


@pytest.mark.parametrize("code", ["finished", "wrong-step", "unknown-ticket"])
def test_cp4_factory_ticket_precedence(tmp_path, legal_histories, code):
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    step, ticket = "legal_covenants", attempt.ticket_id
    if code == "wrong-step":
        step = "financials"
    elif code == "unknown-ticket":
        ticket = "unregistered-ticket"
    else:
        store.interrupt(ticket, "Synthetic capability epoch ended")
    with pytest.raises(api.SourceError, match="not_permitted"):
        api.SourceSession.from_execution(store, ticket, step)


def test_cp4_actual_consumer_repair_has_fresh_binding_and_checks_ancestry(
    tmp_path, legal_histories
):
    api = source_api()
    store, original = cp4_store(tmp_path, legal_histories, "blocked")
    first = api.SourceSession.from_execution(store, original.ticket_id, "legal_covenants")
    first.invoke("read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1})
    # Actual core journal rejection creates repair1; this is a synthetic invalid caller,
    # not a legal semantic submission or accepted CP4 output.
    store.submit_step(
        original.ticket_id,
        "CP-4",
        ("legal_covenants",),
        "legal_covenants",
        "{}",
        lambda *_: StepValidation(issues=("Synthetic caller refused",)),
    )
    repair = store.begin("CP-4")
    assert repair.number == 1 and repair.repair_of == original.ticket_id
    second = api.SourceSession.from_execution(store, repair.ticket_id, "legal_covenants")
    binding = second.bind_submission("{}")
    assert (
        binding["binding"]["attempt"] == 1 and binding["binding"]["ticket_id"] == repair.ticket_id
    )
    assert binding["source_evidence"] == EMPTY
    assert first.invoke("search_pack", {"query": "Covenant"})["error_code"] == "stale_binding"
    snapshot = store.read()
    altered = repair.model_copy(update={"repair_issues": ("Forged ancestry",)})
    store._write(snapshot.model_copy(update={"attempts": (*snapshot.attempts[:-1], altered)}))
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, repair.ticket_id, "legal_covenants")


def test_cp4_direct_finish_cp1_stub_is_not_promotion(tmp_path):
    from deploy_vii.cp0_workflow import submit_cp0_review

    api = source_api()
    pack = legal_pack()
    store = Execution.create(tmp_path / "execution", pack)
    cp0 = store.begin("CP-0")
    assert not submit_cp0_review(store, cp0.ticket_id, legal_cp0_review(pack)).issues
    cp1 = store.begin("CP-1")
    candidate = Module(
        run_id=pack.run.run_id,
        issuer_id=pack.run.issuer_id,
        as_of=pack.run.as_of,
        module_id="CP-1",
        inputs=cp1.inputs,
    )
    assert not store.finish(cp1.ticket_id, candidate.model_dump_json(), lambda _: ()).issues
    attempt = store.begin("CP-4")
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


@pytest.mark.parametrize(
    "tool,args",
    [
        ("read_pages", {"source_id": "legal-covenants", "first_page": True, "last_page": 1}),
        ("read_pages", {"source_id": "legal-covenants", "first_page": 0, "last_page": 1}),
        ("read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 6}),
        ("search_pack", {"query": ""}),
        ("search_pack", {"query": "Covenant", "max_hits": 16}),
        ("search_pack", {"query": float("nan")}),
    ],
)
def test_cp4_malformed_arguments_preserve_prior_evidence(tmp_path, legal_histories, tool, args):
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    read = host.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1}
    )
    result = host.invoke(tool, args)
    assert (
        result["status"] == "refused"
        and result["error_code"] == "bad_arguments"
        and result["body"] is None
    )
    assert result["source_evidence"] == read["source_evidence"]


def test_cp4_facade_rejects_unsolicited_callbacks_and_writer_access(
    tmp_path, legal_histories, monkeypatch
):
    api = source_api()
    store, _ = cp4_store(tmp_path, legal_histories, "blocked")
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-1" and a.number == 1)
    probe = api._CP1Verification(store, snapshot, attempt)
    before = tree_bytes(store.directory)

    def forbidden(*_args, **_kwargs):
        pytest.fail("Unexpected callback or writer executed")

    monkeypatch.setattr(Execution, "_locked", forbidden)
    for method in (
        "_locked",
        "_write",
        "_store",
        "begin",
        "interrupt",
        "replace_pack",
        "_save_finished",
    ):
        with pytest.raises(ValueError):
            getattr(probe, method)
    with pytest.raises(ValueError):
        probe.finish(attempt.ticket_id, store.payload(attempt.payload_sha256), forbidden)
    with pytest.raises(ValueError):
        probe.submit_step(
            attempt.ticket_id, "CP-1", ("source_context",), "source_context", "{}", forbidden
        )
    assert tree_bytes(store.directory) == before


@pytest.mark.parametrize("cp0", ["withheld", "absent"])
def test_cp4_forged_pending_ticket_without_cp0_authority_is_identity_mismatch(tmp_path, cp0):
    """SH-R03: genuine begin is NotAuthorized/no ticket; a forged pending ticket gets no facade."""
    from deploy_vii.contracts import Input
    from deploy_vii.execution import Attempt, NotAuthorized

    api = source_api()
    if cp0 == "withheld":
        store = legal_history(tmp_path, authorize=False, blocked=True)
        with pytest.raises(NotAuthorized):
            store.begin("CP-4")
    else:
        store = Execution.create(tmp_path / "execution", legal_pack())
        with pytest.raises(ValueError, match="Required upstream is unrun"):
            store.begin("CP-4")
    snapshot = store.read()
    assert all(a.module_id != "CP-4" for a in snapshot.attempts)
    heads = {h.module_id: h for h in snapshot.heads}
    assert ("CP-0" in heads) == (cp0 == "withheld")
    forged = Attempt(
        ticket_id="forged-cp4",
        module_id="CP-4",
        number=0,
        inputs=(
            Input(input_id="prepared-pack", sha256=snapshot.pack_sha256, status="accepted"),
            *(
                Input(input_id=m, sha256=heads[m].result_sha256, status=heads[m].status)
                for m in ("CP-0", "CP-1")
                if m in heads
            ),
        ),
    )
    store._write(snapshot.model_copy(update={"attempts": (*snapshot.attempts, forged)}))
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, "forged-cp4", "legal_covenants")


def test_cp4_forged_pending_ticket_with_cp0_authority_is_admitted(tmp_path, legal_histories):
    """SH-R03 positive control: the same forged ticket shape is admitted once CP-0 authorizes.

    This pins why the withheld twin refuses: the missing CP-0 authority, not the forgery shape.
    """
    import shutil

    from deploy_vii.contracts import Input
    from deploy_vii.execution import Attempt

    api = source_api()
    shutil.copytree(legal_histories("blocked"), tmp_path / "execution")
    shutil.copytree(legal_histories("blocked"), tmp_path / "genuine")
    store = Execution(tmp_path / "execution")
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    forged = Attempt(
        ticket_id="forged-cp4",
        module_id="CP-4",
        number=0,
        inputs=(
            Input(input_id="prepared-pack", sha256=snapshot.pack_sha256, status="accepted"),
            *(
                Input(input_id=m, sha256=heads[m].result_sha256, status=heads[m].status)
                for m in ("CP-0", "CP-1")
            ),
        ),
    )
    assert forged.inputs == Execution(tmp_path / "genuine").begin("CP-4").inputs
    store._write(snapshot.model_copy(update={"attempts": (*snapshot.attempts, forged)}))
    host = api.SourceSession.from_execution(store, "forged-cp4", "legal_covenants")
    assert host.bind_submission("{}")["source_evidence"] == EMPTY


@pytest.mark.parametrize("payload", [b"{}", None, 7, ["{}"], "\ud800 lone surrogate"])
def test_cp4_bind_rejects_nonstring_or_nonutf8_payload_without_binding(
    tmp_path, legal_histories, payload
):
    """SH-R21: bad_arguments, no binding, and earlier evidence is untouched."""
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    read = host.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1}
    )
    with pytest.raises(api.SourceError, match="bad_arguments"):
        host.bind_submission(payload)
    ok = host.bind_submission("{}")
    assert ok["source_evidence"] == read["source_evidence"] and ok["call_ids"] == [read["call_id"]]


def test_cp4_unexpected_errors_are_visible_never_success_and_write_nothing(
    tmp_path, legal_histories, monkeypatch
):
    """SH-R22: a program error is an error receipt or a raised error, never ok/auth-true."""
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    before = tree_bytes(store.directory)

    def boom(*_args, **_kwargs):
        raise RuntimeError("unforeseen verifier failure")

    original_history = api._cp1_history
    monkeypatch.setattr(api, "_cp1_history", boom)
    with pytest.raises(RuntimeError):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    monkeypatch.setattr(api, "_cp1_history", original_history)
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    monkeypatch.setattr(api.SourceTools, "stage", boom)
    receipt = host.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1}
    )
    assert receipt["status"] == "error" and receipt["error_code"] == "internal_error"
    assert receipt["body"] is None and receipt["source_evidence"] == EMPTY
    assert "unforeseen" not in json.dumps(receipt)
    assert host.bind_submission("{}")["successful_call_ids"] == []
    assert tree_bytes(store.directory) == before


@pytest.mark.parametrize("substitution", ["blob-under-old-hash", "repointed-pack"])
def test_cp4_alternative_legal_case_bytes_never_silently_switch_variant(
    tmp_path, legal_histories, substitution
):
    """SH-R23: the other adopted legal variant's bytes under the current source/hash are refused."""
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories)
    snapshot = store.read()
    pack = store.pack(snapshot)
    other = legal_pack(1).sources[-1]
    assert other.sha256 != pack.sources[-1].sha256
    swapped = pack.model_copy(update={"sources": (*pack.sources[:-1], other)})
    if substitution == "blob-under-old-hash":
        (store.directory / "blobs" / snapshot.pack_sha256).write_text(swapped.model_dump_json())
    else:
        store._write(
            snapshot.model_copy(update={"pack_sha256": store._store(swapped.model_dump_json())})
        )
    with pytest.raises(api.SourceError, match="identity_mismatch|stale_binding"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


def test_cp4_relabelled_historical_cp1_is_not_proof_for_a_new_legal_run(tmp_path, legal_histories):
    """SH-R24: another run's promoted CP-1, relabelled with this run's identity, is refused."""
    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories)
    other = Execution(legal_histories("gap"))
    other_cp1 = next(a for a in other.read().attempts if a.module_id == "CP-1" and a.result_sha256)
    historical = other.result(other_cp1.result_sha256)
    run = store.read().run
    assert historical.run_id != run.run_id
    rewrite_cp1(
        store,
        lambda _producer: historical.model_copy(
            update={
                "run_id": run.run_id,
                "issuer_id": run.issuer_id,
                "as_of": run.as_of,
                "method_version": run.method_version,
            }
        ),
    )
    with pytest.raises(api.SourceError, match="identity_mismatch"):
        api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")


def test_cp4_bind_is_truthful_evidence_not_a_rule_pass_for_unreturned_cites_or_absence(
    tmp_path, legal_histories
):
    """SH-S08 / SH-R25: search snippets are not reads; existing caller ToolRules judge the Seen."""
    from deploy_vii.live.tools import Seen, absence_issues, absence_markers

    api = source_api()
    store, attempt = cp4_store(tmp_path, legal_histories, "blocked")
    host = api.SourceSession.from_execution(store, attempt.ticket_id, "legal_covenants")
    name, value = absence_markers("legal_covenants")[0]
    absent = json.dumps({"rows": [{name: value}]})
    cited = json.dumps({"citations": [{"source_id": "legal-covenants", "locator": "page:2"}]})

    def seen_of(binding):
        evidence = binding["source_evidence"]
        return Seen(frozenset(tuple(p) for p in evidence["read"]), tuple(evidence["searched"]))

    assert absence_issues("legal_covenants", absent, seen_of(host.bind_submission(absent)))
    search = host.invoke("search_pack", {"query": "Schedule A"})
    assert search["status"] == "ok" and search["source_evidence"]["surfaced"]
    seen = seen_of(host.bind_submission(cited))
    assert seen.read == frozenset() and seen.searched == (None,)
    assert unread_citation_issues(cited, seen)
    assert not absence_issues("legal_covenants", absent, seen)
    host.invoke("read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 1})
    after = seen_of(host.bind_submission(cited))
    assert after.read == frozenset({("legal-covenants", "page:1")})
    assert unread_citation_issues(cited, after)
    page1 = json.dumps({"citations": [{"source_id": "legal-covenants", "locator": "page:1"}]})
    assert not unread_citation_issues(page1, after)
