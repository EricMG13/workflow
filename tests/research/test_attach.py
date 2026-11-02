"""O7c C1: CP-1C and CP-2 bind the settled CP-DR head as a context input (not a dependency edge).

Answer key: ``cases/cpdr-research-owner/expected.json#consumers/*`` and ``#cases/positive/facts``,
read at test time and never edited. The CP-DR heads here are hand-built `Module` objects whose
facts come from the key (a test fixture over a real store, no model, no socket); the closed
runs are the CP-DR owner tests.
"""

import json
from pathlib import Path
from typing import Any

import cpdr_runs
import pytest
from pydantic import ValidationError

from deploy_vii import cp2_synthesis, registry
from deploy_vii.contracts import Fact, Input, Module
from deploy_vii.execution import (
    Execution,
    ExecutionSnapshot,
    candidate_issues,
    inherited_limitations,
    invalidate,
)
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owner_workflow as owner

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
    again = inherited_limitations(snapshot, attempt, (), settled.store.head_module)
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


def test_cp2_does_not_get_sources(expected: dict[str, Any]) -> None:
    assert _key(expected, "consumers", "cp2", "sources") is False
    assert owner.OWNER_SPECS["CP-2"].steps[0].sources is False
    submission_type = cp2_synthesis.CreditSynthesisSubmission
    held = [n for n, f in submission_type.model_fields.items() if "Citation" in repr(f.annotation)]
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
