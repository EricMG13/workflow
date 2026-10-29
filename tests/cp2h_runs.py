"""CP-2H run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed distressed-pathway run (CP-0, CP-1, CP-2A, CP-2G, CP-2H) over the pinned oracle in
`cases/cp2h-owner`, driven through the public `OwnerWorkflow` API only. G2 imports `cp2h_closed`;
`tests/test_owner_cp2h.py` imports the stage functions to fork a run. Nothing here asserts
expected values: the oracle files are read, never derived. CP-0 and CP-1 replay the case's own
literals (`submissions.json cases.<case>.{readiness_review, cp1_source_context, cp1_readiness}`,
the pack hash and the readiness markers bound at run time); CP-2A and CP-2G replay the frozen
literals copied into `submissions.json upstream_step_literals` through their drivers; CP-2H
reads its view, then the case's `tool_calls`, then submits the case's literal with its figures
bound (`manifest.json run_time_bindings`).

STAGE 5 ONLY: a genuine CP-1 promotion, 11-26 minutes per case. Written in Stage 2, never run.
"""

import hashlib
import importlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2h-owner"
CASES = ("positive", "gap", "refused", "blocked", "cp2g_blocked")
# The literals of each run: `blocked` is "same pack as positive", `cp2g_blocked` "same pack as gap".
LITERALS = {"positive": "positive", "gap": "gap", "blocked": "positive", "cp2g_blocked": "gap"}
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
EVID = re.compile(r"\{\{EVID:kpi ([a-z_]+), LTM Q4 25 basis\}\}")
GAP_MARKERS = ("{{GAP_IDS}}", "{{ALL narrative gap ids}}")
LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
STEP = "rating_triggers"


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
    """identity + financial as the financial slice builds them, plus the case's agency source
    (`manifest.json synthetic_source.<positive|gap>`, page hash checked, with its pack
    limitation); `refused`: the financial negative case (financial missing), no agency source."""
    manifest = oracle()["manifest"]
    sources = list(_driver("test_financial_workflow").make_pack(gap=case == "refused").sources)
    if case != "refused":
        synthetic = manifest["synthetic_source"]
        variant = LITERALS[case]
        spans = tuple(Span(**page) for page in synthetic[variant]["pages"])
        joined = "\f".join(span.text for span in spans).encode()
        if hashlib.sha256(joined).hexdigest() != synthetic[variant]["sha256"]:
            raise RuntimeError("agency source page hash drift")
        sources.append(
            Source(
                source_id=synthetic["source_id"],
                name=synthetic["name"],
                status=synthetic["status"],
                sha256=synthetic[variant]["sha256"],
                media_type=synthetic["media_type"],
                spans=spans,
                extractor=synthetic["extractor"],
                extraction_status=synthetic["extraction_status"],
                limitation=synthetic["pack_limitation_" + variant],
            )
        )
    run = Run.model_validate_json(json.dumps(manifest["cases"][case]["run"]))
    return PreparedPack(run=run, sources=tuple(sources))


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack, publication_directory=None), pack


def _with_pack(literal: Any, pack: PreparedPack) -> str:
    return json.dumps(literal, ensure_ascii=False).replace(PACK_PLACEHOLDER, pack.content_hash())


def cp0_review(pack: PreparedPack, case: str) -> str:
    """CP-0's review: the case's `readiness_review` literal (consumer rows CP-1, CP-2A, CP-2G and
    CP-2H; `run_time_bindings.cp0_consumer_rows`); `refused`: the financial negative review with
    the literal rows and gap row of `submissions.json refused`."""
    submissions = oracle()["submissions"]
    if case == "refused":
        review = json.loads(_driver("test_financial_workflow").readiness(pack, gap=True))
        rows = submissions["refused"]
        review["consumers"] = [
            rows[f"cp0_consumer_row_{m}"] for m in ("cp1", "cp2a", "cp2g", "cp2h")
        ]
        review["gaps"] = [rows["gap_row"]]
        return json.dumps(review, ensure_ascii=False)
    return _with_pack(submissions["cases"][LITERALS[case]]["readiness_review"], pack)


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> dict[str, Any]:
    """Every cited page read, then the review; the outcome (it carries any begin refusal)."""
    s1a = _driver("s1a_runs")
    review = cp0_review(pack, case)
    if case == "refused":
        _driver("test_financial_workflow").read_sources(workflow, gap=True)
    else:
        s1a.read_cited(workflow, review)
    outcome: dict[str, Any] = s1a.submit_valid(workflow, review)
    return outcome


