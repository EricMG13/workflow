"""CP-3 run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed R3 run (CP-0, CP-1, CP-1A, CP-2, CP-3, then CP-MODEL) over the pinned oracle in
`cases/cp3-cp6-owner`, driven through the public `OwnerWorkflow` API only. G2 imports
`cp3_closed`. The CP-6 half of the lease is draft and CP-6 has no owner spec yet (rulings
stage2 Q2), so this file exports no `cp6_closed`; `s1a_runs` supplies the CP-0 to CP-2 stage
helpers the two oracles share. Nothing here asserts expected values: the oracle files are read,
never derived (`tests/test_owner_cp3.py` asserts).

Stage 5 only: the run needs a genuine CP-1 promotion (11-26 minutes per case).
"""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import s1a_runs as s1

from deploy_vii.contracts import Fact, Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases/cp3-cp6-owner"
_FILES = ("manifest.json", "submissions.json", "expected.json")
CASES: Mapping[str, str] = {"positive": "cp3-cp6-positive", "gap": "cp3-cp6-gap"}
RUN = "R3"
PACK_PLACEHOLDER = s1.PACK_PLACEHOLDER
STEP = "relative_value"
# The oracle files are pinned by `cases/PINS.json`, the shared manifest LEAD regenerates.
PINS: dict[Path, str] = {
    CASE_DIR / name: digest
    for key, digest in json.loads((ROOT / "cases/PINS.json").read_text(encoding="utf-8")).items()
    for name in _FILES
    if key == f"cases/cp3-cp6-owner/{name}"
}


def oracle() -> dict[str, Any]:
    """The three pinned CP-3/CP-6 oracle files and the S1 oracle they build on (itself pinned);
    a drifted file fails."""
    for path, digest in PINS.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"oracle drift: {path.name}")
    return {
        "manifest": json.loads((CASE_DIR / "manifest.json").read_text()),
        "submissions": json.loads((CASE_DIR / "submissions.json").read_text()),
        "expected": json.loads((CASE_DIR / "expected.json").read_text()),
        "s1": s1.oracle(),
    }


def make_pack(case: str) -> PreparedPack:
    """The case's R3 pack: identity and financial as in S1, the S1 positive business note, and
    (positive only) the `market` quotation sheet, each hash-checked against the oracle."""
    data = oracle()
    manifest, financial, base = data["manifest"], data["s1"]["financial"], data["s1"]["manifest"]
    entry = next(c for c in manifest["cases"] if c["case_id"] == CASES[case])
    market = manifest["market_source"]
    business = base["business_source"]["positive"]
    common = base["business_source"]["common"]
    pages: dict[str, tuple[list[dict[str, Any]], str]] = {
        s["source_id"]: (s["pages"], s["sha256"]) for s in financial["sources"]
    }
    pages["business"] = (business["pages"], business["sha256"])
    pages["market"] = (market["pages"], market["sha256"])
    extra: dict[str, dict[str, Any]] = {
        "business": {
            "media_type": common["media_type"],
            "extractor": common["extractor"],
            "extraction_status": common["extraction_status"],
        },
        "market": {
            "media_type": market["media_type"],
            "extractor": market["extractor"],
            "extraction_status": market["extraction_status"],
        },
    }
    sources = []
    for item in entry["pack_sources"]:
        source_id = item["source_id"]
        spans, digest = pages[source_id]
        if hashlib.sha256("\f".join(p["text"] for p in spans).encode()).hexdigest() != digest:
            raise RuntimeError(f"{source_id} page hash drift")
        sources.append(
            Source(
                source_id=source_id,
                name=item["name"],
                status=item["status"],
                sha256=digest,
                spans=tuple(Span(**p) for p in spans),
                limitation=item["limitation"],
                **extra.get(source_id, {"extraction_status": "complete"}),
            )
        )
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["runs"][RUN]["run"])),
        sources=tuple(sources),
    )


