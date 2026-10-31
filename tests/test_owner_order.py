"""CP-MODEL as a stop in the owner walk (Part B O1, G1a; user ruling B1; supersedes the
2026-10-28 round-2 rule that refused an analytical module after CP-MODEL).

The walk stops at the publisher's plan position: the modules planned before CP-MODEL settle,
`publish` runs (in phase `walked`), and the walk resumes after it with the modules planned after
CP-MODEL. `_check_specs` no longer orders analytical modules against the publisher: CP-5's fan-in
excludes CP-MODEL, so nothing in the registry consumes it.

Every fake here is test-only: a CP-3-shaped analytical spec (the G1-X fake owner core registered
under CP-3, whose connection is a separate branch) and registry graphs that the real registry
cannot produce (it plans producers first, and no module requires CP-MODEL). Checks that need a
real CP-1 promotion (11-26 min) are written at the end and skipped here; run them with
`RUN_PROMOTION=1`.
"""

import importlib
import json
import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest

from deploy_vii.registry import plan, step_chain
from deploy_workflow import host
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
g1x: Any = importlib.import_module("test_owner_g1x")
runs: Any = importlib.import_module("s1a_runs")
financial: Any = importlib.import_module("test_financial_workflow")

CP3 = "CP-3"
Graph = dict[str, set[str]]


