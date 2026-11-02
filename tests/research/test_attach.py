"""O7c C1: CP-1C and CP-2 bind the settled CP-DR head as a context input (not a dependency edge).

Answer key: ``cases/cpdr-research-owner/expected.json#consumers/*`` and ``#cases/positive/facts``,
read at test time and never edited. The CP-DR heads here are hand-built `Module` objects whose
facts come from the key (a test fixture over a real store, no model, no socket); the closed
runs are the CP-DR owner tests.
"""

import json
from pathlib import Path
from typing import Any, get_args

import cpdr_runs
import pytest
from pydantic import BaseModel, ValidationError

from deploy_vii import cp2_synthesis, registry
from deploy_vii.contracts import Citation, Fact, Input, Module
from deploy_vii.execution import (
    Execution,
    ExecutionSnapshot,
    candidate_issues,
    inherited_limitations,
    invalidate,
)
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owners import cpdr

CPDR = "CP-DR"


def _key(expected: dict[str, Any], *path: str) -> Any:
    node: Any = expected
    for part in path:
        node = node[part]
    return node


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


class Settled:
    """A real store over the CP-DR positive pack with a chosen requested set, settled one module
    at a time as hand-built modules."""

    def __init__(self, root: Path, requested: tuple[str, ...], expected: dict[str, Any]) -> None:
        pack = cpdr_runs.make_pack("positive")
        self.pack = PreparedPack(
            run=pack.run.model_copy(update={"requested_modules": requested}), sources=pack.sources
        )
        self.expected = expected
        self.requested = requested
        self.store = Execution.create(root, self.pack)

    def settle(
        self,
        module_id: str,
        *,
        facts: tuple[Fact, ...] | None = None,
        limitations: tuple[str, ...] | None = None,
    ) -> Module:
        ticket = self.store.begin(module_id)
        if facts is None:
            facts = (
                tuple(_command(m) for m in registry.plan(self.requested))
                if module_id == "CP-0"
                else ()
            )
        module = Module(
            run_id=self.pack.run.run_id,
            issuer_id=self.pack.run.issuer_id,
            as_of=self.pack.run.as_of,
            module_id=module_id,
            status="candidate",
            inputs=ticket.inputs,
            facts=facts,
            limitations=(f"{module_id} note",) if limitations is None else limitations,
        )
        self.store.finish(ticket.ticket_id, module.model_dump_json(), lambda _module: ())
        return module

    def cpdr(self, drop: int = 0) -> Module:
        raw = _key(self.expected, "cases", "positive", "facts")
        facts = tuple(Fact.model_validate_json(json.dumps(item)) for item in raw[: len(raw) - drop])
        own = _key(self.expected, "consumers", "inherited", "cpdr_own")
        return self.settle(CPDR, facts=facts, limitations=tuple(own))

    def head(self, module_id: str) -> Any:
        return next(h for h in self.store.read().heads if h.module_id == module_id)

    def through(self, last: str, *, with_cpdr: bool = True, drop: int = 0) -> None:
        for module_id in registry.plan(self.requested):
            if module_id == CPDR:
                if with_cpdr:
                    self.cpdr(drop)
            else:
                self.settle(module_id)
            if module_id == last:
                break


def _cpdr_input(settled: Settled, expected: dict[str, Any]) -> Input:
    head = settled.head(CPDR)
    assert head.status == _key(expected, "consumers", "positive_status")
    return Input(input_id=CPDR, sha256=head.result_sha256, status=head.status)


@pytest.mark.parametrize(
    ("consumer", "requested", "before"),
    [
        ("CP-1C", ("CP-1", CPDR, "CP-1C"), "CP-1"),
        ("CP-2", ("CP-1", "CP-1A", CPDR, "CP-2"), "CP-1A"),
    ],
)
def test_consumer_input_binds_cpdr_head(
    consumer: str,
    requested: tuple[str, ...],
    before: str,
    expected: dict[str, Any],
    tmp_path: Path,
) -> None:
    assert _key(expected, "consumers", "context_producers", consumer) == [CPDR]
    settled = Settled(tmp_path / "bound", requested, expected)
    settled.through(CPDR)
    ticket = settled.store.begin(consumer)
    want = _cpdr_input(settled, expected)
    assert want in ticket.inputs
    assert [i for i in ticket.inputs if i.input_id == CPDR] == [want]
    # No CP-DR head settled: the consumer still begins and its ticket holds no CP-DR input.
    bare = Settled(tmp_path / "bare", requested, expected)
    bare.through(before, with_cpdr=False)
    assert CPDR not in {i.input_id for i in bare.store.begin(consumer).inputs}


def test_not_a_dependency_edge(expected: dict[str, Any]) -> None:
    assert list(registry.plan(("CP-1C",))) == _key(expected, "consumers", "plan_without_cpdr")
    assert list(registry.plan(("CP-1C", CPDR))) == _key(expected, "consumers", "plan_with_cpdr")
    assert list(registry.plan(("CP-2", CPDR))) == _key(expected, "consumers", "plan_cp2_with_cpdr")
    for consumer in ("CP-1C", "CP-2"):
        assert CPDR not in registry.dependencies(("CP-1C", "CP-2", CPDR))[consumer]


