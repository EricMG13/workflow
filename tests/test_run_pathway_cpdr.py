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
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cpdr_runs as runs
import o2_case
import pytest
from cpdr_s1_support import (
    FIXTURE,
    ROOT,
    ResearchCase,
    WebCase,
    key_file,
    off_run_record,
    web_file,
)

from deploy_vii.execution import Execution
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import load_pack
from deploy_workflow import run_pathway as rp
from deploy_workflow.model.adapter import AdapterReply
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ToolCall, Turn
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owners import cpdr
from deploy_workflow.prompts import factory
from deploy_workflow.prompts.fence import UntrustedItem
from deploy_workflow.research import contracts as c
from deploy_workflow.research import evidence
from deploy_workflow.research.contracts import BriefInvalid, CpDrNotAnchored
from deploy_workflow.research.intake import IntakeError
from deploy_workflow.run_inputs import ResearchManifestInvalid, check_arguments, stage_sources
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
    reasons = [e["reason"] for e in json.loads(rejected)]
    assert reasons == [
        key["refusal_texts"]["cutoff"]["text"],
        key["refusal_texts"]["undated"]["text"],
    ]
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
            "origin": "supplied",
            "url": None,
        }
        for item in accepted
    ]
    for item in accepted:  # the staged copy is the item's text; no second copy under research/
        staged = (tmp_path / "run" / "sources" / f"{item['item_id']}.txt").read_bytes()
        assert hashlib.sha256(staged).hexdigest() == item["sha256"]
    assert sorted(p.name for p in (tmp_path / "run" / "research").iterdir()) == [
        "evidence.json",
        "manifest.sha256",
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
    assert [e["reason"] for e in refused] == [key["refusal_texts"]["cutoff"]["text"]]


def test_a_manifest_error_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock(monkeypatch, AFTER_AS_OF)
    rows = [{"path": "evidence/a-sector-desk-note.txt", "tag": "research", "family": "x"}]
    case = ResearchCase(tmp_path, rows)
    with pytest.raises(IntakeError, match="locator"):
        run_pathway(**case.arguments(tmp_path))
    assert not (tmp_path / "run").exists()


def test_cp_dr_false_is_byte_identical(tmp_path: Path) -> None:
    """Plan 4 row 3: the same inputs as the fixture, run with this code, give the same run.json
    and the same run_dir tree. The fixture was made by ``off_run_record`` on checkpoint 65d1a180 (O7-R44)."""
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


# --- resume identity (N1) covers the research arguments (S1 fix 1, M-1) -------------------------


def killed_run(
    base: Path, monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]] | None = None
) -> tuple[ResearchCase, dict[str, Any]]:
    """A cp_dr run that stopped at its first model call, with run.json removed (a killed run)."""
    clock(monkeypatch, AFTER_AS_OF)
    case = ResearchCase(base, rows)
    args = case.arguments(base)
    run_pathway(**args)
    (args["run_dir"] / "run.json").unlink()
    return case, args


def test_resume_with_an_edited_manifest_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """p06 (a): accepted items keep their bytes, their metadata changes: not the staged run."""
    case, args = killed_run(tmp_path, monkeypatch)
    rows = json.loads(case.manifest_path.read_text("utf-8"))
    rows[0]["locator"] = "https://edited.example/after-staging"
    case.manifest_path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)
    assert not (args["run_dir"] / "run.json").exists()


def test_resume_with_a_refused_items_metadata_edited_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, args = killed_run(tmp_path, monkeypatch)
    rows = json.loads(case.manifest_path.read_text("utf-8"))
    for row in rows:
        if row.get("published") == "2026-02-01":
            row["family"] = "edited-family"
    case.manifest_path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)


