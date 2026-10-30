"""Stage 4 batch 1, classes B (tamper, refusals, tool_use by mechanism) and D.

Class B is two checks and no module-specific verifier code: an analytical spec with no `_PROBES`
row is refused at `create` (the verifier would otherwise reach `_PROBES[module]` with a
`KeyError`), and every owner oracle's `tool_use` section agrees with the registries the verifier
replays from (`OWNER_SPECS`, `host._SOURCE_STEPS`, `_VIEWS`). The oracles are read as data and
never edited.
"""

import importlib
import json
import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import test_owner_g1x as g

from deploy_vii.contracts import Run
from deploy_vii.execution import Attempt, Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow import host
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")

pytest_plugins = ("test_owner_g1x",)  # supplies the g1x fixture
CASES = Path(__file__).resolve().parents[1] / "cases"
MODULE_KEY = re.compile(r"^(CP-[0-9A-Z]+)(?:\s|$)")
SUBMIT_ONLY = ("submit only", "submit-only", "zero ok pack calls", "zero pack calls")
PACK_TOOL_MODULES = ("CP-0", "CP-1", "CP-1A")
READS_INPUTS = re.compile(r"(exactly one (ok )?|one |once per attempt|read_inputs once)")


def _pack_for(module_id: str) -> PreparedPack:
    pack = runs.make_pack("positive")
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = [module_id]
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


def test_analytical_spec_without_a_probe_is_refused_at_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A planned analytical module with no `_PROBES` row is `not_permitted` before anything is
    written, not a `KeyError` at the settlement check of a finished run."""
    pack = _pack_for("CP-1A")
    monkeypatch.setattr(
        owner,
        "_PROBES",
        {m: probe for m, probe in owner._PROBES.items() if m != "CP-1A"},
    )
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.create(tmp_path / "store", pack)
    assert caught.value.code == "not_permitted"
    assert not (tmp_path / "store").exists()
    monkeypatch.undo()
    owner.OwnerWorkflow.create(tmp_path / "store", pack)


def test_every_registered_analytical_spec_has_a_probe_row() -> None:
    assert {m for m, s in owner.OWNER_SPECS.items() if s.kind == "analytical"} <= set(owner._PROBES)


def _tool_use(node: Any) -> list[Any]:
    """Every `tool_use` value anywhere in an oracle document."""
    found: list[Any] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found += [value] if key == "tool_use" else _tool_use(value)
    elif isinstance(node, list):
        for item in node:
            found += _tool_use(item)
    return found


def _sections() -> list[tuple[str, str, str]]:
    """(oracle, module, tool_use text) for every module an owner oracle's `tool_use` names. A
    section keyed by module ids gives one row per key; a flat section belongs to the oracle's
    own module (`cp2d-owner` is CP-2D)."""
    rows: list[tuple[str, str, str]] = []
    for path in sorted(CASES.glob("*-owner/expected.json")):
        oracle = path.parent.name
        own = "CP-" + oracle.removesuffix("-owner")[2:].upper()
        for section in _tool_use(json.loads(path.read_text())):
            keyed = (
                {m.group(1): v for k, v in section.items() if (m := MODULE_KEY.match(k))}
                if isinstance(section, dict)
                else {}
            )
            if keyed:
                rows += [(oracle, module, json.dumps(v).lower()) for module, v in keyed.items()]
            else:
                rows.append((oracle, own, json.dumps(section).lower()))
    return [row for row in rows if row[1] in owner.OWNER_SPECS]


SECTIONS = _sections()


def test_the_oracle_sections_are_found() -> None:
    assert len(SECTIONS) >= 25
    assert {oracle for oracle, _, _ in SECTIONS} >= {
        "cp1c-owner",
        "cp2a-owner",
        "cp2d-owner",
        "cp2e-owner",
        "cp4-owner",
        "cp5-owner",
        "cp8-owner",
        "cpdr-owner",
        "cpl10-owner",
    }


@pytest.mark.parametrize(
    ("oracle", "module", "text"), SECTIONS, ids=[f"{o}:{m}" for o, m, _ in SECTIONS]
)
def test_tool_use_sections_match_registrations(oracle: str, module: str, text: str) -> None:
    """The oracle's tool-use statement and the verifier's replay inputs agree: a submit-only
    module has no source session on any step; a module whose section reads pages has a host
    scope; a module whose section requires `read_inputs` has an inputs mode and a view row, and
    one that reads none has no inputs mode."""
    spec = owner.OWNER_SPECS[module]
    assert spec.kind == "analytical"
    if module in PACK_TOOL_MODULES:
        # CP-0, CP-1 and CP-1A are the pack-tool modules: their sections say "pack tools plus
        # submit" or "as the financial slice" (no `read_pages` phrase to key on), and the host
        # serves a source session on exactly the steps `_SOURCE_STEPS` lists.
        assert {s.step_id for s in spec.steps if s.sources} == set(host._SOURCE_STEPS[module])
        assert host._SOURCE_STEPS[module], (oracle, module)
    if any(phrase in text for phrase in SUBMIT_ONLY):
        assert all(not step.sources for step in spec.steps), (oracle, module)
    if "ok read_pages" in text and not any(p in text for p in SUBMIT_ONLY):
        assert module in host._SOURCE_STEPS, (oracle, module)
        assert {s.step_id for s in spec.steps if s.sources} == set(host._SOURCE_STEPS[module])
    if "zero read_inputs" in text:
        assert all(step.inputs == "none" for step in spec.steps), (oracle, module)
    elif "read_inputs" in text and READS_INPUTS.search(text):
        viewed = [step for step in spec.steps if step.inputs != "none"]
        assert viewed, (oracle, module)
        assert all(step.step_id in owner._VIEWS for step in viewed), (oracle, module)


# Submission steps bind the attempt as begun (adversary Medium 1). A patched core that rewrites a
# repair attempt's begin-set fields in the snapshot of one of its valid steps is the forgery.
def _rewrite(store: Execution, ticket_id: str, **update: Any) -> Attempt:
    snap = store.read()
    att = next(a for a in snap.attempts if a.ticket_id == ticket_id)
    forged = att.model_copy(update=update)
    store._write(
        snap.model_copy(
            update={
                "parent": snap.content_hash(),
                "attempts": tuple(forged if a.ticket_id == ticket_id else a for a in snap.attempts),
            }
        )
    )
    return forged


def _relabel_core(g1x_ns: SimpleNamespace, **update: Any) -> None:
    """After the genuine journal of the repair attempt's first step, rewrite the attempt."""
    real = g1x_ns.core.submit

    def submit(store: Execution, ticket_id: str, step_id: str, payload: str, rules: Any) -> Any:
        out = real(store, ticket_id, step_id, payload, rules)
        if step_id == g.SOURCED and out.journal.number == 1 and out.journal.status == "pending":
            out = replace(out, journal=_rewrite(store, ticket_id, **update))
        return out

    g1x_ns.monkeypatch.setattr(g1x_ns.core, "submit", submit)


