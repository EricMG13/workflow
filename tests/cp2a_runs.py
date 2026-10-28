"""CP-2A run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed distressed-pathway run (CP-0, CP-1, CP-2A) over the pinned oracle in
`cases/cp2a-owner`, driven through the public `OwnerWorkflow` API only. G2 imports
`cp2a_closed`; `tests/test_owner_cp2a.py` imports the stage functions to fork a run. Nothing
here asserts expected values: the oracle files are read, never derived. CP-0 and the CP-1
stages are the financial slice's (`tests/test_financial_workflow.py`) except the CP-0 consumer
rows and the CP-1 readiness stage (`submissions.json cp1_downstream_review`, markers bound by
`manifest.json run_time_bindings.cp1_readiness`).

STAGE 5 ONLY: a genuine CP-1 promotion, 11-26 minutes per case. Written in Stage 2, never run.
"""

import importlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Fact, Run
from deploy_vii.downstream_readiness import DownstreamInputs
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2a-owner"
FIG = re.compile(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}")
CASES = ("positive", "gap", "refused", "blocked")


def _fw() -> Any:
    return importlib.import_module("test_financial_workflow")


def oracle() -> dict[str, Any]:
    return {
        name: json.loads((CASE / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("manifest", "submissions", "expected")
    }


def make_pack(case: str) -> PreparedPack:
    """The financial pack (identity + financial, `make_pack()`; the financial source missing for
    `refused`) under the case's run."""
    entry = oracle()["manifest"]["cases"][case]
    pack: PreparedPack = _fw().make_pack(gap=case == "refused")
    return PreparedPack(run=Run.model_validate_json(json.dumps(entry["run"])), sources=pack.sources)


def cp0_review(pack: PreparedPack, case: str) -> str:
    """The financial CP-0 review with the CP-2A consumer row added after CP-1's (`refused`: the
    two literal CONDITIONAL rows and the gap row of `submissions.json refused`)."""
    submissions = oracle()["submissions"]
    refused = case == "refused"
    review = json.loads(_fw().readiness(pack, gap=refused))
    if refused:
        rows = submissions["refused"]
        review["consumers"] = [rows["cp0_consumer_row_cp1"], rows["cp0_consumer_row_cp2a"]]
        review["gaps"] = [rows["gap_row"]]
    else:
        review["consumers"] = [*review["consumers"], submissions["cp0_consumer_row_cp2a"]]
    return json.dumps(review, ensure_ascii=False)


def submit_valid(workflow: OwnerWorkflow, payload: str) -> dict[str, Any]:
    outcome = workflow.submit_review(payload)
    if outcome["status"] != "valid":
        raise RuntimeError(f"submission not valid: {outcome['status']} {outcome['issues']}")
    return outcome


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack), pack


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    _fw().read_sources(workflow, gap=case == "refused")
    submit_valid(workflow, cp0_review(pack, case))


def _marker(inputs: DownstreamInputs, name: str) -> str:
    """The `{{EVID:kpi <name>, LTM Q4 25 basis}}` evidence id: the one `kpi` record of key `name`
    displayed on the one `LTM Q4 25` basis record (column_key `LTM:fy-2025`, scope `historical`;
    manifest `run_time_bindings.cp1_readiness.evidence_predicate`). Zero or several fail."""
    records = [
        (r.evidence_id, r.kind, json.loads(r.record_json))
        for r in inputs.narrative.inputs.catalogue
    ]
    bases = [
        rec["basis_id"]
        for _, kind, rec in records
        if kind == "basis"
        and rec.get("label") == "LTM Q4 25"
        and rec.get("column_key") == "LTM:fy-2025"
        and rec.get("scope") == "historical"
    ]
    if len(bases) != 1:
        raise RuntimeError(f"LTM Q4 25 basis records: {len(bases)}, expected exactly one")
    hits = [
        evidence_id
        for evidence_id, kind, rec in records
        if kind == "kpi" and rec.get("key") == name and rec.get("display_basis_id") == bases[0]
    ]
    if len(hits) != 1:
        raise RuntimeError(
            f"kpi {name} records on the LTM basis: {len(hits)}, expected exactly one"
        )
    return hits[0]


def cp1_readiness_literal(store: Execution, ticket_id: str, read: Mapping[str, Any]) -> str:
    """`cp1_downstream_review` with its markers bound: the step's inputs hash, the two evidence
    ids and every narrative gap id (in catalogue order, as separate list elements)."""
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket_id)
    inputs = DownstreamInputs.model_validate_json(
        store.step_output(attempt.steps[-1].output_sha256 or "")
    )
    evidence = {
        f"{{{{EVID:kpi {name}, LTM Q4 25 basis}}}}": _marker(inputs, name)
        for name in ("fcf", "cash_closing")
    }
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]

    def bind(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            out: list[Any] = []
            for item in value:
                if item == "{{ALL narrative gap ids}}":
                    out.extend(gaps)
                else:
                    out.append(bind(item))
            return out
        if value == "{{INPUTS_SHA256}}":
            return read["inputs_sha256"]
        return evidence.get(value, value) if isinstance(value, str) else value

    return json.dumps(bind(oracle()["submissions"]["cp1_downstream_review"]), ensure_ascii=False)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
    """CP-1 to its promotion: the financial slice's stages, with the CP-2A readiness literal."""
    fw = _fw()
    for source in ("identity", "financial"):
        workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
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
    ready = workflow.read_inputs()
    submit_valid(
        workflow, cp1_readiness_literal(workflow._store, workflow._binding.ticket_id, ready)
    )
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


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled; CP-2A begun and untouched (`refused`: CP-0 only). The slow part."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    if case != "refused":
        drive_cp1(workflow, pack)
    return workflow, pack


def fig_bindings(
    store: Execution, read_body: Mapping[str, Any], figures: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token): the one settled CP-1 T4.10 fact labelled `cp1_label`
    (manifest `fact_selection_rule`; zero or several fail), then required to be a `ref` of the
    CP-2A read body with the oracle unit token and spelling."""
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts: tuple[Fact, ...] = store.head_module(cp1).facts
    refs = {entry["ref"]: entry for entry in read_body["cp1_facts"]}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in figures.items():
        hits = [f for f in facts if f.table_id == "T4.10" and f.label == figure["cp1_label"]]
        if len(hits) != 1:
            raise RuntimeError(f"FIG {name}: {len(hits)} candidate CP-1 facts, expected one")
        entry = refs.get(hits[0].fact_id)
        if entry is None or (entry["unit"], entry["shown"]) != (
            figure["unit_token"],
            figure["spelled"],
        ):
            raise RuntimeError(f"FIG {name}: not offered with the oracle unit and spelling")
        bound[name] = (hits[0].fact_id, figure["unit_token"])
    return bound


def bind_figures(text: str, bindings: Mapping[str, tuple[str, str]]) -> str:
    """`{{FIG:name|token}}` -> `{<fact_id>|<token>}`; an unknown name stays and fails closed."""

    def replace(match: re.Match[str]) -> str:
        if match[1] not in bindings or bindings[match[1]][1] != match[2]:
            return match[0]
        return "{" + bindings[match[1]][0] + "|" + match[2] + "}"

    return FIG.sub(replace, text)


def bound_literal(workflow: OwnerWorkflow, payload: Any, body: Mapping[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    figures = oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in FIG.finditer(text))}
    return bind_figures(text, fig_bindings(workflow._store, body, names))


def drive_cp2a(workflow: OwnerWorkflow, case: str) -> dict[str, Any]:
    """The one exact read, then the case's literal `downside_pathway` (figures bound)."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    payload = oracle()["submissions"][case]["downside_pathway"]
    return workflow.submit_review(bound_literal(workflow, payload, body))


def drive_blocked(workflow: OwnerWorkflow) -> None:
    """Attempt 0 payload r01 (rejected), then attempt 1 payload v13 (blocked), each after its
    one read."""
    refusals = {r["id"]: r for r in oracle()["submissions"]["refusals"]}
    for rid in ("r01", "v13"):
        body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
        outcome = workflow.submit_review(bound_literal(workflow, refusals[rid]["payload"], body))
        if outcome["status"] != "invalid":
            raise RuntimeError(f"{rid} not refused: {outcome['status']}")


def cp2a_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-2A run of `case` under `root`: (store, sealed receipt, no publication)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-2A case {case}")
    workflow, _ = promoted(case, root)
    if case == "blocked":
        drive_blocked(workflow)
    elif case != "refused":
        outcome = drive_cp2a(workflow, case)
        if outcome["status"] != "valid":
            raise RuntimeError(f"CP-2A not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", None
