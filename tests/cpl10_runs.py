"""CP-L10 run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed run (CP-0, CP-1 with the downstream-readiness literal, CP-L10) over the pinned oracle
`cases/cpl10-owner`, driven through the public `OwnerWorkflow` API only. G2 imports `cpl10_closed`.
Nothing here asserts expected values: the oracle files are read, never derived.

DEFERRED (Stage 5): this driver and `tests/test_owner_cpl10.py` are written, not run (the CP-1
promotion takes minutes). Every marker the driver cannot bind raises, so a wrong guess about the
CP-1 readiness read fails loudly instead of submitting a half-bound literal.
"""

import importlib
import json
import re
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cpl10-owner"
POSITIVE, LIMITED = "positive", "limited"
EVID = re.compile(r"\{\{EVID:kpi ([a-z_]+), quarter ([1-4])\}\}")
ALL_GAPS = "{{ALL narrative gap ids}}"


def _fw() -> Any:
    return importlib.import_module("test_financial_workflow")


def oracle() -> dict[str, Any]:
    return {
        name: json.loads((CASE / f"{name}.json").read_text())
        for name in ("manifest", "submissions", "expected")
    }


def make_pack() -> PreparedPack:
    """The financial pack (identity + financial, unchanged) under the CP-L10 case's run."""
    run = Run.model_validate_json(json.dumps(oracle()["manifest"]["run"]))
    return PreparedPack(run=run, sources=_fw().make_pack().sources)


def cp0_literal(pack: PreparedPack) -> str:
    """The financial CP-0 literal with the CP-L10 consumer row next to the unchanged CP-1 row."""
    document = json.loads(_fw().readiness(pack))
    document["consumers"].append(oracle()["submissions"]["cp0_consumer_row_cpl10"])
    return json.dumps(document)


def submit_valid(workflow: OwnerWorkflow, payload: str) -> dict[str, Any]:
    outcome = workflow.submit_review(payload)
    if outcome["status"] != "valid":
        raise RuntimeError(f"submission not valid: {outcome['status']} {outcome['issues']}")
    return outcome


def readiness_literal(read_body: str) -> str:
    """`submissions.json#cp1_downstream_review` with its markers bound from the readiness read:
    the FIRST kpi catalogue row of each (key, quarter column), and every narrative gap id."""
    fw = _fw()
    rows = fw.parsed_evidence(read_body)
    columns = {
        str(n): q["column"] for n, q in enumerate(_quarters(), 1)
    }  # '1' -> 'Q1 25 (2025-01-01 to 2025-03-31)'
    text = json.dumps(oracle()["submissions"]["cp1_downstream_review"])

    def evidence(match: re.Match[str]) -> str:
        key, quarter = match[1], match[2]
        for row in rows:
            if row["kind"] == "kpi" and row["key"] == key and row["period"] == columns[quarter]:
                return str(row["evidence_id"])
        raise RuntimeError(f"no kpi evidence for {key}, quarter {quarter}")

    text = EVID.sub(evidence, text)
    gaps = [r["gap_id"] for r in rows if r["kind"] == "gap"]
    if not gaps:
        raise RuntimeError("the readiness read lists no narrative gap")
    document = json.loads(text)
    for consumer in document["consumers"]:
        for gap in consumer["gaps"]:
            gap["gap_ids"] = [g for i in gap["gap_ids"] for g in (gaps if i == ALL_GAPS else [i])]
    try:
        inputs = json.loads(read_body)["inputs_sha256"]
    except (ValueError, KeyError, TypeError):
        inputs = None  # the step pre-fills the hash binding when the read does not state it
    if inputs is None:
        document.pop("inputs_sha256", None)
    else:
        document["inputs_sha256"] = inputs
    return json.dumps(document)


def _quarters() -> list[dict[str, str]]:
    columns = oracle()["manifest"]["fact_selection_rule"]["columns"]
    return [columns[f"Q{n}"] for n in range(1, 5)]


def start(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack()
    return OwnerWorkflow.create(root / "store", pack), pack


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
    _fw().read_sources(workflow)
    submit_valid(workflow, cp0_literal(pack))


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
    """CP-1 to its promotion: the financial case's literal stages, with the CP-L10 downstream
    readiness literal at the readiness stage (the QA built from the read inputs)."""
    fw = _fw()
    for page in (("identity", 1), ("financial", 1)):
        workflow.invoke("read_pages", {"source_id": page[0], "first_page": 1, "last_page": 1})
    workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    submit_valid(workflow, fw.context(pack))
    fw.financial_reads(workflow)
    submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    refused = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    if refused["error_code"] != "not_permitted":
        raise RuntimeError("narrative step offered a source tool")
    submit_valid(workflow, json.dumps(fw.narrative(read)))
    submit_valid(workflow, readiness_literal(workflow.read_inputs()["body"]))
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
    submit_valid(workflow, json.dumps(review))


def promoted(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled; CP-L10 begun and untouched. The slow part."""
    workflow, pack = start(root)
    drive_cp0(workflow, pack)
    drive_cp1(workflow, pack)
    return workflow, pack


def literal(case: str) -> str:
    return json.dumps(oracle()["submissions"][case])


def drive_cp10(workflow: OwnerWorkflow, case: str = POSITIVE, *, text: str | None = None) -> Any:
    """CP-L10's one read (the exact view) and its submit."""
    workflow.read_inputs()
    return workflow.submit_review(literal(case) if text is None else text)


def cpl10_closed(case: str, root: Path) -> tuple[Path, Path]:
    """One closed run of `case` under `root`: (store, sealed receipt)."""
    workflow, _ = promoted(root)
    outcome = drive_cp10(workflow, case)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-L10 not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"