def test_resume_with_a_reformatted_manifest_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same rows, other bytes: run.json would name a manifest hash that is not the staged one."""
    case, args = killed_run(tmp_path, monkeypatch)
    rows = json.loads(case.manifest_path.read_text("utf-8"))
    case.manifest_path.write_text(json.dumps(rows, indent=4), encoding="utf-8")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)


def test_resume_without_cp_dr_of_a_cp_dr_run_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """p06 (b): a manifest that accepted nothing still makes the run a cp_dr run."""
    rows = [
        r
        for r in key_file("manifest.json")["research_manifest"]["rows"]
        if "published" not in r or r["published"] == "2026-02-01"
    ]
    _, args = killed_run(tmp_path, monkeypatch, rows)
    off = {k: v for k, v in args.items() if k != "research_manifest"} | {"cp_dr": False}
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**off, resume=True)
    assert not (args["run_dir"] / "run.json").exists()


def test_resume_refuses_a_tampered_staged_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, args = killed_run(tmp_path, monkeypatch)
    rejected = args["run_dir"] / "research" / "rejected.json"
    rejected.write_bytes(rejected.read_bytes().replace(b"trade-press-archive", b"x", 1))
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)


def test_an_untouched_cp_dr_resume_proceeds_with_the_staged_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, args = killed_run(tmp_path, monkeypatch)
    again = run_pathway(**args, resume=True)
    assert again.outcome == "stopped"
    body = run_json(args["run_dir"])
    assert (
        body["research_manifest_sha256"]
        == (key_file("manifest.json")["research_manifest"]["file_sha256"])
    )


def test_a_deeply_nested_manifest_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L-3: RecursionError from the JSON parse is ResearchManifestInvalid, nothing written."""
    clock(monkeypatch, AFTER_AS_OF)
    case = ResearchCase(tmp_path)
    case.manifest_path.write_text("[" * 200_000 + "]" * 200_000, encoding="utf-8")
    with pytest.raises(ResearchManifestInvalid):
        run_pathway(**case.arguments(tmp_path))
    assert not (tmp_path / "run").exists()


# --- the closed run's run.json, the anchor stop and the terminator body (S2c; plan 4 rows 4, 5, 13) --


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> runs.ClosedRun:
    """The positive case closed and finished by `_finish_run` (shared with `test_owner_cpdr.py`)."""
    return runs.closed_run("positive", tmp_path_factory)


def test_closed_run_json_records_cp_dr(closed: runs.ClosedRun) -> None:
    """Row 4: the `run.json` a closed cp_dr run wrote (not `_cp_dr_keys`) holds the brief hash, the
    dossier hash by `dossier_sha256_rule` and the head hash by `head_hash_rule`."""
    expected = key_file("expected.json")
    positive = expected["cases"]["positive"]
    heads = {h.module_id: h for h in Execution(closed.root / "execution").read().heads}
    _, brief = runs.brief_file(
        positive["brief"]["template_file"],
        heads["CP-0"].result_sha256,
        heads["CP-1"].result_sha256,
    )
    dossier = positive["dossier"]["template_text"].replace("{{BRIEF_SHA256}}", brief)
    body = run_json(closed.root)
    assert (body["outcome"], body["stopped_reason"]) == ("settled", None)
    assert body["cp_dr_invoked"] is True
    assert body["cp_dr_lineage"] == expected["cp_dr_lineage"]
    assert (
        body["research_manifest_sha256"]
        == key_file("manifest.json")["research_manifest"]["file_sha256"]
    )
    assert body["cp_dr_brief_sha256"] == brief
    assert body["cp_dr_dossier_sha256"] == runs.sha(dossier)
    assert body["cp_dr_dossier_sha256"] == runs.sha(
        (closed.root / "research/dossier.md").read_bytes()
    )
    assert body["cp_dr_head_sha256"] == heads["CP-DR"].result_sha256
    assert body["cp_dr_head_sha256"] != body["cp_dr_dossier_sha256"]
    assert body["cp_dr_state"] == expected["run_json"]["cp_dr_state"]["positive"]


def test_attachments_json_is_written_after_the_dossier(closed: runs.ClosedRun) -> None:
    """Row 13 on the closed run `_finish_run` finished: `research/attachments.json` has the key's
    keys and layout, the positive values, and the hashes `run.json` records."""
    want = key_file("expected.json")["attachments"]
    data = (closed.root / "research/attachments.json").read_bytes()
    parsed = json.loads(data)
    assert sorted(parsed) == want["keys"]
    assert data == (json.dumps(parsed, indent=2, sort_keys=True) + "\n").encode()
    for name, value in want["positive"].items():
        assert parsed[name] == value
    body = run_json(closed.root)
    assert parsed["dossier_sha256"] == body["cp_dr_dossier_sha256"]
    assert parsed["brief_sha256"] == body["cp_dr_brief_sha256"]
    assert parsed["run_id"] == body["run_id"]


