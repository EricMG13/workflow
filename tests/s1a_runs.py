"""S1a run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed credit-snapshot run (CP-0, CP-1, CP-1A, CP-2, CP-MODEL) over the pinned oracle in
`cases/snapshot`, driven through the public `OwnerWorkflow` API only. G2 imports
`s1a_closed`; `tests/test_owner_s1a.py` imports the stage functions to fork a run at any
point. Nothing here asserts expected values: the oracle files are read, never derived.
"""

import hashlib
import importlib
import json
import re
import shutil
from collections.abc import Iterable, Mapping
from copy import copy
from pathlib import Path
from threading import Lock
from typing import Any

from deploy_vii.contracts import Fact, Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_workflow.host import SourceSession
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "cases/snapshot"
FINANCIAL_MANIFEST = ROOT / "cases/financial/manifest.json"
PINS = {
    SNAPSHOT / "expected.json": "d1aa1af9677cc4bd77b890261f0ceeca664acc72aac77f91da55cf36d7279baa",
    SNAPSHOT / "manifest.json": "68d591f672d1fb799e630d1359f5cb135d8ee9439209b23dcae38ca6a0eca3f4",
    SNAPSHOT
    / "submissions.json": "bff9ed18a87627ceae14410961e70a2d6b055128981baa7f4a57d3cd5f9fb35c",
    FINANCIAL_MANIFEST: "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
}
# case -> (manifest case_id, key in submissions.json, key in expected.json)
CASES: Mapping[str, tuple[str, str, str]] = {
    "positive": ("snapshot-positive", "positive", "positive"),
    "gap": (
        "snapshot-gap-business-without-ownership-transaction",
        "gap",
        "gap_business_without_ownership_transaction",
    ),
}
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
LTM_LABEL = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\}\}")


def _fw() -> Any:
    """The financial slice's literal CP-1 stages (financials, narrative), imported as G1 does."""
    return importlib.import_module("test_financial_workflow")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oracle() -> dict[str, Any]:
    """The four pinned oracle files plus the frozen CP-2 view tree; a drifted file fails."""
    for path, digest in PINS.items():
        if _sha(path) != digest:
            raise RuntimeError(f"oracle drift: {path.name}")
    return {
        "manifest": json.loads((SNAPSHOT / "manifest.json").read_text()),
        "submissions": json.loads((SNAPSHOT / "submissions.json").read_text()),
        "expected": json.loads((SNAPSHOT / "expected.json").read_text()),
        "tree": json.loads((SNAPSHOT / "cp2-view-tree.json").read_text()),
        "financial": json.loads(FINANCIAL_MANIFEST.read_text()),
    }


def make_pack(case: str) -> PreparedPack:
    """identity and financial from the hash-checked financial manifest (with its limitation),
    business from the snapshot manifest's case pages (hash-checked), the run from the case."""
    data = oracle()
    manifest, financial = data["manifest"], data["financial"]
    if _sha(FINANCIAL_MANIFEST) != manifest["financial_baseline"]["manifest_sha256"]:
        raise RuntimeError("financial baseline drift")
    entry = next(c for c in manifest["cases"] if c["case_id"] == CASES[case][0])
    business = manifest["business_source"][CASES[case][1]]
    common = manifest["business_source"]["common"]
    pages: dict[str, tuple[list[dict[str, Any]], str]] = {
        s["source_id"]: (s["pages"], s["sha256"]) for s in financial["sources"]
    }
    pages["business"] = (business["pages"], business["sha256"])
    if business["sha256"] != entry["business_source_sha256"]:
        raise RuntimeError("business source hash drift")
    limit = manifest["financial_pack_limitation"]["text"]
    sources = []
    for item in entry["pack_sources"]:
        spans, digest = pages[item["source_id"]]
        if hashlib.sha256("\f".join(p["text"] for p in spans).encode()).hexdigest() != digest:
            raise RuntimeError(f"{item['source_id']} page hash drift")
        if item["source_id"] == "financial" and item["limitation"] != limit:
            raise RuntimeError("financial limitation drift")
        extra: dict[str, Any] = (
            {
                "media_type": common["media_type"],
                "extractor": common["extractor"],
                "extraction_status": common["extraction_status"],
            }
            if item["source_id"] == "business"
            else {"extraction_status": "complete"}
        )
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status=item["status"],
                sha256=digest,
                spans=tuple(Span(**p) for p in spans),
                limitation=item["limitation"],
                **extra,
            )
        )
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["run"])), sources=tuple(sources)
    )


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    """One literal submission as JSON text; the pack hash is bound where the oracle marks it.
    `{{FIG:name}}` stays in `credit_synthesis` until `bind_figures`."""
    text = json.dumps(oracle()["submissions"][CASES[case][1]][name], ensure_ascii=False)
    return text if pack is None else text.replace(PACK_PLACEHOLDER, pack.content_hash())


