"""CP-1D run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed earnings-update run (CP-0, CP-1, CP-1D) over the pinned oracle in `cases/cp1d-owner`,
driven through the public `OwnerWorkflow` API only. G2 imports `cp1d_closed`;
`tests/test_owner_cp1d.py` imports the stage functions to fork a run at any point. Nothing here
asserts expected values: the oracle files are read, never derived. The slow part (the genuine
CP-1 promotion) takes 11-26 minutes per case; no function here is run by the fast gates.
"""

import hashlib
import importlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Fact, Run, Source, Span
from deploy_vii.downstream_readiness import DownstreamInputs
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1d-owner"
CASES = ("positive", "statements_only", "gap")
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]+)\}\}")
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
S1A: Any = importlib.import_module("s1a_runs")


def _fw() -> Any:
    return importlib.import_module("test_financial_workflow")


def oracle() -> dict[str, Any]:
    return {
        "manifest": json.loads((CASE / "manifest.json").read_text()),
        "submissions": json.loads((CASE / "submissions.json").read_text()),
        "expected": json.loads((CASE / "expected.json").read_text()),
    }


def make_pack(case: str) -> PreparedPack:
    """identity and financial as the financial slice builds them, plus the oracle's bridge
    variant (positive, gap) with its pack limitation; the run is the case's own."""
    data = oracle()["manifest"]
    base = _fw().make_pack()
    sources = list(base.sources)
    if case != "statements_only":
        variant = data["synthetic_source"][case]
        synthetic = data["synthetic_source"]
        spans = tuple(Span(**page) for page in variant["pages"])
        if (
            hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest()
            != variant["sha256"]
        ):
            raise RuntimeError("bridge page hash drift")
        sources.append(
            Source(
                source_id="bridge",
                name=synthetic["name"],
                status="ready",
                sha256=variant["sha256"],
                media_type=synthetic["media_type"],
                spans=spans,
                extractor=synthetic["extractor"],
                extraction_status=synthetic["extraction_status"],
                limitation=synthetic["pack_limitation_" + case],
            )
        )
    run = Run.model_validate_json(json.dumps(data["cases"][case]["run"]))
    return PreparedPack(run=run, sources=tuple(sources))


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    text = json.dumps(oracle()["submissions"][case][name], ensure_ascii=False)
    return text if pack is None else text.replace(PACK_PLACEHOLDER, pack.content_hash())


def figure_fact(facts: tuple[Fact, ...], metric: str) -> Fact:
    """The one CP-1 T4.10 fact of `metric` on the LTM Q4 25 basis (manifest
    `cp1_fact_selection_rule`); zero or several fail."""
    hits = [
        f
        for f in facts
        if f.table_id == "T4.10" and f.period == LTM_PERIOD and f.label == f"{LTM_LABEL} · {metric}"
    ]
    if len(hits) != 1:
        raise RuntimeError(f"FIG {metric}: {len(hits)} candidate CP-1 facts, expected exactly one")
    return hits[0]


def fig_bindings(
    store: Execution, view_body: Mapping[str, Any], figures: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    """figure name -> (fact_id, unit token): selected from the settled CP-1 head, then required
    to be a `ref` of the CP-1D view with the oracle unit token and spelling."""
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(cp1).facts
    refs = {entry["ref"]: entry for entry in view_body["cp1_facts"]}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in figures.items():
        fact = figure_fact(facts, figure["metric"])
        entry = refs.get(fact.fact_id)
        if entry is None:
            raise RuntimeError(f"FIG {name}: {fact.fact_id} is not a ref of the CP-1D view")
        if (entry["unit"], entry["shown"]) != (figure["unit_token"], figure["spelled"]):
            raise RuntimeError(f"FIG {name}: unit/shown {entry['unit']}/{entry['shown']}")
        bound[name] = (fact.fact_id, figure["unit_token"])
    return bound


def bind_figures(text: str, bindings: Mapping[str, tuple[str, str]]) -> str:
    """`{{FIG:name|token}}` -> `{<fact_id>|<token>}`; an unknown name stays and fails closed."""

    def replace(match: re.Match[str]) -> str:
        if match[1] not in bindings:
            return match[0]
        return "{" + bindings[match[1]][0] + "|" + match[2] + "}"

    return FIG.sub(replace, text)


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=None)
    return workflow, pack


def downstream_inputs(workflow: OwnerWorkflow) -> DownstreamInputs:
    """The readiness step's `DownstreamInputs`: the retained output of the ticket's narrative
    step (what `live.submission.known_bindings` prefills `step-inputs` from)."""
    store = workflow._store
    attempt = next(a for a in store.read().attempts if a.ticket_id == workflow._binding.ticket_id)
    held = attempt.steps[2]
    if held.step_id != "narrative" or held.status != "valid":
        raise RuntimeError("the narrative step is not retained valid")
    return DownstreamInputs.model_validate_json(store.step_output(held.output_sha256 or ""))