def _dump(document: Any, pack: PreparedPack | None) -> str:
    text = json.dumps(document, ensure_ascii=False)
    return text if pack is None else text.replace(PACK_PLACEHOLDER, pack.content_hash())


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    """One literal submission of the case as JSON text; the pack hash is bound where the oracle
    marks it. `{{FIG:name}}` stays in `relative_value` until `bind_figures`. The oracle composes
    three literals from S1: `readiness_review` takes the run's full document, `business_context`
    is the S1 positive literal with `sources` plus `sources_append` and the run's `consumers`,
    and `credit_synthesis` is the S1 positive literal unchanged (`change: none`)."""
    submissions = oracle()["submissions"][case]
    s1_positive = oracle()["s1"]["submissions"]["positive"]
    match name:
        case "readiness_review":
            return _dump(submissions[name][RUN], pack)
        case "business_context":
            spec = submissions[name]
            merged = {
                **s1_positive[name],
                "sources": [*s1_positive[name]["sources"], *spec["sources_append"]],
                "consumers": spec["consumers"][RUN],
            }
            return _dump(merged, pack)
        case "credit_synthesis":
            if submissions[name]["change"] != "none":
                raise RuntimeError("credit_synthesis: the oracle changes the S1 literal")
            return _dump(s1_positive[name], pack)
        case "cp1_source_context" | "relative_value":
            return _dump(submissions[name], pack)
    raise KeyError(name)


figure_names = s1.figure_names
bind_figures = s1.bind_figures


def cp1_bindings(store: Execution, names: list[str]) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token): the one CP-1 T4.10 LTM fact of each metric, selected from
    the settled CP-1 head (as S1, zero or several candidates fail), with the oracle's unit token.
    CP-3 has no `read_inputs` view, so there is no read body to cross-check (CP-3 lease, deferred
    like S1a Q6); the product validator checks each reference."""
    figures = oracle()["submissions"]["figures"]
    cp1 = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts: tuple[Fact, ...] = store.head_module(cp1).facts
    return {n: (s1.figure_fact(facts, n).fact_id, figures[n]["unit_token"]) for n in names}


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    return workflow, pack


def promoted(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled, CP-1A begun and untouched. The slow part (11-26 minutes).

    `s1.drive_cp1` searches the business note for absence only for its `positive` case; the
    cp3-cp6 pack carries the S1 positive business note in both cases (event scan
    `no_events_identified`), so the S1 positive path is the one that applies to both."""
    workflow, pack = start(case, root)
    s1.drive_cp0(workflow, pack, case, text=literal(case, "readiness_review", pack))
    s1.drive_cp1(workflow, pack, "positive", context=literal(case, "cp1_source_context", pack))
    return workflow, pack


def drive_cp3(
    workflow: OwnerWorkflow, case: str, *, text: str | None = None, read: bool = True
) -> dict[str, Any]:
    """The literal relative_value (or `text`): the figures bound to the settled CP-1 head, one ok
    `read_pages` per cited market page (the positive case; the gap literal cites none), then
    the submit. `unread-citations` is the only rule, so no search is required."""
    payload = literal(case, STEP) if text is None else text
    names = figure_names(payload)
    payload = bind_figures(payload, cp1_bindings(workflow._store, names))
    if read:
        s1.read_cited(workflow, payload)
    return workflow.submit_review(payload)


def reach_cp3(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """From a fresh run to CP-3 active, untouched: CP-0, CP-1, CP-1A and CP-2 (figures bound)
    settled. A refusal test clones this state, so no call of the CP-3 step has been made."""
    workflow, pack = promoted(case, root)
    cp1a = s1.drive_cp1a(workflow, pack, case, text=literal(case, "business_context", pack))
    if cp1a["status"] != "valid":
        raise RuntimeError(f"CP-1A not valid: {cp1a['issues']}")
    body = s1.read_cp2(workflow)
    cp2 = s1.drive_cp2(workflow, case, body, text=literal(case, "credit_synthesis"))
    if cp2["status"] != "valid":
        raise RuntimeError(f"CP-2 not valid: {cp2['issues']}")
    return workflow, pack


def close(workflow: OwnerWorkflow, case: str, receipt: Path) -> None:
    """From CP-3 active to the sealed receipt: CP-3, then CP-MODEL published."""
    cp3 = drive_cp3(workflow, case)
    if cp3["status"] != "valid":
        raise RuntimeError(f"CP-3 not valid: {cp3['issues']}")
    s1.finish(workflow, receipt)


def cp3_closed(case: str, root: Path) -> tuple[Path, Path, Path]:
    """One closed R3 run of `case` under `root`: (store, sealed receipt, publication)."""
    workflow, _ = reach_cp3(case, root)
    close(workflow, case, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", root / "model"