def figure_names(text: str) -> list[str]:
    return list(dict.fromkeys(FIG.findall(text)))


def figure_fact(facts: Iterable[Fact], name: str) -> Fact:
    """The one CP-1 T4.10 fact of metric `name` on the LTM Q4 25 basis (lease rev 2, M2). The
    FY25 fact has the same dates but a different period and label and is never selected."""
    hits = [
        f
        for f in facts
        if f.table_id == "T4.10" and f.period == LTM_PERIOD and f.label == f"{LTM_LABEL} · {name}"
    ]
    if len(hits) != 1:
        raise RuntimeError(f"FIG {name}: {len(hits)} candidate CP-1 facts, expected exactly one")
    return hits[0]


def fig_bindings(
    store: Execution, read_body: Mapping[str, Any], figures: Mapping[str, Any]
) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token): selected from the settled CP-1 head, then required to be a
    `ref` of the CP-2 read body with the oracle unit token and the oracle spelling."""
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(cp1).facts
    refs = {entry["ref"]: entry for entry in read_body["cp1_facts"]}
    bound: dict[str, tuple[str, str]] = {}
    for name, figure in figures.items():
        fact = figure_fact(facts, name)
        entry = refs.get(fact.fact_id)
        if entry is None:
            raise RuntimeError(f"FIG {name}: {fact.fact_id} is not a ref of the CP-2 read body")
        if (entry["unit"], entry["shown"]) != (figure["unit_token"], figure["spelled"]):
            raise RuntimeError(f"FIG {name}: unit/shown {entry['unit']}/{entry['shown']}")
        bound[name] = (fact.fact_id, figure["unit_token"])
    return bound


def bind_figures(text: str, bindings: Mapping[str, tuple[str, str]]) -> str:
    """`{{FIG:name}}` -> `{<fact_id>|<unit_token>}`; an unknown name stays and fails closed."""

    def replace(match: re.Match[str]) -> str:
        if match[1] not in bindings:
            return match[0]
        fact_id, unit = bindings[match[1]]
        return "{" + fact_id + "|" + unit + "}"

    return FIG.sub(replace, text)


BLOCKED_CP2 = SNAPSHOT / "cp2-blocked-cp1a-submission.json"


def blocked_cp2_text() -> str:
    """The reviewed literal `credit_synthesis` valid under a blocked CP-1A (no CP-1A ref cited;
    R3-4). A fixture file, never derived; the test pins its sha256."""
    return BLOCKED_CP2.read_text(encoding="utf-8")


# --- tool-call sequence ----------------------------------------------------------------------


def read_cited(
    workflow: OwnerWorkflow, payload: str, *, skip: Iterable[tuple[str, str]] = ()
) -> None:
    """One ok `read_pages` call per page:N the payload cites (the cited-page rule), minus `skip`."""
    skipped = set(skip)
    pages = sorted(
        (source, int(locator.split(":")[1]))
        for source, locator in cited_locators(payload)
        if re.fullmatch(r"page:\d+", locator) and (source, locator) not in skipped
    )
    for source, number in pages:
        call = workflow.invoke(
            "read_pages", {"source_id": source, "first_page": number, "last_page": number}
        )
        if call["status"] != "ok":
            raise RuntimeError(f"read_pages {source} page:{number}: {call['error_code']}")


def search(workflow: OwnerWorkflow, source_id: str, query: str) -> None:
    call = workflow.invoke("search_pack", {"query": query, "source_id": source_id})
    if call["status"] != "ok":
        raise RuntimeError(f"search_pack {source_id}: {call['error_code']}")


def submit_valid(workflow: OwnerWorkflow, payload: str) -> dict[str, Any]:
    outcome = workflow.submit_review(payload)
    if outcome["status"] != "valid":
        raise RuntimeError(f"submission not valid: {outcome['status']} {outcome['issues']}")
    return outcome


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    return workflow, pack


def cp0_cp1a_conditional(case: str, pack: PreparedPack) -> str:
    """The case's CP-0 literal with CP-1A judged CONDITIONAL (so its T8 command is "DO NOT RUN").
    Test input for R3-1 / A3c, not oracle: only the CP-1A consumer's readiness, missing source and
    rationale change; CP-1 and CP-2 stay as the oracle has them."""
    document = json.loads(literal(case, "readiness_review", pack))
    consumer = next(c for c in document["consumers"] if c["module_id"] == "CP-1A")
    consumer["readiness"] = "CONDITIONAL"
    consumer["missing_source"] = "business: ownership and transaction pages"
    consumer["rationale"] = (
        "The business note does not yet carry located ownership and transaction pages."
    )
    return json.dumps(document, ensure_ascii=False)


def drive_cp0(
    workflow: OwnerWorkflow, pack: PreparedPack, case: str, *, text: str | None = None
) -> None:
    payload = literal(case, "readiness_review", pack) if text is None else text
    read_cited(workflow, payload)
    submit_valid(workflow, payload)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-1 to its promotion: the S1 literal source_context, then the financial case's literal
    financials, narrative, readiness and quality stages (the QA built from the read inputs)."""
    fw = _fw()
    context = literal(case, "cp1_source_context", pack)
    read_cited(workflow, context)
    search(workflow, "financial", "subsequent")
    if case == "positive":  # business event_scan is no_events_identified only here
        search(workflow, "business", "acquisition")
    submit_valid(workflow, context)
    fw.financial_reads(workflow)
    submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    refused = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    if refused["error_code"] != "not_permitted":
        raise RuntimeError("narrative step offered a source tool")
    submit_valid(workflow, json.dumps(fw.narrative(read)))
    workflow.read_inputs()
    submit_valid(workflow, json.dumps({"consumers": []}))
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