def _kpi_id(inputs: DownstreamInputs, key: str) -> str:
    """The evidence_id of the first catalogue record of kind `kpi` with that key whose
    observation_ids hold an id ending `-fy-2025`; none or another shape fails closed."""
    for record in inputs.narrative.inputs.catalogue:
        if record.kind != "kpi":
            continue
        value = json.loads(record.record_json)
        if value.get("key") == key and any(
            str(o).endswith("-fy-2025") for o in value["value"]["observation_ids"]
        ):
            return str(record.evidence_id)
    raise RuntimeError(f"no FY-2025 kpi record for {key}")


def readiness_payload(case: str, inputs: DownstreamInputs) -> str:
    """The case's `cp1_readiness` literal with `{{KPI:key|FY-2025}}` and `{{GAP_IDS}}` bound to
    the readiness-step inputs; `inputs_sha256` is prefilled by Python and left out."""
    document = json.loads(json.dumps(oracle()["submissions"][case]["cp1_readiness"]["payload"]))
    document.pop("inputs_sha256", None)
    gap_ids = [gap.gap_id for gap in inputs.narrative.gaps]
    for consumer in document["consumers"]:
        for requirement in consumer["requirements"]:
            bound = []
            for evidence in requirement["evidence_ids"]:
                match = re.fullmatch(r"\{\{KPI:([a-z_]+)\|FY-2025\}\}", evidence)
                if match is None:
                    raise RuntimeError(f"unexpected evidence placeholder {evidence}")
                bound.append(_kpi_id(inputs, match[1]))
            requirement["evidence_ids"] = bound
        for gap in consumer["gaps"]:
            gap["gap_ids"] = gap_ids
    return json.dumps(document, ensure_ascii=False)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion: the case's source_context, the financial slice's financials and
    narrative, the CP-1D readiness literal, and the quality review built from the read inputs."""
    fw = _fw()
    context = literal(case, "cp1_source_context", pack)
    S1A.read_cited(workflow, context)
    S1A.search(workflow, "financial", "subsequent")
    if case != "statements_only":
        S1A.search(workflow, "bridge", "acquisition")
    S1A.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    S1A.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    S1A.submit_valid(workflow, json.dumps(fw.narrative(read)))
    workflow.read_inputs()
    S1A.submit_valid(workflow, readiness_payload(case, downstream_inputs(workflow)))
    quality_inputs = json.loads(workflow.read_inputs()["body"])
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
            for claim in quality_inputs["claims"]
        ]
    }
    S1A.submit_valid(workflow, json.dumps(review))


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled; CP-1D begun and untouched. The slow part (11-26 minutes)."""
    workflow, pack = start(case, root)
    S1A.drive_cp0(workflow, pack, case, text=literal(case, "readiness_review", pack))
    drive_cp1(workflow, pack, case)
    return workflow, pack


def read_view(workflow: OwnerWorkflow) -> dict[str, Any]:
    """CP-1D's one read: the exact module_context view, parsed."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    return body


def tool_calls(workflow: OwnerWorkflow, case: str) -> None:
    """The case's literal tool sequence after `read_inputs` (`submissions.<case>.tool_calls`):
    each `read_pages` ok and returning the expected span."""
    for call in oracle()["submissions"][case]["tool_calls"]:
        if call["tool"] == "read_inputs":
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {outcome['error_code']}")


def drive_cp1d(
    workflow: OwnerWorkflow, case: str, body: Mapping[str, Any], *, text: str | None = None
) -> dict[str, Any]:
    """Bind the figures against the read body and submit the literal earnings_quality."""
    raw = literal(case, "earnings_quality") if text is None else text
    figures = oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in FIG.finditer(raw))}
    bindings = fig_bindings(workflow._store, body, names)
    return workflow.submit_review(bind_figures(raw, bindings))


def close(workflow: OwnerWorkflow, case: str, receipt: Path) -> None:
    """From CP-1D active to the sealed receipt: the view, the literal reads, the submission."""
    body = read_view(workflow)
    tool_calls(workflow, case)
    outcome = drive_cp1d(workflow, case, body)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-1D not valid: {outcome['issues']}")
    workflow.write_receipt(receipt)


def cp1d_closed(case: str, root: Path) -> tuple[Path, Path]:
    """One closed CP-1D run of `case` under `root`: (store, sealed receipt)."""
    workflow, _pack = promoted(case, root)
    close(workflow, case, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"
