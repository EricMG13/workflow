"""O7b-1c S1: ``run_pathway(cp_dr=True)`` staging against ``cases/cpdr-research-owner``.

The key is read at test time (``expected.json``, ``manifest.json``) and never edited. The runs use a
recorded adapter with no recordings, so each stops at its first model call, after staging; what is
compared is what staging wrote: the pack, ``research/rejected.json``, ``research/evidence.json`` and
``run.json``.
"""

import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from cpdr_s1_support import (
    FIXTURE,
    ResearchCase,
    key_file,
    off_run_record,
)

from deploy_vii.preparation import load_pack
from deploy_workflow import run_pathway as rp
from deploy_workflow.prompts import factory
from deploy_workflow.prompts.fence import UntrustedItem
from deploy_workflow.research import evidence
from deploy_workflow.research.contracts import BriefInvalid, CpDrNotAnchored
from deploy_workflow.research.intake import IntakeError
from deploy_workflow.run_inputs import check_arguments, stage_sources
from deploy_workflow.run_pathway import run_pathway

AFTER_AS_OF = datetime(2026, 11, 2, 5, 40, 0, tzinfo=UTC)
ON_AS_OF = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(socket, "create_connection", refuse)


def clock(monkeypatch: pytest.MonkeyPatch, moment: datetime) -> None:
    monkeypatch.setattr(evidence, "research_clock", lambda: moment)


def pack_ids(run_dir: Path) -> list[str]:
    ids = [s.source_id for s in load_pack(run_dir / "pack").sources]
    return [i for i in ids if i != "context"]  # the key lists the case's sources, not the context


