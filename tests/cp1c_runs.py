"""CP-1C run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed relative-value run (CP-0, CP-1, CP-1C) over the pinned oracle in `cases/cp1c-owner`,
driven through the public `OwnerWorkflow` API only. G2 imports `cp1c_closed`;
`tests/test_owner_cp1c.py` imports the stage functions to fork a run. Nothing here asserts
expected values: the oracle files are read, never derived. CP-0 readiness and CP-1
source_context are the case literals (`submissions.json <case>`, pack hash bound); the later
CP-1 stages are the financial slice's; the CP-1 readiness stage is `<case>.cp1_readiness.payload`
with its markers bound by the predicates of its own `run_time_bindings` (lease ruling S6).

STAGE 5 ONLY: a genuine CP-1 promotion, 11-26 minutes per case. Written in Stage 2, never run.
"""

import copy
import hashlib
import importlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1c-owner"
CASES = ("positive", "gap", "no_peers", "refused", "blocked")
PEERS = ("positive", "gap")  # the packs holding the synthetic peers source
BASE = {"blocked": "positive"}  # the blocked run is r04 twice over the positive pack
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
STEP = "peer_benchmark"
GAP_MARKER = "{{GAP_IDS}}"
BINDING = re.compile(r"evidence_id of the one catalogue record of kind (\w+) with (.+?); none or")
CONDITION = re.compile(r"(?:record\.)?(\w+) == '([^']*)'")


def _driver(name: str) -> Any:
    return importlib.import_module(name)


def _base(case: str) -> str:
    return BASE.get(case, case)


def oracle() -> dict[str, Any]:
    """The three pinned oracle files (`cases/PINS.json`); a drifted file fails."""
    pins = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for name in ("manifest", "submissions", "expected"):
        path = CASE / f"{name}.json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != pins[f"cases/cp1c-owner/{name}.json"]:
            raise RuntimeError(f"oracle drift: {name}.json")
        out[name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def peer_source(variant: str) -> Source:
    """The SYNTHETIC peers source of `manifest.json synthetic_source.<variant>`, hash-checked."""
    synthetic = oracle()["manifest"]["synthetic_source"]
    raw = synthetic[variant]
    texts = [page["text"] for page in raw["pages"]]
    if hashlib.sha256("\f".join(texts).encode("utf-8")).hexdigest() != raw["sha256"]:
        raise RuntimeError(f"peers {variant} page hash drift")
    return Source(
        source_id=synthetic["source_id"],
        name=synthetic["name"],
        status=synthetic["status"],
        sha256=raw["sha256"],
        spans=tuple(Span(**page) for page in raw["pages"]),
        limitation=synthetic["pack_limitation"],
        media_type=synthetic["media_type"],
        extractor=synthetic["extractor"],
        extraction_status=synthetic["extraction_status"],
    )


def make_pack(case: str) -> PreparedPack:
    """The case's run over the financial slice's identity and financial sources (the financial
    source missing for `refused`) plus the peers source of `positive` and `gap`."""
    base = _base(case)
    sources = _driver("test_financial_workflow").make_pack(gap=base == "refused").sources
    if base in PEERS:
        sources = (*sources, peer_source(base))
    run = Run.model_validate_json(json.dumps(oracle()["manifest"]["cases"][base]["run"]))
    return PreparedPack(run=run, sources=sources)


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack, publication_directory=None), pack


def literal(case: str, name: str, pack: PreparedPack) -> str:
    """One literal stage of `submissions.json <case>` as JSON text, the pack hash bound."""
    text = json.dumps(oracle()["submissions"][_base(case)][name], ensure_ascii=False)
    return text.replace(PACK_PLACEHOLDER, pack.content_hash())


def cp0_review(pack: PreparedPack, case: str) -> str:
    """The case's CP-0 literal; `refused`: the financial slice's gap review with the CP-1C
    consumer row appended and the gap row of `submissions.json refused`."""
    if case != "refused":
        return literal(case, "readiness_review", pack)
    rows = oracle()["submissions"]["refused"]
    review = json.loads(_driver("test_financial_workflow").readiness(pack, gap=True))
    review["consumers"] = [*review["consumers"], rows["cp0_consumer_row_cp1c"]]
    review["gaps"] = [rows["gap_row"]]
    return json.dumps(review, ensure_ascii=False)


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> dict[str, Any]:
    """CP-0's reads and its review; the outcome is returned (`refused` carries the CP-1 begin
    refusal), any other case must be valid."""
    review = cp0_review(pack, case)
    if case == "refused":
        _driver("test_financial_workflow").read_sources(workflow, gap=True)
        outcome: dict[str, Any] = workflow.submit_review(review)
        return outcome
    s1a = _driver("s1a_runs")
    s1a.read_cited(workflow, review)
    valid: dict[str, Any] = s1a.submit_valid(workflow, review)
    return valid


def evidence_id(inputs: Any, marker: str, rule: str) -> str:
    """The evidence id a `{{EVID:*}}` marker names: the one catalogue record of the rule's kind
    whose record fields equal the rule's values; an unparsed rule, none or several fail."""
    match = BINDING.match(rule)
    if match is None:
        raise RuntimeError(f"unparsed readiness binding {marker}: {rule}")
    kind, conditions = match[1], CONDITION.findall(match[2])
    if not conditions:
        raise RuntimeError(f"readiness binding {marker} names no record field")
    hits = [
        str(record.evidence_id)
        for record in inputs.narrative.inputs.catalogue
        if record.kind == kind
        and all(
            str(json.loads(record.record_json).get(field)) == value for field, value in conditions
        )
    ]
    if len(hits) != 1:
        raise RuntimeError(f"{marker}: {len(hits)} catalogue records, expected exactly one")
    return hits[0]