def test_consumer_bound_to_old_head_rejected(expected: dict[str, Any], tmp_path: Path) -> None:
    """A consumer candidate that binds the CP-DR head of another settlement is refused. Two
    stores over one pack settle CP-DR with different facts (a same-input re-settle is a refusal
    of the store), so the second store's CP-DR head differs from the first's."""
    requested = ("CP-1", CPDR, "CP-1C")
    old = Settled(tmp_path / "old", requested, expected)
    old.through(CPDR)
    old_ticket = old.store.begin("CP-1C")
    new = Settled(tmp_path / "new", requested, expected)
    new.through(CPDR, drop=1)
    assert new.head(CPDR).result_sha256 != old.head(CPDR).result_sha256
    attempt = new.store.begin("CP-1C")
    stale = Module(
        run_id=new.pack.run.run_id,
        issuer_id=new.pack.run.issuer_id,
        as_of=new.pack.run.as_of,
        module_id="CP-1C",
        status="candidate",
        inputs=old_ticket.inputs,
        limitations=("CP-1C note",),
    )
    snapshot = new.store.read()
    issues = candidate_issues(snapshot, attempt, stale, pack=new.store.pack(snapshot))
    assert _key(expected, "consumers", "rejection_text") in issues
    fresh = stale.model_copy(update={"inputs": attempt.inputs})
    assert candidate_issues(snapshot, attempt, fresh, pack=new.store.pack(snapshot)) == ()


def test_cpdr_resettle_stales_consumers(expected: dict[str, Any], tmp_path: Path) -> None:
    requested = ("CP-1C", "CP-2", CPDR)
    settled = Settled(tmp_path / "stale", requested, expected)
    settled.through("CP-2")
    snapshot: ExecutionSnapshot = settled.store.read()
    assert {h.module_id for h in snapshot.heads} == set(registry.plan(requested))
    after = {h.module_id: h for h in invalidate(snapshot.heads, CPDR)}
    note = _key(expected, "consumers", "stale_note")
    for consumer in ("CP-1C", "CP-2"):
        assert after[consumer].status == "stale"
        assert note in after[consumer].notes
    for untouched in ("CP-0", "CP-1", "CP-1A", CPDR):
        before = next(h for h in snapshot.heads if h.module_id == untouched)
        assert after[untouched] == before


def test_consumers_inherit_cpdr_limitations(expected: dict[str, Any], tmp_path: Path) -> None:
    requested = ("CP-1", CPDR, "CP-1C")
    settled = Settled(tmp_path / "inherit", requested, expected)
    settled.through("CP-1C")
    head_module = settled.store.head_module(settled.head(CPDR))
    assert list(head_module.limitations) == _key(expected, "consumers", "inherited", "cpdr_own")
    consumer = settled.store.head_module(settled.head("CP-1C"))
    carried = [t for t in consumer.inherited_limitations if t in head_module.limitations]
    assert carried == _key(expected, "consumers", "inherited", "positive")
    # The same rule through `inherited_limitations` over a fresh CP-1C attempt.
    snapshot = settled.store.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-1C")
    again = inherited_limitations(
        snapshot, attempt, consumer.limitations, settled.store.head_module
    )
    assert [t for t in again if t in head_module.limitations] == carried


PLAIN = "The supplied record gives no further basis for a view."


def _cp2_submission() -> Any:
    syn = cp2_synthesis
    return syn.CreditSynthesisSubmission(
        assessment=syn.Assessment(
            rationale=PLAIN,
            category="Insufficient Information",
            confidence="Low",
            cp1a_refs=(),
            limitation=PLAIN,
        ),
        thesis=syn.Thesis(
            text=PLAIN, category="Insufficient Information", cp1a_refs=(), limitation=PLAIN
        ),
        strengths=(),
        weaknesses=(),
        key_findings=(),
        risks=(),
        gaps=(),
    )


def _citation_fields(model: type[BaseModel], prefix: str = "") -> list[str]:
    """Dotted paths of every field typed `Citation`, through nested models and containers."""
    found: list[str] = []
    for name, field in model.model_fields.items():
        pending = [field.annotation]
        while pending:
            node = pending.pop()
            pending.extend(get_args(node))
            if node is Citation:
                found.append(f"{prefix}{name}")
            elif isinstance(node, type) and issubclass(node, BaseModel):
                found.extend(_citation_fields(node, f"{prefix}{name}."))
    return found