def run_json(run_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    return loaded


def test_intake_refuses_before_prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan 4 row 1: D (after the cutoff) and E (undated, clock after as_of) are refused at intake,
    listed in rejected.json with the key's texts and bytes, and absent from the pack."""
    clock(monkeypatch, AFTER_AS_OF)
    case = ResearchCase(tmp_path)
    outcome = run_pathway(**case.arguments(tmp_path))
    run_dir = tmp_path / "run"
    assert outcome.outcome == "stopped"  # no recordings: the first model call is the stop
    assert (outcome.stopped_reason or "").startswith("RecordingMissing")
    key = key_file("expected.json")["intake"]
    rejected = (run_dir / "research" / "rejected.json").read_bytes()
    assert rejected.decode("utf-8") == key["rejected_json"]["file_bytes"]
    assert hashlib.sha256(rejected).hexdigest() == key["rejected_json"]["file_sha256"]
    reasons = {e["published"]: e["reason"] for e in json.loads(rejected)}
    assert reasons["2026-02-01"] == key["refusal_texts"]["cutoff"]["text"]
    assert reasons[None] == key["refusal_texts"]["undated"]["text"]
    assert pack_ids(run_dir) == key["pack_sources"]
    assert not any(p.name.startswith(("ev-4", "ev-5")) for p in (run_dir / "sources").iterdir())


def test_evidence_json_records_the_intake_instant_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7-R13: one retrieval time, the intake instant in UTC to the second, on every record."""
    clock(monkeypatch, AFTER_AS_OF.replace(microsecond=987654))
    case = ResearchCase(tmp_path)
    run_pathway(**case.arguments(tmp_path))
    rows = json.loads((tmp_path / "run" / "research" / "evidence.json").read_text("utf-8"))
    accepted = key_file("expected.json")["intake"]["accepted"]
    assert rows == [
        {
            **{k: item[k] for k in ("item_id", "family", "published", "locator", "sha256", "path")},
            "retrieved": "2026-11-02T05:40:00Z",
        }
        for item in accepted
    ]
    for item in accepted:  # the staged copy is the item's text; no second copy under research/
        staged = (tmp_path / "run" / "sources" / f"{item['item_id']}.txt").read_bytes()
        assert hashlib.sha256(staged).hexdigest() == item["sha256"]
    assert sorted(p.name for p in (tmp_path / "run" / "research").iterdir()) == [
        "evidence.json",
        "rejected.json",
    ]


def test_undated_item_is_taken_when_the_clock_is_not_after_as_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock(monkeypatch, ON_AS_OF)
    case = ResearchCase(tmp_path)
    run_pathway(**case.arguments(tmp_path))
    key = key_file("expected.json")["intake"]
    assert pack_ids(tmp_path / "run") == [*key["pack_sources"], "ev-4"]
    refused = json.loads((tmp_path / "run" / "research" / "rejected.json").read_text("utf-8"))
    assert [e["published"] for e in refused] == ["2026-02-01"]


def test_a_manifest_error_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock(monkeypatch, AFTER_AS_OF)
    rows = [{"path": "evidence/a-sector-desk-note.txt", "tag": "research", "family": "x"}]
    case = ResearchCase(tmp_path, rows)
    with pytest.raises(IntakeError, match="locator"):
        run_pathway(**case.arguments(tmp_path))
    assert not (tmp_path / "run").exists()


def test_cp_dr_false_is_byte_identical(tmp_path: Path) -> None:
    """Plan 4 row 3: the same inputs as the fixture, run with this code, give the same run.json
    and the same run_dir tree. The fixture was made by ``off_run_record`` on the 5d4710b1 code."""
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))
    got = off_run_record(tmp_path)
    assert got["run_json"] == pinned["run_json"]
    assert got["tree"] == pinned["tree"]
    assert "cp_dr_lineage" not in json.loads(got["run_json"])


def test_run_json_records_cp_dr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan 4 row 4 (S1 part): the cp_dr keys, the ev-* sources, the three S2b hashes null."""
    clock(monkeypatch, AFTER_AS_OF)
    case = ResearchCase(tmp_path)
    run_pathway(**case.arguments(tmp_path))
    body = run_json(tmp_path / "run")
    key = key_file("expected.json")
    assert body["cp_dr_invoked"] is True
    assert body["cp_dr_lineage"] == key["cp_dr_lineage"]
    assert (
        body["research_manifest_sha256"]
        == (key_file("manifest.json")["research_manifest"]["file_sha256"])
    )
    for hashed in ("cp_dr_brief_sha256", "cp_dr_dossier_sha256", "cp_dr_head_sha256"):
        assert body[hashed] is None
    by_id = {s["source_id"]: s for s in body["sources"]}
    accepted = key["intake"]["accepted"]
    assert [s for s in by_id if s.startswith("ev-")] == [a["item_id"] for a in accepted]
    for item in accepted:
        entry = by_id[item["item_id"]]
        assert entry["path"] == item["path"]  # manifest-relative
        assert entry["media_type"] == "text/plain"
        assert entry["sha256"] == item["sha256"] and entry["converted_sha256"] is None


@pytest.mark.parametrize(
    "fault", [CpDrNotAnchored("CP-0 is blocked"), BriefInvalid("hash mismatch")]
)
def test_research_faults_stop_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: Exception
) -> None:
    """O7-R20: CpDrNotAnchored and BriefInvalid are named faults: the run stops, run.json says
    ``<Type>: <reason>``."""
    clock(monkeypatch, AFTER_AS_OF)
    case = ResearchCase(tmp_path)
    args = case.arguments(tmp_path)
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])

    def prompt_for(pack: object) -> Any:
        def compose(*_: object) -> Any:
            raise fault

        return compose

    outcome = rp._run_pathway(checked, args["run_dir"], args["adapter"], prompt_for)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason == f"{type(fault).__name__}: {fault}"
    assert run_json(args["run_dir"])["stopped_reason"] == outcome.stopped_reason


def test_untrusted_hook_is_passed_only_for_cp_dr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock(monkeypatch, AFTER_AS_OF)
    seen: list[Any] = []
    real = factory.prompt_factory

    def spy(pack: Any, store: Any, **kwargs: Any) -> Any:
        seen.append(kwargs.get("untrusted_for"))
        return real(pack, store, **kwargs)

    monkeypatch.setattr("deploy_workflow.run_pathway.prompt_factory", spy)

    def hook(binding: Any, spec: Any) -> tuple[UntrustedItem, ...]:
        return ()

    for number, cp_dr in enumerate((True, False)):
        base = tmp_path / f"n{number}"
        base.mkdir()
        case = ResearchCase(base)
        args = case.arguments(base, cp_dr=cp_dr)
        if not cp_dr:
            args.pop("research_manifest")
        checked = check_arguments(**args)
        stage_sources(checked, args["run_dir"])
        rp._run_pathway(checked, args["run_dir"], args["adapter"], untrusted_for=hook)
    assert seen == [hook, None]
