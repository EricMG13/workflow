"""CP-2G run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed distressed-pathway run (CP-0, CP-1, CP-1D when requested, CP-2A, CP-2G) over the
pinned oracle in `cases/cp2g-owner`, driven through the public `OwnerWorkflow` API only. G2
imports `cp2g_closed`; `tests/test_owner_cp2g.py` imports the stage functions to fork a run.
Nothing here asserts expected values: the oracle files are read, never derived. The upstream
steps replay the frozen CP-1D and CP-2A literals (`submissions.json upstream_step_literals`)
through the CP-1D and CP-2A drivers; the CP-1 readiness stage is the combined literal
`submissions.json cases.<case>.cp1_readiness`, its markers bound by
`manifest.json run_time_bindings.cp1_readiness`.

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
CASE = ROOT / "cases" / "cp2g-owner"
CASES = ("positive", "gap", "cp1d_blocked", "refused", "blocked", "cp2a_blocked")
BRIDGE = ("positive", "cp1d_blocked")  # the CP-1D bridge pack; CP-1D requested
READINESS = {  # the cp1_readiness literal of each run ("same pack as gap")
    "positive": "positive",
    "cp1d_blocked": "cp1d_blocked",
    "gap": "gap",
    "blocked": "gap",
    "cp2a_blocked": "gap",
}
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
KPI = re.compile(r"\{\{KPI:([a-z_]+)\|FY-2025\}\}")
EVID = re.compile(r"\{\{EVID:kpi ([a-z_]+), LTM Q4 25 basis\}\}")
GAP_MARKERS = ("{{GAP_IDS}}", "{{ALL narrative gap ids}}")
LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
STEP = "forward_credit_model"


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


def make_pack(case: str) -> PreparedPack:
    """The case's run over identity + financial (+ the CP-1D positive bridge pages for the
    bridge cases, byte-identical: `manifest.json bridge_source`; the financial source missing
    for `refused`)."""
    manifest = oracle()["manifest"]
    if case in BRIDGE:
        sources = _driver("cp1d_runs").make_pack("positive").sources
        bridge = next(s for s in sources if s.source_id == manifest["bridge_source"]["source_id"])
        if bridge.sha256 != manifest["bridge_source"]["sha256"]:
            raise RuntimeError("bridge source drift")
    else:
        sources = _driver("test_financial_workflow").make_pack(gap=case == "refused").sources
    run = Run.model_validate_json(json.dumps(manifest["cases"][case]["run"]))
    return PreparedPack(run=run, sources=sources)


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack, publication_directory=None), pack


def cp0_review(pack: PreparedPack, case: str) -> str:
    """CP-0's review with the consumer rows of `run_time_bindings.cp0_consumer_rows`: the CP-1D
    positive review (CP-1, CP-1D) for the bridge cases, the financial review (CP-1) otherwise,
    then CP-2A and CP-2G; `refused`: the literal rows and gap row of `submissions.json refused`."""
    submissions = oracle()["submissions"]
    fw = _driver("test_financial_workflow")
    if case == "refused":
        review = json.loads(fw.readiness(pack, gap=True))
        rows = submissions["refused"]
        review["consumers"] = [
            rows["cp0_consumer_row_cp1"],
            rows["cp0_consumer_row_cp2a"],
            rows["cp0_consumer_row_cp2g"],
        ]
        review["gaps"] = [rows["gap_row"]]
        return json.dumps(review, ensure_ascii=False)
    if case in BRIDGE:
        text = json.dumps(upstream_literal("CP-1D")["readiness_review"], ensure_ascii=False)
        review = json.loads(text.replace(PACK_PLACEHOLDER, pack.content_hash()))
    else:
        review = json.loads(fw.readiness(pack))
    review["consumers"] = [
        *review["consumers"],
        submissions["cp0_consumer_row_cp2a"],
        submissions["cp0_consumer_row_cp2g"],
    ]
    return json.dumps(review, ensure_ascii=False)


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    s1a = _driver("s1a_runs")
    review = cp0_review(pack, case)
    if case in BRIDGE:
        s1a.read_cited(workflow, review)
    else:
        _driver("test_financial_workflow").read_sources(workflow, gap=case == "refused")
    s1a.submit_valid(workflow, review)


PAYLOAD_KEYS = ("inputs_sha256", "consumers")  # DownstreamReview fields (extra="forbid")
COMMENTARY_KEYS = ("note",)  # oracle prose describing the entries; never submitted


def readiness_payload(literal: Mapping[str, Any]) -> dict[str, Any]:
    """The submittable part of an oracle `cp1_readiness` literal: `inputs_sha256` and
    `consumers`. `note` is oracle commentary and is dropped; any other key, or a missing
    payload key, fails closed."""
    unknown = sorted(set(literal) - set(PAYLOAD_KEYS) - set(COMMENTARY_KEYS))
    missing = [key for key in PAYLOAD_KEYS if key not in literal]
    if unknown or missing:
        raise RuntimeError(f"readiness literal keys: unknown {unknown}, missing {missing}")
    return {key: literal[key] for key in PAYLOAD_KEYS}


def readiness_literal(workflow: OwnerWorkflow, case: str, read: Mapping[str, Any]) -> str:
    """`cases.<case>.cp1_readiness` (payload keys only) with its markers bound to the readiness step's inputs:
    `{{INPUTS_SHA256}}` the read's hash; `{{KPI:key|FY-2025}}` (CP-1D frame) and
    `{{EVID:kpi key, LTM Q4 25 basis}}` (CP-2A and CP-2G frame) by the frozen drivers' own
    selection rules; a gap marker list element expands to every narrative gap id. An unknown
    marker fails closed."""
    cp1d_runs, cp2a_runs = _driver("cp1d_runs"), _driver("cp2a_runs")
    inputs = cp1d_runs.downstream_inputs(workflow)
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]

    def scalar(value: str) -> str:
        if value == "{{INPUTS_SHA256}}":
            return str(read["inputs_sha256"])
        if match := KPI.fullmatch(value):
            return str(cp1d_runs._kpi_id(inputs, match[1]))
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
                out.extend(gaps if item in GAP_MARKERS else [bind(item)])
            return out
        return scalar(value) if isinstance(value, str) else value

    literal = oracle()["submissions"]["cases"][READINESS[case]]["cp1_readiness"]
    return json.dumps(bind(readiness_payload(literal)), ensure_ascii=False)


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
    """CP-1 to its promotion: the CP-1D positive source context on the bridge pack (the
    financial slice's otherwise), the financial slice's financials and narrative, the combined
    readiness literal and the quality review built from the read inputs."""
    fw, s1a = _driver("test_financial_workflow"), _driver("s1a_runs")
    if case in BRIDGE:
        text = json.dumps(upstream_literal("CP-1D")["cp1_source_context"], ensure_ascii=False)
        context = text.replace(PACK_PLACEHOLDER, pack.content_hash())
        s1a.read_cited(workflow, context)
        s1a.search(workflow, "financial", "subsequent")
        s1a.search(workflow, "bridge", "acquisition")
    else:
        for source in ("identity", "financial"):
            workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
        s1a.search(workflow, "financial", "subsequent")
        context = fw.context(pack)
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
    """CP-0 and CP-1 settled, the next module begun and untouched (`refused`: CP-0 only)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    if case != "refused":
        drive_cp1(workflow, pack, case)
    return workflow, pack


def _cp1d_attempt(workflow: OwnerWorkflow, text: str) -> dict[str, Any]:
    """One CP-1D attempt: the view, the frozen tool sequence, the literal (figures bound)."""
    cp1d_runs = _driver("cp1d_runs")
    body = cp1d_runs.read_view(workflow)
    for call in upstream_literal("CP-1D")["tool_calls"]:
        if call["tool"] == "read_inputs":
            continue
        call_outcome = workflow.invoke(call["tool"], call["arguments"])
        if call_outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {call_outcome['error_code']}")
    outcome: dict[str, Any] = cp1d_runs.drive_cp1d(workflow, "positive", body, text=text)
    return outcome


def drive_cp1d(workflow: OwnerWorkflow, case: str) -> None:
    """positive: the frozen CP-1D positive literal, settled; cp1d_blocked: CP-1D refusal r06 on
    attempt 0 and on attempt 1 (`upstream_step_literals.CP-1D.blocked`), so CP-1D settles
    blocked."""
    literal = upstream_literal("CP-1D")
    if case == "positive":
        outcome = _cp1d_attempt(workflow, json.dumps(literal["earnings_quality"]))
        if outcome["status"] != "valid":
            raise RuntimeError(f"CP-1D not valid: {outcome['issues']}")
        return
    refusal = json.dumps(literal["blocked"]["payload"]["payload"], ensure_ascii=False)
    for attempt in (0, 1):
        outcome = _cp1d_attempt(workflow, refusal)
        if outcome["status"] != "invalid":
            raise RuntimeError(f"CP-1D attempt {attempt} not refused: {outcome['status']}")


def drive_cp2a(workflow: OwnerWorkflow) -> None:
    """The one exact read, then the frozen CP-2A positive literal (CP-2A figures bound)."""
    cp2a_runs = _driver("cp2a_runs")
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    payload = upstream_literal("CP-2A")["downside_pathway"]
    outcome = workflow.submit_review(cp2a_runs.bound_literal(workflow, payload, body))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2A not valid: {outcome['issues']}")


def ready(case: str, root: Path) -> OwnerWorkflow:
    """Every upstream settled and CP-2G begun, untouched (positive, gap, cp1d_blocked, blocked):
    the state the A3 clones fork."""
    workflow, _ = promoted(case, root)
    if case in BRIDGE:
        drive_cp1d(workflow, case)
    drive_cp2a(workflow)
    return workflow


def fig_bindings(
    workflow: OwnerWorkflow, body: Mapping[str, Any], names: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token) by `run_time_bindings.figure_placeholders`: a cp1 name is
    the one settled CP-1 T4.10 fact labelled `<LTM column> · <metric>` (zero or several fail),
    which must be a `cp1_facts` ref of the view with the oracle unit token; a cp1d name is its
    literal id (checked against `cp1d_facts` when CP-1D is bound; unbound, the reference is
    left to the validator)."""
    store = workflow._store
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(cp1).facts
    refs = {e["ref"]: e for e in (*body["cp1_facts"], *body["cp1d_facts"])}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in names.items():
        if figure["source"] == "cp1d":
            fact_id = str(figure["fact_id"])
            entry = refs.get(fact_id)
            if entry is not None and entry["unit"] != figure["unit_token"]:
                raise RuntimeError(f"FIG {name}: unit {entry['unit']}")
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
        return match[0] if hit is None else "{" + hit[0] + "|" + match[2] + "}"

    return FIG.sub(replace, text)


def drive_cp2g(workflow: OwnerWorkflow, payload: Any) -> dict[str, Any]:
    """CP-2G's one exact read (its only tool use), then `payload` with figures bound."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    outcome: dict[str, Any] = workflow.submit_review(bound_literal(workflow, payload, body))
    return outcome


def drive_blocked(workflow: OwnerWorkflow) -> None:
    """CP-2G attempt 0 payload r01 (rejected), then attempt 1 payload v13 (blocked)."""
    refusals = {r["id"]: r for r in oracle()["submissions"]["refusals"]}
    for rid in ("r01", "v13"):
        outcome = drive_cp2g(workflow, refusals[rid]["payload"])
        if outcome["status"] != "invalid":
            raise RuntimeError(f"{rid} not refused: {outcome['status']}")


def cp2g_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-2G run of `case` under `root`: (store, sealed receipt, no publication)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-2G case {case}")
    receipt = root / "owner-receipt.json"
    if case == "refused":
        workflow, _ = promoted(case, root)
    elif case == "cp2a_blocked":
        workflow, _ = promoted(case, root)
        _driver("cp2a_runs").drive_blocked(workflow)  # CP-2A r01 then v13; CP-2G begin refused
    else:
        workflow = ready(case, root)
        if case == "blocked":
            drive_blocked(workflow)
        else:
            outcome = drive_cp2g(workflow, oracle()["submissions"]["cases"][case][STEP])
            if outcome["status"] != "valid":
                raise RuntimeError(f"CP-2G not valid: {outcome['issues']}")
    workflow.write_receipt(receipt)
    return root / "store", receipt, None