class BadCp0:
    """Answers every CP-0 request with a review that does not bind the pack: invalid twice, so the
    CP-0 head is blocked and the walk's next begin is CP-DR's."""

    config_id = o2_case.MODEL.config_id
    ruling = None

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, request: Any, *, invocation_digest: str, call_index: int, **_: Any) -> Any:
        self.calls += 1
        submit = [t.name for t in request.tools if t.name.startswith("submit_")][-1]
        reads = [
            ToolCall(
                f"r-{call_index}-{n}",
                "read_pages",
                {
                    "source_id": source,
                    "first_page": int(loc.split(":")[1]),
                    "last_page": int(loc.split(":")[1]),
                },
            )
            for n, (source, loc) in enumerate(sorted(cited_locators(self.payload)))
        ]
        calls = (*reads, ToolCall(f"s-{call_index}", submit, json.loads(self.payload)))
        turn = Turn(
            "", calls, o2_case.USAGE, "tool_use", o2_case.MODEL.model, f"x-{call_index}", 200
        )
        return AdapterReply(
            "ok",
            turn,
            None,
            200,
            None,
            None,
            o2_case.STARTED,
            o2_case.FINISHED,
            o2_case.USAGE,
            None,
        )


def blocked_cp0_run(tmp_path: Path) -> tuple[Any, Any, Any]:
    """Drive the blocked-CP-0 recipe through the real loop; the fault, the adapter and the meta."""
    pack = runs.make_pack("positive")
    runs.stage(tmp_path)
    review = json.loads(runs.cp0_text(pack, "positive"))
    review["pack_sha256"] = "0" * 64
    adapter = BadCp0(json.dumps(review))
    execution = tmp_path / "execution"
    workflow = OwnerWorkflow.create(execution, pack, publication_directory=None)
    checked: Any = SimpleNamespace(
        cp_dr=True,
        research=SimpleNamespace(manifest_sha256="0" * 64, ruling=None),
        model=o2_case.MODEL,
        case_id="cpdr-research-owner",
        pathway=pack.run.pathway,
        run_id=pack.run.run_id,
        cap_usd=Decimal(100),
        gate=None,
    )
    meta = rp._Meta(checked, (), False, Redactor())
    result = rp._drive_and_finish(
        checked,
        tmp_path,
        adapter,
        None,
        meta,
        pack,
        workflow,
        Budget(Decimal(100), execution),
        False,
    )
    return result, adapter, meta


def test_anchor_fault_stops_the_run(tmp_path: Path) -> None:
    """Row 5, `refusals/anchors/blocked_cp0`: the blocked CP-0 head stops the run at CP-DR's begin;
    `run.json.stopped_reason` is the key's `fault_record`, no `brief.json`, and the refusal adds no
    line to `calls.jsonl` (one line per model call, none for CP-DR)."""
    want = key_file("expected.json")["refusals"]["anchors"]["blocked_cp0"]
    result, adapter, meta = blocked_cp0_run(tmp_path)
    assert isinstance(result, rp._Fault)
    outcome = rp._stop(tmp_path, meta, result.reason, result.spent)
    assert outcome.outcome == "stopped"
    assert run_json(tmp_path)["stopped_reason"] == want["fault_record"]
    state = key_file("expected.json")["run_json"]["cp_dr_state"]
    assert run_json(tmp_path)["cp_dr_state"] == state["blocked_cp0"]
    assert not (tmp_path / "research" / "brief.json").exists()
    lines = (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) - adapter.calls == want["calls_jsonl_lines_added"]
    assert all("CP-DR" not in line for line in lines)


def test_a_resumed_run_records_the_bare_anchor_fault(tmp_path: Path) -> None:
    """O7b-1c S6 (S2b re-review I-1): a run killed after the CP-0 call record and before
    `run.json`, on resume, records the key's bare `fault_record`, as a fresh run does (O7-R32)."""
    want = key_file("expected.json")["refusals"]["anchors"]["blocked_cp0"]
    _, _, meta = blocked_cp0_run(tmp_path)
    assert not (tmp_path / "run.json").exists()
    resumed = rp._resume_stop(Budget(Decimal(100), tmp_path / "execution"), tmp_path, meta.redactor)
    assert isinstance(resumed, rp._Fault)
    rp._stop(tmp_path, meta, resumed.reason, resumed.spent)
    assert run_json(tmp_path)["stopped_reason"] == want["fault_record"]


