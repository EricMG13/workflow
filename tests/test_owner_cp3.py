"""CP-3 acceptance, Stage 5 only: the closed R3 run over `cases/cp3-cp6-owner`.

Not run in Stage 2 (build-first rule): the fixtures promote CP-1 for real, 11-26 minutes per
case, once per module (three more for the blocked-CP-1A and alias runs, which share the positive
promotion where they can). Run it under the heavy-job lock (see the report's deferred commands).
Expectations come from `cases/cp3-cp6-owner/expected.json` and the CP-3 lease only.

Every item of the lease Acceptance list that needs a store run is here, for R3: upstream
equalities, the CP-2 read body, the CP-3 head, inherited limitations, CONTEXT, render, receipt and
store bytes, tool use, the A4 tamper refusals, the blocked-CP-1A variant, the tool-use refusals
(unread page, out-of-scope read, stale snapshot) and the alias selection.

The one thing not asserted is D3, blocked on the CP-6 freeze: the consumer proof is the CP-6 head
(R6). This file asserts what CP-3 itself consumes (the attempt inputs) and that an R3 run holds no
CP-5 or CP-6 head; CP-3 ships no reader.
"""

import copy
import hashlib
import importlib
import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import cp3_cp6_runs as runs
import pytest
import s1a_runs as s1
import test_connect_cp3 as fast

