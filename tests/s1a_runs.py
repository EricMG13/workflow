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
from collections.abc import Callable, Iterable, Mapping
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


def _credit_quality_review(read: Mapping[str, Any], inputs: Mapping[str, Any]) -> str:
    """The S1 quality review: every claim material, each evidence line classed by the read."""
    fw = _fw()
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
    return json.dumps(review)


def drive_cp1(
    workflow: OwnerWorkflow,
    pack: PreparedPack,
    case: str,
    *,
    context: str | None = None,
    business_search: bool | None = None,
    narrative_tool_check: bool = True,
    readiness: Callable[[OwnerWorkflow, Mapping[str, Any]], str] | None = None,
    quality: Callable[[Mapping[str, Any], Mapping[str, Any]], str] = _credit_quality_review,
) -> None:
    """CP-1 to its promotion: the S1 literal source_context (or `context`, a later oracle's
    literal), then the financial case's literal financials, narrative, readiness and quality
    stages (the QA built from the read inputs).

    A later oracle's driver passes what differs, so none repeats these stages: `business_search`
    (default: only the S1 `positive` case searches the business note for absence),
    `narrative_tool_check` (the refused source tool call in the narrative step), `readiness`
    (the readiness payload from the workflow and the step's read inputs; default: no consumers)
    and `quality` (the quality payload from the narrative read and the quality step's inputs)."""
    fw = _fw()
    context = literal(case, "cp1_source_context", pack) if context is None else context
    read_cited(workflow, context)
    search(workflow, "financial", "subsequent")
    if case == "positive" if business_search is None else business_search:
        search(workflow, "business", "acquisition")
    submit_valid(workflow, context)
    fw.financial_reads(workflow)
    submit_valid(workflow, json.dumps(fw.financials(pack)))
    read = workflow.read_inputs()
    if narrative_tool_check:
        refused = workflow.invoke(
            "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
        )
        if refused["error_code"] != "not_permitted":
            raise RuntimeError("narrative step offered a source tool")
    submit_valid(workflow, json.dumps(fw.narrative(read)))
    ready = workflow.read_inputs()
    submit_valid(
        workflow,
        json.dumps({"consumers": []}) if readiness is None else readiness(workflow, ready),
    )
    inputs = json.loads(workflow.read_inputs()["body"])
    submit_valid(workflow, quality(read, inputs))


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


# --- pack B: the snapshot run with a context source (Phase 2, P2-P13) ----------------------------
# Built from the context-identity-periods oracle files only (`PINS` above are untouched): the
# preparer-written `sources/identity-b.json`, `submissions-b.json` and `overlays.json`. The
# oracle's pack-B citations are re-cut against identity-b, so the snapshot pack cannot be reused.

IDP = ROOT / "cases/context-identity-periods"


def _idp(name: str) -> Any:
    return json.loads((IDP / name).read_text(encoding="utf-8"))


def make_pack_b(context_name: str | None) -> PreparedPack:
    """Pack B: identity-b, the snapshot's financial and business sources, then (when named) the
    `context` source prepared from the oracle context's literal bytes. The run is the oracle's
    for that context; with no context it is the snapshot positive run."""
    from deploy_vii.preparation import SourceRequest, prepare_source

    base = make_pack("positive")
    identity = _idp("sources/identity-b.json")
    if (
        hashlib.sha256("\f".join(p["text"] for p in identity["pages"]).encode()).hexdigest()
        != (identity["sha256"])
    ):
        raise RuntimeError("identity-b page hash drift")
    swapped = [
        s.model_copy(
            update={
                "name": identity["name"],
                "sha256": identity["sha256"],
                "spans": tuple(Span(**p) for p in identity["pages"]),
            }
        )
        if s.source_id == "identity"
        else s
        for s in base.sources
    ]
    if context_name is None:
        return PreparedPack(run=base.run, sources=tuple(swapped))
    entry = _idp("manifest.json")["contexts"][context_name]
    raw = (IDP / entry["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise RuntimeError(f"{context_name} context bytes drift")
    context = prepare_source(
        SourceRequest(source_id="context", path=entry["file"], media_type="text/plain"), raw
    )
    run = Run.model_validate_json(json.dumps({k: v for k, v in entry["run"].items() if k != "set"}))
    return PreparedPack(run=run, sources=(*swapped, context))


def _bind(document: Mapping[str, Any], pack: PreparedPack) -> dict[str, Any]:
    text = json.dumps(document, ensure_ascii=False).replace(PACK_PLACEHOLDER, pack.content_hash())
    bound: dict[str, Any] = json.loads(text)
    return bound


def pack_b_submissions(
    pack: PreparedPack, context_name: str | None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    """(CP-0 readiness, CP-1 source_context, CP-1A business_context, CP-2 credit_synthesis) as
    the oracle literals with the pack hash bound. With a context the overlay adds the `context`
    assessment to CP-0 and CP-1, and the borrower entity and its identity scope to CP-1."""
    literals = _idp("submissions-b.json")["positive"]
    readiness = _bind(literals["readiness_review"], pack)
    source_context = _bind(literals["cp1_source_context"], pack)
    business = _bind(literals["business_context"], pack)
    if context_name is not None:
        overlays = _idp("overlays.json")
        readiness["sources"].append(overlays["per_context"][context_name]["cp0_readiness_source"])
        source_context["sources"].append(
            overlays["per_context"][context_name]["cp1_source_context_source"]
        )
        source_context["entities"].append(overlays["borrower_entity"])
        identity = next(s for s in source_context["sources"] if s["source_id"] == "identity")
        identity["scopes"] = [overlays["borrower_scope_on_identity_assessment"]]
    return readiness, source_context, business, json.dumps(literals["credit_synthesis"])


def start_with_context(
    root: Path, context_name: str | None
) -> tuple[OwnerWorkflow, PreparedPack, dict[str, Any]]:
    """Pack B in a fresh owner workflow, with the oracle literals bound to it."""
    pack = make_pack_b(context_name)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    readiness, source_context, business, synthesis = pack_b_submissions(pack, context_name)
    return (
        workflow,
        pack,
        {
            "readiness": readiness,
            "source_context": source_context,
            "business": business,
            "synthesis": synthesis,
        },
    )


def s1a_closed_with_context(
    case: str, root: Path, context_name: str | None
) -> tuple[Path, Path, Path]:
    """One closed S1a run of pack B under `root`: (store, sealed receipt, publication). The slow
    part is the real CP-1 promotion (11-26 minutes); nothing is faked. Only the `positive` case
    has pack-B literals. With no context the snapshot's own closed run is the comparison page."""
    if case != "positive":
        raise ValueError(f"pack B has no {case!r} case")
    if context_name is None:
        return s1a_closed(case, root)
    workflow, pack, lit = start_with_context(root, context_name)
    drive_cp0(workflow, pack, case, text=json.dumps(lit["readiness"], ensure_ascii=False))
    drive_cp1(workflow, pack, case, context=json.dumps(lit["source_context"], ensure_ascii=False))
    receipt = root / "owner-receipt.json"
    cp1a = drive_cp1a(workflow, pack, case, text=json.dumps(lit["business"], ensure_ascii=False))
    if cp1a["status"] != "valid":
        raise RuntimeError(f"CP-1A not valid: {cp1a['issues']}")
    outcome = drive_cp2(workflow, case, read_cp2(workflow), text=lit["synthesis"])
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2 not valid: {outcome['issues']}")
    finish(workflow, receipt)
    return root / "store", receipt, root / "model"