def readiness_literal(workflow: OwnerWorkflow, case: str, read: Mapping[str, Any]) -> str:
    """`cases.<case>.cp1_readiness` with its markers bound to the readiness step's inputs:
    `{{INPUTS_SHA256}}` the read's hash; `{{EVID:kpi key, LTM Q4 25 basis}}` by the frozen CP-2A
    driver's selection rule; a gap marker list element expands to every narrative gap id. An
    unknown marker fails closed."""
    inputs = _driver("cp1d_runs").downstream_inputs(workflow)
    cp2a_runs = _driver("cp2a_runs")
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
                out.extend(gaps if item in GAP_MARKERS else [bind(item)])
            return out
        return scalar(value) if isinstance(value, str) else value

    literal = oracle()["submissions"]["cases"][LITERALS[case]]["cp1_readiness"]
    return json.dumps(bind(literal), ensure_ascii=False)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion: the case's source context literal (every cited page read, the
    financial event search), the financial slice's financials and narrative, the readiness
    literal and the quality review built from the read inputs (the CP-2G driver's)."""
    fw, s1a = _driver("test_financial_workflow"), _driver("s1a_runs")
    context = _with_pack(
        oracle()["submissions"]["cases"][LITERALS[case]]["cp1_source_context"], pack
    )
    s1a.read_cited(workflow, context)
    s1a.search(workflow, "financial", "subsequent")
    s1a.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    s1a.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    s1a.submit_valid(workflow, json.dumps(fw.narrative(read)))
    ready_read = workflow.read_inputs()
    s1a.submit_valid(workflow, readiness_literal(workflow, case, ready_read))
    inputs = json.loads(workflow.read_inputs()["body"])
    s1a.submit_valid(workflow, _driver("cp2g_runs")._quality_review(fw, read, inputs))


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, dict[str, Any]]:
    """CP-0 and CP-1 settled, CP-2A begun and untouched (`refused`: CP-0 only); CP-0's outcome."""
    workflow, pack = start(case, root)
    outcome = drive_cp0(workflow, pack, case)
    if case != "refused":
        drive_cp1(workflow, pack, case)
    return workflow, outcome


def drive_cp2a(workflow: OwnerWorkflow) -> None:
    """The one exact read, then the frozen CP-2A positive literal (CP-2A figures bound)."""
    cp2a_runs = _driver("cp2a_runs")
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    payload = upstream_literal("CP-2A")["downside_pathway"]
    outcome = workflow.submit_review(cp2a_runs.bound_literal(workflow, payload, body))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2A not valid: {outcome['issues']}")


def drive_cp2g_blocked(workflow: OwnerWorkflow) -> dict[str, Any]:
    """CP-2G attempt 0 (its refusal r01, rejected), then attempt 1 (v13, blocked); the attempt-1
    outcome, which carries the CP-2H begin refusal."""
    blocked = upstream_literal("CP-2G")["blocked"]
    outcome: dict[str, Any] = {}
    for key in ("attempt_0", "attempt_1"):
        outcome = _driver("cp2g_runs").drive_cp2g(workflow, blocked[key]["payload"])
        if outcome["status"] != "invalid":
            raise RuntimeError(f"CP-2G {key} not refused: {outcome['status']}")
    return outcome


def ready(case: str, root: Path) -> OwnerWorkflow:
    """Every upstream settled and CP-2H begun, untouched (positive, gap, blocked): the state the
    A3 clones fork. CP-2G replays its frozen gap literal (`upstream_step_literals.CP-2G`)."""
    workflow, _ = promoted(case, root)
    drive_cp2a(workflow)
    outcome = _driver("cp2g_runs").drive_cp2g(
        workflow, upstream_literal("CP-2G")["forward_credit_model"]
    )
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2G not valid: {outcome['issues']}")
    return workflow


