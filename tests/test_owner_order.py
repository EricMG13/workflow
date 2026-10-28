"""An analytical module after the deterministic CP-MODEL (rulings 2026-10-28 round 2; protocol
G1-X section 5).

`_check_specs` admits an analytical module after CP-MODEL in `planned` only when neither consumes
the other, directly or through `plan`'s producer graph. Publication stays terminal: `publish` runs
once, in phase `walked`, after every planned analytical module has its outcome.

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
def test_module_after_cp_model_that_consumes_it_refuses(
    cp3: SimpleNamespace, tmp_path: Path, shape: str
) -> None:
    graph: Graph = {"CP-0": set(), "CP-1": {"CP-0"}, "CP-1A": {"CP-0"}, "CP-2": {"CP-0"}}
    graph.update(CONSUMES[shape])
    _world(cp3.monkeypatch, ORDER, graph)
    _refuses(tmp_path, _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3))
    assert not (tmp_path / "store").exists() and not (tmp_path / "model").exists()


@pytest.mark.parametrize("shape", sorted(FEEDS))
def test_module_after_cp_model_that_feeds_it_refuses(
    cp3: SimpleNamespace, tmp_path: Path, shape: str
) -> None:
    graph: Graph = {
        "CP-0": set(),
        "CP-1": {"CP-0"},
        "CP-1A": {"CP-0"},
        "CP-2": {"CP-0"},
        CP3: {"CP-0"},
    }
    graph.update(FEEDS[shape])
    _world(cp3.monkeypatch, ORDER, graph)
    _refuses(tmp_path, _pack("CP-1", "CP-MODEL", "CP-1A", "CP-2", CP3))


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
    g1x._drive(workflow)
    assert [b.module_id for b in workflow._begins] == ["CP-0", g1x.MODULE]
    assert {a.module_id for a in workflow._store.read().attempts} == {"CP-0", g1x.MODULE}


def test_publish_waits_for_every_analytical_module_after_cp_model(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    _walk_world(cp3.monkeypatch, {"CP-0"})
    workflow = _created(tmp_path)
    for _ in range(2):  # not before the walk, and a refusal changes nothing
        with pytest.raises(WorkflowError) as early:
            workflow.publish()
        assert early.value.code == "not_permitted"
        assert workflow._publications == []
    _cp0(workflow)  # CP-0 settled, the module after CP-MODEL not yet
    assert workflow._phase == "analytical"
    with pytest.raises(WorkflowError) as middle:
        workflow.publish()
    assert middle.value.code == "not_permitted"
    assert workflow._publications == []
    g1x._drive(workflow)
    assert workflow._phase == "walked"
    result = workflow.publish()  # exactly once, now
    assert len(workflow._publications) == 1
    assert result["status"] == "refused"  # no CP-1 in this store; the real publisher refuses


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


def _financial_pack() -> Any:
    """The financial case with the fake module requested beside CP-1 and CP-MODEL."""
    pack = financial.make_pack()
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = ["CP-1", "CP-MODEL", g1x.MODULE]
    return type(pack)(
        run=type(pack.run).model_validate_json(json.dumps(document)), sources=pack.sources
    )


def _readiness_commanding_module(pack: Any) -> str:
    """The financial CP-0 literal with one more consumer row, for the fake module (copied from
    the CP-1 row and renamed)."""
    review = json.loads(financial.readiness(pack))
    row = next(c for c in review["consumers"] if c["module_id"] == "CP-1")
    review["consumers"] = [*review["consumers"], {**row, "module_id": g1x.MODULE}]
    return json.dumps(review)


def _blocked_cp1_then_module(root: Path) -> Any:
    """CP-0 valid; CP-1 blocks (four empty submissions, about 0.5 s, no promotion); the module
    planned after CP-MODEL still runs; CP-MODEL's own producer is blocked, so it refuses."""
    pack = _financial_pack()
    workflow = owner.OwnerWorkflow.create(
        root / "store", pack, specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )
    financial.read_sources(workflow)
    assert workflow.submit_review(_readiness_commanding_module(pack))["status"] == "valid"
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


def test_later_module_runs_beside_a_refused_publication_and_receipt_verifies(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    order = ("CP-0", "CP-1", "CP-MODEL", g1x.MODULE)
    cp3.monkeypatch.setattr(owner, "plan", lambda requested: order)
    workflow = _blocked_cp1_then_module(tmp_path)
    assert workflow._plan == order
    assert workflow._phase == "analytical"  # the module after CP-MODEL still owes its outcome
    assert workflow._binding.module_id == g1x.MODULE
    assert workflow._refused is True  # CP-MODEL's own producer, CP-1, is blocked
    with pytest.raises(WorkflowError) as early:
        workflow.publish()
    assert early.value.code == "not_permitted"
    assert workflow._publications == []
    g1x._drive(workflow)
    assert workflow._phase == "walked"
    assert workflow.publish()["status"] == "refused"
    assert len(workflow._publications) == 1
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(owner.Execution(tmp_path / "store"), receipt)
    begun = [b.module_id for b in receipt.begins]  # CP-1 begins twice: attempt 0 and 1
    assert (begun[0], begun[-1]) == ("CP-0", g1x.MODULE)
    assert begun.count(g1x.MODULE) == 1
    assert receipt.plan == order


# --- deferred: need a real CP-1 promotion (11-26 min) -----------------------------------------

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


@promotion
def test_publication_is_last_in_the_receipt_chain_and_verifies(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """CP-0 and CP-1 promoted for real, the module after CP-MODEL driven, then CP-MODEL
    published: `publish` runs once after the walk, the publication transition is the last in the
    chain, and the sealed receipt verifies with the published directory (invariants 1, 3, 4)."""
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
    review["consumers"] = [*review["consumers"], {**row, "module_id": g1x.MODULE}]
    runs.drive_cp0(workflow, pack, "positive", text=json.dumps(review))
    runs.drive_cp1(workflow, pack, "positive")
    assert workflow._phase == "analytical"
    g1x._drive(workflow)
    assert workflow._phase == "walked"
    assert workflow.publish()["status"] == "ok"
    assert len(workflow._publications) == 1
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    owner.verify_owner_run_receipt(store, receipt, publication_directory=tmp_path / "model")
    snapshots = [store.read()]
    while snapshots[-1].parent is not None:
        snapshots.append(owner._snapshot(store, snapshots[-1].parent))
    last = receipt.publications[-1]
    assert last.snapshot_after_sha256 == snapshots[0].content_hash()
    assert [a.module_id for a in snapshots[0].attempts][-1] == "CP-MODEL"
    assert [b.module_id for b in receipt.begins][-1] == g1x.MODULE