def promoted(
    case: str, root: Path, *, cp0_text: str | None = None
) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled; CP-1A begun and untouched (or refused, under a `cp0_text` that does
    not command it). The slow part (11-26 minutes)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case, text=cp0_text)
    drive_cp1(workflow, pack, case)
    return workflow, pack


def clone_workflow(template: OwnerWorkflow, destination: Path) -> OwnerWorkflow:
    """Isolated fork of a reached state: the store is copied, the workflow state is cloned and
    the source session is re-opened on the copy. Only a state with no call yet in the current
    step may be cloned, since a re-opened session starts its call sequence afresh."""
    if template._epoch_calls:
        raise RuntimeError("clone only before the first call of a step")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template._store.directory, destination / "store")
    workflow = copy(template)
    workflow._store = Execution(destination / "store")
    workflow._publication_directory = destination / "model"
    workflow._operation = Lock()
    for name in (
        "_calls",
        "_reads",
        "_submissions",
        "_publications",
        "_begins",
        "_refusals",
        "_epoch_calls",
    ):
        setattr(workflow, name, list(getattr(template, name)))
    workflow._limits = template._limits.copy()
    if template._session is not None:
        workflow._session = SourceSession.from_execution(
            workflow._store, template._binding.ticket_id, template._binding.step_id
        )
    return workflow


def drive_cp1a(
    workflow: OwnerWorkflow,
    pack: PreparedPack,
    case: str,
    *,
    skip_reads: Iterable[tuple[str, str]] = (),
    searched: bool = True,
    text: str | None = None,
) -> dict[str, Any]:
    """The literal business_context (or `text`) after its reads and (unless `searched` is off) a
    search."""
    payload = literal(case, "business_context", pack) if text is None else text
    read_cited(workflow, payload, skip=skip_reads)
    if searched:
        search(workflow, "business", "not disclosed")
    return workflow.submit_review(payload)


def read_cp2(workflow: OwnerWorkflow) -> dict[str, Any]:
    """CP-2's one read: the exact module_context view, parsed."""
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    return body


def drive_cp2(
    workflow: OwnerWorkflow, case: str, body: Mapping[str, Any], *, text: str | None = None
) -> dict[str, Any]:
    """Bind the figures against the read body and submit the literal credit_synthesis."""
    literal_text = literal(case, "credit_synthesis") if text is None else text
    figures = oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in figure_names(literal_text)}
    bindings = fig_bindings(workflow._store, body, names)
    return workflow.submit_review(bind_figures(literal_text, bindings))


def finish(workflow: OwnerWorkflow, receipt_path: Path) -> None:
    """Publish CP-MODEL and seal the receipt."""
    published = workflow.publish()
    if published["status"] != "ok":
        raise RuntimeError(f"publication refused: {published['error_code']}")
    workflow.write_receipt(receipt_path)


def close(workflow: OwnerWorkflow, pack: PreparedPack, case: str, receipt: Path) -> None:
    """From CP-1A active to the sealed receipt: CP-1A, CP-2 (figures bound), CP-MODEL."""
    cp1a = drive_cp1a(workflow, pack, case)
    if cp1a["status"] != "valid":
        raise RuntimeError(f"CP-1A not valid: {cp1a['issues']}")
    outcome = drive_cp2(workflow, case, read_cp2(workflow))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2 not valid: {outcome['issues']}")
    finish(workflow, receipt)


def s1a_closed(case: str, root: Path) -> tuple[Path, Path, Path]:
    """One closed S1a run of `case` under `root`: (store, sealed receipt, publication)."""
    workflow, pack = promoted(case, root)
    close(workflow, pack, case, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", root / "model"
