"""Phase 7 Task 1: CP-1C's three EV tables, the CP-4C optional edge and the distressed preset.

Reads the registry (`methodology.json`), `PATHWAY_MODULES` and the shipped binding maps. The
frozen manifests under `cases/*-owner` are the answer key for plan order: no Phase 7 change may
move the plan of a run they recorded.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

import pytest

from deploy_vii import registry
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import PATHWAY_MODULES, Fact, Module, ModuleView, PathwayId, Run, View
from deploy_vii.execution import (
    Attempt,
    Command,
    ExecutionSnapshot,
    Head,
    blocked_ancestors,
    current_inputs,
    inherited_limitations,
)

HeadStatus = Literal["accepted", "restricted", "blocked", "stale"]

ROOT = Path(__file__).resolve().parents[1]
NEW_TABLES = ("T1C.9", "T1C.10", "T1C.11")
FROZEN_EIGHT = ("T1C.1", "T1C.2", "T1C.3", "T1C.4", "T1C.5", "T1C.6", "T1C.7", "T1C.8")
DISTRESSED = (
    "CP-0",
    "CP-1",
    "CP-1A",
    "CP-1C",
    "CP-2",
    "CP-2A",
    "CP-2G",
    "CP-2H",
    "CP-4",
    "CP-4C",
    "CP-5",
)
DISTRESSED_PLAN = (
    "CP-0",
    "CP-1",
    "CP-1A",
    "CP-1C",
    "CP-2A",
    "CP-4",
    "CP-2",
    "CP-2G",
    "CP-2H",
    "CP-4C",
    "CP-5",
)
# The five presets Phase 7 leaves alone, spelled out from HEAD (ff1dc983).
OTHER_PRESETS: dict[PathwayId, tuple[str, ...]] = {
    "credit_snapshot": (
        "CP-0",
        "CP-1",
        "CP-MODEL",
        "CP-1A",
        "CP-2",
        "CP-4",
        "CP-3",
        "CP-5",
        "CP-6",
    ),
    "earnings_update": ("CP-0", "CP-1", "CP-MODEL", "CP-1B", "CP-1D", "CP-5"),
    "relative_value": (
        "CP-0",
        "CP-1",
        "CP-MODEL",
        "CP-1C",
        "CP-2",
        "CP-2D",
        "CP-3",
        "CP-3C",
        "CP-3D",
        "CP-5",
    ),
    "covenant_refinancing": (
        "CP-0",
        "CP-1",
        "CP-MODEL",
        "CP-1A",
        "CP-2",
        "CP-2D",
        "CP-4",
        "CP-3C",
        "CP-5",
    ),
    "portfolio_decision": ("CP-0", "CP-1", "CP-MODEL", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8"),
}


def _module(module_id: str) -> registry.Responsibility:
    return next(m for m in registry.modules() if m.module_id == module_id)


def test_cp1c_registers_ev_tables() -> None:
    ids = _module("CP-1C").table_ids
    assert ids[-4:] == ("T1C.8", "T1C.9", "T1C.10", "T1C.11")
    assert set(ids) == {*FROZEN_EIGHT, *NEW_TABLES}
    all_ids = [t for m in registry.modules() for t in m.table_ids]
    assert all(all_ids.count(t) == 1 for t in NEW_TABLES)


def test_cp4c_optional_cp1c_not_required() -> None:
    cp4c = _module("CP-4C")
    assert "CP-1C" in cp4c.optional
    assert "CP-1C" not in cp4c.required
    assert "CP-1C" not in registry.dependencies(("CP-4C",))
    assert registry.edge_rule("CP-4C", "CP-1C") == "restricted"
    both = registry.plan(("CP-4C", "CP-1C"))  # holds without the edge too (file order, P7-P10)
    assert both.index("CP-1C") < both.index("CP-4C")
    assert "CP-1C" in registry.dependencies(("CP-4C", "CP-1C"))["CP-4C"]


def test_distressed_preset_plans_cp1c() -> None:
    assert PATHWAY_MODULES["distressed_restructuring"] == DISTRESSED
    assert registry.plan(DISTRESSED) == DISTRESSED_PLAN


def _run() -> Run:
    return Run(
        run_id="r1",
        issuer_id="i1",
        issuer_name="Issuer",
        as_of=datetime.date(2026, 1, 1),
        case_kind="synthetic",
        pathway="distressed_restructuring",
    )


def _snapshot(heads: tuple[Head, ...]) -> ExecutionSnapshot:
    run = _run()
    return ExecutionSnapshot(run=run, pack_sha256="0" * 64, heads=heads)


def _heads(
    producers: tuple[str, ...], status: HeadStatus = "accepted", ready: str = "CP-4C"
) -> tuple[Head, ...]:
    heads = [
        Head(
            module_id="CP-0",
            status="accepted",
            result_sha256="a" * 64,
            inputs=(),
            commands=(Command(row_id=ready, text=f"Run {ready}"),),
        )
    ]
    for index, module_id in enumerate(producers):
        heads.append(
            Head(
                module_id=module_id,
                status=status,
                result_sha256=f"{index + 1:x}" * 64,
                inputs=(),
            )
        )
    return tuple(heads)


@pytest.mark.parametrize("consumer", ["CP-2", "CP-4C", "CP-5"])
def test_distressed_inputs_bind_cp1c(consumer: str) -> None:
    upstream = DISTRESSED_PLAN[1 : DISTRESSED_PLAN.index(consumer)]
    snapshot = _snapshot(_heads(upstream, ready=consumer))
    bound = {item.input_id: item for item in current_inputs(snapshot, consumer)}
    assert "CP-1C" in bound, sorted(bound)
    assert bound["CP-1C"].status == "accepted"


def test_cp4c_inherits_cp1c_restriction_and_blocked_cp1c_restricts() -> None:
    upstream = tuple(m for m in DISTRESSED_PLAN[1 : DISTRESSED_PLAN.index("CP-4C")])
    heads = list(_heads(upstream, ready="CP-4C"))
    restricted = [
        h.model_copy(update={"status": "restricted"}) if h.module_id == "CP-1C" else h
        for h in heads
    ]
    bound = {i.input_id: i for i in current_inputs(_snapshot(tuple(restricted)), "CP-4C")}
    assert bound["CP-1C"].status == "restricted"
    blocked = [
        h.model_copy(update={"status": "blocked"}) if h.module_id == "CP-1C" else h for h in heads
    ]
    got = {i.input_id: i for i in current_inputs(_snapshot(tuple(blocked)), "CP-4C")}
    assert got["CP-1C"].status == "blocked"  # a blocked optional producer degrades, not refuses
    assert all(i.status == "accepted" for k, i in got.items() if k not in {"CP-1C"})


def _cp1c_limit_module(module_id: str, limits: tuple[str, ...]) -> Module:
    return Module(
        run_id="r1",
        issuer_id="i1",
        as_of=datetime.date(2026, 1, 1),
        module_id=module_id,
        status="restricted" if limits else "accepted",
        limitations=limits,
    )


def _cp4c_inputs(cp1c_status: HeadStatus) -> tuple[ExecutionSnapshot, tuple[Any, ...]]:
    upstream = DISTRESSED_PLAN[1 : DISTRESSED_PLAN.index("CP-4C")]
    heads = tuple(
        h.model_copy(update={"status": cp1c_status}) if h.module_id == "CP-1C" else h
        for h in _heads(upstream, ready="CP-4C")
    )
    snapshot = _snapshot(heads)
    return snapshot, current_inputs(snapshot, "CP-4C")


def test_cp4c_inherits_cp1c_limitations_over_the_preset() -> None:
    """Design 12(c): CP-4C carries the limitations of its bound CP-1C input. The edge is read
    from the registry; the limitation text is the test's own input, so a constant cannot pass."""
    assert "CP-1C" in _module("CP-4C").optional
    snapshot, inputs = _cp4c_inputs("restricted")
    limit = "CP-1C: the EV/EBITDA basis rests on a thin peer set"
    modules = {"CP-1C": _cp1c_limit_module("CP-1C", (limit,))}

    def load(head: Head) -> Module:
        return modules.get(head.module_id) or _cp1c_limit_module(head.module_id, ())

    attempt = Attempt(ticket_id="t1", module_id="CP-4C", inputs=inputs, number=0)
    assert inherited_limitations(snapshot, attempt, (), load) == (limit,)
    assert inherited_limitations(snapshot, attempt, (limit,), load) == ()  # never repeats own


