"""CP-DR run driver: pack assembly, literal submissions, run-time bindings, tool-call sequence.

One CP-DR run (CP-0, CP-DR) over the pinned oracle in `cases/cpdr-owner`, driven through the
public `OwnerWorkflow` API only. G2 imports `cpdr_closed`; `tests/test_owner_cpdr.py` imports the
stage functions to fork a run at any point. Nothing here asserts expected values: the oracle
files are read, never derived.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import s1a_runs as s1a

from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/cpdr-owner"
PINS_FILE = ROOT / "cases/PINS.json"
PINNED = ("manifest.json", "submissions.json", "expected.json", "builder/build.py")
PACK_PLACEHOLDER = s1a.PACK_PLACEHOLDER
CASES = ("partial", "unresolved", "empty_agenda")


def oracle() -> dict[str, Any]:
    """The pinned oracle files; a drifted file fails (the pins are `cases/PINS.json`)."""
    pins = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    for name in PINNED:
        digest = hashlib.sha256((CASE / name).read_bytes()).hexdigest()
        if digest != pins[f"cases/cpdr-owner/{name}"]:
            raise RuntimeError(f"oracle drift: {name}")
    return {
        "manifest": json.loads((CASE / "manifest.json").read_text()),
        "submissions": json.loads((CASE / "submissions.json").read_text()),
        "expected": json.loads((CASE / "expected.json").read_text()),
    }


def make_pack() -> PreparedPack:
    """Identity, financial and the reduced business note (the snapshot gap case's sources, hash
    checked against this manifest's pins) under the CP-DR run (`requested_modules = (CP-DR,)`)."""
    manifest = oracle()["manifest"]
    pinned = {s["source_id"]: s["sha256"] for s in manifest["sources"]}
    held = s1a.make_pack("gap").sources
    if {s.source_id: s.sha256 for s in held} != pinned:
        raise RuntimeError("CP-DR source pins drift from the snapshot gap pack")
    return PreparedPack(run=Run.model_validate_json(json.dumps(manifest["run"])), sources=held)


def cp0_text(pack: PreparedPack, *, empty: bool = False) -> str:
    """The CP-0 literal (three-part delta of `manifest.cp0_delta`) with the pack hash bound."""
    key = "cp0_readiness_review_empty_agenda" if empty else "cp0_readiness_review"
    text = json.dumps(oracle()["submissions"][key], ensure_ascii=False)
    return text.replace(PACK_PLACEHOLDER, pack.content_hash())


def literal(case: str) -> str:
    """One CP-DR submission literal as JSON text (`submissions.json#cpdr.<case>`)."""
    return json.dumps(oracle()["submissions"]["cpdr"][case], ensure_ascii=False)


def start(root: Path, *, empty: bool = False) -> tuple[OwnerWorkflow, PreparedPack]:
    """Create the workflow and settle CP-0 (the cited pages read first); CP-DR is then active."""
    pack = make_pack()
    workflow = OwnerWorkflow.create(root / "store", pack)
    payload = cp0_text(pack, empty=empty)
    s1a.read_cited(workflow, payload)
    s1a.submit_valid(workflow, payload)
    return workflow, pack


SOURCE_HEAD = re.compile(r"^<<<SOURCE id=(\S+) sha256=[0-9a-f]{64}>>>$")
SPAN_HEAD = re.compile(r"^locator=(page:\d+) \| ")


def spans_of(body: str) -> list[dict[str, str]]:
    """The (source, locator) pairs a pack tool's body shows, in order."""
    found: list[dict[str, str]] = []
    source = ""
    for line in body.split("\n"):
        head = SOURCE_HEAD.match(line)
        if head:
            source = head[1]
            continue
        span = SPAN_HEAD.match(line)
        if span:
            found.append({"source_id": source, "locator": span[1]})
    return found


def replay(workflow: OwnerWorkflow, calls: list[dict[str, Any]]) -> None:
    """The recorded tool-call sequence: the one `read_inputs`, then each pack call, each ok,
    carrying the oracle's header and the oracle's spans (`expect_spans`, `expect_matching_spans`)."""
    for call in calls:
        if call["tool"] == "read_inputs":
            workflow.read_inputs()
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']}: {outcome['error_code']}")
        header = call.get("expect_header")
        body = outcome["body"] or ""
        if header is not None and header not in body:
            raise RuntimeError(f"{call['tool']}: header {header!r} not in the body")
        for key in ("expect_spans", "expect_matching_spans"):
            if key in call and spans_of(body) != call[key]:
                raise RuntimeError(f"{call['tool']}: {key} differ from the body")


def calls_of(name: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A recorded sequence by name (`submissions.tool_calls.<name>`), or the list itself."""
    if isinstance(name, str):
        found: list[dict[str, Any]] = oracle()["submissions"]["tool_calls"][name]
        return found
    return name


def drive(workflow: OwnerWorkflow, payload: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
    """The recorded tool use, then the submission; returns the submit outcome."""
    replay(workflow, calls)
    return workflow.submit_review(payload)


def cpdr_closed(case: str, root: Path) -> tuple[Path, Path]:
    """One closed CP-DR run of `case` under `root`: (store, sealed receipt)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-DR case: {case}")
    workflow, _ = start(root, empty=case == "empty_agenda")
    outcome = drive(workflow, literal(case), calls_of(case))
    if outcome["status"] != "valid":
        raise RuntimeError(f"submission not valid: {outcome['status']} {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"