def test_terminator_body_refused_at_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Row 13: the manifest row whose text holds `<<<END>>>` is refused at intake with the key's
    reason suffix and listed in `rejected.json`; it is not in the pack, not in the staged sources
    and not in the research prompt's evidence."""
    clock(monkeypatch, AFTER_AS_OF)
    manifest = key_file("manifest.json")
    item = manifest["fence_terminator_item"]
    terminator = key_file("expected.json")["fence"]["terminator"]
    rows = [
        *json.loads(manifest["research_manifest"]["file_bytes"]),
        {k: item[k] for k in ("path", "tag", "family", "published", "locator")},
    ]
    case = ResearchCase(tmp_path, rows)
    run_pathway(**case.arguments(tmp_path))
    run_dir = tmp_path / "run"
    refused = {
        e["locator"]: e["reason"]
        for e in json.loads((run_dir / "research" / "rejected.json").read_text("utf-8"))
    }
    assert refused[item["locator"]].endswith(terminator["reason_suffix"])
    body = item["pages"][0]["text"]
    staged = [p for sub in ("pack", "sources") for p in (run_dir / sub).rglob("*") if p.is_file()]
    assert staged and not any(
        body in p.read_text(encoding="utf-8", errors="replace") for p in staged
    )
    binding: Any = SimpleNamespace(module_id=cpdr.MODULE_ID, step_id=cpdr.RESEARCH_STEP)
    spec: Any = None
    shown = cpdr.untrusted_items(run_dir / "research")(binding, spec)
    assert shown and all(body not in each.text for each in shown)


def test_context_cutoff_refuses_before_prepare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7b-2 S1 (`cases/cpdr-context-cutoff/expected.json#intake`): a context cutoff earlier than
    the as-of date refuses item B (dated the as-of day) as well as D and E; rejected.json is the
    key's bytes and the pack holds the key's sources."""
    clock(monkeypatch, AFTER_AS_OF)
    key_dir = ROOT / "cases" / "cpdr-context-cutoff"
    case = ResearchCase(tmp_path)  # the evidence files; the manifest and context are the key's
    manifest = json.loads((key_dir / "manifest.json").read_text("utf-8"))
    case.manifest_path.write_bytes(manifest["research_manifest"]["file_bytes"].encode("utf-8"))
    case.context_path.write_bytes((key_dir / "context.json").read_bytes())
    outcome = run_pathway(**case.arguments(tmp_path))
    assert (outcome.stopped_reason or "").startswith("RecordingMissing")
    key = json.loads((key_dir / "expected.json").read_text("utf-8"))["intake"]
    run_dir = tmp_path / "run"
    rejected = (run_dir / "research" / "rejected.json").read_bytes()
    assert rejected.decode("utf-8") == key["rejected_json"]["file_bytes"]
    assert hashlib.sha256(rejected).hexdigest() == key["rejected_json"]["file_sha256"]
    reasons = {e["locator"]: e["reason"] for e in json.loads(rejected)}
    assert reasons[key["refused"][0]["locator"]] == key["refusal_texts"]["cutoff_b"]["text"]
    assert pack_ids(run_dir) == key["pack_sources"]


# ---- the research_ruling argument: web items staged, recorded and checked on resume (O7b-2 S4) ----


def web_run(base: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[WebCase, dict[str, Any]]:
    """A web run (the key's rows, fetched through the key's fakes) that stopped at its first model
    call, after staging."""
    case = WebCase(base)
    case.install(monkeypatch)
    args = case.arguments(base)
    run_pathway(**args)
    return case, args


def test_web_items_are_staged_and_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`#records/{fetches_json/file_bytes,evidence_json/rows,rejected_json/file_bytes,pack_sources}`;
    each staged `sources/ev-<n>.txt` hashes to its row's sha256."""
    _, args = web_run(tmp_path, monkeypatch)
    run_dir = args["run_dir"]
    records = web_file("expected.json")["records"]
    research = run_dir / "research"
    assert (research / "fetches.json").read_bytes().decode("utf-8") == (
        records["fetches_json"]["file_bytes"]
    )
    assert (
        json.loads((research / "evidence.json").read_text("utf-8"))
        == (records["evidence_json"]["rows"])
    )
    assert (research / "rejected.json").read_bytes().decode("utf-8") == (
        records["rejected_json"]["file_bytes"]
    )
    assert pack_ids(run_dir) == records["pack_sources"]
    for row in records["evidence_json"]["rows"]:
        staged = (run_dir / "sources" / f"{row['item_id']}.txt").read_bytes()
        assert hashlib.sha256(staged).hexdigest() == row["sha256"]