def test_blocked_cp1c_restricts_cp4c_over_the_preset() -> None:
    """Design 12(c): a blocked CP-1C is a blocked ancestor of CP-4C (execution.settle restricts
    CP-4C on any blocked ancestor); an accepted one is not."""
    assert registry.edge_rule("CP-4C", "CP-1C") == "restricted"
    snapshot, inputs = _cp4c_inputs("blocked")
    assert blocked_ancestors(snapshot, inputs) == {"CP-1C"}
    snapshot, inputs = _cp4c_inputs("accepted")
    assert blocked_ancestors(snapshot, inputs) == frozenset()


def test_missing_cp1c_head_refuses_cp2_begin_over_the_preset() -> None:
    """Design 12(c): CP-2 lists CP-1C as optional, and the preset selects it, so CP-2 does not
    begin while CP-1C has no head."""
    assert "CP-1C" in registry.dependencies(DISTRESSED)["CP-2"]
    upstream = DISTRESSED_PLAN[1 : DISTRESSED_PLAN.index("CP-2")]
    without = tuple(m for m in upstream if m != "CP-1C")
    with pytest.raises(ValueError, match="Required upstream is unrun, stale or blocked"):
        current_inputs(_snapshot(_heads(without, ready="CP-2")), "CP-2")
    bound = current_inputs(_snapshot(_heads(upstream, ready="CP-2")), "CP-2")
    assert "CP-1C" in {item.input_id for item in bound}


