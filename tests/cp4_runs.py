"""CP-4 run driver: pack assembly, literal submissions, run-time bindings, tool calls.

One closed CP-0 -> CP-1 -> CP-4 run over the pinned oracle in `cases/cp4-owner`, driven through
the public `OwnerWorkflow` API only. G2 imports `cp4_closed`; `tests/test_owner_cp4.py` imports
the stage functions to fork a run at any point. Nothing here asserts expected values: the oracle
files are read, never derived. The pack and the frozen figures come from the Stage 1 test.
"""

import importlib
import json
from pathlib import Path
from typing import Any

from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

s1a: Any = importlib.import_module("s1a_runs")
stage1: Any = importlib.import_module("test_method_cp4")

CASES = ("positive", "gap", "gap_false_same_definition")
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FIG = "<<FIG:net_leverage_reported>>"
METRIC = "net_leverage_reported"
# The oracle's scoped search per case (expected.json execution.tool_use).
SEARCH = {
    "positive": "Covenant EBITDA",
    "gap": "Schedule A",
    "gap_false_same_definition": "Schedule A",
}
# The semantic refusal is corrected by the gap pack's own legal_covenants literal (A3).
CORRECTED = {"gap_false_same_definition": "gap"}


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    """One literal submission as JSON text, the pack hash bound where the oracle marks it. The
    `<<FIG:...>>` placeholder stays in `legal_covenants` until `bind_metric`."""
    value = stage1.SUBMISSIONS[case][name]
    if isinstance(value, str):  # the oracle writes "= <case>.<name>" for a shared literal
        source, _, key = value.removeprefix("= ").partition(".")
        if not value.startswith("= ") or source not in stage1.SUBMISSIONS:
            raise RuntimeError(f"{case}.{name}: not a literal or a reference: {value[:40]}")
        return literal(source, key, pack)
    text = json.dumps(value, ensure_ascii=False)
    return text if pack is None else text.replace(PACK_PLACEHOLDER, pack.content_hash())


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = stage1.make_pack(case)
    return OwnerWorkflow.create(root / "store", pack), pack


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    payload = literal(case, "readiness_review", pack)
    s1a.read_cited(workflow, payload)
    s1a.submit_valid(workflow, payload)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion: the CP-4 oracle's literal source_context (reads of every page it
    cites), then the financial case's literal financials, narrative, readiness and quality."""
    fw = s1a._fw()
    context = literal(case, "cp1_source_context", pack)
    s1a.read_cited(workflow, context)
    s1a.search(workflow, "financial", "subsequent")
    s1a.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    s1a.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    refused = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    if refused["error_code"] != "not_permitted":
        raise RuntimeError("narrative step offered a source tool")
    s1a.submit_valid(workflow, json.dumps(fw.narrative(read)))
    workflow.read_inputs()
    s1a.submit_valid(workflow, json.dumps({"consumers": []}))
    inputs = json.loads(workflow.read_inputs()["body"])
    kpi_ids = {r["evidence_id"] for r in fw.parsed_evidence(read["body"]) if r["kind"] == "kpi"}
    review = {
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "material": True,
                "evidence": [
                    {
                        "evidence_id": evidence_id,
                        "lineage_class": "Calculated"
                        if evidence_id in kpi_ids
                        else "Directly Sourced",
                        "rationale": "Python calculation"
                        if evidence_id in kpi_ids
                        else "Located source balance-sheet observation",
                    }
                    for evidence_id in claim["evidence_ids"]
                ],
                "rationale": "Material historical credit consideration",
            }
            for claim in inputs["claims"]
        ]
    }
    s1a.submit_valid(workflow, json.dumps(review))


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled; CP-4 begun and untouched. The slow part (11-26 minutes)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    drive_cp1(workflow, pack, case)
    return workflow, pack


def drive_reads(workflow: OwnerWorkflow, case: str) -> dict[str, Any]:
    """The oracle's CP-4 tool use before submit: legal-covenants pages 1 to 3 in one call, the
    case's scoped search, and the one `read_inputs` (the exact step_context view, parsed)."""
    call = workflow.invoke(
        "read_pages", {"source_id": "legal-covenants", "first_page": 1, "last_page": 3}
    )
    if call["status"] != "ok":
        raise RuntimeError(f"read_pages legal-covenants: {call['error_code']}")
    s1a.search(workflow, "legal-covenants", SEARCH[case])
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    return body


def metric_ref(store: Execution, body: dict[str, Any]) -> str:
    """The CP-1 fact id for `<<FIG:net_leverage_reported>>` (lease, FIG binding): the one T4.10
    fact of the frozen period and label on the settled CP-1 head, required to be a `ref` of the
    read body with the oracle unit and spelling. Zero or several candidates fail; the equal
    `Q4 25` and `FY25` aliases are never chosen (`s1a.figure_fact`)."""
    head = next(h for h in store.read().heads if h.module_id == "CP-1")
    fact = s1a.figure_fact(store.head_module(head).facts, METRIC)
    entry = next((e for e in body["cp1_facts"] if e["ref"] == fact.fact_id), None)
    figure = stage1.FIGURE
    if entry is None or (entry["unit"], entry["shown"]) != (
        figure["unit_token"],
        figure["spelled"],
    ):
        raise RuntimeError(f"FIG {METRIC}: {fact.fact_id} is not the offered 1.00x ref")
    ref: str = fact.fact_id
    return ref


def bind_metric(text: str, ref: str) -> str:
    return text.replace(FIG, ref)


def drive_cp4(
    workflow: OwnerWorkflow, case: str, body: dict[str, Any], *, name: str | None = None
) -> dict[str, Any]:
    """Submit a literal `legal_covenants` (the case's, or `name`'s) with the metric bound."""
    text = literal(name or case, "legal_covenants")
    return workflow.submit_review(bind_metric(text, metric_ref(workflow._store, body)))


def cp4_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-4 run of `case` under `root`: (store, sealed receipt, no publication). The
    false-same case is refused by the semantic gate, then settles the gap pack's literal on the
    same ticket (lease A3)."""
    workflow, _pack = promoted(case, root)
    body = drive_reads(workflow, case)
    if case in CORRECTED:
        refused = drive_cp4(workflow, case, body)
        if refused["status"] != "refused":
            raise RuntimeError(f"semantic gate did not refuse: {refused['status']}")
    outcome = drive_cp4(workflow, case, body, name=CORRECTED.get(case))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-4 not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", None