@pytest.fixture
def cp3(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The G1-X fake owner core registered as `CP-3` (owner-only, one sourced and one viewed
    step), plus the fake registered as `CP-3D`, exactly where a module task registers a core."""
    core = g1x._fake_core()
    spec3 = replace(g1x._fake_spec(), module_id=CP3)
    spec3d = g1x._fake_spec()
    specs = MappingProxyType({**owner.OWNER_SPECS, CP3: spec3, g1x.MODULE: spec3d})
    monkeypatch.setattr(owner, "OWNER_SPECS", specs)
    monkeypatch.setattr(
        owner, "SUPPORTED_ANALYTICAL", owner.SUPPORTED_ANALYTICAL | {CP3, g1x.MODULE}
    )
    for module in (CP3, g1x.MODULE):
        monkeypatch.setitem(owner._CORES, module, core)
        monkeypatch.setitem(owner._QUALIFICATION, module, g1x.QUALIFICATION)
        monkeypatch.setitem(owner._PROBES, module, g1x._probe)
        monkeypatch.setitem(owner._PRECHECKS, module, g1x._precheck)
        monkeypatch.setitem(owner._ENTRY_VALIDATORS, module, g1x._validate)
    monkeypatch.setitem(owner._VIEWS, g1x.SOURCED, g1x._view)
    monkeypatch.setitem(owner._VIEWS, g1x.VIEWED, g1x._view)
    monkeypatch.setattr(owner, "SourceSession", g1x._FakeSession)

    def owner_only(module_id: str) -> Any:
        # CP-3's real chain is its own branch's: here CP-3 stands as an owner-only module.
        if module_id == CP3:
            raise ValueError(f"{module_id} has no live step contract")
        return step_chain(module_id)

    monkeypatch.setattr(owner, "step_chain", owner_only)
    scopes = {**host._OWNER_SCOPES}
    for module in (CP3, g1x.MODULE):
        scopes[(module, g1x.SOURCED)] = lambda _pack: ()
    monkeypatch.setattr(host, "_OWNER_SCOPES", MappingProxyType(scopes))
    yield SimpleNamespace(specs=specs, monkeypatch=monkeypatch)


def _pack(*requested: str) -> Any:
    return g1x._pack(*requested)


def _check(root: Path, pack: Any) -> tuple[str, ...]:
    planned: tuple[str, ...] = owner._check_specs(
        pack, owner.OWNER_SPECS, root / "model", root / "store"
    )
    return planned


def _refuses(root: Path, pack: Any) -> None:
    with pytest.raises(WorkflowError) as caught:
        _check(root, pack)
    assert caught.value.code == "not_permitted"


def _world(monkeypatch: pytest.MonkeyPatch, order: tuple[str, ...], graph: Graph) -> None:
    """A registry the real one cannot produce: `order` is the plan, `graph` its producers."""
    monkeypatch.setattr(owner, "plan", lambda requested: order)
    monkeypatch.setattr(
        owner, "dependencies", lambda requested: {k: set(v) for k, v in graph.items()}
    )


# --- the rule ---------------------------------------------------------------------------------


def test_r3_plan_with_cp3_after_cp_model_passes(cp3: SimpleNamespace, tmp_path: Path) -> None:
    pack = _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3)
    assert plan(pack.run.requested_modules) == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", CP3)
    assert _check(tmp_path, pack) == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", CP3)


def test_unrelated_module_after_cp_model_passes_whatever_its_position(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    assert plan(_pack("CP-1", "CP-MODEL", g1x.MODULE).run.requested_modules) == (
        "CP-0",
        "CP-1",
        g1x.MODULE,
        "CP-MODEL",
    )
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE)
    _world(
        cp3.monkeypatch,
        order,
        {"CP-0": set(), "CP-1": {"CP-0"}, "CP-MODEL": {"CP-1"}, g1x.MODULE: {"CP-0"}},
    )
    assert _check(tmp_path, _pack("CP-1", "CP-MODEL", g1x.MODULE)) == order


CONSUMES: dict[str, Graph] = {
    # the later module requires CP-MODEL
    "direct": {"CP-MODEL": {"CP-1"}, CP3: {"CP-MODEL"}},
    # it requires CP-2, which requires CP-MODEL (CP-2 planned before CP-MODEL: no guard on it)
    "transitive": {"CP-MODEL": {"CP-1"}, "CP-2": {"CP-MODEL"}, CP3: {"CP-2"}},
    # a longer chain
    "deep": {"CP-MODEL": {"CP-1"}, "CP-1A": {"CP-MODEL"}, "CP-2": {"CP-1A"}, CP3: {"CP-2"}},
}
FEEDS: dict[str, Graph] = {
    # CP-MODEL requires the later module
    "direct": {"CP-MODEL": {"CP-1", CP3}},
    # CP-MODEL requires CP-2, which requires the later module
    "transitive": {"CP-MODEL": {"CP-1", "CP-2"}, "CP-2": {CP3}},
    "deep": {"CP-MODEL": {"CP-1", "CP-2"}, "CP-2": {"CP-1A"}, "CP-1A": {CP3}},
}
ORDER = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", CP3)


@pytest.mark.parametrize("shape", sorted(CONSUMES))
def test_module_after_cp_model_that_consumes_it_is_admitted(
    cp3: SimpleNamespace, tmp_path: Path, shape: str
) -> None:
    """Formerly refused (round 2). The walk now stops at CP-MODEL and publishes before the later
    module begins, so a consumer of the CP-MODEL head, direct or through other producers, finds
    it settled. Nothing is written by the check."""
    graph: Graph = {"CP-0": set(), "CP-1": {"CP-0"}, "CP-1A": {"CP-0"}, "CP-2": {"CP-0"}}
    graph.update(CONSUMES[shape])
    _world(cp3.monkeypatch, ORDER, graph)
    assert _check(tmp_path, _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3)) == ORDER
    assert not (tmp_path / "store").exists() and not (tmp_path / "model").exists()


@pytest.mark.parametrize("shape", sorted(FEEDS))
def test_module_after_cp_model_that_feeds_it_is_not_refused_by_the_spec_check(
    cp3: SimpleNamespace, tmp_path: Path, shape: str
) -> None:
    """Formerly refused (round 2). The real `plan` puts producers first, so these graphs cannot
    arise from the registry; the order rule is gone and the spec check admits the plan. A
    publisher whose producer has no settled head at the stop is the terminal refusal (H1,
    `_terminal`), not a pre-flight error."""
    graph: Graph = {
        "CP-0": set(),
        "CP-1": {"CP-0"},
        "CP-1A": {"CP-0"},
        "CP-2": {"CP-0"},
        CP3: {"CP-0"},
    }
    graph.update(FEEDS[shape])
    _world(cp3.monkeypatch, ORDER, graph)
    assert _check(tmp_path, _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3)) == ORDER


def test_consumer_behind_an_unrelated_module_after_cp_model_is_admitted(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """Two modules follow CP-MODEL: CP-3D needs only CP-0, CP-3 requires CP-MODEL; both are
    admitted in plan order (formerly CP-3 was refused whichever module preceded it)."""
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE, CP3)
    graph: Graph = {
        "CP-0": set(),
        "CP-1": {"CP-0"},
        "CP-MODEL": {"CP-1"},
        g1x.MODULE: {"CP-0"},
        CP3: {"CP-0", "CP-MODEL"},
    }
    _world(cp3.monkeypatch, order, graph)
    assert _check(tmp_path, _pack("CP-1", "CP-MODEL", g1x.MODULE, CP3)) == order
    graph[CP3] = {"CP-0"}  # unrelated: admitted too
    assert _check(tmp_path, _pack("CP-1", "CP-MODEL", g1x.MODULE, CP3)) == order


def test_two_deterministic_modules_refuse(cp3: SimpleNamespace, tmp_path: Path) -> None:
    second = replace(owner.OWNER_SPECS["CP-MODEL"], module_id="CP-MODEL-2")
    cp3.monkeypatch.setattr(
        owner, "OWNER_SPECS", MappingProxyType({**owner.OWNER_SPECS, "CP-MODEL-2": second})
    )
    order = ("CP-0", "CP-1", "CP-MODEL", "CP-MODEL-2")
    graph: Graph = {"CP-0": set(), "CP-1": {"CP-0"}, "CP-MODEL": {"CP-1"}, "CP-MODEL-2": {"CP-1"}}
    _world(cp3.monkeypatch, order, graph)
    _refuses(tmp_path, _pack("CP-1", "CP-MODEL"))


def test_admission_still_needs_a_supported_spec(cp3: SimpleNamespace, tmp_path: Path) -> None:
    cp3.monkeypatch.setattr(owner, "SUPPORTED_ANALYTICAL", owner.SUPPORTED_ANALYTICAL - {CP3})
    _refuses(tmp_path, _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3))


# --- invariants 1-3, run through a real store --------------------------------------------------

# The walk runs on the real `Execution` with the fake CP-3D, which needs only CP-0. The plan is
# CP-0, CP-MODEL, CP-3D (CP-MODEL placed before the analytical module); the producer graph gives
# CP-MODEL one producer, `CP-0`, in place of CP-1 so that no promotion is needed. CP-MODEL's own
# publisher is not reached in these runs; the real publication is deferred (below).
WALK = ("CP-0", "CP-MODEL", g1x.MODULE)


def _walk_world(m: pytest.MonkeyPatch, producers: set[str]) -> None:
    _world(m, WALK, {"CP-0": set(), "CP-MODEL": producers, g1x.MODULE: {"CP-0"}})


def _created(root: Path) -> Any:
    return owner.OwnerWorkflow.create(
        root / "store", g1x._pack(), specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )


def _cp0(workflow: Any) -> None:
    review = g1x._cp0_review(g1x._pack())
    runs.read_cited(workflow, review)
    assert workflow.submit_review(review)["status"] == "valid"


def test_walk_order_is_planned_without_the_deterministic_module(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    _walk_world(cp3.monkeypatch, {"CP-0"})
    workflow = _created(tmp_path)
    assert workflow._analytical == ("CP-0", g1x.MODULE)
    _cp0(workflow)
    # CP-MODEL is planned between them: the walk stops there, the module after it is not begun
    assert workflow._phase == "walked" and workflow._resume_after == "CP-MODEL"
    assert [b.module_id for b in workflow._begins] == ["CP-0"]
    assert {a.module_id for a in workflow._store.read().attempts} == {"CP-0"}


def test_publish_waits_for_the_modules_before_cp_model_and_a_clean_failure_keeps_the_stop(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """The WALK world has no CP-1, so its real publisher refuses non-terminally (F1): the stop
    holds, the module after CP-MODEL is never begun, and the retry cap of two applies (F8)."""
    _walk_world(cp3.monkeypatch, {"CP-0"})
    workflow = _created(tmp_path)
    with pytest.raises(WorkflowError) as early:  # not before the modules planned before it
        workflow.publish()
    assert early.value.code == "not_permitted"
    assert workflow._publications == []
    _cp0(workflow)  # CP-0 settled: the stop
    assert workflow._phase == "walked"
    for refused in (workflow.read_inputs, lambda: workflow.submit_review("{}")):
        with pytest.raises(WorkflowError) as stopped:
            refused()
        assert stopped.value.code == "not_permitted"
    for attempt in (1, 2):
        assert workflow.publish()["status"] == "refused"  # no CP-1 in this store
        assert len(workflow._publications) == attempt
        assert workflow._phase == "walked" and workflow._resume_after == "CP-MODEL"
    with pytest.raises(WorkflowError) as capped:
        workflow.publish()
    assert capped.value.code == "not_permitted"
    assert len(workflow._publications) == 2
    assert [b.module_id for b in workflow._begins] == ["CP-0"]  # the walk never resumed


def test_a_blocked_later_module_does_not_refuse_publication(cp3: SimpleNamespace) -> None:
    _walk_world(cp3.monkeypatch, {"CP-0"})
    run = _pack().run
    settled = SimpleNamespace(module_id="CP-0", status="accepted")
    blocked = SimpleNamespace(module_id=g1x.MODULE, status="blocked")
    assert owner._terminal((settled, blocked), run, "CP-MODEL") is False
    assert owner._terminal((blocked,), run, "CP-MODEL") is True  # its own producer unsettled
    assert owner._terminal((), run, "CP-MODEL") is True
    cp3.monkeypatch.setattr(
        owner, "dependencies", lambda requested: {"CP-MODEL": {"CP-0"}, g1x.MODULE: {"CP-0"}}
    )
    assert owner._terminal((settled,), run, "CP-MODEL") is False  # the later module has no head


def _financial_pack(*more: str) -> Any:
    """The financial case with the fake module requested beside CP-1 and CP-MODEL."""
    pack = financial.make_pack()
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = ["CP-1", "CP-MODEL", g1x.MODULE, *more]
    return type(pack)(
        run=type(pack.run).model_validate_json(json.dumps(document)), sources=pack.sources
    )


def _readiness_commanding_module(pack: Any, *more: str) -> str:
    """The financial CP-0 literal with one more consumer row, for the fake module (copied from
    the CP-1 row and renamed)."""
    review = json.loads(financial.readiness(pack))
    row = next(c for c in review["consumers"] if c["module_id"] == "CP-1")
    review["consumers"] = [
        *review["consumers"],
        *({**row, "module_id": module} for module in (g1x.MODULE, *more)),
    ]
    return json.dumps(review)


def _blocked_cp1_then_module(root: Path, *more: str) -> Any:
    """CP-0 valid; CP-1 blocks (four empty submissions, about 0.5 s, no promotion); the module
    planned after CP-MODEL still runs; CP-MODEL's own producer is blocked, so it refuses."""
    pack = _financial_pack(*more)
    workflow = owner.OwnerWorkflow.create(
        root / "store", pack, specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )
    financial.read_sources(workflow)
    assert workflow.submit_review(_readiness_commanding_module(pack, *more))["status"] == "valid"
    for _ in range(4):
        for source in ("identity", "financial"):
            call = workflow.invoke(
                "read_pages", {"source_id": source, "first_page": 1, "last_page": 1}
            )
            assert call["status"] == "ok"
        search = {"query": "subsequent", "source_id": "financial"}
        assert workflow.invoke("search_pack", search)["status"] == "ok"
        assert workflow.submit_review("{}")["status"] == "invalid"
    return workflow


def _terminal_world(cp3: SimpleNamespace, root: Path, order: tuple[str, ...], *more: str) -> Any:
    """CP-1 blocked (CP-MODEL's producer), the walk stopped at CP-MODEL, nothing published."""
    cp3.monkeypatch.setattr(owner, "plan", lambda requested: order)
    return _blocked_cp1_then_module(root, *more)


def _ancestors(store: Any) -> list[str]:
    snapshots = [store.read()]
    while snapshots[-1].parent is not None:
        snapshots.append(owner._snapshot(store, snapshots[-1].parent))
    return [s.content_hash() for s in snapshots]


def test_walk_stops_at_cp_model_then_resumes_after_terminal_refusal(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """The terminal-refusal world (CP-1 blocked), where `publish` refuses terminally (the WALK
    world refuses non-terminally, F1). The `ok`-then-resume case is the RUN_PROMOTION test."""
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE)
    workflow = _terminal_world(cp3, tmp_path, order)
    assert workflow._plan == order
    assert workflow._phase == "walked"  # the stop: CP-1 settled blocked, CP-MODEL is next
    assert workflow._resume_after == "CP-MODEL"
    assert workflow._refused is True  # CP-MODEL's own producer, CP-1, is blocked
    assert g1x.MODULE not in {a.module_id for a in workflow._store.read().attempts}
    with pytest.raises(WorkflowError) as read:
        workflow.read_inputs()
    assert read.value.code == "not_permitted"
    with pytest.raises(WorkflowError) as submitted:
        workflow.submit_review("{}")
    assert submitted.value.code == "not_permitted"
    assert workflow._publications == []
    assert workflow.publish()["status"] == "refused"
    assert len(workflow._publications) == 1
    assert workflow._phase == "analytical" and workflow._resume_after is None
    assert workflow._binding.module_id == g1x.MODULE  # the walk resumed after the stop
    with pytest.raises(WorkflowError) as again:
        workflow.publish()  # the stop is cleared: no second publication
    assert again.value.code == "not_permitted"
    g1x._drive(workflow)
    assert workflow._phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    owner.verify_owner_run_receipt(store, receipt)
    # the publication is not the last transition: the module after CP-MODEL settled after it
    publication = receipt.publications[-1]
    assert publication.snapshot_after_sha256 in _ancestors(store)[1:]
    begun = [b.module_id for b in receipt.begins]  # CP-1 begins twice: attempt 0 and 1
    assert (begun[0], begun[-1]) == ("CP-0", g1x.MODULE)
    assert begun.count(g1x.MODULE) == 1
    assert receipt.plan == order


def test_refusal_after_the_stop_is_bound_to_the_final_snapshot(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """Two modules follow CP-MODEL and the second (CP-1C, which blocks on the blocked CP-1) is
    refused at its begin: the module before it settled in between, so the refusal's snapshot is
    the final one, not the first publication's `before` (F3). Swapping the two is rejected."""
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE, "CP-1C")
    workflow = _terminal_world(cp3, tmp_path, order, "CP-1C")
    assert workflow.publish()["status"] == "refused"
    g1x._drive(workflow)
    assert workflow._phase == "complete" and len(workflow._refusals) == 1
    refusal = workflow._refusals[0]
    assert refusal.module_id == "CP-1C"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    assert refusal.snapshot_sha256 == store.read().content_hash()
    stop = receipt.publications[0].snapshot_before_sha256
    assert stop != refusal.snapshot_sha256  # the module before the refused one settled between
    assert g1x._verdict(tmp_path, receipt) == "accepted"
    forged = refusal.model_copy(update={"snapshot_sha256": stop})
    g1x._swap(tmp_path, "refused-begin", refusal, forged)
    tampered = receipt.model_copy(update={"refusals": (forged,)})
    g1x._reseal(tmp_path, tampered)
    assert g1x._verdict(tmp_path, tampered) == "identity_mismatch"


def test_refusal_before_the_stop_still_lets_cp_model_publish(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """A module planned before CP-MODEL refused at its begin (CP-1C on the blocked CP-1) ends
    the walk at the stop: `publish` refuses terminally and the walk is complete, with no module
    after it begun. The refusal sits on the snapshot the publication started from."""
    order = ("CP-0", "CP-1", "CP-1C", "CP-MODEL", g1x.MODULE)
    workflow = _terminal_world(cp3, tmp_path, order, "CP-1C")
    assert workflow._phase == "walked" and workflow._resume_after is None
    assert [r.module_id for r in workflow._refusals] == ["CP-1C"]
    assert workflow.publish()["status"] == "refused"
    assert workflow._phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(owner.Execution(tmp_path / "store"), receipt)
    assert receipt.refusals[0].snapshot_sha256 == receipt.publications[0].snapshot_before_sha256
    assert g1x.MODULE not in {b.module_id for b in receipt.begins}


def test_a_receipt_from_the_old_no_stop_walk_is_rejected(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """A workflow whose `_advance` begins the next analytical module without stopping at
    CP-MODEL leaves a begin of a later module before the publication; `_verify_chain` binds the
    order (F2)."""
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE)

    def no_stop(self: Any, module_id: str) -> None:
        later = self._analytical[self._analytical.index(module_id) + 1 :]
        if later:
            self._begin(later[0])
        else:
            self._finish_walk()

    cp3.monkeypatch.setattr(owner.OwnerWorkflow, "_advance", no_stop)
    workflow = _terminal_world(cp3, tmp_path, order)
    assert workflow._phase == "analytical"  # the old walk: no stop
    g1x._drive(workflow)
    assert workflow._phase == "walked"
    assert workflow.publish()["status"] == "refused"
    assert workflow._phase == "complete"
    with pytest.raises(WorkflowError) as rejected:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert rejected.value.code == "identity_mismatch"
    # only the order check rejects it: without it the same receipt is accepted
    cp3.monkeypatch.setattr(owner, "_verify_chain", lambda *args: None)
    workflow.write_receipt(tmp_path / "receipt.json")


# --- deferred: need a real CP-1 promotion (11-26 min) -----------------------------------------

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


@promotion
def test_walk_stops_at_cp_model_publishes_ok_and_resumes(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """CP-0 and CP-1 promoted for real: the walk stops at CP-MODEL, `publish` returns ok and the
    walk resumes with the module planned after it; the publication transition sits between the
    modules before and after CP-MODEL, and the sealed receipt verifies with the published
    directory (invariants 1, 3, 4; F1, F11)."""
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE)
    cp3.monkeypatch.setattr(owner, "plan", lambda requested: order)
    pack = runs.make_pack("positive")
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = ["CP-1", "CP-MODEL", g1x.MODULE]
    pack = type(pack)(
        run=type(pack.run).model_validate_json(json.dumps(document)), sources=pack.sources
    )
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, specs=owner.OWNER_SPECS, publication_directory=tmp_path / "model"
    )
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    row = next(c for c in review["consumers"] if c["module_id"] == "CP-1")
    review["consumers"] = [row, {**row, "module_id": g1x.MODULE}]  # only selected modules
    runs.drive_cp0(workflow, pack, "positive", text=json.dumps(review))
    runs.drive_cp1(workflow, pack, "positive")
    assert workflow._phase == "walked"  # the stop: the module after CP-MODEL is not begun
    assert [b.module_id for b in workflow._begins][-1] == "CP-1"
    assert workflow.publish()["status"] == "ok"
    assert len(workflow._publications) == 1
    assert workflow._phase == "analytical" and workflow._binding.module_id == g1x.MODULE
    g1x._drive(workflow)
    assert workflow._phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    owner.verify_owner_run_receipt(store, receipt, publication_directory=tmp_path / "model")
    snapshots = [store.read()]
    while snapshots[-1].parent is not None:
        snapshots.append(owner._snapshot(store, snapshots[-1].parent))
    last = receipt.publications[-1]
    assert last.snapshot_after_sha256 != snapshots[0].content_hash()  # the module settled after it
    assert last.snapshot_after_sha256 in {s.content_hash() for s in snapshots}
    assert [a.module_id for a in snapshots[0].attempts][-1] == g1x.MODULE
    assert [b.module_id for b in receipt.begins][-1] == g1x.MODULE