def _repaired_run(root: Path) -> Any:
    workflow = g._start(root)
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"  # page never read
    g._drive(workflow)
    return workflow


def test_valid_step_relabelling_a_repair_as_a_first_try_is_refused(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    _relabel_core(g1x, number=0, repair_of=None, repair_issues=())
    with pytest.raises(WorkflowError) as caught:
        _repaired_run(tmp_path).write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "identity_mismatch"


def test_valid_step_rewriting_repair_issues_is_refused(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    _relabel_core(g1x, repair_issues=("an invented first-try issue",))
    with pytest.raises(WorkflowError) as caught:
        _repaired_run(tmp_path).write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "identity_mismatch"


def test_a_genuine_repair_is_accepted(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = _repaired_run(tmp_path).write_receipt(tmp_path / "receipt.json")
    assert g._verdict(tmp_path, receipt) == "accepted"
    assert [a.number for a in g._fake_attempts(tmp_path)] == [0, 1]


# OI-5 (Stage 4 Info 1): a failed publication's attempt must carry the issues the producer's own
# `Execution.interrupt` writes for its interruption. The attempt is the real producer output
# (the g1x fake module stands for the publisher: `_verify_publications` takes the module id and
# replays `Execution.begin`); only the receipt wrapper is a stand-in, as the function reads just
# its `publications` and `model`.
def _failed_publication(
    root: Path, reason: str = "CP-MODEL publication failed: disk full", **forge: Any
) -> tuple[Execution, Any]:
    workflow = g._start(root)
    store = workflow._store
    begun = store.read()
    pending = [a for a in begun.attempts if a.module_id == g.MODULE]
    assert [a.status for a in pending] == ["pending"]
    before = owner._snapshot(store, begun.parent)
    assert not [a for a in before.attempts if a.module_id == g.MODULE]
    ticket = pending[0].ticket_id
    store.interrupt(ticket, reason)
    if forge:
        _rewrite(store, ticket, **forge)
    call = owner.PublicationCall(
        snapshot_before_sha256=before.content_hash(),
        snapshot_after_sha256=store.read().content_hash(),
        status="failed",
        reason=reason,
        ticket_id=ticket,
        files={},
    )
    return store, SimpleNamespace(publications=(call,), model=None)


def test_a_genuine_failed_publication_verifies(g1x: SimpleNamespace, tmp_path: Path) -> None:
    store, receipt = _failed_publication(tmp_path)
    owner._verify_publications(store, receipt, False, g.MODULE)


def test_a_genuine_failed_publication_with_a_long_reason_verifies(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    """The producer shortens the interruption to 300 characters; the replay agrees."""
    store, receipt = _failed_publication(tmp_path, "CP-MODEL publication failed: " + "x" * 500)
    owner._verify_publications(store, receipt, False, g.MODULE)


def test_a_failed_publication_with_rewritten_issues_is_refused(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    store, receipt = _failed_publication(tmp_path, issues=("Looks fine, nothing to repair",))
    with pytest.raises(WorkflowError) as caught:
        owner._verify_publications(store, receipt, False, g.MODULE)
    assert caught.value.code == "identity_mismatch"


def test_a_failed_publication_with_a_rewritten_interruption_is_refused(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    store, receipt = _failed_publication(tmp_path, interruption="something else entirely")
    with pytest.raises(WorkflowError) as caught:
        owner._verify_publications(store, receipt, False, g.MODULE)
    assert caught.value.code == "identity_mismatch"