def test_other_presets_unchanged() -> None:
    for pathway, modules in OTHER_PRESETS.items():
        assert PATHWAY_MODULES[pathway] == modules, pathway
    assert set(PATHWAY_MODULES) == {*OTHER_PRESETS, "distressed_restructuring"}


def test_ev_tables_bound_to_evidence() -> None:
    cp1c = next(m for m in SHIPPED_MAPS if m.module_id == "CP-1C")
    by_table = {e.fact_coord.table_id: e for e in cp1c.entries}
    assert len(by_table) == len(cp1c.entries)
    slots = [by_table[t].cell_slot for t in NEW_TABLES]
    assert slots == ["cp1c-t1c-9", "cp1c-t1c-10", "cp1c-t1c-11"]
    assert len({e.slot for e in cp1c.entries}) == len(cp1c.entries)
    for table in NEW_TABLES:
        entry = by_table[table]
        assert (entry.block_id, entry.unit_class) == ("evidence", "text")
    assert [e.fact_coord.table_id for e in cp1c.entries if e.block_id == "evidence"] == [
        "T1C.2",
        "T1C.6",
        *NEW_TABLES,
    ]


def _fact(table: str, row: str, fact_id: str) -> Fact:
    return Fact(fact_id=fact_id, table_id=table, row_id=row, label="x", text="x", unit="text")


def test_validate_bindings_clean_on_new_tables() -> None:
    facts = tuple(_fact(t, "r1", f"{t}.r1.v") for t in (*FROZEN_EIGHT, *NEW_TABLES))
    run = _run()
    view = View(
        run=run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id="CP-1C",
                title="Peer benchmark",
                aliases=(),
                status="accepted",
                artifact_sha256="a" * 64,
                facts=facts,
            ),
        ),
    )
    assert validate_bindings(view, SHIPPED_MAPS) == ()


def _planned_runs(node: Any) -> list[tuple[tuple[str, ...], list[str]]]:
    found: list[tuple[tuple[str, ...], list[str]]] = []
    if isinstance(node, dict):
        if "plan_order" in node and "requested_modules" in node:
            found.append((tuple(node["requested_modules"]), node["plan_order"]))
        for value in node.values():
            found.extend(_planned_runs(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_planned_runs(value))
    return found


def test_frozen_cases_keep_plan_order() -> None:
    runs = [
        run
        for path in sorted((ROOT / "cases").glob("*-owner/manifest.json"))
        for run in _planned_runs(json.loads(path.read_text()))
    ]
    assert len(runs) >= 8
    for requested, order in runs:
        assert list(registry.plan(requested)) == order, requested


def test_pins_check() -> None:
    done = subprocess.run(
        [sys.executable, "-I", str(ROOT / "cases" / "pins.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