def test_cp2_does_not_get_sources(expected: dict[str, Any]) -> None:
    assert _key(expected, "consumers", "cp2", "sources") is False
    assert owner.OWNER_SPECS["CP-2"].steps[0].sources is False
    submission_type = cp2_synthesis.CreditSynthesisSubmission
    held = _citation_fields(submission_type)
    assert held == _key(expected, "consumers", "cp2", "citation_fields")
    payload = json.loads(_cp2_submission().model_dump_json())
    submission_type.model_validate_json(json.dumps(payload))
    with pytest.raises(ValidationError):
        submission_type.model_validate_json(json.dumps({**payload, "citations": []}))
    pack = cpdr_runs.make_pack("positive")

    def module(module_id: str) -> Module:
        return Module(
            run_id=pack.run.run_id,
            issuer_id=pack.run.issuer_id,
            as_of=pack.run.as_of,
            module_id=module_id,
        )

    cp1, cp1a = module("CP-1"), module("CP-1A")
    bound = tuple(
        Input(input_id=m.module_id, sha256=m.content_hash(), status="restricted")
        for m in (cp1, cp1a)
    )
    upstream = cp2_synthesis.Upstream(bound=bound, current=bound, cp1=cp1, cp1a=cp1a, inherited=())
    report = cp2_synthesis.credit_synthesis(pack, _cp2_submission(), upstream)
    claims = cp2_synthesis.cp2_module(report, (), 0).claims
    assert claims and all(claim.citations == () for claim in claims)


# --- O7-R54 H-1: the host authenticates a CP-DR head through its core's probe ----------------------


def _core_settled_store(root: Path) -> Execution:
    """CP-0 and CP-1 hand-built (as `cpdr_runs.settled_pair`), CP-DR settled through its core's
    `submit` (brief, then research): a two-step head."""
    store, ticket = cpdr_runs.locked("positive", root)
    cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, cpdr_runs.research_payload("positive"), None)
    return store


def test_producer_inputs_authenticates_a_core_settled_cpdr_head(tmp_path: Path) -> None:
    store = _core_settled_store(tmp_path / "real")
    head = next(h for h in store.read().heads if h.module_id == CPDR)
    snapshot = store.read()
    module = store.head_module(head)
    assert host._producer_inputs(store, snapshot, module) is True
    # A head the journal would not write is refused: a forged module made the head's result.
    forged = module.model_copy(update={"limitations": (*module.limitations, "forged")})
    cpdr_runs.edit_head(store, CPDR, forged=forged)
    tampered = store.read()
    bad = store.head_module(next(h for h in tampered.heads if h.module_id == CPDR))
    assert host._producer_inputs(store, tampered, bad) is False


def test_producer_inputs_refuses_a_hand_built_cpdr_head(
    expected: dict[str, Any], tmp_path: Path
) -> None:
    settled = Settled(tmp_path / "hand", ("CP-1", CPDR), expected)
    settled.through(CPDR)
    snapshot = settled.store.read()
    module = settled.store.head_module(settled.head(CPDR))
    assert host._producer_inputs(settled.store, snapshot, module) is False


@pytest.fixture(scope="module")
def bound_cpdr_store(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    """Genuine CP-0 and CP-1 (the CP-1 promotion, about two minutes) and a core-settled CP-DR over
    a run that also requests CP-1C; the store is left at the CP-1C step."""
    root = tmp_path_factory.mktemp("bound")
    pack = cpdr_runs.make_pack("positive")
    pack = PreparedPack(
        run=pack.run.model_copy(update={"requested_modules": ("CP-1", CPDR, "CP-1C")}),
        sources=pack.sources,
    )
    cpdr_runs.stage(root)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=None)
    review = json.loads(cpdr_runs.cp0_text(pack, "positive"))
    first = next(row for row in review["consumers"] if row["module_id"] == "CP-1")
    review["consumers"].append({**first, "module_id": "CP-1C"})
    text = json.dumps(review, ensure_ascii=False)
    cpdr_runs.read_cited(workflow, text)
    cpdr_runs._driver("s1a_runs").submit_valid(workflow, text)
    cpdr_runs.drive_cp1(workflow, pack)
    assert cpdr_runs.drive_brief(workflow, "positive")["status"] == "valid"
    assert cpdr_runs.drive_research(workflow, "positive")["status"] == "valid"
    return Execution(root / "store")


def test_cp1c_session_opens_over_a_bound_cpdr_head(
    bound_cpdr_store: Execution, expected: dict[str, Any]
) -> None:
    """Plan row 6's surface: the source session of CP-1C, which binds the CP-DR head, lists the
    key's scope (`#consumers/cp1c_scope/positive_pack`) instead of refusing `identity_mismatch`."""
    snapshot = bound_cpdr_store.read()
    pending = [a for a in snapshot.attempts if a.module_id == "CP-1C" and a.status == "pending"]
    ticket = pending[0] if pending else bound_cpdr_store.begin("CP-1C")
    assert CPDR in {i.input_id for i in ticket.inputs}
    sources = host.session_sources(bound_cpdr_store, ticket.ticket_id, "peer_benchmark")
    assert list(sources) == _key(expected, "consumers", "cp1c_scope", "positive_pack")