def fig_bindings(workflow: OwnerWorkflow, body: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token) by `manifest.json cp1_fact_selection_rule`: the one settled
    CP-1 T4.10 fact labelled `<LTM column> · <metric>` (zero or several fail), which must be a
    `cp1_facts` ref of the view with the oracle unit token."""
    store = workflow._store
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(cp1).facts
    refs = {e["ref"]: e for e in body["cp1_facts"]}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in oracle()["submissions"]["figures"].items():
        label = f"{LTM_LABEL} · {figure['metric']}"
        hits = [f for f in facts if f.table_id == "T4.10" and f.label == label]
        if len(hits) != 1:
            raise RuntimeError(f"FIG {name}: {len(hits)} candidate CP-1 facts, expected one")
        entry = refs.get(hits[0].fact_id)
        if entry is None or entry["unit"] != figure["unit_token"]:
            raise RuntimeError(f"FIG {name}: not offered with the oracle unit")
        bound[name] = (hits[0].fact_id, figure["unit_token"])
    return bound


def bound_literal(workflow: OwnerWorkflow, payload: Any, body: Mapping[str, Any]) -> str:
    """`{{FIG:name|token}}` -> `{<fact_id>|<token>}`; an unknown name stays and fails closed."""
    bindings = fig_bindings(workflow, body)

    def replace(match: re.Match[str]) -> str:
        hit = bindings.get(match[1])
        return (
            match[0] if hit is None or hit[1] != match[2] else "{" + hit[0] + "|" + match[2] + "}"
        )

    return FIG.sub(replace, json.dumps(payload, ensure_ascii=False))


def read_view_and_pages(workflow: OwnerWorkflow, case: str = "positive") -> dict[str, Any]:
    """The one exact `read_inputs`, then the case's literal `read_pages` calls (each ok with the
    spans the oracle expects); the view body."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    for call in oracle()["submissions"]["cases"][LITERALS[case]]["tool_calls"]:
        if call["tool"] == "read_inputs":
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {outcome['error_code']}")
    return body


def drive_cp2h(workflow: OwnerWorkflow, payload: Any, case: str = "positive") -> dict[str, Any]:
    """CP-2H's view and page reads, then `payload` with its figures bound."""
    body = read_view_and_pages(workflow, case)
    outcome: dict[str, Any] = workflow.submit_review(bound_literal(workflow, payload, body))
    return outcome


def drive_blocked(workflow: OwnerWorkflow) -> None:
    """CP-2H attempt 0 payload r01 (rejected), then attempt 1 payload v08 (blocked), each after
    the positive page reads (`submissions.json blocked`)."""
    refusals = {r["id"]: r for r in oracle()["submissions"]["refusals"]}
    for rid in ("r01", "v08"):
        outcome = drive_cp2h(workflow, refusals[rid]["payload"])
        if outcome["status"] != "invalid":
            raise RuntimeError(f"{rid} not refused: {outcome['status']}")


def cp2h_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-2H run of `case` under `root`: (store, sealed receipt, no publication)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-2H case {case}")
    receipt = root / "owner-receipt.json"
    if case == "refused":
        workflow, _ = promoted(case, root)
    elif case == "cp2g_blocked":
        workflow, _ = promoted(case, root)
        drive_cp2a(workflow)
        drive_cp2g_blocked(workflow)  # CP-2G r01 then v13; the CP-2H begin is refused
    else:
        workflow = ready(case, root)
        if case == "blocked":
            drive_blocked(workflow)
        else:
            payload = oracle()["submissions"]["cases"][case][STEP]
            outcome = drive_cp2h(workflow, payload, case)
            if outcome["status"] != "valid":
                raise RuntimeError(f"CP-2H not valid: {outcome['issues']}")
    workflow.write_receipt(receipt)
    return root / "store", receipt, None