from deploy_vii.contracts import Fact, Module
from deploy_vii.execution import Attempt, Execution
from deploy_vii.live.tools import UNREAD_PAGE
from deploy_workflow.owner_workflow import (
    OWNER_SPECS,
    OwnerRunReceipt,
    OwnerWorkflow,
    _verify_audit,
    _verify_calls_reads,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cp3
from deploy_workflow.workflow import WorkflowError

s1a_tests: Any = importlib.import_module("test_owner_s1a")
ORACLE = runs.oracle()
MANIFEST: dict[str, Any] = ORACLE["manifest"]
EXPECTED: dict[str, Any] = ORACLE["expected"]
S1_EXPECTED: dict[str, Any] = ORACLE["s1"]["expected"]
S1_TREE: dict[str, Any] = ORACLE["s1"]["tree"]
CASES = ("positive", "gap")
PACK_HASH_PLACEHOLDER = "<<PreparedPack.content_hash(), bound at run time>>"
RUN = MANIFEST["runs"][runs.RUN]
LABEL = re.compile(r"<label and period of FIG:([a-z0-9_]+)>")
ALIAS = ["CP-1", "CP-MODEL", "CP-1A", "CP-2", "CP-3B"]


class Closed:
    """One case: the promoted state, the CP-3-active template, and the closed run cloned from it."""

    def __init__(self, case: str, root: Path) -> None:
        self.case = case
        self.promoted, self.pack = runs.promoted(case, root / "promoted")
        self.template = s1.clone_workflow(self.promoted, root / "template")
        runs.through_cp2(self.template, self.pack, case)
        self.root = root / "closed"
        workflow = s1.clone_workflow(self.template, self.root)
        runs.close(workflow, case, self.root / "owner-receipt.json")
        self.store = Execution(self.root / "store")
        self.receipt = OwnerRunReceipt.model_validate_json(
            (self.root / "owner-receipt.json").read_text()
        )
        self.expected: dict[str, Any] = EXPECTED[case]
        self.facts = {f.fact_id: f for f in head_module(self.store, "CP-1").facts}
        self.bindings = runs.cp1_bindings(self.store, list(ORACLE["submissions"]["figures"]))

    def fork(self, name: str) -> OwnerWorkflow:
        return s1.clone_workflow(self.template, self.root.parent / name)


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return Closed(request.param, tmp_path_factory.mktemp(request.param))


@pytest.fixture(scope="module")
def closed_positive(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return Closed("positive", tmp_path_factory.mktemp("positive-only"))


def head_module(store: Execution, module_id: str) -> Module:
    head = next(h for h in store.read().heads if h.module_id == module_id)
    return store.head_module(head)


def attempt_of(store: Execution, module_id: str) -> Attempt:
    result = next(h for h in store.read().heads if h.module_id == module_id).result_sha256
    return next(a for a in store.read().attempts if a.result_sha256 == result)


def label_period(fact: Fact) -> str:
    return f"{fact.label} · {fact.period}" if fact.period else fact.label


def bind_labels(text: str | None, closed: Closed) -> str | None:
    """The oracle's CP-1 label placeholders, bound to the run's own CP-1 head."""
    if text is None:
        return None
    return LABEL.sub(lambda m: label_period(closed.facts[closed.bindings[m[1]][0]]), text)


def tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


def cp3_expected_tables(closed: Closed) -> list[dict[str, Any]]:
    tables = copy.deepcopy(closed.expected["CP-3"]["tables"])
    for table in tables:
        for row in table["rows"]:
            row["label"] = bind_labels(row["label"], closed)
            row.pop("fact_binding", None)
            for fact in row.get("facts", []):
                fact["text"] = bind_labels(fact["text"], closed)
    return cast(list[dict[str, Any]], tables)


# --- the closed run -----------------------------------------------------------------------------


def test_receipt_verifies_and_leaves_the_bytes_unchanged(closed: Closed) -> None:
    before = tree(closed.root / "store", closed.root / "model")
    verify_owner_run_receipt(
        closed.store, closed.receipt, publication_directory=closed.root / "model"
    )
    assert tree(closed.root / "store", closed.root / "model") == before


def test_plan_heads_and_statuses(closed: Closed) -> None:
    assert list(closed.receipt.plan) == RUN["plan_order"]
    heads = {h.module_id: h for h in closed.store.read().heads}
    assert set(heads) == {"CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-MODEL"}
    for module_id in heads:
        assert head_module(closed.store, module_id).status == "restricted", module_id
    assert closed.receipt.model is not None


def test_no_cp5_or_cp6_head_exists_in_an_r3_run(closed: Closed) -> None:
    """D3 is blocked on the CP-6 freeze: the consumer (CP-6, R6) is not part of this run."""
    assert not {"CP-5", "CP-6"} & {h.module_id for h in closed.store.read().heads}
    assert not hasattr(cp3, "cp3_reader")


# --- upstream equalities ------------------------------------------------------------------------


def test_cp0_r3_equals_the_oracle(closed: Closed) -> None:
    want = closed.expected["upstream"]["CP-0"][runs.RUN]
    module = head_module(closed.store, "CP-0")
    assert module.status == want["status"]
    # the oracle binds the pack hash at run time; bind it to this run's pack before comparing
    pack_hash = closed.pack.content_hash()
    bound_facts = [
        {**fact, "text": fact["text"].replace(PACK_HASH_PLACEHOLDER, pack_hash)}
        for fact in want["facts"]
    ]
    assert sum(pack_hash in fact["text"] for fact in bound_facts) == 1
    assert [
        {
            "fact_id": f.fact_id,
            "text": f.text,
            "cites": [[c.source_id, c.locator] for c in f.citations],
        }
        for f in module.facts
    ] == bound_facts
    assert list(module.limitations) == want["limitations"]
    head = next(h for h in closed.store.read().heads if h.module_id == "CP-0")
    assert {c.row_id: c.text for c in head.commands} == want["exact_commands"]
    assert list(closed.receipt.plan) == want["plan_order"]


def _cp1a_expected(closed: Closed) -> list[dict[str, Any]]:
    """S1 positive CP-1A tables with the oracle's `replace_table` / `append_row` deltas."""
    delta = closed.expected["upstream"]["CP-1A"][runs.RUN]
    tables = copy.deepcopy(S1_EXPECTED["positive"]["CP-1A"]["tables"])
    for table_id, change in delta["tables"].items():
        index = next(i for i, t in enumerate(tables) if t["table_id"] == table_id)
        if "replace_table" in change:
            tables[index] = copy.deepcopy(change["replace_table"])
        else:
            tables[index]["rows"].append(copy.deepcopy(change["append_row"]))
    return cast(list[dict[str, Any]], tables)


def test_cp1a_equals_s1_with_the_deltas_and_catalogue_size(closed: Closed) -> None:
    module = head_module(closed.store, "CP-1A")
    s1a_tests._compare_tables(s1a_tests._table_view(module), _cp1a_expected(closed))
    delta = closed.expected["upstream"]["CP-1A"][runs.RUN]
    assert delta["claims_unchanged"] is True
    assert [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in module.claims
    ] == S1_EXPECTED["positive"]["CP-1A"]["claims"]
    body = cp2_read_body(closed)
    assert len(body["cp1a_rows"]) == delta["catalogue_size"]


def test_cp2_equals_s1_positive(closed: Closed) -> None:
    holder = SimpleNamespace(
        store=closed.store, expected=S1_EXPECTED["positive"], bindings=closed.bindings
    )
    expected = s1a_tests._cp2_expected_tables(holder)
    s1a_tests._compare_tables(s1a_tests._table_view(head_module(closed.store, "CP-2")), expected)
    assert [c.claim_id for c in head_module(closed.store, "CP-2").claims] == [
        c["claim_id"] for c in S1_EXPECTED["positive"]["CP-2"]["claims"]
    ]


def cp2_read_body(closed: Closed) -> dict[str, Any]:
    read = next(r for r in closed.receipt.input_reads if r.binding.module_id == "CP-2")
    assert read.inputs_sha256 == hashlib.sha256(read.body.encode()).hexdigest()
    body: dict[str, Any] = json.loads(read.body)
    return body


def test_cp2_read_body_register_counts_follow_the_oracle(closed: Closed) -> None:
    """Review M4: the S1 key tree and register counts, with the four counts the oracle moves."""
    body, frozen = cp2_read_body(closed), S1_TREE["positive"]
    counts = EXPECTED["execution"]["tool_use"]["CP-2"]["register_counts_by_case_and_run"][
        closed.case
    ][runs.RUN]
    assert list(body) == frozen["top_level_keys"]
    shape = s1a_tests._shape(body)
    for key, value in frozen["tree"].items():
        if key != "cp1a_rows":
            assert shape[key] == value, key
    wanted = {r["ref_prefix"]: r["rows"] for r in frozen["cp1a_registers"]}
    for key in ("source_classification", "T2D.1", "downstream_readiness", "T2D.10"):
        wanted[key] = counts[key]
    got = {prefix: 0 for prefix in wanted}
    for row in body["cp1a_rows"]:
        (prefix,) = [p for p in wanted if row["ref"].startswith(p + ".")]
        got[prefix] += 1
    assert got == wanted
    assert len(body["cp1a_rows"]) == counts["cp1a_rows"]
    assert len(body["cp1a_signals"]) == frozen["cp1a_signals"]
    assert body["upstream"] == [
        {"module_id": m, "status": "restricted"} for m in ("CP-0", "CP-1", "CP-1A")
    ]


# --- the CP-3 head ------------------------------------------------------------------------------


def test_cp3_head_equals_the_oracle(closed: Closed) -> None:
    expected = closed.expected["CP-3"]
    module = head_module(closed.store, "CP-3")
    s1a_tests._compare_tables(fast.table_view(module), cp3_expected_tables(closed))
    assert [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in module.claims
    ] == expected["claims"]
    # own = oracle list, then the synthetic limitation, deduplicated (LEAD, Stage 2 round 3)
    assert list(module.limitations) == expected["settled_limitations"]
    assert module.limitations[-1] == "Synthetic case; not real issuer qualification"
    assert module.status == "restricted"
    candidate = Module.model_validate_json(
        closed.store.payload(attempt_of(closed.store, "CP-3").payload_sha256 or "")
    )
    assert list(candidate.limitations) == expected["own_limitations"]


def test_cp3_inherited_limitations_follow_the_rule(closed: Closed) -> None:
    rule = closed.expected["CP-3"]["inherited_limitations"]
    cp1 = head_module(closed.store, "CP-1")
    module = head_module(closed.store, "CP-3")
    entries = [*rule["literal_head"], *cp1.limitations, *cp1.inherited_limitations]
    entries += rule["literal_tail_after_CP-1"]
    wanted = [x for x in dict.fromkeys(entries) if x not in module.limitations]
    assert list(module.inherited_limitations) == wanted


def test_cp3_inputs_are_hash_equal_to_the_final_heads(closed: Closed) -> None:
    module = head_module(closed.store, "CP-3")
    assert [i.input_id for i in module.inputs] == closed.expected["CP-3"]["module_inputs"]
    heads = {h.module_id: h for h in closed.store.read().heads}
    for item in module.inputs:
        if item.input_id in heads:
            assert item.sha256 == heads[item.input_id].result_sha256, item.input_id
    assert module.inputs[0].sha256 == closed.store.read().pack_sha256
    for absent in (*fast.OPTIONAL_IDS, "CP-4", "CP-MODEL"):
        assert absent not in {i.input_id for i in module.inputs}
    model = head_module(closed.store, "CP-MODEL")
    assert "CP-3" not in {i.input_id for i in model.inputs}


def test_context_block_checks_over_the_run(closed: Closed) -> None:
    fast.assert_context(
        closed.store,
        attempt_of(closed.store, "CP-3"),
        closed.expected["CP-3"]["context_block_checks"],
    )


def test_render_blocks_and_rails(closed: Closed) -> None:
    fast.assert_render(
        head_module(closed.store, "CP-3"),
        closed.store.read().run,
        closed.expected["CP-3"]["render"],
    )


def test_the_head_is_re_derived_by_the_probe(closed: Closed) -> None:
    cp3.probe(closed.store, closed.store.read(), attempt_of(closed.store, "CP-3"))


# --- tool use -----------------------------------------------------------------------------------


def _ok_pages(closed: Closed, binding: Any) -> set[tuple[str, str]]:
    return cast(set[tuple[str, str]], s1a_tests._ok_reads(closed.receipt, binding))


def test_cp3_tool_use(closed: Closed) -> None:
    calls = [c for c in closed.receipt.calls if c.binding.module_id == "CP-3"]
    ok = [c for c in calls if c.status == "ok"]
    if closed.case == "positive":
        reads = sorted((c.arguments["source_id"], c.arguments["first_page"]) for c in ok)
        assert reads == [("market", 1), ("market", 2)]
        assert {c.tool for c in ok} == {"read_pages"}
    else:
        assert ok == []


def test_upstream_chain_reads_market_page_1(closed: Closed) -> None:
    """Positive: CP-0, CP-1 and CP-1A each read `market page:1` before their submit; gap: none."""
    steps = (
        ("CP-0", "source_readiness"),
        ("CP-1", "source_context"),
        ("CP-1A", "business_context"),
    )
    for module_id, step_id in steps:
        submit = next(
            s
            for s in closed.receipt.submissions
            if (s.binding.binding.module_id, s.binding.binding.step_id) == (module_id, step_id)
            and s.disposition == "valid"
        )
        has = ("market", "page:1") in _ok_pages(closed, submit.binding.binding)
        assert has == (closed.case == "positive"), module_id
        if module_id == "CP-1A":
            assert s1a_tests._searches(closed.receipt, submit.binding.binding)
    reads = [r for r in closed.receipt.input_reads if r.binding.module_id == "CP-2"]
    assert len(reads) == 1
    assert not [
        c for c in closed.receipt.calls if c.binding.module_id == "CP-2" and c.status == "ok"
    ]


# --- refusals (oracle refusals.tool_use_refusals) -----------------------------------------------


def _payload(workflow: OwnerWorkflow) -> str:
    text = runs.literal("positive", runs.STEP)
    return runs.bind_figures(text, runs.cp1_bindings(workflow._store, runs.figure_names(text)))


def test_unread_cited_page_is_invalid_and_re_begun(closed_positive: Closed) -> None:
    workflow = closed_positive.fork("unread")
    payload = _payload(workflow)
    s1.read_cited(workflow, payload, skip=[("market", "page:2")])
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "invalid"
    assert any(i.startswith(f"{UNREAD_PAGE}: market page:2") for i in outcome["issues"])
    attempts = [a for a in workflow._store.read().attempts if a.module_id == "CP-3"]
    assert [a.number for a in attempts] == [0, 1]
    assert attempts[1].repair_of == attempts[0].ticket_id


def test_out_of_scope_read_is_refused_not_permitted(closed: Closed) -> None:
    """Positive: the session scope is `market` only, so `financial page:1` is refused. Gap: the
    scope is empty, so any read is. A refused call is scope evidence, not a completion call."""
    workflow = closed.fork("scope")
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert call["status"] == "refused"
    assert call["error_code"] == "not_permitted"


def test_snapshot_change_between_read_and_submit_is_stale(closed_positive: Closed) -> None:
    workflow = closed_positive.fork("stale")
    payload = _payload(workflow)
    s1.read_cited(workflow, payload)
    workflow._store.interrupt(workflow._binding.ticket_id, "external change before the submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"


# --- A4 tamper (review M2; lease Acceptance) ----------------------------------------------------


def test_tamper_refusals_on_clones_of_the_closed_positive_run(
    closed_positive: Closed, tmp_path: Path
) -> None:
    closed = closed_positive
    root = tmp_path / "audit"
    root.mkdir()
    for name in ("store", "model"):
        shutil.copytree(closed.root / name, root / name)
    store = Execution(root / "store")

    def verdict(receipt: OwnerRunReceipt) -> str:
        try:
            verify_owner_run_receipt(store, receipt, publication_directory=root / "model")
        except WorkflowError as error:
            return error.code
        return "accepted"

    assert verdict(closed.receipt) == "accepted"

    # (a) a consistent forged CP-3 call: edited body, audit file under its new hash, new seal
    calls = root / "store/owner-run-audit/calls"
    old = next(
        c
        for c in closed.receipt.calls
        if c.binding.module_id == "CP-3"
        and c.tool == "read_pages"
        and c.status == "ok"
        and c.arguments["first_page"] == 2
    )
    assert old.body is not None
    edited = old.model_copy(update={"body": old.body + " "})
    forged = closed.receipt.model_copy(
        update={"calls": tuple(edited if c == old else c for c in closed.receipt.calls)}
    )
    (calls / old.content_hash()).unlink()
    (calls / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    seal = root / "store/owner-run-audit/receipt.sha256"
    seal.write_text(forged.content_hash())
    _verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    with pytest.raises(WorkflowError) as replay:  # ... so the SourceSession replay refuses
        _verify_calls_reads(store, forged, OWNER_SPECS)
    assert replay.value.code == "identity_mismatch"
    assert verdict(forged) == "identity_mismatch"
    (calls / edited.content_hash()).unlink()
    (calls / old.content_hash()).write_bytes(old.model_dump_json().encode())
    seal.write_text(closed.receipt.content_hash())
    assert verdict(closed.receipt) == "accepted"

    # (b) an edited CP-3 relative_value step output: the store's own blob hash check refuses it
    output = attempt_of(store, "CP-3").steps[0].output_sha256 or ""
    blob = root / "store/blobs" / output
    original = blob.read_bytes()
    blob.write_bytes(original + b" ")
    assert verdict(closed.receipt) == "identity_mismatch"
    blob.write_bytes(original)
    assert verdict(closed.receipt) == "accepted"

    # (c) the CP-3 SettledHead: a changed status, and result_sha256 set to "0" * 64
    for change in ({"status": "accepted"}, {"result_sha256": "0" * 64}):
        heads = tuple(
            h.model_copy(update=change) if h.module_id == "CP-3" else h
            for h in closed.receipt.heads
        )
        assert verdict(closed.receipt.model_copy(update={"heads": heads})) == "identity_mismatch"


# --- blocked CP-1A variant (oracle positive.CP-3.blocked_cp1a_variant) --------------------------


@pytest.fixture(scope="module")
def blocked(closed_positive: Closed, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    """The A3b analogue: CP-1A blocked, CP-2 begun under it, then CP-3, CP-MODEL and the receipt."""
    holder = copy.copy(closed_positive)
    root = tmp_path_factory.mktemp("blocked")
    workflow = s1.clone_workflow(closed_positive.promoted, root / "run")
    runs.blocked_through_cp2(workflow, closed_positive.pack, "positive")
    holder.root = root / "run"
    runs.close(workflow, "positive", holder.root / "owner-receipt.json")
    holder.store = Execution(holder.root / "store")
    holder.receipt = OwnerRunReceipt.model_validate_json(
        (holder.root / "owner-receipt.json").read_text()
    )
    holder.facts = {f.fact_id: f for f in head_module(holder.store, "CP-1").facts}
    holder.bindings = runs.cp1_bindings(holder.store, list(ORACLE["submissions"]["figures"]))
    return holder


def test_blocked_cp1a_receipt_verifies_and_the_head_is_re_derived(blocked: Closed) -> None:
    verify_owner_run_receipt(
        blocked.store, blocked.receipt, publication_directory=blocked.root / "model"
    )
    cp3.probe(blocked.store, blocked.store.read(), attempt_of(blocked.store, "CP-3"))
    heads = {h.module_id: h.status for h in blocked.store.read().heads}
    assert heads["CP-1A"] == "blocked"
    assert heads["CP-3"] == "restricted"


def test_blocked_cp1a_variant_equals_the_oracle(blocked: Closed) -> None:
    variant = EXPECTED["positive"]["CP-3"]["blocked_cp1a_variant"]
    module = head_module(blocked.store, "CP-3")
    attempt = attempt_of(blocked.store, "CP-3")
    assert [i.input_id for i in module.inputs] == variant["module_inputs"]
    assert {
        i.input_id: i.status for i in attempt.inputs if i.input_id.startswith("CP-")
    } == variant["input_statuses"]
    candidate = Module.model_validate_json(blocked.store.payload(attempt.payload_sha256 or ""))
    assert list(candidate.limitations) == variant["own_limitations"]
    assert list(module.limitations) == variant["settled_limitations"]
    s1a_tests._compare_tables(fast.table_view(module), cp3_expected_tables(blocked))
    cp1a = head_module(blocked.store, "CP-1A")
    prefixed = [x for x in module.inherited_limitations if x.startswith("Upstream CP-1A blocked: ")]
    assert prefixed == [f"Upstream CP-1A blocked: {x}" for x in cp1a.limitations]
    fast.assert_context(
        blocked.store, attempt, variant["context_block_checks"], blocked_limitations=True
    )


# --- aliases canonicalise (LEAD, Stage 2 round 3) -----------------------------------------------


def test_an_alias_run_counts_no_alias_completion(tmp_path: Path) -> None:
    """A positive R3 run whose pack names CP-3B: the plan, the receipt and the heads name CP-3
    only, and CP-3B stays unregistered. A third CP-1 promotion (the pack hash differs)."""
    store_dir, receipt_path, _ = runs.cp3_closed("positive", tmp_path, requested=ALIAS)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_text())
    assert list(receipt.plan) == RUN["plan_order"]
    assert "CP-3" in {h.module_id for h in receipt.heads}
    assert not [h for h in receipt.heads if "3B" in h.module_id]
    assert not [a for a in Execution(store_dir).read().attempts if "3B" in a.module_id]
    assert "CP-3B" not in OWNER_SPECS
