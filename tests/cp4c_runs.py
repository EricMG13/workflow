"""CP-4C run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed distressed-pathway run (CP-0, CP-1, CP-2A, CP-4, CP-2G, CP-4C) over the pinned
oracle in `cases/cp4c-owner`, driven through the public `OwnerWorkflow` API only. G2 imports
`cp4c_closed`; `tests/test_owner_cp4c.py` imports the stage functions to fork a run. Nothing
here asserts expected values: the oracle files are read, never derived. The upstream steps
replay the frozen CP-2A, CP-4 and CP-2G literals (`submissions.json upstream_step_literals`)
through their own drivers; CP-0 is the case's `cp0_readiness_review` and the CP-1 readiness
stage is `cases.<case>.cp1_readiness`, its markers bound as in the CP-2A and CP-2G manifests
(`manifest.json run_time_bindings`).

STAGE 5 ONLY: a genuine CP-1 promotion, 11-26 minutes per case. Written in Stage 2, never run.
"""

import importlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp4c-owner"
CASES = ("positive", "gap", "refused", "blocked", "cp2g_blocked")
LITERAL = {  # the case whose literals (packs, CP-0, CP-1, CP-4) a run replays
    "positive": "positive",
    "gap": "gap",
    "blocked": "positive",
    "cp2g_blocked": "positive",
}
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
EVID = re.compile(r"\{\{EVID:kpi ([a-z_]+), LTM Q4 25 basis\}\}")
GAP_MARKER = "{{ALL narrative gap ids}}"
LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
STEP = "restructuring_fulcrum"


def _driver(name: str) -> Any:
    return importlib.import_module(name)


