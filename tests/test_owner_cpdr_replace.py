"""O7c C4 (OD8): a CP-DR replacement over the same evidence is a replay of CP-0 and CP-1 plus a live
CP-DR, written as a fresh run; added evidence is a fresh run, never a replacement.

The plan and the rerun are tested through `replay.plan_replay` and `replay.replay_module`
(O7-R47 Q12), over the closed `positive` run as the earlier run. Every expected value is read from
`cases/cpdr-research-owner/expected.json` (`#replacement/*`, `#cases/v2`); none is restated.

The earlier run is `cpdr_runs.closed_run("positive")`: the promotion of CP-1 alone takes minutes, and
no fast producer yields the retained submissions replay reads (`settled_pair` stores hand-built
modules and no submissions). So the two tests over it are slow and run in CI only (O7-R57).
"""

import hashlib
import json
import re
from pathlib import Path

import cpdr_runs as runs
import pytest

from deploy_vii.registry import plan
from deploy_workflow.owner_workflow import AUDIT, OwnerWorkflow
from deploy_workflow.replay import (
    ReplayPackChanged,
    ReplayRecord,
    check_same_pack,
    journal_unreplayable,
    plan_replay,
    replay_module,
)


def tree_hash(root: Path) -> str:
    """One digest over every file under `root`: its relative name and its bytes."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


@pytest.fixture(scope="module")
def v1(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return runs.closed_run("positive", tmp_path_factory).root


def test_replacement_plan(v1: Path) -> None:
    expected = runs.oracle()["expected"]["replacement"]
    repaired = frozenset(expected["plan"]["repaired"])
    found = plan_replay(v1, plan(tuple(expected["plan"]["requested"])), repaired)
    assert found.earlier_run_id == expected["supersedes"]
    assert found.replayed == tuple(expected["plan"]["replayed"])
    assert found.live == tuple(expected["plan"]["live"])
    consumers = expected["plan_with_consumers"]
    with_consumers = plan_replay(
        v1,
        plan(tuple(consumers["requested"])),
        frozenset(consumers["repaired"]),
    )
    assert with_consumers.replayed == tuple(consumers["replayed"])
    assert with_consumers.live == tuple(consumers["live"])
    assert with_consumers.unreplayable == tuple(consumers["unreplayable"].items())


def test_replacement_rerun(v1: Path, tmp_path: Path) -> None:
    expected = runs.oracle()["expected"]
    replacement, v2 = expected["replacement"], expected["cases"]["v2"]
    before = tree_hash(v1)
    root = tmp_path / "v2"
    outcome = runs.rerun_from(v1, root)
    assert outcome.outcome == "settled"
    assert outcome.run_id == v2["run_id"]
    assert outcome.run_dir == root
    assert not root.samefile(v1)
    assert tree_hash(v1) == before, replacement["earlier_tree"]
    rebound: dict[str, list[str]] = {}
    for path in sorted((root / "execution" / AUDIT / "replays").iterdir()):
        written = json.loads(path.read_text(encoding="utf-8"))
        if written["schema_version"] != "replay/1":
            continue
        replayed = ReplayRecord.model_validate(written)
        assert replayed.earlier_run_id == replacement["supersedes"]
        if replayed.rebound:
            names = [item.path.rsplit(".", 1)[-1] for item in replayed.rebound]
            rebound[f"{replayed.module_id} {replayed.step_id}"] = names
    assert rebound == replacement["rebound"]
    attachments = json.loads((root / "research" / "attachments.json").read_text(encoding="utf-8"))
    assert attachments["supersedes"] == replacement["supersedes"]
    assert attachments["run_id"] == v2["run_id"]
    # ``rerun_from`` drives no model (it replays and fills recorded literals), so a run directory
    # without calls is the helper's own property; that no replayed step sent a request is not
    # asserted here (the replay records hold none: see the report's ``Not verified``).
    calls = root / "calls.jsonl"
    assert not calls.exists() or calls.read_text(encoding="utf-8") == ""


def test_a_cp1c_repair_replays_cp_dr_over_the_closed_run(v1: Path, tmp_path: Path) -> None:
    """O7 phase fix M-1 (CI only, O7-R57): repairing CP-1C replays CP-0, CP-1 and CP-DR, the research
    step's retained `read_pages` calls included, and no call diverges. CP-1C and what follows run
    live in a real rerun; this node stops after the replays."""
    expected = runs.oracle()["expected"]["replacement"]["plan_with_consumers"]
    root = tmp_path / "v2"
    root.mkdir()
    runs.stage(root)
    execution = root / "execution"
    workflow = OwnerWorkflow.create(execution, runs.make_pack("v2"), publication_directory=None)
    found = plan_replay(v1, plan(tuple(expected["requested"])), frozenset({"CP-1C"}))
    assert "CP-DR" in found.replayed
    journal_unreplayable(found, execution)
    for module_id in found.replayed:
        replay_module(workflow, v1, module_id, execution=execution)
    assert not (execution / AUDIT / "faults").exists()


def test_added_evidence_is_a_fresh_run() -> None:
    text: str = runs.oracle()["expected"]["replacement"]["pack_changed_text"]
    earlier = runs.make_pack("positive")
    check_same_pack(earlier, runs.make_pack("v2"))  # the same sources: only the run id differs
    fourth = runs.evidence_sources()[0].model_copy(update={"source_id": "ev-4"})
    added = runs.make_pack("v2").model_copy(update={"sources": (*earlier.sources, fourth)})
    with pytest.raises(ReplayPackChanged, match=re.escape(text)):
        check_same_pack(earlier, added)