def test_web_entries_carry_origin_and_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """S3 review L-6: `_research_entries` carries `origin` and `url` for supplied and web items
    (`#records/evidence_json/rows`); `cpdr._items` carries `origin`."""
    case = WebCase(tmp_path)
    case.install(monkeypatch)
    checked = check_arguments(**case.arguments(tmp_path))
    rows = web_file("expected.json")["records"]["evidence_json"]["rows"]
    entries = rp._research_entries(checked)
    assert [(e["source_id"], e["origin"], e["url"], e["path"]) for e in entries] == [
        (r["item_id"], r["origin"], r["url"], r["path"]) for r in rows
    ]
    items = cpdr._items(rows[:2])  # one supplied and one url item (EvidenceItem has no url)
    assert [(i.item_id, i.origin) for i in items] == [("ev-1", "supplied"), ("ev-2", "web")]


def test_run_json_records_the_research_ruling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`#run_json/{keys,ruling_sha256,ruling_date}`; `#run_json/absent_without_ruling` for the
    supplied-only run."""
    key = web_file("expected.json")["run_json"]
    _, args = web_run(tmp_path / "web", monkeypatch)
    body = run_json(args["run_dir"])
    assert all(name in body for name in key["keys"])
    assert body["research_ruling_sha256"] == key["ruling_sha256"]
    assert body["research_ruling_date"] == key["ruling_date"]
    assert body["research_ruling_path"] == str(args["research_ruling"].resolve())
    clock(monkeypatch, AFTER_AS_OF)
    supplied = ResearchCase(tmp_path / "supplied")
    run_pathway(**supplied.arguments(tmp_path / "supplied"))
    plain = run_json(tmp_path / "supplied" / "run")
    assert key["absent_without_ruling"] is True
    assert not any(name in plain for name in key["keys"])
    assert not (tmp_path / "supplied" / "run" / "research" / "fetches.json").exists()


def test_resume_with_an_edited_fetch_record_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    fetches = args["run_dir"] / "research" / "fetches.json"
    records = json.loads(fetches.read_text("utf-8"))
    records[0]["resolved_ip"] = "93.184.216.99"
    fetches.write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)
    assert not (args["run_dir"] / "run.json").exists()


def test_resume_with_a_reindented_fetch_record_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7b-2 S4 review L-1: `fetches.json` is compared as bytes (`evidence.fetches_bytes`), not as
    parsed records; the key pins the file's sha256 (`#records/fetches_json/file_sha256`)."""
    _, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    fetches = args["run_dir"] / "research" / "fetches.json"
    key = web_file("expected.json")["records"]["fetches_json"]["file_sha256"]
    assert hashlib.sha256(fetches.read_bytes()).hexdigest() == key
    records = json.loads(fetches.read_text("utf-8"))
    fetches.write_text(json.dumps(records, indent=4) + "\n", encoding="utf-8")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**args, resume=True)
    assert not (args["run_dir"] / "run.json").exists()


def test_resume_with_a_removed_fetch_record_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    (args["run_dir"] / "research" / "fetches.json").unlink()
    with pytest.raises(rp.ResumeRefused):
        run_pathway(**args, resume=True)


def test_resume_with_another_ruling_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    other = case.write_ruling("other", case.cases["ruling_texts"]["good"] + "# a later copy\n")
    with pytest.raises(rp.ResumeMismatch):
        run_pathway(**{**args, "research_ruling": other}, resume=True)
    assert not (args["run_dir"] / "run.json").exists()


def test_resume_of_a_web_run_proceeds_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`#records/fetches_json/file_sha256`: the untouched staged record is the key's, and the
    resume goes on to the same stop."""
    _, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    staged = (args["run_dir"] / "research" / "fetches.json").read_bytes()
    assert (
        hashlib.sha256(staged).hexdigest()
        == web_file("expected.json")["records"]["fetches_json"]["file_sha256"]
    )
    again = run_pathway(**args, resume=True)
    assert again.outcome == "stopped"
    assert (
        run_json(args["run_dir"])["research_ruling_sha256"]
        == (web_file("expected.json")["run_json"]["ruling_sha256"])
    )


def test_resume_without_the_ruling_of_a_web_run_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, args = web_run(tmp_path, monkeypatch)
    (args["run_dir"] / "run.json").unlink()
    with pytest.raises(c.EvidenceFetchRefused):
        run_pathway(**{**args, "research_ruling": None}, resume=True)
