"""Closed-run driver over the pinned peers oracle `cases/cpdr-peers-owner` (O7d D2).

One closed relative-value run: CP-0 and CP-1 (the oracle's literals, a genuine CP-1 promotion), CP-DR
(the defaults-only brief, then `submissions.json#research_peers`) and CP-1C (`#cp1c_peers`), driven
through the public `OwnerWorkflow` API. The stage functions are `cpdr_runs`'s, aimed at the peers
oracle for the duration of one run (its `oracle`, pack, run and staging readers are replaced; nothing
else is). Nothing here asserts expected values: the oracle files are read, never derived or edited.

CI ONLY (O7-R57, B16): the CP-1 promotion takes about two minutes. Written in O7d D2 and not run
locally.
"""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import cpdr_runs as runs
import pytest

from deploy_vii.contracts import Run, Source
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.research.intake import AcceptedItem

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cpdr-peers-owner"
CASE_ID = "positive"


def oracle() -> dict[str, Any]:
    """The three pinned oracle files (`cases/PINS.json`); a drifted file fails."""
    pins = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for name in ("manifest", "submissions", "expected"):
        path = CASE / f"{name}.json"
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != pins[f"cases/cpdr-peers-owner/{name}.json"]
        ):
            raise RuntimeError(f"oracle drift: {name}.json")
        out[name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def run_of(_case: str = CASE_ID) -> Run:
    fields = {k: v for k, v in oracle()["manifest"]["run"].items() if k in runs.RUN_FIELDS}
    return Run.model_validate_json(json.dumps(fields))


def context_source() -> Source:
    """The research-minimal context with the oracle's identity, `cp_dr_public` peers, the `auto`
    basis and its one context question (`manifest.json#context`)."""
    manifest = oracle()["manifest"]
    run, context = manifest["run"], manifest["context"]
    document = json.loads(runs.CONTEXT_BASE.read_text(encoding="utf-8"))
    document["run"].update(
        pathway=run["pathway"],
        case_kind=run["case_kind"],
        as_of=run["as_of"],
        reporting_currency=context["reporting_currency"],
    )
    document["identity"].update(issuer_name=run["issuer_name"], issuer_id=run["issuer_id"])
    document["attachments"]["legal_documents"] = "none"
    document["valuation"].update(peer_source=context["peer_source"], basis=context["basis"])
    document["research_questions"] = context["research_questions"]
    raw = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    return prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"), raw
    )


def make_pack(_case: str = CASE_ID) -> PreparedPack:
    """Identity and financial (the financial slice's), `ev-1..3`, then `context`."""
    held = runs._driver("test_financial_workflow").make_pack().sources
    return PreparedPack(run=run_of(), sources=(*held, *runs.evidence_sources(), context_source()))


def accepted_items() -> tuple[AcceptedItem, ...]:
    """`expected.json#intake/accepted` with the text of `manifest.json#evidence`."""
    material = oracle()
    texts = {e["path"]: e["pages"][0]["text"] for e in material["manifest"]["evidence"]}
    return tuple(
        AcceptedItem(
            item_id=a["id"],
            path=a["path"],
            family=a["family"],
            published=date.fromisoformat(a["published"]),
            locator=a["locator"],
            sha256=a["sha256"],
            text=texts[a["path"]],
            origin="supplied",
            url=None,
        )
        for a in material["expected"]["intake"]["accepted"]
    )


def closed_peers_run(factory: pytest.TempPathFactory) -> Path:
    """CP-0, CP-1, CP-DR and CP-1C of the peers oracle over one store, the receipt sealed; the run
    directory (`store/` and `owner-receipt.json` under it)."""
    root = factory.mktemp("cpdr-peers")
    material = oracle()["submissions"]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runs, "oracle", oracle)
        patch.setattr(runs, "make_pack", make_pack)
        patch.setattr(runs, "run_of", run_of)
        patch.setattr(runs, "accepted_items", accepted_items)
        patch.setattr(runs, "refused_items", lambda: ())
        workflow, _pack = runs.promoted(CASE_ID, root)
        brief = runs.drive_brief(workflow, CASE_ID)
        if brief["status"] != "valid":
            raise RuntimeError(f"CP-DR brief not valid: {brief['issues']}")
        research = runs.drive_research(
            workflow, CASE_ID, json.dumps(material["research_peers"], ensure_ascii=False)
        )
        if research["status"] != "valid":
            raise RuntimeError(f"CP-DR research not valid: {research['issues']}")
        runs.run_calls(workflow, material["tool_calls"]["cp1c"])
        closed = workflow.submit_review(json.dumps(material["cp1c_peers"], ensure_ascii=False))
        if closed["status"] != "valid":
            raise RuntimeError(f"CP-1C not valid: {closed['issues']}")
        workflow.write_receipt(root / "owner-receipt.json")
    return root


def cp1c_facts(root: Path) -> dict[str, Any]:
    """The settled CP-1C head's facts by fact id."""
    store = Execution(root / "store")
    head = next(h for h in store.read().heads if h.module_id == "CP-1C")
    return {fact.fact_id: fact for fact in store.head_module(head).facts}