def readiness_literal(workflow: OwnerWorkflow, case: str) -> str:
    """`<case>.cp1_readiness.payload` bound to the readiness step's inputs: each `{{EVID:*}}` by
    its `run_time_bindings` predicate, the `{{GAP_IDS}}` element by every narrative gap id in
    order; `inputs_sha256` is prefilled by Python and left out. An unknown marker fails."""
    readiness = oracle()["submissions"][_base(case)]["cp1_readiness"]
    rules: Mapping[str, str] = readiness["run_time_bindings"]
    inputs = _driver("cp1d_runs").downstream_inputs(workflow)
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]
    document = copy.deepcopy(readiness["payload"])
    document.pop("inputs_sha256")

    def bind(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: bind(item) for key, item in value.items()}
        if isinstance(value, list):
            out: list[Any] = []
            for item in value:
                out.extend(gaps if item == GAP_MARKER else [bind(item)])
            return out
        if isinstance(value, str) and value.startswith("{{EVID:") and value in rules:
            return evidence_id(inputs, value, rules[value])
        if isinstance(value, str) and "{{" in value:
            raise RuntimeError(f"unbound readiness marker {value}")
        return value

    return json.dumps(bind(document), ensure_ascii=False)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion: the case's source_context literal after its cited reads and the
    no-event search, the financial slice's financials and narrative, the bound readiness
    literal and the quality review built from the read inputs (as the CP-2G driver)."""
    fw, s1a = _driver("test_financial_workflow"), _driver("s1a_runs")
    context = literal(case, "cp1_source_context", pack)
    s1a.read_cited(workflow, context)
    s1a.search(workflow, "financial", "subsequent")
    s1a.submit_valid(workflow, context)
    fw.financial_reads(workflow)
    s1a.submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    s1a.submit_valid(workflow, json.dumps(fw.narrative(read)))
    workflow.read_inputs()
    s1a.submit_valid(workflow, readiness_literal(workflow, case))
    inputs = json.loads(workflow.read_inputs()["body"])
    s1a.submit_valid(workflow, _driver("cp2g_runs")._quality_review(fw, read, inputs))


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled, CP-1C begun and untouched (`refused`: CP-0 only)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    if case != "refused":
        drive_cp1(workflow, pack, case)
    return workflow, pack


def run_calls(workflow: OwnerWorkflow, calls: Iterable[Mapping[str, Any]]) -> None:
    """A literal tool sequence (`tool_calls`, `calls_before_submit`): each call must be ok, a
    read must return every `expect_spans` locator and a search its `expect_header` line."""
    for call in calls:
        if call["tool"] == "read_inputs":
            workflow.read_inputs()
            continue
        outcome = workflow.invoke(call["tool"], call["arguments"])
        if outcome["status"] != "ok":
            raise RuntimeError(f"{call['tool']} {call['arguments']}: {outcome['error_code']}")
        body = str(outcome["body"])
        for span in call.get("expect_spans", ()):
            if f"locator={span['locator']} | " not in body:
                raise RuntimeError(f"{call['tool']}: no {span['source_id']} {span['locator']}")
        header = call.get("expect_header")
        if header is not None and body.splitlines()[0] != header:
            raise RuntimeError(f"{call['tool']}: {body.splitlines()[0]}")


def drive_cp1c(
    workflow: OwnerWorkflow,
    case: str,
    *,
    text: str | None = None,
    calls: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """One CP-1C attempt: the case's literal `tool_calls` (or `calls`), then `text` (default the
    case's literal `peer_benchmark`)."""
    case_literals = oracle()["submissions"][_base(case)]
    run_calls(workflow, case_literals["tool_calls"] if calls is None else calls)
    payload = json.dumps(case_literals[STEP], ensure_ascii=False) if text is None else text
    outcome: dict[str, Any] = workflow.submit_review(payload)
    return outcome


def refusal(rid: str) -> dict[str, Any]:
    found: dict[str, Any] = next(r for r in oracle()["submissions"]["refusals"] if r["id"] == rid)
    return found


def drive_refusal(workflow: OwnerWorkflow, rid: str) -> dict[str, Any]:
    """One refused attempt: the refusal's `calls_before_submit`, then its literal payload."""
    literal_refusal = refusal(rid)
    return drive_cp1c(
        workflow,
        literal_refusal["base_case"],
        text=json.dumps(literal_refusal["payload"], ensure_ascii=False),
        calls=literal_refusal["calls_before_submit"],
    )


def close(workflow: OwnerWorkflow, case: str, receipt: Path) -> None:
    """From CP-1C begun to the sealed receipt: the case's literal (valid), or for `blocked` the
    r04 literal on attempt 0 and attempt 1 (`submissions.json blocked`)."""
    if case == "blocked":
        for attempt in (0, 1):
            outcome = drive_refusal(workflow, "r04")
            if outcome["status"] != "invalid":
                raise RuntimeError(f"r04 attempt {attempt} not refused: {outcome['status']}")
    else:
        outcome = drive_cp1c(workflow, case)
        if outcome["status"] != "valid":
            raise RuntimeError(f"CP-1C not valid: {outcome['issues']}")
    workflow.write_receipt(receipt)


def cp1c_closed(case: str, root: Path) -> tuple[Path, Path, None]:
    """One closed CP-1C run of `case` under `root`: (store, sealed receipt, no publication)."""
    if case not in CASES:
        raise ValueError(f"unknown CP-1C case {case}")
    receipt = root / "owner-receipt.json"
    workflow, _ = promoted(case, root)
    if case == "refused":
        workflow.write_receipt(receipt)
    else:
        close(workflow, case, receipt)
    return root / "store", receipt, None