def oracle() -> dict[str, Any]:
    return {
        name: json.loads((CASE / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("manifest", "submissions", "expected")
    }


def upstream_literal(module_id: str) -> dict[str, Any]:
    literal: dict[str, Any] = oracle()["submissions"]["upstream_step_literals"][module_id]
    return literal


def _bound(value: Any, pack: PreparedPack) -> str:
    return json.dumps(value, ensure_ascii=False).replace(PACK_PLACEHOLDER, pack.content_hash())


def make_pack(case: str) -> PreparedPack:
    """The case's run over identity + financial + the case's legal-covenants source (the Stage 1
    test's pack, hash-checked there and against `manifest.json sources`); `refused`: the
    financial slice's pack with the financial source missing."""
    manifest = oracle()["manifest"]
    run = Run.model_validate_json(json.dumps(manifest["cases"][case]["run"]))
    if case == "refused":
        sources = _driver("test_financial_workflow").make_pack(gap=True).sources
        return PreparedPack(run=run, sources=sources)
    literal = LITERAL[case]
    sources = _driver("test_method_cp4c")._pack(literal).sources
    legal = next(s for s in sources if s.source_id == "legal-covenants")
    if legal.sha256 != manifest["sources"]["legal-covenants"][literal]["sha256"]:
        raise RuntimeError("legal-covenants source drift")
    return PreparedPack(run=run, sources=sources)


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack, publication_directory=None), pack


def cp0_review(pack: PreparedPack, case: str) -> str:
    """CP-0's review: the case's literal `cp0_readiness_review` (consumer rows CP-1, CP-2A, CP-4,
    CP-2G, CP-4C), the pack hash bound; `refused`: the financial slice's gap review with the
    literal consumer rows and gap row of `submissions.json refused`."""
    submissions = oracle()["submissions"]
    if case == "refused":
        review = json.loads(_driver("test_financial_workflow").readiness(pack, gap=True))
        rows = submissions["refused"]
        review["consumers"] = list(rows["cp0_consumer_rows"].values())
        review["gaps"] = [rows["gap_row"]]
        return json.dumps(review, ensure_ascii=False)
    return _bound(submissions["cases"][LITERAL[case]]["cp0_readiness_review"], pack)


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> dict[str, Any]:
    s1a = _driver("s1a_runs")
    review = cp0_review(pack, case)
    if case == "refused":
        _driver("test_financial_workflow").read_sources(workflow, gap=True)
        outcome: dict[str, Any] = workflow.submit_review(review)
        return outcome
    s1a.read_cited(workflow, review)
    submitted: dict[str, Any] = s1a.submit_valid(workflow, review)
    return submitted


def readiness_literal(workflow: OwnerWorkflow, case: str, read: Mapping[str, Any]) -> str:
    """`cases.<case>.cp1_readiness` with its markers bound to the readiness step's inputs:
    `{{INPUTS_SHA256}}` the read's hash; `{{EVID:kpi key, LTM Q4 25 basis}}` by the CP-2A
    driver's own rule; the gap marker list element expands to every narrative gap id. An
    unknown marker fails closed."""
    cp1d_runs, cp2a_runs = _driver("cp1d_runs"), _driver("cp2a_runs")
    inputs = cp1d_runs.downstream_inputs(workflow)
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]

    def scalar(value: str) -> str:
        if value == "{{INPUTS_SHA256}}":
            return str(read["inputs_sha256"])
        if match := EVID.fullmatch(value):
            return str(cp2a_runs._marker(inputs, match[1]))
        if "{{" in value:
            raise RuntimeError(f"unbound readiness marker {value}")
        return value

    def bind(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            out: list[Any] = []
            for item in value:
                out.extend(gaps if item == GAP_MARKER else [bind(item)])
            return out
        return scalar(value) if isinstance(value, str) else value

    literal = oracle()["submissions"]["cases"][LITERAL[case]]["cp1_readiness"]
    return json.dumps(bind(_driver("cp2g_runs").readiness_payload(literal)), ensure_ascii=False)


def _quality_review(fw: Any, read: Mapping[str, Any], inputs: Mapping[str, Any]) -> str:
    """The financial slice's quality review over the read inputs (as the CP-2A driver)."""
    kpi_ids = {r["evidence_id"] for r in fw.parsed_evidence(read["body"]) if r["kind"] == "kpi"}
    return json.dumps(
        {
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
    )


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion on the legal pack: the frozen CP-4 `cp1_source_context` (reads of
    every page it cites), the financial slice's financials and narrative, the combined readiness
    literal and the quality review built from the read inputs."""
    fw, s1a = _driver("test_financial_workflow"), _driver("s1a_runs")
    context = _bound(upstream_literal("CP-4")[LITERAL[case]]["cp1_source_context"], pack)
    s1a.read_cited(workflow, context)
    s1a.search(workflow, "financial", "subsequent")
    s1a.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    s1a.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    s1a.submit_valid(workflow, json.dumps(fw.narrative(read)))
    ready = workflow.read_inputs()
    s1a.submit_valid(workflow, readiness_literal(workflow, case, ready))
    inputs = json.loads(workflow.read_inputs()["body"])
    s1a.submit_valid(workflow, _quality_review(fw, read, inputs))


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled, CP-2A begun and untouched (`refused`: CP-0 only)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    if case != "refused":
        drive_cp1(workflow, pack, case)
    return workflow, pack


def drive_cp2a(workflow: OwnerWorkflow) -> None:
    """The one exact read, then the frozen CP-2A positive literal (CP-2A figures bound)."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    payload = upstream_literal("CP-2A")["downside_pathway"]
    outcome = workflow.submit_review(_driver("cp2a_runs").bound_literal(workflow, payload, body))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2A not valid: {outcome['issues']}")


def drive_cp4(workflow: OwnerWorkflow, case: str) -> None:
    """The frozen CP-4 tool sequence (legal-covenants pages 1 to 3, the scoped search, one
    read), then the frozen CP-4 `legal_covenants` literal with its metric bound."""
    cp4_runs = _driver("cp4_runs")
    body = cp4_runs.drive_reads(workflow, LITERAL[case])
    text = json.dumps(upstream_literal("CP-4")[LITERAL[case]]["legal_covenants"])
    outcome = workflow.submit_review(
        cp4_runs.bind_metric(text, cp4_runs.metric_ref(workflow._store, body))
    )
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-4 not valid: {outcome['issues']}")


def drive_cp2g(workflow: OwnerWorkflow) -> None:
    """CP-2G's one exact read, then the frozen CP-2G gap literal (CP-2G figures bound)."""
    outcome = _driver("cp2g_runs").drive_cp2g(
        workflow, upstream_literal("CP-2G")["forward_credit_model"]
    )
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2G not valid: {outcome['issues']}")


def ready(case: str, root: Path) -> OwnerWorkflow:
    """Every upstream settled in plan order and CP-4C begun, untouched (positive, gap,
    blocked): the state the A3 clones fork."""
    workflow, _ = promoted(case, root)
    drive_cp2a(workflow)
    drive_cp4(workflow, case)
    drive_cp2g(workflow)
    return workflow


def read_view(workflow: OwnerWorkflow, case: str) -> dict[str, Any]:
    """The case's frozen CP-4C tool sequence (`cases.<case>.tool_calls`): the one exact read,
    then the scoped searches and the reads of every page the literal cites. Returns the view."""
    body: dict[str, Any] = {}
    for call in oracle()["submissions"]["cases"][LITERAL[case]]["tool_calls"]:
        if call["tool"] == "read_inputs":
            body = json.loads(workflow.read_inputs()["body"])
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {outcome['error_code']}")
    return body


def fig_bindings(
    workflow: OwnerWorkflow, body: Mapping[str, Any], names: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token) by `run_time_bindings.figure_placeholders`: a cp1 name is
    the one settled CP-1 T4.10 fact labelled `<LTM column> · <metric>` (zero or several fail),
    a cp2g name its literal id; either must be a `cp1_facts` or `cp2g_facts` ref of the view
    with the oracle unit token."""
    store = workflow._store
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(cp1).facts
    refs = {e["ref"]: e for e in (*body["cp1_facts"], *body["cp2g_facts"])}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in names.items():
        if figure["source"] == "cp2g":
            fact_id = str(figure["fact_id"])
        else:
            label = f"{LTM_LABEL} · {figure['metric']}"
            hits = [f for f in facts if f.table_id == "T4.10" and f.label == label]
            if len(hits) != 1:
                raise RuntimeError(f"FIG {name}: {len(hits)} candidate CP-1 facts, expected one")
            fact_id = hits[0].fact_id
        entry = refs.get(fact_id)
        if entry is None or entry["unit"] != figure["unit_token"]:
            raise RuntimeError(f"FIG {name}: not offered with the oracle unit")
        bound[name] = (fact_id, figure["unit_token"])
    return bound


def bound_literal(workflow: OwnerWorkflow, payload: Any, body: Mapping[str, Any]) -> str:
    """`{{FIG:name|token}}` -> `{<fact_id>|<token>}`; an unknown name stays and fails closed."""
    text = json.dumps(payload, ensure_ascii=False)
    figures = oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in FIG.finditer(text)) if n in figures}
    bindings = fig_bindings(workflow, body, names)

    def replace(match: re.Match[str]) -> str:
        hit = bindings.get(match[1])
        return (
            match[0] if hit is None or hit[1] != match[2] else "{" + hit[0] + "|" + match[2] + "}"
        )

    return FIG.sub(replace, text)


def drive_cp4c(workflow: OwnerWorkflow, case: str, payload: Any) -> dict[str, Any]:
    """The frozen CP-4C tool sequence, then `payload` with figures bound."""
    body = read_view(workflow, case)
    outcome: dict[str, Any] = workflow.submit_review(bound_literal(workflow, payload, body))
    return outcome


def drive_blocked(workflow: OwnerWorkflow) -> None:
    """CP-4C attempt 0 payload r01 (rejected), then attempt 1 payload v13 (blocked)."""
    refusals = {r["id"]: r for r in oracle()["submissions"]["refusals"]}
    for rid in ("r01", "v13"):
        outcome = drive_cp4c(workflow, "blocked", refusals[rid]["payload"])
        if outcome["status"] != "invalid":
            raise RuntimeError(f"{rid} not refused: {outcome['status']}")


def cp4c_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-4C run of `case` under `root`: (store, sealed receipt, no publication)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-4C case {case}")
    receipt = root / "owner-receipt.json"
    if case == "refused":
        workflow, _ = promoted(case, root)
    elif case == "cp2g_blocked":
        workflow, _ = promoted(case, root)
        drive_cp2a(workflow)
        drive_cp4(workflow, case)
        _driver("cp2g_runs").drive_blocked(workflow)  # CP-2G r01 then v13; CP-4C begin refused
    else:
        workflow = ready(case, root)
        if case == "blocked":
            drive_blocked(workflow)
        else:
            outcome = drive_cp4c(workflow, case, oracle()["submissions"]["cases"][case][STEP])
            if outcome["status"] != "valid":
                raise RuntimeError(f"CP-4C not valid: {outcome['issues']}")
    workflow.write_receipt(receipt)
    return root / "store", receipt, None
